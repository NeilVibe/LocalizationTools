# Windows Runner Setup for Gitea Actions

**Version:** 2512090410
**Status:** ✅ PRODUCTION READY - Patched Runner v15 (NUL Byte Fix)

---

## Overview

This guide documents how to set up a **production-ready Windows runner** for Gitea Actions using a **patched act_runner**:
- Runs as a Windows Service (auto-start on boot)
- **Ephemeral mode**: Fresh runner for each job (like GitHub Actions)
- **Patched v15**: Fixes Windows PowerShell NUL byte issue in GITHUB_OUTPUT
- No cleanup issues - runner exits after each job, handles released
- Has Git properly installed in system PATH

---

## Prerequisites

1. **Windows machine** with admin access
2. **WSL** installed (for running commands from Linux)
3. **Gitea server** running (default: http://localhost:3000)

---

## Step 1: Install Chocolatey (Package Manager)

From **Admin PowerShell**:
```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
```

---

## Step 2: Install Git

From **Admin PowerShell**:
```powershell
choco install git -y --params "/GitAndUnixToolsOnPath /WindowsTerminal"
```

This installs Git to `C:\Program Files\Git` with:
- Git added to system PATH
- Unix tools available
- Windows Terminal integration

**Verify:**
```powershell
git --version  # Should show: git version 2.52.0.windows.1 or similar
```

---

## Step 3: Install NSSM (Service Manager)

Regular executables (like `act_runner.exe`) cannot be registered as Windows Services directly - they require a `ServiceMain` entry point.

**NSSM** (Non-Sucking Service Manager) wraps any executable as a proper Windows Service.

From **Admin PowerShell**:
```powershell
choco install nssm -y
```

NSSM installs to: `C:\ProgramData\chocolatey\lib\NSSM\tools\nssm.exe`

---

## Step 4: Download and Register act_runner

### 4.1 Download act_runner

```powershell
# Create directory
mkdir C:\NEIL_PROJECTS_WINDOWSBUILD\GiteaRunner

# Download act_runner (check https://gitea.com/gitea/act_runner/releases for latest)
Invoke-WebRequest -Uri "https://gitea.com/gitea/act_runner/releases/download/v0.2.11/act_runner-0.2.11-windows-amd64.exe" -OutFile "C:\NEIL_PROJECTS_WINDOWSBUILD\GiteaRunner\act_runner.exe"
```

### 4.2 Register with Gitea

```powershell
cd C:\NEIL_PROJECTS_WINDOWSBUILD\GiteaRunner

# Generate config
.\act_runner.exe generate-config > config.yaml

# Register runner (get token from Gitea → Settings → Actions → Runners)
.\act_runner.exe register --instance http://YOUR_GITEA_IP:3000 --token YOUR_RUNNER_TOKEN --labels windows-latest,windows --name windows-runner
```

---

## Step 5: Create Ephemeral Wrapper Script

Create `C:\NEIL_PROJECTS_WINDOWSBUILD\GiteaRunner\run_ephemeral.bat`:

```batch
@echo off
setlocal EnableDelayedExpansion

set "RUNNER_DIR=C:\NEIL_PROJECTS_WINDOWSBUILD\GiteaRunner"
set "GITEA_URL=http://YOUR_GITEA_IP:3000"
set "RUNNER_NAME=windows-ephemeral"
set "RUNNER_LABELS=windows:host,windows-latest:host,self-hosted:host,x64:host"

cd /d "%RUNNER_DIR%"

:loop
echo [%TIME%] Starting ephemeral runner cycle...

REM Remove old registration
if exist ".runner" del /f /q ".runner"

REM Register as ephemeral (single-use)
act_runner.exe register --no-interactive --ephemeral ^
    --instance "%GITEA_URL%" ^
    --token "%GITEA_RUNNER_TOKEN%" ^
    --name "%RUNNER_NAME%" ^
    --labels "%RUNNER_LABELS%"

REM Run ONE job then exit
act_runner.exe -c config.yaml daemon

echo [%TIME%] Job complete, re-registering...
timeout /t 5 /nobreak >nul
goto loop
```

Create `registration_token.txt` with your Gitea runner token.

---

## Step 6: Create Windows Service with NSSM

From **Admin PowerShell**:
```powershell
$nssm = "C:\ProgramData\chocolatey\lib\NSSM\tools\nssm.exe"

# Remove old service if exists
sc.exe stop GiteaActRunner 2>$null
sc.exe delete GiteaActRunner 2>$null
Start-Sleep -Seconds 2

# Install service with EPHEMERAL wrapper
& $nssm install GiteaActRunner "C:\NEIL_PROJECTS_WINDOWSBUILD\GiteaRunner\run_ephemeral.bat"
& $nssm set GiteaActRunner AppDirectory "C:\NEIL_PROJECTS_WINDOWSBUILD\GiteaRunner"
& $nssm set GiteaActRunner Start SERVICE_AUTO_START

# Start service
& $nssm start GiteaActRunner

# Verify
Get-Service GiteaActRunner | Format-List Name,Status,StartType
```

**Expected output:**
```
Name      : GiteaActRunner
Status    : Running
StartType : Automatic
```

---

## Why Ephemeral Mode?

**Problem (P13.11):** In persistent daemon mode, act_runner's cleanup fails on Windows due to Go process holding file handles. Jobs show "failed" even when build succeeds.

**Solution:** Ephemeral mode - runner exits after each job, releasing all handles. Fresh registration for next job.

| Mode | How it works | Cleanup |
|------|--------------|---------|
| Persistent (old) | Runner stays running | ❌ Fails on Windows |
| Ephemeral (new) | Runner exits after job | ✅ Handles released |

---

## Running Commands from WSL (Admin Elevation)

To run Admin PowerShell commands from WSL:

```bash
# Create script
cat > /mnt/c/temp/my_script.ps1 << 'EOF'
# Your PowerShell commands here
Write-Host "Running as Admin!"
EOF

# Execute with admin elevation
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -NoProfile \
  -Command "Start-Process powershell -Verb RunAs -Wait -ArgumentList '-NoProfile -ExecutionPolicy Bypass -File C:\temp\my_script.ps1'"
```

---

## Full Installation Script (One-Shot)

Save as `C:\temp\install_runner.ps1` and run as Admin:

```powershell
Write-Host "=== GITEA WINDOWS RUNNER FULL INSTALLATION ===" -ForegroundColor Cyan

# 1. Install Git
Write-Host "`n[1/4] Installing Git..." -ForegroundColor Yellow
choco install git -y --params "/GitAndUnixToolsOnPath /WindowsTerminal"

# 2. Install NSSM
Write-Host "`n[2/4] Installing NSSM..." -ForegroundColor Yellow
choco install nssm -y

# 3. Setup runner directory (assumes act_runner.exe already downloaded and registered)
Write-Host "`n[3/4] Configuring service..." -ForegroundColor Yellow
$nssm = "C:\ProgramData\chocolatey\lib\NSSM\tools\nssm.exe"
$runnerPath = "C:\NEIL_PROJECTS_WINDOWSBUILD\GiteaRunner"

# Remove old service
sc.exe stop GiteaActRunner 2>$null
sc.exe delete GiteaActRunner 2>$null
Start-Sleep -Seconds 2

# Create service
& $nssm install GiteaActRunner "$runnerPath\act_runner.exe" "daemon"
& $nssm set GiteaActRunner AppDirectory $runnerPath
& $nssm set GiteaActRunner Start SERVICE_AUTO_START
& $nssm start GiteaActRunner

# 4. Verify
Write-Host "`n[4/4] Verification..." -ForegroundColor Yellow
Write-Host "`nGit:" -ForegroundColor Green
git --version

Write-Host "`nService:" -ForegroundColor Green
Get-Service GiteaActRunner | Format-List Name,Status,StartType

Write-Host "`nProcess:" -ForegroundColor Green
Get-Process act_runner | Format-Table Id,ProcessName,StartTime

Write-Host "`n=== INSTALLATION COMPLETE ===" -ForegroundColor Cyan
```

---

## Troubleshooting

### Service won't start
```powershell
# Check NSSM logs
& "C:\ProgramData\chocolatey\lib\NSSM\tools\nssm.exe" status GiteaActRunner

# Check Windows Event Viewer → Application logs for "nssm" source
```

### Git not in PATH
```powershell
# Refresh environment (new PowerShell session needed after Git install)
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

# Or verify directly
& "C:\Program Files\Git\cmd\git.exe" --version
```

### Chocolatey lock file error
```powershell
# Remove lock files and retry
Remove-Item "C:\ProgramData\chocolatey\lib\*" -Include "*.lock" -Recurse -Force
Remove-Item "C:\ProgramData\chocolatey\lib-bad" -Recurse -Force -ErrorAction SilentlyContinue
choco install nssm -y
```

---

## Service Management Commands

```powershell
# Status
Get-Service GiteaActRunner

# Stop
Stop-Service GiteaActRunner

# Start
Start-Service GiteaActRunner

# Restart
Restart-Service GiteaActRunner

# Disable auto-start
Set-Service GiteaActRunner -StartupType Manual

# Remove service completely
$nssm = "C:\ProgramData\chocolatey\lib\NSSM\tools\nssm.exe"
& $nssm stop GiteaActRunner
& $nssm remove GiteaActRunner confirm
```

---

## Patched Runner (v15) - NUL Byte Fix

The stock act_runner v0.2.11 fails on Windows due to PowerShell writing NUL bytes (`\x00`) to GITHUB_OUTPUT files. This causes:
- `invalid format '\x00'` errors
- `exec: environment variable contains NUL` errors
- "Job failed" even when all build steps succeed

### The Problem

Windows PowerShell's `Add-Content` and `>>` operators write NUL bytes to files, especially with certain encodings. When act_runner parses GITHUB_OUTPUT:

```
name=value\x00\x00
```

The NUL bytes cause Go's `os/exec` to reject environment variables.

### The Solution (v15 Patch)

Patch file: `~/act_runner_patch/act/pkg/container/parse_env_file.go`

```go
// V15-PATCH: Strip NUL bytes from line (Windows PowerShell bug)
line = strings.ReplaceAll(line, "\x00", "")
trimmed := strings.TrimSpace(line)
if trimmed == "" {
    continue
}
```

### Building the Patched Runner

```bash
# Clone repositories
mkdir -p ~/act_runner_patch && cd ~/act_runner_patch
git clone https://github.com/nektos/act.git
git clone https://gitea.com/gitea/act_runner.git

# Apply patch to act/pkg/container/parse_env_file.go
# (Insert lines after `line := s.Text()` in ParseEnvFile function)

# Configure go.mod to use local act
cd act_runner
echo 'replace github.com/nektos/act => ../act' >> go.mod

# Build
GOOS=windows GOARCH=amd64 go build -o act_runner_patched_v15.exe

# Deploy to Windows
cp act_runner_patched_v15.exe /mnt/c/NEIL_PROJECTS_WINDOWSBUILD/GiteaRunner/
```

### Using the Patched Runner

Update `run_ephemeral.bat` to use the patched version:

```batch
REM Replace:
act_runner.exe register ...
act_runner.exe daemon ...

REM With:
act_runner_patched_v15.exe register ...
act_runner_patched_v15.exe daemon ...
```

### Verification

Look for these markers in build logs:
- `[V10-PATCHED] Cleaning up container...` - Confirms patch is active
- `Job succeeded` - No more false positive failures

---

## Key Files & Locations

| Item | Path |
|------|------|
| Git | `C:\Program Files\Git` |
| NSSM | `C:\ProgramData\chocolatey\lib\NSSM\tools\nssm.exe` |
| Runner | `C:\NEIL_PROJECTS_WINDOWSBUILD\GiteaRunner\act_runner_patched_v15.exe` |
| Runner Config | `C:\NEIL_PROJECTS_WINDOWSBUILD\GiteaRunner\.runner` |
| Runner Work Dir | `C:\NEIL_PROJECTS_WINDOWSBUILD\GiteaRunner` |
| Patch Source | `~/act_runner_patch/act/pkg/container/parse_env_file.go` |

---

## Why NSSM Instead of sc.exe?

Windows Services created with `sc.exe create` require:
- A `ServiceMain` entry point in the executable
- Proper Windows Service API integration

`act_runner.exe` is a **regular console application** - it doesn't have these.

**NSSM solves this by:**
1. Creating a proper Windows Service wrapper
2. Managing the console app as a child process
3. Handling start/stop/restart correctly
4. Setting working directory properly

---

*Last updated: 2025-12-09*
*Tested on: Windows 11, Git 2.52.0, act_runner 0.2.11 (patched v15), NSSM 2.24*
