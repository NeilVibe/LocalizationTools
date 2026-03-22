---
phase: 58-merge-api
plan: 01
subsystem: api
tags: [fastapi, pydantic, merge, dry-run, preview, asyncio]

requires:
  - phase: 57-transfer-adapter
    provides: execute_transfer, execute_multi_language_transfer, scan_source_languages, MATCH_MODES
  - phase: 56-backend-service-decomposition
    provides: translate_wsl_path, router registration pattern
provides:
  - POST /api/merge/preview endpoint (dry-run single and multi-language)
  - MergePreviewRequest, MergePreviewResponse, MergeExecuteRequest Pydantic models
  - _merge_in_progress guard flag for concurrent merge prevention
  - Router registered in main.py
affects: [58-02, 59-merge-modal]

tech-stack:
  added: []
  patterns: [asyncio.to_thread for blocking QT calls, overwrite warning extraction from file_results]

key-files:
  created: [server/api/merge.py, tests/test_merge_api.py]
  modified: [server/main.py]

key-decisions:
  - "Single /preview endpoint with multi_language bool flag instead of separate endpoints"
  - "Overwrite warnings extracted from file_results matched count when only_untranslated=false"

patterns-established:
  - "Merge API pattern: translate paths -> dispatch to adapter via asyncio.to_thread -> map result to Pydantic response"

requirements-completed: [API-01, API-04]

duration: 2min
completed: 2026-03-23
---

# Phase 58 Plan 01: Merge API Foundation Summary

**POST /api/merge/preview endpoint with dry-run single/multi-language support, Pydantic models, and 4 integration tests**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-22T17:04:56Z
- **Completed:** 2026-03-22T17:07:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- POST /api/merge/preview endpoint returns dry-run summary with match counts and overwrite warnings
- Multi-language preview mode returns per-language breakdown and scan data
- Invalid match_mode returns 422 with clear error message
- All 4 integration tests pass with mocked transfer_adapter functions

## Task Commits

Each task was committed atomically:

1. **Task 1: Create merge.py with models, preview endpoint, and router registration** - `0aabd07d` (feat)
2. **Task 2: Create integration tests for preview endpoints** - `dcf1a65f` (test)

## Files Created/Modified
- `server/api/merge.py` - Merge API router with 3 Pydantic models, preview endpoint, merge guard
- `server/main.py` - Router registration for merge API (after settings, before LDM)
- `tests/test_merge_api.py` - 4 integration tests covering API-01 and API-04

## Decisions Made
- Single /preview endpoint with `multi_language` bool flag instead of separate endpoints (simpler API surface)
- Overwrite warnings extracted by iterating file_results and checking matched > 0 when only_untranslated is false

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - all endpoints are fully wired to the transfer_adapter functions.

## Next Phase Readiness
- Preview endpoint ready for Plan 02 to add SSE execute endpoint
- MergeExecuteRequest model already defined for Plan 02
- _merge_in_progress guard ready for Plan 02 to implement 409 conflict response

---
*Phase: 58-merge-api*
*Completed: 2026-03-23*
