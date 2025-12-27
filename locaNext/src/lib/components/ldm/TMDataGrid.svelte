<script>
  import {
    InlineNotification,
    InlineLoading,
    Button,
    Search,
    Dropdown,
    Tag,
    Modal,
    TextArea,
    Toggle
  } from "carbon-components-svelte";
  import {
    ArrowUp,
    ArrowDown,
    Edit,
    TrashCan,
    Checkmark,
    CheckmarkFilled,
    DataBase,
    Renew,
    Warning
  } from "carbon-icons-svelte";
  import { createEventDispatcher } from "svelte";
  import { get } from "svelte/store";
  import { logger } from "$lib/utils/logger.js";
  import { serverUrl } from "$lib/stores/app.js";

  const dispatch = createEventDispatcher();

  // API base URL from store (like DataGrid)
  let API_BASE = $derived(get(serverUrl));

  // Svelte 5: Props
  let { tmId = null, tmName = "" } = $props();

  // Svelte 5: State
  let entries = $state([]);
  let total = $state(0);
  let loading = $state(false);
  let errorMessage = $state("");

  // UI-035: Infinite scroll instead of pagination
  let page = $state(1);
  let pageSize = $state(200); // Load more per batch
  let hasMore = $state(true);
  let loadingMore = $state(false);

  // Sorting
  let sortBy = $state("id");
  let sortOrder = $state("asc");

  // Search
  let searchTerm = $state("");
  let searchDebounceTimer = null;

  // Metadata dropdown (BUG-020: added confirmation metadata, BUG-024: added "none" option)
  const metadataOptions = [
    { id: "none", text: "None (2 columns)" },
    { id: "string_id", text: "StringID" },
    { id: "is_confirmed", text: "Confirmed" },
    { id: "created_at", text: "Created At" },
    { id: "created_by", text: "Created By" },
    { id: "updated_at", text: "Updated At" },
    { id: "confirmed_at", text: "Confirmed At" },
    { id: "confirmed_by", text: "Confirmed By" }
  ];
  let selectedMetadata = $state("none"); // BUG-024: Default to 2 columns

  // Edit Modal state (BUG-027: spacious modal instead of inline editing)
  let showEditModal = $state(false);
  let editingEntry = $state(null);
  let editSource = $state("");
  let editTarget = $state("");
  let editStringId = $state("");
  let editConfirmed = $state(false);
  let saving = $state(false);

  // FEAT-004: Sync status state
  let syncStatus = $state({
    isStale: false,
    pendingChanges: 0,
    lastSynced: null,
    loading: false
  });
  let syncing = $state(false);

  // Helper to get auth headers
  function getAuthHeaders() {
    const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
    return token ? { 'Authorization': `Bearer ${token}` } : {};
  }

  // UI-035: Load entries (initial load, resets list)
  async function loadEntries() {
    if (!tmId) return;

    // Check auth token exists
    const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
    if (!token) {
      logger.warn("No auth token for loading entries");
      return;
    }

    loading = true;
    errorMessage = "";
    page = 1;
    hasMore = true;

    try {
      const params = new URLSearchParams({
        page: "1",
        limit: pageSize.toString(),
        sort_by: sortBy,
        sort_order: sortOrder,
        metadata_field: selectedMetadata
      });

      if (searchTerm.trim()) {
        params.append('search', searchTerm.trim());
      }

      const response = await fetch(`${API_BASE}/api/ldm/tm/${tmId}/entries?${params}`, {
        headers: getAuthHeaders()
      });

      if (response.ok) {
        const data = await response.json();
        entries = data.entries;
        total = data.total;
        hasMore = entries.length < total;
        logger.info("Loaded TM entries", { count: entries.length, total, hasMore });
      } else {
        const error = await response.json();
        errorMessage = error.detail || "Failed to load entries";
        logger.error("Failed to load TM entries", { error: errorMessage });
      }
    } catch (err) {
      errorMessage = err.message;
      logger.error("Error loading TM entries", { error: err.message });
    } finally {
      loading = false;
    }
  }

  // UI-035: Load more entries (infinite scroll)
  async function loadMoreEntries() {
    if (!tmId || loadingMore || !hasMore) return;

    loadingMore = true;
    page += 1;

    try {
      const params = new URLSearchParams({
        page: page.toString(),
        limit: pageSize.toString(),
        sort_by: sortBy,
        sort_order: sortOrder,
        metadata_field: selectedMetadata
      });

      if (searchTerm.trim()) {
        params.append('search', searchTerm.trim());
      }

      const response = await fetch(`${API_BASE}/api/ldm/tm/${tmId}/entries?${params}`, {
        headers: getAuthHeaders()
      });

      if (response.ok) {
        const data = await response.json();
        entries = [...entries, ...data.entries];
        hasMore = entries.length < data.total;
        logger.info("Loaded more TM entries", { count: data.entries.length, total: entries.length, hasMore });
      }
    } catch (err) {
      logger.error("Error loading more TM entries", { error: err.message });
    } finally {
      loadingMore = false;
    }
  }

  // UI-035: Handle scroll for infinite loading
  function handleScroll(event) {
    const { scrollTop, scrollHeight, clientHeight } = event.target;
    // Load more when scrolled to 80% of content
    if (scrollTop + clientHeight >= scrollHeight * 0.8 && hasMore && !loadingMore) {
      loadMoreEntries();
    }
  }

  // FEAT-004: Load sync status
  async function loadSyncStatus() {
    if (!tmId) return;

    // Check auth token exists
    const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
    if (!token) {
      logger.warn("No auth token for sync status check");
      return;
    }

    syncStatus.loading = true;

    try {
      const response = await fetch(`${API_BASE}/api/ldm/tm/${tmId}/sync-status`, {
        headers: getAuthHeaders()
      });

      if (response.ok) {
        const data = await response.json();
        // Svelte 5: mutate properties individually for reactivity
        syncStatus.isStale = data.is_stale;
        syncStatus.pendingChanges = data.pending_changes;
        syncStatus.lastSynced = data.last_synced;
        syncStatus.loading = false;
        logger.info("Loaded sync status", { isStale: data.is_stale, pending: data.pending_changes });
      } else {
        // Handle non-OK response (401, 404, 500, etc.)
        const errorText = await response.text().catch(() => "Unknown error");
        logger.warn("Sync status check failed", { status: response.status, error: errorText });
        syncStatus.loading = false;
      }
    } catch (err) {
      // Network error - could be CORS, unreachable server, etc.
      logger.error("Failed to load sync status (network)", { error: err.message, tmId, apiBase: API_BASE });
      syncStatus.loading = false;
    }
  }

  // FEAT-004: Sync indexes with DB
  async function syncIndexes() {
    if (!tmId || syncing) return;

    syncing = true;
    errorMessage = "";

    try {
      logger.userAction("Starting TM sync", { tmId });

      const response = await fetch(`${API_BASE}/api/ldm/tm/${tmId}/sync`, {
        method: 'POST',
        headers: getAuthHeaders()
      });

      if (response.ok) {
        const data = await response.json();
        logger.success("TM sync complete", {
          insert: data.stats.insert,
          update: data.stats.update,
          unchanged: data.stats.unchanged,
          time: data.time_seconds
        });

        // Update sync status (Svelte 5: mutate properties individually)
        syncStatus.isStale = false;
        syncStatus.pendingChanges = 0;
        syncStatus.lastSynced = new Date().toISOString();
        syncStatus.loading = false;

        dispatch('synced', data);
      } else {
        const error = await response.json();
        errorMessage = error.detail || "Sync failed";
        logger.error("TM sync failed", { error: errorMessage });
      }
    } catch (err) {
      errorMessage = err.message;
      logger.error("Error syncing TM", { error: err.message });
    } finally {
      syncing = false;
    }
  }

  // FEAT-004: Mark as stale after edit (local indicator, actual status from API)
  function markAsStale() {
    syncStatus.isStale = true;
    syncStatus.pendingChanges = (syncStatus.pendingChanges || 0) + 1;
  }

  // Handle sort click
  function handleSort(column) {
    if (sortBy === column) {
      sortOrder = sortOrder === "asc" ? "desc" : "asc";
    } else {
      sortBy = column;
      sortOrder = "asc";
    }
    page = 1;
    loadEntries();
  }

  // Handle search with debounce
  function handleSearch() {
    if (searchDebounceTimer) clearTimeout(searchDebounceTimer);
    searchDebounceTimer = setTimeout(() => {
      page = 1;
      loadEntries();
    }, 300);
  }

  // Handle metadata change
  function handleMetadataChange(event) {
    selectedMetadata = event.detail.selectedId;
    loadEntries();
  }

  // UI-035: Removed handlePageChange - using infinite scroll instead

  // BUG-027: Open Edit Modal (not inline editing)
  function startEdit(entry) {
    editingEntry = entry;
    editSource = entry.source_text || "";
    editTarget = entry.target_text || "";
    editStringId = entry.string_id || "";
    editConfirmed = entry.is_confirmed || false;
    showEditModal = true;
    logger.userAction("Edit TM entry modal opened", { entryId: entry.id });
  }

  // Close Edit Modal
  function closeEditModal() {
    showEditModal = false;
    editingEntry = null;
    editSource = "";
    editTarget = "";
    editStringId = "";
    editConfirmed = false;
  }

  // Save entry from modal
  async function saveEdit() {
    if (!editingEntry) return;

    saving = true;
    try {
      const response = await fetch(`${API_BASE}/api/ldm/tm/${tmId}/entries/${editingEntry.id}`, {
        method: 'PUT',
        headers: {
          ...getAuthHeaders(),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          source_text: editSource,
          target_text: editTarget,
          string_id: editStringId || null
        })
      });

      if (response.ok) {
        // If confirmed status changed, update that too
        if (editConfirmed !== editingEntry.is_confirmed) {
          await fetch(`${API_BASE}/api/ldm/tm/${tmId}/entries/${editingEntry.id}/confirm?confirm=${editConfirmed}`, {
            method: 'POST',
            headers: getAuthHeaders()
          });
        }

        logger.success("TM entry updated", { entryId: editingEntry.id });
        closeEditModal();
        await loadEntries();
        markAsStale(); // FEAT-004: Mark indexes as stale
        dispatch('updated');
      } else {
        const error = await response.json();
        errorMessage = error.detail || "Failed to update entry";
        logger.error("Failed to update TM entry", { error: errorMessage });
      }
    } catch (err) {
      errorMessage = err.message;
      logger.error("Error updating TM entry", { error: err.message });
    } finally {
      saving = false;
    }
  }

  // UI-036: Removed toggleConfirm - no longer needed in TM grid

  // Delete entry
  async function deleteEntry(entry) {
    if (!confirm("Delete this entry?")) return;

    try {
      const response = await fetch(`${API_BASE}/api/ldm/tm/${tmId}/entries/${entry.id}`, {
        method: 'DELETE',
        headers: getAuthHeaders()
      });

      if (response.ok) {
        logger.success("TM entry deleted", { entryId: entry.id });
        await loadEntries();
        markAsStale(); // FEAT-004: Mark indexes as stale
        dispatch('updated');
      } else {
        const error = await response.json();
        errorMessage = error.detail || "Failed to delete entry";
        logger.error("Failed to delete TM entry", { error: errorMessage });
      }
    } catch (err) {
      errorMessage = err.message;
      logger.error("Error deleting TM entry", { error: err.message });
    }
  }

  // Format date
  function formatDate(dateStr) {
    if (!dateStr) return "-";
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  // Get metadata value for display
  function getMetadataValue(entry) {
    switch (selectedMetadata) {
      case "string_id":
        return entry.string_id || "-";
      case "is_confirmed":
        return entry.is_confirmed ? "Yes" : "No";
      case "created_at":
        return formatDate(entry.created_at);
      case "created_by":
        return entry.created_by || "-";
      case "updated_at":
        return formatDate(entry.updated_at);
      case "confirmed_at":
        return formatDate(entry.confirmed_at);
      case "confirmed_by":
        return entry.confirmed_by || "-";
      default:
        return "-";
    }
  }

  // Get metadata label
  function getMetadataLabel() {
    const option = metadataOptions.find(o => o.id === selectedMetadata);
    return option?.text || "Metadata";
  }

  // Svelte 5: Effect - Load entries and sync status when TM changes
  $effect(() => {
    if (tmId) {
      // Reset state for new TM
      page = 1;
      searchTerm = "";
      sortBy = "id";
      sortOrder = "asc";
      errorMessage = ""; // Clear any previous errors
      entries = []; // Clear old entries

      // Load data (with small delay to ensure auth is ready)
      setTimeout(() => {
        loadEntries();
        loadSyncStatus();
      }, 50);
    }
  });

  // Handle keyboard shortcuts
  function handleKeydown(event) {
    if (event.key === 'Escape' && showEditModal) {
      closeEditModal();
      event.preventDefault();
    }
    if (event.key === 's' && (event.ctrlKey || event.metaKey) && showEditModal) {
      saveEdit();
      event.preventDefault();
    }
  }
</script>

<svelte:window on:keydown={handleKeydown} />

<div class="tm-data-grid">
  <!-- Header -->
  <div class="grid-header">
    <div class="header-left">
      <DataBase size={20} />
      <h3 class="tm-title">{tmName}</h3>
      <Tag type="outline" size="sm">{total.toLocaleString()} entries</Tag>
    </div>
    <div class="header-center">
      <!-- FEAT-004: Sync Status Indicator -->
      {#if syncStatus.isStale}
        <Tag type="yellow" size="sm">
          <Warning size={12} />
          {syncStatus.pendingChanges || '?'} pending
        </Tag>
      {:else if syncStatus.lastSynced}
        <Tag type="green" size="sm">
          <Checkmark size={12} />
          Synced
        </Tag>
      {:else}
        <Tag type="outline" size="sm">Not synced</Tag>
      {/if}
      <Button
        kind={syncStatus.isStale ? "primary" : "ghost"}
        size="small"
        icon={Renew}
        disabled={syncing}
        on:click={syncIndexes}
      >
        {syncing ? "Syncing..." : "Sync Indexes"}
      </Button>
    </div>
    <div class="header-right">
      <span class="metadata-label">Metadata:</span>
      <Dropdown
        size="sm"
        items={metadataOptions}
        selectedId={selectedMetadata}
        on:select={handleMetadataChange}
      />
    </div>
  </div>

  {#if errorMessage}
    <InlineNotification
      kind="error"
      title="Error"
      subtitle={errorMessage}
      on:close={() => errorMessage = ""}
    />
  {/if}

  <!-- Toolbar -->
  <div class="grid-toolbar">
    <div class="toolbar-left">
      <Search
        bind:value={searchTerm}
        on:clear={() => { searchTerm = ""; handleSearch(); }}
        on:input={handleSearch}
        placeholder="Search source, target, or StringID..."
        size="sm"
      />
    </div>
    <div class="toolbar-right">
      <Button
        kind="ghost"
        size="small"
        icon={Checkmark}
        on:click={loadEntries}
      >
        Refresh
      </Button>
    </div>
  </div>

  <!-- Table with infinite scroll (UI-035) -->
  <div class="entries-table" onscroll={handleScroll}>
    {#if loading && entries.length === 0}
      <div class="loading-container">
        <InlineLoading description="Loading entries..." />
      </div>
    {:else if entries.length === 0}
      <div class="empty-state">
        <DataBase size={32} />
        <p>No entries found.</p>
        {#if searchTerm}
          <p class="empty-hint">Try a different search term.</p>
        {/if}
      </div>
    {:else}
      <table>
        <thead>
          <tr>
            <th class="col-id" onclick={() => handleSort("id")}>
              ID
              {#if sortBy === "id"}
                {#if sortOrder === "asc"}
                  <ArrowUp size={12} />
                {:else}
                  <ArrowDown size={12} />
                {/if}
              {/if}
            </th>
            <th class="col-source" onclick={() => handleSort("source_text")}>
              Source
              {#if sortBy === "source_text"}
                {#if sortOrder === "asc"}
                  <ArrowUp size={12} />
                {:else}
                  <ArrowDown size={12} />
                {/if}
              {/if}
            </th>
            <th class="col-target" onclick={() => handleSort("target_text")}>
              Target
              {#if sortBy === "target_text"}
                {#if sortOrder === "asc"}
                  <ArrowUp size={12} />
                {:else}
                  <ArrowDown size={12} />
                {/if}
              {/if}
            </th>
            {#if selectedMetadata !== "none"}
              <th class="col-metadata" onclick={() => handleSort(selectedMetadata)}>
                {getMetadataLabel()}
                {#if sortBy === selectedMetadata}
                  {#if sortOrder === "asc"}
                    <ArrowUp size={12} />
                  {:else}
                    <ArrowDown size={12} />
                  {/if}
                {/if}
              </th>
            {/if}
            <th class="col-actions">Actions</th>
          </tr>
        </thead>
        <tbody>
          {#each entries as entry (entry.id)}
            <tr
              ondblclick={() => startEdit(entry)}
              class:confirmed={entry.is_confirmed}
            >
              <td class="col-id">
                {entry.id}
                {#if entry.is_confirmed}
                  <CheckmarkFilled size={12} class="confirmed-icon" />
                {/if}
              </td>
              <td class="col-source">
                <span class="cell-text">{entry.source_text}</span>
              </td>
              <td class="col-target">
                <span class="cell-text">{entry.target_text}</span>
              </td>
              {#if selectedMetadata !== "none"}
                <td class="col-metadata">
                  <span class="cell-text metadata">{getMetadataValue(entry)}</span>
                </td>
              {/if}
              <td class="col-actions">
                <!-- UI-036: Removed Confirm button -->
                <Button
                  kind="ghost"
                  size="small"
                  icon={Edit}
                  iconDescription="Edit"
                  tooltipAlignment="end"
                  on:click={() => startEdit(entry)}
                />
                <Button
                  kind="danger-ghost"
                  size="small"
                  icon={TrashCan}
                  iconDescription="Delete"
                  tooltipAlignment="end"
                  on:click={() => deleteEntry(entry)}
                />
              </td>
            </tr>
          {/each}
        </tbody>
      </table>

      {#if loading}
        <div class="loading-bar">
          <InlineLoading description="Loading..." />
        </div>
      {/if}
    {/if}
  </div>

  <!-- UI-035: Infinite scroll loading indicator -->
  {#if loadingMore}
    <div class="loading-bar">
      <InlineLoading description="Loading more..." />
    </div>
  {:else if hasMore && entries.length > 0}
    <div class="scroll-hint">
      Scroll for more ({entries.length} of {total.toLocaleString()})
    </div>
  {/if}
</div>

<!-- BUG-027: Spacious Edit Modal (same pattern as DataGrid) - UI-055 FIX: Use {#if} to prevent DOM bloat -->
{#if showEditModal}
<Modal
  open={true}
  modalHeading="Edit TM Entry"
  primaryButtonText={saving ? "Saving..." : "Save"}
  secondaryButtonText="Cancel"
  primaryButtonDisabled={saving}
  on:click:button--primary={saveEdit}
  on:click:button--secondary={closeEditModal}
  on:close={closeEditModal}
  size="lg"
>
  {#if editingEntry}
    <div class="edit-form">
      <div class="edit-hint">
        <span>Ctrl+S to save</span>
        <span>Esc to cancel</span>
      </div>

      <div class="field">
        <label>Entry ID</label>
        <div class="readonly-value">{editingEntry.id}</div>
      </div>

      <div class="field">
        <label>StringID</label>
        <input
          type="text"
          class="text-input"
          bind:value={editStringId}
          placeholder="StringID (optional)"
        />
      </div>

      <div class="field">
        <label>Source - Read Only</label>
        <div class="source-preview">{editingEntry.source_text}</div>
      </div>

      <TextArea
        bind:value={editTarget}
        labelText="Target (Translation)"
        placeholder="Enter translation..."
        rows={4}
      />

      <div class="confirm-toggle">
        <Toggle
          bind:toggled={editConfirmed}
          labelText="Confirmed"
          labelA="No"
          labelB="Yes"
        />
      </div>
    </div>
  {/if}
</Modal>
{/if}

<style>
  .tm-data-grid {
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
    background: var(--cds-layer-01);
    border-bottom: 1px solid var(--cds-border-subtle-01);
  }

  .header-left {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .header-left :global(svg) {
    color: var(--cds-icon-01);
  }

  .tm-title {
    margin: 0;
    font-size: 1rem;
    font-weight: 600;
    color: var(--cds-text-01);
  }

  .header-center {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .header-center :global(.bx--tag) {
    display: flex;
    align-items: center;
    gap: 0.25rem;
  }

  .header-right {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .metadata-label {
    font-size: 0.75rem;
    color: var(--cds-text-02);
  }

  .grid-toolbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
    padding: 0.5rem 1rem;
    background: var(--cds-layer-01);
    border-bottom: 1px solid var(--cds-border-subtle-01);
  }

  .toolbar-left {
    flex: 1;
    max-width: 400px;
  }

  .toolbar-right {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .entries-table {
    flex: 1;
    overflow: auto;
    background: var(--cds-background);
  }

  .loading-container {
    display: flex;
    justify-content: center;
    align-items: center;
    height: 200px;
  }

  .empty-state {
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    height: 200px;
    gap: 0.5rem;
    color: var(--cds-text-02);
  }

  .empty-hint {
    font-size: 0.75rem;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.8125rem;
  }

  thead {
    position: sticky;
    top: 0;
    background: var(--cds-layer-accent-01);
    z-index: 1;
  }

  th {
    text-align: left;
    padding: 0.75rem 0.5rem;
    font-weight: 600;
    border-bottom: 2px solid var(--cds-border-strong-01);
    cursor: pointer;
    user-select: none;
    white-space: nowrap;
    color: var(--cds-text-01);
  }

  th:hover {
    background: var(--cds-layer-hover-01);
  }

  th :global(svg) {
    vertical-align: middle;
    margin-left: 0.25rem;
  }

  td {
    padding: 0.5rem;
    border-bottom: 1px solid var(--cds-border-subtle-01);
    vertical-align: top;
  }

  tr {
    cursor: pointer;
  }

  tr:hover {
    background: var(--cds-layer-hover-01);
  }

  /* Confirmed row styling */
  tr.confirmed {
    background: rgba(36, 161, 72, 0.08);
  }

  tr.confirmed:hover {
    background: rgba(36, 161, 72, 0.15);
  }

  .col-id {
    width: 70px;
    text-align: center;
    color: var(--cds-text-02);
    font-size: 0.75rem;
  }

  .col-id :global(.confirmed-icon) {
    color: var(--cds-support-02);
    margin-left: 0.25rem;
    vertical-align: middle;
  }

  .col-source {
    width: 35%;
    min-width: 150px;
  }

  .col-target {
    width: 35%;
    min-width: 150px;
  }

  .col-metadata {
    width: 12%;
    min-width: 100px;
  }

  .col-actions {
    width: 140px;
    text-align: right;
    white-space: nowrap;
  }

  .cell-text {
    display: block;
    word-break: break-word;
    white-space: pre-wrap;
    line-height: 1.4;
    max-height: 4.5em;
    overflow: hidden;
  }

  .cell-text.metadata {
    font-family: monospace;
    font-size: 0.75rem;
    color: var(--cds-text-02);
  }

  .loading-bar {
    padding: 0.5rem;
    text-align: center;
    background: var(--cds-layer-02);
    border-top: 1px solid var(--cds-border-subtle-01);
  }

  /* UI-035: Removed pagination-container, added scroll-hint */
  .scroll-hint {
    text-align: center;
    padding: 0.75rem;
    font-size: 0.75rem;
    color: var(--cds-text-02);
    background: var(--cds-layer-02);
    border-top: 1px solid var(--cds-border-subtle-01);
  }

  /* Edit Modal Styles (BUG-027) */
  .edit-form {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .edit-hint {
    display: flex;
    gap: 1rem;
    font-size: 0.75rem;
    color: var(--cds-text-02);
    padding: 0.5rem;
    background: var(--cds-layer-02);
    border-radius: 4px;
  }

  .field {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .field label {
    font-size: 0.75rem;
    font-weight: 500;
    color: var(--cds-text-02);
  }

  .readonly-value {
    padding: 0.5rem;
    background: var(--cds-layer-02);
    border-radius: 4px;
    font-size: 0.875rem;
    color: var(--cds-text-01);
  }

  .source-preview {
    padding: 0.75rem;
    background: var(--cds-layer-02);
    border-radius: 4px;
    font-size: 0.875rem;
    color: var(--cds-text-01);
    white-space: pre-wrap;
    line-height: 1.5;
    max-height: 150px;
    overflow-y: auto;
  }

  .text-input {
    width: 100%;
    padding: 0.5rem;
    border: 1px solid var(--cds-border-strong-01);
    border-radius: 4px;
    background: var(--cds-field-01);
    color: var(--cds-text-01);
    font-size: 0.875rem;
  }

  .text-input:focus {
    outline: none;
    border-color: var(--cds-interactive-01);
  }

  .confirm-toggle {
    padding-top: 0.5rem;
  }
</style>
