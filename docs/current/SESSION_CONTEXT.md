# Session Context

> Last Updated: 2026-02-01 (Session 61)

---

## SESSION 61: Folder Schema Mismatch Fix - OFFLINE Mode Fully Working

### What Was Done

1. **Fixed folder_repo.py schema mismatch** - 5 methods using `updated_at` column that doesn't exist in SQLite
2. **Added QA columns to offline_rows** (previous session carry-over)
3. **Ran 7+ debug agents** to identify and verify issues
4. **Created DOC-002** for folder schema issue documentation
5. **All folder operations now work in OFFLINE mode**

### The Problem

SQLite folder repository was referencing `updated_at` column that doesn't exist in the `offline_folders` table schema. This caused 500 errors on all folder operations in OFFLINE mode.

### Files Modified

| File | Change |
|------|--------|
| `server/repositories/sqlite/folder_repo.py` | Removed `updated_at` from 5 methods |
| `docs/history/DOC-002_FOLDER_SCHEMA_MISMATCH.md` | **NEW** - Issue documentation |

### Methods Fixed in folder_repo.py

| Method | Line | Issue |
|--------|------|-------|
| `get_by_id()` | ~70 | SELECT included `updated_at` |
| `get_by_project()` | ~100 | SELECT included `updated_at` |
| `create()` | ~130 | INSERT included `updated_at` |
| `update()` | ~165 | UPDATE SET `updated_at` |
| `_row_to_folder()` | ~220 | Dict access to `updated_at` |

### Debug Agent Results

| Agent | Task | Finding |
|-------|------|---------|
| Agent 1 | Schema verification | `offline_folders` has no `updated_at` |
| Agent 2 | Method audit | 5 methods with schema mismatch |
| Agent 3 | Code fix | Removed all `updated_at` references |
| Agent 4 | Verification | All folder operations working |
| Agent 5-7 | E2E testing | OFFLINE mode fully functional |

### Verification Status

| Item | Status | Details |
|------|--------|---------|
| Folder creation | ✅ Verified | Working in OFFLINE mode |
| Agent cleanup | ✅ Complete | 15 agents → 8 agents |
| gdp-debugger | ✅ Consolidated | All debugging in one agent |
| Documentation | ✅ Created | Parallel agent docs added |

### Architecture Note

**SQLite offline schema is intentionally simpler:**
- PostgreSQL `ldm_folders`: includes `updated_at` for sync tracking
- SQLite `offline_folders`: no `updated_at` (local-only, no sync needed)

This is by design - offline storage doesn't need timestamp tracking.

---

## Agent Workflow Patterns Used

This session demonstrated effective multi-agent parallel workflows for debugging, analysis, verification, and documentation tasks.

### Pattern 1: Parallel Debugging (7 Agents)

Used to investigate and fix schema mismatch issues across multiple files simultaneously.

| Agent | Focus | Finding |
|-------|-------|---------|
| Agent 1 | Schema verification | `offline_folders` has no `updated_at` column |
| Agent 2 | Method audit | 5 methods in folder_repo.py reference non-existent column |
| Agent 3 | Code fix implementation | Removed all `updated_at` references |
| Agent 4 | Post-fix verification | All folder operations working |
| Agents 5-7 | E2E testing | OFFLINE mode fully functional end-to-end |

**Key insight:** Parallel debugging catches issues faster than sequential investigation. Each agent can focus on one aspect without context-switching overhead.

### Pattern 2: Analysis Flow (analyze → discuss → conclude → document → fix)

A structured approach for complex issues:

1. **Analyze** - Multiple agents read code and logs in parallel
2. **Discuss** - Cross-reference findings to identify root cause
3. **Conclude** - Reach consensus on the fix approach
4. **Document** - Create DOC-XXX issue documentation
5. **Fix** - Implement the solution with verification

### Pattern 3: Parallel Verification (9 Agents)

Used in Session 60+ for comprehensive code review after major changes:

| Agent Group | Count | Scope |
|-------------|-------|-------|
| Code Review | 6 | Thread safety, cache eviction, stale cache, logging, field parity, direct imports |
| TM/QA Review | 3 | TM search, pretranslation, QA functions |

**Findings per agent:**
- Thread-unsafe cache → Added `threading.Lock`
- No cache eviction → LRU with `MAX_SIZE = 10`
- Stale cache on entry change → Cache invalidation in CRUD methods
- `traceback.print_exc()` → `logger.exception()`
- PostgreSQL/SQLite field parity → `get_all_entries()` returns only documented fields
- Direct SQLite imports → RoutingRowRepository pattern

### Pattern 4: Documentation (1 Agent Per Doc)

For documentation tasks, assign one agent per file to avoid merge conflicts:

| Doc File | Agent Task |
|----------|------------|
| DOC-002_FOLDER_SCHEMA_MISMATCH.md | Document issue + root cause + fix |
| DEBUG_AND_SUBAGENTS.md | Full subagent guide |
| QUICK_DEBUG_REFERENCE.md | Quick log commands |
| E2E_TEST_RESULTS_SESSION60.md | Full E2E test log |

### Agent Workflow Best Practices

1. **Parallel > Sequential** - Always prefer parallel agents when tasks are independent
2. **Clear scope per agent** - Each agent gets ONE specific focus area
3. **Consolidate findings** - Main agent synthesizes all results
4. **Verify fixes** - Dedicate agents specifically to verification (not just fixing)
5. **Document discoveries** - Capture patterns in docs for future sessions

### When to Use Each Pattern

| Situation | Pattern | Agent Count |
|-----------|---------|-------------|
| Bug hunting | Parallel Debugging | 5-10 |
| Complex issue analysis | Analysis Flow | 3-5 |
| Post-change review | Parallel Verification | 6-12 |
| Creating/updating docs | 1 Per Doc | 1 each |
| Simple fix | Single agent | 1 |

---

## SESSION 60+: Master Architecture Cleanup - LIMIT-001/002 Fixed

### What Was Done

1. **LIMIT-001 Fixed**: FAISS-based TM suggestions for offline mode
2. **LIMIT-002 Fixed**: Offline pretranslation now works (TMLoader)
3. **Route Cleanup**: Fixed rows.py direct SQLite imports
4. **Documentation**: Updated ISSUES_TO_FIX.md

### Files Created/Modified

| File | Change |
|------|--------|
| `server/repositories/sqlite/tm_repo.py` | FAISS `search_similar()` + `get_all_entries()` + thread-safe cache |
| `server/repositories/postgresql/tm_repo.py` | Added `get_all_entries()` |
| `server/repositories/interfaces/tm_repository.py` | Added `get_all_entries()` abstract |
| `server/tools/shared/tm_loader.py` | **NEW** - Unified TM loader |
| `server/tools/shared/__init__.py` | Export TMLoader |
| `server/tools/xlstransfer/embeddings.py` | Uses TMLoader + logger fix |
| `server/tools/kr_similar/embeddings.py` | Uses TMLoader + logger fix |
| `server/repositories/routing/row_repo.py` | **NEW** - RoutingRowRepository |
| `server/repositories/routing/__init__.py` | **NEW** - exports |
| `server/repositories/factory.py` | Wraps repos with RoutingRowRepository |
| `server/tools/ldm/routes/rows.py` | Zero direct imports now |
| `docs/current/ISSUES_TO_FIX.md` | Marked LIMIT-001/002 as FIXED |

### Architecture Improvements

**Before:**
- `search_similar()` returned empty list for SQLite
- EmbeddingsManagers queried PostgreSQL directly
- Pretranslation failed offline

**After:**
- `search_similar()` uses FAISS with index caching
- TMLoader detects PostgreSQL vs SQLite automatically
- Full offline pretranslation support

### Key Implementation Details

**TMLoader Auto-Detection:**
```python
# Negative IDs = SQLite offline
# config.ACTIVE_DATABASE_TYPE == "sqlite" = SQLite server
# Otherwise = PostgreSQL
```

**FAISS Index Cache:**
```python
# Module-level cache in tm_repo.py
_tm_index_cache: Dict[int, Dict[str, Any]] = {}
```

### 6-Agent Code Review Findings (All Fixed)

| Finding | Fix |
|---------|-----|
| Thread-unsafe cache | Added `threading.Lock` |
| No cache eviction | LRU with `MAX_SIZE = 10` |
| Stale cache on entry change | Cache invalidation in CRUD methods |
| `traceback.print_exc()` | → `logger.exception()` |
| PostgreSQL/SQLite field parity | `get_all_entries()` returns only documented fields |
| Direct SQLite imports | RoutingRowRepository pattern |

### 5-Agent TM/QA Review Results

| Area | Status | Notes |
|------|--------|-------|
| TM Search | ✅ Works | FAISS with caching |
| TM Pretranslation | ✅ Works | TMLoader handles offline |
| Offline TM | ✅ Works | All 23 interface methods |
| RoutingRowRepository | ✅ Clean | Zero direct imports |
| QA Functions | ⚠️ Works | SQLite missing `qa_checked_at`, `qa_flag_count` |

### Open Issues

**0 open issues** - All LIMIT-001, LIMIT-002, and route violations fixed.

**Known Limitation:** SQLite QA schema missing 2 columns (non-blocking).

---

## SESSION 60: aiosqlite Bug Fixes + E2E Testing + Debug Documentation

### What Was Done

1. **Found and fixed 11 aiosqlite migration bugs** in Offline Storage mode
2. **Created comprehensive debug documentation** with subagent guide
3. **Ran full E2E integration test** - all core functionality verified
4. **Discovered limitation**: Offline TMs can't use `standard` pretranslation

### Bugs Fixed (12 total)

| File | Issue | Fix |
|------|-------|-----|
| `files.py:570` | Missing `await` on `remove_subscription()` | Added `await` |
| `files.py:1466` | Missing `await` on `create_local_file()` | Added `await` |
| `files.py:1478` | Missing `await` on `add_rows_to_local_file()` | Added `await` |
| `pretranslate.py:75` | Sync calling async | Used `asyncio.run()` |
| `pretranslate.py:508` | Sync calling async | Used `asyncio.run()` |
| `pretranslate.py:537` | Sync calling async | Used `asyncio.run()` |
| `tm_repo.py:70` | sqlite3.Row without dict() | Added `dict()` |
| `tm_repo.py:102` | sqlite3.Row without dict() | Added `dict()` |
| `tm_repo.py:246` | sqlite3.Row without dict() | Added `dict()` |
| `tm_repo.py:477` | sqlite3.Row without dict() | Added `dict()` |
| `tm_repo.py:33` | Made helper defensive | Added isinstance check |
| **`FilesPage.svelte:646`** | **BUG-042: handleEnterFolder not async** | **Made async + await all 6 calls** |

### Issue Verification (6 Parallel Agents)

| Issue | Verdict | Action |
|-------|---------|--------|
| ARCH-001 | STALE - already fixed | Closed |
| LIMIT-001 | Clarified - pretranslation works, only `/tm/suggest` limited | Updated |
| TECH-DEBT-002 | STALE - intentional CLI design | Closed |
| IMPROVE-001 | STALE - architecturally sound | Closed |
| DOCS-001 | STALE - file reduced 91% | Closed |
| BUG-042 | **REAL + WORSE** - affects ALL navigation | **Fixed** |

### E2E Test Results

| Test | Status |
|------|--------|
| Create folder in Offline Storage | ✅ PASS |
| Upload file to folder | ✅ PASS |
| Register file as TM | ✅ PASS |
| TM appears in same folder | ✅ PASS |
| Activate TM | ✅ PASS |
| Run QA on file | ✅ PASS |
| Update row translations | ✅ PASS |
| Pretranslation with SQLite TM | ⚠️ LIMITATION |

### Documentation Created

| File | Content |
|------|---------|
| `docs/protocols/DEBUG_AND_SUBAGENTS.md` | Full subagent guide + parallel debugging |
| `docs/protocols/QUICK_DEBUG_REFERENCE.md` | Quick log commands + common errors |
| `docs/protocols/E2E_TEST_RESULTS_SESSION60.md` | Full E2E test log |

### Key Insight

**Always test BOTH code paths:**
- PostgreSQL path (admin user)
- SQLite path (OFFLINE_MODE user)

Session 59 fixed PostgreSQL path. Session 60 found SQLite path had 11 bugs!

---

## SESSION 60 TODO (Deferred): Schema-Aware SQLite Repos

**Full plan:** [NEXT_SESSION_TODO.md](NEXT_SESSION_TODO.md)
**Time:** 8-12 hours
**Issue:** ARCH-001

### The Problem

3 layer violations where PostgreSQL repos check SQLite mode internally:
```
postgresql/row_repo.py:423
postgresql/row_repo.py:598
postgresql/tm_repo.py:1001
```

### The Solution

Make SQLite repos schema-aware. Factory picks the right mode.

```
Factory:
├─ Offline mode  → SQLiteTMRepository(schema_mode="offline")  → offline_* tables
├─ Server SQLite → SQLiteTMRepository(schema_mode="server")   → ldm_* tables
└─ PostgreSQL    → PostgreSQLTMRepository(db, user)           → ldm_* tables
```

PostgreSQL repos stay PURE. No SQLite checks inside them.

---

## SESSION 59: aiosqlite Migration + SQLite Mode Fixes ✅

### What Was Done

Complete aiosqlite migration (Phases 1-6) and critical fix for PostgreSQL repos running in SQLite fallback mode.

### Build Journey (12 builds!)

| Build | Issue | Fix |
|-------|-------|-----|
| 504-505 | aiosqlite migration initial | Async infrastructure |
| 506 | Svelte 4 `export let` in ColorText | Changed to `$props()` |
| 507 | `config.POSTGRES_URL` missing | Fixed to `POSTGRES_DATABASE_URL` |
| 508-511 | Server hanging "Creating tables..." | SQLite cleanup timing, 60s timeout |
| 512-514 | `no such function: similarity` | Skip markers (wrong approach) |
| 515 | 500 on list_projects, create_folder | Factory returning wrong repos |
| **516** | **All tests pass** | **PostgreSQL repos handle SQLite gracefully** |

### Root Cause Analysis

**Problem:** When PostgreSQL unavailable, factory was returning SQLite repos. But:
- SQLite repos use **OFFLINE schema**: `offline_projects`, `offline_folders`
- Server creates **STANDARD schema**: `ldm_projects`, `ldm_folders`
- These are DIFFERENT tables → 500 errors

**Solution:**
1. Factory stays with PostgreSQL repos (they work with standard schema)
2. PostgreSQL repos check `config.ACTIVE_DATABASE_TYPE` and return empty for similarity functions

### Architecture Clarified

```
TWO DIFFERENT SQLITE USE CASES:

1. SERVER SQLITE FALLBACK (when PostgreSQL unavailable)
   - Uses STANDARD schema: ldm_projects, ldm_folders, ldm_files
   - Uses PostgreSQL repos
   - Similarity functions return empty (graceful degradation)

2. OFFLINE MODE (user's local data)
   - Uses OFFLINE schema: offline_projects, offline_folders
   - Uses SQLite repos
   - Triggered by "Bearer OFFLINE_MODE_" auth token
```

### Files Modified (Backend)

| File | Change |
|------|--------|
| `server/repositories/factory.py` | Clarified offline mode detection, removed unused functions |
| `server/repositories/postgresql/row_repo.py` | SQLite checks for `suggest_similar()`, `_fuzzy_search()` |
| `server/repositories/postgresql/tm_repo.py` | SQLite check for `search_similar()` |
| `tests/api/test_p3_offline_sync.py` | Skip markers for PostgreSQL-required tests |
| `tests/api/test_generated_stubs.py` | PostgreSQL connection check for skip markers |
| `.gitea/workflows/build.yml` | SQLite cleanup timing, 60s timeout |

### Code Review Fixes

After Build 516 succeeded, ran 4 parallel review agents:

**Backend:**
- Removed unused functions from `factory.py`
- Moved `text` import to module level in `row_repo.py`

**Frontend (13 `{#each}` keys added):**
| Component | Fixed Loops |
|-----------|-------------|
| TMQAPanel | `tmMatches`, `qaIssues` |
| ExplorerSearch | `results` |
| TMManager | `tms` |
| ColorText | `segments` |
| Breadcrumb | `path` |
| TMUploadModal | `languages` (2) |
| PreferencesModal | `fontSizes`, `fontFamilies`, `fontColors` |
| VirtualGrid | `searchModeOptions`, `searchFieldOptions`, `sourceColors` |

### Build Results

| Platform | Build | Status |
|----------|-------|--------|
| GitHub | 516 | ✅ SUCCESS (15m52s) |
| Gitea | 516 | ✅ SUCCESS |

### Key Commits

```
dbbcdec - Cleanup: Code review fixes from Build 516 review
d3b9976 - Trigger Build 516
9a2f681 - Fix: PostgreSQL repos gracefully handle SQLite mode
```

---

## SESSION 58: Project Health Check + Mac Build Prep ✅

### What Was Done

1. **Project Status Review**
   - Verified Windows build stable (v26.118.1916)
   - Confirmed 137 issues fixed, 1,400+ tests passing
   - All 4 tools working (LDM, XLS Transfer, Quick Search, KR Similar)

2. **Tech Debt Audit**
   - Found 40+ print() statements (MEDIUM - documented, deferred)
   - Found 4 Svelte 4 deprecated `$:` syntax → **FIXED**
   - AsyncSessionWrapper fake async → **FIXED in Session 59**

3. **GitHub vs Gitea Sync**
   - Gitea was 14 commits behind GitHub
   - Synced: `git push gitea main` ✅
   - Discovered: GitHub HAS Mac builds, Gitea Windows-only

4. **CI/CD Clarification**
   - **GitHub**: Builds Windows + macOS (dual platform)
   - **Gitea**: Builds Windows only (local runner)

---

## SESSION 57: LanguageDataExporter v2.0 - Correction Workflow ✅

### What Was Built

Complete LQA correction workflow for LanguageDataExporter with 3 major features:

| Feature | Description | Status |
|---------|-------------|--------|
| **Column Order Change** | New column structure with Correction column | ✅ |
| **Prepare For Submit** | Transform files for LQA submission | ✅ |
| **Progress Tracker** | Track correction progress weekly | ✅ |

### New Column Structure

**EU Languages (6 columns):**
```
StrOrigin | ENG from LOC | Str | Correction | Category | StringID
```

**Asian Languages (5 columns):**
```
StrOrigin | Str | Correction | Category | StringID
```

---

## Recent Sessions Summary

| Session | Achievement |
|---------|-------------|
| **61** | Folder schema mismatch fix + OFFLINE mode fully working |
| **60+** | LIMIT-001/002 Fixed + RoutingRowRepository + 6-agent review |
| **60** | aiosqlite bug fixes (11 bugs) + E2E testing + Debug docs |
| **59** | aiosqlite migration + SQLite mode fix (Build 516) |
| **58** | Project health check + Mac build prep |
| **57** | LanguageDataExporter v2.0 - Correction Workflow |

---

## Technical Debt Status

| Issue | Status | Notes |
|-------|--------|-------|
| AsyncSessionWrapper fakes async | ✅ **FIXED** | aiosqlite migration complete |
| print() → logger | DEFERRED | 40+ instances, non-critical |
| SQLite repos use private methods | DOCUMENTED | Working as designed |

---

## Quick Commands

```bash
# Start Gitea for build
./scripts/gitea_control.sh start

# Trigger builds
echo "Build" >> BUILD_TRIGGER.txt && git add -A && git commit -m "Build" && git push origin main
echo "Build NNN" >> GITEA_TRIGGER.txt && git push gitea main

# Check build status
gh run list --limit 3  # GitHub
python3 -c "import sqlite3; ..."  # Gitea (see CLAUDE.md)

# Stop Gitea
./scripts/gitea_control.sh stop
```

---

*Session 61 | Build 524 | Folder Schema Fix + OFFLINE Mode Fully Working*
