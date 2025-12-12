# Autonomous Testing Protocol

**Created:** 2025-12-07 | **Status:** Active Protocol

---

## Purpose

Enable Claude to **fully test any function in any app** without user interaction by:
1. Pre-hardcoded test files for every function
2. CDP commands that skip file dialogs
3. Multi-dimensional verification (CDP + Playwright + Console + Logs)

---

## Protocol Overview

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                    AUTONOMOUS TESTING PROTOCOL                                ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  Layer 1: TEST MODE (CDP)                                                    ║
║    └── window.{app}Test.{function}() → skips dialogs, uses test files        ║
║                                                                              ║
║  Layer 2: Playwright                                                         ║
║    └── Browser automation, screenshot comparison, UI assertions              ║
║                                                                              ║
║  Layer 3: DevTools Console                                                   ║
║    └── Error checking, log verification via CDP Runtime.evaluate             ║
║                                                                              ║
║  Layer 4: Backend Logs                                                       ║
║    └── /mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/LocaNext/logs/*.log - verify processing steps                  ║
║                                                                              ║
║  Layer 5: Output Verification                                                ║
║    └── Check generated files, database state, API responses                  ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

---

## DEV_MODE: Skip Authentication

**For autonomous API testing, use DEV_MODE:**

```bash
DEV_MODE=true python3 server/main.py
```

This enables:
- **Auto-auth on localhost** - No JWT token needed
- **Admin privileges** - Full access to all endpoints
- **curl without headers** - `curl http://localhost:8888/api/v2/...` just works

**Security:** Only works on 127.0.0.1 / ::1. Blocked if PRODUCTION=true.

**Example autonomous testing:**
```bash
# Start server with DEV_MODE
DEV_MODE=true python3 server/main.py &

# Test any endpoint without auth
curl http://localhost:8888/api/v2/admin/stats/overview
curl http://localhost:8888/api/v2/users
```

---

## Test Files Location

```
D:\TestFilesForLocaNext\
│
├── XLSTransfer/
│   ├── dict_source.xlsx          ← Create Dictionary (KR col A, EN col B)
│   ├── translate_target.xlsx     ← Translate Excel
│   ├── translate_text.txt        ← Transfer to Close
│   ├── check_newlines.xlsx       ← Check Newlines
│   └── combine_files/            ← Combine Excel (multiple files)
│
├── QuickSearch/
│   ├── search_source.txt         ← Main search file
│   ├── dictionary.xlsx           ← Dictionary for matching
│   └── xml_source.xml            ← XML search
│
├── KRSimilar/
│   ├── embeddings_source.xlsx    ← Build embeddings
│   └── search_query.txt          ← Similarity search
│
└── [Future Apps]/
    └── [function_specific_files]
```

**Requirement:** Each test file must be:
- Small enough for fast testing (< 1000 rows)
- Representative of real use cases
- Have expected columns/structure documented

---

## TEST MODE Implementation Pattern

Every app component should expose a `window.{app}Test` object:

```javascript
// In {App}.svelte
if (typeof window !== 'undefined') {
  window.{appName}Test = {
    // One function per app feature
    function1: () => testFunction1(),
    function2: () => testFunction2(),
    // Status getter
    getStatus: () => ({ isProcessing, statusMessage, ... })
  };
}

// Test function skips file dialog
async function testFunction1() {
  const testFile = TEST_CONFIG.function1.file;
  // Direct processing without dialog
  // ...
}
```

---

## App-Specific Test Functions

### XLSTransfer ✅ IMPLEMENTED

| Function | Test Command | Test File | Status |
|----------|--------------|-----------|--------|
| Create Dictionary | `window.xlsTransferTest.createDictionary()` | `GlossaryUploadTestFile.xlsx` | ✅ Working |
| Load Dictionary | `window.xlsTransferTest.loadDictionary()` | (uses created dict) | ✅ Working |
| Translate Excel | `window.xlsTransferTest.translateExcel()` | `150linetranslationtest.xlsx` | ✅ Working |
| Transfer to Close | `window.xlsTransferTest.transferToClose()` | `closetotest.txt` | ✅ Working |
| Get Status | `window.xlsTransferTest.getStatus()` | - | ✅ Working |

### QuickSearch ✅ IMPLEMENTED

| Function | Test Command | Description | Status |
|----------|--------------|-------------|--------|
| Load Dictionary | `window.quickSearchTest.loadDictionary()` | Loads BDO-EN dictionary | ✅ Working |
| Search | `window.quickSearchTest.search()` | Searches for "안녕하세요" | ✅ Working |
| Get Status | `window.quickSearchTest.getStatus()` | Returns state | ✅ Working |

### KR Similar ✅ IMPLEMENTED

| Function | Test Command | Description | Status |
|----------|--------------|-------------|--------|
| Load Dictionary | `window.krSimilarTest.loadDictionary()` | Loads BDO embeddings | ✅ Working |
| Search Similar | `window.krSimilarTest.search()` | Finds similar Korean texts | ✅ Working |
| Get Status | `window.krSimilarTest.getStatus()` | Returns state | ✅ Working |

---

## Multi-Dimensional Test Flow

```bash
# ════════════════════════════════════════════════════════════════
# COMPLETE AUTONOMOUS TEST CYCLE
# ════════════════════════════════════════════════════════════════

# ─── PHASE 1: Setup ───
/mnt/c/Windows/System32/taskkill.exe /F /IM LocaNext.exe 2>&1 || true
sleep 3
rm -f /mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/LocaNext/logs/*.log

# ─── PHASE 2: Launch ───
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe \
  -Command "Start-Process -FilePath 'D:\LocaNext\LocaNext.exe' -ArgumentList '--remote-debugging-port=9222'"
sleep 25

# ─── PHASE 3: Verify Launch ───
# 3a. Process count
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe \
  -Command "(Get-Process LocaNext -ErrorAction SilentlyContinue).Count"

# 3b. Backend health
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe \
  -Command "(Invoke-WebRequest -Uri 'http://localhost:8888/health' -UseBasicParsing).Content"

# 3c. CDP available
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe \
  -Command "(Invoke-WebRequest -Uri 'http://localhost:9222/json' -UseBasicParsing).Content"

# ─── PHASE 4: Run TEST MODE ───
# Execute via CDP (example: create dictionary)
node /mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/LocaNext/test_scripts/run_test.js createDictionary

# ─── PHASE 5: Multi-Dimensional Verification ───
# 5a. Check status via CDP
node /mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/LocaNext/test_scripts/check_status.js

# 5b. Check console errors via CDP
node /mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/LocaNext/test_scripts/check_console.js

# 5c. Check backend logs
tail -50 /mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/LocaNext/logs/locanext_app.log | grep -E "(ERROR|SUCCESS|FAIL)"

# 5d. Check output files (if applicable)
ls -la /mnt/d/TestFilesForLocaNext/output/

# ─── PHASE 6: Cleanup ───
/mnt/c/Windows/System32/taskkill.exe /F /IM LocaNext.exe
```

---

## CDP Console Error Checker

```javascript
// check_console.js - Check for frontend errors
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
        // Get console errors
        const result = await send('Runtime.evaluate', {
            expression: `
                (function() {
                    const errors = [];
                    // Check if any error was logged
                    if (window.__consoleErrors) {
                        return JSON.stringify(window.__consoleErrors);
                    }
                    return '[]';
                })()
            `,
            returnByValue: true
        });

        const errors = JSON.parse(result.result.value);
        if (errors.length > 0) {
            console.log('ERRORS FOUND:', errors);
            process.exit(1);
        } else {
            console.log('NO ERRORS');
            process.exit(0);
        }
    });
}
main();
```

---

## Playwright Integration

For UI state verification beyond CDP:

```javascript
// playwright_verify.js
const { chromium } = require('playwright');

async function verify() {
    const browser = await chromium.connectOverCDP('http://localhost:9222');
    const contexts = browser.contexts();
    const page = contexts[0].pages()[0];

    // Check UI state
    const hasError = await page.$('.bx--toast-notification--error');
    const hasSuccess = await page.$('.bx--toast-notification--success');
    const statusText = await page.$eval('.status-container', el => el?.textContent || 'none');

    console.log({
        hasError: !!hasError,
        hasSuccess: !!hasSuccess,
        statusText
    });

    await browser.close();
}
verify();
```

---

## Test File Requirements

### For Dictionary Creation (XLSTransfer)

Excel file structure:
```
| A (Korean)        | B (Translation)   |
|-------------------|-------------------|
| 안녕하세요         | Hello             |
| 감사합니다         | Thank you         |
| ...               | ...               |
```

- Column A: Korean text (source)
- Column B: Translation (target)
- No empty rows in data range
- Sheet name: Sheet1 (or specify in TEST_CONFIG)

### For QuickSearch

Text file:
```
Line 1: Korean text here
Line 2: More text
...
```

### For KR Similar

Excel with Korean text for embedding:
```
| A (Korean Text)   |
|-------------------|
| 문장 1            |
| 문장 2            |
```

---

## Success Criteria

A test is PASSED when:
1. `getStatus().isProcessing === false`
2. `getStatus().statusMessage` contains "success" or expected completion message
3. No errors in console (`check_console.js` returns 0)
4. Backend logs show expected milestones
5. Output files created (if applicable)

A test is FAILED when:
1. `getStatus().statusMessage` contains "error" or "failed"
2. Console has errors
3. Backend logs show exceptions
4. Process times out

---

## Adding TEST MODE to New Apps

When creating a new app, follow this pattern:

1. **Define TEST_CONFIG** with test files for each function
2. **Create test functions** that skip file dialogs
3. **Expose via window object** for CDP access
4. **Document in this file** the test commands
5. **Add test files** to `D:\TestFilesForLocaNext\{AppName}\`

---

## Known Issues

### Multi-Process Spawning
Old background shells may spawn extra processes. Always:
1. Kill ALL processes before testing
2. Verify process count after launch
3. Use synchronous PowerShell, not background bash

### Port Conflicts
If port 8888 is in use:
```bash
/mnt/c/Windows/System32/taskkill.exe /F /IM python.exe
sleep 5  # Wait for port cleanup
```

---

*Protocol established: 2025-12-07*
*Applies to: XLSTransfer, QuickSearch, KR Similar, ALL future apps*
