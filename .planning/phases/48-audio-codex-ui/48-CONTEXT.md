# Phase 48: Audio Codex UI - Context

**Gathered:** 2026-03-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Build a Svelte 5 Audio Codex page. Browse, search, and play WEM audio with script text overlay (KOR + ENG), category tree navigation from export folder hierarchy. All data from MegaIndex. Server-side WEM→WAV streaming via existing media_converter.py + vgmstream-cli.

</domain>

<decisions>
## Implementation Decisions

### UI Layout
- Card/list grid for audio entries — each shows event name, script text preview, play button, duration
- Category tree sidebar from export folder hierarchy (Dialog, QuestDialog, Cinematic, etc.) — MegaIndex D20 event_to_export_path
- Search across event names and script text

### Audio Playback
- Inline HTML5 `<audio>` element per entry — WAV from server-side WEM→WAV conversion
- API: GET /api/ldm/codex/audio/stream/{event_name} → streams WAV
- Use existing media_converter.py WEM→WAV pattern (vgmstream-cli subprocess)
- Script text overlay: KOR (primary) + ENG (secondary) from MegaIndex C4/C5

### Category Tree
- Hierarchical tree from export_path directories
- MegaIndex build_category_tree() or D20 event_to_export_path grouped by directory
- Click category → filter entries to that category
- Show entry counts per category

### Claude's Discretion
- List vs card layout for audio entries (list may be better since audio is text-heavy)
- Tree component implementation (Carbon TreeView or custom)
- Audio player styling

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ItemCodexPage.svelte` / `CharacterCodexPage.svelte` — card grid pattern
- `server/tools/ldm/services/media_converter.py` — existing WEM→WAV conversion
- `locaNext/src/lib/components/ldm/AudioTab.svelte` — existing audio player UI pattern
- MegaIndex D10 (wem_by_event), D11 (event_to_stringid), C4/C5 (script lines), D20 (export_path)

### Integration Points
- API: GET /api/ldm/codex/audio (list), GET /api/ldm/codex/audio/{event} (detail), GET /api/ldm/codex/audio/stream/{event} (WAV stream)
- Navigation: "Audio" tab in sidebar

</code_context>

<specifics>
## Specific Ideas

- Audio entries are different from item/character — no DDS image, but has inline playable audio
- Category tree is unique to audio codex — other codex types use flat tabs
- Script text is the primary visual content (not images)

</specifics>

<deferred>
## Deferred Ideas

- VRS chronological ordering (deferred to v6.0)
- Multi-language audio folder switching (deferred to v6.0)

</deferred>
