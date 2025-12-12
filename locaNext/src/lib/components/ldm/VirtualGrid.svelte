<script>
  import {
    Search,
    InlineLoading,
    Tag
  } from "carbon-components-svelte";
  import { Edit, Locked } from "carbon-icons-svelte";
  import { createEventDispatcher, onMount, onDestroy, tick } from "svelte";
  import { logger } from "$lib/utils/logger.js";
  import { ldmStore, joinFile, leaveFile, lockRow, unlockRow, isRowLocked, onCellUpdate, ldmConnected } from "$lib/stores/ldm.js";
  import { preferences } from "$lib/stores/preferences.js";
  import PresenceBar from "./PresenceBar.svelte";

  const dispatch = createEventDispatcher();

  // API base URL
  const API_BASE = 'http://localhost:8888';

  // Props
  export let fileId = null;
  export let fileName = "";

  // Virtual scrolling constants
  const MIN_ROW_HEIGHT = 48; // Minimum row height
  const MAX_ROW_HEIGHT = 120; // Maximum row height (prevents huge rows)
  const CHARS_PER_LINE = 50; // Estimated chars per line for height calc
  const LINE_HEIGHT = 20; // Height per line of text
  const BUFFER_ROWS = 10; // Extra rows to render above/below viewport
  const PAGE_SIZE = 100; // Rows per page to fetch

  // Real-time subscription
  let cellUpdateUnsubscribe = null;

  // State
  let loading = false;
  let initialLoading = true;
  let rows = []; // Cached rows (sparse array by row_num)
  let total = 0;
  let searchTerm = "";
  let searchDebounceTimer = null;

  // Virtual scroll state
  let containerEl;
  let scrollTop = 0;
  let containerHeight = 400;
  let visibleStart = 0;
  let visibleEnd = 50;

  // Page cache - track which pages we've loaded
  let loadedPages = new Set();
  let loadingPages = new Set();

  // Go to row state - REMOVED (BUG-001 - not useful)

  // Edit modal state
  let showEditModal = false;
  let editingRow = null;
  let editTarget = "";
  let editStatus = "";

  // Selected row state
  let selectedRowId = null;

  // TM suggestions state
  let tmSuggestions = [];
  let tmLoading = false;

  // Table column definitions (widths will be calculated dynamically)
  // Note: Status column REMOVED - using cell colors instead
  const allColumns = {
    row_num: { key: "row_num", label: "#", width: 60, prefKey: "showIndex" },
    string_id: { key: "string_id", label: "StringID", width: 150, prefKey: "showStringId" },
    source: { key: "source", label: "Source (KR)", width: 350, always: true },
    target: { key: "target", label: "Target", width: 350, always: true }
  };

  // Reactive: visible columns based on preferences
  $: visibleColumns = getVisibleColumns($preferences);

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

  // Calculate which rows are visible (with dynamic heights)
  function calculateVisibleRange() {
    if (!containerEl) return;

    containerHeight = containerEl.clientHeight;
    scrollTop = containerEl.scrollTop;

    // Use average height for estimation
    const loadedRows = rows.filter(r => r && !r.placeholder);
    const avgHeight = loadedRows.length > 0
      ? loadedRows.reduce((sum, r) => sum + estimateRowHeight(r), 0) / loadedRows.length
      : MIN_ROW_HEIGHT;

    const startRow = Math.floor(scrollTop / avgHeight);
    const endRow = Math.ceil((scrollTop + containerHeight) / avgHeight);

    visibleStart = Math.max(0, startRow - BUFFER_ROWS);
    visibleEnd = Math.min(total, endRow + BUFFER_ROWS);

    // Check if we need to load more data
    ensureRowsLoaded(visibleStart, visibleEnd);
  }

  // Ensure rows in range are loaded
  async function ensureRowsLoaded(start, end) {
    const startPage = Math.floor(start / PAGE_SIZE) + 1;
    const endPage = Math.floor(end / PAGE_SIZE) + 1;

    for (let page = startPage; page <= endPage; page++) {
      if (!loadedPages.has(page) && !loadingPages.has(page)) {
        await loadPage(page);
      }
    }
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

      const response = await fetch(`${API_BASE}/api/ldm/files/${fileId}/rows?${params}`, {
        headers: getAuthHeaders()
      });

      if (response.ok) {
        const data = await response.json();
        total = data.total;

        // Store rows by their row_num for sparse array access
        data.rows.forEach(row => {
          rows[row.row_num - 1] = {
            ...row,
            id: row.id.toString()
          };
        });

        // Force reactivity
        rows = [...rows];

        loadedPages.add(page);
        logger.info("Loaded page", { page, count: data.rows.length, total });
      }
    } catch (err) {
      logger.error("Failed to load page", { page, error: err.message });
    } finally {
      loadingPages.delete(page);
      loading = loadingPages.size > 0;
      initialLoading = false;
    }
  }

  // Initial load
  export async function loadRows() {
    if (!fileId) return;

    // Reset state
    rows = [];
    loadedPages.clear();
    loadingPages.clear();
    total = 0;
    initialLoading = true;

    // First, get the total count
    try {
      const response = await fetch(`${API_BASE}/api/ldm/files/${fileId}/rows?page=1&limit=1`, {
        headers: getAuthHeaders()
      });
      if (response.ok) {
        const data = await response.json();
        total = data.total;
        logger.info("Got total rows", { total });
      }
    } catch (err) {
      logger.error("Failed to get total", { error: err.message });
    }

    // Load first page
    await loadPage(1);

    // Calculate visible range after initial load
    await tick();
    calculateVisibleRange();
  }

  // Handle scroll
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

    // TODO: Row locking temporarily disabled - WebSocket event delivery issue
    // See ISSUES_TO_FIX.md for details
    // The ldm_lock_row event is not being received by the server
    // if (fileId) {
    //   const granted = await lockRow(fileId, parseInt(row.id));
    //   if (!granted) {
    //     logger.warning("Could not acquire lock", { rowId: row.id });
    //     alert("Could not acquire lock. Row may be in use.");
    //     return;
    //   }
    // }

    editingRow = row;
    // Format target for editing (convert escapes to real newlines)
    editTarget = formatGridText(row.target || "");
    editStatus = row.status || "pending";
    showEditModal = true;
    logger.userAction("Edit modal opened", { rowId: row.id });

    // Fetch TM suggestions in background
    fetchTMSuggestions(row.source, row.id);
  }

  // Close edit modal and release lock
  function closeEditModal() {
    if (editingRow && fileId) {
      unlockRow(fileId, parseInt(editingRow.id));
    }
    showEditModal = false;
    editingRow = null;
    tmSuggestions = [];
    tmLoading = false;
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
  function handleCellUpdates(updates) {
    updates.forEach(update => {
      // Find and update the row in our cache
      const rowIndex = rows.findIndex(r => r && parseInt(r.id) === update.row_id);
      if (rowIndex >= 0) {
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

  // Calculate cumulative heights for virtual scroll positioning
  function getRowTop(index) {
    let top = 0;
    for (let i = 0; i < index; i++) {
      const row = rows[i];
      top += estimateRowHeight(row);
    }
    return top;
  }

  // Calculate total content height
  function getTotalHeight() {
    // For performance, use average height estimation
    const loadedRowCount = rows.filter(r => r && !r.placeholder).length;
    if (loadedRowCount === 0) return total * MIN_ROW_HEIGHT;

    let totalLoadedHeight = 0;
    rows.forEach(row => {
      if (row && !row.placeholder) {
        totalLoadedHeight += estimateRowHeight(row);
      }
    });

    const avgHeight = totalLoadedHeight / loadedRowCount;
    return total * avgHeight;
  }

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

  // Get visible rows for rendering
  $: visibleRows = Array.from({ length: visibleEnd - visibleStart }, (_, i) => {
    const index = visibleStart + i;
    return rows[index] || { row_num: index + 1, placeholder: true };
  });

  // Total scroll height (reactive to rows changes)
  $: totalHeight = getTotalHeight();

  // Subscribe to real-time updates when file changes
  $: if (fileId) {
    joinFile(fileId);
    if (cellUpdateUnsubscribe) {
      cellUpdateUnsubscribe();
    }
    cellUpdateUnsubscribe = onCellUpdate(handleCellUpdates);
  }

  // Watch file changes
  $: if (fileId) {
    searchTerm = "";
    loadRows();
  }

  // Setup scroll listener on mount
  onMount(() => {
    if (containerEl) {
      containerEl.addEventListener('scroll', handleScroll);
      calculateVisibleRange();
    }
  });

  // Cleanup on destroy
  onDestroy(() => {
    if (fileId) {
      leaveFile(fileId);
    }
    if (cellUpdateUnsubscribe) {
      cellUpdateUnsubscribe();
    }
    if (containerEl) {
      containerEl.removeEventListener('scroll', handleScroll);
    }
    if (searchDebounceTimer) {
      clearTimeout(searchDebounceTimer);
    }
  });
</script>

<div class="virtual-grid">
  {#if fileId}
    <div class="grid-header">
      <div class="header-left">
        <h4>{fileName || `File #${fileId}`}</h4>
        <span class="row-count">{total.toLocaleString()} rows</span>
      </div>
      <div class="header-right">
        <PresenceBar />
      </div>
    </div>

    <div class="search-bar">
      <Search
        bind:value={searchTerm}
        on:clear={() => { searchTerm = ""; handleSearch(); }}
        on:input={handleSearch}
        placeholder="Search source, target, or StringID... (Press Enter)"
        size="sm"
      />
    </div>

    <!-- Table Header -->
    <div class="table-header">
      {#each visibleColumns as col}
        <div class="th" style="width: {col.width}px; min-width: {col.width}px;">
          {col.label}
        </div>
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
            <!-- svelte-ignore a11y-click-events-have-key-events -->
            <div
              class="virtual-row"
              class:placeholder={row.placeholder}
              class:locked={rowLock}
              class:selected={selectedRowId === row.id}
              style="top: {rowTop}px; min-height: {rowHeight}px;"
              on:click={(e) => handleCellClick(row, e)}
              role="row"
            >
              {#if row.placeholder}
                <div class="cell" style="width: {visibleColumns[0]?.width || 60}px;">{row.row_num}</div>
                <div class="cell loading-cell" style="flex: 1;">
                  <InlineLoading description="" />
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
                <div
                  class="cell source"
                  class:cell-hover={selectedRowId === row.id}
                  style="width: {allColumns.source.width}px;"
                >
                  <span class="cell-content">{formatGridText(row.source) || ""}</span>
                </div>

                <!-- Target (always visible, editable, full content with newline symbols) -->
                <!-- Cell color indicates status: default=pending, translated=teal, confirmed=green -->
                <div
                  class="cell target"
                  class:locked={rowLock}
                  class:cell-hover={selectedRowId === row.id}
                  class:status-translated={row.status === 'translated'}
                  class:status-reviewed={row.status === 'reviewed'}
                  class:status-approved={row.status === 'approved'}
                  style="width: {allColumns.target.width}px;"
                  on:dblclick={() => openEditModal(row)}
                  role="button"
                  tabindex="0"
                  on:keydown={(e) => e.key === 'Enter' && openEditModal(row)}
                >
                  <span class="cell-content">{formatGridText(row.target) || ""}</span>
                  {#if rowLock}
                    <span class="lock-icon"><Locked size={12} /></span>
                  {:else}
                    <span class="edit-icon"><Edit size={12} /></span>
                  {/if}
                </div>
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

    <div class="grid-footer">
      <span>Showing rows {visibleStart + 1} - {Math.min(visibleEnd, total)} of {total.toLocaleString()}</span>
    </div>
  {:else}
    <div class="empty-state">
      <p>Select a file from the explorer to view its contents</p>
    </div>
  {/if}
</div>

<!-- Edit Modal - BIG, Clean, Space-Optimized -->
{#if showEditModal && editingRow}
  <!-- svelte-ignore a11y-click-events-have-key-events -->
  <!-- svelte-ignore a11y-no-static-element-interactions -->
  <div class="edit-modal-overlay" on:click={closeEditModal}>
    <!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
    <div class="edit-modal" role="dialog" on:click|stopPropagation on:keydown={handleEditKeydown}>
      <!-- Shortcut bar at top -->
      <div class="shortcut-bar">
        <div class="shortcuts">
          <span class="shortcut"><kbd>Ctrl+S</kbd> Confirm (Reviewed)</span>
          <span class="shortcut"><kbd>Ctrl+T</kbd> Translate Only</span>
          <span class="shortcut"><kbd>Tab</kbd> Apply TM</span>
          <span class="shortcut"><kbd>Esc</kbd> Cancel</span>
        </div>
        <button class="close-btn" on:click={closeEditModal} title="Close (Esc)">×</button>
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
                    on:click={() => applyTMSuggestion(suggestion)}
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

  /* Search bar - always expanded, clean styling */
  .search-bar {
    padding: 0.5rem 1rem;
    background: var(--cds-layer-01);
    border-bottom: 1px solid var(--cds-border-subtle-01);
  }

  .search-bar :global(.bx--search) {
    background: var(--cds-field-01);
  }

  .search-bar :global(.bx--search-input) {
    background: var(--cds-field-01);
    border-bottom: 1px solid var(--cds-border-strong-01);
  }

  .search-bar :global(.bx--search-input:focus) {
    border-bottom: 2px solid var(--cds-interactive-01);
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

  .scroll-container {
    flex: 1;
    overflow-y: auto;
    overflow-x: hidden;
    position: relative;
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
    transition: background-color 0.15s ease, box-shadow 0.15s ease;
  }

  .virtual-row:hover {
    background: var(--cds-layer-hover-01);
    box-shadow: inset 0 0 0 1px var(--cds-border-interactive);
  }

  .virtual-row.selected {
    background: var(--cds-layer-selected-01);
    box-shadow: inset 0 0 0 2px var(--cds-border-interactive);
  }

  .virtual-row.placeholder {
    opacity: 0.5;
  }

  .virtual-row.locked {
    background: var(--cds-layer-02);
  }

  .cell {
    padding: 0.5rem;
    font-size: 0.8125rem;
    border-right: 1px solid var(--cds-border-subtle-01);
    display: flex;
    align-items: flex-start;
    overflow: hidden;
  }

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
  }

  .cell.string-id {
    font-family: monospace;
    font-size: 0.75rem;
    word-break: break-all;
  }

  .cell.source {
    background: var(--cds-layer-02);
    color: var(--cds-text-02);
    transition: background-color 0.15s ease, box-shadow 0.15s ease;
  }

  .cell.source.cell-hover {
    background: var(--cds-layer-hover-02);
    box-shadow: inset 0 0 0 2px var(--cds-border-interactive);
  }

  .cell.target {
    position: relative;
    cursor: pointer;
    padding-right: 1.5rem;
    transition: background-color 0.15s ease, box-shadow 0.15s ease;
  }

  .cell.target:hover {
    background: var(--cds-layer-hover-01);
  }

  .cell.target.cell-hover {
    background: var(--cds-layer-selected-01);
    box-shadow: inset 0 0 0 2px var(--cds-border-interactive);
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

  .loading-cell {
    justify-content: center;
  }

  .loading-bar {
    padding: 0.25rem 1rem;
    background: var(--cds-layer-02);
    border-top: 1px solid var(--cds-border-subtle-01);
  }

  .grid-footer {
    padding: 0.5rem 1rem;
    background: var(--cds-layer-01);
    border-top: 1px solid var(--cds-border-subtle-01);
    font-size: 0.75rem;
    color: var(--cds-text-02);
  }

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
</style>
