<script>
  import {
    DataTable,
    Toolbar,
    ToolbarContent,
    ToolbarSearch,
    Pagination,
    InlineLoading,
    Tag,
    Button,
    Modal,
    TextArea,
    Select,
    SelectItem
  } from "carbon-components-svelte";
  import { Edit, CheckmarkFilled, WarningAlt, Time, Locked } from "carbon-icons-svelte";
  import { createEventDispatcher, onMount, onDestroy } from "svelte";
  import { get } from "svelte/store";
  import { logger } from "$lib/utils/logger.js";
  import { ldmStore, joinFile, leaveFile, lockRow, unlockRow, isRowLocked, onCellUpdate } from "$lib/stores/ldm.js";
  import { serverUrl } from "$lib/stores/app.js";
  import PresenceBar from "./PresenceBar.svelte";

  const dispatch = createEventDispatcher();

  // API base URL from store
  $: API_BASE = get(serverUrl);

  // Props
  export let fileId = null;
  export let fileName = "";

  // Real-time subscription
  let cellUpdateUnsubscribe = null;

  // State
  let loading = false;
  let rows = [];
  let total = 0;
  let page = 1;
  let pageSize = 50;
  let totalPages = 1;
  let searchTerm = "";

  // Edit modal state
  let showEditModal = false;
  let editingRow = null;
  let editTarget = "";
  let editStatus = "";

  // Table headers
  const headers = [
    { key: "row_num", value: "#", width: "60px" },
    { key: "string_id", value: "StringID" },
    { key: "source", value: "Source (KR)" },
    { key: "target", value: "Target" },
    { key: "status", value: "Status", width: "100px" }
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

  // Load rows for file
  export async function loadRows() {
    if (!fileId) return;
    loading = true;
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        limit: pageSize.toString()
      });
      if (searchTerm) {
        params.append('search', searchTerm);
      }

      const response = await fetch(`${API_BASE}/api/ldm/files/${fileId}/rows?${params}`, {
        headers: getAuthHeaders()
      });

      if (response.ok) {
        const data = await response.json();
        rows = data.rows.map(row => ({
          ...row,
          id: row.id.toString()
        }));
        total = data.total;
        totalPages = data.total_pages;
        logger.info("Loaded rows", { fileId, count: rows.length, total });
      }
    } catch (err) {
      logger.error("Failed to load rows", { error: err.message });
    } finally {
      loading = false;
    }
  }

  // Handle pagination
  function handlePagination(event) {
    page = event.detail.page;
    pageSize = event.detail.pageSize;
    loadRows();
  }

  // Handle search
  function handleSearch() {
    page = 1;
    loadRows();
  }

  // Open edit modal with row locking
  async function openEditModal(row) {
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
  }

  // Close edit modal and release lock
  function closeEditModal() {
    if (editingRow && fileId) {
      unlockRow(fileId, parseInt(editingRow.id));
    }
    showEditModal = false;
    editingRow = null;
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
        logger.success("Row updated", { rowId });
        closeEditModal();
        await loadRows();
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
      // Update the row in our local state
      rows = rows.map(row => {
        if (parseInt(row.id) === update.row_id) {
          return {
            ...row,
            target: update.target,
            status: update.status
          };
        }
        return row;
      });
      logger.info("Real-time update applied", { rowId: update.row_id, by: update.updated_by_username });
    });
  }

  // Subscribe to real-time updates when file changes
  $: if (fileId) {
    // Join WebSocket room for this file
    joinFile(fileId);

    // Subscribe to cell updates
    if (cellUpdateUnsubscribe) {
      cellUpdateUnsubscribe();
    }
    cellUpdateUnsubscribe = onCellUpdate(handleCellUpdates);
  }

  // Cleanup on component destroy
  onDestroy(() => {
    if (fileId) {
      leaveFile(fileId);
    }
    if (cellUpdateUnsubscribe) {
      cellUpdateUnsubscribe();
    }
  });

  // Get status tag kind
  function getStatusKind(status) {
    switch (status) {
      case 'approved': return 'green';
      case 'reviewed': return 'blue';
      case 'translated': return 'teal';
      default: return 'gray';
    }
  }

  // Watch file changes
  $: if (fileId) {
    page = 1;
    searchTerm = "";
    loadRows();
  }
</script>

<div class="data-grid">
  {#if fileId}
    <div class="grid-header">
      <div class="header-left">
        <h4>{fileName || `File #${fileId}`}</h4>
        <span class="row-count">{total.toLocaleString()} rows</span>
      </div>
      <PresenceBar />
    </div>

    <DataTable
      {headers}
      {rows}
      size="short"
      sortable
    >
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

      <svelte:fragment slot="cell" let:row let:cell>
        {#if cell.key === "source"}
          <div class="source-cell">{cell.value || ""}</div>
        {:else if cell.key === "target"}
          {@const rowLock = isRowLocked(parseInt(row.id))}
          <div
            class="target-cell"
            class:locked={rowLock}
            on:dblclick={() => openEditModal(row)}
            role="button"
            tabindex="0"
            on:keydown={(e) => e.key === 'Enter' && openEditModal(row)}
            title={rowLock ? `Locked by ${rowLock.locked_by}` : "Double-click to edit"}
          >
            {cell.value || ""}
            {#if rowLock}
              <span class="lock-indicator" title="Locked by {rowLock.locked_by}">
                <Locked size={12} />
              </span>
            {:else}
              <span class="edit-hint">
                <Edit size={12} />
              </span>
            {/if}
          </div>
        {:else if cell.key === "status"}
          <Tag type={getStatusKind(cell.value)} size="sm">
            {cell.value || "pending"}
          </Tag>
        {:else if cell.key === "string_id"}
          <div class="string-id-cell" title={cell.value}>
            {cell.value || "-"}
          </div>
        {:else}
          {cell.value}
        {/if}
      </svelte:fragment>
    </DataTable>

    {#if loading}
      <InlineLoading description="Loading..." />
    {/if}

    <Pagination
      bind:pageSize
      bind:page
      totalItems={total}
      pageSizes={[25, 50, 100, 200]}
      on:change={handlePagination}
    />
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
    <div class="edit-form">
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
  .data-grid {
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

  .grid-header h4 {
    margin: 0;
    font-size: 0.875rem;
    font-weight: 600;
  }

  .row-count {
    font-size: 0.75rem;
    color: var(--cds-text-02);
  }

  .source-cell {
    background: var(--cds-layer-02);
    padding: 0.25rem 0.5rem;
    border-radius: 2px;
    color: var(--cds-text-02);
    font-size: 0.8125rem;
    max-width: 300px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .target-cell {
    position: relative;
    padding: 0.25rem 0.5rem;
    padding-right: 1.5rem;
    cursor: pointer;
    min-height: 1.5rem;
    max-width: 300px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    transition: background-color 0.15s ease;
  }

  .target-cell:hover {
    background: var(--cds-layer-active-01);
  }

  .target-cell .edit-hint {
    position: absolute;
    right: 0.25rem;
    top: 50%;
    transform: translateY(-50%);
    opacity: 0;
    color: var(--cds-icon-02);
    transition: opacity 0.15s ease;
  }

  .target-cell:hover .edit-hint {
    opacity: 1;
  }

  .target-cell.locked {
    background: var(--cds-layer-02);
    cursor: not-allowed;
  }

  .target-cell.locked:hover {
    background: var(--cds-layer-02);
  }

  .lock-indicator {
    position: absolute;
    right: 0.25rem;
    top: 50%;
    transform: translateY(-50%);
    color: var(--cds-support-03);
    opacity: 0.8;
  }

  .string-id-cell {
    font-family: monospace;
    font-size: 0.75rem;
    max-width: 200px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
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

  :global(.data-grid .bx--data-table-container) {
    flex: 1;
    overflow: auto;
  }

  :global(.data-grid .bx--pagination) {
    border-top: 1px solid var(--cds-border-subtle-01);
  }
</style>
