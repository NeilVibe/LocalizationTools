# Node.js CDP Testing - LocaNext

**Testing via Chrome DevTools Protocol + Playwright headless browser automation.**

**Updated:** 2025-12-27 | **Philosophy:** ALWAYS CHOOSE HARD

---

## Testing Philosophy: ALWAYS CHOOSE HARD

Between EASY/MEDIUM/HARD approaches, we ALWAYS choose HARD:

| Approach | Result |
|----------|--------|
| **EASY** | Quick fix, breaks later, technical debt, embarrassing |
| **HARD** | Proper fix, survives forever, professional, verified |

**Example from 2025-12-27:**
- EASY: `overflow: visible` → Broke virtual scroll (480,000px container!)
- HARD: `overflow: hidden` + `min-height: 0` + flexbox → Perfect 847px container

**Every fix MUST be verified with automated tests. No assumptions.**

---

## CRITICAL: Run Tests from Windows, NOT WSL

**LocaNext is a Windows app.** CDP binds to Windows `127.0.0.1:9222`. WSL2 cannot reach Windows localhost.

```
✅ Windows PowerShell  →  127.0.0.1:9222  →  WORKS
❌ WSL curl/node       →  127.0.0.1:9222  →  Connection refused
```

**Always run CDP tests from Windows PowerShell:**
```powershell
Push-Location '\\wsl.localhost\Ubuntu2\home\neil1988\LocalizationTools\testing_toolkit\cdp'
node quick_check.js
```

---

## Two Testing Modes

### Mode 1: CDP for Windows App (Production Testing)

```
LocaNext.exe --remote-debugging-port=9222
       ↓
   CDP (port 9222) - WINDOWS LOCALHOST ONLY
       ↓
   Node.js scripts (ws + http) - RUN FROM WINDOWS
       ↓
   WebSocket → Runtime.evaluate → DOM interaction
```

### Mode 2: Playwright Headless for Dev Server (Instant Testing)

```
npm run dev (localhost:5173)
       ↓
   Playwright (headless Chromium)
       ↓
   Page interactions + Screenshots + DOM queries
       ↓
   INSTANT verification with visual evidence
```

**Playwright Headless Benefits:**
- Runs from WSL (no Windows dependency)
- Takes screenshots at every step
- Tests both API endpoints + UI components
- Instant feedback during development
- Automated visual regression testing

**Example: verify_ui_fixes.js**
```bash
cd testing_toolkit/cdp
node verify_ui_fixes.js
```

Output:
```
✓ UI-051 PASS: Modal close button works
✓ UI-052 PASS: TM suggest endpoint works
✓ UI-053 PASS: Scroll container 847px (was 480,000px!)
✓ UI-074 PASS: Files endpoint returns array
Screenshots: /tmp/verify_*.png
```

---

## Quick Start

### Step 1: Launch App with CDP (from WSL)

```bash
# Kill existing and launch fresh
/mnt/c/Windows/System32/taskkill.exe /F /IM "LocaNext.exe" /T 2>/dev/null
cd /mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/Playground/LocaNext
./LocaNext.exe --remote-debugging-port=9222 &
sleep 10
```

### Step 2: Run Tests (from Windows PowerShell)

```powershell
# Access test scripts via UNC path (reaches WSL filesystem)
Push-Location '\\wsl.localhost\Ubuntu2\home\neil1988\LocalizationTools\testing_toolkit\cdp'

# Login first (if at login screen)
node login.js

# Run tests
node quick_check.js
node test_server_status.js
node test_bug029.js
```

### Alternative: All from Windows

```cmd
REM 1. Launch app
cd C:\NEIL_PROJECTS_WINDOWSBUILD\LocaNextProject\Playground\LocaNext
start "" LocaNext.exe --remote-debugging-port=9222

REM 2. Wait, then run tests
timeout 10
cd D:\LocalizationTools\testing_toolkit\cdp
node login.js
node quick_check.js
```

---

## Test Scripts

### Master Runner
```powershell
# Run ALL tests in sequence
$env:CDP_TEST_USER="user"; $env:CDP_TEST_PASS="pass"
node run_all_tests.js           # Full suite
node run_all_tests.js --quick   # Essential tests only
node run_all_tests.js --verbose # Show all output
```

### Individual Tests

| Script | Category | Purpose |
|--------|----------|---------|
| **Essential** | | |
| `login.js` | auth | Login via CDP (requires env credentials) |
| `quick_check.js` | debug | Page state, URL, test interfaces |
| **Core Functionality** | | |
| `test_qa.js` | qa | Basic QA check |
| `test_qa_comprehensive.js` | qa | Full QA with console monitoring |
| `create_project_upload.js` | files | Create project + upload |
| `upload_file.js` | files | File upload test |
| `test_file_download.js` | files | File/TM download test |
| **TM Tests** | | |
| `test_full_tm_sync.js` | tm | End-to-end TM sync |
| `test_auto_sync.js` | tm | Auto-sync functionality |
| `test_ui047_tm_status.js` | tm | TM status display |
| **Bug Verification** | | |
| `test_bug023_build.js` | bugs | Bug 023 - TM index build |
| `test_bug029.js` | bugs | Bug 029 - Upload as TM |
| `test_clean_slate.js` | cleanup | Reset state |
| **UI Verification** | | |
| `verify_ui031_ui032.js` | ui | Font size/bold |
| `verify_ui034_tooltips.js` | ui | Tooltip alignment |
| `verify_ui027_no_confirm.js` | ui | Confirm button removal |
| **Debug Utilities** | | |
| `check_all_settings.js` | debug | Settings panel |
| `check_console_errors.js` | debug | Console error capture |
| `check_network.js` | debug | Network monitoring |
| `debug_websocket.js` | debug | WebSocket debugging |

### Archived (Duplicates)
Duplicate/stale tests moved to `archived_duplicates/`:
- `test_font_settings.js` → replaced by `verify_ui031_ui032.js`
- `verify_font_fix.js` → replaced by `verify_ui031_ui032.js`
- `test_bug023.js` → replaced by `test_bug023_build.js`
- `check_server_status.js` → replaced by `test_server_status.js`
- `check_display_settings.js` → replaced by `check_all_settings.js`
- `tests/` subfolder → had hardcoded credentials (security issue)

### Credential Security (Build 880+)

**login.js requires environment variables - no hardcoded credentials!**

```bash
# For local testing
export CDP_TEST_USER=your_username
export CDP_TEST_PASS=your_password
node login.js

# For CI - uses Gitea secrets automatically
# CI_TEST_USER → CDP_TEST_USER
# CI_TEST_PASS → CDP_TEST_PASS
```

| Mode | Credentials From |
|------|------------------|
| CI (Gitea) | Gitea secrets (CI_TEST_USER, CI_TEST_PASS) |
| Local dev | Environment variables (CDP_TEST_USER, CDP_TEST_PASS) |

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

# Verify CDP is listening (use Windows curl, NOT WSL curl!)
/mnt/c/Windows/System32/curl.exe -s http://127.0.0.1:9222/json
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

## Related Docs

| Doc | Purpose |
|-----|---------|
| [MASTER_TEST_PROTOCOL.md](../MASTER_TEST_PROTOCOL.md) | Complete Build → Install → Test workflow |
| [PLAYGROUND_INSTALL_PROTOCOL.md](../../docs/testing/PLAYGROUND_INSTALL_PROTOCOL.md) | Detailed Playground install process |
| [../README.md](../README.md) | Testing toolkit overview |

---

*Last updated: 2025-12-25 | Pure Node.js CDP testing for Windows + CI Integration*
