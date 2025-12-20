# Master Test Protocol

**Complete workflow from code to validated build**

**Updated:** 2025-12-19 | **Build:** 301

---

## Overview

```
CODE → CI TESTS → BUILD → SMOKE TEST → RELEASE → INSTALL → CDP TESTS
  ↓        ↓         ↓         ↓           ↓         ↓          ↓
Push    Python    Windows   Backend    Gitea    Playground  Node.js
        ~285      NSIS      SQLite     Upload   PostgreSQL  WebSocket
        tests     Installer  Mode               Mode
```

---

## Phase 1: Trigger Build

```bash
# Option A: Just trigger
echo "Build LIGHT" >> GITEA_TRIGGER.txt
git add -A && git commit -m "Build" && git push origin main && git push gitea main

# Option B: Trigger with changes
git add -A && git commit -m "Fix: description"
echo "Build LIGHT" >> GITEA_TRIGGER.txt
git add GITEA_TRIGGER.txt && git commit -m "Build" --amend
git push origin main && git push gitea main
```

**Build Types:**
- `Build LIGHT` - No model (~200MB installer)
- `Build FULL` - With Qwen model (~2GB installer)
- `TROUBLESHOOT` - Skip Windows build, resume from checkpoint
- `TROUBLESHOOT_WINDOWS` - Windows only

---

## Phase 2: CI Pipeline (Automatic)

**Duration:** ~12-15 minutes

### Job 1: Check Trigger (Ubuntu)
- Parses `GITEA_TRIGGER.txt`
- Generates version: `YY.MMDD.HHMM`

### Job 2: Safety Checks (Ubuntu)
1. Inject version into `version.py` and `package.json`
2. Start server: `python3 server/main.py`
3. Verify PostgreSQL connection (NOT SQLite fallback)
4. Create admin user (admin/admin123)
5. Run ~285 Python tests:
   - Unit tests
   - Integration tests (API, auth, database)
   - E2E tests (workflows)
   - Security tests (JWT, CORS, IP filter)
6. Security audits (pip-audit, npm audit)

### Job 3: Build Windows (Windows Runner)
1. Inject version
2. Get Python Embedded (smart cache)
3. Install all pip dependencies
4. Build Electron app
5. Create NSIS installer
6. **SMOKE TEST:**
   - Silent install to `C:\LocaNextSmokeTest\`
   - Verify files present
   - Test backend in SQLite mode
   - `curl http://127.0.0.1:8888/health`
7. Create Gitea release
8. Upload installer + latest.yml

---

## Phase 3: Monitor Build

```bash
# Check if build completed (via releases API)
curl -s "http://172.28.150.120:3000/api/v1/repos/neilvibe/LocaNext/releases?limit=1" | jq -r '.[0] | {tag_name, created_at, name}'

# Watch mode (check every 30s)
watch -n 30 'curl -s "http://172.28.150.120:3000/api/v1/repos/neilvibe/LocaNext/releases?limit=1" | jq -r ".[0].tag_name"'
```

**DO NOT install/test until:** A new release with expected version appears.

---

## Phase 3.5: Verify Servers Online (REQUIRED)

**Before installing, ensure all servers are running:**

```bash
./scripts/check_servers.sh
```

Or manually:

```bash
# PostgreSQL (central database)
pg_isready -h 172.28.150.120 -p 5432 && echo "PostgreSQL: ✅" || echo "PostgreSQL: ❌"

# Gitea (releases/CI)
curl -s -o /dev/null -w "%{http_code}" http://172.28.150.120:3000/api/v1/version | grep -q 200 && echo "Gitea: ✅" || echo "Gitea: ❌"

# Backend (if running locally for dev)
curl -s -o /dev/null -w "%{http_code}" http://localhost:8888/health | grep -q 200 && echo "Backend: ✅" || echo "Backend: ❌"
```

**All servers must be ✅ before proceeding.**

---

## Phase 4: Install to Playground

**IMPORTANT:** Installation requires running a Windows NSIS installer. There is NO pure-WSL method.

### Option A: From WSL (calls PowerShell via interop)

```bash
./scripts/playground_install.sh --launch --auto-login
```

If you get "cannot execute binary file: Exec format error", WSL interop is broken. Use Option B or C.

### Option B: From Windows PowerShell

```powershell
cd D:\LocalizationTools
.\scripts\playground_install.ps1 -LaunchAfterInstall -EnableCDP -AutoLogin
```

### Option C: From Windows CMD

```cmd
cd D:\LocalizationTools
powershell -ExecutionPolicy Bypass -File scripts\playground_install.ps1 -LaunchAfterInstall -EnableCDP -AutoLogin
```

### Why No Pure-WSL Install?
- NSIS installer is a Windows .exe
- Windows binaries require WSL interop to execute
- If interop broken, MUST run from Windows directly

### What Install Does:
1. Fetches latest release from Gitea API
2. Downloads installer (~163MB)
3. Kills existing LocaNext processes
4. Cleans Playground directory
5. Silent install: `/S /D=C:\...\Playground\LocaNext`
6. Creates `%APPDATA%\LocaNext\server-config.json` (PostgreSQL config)
7. Launches with CDP: `--remote-debugging-port=9222`
8. Waits for First Time Setup (~2-5 min first run)
9. Auto-login as neil/neil

### After Install: HARD REFRESH REQUIRED
After installing a new build, do a **hard refresh** in the app:
- **Windows:** `Ctrl+Shift+R` or `Ctrl+F5`
- This clears cached frontend assets and loads the new version

---

## Phase 5: Run Node.js CDP Tests

**IMPORTANT:** CDP tests must run from Windows PowerShell (not WSL). CDP binds to Windows localhost which WSL2 cannot reach.

**From Windows PowerShell:**

```powershell
# Access test scripts via UNC path
Push-Location '\\wsl.localhost\Ubuntu2\home\neil1988\LocalizationTools\testing_toolkit\cdp'

# Login first (if at login screen)
node login.js

# Run tests
node quick_check.js           # Basic page state
node test_server_status.js    # Server panel
node test_bug029.js           # Upload as TM
node test_bug023.js           # TM status
```

**Alternative - Pure Windows paths:**

```cmd
cd D:\LocalizationTools\testing_toolkit\cdp
node login.js
node quick_check.js
```

---

## Quick Reference

### Full Flow Commands

```bash
# 1. PUSH (from WSL)
git push origin main && git push gitea main

# 2. WAIT & MONITOR (from WSL)
watch -n 30 'curl -s "http://172.28.150.120:3000/api/v1/repos/neilvibe/LocaNext/actions/runs" | jq ".[0] | {status, conclusion}"'

# 3. CHECK RELEASE (from WSL)
curl -s "http://172.28.150.120:3000/api/v1/repos/neilvibe/LocaNext/releases?limit=1" | jq -r '.[0].tag_name'

# 4. INSTALL (from Windows PowerShell)
.\scripts\playground_install.ps1 -LaunchAfterInstall -EnableCDP -AutoLogin

# 5. TEST (from Windows PowerShell - NOT WSL!)
Push-Location '\\wsl.localhost\Ubuntu2\home\neil1988\LocalizationTools\testing_toolkit\cdp'
node login.js && node test_server_status.js
```

### Just Launch (Already Installed)

**Windows:**
```cmd
cd C:\NEIL_PROJECTS_WINDOWSBUILD\LocaNextProject\Playground\LocaNext
LocaNext.exe --remote-debugging-port=9222
```

**WSL (when interop works):**
```bash
/mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/Playground/LocaNext/LocaNext.exe --remote-debugging-port=9222 &
```

---

## Paths

| What | Windows | WSL |
|------|---------|-----|
| Repo | `D:\LocalizationTools` | `/home/neil1988/LocalizationTools` |
| Playground | `C:\NEIL_PROJECTS_WINDOWSBUILD\LocaNextProject\Playground\LocaNext` | `/mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/Playground/LocaNext` |
| CDP Tests | `testing_toolkit\cdp\` | `testing_toolkit/cdp/` |
| Install Script | `scripts\playground_install.ps1` | `scripts/playground_install.sh` |

---

## Test Scripts

| Script | Purpose |
|--------|---------|
| `quick_check.js` | Page state, URL, test interfaces |
| `test_server_status.js` | Server panel, database status |
| `test_bug023.js` | TM status (pending vs ready) |
| `test_bug023_build.js` | Trigger TM index build |
| `test_bug029.js` | Right-click "Upload as TM" flow |
| `test_clean_slate.js` | Clear TMs, check file state |

---

## Troubleshooting

### WSL Interop Broken ("Exec format error")

**Symptom:**
```
/mnt/c/.../powershell.exe: cannot execute binary file: Exec format error
```

**Quick Fix (no restart needed):**
```bash
sudo sh -c 'echo ":WSLInterop:M::MZ::/init:PF" > /proc/sys/fs/binfmt_misc/register'
```

**Verify:**
```bash
ls /proc/sys/fs/binfmt_misc/WSLInterop && cmd.exe /c echo "Works!"
```

**Full details:** See [docs/wip/WSL_INTEROP.md](../docs/wip/WSL_INTEROP.md)

### CDP Not Responding
```bash
# Check if app is running
curl -s http://127.0.0.1:9222/json

# If empty, app not running or CDP not enabled
# Launch from Windows with --remote-debugging-port=9222
```

### Build Failed
```bash
# Check Gitea Actions
http://172.28.150.120:3000/neilvibe/LocaNext/actions

# TROUBLESHOOT mode (resume from checkpoint)
echo "TROUBLESHOOT" >> GITEA_TRIGGER.txt
git add -A && git commit -m "Troubleshoot" && git push origin main && git push gitea main
```

---

## Related Docs

| Doc | Purpose |
|-----|---------|
| [cdp/README.md](cdp/README.md) | Node.js CDP test guide |
| [../docs/testing/PLAYGROUND_INSTALL_PROTOCOL.md](../docs/testing/PLAYGROUND_INSTALL_PROTOCOL.md) | Detailed install options |
| [README.md](README.md) | Testing toolkit overview |

---

*Master protocol: Push → CI → Build → Install → Test*
