# Windows EXE Debugging Guide

**Updated:** 2025-12-06 | **Status:** Working | **Tests:** All XLS Transfer endpoints verified

---

## 📂 Document Tree

```
WINDOWS_TROUBLESHOOTING.md
│
├── 🚀 Quick Reference ─────── Launch, kill, logs commands
├── 🎮 CDP Interaction ──────── Click buttons, inspect DOM
├── 📸 Screenshot Method ────── Capture app visually
├── 🧪 Test Scripts ─────────── Automated CDP tests
├── 🔴 Known Issues ─────────── SvelteKit 404, Python paths
├── 📋 Logging ──────────────── Bulletproof logger info
├── 🔄 Deploy Workflow ──────── Build → Copy → Test
└── ✅ Test Results ─────────── 19/20 tests passing
```

---

## Quick Reference

### Launch App from WSL
```bash
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command "Start-Process 'C:\NEIL_PROJECTS_WINDOWSBUILD\LocaNextProject\LocaNext\LocaNext.exe'" &
```

### Launch with Remote Debugging (for UI interaction)
```bash
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command "Start-Process -FilePath 'C:\NEIL_PROJECTS_WINDOWSBUILD\LocaNextProject\LocaNext\LocaNext.exe' -ArgumentList '--remote-debugging-port=9222'" &
```

### Kill App
```bash
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command "Stop-Process -Name LocaNext -Force"
```

### Read Logs
```bash
cat "/mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/LocaNext/logs/locanext_app.log" | tail -50
```

### Push Code Changes
```bash
cp locaNext/electron/main.js "/mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/LocaNext/resources/app/electron/main.js"
cp locaNext/electron/preload.js "/mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/LocaNext/resources/app/electron/preload.js"
cp -r locaNext/build/* "/mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/LocaNext/resources/app/build/"
```

---

## Interacting with the App (No User Needed)

### Method 1: Chrome DevTools Protocol (RECOMMENDED)

Launch app with `--remote-debugging-port=9222`, then use Node.js to interact:

```bash
# 1. Create click_button.js on Windows
cat > "/mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/LocaNext/click_button.js" << 'EOF'
const WebSocket = require('ws');
async function main() {
    const buttonName = process.argv[2] || 'Load dictionary';
    const response = await fetch('http://localhost:9222/json');
    const pages = await response.json();
    const ws = new WebSocket(pages[0].webSocketDebuggerUrl);
    let msgId = 1;

    function send(method, params = {}) {
        return new Promise((resolve) => {
            const id = msgId++;
            ws.on('message', function handler(data) {
                const msg = JSON.parse(data.toString());
                if (msg.id === id) { ws.off('message', handler); resolve(msg.result); }
            });
            ws.send(JSON.stringify({ id, method, params }));
        });
    }

    ws.on('open', async () => {
        const result = await send('Runtime.evaluate', {
            expression: `
                const btn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('${buttonName}'));
                btn ? (btn.click(), 'CLICKED: ' + btn.textContent.trim()) : 'NOT FOUND: ${buttonName}';
            `,
            returnByValue: true
        });
        console.log(result.result.value);
        ws.close();
        process.exit(0);
    });
}
main();
EOF

# 2. Install ws module (one-time)
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command "cd C:\NEIL_PROJECTS_WINDOWSBUILD\LocaNextProject\LocaNext; npm install ws --no-save"

# 3. Click a button
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command "cd C:\NEIL_PROJECTS_WINDOWSBUILD\LocaNextProject\LocaNext; node click_button.js 'Load dictionary'"
```

### Method 2: Inspect DOM
```bash
# Create inspect_dom.js
cat > "/mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/LocaNext/inspect_dom.js" << 'EOF'
const WebSocket = require('ws');
async function main() {
    const response = await fetch('http://localhost:9222/json');
    const pages = await response.json();
    const ws = new WebSocket(pages[0].webSocketDebuggerUrl);
    let msgId = 1;

    function send(method, params = {}) {
        return new Promise((resolve) => {
            const id = msgId++;
            ws.on('message', function handler(data) {
                const msg = JSON.parse(data.toString());
                if (msg.id === id) { ws.off('message', handler); resolve(msg.result); }
            });
            ws.send(JSON.stringify({ id, method, params }));
        });
    }

    ws.on('open', async () => {
        // Count buttons
        const btnCount = await send('Runtime.evaluate', {
            expression: 'document.querySelectorAll("button").length',
            returnByValue: true
        });
        console.log('Buttons:', btnCount.result.value);

        // List button texts
        const btnTexts = await send('Runtime.evaluate', {
            expression: 'Array.from(document.querySelectorAll("button")).map(b => b.textContent.trim()).join(" | ")',
            returnByValue: true
        });
        console.log('Button texts:', btnTexts.result.value);

        // Check containers
        const containers = await send('Runtime.evaluate', {
            expression: `JSON.stringify({
                xlstransfer: !!document.querySelector(".xlstransfer-container"),
                buttonFrame: !!document.querySelector(".button-frame"),
                header: !!document.querySelector(".bx--header")
            })`,
            returnByValue: true
        });
        console.log('Containers:', containers.result.value);

        ws.close();
        process.exit(0);
    });
}
main();
EOF

# Run inspection
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command "cd C:\NEIL_PROJECTS_WINDOWSBUILD\LocaNextProject\LocaNext; node inspect_dom.js"
```

### Method 3: Take Screenshot
```bash
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command "
Add-Type -AssemblyName System.Windows.Forms, System.Drawing
\$proc = Get-Process LocaNext | Select -First 1
Add-Type 'using System; using System.Runtime.InteropServices; public struct RECT { public int Left, Top, Right, Bottom; } public class WinAPI { [DllImport(\"user32.dll\")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT r); }'
\$r = New-Object RECT
[WinAPI]::GetWindowRect(\$proc.MainWindowHandle, [ref]\$r)
\$w = \$r.Right - \$r.Left; \$h = \$r.Bottom - \$r.Top
\$bmp = New-Object System.Drawing.Bitmap(\$w, \$h)
[System.Drawing.Graphics]::FromImage(\$bmp).CopyFromScreen(\$r.Left, \$r.Top, 0, 0, [System.Drawing.Size]::new(\$w, \$h))
\$bmp.Save('C:\NEIL_PROJECTS_WINDOWSBUILD\LocaNextProject\LocaNext\screenshot.png')
"

# View in Claude (use Read tool)
# /mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/LocaNext/screenshot.png
```

### Method 4: Test Backend API
```bash
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command "
Invoke-RestMethod -Uri 'http://localhost:8888/health'
"
```

---

## Success Indicators in Logs

```
✅ Auto health check DISABLED
✅ XLSTransfer modules loaded successfully
✅ Authentication verified | username: admin
✅ WebSocket connected
✅ Component: XLSTransfer - mounted
```

---

## Startup Error Diagnosis (App Won't Launch)

When the Windows app won't start, use these methods to diagnose:

### 1. Check startup_crash.txt (Added 2025-12-06)

The app now logs startup errors to a file:
```bash
# Check startup crash log
cat "/mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/LocaNext/resources/app/logs/startup_crash.txt" 2>/dev/null || echo "No crash log - app started OK"
```

This captures ES module import errors before the main logging system starts.

### 2. Test Backend API Separately

If app shows errors, test if backend is running:
```bash
# Use PowerShell to test Windows localhost (WSL curl can't reach Windows localhost!)
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command "
    Invoke-WebRequest -Uri 'http://localhost:8888/health' -UseBasicParsing -TimeoutSec 5
"
```

### 3. Test API Endpoints Directly

Use curl.exe to bypass UI issues:
```bash
# Login and test XLS Transfer endpoints via PowerShell
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command "
    \$response = Invoke-RestMethod -Uri 'http://localhost:8888/api/auth/login' -Method Post -Body '{\"username\":\"admin\",\"password\":\"admin123\"}' -ContentType 'application/json'
    \$token = \$response.access_token
    curl.exe -s 'http://localhost:8888/api/v2/xlstransfer/health' -H \"Authorization: Bearer \$token\"
"
```

### 4. Ask User for Screenshot

If no logs and app shows error dialog:
1. Ask user to take screenshot of error dialog
2. Save to `screenshotsForClaude/` folder
3. Read the image with Read tool

### 5. Missing Module Error (Common)

Example: `ERR_MODULE_NOT_FOUND: Cannot find module 'telemetry.js'`
```bash
# Fix: Copy missing file
cp /home/neil1988/LocalizationTools/locaNext/electron/telemetry.js /mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/LocaNext/resources/app/electron/
```

Always sync ALL electron files after changes:
```bash
cp /home/neil1988/LocalizationTools/locaNext/electron/*.js /mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/LocaNext/resources/app/electron/
```

---

## Known Issues

### 1. SvelteKit 404 (WORKAROUND)
- **Symptom:** `[Renderer ERROR] | "Error: Not found: /C:/Users/.../index.html"`
- **Current fix:** `+error.svelte` catches 404 and renders content
- **Real fix needed:** Hash-based routing or proper SvelteKit adapter config

### 2. Python Scripts Missing
- **Symptom:** `can't open file '...tools/xlstransfer/load_dictionary.py': No such file`
- **Fix:** Python scripts should be at `resources/tools/xlstransfer/` (extraResources from build)
- **Manual deploy:** `cp -r server/tools/xlstransfer "/mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/LocaNext/resources/tools/"`

### 3. Port 9222 Already in Use (CDP Conflict)
- **Symptom:** `listen EADDRINUSE: address already in use :::9222` or CDP not responding
- **Cause:** Multiple LocaNext instances launched without killing previous ones
- **Fix:**
```bash
# Kill ALL LocaNext processes on Windows
/mnt/c/Windows/System32/taskkill.exe /F /IM LocaNext.exe

# Verify port is clear
ss -tlnp | grep 9222 || echo "Port 9222 clear"

# Then launch ONE instance
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command "Start-Process -FilePath 'C:\NEIL_PROJECTS_WINDOWSBUILD\LocaNextProject\LocaNext\LocaNext.exe' -ArgumentList '--remote-debugging-port=9222'" &
```
- **Prevention:** Always kill previous instances before launching new ones during testing

### 4. CDP Not Accessible from WSL (CRITICAL!)
- **Symptom:** `fetch('http://localhost:9222/json')` hangs or fails from WSL
- **Cause:** CDP on Windows binds to `127.0.0.1` (Windows-only). WSL has its own network stack and cannot reach Windows localhost directly.
- **Wrong approach:**
```bash
# This WON'T work from WSL:
curl http://localhost:9222/json  # Times out!
node cdp_test.js                 # Connection refused!
```
- **Correct approach:** Run CDP scripts via PowerShell:
```bash
# Create test script on Windows side
cat > /mnt/c/NEIL_PROJECTS_WINDOWSBUILD/cdp_test.js << 'EOF'
const WebSocket = require('ws');
async function main() {
    const response = await fetch('http://localhost:9222/json');
    const pages = await response.json();
    console.log('Pages:', pages.length);
    // ... rest of test
}
main();
EOF

# Run from WSL via PowerShell (THIS WORKS!)
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command "cd C:\NEIL_PROJECTS_WINDOWSBUILD; node cdp_test.js"
```
- **Key insight:** The Node.js process runs on Windows, so it CAN reach Windows localhost:9222

---

## Bulletproof Logging

Uses `process.execPath` which works in all environments:
- Production: `C:\...\LocaNext.exe` → logs to `{exe_dir}/logs/`
- Development: `/usr/bin/node` → logs to `{cwd}/locaNext/logs/`

**Key files:**
- `electron/logger.js` - Main logger
- `electron/main.js` - Error handlers, dialog interceptor

---

## Full Test Workflow

```bash
# 1. Kill, clear, push, restart
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command "Stop-Process -Name LocaNext -Force" 2>/dev/null
rm -f "/mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/LocaNext/logs/"*.log
cp locaNext/electron/main.js "/mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/LocaNext/resources/app/electron/main.js"
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command "Start-Process -FilePath 'C:\NEIL_PROJECTS_WINDOWSBUILD\LocaNextProject\LocaNext\LocaNext.exe' -ArgumentList '--remote-debugging-port=9222'" &

# 2. Wait for startup
sleep 35

# 3. Inspect DOM
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command "cd C:\NEIL_PROJECTS_WINDOWSBUILD\LocaNextProject\LocaNext; node inspect_dom.js"

# 4. Click button
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command "cd C:\NEIL_PROJECTS_WINDOWSBUILD\LocaNextProject\LocaNext; node click_button.js 'Create dictionary'"

# 5. Check logs
tail -30 "/mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/LocaNext/logs/locanext_app.log"
```

---

---

## 🧪 Automated Test Scripts

Pre-built test scripts in `C:\NEIL_PROJECTS_WINDOWSBUILD\LocaNextProject\LocaNext\`:

### Run Complete App Verification
```bash
# Kill any existing instances, launch app, run test
/mnt/c/Windows/System32/taskkill.exe /F /IM LocaNext.exe 2>/dev/null; sleep 2
cd /mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/LocaNext && ./LocaNext.exe --remote-debugging-port=9222 &
sleep 15
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command "cd C:\\Users\\MYCOM\\Desktop\\LocaNext; node complete_test.js"
```

### Available Test Scripts

```
C:\NEIL_PROJECTS_WINDOWSBUILD\LocaNextProject\LocaNext\
├── full_stack_test.js ─── Full Stack: API + WebSocket + Task Manager (12 tests)
├── complete_test.js ───── App verification (6 tests)
├── tasks_test.js ──────── Task Manager UI (8 tests)
├── final_test.js ──────── Navigation + buttons (5 tests)
├── inspect_dom.js ─────── Debug DOM state
└── click_button.js ────── Click specific button
```

| Script | Tests | Purpose |
|--------|-------|---------|
| `full_stack_test.js` | 12 | Backend API, WebSocket, Task Manager, Telemetry |
| `complete_test.js` | 6 | Full app verification |
| `tasks_test.js` | 8 | Task manager verification |
| `final_test.js` | 5 | Navigation + buttons |
| `inspect_dom.js` | - | Debug DOM state |
| `click_button.js` | - | Click specific button |

---

## 🔴 CRITICAL: +error.svelte Workaround

**When adding a new app, you MUST add it to BOTH files:**

1. `locaNext/src/routes/+page.svelte` - Normal SvelteKit routing
2. `locaNext/src/routes/+error.svelte` - Electron file:// workaround

**Why?** In Electron with file:// protocol, SvelteKit router fails and falls back to +error.svelte.
If your app isn't in +error.svelte, it will show Welcome instead!

```svelte
<!-- +error.svelte - MUST have all apps! -->
<script>
  import XLSTransfer from "$lib/components/apps/XLSTransfer.svelte";
  import QuickSearch from "$lib/components/apps/QuickSearch.svelte";
  import KRSimilar from "$lib/components/apps/KRSimilar.svelte";  // ← ADD NEW APPS HERE TOO!
</script>

{#if app === 'xlstransfer'}
  <XLSTransfer />
{:else if app === 'quicksearch'}
  <QuickSearch />
{:else if app === 'krsimilar'}
  <KRSimilar />  <!-- ← AND HERE! -->
{:else}
  <Welcome />
{/if}
```

---

## 📦 Deploy Build from WSL to Windows

After making changes and rebuilding:

```bash
# 1. Build the frontend
cd /home/neil1988/LocalizationTools/locaNext
npm run build

# 2. Copy to Windows app
cp -r build/* "/mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/LocaNext/resources/app/build/"

# 3. Restart app to test
/mnt/c/Windows/System32/taskkill.exe /F /IM LocaNext.exe 2>/dev/null
cd /mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/LocaNext && ./LocaNext.exe --remote-debugging-port=9222 &
```

---

## ✅ Test Results (2025-12-05)

```
Test Coverage Tree
│
├── 🔌 Backend API (4/4)
│   ├── ✓ /health endpoint
│   ├── ✓ /api/auth/login
│   ├── ✓ /api/progress/operations
│   └── ✓ /api/v1/remote-logs/frontend
│
├── 🖥️ UI Components (6/6)
│   ├── ✓ XLSTransfer Container
│   ├── ✓ QuickSearch Container
│   ├── ✓ KR Similar Container
│   ├── ✓ Tasks Container + DataTable
│   ├── ✓ Refresh Button
│   └── ✓ Clear History Button
│
├── 🔗 WebSocket (3/3)
│   ├── ✓ Connection established
│   ├── ✓ Progress room subscription
│   └── ✓ Auth token in localStorage
│
├── 🧭 Navigation (4/4)
│   ├── ✓ Apps dropdown menu
│   ├── ✓ XLSTransfer → QuickSearch
│   ├── ✓ QuickSearch → KR Similar
│   └── ✓ Navigation Round-Trip
│
├── 📊 Telemetry (2/2)
│   ├── ✓ Remote logging endpoint
│   └── ✓ Frontend errors sent to backend
│
└── 🔐 Authentication (1/1)
    └── ✓ DEV auto-login as admin
```

**Total: 20/20 tests across all categories**

---

## 🔄 Data Flow (Verified)

```
Frontend (Svelte)
     │
     ├── API Calls → http://127.0.0.1:8888/api/*
     │   ├── /api/auth/login ✓
     │   ├── /api/progress/operations ✓
     │   └── /api/v1/remote-logs/frontend ✓
     │
     ├── WebSocket → http://localhost:8888/ws/socket.io
     │   ├── connect ✓
     │   ├── subscribe(progress) ✓
     │   └── operation_start, progress_update, operation_complete events
     │
     └── LocalStorage
         ├── auth_token ✓
         └── user info ✓

Backend (FastAPI)
     │
     ├── Database: PostgreSQL (central)
     │   ├── users table ✓
     │   ├── ldm_rows table ✓ (ALL text data)
     │   ├── log_entries table ✓
     │   └── PgBouncer: 1000 connections
     │
     ├── Local Storage (server/data/):
     │   ├── FAISS indexes (heavy, rebuildable)
     │   ├── Embeddings (.npy)
     │   └── ML models
     │
     └── Telemetry: Sent to central PostgreSQL
```

---

*Last updated: 2025-12-05 - Full stack tests, test coverage tree, data flow diagram*
