# CDP (Chrome DevTools Protocol) Test Suite

Autonomous tests for the LocaNext Electron app via Chrome DevTools Protocol.

---

## Test Files

### Full Flow Tests (E2E)

| File | Type | Purpose |
|------|------|---------|
| `test_full_flow.js` | Normal | Quick E2E: Project → File → Edit Modal |
| `test_full_flow_detailed.js` | Detailed | Verbose E2E with full logging |

### Feature Tests

| File | Purpose |
|------|---------|
| `test_edit_final.js` | BUG-002 fix verification - edit lock test |
| `test_lock_simple.js` | Simple lock check with project/file navigation |

### Debug/Discovery Tools

| File | Purpose |
|------|---------|
| `check_page.js` | Quick page state inspection |
| `find_buttons.js` | DOM element discovery - find clickable elements |
| `debug_dom.js` | CSS class analysis |

---

## Normal vs Detailed Tests

### Normal (Quick)
```bash
node test_full_flow.js
```
- Key steps logged
- Pass/fail in ~10 seconds
- Good for CI/CD, quick checks

### Detailed (Verbose)
```bash
node test_full_flow_detailed.js
```
- Every DOM query logged
- Click coordinates shown
- Timing for each operation
- Console messages captured
- Good for debugging failures

---

## Requirements

- Node.js on Windows
- LocaNext running with `--remote-debugging-port=9222`
- Backend servers running (PostgreSQL, FastAPI)

---

## Running Tests

### From WSL

```bash
# 1. Ensure servers are running
./scripts/check_servers.sh

# 2. Start app with CDP
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command "
Start-Process 'C:\NEIL_PROJECTS_WINDOWSBUILD\LocaNextProject\LocaNext\LocaNext.exe' -ArgumentList '--remote-debugging-port=9222'
"

# 3. Wait for app to load
sleep 5

# 4. Run test (Normal)
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command "
cd C:\NEIL_PROJECTS_WINDOWSBUILD\LocaNextProject; node test_full_flow.js
"

# 5. Or run Detailed test
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command "
cd C:\NEIL_PROJECTS_WINDOWSBUILD\LocaNextProject; node test_full_flow_detailed.js
"
```

### Deploying Tests to Windows

```bash
# Copy all tests to Windows
cp /home/neil1988/LocalizationTools/tests/cdp/*.js /mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/
```

---

## Test Output Examples

### Normal Test Output
```
═══════════════════════════════════════════════════════════
  FULL FLOW TEST: Project → File → Row → Edit Modal
═══════════════════════════════════════════════════════════

[1/8] Connecting to CDP...
   ✓ Connected to CDP
[2/8] Checking app state...
   Current App: ldm
   Authenticated: true
...
═══════════════════════════════════════════════════════════
  ✅ TEST PASSED: Edit modal opened successfully!
═══════════════════════════════════════════════════════════
```

### Detailed Test Output
```
╔══════════════════════════════════════════════════════════════════╗
║     DETAILED FULL FLOW TEST - CDP Autonomous Testing             ║
╚══════════════════════════════════════════════════════════════════╝

[     0ms] ═══ STEP 1: Connect to CDP ═══
[     1ms]   → Fetching targets from http://localhost:9222/json
[    45ms]   → Received 1847 bytes
[    46ms]   → Found 2 target(s)
[    47ms] ✓ Connected to CDP WebSocket
...
╔══════════════════════════════════════════════════════════════════╗
║                    ✅ TEST PASSED                                ║
║     Total time: 12.34s                                           ║
╚══════════════════════════════════════════════════════════════════╝
```

---

## Creating New Tests

Use `test_full_flow.js` as a template:

1. Copy the file
2. Modify the test steps
3. Use helper functions:
   - `queryDOM(ws, id, selector, description)` - Find elements
   - `clickElement(ws, id, selector, description)` - Click
   - `doubleClickElement(ws, id, selector, description)` - Double-click
   - `evaluate(ws, id, expression, description)` - Run JS
   - `wait(ms)` - Pause

---

## Error Handling

All tests catch:
- ✅ Alert dialogs (intercepted)
- ✅ Element not found
- ✅ Timeouts
- ✅ Authentication failures
- ✅ CDP connection errors

Exit codes:
- `0` = PASS
- `1` = FAIL

---

## See Also

- [CDP Testing Guide](../../docs/testing/CDP_TESTING_GUIDE.md) - Full documentation
- [Debug and Test Hub](../../docs/testing/DEBUG_AND_TEST_HUB.md) - All testing info
- [Server Management](../../docs/development/SERVER_MANAGEMENT.md) - Start servers

---

*Last Updated: 2025-12-12*
