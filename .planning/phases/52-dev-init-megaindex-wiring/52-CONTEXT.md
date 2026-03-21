# Phase 52: DEV Init + MegaIndex Wiring - Context

**Gathered:** 2026-03-22
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase wires MegaIndex.build() into the DEV server startup lifecycle so that all 35 dicts are auto-populated from mock_gamedata fixtures. PerforcePathService must auto-detect mock_gamedata in DEV mode. After this phase, starting the DEV server produces a fully populated MegaIndex with zero manual steps.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — pure infrastructure phase.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `server/tools/ldm/services/mega_index.py` — MegaIndex with `build()` method (7-phase pipeline, 35 dicts)
- `server/tools/ldm/services/perforce_path_service.py` — path resolution service (no DEV mode auto-detect yet)
- `server/tools/ldm/services/mega_index_schemas.py` — schema definitions
- `tools/generate_mega_index_mockdata.py` — mock data generator
- `tests/fixtures/mock_gamedata/` — fixture data (StaticInfo, textures, sound, localization, etc.)

### Established Patterns
- DEV mode auto-init pattern already exists in `server/main.py` lifespan() — mapdata_service and glossary_service are auto-populated from mock_gamedata in DEV mode
- `config.DEV_MODE` flag controls DEV-only behavior
- `base_dir / "tests" / "fixtures" / "mock_gamedata"` is the standard fixture path
- Services use singleton pattern via `get_*_service()` functions

### Integration Points
- `server/main.py` lifespan() — startup hook where MegaIndex.build() must be called
- `server/config.py` — DEV_MODE flag
- Codex routes (`codex_items.py`, `codex_characters.py`, `codex_audio.py`, `codex_regions.py`) — consume MegaIndex data
- `server/tools/ldm/routes/mega_index.py` — MegaIndex API endpoints

</code_context>

<specifics>
## Specific Ideas

No specific requirements — infrastructure phase.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>
