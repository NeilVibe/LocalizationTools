<script>
  import {
    Search,
    InlineLoading,
    Tag,
    Button,
    Dropdown
  } from "carbon-components-svelte";
  import { Edit, Locked } from "carbon-icons-svelte";
  import { createEventDispatcher, onMount, onDestroy, tick } from "svelte";
  import { get } from "svelte/store";
  import { logger } from "$lib/utils/logger.js";
  import { ldmStore, joinFile, leaveFile, lockRow, unlockRow, isRowLocked, onCellUpdate, ldmConnected } from "$lib/stores/ldm.js";
  import { preferences, getFontSizeValue } from "$lib/stores/preferences.js";
  import { WarningAltFilled } from "carbon-icons-svelte";
  import { serverUrl } from "$lib/stores/app.js";
  import PresenceBar from "./PresenceBar.svelte";

  const dispatch = createEventDispatcher();

  // Svelte 5: Derived - API base URL from store
  let API_BASE = $derived(get(serverUrl));

  // Svelte 5: Props
  let { fileId = $bindable(null), fileName = "" } = $props();

  // Virtual scrolling constants
  // UI-057: Increased from 48 to 72 for better readability (fits 2-3 lines)
  const MIN_ROW_HEIGHT = 72; // Minimum row height
  const MAX_ROW_HEIGHT = 200; // Maximum row height (~8 lines max per user request)
  const CHARS_PER_LINE = 50; // Estimated chars per line for height calc
  const LINE_HEIGHT = 20; // Height per line of text
  const BUFFER_ROWS = 10; // Extra rows to render above/below viewport
  const PAGE_SIZE = 100; // Rows per page to fetch
  const PREFETCH_PAGES = 2; // Number of pages to prefetch ahead/behind

  // Real-time subscription
  let cellUpdateUnsubscribe = null;

  // Svelte 5: State
  let loading = $state(false);
  let initialLoading = $state(true);
  let rows = $state([]); // Cached rows (sparse array by row_num)
  let total = $state(0);
  let searchTerm = $state("");
  let searchDebounceTimer = null;

  // P2: Filter state
  let activeFilter = $state("all"); // 'all' | 'confirmed' | 'unconfirmed' | 'qa_flagged'
  const filterOptions = [
    { id: "all", text: "All Rows" },
    { id: "confirmed", text: "Confirmed" },
    { id: "unconfirmed", text: "Unconfirmed" },
    { id: "qa_flagged", text: "QA Flagged" }
  ];

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

  // Svelte 5: Edit modal state
  let showEditModal = $state(false);
  let editingRow = $state(null);
  let editTarget = $state("");
  let editStatus = $state("");

  // Selected row state
  let selectedRowId = $state(null);

  // TM suggestions state
  let tmSuggestions = $state([]);
  let tmLoading = $state(false);

  // P2: QA state
  let qaLoading = $state(false);
  let lastQaResult = $state(null); // Latest QA check result for edit modal

  // UI-044: Resizable columns state
  let sourceWidthPercent = $state(50); // Source column takes 50% by default
  let isResizing = $state(false);
  let resizeStartX = $state(0);
  let resizeStartPercent = $state(50);

  // Table column definitions (widths will be calculated dynamically)
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

  // Svelte 5: Derived - font styles from preferences (UI-031, UI-032)
  let gridFontSize = $derived(getFontSizeValue($preferences.fontSize));
  let gridFontWeight = $derived($preferences.fontWeight === 'bold' ? '600' : '400');

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

  // Helper to get auth headers
  function getAuthHeaders() {
    const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
    return token ? { 'Authorization': `Bearer ${token}` } : {};
  }

  // PERFORMANCE FIX: Calculate visible range with O(1) complexity
  // Uses constant row height for consistent, fast scroll calculations
  function calculateVisibleRange() {
    if (!containerEl) return;

    containerHeight = containerEl.clientHeight;
    scrollTop = containerEl.scrollTop;

    // Sanity check: container height shouldn't be larger than viewport
    // BUG-036-FIX: Detect incorrect container sizing
    if (containerHeight > 5000) {
      logger.warning("Container height unusually large", {
        containerHeight,
        windowHeight: typeof window !== 'undefined' ? window.innerHeight : 0
      });
      // Cap to reasonable max
      containerHeight = Math.min(containerHeight, 1200);
    }

    // O(1) calculation using constant row height
    const startRow = Math.floor(scrollTop / MIN_ROW_HEIGHT);
    const endRow = Math.ceil((scrollTop + containerHeight) / MIN_ROW_HEIGHT);

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
      }
      // P2: Add filter param
      if (activeFilter && activeFilter !== 'all') {
        params.append('filter', activeFilter);
      }

      const response = await fetch(`${API_BASE}/api/ldm/files/${fileId}/rows?${params}`, {
        headers: getAuthHeaders()
      });

      if (response.ok) {
        const data = await response.json();
        total = data.total;

        // Store rows by their row_num for sparse array access
        // SMART INDEXING: Also build index map for O(1) lookups
        data.rows.forEach(row => {
          const index = row.row_num - 1;
          const rowData = {
            ...row,
            id: row.id.toString()
          };
          rows[index] = rowData;
          rowIndexById.set(row.id.toString(), index); // O(1) lookup index
        });

        // Force reactivity
        rows = [...rows];

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

  // SMART INDEXING: Initial load with instant display
  // BUG-037: Export function to open edit modal by row ID (for QA panel integration)
  export async function openEditModalByRowId(rowId) {
    // Find the row in our loaded rows
    const row = rows.find(r => r && r.id === rowId);
    if (row) {
      await openEditModal(row);
    } else {
      logger.warning("Row not loaded yet", { rowId });
    }
  }

  export async function loadRows() {
    if (!fileId) return;

    // Reset state INSTANTLY - don't wait for API
    rows = [];
    loadedPages.clear();
    loadingPages.clear();
    rowIndexById.clear(); // SMART INDEXING: Clear index map
    total = 0;
    initialLoading = true;

    // OPTIMIZATION: Single API call for first page + count (not 2 calls)
    // The first page response includes total count
    try {
      const params = new URLSearchParams({
        page: '1',
        limit: PAGE_SIZE.toString()
      });

      const response = await fetch(`${API_BASE}/api/ldm/files/${fileId}/rows?${params}`, {
        headers: getAuthHeaders()
      });

      if (response.ok) {
        const data = await response.json();
        total = data.total;

        // INSTANT: Store rows immediately + build index
        data.rows.forEach(row => {
          const index = row.row_num - 1;
          const rowData = {
            ...row,
            id: row.id.toString()
          };
          rows[index] = rowData;
          rowIndexById.set(row.id.toString(), index); // O(1) lookup
        });
        rows = [...rows];
        loadedPages.add(1);

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
  function handleSearch() {
    if (searchDebounceTimer) clearTimeout(searchDebounceTimer);
    searchDebounceTimer = setTimeout(() => {
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

  // Fetch TM suggestions for a source text
  async function fetchTMSuggestions(sourceText, rowId) {
    if (!sourceText || !sourceText.trim()) {
      tmSuggestions = [];
      return;
    }

    tmLoading = true;
    tmSuggestions = [];

    try {
      const params = new URLSearchParams({
        source: sourceText,
        threshold: '0.3',
        max_results: '5'
      });
      if (fileId) params.append('file_id', fileId.toString());
      if (rowId) params.append('exclude_row_id', rowId.toString());

      const response = await fetch(`${API_BASE}/api/ldm/tm/suggest?${params}`, {
        headers: getAuthHeaders()
      });

      if (response.ok) {
        const data = await response.json();
        tmSuggestions = data.suggestions || [];
        logger.info("TM suggestions fetched", { count: tmSuggestions.length });
      }
    } catch (err) {
      logger.error("Failed to fetch TM suggestions", { error: err.message });
    } finally {
      tmLoading = false;
    }
  }

  // Apply a TM suggestion
  function applyTMSuggestion(suggestion) {
    editTarget = suggestion.target;
    logger.userAction("TM suggestion applied", {
      source: suggestion.source.substring(0, 30),
      similarity: suggestion.similarity
    });
  }

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
   * Fetch TM result for a row and cache it
   */
  async function fetchTMResultForRow(row) {
    if (!row.source || !$preferences.activeTmId) return;

    const rowId = row.id;
    if (tmResults.has(rowId)) return; // Already cached

    try {
      const params = new URLSearchParams({
        source: row.source,
        threshold: '0.5',
        max_results: '1'
      });
      if ($preferences.activeTmId) {
        params.append('tm_id', $preferences.activeTmId.toString());
      }

      const response = await fetch(`${API_BASE}/api/ldm/tm/suggest?${params}`, {
        headers: getAuthHeaders()
      });

      if (response.ok) {
        const data = await response.json();
        if (data.suggestions && data.suggestions.length > 0) {
          const best = data.suggestions[0];
          tmResults.set(rowId, {
            target: best.target,
            similarity: best.similarity,
            source: best.source
          });
          tmResults = tmResults; // Trigger reactivity
        }
      }
    } catch (err) {
      // Silent fail - TM results are optional
    }
  }

  // Svelte 5: Effect - Clear TM cache when active TM changes
  $effect(() => {
    if ($preferences.activeTmId !== undefined) {
      tmResults = new Map();
    }
  });

  // Open edit modal with row locking
  async function openEditModal(row) {
    if (!row) return;

    // Check if row is locked by another user
    const lock = isRowLocked(parseInt(row.id));
    // Only block if there's a valid lock with a username (null = stale/invalid lock)
    if (lock && lock.locked_by) {
      logger.warning("Row locked by another user", { rowId: row.id, lockedBy: lock.locked_by });
      alert(`This row is being edited by ${lock.locked_by}`);
      return;
    }

    // Request row lock for editing
    if (fileId) {
      const granted = await lockRow(fileId, parseInt(row.id));
      if (!granted) {
        logger.warning("Could not acquire lock", { rowId: row.id });
        alert("Could not acquire lock. Row may be in use by another user.");
        return;
      }
    }

    editingRow = row;
    // Format target for editing (convert escapes to real newlines)
    editTarget = formatGridText(row.target || "");
    editStatus = row.status || "pending";
    showEditModal = true;
    logger.userAction("Edit modal opened", { rowId: row.id });

    // Fetch TM suggestions in background
    fetchTMSuggestions(row.source, row.id);

    // Auto-focus textarea after modal renders (fixes BUG-005: keyboard shortcuts not working)
    await tick();
    const textarea = document.querySelector('.target-textarea');
    if (textarea) {
      textarea.focus();
    }
  }

  // Close edit modal and release lock
  function closeEditModal() {
    logger.info("closeEditModal called", {
      hasEditingRow: !!editingRow,
      fileId,
      showEditModal
    });

    try {
      if (editingRow && fileId) {
        // Fire and forget - don't let unlock failure block modal close
        unlockRow(fileId, parseInt(editingRow.id)).catch(err => {
          logger.warning("Failed to unlock row", { error: err.message });
        });
      }
    } catch (err) {
      logger.error("Error in unlockRow", { error: err.message });
    }

    // These MUST execute regardless of unlock status
    showEditModal = false;
    editingRow = null;
    tmSuggestions = [];
    tmLoading = false;

    logger.info("closeEditModal complete", { showEditModal });
  }

  // Save and move to next row
  async function saveAndNext() {
    if (!editingRow) return;

    const currentRowNum = editingRow.row_num;
    await saveEdit();

    // After save, find and edit next row
    await tick();
    const nextRow = rows[currentRowNum]; // row_num is 1-indexed, array is 0-indexed
    if (nextRow && !nextRow.placeholder) {
      setTimeout(() => openEditModal(nextRow), 100);
    }
  }

  // Handle keyboard shortcuts in edit modal
  function handleEditKeydown(event) {
    // Ctrl+S: Save as Confirmed (Reviewed status)
    if (event.ctrlKey && event.key === 's') {
      event.preventDefault();
      editStatus = 'reviewed';
      saveEdit();
      return;
    }

    // Ctrl+T: Save as Translated only (not confirmed)
    if (event.ctrlKey && event.key === 't') {
      event.preventDefault();
      editStatus = 'translated';
      saveEdit();
      return;
    }

    // Ctrl+Enter: Save and next (legacy, keeps current status)
    if (event.ctrlKey && event.key === 'Enter') {
      event.preventDefault();
      saveAndNext();
      return;
    }

    // Tab: Apply first TM suggestion (if available)
    if (event.key === 'Tab' && !event.shiftKey && tmSuggestions.length > 0) {
      event.preventDefault();
      applyTMSuggestion(tmSuggestions[0]);
      return;
    }

    // Escape: Cancel edit
    if (event.key === 'Escape') {
      event.preventDefault();
      closeEditModal();
      return;
    }
  }

  // Save edit
  async function saveEdit() {
    if (!editingRow) return;
    loading = true;
    try {
      const rowId = editingRow.id;
      // Convert newlines based on file type before saving
      const targetToSave = formatTextForSave(editTarget);

      const response = await fetch(`${API_BASE}/api/ldm/rows/${rowId}`, {
        method: 'PUT',
        headers: {
          ...getAuthHeaders(),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          target: targetToSave,
          status: editStatus
        })
      });

      if (response.ok) {
        // Update local cache with the saved format
        const rowIndex = editingRow.row_num - 1;
        if (rows[rowIndex]) {
          rows[rowIndex] = {
            ...rows[rowIndex],
            target: targetToSave,
            status: editStatus
          };
          rows = [...rows];
        }

        logger.success("Row updated", { rowId });

        // P2: Run QA check if LIVE QA is enabled
        if ($preferences.enableLiveQa) {
          const qaResult = await runQACheck(rowId);
          if (qaResult && qaResult.issue_count > 0) {
            // Keep modal open to show QA issues
            lastQaResult = qaResult;
            logger.warning("QA issues detected after save", { count: qaResult.issue_count });
            // Don't close modal - let user see the issues
            dispatch('rowUpdate', { rowId });
            return; // Exit without closing modal
          }
        }

        closeEditModal();
        dispatch('rowUpdate', { rowId });
      } else {
        const error = await response.json();
        logger.error("Update failed", { error: error.detail });
      }
    } catch (err) {
      logger.error("Save error", { error: err.message });
    } finally {
      loading = false;
    }
  }

  // Handle real-time cell updates from other users
  // SMART INDEXING: Uses O(1) lookup instead of O(n) findIndex
  function handleCellUpdates(updates) {
    updates.forEach(update => {
      // O(1) lookup using index map
      const rowIndex = getRowIndexById(update.row_id);
      if (rowIndex !== undefined && rows[rowIndex]) {
        rows[rowIndex] = {
          ...rows[rowIndex],
          target: update.target,
          status: update.status
        };
      }
    });
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

  // Convert newlines back for saving based on file type
  // XML files use &lt;br/&gt;, TXT files use \n
  function formatTextForSave(text) {
    if (!text) return "";
    // Determine file type from fileName
    const isXML = fileName.toLowerCase().endsWith('.xml');
    if (isXML) {
      // XML: convert actual newlines to &lt;br/&gt;
      return text.replace(/\n/g, '&lt;br/&gt;');
    } else {
      // TXT and others: keep actual newlines (backend will handle)
      return text;
    }
  }

  // Count all types of newlines in text
  function countNewlines(text) {
    if (!text) return 0;
    // Count actual \n, escaped \\n, and XML &lt;br/&gt;
    const actualNewlines = (text.match(/\n/g) || []).length;
    const escapedNewlines = (text.match(/\\n/g) || []).length;
    const xmlNewlines = (text.match(/&lt;br\/&gt;/g) || []).length;
    return actualNewlines + escapedNewlines + xmlNewlines;
  }

  // Estimate row height based on content length
  function estimateRowHeight(row) {
    if (!row || row.placeholder) return MIN_ROW_HEIGHT;

    // Get the longest text (source or target)
    const sourceLen = (row.source || "").length;
    const targetLen = (row.target || "").length;
    const maxLen = Math.max(sourceLen, targetLen);

    // Count all newlines (actual, escaped, XML)
    const sourceNewlines = countNewlines(row.source);
    const targetNewlines = countNewlines(row.target);
    const maxNewlines = Math.max(sourceNewlines, targetNewlines);

    // Estimate lines needed
    const wrapLines = Math.ceil(maxLen / CHARS_PER_LINE);
    const totalLines = Math.max(1, wrapLines + maxNewlines);

    // Calculate height
    const estimatedHeight = MIN_ROW_HEIGHT + (totalLines - 1) * LINE_HEIGHT;
    return Math.min(estimatedHeight, MAX_ROW_HEIGHT);
  }

  // PERFORMANCE FIX: Use constant row height for positioning (O(1) instead of O(n))
  // Dynamic heights are only used for visual display, not scroll positioning
  // This fixes the O(n²) bug that caused 10K+ row files to freeze
  function getRowTop(index) {
    return index * MIN_ROW_HEIGHT;
  }

  // PERFORMANCE FIX: Simple O(1) total height calculation
  function getTotalHeight() {
    return total * MIN_ROW_HEIGHT;
  }

  // UI-029: downloadFile removed - users download via right-click on FileExplorer

  // Pre-fetch TM on cell click
  let prefetchedRowId = null;

  function handleCellClick(row, event) {
    if (!row || row.placeholder) return;

    // Select the row
    selectedRowId = row.id;

    // Pre-fetch TM suggestions if not already fetched
    if (prefetchedRowId !== row.id && row.source) {
      prefetchedRowId = row.id;
      fetchTMSuggestions(row.source, row.id);
      logger.info("Pre-fetching TM for row", { rowId: row.id });
    }
  }

  // UI-044: Column resize handlers
  function startResize(event) {
    event.preventDefault();
    isResizing = true;
    resizeStartX = event.clientX;
    resizeStartPercent = sourceWidthPercent;

    // Add global listeners for drag
    document.addEventListener('mousemove', handleResize);
    document.addEventListener('mouseup', stopResize);
  }

  function handleResize(event) {
    if (!isResizing) return;

    const headerEl = document.querySelector('.table-header');
    if (!headerEl) return;

    const headerRect = headerEl.getBoundingClientRect();
    const headerWidth = headerRect.width;
    const deltaX = event.clientX - resizeStartX;
    const deltaPercent = (deltaX / headerWidth) * 100;

    // Clamp between 20% and 80%
    sourceWidthPercent = Math.max(20, Math.min(80, resizeStartPercent + deltaPercent));
  }

  function stopResize() {
    isResizing = false;
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

  // Svelte 5: Effect - Subscribe to real-time updates when file changes
  $effect(() => {
    if (fileId) {
      joinFile(fileId);
      if (cellUpdateUnsubscribe) {
        cellUpdateUnsubscribe();
      }
      cellUpdateUnsubscribe = onCellUpdate(handleCellUpdates);
    }
  });

  // Svelte 5: Effect - Watch file changes
  $effect(() => {
    if (fileId) {
      searchTerm = "";
      loadRows();
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
        });
      }
      resizeObserver.observe(containerEl);

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

<div class="virtual-grid" style="--grid-font-size: {gridFontSize}; --grid-font-weight: {gridFontWeight};">
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
      <div class="search-wrapper">
        <Search
          bind:value={searchTerm}
          on:clear={() => { searchTerm = ""; handleSearch(); }}
          on:input={handleSearch}
          placeholder="Search source, target, or StringID..."
          size="sm"
        />
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

    <!-- Table Header -->
    <!-- UI-043/UI-044: Source and Target columns with resizable divider -->
    <div class="table-header">
      {#each visibleColumns as col}
        {#if col.key === 'source'}
          <div class="th th-source" style="flex: 0 0 {sourceWidthPercent}%;">
            {col.label}
            <!-- Resize handle -->
            <div
              class="resize-handle"
              onmousedown={startResize}
              role="separator"
              aria-label="Resize columns"
            ></div>
          </div>
        {:else if col.key === 'target'}
          <div class="th th-target" style="flex: 0 0 {100 - sourceWidthPercent}%;">
            {col.label}
          </div>
        {:else}
          <div class="th" style="flex: 0 0 {col.width}px;">
            {col.label}
          </div>
        {/if}
      {/each}
    </div>

    <!-- Virtual Scroll Container -->
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
            {@const rowTop = getRowTop(visibleStart + i)}
            {@const rowHeight = estimateRowHeight(row)}
            {@const rowLock = $ldmConnected && row.id ? isRowLocked(parseInt(row.id)) : null}
            <!-- svelte-ignore a11y_click_events_have_key_events -->
            <div
              class="virtual-row"
              class:placeholder={row.placeholder}
              class:locked={rowLock}
              class:selected={selectedRowId === row.id}
              style="top: {rowTop}px; min-height: {rowHeight}px;"
              onclick={(e) => handleCellClick(row, e)}
              role="row"
            >
              {#if row.placeholder}
                <div class="cell" style="width: {visibleColumns[0]?.width || 60}px;">{row.row_num}</div>
                <div class="cell loading-cell" style="flex: 1;">
                  <!-- PERF: Static placeholder instead of animated InlineLoading -->
                  <div class="placeholder-shimmer"></div>
                </div>
              {:else}
                <!-- Row number (conditional) -->
                {#if $preferences.showIndex}
                  <div class="cell row-num" style="width: {allColumns.row_num.width}px;">
                    {row.row_num}
                  </div>
                {/if}

                <!-- StringID (conditional) -->
                {#if $preferences.showStringId}
                  <div class="cell string-id" style="width: {allColumns.string_id.width}px;">
                    {row.string_id || "-"}
                  </div>
                {/if}

                <!-- Source (always visible, full content with newline symbols) -->
                <!-- UI-044: Uses percentage width matching header -->
                <div
                  class="cell source"
                  class:cell-hover={selectedRowId === row.id}
                  style="flex: 0 0 {sourceWidthPercent}%;"
                >
                  <span class="cell-content">{formatGridText(row.source) || ""}</span>
                </div>

                <!-- Target (always visible, editable, full content with newline symbols) -->
                <!-- Cell color indicates status: default=pending, translated=teal, confirmed=green -->
                <!-- UI-044: Uses percentage width matching header -->
                <!-- P2: QA flag shown when qa_flag_count > 0 -->
                <div
                  class="cell target"
                  class:locked={rowLock}
                  class:cell-hover={selectedRowId === row.id}
                  class:status-translated={row.status === 'translated'}
                  class:status-reviewed={row.status === 'reviewed'}
                  class:status-approved={row.status === 'approved'}
                  class:qa-flagged={row.qa_flag_count > 0}
                  style="flex: 0 0 {100 - sourceWidthPercent}%;"
                  ondblclick={() => openEditModal(row)}
                  role="button"
                  tabindex="0"
                  onkeydown={(e) => e.key === 'Enter' && openEditModal(row)}
                >
                  <span class="cell-content">{formatGridText(row.target) || ""}</span>
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
                </div>

                <!-- Reference Column (conditional - Phase 8) -->
                {#if $preferences.showReference}
                  {@const refText = getReferenceForRow(row, $preferences.referenceMatchMode)}
                  <div
                    class="cell reference"
                    class:has-match={refText}
                    class:no-match={!refText}
                    style="width: {allColumns.reference.width}px;"
                    title={refText ? `Reference: ${refText}` : 'No reference match'}
                  >
                    {#if referenceLoading}
                      <span class="cell-loading">Loading...</span>
                    {:else if refText}
                      <span class="cell-content ref-match">{formatGridText(refText)}</span>
                    {:else}
                      <span class="cell-content no-match">-</span>
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
</div>

<!-- Edit Modal - BIG, Clean, Space-Optimized -->
{#if showEditModal && editingRow}
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="edit-modal-overlay" onclick={closeEditModal} role="presentation">
    <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
    <div class="edit-modal" role="dialog" tabindex="-1" onclick={(e) => e.stopPropagation()} onkeydown={handleEditKeydown}>
      <!-- Shortcut bar at top -->
      <div class="shortcut-bar">
        <div class="shortcuts">
          <span class="shortcut"><kbd>Ctrl+S</kbd> Confirm (Reviewed)</span>
          <span class="shortcut"><kbd>Ctrl+T</kbd> Translate Only</span>
          <span class="shortcut"><kbd>Tab</kbd> Apply TM</span>
          <span class="shortcut"><kbd>Esc</kbd> Cancel</span>
        </div>
        <button class="close-btn" type="button" onclick={closeEditModal} title="Close (Esc)">×</button>
      </div>

      <!-- Two-column layout -->
      <div class="edit-content">
        <!-- Left column: Source + Target -->
        <div class="edit-left">
          <div class="source-section">
            <span class="section-label">SOURCE (Korean)</span>
            <div class="source-text">{formatGridText(editingRow.source) || "-"}</div>
          </div>

          <div class="target-section">
            <label class="section-label" for="target-edit-textarea">TARGET (Translation)</label>
            <textarea
              id="target-edit-textarea"
              class="target-textarea"
              bind:value={editTarget}
              placeholder="Enter translation..."
            ></textarea>
          </div>
        </div>

        <!-- Right column: TM Suggestions -->
        <div class="edit-right">
          <!-- P2: QA Results Panel (shown when issues exist) -->
          {#if lastQaResult && lastQaResult.issue_count > 0}
            <div class="qa-section">
              <div class="qa-header-bar">
                <span class="section-label qa-label">
                  <WarningAltFilled size={14} />
                  QA ISSUES ({lastQaResult.issue_count})
                </span>
                {#if qaLoading}
                  <InlineLoading description="" />
                {/if}
              </div>
              <div class="qa-list">
                {#each lastQaResult.issues as issue}
                  <div class="qa-item" class:error={issue.severity === 'error'} class:warning={issue.severity === 'warning'}>
                    <div class="qa-item-header">
                      <Tag type={issue.severity === 'error' ? 'red' : 'magenta'} size="sm">
                        {issue.check_type}
                      </Tag>
                    </div>
                    <div class="qa-item-message">{issue.message}</div>
                  </div>
                {/each}
                <button
                  class="qa-dismiss-btn"
                  type="button"
                  onclick={() => { lastQaResult = null; closeEditModal(); }}
                >
                  Dismiss & Close
                </button>
              </div>
            </div>
          {/if}

          <!-- TM Matches Section -->
          <div class="tm-section">
            <div class="tm-header-bar">
              <span class="section-label">TM MATCHES</span>
              {#if tmLoading}
                <InlineLoading description="" />
              {/if}
            </div>

            <div class="tm-list">
              {#if tmSuggestions.length > 0}
                {#each tmSuggestions as suggestion, idx}
                  <button
                    class="tm-item"
                    onclick={() => applyTMSuggestion(suggestion)}
                    title="Click to apply (Tab = apply first)"
                  >
                    <div class="tm-item-header">
                      <Tag type="teal" size="sm">{Math.round(suggestion.similarity * 100)}%</Tag>
                      {#if idx === 0}<span class="tm-hint">Tab</span>{/if}
                    </div>
                    <div class="tm-item-source">{suggestion.source}</div>
                    <div class="tm-item-target">{suggestion.target}</div>
                  </button>
                {/each}
              {:else if !tmLoading}
                <div class="tm-empty-msg">No similar translations found</div>
              {/if}
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
{/if}

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
    padding: 0.75rem 1rem;
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
  }

  .filter-wrapper :global(.bx--list-box__field) {
    height: 2rem;
  }

  .table-header {
    display: flex;
    background: var(--cds-layer-accent-01);
    border-bottom: 2px solid var(--cds-border-strong-01);
    font-weight: 600;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .th {
    padding: 0.75rem 0.5rem;
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

  /* UI-044: Source column header has visible right border and resize handle */
  .th-source {
    position: relative;
    border-right: 2px solid var(--cds-border-strong-01, #525252);
  }

  .th-target {
    /* Target header - no special border needed */
  }

  /* UI-044: Resize handle for column resizing */
  .resize-handle {
    position: absolute;
    right: -4px;
    top: 0;
    bottom: 0;
    width: 8px;
    cursor: col-resize;
    background: transparent;
    z-index: 10;
    transition: background-color 0.2s;
  }

  .resize-handle:hover,
  .resize-handle:active {
    background: var(--cds-interactive-01, #0f62fe);
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
    border-bottom: 1px solid var(--cds-border-subtle-01);
    background: var(--cds-layer-01);
    transition: background-color 0.15s ease;
  }

  .virtual-row:hover {
    background: var(--cds-layer-hover-01);
  }

  .virtual-row.selected {
    background: var(--cds-layer-selected-01);
  }

  .virtual-row.placeholder {
    opacity: 0.5;
  }

  .virtual-row.locked {
    background: var(--cds-layer-02);
  }

  .cell {
    padding: 0.5rem;
    font-size: var(--grid-font-size, 14px);
    font-weight: var(--grid-font-weight, 400);
    border-right: 1px solid var(--cds-border-subtle-01);
    display: flex;
    align-items: flex-start;
    overflow: hidden;
    min-width: 0;
    /* Allow cells to expand with content up to max-height */
    max-height: 200px;
    overflow-y: auto;
  }

  /* UI-044: Source and Target cells use percentage widths (set via inline style) */
  /* flex is controlled by inline style, no default flex here */

  .cell-content {
    word-break: break-word;
    white-space: pre-wrap;
    line-height: 1.4;
  }

  .cell.row-num {
    justify-content: center;
    align-items: center;
    color: var(--cds-text-02);
    font-size: 0.75rem;
    flex: 0 0 60px;
  }

  .cell.string-id {
    font-family: monospace;
    font-size: 0.75rem;
    word-break: break-all;
    flex: 0 0 150px;
  }

  .cell.source {
    background: var(--cds-layer-02);
    color: var(--cds-text-02);
    transition: background-color 0.15s ease;
    /* UI-044: Add visible right border to separate from target */
    border-right: 2px solid var(--cds-border-strong-01, #525252);
  }

  /* UI-057 FIX: Add hover state to source cell (SAME as target: hover-01) */
  .cell.source:hover,
  .cell.source.cell-hover {
    background: var(--cds-layer-hover-01);
  }

  .cell.target {
    position: relative;
    cursor: pointer;
    padding-right: 1.5rem;
    transition: background-color 0.15s ease;
  }

  .cell.target:hover {
    background: var(--cds-layer-hover-01);
  }

  .cell.target.cell-hover {
    background: var(--cds-layer-selected-01);
  }

  .cell.target.locked {
    cursor: not-allowed;
    background: var(--cds-layer-02);
  }

  /* Status-based cell colors (replaces Status column) */
  .cell.target.status-translated {
    background: rgba(0, 157, 154, 0.15); /* teal - translated */
    border-left: 3px solid var(--cds-support-04);
  }

  .cell.target.status-reviewed {
    background: rgba(15, 98, 254, 0.15); /* blue - reviewed */
    border-left: 3px solid var(--cds-support-01);
  }

  .cell.target.status-approved {
    background: rgba(36, 161, 72, 0.15); /* green - approved/confirmed */
    border-left: 3px solid var(--cds-support-02);
  }

  /* Status hover overrides for colored cells */
  .cell.target.status-translated:hover,
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
    right: 1.5rem;
    color: var(--cds-support-01, #da1e28);
    opacity: 1;
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
    flex: 0 0 300px;
  }

  .cell.reference.has-match {
    background: rgba(36, 161, 72, 0.08);
    border-left: 2px solid var(--cds-support-02);
  }

  .cell.reference .ref-match {
    color: var(--cds-text-01);
  }

  .cell.reference .no-match {
    color: var(--cds-text-03);
    font-style: italic;
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
     NEW EDIT MODAL - BIG, Clean, Spacious
     ======================================== */

  .edit-modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.6);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 10000;
    backdrop-filter: blur(2px);
  }

  .edit-modal {
    width: 85%;
    height: 85%;
    max-width: 1400px;
    max-height: 900px;
    background: var(--cds-layer-01);
    border-radius: 8px;
    display: flex;
    flex-direction: column;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    overflow: hidden;
  }

  /* Shortcut bar at top */
  .shortcut-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.5rem 1rem;
    background: var(--cds-layer-accent-01);
    border-bottom: 1px solid var(--cds-border-subtle-01);
  }

  .shortcuts {
    display: flex;
    gap: 1.5rem;
    flex-wrap: wrap;
  }

  .shortcut {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.75rem;
    color: var(--cds-text-02);
  }

  .shortcut kbd {
    background: var(--cds-layer-02);
    border: 1px solid var(--cds-border-strong-01);
    border-radius: 3px;
    padding: 0.15rem 0.4rem;
    font-family: monospace;
    font-size: 0.7rem;
    color: var(--cds-text-01);
  }

  .close-btn {
    background: transparent;
    border: none;
    font-size: 1.5rem;
    pointer-events: auto;
    z-index: 100;
    position: relative;
    color: var(--cds-text-02);
    cursor: pointer;
    width: 2rem;
    height: 2rem;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 4px;
    transition: background 0.15s, color 0.15s;
  }

  .close-btn:hover {
    background: var(--cds-layer-hover-01);
    color: var(--cds-text-01);
  }

  /* Two-column layout */
  .edit-content {
    display: flex;
    flex: 1;
    overflow: hidden;
  }

  .edit-left {
    flex: 1;
    display: flex;
    flex-direction: column;
    padding: 1rem;
    gap: 1rem;
    overflow: hidden;
  }

  .edit-right {
    width: 320px;
    min-width: 280px;
    border-left: 1px solid var(--cds-border-subtle-01);
    background: var(--cds-layer-02);
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  /* Section labels */
  .section-label {
    display: block;
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--cds-text-02);
    margin-bottom: 0.5rem;
  }

  /* Source section */
  .source-section {
    flex: 0 0 auto;
    max-height: 40%;
    display: flex;
    flex-direction: column;
  }

  .source-text {
    flex: 1;
    background: var(--cds-layer-02);
    padding: 1rem;
    border-radius: 4px;
    font-size: 0.9375rem;
    line-height: 1.5;
    color: var(--cds-text-02);
    white-space: pre-wrap;
    overflow-y: auto;
    border: 1px solid var(--cds-border-subtle-01);
  }

  /* Target section */
  .target-section {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
  }

  .target-textarea {
    flex: 1;
    width: 100%;
    padding: 1rem;
    border: 2px solid var(--cds-border-strong-01);
    border-radius: 4px;
    background: var(--cds-field-01);
    color: var(--cds-text-01);
    font-size: 0.9375rem;
    line-height: 1.5;
    resize: none;
    font-family: inherit;
  }

  .target-textarea:focus {
    outline: none;
    border-color: var(--cds-interactive-01);
    box-shadow: 0 0 0 1px var(--cds-interactive-01);
  }

  .target-textarea::placeholder {
    color: var(--cds-text-placeholder);
  }

  /* TM section (right column) */
  .tm-section {
    display: flex;
    flex-direction: column;
    height: 100%;
    overflow: hidden;
  }

  .tm-header-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.75rem 1rem;
    border-bottom: 1px solid var(--cds-border-subtle-01);
    background: var(--cds-layer-accent-01);
  }

  .tm-list {
    flex: 1;
    overflow-y: auto;
    padding: 0.5rem;
  }

  .tm-item {
    display: block;
    width: 100%;
    padding: 0.75rem;
    margin-bottom: 0.5rem;
    border: 1px solid var(--cds-border-subtle-01);
    border-radius: 4px;
    background: var(--cds-layer-01);
    text-align: left;
    cursor: pointer;
    transition: background 0.15s, border-color 0.15s, transform 0.1s;
  }

  .tm-item:hover {
    background: var(--cds-layer-hover-01);
    border-color: var(--cds-border-interactive);
    transform: translateY(-1px);
  }

  .tm-item:active {
    transform: translateY(0);
  }

  .tm-item-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.5rem;
  }

  .tm-hint {
    font-size: 0.625rem;
    color: var(--cds-text-02);
    background: var(--cds-layer-02);
    padding: 0.1rem 0.3rem;
    border-radius: 2px;
    font-family: monospace;
  }

  .tm-item-source {
    font-size: 0.75rem;
    color: var(--cds-text-02);
    margin-bottom: 0.25rem;
    line-height: 1.4;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .tm-item-target {
    font-size: 0.8125rem;
    color: var(--cds-text-01);
    line-height: 1.4;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .tm-empty-msg {
    padding: 2rem 1rem;
    text-align: center;
    color: var(--cds-text-02);
    font-size: 0.8125rem;
    font-style: italic;
  }

  /* P2: QA Panel Styles */
  .qa-section {
    display: flex;
    flex-direction: column;
    border-bottom: 1px solid var(--cds-border-subtle-01);
    background: rgba(218, 30, 40, 0.05);
  }

  .qa-header-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.75rem 1rem;
    background: rgba(218, 30, 40, 0.12);
    border-bottom: 1px solid rgba(218, 30, 40, 0.2);
  }

  .qa-label {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    color: var(--cds-support-01, #da1e28);
  }

  .qa-list {
    padding: 0.5rem;
    max-height: 200px;
    overflow-y: auto;
  }

  .qa-item {
    padding: 0.5rem 0.75rem;
    margin-bottom: 0.5rem;
    border-radius: 4px;
    background: var(--cds-layer-01);
    border-left: 3px solid var(--cds-support-01, #da1e28);
  }

  .qa-item.warning {
    border-left-color: var(--cds-support-03, #f1c21b);
  }

  .qa-item-header {
    margin-bottom: 0.25rem;
  }

  .qa-item-message {
    font-size: 0.8125rem;
    color: var(--cds-text-01);
    line-height: 1.4;
  }

  .qa-dismiss-btn {
    width: 100%;
    padding: 0.5rem;
    margin-top: 0.5rem;
    border: 1px solid var(--cds-border-strong-01);
    border-radius: 4px;
    background: var(--cds-layer-01);
    color: var(--cds-text-01);
    font-size: 0.8125rem;
    cursor: pointer;
    transition: background 0.15s;
  }

  .qa-dismiss-btn:hover {
    background: var(--cds-layer-hover-01);
  }
</style>
