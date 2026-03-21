---
phase: 49-region-codex-ui-interactive-map
plan: 01
subsystem: api
tags: [fastapi, pydantic, region, faction, codex, mega-index]

requires:
  - phase: 45-mega-index-foundation
    provides: MegaIndex with region_by_strkey, faction_by_strkey, faction_group_by_strkey dicts
  - phase: 46-item-codex-ui
    provides: KnowledgePassEntry schema, knowledge 3-pass resolution pattern
provides:
  - Region Codex API with 3 endpoints at /api/ldm/codex/regions prefix
  - FactionGroup->Faction->Region hierarchy tree endpoint
  - Region detail with WorldPosition and knowledge 3-pass resolution
  - Paginated region list with faction_group filter and text search
affects: [49-02 frontend, region-map-visualization]

tech-stack:
  added: []
  patterns: [faction-tree-hierarchy, region-faction-parent-lookup]

key-files:
  created:
    - server/tools/ldm/schemas/codex_regions.py
    - server/tools/ldm/routes/codex_regions.py
  modified:
    - server/tools/ldm/routes/__init__.py
    - server/tools/ldm/router.py

key-decisions:
  - "Faction parent lookup iterates faction_by_strkey checking node_strkeys membership (O(F) per region, acceptable for small faction count)"
  - "Region name prefers display_name over name field for consistency with game UI"
  - "Reused KnowledgePassEntry from codex_items schema (Phase 46 pattern)"

patterns-established:
  - "Faction tree: FactionGroupEntry->FactionEntry->RegionEntry hierarchy via strkey chains"
  - "Region card helper: _build_region_card with faction parent resolution"

requirements-completed: [REGION-01, REGION-02, REGION-03, REGION-04]

duration: 2min
completed: 2026-03-21
---

# Phase 49 Plan 01: Region Codex Backend API Summary

**Region Codex API with faction hierarchy tree, paginated list with faction_group filtering, and region detail with WorldPosition and knowledge 3-pass resolution**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-21T12:57:26Z
- **Completed:** 2026-03-21T12:59:40Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- 7 Pydantic v2 models for Region Codex responses (card, detail, tree nodes, list)
- 3 API endpoints: /tree (faction hierarchy), /{strkey} (detail), / (paginated list)
- Knowledge 3-pass resolution following exact codex_items.py pattern
- Router registered in LDM main router

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Pydantic schemas for Region Codex** - `562f555d` (feat)
2. **Task 2: Create Region Codex API routes + register router** - `6d09f3bb` (feat)

## Files Created/Modified
- `server/tools/ldm/schemas/codex_regions.py` - 7 Pydantic models: RegionCardResponse, RegionDetailResponse, FactionTreeResponse, FactionGroupNode, FactionNode, FactionNodeItem, RegionListResponse
- `server/tools/ldm/routes/codex_regions.py` - 3 endpoints: /tree, /{strkey}, / with helpers for card building and faction parent lookup
- `server/tools/ldm/routes/__init__.py` - Added codex_regions_router import and __all__ entry
- `server/tools/ldm/router.py` - Added codex_regions_router include

## Decisions Made
- Faction parent lookup iterates faction_by_strkey checking node_strkeys membership -- O(F) per region, acceptable for small faction count
- Region name prefers display_name over name field for consistency with game UI
- Reused KnowledgePassEntry from codex_items schema (Phase 46 established pattern)
- /tree route defined before /{strkey} to avoid FastAPI path matching conflict

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - all endpoints are fully wired to MegaIndex data.

## Next Phase Readiness
- Region Codex backend API complete, ready for Plan 02 (frontend UI + interactive map)
- All 3 endpoints importable and registered in main router
- WorldPosition data available for map visualization

---
*Phase: 49-region-codex-ui-interactive-map*
*Completed: 2026-03-21*
