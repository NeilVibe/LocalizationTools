# Master Test Protocol

**Complete workflow from code to validated build**

**Updated:** 2025-12-21 | **Build:** 312 (VERIFIED)

---

## Overview

```
CODE → CI TESTS → BUILD → SMOKE TEST → RELEASE → INSTALL/UPDATE → CDP TESTS
  ↓        ↓         ↓         ↓           ↓            ↓              ↓
Push    Python    Windows   Backend    Gitea     Playground       Node.js
        ~285      NSIS      SQLite     Upload    PostgreSQL       WebSocket
        tests     Installer  Mode                Mode
```

---

## ⚠️ CRITICAL: INSTALL vs UPDATE

**These are COMPLETELY DIFFERENT operations. Using the wrong one wastes time and tests the wrong thing.**

| | INSTALL | UPDATE |
|--|---------|--------|
| **What** | Fresh installation from .exe | Auto-updater downloads new version |
| **When** | First time, clean slate, testing first-run | App already installed, just need new code |
| **Time** | 2-5 min (includes Python setup) | 30 sec - 2 min |
| **Command** | `./scripts/playground_install.sh` | Just open the app, it auto-updates |
| **Tests** | First-run experience, clean install | Upgrade path, existing user experience |

### Decision Guide

| Scenario | Use |
|----------|-----|
| App not installed yet | INSTALL |
| App installed, testing new fix | **UPDATE** (just open app) |
| Testing first-run setup | INSTALL |
| Testing auto-updater | **UPDATE** |
| Clean slate needed | INSTALL |
| Quick verification of fix | **UPDATE** |
| User reported bug | **UPDATE** |

### UPDATE Flow (Most Common)

```
1. Push code → CI builds → Release on Gitea
2. Open LocaNext (already installed)
3. App auto-checks on startup OR Menu → Help → Check for Updates
4. Download notification appears
5. Click "Download" → "Install & Restart"
6. App restarts with new version
7. Test the fix
```

### INSTALL Flow (Less Common)

```
1. Push code → CI builds → Release on Gitea
2. Run: ./scripts/playground_install.sh --launch --auto-login
3. Wait for First Time Setup (~2-5 min)
4. Test in clean environment
```

**See [DOC-001: Install vs Update Confusion](../docs/wip/DOC-001_INSTALL_VS_UPDATE_CONFUSION.md) for full details.**

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

## Phase 4: Get New Version to Playground

**Choose based on your testing needs:**

### Option 1: UPDATE (Most Common - 30 sec to 2 min)

If app is already installed and you just need the new code:

1. Open LocaNext (from Playground or Start Menu)
2. App auto-checks for updates on startup
3. When notification appears: Download → Install & Restart
4. App restarts with new version - ready to test

**Skip to Phase 5 for CDP testing.**

### Option 2: INSTALL (Fresh Install - 2-5 min)

Only use if: first time, testing first-run, or need clean slate.

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

## Phase 6: AI Visual Verification Protocol

**USER SCREENSHOT LOCATION:** `/mnt/c/Users/MYCOM/Pictures/Screenshots/`

```bash
# Check user's latest screenshot (Win+Shift+S)
ls -lt /mnt/c/Users/MYCOM/Pictures/Screenshots/*.png | head -3

# Read the newest one
cat "/mnt/c/Users/MYCOM/Pictures/Screenshots/$(ls -t /mnt/c/Users/MYCOM/Pictures/Screenshots/ | head -1)"
```

**This protocol ensures UI/UX fixes are VERIFIED with screenshot proof before marking as complete.**

### Mindset: Be DEMANDING (CRITICAL)

**TAKE MULTIPLE SCREENSHOTS. CHECK AGAIN AND AGAIN AND AGAIN.**

1. **Never trust code changes alone** - PROVE IT with screenshots
2. **Take MULTIPLE screenshots** - One is NOT enough
3. **Check AGAIN and AGAIN** - Until you are 100% CERTAIN
4. **Compare before/after** - Understand what changed
5. **Don't mark VERIFIED until you have EXACT PROOF**
6. **If ANY doubt remains** - Take ANOTHER screenshot

```
The Verification Loop:
┌─────────────────────────────────────────┐
│  1. Take screenshot                      │
│  2. Read image - analyze what you see    │
│  3. Is this EXACTLY what we need?        │
│     │                                    │
│     ├─ YES (100% certain) → VERIFIED ✅  │
│     │                                    │
│     └─ ANY doubt → Go back to step 1     │
│        Take ANOTHER screenshot           │
│        Check AGAIN. And AGAIN.           │
└─────────────────────────────────────────┘
```

### Step-by-Step Protocol

```bash
# 1. Take screenshot via CDP (from WSL)
/mnt/c/Program\ Files/nodejs/node.exe -e "
const CDP = require('chrome-remote-interface');
const fs = require('fs');

(async () => {
    const client = await CDP({ port: 9222 });
    const { Page } = client;
    await Page.enable();

    const screenshot = await Page.captureScreenshot({ format: 'png' });
    const buffer = Buffer.from(screenshot.data, 'base64');
    fs.writeFileSync('C:\\\\path\\\\to\\\\screenshot.png', buffer);
    console.log('Screenshot saved');

    await client.close();
})();
"

# 2. View screenshot (Claude can read images)
# Use the Read tool on the .png file

# 3. Analyze and verify the fix is visible
```

### What to Verify Visually

| Issue Type | What to Look For |
|------------|------------------|
| **Column layout** | No overlap, proper separator lines, columns fill width |
| **Removed elements** | Element NOT visible in DOM/UI |
| **Added elements** | Element IS visible and correct |
| **Responsive layout** | Columns adapt to container width |
| **Text/labels** | Correct text, no "?" or "undefined" |

### Svelte 5 UIUX Verification

When implementing UI fixes with Svelte 5:

1. **Verify `$state()` reactivity** - Change state, verify UI updates
2. **Verify percentage widths** - Resize window, verify auto-adaptation
3. **Verify no hardcoded pixels** - Columns should flex, not fixed

### Screenshot Evidence Pattern

```
Build XXX Verification:
1. build{XXX}_dashboard.png - Initial state
2. build{XXX}_fileview.png - File viewer opened
3. build{XXX}_detail.png - Close-up of specific fix
4. build{XXX}_verified.png - Final proof screenshot
```

### Example: UI-044 Verification

```
Issue: Source/Target columns overlapping
Fix: Added 2px border + percentage-based widths

Verification Steps:
1. Open file with content (sampleofLanguageData.txt)
2. Screenshot shows:
   - Clear vertical line between SOURCE (KR) and TARGET
   - Both columns fill available width
   - No empty 3rd column on right
3. Status: VERIFIED ✅
```

### Documentation After Verification

Update these files:
1. **ISSUES_TO_FIX.md** - Mark status as VERIFIED, add screenshot reference
2. **SESSION_CONTEXT.md** - Document what was verified and how
3. **GITEA_TRIGGER.txt** - Add build description

### AI State of Mind Principles

1. **Be skeptical** - Code changes don't prove UI works
2. **Be visual** - Screenshots reveal what users actually see
3. **Be thorough** - Test multiple scenarios, not just happy path
4. **Be precise** - Document exactly what was fixed and how
5. **Be demanding** - Don't accept "probably works", need proof

### Common Verification Failures

| Symptom | Likely Cause |
|---------|--------------|
| Screenshot shows old UI | Browser cache - need hard refresh |
| Element still visible | CSS specificity issue or wrong selector |
| Text shows "?" or "undefined" | Reactive binding not working |
| Layout broken at edges | Missing min-width or flex constraints |

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
