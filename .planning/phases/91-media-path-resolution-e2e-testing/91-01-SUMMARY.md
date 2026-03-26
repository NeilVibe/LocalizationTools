---
phase: 91-media-path-resolution-e2e-testing
plan: 01
subsystem: api, ui
tags: [fastapi, svelte, mapdata, fallback-reason, image, audio, media-resolution]

# Dependency graph
requires:
  - phase: 90-branch-drive-configuration
    provides: Branch+Drive selector and path configuration API
provides:
  - fallback_reason field on ImageContext and AudioContext dataclasses
  - API returns 200 with structured reason instead of 404 for missing media
  - ImageTab and AudioTab display specific fallback reasons
  - data-testid attributes for E2E test hooks
affects: [91-02-PLAN, 92-megaindex-decomposition]

# Tech tracking
tech-stack:
  added: []
  patterns: [fallback-reason-pattern, 200-with-reason-instead-of-404]

key-files:
  created: []
  modified:
    - server/tools/ldm/services/mapdata_service.py
    - server/tools/ldm/routes/mapdata.py
    - locaNext/src/lib/components/ldm/ImageTab.svelte
    - locaNext/src/lib/components/ldm/AudioTab.svelte
    - tests/unit/ldm/test_mapdata_service.py

key-decisions:
  - "Return 200 with fallback_reason instead of 404 for missing media -- enables structured client-side reason display"
  - "503 for uninitialized service (not 404) -- distinguishes service-not-ready from media-not-found"
  - "Accumulate reason through lookup chain -- each step sets progressively more specific reason"

patterns-established:
  - "Fallback reason pattern: dataclass gains fallback_reason='' field, methods return object with reason instead of None"
  - "200-with-reason: API returns 200 with has_image=False/empty wem_path + fallback_reason instead of 404"

requirements-completed: [MEDIA-01, MEDIA-02, MEDIA-03, MEDIA-04]

# Metrics
duration: 4min
completed: 2026-03-26
---

# Phase 91 Plan 01: Fallback Reason Tracking Summary

**Structured fallback_reason field added to image/audio resolution chains with specific failure reasons displayed in frontend tabs**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-26T05:34:20Z
- **Completed:** 2026-03-26T05:38:07Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- ImageContext and AudioContext dataclasses gain fallback_reason field tracking why media resolution failed
- Backend returns 200 with structured reason instead of 404, enabling rich client-side display
- ImageTab and AudioTab show specific reasons like "Entity not found for this StringID" or "No audio event linked to this StringID"
- data-testid attributes added for Plan 91-02 E2E test hooks

## Task Commits

Each task was committed atomically:

1. **Task 1: Add fallback_reason to backend image/audio resolution and API responses** - `dd7dbcbe` (feat)
2. **Task 2: Update ImageTab and AudioTab to show specific fallback reasons** - `8218d9db` (feat)

## Files Created/Modified
- `server/tools/ldm/services/mapdata_service.py` - fallback_reason field on dataclasses, reason tracking through lookup chains
- `server/tools/ldm/routes/mapdata.py` - fallback_reason on response models, 503 for uninitialized instead of 404
- `locaNext/src/lib/components/ldm/ImageTab.svelte` - Show fallback_reason when has_image=false, data-testid hooks
- `locaNext/src/lib/components/ldm/AudioTab.svelte` - Check wem_path before player, show fallback_reason, data-testid hooks
- `tests/unit/ldm/test_mapdata_service.py` - Updated tests to verify fallback reason objects instead of None

## Decisions Made
- Return 200 with fallback_reason instead of 404 -- enables structured client-side display without error handling
- 503 for uninitialized service -- clear distinction between "service not ready" and "media not found"
- Reason accumulates through chain: entity lookup -> knowledge lookup -> texture lookup, each step refines the reason

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed stream_audio endpoint for new return behavior**
- **Found during:** Task 1
- **Issue:** stream_audio endpoint checked `audio_ctx is None` but now get_audio_context returns AudioContext with empty wem_path instead of None
- **Fix:** Added additional check for empty wem_path, returning 404 with the fallback_reason as detail
- **Files modified:** server/tools/ldm/routes/mapdata.py
- **Verification:** Endpoint correctly returns 404 for streaming when no WEM file exists
- **Committed in:** dd7dbcbe (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Essential fix -- stream_audio would have tried to serve empty path without this.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - all data flows are wired to real resolution chains.

## Next Phase Readiness
- fallback_reason fields and data-testid attributes ready for Plan 91-02 E2E tests
- Frontend tabs correctly handle all response states (found, not found with reason, error, loading)

---
*Phase: 91-media-path-resolution-e2e-testing*
*Completed: 2026-03-26*
