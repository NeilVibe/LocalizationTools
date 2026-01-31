# Issues To Fix

**Last Updated:** 2026-01-31 (Session 60+) | **Build:** 523 | **Open:** 0

---

## Quick Summary

| Status | Count |
|--------|-------|
| **OPEN** | 0 |
| **FIXED/CLOSED** | 160 |

---

## RECENTLY FIXED (Session 60+)

### LIMIT-001: Offline TM Search Suggestions ✅ FIXED

- **Fixed:** Session 60+ (Master Architecture Cleanup)
- **Component:** `server/repositories/sqlite/tm_repo.py`

**Problem:** The `/tm/suggest` endpoint returned empty results for SQLite TMs because it used PostgreSQL's `pg_trgm` extension.

**Solution:**
- Added FAISS-based `search_similar()` implementation to `SQLiteTMRepository`
- Uses `TMSearcher` with cached FAISS indexes (module-level `_tm_index_cache`)
- Graceful fallback when no indexes exist

**Files Modified:**
- `server/repositories/sqlite/tm_repo.py` - FAISS search_similar implementation

---

### LIMIT-002: Offline TM Pretranslation ✅ FIXED

- **Fixed:** Session 60+ (Master Architecture Cleanup)
- **Component:** EmbeddingsManagers, TMRepository interface
- **Effort:** Complete rewrite of TM loading

**Problem:** All 3 pretranslation engines queried PostgreSQL directly for TM data, bypassing the repository pattern.

**Solution:**
1. Added `get_all_entries(tm_id)` to `TMRepository` interface
2. Implemented in both PostgreSQL and SQLite repos
3. Created `TMLoader` - unified loader that auto-detects PostgreSQL vs SQLite
4. Updated `XLS Transfer` and `KR Similar` EmbeddingsManagers to use TMLoader

**Files Created/Modified:**
- `server/repositories/interfaces/tm_repository.py` - Added `get_all_entries()` abstract method
- `server/repositories/postgresql/tm_repo.py` - Implemented `get_all_entries()`
- `server/repositories/sqlite/tm_repo.py` - Implemented `get_all_entries()`
- `server/tools/shared/tm_loader.py` - **NEW** unified TM entry loader
- `server/tools/shared/__init__.py` - Export TMLoader
- `server/tools/xlstransfer/embeddings.py` - Uses TMLoader
- `server/tools/kr_similar/embeddings.py` - Uses TMLoader

**Result:** All pretranslation engines now work offline:
| Engine | File Loading | TM Loading | Status |
|--------|--------------|------------|--------|
| `standard` | SQLite ✓ | TMLoader ✓ | **WORKS offline** |
| `xls_transfer` | SQLite ✓ | TMLoader ✓ | **WORKS offline** |
| `kr_similar` | SQLite ✓ | TMLoader ✓ | **WORKS offline** |

---

### ROUTE-001: rows.py Direct SQLite Import ✅ FIXED

- **Fixed:** Session 60+ (Master Architecture Cleanup)
- **Component:** `server/tools/ldm/routes/rows.py`

**Problem:** Direct `SQLiteRowRepository` imports without proper `SchemaMode`.

**Solution:** Created `RoutingRowRepository` pattern - transparent ID-based routing.
- Negative IDs → SQLite OFFLINE mode
- Positive IDs → Primary repo (PostgreSQL or SQLite SERVER)
- Factory now wraps primary repo with RoutingRowRepository
- Zero direct imports in rows.py

**Files Created/Modified:**
- `server/repositories/routing/row_repo.py` - **NEW** RoutingRowRepository
- `server/repositories/routing/__init__.py` - **NEW** exports
- `server/repositories/factory.py` - Wraps repos with RoutingRowRepository

---

### CODE-REVIEW-001: Thread Safety + Cache Eviction ✅ FIXED

- **Fixed:** Session 60+ (6-agent parallel code review)
- **Component:** `server/repositories/sqlite/tm_repo.py`

**Findings Fixed:**
1. Added `threading.Lock` for thread-safe cache access
2. Added LRU-style eviction with `_TM_INDEX_CACHE_MAX_SIZE = 10`
3. Added cache invalidation in `add_entry()`, `add_entries_bulk()`, `delete_entry()`, `update_entry()`
4. Replaced `traceback.print_exc()` → `logger.exception()` in EmbeddingsManagers

---

## OPEN ISSUES

*No open issues.*

---

## KNOWN LIMITATIONS

### QA-SCHEMA-001: SQLite Missing QA Columns (LOW PRIORITY)

- **Status:** Known limitation, not blocking
- **Component:** SQLite offline schema

**Issue:** SQLite `rows` table missing these PostgreSQL columns:
- `qa_checked_at` (timestamp)
- `qa_flag_count` (integer)

**Impact:** QA flag operations work, but some metadata tracking incomplete in offline mode.

**Workaround:** None needed - QA core functionality works.

---

## RECENTLY FIXED (Session 60)

### BUG-042: Navigation Broken on Windows ✅ FIXED

- **Fixed:** Session 60
- **Problem:** `handleEnterFolder` was not async and didn't await folder load functions
- **Impact:** All folder navigation (platforms, projects, folders, trash) potentially broken on Windows
- **Fix:** Made `handleEnterFolder` async and added `await` to all 6 folder load calls

**File:** `locaNext/src/lib/components/pages/FilesPage.svelte:646-674`

---

### AIOSQLITE-001 to AIOSQLITE-011: Missing Await/Dict Conversions ✅ FIXED

- **Fixed:** Session 60
- **Problem:** aiosqlite migration left 11 bugs in Offline Storage code path
- **Files Fixed:**
  - `files.py` - 3 missing `await` statements
  - `pretranslate.py` - 3 sync→async bridges with `asyncio.run()`
  - `tm_repo.py` - 5 `sqlite3.Row` to `dict()` conversions

---

## CLOSED (Session 60 Verification)

### ARCH-001: Repository Layer Violations ✅ ALREADY FIXED

- **Verified:** Session 60 (6-agent parallel verification)
- **Finding:** No layer violations exist. Factory handles all mode detection at boundary.
- **Evidence:** grep found 0 instances of `ACTIVE_DATABASE_TYPE` in PostgreSQL repos

---

### TECH-DEBT-002: CLI Tools Use print() ✅ NOT A BUG

- **Verified:** Session 60
- **Finding:** Intentional design. CLI tools NEED stdout/stderr for:
  - Progress tracking (`print(..., file=sys.stderr)`)
  - JSON output for subprocess piping
- **Action:** Closed as "by design"

---

### IMPROVE-001: Unify First-Run Setup with Launcher ✅ NOT NEEDED

- **Verified:** Session 60
- **Finding:** Architecturally sound separation:
  - First-run setup: ONE-TIME environment init (pre-app)
  - Launcher: EVERY-TIME connection mode selection (in-app)
- **Action:** Closed as "working as designed"

---

### DOCS-001: Documentation Files Too Large ✅ FIXED

- **Verified:** Session 60
- **Finding:** `OFFLINE_ONLINE_MODE.md` reduced from 1660 → 150 lines (91% reduction)
- **Action:** Closed

---

### TECH-DEBT-001: SQLite Sync I/O ✅ MOSTLY FIXED

- **Fixed:** Sessions 59-60
- **What was done:**
  - AsyncSessionWrapper removed
  - aiosqlite migration complete
  - 11 additional bugs fixed in Session 60
- **Action:** Closed (monitor for any remaining edge cases)

---

## Historical Issues

See `docs/archive/history/ISSUES_ARCHIVE.md` for 150+ resolved issues from Sessions 1-59.
