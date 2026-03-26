# Phase 84: VirtualGrid Decomposition - Context

**Gathered:** 2026-03-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Decompose VirtualGrid.svelte (4300 lines) into focused, composable modules — each testable in isolation, none exceeding 800 lines. The parent VirtualGrid.svelte becomes a thin orchestrator. Zero user-visible behavior changes. This is a pure refactoring phase.

</domain>

<decisions>
## Implementation Decisions

### Module communication pattern
- **D-01:** Use shared `gridState.svelte.ts` file exporting `$state` fields — all modules import what they need
- **D-02:** Shared state fields: `rows`, `selectedRowId`, `hoveredRowId`, `inlineEditingRowId`, `visibleStart`, `visibleEnd`, `total`, `activeFilter`, `selectedCategories`
- **D-03:** Document write-ownership at top of gridState.svelte.ts (e.g., "visibleStart/visibleEnd: written only by ScrollEngine") as poor-man's access control
- **D-04:** Derived state ($derived) lives in gridState.svelte.ts when cross-module, or in the owning module when single-module
- **D-05:** Props used only for parent→child configuration (fileId, fileName, fileType, callbacks), NOT for shared reactive state

### Extraction strategy
- **D-06:** Hybrid extraction in 2-3 dependency-grouped batches, NOT one-at-a-time or all-at-once
- **D-07:** Batch 1: gridState.svelte.ts + ScrollEngine + StatusColors (no upstream deps)
- **D-08:** Batch 2: CellRenderer + SelectionManager (depend on batch 1 state)
- **D-09:** Batch 3: InlineEditor + SearchEngine (depend on batch 2)
- **D-10:** Each batch produces a working app — commit between batches
- **D-11:** Playwright E2E tests run between batches to catch regressions early (don't wait for Phase 85)

### Module inventory (6 modules, not 5)
- **D-12:** ScrollEngine — virtual scroll, row heights, page loading, viewport management (~380 lines)
- **D-13:** CellRenderer — column layout, resize, cell markup, text formatting (~600 lines)
- **D-14:** SelectionManager — row/cell selection, hover states, keyboard navigation, context menu (~250 lines)
- **D-15:** InlineEditor — textarea editing, color picker, undo/redo, save/cancel (~350 lines)
- **D-16:** StatusColors — row status, QA flags, TM matches, reference data (~450 lines)
- **D-17:** SearchEngine — semantic search, search config, filter orchestration (~100 lines)
- **D-18:** Parent VirtualGrid.svelte — thin orchestrator (~230 lines): props, WebSocket sync (30 lines), layout composition, lifecycle effects

### Orphan code placement
- **D-19:** WebSocket real-time sync stays in parent (30 lines, coordinates across modules)
- **D-20:** Semantic search + search config + filter orchestration → SearchEngine module (minor scope flex from 5→6 modules, justified by coherence)
- **D-21:** Preferences store reads stay in parent, passed to modules via gridState or props

### File structure
- **D-22:** New files in `locaNext/src/lib/components/ldm/grid/` directory
- **D-23:** gridState.svelte.ts, ScrollEngine.svelte, CellRenderer.svelte, SelectionManager.svelte, InlineEditor.svelte, StatusColors.svelte, SearchEngine.svelte
- **D-24:** VirtualGrid.svelte stays at its current path, imports from `./grid/`

### Phase 83 integration
- **D-25:** statusColors.ts (extracted in Phase 83) is already at `src/lib/utils/statusColors.ts` — StatusColors module imports from it
- **D-26:** Existing Vitest tests continue to pass against the extracted utilities (tagDetector, statusColors)

### Claude's Discretion
- Exact line-by-line extraction decisions within each module
- Internal helper function organization within modules
- Whether to use Svelte snippets vs component composition for CellRenderer sub-parts
- Exact gridState.svelte.ts field typing (interface vs inline types)
- Whether undo/redo stack stays in InlineEditor or moves to gridState

</decisions>

<specifics>
## Specific Ideas

- ScrollEngine extraction order matters: it's the only module with zero upstream dependencies
- CellRenderer is the LARGEST module (~600 lines) — may need sub-helpers but should stay one component
- Color picker in InlineEditor is tightly coupled to source text parsing — keep together
- Write-ownership comments in gridState.svelte.ts prevent implicit coupling from becoming chaos
- Batch boundaries align with dependency graph: each batch's modules only depend on already-extracted modules

### Shared State Ownership Map (from codebase analysis)
| State | Writer | Readers |
|-------|--------|---------|
| rows | ScrollEngine (load), InlineEditor (save) | All |
| visibleStart/visibleEnd | ScrollEngine | CellRenderer |
| selectedRowId | SelectionManager | CellRenderer, InlineEditor, StatusColors |
| hoveredRowId/hoveredCell | SelectionManager | CellRenderer |
| inlineEditingRowId | InlineEditor | CellRenderer, SelectionManager |
| tmAppliedRows | StatusColors | CellRenderer |
| referenceData | StatusColors | CellRenderer |
| activeFilter/selectedCategories | SearchEngine | StatusColors (filters rows shown) |

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Target file to decompose
- `locaNext/src/lib/components/ldm/VirtualGrid.svelte` — 4300 lines, the monolith being split

### Architecture docs
- `docs/architecture/OFFLINE_ONLINE_MODE.md` — Repository pattern, 3-mode DB, WebSocket sync architecture
- `docs/architecture/ARCHITECTURE_SUMMARY.md` — Overall system design
- `.planning/REQUIREMENTS.md` §GRID-02 through GRID-07 — Requirement definitions for this phase

### Phase 83 artifacts (test infrastructure)
- `locaNext/vitest.config.ts` — Vitest config (must continue working)
- `locaNext/src/lib/utils/statusColors.ts` — Already extracted in Phase 83, StatusColors module imports this
- `locaNext/tests/tagDetector.test.mjs` — Existing tests must keep passing
- `locaNext/tests/statusColors.test.ts` — Existing tests must keep passing
- `locaNext/tests/TagText.svelte.test.ts` — Existing tests must keep passing

### Related components (integration points)
- `locaNext/src/lib/components/ldm/TagText.svelte` — Used by CellRenderer for tag pill rendering
- `locaNext/src/lib/stores/sync.js` — WebSocket sync store used by parent
- `locaNext/src/lib/api/client.js` — API client used by ScrollEngine, InlineEditor, StatusColors

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- statusColors.ts: Already extracted pure function (Phase 83) — StatusColors module imports it
- tagDetector.js + TagText.svelte: Already tested, used by CellRenderer
- Vitest infrastructure: Ready for new module tests

### Established Patterns
- Svelte 5 runes throughout ($state, $derived, $effect)
- Carbon Components (Tag, Button, TextInput) used in markup
- Loguru logger imported in server code (NOT in Svelte — use console.log in frontend)
- Preferences store ($preferences) for user settings

### Integration Points
- WebSocket sync (parent → all modules via gridState.rows mutation)
- API calls from ScrollEngine (load pages), InlineEditor (save), StatusColors (QA, TM)
- Keyboard shortcuts (SelectionManager handles most, InlineEditor handles edit-mode keys)
- Context menus (SelectionManager owns menu state, StatusColors/InlineEditor provide actions)

</code_context>

<deferred>
## Deferred Ideas

- Unit tests for extracted modules — belongs in Phase 85 (regression verification) or future
- Performance optimization (virtualization tuning) — not in v11.0 scope
- SearchEngine could become a standalone reusable component — future consideration

</deferred>

---

*Phase: 84-virtualgrid-decomposition*
*Context gathered: 2026-03-26*
