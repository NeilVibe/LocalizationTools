# Windows Runner Setup for Gitea Actions

**Version:** 2512211600
**Status:** PRODUCTION READY - Patched Runner v15 (NUL Byte Fix)

---

## CRITICAL: NEVER RESTART

**Restarting does NOT solve issues.** ALWAYS follow this workflow:

1. **STOP** everything
2. **CLEAN** resources
3. **INVESTIGATE** root cause
4. **FIX** the actual issue
5. Only **THEN** start fresh

---

## Config Warning: fetch_interval

**IMPORTANT:** The `config.yaml` must have a reasonable `fetch_interval`.

```yaml
runner:
  fetch_interval: 30s  # ← MUST be 30s or higher, NOT 2s!
```

**2s = 43,200 requests/day = 650% CPU on Gitea**

---

## Current Production Setup

```
Binary:     C:\NEIL_PROJECTS_WINDOWSBUILD\GiteaRunner\act_runner_patched_v15.exe
Mode:       DAEMON (persistent, picks up jobs continuously)
Parameters: -c config.yaml daemon
Service:    GiteaActRunner (via NSSM)
Auto-start: Yes (SERVICE_AUTO_START)
```

**We use DAEMON mode, NOT ephemeral mode.** The v15 patch fixes Windows issues without needing ephemeral restarts.

---

## Quick Reference

| What | Command |
|------|---------|
| Status | `Get-Service GiteaActRunner` |
| Stop | `Stop-Service GiteaActRunner` |
| Start | `Start-Service GiteaActRunner` |
| Restart | `Restart-Service GiteaActRunner` |
| Rebuild | See `runner/README.md` |

---

## Overview

This guide documents how to set up a **production-ready Windows runner** for Gitea Actions:
- Runs as a Windows Service (auto-start on boot)
- **Daemon mode**: Persistent runner, picks up jobs continuously
- **Patched v15**: Fixes Windows PowerShell NUL byte issue in GITHUB_OUTPUT
- Has Git properly installed in system PATH

---

## Prerequisites

1. **Windows machine** with admin access
2. **WSL** installed (for building patched runner)
3. **Gitea server** running (default: http://localhost:3000)
4. **Go 1.21+** installed in WSL (for building)

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

**Verify:**
```powershell
git --version  # Should show: git version 2.52.0.windows.1 or similar
```

---

## Step 3: Install NSSM (Service Manager)

**NSSM** (Non-Sucking Service Manager) wraps console apps as Windows Services.

From **Admin PowerShell**:
```powershell
choco install nssm -y
```

NSSM installs to: `C:\ProgramData\chocolatey\lib\NSSM\tools\nssm.exe`

---

## Step 4: Build the Patched Runner

The stock act_runner fails on Windows due to PowerShell NUL byte bugs. We have a patch.

From **WSL**:
```bash
cd /path/to/LocalizationTools/runner/scripts
chmod +x build_patched_runner.sh
./build_patched_runner.sh

# Deploy to Windows
cp ~/act_runner_build/act_runner/act_runner_patched_v15.exe \
   /mnt/c/NEIL_PROJECTS_WINDOWSBUILD/GiteaRunner/
```

See `runner/README.md` for full details.

---

## Step 5: Register with Gitea

From **Windows PowerShell**:
```powershell
cd C:\NEIL_PROJECTS_WINDOWSBUILD\GiteaRunner

# Generate config (one-time)
.\act_runner_patched_v15.exe generate-config > config.yaml

# Register runner (get token from Gitea -> Settings -> Actions -> Runners)
.\act_runner_patched_v15.exe register `
    --instance http://YOUR_GITEA_IP:3000 `
    --token YOUR_RUNNER_TOKEN `
    --labels "windows-latest:host,windows:host,self-hosted:host,x64:host" `
    --name "windows-runner"
```

**Important:** Do NOT use `--ephemeral` flag. We use persistent daemon mode.

---

## Step 6: Create Windows Service (DAEMON Mode)

From **Admin PowerShell**:
```powershell
$nssm = "C:\ProgramData\chocolatey\lib\NSSM\tools\nssm.exe"
$runnerDir = "C:\NEIL_PROJECTS_WINDOWSBUILD\GiteaRunner"
$runnerExe = "act_runner_patched_v15.exe"

# Remove old service if exists
sc.exe stop GiteaActRunner 2>$null
sc.exe delete GiteaActRunner 2>$null
Start-Sleep -Seconds 2

# Install service - DAEMON MODE (persistent)
& $nssm install GiteaActRunner "$runnerDir\$runnerExe" "-c config.yaml daemon"
& $nssm set GiteaActRunner AppDirectory $runnerDir
& $nssm set GiteaActRunner Start SERVICE_AUTO_START
& $nssm set GiteaActRunner DisplayName "Gitea Actions Runner (Patched v15)"
& $nssm set GiteaActRunner Description "Patched act_runner with NUL byte fix - DAEMON mode"

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

## Verify It's Working

```powershell
# Check service
Get-Service GiteaActRunner

# Check process
Get-Process act_runner* | Format-Table Id,ProcessName,StartTime

# Check NSSM config (should show daemon, NOT ephemeral)
$nssm = "C:\ProgramData\chocolatey\lib\NSSM\tools\nssm.exe"
& $nssm get GiteaActRunner Application
& $nssm get GiteaActRunner AppParameters  # Should show: -c config.yaml daemon
```

Also check Gitea -> Settings -> Actions -> Runners - should show as "Idle" or "Running".

---

## The v15 Patch (NUL Byte Fix)

### The Problem

Windows PowerShell writes NUL bytes (`\x00`) to GITHUB_OUTPUT files:
```
name=value\x00\x00
```

This causes:
- `invalid format '\x00'` errors
- `exec: environment variable contains NUL` errors
- "Job failed" even when all build steps succeed

### The Solution

Our patch strips NUL bytes when parsing env files:

```go
// V15-PATCH: Strip NUL bytes from line (Windows PowerShell bug)
line = strings.ReplaceAll(line, "\x00", "")
```

Patch location: `runner/patches/v15_nul_byte_fix.patch`

---

## Troubleshooting

### Service won't start
```powershell
& "C:\ProgramData\chocolatey\lib\NSSM\tools\nssm.exe" status GiteaActRunner
# Check Windows Event Viewer -> Application logs for "nssm" source
```

### Git not in PATH
```powershell
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
```

### Runner not picking up jobs
1. Check Gitea -> Settings -> Actions -> Runners
2. Verify runner shows as "Idle" not "Offline"
3. Check labels match workflow `runs-on:`

---

## Service Management

```powershell
# Status
Get-Service GiteaActRunner

# Stop/Start/Restart
Stop-Service GiteaActRunner
Start-Service GiteaActRunner
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
| Runner | `C:\NEIL_PROJECTS_WINDOWSBUILD\GiteaRunner\act_runner_patched_v15.exe` |
| Runner Config | `C:\NEIL_PROJECTS_WINDOWSBUILD\GiteaRunner\config.yaml` |
| Registration | `C:\NEIL_PROJECTS_WINDOWSBUILD\GiteaRunner\.runner` |
| Rebuild Kit | `runner/` (in repo) |

---

## Why NSSM Instead of sc.exe?

Windows Services require a `ServiceMain` entry point. `act_runner.exe` is a console app without this.

**NSSM solves this by:**
1. Creating a proper Windows Service wrapper
2. Managing the console app as a child process
3. Handling start/stop/restart correctly
4. Setting working directory properly

---

## Historical Note: Ephemeral Mode

We previously tried ephemeral mode (runner exits after each job) to work around cleanup issues. The v15 patch makes this unnecessary - daemon mode now works reliably.

**Current mode: DAEMON (persistent)**

---

*Last updated: 2025-12-21*
*Mode: DAEMON (NOT ephemeral)*
*Tested on: Windows 11, Git 2.52.0, act_runner 0.2.11 (patched v15), NSSM 2.24*
