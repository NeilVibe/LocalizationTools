# LocaNext Testing Toolkit

**Autonomous Testing System for LocaNext Desktop App**

This toolkit enables **fully autonomous testing** of all LocaNext app functions without human interaction using Chrome DevTools Protocol (CDP).

---

## Quick Start

```bash
# 1. Install dependencies
cd testing_toolkit/scripts
npm install

# 2. Check prerequisites
cd ../setup
bash check_prerequisites.sh

# 3. Run all tests (launches app, tests, closes)
bash launch_and_test.sh
```

---

## How It Works

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                     AUTONOMOUS TESTING ARCHITECTURE                           ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐       ║
║  │   WSL/Linux     │────▶│  LocaNext.exe   │────▶│   CDP (9222)    │       ║
║  │   Test Runner   │◀────│  (Windows)      │◀────│   WebSocket     │       ║
║  └─────────────────┘     └─────────────────┘     └─────────────────┘       ║
║                                                                              ║
║  Layer 1: TEST MODE (window.{app}Test.{function})                           ║
║    └── Executes functions directly, skips file dialogs                      ║
║                                                                              ║
║  Layer 2: CDP Protocol                                                       ║
║    └── Runtime.evaluate() to call JavaScript in Electron renderer           ║
║                                                                              ║
║  Layer 3: Backend API (port 8888)                                           ║
║    └── Health checks, processing verification                               ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

---

## Available Test Functions

### XLSTransfer (`window.xlsTransferTest`)

| Function | Command | Description | Time |
|----------|---------|-------------|------|
| createDictionary | `node run_test.js xlsTransfer.createDictionary` | Create dict from test file | ~20s |
| loadDictionary | `node run_test.js xlsTransfer.loadDictionary` | Load existing dictionary | ~5s |
| translateExcel | `node run_test.js xlsTransfer.translateExcel` | Translate Excel file | ~10s |
| transferToClose | `node run_test.js xlsTransfer.transferToClose` | Transfer to Close tool | ~5s |
| getStatus | `node run_test.js xlsTransfer.getStatus` | Get current status | instant |

### QuickSearch (`window.quickSearchTest`)

| Function | Command | Description | Time |
|----------|---------|-------------|------|
| loadDictionary | `node run_test.js quickSearch.loadDictionary` | Load BDO_EN dictionary | ~15s |
| search | `node run_test.js quickSearch.search` | Search for test query | ~5s |
| getStatus | `node run_test.js quickSearch.getStatus` | Get current status | instant |

### KR Similar (`window.krSimilarTest`)

| Function | Command | Description | Time |
|----------|---------|-------------|------|
| loadDictionary | `node run_test.js krSimilar.loadDictionary` | Load BDO embeddings | ~45s |
| search | `node run_test.js krSimilar.search` | Find similar texts | ~10s |
| getStatus | `node run_test.js krSimilar.getStatus` | Get current status | instant |

---

## Directory Structure

```
testing_toolkit/
├── README.md                  # This file
├── TEST_FILES_MANIFEST.md     # Required test files documentation
│
├── scripts/
│   ├── package.json           # Node.js dependencies
│   ├── run_test.js            # Single test runner
│   └── run_all_tests.js       # Full test suite
│
└── setup/
    ├── check_prerequisites.sh # Verify environment
    └── launch_and_test.sh     # Complete test workflow
```

---

## Prerequisites

1. **LocaNext installed** at `D:\LocaNext\`
2. **Test files** at `D:\TestFilesForLocaNext\` (see TEST_FILES_MANIFEST.md)
3. **Node.js** with `ws` module installed
4. **WSL** with access to Windows PowerShell

Verify with:
```bash
bash setup/check_prerequisites.sh
```

---

## Manual Testing

If you prefer to control each step:

```bash
# 1. Kill existing processes
/mnt/c/Windows/System32/taskkill.exe /F /IM LocaNext.exe

# 2. Launch with CDP
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe \
  -Command "Start-Process -FilePath 'D:\LocaNext\LocaNext.exe' -ArgumentList '--remote-debugging-port=9222'"

# 3. Wait for app to start
sleep 25

# 4. Run individual test
cd testing_toolkit/scripts
node run_test.js xlsTransfer.createDictionary --wait 30

# 5. Check status
node run_test.js xlsTransfer.getStatus

# 6. Cleanup
/mnt/c/Windows/System32/taskkill.exe /F /IM LocaNext.exe
```

---

## Test Options

### Run specific app tests
```bash
node run_all_tests.js --app xlsTransfer
node run_all_tests.js --app quickSearch
node run_all_tests.js --app krSimilar
```

### Skip slow tests
```bash
node run_all_tests.js --skip-slow
```

### Custom wait time
```bash
node run_test.js xlsTransfer.createDictionary --wait 60
```

### Custom CDP port
```bash
CDP_PORT=9333 bash setup/launch_and_test.sh
```

---

## TEST MODE in Code

Each app component exposes test functions via the `window` object:

```javascript
// XLSTransfer.svelte
window.xlsTransferTest = {
  createDictionary: () => testCreateDictionary(),
  loadDictionary: () => loadDictionary(),
  translateExcel: () => testTranslateExcel(),
  transferToClose: () => testTransferToClose(),
  getStatus: () => ({
    isProcessing,
    statusMessage,
    isDictionaryLoaded,
    isTransferEnabled
  })
};
```

Test functions use predefined test files (see `TEST_CONFIG` in each component) to skip file dialogs.

---

## Troubleshooting

### CDP not accessible

```bash
# Check if app is running
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe \
  -Command "(Get-Process LocaNext -ErrorAction SilentlyContinue).Count"

# Check CDP endpoint
curl http://localhost:9222/json
```

### Multiple processes spawning

Always kill ALL processes before launching:
```bash
/mnt/c/Windows/System32/taskkill.exe /F /IM LocaNext.exe
sleep 3
```

### Test files not found

Verify test files exist:
```bash
ls -la /mnt/d/TestFilesForLocaNext/
```

### Port 8888 conflict

Kill Python processes:
```bash
/mnt/c/Windows/System32/taskkill.exe /F /IM python.exe
sleep 5
```

---

## Related Documentation

- [ADD_TEST_MODE_GUIDE.md](ADD_TEST_MODE_GUIDE.md) - **How to add TEST MODE to new apps** (for future Claude sessions)
- [AUTONOMOUS_TESTING_PROTOCOL.md](../docs/testing/AUTONOMOUS_TESTING_PROTOCOL.md) - Full protocol
- [AUTONOMOUS_WINDOWS_TESTING.md](../docs/testing/AUTONOMOUS_WINDOWS_TESTING.md) - Windows-specific guide
- [DEBUG_AND_TEST_HUB.md](../docs/testing/DEBUG_AND_TEST_HUB.md) - Master testing hub

---

*Created: 2025-12-07 | LocaNext Testing Toolkit v1.0*
