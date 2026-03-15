---
phase: 20-interactive-world-map
plan: 01
subsystem: api
tags: [worldmap, xml-parsing, lxml, pydantic, fastapi, codex-enrichment]

requires:
  - phase: 15-mock-gamedata-universe
    provides: FactionNode and NodeWaypointInfo XML fixtures for parsing
  - phase: 19-game-world-codex
    provides: CodexService and CodexEntity for Codex enrichment
provides:
  - WorldMapService singleton parsing FactionNode positions and waypoint routes
  - Pydantic schemas MapNode, MapRoute, WorldMapData
  - GET /api/ldm/worldmap/data REST endpoint
  - 20 unit tests (16 service + 4 route)
affects: [20-02-interactive-world-map-frontend]

tech-stack:
  added: []
  patterns: [worldmap-service-singleton, codex-enrichment-cross-ref, lazy-initialization]

key-files:
  created:
    - server/tools/ldm/schemas/worldmap.py
    - server/tools/ldm/services/worldmap_service.py
    - server/tools/ldm/routes/worldmap.py
    - tests/unit/ldm/test_worldmap_service.py
    - tests/unit/ldm/test_worldmap_route.py
  modified:
    - server/tools/ldm/router.py

key-decisions:
  - "WorldMapService uses module-level codex_service variable for decoupled Codex enrichment"
  - "WorldPosition 'X,0,Z' string format parsed by comma-split (Y always 0, ignored)"
  - "Fallback to StrKey as node name when CodexService unavailable"
  - "entity_type_counts derived from Codex related_entities cross-references"

patterns-established:
  - "WorldMap service follows same singleton + lazy init pattern as CodexService"
  - "Route layer creates service with mock_gamedata fallback (same as codex route)"

requirements-completed: [MAP-01, MAP-02, MAP-03, MAP-04]

duration: 4min
completed: 2026-03-15
---

# Phase 20 Plan 01: WorldMap Backend Service Summary

**WorldMapService parsing 14 FactionNode positions and 13 waypoint routes from XML, with Codex entity enrichment for names/descriptions/NPCs, exposed via GET /api/ldm/worldmap/data**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-15T14:20:21Z
- **Completed:** 2026-03-15T14:24:47Z
- **Tasks:** 2 (TDD)
- **Files modified:** 6

## Accomplishments
- WorldMapService parses 14 FactionNode positions with X,Z coordinates from WorldPosition attribute
- 13 NodeWaypointInfo routes parsed with intermediate waypoint coordinates
- Codex enrichment populates region names, descriptions, NPC lists, and entity type counts
- GET /api/ldm/worldmap/data endpoint returns complete WorldMapData with bounds
- 20 tests pass (16 service + 4 route), existing LDM tests unbroken

## Task Commits

Each task was committed atomically (TDD: RED then GREEN):

1. **Task 1: WorldMap schemas + service** - `37dfc76a` (test: RED) -> `760cc190` (feat: GREEN)
2. **Task 2: REST endpoint + router** - `5aa98f72` (test: RED) -> `ef19cde1` (feat: GREEN)

## Files Created/Modified
- `server/tools/ldm/schemas/worldmap.py` - Pydantic models: MapNode, MapRoute, WorldMapData
- `server/tools/ldm/services/worldmap_service.py` - WorldMapService with XML parsing + Codex enrichment
- `server/tools/ldm/routes/worldmap.py` - GET /worldmap/data endpoint
- `server/tools/ldm/router.py` - Registered worldmap_router
- `tests/unit/ldm/test_worldmap_service.py` - 16 service tests
- `tests/unit/ldm/test_worldmap_route.py` - 4 route integration tests

## Decisions Made
- Module-level `codex_service` variable for decoupled enrichment (avoids circular imports)
- WorldPosition "X,0,Z" parsed via comma-split, Y coordinate discarded (2D map)
- StrKey used as fallback node name when Codex unavailable
- entity_type_counts computed from Codex related_entities (character/item cross-refs)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Pre-existing test failure in test_glossary_service.py (unrelated to worldmap changes)

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- WorldMap backend API complete, ready for frontend SVG visualization (Plan 02)
- All data endpoints tested and returning correct structures

---
*Phase: 20-interactive-world-map*
*Completed: 2026-03-15*
