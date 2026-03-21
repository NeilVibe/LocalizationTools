# Phase 47: Character Codex UI - Context

**Gathered:** 2026-03-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Build a Svelte 5 Character Codex page. Browse, search, and inspect game characters with portraits, filename-based grouping tabs (NPC, MONSTER, etc.), and detail panel with Race/Gender/Age/Job fields + knowledge panel. All data from MegaIndex. Follows same pattern as Phase 46 Item Codex.

</domain>

<decisions>
## Implementation Decisions

### UI Layout
- Same card grid pattern as ItemCodexPage — reuse InfiniteScroll, SkeletonCard, search-first UX
- Character cards show: DDS portrait, Korean name, translated name, category badge (NPC/MONSTER)
- Category tabs from filename-based grouping (characterinfo_npc → "NPC", characterinfo_monster → "MONSTER")
- Detail panel with character-specific fields

### Detail Panel
- Race/Gender parsed from UseMacro field (e.g., "Macro_NPC_Human_Male" → Race: Human, Gender: Male)
- Age and Job displayed as badges
- Knowledge panel shows resolved knowledge children
- Portrait image (DDS) shown large at top

### Claude's Discretion
- Card grid responsive breakpoints
- Badge colors for NPC vs MONSTER categories
- Knowledge panel layout

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ItemCodexPage.svelte` (just built in Phase 46) — nearly identical pattern to follow
- `ItemCodexDetail.svelte` — knowledge tabs pattern
- `codex_items.py` routes — same endpoint pattern for characters
- All common components (InfiniteScroll, SkeletonCard, CodexCard)

### Integration Points
- API: GET /api/ldm/codex/characters (paginated), GET /api/ldm/codex/characters/{strkey}
- MegaIndex: get_character(strkey), all_entities("character"), character_by_strkey
- Navigation: "Characters" tab in sidebar

</code_context>

<specifics>
## Specific Ideas

- UseMacro parsing: split on "_" → extract race and gender from known patterns
- Filename grouping: strip "characterinfo_" prefix, use remainder as group name

</specifics>

<deferred>
## Deferred Ideas

None

</deferred>
