---
phase: 61-merge-internalization
plan: 02
subsystem: merge-engine
tags: [internalization, adapter-rewire, integration-test, pyinstaller-safe]
dependency_graph:
  requires:
    - phase: 61-01
      provides: server.services.merge package (14 modules + _config.py)
  provides:
    - Rewired transfer_adapter.py using server.services.merge (no sys.path/importlib)
    - Integration tests for all 4 MARCH requirements (17 tests)
    - Deprecated transfer_config_shim.py
  affects: [server/api/merge.py, server/services/transfer_adapter.py]
tech_stack:
  added: []
  patterns: [direct-import-over-sys-path, dataclass-config-over-module-shim]
key_files:
  created:
    - tests/test_merge_internalization.py
  modified:
    - server/services/transfer_adapter.py
    - server/services/transfer_config_shim.py
key_decisions:
  - "Direct function imports instead of _qt_modules dict lookup -- functions bound at import time, no lazy importlib"
  - "Keep transfer_config_shim.py with DEPRECATED notice instead of deleting -- prevents ImportError from stale references"
patterns_established:
  - "Merge config via _merge_configure/_merge_reconfigure -- no sys.modules injection"
requirements-completed: [MARCH-01, MARCH-02, MARCH-03, MARCH-04]
duration: 4min
completed: 2026-03-23
---

# Phase 61 Plan 02: Rewire Adapter + Integration Tests Summary

Rewired transfer_adapter.py to import from server.services.merge package (zero sys.path/importlib/config shim), with 17 integration tests verifying all 4 MARCH requirements pass.

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-23T04:57:44Z
- **Completed:** 2026-03-23T05:01:46Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Eliminated all sys.path injection, importlib hacks, and config shim usage from transfer_adapter.py
- server/api/merge.py imports work unchanged (zero modifications needed)
- 17 integration tests covering MARCH-01 (no sys.path), MARCH-02 (3 match types), MARCH-03 (postprocess), MARCH-04 (SSE chain)

## Task Commits

1. **Task 1: Rewire transfer_adapter.py** - `1e811b74` (feat)
2. **Task 2: Integration tests** - `81667065` (test)

## Files Created/Modified

- `server/services/transfer_adapter.py` - Rewired to use server.services.merge imports (removed 119 lines of sys.path/importlib machinery, added 60 lines of clean direct imports)
- `server/services/transfer_config_shim.py` - Marked DEPRECATED (kept for backward compat)
- `tests/test_merge_internalization.py` - 17 integration tests across 5 test classes

## Decisions Made

- Direct function imports at module level instead of lazy importlib loading -- simpler, faster, PyInstaller-compatible
- Kept transfer_config_shim.py with DEPRECATED markers instead of deleting -- prevents potential ImportError if any external reference exists

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed importlib detection test false positive**
- **Found during:** Task 2 (integration tests)
- **Issue:** Test filtering docstring lines was not handling multi-line docstrings correctly, causing false positive on "importlib" in docstring text
- **Fix:** Changed test to check for actual `import importlib` or `importlib.util` statements instead of substring matching
- **Files modified:** tests/test_merge_internalization.py
- **Verification:** All 17 tests pass
- **Committed in:** 81667065 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Minor test logic fix. No scope creep.

## Known Stubs

None -- all adapter wiring is complete, all functions resolve to real implementations.

## Issues Encountered

None.

## Next Phase Readiness

- Phase 61 (merge internalization) is COMPLETE -- both plans shipped
- server.services.merge is a self-contained package with zero QT source tree dependencies
- Ready for Phase 62 (TM Auto-Update Pipeline) or Phase 63 (Performance Instrumentation)

## Self-Check: PASSED

- All 3 files exist on disk
- Both commit hashes (1e811b74, 81667065) verified in git log
- 17/17 integration tests passing

---
*Phase: 61-merge-internalization*
*Completed: 2026-03-23*
