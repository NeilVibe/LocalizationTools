# Windows Runner Setup for Gitea Actions

**Version:** 2512080200
**Status:** 100% CLEAN - No fallbacks, proper installation only

---

## Overview

This guide documents how to set up a **production-ready Windows runner** for Gitea Actions that:
- Runs as a Windows Service (auto-start on boot)
- Has Git properly installed in system PATH
- Works without any fallbacks or workarounds

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

## Step 5: Create Windows Service with NSSM

From **Admin PowerShell**:
```powershell
$nssm = "C:\ProgramData\chocolatey\lib\NSSM\tools\nssm.exe"

# Remove old service if exists
sc.exe stop GiteaActRunner 2>$null
sc.exe delete GiteaActRunner 2>$null
Start-Sleep -Seconds 2

# Install service
& $nssm install GiteaActRunner "C:\NEIL_PROJECTS_WINDOWSBUILD\GiteaRunner\act_runner.exe" "daemon"
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

## Key Files & Locations

| Item | Path |
|------|------|
| Git | `C:\Program Files\Git` |
| NSSM | `C:\ProgramData\chocolatey\lib\NSSM\tools\nssm.exe` |
| Runner | `C:\NEIL_PROJECTS_WINDOWSBUILD\GiteaRunner\act_runner.exe` |
| Runner Config | `C:\NEIL_PROJECTS_WINDOWSBUILD\GiteaRunner\.runner` |
| Runner Work Dir | `C:\NEIL_PROJECTS_WINDOWSBUILD\GiteaRunner` |

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

*Last updated: 2025-12-08*
*Tested on: Windows 11, Git 2.52.0, act_runner 0.2.11, NSSM 2.24*
