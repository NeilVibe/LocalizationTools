<script>
  import {
    Toolbar,
    ToolbarContent,
    ToolbarSearch,
    InlineLoading,
    Tag,
    Button,
    Modal,
    TextArea,
    Select,
    SelectItem,
    TextInput,
    NumberInput
  } from "carbon-components-svelte";
  import { Edit, Locked, ArrowRight, Search } from "carbon-icons-svelte";
  import { createEventDispatcher, onMount, onDestroy, tick } from "svelte";
  import { logger } from "$lib/utils/logger.js";
  import { ldmStore, joinFile, leaveFile, lockRow, unlockRow, isRowLocked, onCellUpdate } from "$lib/stores/ldm.js";
  import PresenceBar from "./PresenceBar.svelte";

  const dispatch = createEventDispatcher();

  // API base URL
  const API_BASE = 'http://localhost:8888';

  // Props
  export let fileId = null;
  export let fileName = "";

  // Virtual scrolling constants
  const ROW_HEIGHT = 40; // Fixed row height in pixels
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

  // Go to row state
  let showGoToRow = false;
  let goToRowNumber = 1;

  // Edit modal state
  let showEditModal = false;
  let editingRow = null;
  let editTarget = "";
  let editStatus = "";

  // TM suggestions state
  let tmSuggestions = [];
  let tmLoading = false;

  // Table column widths
  const columns = [
    { key: "row_num", label: "#", width: 60 },
    { key: "string_id", label: "StringID", width: 150 },
    { key: "source", label: "Source (KR)", width: 300 },
    { key: "target", label: "Target", width: 300 },
    { key: "status", label: "Status", width: 100 }
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

  // Calculate which rows are visible
  function calculateVisibleRange() {
    if (!containerEl) return;

    containerHeight = containerEl.clientHeight;
    scrollTop = containerEl.scrollTop;

    const startRow = Math.floor(scrollTop / ROW_HEIGHT);
    const endRow = Math.ceil((scrollTop + containerHeight) / ROW_HEIGHT);

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

  // Go to specific row
  async function goToRow() {
    if (goToRowNumber < 1 || goToRowNumber > total) {
      logger.warning("Invalid row number", { rowNumber: goToRowNumber, total });
      return;
    }

    // Scroll to row position
    const scrollPosition = (goToRowNumber - 1) * ROW_HEIGHT;
    if (containerEl) {
      containerEl.scrollTop = scrollPosition;
    }

    showGoToRow = false;
    logger.userAction("Go to row", { rowNumber: goToRowNumber });
  }

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
    if (lock) {
      logger.warning("Row locked by another user", { rowId: row.id, lockedBy: lock.locked_by });
      alert(`This row is being edited by ${lock.locked_by}`);
      return;
    }

    // Request lock before opening modal
    if (fileId) {
      const granted = await lockRow(fileId, parseInt(row.id));
      if (!granted) {
        logger.warning("Could not acquire lock", { rowId: row.id });
        alert("Could not acquire lock. Row may be in use.");
        return;
      }
    }

    editingRow = row;
    editTarget = row.target || "";
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
    // Ctrl+Enter: Save and next
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
      const response = await fetch(`${API_BASE}/api/ldm/rows/${rowId}`, {
        method: 'PUT',
        headers: {
          ...getAuthHeaders(),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          target: editTarget,
          status: editStatus
        })
      });

      if (response.ok) {
        // Update local cache
        const rowIndex = editingRow.row_num - 1;
        if (rows[rowIndex]) {
          rows[rowIndex] = {
            ...rows[rowIndex],
            target: editTarget,
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

  // Get visible rows for rendering
  $: visibleRows = Array.from({ length: visibleEnd - visibleStart }, (_, i) => {
    const index = visibleStart + i;
    return rows[index] || { row_num: index + 1, placeholder: true };
  });

  // Total scroll height
  $: totalHeight = total * ROW_HEIGHT;

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
        <Button
          size="small"
          kind="ghost"
          icon={ArrowRight}
          iconDescription="Go to row"
          on:click={() => showGoToRow = !showGoToRow}
        >
          Go to row
        </Button>
        <PresenceBar />
      </div>
    </div>

    {#if showGoToRow}
      <div class="go-to-row-bar">
        <NumberInput
          bind:value={goToRowNumber}
          min={1}
          max={total}
          size="sm"
          label="Row number"
          hideLabel
        />
        <Button size="small" on:click={goToRow}>Go</Button>
        <span class="go-to-hint">1 - {total.toLocaleString()}</span>
      </div>
    {/if}

    <Toolbar>
      <ToolbarContent>
        <ToolbarSearch
          bind:value={searchTerm}
          on:clear={() => { searchTerm = ""; handleSearch(); }}
          on:input={handleSearch}
          placeholder="Search source, target, or StringID..."
        />
      </ToolbarContent>
    </Toolbar>

    <!-- Table Header -->
    <div class="table-header">
      {#each columns as col}
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
            {@const rowTop = (visibleStart + i) * ROW_HEIGHT}
            {@const rowLock = row.id ? isRowLocked(parseInt(row.id)) : null}
            <div
              class="virtual-row"
              class:placeholder={row.placeholder}
              class:locked={rowLock}
              style="top: {rowTop}px; height: {ROW_HEIGHT}px;"
            >
              {#if row.placeholder}
                <div class="cell" style="width: {columns[0].width}px;">{row.row_num}</div>
                <div class="cell loading-cell" style="flex: 1;">
                  <InlineLoading description="" />
                </div>
              {:else}
                <!-- Row number -->
                <div class="cell row-num" style="width: {columns[0].width}px;">
                  {row.row_num}
                </div>

                <!-- StringID -->
                <div class="cell string-id" style="width: {columns[1].width}px;" title={row.string_id}>
                  {row.string_id || "-"}
                </div>

                <!-- Source -->
                <div class="cell source" style="width: {columns[2].width}px;" title={row.source}>
                  {row.source || ""}
                </div>

                <!-- Target (editable) -->
                <div
                  class="cell target"
                  class:locked={rowLock}
                  style="width: {columns[3].width}px;"
                  on:dblclick={() => openEditModal(row)}
                  role="button"
                  tabindex="0"
                  on:keydown={(e) => e.key === 'Enter' && openEditModal(row)}
                  title={rowLock ? `Locked by ${rowLock.locked_by}` : "Double-click to edit"}
                >
                  {row.target || ""}
                  {#if rowLock}
                    <span class="lock-icon"><Locked size={12} /></span>
                  {:else}
                    <span class="edit-icon"><Edit size={12} /></span>
                  {/if}
                </div>

                <!-- Status -->
                <div class="cell status" style="width: {columns[4].width}px;">
                  <Tag type={getStatusKind(row.status)} size="sm">
                    {row.status || "pending"}
                  </Tag>
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

<!-- Edit Modal -->
<Modal
  bind:open={showEditModal}
  modalHeading="Edit Translation"
  primaryButtonText="Save"
  secondaryButtonText="Cancel"
  on:click:button--primary={saveEdit}
  on:click:button--secondary={closeEditModal}
  on:close={closeEditModal}
  size="lg"
>
  {#if editingRow}
    <!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
    <div class="edit-form" role="form" on:keydown={handleEditKeydown}>
      <div class="field">
        <label>StringID</label>
        <div class="readonly-value">{editingRow.string_id || "-"}</div>
      </div>

      <div class="field">
        <label>Source (Korean) - Read Only</label>
        <div class="source-preview">{editingRow.source || "-"}</div>
      </div>

      <TextArea
        bind:value={editTarget}
        labelText="Target (Translation)"
        placeholder="Enter translation..."
        rows={4}
      />

      <!-- TM Suggestions Panel -->
      <div class="tm-panel">
        <div class="tm-header">
          <span class="tm-title">Translation Memory</span>
          {#if tmLoading}
            <InlineLoading description="Searching..." />
          {/if}
        </div>

        {#if tmSuggestions.length > 0}
          <div class="tm-suggestions">
            {#each tmSuggestions as suggestion}
              <button
                class="tm-suggestion"
                on:click={() => applyTMSuggestion(suggestion)}
                title="Click to apply this translation"
              >
                <div class="tm-match">
                  <Tag type="teal" size="sm">{Math.round(suggestion.similarity * 100)}%</Tag>
                  <span class="tm-file">{suggestion.file_name}</span>
                </div>
                <div class="tm-source">{suggestion.source}</div>
                <div class="tm-target">{suggestion.target}</div>
              </button>
            {/each}
          </div>
        {:else if !tmLoading}
          <div class="tm-empty">No similar translations found</div>
        {/if}
      </div>

      <Select
        bind:selected={editStatus}
        labelText="Status"
      >
        {#each statusOptions as opt}
          <SelectItem value={opt.value} text={opt.label} />
        {/each}
      </Select>
    </div>
  {/if}
</Modal>

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

  .go-to-row-bar {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 1rem;
    background: var(--cds-layer-02);
    border-bottom: 1px solid var(--cds-border-subtle-01);
  }

  .go-to-hint {
    font-size: 0.75rem;
    color: var(--cds-text-02);
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
  }

  .virtual-row:hover {
    background: var(--cds-layer-hover-01);
  }

  .virtual-row.placeholder {
    opacity: 0.5;
  }

  .virtual-row.locked {
    background: var(--cds-layer-02);
  }

  .cell {
    padding: 0.5rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: 0.8125rem;
    border-right: 1px solid var(--cds-border-subtle-01);
    display: flex;
    align-items: center;
  }

  .cell.row-num {
    justify-content: center;
    color: var(--cds-text-02);
    font-size: 0.75rem;
  }

  .cell.string-id {
    font-family: monospace;
    font-size: 0.75rem;
  }

  .cell.source {
    background: var(--cds-layer-02);
    color: var(--cds-text-02);
  }

  .cell.target {
    position: relative;
    cursor: pointer;
    padding-right: 1.5rem;
  }

  .cell.target:hover {
    background: var(--cds-layer-hover-01);
  }

  .cell.target.locked {
    cursor: not-allowed;
    background: var(--cds-layer-02);
  }

  .edit-icon, .lock-icon {
    position: absolute;
    right: 0.25rem;
    opacity: 0;
    color: var(--cds-icon-02);
  }

  .cell.target:hover .edit-icon {
    opacity: 1;
  }

  .cell.target.locked .lock-icon {
    opacity: 0.8;
    color: var(--cds-support-03);
  }

  .cell.status {
    justify-content: center;
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

  .edit-form {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .field label {
    display: block;
    font-size: 0.75rem;
    color: var(--cds-text-02);
    margin-bottom: 0.25rem;
  }

  .readonly-value {
    font-size: 0.875rem;
    color: var(--cds-text-01);
  }

  .source-preview {
    background: var(--cds-layer-02);
    padding: 0.75rem;
    border-radius: 4px;
    color: var(--cds-text-02);
    font-size: 0.875rem;
    white-space: pre-wrap;
  }

  /* TM Panel Styles */
  .tm-panel {
    margin-top: 0.5rem;
    border: 1px solid var(--cds-border-subtle-01);
    border-radius: 4px;
    background: var(--cds-layer-02);
  }

  .tm-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.5rem 0.75rem;
    border-bottom: 1px solid var(--cds-border-subtle-01);
    background: var(--cds-layer-accent-01);
  }

  .tm-title {
    font-weight: 600;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--cds-text-02);
  }

  .tm-suggestions {
    max-height: 200px;
    overflow-y: auto;
  }

  .tm-suggestion {
    display: block;
    width: 100%;
    padding: 0.5rem 0.75rem;
    border: none;
    border-bottom: 1px solid var(--cds-border-subtle-01);
    background: transparent;
    text-align: left;
    cursor: pointer;
    transition: background 0.15s;
  }

  .tm-suggestion:last-child {
    border-bottom: none;
  }

  .tm-suggestion:hover {
    background: var(--cds-layer-hover-02);
  }

  .tm-match {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.25rem;
  }

  .tm-file {
    font-size: 0.6875rem;
    color: var(--cds-text-02);
  }

  .tm-source {
    font-size: 0.75rem;
    color: var(--cds-text-02);
    margin-bottom: 0.25rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .tm-target {
    font-size: 0.8125rem;
    color: var(--cds-text-01);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .tm-empty {
    padding: 0.75rem;
    text-align: center;
    color: var(--cds-text-02);
    font-size: 0.75rem;
    font-style: italic;
  }
</style>
