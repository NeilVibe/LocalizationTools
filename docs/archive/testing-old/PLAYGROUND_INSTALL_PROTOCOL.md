# Autonomous Playground Install Protocol

**Purpose:** FRESH INSTALL of LocaNext to Playground for testing
**Last Updated:** 2025-12-28

---

## ⚠️ INSTALL vs UPDATE - READ THIS FIRST

| | INSTALL (this doc) | UPDATE |
|--|---------|--------|
| **What** | Fresh .exe installation | Auto-updater downloads new version |
| **When** | First time, clean slate, testing first-run | App already installed |
| **Time** | 2-5 min | 30 sec - 2 min |
| **Command** | `./scripts/playground_install.sh` | Just open the app |

**If app is ALREADY INSTALLED, use UPDATE instead:**
1. Open LocaNext
2. App auto-checks for updates on startup
3. Download → Install & Restart

**See [DOC-001: Install vs Update Confusion](../wip/DOC-001_INSTALL_VS_UPDATE_CONFUSION.md) for full details.**

---

> **NOTE:** For updating an existing install, use **SMART_UPDATE_PROTOCOL.md** instead.
> This doc is for FRESH installs only.

---

## Quick Start

```bash
# From WSL - Full clean install
./scripts/playground_install.sh

# With auto-launch and CDP verification
./scripts/playground_install.sh --launch

# Skip cleaning (reinstall in place)
./scripts/playground_install.sh --skip-clean --launch
```

---

## What It Does

1. **Fetches** latest release from Gitea API
2. **Cleans** Playground directory and user data
3. **Downloads** installer (~163 MB)
4. **Installs** silently to Playground (~605 MB)
5. **Launches** with CDP debugging (optional)
6. **Verifies** via CDP that app loaded

---

## Scripts

| Script | Platform | Usage |
|--------|----------|-------|
| `scripts/playground_install.sh` | WSL | `./scripts/playground_install.sh [options]` |
| `scripts/playground_install.ps1` | Windows | `.\scripts\playground_install.ps1 [params]` |

### WSL Options

```bash
./scripts/playground_install.sh [options]

Options:
  --launch        Launch app after install with CDP enabled
  --skip-clean    Don't clean Playground first
  --cdp-port PORT CDP debugging port (default: 9222)
  --auto-login    Auto-login as admin/admin123 after First Time Setup
```

### PowerShell Parameters

```powershell
.\scripts\playground_install.ps1 [params]

Parameters:
  -GiteaHost       Gitea server IP (default: 172.28.150.120)
  -GiteaPort       Gitea server port (default: 3000)
  -PlaygroundPath  Install location (default: C:\...\Playground)
  -LaunchAfterInstall  Launch app after install
  -EnableCDP       Enable CDP debugging
  -CDPPort         CDP port (default: 9222)
  -SkipDownload    Skip download (use cached installer)
  -SkipClean       Don't clean Playground
  -AutoLogin       Auto-login after First Time Setup (default: admin/admin123)
  -LoginUsername   Username for auto-login (default: admin)
  -LoginPassword   Password for auto-login (default: admin123)
```

---

## Installation Flow

```
┌─────────────────────────────────────────────────────────────┐
│                 AUTONOMOUS INSTALL FLOW                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. GET RELEASE                                             │
│     └─> Gitea API: /api/v1/repos/neilvibe/LocaNext/releases │
│     └─> Get: tag_name, installer URL                        │
│                                                             │
│  2. CLEAN PLAYGROUND                                        │
│     └─> Kill LocaNext.exe processes                         │
│     └─> Delete: C:\...\Playground\LocaNext\*                │
│     └─> Delete: %APPDATA%\LocaNext                          │
│     └─> Delete: %LOCALAPPDATA%\LocaNext                     │
│     └─> Delete: %LOCALAPPDATA%\locanext-updater             │
│                                                             │
│  3. DOWNLOAD INSTALLER                                      │
│     └─> Download to: %TEMP%\LocaNext_v*.exe                 │
│     └─> Size: ~163 MB                                       │
│                                                             │
│  4. SILENT INSTALL                                          │
│     └─> Run: installer.exe /S /D=<playground>\LocaNext      │
│     └─> Wait for completion (~60-90 seconds)                │
│     └─> Verify: LocaNext.exe exists                         │
│                                                             │
│  5. CONFIGURE CENTRAL SERVER                                │
│     └─> Create: %APPDATA%\LocaNext\server-config.json       │
│     └─> Host: 172.28.150.120:5432 (PostgreSQL)              │
│     └─> User: localization_admin                            │
│     └─> IMPORTANT: Write UTF-8 without BOM                  │
│                                                             │
│  6. LAUNCH (optional)                                       │
│     └─> Run: LocaNext.exe --remote-debugging-port=9222      │
│     └─> Wait: 5 seconds for startup                         │
│                                                             │
│  7. VERIFY (optional)                                       │
│     └─> CDP: http://127.0.0.1:9222/json                     │
│     └─> Check: page target exists                           │
│     └─> Check: backend health shows database_type: postgresql│
│                                                             │
│  8. AUTO-LOGIN (optional)                                   │
│     └─> Wait for First Time Setup (~5 min on first run)     │
│     └─> Login via API: POST /api/auth/login                 │
│     └─> User: admin / Password: admin123                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Paths

| What | Path |
|------|------|
| Playground (Windows) | `C:\NEIL_PROJECTS_WINDOWSBUILD\LocaNextProject\Playground` |
| Playground (WSL) | `/mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/Playground` |
| Install Dir | `<Playground>\LocaNext` |
| Executable | `<Playground>\LocaNext\LocaNext.exe` |
| User Data | `%APPDATA%\LocaNext` |
| Local Data | `%LOCALAPPDATA%\LocaNext` |
| Updater | `%LOCALAPPDATA%\locanext-updater` |
| **Server Config** | `%APPDATA%\LocaNext\server-config.json` |

---

## Central Server Configuration

The install script automatically creates `%APPDATA%\LocaNext\server-config.json` with PostgreSQL credentials for online mode.

### Config File Format

```json
{
  "postgres_host": "172.28.150.120",
  "postgres_port": 5432,
  "postgres_user": "localization_admin",
  "postgres_password": "locanext_dev_2025",
  "postgres_db": "localizationtools"
}
```

### Critical: UTF-8 Without BOM

**PowerShell 5.x** (`Set-Content -Encoding UTF8`) adds a UTF-8 BOM which breaks JSON parsing. The install script uses .NET to write without BOM:

```powershell
# Correct - no BOM
$jsonContent = $config | ConvertTo-Json
[System.IO.File]::WriteAllText($configPath, $jsonContent, [System.Text.UTF8Encoding]::new($false))

# WRONG - adds BOM, breaks JSON parsing
$config | ConvertTo-Json | Set-Content -Path $configPath -Encoding UTF8
```

### Config Priority

The backend loads configuration with this priority:
1. Environment variables (highest)
2. User config file (`server-config.json`)
3. Default values (lowest)

### Verifying Connection

After install, verify PostgreSQL connection:

```powershell
# Check backend health
Invoke-RestMethod -Uri "http://localhost:8888/health"

# Expected for ONLINE mode:
# {
#   "status": "healthy",
#   "database": "connected",
#   "database_type": "postgresql",   <-- THIS indicates online mode
#   "local_mode": false
# }
```

---

## NSIS Silent Install

The installer uses NSIS (Nullsoft) with these silent install options:

```
/S             Silent mode (no UI)
/D=<path>      Installation directory (must be last, no quotes)
```

Example:
```
LocaNext_v25.1216.1251_Light_Setup.exe /S /D=C:\Test\LocaNext
```

---

## CDP Verification

After launch, verify via Chrome DevTools Protocol:

```bash
# Get targets
curl http://127.0.0.1:9222/json

# Expected: page target with URL containing "localhost:5176" or "login" or "setup"
```

### CDP Test from WSL

```bash
# Check CDP is ready
curl -s http://127.0.0.1:9222/json | jq '.[0].url'

# Run full CDP test
node tests/cdp/test_connection_check.js
```

---

## Troubleshooting

### Installer hangs
```powershell
# Kill any stuck installer
Get-Process -Name "LocaNext*" | Stop-Process -Force
Get-Process -Name "*Setup*" | Stop-Process -Force
```

### CDP not responding
```bash
# Check if app is running
tasklist | grep -i locanext

# Check if port is listening
netstat -an | grep 9222

# Restart app with CDP
/mnt/c/.../Playground/LocaNext/LocaNext.exe --remote-debugging-port=9222
```

### Download fails
```powershell
# Check Gitea is reachable
Test-NetConnection -ComputerName 172.28.150.120 -Port 3000

# Manual download
Invoke-WebRequest -Uri "http://172.28.150.120:3000/neilvibe/LocaNext/releases/download/v25.1216.1251/LocaNext_v25.1216.1251_Light_Setup.exe" -OutFile "$env:TEMP\installer.exe"
```

---

## Example Output

```
============================================
  AUTONOMOUS PLAYGROUND INSTALL (WSL)
============================================

Running PowerShell script...

[13:48:11] [INFO]   AUTONOMOUS PLAYGROUND INSTALL
[13:48:11] [OK] Latest release: v25.1216.1251
[13:48:11] [OK] Playground cleaned
[13:48:13] [OK] Downloaded: 162.83 MB
[13:49:31] [OK] Installation complete
[13:49:31] [OK] LocaNext started (PID: 13496)
[13:51:02] [OK] CDP ready! Found 1 target(s)
[13:51:02] [OK] Page Title: LocaNext - First Time Setup
[13:51:02] [OK]   INSTALLATION SUCCESSFUL!

Playground contents:
total 288336
drwxrwxrwx 1 root root    4096 Dec 16 13:49 .
-rwxrwxrwx 1 root root 4741480 Dec 16 12:56 d3dcompiler_47.dll
...

App size: 605M
```

---

## Integration with CI

This script can be used in CI for Windows E2E testing:

```yaml
- name: Install to Playground
  shell: powershell
  run: |
    .\scripts\playground_install.ps1 -LaunchAfterInstall -EnableCDP

- name: Run CDP Tests
  run: |
    node tests/cdp/test_connection_check.js
```

---

## Database Modes & Testing

### Architecture Overview

LocaNext supports two database modes:

| Mode | Database | Use Case |
|------|----------|----------|
| **Offline (Local)** | SQLite | Single-user, no network required |
| **Online (Central)** | PostgreSQL | Multi-user, enterprise deployment |

The embedded Python backend (`localhost:8888`) runs on the user's machine and connects to either SQLite locally or PostgreSQL centrally.

### Default Behavior (Fresh Install)

After a fresh Playground install:
- App starts in **Offline mode** (SQLite)
- Server Status shows:
  - API Server: `http://localhost:8888` ✅ connected (embedded backend)
  - Database: PostgreSQL ❌ error (not configured)
  - WebSocket: ❌ disconnected
- "Go Online" button triggers connection attempt

### Testing Offline Mode

```powershell
# Check embedded backend health
Invoke-RestMethod -Uri "http://localhost:8888/health"

# Expected response:
# status: healthy
# database: connected
# database_type: sqlite
# local_mode: True
```

### Auto-Login Feature

Use `--auto-login` to automatically log in after First Time Setup completes:

```bash
# Full install with auto-login
./scripts/playground_install.sh --launch --auto-login
```

This will:
1. Wait for First Time Setup to complete (downloads model ~2.3GB)
2. Wait for login page to appear
3. Login via backend API as admin/admin123
4. Report success/failure

The app auto-connects to the central PostgreSQL server at `172.28.150.120:5432`.

### WSL2 Network Limitation

**WSL2 CANNOT reach Windows localhost.** CDP binds to Windows 127.0.0.1 which is inaccessible from WSL.

```bash
# From WSL - this does NOT work:
curl http://127.0.0.1:9222/json              # Connection refused!
```

**Run CDP tests from Windows PowerShell instead:**

```powershell
Push-Location '\\wsl.localhost\Ubuntu2\home\neil1988\LocalizationTools\testing_toolkit\cdp'
node login.js
node quick_check.js
```

See [testing_toolkit/cdp/README.md](../../testing_toolkit/cdp/README.md) for full CDP testing guide.

---

## Test Results (Build 296)

### Verified Working

| Feature | Status | Notes |
|---------|--------|-------|
| Autonomous install | ✅ | 163MB download, 605MB installed |
| Silent NSIS install | ✅ | `/S /D=path` works correctly |
| CDP debugging | ✅ | `--remote-debugging-port=9222` |
| First-time setup | ✅ | Dependencies and model loaded |
| Offline mode (SQLite) | ✅ | Embedded backend working |
| **Online mode (PostgreSQL)** | ✅ | Auto-configured via server-config.json |
| Auto-login | ✅ | admin/admin123 via API after First Time Setup |
| App UI | ✅ | LDM loaded, navigation works |

### Complete Flow

```
1. Install (163MB download, ~90s install)
2. Configure (server-config.json created automatically)
3. Launch (CDP enabled)
4. First Time Setup (~5 min on first run)
5. Backend connects to PostgreSQL (172.28.150.120:5432)
6. Auto-login as admin/admin123
7. App ready in ONLINE mode
```

### Prerequisites

| Requirement | Details |
|-------------|---------|
| PostgreSQL | Running on 172.28.150.120:5432 |
| User | localization_admin with correct password |
| pg_hba.conf | Allow connections from 172.28.0.0/16 |

---

*Created: 2025-12-16 | Updated: 2025-12-27 | Credentials: admin/admin123*
