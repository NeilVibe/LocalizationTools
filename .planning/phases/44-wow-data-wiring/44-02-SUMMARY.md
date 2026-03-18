---
phase: 44-wow-data-wiring
plan: 02
subsystem: api
tags: [pydantic, fastapi, dev-mode, mapdata, glossary, tm]

requires:
  - phase: 43-mockdata-quality-audit
    provides: Mock PNG textures, staticinfo XMLs, enriched gamedata
provides:
  - TM list/get endpoints return 200 (no 500 on None status)
  - DEV mode auto-init for MapDataService with mock PNG textures
  - DEV mode auto-init for GlossaryService with mock staticinfo
affects: [right-panel, tm-panel, image-tab, context-tab]

tech-stack:
  added: []
  patterns: ["DEV mode service auto-init in lifespan()"]

key-files:
  created: []
  modified:
    - server/tools/ldm/routes/tm_crud.py
    - server/tools/ldm/schemas/tm.py
    - server/main.py

key-decisions:
  - "Use `or 'ready'` instead of `.get('status', 'ready')` to handle both missing key AND None value"
  - "GlossaryService uses _entity_index (not _entities) for count logging"

patterns-established:
  - "DEV mode auto-init pattern: guard with config.DEV_MODE, import lazily, catch all exceptions"

requirements-completed: [WOW-WIRE-02, WOW-WIRE-03]

duration: 2min
completed: 2026-03-18
---

# Phase 44 Plan 02: TM Status Fix + DEV Mode Auto-Init Summary

**Fixed TM 500 error (status=None Pydantic validation) and auto-initialized MapDataService/GlossaryService in DEV mode for Right Panel image/context tabs**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-18T07:29:05Z
- **Completed:** 2026-03-18T07:31:05Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- TM list and get endpoints now return 200 instead of 500 when status is None
- MapDataService pre-populated with mock PNG textures at DEV startup (image tab lights up)
- GlossaryService initialized with mock staticinfo paths at DEV startup (context tab detects entities)

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix TM status None handling** - `74a149c1` (fix)
2. **Task 2: DEV mode auto-init for MapDataService and GlossaryService** - `2662cd5d` (feat)

## Files Created/Modified
- `server/tools/ldm/schemas/tm.py` - TMResponse status default "ready"
- `server/tools/ldm/routes/tm_crud.py` - TMLike status `or "ready"` in both list_tms and get_tm
- `server/main.py` - DEV mode auto-init block for MapDataService + GlossaryService in lifespan()

## Decisions Made
- Used `or "ready"` instead of `.get("status", "ready")` to handle both missing key AND explicit None value
- GlossaryService log uses `_entity_index` attribute (not `_entities` which doesn't exist)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 44 complete: all WOW data wiring done
- TM endpoints work, Right Panel services auto-init in DEV mode
- Ready for demo verification or next milestone

---
*Phase: 44-wow-data-wiring*
*Completed: 2026-03-18*
