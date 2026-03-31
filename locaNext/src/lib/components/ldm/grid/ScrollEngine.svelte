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
    imageCache,
    rowIndexById,
    rowHeightCache,
    findRowAtPosition,
    getRowTop,
    MIN_ROW_HEIGHT,
    BUFFER_ROWS,
    setAllRows,
    buildCumulativeHeights,
    applyFilter,
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

  // Throttled scroll logging (max 1 per second)
  let lastScrollLog = 0;

  // ========================================
  // Calculate visible range (unchanged — reads from in-memory rows)
  // ========================================
  export function calculateVisibleRange() {
    if (!containerEl) return;

    containerHeight = containerEl.clientHeight;
    scrollTop = containerEl.scrollTop;

    if (containerHeight > 5000) containerHeight = Math.min(containerHeight, 1200);

    const startRow = findRowAtPosition(scrollTop);
    const visibleCount = Math.ceil(containerHeight / MIN_ROW_HEIGHT);

    grid.visibleStart = Math.max(0, startRow - BUFFER_ROWS);
    grid.visibleEnd = Math.min(grid.total, startRow + visibleCount + BUFFER_ROWS);

    const now = Date.now();
    if (now - lastScrollLog > 1000) {
      logger.debug("GRID: scroll", { offset: Math.round(scrollTop), visible: grid.visibleStart + '-' + grid.visibleEnd });
      lastScrollLog = now;
    }
  }

  // ========================================
  // BULK LOAD — ONE call, ALL rows
  // ========================================
  export async function loadRows() {
    if (!fileId) return;

    // Clear everything
    setAllRows([], stripColorTags);
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
        const rows = data.rows.map((row) => ({ ...row, id: row.id.toString() }));

        setAllRows(rows, stripColorTags);

        logger.success("BULK LOAD complete", {
          total: rows.length,
          fileId,
          memoryMB: Math.round(JSON.stringify(rows).length / 1024 / 1024)
        });

        // Fire-and-forget image preload (non-blocking)
        preloadImages(rows);
      } else {
        const err = await response.json().catch(() => ({}));
        logger.error("BULK LOAD failed", { status: response.status, detail: err.detail });
        grid.loadError = `Failed to load: ${err.detail || 'Server error ' + response.status}`;
      }
    } catch (err) {
      logger.error("BULK LOAD error", { error: err.message });
      grid.loadError = `Connection error: ${err.message}`;
    } finally {
      grid.loading = false;
      grid.initialLoading = false;
    }

    await tick();
    calculateVisibleRange();
  }

  // ========================================
  // IMAGE PRELOAD — batch lookup after bulk load
  // ========================================
  async function preloadImages(rows) {
    const stringIds = [...new Set(
      rows.map(r => r.string_id).filter(Boolean)
    )];

    if (stringIds.length === 0) {
      grid.imagesReady = true;
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/api/ldm/mapdata/images/batch`, {
        method: 'POST',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ string_ids: stringIds }),
      });

      if (response.status === 503) {
        // MegaIndex not built — graceful degradation
        logger.info("GRID: image preload skipped (MegaIndex not built)");
        grid.imagesReady = true;
        return;
      }

      if (!response.ok) {
        logger.warning("GRID: image preload failed", { status: response.status });
        grid.imagesReady = true;
        return;
      }

      const data = await response.json();
      imageCache.clear();
      for (const [sid, entry] of Object.entries(data.results)) {
        imageCache.set(sid, entry);
      }

      logger.info("GRID: preloaded images", {
        total: data.total_requested,
        found: data.total_found,
      });
    } catch (err) {
      logger.warning("GRID: image preload error", { error: err.message });
    }

    grid.imagesReady = true;
  }

  // ========================================
  // CLIENT-SIDE FILTER — unified search + status + category
  // ONE function for all filtering. No separate clientSearch.
  // ========================================
  export function clientFilter(activeFilter, selectedCategories) {
    applyFilter(
      activeFilter,
      selectedCategories,
      grid.searchTerm,
      grid.searchMode,
      grid.searchFields,
    );
    buildCumulativeHeights(stripColorTags);

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
    logger.info("GRID: scrollToRow", { rowId, index, targetTop: Math.round(top) });
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
