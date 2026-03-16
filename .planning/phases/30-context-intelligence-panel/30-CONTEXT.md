# Phase 30: Context Intelligence Panel - Context

**Gathered:** 2026-03-16
**Status:** Ready for planning
**Source:** Auto-discuss with codebase scout (80% infrastructure exists)

<domain>
## Phase Boundary

Add a right-side context intelligence panel to the GameData tree view. When a user selects any tree node, the panel shows TM suggestions from language data, related images, audio playback, AI-powered context analysis via the existing 6-tier cascade search, and cross-reference maps showing which entities reference each other. The panel reuses the existing RightPanel tab architecture and integrates with the Phase 29 indexing infrastructure.

Requirements: CTX-01, CTX-02, CTX-03, CTX-04, CTX-05

</domain>

<decisions>
## Implementation Decisions

### Panel Placement & Layout
- Reuse RightPanel.svelte tab architecture — consistent UX, already has resize/collapse, avoids duplication
- NodeDetailPanel stays as primary detail view — context panel adds intelligence alongside it
- Tabbed layout within the right section: NodeDetailPanel content becomes the "Details" tab, context intelligence becomes other tabs
- Same resize/collapse pattern as existing RightPanel (min 200px, max 500px, 40px collapsed icon state)
- Three-column layout avoided — tabs prevent horizontal squeeze

### Content Tabs (4 tabs)
- **Details** (default active) — Current NodeDetailPanel content: attributes, editable fields, children list, cross-ref links, AI summary (inline below attributes, on-demand button)
- **Cross-Refs** — Forward refs (what this entity references) AND backward refs (what references this entity), grouped by entity type with expandable items
- **Related** — Semantically similar entities via FAISS search + TM suggestions from language data (only if entity has matching StrKey in loaded language data)
- **Media** — Image display (DDS→PNG thumbnail if entity has texture reference) + audio playback (WEM→WAV if entity has voice data)

### Progressive Loading Behavior
- Progressive reveal — show each section's results as they arrive (hash: instant, FAISS: fast, AI: slow)
- Carbon SkeletonText for pending sections
- Subtle tier badges showing which search tier produced each result (e.g., "exact match", "semantic 94%", "n-gram 78%")
- AI summary is on-demand via button — not auto-triggered (saves GPU, explicit user action)
- In-memory cache per session — navigating back to a node shows cached results instantly without re-fetching

### Cross-Reference Map
- Grouped list by entity type: "Skills using this Knowledge (3)" with expandable items
- Two sections: "References" (forward — what this entity points to) and "Referenced By" (backward — what points to this entity)
- All items clickable — navigates to referenced entity in tree (reuse Phase 28 cross-ref navigation)
- Reverse index built during folder load — O(1) backward reference lookup at display time

### Default Active Tab
- "Details" tab active on node selection — attributes are the primary action
- Tab state persists within session (if user switches to Cross-Refs, it stays on Cross-Refs for next node selection)

### Claude's Discretion
- Exact tab icon choices (Carbon icon set)
- Skeleton loader animation details
- Whether to show empty tabs or hide tabs with no content for current node
- Exact threshold for "similar" in Related tab
- Badge styling for search tier indicators
- Whether AI summary button appears only when Ollama is available

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing Right Panel (REUSE architecture)
- `locaNext/src/lib/components/ldm/RightPanel.svelte` — Tab system, resize/collapse, selectedRow prop. Extend for gamedata mode.
- `locaNext/src/lib/components/ldm/ImageTab.svelte` — DDS→PNG image display pattern. Reuse for Media tab.
- `locaNext/src/lib/components/ldm/AudioTab.svelte` — WEM→WAV audio player pattern. Reuse for Media tab.
- `locaNext/src/lib/components/ldm/ContextTab.svelte` — Entity detection display + AI summary. Adapt for gamedata context.
- `locaNext/src/lib/components/ldm/AISuggestionsTab.svelte` — Qwen3 suggestion pattern with debounce. Reference for AI summary.

### GameData Tree UI (Phase 28 — integrate with)
- `locaNext/src/lib/components/ldm/GameDataTree.svelte` — 1244 lines. Node selection, search bar, navigateToNode export. Context panel triggers from onNodeSelect.
- `locaNext/src/lib/components/ldm/NodeDetailPanel.svelte` — 568 lines. Attribute display, editable fields, AC highlights, children list. Becomes "Details" tab content.
- `locaNext/src/lib/components/ldm/GameDevPage.svelte` — Page layout where tree + context panel integrate.

### Indexing & Search (Phase 29 — query these)
- `server/tools/ldm/indexing/gamedata_searcher.py` — GameDataSearcher: 6-tier cascade search + detect_entities. Backend for Related tab.
- `server/tools/ldm/indexing/gamedata_indexer.py` — GameDataIndexer: hash + FAISS + AC indexes. Source of cross-ref data.
- `server/tools/ldm/routes/gamedata.py` — POST /gamedata/index/search, POST /gamedata/index/detect, GET /gamedata/index/status endpoints.

### Media Endpoints (REUSE directly)
- `server/tools/ldm/routes/mapdata.py` — GET /mapdata/thumbnail/{texture_name}, GET /mapdata/audio/stream/{string_id}, GET /mapdata/image/{string_id}, GET /mapdata/audio/{string_id}.
- `server/tools/ldm/services/mapdata_service.py` — MapDataService: image/audio resolution from datapoint metadata.

### Context & AI Services (ADAPT for gamedata)
- `server/tools/ldm/services/context_service.py` — ContextService: entity detection + media resolution. Adapt resolve pattern for gamedata nodes.
- `server/tools/ldm/services/ai_suggestion_service.py` — AISuggestionService: Qwen3 summary via Ollama. Reuse for on-demand AI context.
- `server/tools/ldm/services/glossary_service.py` — GlossaryService: AC entity detection. Already integrated in Phase 29.

### Entity Display Patterns
- `locaNext/src/lib/components/ldm/EntityCard.svelte` — Entity type icons + color mapping. Reuse for cross-ref list items.
- `locaNext/src/lib/components/ldm/CodexEntityDetail.svelte` — 451 lines. Image + audio + similar items pattern. Reference for Media tab.

### Data References
- `server/tools/ldm/services/gamedata_browse_service.py` lines 24-38 — EDITABLE_ATTRS mapping per entity type.
- `server/tools/ldm/services/gamedata_tree_service.py` — TreeNode schema, cross-ref resolution logic.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets (80% of implementation exists)
- **RightPanel.svelte**: Tab system with resize/collapse — extend with gamedata-specific tabs
- **ImageTab/AudioTab**: DDS→PNG and WEM→WAV display — reuse directly for Media tab
- **ContextTab**: Entity detection display + AI summary — adapt for gamedata nodes
- **EntityCard.svelte**: Entity type icons + colors — reuse for cross-ref list items
- **GameDataSearcher**: 6-tier cascade — query for Related tab content
- **MapDataService**: Image/audio resolution from entity metadata — reuse for Media tab
- **AISuggestionService**: Qwen3 summaries — reuse for on-demand AI context

### Established Patterns
- Svelte 5 Runes: $state(), $derived(), $effect(), $props() — mandatory
- Carbon Components: Tab, TabContent, Button, SkeletonText — consistent UI
- Optimistic UI: update instantly, revert on failure
- API calls: fetch + getAuthHeaders + JSON + AbortController for rapid navigation
- Debounced fetch: 500ms pattern from AISuggestionsTab

### Integration Points
- GameDataTree.svelte `onNodeSelect(node)` → triggers context panel update
- GameDataTree.svelte `navigateToNode(nodeId)` → cross-ref click navigation
- `/api/ldm/gamedata/index/search` → Related tab: semantically similar entities
- `/api/ldm/gamedata/index/detect` → Cross-Refs tab: entity detection in attributes
- `/api/ldm/mapdata/thumbnail/{name}` → Media tab: DDS→PNG images
- `/api/ldm/mapdata/audio/stream/{id}` → Media tab: WEM→WAV audio
- New endpoint needed: `/api/ldm/gamedata/context/{node_id}` → aggregated context for a node

### New Work Required
- **GameDataContextService.py** — New backend service: resolve cross-refs (forward + backward), find related entities, resolve media
- **Reverse index** — Build backward reference map during folder load (entity A → all entities referencing A)
- **Context endpoint** — New `/api/ldm/gamedata/context/{node_id}` combining cross-refs, related, media
- **Tab integration** — Refactor NodeDetailPanel into a tab within the right panel system

</code_context>

<specifics>
## Specific Ideas

- RightPanel tab architecture is proven for translator mode — extending it for gamedata keeps UX consistent across both modes
- Cross-reference map is the key differentiator: game devs need to see "what uses this item?" instantly
- AI summary should be on-demand (button) not auto — GPU cost + game devs don't always need narrative context
- Backward references need a reverse index built at folder load time — same pattern as forward index in Phase 29
- TM suggestions only shown when relevant (entity has StrKey in language data) — don't show empty TM tab to game devs

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 30-context-intelligence-panel*
*Context gathered: 2026-03-16*
