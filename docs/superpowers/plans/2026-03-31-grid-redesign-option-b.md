# Grid Redesign: Content-Aware Heights + Edit Overlay — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the laggy grid with content-aware heights (computed ONCE on load) + floating edit overlay. Save updates ONE row only (0.15ms). No full 173k rebuild ever.

**Architecture:** Content-aware virtual grid (heights estimated from text on load, cumulative Float64Array built once). Editing via floating EditOverlay with native `<textarea>`. Single-row incremental height update on save. `$state.raw` for row data — zero proxy overhead.

**Tech Stack:** Svelte 5 (runes), TypeScript, Carbon Components (Tag, InlineLoading)

**KEY CHANGE from v1:** Row heights are NOT fixed 36px. They vary by content (short text = 36px, multiline = taller). Heights computed ONCE on load, updated for ONE row on save. Cells display FULL text with natural wrapping — no truncation, no ellipsis.

---

## File Map

| Action | File | Responsibility |
|--------|------|---------------|
| **CREATE** | `locaNext/src/lib/components/ldm/editor/EditOverlay.svelte` | Floating edit panel: textarea, save/cancel/confirm, keyboard, color picker, undo/redo |
| **REPLACE** | `locaNext/src/lib/components/ldm/grid/gridState.svelte.ts` → rewrite in-place | Remove all height code, switch to `$state.raw`, fixed `ROW_HEIGHT = 36` |
| **SIMPLIFY** | `locaNext/src/lib/components/ldm/grid/CellRenderer.svelte` | Remove inline editing, contenteditable, height measurement. Read-only display with ellipsis. |
| **SIMPLIFY** | `locaNext/src/lib/components/ldm/grid/ScrollEngine.svelte` | Remove height rebuild calls. Use `Math.floor(scrollTop / 36)`. |
| **MODIFY** | `locaNext/src/lib/components/ldm/VirtualGrid.svelte` | Wire EditOverlay, remove InlineEditor, remove height imports |
| **SIMPLIFY** | `locaNext/src/lib/components/ldm/grid/SelectionManager.svelte` | Change `onEditRequest` to open overlay instead of inline edit |
| **DELETE** | `locaNext/src/lib/components/ldm/grid/InlineEditor.svelte` | All logic absorbed into EditOverlay |

---

### Task 1: Rewrite gridState.svelte.ts — Fixed Heights + $state.raw

**Files:**
- Modify: `locaNext/src/lib/components/ldm/grid/gridState.svelte.ts`

This is the foundation. Everything else depends on it.

- [ ] **Step 1: Replace the entire file content**

Replace `gridState.svelte.ts` with the new fixed-height version. Key changes:
- `$state.raw([])` for `allRows` and `displayRows` (no proxy on 173k objects)
- `ROW_HEIGHT = 36` constant
- `getRowTop(i) = i * ROW_HEIGHT` — O(1)
- `findRowAtPosition(s) = Math.floor(s / ROW_HEIGHT)` — O(1)
- `getTotalHeight() = grid.total * ROW_HEIGHT` — O(1)
- Delete: `heightData` wrapper (unwrap to plain Float64Array), `measureRowHeight` action, `$state` proxy on row arrays
- Keep: `estimateRowHeight`, `countDisplayLines` (still compute heights from text), `rowHeightCache` (plain Map), cumulative heights (as plain Float64Array, not wrapped in $state)
- Keep: `grid` state object (remove `inlineEditingRowId`), `tmAppliedRows`, `referenceData`, `qaFlags`, `gameDevDynamicColumns`, `getVisibleRows`, `getRowById`, `getRowIndexById`, `resetGridState`
- Simplify: `rebuildCumulativeHeights` — keep for load/filter, NEVER call on save
- Add: `allRows` and `displayRows` as `$state.raw` top-level exports
- Add: `rowIndexById` as plain Map (not $state)
- Add: `updateRow(rowId, updates)` — O(1) single-row update with `Object.assign`
- Add: `updateRowHeight(rowIndex, newHeight)` — single-row incremental shift (0.15ms)
- Add: `setAllRows(rows, stripColorTags)` — bulk load + height build
- Add: `applyFilter(...)` — client-side filter (moved from ScrollEngine)

```typescript
/**
 * gridState.svelte.ts -- Content-aware grid state (Option B v2 redesign).
 *
 * KEY CHANGES from old version:
 * - $state.raw for row arrays (zero proxy overhead on 173k objects)
 * - Content-aware heights computed ONCE on load (estimateRowHeight kept)
 * - Cumulative Float64Array built once on load, incremental update on save
 * - updateRowHeight() for single-row incremental shift (0.15ms, not 173k rebuild)
 * - No measureRowHeight action (no DOM measurement, pure math estimation)
 * - No rebuildCumulativeHeights on save (only on load/filter)
 */

// --- Row data: $state.raw = NO proxy overhead ---
export let allRows: any[] = $state.raw([]);
export let displayRows: any[] = $state.raw([]);

// --- Core grid state (only scalars, cheap to proxy) ---
export const grid = $state({
  total: 0,
  visibleStart: 0,
  visibleEnd: 50,
  loading: false,
  initialLoading: true,
  loadError: null as string | null,
  loadingFileName: '' as string,
  selectedRowId: null as string | null,
  hoveredRowId: null as string | null,
  hoveredCell: null as string | null,
  activeFilter: 'all' as string,
  selectedCategories: [] as string[],
  searchTerm: '' as string,
  searchMode: 'contain' as string,
  searchFields: ['source', 'target'] as string[],
  containerEl: null as HTMLElement | null,
  rowsVersion: 0,
});

// --- GameDev dynamic columns ---
export let gameDevDynamicColumns = $state(['category', 'fileName', 'textState'] as string[]);

// --- Mutable Maps (plain, not reactive except where needed) ---
export const rowIndexById = new Map<string, number>();
export const tmAppliedRows = $state(new Map<string, { match_type: string }>());
export const referenceData = $state(new Map<string, { target: string; source: string }>());
export const qaFlags = $state(new Map<string, number>());

// --- Height system: compute once, update one ---
export const MIN_ROW_HEIGHT = 36;
export const MAX_ROW_HEIGHT = 400;
export const BUFFER_ROWS = 10;

// Plain data structures — NOT reactive (no $state wrapper)
export const rowHeightCache = new Map<number, number>();
export let cumulativeHeights = new Float64Array(1); // rebuilt on load/filter

/** Estimate row height from text content (pure math, no DOM) */
export function estimateRowHeight(row: any, index: number, stripColorTags: (t: string) => string): number {
  if (!row || row.placeholder) return MIN_ROW_HEIGHT;
  if (rowHeightCache.has(index)) return rowHeightCache.get(index)!;

  const source = stripColorTags(row.source || '');
  const target = stripColorTags(row.target || '');
  const charsPerLine = 55;
  const lineHeight = 22;
  const padding = 24;

  function countLines(text: string): number {
    if (!text) return 1;
    const normalized = text.replace(/&lt;br\s*\/&gt;/gi, '\n').replace(/<br\s*\/?>/gi, '\n').replace(/\\n/g, '\n');
    return normalized.split('\n').reduce((total, seg) => total + Math.max(1, Math.ceil(seg.length / charsPerLine)), 0);
  }

  const lines = Math.max(countLines(source), countLines(target));
  const height = Math.min(MAX_ROW_HEIGHT, Math.max(MIN_ROW_HEIGHT, lines * lineHeight + padding));
  rowHeightCache.set(index, height);
  return height;
}

/** Build cumulative heights — called ONCE on load/filter, NEVER on save */
export function buildCumulativeHeights(stripColorTags: (t: string) => string): void {
  const total = grid.total;
  const rows = displayRows;
  const cum = new Float64Array(total + 1);
  for (let i = 0; i < total; i++) {
    cum[i + 1] = cum[i] + estimateRowHeight(rows[i], i, stripColorTags);
  }
  cumulativeHeights = cum;
}

/** Update ONE row's height after save — incremental shift, 0.15ms */
export function updateRowHeight(rowIndex: number, stripColorTags: (t: string) => string): void {
  const row = displayRows[rowIndex];
  if (!row) return;
  const oldHeight = rowHeightCache.get(rowIndex) || MIN_ROW_HEIGHT;
  rowHeightCache.delete(rowIndex); // force re-estimate
  const newHeight = estimateRowHeight(row, rowIndex, stripColorTags);
  const delta = newHeight - oldHeight;
  if (Math.abs(delta) < 1) return;
  // Incremental shift — only touches entries after this row
  for (let i = rowIndex + 1; i < cumulativeHeights.length; i++) {
    cumulativeHeights[i] += delta;
  }
}

// --- Scroll math using cumulative heights ---
export function getRowTop(index: number): number {
  return index < cumulativeHeights.length ? cumulativeHeights[index] : index * MIN_ROW_HEIGHT;
}

export function getRowHeight(index: number): number {
  return rowHeightCache.get(index) || MIN_ROW_HEIGHT;
}

export function getTotalHeight(): number {
  return cumulativeHeights.length > grid.total ? cumulativeHeights[grid.total] : grid.total * MIN_ROW_HEIGHT;
}

export function findRowAtPosition(scrollPos: number): number {
  let low = 0, high = grid.total - 1;
  while (low < high) {
    const mid = (low + high) >> 1;
    if (cumulativeHeights[mid + 1] <= scrollPos) low = mid + 1;
    else high = mid;
  }
  return Math.max(0, low);
}

// --- Visible rows (reads grid.visibleStart/End + displayRows) ---
export function getVisibleRows() {
  return Array.from({ length: grid.visibleEnd - grid.visibleStart }, (_, i) => {
    const index = grid.visibleStart + i;
    return displayRows[index] || { row_num: index + 1, placeholder: true };
  });
}

// --- Row access ---
export function getRowById(rowId: string): any | null {
  const index = rowIndexById.get(rowId?.toString());
  return index !== undefined ? displayRows[index] : null;
}

export function getRowIndexById(rowId: string): number | undefined {
  return rowIndexById.get(rowId?.toString());
}

// --- Bulk operations ---
export function setAllRows(rows: any[], stripColorTags: (t: string) => string): void {
  allRows = rows;
  displayRows = rows;
  grid.total = rows.length;
  rebuildRowIndex(rows);
  rowHeightCache.clear();
  buildCumulativeHeights(stripColorTags);
  grid.rowsVersion++;
}

export function rebuildRowIndex(rows?: any[]): void {
  const source = rows || displayRows;
  rowIndexById.clear();
  for (let i = 0; i < source.length; i++) {
    if (source[i]?.id) rowIndexById.set(source[i].id.toString(), i);
  }
}

/** O(1) single-row update — no rebuild, no cascade */
export function updateRow(rowId: string, updates: Record<string, any>): void {
  const displayIdx = rowIndexById.get(rowId?.toString());
  if (displayIdx !== undefined && displayRows[displayIdx]) {
    Object.assign(displayRows[displayIdx], updates);
  }
  // Also update in allRows so filters don't revert the change
  const allIdx = allRows.findIndex(r => r?.id?.toString() === rowId?.toString());
  if (allIdx !== -1) {
    Object.assign(allRows[allIdx], updates);
  }
  grid.rowsVersion++;
}

/** Client-side filter (search + status + category) */
export function applyFilter(activeFilter: string, selectedCategories: string[], searchTerm: string, searchMode: string, searchFields: string[]): void {
  let filtered = allRows;

  if (activeFilter && activeFilter !== 'all') {
    if (activeFilter === 'confirmed') {
      filtered = filtered.filter(r => r.status === 'approved' || r.status === 'reviewed');
    } else if (activeFilter === 'unconfirmed') {
      filtered = filtered.filter(r => r.status === 'pending' || r.status === 'translated');
    } else if (activeFilter === 'qa_flagged') {
      filtered = filtered.filter(r => (r.qa_flag_count || 0) > 0);
    }
  }

  if (selectedCategories?.length > 0) {
    const catSet = new Set(selectedCategories);
    filtered = filtered.filter(r => catSet.has(r.category));
  }

  const term = searchTerm?.trim().toLowerCase();
  if (term) {
    const fields = searchFields || ['source', 'target'];
    if (searchMode === 'exact') {
      filtered = filtered.filter(row => fields.some(f => row[f]?.toLowerCase() === term));
    } else if (searchMode === 'not_contain') {
      filtered = filtered.filter(row => fields.every(f => !row[f]?.toLowerCase().includes(term)));
    } else {
      filtered = filtered.filter(row => fields.some(f => row[f]?.toLowerCase().includes(term)));
    }
  }

  displayRows = filtered;
  grid.total = filtered.length;
  rebuildRowIndex(filtered);
  rowHeightCache.clear();
  // buildCumulativeHeights called by ScrollEngine after filter
  grid.rowsVersion++;
}

/** Reset all state for file changes */
export function resetGridState(): void {
  allRows = [];
  displayRows = [];
  grid.total = 0;
  grid.visibleStart = 0;
  grid.visibleEnd = 50;
  grid.loading = false;
  grid.initialLoading = true;
  grid.selectedRowId = null;
  grid.hoveredRowId = null;
  grid.hoveredCell = null;
  grid.activeFilter = 'all';
  grid.selectedCategories = [];
  grid.searchTerm = '';
  grid.searchMode = 'contain';
  grid.searchFields = ['source', 'target'];
  grid.loadingFileName = '';
  grid.rowsVersion = 0;
  rowIndexById.clear();
  tmAppliedRows.clear();
  referenceData.clear();
  qaFlags.clear();
}
```

- [ ] **Step 2: Verify no import errors**

Run: `cd locaNext && npx svelte-check --threshold error 2>&1 | tail -5`

Expected: Import errors from files still referencing old exports (`heightData`, `rebuildCumulativeHeights`, etc.). This is expected — we fix them in subsequent tasks.

- [ ] **Step 3: Commit**

```bash
git add locaNext/src/lib/components/ldm/grid/gridState.svelte.ts
git commit -m "refactor: rewrite gridState to fixed-height + \$state.raw (Option B foundation)"
```

---

### Task 2: Simplify ScrollEngine — Fixed Height Math

**Files:**
- Modify: `locaNext/src/lib/components/ldm/grid/ScrollEngine.svelte`

- [ ] **Step 1: Remove height imports and simplify scroll math**

Remove imports: `rowHeightCache`, `heightData`, `rebuildCumulativeHeights`
Keep imports: `grid`, `rowIndexById`, `findRowAtPosition`, `getRowTop`, `ROW_HEIGHT`, `BUFFER_ROWS`, `setAllRows`, `displayRows`, `rebuildRowIndex`, `applyFilter`

Replace `calculateVisibleRange`:
```javascript
export function calculateVisibleRange() {
  if (!containerEl) return;
  containerHeight = containerEl.clientHeight;
  scrollTop = containerEl.scrollTop;
  if (containerHeight > 5000) containerHeight = Math.min(containerHeight, 1200);

  const startRow = findRowAtPosition(scrollTop);
  const visibleCount = Math.ceil(containerHeight / ROW_HEIGHT);

  grid.visibleStart = Math.max(0, startRow - BUFFER_ROWS);
  grid.visibleEnd = Math.min(grid.total, startRow + visibleCount + BUFFER_ROWS);
}
```

Replace `loadRows` bulk load section — use `setAllRows(allRows)` instead of manually setting `grid.allRows`, `grid.rows`, `grid.total`, `rebuildCumulativeHeights`.

Replace `clientFilter` — delegate to `applyFilter` from gridState, then `calculateVisibleRange()`.

- [ ] **Step 2: Verify**

Run: `cd locaNext && npx svelte-check --threshold error 2>&1 | tail -5`

- [ ] **Step 3: Commit**

```bash
git add locaNext/src/lib/components/ldm/grid/ScrollEngine.svelte
git commit -m "refactor: ScrollEngine uses fixed-height math, no height rebuilds"
```

---

### Task 3: Create EditOverlay.svelte — The New Editor

**Files:**
- Create: `locaNext/src/lib/components/ldm/editor/EditOverlay.svelte`

This is the core new component. It replaces InlineEditor.svelte (818 lines) with a cleaner ~300 line implementation using native `<textarea>`.

- [ ] **Step 1: Create the editor directory and component**

```bash
mkdir -p locaNext/src/lib/components/ldm/editor
```

Create `EditOverlay.svelte` with:

**Script section** — Port from InlineEditor:
- `startEdit(row)` — lock row, set editRowId/editValue, focus textarea
- `save(moveToNext)` — optimistic update via `updateRow()`, API PUT, unlock, move next
- `confirm()` — save as 'reviewed', fire `onConfirmTranslation`
- `cancel()` — unlock, close overlay
- `handleKeydown(e)` — Tab=save+next, Ctrl+S=confirm, Esc=cancel, Enter=native linebreak (NO special handling!)
- `formatForDisplay(text)` — `<br/>` → `\n` (same as InlineEditor.formatTextForDisplay)
- `formatForSave(text)` — `\n` → `<br/>` for XML (same as InlineEditor.formatTextForSave)
- Color picker state + `applyColor()`, `handleContextMenu()` (port from InlineEditor)
- Undo/redo — use native textarea undo (Ctrl+Z/Ctrl+Y work natively)
- `markAsTranslated()`, `revertRowStatus()` — port from InlineEditor
- `applyTMToRow(row, targetText, callback)` — port from InlineEditor
- Auto-grow textarea: `$effect(() => { if (textareaEl) textareaEl.style.height = textareaEl.scrollHeight + 'px'; })`

**Template section:**
```svelte
{#if editRowId}
  <div
    class="edit-overlay"
    style="top: {overlayTop}px; left: 0; right: 0;"
    onkeydown={handleKeydown}
  >
    <!-- Source (read-only) -->
    <div class="overlay-source">
      <span class="field-label">Source</span>
      <div class="source-display"><TagText text={activeRow?.source || ''} /></div>
    </div>
    <!-- Target (editable textarea) -->
    <div class="overlay-target">
      <span class="field-label">Target</span>
      <textarea
        bind:this={textareaEl}
        bind:value={editValue}
        class="edit-textarea"
        placeholder="Enter translation..."
        spellcheck="true"
      ></textarea>
    </div>
    <!-- Footer with hotkeys + status -->
    <div class="overlay-footer">
      <span><kbd>Enter</kbd> Linebreak</span>
      <span><kbd>Tab</kbd> Save+Next</span>
      <span><kbd>Ctrl+S</kbd> Confirm</span>
      <span><kbd>Esc</kbd> Cancel</span>
      <span class="status-label">{activeRow?.status || 'new'}</span>
    </div>
  </div>
{/if}
```

**Key difference from InlineEditor:** NO contenteditable. NO `document.execCommand`. NO `htmlToPaColor`/`paColorToHtml` during editing. The textarea works with plain text. Color markup is typed as raw `<PAColor...>` tags in the text (same as MemoQ shows markup). TagText renders colors in the source display.

**Overlay positioning:**
```javascript
let overlayTop = $derived.by(() => {
  if (!editRowId) return 0;
  const rowIndex = getRowIndexById(editRowId);
  if (rowIndex === undefined) return 0;
  // Position overlay right below the selected row
  return getRowTop(rowIndex) + ROW_HEIGHT;
});
```

The overlay is `position: absolute` inside the scroll-content div, so it scrolls with the grid.

- [ ] **Step 2: Verify it compiles**

Run: `cd locaNext && npx svelte-check --threshold error 2>&1 | tail -5`

- [ ] **Step 3: Commit**

```bash
git add locaNext/src/lib/components/ldm/editor/EditOverlay.svelte
git commit -m "feat: create EditOverlay with native textarea editing (Option B)"
```

---

### Task 4: Simplify CellRenderer — Read-Only Display

**Files:**
- Modify: `locaNext/src/lib/components/ldm/grid/CellRenderer.svelte`

- [ ] **Step 1: Remove all inline editing code**

Remove imports: `heightData`, `rebuildCumulativeHeights`, `rowHeightCache`, `measureRowHeight`

Remove from props: `inlineEditingRowId`, `inlineEditTextarea` (bindable), `onInlineEditKeydown`, `onInlineEditBlur`, `onEditContextMenu`

Remove functions: `handleEditInput`, `resizeRafId`

Remove from `getRowHeight` function — replace with constant:
```javascript
function getRowHeight() { return ROW_HEIGHT; }
```

Or just use `ROW_HEIGHT` directly in the template.

Change the row template:
- Replace `style="top: {getRowTop(rowIndex)}px; min-height: {getRowHeight(rowIndex)}px;"` with `style="top: {getRowTop(rowIndex)}px; min-height: {getRowHeight(rowIndex)}px;"` (KEEP min-height — content-aware, not fixed)
- Remove `use:measureRowHeight={{ index: rowIndex }}` (no DOM measurement)
- Remove the `{#if inlineEditingRowId === row.id}` contenteditable block entirely
- The target cell becomes always read-only with FULL content display:
```svelte
<div class="cell target" class:selected={grid.selectedRowId === row.id}>
  <span class="cell-content">
    <TagText text={row.target || ""} />
  </span>
</div>
```

Change CSS:
- `.virtual-row`: keep `min-height` (content-aware, cells show full text)
- `.cell-content`: `white-space: pre-wrap; word-wrap: break-word;` (wrap naturally, show linebreaks)
- Remove all `.inline-edit-*` CSS classes (~80 lines)
- Remove `.cell.target.inline-editing` CSS

- [ ] **Step 2: Verify**

Run: `cd locaNext && npx svelte-check --threshold error 2>&1 | tail -5`
Expected: 0 errors

- [ ] **Step 3: Commit**

```bash
git add locaNext/src/lib/components/ldm/grid/CellRenderer.svelte
git commit -m "refactor: CellRenderer is now read-only display with fixed 36px rows"
```

---

### Task 5: Wire EditOverlay into VirtualGrid

**Files:**
- Modify: `locaNext/src/lib/components/ldm/VirtualGrid.svelte`

- [ ] **Step 1: Replace InlineEditor with EditOverlay**

Remove imports: `InlineEditor`, `rebuildCumulativeHeights`, `rowHeightCache`
Add import: `EditOverlay` from `'./editor/EditOverlay.svelte'`
Add import: `updateRow` from `'./grid/gridState.svelte.ts'`

Replace `inlineEditor` ref with `editOverlay` ref:
```javascript
let editOverlay = $state(null);
```

Remove: `inlineEditTextarea` state, textarea bridge `$effect`, delegate wiring `$effect`

In template, replace `<InlineEditor .../>` with:
```svelte
<EditOverlay
  bind:this={editOverlay}
  {fileId}
  {fileName}
  {fileType}
  {isLocalFile}
  {onRowUpdate}
  {onRowSelect}
  {onConfirmTranslation}
/>
```

Move the EditOverlay INSIDE the scroll-wrapper div (so it scrolls with content):
```svelte
<div class="scroll-wrapper">
  <CellRenderer
    bind:this={cellRenderer}
    {fileType}
    {gamedevDynamicColumns}
    onRowClick={handleCellClick}
    onRowDoubleClick={(row) => editOverlay?.startEdit(row)}
    onCellContextMenu={handleCellContextMenu}
    onCellMouseEnter={handleCellMouseEnter}
    onCellMouseLeave={handleCellMouseLeave}
    onRowMouseLeave={handleRowMouseLeave}
    onQADismiss={handleQADismiss}
    {getReferenceForRow}
    {referenceLoading}
  />
  <EditOverlay ... />
</div>
```

Remove from CellRenderer props: `inlineEditingRowId`, `bind:inlineEditTextarea`, `onInlineEditKeydown`, `onInlineEditBlur`, `onEditContextMenu`

Update `handleCellUpdates` — use `updateRow()` instead of manual `grid.rows[rowIndex] = ...` + `rebuildCumulativeHeights`:
```javascript
function handleCellUpdates(updates) {
  updates.forEach(update => {
    const rowId = update.row_id?.toString();
    updateRow(rowId, { target: update.target, status: update.status });
  });
  logger.info("Real-time updates applied", { count: updates.length });
}
```

Update export wrappers:
```javascript
export async function openEditModalByRowId(rowId) {
  scrollToRowById(rowId);
  const row = getRowById(rowId);
  if (row) editOverlay?.startEdit(row);
}
export function applyTMToRow(lineNumber, targetText) {
  const row = grid.rows?.find?.(r => r?.row_num === lineNumber) || displayRows.find(r => r?.row_num === lineNumber);
  if (!row) return;
  editOverlay?.applyTMToRow(row, targetText, (rowId, matchType) => {
    statusColors?.markRowAsTMApplied(rowId, matchType);
  });
}
```

Update hotkey bar to remove Undo/Redo (textarea handles natively):
```svelte
<div class="hotkey-bar">
  <span class="hotkey"><kbd>Enter</kbd> Linebreak</span>
  <span class="hotkey"><kbd>Tab</kbd> Save & Next</span>
  <span class="hotkey"><kbd>Ctrl+S</kbd> Confirm</span>
  <span class="hotkey"><kbd>Esc</kbd> Cancel</span>
</div>
```

- [ ] **Step 2: Verify**

Run: `cd locaNext && npx svelte-check --threshold error 2>&1 | tail -5`
Expected: 0 errors

- [ ] **Step 3: Commit**

```bash
git add locaNext/src/lib/components/ldm/VirtualGrid.svelte
git commit -m "feat: wire EditOverlay into VirtualGrid, remove InlineEditor"
```

---

### Task 6: Update StatusColors — Remove Height Triggers

**Files:**
- Modify: `locaNext/src/lib/components/ldm/grid/StatusColors.svelte`

- [ ] **Step 1: Remove height-related imports and rowsVersion bumps that trigger cascades**

Remove import: `rebuildCumulativeHeights`

The `grid.rowsVersion++` calls should stay (they trigger visible row re-evaluation) but we should verify they don't reference any deleted exports.

Check that StatusColors only imports what exists in the new gridState.

- [ ] **Step 2: Verify**

Run: `cd locaNext && npx svelte-check --threshold error 2>&1 | tail -5`

- [ ] **Step 3: Commit**

```bash
git add locaNext/src/lib/components/ldm/grid/StatusColors.svelte
git commit -m "refactor: StatusColors removes height rebuild imports"
```

---

### Task 7: Delete InlineEditor.svelte + Final Cleanup

**Files:**
- Delete: `locaNext/src/lib/components/ldm/grid/InlineEditor.svelte`
- Modify: Any remaining files with stale imports

- [ ] **Step 1: Delete InlineEditor.svelte**

```bash
rm locaNext/src/lib/components/ldm/grid/InlineEditor.svelte
```

- [ ] **Step 2: Search for any remaining references to deleted exports**

```bash
cd locaNext && grep -r "InlineEditor\|inlineEditingRowId\|rebuildCumulativeHeights\|heightData\|rowHeightCache\|measureRowHeight\|estimateRowHeight\|countDisplayLines\|MIN_ROW_HEIGHT\|MAX_ROW_HEIGHT\|CHARS_PER_LINE\|LINE_HEIGHT\|CELL_PADDING" src/ --include="*.svelte" --include="*.ts" -l
```

Fix any remaining references.

- [ ] **Step 3: Full verification**

Run: `cd locaNext && npx svelte-check --threshold error 2>&1 | tail -10`
Expected: 0 errors, 0 warnings

- [ ] **Step 4: Commit**

```bash
git add -A locaNext/src/lib/components/ldm/
git commit -m "cleanup: delete InlineEditor.svelte (818 lines), remove all stale imports"
```

---

### Task 8: Verify Grid Functions End-to-End

**Files:** No code changes — testing only

- [ ] **Step 1: Start dev servers and verify**

```bash
DEV_MODE=true python3 server/main.py &
cd locaNext && npm run dev
```

- [ ] **Step 2: Test via API (curl)**

```bash
# Health check
curl -s http://localhost:8888/health | jq .

# Login
TOKEN=$(curl -s -X POST http://localhost:8888/api/v2/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | jq -r .token)

# Upload a test file
curl -s -X POST http://localhost:8888/api/ldm/files/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test_500.tmx" -F "storage=local" | jq .status

# Verify rows load
curl -s http://localhost:8888/api/ldm/files/-1/rows/all \
  -H "Authorization: Bearer $TOKEN" | jq '.rows | length'
```

- [ ] **Step 3: Visual verification with Playwright screenshot**

Open browser to localhost:5173, navigate to a file, verify:
- Grid shows content-aware row heights (cells match text beautifully)
- Double-click opens EditOverlay
- Type in textarea + press Enter for linebreaks
- Tab saves and moves to next row
- Ctrl+S confirms
- Esc cancels
- No freeze, no lag

- [ ] **Step 4: Commit any fixes**

```bash
git add -A
git commit -m "fix: address issues found during end-to-end testing"
```

---

## Summary

| Task | What | Deletions | Additions |
|------|------|-----------|-----------|
| 1 | Rewrite gridState.svelte.ts | ~80 lines (measureRowHeight, $state wrappers) | ~100 lines ($state.raw + updateRowHeight) |
| 2 | Simplify ScrollEngine | ~40 lines (height rebuilds) | ~10 lines (fixed math) |
| 3 | Create EditOverlay | — | ~300 lines (new component) |
| 4 | Simplify CellRenderer | ~400 lines (inline edit + height measurement) | ~5 lines (pre-wrap CSS) |
| 5 | Wire VirtualGrid | ~50 lines (InlineEditor refs) | ~30 lines (EditOverlay refs) |
| 6 | Clean StatusColors | ~5 lines (height imports) | — |
| 7 | Delete InlineEditor | 818 lines | — |
| 8 | End-to-end test | — | — |
| **Total** | | **~1,460 deleted** | **~495 added** |

Net result: **~965 fewer lines of code** with a faster, simpler, working grid.

---

### Task 9: Changed vs Confirmed Status Colors in UI

**Files:**
- Modify: `locaNext/src/lib/components/ldm/grid/CellRenderer.svelte` (row colors)
- Modify: `locaNext/src/lib/utils/statusColors.ts` or inline in CellRenderer

- [ ] **Step 1: Define status color mapping**

In CellRenderer, update the row background color logic:

```javascript
function getRowBackground(status) {
  switch (status) {
    case 'translated': return 'rgba(255, 214, 0, 0.08)';   // Yellow — changed but not confirmed
    case 'reviewed':   return 'rgba(0, 200, 150, 0.08)';   // Blue-green — confirmed
    case 'approved':   return 'rgba(0, 180, 100, 0.08)';   // Green — approved by reviewer
    default:           return 'transparent';                 // untranslated
  }
}
```

Add status dot badge in the row (small colored circle in the first cell or a dedicated status column):

```svelte
<span class="status-dot" class:yellow={row.status === 'translated'} class:confirmed={row.status === 'reviewed'} class:approved={row.status === 'approved'}></span>
```

```css
.status-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.status-dot.yellow { background: #ffd600; }
.status-dot.confirmed { background: #00c896; }
.status-dot.approved { background: #00b464; }
```

- [ ] **Step 2: Update EditOverlay save logic**

In `EditOverlay.svelte`:
- `save(moveToNext)` → sets status to `'translated'` (yellow = changed, not confirmed)
- `confirm()` → sets status to `'reviewed'` (blue-green = confirmed)

This is already the behavior in the spec. Verify the API PUT sends the correct status.

- [ ] **Step 3: Update merge filter to only take confirmed rows**

In `server/services/merge/` — verify merge operations filter on `status IN ('reviewed', 'approved')`.

Check `server/tools/ldm/routes/merge.py` and `server/services/merge/tmx_tools.py` for the status filter.

- [ ] **Step 4: Verify**

Run: `cd locaNext && npx svelte-check --threshold error 2>&1 | tail -5`

- [ ] **Step 5: Commit**

```bash
git add locaNext/src/lib/components/ldm/grid/CellRenderer.svelte locaNext/src/lib/components/ldm/editor/EditOverlay.svelte
git commit -m "feat: Changed (yellow) vs Confirmed (blue-green) status colors in grid"
```

---

### Task 10: Batch Update API Endpoint

**Files:**
- Create or modify: `server/tools/ldm/routes/rows.py`

- [ ] **Step 1: Add batch-update endpoint**

```python
@router.put("/files/{file_id}/rows/batch-update")
async def batch_update_rows(
    file_id: int,
    payload: BatchUpdatePayload,
    current_user: dict = Depends(get_current_active_user_async)
):
    """Batch update multiple rows in a single transaction (for Find & Replace All)."""
    repo = get_repo()
    results = []
    for update in payload.updates:
        row = await repo.update(
            row_id=update.row_id,
            target=update.target,
            status=update.status,
            updated_by=current_user.get("id")
        )
        results.append({"row_id": update.row_id, "success": row is not None})
    return {"updated": len(results), "results": results}
```

Add Pydantic model:
```python
class RowUpdate(BaseModel):
    row_id: int
    target: str
    status: str = "translated"

class BatchUpdatePayload(BaseModel):
    updates: List[RowUpdate]
```

- [ ] **Step 2: Verify endpoint works**

```bash
curl -s -X PUT http://localhost:8888/api/ldm/files/-1/rows/batch-update \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"updates": [{"row_id": -942634833, "target": "test", "status": "translated"}]}' | jq .
```

- [ ] **Step 3: Commit**

```bash
git add server/tools/ldm/routes/rows.py
git commit -m "feat: add batch-update endpoint for Find & Replace All"
```

---

### Task 11: Find & Replace Modal (Ctrl+H)

**Files:**
- Create: `locaNext/src/lib/components/ldm/FindReplaceModal.svelte`
- Modify: `locaNext/src/lib/components/ldm/VirtualGrid.svelte` (wire Ctrl+H + modal)

- [ ] **Step 1: Create FindReplaceModal.svelte**

```svelte
<script>
  import { Modal, TextInput, RadioButtonGroup, RadioButton, Toggle, Button } from "carbon-components-svelte";
  import { displayRows, updateRow } from './grid/gridState.svelte.ts';
  import { getAuthHeaders, getApiBase } from '$lib/utils/api.js';
  import { logger } from '$lib/utils/logger.js';

  let { open = $bindable(false), fileId = null } = $props();

  let findText = $state('');
  let replaceText = $state('');
  let useRegex = $state(false);
  let caseSensitive = $state(false);
  let wholeWord = $state(false);
  let scope = $state('target');  // 'target' | 'source' | 'all'
  let matches = $state([]);
  let currentMatchIndex = $state(0);
  let isApplying = $state(false);

  function findMatches() {
    if (!findText.trim()) { matches = []; return; }

    let pattern;
    try {
      const flags = caseSensitive ? 'g' : 'gi';
      const escaped = useRegex ? findText : findText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      const wrapped = wholeWord ? `\\b${escaped}\\b` : escaped;
      pattern = new RegExp(wrapped, flags);
    } catch { matches = []; return; }

    const results = [];
    for (let i = 0; i < displayRows.length; i++) {
      const row = displayRows[i];
      if (!row) continue;
      const fields = scope === 'all' ? ['source', 'target'] : [scope];
      for (const field of fields) {
        if (row[field] && pattern.test(row[field])) {
          const preview = row[field].replace(pattern, replaceText);
          results.push({ index: i, rowId: row.id, rowNum: row.row_num, field, original: row[field], preview });
          break;
        }
      }
    }
    matches = results;
    currentMatchIndex = 0;
  }

  async function replaceAndSet(status) {
    // Replace current match
    const match = matches[currentMatchIndex];
    if (!match) return;
    const row = displayRows[match.index];
    if (!row) return;
    row[match.field] = match.preview;
    updateRow(match.rowId, { [match.field]: match.preview, status });
    // API call
    const API_BASE = getApiBase();
    await fetch(`${API_BASE}/api/ldm/rows/${match.rowId}`, {
      method: 'PUT',
      headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ [match.field]: match.preview, status })
    });
    // Move to next
    matches = matches.filter((_, i) => i !== currentMatchIndex);
    if (currentMatchIndex >= matches.length) currentMatchIndex = Math.max(0, matches.length - 1);
  }

  async function replaceAll(status) {
    isApplying = true;
    const API_BASE = getApiBase();
    const updates = matches.map(m => ({ row_id: parseInt(m.rowId), target: m.preview, status }));
    // Optimistic local update
    for (const match of matches) {
      updateRow(match.rowId, { [match.field]: match.preview, status });
    }
    // Batch API call
    await fetch(`${API_BASE}/api/ldm/files/${fileId}/rows/batch-update`, {
      method: 'PUT',
      headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ updates })
    });
    matches = [];
    isApplying = false;
    logger.success(`Replaced ${updates.length} matches`, { status });
  }

  // Re-search when find text changes
  $effect(() => { if (findText || replaceText || useRegex || caseSensitive || scope) findMatches(); });
</script>

<Modal bind:open modalHeading="Find & Replace" passiveModal size="lg" onclose={() => open = false}>
  <div class="find-replace-form">
    <div class="input-row">
      <TextInput labelText="Find" bind:value={findText} placeholder="Search text or regex..." />
      <Toggle labelText="Regex" size="sm" bind:toggled={useRegex} />
      <Toggle labelText="Case" size="sm" bind:toggled={caseSensitive} />
      <Toggle labelText="Word" size="sm" bind:toggled={wholeWord} />
    </div>
    <TextInput labelText="Replace with" bind:value={replaceText} placeholder="Replacement text..." />

    <RadioButtonGroup legendText="Scope" bind:selected={scope}>
      <RadioButton value="target" labelText="Target only" />
      <RadioButton value="source" labelText="Source only" />
      <RadioButton value="all" labelText="Both" />
    </RadioButtonGroup>

    <div class="match-count">{matches.length} matches found</div>

    {#if matches.length > 0}
      <div class="match-preview">
        {#each matches.slice(0, 50) as match, i}
          <div class="match-row" class:active={i === currentMatchIndex} onclick={() => currentMatchIndex = i}>
            <span class="match-num">Row {match.rowNum}</span>
            <span class="match-original">{match.original.substring(0, 60)}</span>
            <span class="match-arrow">→</span>
            <span class="match-preview-text">{match.preview.substring(0, 60)}</span>
          </div>
        {/each}
        {#if matches.length > 50}
          <div class="match-more">...and {matches.length - 50} more</div>
        {/if}
      </div>
    {/if}

    <div class="action-buttons">
      <Button kind="secondary" on:click={() => replaceAndSet('translated')}>Replace → Change</Button>
      <Button kind="primary" on:click={() => replaceAndSet('reviewed')}>Replace → Confirm</Button>
      <Button kind="danger-tertiary" on:click={() => replaceAll('translated')} disabled={isApplying}>Change All ({matches.length})</Button>
      <Button kind="danger" on:click={() => replaceAll('reviewed')} disabled={isApplying}>Confirm All ({matches.length})</Button>
    </div>
  </div>
</Modal>
```

- [ ] **Step 2: Wire Ctrl+H in VirtualGrid**

In `VirtualGrid.svelte`, add:
```javascript
let showFindReplace = $state(false);

function handleGridKeydown(e) {
  if (e.ctrlKey && e.key === 'h') {
    e.preventDefault();
    showFindReplace = true;
    return;
  }
  selectionManager?.handleKeyDown(e);
}
```

Add to template:
```svelte
<FindReplaceModal bind:open={showFindReplace} {fileId} />
```

Add to hotkey bar:
```svelte
<span class="hotkey"><kbd>Ctrl+H</kbd> Find & Replace</span>
```

- [ ] **Step 3: Verify**

Run: `cd locaNext && npx svelte-check --threshold error 2>&1 | tail -5`

- [ ] **Step 4: Commit**

```bash
git add locaNext/src/lib/components/ldm/FindReplaceModal.svelte locaNext/src/lib/components/ldm/VirtualGrid.svelte
git commit -m "feat: Find & Replace modal (Ctrl+H) with Change/Confirm modes"
```

---

## Updated Summary

| Task | What | Deletions | Additions |
|------|------|-----------|-----------|
| 1 | Rewrite gridState.svelte.ts | ~80 lines | ~100 lines |
| 2 | Simplify ScrollEngine | ~40 lines | ~10 lines |
| 3 | Create EditOverlay | — | ~300 lines |
| 4 | Simplify CellRenderer | ~400 lines | ~5 lines |
| 5 | Wire VirtualGrid | ~50 lines | ~30 lines |
| 6 | Clean StatusColors | ~5 lines | — |
| 7 | Delete InlineEditor | 818 lines | — |
| 8 | End-to-end test | — | — |
| 9 | Status colors (Changed/Confirmed) | — | ~40 lines |
| 10 | Batch update endpoint | — | ~40 lines |
| 11 | Find & Replace modal | — | ~200 lines |
| **Total** | | **~1,393 deleted** | **~725 added** |

Net result: **~668 fewer lines** + 3 new features (status colors, batch API, Find & Replace).
