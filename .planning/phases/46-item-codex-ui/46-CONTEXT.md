# Phase 46: Item Codex UI - Context

**Gathered:** 2026-03-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Build a Svelte 5 Item Codex page that lets users browse, search, and inspect game items as a visual encyclopedia. All data comes from MegaIndex (item_by_strkey, item_group_hierarchy, strkey_to_image_path) — NO parsing in this phase. Extends the existing CodexPage pattern.

</domain>

<decisions>
## Implementation Decisions

### UI Layout
- Reuse existing CodexPage.svelte card grid pattern — same card sizes, same infinite scroll, same skeleton loading
- Item cards show: DDS image thumbnail, Korean name, translated name, category badge
- Category tabs at top derived from ItemGroupInfo hierarchy (MegaIndex D14)
- Detail panel slides in on card click — same pattern as existing CodexEntityDetail.svelte

### Search
- Search bar at top (same as existing Codex search-first UX from v3.3 CDX-05)
- Searches across: Korean name, translated name, StrKey, description — via MegaIndex text fields
- Debounced input, results update as user types

### Detail Panel
- Knowledge resolution displayed as tabs: Knowledge Pass 0/1/2, InspectData
- Each tab shows resolved knowledge entries with names and descriptions
- DDS image shown larger in detail view
- Cross-reference links to related entities (characters, regions)

### Claude's Discretion
- Card grid column count and responsive breakpoints
- Animation/transition details for detail panel
- Empty state messaging when no items match search

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `locaNext/src/lib/components/pages/CodexPage.svelte` — existing card grid with search, infinite scroll, category tabs
- `locaNext/src/lib/components/codex/CodexCard.svelte` — glassmorphism entity card with parallax hover
- `locaNext/src/lib/components/codex/CodexEntityDetail.svelte` — detail panel with attributes
- `locaNext/src/lib/components/common/InfiniteScroll.svelte` — intersection observer sentinel
- `locaNext/src/lib/components/common/SkeletonCard.svelte` — loading placeholder

### Established Patterns
- Svelte 5 Runes ($state, $derived, $effect) — no Svelte 4 patterns
- Carbon Components for UI primitives
- Fetch with AbortController for API calls
- Optimistic UI updates

### Integration Points
- New API endpoints: GET /api/ldm/codex/items (paginated), GET /api/ldm/codex/items/{strkey} (detail)
- MegaIndex provides: get_item(strkey), all_entities("item"), get_image_path(knowledge_key)
- Navigation: new "Items" tab in Codex page or separate page in sidebar

</code_context>

<specifics>
## Specific Ideas

- Follow exact same visual pattern as existing Codex cards (glassmorphism, parallax hover)
- ItemGroupInfo hierarchy should feel like folder navigation — groups contain subgroups and items
- Knowledge tabs in detail view should show the full resolution chain (Pass 0 inline children → Pass 1 direct KnowledgeKey → Pass 2 name match)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---
*Phase: 46-item-codex-ui*
*Context gathered: 2026-03-21 via smart discuss (autonomous)*
