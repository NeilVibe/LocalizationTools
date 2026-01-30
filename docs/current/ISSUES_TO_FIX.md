# Issues To Fix

**Last Updated:** 2026-01-31 (Session 59) | **Build:** 499 | **Open:** 4

---

## Quick Summary

| Status | Count |
|--------|-------|
| **OPEN** | 4 |
| **FIXED/CLOSED** | 141 |

---

## OPEN ISSUES

### TECH-DEBT-001: SQLite Repositories Use Sync I/O ⚠️ LOW

- **Severity:** LOW (single-user offline mode, not critical)
- **Component:** `server/repositories/sqlite/*.py`, `server/database/offline.py`

**Problem:** SQLite repositories use sync `sqlite3` calls inside `async def` methods.

**Impact:** Event loop blocked during SQLite queries in offline mode.

**Why LOW:** Offline mode = single user desktop app. No concurrent requests. Works fine.

**Fixed (2026-01-31):**
- AsyncSessionWrapper REMOVED (~110 lines deleted)
- `get_async_db()` now uses real aiosqlite for SQLite mode
- Both PostgreSQL and SQLite use TRUE async via SQLAlchemy layer

**Remaining:** SQLite repositories use `OfflineDatabase` which is sync. Deferred.

---

### TECH-DEBT-002: CLI Tools Use print() Instead of Logger ⚠️ LOW

- **Severity:** LOW (CLI tools, intentional stdout/stderr for user interaction)
- **Components:** `server/tools/xlstransfer/` (40+ instances)

**Problem:** Legacy CLI tools use `print()` instead of `logger.*()`.

**Locations:**
- `server/tools/xlstransfer/translate_file.py`
- `server/tools/xlstransfer/process_operation.py`
- `server/tools/xlstransfer/load_dictionary.py`
- `server/tools/xlstransfer/embeddings.py`
- `server/client_config/client_config.py`

**Why LOW:** These are CLI tools that NEED stdout/stderr for user interaction. Not bugs.

**Fixed (2026-01-31):** Security logging in `config.py` now uses `logger` (3 lines fixed).

---

### BUG-042: Trash Bin Cannot Be Accessed ⚠️ LOW

- **Severity:** LOW (works in DEV mode)
- **Status:** NEEDS WINDOWS TESTING

**Problem:** Clicking Trash Bin does nothing on Windows Electron app. Works fine in DEV mode.

---

### IMPROVE-001: Unify First-Run Setup with Launcher UI ⚠️ LOW

- **Severity:** LOW (UX polish)
- **Components:** `electron/first-run-setup.js`, `src/lib/components/Launcher.svelte`

**Problem:** Two separate UIs for launcher and first-run setup. Could unify for consistent UX.

---

### DOCS-001: Documentation Files Too Large ⚠️ LOW

- **Severity:** LOW (affects Claude context)

**Problem:** Some docs exceed token limits.

| File | Lines | Target |
|------|-------|--------|
| `OFFLINE_ONLINE_MODE.md` | 1660 | < 1000 |

---

## RECENTLY FIXED (Session 58)

### TECH-DEBT-003: Svelte 4 Deprecated Syntax ✅ FIXED

- **Fixed:** Session 58
- **Problem:** Used `$:` reactive statements instead of Svelte 5 `$derived`
- **Files Fixed:**
  - `PresenceBar.svelte` - 3 instances → `$derived`
  - `ColorText.svelte` - 1 instance → `$derived`

---

## Session 53 Fixes

### BUILD-001: Slim Installer ✅ FIXED

- **Fixed:** Build 497
- **Problem:** Installer 594MB → Target 150MB
- **Solution:** Created `requirements-build.txt`, fixed cache hash
- **Result:** **174 MB** installer (71% smaller)

### UI-113, BUG-044, UI-114 ✅ FIXED (Session 50-51)

| Issue | Fix |
|-------|-----|
| UI-113 | Edit mode right-click menu with colors |
| BUG-044 | File search localStorage key fix |
| UI-114 | Toast notification positioning |

---

## Historical Issues

See `docs/archive/history/ISSUES_ARCHIVE.md` for 130+ resolved issues from Sessions 1-47.
