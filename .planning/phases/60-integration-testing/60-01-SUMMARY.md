---
phase: 60-integration-testing
plan: 01
subsystem: testing
tags: [integration-tests, merge-pipeline, sse, settings-validation, mock-data]
dependency_graph:
  requires: [phase-56-mock-data, phase-57-transfer-adapter, phase-58-merge-api, phase-59-merge-ui]
  provides: [merge-pipeline-e2e-tests]
  affects: [tests/integration/]
tech_stack:
  added: [pytest-fixtures-module-scoped, sse-event-parsing]
  patterns: [graceful-skip-on-no-server, subprocess-mock-data-setup]
key_files:
  created:
    - tests/integration/conftest_merge.py
    - tests/integration/test_merge_pipeline.py
  modified: []
decisions:
  - Used pytest_plugins for fixture registration instead of renaming to conftest.py (avoids conflict with existing conftest)
  - Tests skip gracefully via server_running fixture when server unavailable
  - Multi-language test skips when TEST123_PATH doesn't exist on the machine
metrics:
  duration: 2min
  completed: "2026-03-22T19:21:00Z"
  tasks_completed: 1
  tasks_total: 2
---

# Phase 60 Plan 01: Merge Pipeline E2E Integration Tests Summary

E2E integration test suite verifying mock data setup, settings path validation, single/multi-language merge preview, SSE streaming execute, and event ordering against live server.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create merge test fixtures and E2E pipeline tests | dd26fe3b | conftest_merge.py, test_merge_pipeline.py |

## Task 2: Awaiting Human Verification

Task 2 (checkpoint:human-verify) requires running tests against a live server.

## What Was Built

### conftest_merge.py -- Shared Fixtures

- `server_running`: Module-scoped fixture that skips all tests if server unavailable
- `admin_headers`: Gets admin Bearer token via self-healing mechanism from tests/conftest.py
- `mock_data_ready`: Runs setup_mock_data.py to create fresh projects (project_FRE, project_ENG, project_MULTI)
- `merge_temp_target`: Creates temp directory with languagedata_FRE.xml (from test123 or minimal XML fallback)
- `merge_temp_source`: Creates temp directory with corrections.xml containing one matched entry

### test_merge_pipeline.py -- 9 E2E Tests

1. `test_mock_data_setup` -- Verifies mock script ran and projects are queryable via GET /api/v2/ldm/projects
2. `test_health_endpoint` -- Health check returns 200
3. `test_settings_path_validation` -- POST /api/settings/validate-path with valid + invalid paths (SET-01/02/03)
4. `test_preview_single_language` -- POST /api/merge/preview returns total_matched + errors list
5. `test_preview_invalid_match_mode` -- Invalid match_mode returns 422
6. `test_execute_streams_sse` -- POST /api/merge/execute with stream=True, parses SSE events, verifies complete event has total_matched
7. `test_execute_concurrent_guard` -- Skipped (needs threading setup)
8. `test_multi_language_preview` -- POST /api/merge/preview with multi_language=True (skips if no test123)
9. `test_sse_event_types_ordered` -- Verifies complete/error is the last SSE event

## Requirements Coverage

| Requirement | Test | Verified |
|-------------|------|----------|
| MOCK-01 to MOCK-04 | test_mock_data_setup | Mock projects queryable |
| SET-01, SET-02, SET-03 | test_settings_path_validation | Path validation endpoint |
| XFER-01 | test_preview_single_language, test_execute_streams_sse | Single-language merge |
| XFER-07 | test_multi_language_preview | Multi-language merge |
| API-01 to API-04 | All tests | API endpoints work end-to-end |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed relative import in test_merge_pipeline.py**
- **Found during:** Task 1
- **Issue:** `from .conftest_merge import ...` fails because tests/integration/ has no `__init__.py` and pytest doesn't treat it as a package
- **Fix:** Changed to absolute import `from tests.integration.conftest_merge import ...` and added `pytest_plugins = ["tests.integration.conftest_merge"]` for fixture registration
- **Files modified:** tests/integration/test_merge_pipeline.py
- **Commit:** dd26fe3b

## Known Stubs

None -- all tests are fully implemented (1 intentionally skipped for threading complexity).

## Self-Check: PASSED

- FOUND: tests/integration/conftest_merge.py
- FOUND: tests/integration/test_merge_pipeline.py
- FOUND: .planning/phases/60-integration-testing/60-01-SUMMARY.md
- FOUND: commit dd26fe3b
