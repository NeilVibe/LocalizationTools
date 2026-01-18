<script>
  import {
    Search,
    InlineLoading,
    Tag,
    Button,
    Dropdown
  } from "carbon-components-svelte";
  import { Edit, Locked, Settings, ChevronDown } from "carbon-icons-svelte";
  import { createEventDispatcher, onMount, onDestroy, tick } from "svelte";
  import { get } from "svelte/store";
  import { logger } from "$lib/utils/logger.js";
  import { getAuthHeaders, getApiBase } from "$lib/utils/api.js";
  import { ldmStore, joinFile, leaveFile, lockRow, unlockRow, isRowLocked, onCellUpdate, ldmConnected } from "$lib/stores/ldm.js";
  import { preferences, getFontSizeValue, getFontFamilyValue, getFontColorValue } from "$lib/stores/preferences.js";
  import { WarningAltFilled } from "carbon-icons-svelte";
  import PresenceBar from "./PresenceBar.svelte";
  import ColorText from "./ColorText.svelte";
  import { stripColorTags, paColorToHtml, htmlToPaColor, hexToCSS } from "$lib/utils/colorParser.js";

  const dispatch = createEventDispatcher();

  // API base URL - centralized in api.js
  let API_BASE = $derived(getApiBase());

  // Svelte 5: Props
  let { fileId = $bindable(null), fileName = "", activeTMs = [], isLocalFile = false } = $props();

  // Virtual scrolling constants
  const MIN_ROW_HEIGHT = 48; // Minimum row height (base)
  const MAX_ROW_HEIGHT = 800; // Allow cells to expand much more for long content
  const CHARS_PER_LINE = 45; // Estimated chars per line for height calc
  const LINE_HEIGHT = 26; // Height per line of text (14px * 1.6 line-height + buffer)
  const CELL_PADDING = 24; // Vertical padding in cells (0.75rem * 2)
  const BUFFER_ROWS = 8; // Extra rows to render above/below viewport
  const PAGE_SIZE = 100; // Rows per page to fetch
  const PREFETCH_PAGES = 2; // Number of pages to prefetch ahead/behind

  // VARIABLE HEIGHT VIRTUALIZATION: Height cache and cumulative positions
  let rowHeightCache = $state(new Map()); // row_index -> estimated height
  let cumulativeHeights = $state([]); // cumulativeHeights[i] = position of row i

  // Real-time subscription
  let cellUpdateUnsubscribe = null;

  // Svelte 5: State
  let loading = $state(false);
  let initialLoading = $state(true);
  let rows = $state([]); // Cached rows (sparse array by row_num)
  let total = $state(0);
  let searchTerm = $state("");
  let searchDebounceTimer = null;

  // Note: Clear button directly manipulates both searchTerm and DOM input value

  // P2: Filter state
  let activeFilter = $state("all"); // 'all' | 'confirmed' | 'unconfirmed' | 'qa_flagged'
  const filterOptions = [
    { id: "all", text: "All Rows" },
    { id: "confirmed", text: "Confirmed" },
    { id: "unconfirmed", text: "Unconfirmed" },
    { id: "qa_flagged", text: "QA Flagged" }
  ];

  // P5: Advanced Search state
  let searchMode = $state("contain"); // 'contain' | 'exact' | 'not_contain' | 'fuzzy'
  const searchModeOptions = [
    { id: "contain", text: "Contains", icon: "⊃" },
    { id: "exact", text: "Exact", icon: "=" },
    { id: "not_contain", text: "Excludes", icon: "≠" },
    { id: "fuzzy", text: "Similar", icon: "≈" }
  ];

  let searchFields = $state(["source", "target"]); // Default search in source and target
  const searchFieldOptions = [
    { id: "string_id", text: "ID" },
    { id: "source", text: "Source" },
    { id: "target", text: "Target" }
  ];

  // P5: Search settings popover state
  let showSearchSettings = $state(false);

  // Svelte 5: Virtual scroll state
  let containerEl = $state(null);
  let scrollTop = $state(0);
  let containerHeight = $state(400);
  let visibleStart = $state(0);
  let visibleEnd = $state(50);

  // Page cache - track which pages we've loaded
  let loadedPages = $state(new Set());
  let loadingPages = $state(new Set());

  // SMART INDEXING: Row index map for O(1) lookups by row_id
  let rowIndexById = $state(new Map()); // row_id -> array index

  // SMART INDEXING: O(1) row lookup by ID
  function getRowById(rowId) {
    const index = rowIndexById.get(rowId.toString());
    return index !== undefined ? rows[index] : null;
  }

  // SMART INDEXING: O(1) row index lookup
  function getRowIndexById(rowId) {
    return rowIndexById.get(rowId.toString());
  }

  // Go to row state - REMOVED (BUG-001 - not useful)

  // Phase 2: Inline editing state (MemoQ-style) - replaces modal editing
  let inlineEditingRowId = $state(null);
  let inlineEditValue = $state("");
  let inlineEditTextarea = $state(null);
  let isCancellingEdit = $state(false); // Flag to prevent blur-save race condition

  // Color picker state for inline editing
  let showColorPicker = $state(false);
  let colorPickerPosition = $state({ x: 0, y: 0 });
  let textSelection = $state({ start: 0, end: 0, text: "" });

  // Default colors for PAColor format (fallback if source has no colors)
  const PAColors = [
    { name: "Gold", hex: "0xffe9bd23", css: "#e9bd23" },
    { name: "Green", hex: "0xff67d173", css: "#67d173" },
    { name: "Blue", hex: "0xff4a90d9", css: "#4a90d9" },
    { name: "Red", hex: "0xffff4444", css: "#ff4444" },
    { name: "Purple", hex: "0xffb88fdc", css: "#b88fdc" },
    { name: "Orange", hex: "0xffff9500", css: "#ff9500" },
    { name: "Cyan", hex: "0xff00bcd4", css: "#00bcd4" },
    { name: "Pink", hex: "0xffe91e63", css: "#e91e63" }
  ];

  /**
   * UI-113: Extract unique colors from source text
   * Returns array of color objects {hex, css, name} found in source
   */
  function extractColorsFromSource(sourceText) {
    if (!sourceText) return [];

    const colorPattern = /<PAColor(0x[0-9a-fA-F]{6,8})>/gi;
    const uniqueColors = new Map();
    let match;

    while ((match = colorPattern.exec(sourceText)) !== null) {
      const hex = match[1].toLowerCase();
      if (!uniqueColors.has(hex)) {
        const css = hexToCSS(hex);
        // Try to find a matching name from PAColors
        const known = PAColors.find(c => c.hex.toLowerCase() === hex);
        uniqueColors.set(hex, {
          hex: hex,
          css: css,
          name: known?.name || css // Use CSS color as name if unknown
        });
      }
    }

    return Array.from(uniqueColors.values());
  }

  // UI-113: Derived state for colors available in current editing row's source
  let sourceColors = $derived.by(() => {
    if (!inlineEditingRowId) return [];
    const row = getRowById(inlineEditingRowId);
    return row ? extractColorsFromSource(row.source) : [];
  });

  // Selected row state (click-based)
  let selectedRowId = $state(null);

  // HOVER SYSTEM: Track actual mouse hover (not click)
  let hoveredRowId = $state(null);
  let hoveredCell = $state(null); // 'source' | 'target' | null

  // TM suggestions state
  let tmSuggestions = $state([]);
  let tmLoading = $state(false);

  // P2: QA state
  let qaLoading = $state(false);
  let lastQaResult = $state(null); // Latest QA check result (for QA badge updates)

  // UX-002: Cell context menu state
  let showContextMenu = $state(false);
  let contextMenuPosition = $state({ x: 0, y: 0 });
  let contextMenuRowId = $state(null);

  // ============================================================
  // UNIFIED COLUMN RESIZE SYSTEM (UI-083)
  // All columns use full-height resize bars, factorized logic
  // ============================================================

  // Column widths (px for fixed, % for source/target split)
  let indexColumnWidth = $state(60);
  let stringIdColumnWidth = $state(150);
  let sourceWidthPercent = $state(50);
  let referenceColumnWidth = $state(300);

  // Column width limits (min, max)
  const COLUMN_LIMITS = {
    index: { min: 40, max: 120 },
    stringId: { min: 80, max: 300 },
    source: { min: 20, max: 80 }, // percentage
    reference: { min: 150, max: 500 }
  };

  // Resize state (unified) - using simple variables to avoid reactivity issues
  let isResizing = $state(false);
  let resizeColumn = $state(null);    // 'index' | 'stringId' | 'source' | 'reference'
  let resizeStartX = $state(0);
  let resizeStartValue = $state(0);   // px or % depending on column

  // Calculate total fixed width before source column
  function getFixedWidthBefore() {
    let width = 0;
    if ($preferences.showIndex) width += indexColumnWidth;
    if ($preferences.showStringId) width += stringIdColumnWidth;
    return width;
  }

  // Calculate total fixed width after target column
  function getFixedWidthAfter() {
    return $preferences.showReference ? referenceColumnWidth : 0;
  }

  // Container width for position calculations (reactive)
  let containerWidth = $state(800);

  // Update container width when it changes
  function updateContainerWidth() {
    if (containerEl) {
      containerWidth = containerEl.clientWidth;
    }
  }

  // Get visible resize bars based on preferences
  let visibleResizeBars = $derived.by(() => {
    const bars = [];
    if ($preferences.showIndex) bars.push('index');
    if ($preferences.showStringId) bars.push('stringId');
    bars.push('source'); // Always visible (source/target split)
    if ($preferences.showReference) bars.push('reference');
    return bars;
  });

  // Pre-compute resize bar positions (REACTIVE)
  let resizeBarPositions = $derived.by(() => {
    const positions = {};
    let pos = 0;

    // Index bar position (at right edge of index column)
    if ($preferences.showIndex) {
      positions['index'] = indexColumnWidth;
      pos += indexColumnWidth;
    }

    // StringID bar position (at right edge of stringId column)
    if ($preferences.showStringId) {
      positions['stringId'] = pos + stringIdColumnWidth;
      pos += stringIdColumnWidth;
    }

    // Source bar position (between source and target, percentage-based)
    const fixedAfter = $preferences.showReference ? referenceColumnWidth : 0;
    const fixedTotal = pos + fixedAfter;
    const flexWidth = containerWidth - fixedTotal;
    positions['source'] = pos + (flexWidth * sourceWidthPercent / 100);

    // Reference bar position (at left edge of reference column)
    if ($preferences.showReference) {
      positions['reference'] = containerWidth - referenceColumnWidth;
    }

    return positions;
  });

  // Table column definitions (base config, actual widths from state)
  // Note: Status column REMOVED - using cell colors instead
  const allColumns = {
    row_num: { key: "row_num", label: "#", width: 60, prefKey: "showIndex" },
    string_id: { key: "string_id", label: "StringID", width: 150, prefKey: "showStringId" },
    source: { key: "source", label: "Source (KR)", width: 350, always: true },
    target: { key: "target", label: "Target", width: 350, always: true },
    reference: { key: "reference", label: "Reference", width: 300, prefKey: "showReference" },
    tm_result: { key: "tm_result", label: "TM Match", width: 300, prefKey: "showTmResults" }
  };

  // Reference data cache (loaded when referenceFileId changes)
  let referenceData = $state(new Map()); // string_id -> { target, source }
  let referenceLoading = $state(false);

  // TM results cache (per row)
  let tmResults = $state(new Map()); // row_id -> { target, similarity, source }

  // Svelte 5: Derived - visible columns based on preferences
  let visibleColumns = $derived(getVisibleColumns($preferences));

  // Svelte 5: Derived - font styles from preferences (UI-031, UI-032, P2)
  let gridFontSize = $derived(getFontSizeValue($preferences.fontSize));
  let gridFontWeight = $derived($preferences.fontWeight === 'bold' ? '600' : '400');
  let gridFontFamily = $derived(getFontFamilyValue($preferences.fontFamily));
  let gridFontColor = $derived(getFontColorValue($preferences.fontColor));

  function getVisibleColumns(prefs) {
    const cols = [];

    // Optional: Index number
    if (prefs.showIndex) {
      cols.push(allColumns.row_num);
    }

    // Optional: String ID
    if (prefs.showStringId) {
      cols.push(allColumns.string_id);
    }

    // Always visible: Source and Target
    cols.push(allColumns.source);
    cols.push(allColumns.target);

    // Optional: Reference column (on the right)
    if (prefs.showReference) {
      cols.push(allColumns.reference);
    }

    // UI-039: Removed TM Results column - only StringID (left) and Reference (right) are supported

    return cols;
  }

  // Legacy: columns array for compatibility (deprecated, use visibleColumns)
  const columns = [
    { key: "row_num", label: "#", width: 60 },
    { key: "string_id", label: "StringID", width: 150 },
    { key: "source", label: "Source (KR)", width: 350 },
    { key: "target", label: "Target", width: 350 }
  ];

  // Status options
  const statusOptions = [
    { value: "pending", label: "Pending" },
    { value: "translated", label: "Translated" },
    { value: "reviewed", label: "Reviewed" },
    { value: "approved", label: "Approved" }
  ];

  // VARIABLE HEIGHT: Calculate visible range using binary search
  // O(log n) complexity for finding start row, O(k) for visible rows
  function calculateVisibleRange() {
    if (!containerEl) return;

    containerHeight = containerEl.clientHeight;
    scrollTop = containerEl.scrollTop;

    // Sanity check: container height shouldn't be larger than viewport
    if (containerHeight > 5000) {
      logger.warning("Container height unusually large", {
        containerHeight,
        windowHeight: typeof window !== 'undefined' ? window.innerHeight : 0
      });
      containerHeight = Math.min(containerHeight, 1200);
    }

    // Use binary search to find first visible row
    const startRow = findRowAtPosition(scrollTop);

    // Find end row by scanning forward until we exceed viewport
    let endRow = startRow;
    const viewportBottom = scrollTop + containerHeight;

    while (endRow < total && getRowTop(endRow) < viewportBottom) {
      endRow++;
    }

    // Add buffer rows
    visibleStart = Math.max(0, startRow - BUFFER_ROWS);
    visibleEnd = Math.min(total, endRow + BUFFER_ROWS);

    // Check if we need to load more data
    ensureRowsLoaded(visibleStart, visibleEnd);
  }

  // SMART INDEXING: Ensure rows in range are loaded + prefetch ahead
  // Throttled to prevent excessive API calls during fast scrolling
  let ensureRowsThrottleTimer = null;
  let lastEnsureRowsTime = 0;
  const ENSURE_ROWS_THROTTLE_MS = 100; // Max 10 API batches per second

  async function ensureRowsLoaded(start, end) {
    const now = Date.now();

    // Throttle API calls during fast scrolling
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

    // BUG-036-FIX: Prevent loading too many pages at once (max 3 pages visible)
    const MAX_PAGES_TO_LOAD = 3;
    const limitedEndPage = Math.min(endPage, startPage + MAX_PAGES_TO_LOAD - 1);

    if (endPage > limitedEndPage) {
      logger.warning("Prevented excessive page load", {
        startPage, endPage, limitedTo: limitedEndPage,
        visibleRange: { start, end }
      });
    }

    // Load visible pages (blocking)
    for (let page = startPage; page <= limitedEndPage; page++) {
      if (!loadedPages.has(page) && !loadingPages.has(page)) {
        await loadPage(page);
      }
    }

    // SMART PREFETCH: Load adjacent pages in background (non-blocking)
    prefetchAdjacentPages(limitedEndPage);
  }

  // Load a specific page of rows
  async function loadPage(page) {
    if (!fileId || loadingPages.has(page)) return;

    loadingPages.add(page);
    loading = true;

    try {
      const params = new URLSearchParams({
        page: page.toString(),
        limit: PAGE_SIZE.toString()
      });
      if (searchTerm) {
        params.append('search', searchTerm);
        params.append('search_mode', searchMode);
        params.append('search_fields', searchFields.join(','));
      }
      // P2: Add filter param
      if (activeFilter && activeFilter !== 'all') {
        params.append('filter', activeFilter);
      }

      // P9: Unified endpoint - backend handles both PostgreSQL and SQLite
      const response = await fetch(`${API_BASE}/api/ldm/files/${fileId}/rows?${params}`, {
        headers: getAuthHeaders()
      });

      if (response.ok) {
        const data = await response.json();
        total = data.total;

        // Store rows by their index position
        // SMART INDEXING: Also build index map for O(1) lookups
        // BUG FIX: When searching, use sequential indices not original row_num
        const isSearching = searchTerm && searchTerm.trim();
        const pageStartIndex = (page - 1) * PAGE_SIZE;
        data.rows.forEach((row, pageIndex) => {
          // For search: use sequential index based on page position
          // For normal: use row_num - 1 (preserves position for pagination)
          const index = isSearching ? (pageStartIndex + pageIndex) : (row.row_num - 1);
          const rowData = {
            ...row,
            id: row.id.toString()
          };
          rows[index] = rowData;
          rowIndexById.set(row.id.toString(), index); // O(1) lookup index
          // Clear height cache for this row (will be recalculated)
          rowHeightCache.delete(index);
        });

        // Force reactivity
        rows = [...rows];

        // VARIABLE HEIGHT: Rebuild cumulative heights after loading new rows
        rebuildCumulativeHeights();

        loadedPages.add(page);
        logger.info("SMART LOAD: Page loaded", { page, count: data.rows.length, total, indexSize: rowIndexById.size });
      }
    } catch (err) {
      logger.error("Failed to load page", { page, error: err.message });
    } finally {
      loadingPages.delete(page);
      loading = loadingPages.size > 0;
      initialLoading = false;
    }
  }

  // BUG-037: Export function to scroll to a row and highlight it
  export function scrollToRowById(rowId) {
    // Use O(1) lookup via rowIndexById map
    const row = getRowById(rowId);
    if (!row) {
      logger.warning("Row not found for scroll", { rowId, loadedRows: rows.filter(r => r).length });
      return false;
    }

    // Get row index from map (more reliable than row_num - 1)
    const index = getRowIndexById(rowId);
    if (index === undefined) {
      logger.warning("Row index not found", { rowId });
      return false;
    }

    // Set selected to highlight the row
    selectedRowId = row.id;

    // Scroll to row position
    if (containerEl) {
      const scrollPos = getRowTop(index);
      // Center the row in view (subtract half container height)
      const centeredPos = Math.max(0, scrollPos - (containerHeight / 2) + 20);
      containerEl.scrollTop = centeredPos;
      logger.userAction("Scrolled to row", { rowId, index, scrollPos: centeredPos });
    }

    return true;
  }

  // BUG-037: Export function to scroll to a row by row number
  export function scrollToRowNum(rowNum) {
    // Row number is 1-based, find by index
    const index = rowNum - 1;
    const row = rows[index];

    if (!row) {
      logger.warning("Row not found for scroll", { rowNum });
      return false;
    }

    return scrollToRowById(row.id);
  }

  // BUG-037: Export function to navigate to row and start editing (for QA panel integration)
  // Phase 2: Now uses inline editing instead of modal
  export async function openEditModalByRowId(rowId) {
    // First scroll to and highlight the row
    scrollToRowById(rowId);

    // Use O(1) lookup
    const row = getRowById(rowId);
    if (row) {
      // Phase 2: Use inline editing instead of modal
      await startInlineEdit(row);
    } else {
      logger.warning("Row not loaded yet", { rowId });
    }
  }

  // Phase 2: Export function to update a row's QA flag count (for Ctrl+D dismiss)
  export function updateRowQAFlag(rowId, flagCount) {
    const rowIndex = getRowIndexById(rowId);
    if (rowIndex !== undefined && rows[rowIndex]) {
      rows[rowIndex] = {
        ...rows[rowIndex],
        qa_flag_count: flagCount
      };
      rows = [...rows]; // Trigger reactivity
      logger.info('Updated row QA flag', { rowId, flagCount });
    } else {
      logger.warning("Row not found for QA flag update", { rowId });
    }
  }

  export async function loadRows() {
    if (!fileId) return;

    // Reset state INSTANTLY - don't wait for API
    rows = [];
    loadedPages.clear();
    loadingPages.clear();
    rowIndexById.clear(); // SMART INDEXING: Clear index map
    rowHeightCache.clear(); // VARIABLE HEIGHT: Clear height cache
    cumulativeHeights = [0]; // VARIABLE HEIGHT: Reset cumulative heights
    total = 0;
    initialLoading = true;

    // OPTIMIZATION: Single API call for first page + count (not 2 calls)
    // The first page response includes total count
    try {
      const params = new URLSearchParams({
        page: '1',
        limit: PAGE_SIZE.toString()
      });

      // Add search term if present
      if (searchTerm && searchTerm.trim()) {
        params.append('search', searchTerm.trim());
        params.append('search_mode', searchMode);
        params.append('search_fields', searchFields.join(','));
        logger.info("loadRows with search", { searchTerm, searchMode, searchFields });
      }

      // P9: Unified endpoint - backend handles both PostgreSQL and SQLite
      const response = await fetch(`${API_BASE}/api/ldm/files/${fileId}/rows?${params}`, {
        headers: getAuthHeaders()
      });

      if (response.ok) {
        const data = await response.json();
        total = data.total;

        // INSTANT: Store rows immediately + build index
        // BUG FIX: When searching, use sequential indices (0, 1, 2...) not original row_num
        // Original row_num is kept in row data for display, but storage index must be sequential
        const isSearching = searchTerm && searchTerm.trim();
        data.rows.forEach((row, pageIndex) => {
          // For search: use sequential index (page 1 = 0-49)
          // For normal: use row_num - 1 (preserves position for pagination)
          const index = isSearching ? pageIndex : (row.row_num - 1);
          const rowData = {
            ...row,
            id: row.id.toString()
          };
          rows[index] = rowData;
          rowIndexById.set(row.id.toString(), index); // O(1) lookup
        });
        rows = [...rows];
        loadedPages.add(1);

        // VARIABLE HEIGHT: Build cumulative heights for positioning
        rebuildCumulativeHeights();

        logger.info("SMART LOAD: Initial page loaded", { total, loaded: data.rows.length, indexSize: rowIndexById.size });

        // PREFETCH: Start loading adjacent pages in background (non-blocking)
        prefetchAdjacentPages(1);
      }
    } catch (err) {
      logger.error("Failed to load rows", { error: err.message });
    } finally {
      initialLoading = false;
    }

    // Calculate visible range immediately
    await tick();
    calculateVisibleRange();
  }

  // SMART INDEXING: Prefetch pages in background for smooth scrolling
  function prefetchAdjacentPages(currentPage) {
    // Prefetch next pages in background (non-blocking)
    for (let i = 1; i <= PREFETCH_PAGES; i++) {
      const nextPage = currentPage + i;
      const maxPage = Math.ceil(total / PAGE_SIZE);
      if (nextPage <= maxPage && !loadedPages.has(nextPage) && !loadingPages.has(nextPage)) {
        // Use setTimeout to not block the main thread
        setTimeout(() => loadPage(nextPage), i * 50);
      }
    }
  }

  // Handle scroll - update visible range immediately for smooth scrolling
  // API calls are throttled inside ensureRowsLoaded
  function handleScroll() {
    calculateVisibleRange();
  }

  // Handle search with debounce
  function handleSearch(event) {
    logger.info("handleSearch triggered", { searchTerm, event: event?.type || 'no event' });
    if (searchDebounceTimer) clearTimeout(searchDebounceTimer);
    searchDebounceTimer = setTimeout(() => {
      logger.info("handleSearch executing search", { searchTerm });
      loadedPages.clear();
      rows = [];
      loadRows();
    }, 300);
  }

  // P2: Handle filter change
  function handleFilterChange(event) {
    activeFilter = event.detail.selectedId;
    loadedPages.clear();
    rows = [];
    loadRows();
    logger.userAction("Filter changed", { filter: activeFilter });
  }

  // Go to specific row - REMOVED (BUG-001 - not useful)

  // Fetch TM suggestions for a source text - USES HIERARCHY TMs
  async function fetchTMSuggestions(sourceText, rowId) {
    if (!sourceText || !sourceText.trim()) {
      tmSuggestions = [];
      return;
    }

    // Only search if we have active TMs from hierarchy
    if (!activeTMs || activeTMs.length === 0) {
      tmSuggestions = [];
      return;
    }

    tmLoading = true;
    tmSuggestions = [];

    try {
      const params = new URLSearchParams({
        source: sourceText,
        threshold: $preferences.tmThreshold.toString(),
        max_results: '5',
        tm_id: activeTMs[0].tm_id.toString()  // Use hierarchy TM, not preferences
      });
      if (fileId) params.append('file_id', fileId.toString());
      if (rowId) params.append('exclude_row_id', rowId.toString());

      const response = await fetch(`${API_BASE}/api/ldm/tm/suggest?${params}`, {
        headers: getAuthHeaders()
      });

      if (response.ok) {
        const data = await response.json();
        tmSuggestions = data.suggestions || [];
        logger.info("TM suggestions fetched", { count: tmSuggestions.length, tmId: activeTMs[0].tm_id });
      }
    } catch (err) {
      logger.error("Failed to fetch TM suggestions", { error: err.message });
    } finally {
      tmLoading = false;
    }
  }

  // Phase 2: applyTMSuggestion REMOVED - TM application now handled via
  // TMQAPanel.svelte 'applyTM' event -> LDM.svelte -> applyTMToRow()

  // P2: Run QA check on a row
  async function runQACheck(rowId) {
    if (!rowId) return null;

    qaLoading = true;
    lastQaResult = null;

    try {
      const response = await fetch(`${API_BASE}/api/ldm/rows/${rowId}/check-qa`, {
        method: 'POST',
        headers: {
          ...getAuthHeaders(),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          checks: ["line", "pattern", "term"],
          force: true
        })
      });

      if (response.ok) {
        const result = await response.json();
        lastQaResult = result;

        // Update row's qa_flag_count in cache
        // SMART INDEXING: O(1) lookup instead of O(n) findIndex
        const rowIndex = getRowIndexById(rowId);
        if (rowIndex !== undefined && rows[rowIndex]) {
          rows[rowIndex] = {
            ...rows[rowIndex],
            qa_flag_count: result.issue_count,
            qa_checked_at: result.checked_at
          };
          rows = [...rows];
        }

        if (result.issue_count > 0) {
          logger.warning("QA issues found", { rowId, count: result.issue_count });
        } else {
          logger.success("QA check passed", { rowId });
        }

        return result;
      }
    } catch (err) {
      logger.error("QA check failed", { rowId, error: err.message });
    } finally {
      qaLoading = false;
    }

    return null;
  }

  // P2: Get QA results for a row (for edit modal)
  async function fetchQAResults(rowId) {
    if (!rowId) return [];

    try {
      const response = await fetch(`${API_BASE}/api/ldm/rows/${rowId}/qa-results`, {
        headers: getAuthHeaders()
      });

      if (response.ok) {
        const data = await response.json();
        return data.issues || [];
      }
    } catch (err) {
      logger.error("Failed to fetch QA results", { rowId, error: err.message });
    }

    return [];
  }

  // =========================================================================
  // Reference Column Functions (Phase 8)
  // =========================================================================

  /**
   * Load reference file data for matching
   */
  async function loadReferenceData(refFileId) {
    if (!refFileId) {
      referenceData = new Map();
      return;
    }

    referenceLoading = true;
    logger.info("Loading reference file", { fileId: refFileId });

    try {
      // Fetch reference file rows (limit to 10K for performance)
      // Reference matching is by string_id, so we need enough rows to match
      const response = await fetch(`${API_BASE}/api/ldm/files/${refFileId}/rows?limit=10000`, {
        headers: getAuthHeaders()
      });

      if (response.ok) {
        const data = await response.json();
        const refRows = data.rows || [];

        // Build lookup map by string_id
        referenceData = new Map();
        for (const row of refRows) {
          if (row.string_id) {
            referenceData.set(row.string_id, {
              target: row.target,
              source: row.source
            });
          }
        }

        logger.success("Reference data loaded", { entries: referenceData.size });
      } else {
        logger.error("Failed to load reference file", { status: response.status });
      }
    } catch (err) {
      logger.error("Error loading reference", { error: err.message });
    } finally {
      referenceLoading = false;
    }
  }

  /**
   * Get reference translation for a row
   */
  function getReferenceForRow(row, matchMode) {
    if (!row.string_id || referenceData.size === 0) return null;

    const ref = referenceData.get(row.string_id);
    if (!ref) return null;

    // If matching by string_id + source, verify source matches too
    if (matchMode === 'stringIdAndSource') {
      if (ref.source !== row.source) return null;
    }

    return ref.target;
  }

  // Svelte 5: Effect - load reference when preference changes
  $effect(() => {
    if ($preferences.referenceFileId) {
      loadReferenceData($preferences.referenceFileId);
    } else {
      referenceData = new Map();
    }
  });

  // =========================================================================
  // TM Results Column Functions (Phase 9)
  // =========================================================================

  /**
   * Get best TM match for a row (cached)
   */
  function getTMResultForRow(row) {
    if (!row.id) return null;
    return tmResults.get(row.id) || null;
  }

  /**
   * Fetch TM result for a row and cache it - USES HIERARCHY TMs
   */
  async function fetchTMResultForRow(row) {
    // DEBUG: Enhanced logging for TM fetch
    if (!row.source) {
      logger.debug("[TM-FETCH] Skip: no source text", { rowId: row.id });
      return;
    }
    // Use hierarchy TMs, not preferences
    if (!activeTMs || activeTMs.length === 0) {
      logger.debug("[TM-FETCH] Skip: no active TM in hierarchy");
      return;
    }

    const rowId = row.id;
    if (tmResults.has(rowId)) {
      logger.debug("[TM-FETCH] Skip: cached", { rowId });
      return;
    }

    const tmId = activeTMs[0].tm_id;
    logger.info("[TM-FETCH] START", {
      rowId,
      tmId,
      source: row.source.substring(0, 30) + "..."
    });

    try {
      const params = new URLSearchParams({
        source: row.source,
        threshold: $preferences.tmThreshold.toString(),
        max_results: '1',
        tm_id: tmId.toString()  // Use hierarchy TM
      });

      const response = await fetch(`${API_BASE}/api/ldm/tm/suggest?${params}`, {
        headers: getAuthHeaders()
      });

      if (response.ok) {
        const data = await response.json();
        logger.info("[TM-FETCH] RESPONSE", {
          rowId,
          count: data.count,
          hasMatches: data.suggestions?.length > 0
        });
        if (data.suggestions && data.suggestions.length > 0) {
          const best = data.suggestions[0];
          logger.debug("[TM-FETCH] Best match", {
            similarity: best.similarity,
            source: best.source?.substring(0, 30)
          });
          tmResults.set(rowId, {
            target: best.target,
            similarity: best.similarity,
            source: best.source
          });
          tmResults = tmResults; // Trigger reactivity
        }
      } else {
        logger.warning("[TM-FETCH] HTTP error", {
          rowId,
          status: response.status
        });
      }
    } catch (err) {
      logger.error("[TM-FETCH] Exception", { rowId, error: err.message });
    }
  }

  // Svelte 5: Effect - Clear TM cache when activeTMs changes
  let prevActiveTMId = $state(null);
  $effect(() => {
    const currentTMId = activeTMs?.[0]?.tm_id || null;
    if (currentTMId !== prevActiveTMId) {
      prevActiveTMId = currentTMId;
      tmResults = new Map();
    }
  });

  // ============================================
  // Phase 2: Inline Editing (MemoQ-style)
  // ============================================

  /**
   * Start inline editing on a cell (double-click)
   */
  async function startInlineEdit(row) {
    if (!row) return;

    // P9: Skip locking for orphaned files (Offline Storage) - no multi-user sync
    if (!isLocalFile) {
      // Check if row is locked by another user
      const lock = isRowLocked(parseInt(row.id));
      if (lock && lock.locked_by) {
        logger.warning("Row locked by another user", { rowId: row.id, lockedBy: lock.locked_by });
        return;
      }

      // Request row lock for editing
      if (fileId) {
        const granted = await lockRow(fileId, parseInt(row.id));
        if (!granted) {
          logger.warning("Could not acquire lock for inline edit", { rowId: row.id });
          return;
        }
      }
    }

    // Set inline editing state
    inlineEditingRowId = row.id;
    // Convert file-format linebreaks to actual \n for editing, then to HTML for WYSIWYG
    const rawText = formatTextForDisplay(row.target || "");
    const htmlContent = paColorToHtml(rawText);
    selectedRowId = row.id;

    // Push initial state to undo stack
    pushUndoState(row.id, row.target || "");

    logger.userAction("Inline edit started", { rowId: row.id });

    // Focus the contenteditable after render and set initial content
    await tick();
    if (inlineEditTextarea) {
      // Set content directly (not via reactive binding to avoid cursor reset)
      inlineEditTextarea.innerHTML = htmlContent;
      inlineEditTextarea.focus();
      // Move cursor to end using selection API
      const range = document.createRange();
      const sel = window.getSelection();
      range.selectNodeContents(inlineEditTextarea);
      range.collapse(false);
      sel.removeAllRanges();
      sel.addRange(range);
    }
  }

  /**
   * Save inline edit and move to next row (or just save)
   */
  async function saveInlineEdit(moveToNext = false) {
    // Don't save if we're intentionally cancelling (Escape key)
    if (!inlineEditingRowId || isCancellingEdit) return;

    const row = getRowById(inlineEditingRowId);
    if (!row) {
      cancelInlineEdit();
      return;
    }

    // Convert from HTML (contenteditable) back to PAColor format, then to file format
    // Read directly from textarea to avoid cursor reset issue
    const currentHtml = inlineEditTextarea?.innerHTML || "";
    const rawText = htmlToPaColor(currentHtml);
    const textToSave = formatTextForSave(rawText);

    // Only save if value changed (compare formatted values)
    if (textToSave !== row.target) {
      try {
        // P9: Unified endpoint - backend handles both PostgreSQL and SQLite
        const response = await fetch(`${API_BASE}/api/ldm/rows/${row.id}`, {
          method: 'PUT',
          headers: {
            ...getAuthHeaders(),
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            target: textToSave,
            status: 'translated' // Mark as translated when edited
          })
        });

        if (response.ok) {
          // Update local row data with file-format text
          row.target = textToSave;
          row.status = 'translated';

          // Invalidate height cache for this row (content changed, height may differ)
          const rowIndex = getRowIndexById(row.id);
          if (rowIndex !== undefined) {
            rowHeightCache.delete(rowIndex);
            rebuildCumulativeHeights(); // Recalculate all positions
          }

          logger.success("Inline edit saved", { rowId: row.id, offline: isLocalFile });
          dispatch('rowUpdate', { rowId: row.id });
        } else {
          logger.error("Failed to save inline edit", { status: response.status });
        }
      } catch (err) {
        logger.error("Error saving inline edit", { error: err.message });
      }
    }

    // Release lock (fire-and-forget) - skip for orphaned files (no locking)
    if (fileId && !isLocalFile) {
      unlockRow(fileId, parseInt(row.id));
    }

    // Clear inline editing state
    const currentRowId = inlineEditingRowId;
    inlineEditingRowId = null;
    inlineEditValue = "";

    // Move to next row if requested
    if (moveToNext) {
      const currentIndex = getRowIndexById(currentRowId);
      if (currentIndex !== undefined && rows[currentIndex + 1]) {
        const nextRow = rows[currentIndex + 1];
        if (nextRow && !nextRow.placeholder) {
          selectedRowId = nextRow.id;
          dispatch('rowSelect', { row: nextRow });
          // Auto-start editing on next row
          await startInlineEdit(nextRow);
        }
      }
    }
  }

  /**
   * Cancel inline edit without saving
   */
  function cancelInlineEdit() {
    if (!inlineEditingRowId) return;

    const rowId = inlineEditingRowId;

    // Set flag to prevent blur handler from saving
    isCancellingEdit = true;

    // Release lock (fire-and-forget, no return value)
    if (fileId) {
      unlockRow(fileId, parseInt(rowId));
    }

    inlineEditingRowId = null;
    inlineEditValue = "";
    logger.userAction("Inline edit cancelled", { rowId });

    // Reset cancel flag after DOM update
    setTimeout(() => { isCancellingEdit = false; }, 0);
  }

  /**
   * Handle right-click in contenteditable to show color picker
   */
  let savedRange = null; // Store selection range for color picker

  /**
   * UI-113: Handle right-click in edit mode - show edit-specific context menu
   */
  function handleEditContextMenu(e) {
    if (!inlineEditTextarea) return;

    e.preventDefault();

    // Get text selection from contenteditable
    const sel = window.getSelection();
    const range = sel && sel.rangeCount > 0 ? sel.getRangeAt(0) : null;
    const selectedText = sel ? sel.toString() : "";

    // Save the range for color application
    if (range && selectedText.length > 0) {
      savedRange = range.cloneRange();
      textSelection = {
        start: 0,
        end: selectedText.length,
        text: selectedText
      };
    } else {
      savedRange = null;
      textSelection = { start: 0, end: 0, text: "" };
    }

    // Show edit context menu (not just color picker)
    colorPickerPosition = { x: e.clientX, y: e.clientY };
    showColorPicker = true;
    logger.userAction("Edit context menu opened", { hasSelection: selectedText.length > 0 });
  }

  /**
   * UI-113: Edit actions for context menu
   */
  function handleEditCut() {
    if (!inlineEditTextarea) return;
    document.execCommand('cut');
    closeColorPicker();
    inlineEditTextarea.focus();
  }

  function handleEditCopy() {
    if (!inlineEditTextarea) return;
    document.execCommand('copy');
    closeColorPicker();
    inlineEditTextarea.focus();
  }

  function handleEditPaste() {
    if (!inlineEditTextarea) return;
    document.execCommand('paste');
    closeColorPicker();
    inlineEditTextarea.focus();
  }

  function handleEditSelectAll() {
    if (!inlineEditTextarea) return;
    closeColorPicker();
    // Select all text in contenteditable
    const range = document.createRange();
    range.selectNodeContents(inlineEditTextarea);
    const sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(range);
    inlineEditTextarea.focus();
  }

  /**
   * Apply color to selected text in contenteditable
   */
  function applyColor(color) {
    if (!inlineEditTextarea || !savedRange || textSelection.text.length === 0) {
      closeColorPicker();
      return;
    }

    // Focus the contenteditable
    inlineEditTextarea.focus();

    // Restore the saved selection
    const sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(savedRange);

    // Create a colored span to wrap the selection
    const coloredSpan = document.createElement('span');
    coloredSpan.style.color = hexToCSS(color.hex);
    coloredSpan.setAttribute('data-pacolor', color.hex);

    // Extract contents and wrap in span
    coloredSpan.appendChild(savedRange.extractContents());
    savedRange.insertNode(coloredSpan);

    // Note: Don't update inlineEditValue here - we read directly from textarea on save

    logger.userAction("Applied color to text", { color: color.name, text: textSelection.text });
    closeColorPicker();

    // Move cursor after the colored span
    tick().then(() => {
      if (inlineEditTextarea) {
        inlineEditTextarea.focus();
        const range = document.createRange();
        range.setStartAfter(coloredSpan);
        range.collapse(true);
        const sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
      }
    });
  }

  /**
   * Close color picker
   */
  function closeColorPicker() {
    showColorPicker = false;
    textSelection = { start: 0, end: 0, text: "" };
  }

  /**
   * Handle keyboard events at grid level (selection mode - single click on row)
   * Works when a row is selected but NOT being edited
   */
  function handleGridKeydown(e) {
    // Skip if in edit mode (textarea handles its own keys)
    if (inlineEditingRowId) return;

    // Skip if no row selected
    if (!selectedRowId) return;

    // Skip if focus is in search/filter inputs
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

    const row = getRowById(selectedRowId);
    if (!row) return;

    // Ctrl+S: Confirm selected row
    if (e.ctrlKey && e.key === 's') {
      e.preventDefault();
      confirmSelectedRow(row);
      return;
    }

    // Ctrl+D: Dismiss QA for selected row
    if (e.ctrlKey && e.key === 'd') {
      e.preventDefault();
      dismissQAIssues();
      return;
    }

    // Enter: Start editing selected row
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      const lock = isRowLocked(parseInt(row.id));
      if (!lock) {
        startInlineEdit(row);
      }
      return;
    }

    // Escape: Clear selection
    if (e.key === 'Escape') {
      e.preventDefault();
      selectedRowId = null;
      return;
    }

    // Arrow Down: Move to next row
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      const currentIndex = getRowIndexById(selectedRowId);
      if (currentIndex !== undefined && rows[currentIndex + 1]) {
        selectedRowId = rows[currentIndex + 1].id;
        dispatch('rowSelect', { row: rows[currentIndex + 1] });
      }
      return;
    }

    // Arrow Up: Move to previous row
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      const currentIndex = getRowIndexById(selectedRowId);
      if (currentIndex !== undefined && currentIndex > 0 && rows[currentIndex - 1]) {
        selectedRowId = rows[currentIndex - 1].id;
        dispatch('rowSelect', { row: rows[currentIndex - 1] });
      }
      return;
    }
  }

  /**
   * Confirm selected row (mark as reviewed + add to TM) without editing
   */
  async function confirmSelectedRow(row) {
    if (!row) return;

    try {
      const response = await fetch(`${API_BASE}/api/ldm/rows/${row.id}`, {
        method: 'PUT',
        headers: {
          ...getAuthHeaders(),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          status: 'reviewed'
        })
      });

      if (response.ok) {
        row.status = 'reviewed';
        logger.success("Row confirmed (selection mode)", { rowId: row.id });

        // Dispatch event to add to linked TM
        dispatch('confirmTranslation', {
          rowId: row.id,
          source: row.source,
          target: row.target
        });

        dispatch('rowUpdate', { rowId: row.id });

        // Move to next row
        const currentIndex = getRowIndexById(row.id);
        if (currentIndex !== undefined && rows[currentIndex + 1]) {
          selectedRowId = rows[currentIndex + 1].id;
          dispatch('rowSelect', { row: rows[currentIndex + 1] });
        }
      }
    } catch (err) {
      logger.error("Error confirming row", { error: err.message });
    }
  }

  /**
   * Handle keyboard events during inline edit
   * Hotkeys:
   * - Escape: Cancel edit
   * - Enter: Save and move to next
   * - Tab: Save and move to next
   * - Shift+Enter: New line
   * - Ctrl+S: Confirm (save as reviewed + add to TM)
   * - Ctrl+D: Dismiss QA issue for current row
   * - Ctrl+Z: Undo last edit
   * - Ctrl+Y: Redo
   */
  function handleInlineEditKeydown(e) {
    // Ctrl+S: Confirm (save as reviewed status + add to TM)
    if (e.ctrlKey && e.key === 's') {
      e.preventDefault();
      confirmInlineEdit();
      return;
    }

    // Ctrl+D: Dismiss QA issues for current row
    if (e.ctrlKey && e.key === 'd') {
      e.preventDefault();
      dismissQAIssues();
      return;
    }

    // Ctrl+U: Revert to untranslated (reset status)
    if (e.ctrlKey && e.key === 'u') {
      e.preventDefault();
      revertRowStatus();
      return;
    }

    // Ctrl+Z: Undo
    if (e.ctrlKey && e.key === 'z' && !e.shiftKey) {
      e.preventDefault();
      undoEdit();
      return;
    }

    // Ctrl+Y or Ctrl+Shift+Z: Redo
    if ((e.ctrlKey && e.key === 'y') || (e.ctrlKey && e.shiftKey && e.key === 'z')) {
      e.preventDefault();
      redoEdit();
      return;
    }

    if (e.key === 'Escape') {
      e.preventDefault();
      e.stopPropagation();
      cancelInlineEdit();
      return;
    } else if (e.key === 'Enter' && !e.shiftKey) {
      // Enter without shift = save and move to next
      e.preventDefault();
      saveInlineEdit(true);
    } else if (e.key === 'Tab') {
      // Tab = save and move to next
      e.preventDefault();
      saveInlineEdit(true);
    }
    // Shift+Enter = newline (default behavior, don't prevent)
  }

  /**
   * Confirm translation: Save as "reviewed" status and add to linked TM
   */
  async function confirmInlineEdit() {
    if (!inlineEditingRowId) return;

    const row = getRowById(inlineEditingRowId);
    if (!row) {
      cancelInlineEdit();
      return;
    }

    // CRITICAL: Convert HTML spans back to PAColor tags FIRST, then format for file
    // Read directly from textarea to avoid cursor reset issue
    const currentHtml = inlineEditTextarea?.innerHTML || "";
    const rawText = htmlToPaColor(currentHtml);
    const textToSave = formatTextForSave(rawText);

    try {
      // Save with "reviewed" status
      const response = await fetch(`${API_BASE}/api/ldm/rows/${row.id}`, {
        method: 'PUT',
        headers: {
          ...getAuthHeaders(),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          target: textToSave,
          status: 'reviewed'  // Confirmed = reviewed status
        })
      });

      if (response.ok) {
        // Update local row data with file-format text
        row.target = textToSave;
        row.status = 'reviewed';

        // Invalidate height cache for this row (content changed, height may differ)
        const rowIndex = getRowIndexById(row.id);
        if (rowIndex !== undefined) {
          rowHeightCache.delete(rowIndex);
          rebuildCumulativeHeights(); // Recalculate all positions
        }

        logger.success("Translation confirmed", { rowId: row.id, status: 'reviewed' });

        // Dispatch event to add to linked TM (handled by LDM.svelte)
        dispatch('confirmTranslation', {
          rowId: row.id,
          source: row.source,
          target: textToSave
        });

        dispatch('rowUpdate', { rowId: row.id });
      } else {
        logger.error("Failed to confirm translation", { status: response.status });
      }
    } catch (err) {
      logger.error("Error confirming translation", { error: err.message });
    }

    // Release lock (fire-and-forget)
    if (fileId) {
      unlockRow(fileId, parseInt(row.id));
    }

    const currentRowId = inlineEditingRowId;
    inlineEditingRowId = null;
    inlineEditValue = "";

    // Move to next row
    const currentIndex = getRowIndexById(currentRowId);
    if (currentIndex !== undefined && rows[currentIndex + 1]) {
      const nextRow = rows[currentIndex + 1];
      if (nextRow && !nextRow.placeholder) {
        selectedRowId = nextRow.id;
        dispatch('rowSelect', { row: nextRow });
        await startInlineEdit(nextRow);
      }
    }
  }

  /**
   * Dismiss QA issues for current row
   */
  function dismissQAIssues() {
    // Works in both edit mode and selection mode
    const targetRowId = inlineEditingRowId || selectedRowId;
    if (!targetRowId) return;

    const row = getRowById(targetRowId);
    if (!row) return;

    dispatch('dismissQA', { rowId: row.id });
    logger.userAction("QA issues dismissed", { rowId: row.id });
  }

  /**
   * Revert row status to untranslated (Ctrl+U)
   * Works in both edit mode and selection mode
   */
  async function revertRowStatus() {
    const targetRowId = inlineEditingRowId || selectedRowId;
    if (!targetRowId) return;

    const row = getRowById(targetRowId);
    if (!row) return;

    // Already untranslated? Nothing to do
    if (row.status === 'untranslated') {
      logger.info("Row already untranslated", { rowId: row.id });
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/api/ldm/rows/${row.id}`, {
        method: 'PUT',
        headers: {
          ...getAuthHeaders(),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          status: 'untranslated'
        })
      });

      if (response.ok) {
        row.status = 'untranslated';
        logger.success("Row reverted to untranslated", { rowId: row.id });
        dispatch('rowUpdate', { rowId: row.id });
      } else {
        logger.error("Failed to revert row status", { rowId: row.id, status: response.status });
      }
    } catch (err) {
      logger.error("Error reverting row status", { error: err.message });
    }
  }

  // ============================================================
  // UX-002: CELL CONTEXT MENU
  // ============================================================

  /**
   * Handle right-click on cell row
   */
  function handleCellContextMenu(e, rowId) {
    e.preventDefault();
    e.stopPropagation();

    contextMenuRowId = rowId;
    contextMenuPosition = { x: e.clientX, y: e.clientY };
    showContextMenu = true;

    // Also select the row
    selectedRowId = rowId;
    const row = getRowById(rowId);
    if (row) {
      dispatch('rowSelect', { row });
    }
  }

  /**
   * Close context menu
   */
  function closeContextMenu() {
    showContextMenu = false;
    contextMenuRowId = null;
  }

  /**
   * Set row status via context menu
   */
  async function setRowStatus(status) {
    closeContextMenu();
    if (!contextMenuRowId) return;

    const row = getRowById(contextMenuRowId);
    if (!row || row.status === status) return;

    try {
      const response = await fetch(`${API_BASE}/api/ldm/rows/${row.id}`, {
        method: 'PUT',
        headers: {
          ...getAuthHeaders(),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ status })
      });

      if (response.ok) {
        row.status = status;
        logger.success(`Row status set to ${status}`, { rowId: row.id });
        dispatch('rowUpdate', { rowId: row.id });

        // If confirming, also dispatch for TM auto-add
        if (status === 'reviewed') {
          dispatch('confirmTranslation', {
            rowId: row.id,
            source: row.source,
            target: row.target
          });
        }
      }
    } catch (err) {
      logger.error("Error setting row status", { error: err.message });
    }
  }

  /**
   * Copy text to clipboard
   */
  async function copyToClipboard(text, label) {
    closeContextMenu();
    try {
      await navigator.clipboard.writeText(text);
      logger.success(`${label} copied to clipboard`);
    } catch (err) {
      logger.error("Failed to copy to clipboard", { error: err.message });
    }
  }

  /**
   * Run QA on row via context menu
   */
  function runQAOnRow() {
    closeContextMenu();
    if (!contextMenuRowId) return;

    const row = getRowById(contextMenuRowId);
    if (!row) return;

    // Dispatch QA request event
    dispatch('runQA', { rowId: row.id, source: row.source, target: row.target });
    logger.userAction("QA check requested from context menu", { rowId: row.id });
  }

  /**
   * Dismiss QA via context menu
   */
  function dismissQAFromContextMenu() {
    closeContextMenu();
    if (!contextMenuRowId) return;

    dispatch('dismissQA', { rowId: contextMenuRowId });
    logger.userAction("QA dismissed from context menu", { rowId: contextMenuRowId });
  }

  /**
   * Add row to TM via context menu
   */
  function addToTMFromContextMenu() {
    closeContextMenu();
    if (!contextMenuRowId) return;

    const row = getRowById(contextMenuRowId);
    if (!row) return;

    dispatch('addToTM', { rowId: row.id, source: row.source, target: row.target });
    logger.userAction("Add to TM requested from context menu", { rowId: row.id });
  }

  // Close context menu on click outside
  function handleGlobalClick(e) {
    if (showContextMenu) {
      closeContextMenu();
    }
  }

  // Undo/Redo state
  let undoStack = $state([]);
  let redoStack = $state([]);
  const MAX_UNDO_HISTORY = 50;

  /**
   * Push current state to undo stack (called before making changes)
   */
  function pushUndoState(rowId, oldValue) {
    undoStack = [...undoStack.slice(-MAX_UNDO_HISTORY + 1), { rowId, value: oldValue }];
    redoStack = []; // Clear redo when new edit is made
  }

  /**
   * Undo last edit
   */
  function undoEdit() {
    if (undoStack.length === 0) {
      logger.info("Nothing to undo");
      return;
    }

    const lastState = undoStack[undoStack.length - 1];
    undoStack = undoStack.slice(0, -1);

    // Save current value to redo stack
    if (inlineEditingRowId && inlineEditTextarea) {
      redoStack = [...redoStack, { rowId: inlineEditingRowId, value: inlineEditTextarea.innerHTML }];
    }

    // Restore the previous value by setting innerHTML directly
    if (inlineEditTextarea) {
      inlineEditTextarea.innerHTML = lastState.value;
    }
    logger.userAction("Undo", { rowId: lastState.rowId });
  }

  /**
   * Redo last undone edit
   */
  function redoEdit() {
    if (redoStack.length === 0) {
      logger.info("Nothing to redo");
      return;
    }

    const redoState = redoStack[redoStack.length - 1];
    redoStack = redoStack.slice(0, -1);

    // Save current value to undo stack
    if (inlineEditingRowId && inlineEditTextarea) {
      undoStack = [...undoStack, { rowId: inlineEditingRowId, value: inlineEditTextarea.innerHTML }];
    }

    // Restore the redo value by setting innerHTML directly
    if (inlineEditTextarea) {
      inlineEditTextarea.innerHTML = redoState.value;
    }
    logger.userAction("Redo", { rowId: redoState.rowId });
  }

  // ============================================
  // Phase 2: Modal Editing REMOVED
  // Replaced by inline editing (startInlineEdit, saveInlineEdit, cancelInlineEdit)
  // TM/QA display moved to TMQAPanel.svelte (side panel)
  // ============================================

  // Handle real-time cell updates from other users
  // SMART INDEXING: Uses O(1) lookup instead of O(n) findIndex
  function handleCellUpdates(updates) {
    let heightsChanged = false;
    updates.forEach(update => {
      // O(1) lookup using index map
      const rowIndex = getRowIndexById(update.row_id);
      if (rowIndex !== undefined && rows[rowIndex]) {
        rows[rowIndex] = {
          ...rows[rowIndex],
          target: update.target,
          status: update.status
        };
        // Invalidate height cache for this row (content may have changed)
        rowHeightCache.delete(rowIndex);
        heightsChanged = true;
      }
    });
    if (heightsChanged) {
      rebuildCumulativeHeights();
    }
    rows = [...rows];
    logger.info("Real-time updates applied", { count: updates.length });
  }

  // Get status tag type
  function getStatusKind(status) {
    switch (status) {
      case 'approved': return 'green';
      case 'reviewed': return 'blue';
      case 'translated': return 'teal';
      default: return 'gray';
    }
  }

  // Format text for grid display - show actual line breaks
  // Text is displayed with pre-wrap, so \n shows as real line breaks
  // XML &lt;br/&gt; is converted to visual line breaks for display
  function formatGridText(text) {
    if (!text) return "";
    // Convert XML-style line breaks to actual newlines for display
    let formatted = text.replace(/&lt;br\/&gt;/g, '\n');
    // Also handle escaped versions
    formatted = formatted.replace(/\\n/g, '\n');
    return formatted;
  }

  /**
   * Convert file-format linebreaks to actual newlines for display in textarea
   * Handles: \\n (escaped), &lt;br/&gt; (XML escaped), <br/> (XML), <br> (Excel)
   */
  function formatTextForDisplay(text) {
    if (!text) return "";
    let result = text;
    // 1. XML escaped: &lt;br/&gt; → \n
    result = result.replace(/&lt;br\s*\/&gt;/gi, '\n');
    // 2. XML unescaped: <br/> or <br /> → \n
    result = result.replace(/<br\s*\/?>/gi, '\n');
    // 3. Escaped newlines: \\n → \n (literal backslash-n in text files)
    result = result.replace(/\\n/g, '\n');
    return result;
  }

  /**
   * Convert actual newlines back to file-format for saving
   * XML files use &lt;br/&gt;, TXT files keep \n
   */
  function formatTextForSave(text) {
    if (!text) return "";
    // Determine file type from fileName
    const isXML = fileName.toLowerCase().endsWith('.xml');
    const isExcel = fileName.toLowerCase().endsWith('.xlsx') || fileName.toLowerCase().endsWith('.xls');

    if (isXML) {
      // XML: convert actual newlines to &lt;br/&gt; (escaped for XML content)
      return text.replace(/\n/g, '&lt;br/&gt;');
    } else if (isExcel) {
      // Excel: convert actual newlines to <br> (unescaped)
      return text.replace(/\n/g, '<br>');
    } else {
      // TXT and others: keep actual newlines
      return text;
    }
  }

  // Calculate display lines for text (accounts for newlines AND wrapping per segment)
  // Each segment (split by newlines) is measured for wrapping, then summed
  function countDisplayLines(text, charsPerLine = 55) {
    if (!text) return 1;

    // First, convert all newline types to actual newlines for consistent splitting
    let normalized = text
      .replace(/&lt;br\s*\/&gt;/gi, '\n')  // XML escaped
      .replace(/<br\s*\/?>/gi, '\n')       // HTML
      .replace(/\\n/g, '\n');              // Escaped \n

    // Split by newlines to get segments
    const segments = normalized.split('\n');

    // Calculate wrap lines for EACH segment, then sum
    let totalLines = 0;
    for (const segment of segments) {
      // Each segment takes at least 1 line, plus extra for wrapping
      const segmentLines = Math.max(1, Math.ceil(segment.length / charsPerLine));
      totalLines += segmentLines;
    }

    return totalLines;
  }

  // VARIABLE HEIGHT: Estimate row height based on content
  // This is used for both display AND positioning (proper virtualization)
  function estimateRowHeight(row, index) {
    if (!row || row.placeholder) return MIN_ROW_HEIGHT;

    // Check cache first - if we have a measured height, use it
    if (rowHeightCache.has(index)) {
      return rowHeightCache.get(index);
    }

    // FIX: Strip color tags before calculating length (tags are not rendered)
    // This gives accurate length of what's actually displayed
    const sourceText = stripColorTags(row.source || "");
    const targetText = stripColorTags(row.target || "");

    // FIXED: Calculate display lines properly - accounts for both newlines AND wrapping
    // Old bug: was adding wrapLines + newlines which double-counted
    const effectiveCharsPerLine = 55; // ~45% viewport width, ~8px per char
    const sourceLines = countDisplayLines(sourceText, effectiveCharsPerLine);
    const targetLines = countDisplayLines(targetText, effectiveCharsPerLine);
    const totalLines = Math.max(sourceLines, targetLines);

    // Calculate height: use tighter line height (actual CSS is ~20px)
    const actualLineHeight = 22; // Closer to real rendered line height
    const contentHeight = totalLines * actualLineHeight;
    const estimatedHeight = Math.max(MIN_ROW_HEIGHT, contentHeight + CELL_PADDING);
    const finalHeight = Math.min(estimatedHeight, MAX_ROW_HEIGHT);

    // Cache the result (will be updated with actual measurement later)
    rowHeightCache.set(index, finalHeight);

    return finalHeight;
  }

  // SMART MEMBRANE: Measure actual row height after render and update cache
  function measureRowHeight(node, { index }) {
    // Wait for next frame to ensure content is rendered
    requestAnimationFrame(() => {
      const actualHeight = node.scrollHeight;
      const cachedHeight = rowHeightCache.get(index);

      // Only update if significantly different (>10px difference)
      if (cachedHeight && Math.abs(actualHeight - cachedHeight) > 10) {
        rowHeightCache.set(index, actualHeight);
        // Trigger re-calculation of cumulative heights
        rebuildCumulativeHeights();
      } else if (!cachedHeight) {
        rowHeightCache.set(index, actualHeight);
      }
    });

    return {
      destroy() {
        // Cleanup if needed
      }
    };
  }

  // VARIABLE HEIGHT: Rebuild cumulative heights for all loaded rows
  // Called when rows change or on initial load
  function rebuildCumulativeHeights() {
    const newCumulative = [0]; // First row starts at position 0

    for (let i = 0; i < total; i++) {
      const row = rows[i];
      const height = row ? estimateRowHeight(row, i) : MIN_ROW_HEIGHT;
      newCumulative[i + 1] = newCumulative[i] + height;
    }

    cumulativeHeights = newCumulative;
  }

  // VARIABLE HEIGHT: Get row position using cumulative heights
  function getRowTop(index) {
    // If we have cumulative heights calculated, use them
    if (cumulativeHeights.length > index) {
      return cumulativeHeights[index];
    }
    // Fallback: estimate based on MIN_ROW_HEIGHT (for rows not yet calculated)
    return index * MIN_ROW_HEIGHT;
  }

  // VARIABLE HEIGHT: Get height of a specific row
  function getRowHeight(index) {
    const row = rows[index];
    return row ? estimateRowHeight(row, index) : MIN_ROW_HEIGHT;
  }

  // VARIABLE HEIGHT: Total height is last cumulative value
  function getTotalHeight() {
    if (cumulativeHeights.length > total) {
      return cumulativeHeights[total];
    }
    // Fallback: estimate
    return total * MIN_ROW_HEIGHT;
  }

  // VARIABLE HEIGHT: Binary search to find row at scroll position
  function findRowAtPosition(scrollPos) {
    if (cumulativeHeights.length === 0) {
      return Math.floor(scrollPos / MIN_ROW_HEIGHT);
    }

    let low = 0;
    let high = total - 1;

    while (low < high) {
      const mid = Math.floor((low + high) / 2);
      if (cumulativeHeights[mid + 1] <= scrollPos) {
        low = mid + 1;
      } else {
        high = mid;
      }
    }

    return Math.max(0, low);
  }

  // UI-029: downloadFile removed - users download via right-click on FileExplorer

  // Pre-fetch TM on cell click
  let prefetchedRowId = null;

  function handleCellClick(row, event) {
    if (!row || row.placeholder) return;

    // Select the row
    selectedRowId = row.id;

    // Phase 1: Dispatch rowSelect event for side panel
    dispatch('rowSelect', { row });

    // Pre-fetch TM suggestions if not already fetched
    if (prefetchedRowId !== row.id && row.source) {
      prefetchedRowId = row.id;
      fetchTMSuggestions(row.source, row.id);
      logger.info("Pre-fetching TM for row", { rowId: row.id });
    }
  }

  // HOVER SYSTEM: Track mouse enter/leave on cells
  function handleCellMouseEnter(row, cellType) {
    if (!row || row.placeholder) return;
    hoveredRowId = row.id;
    hoveredCell = cellType; // 'source' or 'target'
  }

  function handleCellMouseLeave() {
    hoveredRowId = null;
    hoveredCell = null;
  }

  function handleRowMouseLeave() {
    hoveredRowId = null;
    hoveredCell = null;
  }

  // ============================================================
  // UI-083: UNIFIED RESIZE HANDLERS (factorized)
  // Single entry point for all column resizing
  // ============================================================

  function startResize(event, column = 'source') {
    event.preventDefault();
    event.stopPropagation();

    // Get starting value based on column type
    if (column === 'source') {
      resizeStartValue = sourceWidthPercent;
    } else if (column === 'index') {
      resizeStartValue = indexColumnWidth;
    } else if (column === 'stringId') {
      resizeStartValue = stringIdColumnWidth;
    } else if (column === 'reference') {
      resizeStartValue = referenceColumnWidth;
    }

    isResizing = true;
    resizeColumn = column;
    resizeStartX = event.clientX;

    document.addEventListener('mousemove', handleResize);
    document.addEventListener('mouseup', stopResize);
  }

  function handleResize(event) {
    if (!isResizing || !containerEl) return;

    const deltaX = event.clientX - resizeStartX;
    const limits = COLUMN_LIMITS[resizeColumn];
    if (!limits) return;

    if (resizeColumn === 'source') {
      // Source/Target split (percentage-based)
      const cw = containerEl.clientWidth;
      const fixedTotal = getFixedWidthBefore() + getFixedWidthAfter();
      const flexWidth = cw - fixedTotal;
      if (flexWidth <= 0) return;
      const deltaPercent = (deltaX / flexWidth) * 100;
      const newPercent = resizeStartValue + deltaPercent;
      sourceWidthPercent = Math.max(limits.min, Math.min(limits.max, newPercent));
    } else if (resizeColumn === 'reference') {
      // Reference resizes from LEFT edge (dragging left = bigger)
      const newWidth = resizeStartValue - deltaX;
      referenceColumnWidth = Math.max(limits.min, Math.min(limits.max, newWidth));
    } else if (resizeColumn === 'index') {
      const newWidth = resizeStartValue + deltaX;
      indexColumnWidth = Math.max(limits.min, Math.min(limits.max, newWidth));
    } else if (resizeColumn === 'stringId') {
      const newWidth = resizeStartValue + deltaX;
      stringIdColumnWidth = Math.max(limits.min, Math.min(limits.max, newWidth));
    }
  }

  function stopResize() {
    isResizing = false;
    resizeColumn = null;
    document.removeEventListener('mousemove', handleResize);
    document.removeEventListener('mouseup', stopResize);
  }

  // Svelte 5: Derived - Get visible rows for rendering
  let visibleRows = $derived(Array.from({ length: visibleEnd - visibleStart }, (_, i) => {
    const index = visibleStart + i;
    return rows[index] || { row_num: index + 1, placeholder: true };
  }));

  // Svelte 5: Derived - Total scroll height (reactive to rows changes)
  let totalHeight = $derived(getTotalHeight());

  // Svelte 5: Effect - Watch file changes AND subscribe to real-time updates
  // CRITICAL: Must track previousFileId to prevent infinite loop (BUG-001)
  let previousFileId = $state(null);
  $effect(() => {
    if (fileId && fileId !== previousFileId) {
      logger.info("fileId changed - resetting and subscribing", { from: previousFileId, to: fileId });
      previousFileId = fileId;

      // Reset search
      searchTerm = "";

      // Subscribe to WebSocket updates (was causing infinite loop without previousFileId check!)
      joinFile(fileId);
      if (cellUpdateUnsubscribe) {
        cellUpdateUnsubscribe();
      }
      cellUpdateUnsubscribe = onCellUpdate(handleCellUpdates);

      // Load rows
      loadRows();
    }
  });

  // Svelte 5: Effect - Watch searchTerm changes
  // Simple effect - triggers on any searchTerm change
  $effect(() => {
    // Access searchTerm to establish dependency
    const term = searchTerm;
    logger.info("searchTerm effect triggered", { searchTerm: term, hasFileId: !!fileId });

    // Only search if we have a file loaded
    if (fileId && term !== undefined) {
      handleSearch();
    }
  });

  // ResizeObserver to handle container size changes
  let resizeObserver = null;

  // Svelte 5: Effect - Setup scroll listener when container element is available
  // This is more reliable than onMount for bind:this elements
  $effect(() => {
    if (containerEl) {
      // Add scroll listener
      containerEl.addEventListener('scroll', handleScroll);
      calculateVisibleRange();

      // Add resize observer to recalculate when container size changes
      if (!resizeObserver) {
        resizeObserver = new ResizeObserver(() => {
          calculateVisibleRange();
          updateContainerWidth(); // UI-083: Update for resize bar positions
        });
      }
      resizeObserver.observe(containerEl);
      updateContainerWidth(); // Initial width calculation

      // Cleanup function returned from $effect
      return () => {
        containerEl.removeEventListener('scroll', handleScroll);
        if (resizeObserver) {
          resizeObserver.disconnect();
        }
      };
    }
  });

  // Keep onMount for backward compatibility but also handle via effect
  onMount(() => {
    // Initial calculation in case effect hasn't run yet
    if (containerEl) {
      calculateVisibleRange();
    }
  });

  // Cleanup on destroy (scroll/resize cleanup handled in $effect above)
  onDestroy(() => {
    if (fileId) {
      leaveFile(fileId);
    }
    if (cellUpdateUnsubscribe) {
      cellUpdateUnsubscribe();
    }
    if (searchDebounceTimer) {
      clearTimeout(searchDebounceTimer);
    }
  });
</script>

<div
  class="virtual-grid"
  style="--grid-font-size: {gridFontSize}; --grid-font-weight: {gridFontWeight}; --grid-font-family: {gridFontFamily}; --grid-font-color: {gridFontColor};"
  onkeydown={handleGridKeydown}
  tabindex="-1"
>
  {#if fileId}
    <div class="grid-header">
      <div class="header-left">
        <h4>{fileName || `File #${fileId}`}</h4>
        <span class="row-count">{total.toLocaleString()} rows</span>
      </div>
      <!-- UI-029: Removed download menu - users download via right-click on file list -->
      <div class="header-right">
        <PresenceBar />
      </div>
    </div>

    <div class="search-filter-bar">
      <!-- P5: Combined Search Control -->
      <div class="search-control">
        <!-- Mode indicator button -->
        <button
          class="search-mode-btn"
          onclick={() => showSearchSettings = !showSearchSettings}
          title="Search settings"
        >
          <span class="mode-icon">{searchModeOptions.find(m => m.id === searchMode)?.icon || "⊃"}</span>
          <ChevronDown size={12} />
        </button>

        <!-- Search input -->
        <div class="search-input-wrapper">
          <input
            type="text"
            id="ldm-search-input"
            class="search-input"
            placeholder="Search {searchFields.join(', ')}..."
            oninput={(e) => {
              searchTerm = e.target.value;
              logger.info("Search oninput", { value: searchTerm });
            }}
          />
          {#if searchTerm}
            <button
              type="button"
              class="search-clear"
              onclick={() => {
                searchTerm = "";
                const inputEl = document.getElementById('ldm-search-input');
                if (inputEl) inputEl.value = "";
              }}
              aria-label="Clear search"
            >
              <svg width="14" height="14" viewBox="0 0 16 16">
                <path d="M12 4.7L11.3 4 8 7.3 4.7 4 4 4.7 7.3 8 4 11.3 4.7 12 8 8.7 11.3 12 12 11.3 8.7 8z"/>
              </svg>
            </button>
          {/if}
        </div>

        <!-- Settings popover -->
        {#if showSearchSettings}
          <div class="search-settings-popover">
            <div class="settings-section">
              <div class="settings-label">Mode</div>
              <div class="mode-buttons">
                {#each searchModeOptions as mode}
                  <button
                    class="mode-option {searchMode === mode.id ? 'active' : ''}"
                    onclick={() => { searchMode = mode.id; if (searchTerm) handleSearch(); }}
                    title={mode.text}
                  >
                    <span class="mode-option-icon">{mode.icon}</span>
                    <span class="mode-option-text">{mode.text}</span>
                  </button>
                {/each}
              </div>
            </div>
            <div class="settings-section">
              <div class="settings-label">Fields</div>
              <div class="field-toggles">
                {#each searchFieldOptions as field}
                  <label class="field-toggle {searchFields.includes(field.id) ? 'active' : ''}">
                    <input
                      type="checkbox"
                      checked={searchFields.includes(field.id)}
                      onchange={(e) => {
                        if (e.target.checked) {
                          searchFields = [...searchFields, field.id];
                        } else {
                          searchFields = searchFields.filter(f => f !== field.id);
                        }
                        if (searchTerm) handleSearch();
                      }}
                    />
                    <span>{field.text}</span>
                  </label>
                {/each}
              </div>
            </div>
          </div>
          <!-- Backdrop to close popover -->
          <div class="settings-backdrop" onclick={() => showSearchSettings = false}></div>
        {/if}
      </div>

      <!-- P2: Filter Dropdown -->
      <div class="filter-wrapper">
        <Dropdown
          size="sm"
          selectedId={activeFilter}
          items={filterOptions}
          on:select={handleFilterChange}
          titleText=""
          hideLabel
        />
      </div>
    </div>

    <!-- Hotkey Reference Bar -->
    <div class="hotkey-bar">
      <span class="hotkey"><kbd>Enter</kbd> Save & Next</span>
      <span class="hotkey"><kbd>Ctrl+S</kbd> Confirm</span>
      <span class="hotkey"><kbd>Esc</kbd> Cancel</span>
      <span class="hotkey"><kbd>Ctrl+D</kbd> Dismiss QA</span>
      <span class="hotkey"><kbd>Ctrl+Z</kbd> Undo</span>
      <span class="hotkey"><kbd>Ctrl+Y</kbd> Redo</span>
    </div>

    <!-- Virtual Scroll Container with Resize Overlay -->
    <!-- UI-081: Clean grid - no header, just data rows -->
    <div class="scroll-wrapper">
      <!-- UI-083: Full-height resize bars - OUTSIDE scroll container so they don't scroll -->
      {#each visibleResizeBars as column (column)}
        <div
          class="column-resize-bar"
          class:resize-active={isResizing && resizeColumn === column}
          style="left: {resizeBarPositions[column] || 0}px;"
          onmousedown={(e) => startResize(e, column)}
          role="separator"
          aria-label="Resize {column} column"
        ></div>
      {/each}
      <div class="scroll-container" bind:this={containerEl}>
      {#if initialLoading}
        <div class="loading-overlay">
          <InlineLoading description="Loading rows..." />
        </div>
      {:else}
        <!-- Total height spacer -->
        <div class="scroll-content" style="height: {totalHeight}px;">
          <!-- Rendered rows -->
          {#each visibleRows as row, i (row.row_num)}
            {@const rowIndex = visibleStart + i}
            {@const rowLock = $ldmConnected && row.id ? isRowLocked(parseInt(row.id)) : null}
            <!-- svelte-ignore a11y_click_events_have_key_events -->
            <div
              class="virtual-row"
              class:placeholder={row.placeholder}
              class:locked={rowLock}
              class:selected={selectedRowId === row.id}
              class:row-hovered={hoveredRowId === row.id}
              style="top: {getRowTop(rowIndex)}px; min-height: {getRowHeight(rowIndex)}px;"
              use:measureRowHeight={{ index: rowIndex }}
              onclick={(e) => handleCellClick(row, e)}
              oncontextmenu={(e) => !row.placeholder && handleCellContextMenu(e, row.id)}
              onmouseleave={handleRowMouseLeave}
              role="row"
            >
              {#if row.placeholder}
                <!-- UI-066: Placeholder rows match actual column structure -->
                <!-- UI-082: Using state-based widths for all columns -->
                {#if $preferences.showIndex}
                  <div class="cell row-num" style="width: {indexColumnWidth}px;">{row.row_num}</div>
                {/if}
                {#if $preferences.showStringId}
                  <div class="cell string-id loading-cell" style="width: {stringIdColumnWidth}px;">
                    <div class="placeholder-shimmer"></div>
                  </div>
                {/if}
                <!-- UI-090: Use flex-grow ratios to share remaining space after fixed columns -->
                <div class="cell source loading-cell" style="flex: {sourceWidthPercent} 1 0;">
                  <div class="placeholder-shimmer"></div>
                </div>
                <div class="cell target loading-cell" style="flex: {100 - sourceWidthPercent} 1 0;">
                  <div class="placeholder-shimmer"></div>
                </div>
                {#if $preferences.showReference}
                  <div class="cell reference loading-cell" style="width: {referenceColumnWidth}px;">
                    <div class="placeholder-shimmer"></div>
                  </div>
                {/if}
              {:else}
                <!-- UI-083: Row number (conditional) - resize via full-height bar -->
                {#if $preferences.showIndex}
                  <div class="cell row-num" style="width: {indexColumnWidth}px;">
                    {row.row_num}
                  </div>
                {/if}

                <!-- UI-083: StringID (conditional) - resize via full-height bar -->
                {#if $preferences.showStringId}
                  <div class="cell string-id" style="width: {stringIdColumnWidth}px;">
                    {row.string_id || "-"}
                  </div>
                {/if}

                <!-- Source (always visible, READ-ONLY) -->
                <!-- UI-090: Uses flex-grow ratio to share remaining space after fixed columns -->
                <div
                  class="cell source"
                  class:source-hovered={hoveredRowId === row.id && hoveredCell === 'source'}
                  class:row-active={hoveredRowId === row.id || selectedRowId === row.id}
                  class:cell-selected={selectedRowId === row.id}
                  style="flex: {sourceWidthPercent} 1 0;"
                  onmouseenter={() => handleCellMouseEnter(row, 'source')}
                >
                  <span class="cell-content"><ColorText text={formatGridText(row.source) || ""} /></span>
                </div>

                <!-- Target (always visible, EDITABLE) -->
                <!-- Phase 2: Inline editing on double-click -->
                <!-- Cell color indicates status: default=pending, translated=teal, confirmed=green -->
                <div
                  class="cell target"
                  class:locked={rowLock}
                  class:target-hovered={hoveredRowId === row.id && hoveredCell === 'target'}
                  class:row-active={hoveredRowId === row.id || selectedRowId === row.id}
                  class:cell-selected={selectedRowId === row.id}
                  class:inline-editing={inlineEditingRowId === row.id}
                  class:status-translated={row.status === 'translated'}
                  class:status-reviewed={row.status === 'reviewed'}
                  class:status-approved={row.status === 'approved'}
                  class:qa-flagged={row.qa_flag_count > 0}
                  style="flex: {100 - sourceWidthPercent} 1 0;"
                  onmouseenter={() => handleCellMouseEnter(row, 'target')}
                  ondblclick={() => !rowLock && startInlineEdit(row)}
                  role="button"
                  tabindex="0"
                  onkeydown={(e) => e.key === 'Enter' && !e.shiftKey && !rowLock && !inlineEditingRowId && startInlineEdit(row)}
                >
                  {#if inlineEditingRowId === row.id}
                    <!-- WYSIWYG inline editing - colors render directly -->
                    <div class="inline-edit-container">
                      <div
                        bind:this={inlineEditTextarea}
                        contenteditable="true"
                        class="inline-edit-textarea"
                        onkeydown={handleInlineEditKeydown}
                        onblur={() => saveInlineEdit(false)}
                        oncontextmenu={handleEditContextMenu}
                        data-placeholder="Enter translation..."
                      ></div>
                    </div>
                  {:else}
                    <!-- Display mode -->
                    <span class="cell-content"><ColorText text={formatGridText(row.target) || ""} /></span>
                    {#if row.qa_flag_count > 0}
                      <span class="qa-icon" title="{row.qa_flag_count} QA issue(s)">
                        <WarningAltFilled size={14} />
                      </span>
                    {/if}
                    {#if rowLock}
                      <span class="lock-icon"><Locked size={12} /></span>
                    {:else}
                      <span class="edit-icon"><Edit size={12} /></span>
                    {/if}
                  {/if}
                </div>

                <!-- UI-083: Reference Column (conditional) - resize via full-height bar -->
                {#if $preferences.showReference}
                  {@const refText = getReferenceForRow(row, $preferences.referenceMatchMode)}
                  <div
                    class="cell reference"
                    class:has-match={refText}
                    class:no-match={!refText}
                    style="width: {referenceColumnWidth}px;"
                    title={refText ? `Reference: ${refText}` : 'No reference match'}
                  >
                    {#if referenceLoading}
                      <span class="cell-loading">Loading...</span>
                    {:else if refText}
                      <span class="cell-content ref-match">{formatGridText(refText)}</span>
                    {:else}
                      <!-- UI-071: Clearer "No match" styling -->
                      <span class="cell-content no-match">No match</span>
                    {/if}
                  </div>
                {/if}

                <!-- UI-039: Removed TM Result Column - only StringID (left) and Reference (right) are third column options -->
              {/if}
            </div>
          {/each}
        </div>
      {/if}
      </div>
    </div>

    {#if loading && !initialLoading}
      <div class="loading-bar">
        <InlineLoading description="Loading more..." />
      </div>
    {/if}

    <!-- UI-041: Removed grid-footer (useless "Showing rows X-Y of Z") -->
  {:else}
    <div class="empty-state">
      <p>Select a file from the explorer to view its contents</p>
    </div>
  {/if}

  <!-- UI-113: Edit Mode Context Menu (Color Picker + Edit Actions) -->
  {#if showColorPicker}
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="color-picker-overlay" onclick={closeColorPicker}></div>
    <div
      class="edit-context-menu"
      style="left: {colorPickerPosition.x}px; top: {colorPickerPosition.y}px;"
    >
      <!-- Color Section (only if source has colors AND text is selected) -->
      {#if sourceColors.length > 0 && textSelection.text.length > 0}
        <div class="edit-menu-section">
          <div class="edit-menu-header">Apply Color</div>
          <div class="color-picker-colors">
            {#each sourceColors as color}
              <button
                class="color-swatch"
                style="background-color: {color.css};"
                title={color.name}
                onclick={() => applyColor(color)}
              >
                <span class="color-name">{color.name}</span>
              </button>
            {/each}
          </div>
          {#if textSelection.text}
            <div class="color-picker-preview">
              <span class="preview-label">Selected:</span>
              <span class="preview-text">"{textSelection.text.length > 30 ? textSelection.text.substring(0, 30) + '...' : textSelection.text}"</span>
            </div>
          {/if}
        </div>
        <div class="edit-menu-divider"></div>
      {:else if textSelection.text.length > 0 && sourceColors.length === 0}
        <div class="edit-menu-section">
          <div class="edit-menu-hint">No colors in source text</div>
        </div>
        <div class="edit-menu-divider"></div>
      {/if}

      <!-- Edit Actions -->
      <div class="edit-menu-section">
        <button class="edit-menu-item" onclick={handleEditCut} disabled={!textSelection.text}>
          <span class="edit-menu-icon">✂</span>
          <span>Cut</span>
          <span class="edit-menu-shortcut">Ctrl+X</span>
        </button>
        <button class="edit-menu-item" onclick={handleEditCopy} disabled={!textSelection.text}>
          <span class="edit-menu-icon">📋</span>
          <span>Copy</span>
          <span class="edit-menu-shortcut">Ctrl+C</span>
        </button>
        <button class="edit-menu-item" onclick={handleEditPaste}>
          <span class="edit-menu-icon">📝</span>
          <span>Paste</span>
          <span class="edit-menu-shortcut">Ctrl+V</span>
        </button>
        <div class="edit-menu-divider"></div>
        <button class="edit-menu-item" onclick={handleEditSelectAll}>
          <span class="edit-menu-icon">☑</span>
          <span>Select All</span>
          <span class="edit-menu-shortcut">Ctrl+A</span>
        </button>
      </div>
    </div>
  {/if}

  <!-- UX-002: Cell Context Menu -->
  {#if showContextMenu}
    {@const contextRow = getRowById(contextMenuRowId)}
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div
      class="context-menu"
      style="left: {contextMenuPosition.x}px; top: {contextMenuPosition.y}px;"
      onclick={(e) => e.stopPropagation()}
    >
      <div class="context-menu-section">
        <button
          class="context-item"
          onclick={() => setRowStatus('reviewed')}
          disabled={contextRow?.status === 'reviewed'}
        >
          <span class="context-icon">✓</span>
          <span>Confirm</span>
          <span class="context-shortcut">Ctrl+S</span>
        </button>
        <button
          class="context-item"
          onclick={() => setRowStatus('translated')}
          disabled={contextRow?.status === 'translated'}
        >
          <span class="context-icon">📝</span>
          <span>Set as Translated</span>
        </button>
        <button
          class="context-item"
          onclick={() => setRowStatus('untranslated')}
          disabled={contextRow?.status === 'untranslated'}
        >
          <span class="context-icon">↩</span>
          <span>Set as Untranslated</span>
          <span class="context-shortcut">Ctrl+U</span>
        </button>
      </div>
      <div class="context-menu-divider"></div>
      <div class="context-menu-section">
        <button class="context-item" onclick={runQAOnRow}>
          <span class="context-icon">⚠</span>
          <span>Run QA on Row</span>
        </button>
        <button
          class="context-item"
          onclick={dismissQAFromContextMenu}
          disabled={!contextRow?.qa_flag_count}
        >
          <span class="context-icon">✗</span>
          <span>Dismiss QA Issues</span>
          <span class="context-shortcut">Ctrl+D</span>
        </button>
        <button class="context-item" onclick={addToTMFromContextMenu}>
          <span class="context-icon">+</span>
          <span>Add to TM</span>
        </button>
      </div>
      <div class="context-menu-divider"></div>
      <div class="context-menu-section">
        <button class="context-item" onclick={() => copyToClipboard(contextRow?.source || '', 'Source')}>
          <span class="context-icon">📋</span>
          <span>Copy Source</span>
        </button>
        <button class="context-item" onclick={() => copyToClipboard(contextRow?.target || '', 'Target')}>
          <span class="context-icon">📋</span>
          <span>Copy Target</span>
        </button>
        <button class="context-item" onclick={() => copyToClipboard(`${contextRow?.source || ''}\t${contextRow?.target || ''}`, 'Row')}>
          <span class="context-icon">📋</span>
          <span>Copy Row</span>
        </button>
      </div>
    </div>
  {/if}
</div>

<!-- svelte:window for closing context menu -->
<svelte:window onclick={handleGlobalClick} />

<!-- Phase 2: Edit Modal REMOVED - replaced by inline editing
     Double-click Target cell = inline edit
     TM matches displayed in side panel (TMQAPanel.svelte)
-->

<style>
  .virtual-grid {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    background: var(--cds-background);
    /* UI-053 FIX: min-height: 0 allows flex child to shrink below content size */
    min-height: 0;
  }

  .grid-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem 1.25rem; /* More spacious header */
    border-bottom: 1px solid var(--cds-border-subtle-01);
    background: var(--cds-layer-01);
  }

  .header-left {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .header-right {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .grid-header h4 {
    margin: 0;
    font-size: 0.875rem;
    font-weight: 600;
  }

  .row-count {
    font-size: 0.75rem;
    color: var(--cds-text-02);
  }

  /* P2: Search + Filter bar layout */
  .search-filter-bar {
    display: flex;
    gap: 0.75rem;
    padding: 0.5rem 1rem;
    background: var(--cds-layer-01);
    border-bottom: 1px solid var(--cds-border-subtle-01);
    align-items: center;
  }

  .search-wrapper {
    flex: 1;
    min-width: 200px;
  }

  .search-wrapper :global(.bx--search) {
    background: var(--cds-field-01);
  }

  .search-wrapper :global(.bx--search-input) {
    background: var(--cds-field-01);
    border-bottom: 1px solid var(--cds-border-strong-01);
  }

  .search-wrapper :global(.bx--search-input:focus) {
    border-bottom: 2px solid var(--cds-interactive-01);
  }

  .filter-wrapper {
    flex: 0 0 160px;
  }

  .filter-wrapper :global(.bx--dropdown) {
    background: var(--cds-field-01);
    height: 2rem; /* Match search input height (32px) */
  }

  .filter-wrapper :global(.bx--list-box) {
    height: 2rem; /* Match search input height (32px) */
  }

  .filter-wrapper :global(.bx--list-box__field) {
    height: 2rem; /* Match search input height (32px) */
  }

  /* P5: Combined Search Control */
  .search-control {
    display: flex;
    align-items: center;
    flex: 1;
    min-width: 200px;
    /* Removed max-width: 400px - was too restrictive, matching old search-wrapper behavior */
    position: relative;
  }

  .search-mode-btn {
    display: flex;
    align-items: center;
    gap: 2px;
    padding: 0 8px;
    height: 2rem;
    background: var(--cds-field-02);
    border: 1px solid var(--cds-border-subtle-01);
    border-right: none;
    border-radius: 4px 0 0 4px;
    cursor: pointer;
    color: var(--cds-text-01);
    font-size: 0.875rem;
    transition: background 0.15s;
  }

  .search-mode-btn:hover {
    background: var(--cds-layer-hover-01);
  }

  .mode-icon {
    font-size: 1rem;
    font-weight: 500;
  }

  .search-input-wrapper {
    flex: 1;
    position: relative;
  }

  .search-input {
    width: 100%;
    height: 2rem;
    padding: 0 2rem 0 0.75rem;
    background: var(--cds-field-01);
    border: 1px solid var(--cds-border-subtle-01);
    border-radius: 0 4px 4px 0;
    color: var(--cds-text-01);
    font-size: 0.875rem;
    outline: none;
  }

  .search-input:focus {
    border-color: var(--cds-focus);
    box-shadow: inset 0 0 0 1px var(--cds-focus);
  }

  .search-input::placeholder {
    color: var(--cds-text-05);
  }

  .search-clear {
    position: absolute;
    right: 4px;
    top: 50%;
    transform: translateY(-50%);
    display: flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    background: transparent;
    border: none;
    cursor: pointer;
    color: var(--cds-text-02);
    border-radius: 2px;
  }

  .search-clear:hover {
    background: var(--cds-layer-hover-01);
    color: var(--cds-text-01);
  }

  /* Search Settings Popover */
  .search-settings-popover {
    position: absolute;
    top: calc(100% + 4px);
    left: 0;
    z-index: 1000;
    background: var(--cds-layer-01);
    border: 1px solid var(--cds-border-subtle-01);
    border-radius: 6px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
    padding: 12px;
    min-width: 280px;
  }

  .settings-section {
    margin-bottom: 12px;
  }

  .settings-section:last-child {
    margin-bottom: 0;
  }

  .settings-label {
    font-size: 0.7rem;
    font-weight: 600;
    color: var(--cds-text-02);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 6px;
  }

  .mode-buttons {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 4px;
  }

  .mode-option {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 10px;
    background: var(--cds-field-01);
    border: 1px solid var(--cds-border-subtle-01);
    border-radius: 4px;
    cursor: pointer;
    transition: all 0.15s;
    color: var(--cds-text-02);
  }

  .mode-option:hover {
    background: var(--cds-layer-hover-01);
    color: var(--cds-text-01);
  }

  .mode-option.active {
    background: var(--cds-interactive-01);
    border-color: var(--cds-interactive-01);
    color: var(--cds-text-on-color);
  }

  .mode-option-icon {
    font-size: 1rem;
    font-weight: 600;
  }

  .mode-option-text {
    font-size: 0.8rem;
  }

  .field-toggles {
    display: flex;
    gap: 6px;
  }

  .field-toggle {
    display: flex;
    align-items: center;
    padding: 6px 10px;
    background: var(--cds-field-01);
    border: 1px solid var(--cds-border-subtle-01);
    border-radius: 4px;
    cursor: pointer;
    transition: all 0.15s;
    font-size: 0.8rem;
    color: var(--cds-text-02);
  }

  .field-toggle:hover {
    background: var(--cds-layer-hover-01);
  }

  .field-toggle.active {
    background: var(--cds-interactive-02);
    border-color: var(--cds-interactive-02);
    color: var(--cds-text-on-color);
  }

  .field-toggle input[type="checkbox"] {
    display: none;
  }

  .settings-backdrop {
    position: fixed;
    inset: 0;
    z-index: 999;
  }

  /* Hotkey Reference Bar */
  .hotkey-bar {
    display: flex;
    gap: 1rem;
    padding: 0.35rem 1rem;
    background: var(--cds-layer-accent-01);
    border-bottom: 1px solid var(--cds-border-subtle-01);
    font-size: 0.7rem;
    color: var(--cds-text-02);
    flex-wrap: wrap;
  }

  .hotkey {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
  }

  .hotkey kbd {
    display: inline-block;
    padding: 0.15rem 0.4rem;
    background: var(--cds-field-01);
    border: 1px solid var(--cds-border-strong-01);
    border-radius: 3px;
    font-family: var(--cds-code-01);
    font-size: 0.65rem;
    font-weight: 500;
    color: var(--cds-text-01);
    box-shadow: 0 1px 0 var(--cds-border-subtle-01);
  }

  .table-header {
    display: flex;
    background: var(--cds-layer-accent-01);
    border-bottom: 1px solid var(--cds-border-subtle-01);
    font-weight: 500;
    font-size: 0.8125rem;
    text-transform: none; /* Cleaner look without uppercase */
    letter-spacing: normal;
    color: var(--cds-text-02);
  }

  /* UI-083: Full-height column resize bars (unified system) */
  .column-resize-bar {
    position: absolute;
    top: 0;
    bottom: 0;
    width: 10px;
    margin-left: -5px; /* Center on the column boundary */
    cursor: col-resize;
    background: transparent;
    z-index: 20;
    transition: background-color 0.15s;
  }

  .column-resize-bar:hover {
    background: rgba(15, 98, 254, 0.35);
  }

  .column-resize-bar:active,
  .column-resize-bar.resize-active {
    background: var(--cds-interactive-01, #0f62fe);
  }

  .th {
    padding: 0.875rem 1rem; /* Match cell padding for alignment */
    border-right: 1px solid var(--cds-border-subtle-01);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  /* UI-044: Minimum width for source/target headers */
  .th-source,
  .th-target {
    min-width: 150px;
  }

  /* Source column header - subtle divider */
  .th-source {
    position: relative;
    border-right: 1px solid var(--cds-border-subtle-02, #525252);
  }

  .th-target {
    /* Target header - no special border needed */
  }

  /* NOTE: UI-083 removed .resize-handle - now using unified .column-resize-bar system */

  /* FIX: Wrapper for scroll container + resize bars overlay */
  .scroll-wrapper {
    flex: 1;
    display: flex;
    flex-direction: column;
    position: relative;
    min-height: 0;
    height: 0; /* Critical for flex to work */
  }

  .scroll-container {
    flex: 1;
    overflow-y: auto;
    overflow-x: hidden;
    position: relative;
    /* UI-053 FIX: Critical - height: 0 + flex: 1 forces container to respect parent height */
    /* Without this, flex child expands to content height, breaking virtual scroll */
    height: 0;
    min-height: 200px; /* Minimum for usability */
    /* UI-080 FIX: Reserve scrollbar space to align header with data rows */
    /* Without this, header columns are wider than data columns by scrollbar width (~15px) */
    scrollbar-gutter: stable;
  }

  .scroll-content {
    position: relative;
    width: 100%;
  }

  .loading-overlay {
    display: flex;
    justify-content: center;
    align-items: center;
    height: 200px;
  }

  .virtual-row {
    position: absolute;
    left: 0;
    right: 0;
    display: flex;
    /* Subtle row separator for cleaner look */
    border-bottom: 1px solid var(--cds-border-subtle-01, #393939);
    background: var(--cds-layer-01);
    transition: background-color 0.15s ease;
    /* VARIABLE HEIGHT: Row height is set via inline style, content can expand */
    box-sizing: border-box;
  }

  /* HOVER SYSTEM: Row-level hover (subtle background) */
  .virtual-row:hover,
  .virtual-row.row-hovered {
    background: var(--cds-layer-hover-01);
  }

  /* UI-059 FIX: Selected row takes priority over hover */
  .virtual-row.selected {
    background: var(--cds-layer-selected-01) !important;
    /* Make selection more prominent with left border */
    border-left: 3px solid var(--cds-interactive-01, #0f62fe);
    /* Subtle shadow for depth */
    box-shadow: inset 0 0 0 1px rgba(15, 98, 254, 0.2);
  }

  /* UI-059: Selected + hovered - slightly different to show both states */
  .virtual-row.selected:hover,
  .virtual-row.selected.row-hovered {
    background: var(--cds-layer-selected-hover-01, rgba(15, 98, 254, 0.18)) !important;
  }

  .virtual-row.placeholder {
    opacity: 0.5;
  }

  .virtual-row.locked {
    background: var(--cds-layer-02);
  }

  .cell {
    padding: 0.75rem 1rem; /* More spacious padding for cleaner look */
    font-size: var(--grid-font-size, 14px);
    font-weight: var(--grid-font-weight, 400);
    font-family: var(--grid-font-family, inherit);
    color: var(--grid-font-color, var(--cds-text-01));
    /* Subtle border for cleaner look */
    border-right: 1px solid var(--cds-border-subtle-01, #393939);
    display: flex;
    align-items: flex-start;
    /* VARIABLE HEIGHT: Cells expand to fit content */
    overflow: hidden;
    text-overflow: ellipsis;
    min-width: 0;
    /* SMART MEMBRANE: Let content determine height, don't force 100% */
    align-self: stretch;
    box-sizing: border-box;
  }

  /* UI-090: Source and Target cells use flex-grow ratios to share remaining space */
  /* After fixed columns (index, stringId), source/target divide what's left */
  /* flex is controlled by inline style, no default flex here */

  .cell-content {
    word-break: break-word;
    white-space: pre-wrap;
    line-height: 1.6; /* More spacious line height for readability */
    /* VARIABLE HEIGHT: Content expands fully - no scrollbar */
    width: 100%;
  }

  .cell.row-num {
    justify-content: center;
    align-items: center;
    color: var(--cds-text-02);
    font-size: 0.75rem;
    flex: none; /* UI-083: Use inline width style, not fixed flex */
  }

  .cell.string-id {
    font-family: monospace;
    font-size: 0.75rem;
    word-break: break-all;
    flex: none; /* UI-083: Use inline width style, not fixed flex */
  }

  .cell.source {
    background: var(--cds-layer-02);
    color: var(--cds-text-02);
    transition: background-color 0.15s ease;
    /* Subtle divider between source and target */
    border-right: 1px solid var(--cds-border-subtle-02, #525252);
    /* Source is READ-ONLY - cursor indicates this */
    cursor: default;
  }

  /* HOVER SYSTEM: Source cell - subtle hover (read-only indicator) */
  .cell.source.row-active {
    background: var(--cds-layer-hover-01);
  }

  .cell.source.source-hovered {
    /* Slightly more prominent when directly hovered, but still subtle */
    background: var(--cds-layer-accent-hover-01, var(--cds-layer-hover-01));
    /* Subtle left border to show focus */
    border-left: 2px solid var(--cds-border-subtle-02, #525252);
  }

  .cell.target {
    position: relative;
    cursor: pointer;
    padding-right: 1.5rem;
    transition: all 0.15s ease;
  }

  /* HOVER SYSTEM: Target cell - when row is active but source is hovered */
  .cell.target.row-active {
    background: var(--cds-layer-hover-01);
  }

  /* HOVER SYSTEM: Target cell - prominent when directly hovered (EDITABLE) */
  .cell.target.target-hovered {
    background: var(--cds-interactive-02, #4589ff);
    background: rgba(69, 137, 255, 0.15);
    /* Blue left border indicates editable/active */
    border-left: 3px solid var(--cds-interactive-01, #0f62fe);
    /* Slight shadow for depth */
    box-shadow: inset 0 0 0 1px rgba(15, 98, 254, 0.3);
  }

  /* Show edit icon when target is hovered */
  .cell.target.target-hovered .edit-icon {
    opacity: 1;
    color: var(--cds-interactive-01, #0f62fe);
  }

  .cell.target.locked {
    cursor: not-allowed;
    background: var(--cds-layer-02);
  }

  /* Phase 2: Inline editing mode */
  .cell.target.inline-editing {
    padding: 0;
    background: var(--cds-field-01);
    border: 2px solid var(--cds-interactive-01);
    box-shadow: 0 0 0 2px rgba(15, 98, 254, 0.3);
  }

  .inline-edit-textarea {
    width: 100%;
    height: 100%;
    min-height: 100%;
    padding: 0.5rem;
    border: none;
    background: var(--cds-field-01);
    color: var(--grid-font-color, var(--cds-text-01));
    font-family: var(--grid-font-family, inherit);
    font-size: var(--grid-font-size, 0.875rem);
    font-weight: var(--grid-font-weight, 400);
    line-height: 1.5;
    outline: none;
    overflow-y: auto;
    white-space: pre-wrap;
    word-wrap: break-word;
    cursor: text;
  }

  .inline-edit-textarea:focus {
    outline: none;
  }

  /* Placeholder for contenteditable */
  .inline-edit-textarea:empty:before {
    content: attr(data-placeholder);
    color: var(--cds-text-02);
    font-style: italic;
    pointer-events: none;
  }

  /* Inline edit container for textarea + preview */
  .inline-edit-container {
    display: flex;
    flex-direction: column;
    width: 100%;
    height: 100%;
    min-height: 100%;
  }

  .inline-edit-container .inline-edit-textarea {
    flex: 1;
    min-height: 60px;
  }

  /* Color Picker Context Menu */
  .color-picker-overlay {
    position: fixed;
    inset: 0;
    z-index: 999;
  }

  .color-picker-menu {
    position: fixed;
    z-index: 1000;
    min-width: 200px;
    background: var(--cds-layer-02);
    border: 1px solid var(--cds-border-strong-01);
    border-radius: 4px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    overflow: hidden;
  }

  .color-picker-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.5rem 0.75rem;
    background: var(--cds-layer-01);
    border-bottom: 1px solid var(--cds-border-subtle-01);
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--cds-text-01);
  }

  .color-picker-header .close-btn {
    background: none;
    border: none;
    color: var(--cds-text-02);
    font-size: 1rem;
    cursor: pointer;
    padding: 0;
    line-height: 1;
  }

  .color-picker-header .close-btn:hover {
    color: var(--cds-text-01);
  }

  .color-picker-colors {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 4px;
    padding: 0.5rem;
  }

  .color-swatch {
    width: 100%;
    aspect-ratio: 1;
    border: 2px solid transparent;
    border-radius: 4px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.15s ease;
  }

  .color-swatch:hover {
    transform: scale(1.1);
    border-color: var(--cds-border-strong-01);
  }

  .color-swatch .color-name {
    font-size: 0.5rem;
    color: #000;
    text-shadow: 0 0 2px #fff, 0 0 2px #fff;
    font-weight: 600;
  }

  .color-picker-preview {
    padding: 0.5rem 0.75rem;
    background: var(--cds-layer-01);
    border-top: 1px solid var(--cds-border-subtle-01);
    font-size: 0.7rem;
    color: var(--cds-text-02);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .color-picker-preview .preview-text {
    font-style: italic;
  }

  .color-picker-preview .preview-label {
    color: var(--cds-text-02);
    margin-right: 0.25rem;
  }

  /* UI-113: Edit Context Menu (replaces simple color picker) */
  .edit-context-menu {
    position: fixed;
    z-index: 1000;
    min-width: 220px;
    background: var(--cds-layer-02);
    border: 1px solid var(--cds-border-strong-01);
    border-radius: 4px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    overflow: hidden;
  }

  .edit-menu-section {
    padding: 0.25rem 0;
  }

  .edit-menu-header {
    padding: 0.5rem 0.75rem 0.25rem;
    font-size: 0.7rem;
    font-weight: 600;
    color: var(--cds-text-02);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .edit-menu-hint {
    padding: 0.5rem 0.75rem;
    font-size: 0.7rem;
    color: var(--cds-text-03);
    font-style: italic;
  }

  .edit-menu-divider {
    height: 1px;
    background: var(--cds-border-subtle-01);
    margin: 0.25rem 0;
  }

  .edit-menu-item {
    display: flex;
    align-items: center;
    width: 100%;
    padding: 0.5rem 0.75rem;
    background: none;
    border: none;
    color: var(--cds-text-01);
    font-size: 0.8rem;
    cursor: pointer;
    text-align: left;
    gap: 0.5rem;
  }

  .edit-menu-item:hover:not(:disabled) {
    background: var(--cds-layer-hover-02);
  }

  .edit-menu-item:disabled {
    color: var(--cds-text-03);
    cursor: not-allowed;
  }

  .edit-menu-icon {
    width: 1rem;
    text-align: center;
    font-size: 0.9rem;
  }

  .edit-menu-item span:nth-child(2) {
    flex: 1;
  }

  .edit-menu-shortcut {
    font-size: 0.65rem;
    color: var(--cds-text-03);
  }

  /* Status-based cell colors (replaces Status column)
   * Simple 2-state scheme:
   * - Unconfirmed (pending, translated) = Gray (default, no styling)
   * - Confirmed (reviewed, approved) = Teal highlight
   */

  /* Unconfirmed: No special styling - just default gray background */
  /* .cell.target.status-translated - intentionally unstyled */

  /* Confirmed: Teal highlight for reviewed rows */
  .cell.target.status-reviewed {
    background: rgba(0, 157, 154, 0.15); /* teal - confirmed */
    border-left: 3px solid var(--cds-support-04);
  }

  /* Confirmed: Teal highlight for approved rows (same as reviewed) */
  .cell.target.status-approved {
    background: rgba(0, 157, 154, 0.15); /* teal - confirmed */
    border-left: 3px solid var(--cds-support-04);
  }

  /* Status hover overrides for confirmed cells */
  .cell.target.status-reviewed:hover,
  .cell.target.status-approved:hover {
    filter: brightness(1.1);
  }

  .edit-icon, .lock-icon {
    position: absolute;
    right: 0.25rem;
    opacity: 0;
    color: var(--cds-icon-02);
    transition: opacity 0.15s ease;
  }

  .cell.target:hover .edit-icon {
    opacity: 1;
  }

  /* UI-059 & UI-065: Selected cell states */
  .cell.cell-selected {
    background: var(--cds-layer-selected-01);
  }

  .cell.target.cell-selected {
    /* Selected target cell - subtle blue tint */
    background: rgba(69, 137, 255, 0.1);
    border-left: 3px solid var(--cds-interactive-01, #0f62fe);
  }

  /* UI-065: Show edit icon on selected cells (not just hover) */
  .cell.target.cell-selected .edit-icon {
    opacity: 0.7;
    color: var(--cds-interactive-01, #0f62fe);
  }

  /* Selected + hovered - full opacity */
  .cell.target.cell-selected:hover .edit-icon,
  .cell.target.cell-selected.target-hovered .edit-icon {
    opacity: 1;
  }

  .cell.target.locked .lock-icon {
    opacity: 0.8;
    color: var(--cds-support-03);
  }

  /* P2: QA Flag Styles */
  .cell.target.qa-flagged {
    border-left: 3px solid var(--cds-support-01, #da1e28);
    background: rgba(218, 30, 40, 0.08);
  }

  .qa-icon {
    position: absolute;
    right: 1.75rem; /* UI-069: Moved left to avoid overlap with edit icon */
    color: var(--cds-support-01, #da1e28);
    opacity: 1;
    z-index: 1; /* Below edit icon */
  }

  /* UI-069: When QA icon present, shift edit icon right to ensure no overlap */
  .cell.target.qa-flagged .edit-icon {
    right: 0.35rem;
  }

  .cell.target.qa-flagged:hover {
    background: rgba(218, 30, 40, 0.12);
  }

  /* ========================================
     Reference Column (Phase 8)
     ======================================== */
  .cell.reference {
    background: var(--cds-layer-02);
    color: var(--cds-text-02);
    font-size: 0.8rem;
    flex: none; /* UI-083: Use inline width style, not fixed flex */
  }

  .cell.reference.has-match {
    background: rgba(36, 161, 72, 0.08);
    border-left: 2px solid var(--cds-support-02);
  }

  .cell.reference .ref-match {
    color: var(--cds-text-01);
  }

  /* UI-071: Clearer "No match" styling */
  .cell.reference .no-match {
    color: var(--cds-text-03);
    font-style: italic;
    font-size: 0.75rem;
    opacity: 0.7;
  }

  /* ========================================
     TM Match Column (Phase 9)
     ======================================== */
  .cell.tm-result {
    background: var(--cds-layer-02);
    flex-direction: column;
    align-items: flex-start;
    gap: 0.25rem;
    padding: 0.35rem 0.5rem;
  }

  .cell.tm-result.high-match {
    background: rgba(36, 161, 72, 0.12);
    border-left: 3px solid var(--cds-support-02);
  }

  .cell.tm-result.medium-match {
    background: rgba(255, 209, 0, 0.12);
    border-left: 3px solid var(--cds-support-03);
  }

  .cell.tm-result.low-match {
    background: rgba(198, 198, 198, 0.12);
    border-left: 3px solid var(--cds-border-subtle-01);
  }

  .tm-similarity {
    font-size: 0.65rem;
    font-weight: 600;
    padding: 0.1rem 0.35rem;
    border-radius: 4px;
    background: var(--cds-layer-accent-01);
    color: var(--cds-text-02);
  }

  .cell.tm-result.high-match .tm-similarity {
    background: var(--cds-support-02);
    color: white;
  }

  .cell.tm-result.medium-match .tm-similarity {
    background: var(--cds-support-03);
    color: var(--cds-text-inverse);
  }

  .cell.tm-result .no-match {
    color: var(--cds-text-03);
    font-style: italic;
    font-size: 0.75rem;
  }

  .loading-cell {
    justify-content: center;
  }

  /* PERF: Static placeholder - no animation for smooth scrolling */
  .placeholder-shimmer {
    width: 60%;
    height: 16px;
    background: #3a3a3a;
    border-radius: 4px;
  }

  .loading-bar {
    padding: 0.25rem 1rem;
    background: var(--cds-layer-02);
    border-top: 1px solid var(--cds-border-subtle-01);
  }

  /* UI-041: Removed .grid-footer CSS */

  .empty-state {
    display: flex;
    justify-content: center;
    align-items: center;
    height: 100%;
    color: var(--cds-text-02);
  }

  /* ========================================
     Phase 2: EDIT MODAL CSS REMOVED
     Replaced by:
     - Inline editing (double-click Target cell)
     - TMQAPanel.svelte (side panel for TM/QA)
     ======================================== */

  /* ========================================
     UX-002: Cell Context Menu
     ======================================== */
  .context-menu {
    position: fixed;
    z-index: 1000;
    min-width: 200px;
    background: var(--cds-layer-02, #262626);
    border: 1px solid var(--cds-border-subtle-01);
    border-radius: 4px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
    padding: 0.25rem 0;
  }

  .context-menu-section {
    padding: 0.25rem 0;
  }

  .context-menu-divider {
    height: 1px;
    background: var(--cds-border-subtle-01);
    margin: 0.25rem 0;
  }

  .context-item {
    display: flex;
    align-items: center;
    width: 100%;
    padding: 0.5rem 1rem;
    background: transparent;
    border: none;
    text-align: left;
    color: var(--cds-text-01);
    font-size: 0.875rem;
    cursor: pointer;
    transition: background 0.1s ease;
    gap: 0.75rem;
  }

  .context-item:hover:not(:disabled) {
    background: var(--cds-layer-hover-01);
  }

  .context-item:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .context-icon {
    width: 1rem;
    text-align: center;
    flex-shrink: 0;
  }

  .context-shortcut {
    margin-left: auto;
    font-size: 0.75rem;
    color: var(--cds-text-02);
    opacity: 0.7;
  }
</style>
