# CDP Testing Toolkit

**Purpose:** Chrome DevTools Protocol testing for LocaNext Electron app
**Updated:** 2025-12-17 | **Tested:** Build 298

---

## Quick Start

```bash
# From WSL - Run on Windows side (REQUIRED - WSL can't access Windows localhost)
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command "
  cd C:\NEIL_PROJECTS_WINDOWSBUILD\LocaNextProject
  node quick_check.js
"
```

---

## Critical Constraints

| Constraint | Details |
|------------|---------|
| **WSL2 ↔ Windows** | WSL cannot access `localhost:9222`. Must run Node.js on Windows side. |
| **CDP Port** | 9222 (default). App must be launched with `--remote-debugging-port=9222` |
| **Scripts Location** | Run from `C:\NEIL_PROJECTS_WINDOWSBUILD\LocaNextProject\` |
| **ws Module** | Required: `npm install ws` in Windows project folder |

---

## Test Scripts

| Script | Purpose | Location |
|--------|---------|----------|
| `quick_check.js` | Page state check (login, interfaces) | Windows side |
| `cdp_login.js` | Auto-login as neil/neil | Windows side |
| `test_tm_viewer_final.js` | TM Manager & Viewer test | Windows side |
| `check_tm_status.js` | List all TMs with status | Windows side |
| `explore_entries_table.js` | Debug TM Viewer structure | Windows side |

### Running Tests

```bash
# Always run from WSL using PowerShell
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command "
  cd C:\NEIL_PROJECTS_WINDOWSBUILD\LocaNextProject
  node <script_name>.js
"
```

---

## UI Navigation Map

### LDM (Language Data Manager)

```
Login Page
│
├── [Login] → Main App
│   │
│   ├── Sidebar: Files | TM tabs
│   │
│   ├── [Files Tab] (default)
│   │   └── Project list → File grid
│   │
│   └── [TM Tab]
│       ├── TM List (tm-item buttons)
│       │   └── Select TM → "Open TM Manager" button appears
│       │
│       └── [Open TM Manager] → Modal with TM table
│           │
│           ├── Columns: Name | Entries | Languages | Status | Created
│           ├── Status: ready | indexing | error | pending
│           │
│           └── Row Actions:
│               ├── [View Entries] → TM Viewer Modal
│               ├── [Export TM]
│               ├── [Activate]
│               └── [Delete TM]

TM Viewer Modal (when View Entries clicked)
├── viewer-toolbar
│   ├── Metadata dropdown (StringID, Confirmed, etc.)
│   └── Search input
└── entries-table
    ├── Columns: Source | Target | Metadata | Actions
    └── Row Actions: Confirm | Edit | Delete
```

---

## Element Selectors

### Navigation

| Element | Selector |
|---------|----------|
| TM Tab | `button.tab-button` containing "TM" |
| Files Tab | `button.tab-button` containing "Files" |
| TM Item | `.tm-item` |
| Open TM Manager | `button` containing "Open TM Manager" |

### TM Manager Modal

| Element | Selector |
|---------|----------|
| TM Table | `table` inside `.tm-manager` |
| View Entries Button | `button` containing "View Entries" |
| TM Status Cell | `td:nth-child(4)` in table row |

### TM Viewer Modal

| Element | Selector |
|---------|----------|
| Viewer Container | `.tm-viewer` |
| Entries Table | `.entries-table` |
| Viewer Toolbar | `.viewer-toolbar` |
| Search Input | `input[placeholder*="Search"]` |
| Metadata Dropdown | `.bx--dropdown` or `.bx--list-box` |

### Global UI

| Element | Selector |
|---------|----------|
| Toast Container | `.global-toast-container` |
| Modal (visible) | `.bx--modal.is-visible` |
| Active Toasts | `[class*="toast"]:not([class*="container"])` |

---

## Test Interfaces

LocaNext exposes test interfaces on `window`:

| Interface | App | Available After |
|-----------|-----|-----------------|
| `navTest` | All | Login |
| `ldmTest` | LDM | Navigate to LDM |
| `xlsTransferTest` | XLS Transfer | Navigate to XLS Transfer |
| `quickSearchTest` | Quick Search | Navigate to Quick Search |
| `krSimilarTest` | KR Similar | Navigate to KR Similar |

Check availability:
```javascript
JSON.stringify({
    navTest: typeof window.navTest !== 'undefined',
    ldmTest: typeof window.ldmTest !== 'undefined',
    // ... etc
})
```

---

## CDP Patterns

### Basic Connection

```javascript
const WebSocket = require('ws');
const http = require('http');

// Get CDP target
const targets = await new Promise((resolve, reject) => {
    http.get('http://127.0.0.1:9222/json', (res) => {
        let data = '';
        res.on('data', chunk => data += chunk);
        res.on('end', () => resolve(JSON.parse(data)));
    }).on('error', reject);
});

const page = targets.find(t => t.type === 'page');
const ws = new WebSocket(page.webSocketDebuggerUrl);
```

### Evaluate JavaScript

```javascript
async function evaluate(expression) {
    const result = await send('Runtime.evaluate', {
        expression,
        returnByValue: true,
        awaitPromise: true
    });
    return result.result?.result?.value;
}

// Usage
const bodyText = await evaluate('document.body.innerText.substring(0, 200)');
```

### Click Element

```javascript
await evaluate(`
    const btn = document.querySelector('button.my-button');
    if (btn) btn.click();
`);
```

### Wait for Element

```javascript
async function waitFor(selector, timeout = 10000) {
    const start = Date.now();
    while (Date.now() - start < timeout) {
        const exists = await evaluate(`!!document.querySelector('${selector}')`);
        if (exists) return true;
        await new Promise(r => setTimeout(r, 200));
    }
    return false;
}
```

---

## TM Status Reference

| Status | Meaning | Can View Entries? |
|--------|---------|-------------------|
| `ready` | Indexed and ready | ✅ Yes |
| `active` | Currently in use | ✅ Yes |
| `indexing` | Building index | ❌ No (wait) |
| `pending` | Waiting to process | ❌ No |
| `error` | Processing failed | ❌ No |

---

## Troubleshooting

### WSL can't connect to CDP

```bash
# WRONG - Won't work from WSL
node test.js  # Error: ECONNREFUSED 127.0.0.1:9222

# CORRECT - Run on Windows side
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command "
  cd C:\NEIL_PROJECTS_WINDOWSBUILD\LocaNextProject
  node test.js
"
```

### CDP not responding

```bash
# Check if app is running
/mnt/c/Windows/System32/tasklist.exe | grep -i locanext

# Check CDP port
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command "
  Test-NetConnection -ComputerName localhost -Port 9222
"

# Restart app with CDP
/mnt/c/Windows/System32/taskkill.exe /F /IM "LocaNext.exe" /T
```

### No ws module

```bash
# Install on Windows side
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command "
  cd C:\NEIL_PROJECTS_WINDOWSBUILD\LocaNextProject
  npm install ws
"
```

### TM entries won't load

1. Check TM status (must be `ready` or `active`)
2. Check backend logs: `tail -f /tmp/locatools_server.log`
3. Try different TM

---

## File Locations

| What | Windows Path | WSL Path |
|------|--------------|----------|
| Playground App | `C:\...\Playground\LocaNext\` | `/mnt/c/.../Playground/LocaNext/` |
| Test Scripts | `C:\...\LocaNextProject\` | `/mnt/c/.../LocaNextProject/` |
| CDP Toolkit | N/A (WSL only) | `testing_toolkit/cdp/` |
| Backend Logs | N/A | `/tmp/locatools_server.log` |

---

## Related Docs

| Doc | Purpose |
|-----|---------|
| [PLAYGROUND_INSTALL_PROTOCOL.md](../../docs/testing/PLAYGROUND_INSTALL_PROTOCOL.md) | Install app to Playground |
| [CDP_TESTING_GUIDE.md](../../docs/testing/CDP_TESTING_GUIDE.md) | High-level CDP guide |
| [DEBUG_AND_TEST_HUB.md](../../docs/testing/DEBUG_AND_TEST_HUB.md) | Master testing guide |

---

*Last updated: 2025-12-17 - Build 298 verified*
