# Session Context - Claude Handoff Document

**Last Updated:** 2025-12-19 17:55 | **Build:** 301 (v25.1219.1118) | **Next:** 302

---

## CURRENT STATE

### Build 301 Status: INSTALLED & TESTED
- ✅ Playground has Build 301 installed
- ✅ CDP testing infrastructure working
- ✅ BUG-028, BUG-029 verified fixed
- 🔧 BUG-030 fix ready (code changed, needs Build 302)

### Pending Build 302
Code changes ready to deploy:
- **BUG-030 FIX:** WebSocket import path fixed in `server/api/health.py`

---

## CDP Testing (IMPORTANT)

**WSL2 cannot reach Windows localhost.** CDP tests MUST run from Windows PowerShell.

### Quick Start
```powershell
# From Windows PowerShell:
Push-Location '\\wsl.localhost\Ubuntu2\home\neil1988\LocalizationTools\testing_toolkit\cdp'
node login.js              # Login as neil/neil
node quick_check.js        # Check page state
node test_server_status.js # Check server status
node test_bug029.js        # Test Upload as TM
```

### Launch App with CDP (from WSL)
```bash
/mnt/c/Windows/System32/taskkill.exe /F /IM "LocaNext.exe" /T 2>/dev/null
cd /mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/Playground/LocaNext
./LocaNext.exe --remote-debugging-port=9222 &
```

---

## Issues Summary

| Issue | Status | Description |
|-------|--------|-------------|
| BUG-028 | ✅ FIXED | Model2Vec import - verified in Build 301 |
| BUG-029 | ✅ FIXED | Upload as TM - verified in Build 301 |
| BUG-030 | 🔧 CODE FIXED | WebSocket "disconnected" - wrong import path |
| UI-033 | ✅ CLOSED | App Settings NOT empty |
| UI-031 | 🔄 OPEN | Font size setting may not apply |
| UI-032 | 🔄 OPEN | Bold setting may not apply |
| UI-034 | 🔄 OPEN | Tooltips cut off at window edge |
| UI-027 | ❓ DECISION | Confirm button - keep or remove? |
| Q-001 | ❓ DECISION | TM auto-sync vs manual sync? |

### Counts
- **Fixed (verified):** 2 (BUG-028, BUG-029)
- **Fixed (pending build):** 1 (BUG-030)
- **Closed:** 1 (UI-033)
- **Open UI issues:** 3 (UI-031, UI-032, UI-034)
- **Decisions needed:** 2 (UI-027, Q-001)

---

## BUG-030 Fix Details

**Problem:** Server status showed WebSocket as "disconnected" even when connected.

**Root Cause:** `server/api/health.py` imported from non-existent file:
```python
# WRONG - file doesn't exist!
from server.socket_manager import sio

# CORRECT - actual location
from server.utils.websocket import sio
```

**Fix Applied:**
- Line 142: Fixed `sio` import path
- Line 156: Fixed `connected_clients` import path

**File:** `server/api/health.py`

---

## Trigger Build 302

```bash
# From WSL:
git add -A && git commit -m "Fix: BUG-030 WebSocket import path in health.py"
echo "Build LIGHT" >> GITEA_TRIGGER.txt
git add GITEA_TRIGGER.txt && git commit --amend --no-edit
git push origin main && git push gitea main
```

After build completes (~12-15 min):
```bash
# Install to Playground
./scripts/playground_install.sh --launch --auto-login

# Verify fix (from Windows PowerShell)
Push-Location '\\wsl.localhost\Ubuntu2\home\neil1988\LocalizationTools\testing_toolkit\cdp'
node login.js
node check_server_status.js  # Should show WebSocket: connected
```

---

## Key Paths

| What | Path |
|------|------|
| Playground | `C:\NEIL_PROJECTS_WINDOWSBUILD\LocaNextProject\Playground\LocaNext` |
| CDP Tests | `testing_toolkit/cdp/*.js` |
| Health API | `server/api/health.py` |
| WebSocket | `server/utils/websocket.py` |
| Session Doc | `docs/wip/SESSION_CONTEXT.md` |
| Issue List | `docs/wip/ISSUES_TO_FIX.md` |

---

## CDP Test Scripts

| Script | Purpose |
|--------|---------|
| `login.js` | Auto-login as neil/neil |
| `quick_check.js` | Page state, test interfaces |
| `check_server_status.js` | Server status panel (BUG-030) |
| `test_bug029.js` | Upload as TM flow |
| `test_server_status.js` | Server status + TM build |
| `debug_websocket.js` | WebSocket debug info |
| `check_network.js` | Network request debug |

---

## Remaining Work Priority

1. **Build 302** - Deploy BUG-030 fix, verify WebSocket shows "connected"
2. **UI-031/032** - Test if Font/Bold settings actually work
3. **UI-034** - Tooltip positioning fix
4. **UI-027** - Decide: keep or remove Confirm button?
5. **Q-001** - Decide: auto-sync or manual sync for TM?

---

*Session handoff - BUG-030 fix ready, awaiting Build 302*
