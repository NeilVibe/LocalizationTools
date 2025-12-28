<script>
  import {
    Modal,
    InlineNotification,
    InlineLoading,
    Button,
    Search,
    Dropdown,
    Tag
  } from "carbon-components-svelte";
  import {
    ArrowUp,
    ArrowDown,
    Edit,
    TrashCan,
    Checkmark,
    CheckmarkFilled,
    Close,
    Download
  } from "carbon-icons-svelte";
  import { createEventDispatcher, tick } from "svelte";
  import { get } from "svelte/store";
  import { logger } from "$lib/utils/logger.js";
  import { serverUrl } from "$lib/stores/app.js";

  const dispatch = createEventDispatcher();

  // API base URL from store (never hardcode!)
  const API_BASE = get(serverUrl);

  // Svelte 5: Props
  let { open = $bindable(false), tm = null } = $props();

  // Svelte 5: State
  let entries = $state([]);
  let total = $state(0);
  let loading = $state(false);
  let errorMessage = $state("");

  // UI-025/026/028: Removed pagination - use infinite scroll instead
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

  // Editing state
  let editingEntryId = $state(null);
  let editSource = $state("");
  let editTarget = $state("");
  let editStringId = $state("");
  let saving = $state(false);

  // Helper to get auth headers
  function getAuthHeaders() {
    const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
    return token ? { 'Authorization': `Bearer ${token}` } : {};
  }

  // Load entries (initial load or after filter change)
  async function loadEntries() {
    if (!tm?.id) return;

    loading = true;
    errorMessage = "";
    page = 1; // Reset to first page

    try {
      const params = new URLSearchParams({
        page: '1',
        limit: pageSize.toString(),
        sort_by: sortBy,
        sort_order: sortOrder,
        metadata_field: selectedMetadata
      });

      if (searchTerm.trim()) {
        params.append('search', searchTerm.trim());
      }

      const response = await fetch(`${API_BASE}/api/ldm/tm/${tm.id}/entries?${params}`, {
        headers: getAuthHeaders()
      });

      if (response.ok) {
        const data = await response.json();
        entries = data.entries;
        total = data.total;
        hasMore = entries.length < total;
        logger.info("Loaded TM entries", { count: entries.length, total });
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

  // UI-025/026/028: Load more entries (infinite scroll)
  async function loadMoreEntries() {
    if (!tm?.id || loadingMore || !hasMore) return;

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

      const response = await fetch(`${API_BASE}/api/ldm/tm/${tm.id}/entries?${params}`, {
        headers: getAuthHeaders()
      });

      if (response.ok) {
        const data = await response.json();
        entries = [...entries, ...data.entries];
        hasMore = entries.length < total;
        logger.info("Loaded more TM entries", { loaded: entries.length, total });
      }
    } catch (err) {
      logger.error("Error loading more entries", { error: err.message });
      page -= 1; // Revert page on error
    } finally {
      loadingMore = false;
    }
  }

  // Handle scroll for infinite loading
  function handleScroll(event) {
    const { scrollTop, scrollHeight, clientHeight } = event.target;
    // Load more when scrolled to 80% of content
    if (scrollTop + clientHeight >= scrollHeight * 0.8 && hasMore && !loadingMore) {
      loadMoreEntries();
    }
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


  // Start editing entry
  function startEdit(entry) {
    editingEntryId = entry.id;
    editSource = entry.source_text || "";
    editTarget = entry.target_text || "";
    editStringId = entry.string_id || "";
    logger.userAction("Edit TM entry started", { entryId: entry.id });
  }

  // Cancel editing
  function cancelEdit() {
    editingEntryId = null;
    editSource = "";
    editTarget = "";
    editStringId = "";
  }

  // UI-055 FIX: Handle modal close with event dispatch for parent control
  function handleModalClose() {
    open = false;
    cancelEdit();
    dispatch('close');
  }

  // Save entry
  async function saveEntry(entryId) {
    saving = true;
    try {
      const response = await fetch(`${API_BASE}/api/ldm/tm/${tm.id}/entries/${entryId}`, {
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
        logger.success("TM entry updated", { entryId });
        cancelEdit();
        await loadEntries();
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

  // Delete entry
  async function deleteEntry(entryId) {
    if (!confirm("Delete this entry?")) return;

    try {
      const response = await fetch(`${API_BASE}/api/ldm/tm/${tm.id}/entries/${entryId}`, {
        method: 'DELETE',
        headers: getAuthHeaders()
      });

      if (response.ok) {
        logger.success("TM entry deleted", { entryId });
        await loadEntries();
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

  // Get metadata value for display (BUG-020: added confirmation metadata)
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

  // Svelte 5: Effect - Load entries when modal opens or TM changes
  $effect(() => {
    if (open && tm?.id) {
      page = 1;
      searchTerm = "";
      sortBy = "id";
      sortOrder = "asc";
      loadEntries();
    }
  });

  // Handle keyboard shortcuts
  function handleKeydown(event) {
    if (event.key === 'Escape' && editingEntryId) {
      cancelEdit();
      event.preventDefault();
    }
    if (event.key === 'Enter' && event.ctrlKey && editingEntryId) {
      saveEntry(editingEntryId);
      event.preventDefault();
    }
  }
</script>

<svelte:window on:keydown={handleKeydown} />

<Modal
  bind:open
  modalHeading={tm ? `TM Viewer: ${tm.name}` : "TM Viewer"}
  passiveModal
  size="lg"
  on:close={handleModalClose}
>
  <div class="tm-viewer">
    {#if errorMessage}
      <InlineNotification
        kind="error"
        title="Error"
        subtitle={errorMessage}
        on:close={() => errorMessage = ""}
      />
    {/if}

    <!-- Toolbar -->
    <div class="viewer-toolbar">
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
        <span class="metadata-label">Metadata:</span>
        <Dropdown
          size="sm"
          items={metadataOptions}
          selectedId={selectedMetadata}
          on:select={handleMetadataChange}
        />
        <span class="entry-count">
          {total.toLocaleString()} entries
        </span>
      </div>
    </div>

    <!-- Table with infinite scroll -->
    <div class="entries-table" onscroll={handleScroll}>
      {#if loading && entries.length === 0}
        <div class="loading-container">
          <InlineLoading description="Loading entries..." />
        </div>
      {:else if entries.length === 0}
        <div class="empty-state">
          <p>No entries found.</p>
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
              <th class="col-actions"></th>
            </tr>
          </thead>
          <tbody>
            {#each entries as entry (entry.id)}
              {#if editingEntryId === entry.id}
                <!-- Editing row -->
                <tr class="editing-row">
                  <td class="col-id">{entry.id}</td>
                  <td class="col-source">
                    <textarea
                      class="edit-input"
                      bind:value={editSource}
                      placeholder="Source text"
                    ></textarea>
                  </td>
                  <td class="col-target">
                    <textarea
                      class="edit-input"
                      bind:value={editTarget}
                      placeholder="Target text"
                    ></textarea>
                  </td>
                  {#if selectedMetadata !== "none"}
                    <td class="col-metadata">
                      {#if selectedMetadata === "string_id"}
                        <input
                          type="text"
                          class="edit-input-sm"
                          bind:value={editStringId}
                          placeholder="StringID"
                        />
                      {:else}
                        {getMetadataValue(entry)}
                      {/if}
                    </td>
                  {/if}
                  <td class="col-actions">
                    <Button
                      kind="primary"
                      size="small"
                      icon={Checkmark}
                      iconDescription="Save"
                      tooltipAlignment="end"
                      disabled={saving}
                      on:click={() => saveEntry(entry.id)}
                    />
                    <Button
                      kind="ghost"
                      size="small"
                      icon={Close}
                      iconDescription="Cancel"
                      tooltipAlignment="end"
                      on:click={cancelEdit}
                    />
                  </td>
                </tr>
              {:else}
                <!-- Normal row -->
                <tr ondblclick={() => startEdit(entry)} class:confirmed={entry.is_confirmed}>
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
                      on:click={() => deleteEntry(entry.id)}
                    />
                  </td>
                </tr>
              {/if}
            {/each}
          </tbody>
        </table>

        {#if loading}
          <div class="loading-bar">
            <InlineLoading description="Loading..." />
          </div>
        {/if}

        <!-- UI-025/026/028: Infinite scroll loading indicator -->
        {#if loadingMore}
          <div class="loading-bar">
            <InlineLoading description="Loading more..." />
          </div>
        {:else if hasMore && entries.length > 0}
          <div class="load-more-hint">
            Scroll for more ({entries.length} of {total.toLocaleString()})
          </div>
        {/if}
      {/if}
    </div>
  </div>
</Modal>

<style>
  .tm-viewer {
    display: flex;
    flex-direction: column;
    min-height: 500px;
    max-height: 70vh;
  }

  .viewer-toolbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
    padding: 0.75rem 0;
    border-bottom: 1px solid var(--cds-border-subtle-01);
    margin-bottom: 0.5rem;
    flex-wrap: wrap;
  }

  .toolbar-left {
    flex: 1;
    min-width: 200px;
    max-width: 400px;
  }

  .toolbar-right {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .metadata-label {
    font-size: 0.75rem;
    color: var(--cds-text-02);
  }

  .entry-count {
    font-size: 0.75rem;
    color: var(--cds-text-02);
    padding: 0.25rem 0.5rem;
    background: var(--cds-layer-02);
    border-radius: 4px;
  }

  .entries-table {
    flex: 1;
    overflow: auto;
    border: 1px solid var(--cds-border-subtle-01);
    border-radius: 4px;
  }

  .loading-container {
    display: flex;
    justify-content: center;
    align-items: center;
    height: 200px;
  }

  .empty-state {
    display: flex;
    justify-content: center;
    align-items: center;
    height: 200px;
    color: var(--cds-text-02);
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

  tr:hover {
    background: var(--cds-layer-hover-01);
  }

  tr.editing-row {
    background: var(--cds-layer-selected-01);
  }

  .col-id {
    width: 60px;
    text-align: center;
    color: var(--cds-text-02);
    font-size: 0.75rem;
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
    width: 15%;
    min-width: 100px;
  }

  .col-actions {
    width: 120px;
    text-align: right;
    white-space: nowrap;
  }

  /* BUG-020: Confirmed row styling */
  tr.confirmed {
    background: rgba(36, 161, 72, 0.08);
  }

  tr.confirmed:hover {
    background: rgba(36, 161, 72, 0.15);
  }

  .col-id :global(.confirmed-icon) {
    color: var(--cds-support-02);
    margin-left: 0.25rem;
    vertical-align: middle;
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

  .edit-input {
    width: 100%;
    min-height: 60px;
    padding: 0.5rem;
    border: 1px solid var(--cds-border-strong-01);
    border-radius: 4px;
    background: var(--cds-field-01);
    color: var(--cds-text-01);
    font-size: 0.8125rem;
    font-family: inherit;
    resize: vertical;
  }

  .edit-input:focus {
    outline: none;
    border-color: var(--cds-interactive-01);
  }

  .edit-input-sm {
    width: 100%;
    padding: 0.35rem 0.5rem;
    border: 1px solid var(--cds-border-strong-01);
    border-radius: 4px;
    background: var(--cds-field-01);
    color: var(--cds-text-01);
    font-size: 0.75rem;
    font-family: monospace;
  }

  .edit-input-sm:focus {
    outline: none;
    border-color: var(--cds-interactive-01);
  }

  .loading-bar {
    padding: 0.5rem;
    text-align: center;
    background: var(--cds-layer-02);
    border-top: 1px solid var(--cds-border-subtle-01);
  }

  /* UI-025/026/028: Infinite scroll hint */
  .load-more-hint {
    padding: 0.5rem;
    text-align: center;
    font-size: 0.75rem;
    color: var(--cds-text-02);
    background: var(--cds-layer-02);
    border-top: 1px solid var(--cds-border-subtle-01);
  }
</style>
