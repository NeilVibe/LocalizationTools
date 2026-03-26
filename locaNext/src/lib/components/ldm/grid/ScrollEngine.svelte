<script>
  /**
   * ScrollEngine.svelte -- Virtual scroll, row loading, viewport management.
   *
   * Phase 84 Batch 1: Extracted from VirtualGrid.svelte.
   * Renderless component (logic only, no markup). Parent delegates via bind:this.
   *
   * Writes to gridState: grid.rows, grid.total, grid.loading, grid.initialLoading,
   *   grid.visibleStart, grid.visibleEnd, rowIndexById, rowHeightCache, loadedPages
   */

  import {
    grid,
    rowIndexById,
    rowHeightCache,
    loadedPages,
    heightData,
    rebuildCumulativeHeights,
    findRowAtPosition,
    getRowTop,
    MIN_ROW_HEIGHT,
    PAGE_SIZE,
    BUFFER_ROWS,
    PREFETCH_PAGES,
  } from './gridState.svelte.ts';
  import { logger } from '$lib/utils/logger.js';
  import { getAuthHeaders, getApiBase } from '$lib/utils/api.js';
  import { stripColorTags } from '$lib/utils/colorParser.js';
  import { tick } from 'svelte';

  // Props from parent (configuration only, per D-05)
  let {
    fileId = null,
    fileType = 'translator',
    activeTMs = [],
  } = $props();

  // containerEl comes from gridState (set by CellRenderer via bind:this)
  // Using $derived ensures we always have the latest reference
  let containerEl = $derived(grid.containerEl);

  // API base URL
  let API_BASE = $derived(getApiBase());

  // Module-local state (not shared)
  let loadingPages = $state(new Set());

  // Scroll state
  let scrollTop = $state(0);
  let containerHeight = $state(400);

  // Throttle state for ensureRowsLoaded
  let ensureRowsThrottleTimer = null;
  let lastEnsureRowsTime = 0;
  const ENSURE_ROWS_THROTTLE_MS = 100;

  // ========================================
  // Calculate visible range using binary search
  // ========================================
  export function calculateVisibleRange() {
    if (!containerEl) return;

    containerHeight = containerEl.clientHeight;
    scrollTop = containerEl.scrollTop;

    // Sanity check
    if (containerHeight > 5000) {
      logger.warning("Container height unusually large", {
        containerHeight,
        windowHeight: typeof window !== 'undefined' ? window.innerHeight : 0
      });
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

    ensureRowsLoaded(grid.visibleStart, grid.visibleEnd);
  }

  // ========================================
  // Ensure rows in range are loaded + prefetch
  // ========================================
  async function ensureRowsLoaded(start, end) {
    const now = Date.now();

    if (now - lastEnsureRowsTime < ENSURE_ROWS_THROTTLE_MS) {
      if (!ensureRowsThrottleTimer) {
        ensureRowsThrottleTimer = setTimeout(() => {
          ensureRowsThrottleTimer = null;
          ensureRowsLoadedImmediate(start, end);
        }, ENSURE_ROWS_THROTTLE_MS);
      }
      return;
    }

    lastEnsureRowsTime = now;
    await ensureRowsLoadedImmediate(start, end);
  }

  async function ensureRowsLoadedImmediate(start, end) {
    const startPage = Math.floor(start / PAGE_SIZE) + 1;
    const endPage = Math.floor(end / PAGE_SIZE) + 1;

    const MAX_PAGES_TO_LOAD = 3;
    const limitedEndPage = Math.min(endPage, startPage + MAX_PAGES_TO_LOAD - 1);

    if (endPage > limitedEndPage) {
      logger.warning("Prevented excessive page load", {
        startPage, endPage, limitedTo: limitedEndPage,
        visibleRange: { start, end }
      });
    }

    for (let page = startPage; page <= limitedEndPage; page++) {
      if (!loadedPages.has(page) && !loadingPages.has(page)) {
        await loadPage(page);
      }
    }

    prefetchAdjacentPages(limitedEndPage);
  }

  // ========================================
  // Load a specific page of rows
  // ========================================
  async function loadPage(page) {
    if (!fileId || loadingPages.has(page)) return;

    loadingPages.add(page);
    grid.loading = true;

    try {
      const params = new URLSearchParams({
        page: page.toString(),
        limit: PAGE_SIZE.toString()
      });
      if (grid.searchTerm) {
        params.append('search', grid.searchTerm);
        params.append('search_mode', grid.searchMode);
        params.append('search_fields', grid.searchFields.join(','));
      }
      if (grid.activeFilter && grid.activeFilter !== 'all') {
        params.append('filter', grid.activeFilter);
      }
      if (grid.selectedCategories.length > 0) {
        params.append('category', grid.selectedCategories.join(','));
      }

      let response;
      if (fileType === 'gamedev') {
        const body = {
          xml_path: fileId,
          page: page,
          limit: PAGE_SIZE,
          search: grid.searchTerm || ""
        };
        if (grid.searchTerm) {
          body.search_mode = grid.searchMode;
          body.search_fields = grid.searchFields.join(',');
        }
        if (grid.activeFilter && grid.activeFilter !== 'all') {
          body.filter = grid.activeFilter;
        }
        if (grid.selectedCategories.length > 0) {
          body.category = grid.selectedCategories.join(',');
        }
        response = await fetch(`${API_BASE}/api/ldm/gamedata/rows`, {
          method: 'POST',
          headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
          body: JSON.stringify(body)
        });
      } else {
        response = await fetch(`${API_BASE}/api/ldm/files/${fileId}/rows?${params}`, {
          headers: getAuthHeaders()
        });
      }

      if (response.ok) {
        const data = await response.json();
        grid.total = data.total;

        const isSearching = grid.searchTerm && grid.searchTerm.trim();
        const pageStartIndex = (page - 1) * PAGE_SIZE;
        data.rows.forEach((row, pageIndex) => {
          const index = isSearching ? (pageStartIndex + pageIndex) : (row.row_num - 1);
          const rowData = {
            ...row,
            id: row.id.toString()
          };
          grid.rows[index] = rowData;
          rowIndexById.set(row.id.toString(), index);
          rowHeightCache.delete(index);
        });

        // Trigger reactivity by bumping a version counter instead of spreading 100k+ array
        grid.rowsVersion++;

        rebuildCumulativeHeights(stripColorTags);

        loadedPages.add(page);
        logger.info("SMART LOAD: Page loaded", { page, count: data.rows.length, total: grid.total, indexSize: rowIndexById.size });
      }
    } catch (err) {
      logger.error("Failed to load page", { page, error: err.message });
    } finally {
      loadingPages.delete(page);
      grid.loading = loadingPages.size > 0;
      grid.initialLoading = false;
    }
  }

  // ========================================
  // Prefetch adjacent pages
  // ========================================
  function prefetchAdjacentPages(currentPage) {
    for (let i = 1; i <= PREFETCH_PAGES; i++) {
      const nextPage = currentPage + i;
      const maxPage = Math.ceil(grid.total / PAGE_SIZE);
      if (nextPage <= maxPage && !loadedPages.has(nextPage) && !loadingPages.has(nextPage)) {
        setTimeout(() => loadPage(nextPage), i * 50);
      }
    }
  }

  // ========================================
  // loadRows -- main entry point (exported)
  // ========================================
  export async function loadRows() {
    if (!fileId) return;

    // Reset state
    grid.rows = [];
    loadedPages.clear();
    loadingPages.clear();
    rowIndexById.clear();
    rowHeightCache.clear();
    grid.total = 0;
    grid.initialLoading = true;

    try {
      const params = new URLSearchParams({
        page: '1',
        limit: PAGE_SIZE.toString()
      });

      if (grid.searchTerm && grid.searchTerm.trim()) {
        params.append('search', grid.searchTerm.trim());
        params.append('search_mode', grid.searchMode);
        params.append('search_fields', grid.searchFields.join(','));
        logger.info("loadRows with search", { searchTerm: grid.searchTerm, searchMode: grid.searchMode, searchFields: grid.searchFields });
      }

      let response;
      if (fileType === 'gamedev') {
        const body = {
          xml_path: fileId,
          page: 1,
          limit: PAGE_SIZE,
          search: ""
        };
        if (grid.searchTerm && grid.searchTerm.trim()) {
          body.search = grid.searchTerm.trim();
          body.search_mode = grid.searchMode;
          body.search_fields = grid.searchFields.join(',');
        }
        response = await fetch(`${API_BASE}/api/ldm/gamedata/rows`, {
          method: 'POST',
          headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
          body: JSON.stringify(body)
        });
      } else {
        response = await fetch(`${API_BASE}/api/ldm/files/${fileId}/rows?${params}`, {
          headers: getAuthHeaders()
        });
      }

      if (response.ok) {
        const data = await response.json();
        grid.total = data.total;

        const isSearching = grid.searchTerm && grid.searchTerm.trim();
        data.rows.forEach((row, pageIndex) => {
          const index = isSearching ? pageIndex : (row.row_num - 1);
          const rowData = {
            ...row,
            id: row.id.toString()
          };
          grid.rows[index] = rowData;
          rowIndexById.set(row.id.toString(), index);
        });
        // Trigger reactivity without creating a dense copy of the sparse array
        grid.rowsVersion++;
        loadedPages.add(1);

        rebuildCumulativeHeights(stripColorTags);

        logger.info("SMART LOAD: Initial page loaded", { total: grid.total, loaded: data.rows.length, indexSize: rowIndexById.size });

        prefetchAdjacentPages(1);
      }
    } catch (err) {
      logger.error("Failed to load rows", { error: err.message });
    } finally {
      grid.initialLoading = false;
    }

    await tick();
    calculateVisibleRange();
  }

  // ========================================
  // handleScroll -- scroll event handler
  // ========================================
  export function handleScroll() {
    calculateVisibleRange();
  }

  // ========================================
  // scrollToRowById / scrollToRowNum
  // ========================================
  export function scrollToRowById(rowId) {
    const row = grid.rows[rowIndexById.get(rowId?.toString())];
    if (!row) {
      logger.warning("Row not found for scroll", { rowId, loadedRows: grid.rows.filter(r => r).length });
      return false;
    }

    const index = rowIndexById.get(rowId.toString());
    if (index === undefined) {
      logger.warning("Row index not found", { rowId });
      return false;
    }

    grid.selectedRowId = row.id;

    if (containerEl) {
      const scrollPos = getRowTop(index);
      const centeredPos = Math.max(0, scrollPos - (containerHeight / 2) + 20);
      containerEl.scrollTop = centeredPos;
      logger.userAction("Scrolled to row", { rowId, index, scrollPos: centeredPos });
    }

    return true;
  }

  export function scrollToRowNum(rowNum) {
    const index = rowNum - 1;
    const row = grid.rows[index];

    if (!row) {
      logger.warning("Row not found for scroll", { rowNum });
      return false;
    }

    return scrollToRowById(row.id);
  }
</script>
