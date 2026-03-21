# Phase 50: StringID-to-Audio/Image Integration - Context

**Gathered:** 2026-03-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire MegaIndex reverse lookups (C3 stringid_to_audio_path, C7 stringid_to_entity, C1 strkey_to_image_path) to the existing LDM grid RightPanel. When a translator selects a row with a StringID, the Audio tab plays the voice line and the Image tab shows the entity portrait. UI already exists (AudioTab.svelte, ImageTab.svelte) — this phase wires real data via updated backend endpoints.

</domain>

<decisions>
## Implementation Decisions

### Backend
- Update GET /api/ldm/mapdata/audio/{stringId} to use MegaIndex C3 (stringid_to_audio_path) + R3 (stringid_to_event) + C4/C5 (scripts)
- Update GET /api/ldm/mapdata/image/{stringId} to use MegaIndex C7 (stringid_to_entity) → C1 (strkey_to_image_path)
- Both endpoints already exist and return the right response shapes — just need real data backing

### Frontend
- AudioTab.svelte already calls /api/ldm/mapdata/audio/{stringId} — no changes needed if backend returns correct shape
- ImageTab.svelte already calls /api/ldm/mapdata/image/{stringId} — no changes needed if backend returns correct shape
- May need minor adjustments if response schema differs

### Claude's Discretion
- Whether to add a "linked entity" badge on the AudioTab showing which entity this voice line belongs to
- Fallback behavior when StringID exists but no audio/image mapping found

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `locaNext/src/lib/components/ldm/AudioTab.svelte` — already fetches /api/ldm/mapdata/audio/{stringId}
- `locaNext/src/lib/components/ldm/ImageTab.svelte` — already fetches /api/ldm/mapdata/image/{stringId}
- `server/tools/ldm/services/mapdata_service.py` — get_audio_context() and get_image_context() already wired to MegaIndex in Phase 45-04
- MegaIndex C3, C7, C1, R3, C4, C5 — all composed dicts ready

### Key Insight
Phase 45-04 already wired MapDataService to MegaIndex. The endpoints may ALREADY work. This phase verifies and fills any gaps.

</code_context>

<specifics>
## Specific Ideas

- This may be a very thin phase — Phase 45-04 did most of the wiring
- Main work: verify the chain works end-to-end, fix any gaps in response format

</specifics>

<deferred>
## Deferred Ideas

None

</deferred>
