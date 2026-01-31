# Session Context

> Last Updated: 2026-01-31 (Session 60+)

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
| `server/repositories/sqlite/tm_repo.py` | FAISS `search_similar()` + `get_all_entries()` |
| `server/repositories/postgresql/tm_repo.py` | Added `get_all_entries()` |
| `server/repositories/interfaces/tm_repository.py` | Added `get_all_entries()` abstract |
| `server/tools/shared/tm_loader.py` | **NEW** - Unified TM loader |
| `server/tools/shared/__init__.py` | Export TMLoader |
| `server/tools/xlstransfer/embeddings.py` | Uses TMLoader |
| `server/tools/kr_similar/embeddings.py` | Uses TMLoader |
| `server/tools/ldm/routes/rows.py` | Added SchemaMode to imports |
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

### Open Issues

**0 open issues** - All LIMIT-001, LIMIT-002, and route violations fixed.

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
| **60** | aiosqlite bug fixes (11 bugs) + E2E testing + Debug docs |
| **59** | aiosqlite migration + SQLite mode fix (Build 516) |
| **58** | Project health check + Mac build prep |
| **57** | LanguageDataExporter v2.0 - Correction Workflow |
| **56** | QACompiler Progress Tracker Manager Stats Fix |

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

*Session 60 | Build 522 SUCCESS | aiosqlite Bug Fixes Complete*
