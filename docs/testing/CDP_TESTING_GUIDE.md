# CDP (Chrome DevTools Protocol) Testing Guide

**Purpose:** Autonomous testing of LocaNext Electron app via Chrome DevTools Protocol
**Last Updated:** 2025-12-17 | **Build:** 298

---

## ⚠️ CRITICAL: WSL2 Network Constraint

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║  WSL2 CANNOT ACCESS WINDOWS localhost:9222                                    ║
║                                                                               ║
║  ❌ WRONG: Running `node test.js` from WSL                                    ║
║  ✅ RIGHT: Run via PowerShell on Windows side                                 ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

**All CDP test scripts MUST run on Windows side.** Use PowerShell from WSL:

```bash
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command "
  cd C:\NEIL_PROJECTS_WINDOWSBUILD\LocaNextProject
  node test_script.js
"
```

---

## Overview

CDP allows automated testing of the Electron app without manual interaction. Tests can:
- Click elements, fill forms, navigate
- Intercept alerts/dialogs
- Check DOM state
- Verify WebSocket events
- Take screenshots

**Detailed documentation:** [testing_toolkit/cdp/README.md](../../testing_toolkit/cdp/README.md)

---

## Quick Start

### 1. Start App with CDP Enabled

```bash
# From WSL, launch Playground app via PowerShell
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command "
  Start-Process 'C:\NEIL_PROJECTS_WINDOWSBUILD\LocaNextProject\Playground\LocaNext\LocaNext.exe' -ArgumentList '--remote-debugging-port=9222'
"
```

### 2. Run a Test (MUST use PowerShell)

```bash
# From WSL - run on Windows side
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command "
  cd C:\NEIL_PROJECTS_WINDOWSBUILD\LocaNextProject
  node quick_check.js
"
```

---

## Test Scripts & Toolkit

### CDP Testing Toolkit

Organized test scripts in `testing_toolkit/cdp/`:

```
testing_toolkit/cdp/
├── README.md                          ← Hub with navigation map, selectors
├── utils/cdp-client.js                ← Reusable CDP client
└── tests/
    ├── login/cdp_login.js             ← Auto-login
    ├── navigation/quick_check.js      ← Page state check
    └── tm-viewer/
        ├── check_tm_status.js         ← List TMs with status
        ├── test_tm_viewer_final.js    ← TM Viewer test
        └── explore_entries_table.js   ← Debug viewer structure
```

### Windows Side Scripts

Test scripts run from `C:\NEIL_PROJECTS_WINDOWSBUILD\LocaNextProject\`:

| Script | Purpose |
|--------|---------|
| `quick_check.js` | Page state, test interfaces |
| `cdp_login.js` | Auto-login as neil/neil |
| `check_tm_status.js` | List TMs with status |
| `test_tm_viewer_final.js` | TM Manager & Viewer test |

---

## Test Template

```javascript
const WebSocket = require('ws');
const http = require('http');

http.get('http://localhost:9222/json', (res) => {
    let data = '';
    res.on('data', chunk => data += chunk);
    res.on('end', () => {
        const targets = JSON.parse(data);
        const page = targets.find(t => t.type === 'page');
        const ws = new WebSocket(page.webSocketDebuggerUrl);
        let id = 1;

        ws.on('open', async () => {
            console.log('=== TEST NAME ===');

            // Enable Page events (for alerts)
            await send(ws, id++, 'Page.enable', {});
            await send(ws, id++, 'Runtime.enable', {});

            // Intercept alert() calls
            await send(ws, id++, 'Runtime.evaluate', {
                expression: `
                    window.__alertMessages = [];
                    window.alert = function(msg) {
                        window.__alertMessages.push(msg);
                    };
                `,
                returnByValue: true
            });

            // YOUR TEST STEPS HERE

            // Example: Click an element
            await send(ws, id++, 'Runtime.evaluate', {
                expression: `document.querySelector('.my-button')?.click()`,
                returnByValue: true
            });

            // Example: Check state
            const result = await send(ws, id++, 'Runtime.evaluate', {
                expression: `JSON.stringify({ found: document.querySelector('.expected') !== null })`,
                returnByValue: true
            });
            console.log(JSON.parse(result.result?.result?.value || '{}'));

            // Check intercepted alerts
            const alerts = await send(ws, id++, 'Runtime.evaluate', {
                expression: `JSON.stringify(window.__alertMessages || [])`,
                returnByValue: true
            });
            console.log('Alerts:', JSON.parse(alerts.result?.result?.value || '[]'));

            ws.close();
            process.exit(0);
        });

        function send(ws, id, method, params) {
            return new Promise(resolve => {
                const timeout = setTimeout(() => resolve({ error: 'timeout' }), 10000);
                const handler = (data) => {
                    const msg = JSON.parse(data);
                    if (msg.id === id) {
                        clearTimeout(timeout);
                        ws.removeListener('message', handler);
                        resolve(msg);
                    }
                };
                ws.on('message', handler);
                ws.send(JSON.stringify({ id, method, params }));
            });
        }
    });
}).on('error', err => {
    console.log('HTTP Error:', err.message);
    process.exit(1);
});
```

---

## Common CDP Commands

### Execute JavaScript
```javascript
await send(ws, id++, 'Runtime.evaluate', {
    expression: `document.querySelector('.btn').click()`,
    returnByValue: true
});
```

### Get Page State
```javascript
const result = await send(ws, id++, 'Runtime.evaluate', {
    expression: `JSON.stringify({
        url: window.location.href,
        title: document.title,
        hasElement: document.querySelector('.target') !== null
    })`,
    returnByValue: true
});
```

### Take Screenshot
```javascript
await send(ws, id++, 'Page.enable', {});
const screenshot = await send(ws, id++, 'Page.captureScreenshot', { format: 'png' });
fs.writeFileSync('screenshot.png', Buffer.from(screenshot.result.data, 'base64'));
```

### Intercept Alerts
```javascript
// Monkey-patch alert before test
await send(ws, id++, 'Runtime.evaluate', {
    expression: `
        window.__alertMessages = [];
        window.alert = function(msg) {
            window.__alertMessages.push(msg);
        };
    `,
    returnByValue: true
});

// After test, check alerts
const alerts = await send(ws, id++, 'Runtime.evaluate', {
    expression: `JSON.stringify(window.__alertMessages)`,
    returnByValue: true
});
```

### Double-Click Element
```javascript
await send(ws, id++, 'Runtime.evaluate', {
    expression: `
        const el = document.querySelector('.cell.target');
        const event = new MouseEvent('dblclick', { bubbles: true, cancelable: true, view: window });
        el.dispatchEvent(event);
    `,
    returnByValue: true
});
```

### Keyboard Testing: Focus Matters

Two ways to simulate keyboard input - they behave differently:

| Method | Level | Focus Required? |
|--------|-------|-----------------|
| `Runtime.evaluate` + `new KeyboardEvent()` | JavaScript | No - can target any element |
| `Input.dispatchKeyEvent` | Browser (real keys) | **YES** - goes to focused element |

**Real key simulation (Input.dispatchKeyEvent):**
```javascript
// IMPORTANT: Check/set focus FIRST
await send(ws, id++, 'Runtime.evaluate', {
    expression: `document.querySelector('.my-textarea').focus()`,
    returnByValue: true
});

// Then send keys - they go to focused element
await send(ws, id++, 'Input.dispatchKeyEvent', {
    type: 'keyDown', key: 'Control', code: 'ControlLeft', modifiers: 2
});
await send(ws, id++, 'Input.dispatchKeyEvent', {
    type: 'keyDown', key: 's', code: 'KeyS', modifiers: 2, text: 's'
});
await send(ws, id++, 'Input.dispatchKeyEvent', {
    type: 'keyUp', key: 's', code: 'KeyS', modifiers: 2
});
await send(ws, id++, 'Input.dispatchKeyEvent', {
    type: 'keyUp', key: 'Control', code: 'ControlLeft', modifiers: 0
});
```

**JS-level events (can target directly):**
```javascript
await send(ws, id++, 'Runtime.evaluate', {
    expression: `
        const el = document.querySelector('.my-textarea');
        const event = new KeyboardEvent('keydown', {
            key: 's', code: 'KeyS', ctrlKey: true,
            bubbles: true, cancelable: true
        });
        el.dispatchEvent(event);
    `,
    returnByValue: true
});
```

**When to use which:**
- `Input.dispatchKeyEvent` - Testing real user behavior, Electron shortcuts
- `Runtime.evaluate` + KeyboardEvent - Quick tests, when focus is complex

**Common gotcha:** If `Input.dispatchKeyEvent` seems to do nothing, check `document.activeElement` - focus is probably wrong.

---

## Server Log Correlation

When running CDP tests, check server logs for backend activity:

```bash
# In another terminal
tail -f /tmp/locatools_server.log | grep -i "ldm\|lock\|websocket\|error"
```

This helps correlate frontend actions with backend responses.

---

## WSL <-> Windows Considerations

### Network Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      WINDOWS HOST                           │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  LocaNext.exe (Electron)                            │   │
│  │  └── CDP: localhost:9222  ←── Only Windows can access│   │
│  └─────────────────────────────────────────────────────┘   │
│                           │                                 │
│                           │ HTTP (works both ways)         │
│                           ↓                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  WSL2                                               │   │
│  │  └── Backend: localhost:8888                        │   │
│  │  └── Test scripts: testing_toolkit/cdp/             │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Key Constraints

| From | To | Works? |
|------|-----|--------|
| WSL | `localhost:8888` (backend) | ✅ Yes |
| Windows | `localhost:8888` (backend) | ✅ Yes |
| WSL | `localhost:9222` (CDP) | ❌ **NO** |
| Windows | `localhost:9222` (CDP) | ✅ Yes |

### Running CDP Tests

```bash
# WRONG - Won't work from WSL
node test.js  # Error: ECONNREFUSED 127.0.0.1:9222

# CORRECT - Run on Windows side via PowerShell
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command "
  cd C:\NEIL_PROJECTS_WINDOWSBUILD\LocaNextProject
  node test.js
"
```

---

## Test Types: Normal vs Detailed

### Normal Tests (Quick)
- **Purpose:** Quick pass/fail verification
- **Logging:** Key steps only
- **Use when:** Running CI/CD, quick sanity checks
- **Example:** `test_full_flow.js`

```
[4/8] Checking for projects...
   Found 5 project(s)
   Selecting first project: Test Project LDM
```

### Detailed Tests (Verbose)
- **Purpose:** Deep debugging, finding exact failure point
- **Logging:** Every DOM query, click coordinates, timing, console messages
- **Use when:** Debugging failures, understanding behavior
- **Example:** `test_full_flow_detailed.js`

```
[  1234ms] ═══ STEP 4: Select Project ═══
[  1235ms]   → DOM Query: ".project-item" (Project items)
[  1240ms]   → Found 5 element(s), first: <BUTTON>
[  1241ms] ✓ Found 5 project(s)
[  1242ms]   → Click: ".project-item" (First project)
[  1250ms] ✓ Clicked <BUTTON> at (145, 203) - "Test Project LDM"
```

---

## Test Categories

### 1. Page State Tests
- Check if components loaded
- Verify DOM structure
- List available buttons/elements

### 2. Interaction Tests
- Click buttons, expand trees
- Fill forms, submit
- Double-click cells for edit

### 3. WebSocket Tests
- Verify lock acquisition
- Check real-time updates
- Test presence tracking

### 4. Error Handling Tests
- Test with server down
- Test with invalid data
- Check error messages

### 5. Full Flow Tests (E2E)
- Complete user journeys
- Project → File → Edit → Save
- Login → Navigate → Interact

---

## Debugging Tips

1. **Element not found**: Use `find_buttons.js` or `debug_dom.js` to discover actual class names
2. **Click not working**: Check if element is visible (`el.offsetParent !== null`)
3. **Alert not captured**: Make sure to patch `window.alert` BEFORE the action
4. **Timeout**: Increase wait time or check server logs

---

## Best Practices

1. **Always intercept alerts** - Native alerts block execution
2. **Add wait times** - UI needs time to render
3. **Check server logs** - Correlate frontend/backend
4. **Use JSON.stringify** - For returning complex data from evaluate
5. **Test incrementally** - Start with page state, then add interactions

---

---

## Related Documentation

| Doc | Purpose |
|-----|---------|
| [testing_toolkit/cdp/README.md](../../testing_toolkit/cdp/README.md) | CDP toolkit hub with selectors, navigation map |
| [PLAYGROUND_INSTALL_PROTOCOL.md](PLAYGROUND_INSTALL_PROTOCOL.md) | Install app to Playground |
| [DEBUG_AND_TEST_HUB.md](DEBUG_AND_TEST_HUB.md) | Master testing guide |

---

*Updated: 2025-12-17 | Build 298 verified | Part of LocaNext testing infrastructure*
