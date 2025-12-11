# CDP (Chrome DevTools Protocol) Testing Guide

**Purpose:** Autonomous testing of LocaNext Electron app via Chrome DevTools Protocol
**Last Updated:** 2025-12-12

---

## Overview

CDP allows automated testing of the Electron app without manual interaction. Tests can:
- Click elements, fill forms, navigate
- Intercept alerts/dialogs
- Check DOM state
- Verify WebSocket events
- Take screenshots

---

## Quick Start

### 1. Start App with CDP Enabled

```bash
# From WSL, launch app via PowerShell
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command "
Start-Process 'C:\\NEIL_PROJECTS_WINDOWSBUILD\\LocaNextProject\\LocaNext\\LocaNext.exe' -ArgumentList '--remote-debugging-port=9222'
"
```

### 2. Run a Test

```bash
cd C:\NEIL_PROJECTS_WINDOWSBUILD\LocaNextProject
node test_edit_final.js
```

---

## Test File Location

Test files are stored on Windows for CDP access:
```
C:\NEIL_PROJECTS_WINDOWSBUILD\LocaNextProject\
├── test_edit_final.js      # BUG-002 lock fix test
├── test_lock_simple.js     # Simple lock check
├── check_page.js           # Page state check
├── find_buttons.js         # DOM button discovery
├── debug_dom.js            # DOM class analysis
└── test_ldm_full.js        # Full LDM test suite
```

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

- WSL localhost != Windows localhost
- CDP runs on Windows (port 9222)
- Backend runs in WSL (port 8888)
- App connects to WSL backend via localhost:8888 (works because Docker/WSL networking)

**Run tests from Windows side:**
```bash
# From WSL
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command "cd C:\\NEIL_PROJECTS_WINDOWSBUILD\\LocaNextProject; node test.js"
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

*Created: 2025-12-12 | Part of LocaNext testing infrastructure*
