# Autonomous Windows Testing Guide

**Created:** 2025-12-07 | **Status:** Working

---

## Overview

This guide covers how Claude can **autonomously test** the Windows app without user interaction, using:
- Chrome DevTools Protocol (CDP) for UI interaction
- TEST MODE for skipping file dialogs
- Proper process management to avoid chaos

---

## Critical Issues & Solutions

### Issue 1: Multiple Process Spawning

**Problem:** Running `./LocaNext.exe` from background bash shells creates multiple processes that persist.

**Solution:**
1. ALWAYS kill all processes before launching
2. NEVER use background bash (`&`) for Windows apps
3. Use synchronous PowerShell commands
4. Verify process count after launch

```bash
# CORRECT: Kill, then launch, then verify
/mnt/c/Windows/System32/taskkill.exe /F /IM LocaNext.exe 2>&1
sleep 2
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command "Start-Process -FilePath 'D:\LocaNext\LocaNext.exe' -ArgumentList '--remote-debugging-port=9222'"
sleep 20
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command "(Get-Process LocaNext -ErrorAction SilentlyContinue).Count"
```

### Issue 2: Port 8888 Conflicts

**Problem:** Multiple backends trying to bind to same port.

**Solution:** Kill all processes and wait for port cleanup.

```bash
/mnt/c/Windows/System32/taskkill.exe /F /IM LocaNext.exe
/mnt/c/Windows/System32/taskkill.exe /F /IM python.exe  # Optional
sleep 5  # Wait for TIME_WAIT to clear
```

### Issue 3: File Dialogs Block CDP Testing

**Problem:** Native Windows file dialogs can't be automated via CDP.

**Solution:** Use TEST MODE - exposed via `window.xlsTransferTest` object.

---

## TEST MODE

XLSTransfer has a built-in TEST MODE that skips file dialogs and uses predefined test files.

### Available Test Functions

```javascript
// Exposed globally as window.xlsTransferTest
window.xlsTransferTest.createDictionary()  // Uses D:\TestFilesForLocaNext\GlossaryUploadTestFile.xlsx (100 rows, fast)
window.xlsTransferTest.loadDictionary()    // Loads existing dictionary
window.xlsTransferTest.translateExcel()    // Uses 150linetranslationtest.xlsx
window.xlsTransferTest.transferToClose()   // Uses closetotest.txt
window.xlsTransferTest.getStatus()         // Returns {isProcessing, statusMessage, isDictionaryLoaded, isTransferEnabled}
```

### Test Files Location

```
D:\TestFilesForLocaNext\
├── GlossaryUploadTestFile.xlsx   <- Create Dictionary test (100 rows, ~18 seconds)
├── TESTSMALL.xlsx                <- Larger dictionary test (22,917 rows, ~15 min)
├── 150linetranslationtest.xlsx   <- Translate Excel test
├── closetotest.txt               <- Transfer to Close test
└── ... other test files
```

**Note:** GlossaryUploadTestFile.xlsx is the recommended test file - small enough for quick testing (~18s) but representative of real use.

### How to Run Tests via CDP

```bash
# Create test script
cat > /tmp/test_xlstransfer.js << 'EOF'
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
        // Run test
        await send('Runtime.evaluate', {
            expression: 'window.xlsTransferTest.createDictionary()',
            returnByValue: true
        });

        // Wait and check status
        await new Promise(r => setTimeout(r, 5000));

        const status = await send('Runtime.evaluate', {
            expression: 'JSON.stringify(window.xlsTransferTest.getStatus())',
            returnByValue: true
        });
        console.log('Status:', status.result.value);

        ws.close();
        process.exit(0);
    });
}
main();
EOF

# Copy and run
cp /tmp/test_xlstransfer.js /mnt/d/LocaNext/
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command "cd D:\LocaNext; node test_xlstransfer.js"
```

---

## Complete Autonomous Test Workflow

```bash
# 1. Kill all existing processes
/mnt/c/Windows/System32/taskkill.exe /F /IM LocaNext.exe 2>&1 || true
sleep 3

# 2. Launch ONE instance with CDP
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command "Start-Process -FilePath 'D:\LocaNext\LocaNext.exe' -ArgumentList '--remote-debugging-port=9222'"
sleep 20

# 3. Verify single process
PROC_COUNT=$(/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command "(Get-Process LocaNext -ErrorAction SilentlyContinue).Count")
echo "Process count: $PROC_COUNT"  # Should be 1-4 (main + renderer + GPU + utility)

# 4. Verify backend healthy
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command "(Invoke-WebRequest -Uri 'http://localhost:8888/health' -UseBasicParsing).Content"

# 5. Run CDP test
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command "cd D:\LocaNext; node test_xlstransfer.js"

# 6. Check logs
tail -30 /mnt/d/LocaNext/logs/locanext_app.log

# 7. Kill when done
/mnt/c/Windows/System32/taskkill.exe /F /IM LocaNext.exe
```

---

## Correct PowerShell Paths

**IMPORTANT:** Use full paths for PowerShell commands from WSL:

| Command | Full Path |
|---------|-----------|
| PowerShell | `/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe` |
| taskkill | `/mnt/c/Windows/System32/taskkill.exe` |
| App location | `D:\LocaNext\LocaNext.exe` (from Windows) or `/mnt/d/LocaNext/` (from WSL) |

---

## Test File Requirements

For Create Dictionary to work, the Excel file needs:
- Column A: Korean text
- Column B: Translation (any language)
- Data starting from row 1 or 2

If you get "positional indexers are out-of-bounds", the test file columns are empty or wrong.

---

## Logs Location

```bash
# App logs
/mnt/d/LocaNext/logs/locanext_app.log

# Clear logs before testing
rm -f /mnt/d/LocaNext/logs/*.log
```

---

*Last updated: 2025-12-07*
