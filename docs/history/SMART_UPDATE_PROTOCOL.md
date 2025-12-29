# Smart Update Protocol

**Purpose:** Fast update workflow without full reinstall

**Status:** ENABLED as of Build 399+

---

## How Smart Updates Work

electron-updater uses **blockmap differential downloads**:

1. **Blockmap file** (`.exe.blockmap`) uploaded alongside installer
2. When updating, electron-updater compares blocks
3. **Only downloads changed blocks** (typically 5-15MB vs 173MB full)
4. Applies changes in-place

**CI changes (build.yml):**
- Line 1581-1588: Copies blockmap from dist-electron to installer_output
- Line 2351-2361: Uploads blockmap to Gitea release

---

## Overview

LocaNext has THREE refresh methods:

| Method | When to Use | Time |
|--------|-------------|------|
| **Hot Reload** | JS/CSS changes only | 2 sec |
| **Auto-Update** | New build from Gitea | 1-2 min |
| **Full Reinstall** | Major changes, corrupted state | 5-10 min |

---

## Method 1: Hot Reload (Ctrl+Shift+R)

**Use when:** Testing CSS/UI changes during dev

```bash
# In the running Electron app:
# Press Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)
```

**What it does:**
- Clears browser cache
- Reloads the frontend assets
- Does NOT restart backend

**Limitation:** Only works if the app is loading from dev server (localhost:5173)

---

## Method 2: Auto-Update (Recommended)

**Use when:** New build available on Gitea, want to update without reinstall

### Option A: Trigger from App UI

1. Open LocaNext
2. Click "Settings" menu
3. Click "About"
4. Click "Check for Updates"
5. If update found, click "Download and Install"
6. App restarts with new version

### Option B: Trigger via CDP (for Claude)

```javascript
// From Windows Node.js:
const evaluate = (expr) => { /* CDP helper */ };

// Trigger update check
await evaluate(`
  window.electronAPI?.checkForUpdates?.() ||
  console.log('No electronAPI available')
`);
```

### Option C: Force Update via IPC

```javascript
// In the Electron console (DevTools):
require('electron').ipcRenderer.invoke('check-for-updates')
  .then(result => console.log('Update result:', result));
```

---

## Method 3: Full Reinstall

**Use when:** Auto-update fails, major version change, corrupted state

### From Windows PowerShell:

```powershell
# 1. Kill existing app
taskkill /F /IM LocaNext.exe /T

# 2. Download latest installer from Gitea
$release = Invoke-RestMethod "http://172.28.150.120:3000/api/v1/repos/neilvibe/LocaNext/releases?limit=1"
$installer = $release[0].assets | Where-Object { $_.name -like "*Setup.exe" }
Invoke-WebRequest $installer.browser_download_url -OutFile "$env:TEMP\LocaNext_Setup.exe"

# 3. Silent install to Playground
& "$env:TEMP\LocaNext_Setup.exe" /S /D=C:\NEIL_PROJECTS_WINDOWSBUILD\LocaNextProject\Playground\LocaNext

# 4. Wait for install
Start-Sleep -Seconds 90

# 5. Launch with CDP
& "C:\NEIL_PROJECTS_WINDOWSBUILD\LocaNextProject\Playground\LocaNext\LocaNext.exe" --remote-debugging-port=9222
```

---

## Playground Location

```
Windows Path: C:\NEIL_PROJECTS_WINDOWSBUILD\LocaNextProject\Playground\LocaNext\
WSL Path:     /mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/Playground/LocaNext/

Key Files:
├── LocaNext.exe                    # Main executable
├── resources/
│   └── app.asar                    # Bundled frontend (extract to verify CSS)
└── resources/server/               # Python backend

Shortcuts:
- Playground: /mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/Playground/
- App exe:    Playground/LocaNext/LocaNext.exe
```

---

## Complete Playground Refresh Workflow

### Scenario 1: App Already Running + New Build Ready

```bash
# 1. Check if app is running on CDP port
/mnt/c/Windows/System32/curl.exe -s http://127.0.0.1:9222/json > /dev/null && echo "Running"

# 2. Trigger update via CDP script
cd /home/neil1988/LocalizationTools/testing_toolkit/cdp
/mnt/c/Program\ Files/nodejs/node.exe trigger_update.js

# 3. App downloads update and restarts automatically
# 4. Login via CDP
/mnt/c/Program\ Files/nodejs/node.exe login.js
```

### Scenario 2: App Not Running + New Build Ready

```bash
# 1. Launch app with CDP enabled
"/mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/Playground/LocaNext/LocaNext.exe" --remote-debugging-port=9222 &

# 2. Wait for startup
sleep 10

# 3. Login via CDP
cd /home/neil1988/LocalizationTools/testing_toolkit/cdp
/mnt/c/Program\ Files/nodejs/node.exe login.js
```

### Scenario 3: First Install (No Existing App)

```bash
# Use scripts/playground_install.sh (downloads and installs latest from Gitea)
./scripts/playground_install.sh --launch --auto-login
```

---

## Claude Workflow: After Build Completes

1. **Wait for Build** (via Gitea DB check)
2. **Check if app is running** (via CDP port check)
3. **Trigger auto-update** (via CDP/IPC)
4. **Wait for update** (check version changed)
5. **Auto-login** (via API after restart)
6. **Verify fixes** (via CDP tests)

### Script: Smart Refresh

```bash
#!/bin/bash
# smart_refresh.sh - Intelligent app refresh

# Check if app is running
if /mnt/c/Windows/System32/curl.exe -s http://127.0.0.1:9222/json > /dev/null 2>&1; then
    echo "App running - triggering auto-update"
    # Use CDP to trigger update check
    /mnt/c/Program\ Files/nodejs/node.exe -e "
    const http = require('http');
    const WebSocket = require('ws');

    async function triggerUpdate() {
        const targets = await new Promise(r => {
            http.get('http://127.0.0.1:9222/json', res => {
                let d=''; res.on('data',c=>d+=c); res.on('end',()=>r(JSON.parse(d)));
            });
        });
        const ws = new WebSocket(targets[0].webSocketDebuggerUrl);
        // ... CDP commands to trigger update
    }
    triggerUpdate();
    "
else
    echo "App not running - launching..."
    /mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/Playground/LocaNext/LocaNext.exe --remote-debugging-port=9222 &
fi
```

---

## Auto-Login After Refresh

**Credentials:** admin / admin123 (superadmin)

### Via Backend API (recommended)

```bash
# From Windows curl:
/mnt/c/Windows/System32/curl.exe -s -X POST "http://127.0.0.1:8888/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

### Via CDP (fills form)

```javascript
// Fill username
await evaluate(`document.querySelector('input').value = 'admin'`);
// Fill password
await evaluate(`document.querySelector('input[type="password"]').value = 'admin123'`);
// Click login
await evaluate(`document.querySelector('button').click()`);
```

---

## Verification After Update

1. **Check version** in health endpoint
2. **Extract app.asar** and grep for changes
3. **Take screenshot** as proof
4. **Run CDP tests** for specific fixes

```bash
# Check version
/mnt/c/Windows/System32/curl.exe -s http://127.0.0.1:8888/health | grep version

# Extract and verify CSS fix
cd /tmp && npx asar extract "/mnt/c/.../app.asar" app && grep "my-fix" app/**/*.css
```

---

## Critical Notes for Claude

### WSL vs Windows
- **CDP scripts MUST run with Windows Node.js**, not WSL node
- Use: `/mnt/c/Program\ Files/nodejs/node.exe script.js`
- NOT: `node script.js` (WSL node can't reach Windows localhost)

### Environment Variables
- Env vars from WSL **DO NOT pass** to Windows processes
- CDP scripts use defaults (admin/admin123) - no env vars needed

### Credentials
| User | Password | Notes |
|------|----------|-------|
| admin | admin123 | Superadmin - ALWAYS WORKS |
| neil | ??? | Exists but password unknown |
| ci_tester | ci_test_pass_2024 | CI only (Gitea secrets) |

### Verify CSS Deployed
```bash
# Extract app.asar and check CSS
cd /tmp
npx asar extract "/mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/Playground/LocaNext/resources/app.asar" app
grep "cds-layer-hover" app/build/_app/immutable/**/*.css
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Update not detected | Check Gitea has new release |
| Update download fails | Check network, try full reinstall |
| App won't start after update | Delete %APPDATA%\LocaNext, reinstall |
| Old version still showing | Hard refresh (Ctrl+Shift+R) |
| Login fails | Use admin/admin123, not neil/neil |
| CDP timeout | App not started with `--remote-debugging-port=9222` |
| ECONNREFUSED | App not running on Windows |

---

*Created: 2025-12-27 | Updated: 2025-12-27 | Purpose: Fast iteration without full reinstalls*
