# Gitea CI/CD Complete Setup Guide

**Version:** 2512101235
**Status:** PRODUCTION READY - Patched Runner v15 (DAEMON Mode)

---

## Overview

This guide documents the complete setup of **Gitea** as a self-hosted Git server with CI/CD pipeline for building LocaNext Windows installers. This setup enables:

- **Dual Remote Strategy**: Push to both GitHub (public) and Gitea (local CI/CD)
- **Windows Builds**: Native Windows installer creation via Inno Setup
- **Automatic Releases**: ZIP artifacts created on successful builds
- **No External Dependencies**: Fully self-hosted on company network

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Developer Machine (WSL)                   │
├─────────────────────────────────────────────────────────────────┤
│  git push origin main    →  GitHub (public backup)              │
│  git push gitea main     →  Gitea (local CI/CD)                 │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Gitea Server (WSL Linux)                     │
├─────────────────────────────────────────────────────────────────┤
│  Port 3000: Web UI + API                                        │
│  Port 2222: SSH (git operations)                                │
│  Actions: ENABLED                                               │
│  Database: SQLite (Gitea's internal DB, NOT LocaNext data)      │
└─────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
┌──────────────────────────┐    ┌──────────────────────────────────┐
│   Linux Runner (WSL)      │    │   Windows Runner (Native)         │
├──────────────────────────┤    ├──────────────────────────────────┤
│  Name: locanext-runner    │    │  Name: windows-runner             │
│  Jobs: safety-checks,     │    │  Jobs: build-windows              │
│        create-release     │    │  Mode: DAEMON (persistent)        │
│  Binary: act_runner       │    │  Binary: act_runner_patched_v15   │
│  (stock, no patch needed) │    │  (PATCHED for NUL byte fix)       │
└──────────────────────────┘    └──────────────────────────────────┘
```

---

## Part 1: Gitea Server Installation

### 1.1 Download and Setup

```bash
# Create Gitea directory
mkdir -p ~/gitea && cd ~/gitea

# Download Gitea (check https://dl.gitea.com/gitea/ for latest)
wget -O gitea https://dl.gitea.com/gitea/1.22.3/gitea-1.22.3-linux-amd64
chmod +x gitea

# Create data directories
mkdir -p data custom

# Generate initial config
./gitea generate secret INTERNAL_TOKEN
./gitea generate secret SECRET_KEY
./gitea generate secret LFS_JWT_SECRET
```

### 1.2 Configuration (app.ini)

Create `~/gitea/custom/conf/app.ini`:

```ini
[server]
APP_DATA_PATH = /home/neil1988/gitea/data
HTTP_PORT = 3000
ROOT_URL = http://172.28.150.120:3000/
SSH_DOMAIN = 172.28.150.120
SSH_PORT = 2222
START_SSH_SERVER = true
DOMAIN = 172.28.150.120
DISABLE_SSH = false

[database]
; This is Gitea's INTERNAL database for storing repos/users/issues
; NOT related to LocaNext data (which uses PostgreSQL)
DB_TYPE = sqlite3
PATH = /home/neil1988/gitea/data/gitea.db

[repository]
ROOT = /home/neil1988/gitea/data/gitea-repositories

[actions]
ENABLED = true
DEFAULT_ACTIONS_URL = https://github.com

[log]
ROOT_PATH = /home/neil1988/gitea/data/log
MODE = console, file
LEVEL = Info
```

### 1.3 Start/Stop Scripts

**~/gitea/start.sh:**
```bash
#!/bin/bash
cd /home/neil1988/gitea
nohup ./gitea web > gitea.log 2>&1 &
echo "Gitea started on http://localhost:3000"
```

**~/gitea/stop.sh:**
```bash
#!/bin/bash
pkill -f "gitea web"
echo "Gitea stopped"
```

### 1.4 First Run

```bash
cd ~/gitea && ./start.sh
# Open http://localhost:3000
# Complete setup wizard:
#   - Admin username: neilvibe
#   - Admin email: your@email.com
#   - Admin password: (your choice)
```

---

## Part 2: Repository Setup

### 2.1 Create Repository in Gitea

1. Login to Gitea (http://localhost:3000)
2. Click "+" → "New Repository"
3. Name: `LocaNext`
4. Keep other defaults → Create

### 2.2 Configure Dual Remotes

```bash
cd ~/LocalizationTools

# Add Gitea as second remote
git remote add gitea neil1988@172.28.150.120:2222/neilvibe/LocaNext.git

# Verify remotes
git remote -v
# origin  git@github.com:NeilVibe/LocalizationTools.git (fetch)
# origin  git@github.com:NeilVibe/LocalizationTools.git (push)
# gitea   neil1988@172.28.150.120:2222/neilvibe/LocaNext.git (fetch)
# gitea   neil1988@172.28.150.120:2222/neilvibe/LocaNext.git (push)

# Push to both
git push origin main   # GitHub
git push gitea main    # Gitea
```

### 2.3 SSH Key Setup

```bash
# Generate key if needed
ssh-keygen -t ed25519 -C "your@email.com"

# Copy public key
cat ~/.ssh/id_ed25519.pub

# Add to Gitea: Settings → SSH/GPG Keys → Add Key
```

---

## Part 3: Linux Runner Setup

The Linux runner handles lightweight jobs (safety checks, release creation).

### 3.1 Download act_runner

```bash
cd ~/gitea

# Download act_runner
wget -O act_runner https://gitea.com/gitea/act_runner/releases/download/v0.2.11/act_runner-0.2.11-linux-amd64
chmod +x act_runner
```

### 3.2 Register Runner

```bash
# Get registration token from Gitea:
# Settings → Actions → Runners → Create new Runner → Copy token

# Register
./act_runner register \
  --instance http://localhost:3000 \
  --token YOUR_TOKEN \
  --name locanext-runner \
  --labels ubuntu-latest:host,linux:host
```

### 3.3 Start Runner

**~/gitea/start_runner.sh:**
```bash
#!/bin/bash
cd /home/neil1988/gitea
nohup ./act_runner daemon > runner.log 2>&1 &
echo "Runner started"
```

**~/gitea/stop_runner.sh:**
```bash
#!/bin/bash
pkill -f "act_runner daemon"
echo "Runner stopped"
```

---

## Part 4: Windows Runner Setup (CRITICAL!)

The Windows runner builds the actual installer. This requires a **patched act_runner** due to a Windows PowerShell bug.

### 4.1 The Problem

Windows PowerShell writes NUL bytes (`\x00`) to GITHUB_OUTPUT files when using `Add-Content` or `>>`. The stock act_runner fails to parse these, causing:
- `invalid format '\x00'` errors
- `exec: environment variable contains NUL` errors
- **"Job failed" even when all build steps succeed**

### 4.2 The Solution: Patched Runner v15

We patched `nektos/act` (the library act_runner uses) to strip NUL bytes:

**File:** `act/pkg/container/parse_env_file.go`

```go
// In ParseEnvFile function, after: line := s.Text()
// Add these lines:

// V15-PATCH: Strip NUL bytes from line (Windows PowerShell bug)
line = strings.ReplaceAll(line, "\x00", "")
trimmed := strings.TrimSpace(line)
if trimmed == "" {
    continue
}
```

### 4.3 Building the Patched Runner

```bash
# Clone repositories
mkdir -p ~/act_runner_patch && cd ~/act_runner_patch
git clone https://github.com/nektos/act.git
git clone https://gitea.com/gitea/act_runner.git

# Apply the patch to act/pkg/container/parse_env_file.go
# (Edit the file as shown above)

# Configure act_runner to use local patched act
cd act_runner
echo 'replace github.com/nektos/act => ../act' >> go.mod

# Build for Windows
GOOS=windows GOARCH=amd64 go build -o act_runner_patched_v15.exe

# Copy to Windows
cp act_runner_patched_v15.exe /mnt/c/NEIL_PROJECTS_WINDOWSBUILD/GiteaRunner/
```

### 4.4 Windows Runner Directory Structure

```
C:\NEIL_PROJECTS_WINDOWSBUILD\GiteaRunner\
├── act_runner_patched_v15.exe    # Patched runner binary (DAEMON mode)
├── config.yaml                   # Runner configuration
├── .runner                       # Registration file (auto-created)
└── _work\                        # Job workspace (auto-created)
```

### 4.5 Install as Windows Service (DAEMON Mode)

**Current approach - DAEMON mode (recommended):**

```powershell
$runnerDir = "C:\NEIL_PROJECTS_WINDOWSBUILD\GiteaRunner"
$runnerExe = "act_runner_patched_v15.exe"
$nssm = "C:\ProgramData\chocolatey\lib\NSSM\tools\nssm.exe"

# Remove old service
sc.exe stop GiteaActRunner 2>$null
sc.exe delete GiteaActRunner 2>$null
Start-Sleep -Seconds 2

# Install service - DAEMON MODE (runs binary directly, no wrapper script)
& $nssm install GiteaActRunner "$runnerDir\$runnerExe" "-c config.yaml daemon"
& $nssm set GiteaActRunner AppDirectory $runnerDir
& $nssm set GiteaActRunner Start SERVICE_AUTO_START
& $nssm set GiteaActRunner DisplayName "Gitea Actions Runner (Patched v15)"

# Start
& $nssm start GiteaActRunner
```

Run as Administrator. See also: `runner/scripts/install_windows.ps1` in repo.

### 4.6 Prerequisites (Windows)

```powershell
# Install Chocolatey (if not installed)
Set-ExecutionPolicy Bypass -Scope Process -Force
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# Install Git and NSSM
choco install git -y --params "/GitAndUnixToolsOnPath"
choco install nssm -y
choco install innosetup -y
choco install nodejs-lts -y
```

---

## Part 5: Workflow Configuration

### 5.1 Trigger Files

The build system uses trigger files to control when builds run:

| File | Remote | Purpose |
|------|--------|---------|
| `BUILD_TRIGGER.txt` | GitHub | Production builds |
| `GITEA_TRIGGER.txt` | Gitea | Local test builds |

### 5.2 Workflow File

**.gitea/workflows/build.yml:**

```yaml
name: Build LocaNext

on:
  push:
    branches: [main]
    paths:
      - 'GITEA_TRIGGER.txt'
      - 'version.py'

jobs:
  safety-checks:
    runs-on: ubuntu-latest
    outputs:
      version: ${{ steps.version.outputs.version }}
      should_build: ${{ steps.check.outputs.should_build }}
    steps:
      - uses: actions/checkout@v4

      - name: Extract version
        id: version
        run: |
          VERSION=$(grep "^VERSION" version.py | cut -d'"' -f2)
          echo "version=$VERSION" >> $GITHUB_OUTPUT

      - name: Check trigger
        id: check
        run: |
          if grep -q "Build LIGHT" GITEA_TRIGGER.txt; then
            echo "should_build=true" >> $GITHUB_OUTPUT
          fi

  build-windows:
    needs: safety-checks
    if: needs.safety-checks.outputs.should_build == 'true'
    runs-on: windows
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        run: |
          node --version
          npm --version

      - name: Install dependencies
        run: |
          cd locaNext
          npm ci

      - name: Build Electron (dir)
        run: |
          cd locaNext
          npm run build:dir

      - name: Build Installer (Inno Setup)
        run: |
          & "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\locanext_light.iss

      - name: Create ZIP
        run: |
          Compress-Archive -Path installer_output\* -DestinationPath "LocaNext_v${{ needs.safety-checks.outputs.version }}_Light.zip"

  create-release:
    needs: [safety-checks, build-windows]
    runs-on: ubuntu-latest
    steps:
      - name: Create Release
        run: |
          echo "Release v${{ needs.safety-checks.outputs.version }} created!"
```

---

## Part 6: Daily Operations

### 6.1 Trigger a Build

```bash
# Update version
NEW_VERSION=$(date '+%y%m%d%H%M')
# Edit version.py with $NEW_VERSION
python3 scripts/check_version_unified.py

# Add trigger
echo "Build LIGHT v$NEW_VERSION" >> GITEA_TRIGGER.txt

# Commit and push
git add -A
git commit -m "Build v$NEW_VERSION"
git push gitea main   # Triggers Gitea build
git push origin main  # Syncs to GitHub
```

### 6.2 Monitor Build

```bash
# List recent logs
ls -lt ~/gitea/data/actions_log/neilvibe/LocaNext/*/*.log | head -5

# Watch live
tail -f $(ls -t ~/gitea/data/actions_log/neilvibe/LocaNext/*/*.log | head -1)

# Check result
strings $(ls -t ~/gitea/data/actions_log/neilvibe/LocaNext/*/*.log | head -1) | grep -E "Job succeeded|Job failed"
```

### 6.3 Service Management

**Linux (Gitea + Runner):**
```bash
cd ~/gitea
./start.sh        # Start Gitea
./start_runner.sh # Start Linux runner
./stop.sh         # Stop Gitea
./stop_runner.sh  # Stop Linux runner
```

**Windows (Runner Service):**
```powershell
Get-Service GiteaActRunner           # Check status
Start-Service GiteaActRunner         # Start
Stop-Service GiteaActRunner          # Stop
Restart-Service GiteaActRunner       # Restart
```

---

## Part 7: Troubleshooting

### 7.1 Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| "Job failed" after success | NUL bytes in GITHUB_OUTPUT | Use patched runner v15 |
| "git not recognized" | Git not in Windows PATH | `choco install git -y --params "/GitAndUnixToolsOnPath"` |
| Runner not picking up jobs | Wrong labels | Check runner labels match workflow `runs-on` |
| SSH connection refused | Wrong port/username | Use `neil1988@host:2222` not `git@host` |
| Build timeout | Service not running | Install as Windows Service |
| Windows runner won't connect | NSSM service stopped | Start service manually (see 7.4) |
| Token expiration | Registration token expired | Re-register runner (see 7.5) |
| curl.exe JSON parse error | UTF-8 BOM character (`ï`) | Use `Invoke-RestMethod` instead |

### 7.4 Windows Runner Service Issues (CRITICAL!)

**Problem:** The Windows runner service (managed by NSSM) can stop unexpectedly, causing builds to hang at "build-windows" forever.

**Symptoms:**
- `safety-checks` job completes, but `build-windows` shows "waiting"
- Linux runner shows jobs, Windows runner shows nothing
- Service status shows "STOPPED"

**Diagnosis (from WSL):**
```bash
# Check if Windows runner service is running
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command "Get-Service GiteaActRunner"

# Expected output:
# Status   Name               DisplayName
# ------   ----               -----------
# Running  GiteaActRunner     GiteaActRunner
```

**Fix (from WSL with PowerShell):**
```bash
# Start the service
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command "Start-Service GiteaActRunner"

# Verify it's running
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command "Get-Service GiteaActRunner"
```

**Why this happens:**
- NSSM restarts the service, but registration can fail silently
- Network changes can disconnect the runner from Gitea
- Token expiration (re-register if needed)

### 7.5 Runner Mode

**Current Setup: DAEMON mode** - Persistent runner, picks up jobs continuously.

For full setup details, see:
- `docs/deployment/WINDOWS_RUNNER_SETUP.md` - Complete Windows runner guide
- `runner/README.md` - Rebuild kit with patch and scripts

### 7.6 Release API Issues (curl.exe vs Invoke-RestMethod)

**Problem:** When using `curl.exe` in PowerShell workflows to create releases, you may see:
```
Error: invalid character 'ï' looking for beginning of value
```

**Cause:** Windows `curl.exe` can add UTF-8 BOM (Byte Order Mark) characters to output, which corrupts JSON parsing.

**Solution:** Use native PowerShell `Invoke-RestMethod` instead of `curl.exe`:

```yaml
# BAD - can produce UTF-8 BOM errors
- name: Create Release
  run: |
    curl.exe -X POST "$env:GITEA_URL/api/v1/repos/$env:GITEA_REPO/releases" ...

# GOOD - native PowerShell, no encoding issues
- name: Create Release
  run: |
    $releaseData = @{
      tag_name = "v${{ needs.safety-checks.outputs.version }}"
      name = "LocaNext v${{ needs.safety-checks.outputs.version }}"
      body = "Automated release"
    } | ConvertTo-Json

    $response = Invoke-RestMethod -Uri "$env:GITEA_URL/api/v1/repos/$env:GITEA_REPO/releases" `
      -Method POST `
      -Headers @{ "Authorization" = "token $env:GITEA_TOKEN"; "Content-Type" = "application/json" } `
      -Body $releaseData
```

### 7.2 Verify Patch is Working

Look for these markers in build logs:
```
[V10-PATCHED] Cleaning up container...   ← Patch is active
Job succeeded                             ← No more false failures
```

### 7.3 Log Locations

| Component | Log Location |
|-----------|--------------|
| Gitea Server | `~/gitea/gitea.log` |
| Linux Runner | `~/gitea/runner.log` |
| Action Jobs | `~/gitea/data/actions_log/{owner}/{repo}/{prefix}/{id}.log` |
| Windows Service | Event Viewer → Application → nssm |

---

## Part 8: File Locations Summary

### Linux (WSL)

| Item | Path |
|------|------|
| Gitea binary | `~/gitea/gitea` |
| Gitea config | `~/gitea/custom/conf/app.ini` |
| Gitea data | `~/gitea/data/` |
| Linux runner | `~/gitea/act_runner` |
| Action logs | `~/gitea/data/actions_log/` |
| Patch source | `~/act_runner_patch/act/pkg/container/parse_env_file.go` |

### Windows

| Item | Path |
|------|------|
| Runner binary | `C:\NEIL_PROJECTS_WINDOWSBUILD\GiteaRunner\act_runner_patched_v15.exe` |
| Config | `C:\NEIL_PROJECTS_WINDOWSBUILD\GiteaRunner\config.yaml` |
| Runner token | `C:\NEIL_PROJECTS_WINDOWSBUILD\GiteaRunner\registration_token.txt` |
| Build workspace | `C:\NEIL_PROJECTS_WINDOWSBUILD\GiteaRunner\_work\` |
| Build cache | `C:\NEIL_PROJECTS_WINDOWSBUILD\GiteaRunner\_cache\` |
| Git | `C:\Program Files\Git\` |
| Inno Setup | `C:\Program Files (x86)\Inno Setup 6\` |

---

## Part 9: Maintenance

### 9.1 Periodic Cleanup (Monthly)

The `_work` folder accumulates build artifacts (~2GB per build). Clean it periodically:

**From WSL:**
```bash
# Check size
du -sh /mnt/c/NEIL_PROJECTS_WINDOWSBUILD/GiteaRunner/_work

# Clean (safe when no build is running)
rm -rf /mnt/c/NEIL_PROJECTS_WINDOWSBUILD/GiteaRunner/_work/*
```

**From PowerShell (Admin):**
```powershell
# Check size
(Get-ChildItem -Recurse C:\NEIL_PROJECTS_WINDOWSBUILD\GiteaRunner\_work | Measure-Object -Property Length -Sum).Sum / 1GB

# Clean
Remove-Item -Recurse -Force C:\NEIL_PROJECTS_WINDOWSBUILD\GiteaRunner\_work\*
```

### 9.2 What to Keep vs Delete

| Item | Keep? | Why |
|------|-------|-----|
| `act_runner_patched_v15.exe` | ✅ YES | Active runner binary |
| `config.yaml` | ✅ YES | Runner configuration |
| `.runner` | ✅ YES | Registration info |
| `registration_token.txt` | ✅ YES | Auth token |
| `_cache/` | ✅ YES | Speeds up builds (npm cache) |
| `_work/` contents | 🗑️ DELETE | Old build artifacts |
| `act_runner_patched_v*.exe` | 🗑️ DELETE | Old runner versions |
| `*.log`, `*.txt` (except token) | 🗑️ DELETE | Old logs |

### 9.3 Automated Cleanup (Recommended)

Script already installed at `C:\NEIL_PROJECTS_WINDOWSBUILD\GiteaRunner\cleanup_workspace.ps1`

**Setup Task Scheduler (one-time, from Admin PowerShell):**
```powershell
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-ExecutionPolicy Bypass -File C:\NEIL_PROJECTS_WINDOWSBUILD\GiteaRunner\cleanup_workspace.ps1"
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 3am
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable
Register-ScheduledTask -TaskName "GiteaRunnerCleanup" -Action $action -Trigger $trigger -Settings $settings -RunLevel Highest
```

**Manual run:**
```powershell
& "C:\NEIL_PROJECTS_WINDOWSBUILD\GiteaRunner\cleanup_workspace.ps1"
```

**Check logs:**
```powershell
Get-Content C:\NEIL_PROJECTS_WINDOWSBUILD\GiteaRunner\cleanup.log -Tail 10
```

---

## Resource Usage

| Component | CPU (idle) | RAM |
|-----------|------------|-----|
| Gitea Server | ~0% | ~50 MB |
| Linux Runner | 0.1% | ~25 MB |
| Windows Service (NSSM) | 0% | ~8 MB |

Builds temporarily spike CPU/RAM, then return to idle.

---

## Quick Reference

### Start Everything
```bash
# Linux
cd ~/gitea && ./start.sh && ./start_runner.sh

# Windows (automatic via service)
# Service starts on boot
```

### Trigger Build
```bash
echo "Build LIGHT v$(date '+%y%m%d%H%M')" >> GITEA_TRIGGER.txt
git add -A && git commit -m "Trigger build" && git push gitea main
```

### Check Build Status
```bash
strings $(ls -t ~/gitea/data/actions_log/neilvibe/LocaNext/*/*.log | head -1) | grep "Job"
```

---

*Last updated: 2025-12-21*
*Gitea: v1.22.3 | act_runner: v0.2.11 (patched v15) | Mode: DAEMON | Status: PRODUCTION READY*
