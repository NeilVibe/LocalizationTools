# Issues To Fix

**Last Updated:** 2026-02-01 (Session 60+) | **Build:** 524 | **Open:** 0

---

## Quick Summary

| Status | Count |
|--------|-------|
| **OPEN** | 0 |
| **FIXED/CLOSED** | 167 |

---

## OPEN ISSUES

*No open issues. All caught up!*

---

## RECENTLY FIXED (Session 60+)

### DOCS-002: Repository/Factory Pattern Documentation ✅ ALREADY DOCUMENTED

- **Verified:** Session 60+ (2026-02-01)
- **Component:** Documentation

**Finding:** Documentation already exists in TWO places:
1. `docs/architecture/ARCHITECTURE_SUMMARY.md` - Lines 163-407 (full coverage)
2. `docs/current/WIP_EMBEDDING_IMPROVEMENTS.md` - Lines 58-100 (Repository Pattern section)

**Coverage includes:**
- Repository interface pattern (9 interfaces)
- Factory pattern with 3-mode detection (SchemaMode)
- Dependency injection examples
- Route usage patterns
- RoutingRowRepository for hybrid ID-based routing
- TMLoader for pretranslation

**Status:** Closed as "already documented"

---

### UX-001/UX-002/UX-003: TM Settings Panel UX Overhaul ✅ FIXED

- **Fixed:** Session 60+ (2026-02-01)
- **Component:** `locaNext/src/lib/components/pages/TMPage.svelte`

**Problems:**
1. **UX-001:** Model selection toggle not visible in TMPage settings
2. **UX-002:** Threshold more prominent than model selection
3. **UX-003:** Fast/Deep toggle needed clearer labeling

**Solution:**
Ported the engine selector from TMManager.svelte to TMPage.svelte settings panel:
- Added Fast/Deep toggle with icons (Flash/MachineLearning) at TOP of settings panel
- Rebalanced prominence: Engine toggle ABOVE threshold slider
- Added dynamic hint text explaining current mode
- Added tooltips explaining each mode's tradeoffs
- Consistent styling with TMManager.svelte engine toggle

**Files Modified:**
- `locaNext/src/lib/components/pages/TMPage.svelte`:
  - Added `Flash`, `MachineLearning` icon imports
  - Added `currentEngine`, `engineLoading` state variables
  - Added `loadCurrentEngine()`, `setEmbeddingEngine()` API functions
  - Added engine toggle UI to settings panel (prominent position)
  - Added CSS styles for `.engine-toggle`, `.engine-btn`, `.setting-divider`

---

### ARCH-002: Factory Violation in tm_crud.py ✅ FIXED

- **Fixed:** Session 60+ (2026-02-01)
- **Component:** `server/tools/ldm/routes/tm_crud.py`

**Problem:** Duplicate name check bypassed repository factory pattern.

**Solution:**
1. Added `check_name_exists(name)` abstract method to `TMRepository` interface
2. Implemented in `PostgreSQLTMRepository` and `SQLiteTMRepository`
3. Updated `tm_crud.py` line 84 to use `await repo.check_name_exists(name)`

**Files Modified:**
- `server/repositories/interfaces/tm_repository.py` - Added abstract method
- `server/repositories/postgresql/tm_repo.py` - Implemented method
- `server/repositories/sqlite/tm_repo.py` - Implemented method
- `server/tools/ldm/routes/tm_crud.py` - Uses repository pattern

---

### CODE-001: Dead Code in trash.py ✅ FIXED

- **Fixed:** Session 60+ (2026-02-01)
- **Component:** `server/tools/ldm/routes/trash.py`

**Problem:** Legacy serialize functions (lines 245-361) were dead code.

**Solution:** Removed 127 lines of unused code:
- `serialize_file_for_trash()`
- `serialize_folder_for_trash()`
- `serialize_project_for_trash()`
- `serialize_platform_for_trash()`

**Files Modified:**
- `server/tools/ldm/routes/trash.py` - Removed lines 245-361

---

### DOC-002: folder_repo.py updated_at Column in OFFLINE Mode ✅ FIXED

- **Fixed:** Session 60+ (2026-02-01)
- **Component:** `server/repositories/sqlite/folder_repo.py`
- **Reference:** DOC-002

**Problem:** SQLite folder_repo.py was using `updated_at` column in OFFLINE mode SQL statements, but the `offline_folders` table schema does not have this column. Only `created_at` exists.

**Solution:** Removed `updated_at` from all OFFLINE mode SQL statements in 5 methods:
1. `rename()` - Removed `updated_at = ?` from UPDATE SET clause
2. `move()` - Removed `updated_at = ?` from UPDATE SET clause
3. `move_cross_project()` - Removed `updated_at = ?` from UPDATE SET clause
4. `copy()` - Removed `updated_at` from INSERT columns and VALUES
5. `_copy_folder_contents()` - Removed `updated_at` from INSERT columns and VALUES

**Files Modified:**
- `server/repositories/sqlite/folder_repo.py` - 5 methods fixed

**Result:** All folder operations now work correctly in OFFLINE mode without "no such column: updated_at" errors.

---

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

### QA-SCHEMA-001: SQLite Missing QA Columns ✅ FIXED

- **Fixed:** Session 60+ (5-agent parallel review)
- **Component:** SQLite offline_rows schema + QA repositories

**Problem:** SQLite `offline_rows` table missing QA columns that PostgreSQL had.

**Solution:**
1. Added `updated_by`, `qa_checked_at`, `qa_flag_count` to `offline_schema.sql`
2. Added `idx_offline_rows_qa_flagged` index
3. Updated SQLite `qa_repo.py` - `update_row_qa_count()` now works
4. Fixed PostgreSQL `qa_repo.py` - was ALSO missing `update_row_qa_count()` calls!

**Files Modified:**
- `server/database/offline_schema.sql` - Added 3 columns + index
- `server/database/offline.py` - Added migration for existing DBs
- `server/repositories/sqlite/qa_repo.py` - Real implementation
- `server/repositories/postgresql/qa_repo.py` - Added missing calls

**Result:** Full parity between PostgreSQL and SQLite for QA operations.

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
