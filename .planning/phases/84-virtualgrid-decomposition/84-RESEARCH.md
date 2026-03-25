# Phase 84: VirtualGrid Decomposition - Research

**Researched:** 2026-03-26
**Domain:** Svelte 5 component decomposition, shared reactive state, virtual scroll architecture
**Confidence:** HIGH

## Summary

VirtualGrid.svelte is 4293 lines: ~2564 lines of script, ~553 lines of markup, and ~1176 lines of CSS. The decomposition targets the script and markup; CSS will be distributed to each new module with its associated markup. The file is a working monolith with no circular dependencies on external components -- it imports from stores, utilities, and child components but is not imported by anything except GridPage.svelte and LDM.svelte (via GridPage).

The project already has a working `.svelte.ts` pattern in `aiCapabilityStore.svelte.ts` that proves Svelte 5 rune-based module state works in this codebase. The critical technical constraint is that `.svelte.ts` files cannot directly export reassigned `$state` variables -- they must export either (a) `$state` objects whose properties are mutated, or (b) getter functions. The CONTEXT.md decisions (D-01 through D-04) align with pattern (a): a single `gridState.svelte.ts` exporting `$state` objects.

**Primary recommendation:** Use a single `gridState.svelte.ts` file exporting `$state` wrapper objects with property mutation (not reassignment). Extract in 3 batches per D-07/D-08/D-09, running Playwright E2E between batches.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Use shared `gridState.svelte.ts` file exporting `$state` fields -- all modules import what they need
- **D-02:** Shared state fields: `rows`, `selectedRowId`, `hoveredRowId`, `inlineEditingRowId`, `visibleStart`, `visibleEnd`, `total`, `activeFilter`, `selectedCategories`
- **D-03:** Document write-ownership at top of gridState.svelte.ts (e.g., "visibleStart/visibleEnd: written only by ScrollEngine") as poor-man's access control
- **D-04:** Derived state ($derived) lives in gridState.svelte.ts when cross-module, or in the owning module when single-module
- **D-05:** Props used only for parent->child configuration (fileId, fileName, fileType, callbacks), NOT for shared reactive state
- **D-06:** Hybrid extraction in 2-3 dependency-grouped batches, NOT one-at-a-time or all-at-once
- **D-07:** Batch 1: gridState.svelte.ts + ScrollEngine + StatusColors (no upstream deps)
- **D-08:** Batch 2: CellRenderer + SelectionManager (depend on batch 1 state)
- **D-09:** Batch 3: InlineEditor + SearchEngine (depend on batch 2)
- **D-10:** Each batch produces a working app -- commit between batches
- **D-11:** Playwright E2E tests run between batches to catch regressions early
- **D-12:** ScrollEngine -- virtual scroll, row heights, page loading, viewport management (~380 lines)
- **D-13:** CellRenderer -- column layout, resize, cell markup, text formatting (~600 lines)
- **D-14:** SelectionManager -- row/cell selection, hover states, keyboard navigation, context menu (~250 lines)
- **D-15:** InlineEditor -- textarea editing, color picker, undo/redo, save/cancel (~350 lines)
- **D-16:** StatusColors -- row status, QA flags, TM matches, reference data (~450 lines)
- **D-17:** SearchEngine -- semantic search, search config, filter orchestration (~100 lines)
- **D-18:** Parent VirtualGrid.svelte -- thin orchestrator (~230 lines)
- **D-19:** WebSocket real-time sync stays in parent (30 lines)
- **D-20:** Semantic search + search config + filter orchestration -> SearchEngine module
- **D-21:** Preferences store reads stay in parent, passed to modules via gridState or props
- **D-22:** New files in `locaNext/src/lib/components/ldm/grid/` directory
- **D-23:** gridState.svelte.ts, ScrollEngine.svelte, CellRenderer.svelte, SelectionManager.svelte, InlineEditor.svelte, StatusColors.svelte, SearchEngine.svelte
- **D-24:** VirtualGrid.svelte stays at its current path, imports from `./grid/`
- **D-25:** statusColors.ts (extracted in Phase 83) is already at `src/lib/utils/statusColors.ts`
- **D-26:** Existing Vitest tests continue to pass

### Claude's Discretion
- Exact line-by-line extraction decisions within each module
- Internal helper function organization within modules
- Whether to use Svelte snippets vs component composition for CellRenderer sub-parts
- Exact gridState.svelte.ts field typing (interface vs inline types)
- Whether undo/redo stack stays in InlineEditor or moves to gridState

### Deferred Ideas (OUT OF SCOPE)
- Unit tests for extracted modules -- belongs in Phase 85 or future
- Performance optimization (virtualization tuning) -- not in v11.0 scope
- SearchEngine could become a standalone reusable component -- future consideration
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| GRID-02 | VirtualGrid.svelte split into composable modules (target: no module > 800 lines) | Function boundary analysis shows 6 modules + parent all under 800 lines; CSS distribution strategy confirmed |
| GRID-03 | ScrollEngine module extracted -- virtual scroll, row height calculation, viewport management | Lines 55-68, 130-139, 432-835, 2247-2363 identified; `measureRowHeight` action directive pattern documented |
| GRID-04 | CellRenderer module extracted -- source/target/reference cell rendering, TagText integration | Markup lines 2746-2941, column definitions 332-414, resize system 237-466; CSS co-location strategy |
| GRID-05 | SelectionManager module extracted -- cell selection, keyboard navigation, multi-select | Lines 217-221, 1576-1645, 2370-2402, context menu 1948-2077; keyboard event delegation pattern |
| GRID-06 | InlineEditor module extracted -- textarea editing, save/cancel, keyboard shortcuts | Lines 157-168, 1259-1760, 1802-2137; contenteditable + color picker + undo/redo |
| GRID-07 | StatusColors module extracted -- 3-state status scheme, hover states, QA badge styling | Lines 224-229, 1018-1069, 1091-1257; imports from `$lib/utils/statusColors.ts` |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Svelte 5 | current in project | Component framework | Already in use, runes required |
| SvelteKit | current in project | App framework | Already in use, provides $lib alias |
| Vitest | current in project | Unit testing | Phase 83 already set up |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| carbon-components-svelte | current in project | UI components (Tag, Button, Dropdown, InlineLoading) | CellRenderer and parent markup |
| carbon-icons-svelte | current in project | Icons (Edit, Locked, etc.) | CellRenderer markup |
| @testing-library/svelte | current in project | Component testing | Phase 83 already set up |

No new libraries needed. This is a pure refactoring phase using existing dependencies.

## Architecture Patterns

### Recommended Project Structure
```
locaNext/src/lib/components/ldm/
├── VirtualGrid.svelte          # Thin orchestrator (~230 lines)
├── grid/
│   ├── gridState.svelte.ts     # Shared reactive state (~80 lines)
│   ├── ScrollEngine.svelte     # Virtual scroll + row heights (~380 lines)
│   ├── CellRenderer.svelte     # Column layout + cell markup (~600 lines)
│   ├── SelectionManager.svelte # Selection + keyboard nav (~250 lines)
│   ├── InlineEditor.svelte     # Textarea editing + color picker (~350 lines)
│   ├── StatusColors.svelte     # Status/QA/TM/Reference data (~450 lines)
│   └── SearchEngine.svelte     # Search + filters (~100 lines)
├── TagText.svelte              # Existing (unchanged)
├── ColorText.svelte            # Existing (unchanged)
├── CategoryFilter.svelte       # Existing (unchanged)
├── PresenceBar.svelte          # Existing (unchanged)
├── SemanticResults.svelte      # Existing (unchanged)
└── QAInlineBadge.svelte        # Existing (unchanged)
```

### Pattern 1: Shared Reactive State via .svelte.ts
**What:** A `.svelte.ts` file exports `$state` objects whose properties are mutated (never reassigned).
**When to use:** When multiple Svelte components need to read/write the same reactive state.
**Critical constraint:** You CANNOT export a `$state` variable and then reassign it from another file. Svelte 5 only tracks property mutations on exported `$state` objects.

**Example (from Svelte docs + project precedent in aiCapabilityStore.svelte.ts):**
```typescript
// gridState.svelte.ts
// Source: https://svelte.dev/docs/svelte/$state

// WRITE OWNERSHIP:
// rows: ScrollEngine (load), InlineEditor (save)
// visibleStart/visibleEnd: ScrollEngine
// selectedRowId: SelectionManager
// hoveredRowId/hoveredCell: SelectionManager
// inlineEditingRowId: InlineEditor

// Pattern: export $state OBJECTS, mutate properties
export const grid = $state({
  rows: [] as any[],
  total: 0,
  visibleStart: 0,
  visibleEnd: 50,
  selectedRowId: null as string | null,
  hoveredRowId: null as string | null,
  hoveredCell: null as string | null,
  inlineEditingRowId: null as string | null,
  activeFilter: 'all' as string,
  selectedCategories: [] as string[],
});

// Mutable Maps/Sets -- exported as objects, mutated in place
export const rowIndexById = $state(new Map<string, number>());
export const rowHeightCache = $state(new Map<number, number>());
export const loadedPages = $state(new Set<number>());

// Cross-module derived state
export const visibleRows = $derived(
  Array.from({ length: grid.visibleEnd - grid.visibleStart }, (_, i) => {
    const index = grid.visibleStart + i;
    return grid.rows[index] || { row_num: index + 1, placeholder: true };
  })
);

// Helper functions that operate on shared state
export function getRowById(rowId: string) {
  const index = rowIndexById.get(rowId.toString());
  return index !== undefined ? grid.rows[index] : null;
}

export function getRowIndexById(rowId: string) {
  return rowIndexById.get(rowId.toString());
}

// Reset function for file changes
export function resetGridState() {
  grid.rows = [];
  grid.total = 0;
  grid.visibleStart = 0;
  grid.visibleEnd = 50;
  grid.selectedRowId = null;
  grid.hoveredRowId = null;
  grid.hoveredCell = null;
  grid.inlineEditingRowId = null;
  grid.activeFilter = 'all';
  grid.selectedCategories = [];
  rowIndexById.clear();
  rowHeightCache.clear();
  loadedPages.clear();
}
```

**Why this works:** `grid` is never reassigned -- only `grid.rows`, `grid.total`, etc. are mutated. Maps and Sets are mutated via `.set()`, `.clear()`, etc. Svelte 5 proxies all property access, so any component importing `grid` will react to property changes.

### Pattern 2: Svelte Action Directive (`use:measureRowHeight`)
**What:** The `measureRowHeight` function is a Svelte action directive used on row DOM elements.
**Critical for ScrollEngine extraction:** The action must be defined in the same scope where it's used in markup, OR exported from a module and imported.

**After extraction:**
```svelte
<!-- CellRenderer.svelte or parent VirtualGrid.svelte -->
<script>
  import { measureRowHeight } from './grid/ScrollEngine.svelte';
  // OR define measureRowHeight in gridState.svelte.ts as a plain function
</script>
<div use:measureRowHeight={{ index: rowIndex }}>...</div>
```

**Recommendation:** Move `measureRowHeight` to `gridState.svelte.ts` as a plain exported function (it only reads/writes `rowHeightCache` and calls `rebuildCumulativeHeights`). This avoids the complexity of exporting from a `.svelte` component.

### Pattern 3: Export Functions from Svelte Components (for parent API)
**What:** VirtualGrid.svelte currently exports 7 functions (`scrollToRowById`, `scrollToRowNum`, `openEditModalByRowId`, `updateRowQAFlag`, `loadRows`, `applyTMToRow`, `markRowAsTMApplied`) called by GridPage.svelte and LDM.svelte.
**After decomposition:** The parent VirtualGrid.svelte must continue to export these same functions. They delegate to the appropriate child module's functions.

```svelte
<!-- VirtualGrid.svelte (parent orchestrator) -->
<script>
  import { grid, getRowById } from './grid/gridState.svelte.ts';
  // ... child component refs ...

  // Re-export for GridPage.svelte / LDM.svelte consumers
  export function scrollToRowById(rowId) { /* delegate to ScrollEngine */ }
  export function loadRows() { /* delegate to ScrollEngine */ }
  export function applyTMToRow(lineNumber, targetText) { /* delegate to InlineEditor */ }
  export function updateRowQAFlag(rowId, flagCount) { /* delegate to StatusColors */ }
  export function openEditModalByRowId(rowId) { /* delegate: scroll + edit */ }
  export function markRowAsTMApplied(rowId, matchType) { /* delegate to StatusColors */ }
  export function scrollToRowNum(rowNum) { /* delegate to ScrollEngine */ }
</script>
```

### Pattern 4: CSS Distribution Strategy
**What:** The file has 1176 lines of CSS (lines 3118-4293). Each extracted component takes its relevant CSS.
**Key concern:** Svelte scopes CSS to the component. Class names like `.virtual-row`, `.cell`, `.cell.target` must be in the component that renders that markup.
**CSS custom properties** (`--grid-font-size`, etc.) are set on the parent `.virtual-grid` div and inherited by children -- this works across component boundaries.

### Anti-Patterns to Avoid
- **Exporting and reassigning $state:** `export let x = $state(0); x = 5;` will NOT be reactive in importers. Always mutate object properties instead.
- **Duplicating state across modules:** Never create a local copy of shared state. Always import from gridState.svelte.ts.
- **Moving CSS custom properties to children:** Keep `--grid-font-size` etc. on the parent div; children inherit via CSS cascade.
- **Breaking the export API:** GridPage.svelte calls `virtualGrid.loadRows()` etc. -- these MUST continue working.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cross-component reactivity | Custom event bus / store | `.svelte.ts` with `$state` objects | Built into Svelte 5, zero overhead |
| Action directive sharing | Component method exports | Plain function in `.svelte.ts` | Simpler, testable, no component coupling |
| DOM selector stability | data-testid attributes | Keep existing CSS classes | E2E tests use CSS classes already |

## Common Pitfalls

### Pitfall 1: $state Reassignment in .svelte.ts
**What goes wrong:** Exporting `let rows = $state([])` then doing `rows = newArray` in another file. The importing component never sees the change.
**Why it happens:** Svelte compiles `$state` to getter/setter in the declaring file. Other files get a plain value at import time.
**How to avoid:** Use `grid.rows = newArray` where `grid` is a `$state({})` object. Property mutation is tracked.
**Warning signs:** State updates in one module not reflecting in another module's rendering.

### Pitfall 2: CSS Scoping After Decomposition
**What goes wrong:** Styles that worked in the monolith stop applying because they're scoped to the wrong component.
**Why it happens:** Svelte scopes `<style>` to the component's own markup. A class defined in parent CSS won't style child component elements.
**How to avoid:** Move CSS with its markup. If parent needs to style child slots, use `:global()` sparingly or pass classes as props.
**Warning signs:** Rows lose their status colors, hover effects disappear, cells misalign.

### Pitfall 3: Breaking the Export API
**What goes wrong:** GridPage.svelte calls `virtualGrid.loadRows()` but the function was moved to ScrollEngine without a delegating wrapper in parent.
**Why it happens:** During extraction, the export functions get moved but the parent forgets to re-export them.
**How to avoid:** Before each batch, list all 7 exported functions and verify they're re-exported from parent.
**Warning signs:** `TypeError: virtualGrid.loadRows is not a function` in the browser console.

### Pitfall 4: `use:measureRowHeight` Action Orphaning
**What goes wrong:** The `measureRowHeight` action is defined in ScrollEngine but used in CellRenderer's markup (the `<div class="virtual-row" use:measureRowHeight=...>`).
**Why it happens:** Actions must be in scope where the `use:` directive is applied.
**How to avoid:** Define `measureRowHeight` in `gridState.svelte.ts` as a plain exported function, imported by whichever component renders the row div.
**Warning signs:** `measureRowHeight is not defined` error, rows not getting correct heights.

### Pitfall 5: Losing Reactivity on Map/Set Operations
**What goes wrong:** `rowHeightCache.set(index, height)` doesn't trigger re-renders in consuming components.
**Why it happens:** Svelte 5 tracks Map/Set mutations when they're `$state`, but ONLY if accessed via the same reference. If you do `rowHeightCache = new Map(rowHeightCache)` to trigger reactivity (as the current code does for some Maps), the exported reference breaks.
**How to avoid:** With `$state(new Map())`, direct `.set()/.delete()/.clear()` calls ARE tracked by Svelte 5's proxy. Remove the `rows = [...rows]` reactivity triggers -- they become unnecessary with `$state` proxy.
**Warning signs:** Stale data after map updates, or "maximum call stack" from recursive reactivity.

### Pitfall 6: onMount/onDestroy Lifecycle in Wrong Component
**What goes wrong:** WebSocket subscription (`joinFile`/`leaveFile`) or ResizeObserver cleanup runs in a child component that gets destroyed/recreated during navigation.
**Why it happens:** Lifecycle hooks are scoped to the component they're defined in.
**How to avoid:** Keep lifecycle hooks in the parent VirtualGrid.svelte (per D-19). The parent owns the file subscription lifecycle.
**Warning signs:** WebSocket disconnects on scroll, memory leaks from uncleared observers.

## Code Examples

### gridState.svelte.ts Skeleton
```typescript
// Source: Svelte 5 docs + project pattern (aiCapabilityStore.svelte.ts)
// File: locaNext/src/lib/components/ldm/grid/gridState.svelte.ts

// ============================================================
// WRITE OWNERSHIP (poor-man's access control per D-03):
// rows:                ScrollEngine (load), InlineEditor (save), parent (WebSocket)
// total:               ScrollEngine
// visibleStart/End:    ScrollEngine
// selectedRowId:       SelectionManager
// hoveredRowId/Cell:   SelectionManager
// inlineEditingRowId:  InlineEditor
// activeFilter:        SearchEngine
// selectedCategories:  SearchEngine
// tmAppliedRows:       StatusColors
// referenceData:       StatusColors
// ============================================================

export const grid = $state({
  rows: [] as any[],
  total: 0,
  visibleStart: 0,
  visibleEnd: 50,
  loading: false,
  initialLoading: true,
  selectedRowId: null as string | null,
  hoveredRowId: null as string | null,
  hoveredCell: null as string | null,
  inlineEditingRowId: null as string | null,
  activeFilter: 'all',
  selectedCategories: [] as string[],
});

export const rowIndexById = $state(new Map<string, number>());
// ... etc
```

### ScrollEngine.svelte Module Pattern
```svelte
<!-- File: locaNext/src/lib/components/ldm/grid/ScrollEngine.svelte -->
<script>
  import { grid, rowIndexById, rowHeightCache } from './gridState.svelte.ts';
  import { getAuthHeaders, getApiBase } from '$lib/utils/api.js';
  import { logger } from '$lib/utils/logger.js';

  // Props from parent (configuration only, per D-05)
  let { fileId, fileType, searchTerm, searchMode, searchFields, activeTMs } = $props();

  // Constants
  const PAGE_SIZE = 100;
  const MIN_ROW_HEIGHT = 48;
  const BUFFER_ROWS = 8;

  // Module-local state (not shared)
  let loadingPages = $state(new Set());
  let loadedPages = $state(new Set());

  // All scroll/load functions from VirtualGrid.svelte lines 432-835
  export async function loadRows() { /* ... */ }
  export function calculateVisibleRange() { /* ... */ }
  // etc.
</script>

<!-- No markup -- ScrollEngine is logic-only, or minimal hidden markup -->
```

### Parent VirtualGrid.svelte Orchestrator Pattern
```svelte
<!-- File: locaNext/src/lib/components/ldm/VirtualGrid.svelte -->
<script>
  import { grid, resetGridState } from './grid/gridState.svelte.ts';
  import ScrollEngine from './grid/ScrollEngine.svelte';
  import CellRenderer from './grid/CellRenderer.svelte';
  import SelectionManager from './grid/SelectionManager.svelte';
  import InlineEditor from './grid/InlineEditor.svelte';
  import StatusColors from './grid/StatusColors.svelte';
  import SearchEngine from './grid/SearchEngine.svelte';
  import { joinFile, leaveFile, onCellUpdate } from '$lib/stores/ldm.js';
  import { onDestroy } from 'svelte';

  // Props (passed through to children)
  let { fileId = $bindable(null), fileName = '', fileType = 'translator', /* ... */ } = $props();

  // Component refs for delegation
  let scrollEngine, inlineEditor, statusColors;

  // WebSocket sync (stays in parent per D-19)
  let cellUpdateUnsubscribe = null;
  $effect(() => {
    if (fileId && fileId !== previousFileId) {
      previousFileId = fileId;
      joinFile(fileId);
      cellUpdateUnsubscribe?.();
      cellUpdateUnsubscribe = onCellUpdate(handleCellUpdates);
      scrollEngine.loadRows();
    }
  });

  // Re-export API for GridPage.svelte consumers
  export function loadRows() { return scrollEngine.loadRows(); }
  export function scrollToRowById(id) { return scrollEngine.scrollToRowById(id); }
  // ... etc
</script>

<div class="virtual-grid" style="--grid-font-size: ...">
  <SearchEngine bind:this={searchEngine} {fileId} {fileType} />
  <ScrollEngine bind:this={scrollEngine} {fileId} {fileType} />
  <CellRenderer {fileType} />
  <SelectionManager />
  <InlineEditor bind:this={inlineEditor} {fileId} {fileName} {fileType} />
  <StatusColors bind:this={statusColors} {fileId} {activeTMs} />
</div>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Svelte stores (writable) | `.svelte.ts` with `$state` | Svelte 5 (2024) | No store subscription boilerplate |
| `export let` props | `$props()` | Svelte 5 (2024) | Destructured, typed props |
| `$:` reactive declarations | `$derived` / `$effect` | Svelte 5 (2024) | Explicit dependency tracking |
| `createEventDispatcher` | Callback props | Svelte 5 (2024) | Direct function calls |

**The project is already on Svelte 5 runes.** No migration needed -- just apply the `.svelte.ts` shared state pattern consistently.

## Open Questions

1. **Logic-only components vs renderless components**
   - What we know: ScrollEngine, StatusColors, and SearchEngine are primarily logic modules. They could be renderless Svelte components (with `<script>` only, no markup) or plain `.svelte.ts` modules.
   - What's unclear: Whether using `.svelte` components for logic-only modules provides benefits (lifecycle hooks, component refs for export delegation) over `.svelte.ts` files.
   - Recommendation: Use `.svelte` components for modules that need `$effect` with cleanup, `onMount`/`onDestroy`, or `bind:this` for export delegation. Use `.svelte.ts` for pure state + helpers (gridState). The CONTEXT.md specifies `.svelte` for all modules, follow that.

2. **CSS variable inheritance depth**
   - What we know: `--grid-font-size` etc. are set on the parent `.virtual-grid` div. CSS custom properties inherit through the DOM tree.
   - What's unclear: Whether Svelte's component scoping affects CSS variable inheritance when child components render in slots vs direct children.
   - Recommendation: CSS custom properties inherit through the DOM regardless of Svelte scoping. This is safe. Verify during batch 1.

3. **`bind:this` on child components for export delegation**
   - What we know: GridPage.svelte calls `virtualGrid.loadRows()`. After decomposition, parent needs `scrollEngine.loadRows()`.
   - What's unclear: Whether `bind:this` on Svelte 5 components exposes `export function` declarations.
   - Recommendation: Yes, Svelte 5 components expose exported functions via `bind:this`. The existing `bind:this={gridPageRef}` in LDM.svelte already demonstrates this pattern.

## Sources

### Primary (HIGH confidence)
- Svelte 5 official docs `$state` -- https://svelte.dev/docs/svelte/$state -- export rules, object mutation pattern
- Project file `locaNext/src/lib/stores/aiCapabilityStore.svelte.ts` -- working `.svelte.ts` pattern in this codebase
- VirtualGrid.svelte source code (4293 lines) -- direct analysis of function boundaries, state dependencies, exports
- GridPage.svelte + LDM.svelte source -- consumer analysis for export API preservation

### Secondary (MEDIUM confidence)
- Svelte 5 Universal Reactivity tutorial -- https://svelte.dev/tutorial/svelte/universal-reactivity
- Joy of Code "Different Ways To Share State In Svelte 5" -- https://joyofcode.xyz/how-to-share-state-in-svelte-5
- DEV Community "Svelte 5: Share state between components" -- https://dev.to/mandrasch/svelte-5-share-state-between-components-for-dummies-4gd2

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new libraries, pure refactoring
- Architecture: HIGH -- `.svelte.ts` pattern verified in codebase AND official docs; function boundaries mapped from source
- Pitfalls: HIGH -- based on direct code analysis of actual state access patterns and Svelte 5 proxy behavior

**Research date:** 2026-03-26
**Valid until:** 2026-04-26 (stable -- Svelte 5 patterns are settled)
