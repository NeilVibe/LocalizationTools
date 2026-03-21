---
phase: 51-offline-production-bundle
plan: 02
subsystem: testing
tags: [pytest, sqlite, offline, factory-pattern, smoke-test, repository-audit]

requires:
  - phase: 51-offline-production-bundle
    provides: "Plan 01 established WAL mode, vgmstream bundling, light mode detection"
provides:
  - "31 tests verifying all 9 factory/repo paths work correctly in OFFLINE and SERVER-LOCAL SQLite modes"
  - "Smoke tests confirming no service imports PostgreSQL drivers directly"
  - "Verification that embedding engine light mode and media converter don't crash without dependencies"
affects: [offline-bundle, packaging, ci]

tech-stack:
  added: []
  patterns: ["factory audit via isinstance + schema_mode assertion", "AST-based import scanning for dependency isolation"]

key-files:
  created:
    - tests/test_offline_bundle.py
  modified: []

key-decisions:
  - "Used AST parsing (not regex) to detect PostgreSQL driver imports in service layer"
  - "RoutingRowRepository._primary accessed directly for server-local mode assertion (internal attribute, test-only)"

patterns-established:
  - "Factory audit pattern: mock Request headers + config patch -> verify repo type + schema_mode"
  - "Import isolation smoke test: AST walk over service files to detect prohibited imports"

requirements-completed: [OFFLINE-04, OFFLINE-05]

duration: 2min
completed: 2026-03-21
---

# Phase 51 Plan 02: Factory/Repo Audit + Offline Smoke Tests Summary

**31 pytest tests auditing all 9 factory/repository paths for SQLite correctness in OFFLINE and SERVER-LOCAL modes, plus smoke tests confirming no PostgreSQL hard-dependencies in the service layer**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-21T13:27:48Z
- **Completed:** 2026-03-21T13:30:13Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- All 9 factory functions verified to produce correct SQLite repo instances with SchemaMode.OFFLINE
- All 9 factory functions verified to produce correct SQLite repo instances with SchemaMode.SERVER in server-local mode
- Row repo routing wrapper (RoutingRowRepository) confirmed in server-local mode
- Zero PostgreSQL driver imports found in server/tools/ldm/services/ (AST scan)
- Embedding engine light mode and media converter vgmstream search confirmed crash-free

## Task Commits

Each task was committed atomically:

1. **Task 1: Factory/Repo audit test covering all 9 repositories** - `d2695b75` (test)

## Files Created/Modified
- `tests/test_offline_bundle.py` - 31 tests: mode detection (5), offline factory audit (9), server-local factory audit (9), smoke tests (8)

## Decisions Made
- Used AST parsing instead of regex for PostgreSQL import scanning -- more reliable, handles `from X import Y` correctly
- Accessed RoutingRowRepository._primary directly in tests -- internal attribute but necessary for verifying schema_mode on wrapped repo

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed config patching for _is_server_local test**
- **Found during:** Task 1 (first test run)
- **Issue:** Patching `server.repositories.factory.config` failed because `_is_server_local()` uses `from server import config` (lazy import), not a module-level attribute
- **Fix:** Changed to `@patch("server.config.ACTIVE_DATABASE_TYPE", "sqlite")` which patches the actual config module
- **Files modified:** tests/test_offline_bundle.py
- **Verification:** Test passes

**2. [Rule 1 - Bug] Fixed RoutingRowRepository attribute name**
- **Found during:** Task 1 (first test run)
- **Issue:** Plan referenced `primary_repo` but actual attribute is `_primary` (private)
- **Fix:** Changed assertion from `repo.primary_repo` to `repo._primary`
- **Files modified:** tests/test_offline_bundle.py
- **Verification:** Test passes

---

**Total deviations:** 2 auto-fixed (2 bugs)
**Impact on plan:** Both fixes necessary for test correctness. No scope creep.

## Issues Encountered
None beyond the auto-fixed deviations above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All 9 factory/repo paths confirmed working in SQLite-only modes
- Phase 51 (Offline Production Bundle) plan 02 complete -- both plans done
- Ready for phase verification

## Self-Check

Verified below.

---
*Phase: 51-offline-production-bundle*
*Completed: 2026-03-21*
