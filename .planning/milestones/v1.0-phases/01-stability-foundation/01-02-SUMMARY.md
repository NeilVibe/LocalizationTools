---
phase: 01-stability-foundation
plan: 02
subsystem: testing
tags: [pytest, sqlite, parity-testing, database, repository-pattern, asyncio]

# Dependency graph
requires:
  - "01-01: DbMode enum, clean_db fixture, 9 repo fixtures, assert_equivalent, game_data_factory"
provides:
  - "9 repository parity test files covering ~95 interface methods across server_local and offline modes"
  - "451 total test cases (including schema drift tests from 01-01)"
  - "2 TM repo bug fixes (owner_id missing in server mode, sqlite3.Row .get() crash)"
affects: [01-03, 06-offline-validation]

# Tech tracking
tech-stack:
  added: []
  patterns: [async-test-pattern, helper-hierarchy-creation, stub-degradation-testing]

key-files:
  created:
    - tests/stability/test_platform_repo.py
    - tests/stability/test_project_repo.py
    - tests/stability/test_folder_repo.py
    - tests/stability/test_file_repo.py
    - tests/stability/test_row_repo.py
    - tests/stability/test_tm_repo.py
    - tests/stability/test_qa_repo.py
    - tests/stability/test_trash_repo.py
    - tests/stability/test_capability_repo.py
  modified:
    - tests/stability/conftest.py
    - server/repositories/sqlite/tm_repo.py

key-decisions:
  - "Template DB caching: session-scoped SQLAlchemy create_all reduces per-test setup from 70s to <1ms"
  - "Capability repo tests verify stub degradation not functional parity (SQLite modes are stubs by design)"
  - "TM get_for_scope with all-None params returns empty list (JOIN on assignments excludes unassigned TMs) - tested as-is"

patterns-established:
  - "Async test pattern: pytestmark = [pytest.mark.stability, pytest.mark.asyncio] + async def test_*(repo, db_mode)"
  - "Helper hierarchy creation: _create_file(), _create_hierarchy() helpers build test entity trees"
  - "Stub degradation testing: verify stubs return sensible defaults without exceptions"

requirements-completed: [STAB-02, STAB-03]

# Metrics
duration: 65min
completed: 2026-03-14
---

# Phase 1 Plan 02: Repository Parity Tests Summary

**9 repository parity test files with 451 total test cases exercising ~95 methods across server_local and offline SQLite modes, catching 2 real TM repo bugs**

## Performance

- **Duration:** 65 min
- **Started:** 2026-03-14T09:01:23Z
- **Completed:** 2026-03-14T10:07:03Z
- **Tasks:** 2
- **Files modified:** 11

## Accomplishments
- 9 test files covering all repository interfaces: Platform, Project, Folder, File, Row, TM, QA, Trash, Capability
- 451 total test cases across the full stability suite (including 01-01 schema drift tests)
- Found and fixed 2 real bugs in TM repo: missing owner_id in SERVER mode INSERT, sqlite3.Row .get() crash in get_all_entries
- Korean/English game-realistic data throughout (다크 소울 IV, 새 게임, 계속하기, 설정)
- Capability repo stub degradation verified -- all stubs return sensible defaults without crashing

## Task Commits

Each task was committed atomically:

1. **Task 1: Parity tests for hierarchy repos (Platform, Project, Folder, File, Row)** - `bbc2b893` (feat)
2. **Task 2: Parity tests for TM, QA, Trash, Capability repos** - `fd14c3ff` (feat)

## Files Created/Modified
- `tests/stability/test_platform_repo.py` - 20 tests: CRUD, restriction, assign, search, accessible (207 lines)
- `tests/stability/test_project_repo.py` - 17 tests: CRUD, rename, stats, search, accessible (173 lines)
- `tests/stability/test_folder_repo.py` - 12 tests: CRUD, nested, move, children, search (160 lines)
- `tests/stability/test_file_repo.py` - 14 tests: CRUD, rename, move, copy, rows, search (236 lines)
- `tests/stability/test_row_repo.py` - 13 tests: CRUD, bulk, pagination, history, similarity (222 lines)
- `tests/stability/test_tm_repo.py` - 35 tests: CRUD, assignments, entries, search, tree, linking (360 lines)
- `tests/stability/test_qa_repo.py` - 14 tests: CRUD, resolve, bulk, summary, filter (242 lines)
- `tests/stability/test_trash_repo.py` - 14 tests: CRUD, restore, empty, cleanup, count (171 lines)
- `tests/stability/test_capability_repo.py` - 7 tests: stub degradation for all 7 interface methods (68 lines)
- `tests/stability/conftest.py` - Template DB caching, _make_repo helper, _get_schema_mode helper
- `server/repositories/sqlite/tm_repo.py` - Fixed owner_id and sqlite3.Row bugs

## Decisions Made
- Template DB caching via session-scoped fixture cuts server_local setup from 70s to <1ms per test
- Capability repo tests verify graceful degradation, not parity (SQLite modes are explicit stubs)
- TM `get_for_scope` with all-None params uses JOIN so unassigned TMs don't appear -- documented as correct behavior

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] TM create missing owner_id in SERVER mode**
- **Found during:** Task 2 (test_tm_create)
- **Issue:** SQLiteTMRepository.create() SERVER mode INSERT omitted owner_id column, causing NOT NULL constraint failure on ldm_translation_memories table
- **Fix:** Added owner_id to SERVER mode INSERT statement with fallback to 1
- **Files modified:** server/repositories/sqlite/tm_repo.py
- **Verification:** test_tm_create passes for both server_local and offline modes
- **Committed in:** fd14c3ff (Task 2 commit)

**2. [Rule 1 - Bug] TM get_all_entries using .get() on sqlite3.Row**
- **Found during:** Task 2 (test_tm_get_all_entries)
- **Issue:** get_all_entries() called row.get("string_id") on sqlite3.Row which lacks .get() method, causing AttributeError
- **Fix:** Wrapped with dict(row).get() for safe attribute access
- **Files modified:** server/repositories/sqlite/tm_repo.py
- **Verification:** test_tm_get_all_entries passes for both modes
- **Committed in:** fd14c3ff (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 bugs)
**Impact on plan:** Both bugs were real production issues in the TM repository that would crash in server-local mode. No scope creep.

## Issues Encountered
- Test suite takes ~10 min per file due to SQLAlchemy Base.metadata.create_all (~70s first time) -- mitigated by session-scoped template DB caching
- Online mode tests skipped throughout (PostgreSQL not available in test environment) -- 1/3 of test cases skipped

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Full repository parity regression suite established for server_local and offline modes
- 451 test cases provide permanent stability guard against repository regressions
- Ready for Plan 03 (startup reliability and process lifecycle)
- Known gap: online mode tests require PostgreSQL (tracked, not blocking)

## Self-Check: PASSED

- 9/9 test files found
- 2/2 task commits verified (bbc2b893, fd14c3ff)
- 451 test cases collected

---
*Phase: 01-stability-foundation*
*Completed: 2026-03-14*
