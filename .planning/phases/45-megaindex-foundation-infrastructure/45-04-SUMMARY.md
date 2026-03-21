---
phase: 45-megaindex-foundation-infrastructure
plan: 04
subsystem: infra
tags: [megaindex, codex, mapdata, migration, refactor, singleton]

# Dependency graph
requires:
  - phase: 45-03
    provides: MegaIndex core with 35 dicts, build() pipeline, get_mega_index() singleton
  - phase: 45-01
    provides: PerforcePathService, MegaIndex schemas (KnowledgeEntry, CharacterEntry, etc.)
provides:
  - CodexService reads entity data from MegaIndex (no independent XML scanning)
  - MapDataService reads knowledge/DDS/audio data from MegaIndex (no independent XML parsing)
  - Single-parse architecture (MegaIndex.build() is the ONE XML parse)
affects: [codex-ui, audio-codex, item-codex, character-codex, region-codex, offline-bundle]

# Tech tracking
tech-stack:
  added: []
  patterns: [mega-index-consumer, singleton-delegation, frozen-to-pydantic-conversion]

key-files:
  created: []
  modified:
    - server/tools/ldm/services/codex_service.py
    - server/tools/ldm/services/mapdata_service.py

key-decisions:
  - "Removed lxml import from CodexService since no direct XML parsing needed"
  - "MapDataService._dds_index references MegaIndex.dds_by_stem directly (no copy)"
  - "Audio context uses MegaIndex C3/R3/C4/C5 chain with TTS WAV fallback"

patterns-established:
  - "MegaIndex consumer pattern: import get_mega_index, check _built, call build() if needed, read dicts"
  - "Frozen dataclass to Pydantic conversion: iterate MegaIndex dict, construct Pydantic model per entry"

requirements-completed: [INFRA-01, INFRA-02, INFRA-03]

# Metrics
duration: 3min
completed: 2026-03-21
---

# Phase 45 Plan 04: Service Migration Summary

**CodexService and MapDataService wired to MegaIndex -- single XML parse replaces 3 independent scans**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-21T11:45:33Z
- **Completed:** 2026-03-21T11:49:10Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- CodexService._registry populated from MegaIndex frozen dataclasses converted to CodexEntity Pydantic models
- MapDataService delegates knowledge table, DDS index, and image chains to MegaIndex
- Audio context now uses real WEM path resolution via MegaIndex C3/R3/C4/C5 (not just TTS stubs)
- All existing API endpoints continue working with same response shapes
- Removed ~200 lines of duplicate XML parsing code

## Task Commits

Each task was committed atomically:

1. **Task 1: Wire CodexService to MegaIndex** - `c5e6aba7` (feat)
2. **Task 2: Wire MapDataService to MegaIndex** - `9c71615e` (feat)

## Files Created/Modified
- `server/tools/ldm/services/codex_service.py` - _populate_from_mega_index() replaces _scan_entities(), removed lxml dependency
- `server/tools/ldm/services/mapdata_service.py` - initialize() populates from MegaIndex, removed build_knowledge_table/build_dds_index/resolve_image_chains

## Decisions Made
- Removed lxml import from CodexService (no longer parses XML directly)
- MapDataService._dds_index is a direct reference to MegaIndex.dds_by_stem (no copy needed, same Dict[str, Path] type)
- Audio context enriched with MegaIndex C3 (stringid_to_audio_path) + R3 (stringid_to_event) + C4/C5 (script text), with TTS WAV files kept as fallback
- Gimmick description combines desc and seal_desc with " | " separator when both present
- Region entities use display_name over name (consistent with MegaIndex RegionEntry.display_name)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 45 complete -- all 4 plans executed
- MegaIndex infrastructure ready for consumption by Codex UI phases (46-49)
- Single-parse architecture established: MegaIndex.build() -> all services read from it

## Self-Check: PASSED

---
*Phase: 45-megaindex-foundation-infrastructure*
*Completed: 2026-03-21*
