# Phase 53: Codex + Right Panel Verification - Context

**Gathered:** 2026-03-22
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase verifies that all 4 Codex UIs (Item, Character, Audio, Region) render correctly with MegaIndex mock data and that the RightPanel Image/Audio tabs display linked entity data. Pure verification — no new features, just Playwright testing and bug fixes for anything broken.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — pure verification/testing phase. Fix any rendering bugs found during testing.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `locaNext/src/lib/components/pages/ItemCodexPage.svelte` — Item codex grid
- `locaNext/src/lib/components/pages/CharacterCodexPage.svelte` — Character codex grid
- `locaNext/src/lib/components/pages/AudioCodexPage.svelte` — Audio codex list
- `locaNext/src/lib/components/pages/RegionCodexPage.svelte` — Region codex map
- `locaNext/src/lib/components/ldm/ItemCodexDetail.svelte` — Item detail panel
- `locaNext/src/lib/components/ldm/CharacterCodexDetail.svelte` — Character detail panel
- `locaNext/src/lib/components/ldm/AudioCodexDetail.svelte` — Audio detail panel
- `locaNext/src/lib/components/ldm/RegionCodexDetail.svelte` — Region detail
- `locaNext/src/lib/components/ldm/RegionCodexMap.svelte` — D3-zoom map
- Codex API routes: `server/tools/ldm/routes/codex_items.py`, `codex_characters.py`, `codex_audio.py`, `codex_regions.py`
- RightPanel with ImageTab and AudioTab already wired in Phase 50

### Established Patterns
- DEV server runs at localhost:5173 (Vite) + localhost:8888 (backend)
- Playwright MCP available for screenshots
- Login: admin/admin123

### Integration Points
- Phase 52 wired MegaIndex auto-build — all endpoints should return data
- LDM grid row selection → RightPanel → ImageTab/AudioTab via MegaIndex lookups

</code_context>

<specifics>
## Specific Ideas

Each codex page must be visited and screenshotted via Playwright. RightPanel integration tested by selecting a LDM row with linked entity.

</specifics>

<deferred>
## Deferred Ideas

None — verification stays within phase scope.

</deferred>
