# CDP (Chrome DevTools Protocol) Test Suite

This directory contains autonomous tests for the LocaNext Electron app.

## Test Files

| File | Purpose |
|------|---------|
| `test_edit_final.js` | BUG-002 fix verification - edit lock test |
| `test_lock_simple.js` | Simple lock check with project/file navigation |
| `check_page.js` | Quick page state inspection |
| `find_buttons.js` | DOM element discovery |
| `debug_dom.js` | CSS class analysis |

## Requirements

- Node.js on Windows
- `chrome-remote-interface` npm package
- LocaNext running with `--remote-debugging-port=9222`

## Running Tests

From WSL:
```bash
# Start app with CDP
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command "
Start-Process 'C:\\NEIL_PROJECTS_WINDOWSBUILD\\LocaNextProject\\LocaNext\\LocaNext.exe' -ArgumentList '--remote-debugging-port=9222'
"

# Wait for app to load, then run test
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -Command "cd C:\\NEIL_PROJECTS_WINDOWSBUILD\\LocaNextProject; node test_edit_final.js"
```

## Deploying Tests to Windows

```bash
cp /home/neil1988/LocalizationTools/tests/cdp/*.js /mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/
```

## See Also

- [CDP Testing Guide](../../docs/testing/CDP_TESTING_GUIDE.md) - Full documentation
- [Debug and Test Hub](../../docs/testing/DEBUG_AND_TEST_HUB.md) - All testing info
