/**
 * gridState.svelte.ts -- Shared reactive state for all VirtualGrid modules.
 *
 * Phase 84 Batch 1: Single source of truth for grid state.
 * All modules import what they need. Never reassign top-level exports --
 * only mutate properties on $state objects.
 *
 * ============================================================
 * WRITE OWNERSHIP (poor-man's access control per D-03):
 *
 * rows:                ScrollEngine (load), InlineEditor (save), parent (WebSocket)
 * total:               ScrollEngine
 * loading:             ScrollEngine
 * initialLoading:      ScrollEngine
 * visibleStart/End:    ScrollEngine
 * selectedRowId:       SelectionManager
 * hoveredRowId/Cell:   SelectionManager
 * inlineEditingRowId:  InlineEditor
 * activeFilter:        SearchEngine
 * selectedCategories:  SearchEngine
 * searchTerm:          SearchEngine
 * searchMode:          SearchEngine
 * searchFields:        SearchEngine
 * tmAppliedRows:       StatusColors
 * referenceData:       StatusColors
 * qaFlags:             StatusColors
 * ============================================================
 */

// --- Core grid state (single $state object, mutate properties only) ---
export const grid = $state({
  allRows: [] as any[],    // ALL rows from DB (immutable after bulk load)
  rows: [] as any[],        // DISPLAY rows (= allRows or filtered subset)
  total: 0,
  visibleStart: 0,
  visibleEnd: 50,
  loading: false,
  initialLoading: true,
  loadError: null as string | null,
  selectedRowId: null as string | null,
  hoveredRowId: null as string | null,
  hoveredCell: null as string | null,
  inlineEditingRowId: null as string | null,
  activeFilter: 'all' as string,
  selectedCategories: [] as string[],
  searchTerm: '' as string,
  searchMode: 'contain' as string,
  searchFields: ['source', 'target'] as string[],
  containerEl: null as HTMLElement | null,
  // Version counter: bump after batch-mutating grid.rows to trigger $derived re-evaluation.
  // Safer than self-assignment (grid.rows = grid.rows) which may be optimized away in future Svelte versions.
  rowsVersion: 0,
});

// --- Mutable Maps/Sets ---
export const rowIndexById = $state(new Map<string, number>());
// CRITICAL: rowHeightCache must be a PLAIN Map (not $state).
// A reactive Map triggers ALL rows to re-render when ANY entry changes,
// creating an O(n²) cascade with measureRowHeight (50 rows × 50 re-renders = freeze).
export const rowHeightCache = new Map<number, number>();
// loadedPages removed — bulk load architecture loads ALL rows at once
export const tmAppliedRows = $state(new Map<string, { match_type: string }>());
export const referenceData = $state(new Map<string, { target: string; source: string }>());
export const qaFlags = $state(new Map<string, number>());

// --- Variable height virtualization (property on $state wrapper for cross-module reactivity) ---
export const heightData = $state({ cumulativeHeights: [0] as number[] });

// Virtual scrolling constants
export const MIN_ROW_HEIGHT = 48;
export const MAX_ROW_HEIGHT = 800;
export const CHARS_PER_LINE = 45;
export const LINE_HEIGHT = 26;
export const CELL_PADDING = 24;
export const BUFFER_ROWS = 8;
export const PAGE_SIZE = 100;
export const PREFETCH_PAGES = 5;

// --- Cross-module derived state (per D-04) ---
// Cannot export $derived from .svelte.ts module — export function instead
export function getVisibleRows() {
  return Array.from({ length: grid.visibleEnd - grid.visibleStart }, (_, i) => {
    const index = grid.visibleStart + i;
    return grid.rows[index] || { row_num: index + 1, placeholder: true };
  });
}

// --- Helper functions ---

/** O(1) row lookup by ID */
export function getRowById(rowId: string): any | null {
  const index = rowIndexById.get(rowId.toString());
  return index !== undefined ? grid.rows[index] : null;
}

/** O(1) row index lookup by ID */
export function getRowIndexById(rowId: string): number | undefined {
  return rowIndexById.get(rowId.toString());
}

/** Rebuild rowIndexById from current grid.rows */
export function rebuildRowIndex(): void {
  rowIndexById.clear();
  for (let i = 0; i < grid.rows.length; i++) {
    const row = grid.rows[i];
    if (row && row.id) {
      rowIndexById.set(row.id.toString(), i);
    }
  }
}

/** Calculate display lines for text (accounts for newlines AND wrapping per segment) */
export function countDisplayLines(text: string, charsPerLine = 55): number {
  if (!text) return 1;

  // Convert all newline types to actual newlines for consistent splitting
  let normalized = text
    .replace(/&lt;br\s*\/&gt;/gi, '\n')
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/\\n/g, '\n');

  const segments = normalized.split('\n');
  let totalLines = 0;
  for (const segment of segments) {
    const segmentLines = Math.max(1, Math.ceil(segment.length / charsPerLine));
    totalLines += segmentLines;
  }
  return totalLines;
}

/** Estimate row height based on content */
export function estimateRowHeight(row: any, index: number, stripColorTags: (text: string) => string): number {
  if (!row || row.placeholder) return MIN_ROW_HEIGHT;

  // Check cache first
  if (rowHeightCache.has(index)) {
    return rowHeightCache.get(index)!;
  }

  const sourceText = stripColorTags(row.source || "");
  const targetText = stripColorTags(row.target || "");

  const effectiveCharsPerLine = 55;
  const sourceLines = countDisplayLines(sourceText, effectiveCharsPerLine);
  const targetLines = countDisplayLines(targetText, effectiveCharsPerLine);
  const totalLines = Math.max(sourceLines, targetLines);

  const actualLineHeight = 22;
  const contentHeight = totalLines * actualLineHeight;
  const estimatedHeight = Math.max(MIN_ROW_HEIGHT, contentHeight + CELL_PADDING);
  const finalHeight = Math.min(estimatedHeight, MAX_ROW_HEIGHT);

  rowHeightCache.set(index, finalHeight);
  return finalHeight;
}

/**
 * Rebuild cumulative heights for virtual scroll positioning.
 *
 * Uses $state.snapshot to bypass Svelte proxy overhead when iterating large arrays.
 * Without this, 103k proxy get-trap calls freeze the main thread.
 */
export function rebuildCumulativeHeights(stripColorTags: (text: string) => string): void {
  const total = grid.total;
  if (total === 0) {
    heightData.cumulativeHeights = [0];
    return;
  }

  // CRITICAL: $state.snapshot bypasses Svelte proxy overhead.
  // Without this, 103k proxy get-trap calls take 130ms+ per rebuild
  // (called 3+ times during file open due to prefetch cascade).
  const rows = $state.snapshot(grid.rows);

  const cumulative = new Float64Array(total + 1);
  for (let i = 0; i < total; i++) {
    const row = rows[i];
    const height = row ? estimateRowHeight(row, i, stripColorTags) : MIN_ROW_HEIGHT;
    cumulative[i + 1] = cumulative[i] + height;
  }

  heightData.cumulativeHeights = cumulative as any;
}

/** Get row position using cumulative heights */
export function getRowTop(index: number): number {
  if (heightData.cumulativeHeights.length > index) {
    return heightData.cumulativeHeights[index];
  }
  return index * MIN_ROW_HEIGHT;
}

/** Get height of a specific row */
export function getRowHeight(index: number, stripColorTags: (text: string) => string): number {
  const row = grid.rows[index];
  return row ? estimateRowHeight(row, index, stripColorTags) : MIN_ROW_HEIGHT;
}

/** Total height is last cumulative value */
export function getTotalHeight(): number {
  if (heightData.cumulativeHeights.length > grid.total) {
    return heightData.cumulativeHeights[grid.total];
  }
  return grid.total * MIN_ROW_HEIGHT;
}

/** Binary search to find row at scroll position */
export function findRowAtPosition(scrollPos: number): number {
  if (heightData.cumulativeHeights.length === 0) {
    return Math.floor(scrollPos / MIN_ROW_HEIGHT);
  }

  let low = 0;
  let high = grid.total - 1;

  while (low < high) {
    const mid = Math.floor((low + high) / 2);
    if (heightData.cumulativeHeights[mid + 1] <= scrollPos) {
      low = mid + 1;
    } else {
      high = mid;
    }
  }

  return Math.max(0, low);
}

/** Svelte action: measure actual row height after render and update cache */
export function measureRowHeight(node: HTMLElement, params: { index: number }) {
  requestAnimationFrame(() => {
    const actualHeight = node.scrollHeight;
    const cachedHeight = rowHeightCache.get(params.index);

    if (cachedHeight && Math.abs(actualHeight - cachedHeight) > 10) {
      rowHeightCache.set(params.index, actualHeight);
      // Note: caller should rebuildCumulativeHeights after significant changes
    } else if (!cachedHeight) {
      rowHeightCache.set(params.index, actualHeight);
    }
  });

  return {
    destroy() {
      // Cleanup if needed
    }
  };
}

/** Reset all grid state for file changes */
export function resetGridState(): void {
  grid.allRows = [];
  grid.rows = [];
  grid.total = 0;
  grid.visibleStart = 0;
  grid.visibleEnd = 50;
  grid.loading = false;
  grid.initialLoading = true;
  grid.selectedRowId = null;
  grid.hoveredRowId = null;
  grid.hoveredCell = null;
  grid.inlineEditingRowId = null;
  grid.activeFilter = 'all';
  grid.selectedCategories = [];
  grid.searchTerm = '';
  grid.searchMode = 'contain';
  grid.searchFields = ['source', 'target'];
  grid.rowsVersion = 0;
  rowIndexById.clear();
  rowHeightCache.clear();
  loadedPages.clear();
  tmAppliedRows.clear();
  referenceData.clear();
  qaFlags.clear();
  heightData.cumulativeHeights = [0];
}
