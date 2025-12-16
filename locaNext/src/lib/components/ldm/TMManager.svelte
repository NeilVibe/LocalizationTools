<script>
  import {
    DataTable,
    Toolbar,
    ToolbarContent,
    Button,
    Modal,
    InlineNotification,
    InlineLoading,
    Tag,
    OverflowMenu,
    OverflowMenuItem
  } from "carbon-components-svelte";
  import {
    Add,
    TrashCan,
    Renew,
    CheckmarkFilled,
    WarningAlt,
    InProgress,
    Power
  } from "carbon-icons-svelte";
  import { createEventDispatcher, onMount } from "svelte";
  import { logger } from "$lib/utils/logger.js";
  import { preferences } from "$lib/stores/preferences.js";
  import TMUploadModal from "./TMUploadModal.svelte";

  const dispatch = createEventDispatcher();

  // API base URL
  const API_BASE = 'http://localhost:8888';

  // Svelte 5: Props
  let { open = $bindable(false) } = $props();

  // Svelte 5: State
  let tms = $state([]);
  let loading = $state(false);
  let errorMessage = $state("");
  let showUploadModal = $state(false);
  let deleteConfirmOpen = $state(false);
  let tmToDelete = $state(null);
  let buildingIndexes = $state(new Set());
  let buildConfirmOpen = $state(false);
  let tmToBuild = $state(null);

  // UI-003: Active TM state
  let activeTmId = $state(null);

  // Load active TM from preferences
  function loadActiveTm() {
    const prefs = $preferences;
    activeTmId = prefs.activeTmId;
  }

  // UI-003: Activate/Deactivate TM
  function toggleActiveTm(tm) {
    if (activeTmId === tm.id) {
      // Deactivate
      activeTmId = null;
      preferences.setActiveTm(null);
      logger.userAction("TM deactivated", { tmId: tm.id, name: tm.name });
    } else {
      // Activate (only if ready)
      if (tm.status !== 'ready') {
        errorMessage = "Cannot activate TM - indexes not built yet. Build indexes first.";
        return;
      }
      activeTmId = tm.id;
      preferences.setActiveTm(tm.id);
      logger.userAction("TM activated", { tmId: tm.id, name: tm.name });
    }
  }

  // Helper to get auth headers
  function getAuthHeaders() {
    const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
    return token ? { 'Authorization': `Bearer ${token}` } : {};
  }

  // Load TMs list
  async function loadTMs() {
    loading = true;
    errorMessage = "";
    try {
      const response = await fetch(`${API_BASE}/api/ldm/tm`, {
        headers: getAuthHeaders()
      });
      if (response.ok) {
        tms = await response.json();
        logger.info("Loaded TMs", { count: tms.length });
      } else {
        const error = await response.json();
        errorMessage = error.detail || "Failed to load TMs";
        logger.error("Failed to load TMs", { error: errorMessage });
      }
    } catch (err) {
      errorMessage = err.message;
      logger.error("Error loading TMs", { error: err.message });
    } finally {
      loading = false;
    }
  }

  // Delete TM
  async function deleteTM() {
    if (!tmToDelete) return;

    try {
      const response = await fetch(`${API_BASE}/api/ldm/tm/${tmToDelete.id}`, {
        method: 'DELETE',
        headers: getAuthHeaders()
      });

      if (response.ok) {
        logger.success("TM deleted", { name: tmToDelete.name, id: tmToDelete.id });
        await loadTMs();
      } else {
        const error = await response.json();
        errorMessage = error.detail || "Failed to delete TM";
        logger.error("Failed to delete TM", { error: errorMessage });
      }
    } catch (err) {
      errorMessage = err.message;
      logger.error("Error deleting TM", { error: err.message });
    } finally {
      deleteConfirmOpen = false;
      tmToDelete = null;
    }
  }

  // Build indexes for TM
  async function buildIndexes(tm) {
    buildingIndexes = new Set([...buildingIndexes, tm.id]);

    try {
      const response = await fetch(`${API_BASE}/api/ldm/tm/${tm.id}/build-indexes`, {
        method: 'POST',
        headers: getAuthHeaders()
      });

      if (response.ok) {
        const result = await response.json();
        logger.success("Indexes built", { name: tm.name, ...result });
        await loadTMs();
      } else {
        const error = await response.json();
        errorMessage = error.detail || "Failed to build indexes";
        logger.error("Failed to build indexes", { error: errorMessage });
      }
    } catch (err) {
      errorMessage = err.message;
      logger.error("Error building indexes", { error: err.message });
    } finally {
      buildingIndexes.delete(tm.id);
      buildingIndexes = buildingIndexes;
    }
  }

  // Format entry count
  function formatCount(count) {
    if (count >= 1000000) return `${(count / 1000000).toFixed(1)}M`;
    if (count >= 1000) return `${(count / 1000).toFixed(1)}K`;
    return count.toString();
  }

  // Format date
  function formatDate(dateStr) {
    if (!dateStr) return "-";
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  }

  // Get status tag kind
  function getStatusKind(status) {
    switch (status) {
      case 'ready': return 'green';
      case 'pending': return 'gray';
      case 'indexing': return 'blue';
      case 'error': return 'red';
      default: return 'gray';
    }
  }

  // Get status icon
  function getStatusIcon(status) {
    switch (status) {
      case 'ready': return CheckmarkFilled;
      case 'indexing': return InProgress;
      case 'error': return WarningAlt;
      default: return null;
    }
  }

  // Handle upload complete
  function handleUploadComplete(event) {
    showUploadModal = false;
    loadTMs();
    dispatch('tmUploaded', event.detail);
  }

  // Open delete confirmation
  function confirmDelete(tm) {
    tmToDelete = tm;
    deleteConfirmOpen = true;
  }

  // Open build confirmation (warning about resource usage)
  function confirmBuildIndexes(tm) {
    tmToBuild = tm;
    buildConfirmOpen = true;
  }

  // Execute build after confirmation
  function executeBuildIndexes() {
    if (tmToBuild) {
      buildIndexes(tmToBuild);
    }
    buildConfirmOpen = false;
    tmToBuild = null;
  }

  // Svelte 5: Effect - Load TMs and active TM when modal opens
  $effect(() => {
    if (open) {
      loadActiveTm();
      loadTMs();
    }
  });

  // DataTable headers
  const headers = [
    { key: 'name', value: 'Name' },
    { key: 'entry_count', value: 'Entries' },
    { key: 'source_lang', value: 'Source' },
    { key: 'target_lang', value: 'Target' },
    { key: 'status', value: 'Status' },
    { key: 'created_at', value: 'Created' },
    { key: 'actions', value: '', empty: true }
  ];
</script>

<Modal
  bind:open
  modalHeading="Translation Memories"
  passiveModal
  size="lg"
  on:close={() => open = false}
>
  <div class="tm-manager">
    {#if errorMessage}
      <InlineNotification
        kind="error"
        title="Error"
        subtitle={errorMessage}
        on:close={() => errorMessage = ""}
      />
    {/if}

    <div class="tm-toolbar">
      <Button
        kind="primary"
        size="small"
        icon={Add}
        on:click={() => showUploadModal = true}
      >
        Upload TM
      </Button>
      <Button
        kind="ghost"
        size="small"
        icon={Renew}
        iconDescription="Refresh"
        on:click={loadTMs}
      />
    </div>

    {#if loading}
      <div class="loading-container">
        <InlineLoading description="Loading Translation Memories..." />
      </div>
    {:else if tms.length === 0}
      <div class="empty-state">
        <p>No Translation Memories yet.</p>
        <p class="empty-hint">Upload a TM file (TXT, XML, or Excel) to get started.</p>
      </div>
    {:else}
      <div class="tm-table">
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Entries</th>
              <th>Languages</th>
              <th>Status</th>
              <th>Created</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {#each tms as tm}
              {@const TMStatusIcon = getStatusIcon(tm.status)}
              {@const isActive = activeTmId === tm.id}
              <tr class:active-row={isActive}>
                <td class="name-cell">
                  <div class="name-with-indicator">
                    {#if isActive}
                      <CheckmarkFilled size={16} class="active-indicator" />
                    {/if}
                    <div>
                      <span class="tm-name">{tm.name}</span>
                      {#if tm.description}
                        <span class="tm-description">{tm.description}</span>
                      {/if}
                    </div>
                  </div>
                </td>
                <td class="count-cell">{formatCount(tm.entry_count)}</td>
                <td class="lang-cell">
                  <Tag size="sm" type="outline">{tm.source_lang?.toUpperCase() || 'KO'}</Tag>
                  <span class="arrow">→</span>
                  <Tag size="sm" type="outline">{tm.target_lang?.toUpperCase() || 'EN'}</Tag>
                </td>
                <td class="status-cell">
                  <Tag type={getStatusKind(tm.status)} size="sm">
                    {#if TMStatusIcon}
                      <TMStatusIcon size={12} />
                    {/if}
                    {tm.status}
                  </Tag>
                </td>
                <td class="date-cell">{formatDate(tm.created_at)}</td>
                <td class="actions-cell">
                  <!-- UI-003: Activate/Deactivate button -->
                  <Button
                    kind={isActive ? "primary" : "ghost"}
                    size="small"
                    icon={Power}
                    iconDescription={isActive ? "Deactivate TM" : "Activate TM"}
                    on:click={() => toggleActiveTm(tm)}
                  >
                    {isActive ? "Active" : "Activate"}
                  </Button>
                  {#if tm.status === 'pending' || tm.status === 'error'}
                    <Button
                      kind="ghost"
                      size="small"
                      icon={Renew}
                      iconDescription="Build Indexes"
                      disabled={buildingIndexes.has(tm.id)}
                      on:click={() => confirmBuildIndexes(tm)}
                    />
                  {/if}
                  <Button
                    kind="danger-ghost"
                    size="small"
                    icon={TrashCan}
                    iconDescription="Delete TM"
                    on:click={() => confirmDelete(tm)}
                  />
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  </div>
</Modal>

<!-- TM Upload Modal -->
<TMUploadModal
  bind:open={showUploadModal}
  on:uploaded={handleUploadComplete}
/>

<!-- Delete Confirmation Modal -->
<Modal
  bind:open={deleteConfirmOpen}
  modalHeading="Delete Translation Memory"
  primaryButtonText="Delete"
  secondaryButtonText="Cancel"
  danger
  on:click:button--primary={deleteTM}
  on:click:button--secondary={() => { deleteConfirmOpen = false; tmToDelete = null; }}
>
  {#if tmToDelete}
    <p>Are you sure you want to delete <strong>{tmToDelete.name}</strong>?</p>
    <p class="delete-warning">
      This will permanently delete {formatCount(tmToDelete.entry_count)} entries and all associated indexes.
    </p>
  {/if}
</Modal>

<!-- Build Indexes Confirmation Modal -->
<Modal
  bind:open={buildConfirmOpen}
  modalHeading="Build TM Indexes"
  primaryButtonText="Start Processing"
  secondaryButtonText="Cancel"
  on:click:button--primary={executeBuildIndexes}
  on:click:button--secondary={() => { buildConfirmOpen = false; tmToBuild = null; }}
>
  {#if tmToBuild}
    <p>Build semantic search indexes for <strong>{tmToBuild.name}</strong>?</p>
    <div class="build-warning">
      <p><WarningAlt size={16} style="display: inline; vertical-align: middle; margin-right: 4px;" />
        <strong>Resource Warning:</strong></p>
      <ul>
        <li>Processing <strong>{formatCount(tmToBuild.entry_count)}</strong> entries</li>
        <li>Uses AI model (Qwen) for embeddings</li>
        <li>Creates FAISS vector index</li>
        <li>May take several minutes for large TMs</li>
        <li>CPU/Memory usage will increase during processing</li>
      </ul>
      <p class="build-hint">Progress will be tracked in the Task Manager.</p>
    </div>
  {/if}
</Modal>

<style>
  .tm-manager {
    min-height: 300px;
  }

  .tm-toolbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid var(--cds-border-subtle-01);
  }

  .loading-container {
    display: flex;
    justify-content: center;
    padding: 2rem;
  }

  .empty-state {
    text-align: center;
    padding: 3rem 1rem;
    color: var(--cds-text-02);
  }

  .empty-state p {
    margin: 0;
  }

  .empty-hint {
    font-size: 0.875rem;
    margin-top: 0.5rem !important;
  }

  .tm-table {
    overflow-x: auto;
  }

  .tm-table table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.875rem;
  }

  .tm-table th {
    text-align: left;
    padding: 0.75rem 0.5rem;
    font-weight: 600;
    border-bottom: 2px solid var(--cds-border-subtle-01);
    color: var(--cds-text-01);
  }

  .tm-table td {
    padding: 0.75rem 0.5rem;
    border-bottom: 1px solid var(--cds-border-subtle-01);
    vertical-align: middle;
  }

  .tm-table tr:hover {
    background: var(--cds-layer-hover-01);
  }

  .name-cell {
    max-width: 200px;
  }

  /* UI-003: Active TM row styling */
  .active-row {
    background: var(--cds-layer-02) !important;
    border-left: 3px solid var(--cds-interactive-01);
  }

  .active-row:hover {
    background: var(--cds-layer-03) !important;
  }

  .name-with-indicator {
    display: flex;
    align-items: flex-start;
    gap: 0.5rem;
  }

  .name-with-indicator :global(.active-indicator) {
    color: var(--cds-interactive-01);
    flex-shrink: 0;
    margin-top: 2px;
  }

  .tm-name {
    display: block;
    font-weight: 500;
    color: var(--cds-text-01);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .tm-description {
    display: block;
    font-size: 0.75rem;
    color: var(--cds-text-02);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    margin-top: 0.125rem;
  }

  .count-cell {
    font-weight: 500;
    text-align: right;
    padding-right: 1rem !important;
  }

  .lang-cell {
    display: flex;
    align-items: center;
    gap: 0.25rem;
  }

  .arrow {
    color: var(--cds-text-02);
    font-size: 0.75rem;
  }

  .status-cell :global(.bx--tag) {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
  }

  .date-cell {
    color: var(--cds-text-02);
    white-space: nowrap;
  }

  .actions-cell {
    text-align: right;
    white-space: nowrap;
  }

  .delete-warning {
    margin-top: 0.5rem;
    font-size: 0.875rem;
    color: var(--cds-text-02);
  }

  .build-warning {
    margin-top: 1rem;
    padding: 1rem;
    background: var(--cds-notification-info-background);
    border-radius: 4px;
    font-size: 0.875rem;
  }

  .build-warning p {
    margin: 0 0 0.5rem 0;
  }

  .build-warning ul {
    margin: 0.5rem 0;
    padding-left: 1.5rem;
  }

  .build-warning li {
    margin: 0.25rem 0;
    color: var(--cds-text-02);
  }

  .build-hint {
    margin-top: 0.75rem !important;
    font-size: 0.75rem;
    color: var(--cds-text-02);
    font-style: italic;
  }
</style>
