---
phase: 45-megaindex-foundation-infrastructure
plan: 01
subsystem: infra
tags: [perforce, path-resolution, dataclass, singleton, wsl, megaindex]

# Dependency graph
requires: []
provides:
  - "PerforcePathService singleton with 11 path templates, drive/branch configuration, WSL conversion"
  - "10 frozen dataclass schemas for all MegaIndex entity types"
  - "API endpoints for path configuration (GET/POST /api/ldm/mapdata/paths/*)"
affects: [45-02, 45-03, 46, 47, 48, 49]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Centralized path service singleton extracted from domain service"
    - "Frozen dataclass schemas with slots for immutable entity data"
    - "SCHEMA_REGISTRY dict for dynamic type access"

key-files:
  created:
    - server/tools/ldm/services/perforce_path_service.py
    - server/tools/ldm/services/mega_index_schemas.py
  modified:
    - server/tools/ldm/services/mapdata_service.py
    - server/tools/ldm/routes/mapdata.py

key-decisions:
  - "Merged KNOWN_BRANCHES from both QACompiler (cd_delta) and MapDataGenerator into unified list of 5 branches"
  - "Added SCHEMA_REGISTRY dict for dynamic type access by future MegaIndex builder"
  - "All str fields default to empty string for graceful handling of missing XML attributes"

patterns-established:
  - "PerforcePathService.resolve(key) returns WSL Path directly -- no intermediate string conversion needed"
  - "Frozen dataclass + slots for all entity schemas -- immutable after MegaIndex build"

requirements-completed: [INFRA-01]

# Metrics
duration: 3min
completed: 2026-03-21
---

# Phase 45 Plan 01: PerforcePathService + MegaIndex Schemas Summary

**Centralized Perforce path resolution service (11 templates, drive/branch config, WSL conversion) extracted from MapDataService, plus 10 frozen dataclass schemas for all MegaIndex entity types**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-21T11:30:53Z
- **Completed:** 2026-03-21T11:34:17Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Extracted PATH_TEMPLATES, KNOWN_BRANCHES, convert_to_wsl_path, generate_paths into shared PerforcePathService singleton
- Created 10 frozen dataclass schemas matching MegaIndex design document exactly
- Refactored MapDataService to delegate all path resolution to PerforcePathService
- Added GET/POST /api/ldm/mapdata/paths/* endpoints for drive/branch configuration

## Task Commits

Each task was committed atomically:

1. **Task 1: Create PerforcePathService + MegaIndex schemas** - `f85c2a26` (feat)
2. **Task 2: Refactor MapDataService + add settings endpoint** - `694a9532` (refactor)

## Files Created/Modified
- `server/tools/ldm/services/perforce_path_service.py` - Centralized path resolution with 11 templates, drive/branch substitution, WSL conversion, singleton pattern
- `server/tools/ldm/services/mega_index_schemas.py` - 10 frozen dataclass schemas for all MegaIndex entity types plus SCHEMA_REGISTRY
- `server/tools/ldm/services/mapdata_service.py` - Removed inline PATH_TEMPLATES/KNOWN_BRANCHES/helpers, delegates to PerforcePathService
- `server/tools/ldm/routes/mapdata.py` - Added paths/status and paths/configure endpoints, updated imports

## Decisions Made
- Merged KNOWN_BRANCHES from QACompiler (has cd_delta) and MapDataGenerator into unified 5-branch list
- Added SCHEMA_REGISTRY dict for dynamic type access -- future MegaIndex builder can iterate schemas without hardcoding
- All str fields in schemas default to empty string for graceful handling of missing XML attributes

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None - all functionality is fully wired.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- PerforcePathService is ready for all future Codex services (Item, Character, Audio, Region) to import
- MegaIndex schemas are ready for the MegaIndex builder (Plan 03) to populate
- MapDataService successfully delegates path resolution -- no duplicate PATH_TEMPLATES anywhere

---
*Phase: 45-megaindex-foundation-infrastructure*
*Completed: 2026-03-21*
