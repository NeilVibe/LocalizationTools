# Codebase Concerns

**Analysis Date:** 2026-03-14

## Architecture & Design

### asyncio.run() in Event Loop Context

**Issue:** Multiple files use `asyncio.run()` inside async functions that already have a running event loop.

**Files:**
- `server/tools/ldm/pretranslate.py:76, 509, 539` - Calls `asyncio.run()` in PretranslationManager
- `server/tools/shared/tm_loader.py:107-115` - Detects running loop, uses ThreadPoolExecutor workaround
- `server/api/base_tool_api.py:287, 336` - Calls `asyncio.run()` in WebSocket handlers

**Impact:** Runtime error `RuntimeError: asyncio.run() cannot be called from a running event loop`. Breaks offline pretranslation and TM loading in certain conditions.

**Current Status:** Partially mitigated in `tm_loader.py` with ThreadPoolExecutor workaround. Other files still at risk.

**Fix Approach:**
1. Replace all `asyncio.run()` with `asyncio.get_event_loop().run_until_complete()` in sync contexts
2. In async contexts, directly `await` the coroutine instead of wrapping with `asyncio.run()`
3. Create async wrapper functions for functions that bridge sync/async boundaries

---

### ML Components Scattered Across Tool Modules

**Issue:** KR Similar and XLS Transfer embeddings logic is imported directly into LDM, creating tight coupling.

**Files:**
- `server/tools/ldm/tm.py:16` - TODO: Move KR Similar EmbeddingsManager to utils
- `server/tools/ldm/pretranslate.py:272, 372` - TODO: Move XLS Transfer and KR Similar ML components to utils
- `server/tools/ldm/tm_manager.py` - Reuses file handlers but not embeddings logic

**Impact:**
- Hard to reuse embeddings logic across tools
- Difficult to test ML components in isolation
- Tight coupling makes refactoring risky

**Fix Approach:** Create `server/utils/embeddings/` package:
1. Extract `EmbeddingsManager` base class
2. Create tool-specific implementations: `XLSTransferEmbeddingsManager`, `KRSimilarEmbeddingsManager`
3. Export from `server/utils/embeddings/__init__.py`
4. Update imports in LDM, pretranslate, xlstransfer, kr_similar

---

## Performance & Scalability

### TM Index Cache Unbounded Growth Risk

**Issue:** FAISS index cache in `SQLiteTMRepository` has LRU eviction, but cache is per-module instance.

**Files:**
- `server/repositories/sqlite/tm_repo.py:25-26, 1054-1087` - Module-level `_tm_index_cache` with `_TM_INDEX_CACHE_MAX_SIZE = 10`

**Impact:**
- Only 10 TM indexes cached at once (reasonable)
- But no cache warming strategy — first request for a TM always rebuilds index
- Slow first search after server restart or index eviction

**Current Status:** Functional but not optimal. Lock-based thread safety is in place.

**Fix Approach:**
1. Add cache warming on startup: Load top 5-10 most-used TMs into cache
2. Add cache hit/miss metrics to track effectiveness
3. Consider persistent cache (save serialized FAISS indexes to disk)

---

### Virtual Grid Row Height Estimation

**Issue:** VirtualGrid uses estimated row heights that may be inaccurate for CJK (Korean) text with different line wrapping.

**Files:**
- `locaNext/src/lib/components/ldm/VirtualGrid.svelte:30-36` - HEIGHT calculation constants

**Calculation:**
```
CHARS_PER_LINE = 45
LINE_HEIGHT = 26px per line
Actual wrapping varies by font, zoom, and CJK character width
```

**Impact:**
- Scrollbar thumb size may not match actual content
- Jumping when scrolling from estimated to measured rows
- Large cells (800px max) get better measurement via `ResizeObserver` callback, but small cells are estimated

**Current Status:** Partially mitigated by `rowHeightCache` and post-render measurement. Acceptable for most cases.

**Fix Approach:**
1. Use CSS `contain: layout` on grid cells for faster resize detection
2. Add `ResizeObserver` for ALL rows, not just during scroll
3. Adjust `CHARS_PER_LINE` based on current font (measure once at startup)

---

## Test Coverage Gaps

### TM Assignment & Multi-Language Support

**Issue:** TM assignment logic (platform/project/folder levels) lacks comprehensive test coverage.

**Files:**
- `server/tools/ldm/routes/tm_assignment.py` - Assignment CRUD
- `server/repositories/postgresql/tm_repo.py` - Assignment queries
- `locaNext/src/lib/components/ldm/TMExplorerTree.svelte` - UI for assignment

**What's Not Tested:**
- Cascade behavior: Does deleting a project cascade delete its TM assignments?
- Conflict resolution: If TM assigned at platform AND project level, which takes precedence?
- Multi-language scenarios: TM for KR→EN assigned to project with DE→FR folder

**Risk:** Medium. Bug in assignment logic could silently select wrong TM.

**Priority:** High — affects translation quality directly.

---

### Offline Sync Edge Cases

**Issue:** Sync between PostgreSQL and SQLite in offline mode has incomplete test coverage.

**Files:**
- `server/tools/ldm/routes/sync.py:1-100` - Sync orchestration
- `server/services/sync_service.py` - Core sync logic
- `server/database/offline.py` - Offline DB management

**Untested Scenarios:**
- Network drops mid-sync (partial upload)
- User edits same row in offline + online mode simultaneously
- Large file downloads (>100MB) with resume/retry
- SQLite transaction rollback on conflict

**Current Status:** Basic sync works. Complex scenarios may fail silently.

**Fix Approach:**
1. Add integration tests for sync failure scenarios
2. Implement transaction isolation levels for conflict detection
3. Add sync log with timestamps for debugging

---

### Background Tasks Placeholder Implementation

**Issue:** Background task system has empty placeholder implementations.

**Files:**
- `server/tasks/background_tasks.py:22, 47, 70, 95` - Four TODO comments for:
  - `_stats_aggregation_task()` - Statistics collection
  - `_cleanup_task()` - Temporary file/session cleanup
  - `_report_generation_task()` - Report generation
  - `_batch_processing_task()` - Batch operation handling

**Impact:**
- Statistics not being collected (affects analytics)
- Old temp files not cleaned up (disk usage grows)
- No report generation capability
- Batch operations may queue forever

**Priority:** Medium — affects operational efficiency, not core functionality.

---

## Security & Reliability

### Session Context Missing in API Logging

**Issue:** API logging can't attribute operations to users in some contexts.

**Files:**
- `server/api/progress_operations.py:111` - `session_id=None` TODO
- `server/utils/client/logger.py:280` - `user_id=None` TODO

**Impact:**
- Audit logs can't fully trace user actions
- Harder to debug multi-user issues
- Compliance gaps for audit trails

**Fix Approach:**
1. Inject session context via FastAPI Depends
2. Store session_id in thread-local or context var
3. Retrieve automatically in logger

---

### Direct print() in CLI Tools

**Issue:** Some tools use print() for output instead of logger.

**Files:**
- Multiple in `server/tools/xlstransfer/cli/`
- Multiple in `server/tools/kr_similar/`

**Status:** By design. CLI tools NEED stdout/stderr for:
- Progress tracking via stderr
- JSON output for subprocess piping

**This is NOT a bug** — documented in ISSUES_TO_FIX.md as "TECH-DEBT-002: Closed as by design"

---

### XML Linebreak Handling (Critical)

**Issue:** XML files use `<br/>` tags for newlines. Must be preserved through ALL operations.

**Files:**
- `server/tools/ldm/file_handlers/xml_handler.py` - Read/write XML
- `server/database/db_utils.py` - TM entry storage
- `RessourcesForCodingTheProject/NewScripts/QuickTranslate/` - Tools that process XML

**Pattern:**
```xml
<!-- CORRECT -->
KR="첫 번째 줄<br/>두 번째 줄"

<!-- WRONG (breaks parsing) -->
KR="첫 번째 줄&#10;두 번째 줄"
```

**Impact:** Any tool that replaces `<br/>` with `\n` or `&#10;` breaks XML parsing for multi-line text.

**Current Status:** LocaNext correctly preserves `<br/>`. External tools must follow this pattern.

---

### Large File Handling

**Issue:** No explicit limits on file upload size or row count per file.

**Files:**
- `server/tools/ldm/routes/files.py` - File upload endpoint
- `server/tools/ldm/tm_manager.py` - TM upload with bulk_insert
- `locaNext/src/lib/components/ldm/VirtualGrid.svelte` - VirtualGrid rendering

**Potential Issues:**
- User uploads 1GB file → OOM on parsing
- TM with 1M entries → FAISS index build timeout
- Virtual grid with 100k rows → browser memory spike

**Current Mitigations:**
- VirtualGrid uses pagination (PAGE_SIZE = 100 rows)
- TM bulk insert is optimized with COPY TEXT
- No explicit file size cap

**Recommended Limits:**
- File upload: 500MB (configurable)
- TM entries: 1M per TM
- Grid virtual scroll: 500k rows max

---

## Fragile Areas

### offline.py Schema Initialization & Migrations

**Issue:** SQLite schema initialization uses sync sqlite3 at startup. Migrations run on every startup with silent column-exists checks.

**Files:**
- `server/database/offline.py:94-130` - `_run_migrations_sync()` method
- `server/database/offline_schema.sql:384-393` - Commented-out ALTER TABLE statements

**Current Pattern:**
```python
# Just run CREATE TABLE above on fresh installs,
# use migration logic below for existing DBs
```

**Risk:** Difficult to debug if migrations fail silently. No version tracking.

**Safe Modification:**
1. Add explicit `schema_version` column to track migration state
2. Only run migrations if version < current
3. Log each migration attempt
4. Add rollback mechanism

---

### Svelte 5 Rune Usage Inconsistency

**Issue:** Most components correctly use Svelte 5 runes (`$state`, `$derived`, `$effect`), but some edge cases exist.

**Files:**
- `locaNext/src/lib/components/` - 45 .svelte files with 536 rune instances
- Only 1 `export let` found (rest are `$state`)

**Observed:**
- {#each} loops generally use keys correctly
- Some loops missing key identifiers (e.g., `{#each GAMES as game}` instead of `{#each GAMES as game (game)}`)

**Impact:** Key-less loops may render incorrectly when list order changes.

**Safe Modification:** Add `(item.id)` key to ALL {#each} loops, even if items appear stable.

---

### Database Connection Pool Configuration

**Issue:** PostgreSQL pool settings may be suboptimal for concurrent load.

**Files:**
- `server/database/db_setup.py:132-136` - Pool configuration

**Current Settings:**
```python
pool_size=config.DB_POOL_SIZE           # Default likely 5-10
pool_recycle=config.DB_POOL_RECYCLE     # Helps with connection reuse
pool_pre_ping=True                      # Good - tests connection before use
```

**Risk:**
- If `DB_POOL_SIZE` is too small, concurrent requests queue up
- If too large, PostgreSQL connection limit exceeded
- No monitoring of pool exhaustion

**Current Status:** Likely works for current user base. May need tuning at scale.

**Improvement Path:**
1. Add pool statistics logging (current/max connections)
2. Alert if pool exhaustion detected
3. Recommend pool_size = (num_workers * 2) + max_overflow

---

## Technical Debt

### Service Extraction Incomplete

**Issue:** Services stub files exist but lack implementation.

**Files:**
- `server/tools/ldm/services/tm_service.py:4` - TODO: Extract from tm_manager.py
- `server/tools/ldm/services/entry_service.py:4` - TODO: Extract from tm_manager.py

**Impact:** Logic still tightly coupled in `tm_manager.py` (1133 lines). Makes testing harder.

**Fix Approach:**
1. Create `TMListing`, `TMImport`, `TMDeletion` service classes
2. Each handles one TM operation
3. Inject repository via constructor
4. Update routes to use services instead of calling manager directly

---

### File Builders Not Migrated

**Issue:** File builders (TXT, XML, Excel export) are stub functions.

**Files:**
- `server/tools/ldm/helpers/file_builders.py:4-25` - All marked TODO

**Current State:**
```python
def build_txt_file(rows):
    """Build a TXT file from rows. TODO: Migrate from api.py"""
    pass
```

**Impact:** Export functionality may be calling legacy code from `api.py` lines 2623-2784.

**Fix Approach:**
1. Copy/refactor export logic from `api.py` to `file_builders.py`
2. Update all export endpoints to use new functions
3. Remove legacy functions from `api.py`

---

## Known Issues - Recently Fixed

The following issues have been resolved and should remain fixed:

### AIOSQLITE Migration (Session 60) ✅
- 11 missing `await` statements fixed
- `sqlite3.Row` → `dict()` conversions added
- Status: Fixed, monitor for edge cases

### Repository Pattern Violations ✅
- ARCH-002: Factory violations in `tm_crud.py` - Fixed via check_name_exists()
- ROUTE-001: Direct SQLite imports - Fixed via RoutingRowRepository
- Status: All violations closed via architecture refactoring

### Offline Mode Parity ✅
- LIMIT-001: TM search offline - Fixed via FAISS fallback
- LIMIT-002: TM pretranslation offline - Fixed via TMLoader
- DOC-002: SQLite schema offline columns - Fixed via migration
- Status: Full offline feature parity achieved

---

## Monitoring Recommendations

1. **Cache Hit Ratio:** Monitor FAISS index cache effectiveness in `SQLiteTMRepository`
2. **Sync Performance:** Track sync duration for files >10MB
3. **Virtual Grid Performance:** Monitor VirtualGrid scroll smoothness with large files (>50k rows)
4. **Database Pool:** Log connection pool exhaustion events
5. **TM Assignment Correctness:** Add logging when TM selection happens to verify correct precedence

---

*Concerns audit: 2026-03-14*
