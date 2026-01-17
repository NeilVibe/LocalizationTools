# Session Context

> Last Updated: 2026-01-18 (Session 49 - QACompiler Fixes)

---

## SESSION 49: QACompiler Fixes ✅

### Progress Tracker - Workload Data Preservation Bug

**Problem:** Days Worked and Comment columns (M and P) were losing user-entered data on rebuild.

**Root Cause:** `read_existing_workload_data()` iterated through ALL rows including CATEGORY BREAKDOWN section. Since both tables have "User" in column A but different data in columns M and P:
- Tester Stats row: M=Days Worked, P=Comment
- Category Breakdown row: M=category data ("-"), P=category data ("-")

Category breakdown rows came AFTER tester stats, so they OVERWROTE the preserved data.

**Fix:** Stop reading when hitting "CATEGORY BREAKDOWN":
```python
if "CATEGORY BREAKDOWN" in user_str: break
```

**File:** `tracker/total.py` line ~168

### Other QACompiler Fixes (Session 48-49)

| Issue | Fix | File |
|-------|-----|------|
| System output path wrong | Use `DATASHEET_OUTPUT` not `input_path.parent` | `gui/app.py:463` |
| System not in populate pipeline | Added System config to `DATASHEET_LOCATIONS` | `core/populate_new.py` |
| System files showing stale | Use `shutil.copy()` not `shutil.copy2()` | `system_localizer.py` |
| CI workflow fragmented | Consolidated 3 jobs into 1 | `.github/workflows/qacompiler-build.yml` |
| Artifacts combined | Split into Setup, Portable, Source | `.github/workflows/qacompiler-build.yml` |

---

## SESSION 48: Patch Updater COMPLETE ✅

### THE GOAL (ACHIEVED!)

```
Game-launcher style PATCH updates:
✅ Download ONLY changed files (~18MB app.asar)
✅ NOT the full 624MB installer
✅ Restart and apply update automatically
```

### WHAT WAS FIXED

| Bug | Root Cause | Fix | Build |
|-----|------------|-----|-------|
| fetchJson failed | Node.js `http` module doesn't work reliably in packaged Electron | Use Electron `net` module | 484 |
| Hash verification failed | `fileStream.end()` is async - resolved before file flushed | Wait for 'finish' event | 487 |
| ASAR interception | Electron's patched `fs` intercepts ALL `.asar` file operations | Use `original-fs` module | 489 |

### FINAL TEST RESULTS (Build 490)

```
=== Before Restart ===
Version: 26.117.2338

=== After Restart ===
Version: 26.117.2359  ✅ UPDATE APPLIED!
```

**Debug log confirms:**
- Downloaded: 17.92 MB (NOT 624 MB!)
- Hash verified: `87beef60f5693993...` ✅
- File staged to `pending-updates/app.asar` ✅
- Restart triggered ✅
- Update applied on restart ✅
- `component-state.json` updated ✅

### KEY FIX: ASAR Interception

**Problem:** Electron patches Node.js `fs` module to intercept ANY file with `.asar` in the name - even in AppData!

```javascript
// WRONG - fs is patched by Electron
const fs = require('fs');
fs.createWriteStream('path/to/app.asar');  // → "Invalid package" error

// CORRECT - bypass Electron's ASAR interception
const originalFs = require('original-fs');
originalFs.createWriteStream('path/to/app.asar');  // → Works!
```

**Files Modified:** `electron/patch-updater.js`
- All `fs.*` calls for `.asar` files now use `originalFs`

### CLOSED ISSUES

- **PATCH-001:** ✅ FIXED - Downloads ~18MB patch, not 624MB installer
- **PATCH-002:** ✅ FIXED - Install/swap works correctly on restart

---

## DB FACTORY & REPOSITORY PATTERN REVIEW

### Overall Rating: 7/10 - Functional but needs hardening

### Strengths (EXCELLENT)

| # | Item |
|---|------|
| 1 | Interface design - Full parity across PostgreSQL/SQLite adapters |
| 2 | Factory pattern - Clean, testable, request-scoped |
| 3 | Offline/online separation - Clear mode detection via token |
| 4 | Permission isolation - Checked inside repos, not routes |
| 5 | Repository usage - Routes use ONLY interfaces |

### Weaknesses (NEED FIX)

| # | Issue | Severity | Location |
|---|-------|----------|----------|
| 1 | **SQLite repos access `_get_connection()` directly** | MEDIUM | `row_repo.py`, `tm_repo.py` |
| 2 | **AsyncSessionWrapper is a hack, not true async** | HIGH | `dependencies.py:33-143` |
| 3 | **Bulk ops break out to sync session** | MEDIUM | `tm_repo.py:588-606` |

### LEAK #1: Private Method Access

SQLite repos bypass encapsulation:
```python
# WRONG - Accesses private method
with self.db._get_connection() as conn:
    conn.execute(...)

# SHOULD BE - Public method
await self.db.execute_raw(...)
```

### LEAK #2: AsyncSessionWrapper (THE BIG ONE)

**What it does:** Wraps sync Session to return fake awaitables
```python
def execute(self, *args, **kwargs):
    result = self._session.execute(*args)
    async def _awaitable():
        return result  # Resolves INSTANTLY - not true async!
    return _awaitable()
```

**Problems:**
- No actual concurrency - blocks event loop
- GIL blocking with SQLite in async context
- Misleading type signature
- Hides the real problem

**The fix:** Use `aiosqlite` library for true async SQLite

### LEAK #3: Bulk Operations

`add_entries_bulk()` breaks async pattern:
```python
async def add_entries_bulk(self, ...):
    sync_db = next(get_db())  # ← Gets SYNC session in ASYNC method!
```

### Recommended Actions

| Priority | Action | Effort |
|----------|--------|--------|
| HIGH | Replace AsyncSessionWrapper with aiosqlite | 2-3 days |
| MEDIUM | Add public methods to OfflineDatabase | 1-2 days |
| MEDIUM | Make bulk operations consistently async | 1-2 days |
| LOW | Add encapsulation tests | 1 day |

---

## NEW BUGS DISCOVERED (Session 47)

### BUG-042: Trash Bin - WORKS IN DEV MODE ✅

**Original Symptom:** Clicking on Trash Bin does nothing (Windows app)

**DEV Mode Testing Result:**
- ✅ **WORKS** - Full chain verified via GDP logging:
  - `handleDoubleClick` → `dispatch('enterFolder')` → `handleEnterFolder` → `loadTrashContents()`
- Screenshot proof: Breadcrumb shows "Home > Recycle Bin" with trash items displayed
- **Conclusion:** Bug is Windows Electron-specific, not in core functionality

### BUG-043: Offline Storage - Navigation WORKS ✅

**Original Symptom:** Folder creation fails (Windows app)

**DEV Mode Testing Result:**
- ✅ **Navigation WORKS** - Verified via GDP logging:
  - `handleDoubleClick` → `dispatch('enterFolder')` → `loadOfflineStorageContents()`
- Screenshot proof: Breadcrumb shows "Home > Offline Storage" with folders listed
- GDP logging added to `createFolder()` for Windows debugging
- **Conclusion:** May be Windows-specific or API-related

### GDP Frontend Logging - ADDED ✅

Added GDP-style logging to critical paths:
- `ExplorerGrid.svelte:handleDoubleClick()` - Logs item type and dispatches
- `FilesPage.svelte:handleEnterFolder()` - Logs received events
- `FilesPage.svelte:loadTrashContents()` - Logs call
- `FilesPage.svelte:createFolder()` - Logs folder creation with API response

**How to use:**
```javascript
// Added logging uses logger.warning for visibility in backend logs
logger.warning('GDP: function called', { data });
```

Logs visible in:
- Browser console (DEV mode)
- Backend logs (via remote-logger endpoint)

---

## SESSION 46 RECAP: GDP Debug Journey

### Root Causes Found (via GDP)

| # | Bug | Evidence | Fix |
|---|-----|----------|-----|
| 1 | ASAR Interception | `ENOENT, not found in ...app.asar` | Use `original-fs` module |
| 2 | Node.js HTTP Blocking | Only 1 chunk, then 2 min silence | Use Electron `net` module |

### GDP Debug Log Location

```
%APPDATA%/LocaNext/patch-updater-debug.log
```

### Key Lesson: Electron Networking

Node.js `http` module doesn't work reliably in Electron packaged apps on Windows.
Electron's `net` module (Chromium network stack) works correctly.

---

## ARCHITECTURE

```
LocaNext.exe (User PC)           Central PostgreSQL
├─ Electron + Svelte 5       →   ├─ All text data
├─ Embedded Python Backend       ├─ Users, sessions
├─ SQLite (offline storage)  ←   ├─ LDM rows, TM entries
├─ FAISS indexes (local)         └─ Logs
└─ Qwen model (optional)

DATABASE ABSTRACTION:
┌─────────────────────────────────────┐
│      Repository Interface           │
│   tm.get(), tm.assign(), etc.       │
└──────────────┬──────────────────────┘
               │
       ┌───────┴───────┐
       │               │
┌──────▼─────┐  ┌──────▼─────┐
│ PostgreSQL │  │   SQLite   │
│  (async)   │  │  (HACK!)   │ ← AsyncSessionWrapper
└────────────┘  └────────────┘

SHOULD BE:
┌──────▼─────┐  ┌──────▼─────┐
│ PostgreSQL │  │   SQLite   │
│  (asyncpg) │  │ (aiosqlite)│ ← True async!
└────────────┘  └────────────┘
```

---

## PRIORITIES

| Priority | Task | Status |
|----------|------|--------|
| **CRITICAL** | Patch updater - download only app.asar | NOT DONE |
| **CRITICAL** | Patch updater - fix install/swap logic | NOT DONE |
| **HIGH** | Replace AsyncSessionWrapper with aiosqlite | TODO |
| **MEDIUM** | Fix BUG-042 (Trash Bin access) | TODO |
| **MEDIUM** | Fix BUG-043 (Folder creation) | TODO |
| **LOW** | SQLite repo encapsulation cleanup | TODO |

---

## QUICK COMMANDS

```bash
# DEV servers
./scripts/start_all_servers.sh --with-vite

# Check servers
./scripts/check_servers.sh

# Run tests
cd locaNext && npx playwright test

# Build trigger
echo "Build skip_linux NNN: Description" >> GITEA_TRIGGER.txt && git add -A && git commit -m "Build NNN" && git push origin main && git push gitea main

# Check build status
python3 -c "
import sqlite3
c = sqlite3.connect('/home/neil1988/gitea/data/gitea.db').cursor()
c.execute('SELECT id, status, title FROM action_run ORDER BY id DESC LIMIT 3')
STATUS = {0:'UNKNOWN', 1:'SUCCESS', 2:'FAILURE', 3:'CANCELLED', 4:'SKIPPED', 5:'WAITING', 6:'RUNNING', 7:'BLOCKED'}
for r in c.fetchall(): print(f'Run {r[0]}: {STATUS.get(r[1], r[1]):8} - {r[2]}')"
```

---

## HONEST ASSESSMENT OF TODAY

### What We Achieved
1. **Download mechanism fixed** - Electron net module works
2. **GDP methodology proven** - Found real bugs via granular logging
3. **DB architecture reviewed** - Know what needs fixing

### What We Didn't Achieve
1. **Actual patch updates** - Still downloading full installer
2. **Working install/swap** - Old app deleted, new not installed
3. **The core goal** - Game-launcher style small patches

### Technical Debt Discovered
1. AsyncSessionWrapper should be replaced with aiosqlite
2. SQLite repos access private methods
3. Bulk operations are inconsistent

---

*Session 47 | Build 483 | Patch Download Works, Core Patch Logic Missing*
