<script>
  /**
   * ScrollEngine.svelte -- BULK LOAD architecture.
   *
   * ONE API call loads ALL rows into memory. No page-by-page.
   * Search/filter happens client-side via Array.filter(). Zero API calls during browsing.
   * Virtual scroll only determines which rows to RENDER from the in-memory array.
   */

  import {
    grid,
    rowIndexById,
    rowHeightCache,
    heightData,
    rebuildCumulativeHeights,
    findRowAtPosition,
    getRowTop,
    MIN_ROW_HEIGHT,
    BUFFER_ROWS,
  } from './gridState.svelte.ts';
  import { logger } from '$lib/utils/logger.js';
  import { getAuthHeaders, getApiBase } from '$lib/utils/api.js';
  import { stripColorTags } from '$lib/utils/colorParser.js';
  import { tick } from 'svelte';

  // Props from parent
  let {
    fileId = null,
    fileType = 'translator',
    activeTMs = [],
  } = $props();

  let containerEl = $derived(grid.containerEl);
  let API_BASE = $derived(getApiBase());

  // Scroll state
  let scrollTop = $state(0);
  let containerHeight = $state(400);

  // ========================================
  // Calculate visible range (unchanged — reads from in-memory rows)
  // ========================================
  export function calculateVisibleRange() {
    if (!containerEl) return;

    containerHeight = containerEl.clientHeight;
    scrollTop = containerEl.scrollTop;

    if (containerHeight > 5000) {
      containerHeight = Math.min(containerHeight, 1200);
    }

    const startRow = findRowAtPosition(scrollTop);
    let endRow = startRow;
    const viewportBottom = scrollTop + containerHeight;

    while (endRow < grid.total && getRowTop(endRow) < viewportBottom) {
      endRow++;
    }

    grid.visibleStart = Math.max(0, startRow - BUFFER_ROWS);
    grid.visibleEnd = Math.min(grid.total, endRow + BUFFER_ROWS);
    // No ensureRowsLoaded — ALL rows already in memory
  }

  // ========================================
  // BULK LOAD — ONE call, ALL rows
  // ========================================
  export async function loadRows() {
    if (!fileId) return;

    // Clear everything
    grid.allRows = [];
    grid.rows = [];
    grid.total = 0;
    rowIndexById.clear();
    rowHeightCache.clear();
    grid.loading = true;
    grid.initialLoading = true;

    try {
      let response;

      if (fileType === 'gamedev') {
        // GameDev: use existing POST endpoint with high limit
        response = await fetch(`${API_BASE}/api/ldm/gamedata/rows`, {
          method: 'POST',
          headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
          body: JSON.stringify({ xml_path: fileId, page: 1, limit: 999999 })
        });
      } else {
        // Translator: use bulk endpoint
        response = await fetch(`${API_BASE}/api/ldm/files/${fileId}/rows/all`, {
          headers: getAuthHeaders()
        });
      }

      if (response.ok) {
        const data = await response.json();

        // Store ALL rows in memory
        const allRows = data.rows.map((row, i) => {
          const rowData = { ...row, id: row.id.toString() };
          rowIndexById.set(row.id.toString(), i);
          return rowData;
        });

        grid.allRows = allRows;
        grid.rows = allRows;
        grid.total = allRows.length;
        grid.rowsVersion++;

        rebuildCumulativeHeights(stripColorTags);

        logger.success("BULK LOAD complete", {
          total: allRows.length,
          fileId,
          memoryMB: Math.round(JSON.stringify(allRows).length / 1024 / 1024)
        });
      } else {
        const err = await response.json().catch(() => ({}));
        logger.error("BULK LOAD failed", { status: response.status, detail: err.detail });
      }
    } catch (err) {
      logger.error("BULK LOAD error", { error: err.message });
    } finally {
      grid.loading = false;
      grid.initialLoading = false;
    }

    await tick();
    calculateVisibleRange();
  }

  // ========================================
  // CLIENT-SIDE FILTER — unified search + status + category
  // ONE function for all filtering. No separate clientSearch.
  // ========================================
  export function clientFilter(activeFilter, selectedCategories) {
    let filtered = grid.allRows;

    // 1. Status filter
    if (activeFilter && activeFilter !== 'all') {
      if (activeFilter === 'confirmed') {
        filtered = filtered.filter(r => r.status === 'approved' || r.status === 'reviewed');
      } else if (activeFilter === 'unconfirmed') {
        filtered = filtered.filter(r => r.status === 'pending' || r.status === 'translated');
      } else if (activeFilter === 'qa_flagged') {
        filtered = filtered.filter(r => (r.qa_flag_count || 0) > 0);
      }
    }

    // 2. Category filter
    if (selectedCategories && selectedCategories.length > 0) {
      const catSet = new Set(selectedCategories);
      filtered = filtered.filter(r => catSet.has(r.category));
    }

    // 3. Search filter (mode-aware: contain, exact, not_contain)
    const term = grid.searchTerm?.trim().toLowerCase();
    if (term) {
      const fields = grid.searchFields || ['source', 'target'];
      const mode = grid.searchMode || 'contain';

      if (mode === 'exact') {
        filtered = filtered.filter(row =>
          fields.some(f => row[f]?.toLowerCase() === term)
        );
      } else if (mode === 'not_contain') {
        filtered = filtered.filter(row =>
          fields.every(f => !row[f]?.toLowerCase().includes(term))
        );
      } else {
        // contain (default)
        filtered = filtered.filter(row =>
          fields.some(f => row[f]?.toLowerCase().includes(term))
        );
      }
    }

    grid.rows = filtered;
    grid.total = filtered.length;

    rowIndexById.clear();
    grid.rows.forEach((row, i) => {
      rowIndexById.set(row.id.toString(), i);
    });

    rowHeightCache.clear();
    grid.rowsVersion++;
    rebuildCumulativeHeights(stripColorTags);

    if (containerEl) containerEl.scrollTop = 0;
    calculateVisibleRange();
  }

  // ========================================
  // handleScroll — throttled for 60fps
  // ========================================
  let scrollRAF = null;

  export function handleScroll() {
    if (scrollRAF) return;
    scrollRAF = requestAnimationFrame(() => {
      scrollRAF = null;
      calculateVisibleRange();
    });
  }

  // ========================================
  // scrollToRowById
  // ========================================
  export function scrollToRowById(rowId) {
    const index = rowIndexById.get(rowId?.toString());
    if (index === undefined || !containerEl) return;

    const top = getRowTop(index);
    containerEl.scrollTop = top;
    grid.selectedRowId = rowId.toString();
    calculateVisibleRange();
  }

  export function scrollToRowNum(rowNum) {
    const index = rowNum - 1;
    if (index < 0 || index >= grid.total || !containerEl) return;

    const top = getRowTop(index);
    containerEl.scrollTop = top;
    calculateVisibleRange();
  }
</script>
