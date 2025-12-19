# CDP Testing - LocaNext Windows App

**Purpose:** Automated testing of LocaNext.exe via Chrome DevTools Protocol
**Updated:** 2025-12-19 | **Build:** 300

---

## How It Works

```
LocaNext.exe --remote-debugging-port=9222
       ↓
   CDP (port 9222)
       ↓
   Node.js scripts (ws + http)
       ↓
   WebSocket → Runtime.evaluate → DOM interaction
```

All tests are **pure Node.js** using `ws` and `http` modules. No Playwright. No PowerShell wrappers.

**WSL ↔ Windows:** Ports are shared. WSL's `127.0.0.1:9222` reaches the Windows app.

---

## Quick Start

### From Windows (CMD/PowerShell)

```cmd
REM 1. Launch app with CDP
cd C:\NEIL_PROJECTS_WINDOWSBUILD\LocaNextProject\Playground\LocaNext
LocaNext.exe --remote-debugging-port=9222

REM 2. Run test (new terminal)
cd C:\path\to\LocalizationTools\testing_toolkit\cdp
node test_bug029.js
```

### From WSL

```bash
# 1. Launch app (from WSL, runs on Windows)
cd /mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/Playground/LocaNext
./LocaNext.exe --remote-debugging-port=9222 &

# 2. Wait for startup
sleep 30

# 3. Run test
cd /home/neil1988/LocalizationTools/testing_toolkit/cdp
node test_bug029.js
```

---

## Test Scripts

| Script | Purpose |
|--------|---------|
| `quick_check.js` | Page state, URL, available test interfaces |
| `test_bug023.js` | TM status check (pending vs ready) |
| `test_bug023_build.js` | Trigger TM index build, check for errors |
| `test_bug029.js` | Right-click "Upload as TM" flow |
| `test_clean_slate.js` | Clear TMs and check file state |
| `test_server_status.js` | Server status panel, TM build buttons |

---

## Test Pattern

Every test follows this structure:

```javascript
const WebSocket = require('ws');
const http = require('http');

const sleep = ms => new Promise(r => setTimeout(r, ms));

async function main() {
    // 1. Get CDP targets
    const targets = await new Promise((resolve, reject) => {
        http.get('http://127.0.0.1:9222/json', (res) => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => resolve(JSON.parse(data)));
        }).on('error', reject);
    });

    // 2. Connect to page
    const page = targets.find(t => t.type === 'page');
    const ws = new WebSocket(page.webSocketDebuggerUrl);

    // 3. Helper to send CDP commands
    let id = 1;
    const send = (method, params = {}) => new Promise((resolve) => {
        const msgId = id++;
        ws.on('message', function handler(data) {
            const msg = JSON.parse(data.toString());
            if (msg.id === msgId) {
                ws.off('message', handler);
                resolve(msg);
            }
        });
        ws.send(JSON.stringify({ id: msgId, method, params }));
    });

    // 4. Helper to evaluate JS in page
    const evaluate = async (expression) => {
        const result = await send('Runtime.evaluate', {
            expression,
            returnByValue: true,
            awaitPromise: true
        });
        return result.result?.result?.value;
    };

    // 5. Wait for connection
    await new Promise(resolve => ws.on('open', resolve));

    // 6. Your test code
    const pageText = await evaluate('document.body.innerText.substring(0, 500)');
    console.log('Page:', pageText);

    // 7. Cleanup
    ws.close();
}

main().catch(console.error);
```

---

## Common Operations

### Click a button
```javascript
await evaluate(`
    const btn = Array.from(document.querySelectorAll('button'))
        .find(b => b.textContent.includes('Files'));
    if (btn) btn.click();
`);
```

### Right-click (context menu)
```javascript
await evaluate(`
    const el = document.querySelector('.tree-node');
    const event = new MouseEvent('contextmenu', {
        bubbles: true,
        cancelable: true,
        clientX: 100,
        clientY: 100,
        button: 2
    });
    el.dispatchEvent(event);
`);
```

### Wait for element
```javascript
async function waitFor(selector, timeout = 10000) {
    const start = Date.now();
    while (Date.now() - start < timeout) {
        const exists = await evaluate(`!!document.querySelector('${selector}')`);
        if (exists) return true;
        await sleep(200);
    }
    return false;
}
```

### Get element text
```javascript
const text = await evaluate(`
    document.querySelector('.tm-item')?.innerText || 'not found'
`);
```

### Check for errors
```javascript
const hasError = await evaluate(`
    document.body.innerText.includes('Error') ||
    document.body.innerText.includes('NameError')
`);
```

### Take screenshot
```javascript
const result = await send('Page.captureScreenshot', { format: 'png' });
require('fs').writeFileSync('screenshot.png', Buffer.from(result.result.data, 'base64'));
```

---

## Element Selectors

### Navigation
| Element | Selector |
|---------|----------|
| Files Tab | `button` with text "Files" |
| TM Tab | `button` with text "TM" |
| Settings Tab | `button` with text "Settings" |

### File Explorer
| Element | Selector |
|---------|----------|
| Project Item | `.project-item` |
| Tree Node | `.tree-node` |
| Context Menu | `.context-menu` |
| Menu Item | `.context-menu-item` |

### TM Manager
| Element | Selector |
|---------|----------|
| TM Item | `.tm-item` |
| Status Badge | `.badge`, `[class*="status"]` |

### Modals
| Element | Selector |
|---------|----------|
| Visible Modal | `.bx--modal.is-visible` |
| Modal Heading | `.bx--modal-header__heading` |
| Primary Button | `.bx--btn--primary` |

---

## Windows-Specific Testing

### Running Tests Directly on Windows

Node.js works the same on Windows. From CMD or PowerShell:

```cmd
REM Install ws module (one time)
cd C:\path\to\LocalizationTools\testing_toolkit\cdp
npm install ws

REM Run any test
node test_bug029.js
```

### Process Management (Windows)

```cmd
REM Kill existing LocaNext processes
taskkill /F /IM LocaNext.exe /T

REM Launch with CDP
cd C:\NEIL_PROJECTS_WINDOWSBUILD\LocaNextProject\Playground\LocaNext
start "" LocaNext.exe --remote-debugging-port=9222

REM Check CDP is responding
curl http://127.0.0.1:9222/json
```

### Process Management (WSL → Windows)

```bash
# Kill existing (use full path)
/mnt/c/Windows/System32/taskkill.exe /F /IM "LocaNext.exe" /T

# Launch (runs on Windows, controlled from WSL)
cd /mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/Playground/LocaNext
./LocaNext.exe --remote-debugging-port=9222 &

# Verify
curl -s http://127.0.0.1:9222/json | head -20
```

### Windows Paths

| What | Windows Path | WSL Path |
|------|--------------|----------|
| Playground App | `C:\NEIL_PROJECTS_WINDOWSBUILD\LocaNextProject\Playground\LocaNext` | `/mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/Playground/LocaNext` |
| Test Files | `D:\TestFilesForLocaNext` | `/mnt/d/TestFilesForLocaNext` |
| CDP Scripts | `testing_toolkit\cdp\` | `testing_toolkit/cdp/` |
| App Logs | `%LOCALAPPDATA%\LocaNext\logs\` | `/mnt/c/Users/.../AppData/Local/LocaNext/logs/` |

### TEST MODE (Skip File Dialogs)

The app exposes test functions that bypass native file dialogs:

```javascript
// Available on window object
window.xlsTransferTest.createDictionary()  // Uses test file
window.xlsTransferTest.getStatus()         // Returns {isProcessing, statusMessage, ...}
window.quickSearchTest.loadDictionary()
window.krSimilarTest.search()
```

Test files location: `D:\TestFilesForLocaNext\`

---

## Troubleshooting

### "No page found"
App not running or CDP not enabled:
```cmd
LocaNext.exe --remote-debugging-port=9222
```

### Connection refused
Port 9222 not listening. Check app is running with CDP flag.

### WebSocket error
Multiple connections to same target. Close other DevTools windows.

### Test timeout
- App stuck on login screen → Login first manually
- Slow machine → Increase sleep() times in test

### "ws module not found"
```bash
cd testing_toolkit/cdp && npm install ws
```

### Port 9222 already in use
```bash
# WSL
fuser -k 9222/tcp

# Windows
netstat -ano | findstr :9222
taskkill /PID <pid> /F
```

---

## Other Testing Methods

### Backend API (pytest)
```bash
python -m pytest tests/unit/ tests/integration/ -v
```

### Playwright (Dev Server)
For testing against localhost:5173 during development:
```bash
cd locaNext && npm test
```

---

## File Locations

| What | Path |
|------|------|
| CDP Tests | `testing_toolkit/cdp/*.js` |
| Playwright Tests | `locaNext/tests/*.spec.ts` |
| Backend Tests | `tests/unit/`, `tests/integration/` |
| Playground App | `C:\...\Playground\LocaNext\LocaNext.exe` |

---

*Last updated: 2025-12-19 | Pure Node.js CDP testing for Windows*
