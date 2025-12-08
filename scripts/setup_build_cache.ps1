<#
.SYNOPSIS
    LocaNext Build Cache Setup Script

.DESCRIPTION
    Initializes the build cache on Windows machine for faster Gitea CI builds.
    Downloads and caches: VC++ Redistributable, Python Embedded, NSIS includes.
    npm packages are cached during first build (hash-dependent).

.NOTES
    Run this ONCE on the Windows build machine before using cached builds.
    Location: C:\BuildCache\

.EXAMPLE
    .\setup_build_cache.ps1
    .\setup_build_cache.ps1 -Force  # Re-download everything
#>

param(
    [switch]$Force  # Force re-download even if cache exists
)

$ErrorActionPreference = "Stop"

# Configuration
$CacheRoot = "C:\BuildCache"
$ManifestPath = "$CacheRoot\CACHE_MANIFEST.json"

# Versions (update these when upgrading)
$PythonVersion = "3.11.9"
$VCRedistVersion = "17.8"
$NSISVersion = "1.0"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  LocaNext Build Cache Setup" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Create cache root
if (-not (Test-Path $CacheRoot)) {
    New-Item -ItemType Directory -Path $CacheRoot -Force | Out-Null
    Write-Host "[OK] Created cache root: $CacheRoot" -ForegroundColor Green
} else {
    Write-Host "[OK] Cache root exists: $CacheRoot" -ForegroundColor Green
}

# Initialize manifest
$manifest = @{
    version = "1.0"
    description = "LocaNext Build Cache Manifest"
    created = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ssZ")
    updated = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ssZ")
    cache_root = $CacheRoot
    components = @{}
}

# ============================================
# 1. VC++ Redistributable
# ============================================
Write-Host ""
Write-Host "--- VC++ Redistributable ---" -ForegroundColor Yellow

$vcredistDir = "$CacheRoot\vcredist"
$vcredistPath = "$vcredistDir\vc_redist.x64.exe"
$vcredistUrl = "https://aka.ms/vs/17/release/vc_redist.x64.exe"

if ((Test-Path $vcredistPath) -and -not $Force) {
    $size = [math]::Round((Get-Item $vcredistPath).Length / 1MB, 1)
    Write-Host "[CACHED] VC++ Redistributable exists ($size MB)" -ForegroundColor Green
} else {
    Write-Host "Downloading VC++ Redistributable..." -ForegroundColor Cyan
    New-Item -ItemType Directory -Path $vcredistDir -Force | Out-Null
    Invoke-WebRequest -Uri $vcredistUrl -OutFile $vcredistPath -UseBasicParsing
    $size = [math]::Round((Get-Item $vcredistPath).Length / 1MB, 1)
    Write-Host "[OK] Downloaded VC++ Redistributable ($size MB)" -ForegroundColor Green
}

$manifest.components.vcredist = @{
    version = $VCRedistVersion
    path = $vcredistPath
    size_mb = [math]::Round((Get-Item $vcredistPath).Length / 1MB, 1)
    hash = (Get-FileHash $vcredistPath -Algorithm SHA256).Hash.Substring(0, 16)
    cached_at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ssZ")
}

# ============================================
# 2. Python Embedded + pip packages
# ============================================
Write-Host ""
Write-Host "--- Python Embedded ---" -ForegroundColor Yellow

$pythonDir = "$CacheRoot\python-embedded\python-$PythonVersion"
$pythonExe = "$pythonDir\python.exe"
$pythonUrl = "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-embed-amd64.zip"

if ((Test-Path $pythonExe) -and -not $Force) {
    $size = [math]::Round((Get-ChildItem $pythonDir -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB, 1)
    Write-Host "[CACHED] Python $PythonVersion exists ($size MB)" -ForegroundColor Green
} else {
    Write-Host "Downloading Python $PythonVersion Embedded..." -ForegroundColor Cyan

    # Create directory
    New-Item -ItemType Directory -Path $pythonDir -Force | Out-Null

    # Download and extract
    $zipPath = "$CacheRoot\python-embedded.zip"
    Invoke-WebRequest -Uri $pythonUrl -OutFile $zipPath -UseBasicParsing
    Expand-Archive -Path $zipPath -DestinationPath $pythonDir -Force
    Remove-Item $zipPath

    # Enable pip in embedded Python
    $pthFile = Get-ChildItem "$pythonDir\python*._pth" | Select-Object -First 1
    if ($pthFile) {
        $content = Get-Content $pthFile.FullName
        $content = $content -replace '#import site', 'import site'
        Set-Content -Path $pthFile.FullName -Value $content
    }

    # Install pip
    Write-Host "Installing pip..." -ForegroundColor Cyan
    Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile "$pythonDir\get-pip.py" -UseBasicParsing
    & "$pythonExe" "$pythonDir\get-pip.py" --no-warn-script-location 2>&1 | Out-Null
    Remove-Item "$pythonDir\get-pip.py"

    # Install all required packages
    Write-Host "Installing pip packages (this takes a few minutes)..." -ForegroundColor Cyan
    $packages = @(
        "fastapi", "uvicorn", "python-multipart", "python-socketio",
        "sqlalchemy", "aiosqlite",
        "PyJWT", "python-jose", "passlib", "python-dotenv", "bcrypt",
        "pydantic", "pydantic-settings", "email-validator",
        "pandas", "openpyxl", "xlrd",
        "httpx", "requests", "loguru", "tqdm", "pyyaml", "huggingface_hub"
    )

    & "$pythonExe" -m pip install --no-warn-script-location $packages 2>&1 | Out-Null

    $size = [math]::Round((Get-ChildItem $pythonDir -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB, 1)
    Write-Host "[OK] Python $PythonVersion + packages installed ($size MB)" -ForegroundColor Green
}

# Verify Python works
Write-Host "Verifying Python installation..." -ForegroundColor Cyan
$pythonVer = & "$pythonExe" --version 2>&1
Write-Host "  $pythonVer" -ForegroundColor Gray

$manifest.components.python_embedded = @{
    version = $PythonVersion
    path = $pythonDir
    size_mb = [math]::Round((Get-ChildItem $pythonDir -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB, 1)
    includes_pip = $true
    requirements_hash = ""  # Will be set during build
    cached_at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ssZ")
}

# ============================================
# 3. NSIS Include Files
# ============================================
Write-Host ""
Write-Host "--- NSIS Include Files ---" -ForegroundColor Yellow

$nsisDir = "$CacheRoot\nsis-includes"
$nsisFiles = @(
    "StdUtils.nsh", "WinVer.nsh", "allowOnlyOneInstallerInstance.nsh",
    "assistedInstaller.nsh", "boringInstaller.nsh", "checkAppRunning.nsh",
    "extractAppPackage.nsh", "fileAssociation.nsh", "installer.nsh",
    "installSection.nsh", "multiUser.nsh", "multiUserUi.nsh",
    "oneClick.nsh", "UAC.nsh", "uninstaller.nsh"
)
$nsisBaseUrl = "https://raw.githubusercontent.com/electron-userland/electron-builder/master/packages/app-builder-lib/templates/nsis/include"

$stdUtilsPath = "$nsisDir\StdUtils.nsh"

if ((Test-Path $stdUtilsPath) -and -not $Force) {
    Write-Host "[CACHED] NSIS includes exist ($($nsisFiles.Count) files)" -ForegroundColor Green
} else {
    Write-Host "Downloading NSIS include files..." -ForegroundColor Cyan
    New-Item -ItemType Directory -Path $nsisDir -Force | Out-Null

    foreach ($file in $nsisFiles) {
        $url = "$nsisBaseUrl/$file"
        $dest = "$nsisDir\$file"
        Invoke-WebRequest -Uri $url -OutFile $dest -UseBasicParsing 2>&1 | Out-Null
    }

    Write-Host "[OK] Downloaded $($nsisFiles.Count) NSIS include files" -ForegroundColor Green
}

$manifest.components.nsis_includes = @{
    version = $NSISVersion
    path = $nsisDir
    file_count = $nsisFiles.Count
    cached_at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ssZ")
}

# ============================================
# 4. npm cache placeholder
# ============================================
Write-Host ""
Write-Host "--- npm Cache ---" -ForegroundColor Yellow

$npmCacheDir = "$CacheRoot\npm-cache"
if (-not (Test-Path $npmCacheDir)) {
    New-Item -ItemType Directory -Path $npmCacheDir -Force | Out-Null
}
Write-Host "[INFO] npm cache will be populated during first build" -ForegroundColor Gray
Write-Host "       (keyed by package-lock.json hash)" -ForegroundColor Gray

$manifest.components.npm_cache = @{
    path = $npmCacheDir
    packagelock_hash = ""  # Will be set during build
    cached_at = ""
}

# ============================================
# Save Manifest
# ============================================
Write-Host ""
Write-Host "--- Saving Manifest ---" -ForegroundColor Yellow

$manifest | ConvertTo-Json -Depth 10 | Out-File $ManifestPath -Encoding UTF8
Write-Host "[OK] Manifest saved: $ManifestPath" -ForegroundColor Green

# ============================================
# Summary
# ============================================
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Cache Setup Complete!" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Cache Location: $CacheRoot" -ForegroundColor White
Write-Host ""

# Calculate total size
$totalSize = 0
Get-ChildItem $CacheRoot -Recurse -File | ForEach-Object { $totalSize += $_.Length }
$totalSizeMB = [math]::Round($totalSize / 1MB, 1)

Write-Host "Components cached:" -ForegroundColor White
Write-Host "  - VC++ Redistributable: $($manifest.components.vcredist.size_mb) MB" -ForegroundColor Gray
Write-Host "  - Python $PythonVersion + packages: $($manifest.components.python_embedded.size_mb) MB" -ForegroundColor Gray
Write-Host "  - NSIS includes: $($manifest.components.nsis_includes.file_count) files" -ForegroundColor Gray
Write-Host "  - npm cache: (pending first build)" -ForegroundColor Gray
Write-Host ""
Write-Host "Total cache size: $totalSizeMB MB" -ForegroundColor Green
Write-Host ""
Write-Host "Next: Run a Gitea build to populate npm cache" -ForegroundColor Yellow
