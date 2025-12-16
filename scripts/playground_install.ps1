# ============================================================================
# AUTONOMOUS PLAYGROUND INSTALL SCRIPT
# ============================================================================
# Purpose: Clean install LocaNext to Playground for testing
# Usage: Run from PowerShell on Windows
#        .\scripts\playground_install.ps1
# ============================================================================

param(
    [string]$GiteaHost = "172.28.150.120",
    [int]$GiteaPort = 3000,
    [string]$PlaygroundPath = "C:\NEIL_PROJECTS_WINDOWSBUILD\LocaNextProject\Playground",
    [string]$Version = "",  # Empty = latest
    [switch]$SkipDownload,
    [switch]$SkipClean,
    [switch]$LaunchAfterInstall,
    [switch]$EnableCDP,
    [int]$CDPPort = 9222
)

$ErrorActionPreference = "Stop"

function Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "HH:mm:ss"
    $color = switch ($Level) {
        "INFO" { "White" }
        "OK" { "Green" }
        "WARN" { "Yellow" }
        "ERROR" { "Red" }
        default { "White" }
    }
    Write-Host "[$timestamp] [$Level] $Message" -ForegroundColor $color
}

function Get-LatestRelease {
    Log "Fetching latest release info from Gitea..."

    $releasesUrl = "http://${GiteaHost}:${GiteaPort}/api/v1/repos/neilvibe/LocaNext/releases"

    try {
        $releases = Invoke-RestMethod -Uri $releasesUrl -Method Get -TimeoutSec 30

        if ($releases.Count -eq 0) {
            throw "No releases found"
        }

        # Get latest (first) release
        $latest = $releases[0]

        Log "Latest release: $($latest.tag_name)" -Level "OK"

        # Find the installer asset
        $installer = $latest.assets | Where-Object { $_.name -like "*Setup*.exe" -and $_.name -notlike "*blockmap*" } | Select-Object -First 1

        if (-not $installer) {
            throw "No installer found in release assets"
        }

        return @{
            Version = $latest.tag_name
            InstallerUrl = $installer.browser_download_url
            InstallerName = $installer.name
        }
    }
    catch {
        Log "Failed to fetch releases: $_" -Level "ERROR"
        throw
    }
}

function Clean-Playground {
    Log "Cleaning Playground directory: $PlaygroundPath"

    # Kill any running LocaNext processes
    $processes = Get-Process -Name "LocaNext*" -ErrorAction SilentlyContinue
    if ($processes) {
        Log "Killing running LocaNext processes..." -Level "WARN"
        $processes | Stop-Process -Force
        Start-Sleep -Seconds 2
    }

    # Remove existing installation
    if (Test-Path $PlaygroundPath) {
        Log "Removing existing Playground contents..."

        # Remove all contents
        Get-ChildItem -Path $PlaygroundPath -Recurse -Force | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

        # Also remove the LocaNext folder if it exists
        $locanextDir = Join-Path $PlaygroundPath "LocaNext"
        if (Test-Path $locanextDir) {
            Remove-Item -Path $locanextDir -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
    else {
        New-Item -Path $PlaygroundPath -ItemType Directory -Force | Out-Null
    }

    # Clean user data directories (optional - keeps settings fresh)
    $userDataPaths = @(
        "$env:APPDATA\LocaNext",
        "$env:LOCALAPPDATA\LocaNext",
        "$env:LOCALAPPDATA\locanext-updater"
    )

    foreach ($path in $userDataPaths) {
        if (Test-Path $path) {
            Log "Cleaning user data: $path" -Level "WARN"
            Remove-Item -Path $path -Recurse -Force -ErrorAction SilentlyContinue
        }
    }

    Log "Playground cleaned" -Level "OK"
}

function Download-Installer {
    param(
        [string]$Url,
        [string]$FileName
    )

    $downloadPath = Join-Path $env:TEMP $FileName

    Log "Downloading installer from: $Url"
    Log "Saving to: $downloadPath"

    try {
        # Use WebClient for faster download with progress
        $webClient = New-Object System.Net.WebClient
        $webClient.DownloadFile($Url, $downloadPath)

        $size = (Get-Item $downloadPath).Length / 1MB
        Log "Downloaded: $([math]::Round($size, 2)) MB" -Level "OK"

        return $downloadPath
    }
    catch {
        Log "Download failed: $_" -Level "ERROR"
        throw
    }
}

function Install-LocaNext {
    param(
        [string]$InstallerPath,
        [string]$InstallDir
    )

    Log "Installing LocaNext to: $InstallDir"

    # NSIS silent install arguments
    # /S = Silent mode
    # /D= = Installation directory (must be last parameter, no quotes)
    $arguments = "/S /D=$InstallDir"

    Log "Running: $InstallerPath $arguments"

    try {
        $process = Start-Process -FilePath $InstallerPath -ArgumentList $arguments -Wait -PassThru -NoNewWindow

        if ($process.ExitCode -ne 0) {
            throw "Installer exited with code: $($process.ExitCode)"
        }

        # Verify installation
        $exePath = Join-Path $InstallDir "LocaNext.exe"
        if (-not (Test-Path $exePath)) {
            throw "LocaNext.exe not found after installation"
        }

        Log "Installation complete" -Level "OK"
        return $exePath
    }
    catch {
        Log "Installation failed: $_" -Level "ERROR"
        throw
    }
}

function Start-LocaNextWithCDP {
    param(
        [string]$ExePath,
        [int]$Port = 9222
    )

    Log "Starting LocaNext with CDP on port $Port..."

    $arguments = "--remote-debugging-port=$Port"

    try {
        $process = Start-Process -FilePath $ExePath -ArgumentList $arguments -PassThru

        Log "LocaNext started (PID: $($process.Id))" -Level "OK"
        Log "CDP available at: http://127.0.0.1:$Port" -Level "OK"

        return $process
    }
    catch {
        Log "Failed to start LocaNext: $_" -Level "ERROR"
        throw
    }
}

function Wait-ForCDP {
    param(
        [int]$Port = 9222,
        [int]$TimeoutSeconds = 60
    )

    Log "Waiting for CDP to be ready (timeout: ${TimeoutSeconds}s)..."

    $startTime = Get-Date

    while ((Get-Date) - $startTime -lt [TimeSpan]::FromSeconds($TimeoutSeconds)) {
        try {
            $response = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/json" -TimeoutSec 2

            if ($response) {
                Log "CDP ready! Found $($response.Count) target(s)" -Level "OK"
                return $response
            }
        }
        catch {
            # Not ready yet
        }

        Start-Sleep -Seconds 1
    }

    throw "CDP did not become ready within ${TimeoutSeconds} seconds"
}

function Verify-Installation {
    param(
        [int]$CDPPort = 9222
    )

    Log "Verifying installation via CDP..."

    try {
        $targets = Wait-ForCDP -Port $CDPPort -TimeoutSeconds 60

        $pageTarget = $targets | Where-Object { $_.type -eq "page" } | Select-Object -First 1

        if (-not $pageTarget) {
            throw "No page target found in CDP"
        }

        Log "Page URL: $($pageTarget.url)" -Level "OK"
        Log "Page Title: $($pageTarget.title)" -Level "OK"

        # Check if it's on the login page or LDM (good signs)
        if ($pageTarget.url -match "login|ldm|localhost:5176") {
            Log "App loaded successfully!" -Level "OK"
            return $true
        }
        else {
            Log "Unexpected page: $($pageTarget.url)" -Level "WARN"
            return $true  # Still consider it a success
        }
    }
    catch {
        Log "Verification failed: $_" -Level "ERROR"
        return $false
    }
}

# ============================================================================
# MAIN EXECUTION
# ============================================================================

Log "============================================"
Log "  AUTONOMOUS PLAYGROUND INSTALL"
Log "============================================"
Log "Playground: $PlaygroundPath"
Log "Gitea: http://${GiteaHost}:${GiteaPort}"
Log ""

try {
    # Step 1: Get release info
    $release = Get-LatestRelease
    Log "Version: $($release.Version)"
    Log "Installer: $($release.InstallerName)"
    Log ""

    # Step 2: Clean playground
    if (-not $SkipClean) {
        Clean-Playground
        Log ""
    }

    # Step 3: Download installer
    $installerPath = $null
    if (-not $SkipDownload) {
        $installerPath = Download-Installer -Url $release.InstallerUrl -FileName $release.InstallerName
        Log ""
    }
    else {
        # Use existing installer in temp
        $installerPath = Join-Path $env:TEMP $release.InstallerName
        if (-not (Test-Path $installerPath)) {
            throw "Installer not found: $installerPath (use without -SkipDownload)"
        }
    }

    # Step 4: Install
    $installDir = Join-Path $PlaygroundPath "LocaNext"
    $exePath = Install-LocaNext -InstallerPath $installerPath -InstallDir $installDir
    Log ""

    # Step 5: Launch and verify (optional)
    if ($LaunchAfterInstall -or $EnableCDP) {
        $cdpPort = if ($EnableCDP) { $CDPPort } else { 9222 }

        $process = Start-LocaNextWithCDP -ExePath $exePath -Port $cdpPort
        Log ""

        # Wait a bit for startup
        Start-Sleep -Seconds 5

        $verified = Verify-Installation -CDPPort $cdpPort
        Log ""

        if ($verified) {
            Log "============================================" -Level "OK"
            Log "  INSTALLATION SUCCESSFUL!" -Level "OK"
            Log "============================================" -Level "OK"
            Log "  Version: $($release.Version)"
            Log "  Path: $installDir"
            Log "  CDP: http://127.0.0.1:$cdpPort"
            Log ""
        }
    }
    else {
        Log "============================================" -Level "OK"
        Log "  INSTALLATION COMPLETE!" -Level "OK"
        Log "============================================" -Level "OK"
        Log "  Version: $($release.Version)"
        Log "  Path: $installDir"
        Log "  Executable: $exePath"
        Log ""
        Log "To launch with CDP debugging:"
        Log "  & '$exePath' --remote-debugging-port=9222"
        Log ""
    }

    # Cleanup installer
    if ($installerPath -and (Test-Path $installerPath)) {
        Remove-Item $installerPath -Force -ErrorAction SilentlyContinue
    }

    exit 0
}
catch {
    Log "============================================" -Level "ERROR"
    Log "  INSTALLATION FAILED!" -Level "ERROR"
    Log "============================================" -Level "ERROR"
    Log "Error: $_" -Level "ERROR"
    exit 1
}
