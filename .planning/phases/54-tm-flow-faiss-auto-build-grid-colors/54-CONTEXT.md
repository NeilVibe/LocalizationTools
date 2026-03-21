# Phase 54: TM Flow + FAISS Auto-Build + Grid Colors - Context

**Gathered:** 2026-03-22
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase makes the TM workflow end-to-end functional (edit → reviewed → auto-register → FAISS rebuild → cascade search returns results) and corrects the LanguageData grid color scheme (grey default, yellow for "needs confirmation", blue-green for confirmed/approved).

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — infrastructure + bug fix phase. Fix TM pipeline wiring and grid color logic.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `server/tools/ldm/tm_manager.py` — TM CRUD and search operations
- `server/tools/ldm/routes/tm_crud.py` — TM API endpoints
- `server/tools/ldm/routes/tm_assignment.py` — TM linking to files
- `server/tools/ldm/indexing/gamedata_indexer.py` — FAISS indexing
- `server/tools/ldm/indexing/gamedata_searcher.py` — FAISS search
- `server/tools/ldm/routes/files.py` — file edit endpoints (has reviewed status logic)
- `server/tools/ldm/services/translator_merge.py` — merge with TM cascade
- `locaNext/src/lib/components/ldm/VirtualGrid.svelte` — main grid component
- `locaNext/src/lib/components/ldm/TMTab.svelte` — right panel TM tab
- `locaNext/src/lib/components/ldm/TMDataGrid.svelte` — TM data grid
- `locaNext/src/lib/components/ldm/SemanticResults.svelte` — semantic search results

### Established Patterns
- TM 5-tier cascade search exists in translator_merge.py
- FAISS index exists in gamedata_indexer.py
- Grid row styling in VirtualGrid.svelte
- Status-based coloring pattern in ExplorerGrid.svelte

### Integration Points
- Row edit → status change → auto-register TM entry
- TM entry change → FAISS index rebuild
- Row selection → TMTab → cascade search display
- VirtualGrid row class → color scheme based on status

</code_context>

<specifics>
## Specific Ideas

Grid color scheme: grey (default/untranslated), yellow (needs confirmation), blue-green (confirmed/approved).

</specifics>

<deferred>
## Deferred Ideas

None — stays within phase scope.

</deferred>
