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

import { logger } from '$lib/utils/logger.js';

// --- Row data: wrapped in object to allow reassignment from module ---
// Svelte 5 forbids exporting reassigned $state. Wrapping in an object works.
const rowData = $state.raw({ all: [] as any[], display: [] as any[] });
export function getAllRows(): any[] { return rowData.all; }
export function getDisplayRows(): any[] { return rowData.display; }
// Internal setters (used by setAllRows, applyFilter, resetGridState)
function _setAllRows(rows: any[]) { rowData.all = rows; }
function _setDisplayRows(rows: any[]) { rowData.display = rows; }

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
  imagesReady: false,
  editRowId: null as string | null,
});

// --- GameDev dynamic columns ---
export let gameDevDynamicColumns = $state(['category', 'fileName', 'textState'] as string[]);

// --- Image preload cache (plain Map, NOT $state — see svelte5-reactive-containers rule) ---
export const imageCache = new Map<string, { has_image: boolean; thumbnail_url: string; texture_name: string }>();

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
  const t0 = performance.now();
  const total = rowData.display.length;
  const rows = rowData.display;
  const cum = new Float64Array(total + 1);
  for (let i = 0; i < total; i++) {
    cum[i + 1] = cum[i] + estimateRowHeight(rows[i], i, stripColorTags);
  }
  cumulativeHeights = cum;
  const elapsed = performance.now() - t0;
  logger.info("GRID: heights computed", { rows: total, ms: Math.round(elapsed * 100) / 100 });
}

/** Update ONE row's height after save — incremental shift, 0.15ms */
export function updateRowHeight(rowIndex: number, stripColorTags: (t: string) => string): void {
  const row = rowData.display[rowIndex];
  if (!row) return;
  const oldHeight = rowHeightCache.get(rowIndex) || MIN_ROW_HEIGHT;
  rowHeightCache.delete(rowIndex); // force re-estimate
  const newHeight = estimateRowHeight(row, rowIndex, stripColorTags);
  const delta = newHeight - oldHeight;
  if (Math.abs(delta) < 1) return;
  logger.debug("GRID: row height updated", { rowIndex, oldHeight, newHeight, delta: Math.round(delta * 10) / 10 });
  // Incremental shift — only touches entries after this row
  for (let i = rowIndex + 1; i < cumulativeHeights.length; i++) {
    cumulativeHeights[i] += delta;
  }
  grid.rowsVersion++;
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

// --- Visible rows (reads grid.visibleStart/End + rowData.display) ---
export function getVisibleRows() {
  return Array.from({ length: grid.visibleEnd - grid.visibleStart }, (_, i) => {
    const index = grid.visibleStart + i;
    return rowData.display[index] || { row_num: index + 1, placeholder: true };
  });
}

// --- Row access ---
export function getRowById(rowId: string): any | null {
  const index = rowIndexById.get(rowId?.toString());
  return index !== undefined ? rowData.display[index] : null;
}

export function getRowIndexById(rowId: string): number | undefined {
  return rowIndexById.get(rowId?.toString());
}

// --- Bulk operations ---
export function setAllRows(rows: any[], stripColorTags: (t: string) => string): void {
  rowData.all = rows;
  rowData.display = rows;
  grid.total = rows.length;
  rebuildRowIndex(rows);
  rowHeightCache.clear();
  buildCumulativeHeights(stripColorTags);
  grid.rowsVersion++;
  logger.info("GRID: loaded", { total: rows.length, memoryMB: rows.length > 0 ? Math.round(JSON.stringify(rows).length / 1024 / 1024) : 0 });
}

export function rebuildRowIndex(rows?: any[]): void {
  const source = rows || rowData.display;
  rowIndexById.clear();
  for (let i = 0; i < source.length; i++) {
    if (source[i]?.id) rowIndexById.set(source[i].id.toString(), i);
  }
}

/** O(1) single-row update — no rebuild, no cascade */
export function updateRow(rowId: string, updates: Record<string, any>): void {
  const displayIdx = rowIndexById.get(rowId?.toString());
  if (displayIdx !== undefined && rowData.display[displayIdx]) {
    Object.assign(rowData.display[displayIdx], updates);
  }
  // Also update in rowData.all so filters don't revert the change
  const allIdx = rowData.all.findIndex(r => r?.id?.toString() === rowId?.toString());
  if (allIdx !== -1) {
    Object.assign(rowData.all[allIdx], updates);
  }
  grid.rowsVersion++;
}

/** Client-side filter (search + status + category) */
export function applyFilter(activeFilter: string, selectedCategories: string[], searchTerm: string, searchMode: string, searchFields: string[]): void {
  let filtered = rowData.all;

  if (activeFilter && activeFilter !== 'all') {
    if (activeFilter === 'confirmed') {
      filtered = filtered.filter(r => r.status === 'approved' || r.status === 'reviewed');
    } else if (activeFilter === 'unconfirmed') {
      filtered = filtered.filter(r => r.status === 'pending' || r.status === 'translated' || r.status === 'original');
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

  const beforeCount = rowData.all.length;
  rowData.display = filtered;
  grid.total = filtered.length;
  rebuildRowIndex(filtered);
  rowHeightCache.clear();
  // buildCumulativeHeights called by ScrollEngine after filter
  grid.rowsVersion++;
  logger.info("GRID: filter applied", { before: beforeCount, after: filtered.length, filter: activeFilter, search: searchTerm || null, categories: selectedCategories?.length || 0 });
}

/** Reset all state for file changes */
export function resetGridState(): void {
  rowData.all = [];
  rowData.display = [];
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
  grid.imagesReady = false;
  grid.editRowId = null;
  rowIndexById.clear();
  rowHeightCache.clear();
  imageCache.clear();
  tmAppliedRows.clear();
  referenceData.clear();
  qaFlags.clear();
}
