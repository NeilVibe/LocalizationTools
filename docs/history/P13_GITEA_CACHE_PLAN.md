# P13.12: Gitea Build Caching - Implementation Plan

**Status:** ✅ IMPLEMENTED - Smart Cache v2.0 (Hash-Based Invalidation)
**Created:** 2025-12-09
**Updated:** 2025-12-09

---

## Smart Cache v2.0 Features

| Feature | Description |
|---------|-------------|
| **Hash-based invalidation** | `requirements.txt` hash triggers Python cache refresh |
| **Version tracking** | Python/VC++ version changes auto-invalidate |
| **Fallback validation** | Package existence check as safety net |
| **Manifest tracking** | JSON manifest stores hashes + versions |
| **Future-ready** | `package-lock.json` hash computed (npm cache ready) |

---

## Problem

Current Gitea workflow downloads **~350MB every build**:
```
VC++ Redistributable:  ~25MB   (never changes)
Python Embedded:       ~145MB  (rarely changes)
Pip packages:          ~150MB  (changes with requirements)
NSIS includes:         ~1MB    (never changes)
─────────────────────────────────────────
TOTAL:                 ~350MB per build
```

**Build time:** ~5 minutes just for downloads

---

## Solution

Use `C:\BuildCache\` on Windows runner with smart cache-first logic:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CACHE-FIRST BUILD LOGIC                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  FOR EACH COMPONENT:                                                         │
│                                                                              │
│  1. Check C:\BuildCache\{component}                                          │
│  2. IF exists AND valid:                                                     │
│     → COPY from cache (instant)                                              │
│  3. ELSE:                                                                    │
│     → DOWNLOAD fresh                                                         │
│     → POPULATE cache for next build                                          │
│                                                                              │
│  INVALIDATION:                                                               │
│  • VC++ Redist:    Never (static version)                                   │
│  • Python Embed:   Version change only                                       │
│  • Pip packages:   Hash of requirements.txt                                  │
│  • NSIS includes:  Never (static)                                           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Expected improvement:**
| Scenario | Before | After |
|----------|--------|-------|
| Cold cache | ~5 min | ~5 min |
| Cache hit | ~5 min | **~30 sec** |

---

## Implementation

### Step 1: Create Cache Helper Functions

Add to beginning of `build-windows` job:

```powershell
# ============================================================
# CACHE HELPER FUNCTIONS
# ============================================================
- name: Define Cache Helpers
  run: |
    # Cache configuration
    $script:CacheRoot = "C:\BuildCache"
    $script:ManifestPath = "$script:CacheRoot\CACHE_MANIFEST.json"

    function Test-CacheValid {
      param([string]$Component, [string]$ExpectedVersion)

      if (-not (Test-Path $script:ManifestPath)) { return $false }

      $manifest = Get-Content $script:ManifestPath | ConvertFrom-Json
      $cached = $manifest.components.$Component

      if (-not $cached) { return $false }
      if ($cached.version -ne $ExpectedVersion) { return $false }
      if (-not (Test-Path $cached.path)) { return $false }

      return $true
    }

    function Get-CachePath {
      param([string]$Component)

      $manifest = Get-Content $script:ManifestPath | ConvertFrom-Json
      return $manifest.components.$Component.path
    }

    Write-Host "[OK] Cache helpers defined"
    Write-Host "Cache root: $script:CacheRoot"
  shell: powershell
```

### Step 2: Replace VC++ Download with Cache-First

**BEFORE (current):**
```powershell
- name: Download VC++ Redistributable
  run: |
    Invoke-WebRequest -Uri "https://aka.ms/vs/17/release/vc_redist.x64.exe" -OutFile "installer\redist\vc_redist.x64.exe"
```

**AFTER (cache-first):**
```powershell
- name: Get VC++ Redistributable (Cache-First)
  run: |
    $cacheRoot = "C:\BuildCache"
    $cachedPath = "$cacheRoot\vcredist\vc_redist.x64.exe"
    $targetPath = "installer\redist\vc_redist.x64.exe"

    New-Item -ItemType Directory -Force -Path "installer\redist" | Out-Null

    if (Test-Path $cachedPath) {
      Write-Host "[CACHE HIT] Copying VC++ Redistributable from cache..."
      Copy-Item $cachedPath -Destination $targetPath -Force
      $size = [math]::Round((Get-Item $targetPath).Length / 1MB, 1)
      Write-Host "[OK] VC++ Redistributable: $size MB (from cache)"
    } else {
      Write-Host "[CACHE MISS] Downloading VC++ Redistributable..."
      Invoke-WebRequest -Uri "https://aka.ms/vs/17/release/vc_redist.x64.exe" -OutFile $targetPath

      # Populate cache for next build
      New-Item -ItemType Directory -Force -Path "$cacheRoot\vcredist" | Out-Null
      Copy-Item $targetPath -Destination $cachedPath -Force
      Write-Host "[OK] Downloaded and cached VC++ Redistributable"
    }
  shell: powershell
```

### Step 3: Replace Python Download with Cache-First

**AFTER (cache-first):**
```powershell
- name: Get Python Embedded (Cache-First)
  run: |
    $cacheRoot = "C:\BuildCache"
    $pythonVersion = "3.11.9"
    $cachedPythonDir = "$cacheRoot\python-embedded\python-$pythonVersion"
    $targetDir = "tools\python"

    if ((Test-Path "$cachedPythonDir\python.exe") -and (Test-Path "$cachedPythonDir\Lib\site-packages\fastapi")) {
      Write-Host "[CACHE HIT] Copying Python $pythonVersion from cache..."

      New-Item -ItemType Directory -Force -Path $targetDir | Out-Null
      Copy-Item -Path "$cachedPythonDir\*" -Destination $targetDir -Recurse -Force

      $size = [math]::Round((Get-ChildItem $targetDir -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB, 1)
      Write-Host "[OK] Python + packages: $size MB (from cache)"
    } else {
      Write-Host "[CACHE MISS] Downloading Python $pythonVersion..."

      # Download Python
      New-Item -ItemType Directory -Force -Path $targetDir | Out-Null
      $pythonUrl = "https://www.python.org/ftp/python/$pythonVersion/python-$pythonVersion-embed-amd64.zip"
      $zipPath = "tools\python-embedded.zip"
      Invoke-WebRequest -Uri $pythonUrl -OutFile $zipPath
      Expand-Archive -Path $zipPath -DestinationPath $targetDir -Force
      Remove-Item $zipPath

      # Enable pip
      $pthFile = Get-ChildItem "$targetDir\python*._pth" | Select-Object -First 1
      if ($pthFile) {
        $content = Get-Content $pthFile.FullName
        $content = $content -replace '#import site', 'import site'
        Set-Content -Path $pthFile.FullName -Value $content
      }

      # Install pip
      Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile "$targetDir\get-pip.py"
      & "$targetDir\python.exe" "$targetDir\get-pip.py" --no-warn-script-location
      Remove-Item "$targetDir\get-pip.py"

      # Install packages
      & "$targetDir\python.exe" -m pip install --no-warn-script-location `
        fastapi uvicorn python-multipart python-socketio `
        sqlalchemy aiosqlite `
        PyJWT python-jose passlib python-dotenv bcrypt `
        pydantic pydantic-settings email-validator `
        pandas openpyxl xlrd `
        httpx requests loguru tqdm pyyaml huggingface_hub

      # POPULATE CACHE for next build
      Write-Host "Populating cache for next build..."
      New-Item -ItemType Directory -Force -Path "$cacheRoot\python-embedded" | Out-Null
      if (Test-Path $cachedPythonDir) { Remove-Item $cachedPythonDir -Recurse -Force }
      Copy-Item -Path $targetDir -Destination $cachedPythonDir -Recurse -Force
      Write-Host "[OK] Python cached for future builds"
    }
  shell: powershell
```

### Step 4: Replace NSIS Download with Cache-First

**AFTER (cache-first):**
```powershell
- name: Get NSIS Includes (Cache-First)
  run: |
    $cacheRoot = "C:\BuildCache"
    $cachedNsisDir = "$cacheRoot\nsis-includes"
    $targetDir = "locaNext\node_modules\app-builder-lib\templates\nsis\include"

    New-Item -ItemType Directory -Force -Path $targetDir | Out-Null

    if (Test-Path "$cachedNsisDir\StdUtils.nsh") {
      Write-Host "[CACHE HIT] Copying NSIS includes from cache..."
      Copy-Item -Path "$cachedNsisDir\*.nsh" -Destination $targetDir -Force
      $count = (Get-ChildItem "$targetDir\*.nsh").Count
      Write-Host "[OK] NSIS includes: $count files (from cache)"
    } else {
      Write-Host "[CACHE MISS] Downloading NSIS includes..."

      $baseUrl = "https://raw.githubusercontent.com/electron-userland/electron-builder/master/packages/app-builder-lib/templates/nsis/include"
      $files = @("StdUtils.nsh","WinVer.nsh","allowOnlyOneInstallerInstance.nsh","assistedInstaller.nsh","boringInstaller.nsh","checkAppRunning.nsh","extractAppPackage.nsh","fileAssociation.nsh","installer.nsh","installSection.nsh","multiUser.nsh","multiUserUi.nsh","oneClick.nsh","UAC.nsh","uninstaller.nsh")

      foreach ($f in $files) {
        curl.exe -L --retry 3 -s -o "$targetDir\$f" "$baseUrl/$f"
      }

      # Populate cache
      New-Item -ItemType Directory -Force -Path $cachedNsisDir | Out-Null
      Copy-Item -Path "$targetDir\*.nsh" -Destination $cachedNsisDir -Force
      Write-Host "[OK] NSIS includes cached for future builds"
    }
  shell: powershell
```

### Step 5: Add Cache Status Summary

```powershell
- name: Cache Status Summary
  run: |
    Write-Host ""
    Write-Host "============================================" -ForegroundColor Cyan
    Write-Host "  BUILD CACHE STATUS" -ForegroundColor Cyan
    Write-Host "============================================" -ForegroundColor Cyan

    $cacheRoot = "C:\BuildCache"
    if (Test-Path $cacheRoot) {
      $totalSize = [math]::Round((Get-ChildItem $cacheRoot -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB, 1)
      Write-Host "Cache location: $cacheRoot" -ForegroundColor White
      Write-Host "Total cache size: $totalSize MB" -ForegroundColor Green
      Write-Host ""
      Write-Host "Components:" -ForegroundColor White

      if (Test-Path "$cacheRoot\vcredist") {
        $size = [math]::Round((Get-ChildItem "$cacheRoot\vcredist" -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB, 1)
        Write-Host "  [OK] vcredist: $size MB" -ForegroundColor Green
      }
      if (Test-Path "$cacheRoot\python-embedded") {
        $size = [math]::Round((Get-ChildItem "$cacheRoot\python-embedded" -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB, 1)
        Write-Host "  [OK] python-embedded: $size MB" -ForegroundColor Green
      }
      if (Test-Path "$cacheRoot\nsis-includes") {
        $count = (Get-ChildItem "$cacheRoot\nsis-includes\*.nsh" -ErrorAction SilentlyContinue).Count
        Write-Host "  [OK] nsis-includes: $count files" -ForegroundColor Green
      }
    } else {
      Write-Host "No cache found at $cacheRoot" -ForegroundColor Yellow
      Write-Host "Cache will be populated after this build" -ForegroundColor Yellow
    }
  shell: powershell
```

---

## Testing Plan

### Test 1: Cold Cache (First Build)
```bash
# On Windows runner, clear cache
Remove-Item -Recurse -Force C:\BuildCache

# Trigger build
echo "Build LIGHT v$(date '+%y%m%d%H%M')" >> GITEA_TRIGGER.txt
git add -A && git commit -m "Test cold cache"
git push gitea main

# Expected: Downloads everything, populates cache
# Expected time: ~5 minutes
```

### Test 2: Warm Cache (Second Build)
```bash
# Trigger another build (cache should exist)
echo "Build LIGHT v$(date '+%y%m%d%H%M')" >> GITEA_TRIGGER.txt
git add -A && git commit -m "Test warm cache"
git push gitea main

# Expected: Uses cache, no downloads
# Expected time: ~30 seconds for dependencies
```

### Test 3: Cache Invalidation
```bash
# On Windows runner, delete Python cache
Remove-Item -Recurse -Force C:\BuildCache\python-embedded

# Trigger build
# Expected: Downloads Python only, uses cache for others
```

---

## Files to Modify

| File | Changes |
|------|---------|
| `.gitea/workflows/build.yml` | Replace download steps with cache-first logic |
| `scripts/setup_build_cache.ps1` | Already exists, no changes needed |

---

## Rollback Plan

If caching causes issues:
1. Comment out cache-first steps
2. Uncomment original download steps
3. Build workflow reverts to downloading fresh

The cache is completely optional - workflow works without it.

---

## Summary

```
IMPLEMENTATION:
1. Add cache helper functions
2. Replace VC++ download → cache-first
3. Replace Python download → cache-first
4. Replace NSIS download → cache-first
5. Add cache status summary

EXPECTED RESULT:
• First build: ~5 min (populates cache)
• Subsequent builds: ~30 sec (uses cache)
• Savings: ~4.5 min per build
```

---

*Ready to implement. Shall I proceed?*
