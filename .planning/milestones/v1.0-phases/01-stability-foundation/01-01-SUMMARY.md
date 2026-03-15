---
phase: 01-stability-foundation
plan: 01
subsystem: testing
tags: [pytest, sqlite, schema-drift, parity-testing, database]

# Dependency graph
requires: []
provides:
  - "DbMode enum and db_mode parametrization fixture for 3-mode testing"
  - "clean_db fixture creating temp SQLite databases per mode"
  - "9 repository fixtures (platform, project, folder, file, row, tm, qa, trash, capability)"
  - "assert_equivalent helper for cross-mode comparison"
  - "game_data_factory fixture with Korean/English game strings"
  - "Schema drift guard catching TABLE_MAP gaps, OFFLINE_ONLY_COLUMNS staleness, SQL dialect violations"
  - "Terminology rename: sqlite_fallback -> server_local"
affects: [01-02, 01-03, 06-offline-validation]

# Tech tracking
tech-stack:
  added: [sqlparse, pytest-timeout]
  patterns: [parametrized-db-mode-testing, known-drift-allowlist]

key-files:
  created:
    - tests/stability/__init__.py
    - tests/stability/conftest.py
    - tests/stability/test_schema_drift.py
  modified:
    - server/repositories/factory.py
    - server/repositories/sqlite/base.py
    - server/database/db_utils.py
    - pytest.ini

key-decisions:
  - "OFFLINE_ONLY_COLUMNS is a global set -- per-table differences (e.g. created_at in offline_rows) cannot be added since _has_column() is table-agnostic"
  - "Known pre-existing schema drift documented in KNOWN_SCHEMA_DRIFT allowlist rather than fixed (out of scope, pre-existing)"
  - "SQL dialect audit only checks non-PostgreSQL repos -- PostgreSQL repos are expected to use PG features"
  - "SQLite foreign_keys PRAGMA is per-connection, not tested as persistent -- WAL mode IS persistent and verified"

patterns-established:
  - "DbMode parametrization: all parity tests use @pytest.fixture(params=[DbMode.ONLINE, DbMode.SERVER_LOCAL, DbMode.OFFLINE])"
  - "Known drift allowlist: KNOWN_SCHEMA_DRIFT dict tracks pre-existing mismatches, test catches only NEW drift"
  - "assert_equivalent: normalizes SQLite 0/1 to bool, ignores volatile fields (id, created_at, updated_at, etc.)"

requirements-completed: [STAB-05, STAB-03]

# Metrics
duration: 9min
completed: 2026-03-14
---

# Phase 1 Plan 01: Parity Test Infrastructure Summary

**Schema drift guard with 6 test functions, 3-mode parametrized fixtures, and sqlite_fallback-to-server_local rename across 27 occurrences**

## Performance

- **Duration:** 9 min
- **Started:** 2026-03-14T07:48:15Z
- **Completed:** 2026-03-14T07:57:30Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Built complete parity test infrastructure with DbMode enum, clean_db fixture, 9 repo fixtures, and game_data_factory
- Schema drift guard caught real bugs: 2 missing OFFLINE_ONLY_COLUMNS entries (memo, error_message) and 5 pre-existing schema mismatches
- Renamed "sqlite_fallback" terminology to "server_local" across all 3 source files (27 occurrences, 0 remaining)
- SQL dialect audit ensures no PostgreSQL-specific constructs leak into SQLite repos

## Task Commits

Each task was committed atomically:

1. **Task 1: Create test infrastructure and terminology rename** - `006a30af` (feat)
2. **Task 2: Schema drift guard and SQL dialect audit tests** - `5ea47714` (feat)

## Files Created/Modified
- `tests/stability/__init__.py` - Package marker
- `tests/stability/conftest.py` - DbMode, fixtures, assert_equivalent, game_data_factory (323 lines)
- `tests/stability/test_schema_drift.py` - 6 schema drift tests (362 lines)
- `server/repositories/factory.py` - Renamed _is_sqlite_fallback to _is_server_local, updated all docstrings
- `server/repositories/sqlite/base.py` - Added memo/error_message to OFFLINE_ONLY_COLUMNS, updated docstrings
- `server/database/db_utils.py` - Updated docstring terminology
- `pytest.ini` - Added stability marker

## Decisions Made
- OFFLINE_ONLY_COLUMNS is global -- per-table column differences (created_at in rows vs files) documented in KNOWN_SCHEMA_DRIFT instead
- SQL dialect audit scoped to non-PostgreSQL repos only (PG repos legitimately use PG features)
- PRAGMA foreign_keys test verifies enablement capability, not persistence (SQLite limitation)
- Pre-existing schema drift documented in allowlist, not fixed (scope boundary)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed incomplete OFFLINE_ONLY_COLUMNS**
- **Found during:** Task 2 (test_offline_only_columns_complete)
- **Issue:** memo and error_message columns exist only in offline schema but were not in OFFLINE_ONLY_COLUMNS
- **Fix:** Added both columns to OFFLINE_ONLY_COLUMNS frozenset
- **Files modified:** server/repositories/sqlite/base.py
- **Verification:** test_offline_only_columns_complete passes
- **Committed in:** 5ea47714 (Task 2 commit)

**2. [Rule 1 - Bug] Fixed SQL dialect test false positives**
- **Found during:** Task 2 (test_no_postgresql_specific_sql_in_repos)
- **Issue:** Test flagged Python datetime.now() as SQL NOW() and flagged PostgreSQL repos for using PG features
- **Fix:** Scoped audit to non-PostgreSQL repos only, matched SQL string patterns instead of raw code
- **Files modified:** tests/stability/test_schema_drift.py
- **Verification:** test_no_postgresql_specific_sql_in_repos passes with zero false positives
- **Committed in:** 5ea47714 (Task 2 commit)

**3. [Rule 1 - Bug] Fixed PRAGMA test for SQLite per-connection semantics**
- **Found during:** Task 2 (test_sqlite_pragmas)
- **Issue:** foreign_keys PRAGMA is per-connection in SQLite, test failed because new connection doesn't inherit it
- **Fix:** Test now verifies WAL (persistent) and verifies foreign_keys CAN be enabled
- **Files modified:** tests/stability/test_schema_drift.py
- **Verification:** test_sqlite_pragmas passes for both server_local and offline modes
- **Committed in:** 5ea47714 (Task 2 commit)

---

**Total deviations:** 3 auto-fixed (3 bugs)
**Impact on plan:** All auto-fixes were necessary for test correctness. No scope creep.

## Issues Encountered
- sqlparse installed for Python 3.11 initially, had to reinstall for Python 3.10 (system python)
- Pre-existing schema drift found in 5 table pairs -- documented in KNOWN_SCHEMA_DRIFT allowlist for future resolution

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Test infrastructure ready for Plan 02 (repository parity tests)
- conftest.py provides all fixtures needed for parametrized cross-mode testing
- Known schema drift documented for future schema alignment work

---
*Phase: 01-stability-foundation*
*Completed: 2026-03-14*
