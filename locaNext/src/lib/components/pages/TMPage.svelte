<script>
  /**
   * TMPage.svelte - Phase 10 UI Overhaul
   *
   * Clean Windows Explorer style Translation Memory management.
   * Everything through context menu and double-click.
   * No ugly buttons, no prompt/confirm dialogs.
   */
  import { createEventDispatcher, onMount } from 'svelte';
  import { Slider } from 'carbon-components-svelte';
  import {
    CheckmarkFilled,
    TrashCan,
    Download,
    View,
    Settings,
    Upload
  } from 'carbon-icons-svelte';
  import { preferences } from '$lib/stores/preferences.js';
  import { logger } from '$lib/utils/logger.js';
  import { getAuthHeaders, getApiBase } from '$lib/utils/api.js';
  import { openTMInGrid } from '$lib/stores/navigation.js';
  import TMExplorerGrid from '$lib/components/ldm/TMExplorerGrid.svelte';
  import TMUploadModal from '$lib/components/ldm/TMUploadModal.svelte';
  import ConfirmModal from '$lib/components/common/ConfirmModal.svelte';

  // Props
  let {
    selectedTMId = $bindable(null)
  } = $props();

  const dispatch = createEventDispatcher();
  const API_BASE = getApiBase();

  // State
  let tmList = $state([]);
  let tmLoading = $state(false);
  let activeTmId = $state(null);
  let showSettings = $state(false);
  let selectedTM = $state(null);

  // Component reference
  let tmGridRef = $state(null);

  // Modals
  let showUploadModal = $state(false);
  let uploadTargetScope = $state(null);  // Sprint 5: Target scope for upload

  // Context menu
  let contextMenu = $state({ show: false, x: 0, y: 0, tm: null, isBackground: false });

  // Confirm modal
  let confirmModal = $state({ open: false, title: '', message: '', action: null, tm: null });

  // ========================================
  // Data Loading
  // ========================================

  async function loadTMs() {
    tmLoading = true;
    try {
      logger.apiCall('/api/ldm/tm', 'GET');
      const response = await fetch(`${API_BASE}/api/ldm/tm`, {
        headers: getAuthHeaders()
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const data = await response.json();
      tmList = Array.isArray(data) ? data : (data.tms || []);

      const activeTM = tmList.find(tm => tm.is_active);
      activeTmId = activeTM?.id || null;

      logger.success('TMs loaded', { count: tmList.length });
    } catch (err) {
      logger.error('Failed to load TMs', { error: err.message });
      tmList = [];
    } finally {
      tmLoading = false;
    }
  }

  // ========================================
  // TM Operations
  // ========================================

  function selectTM(tm) {
    selectedTMId = tm.id;
    selectedTM = tm;
    dispatch('tmSelect', { tmId: tm.id, tm });
  }

  async function activateTM(tm) {
    try {
      logger.apiCall(`/api/ldm/tm/${tm.id}/activate`, 'POST');
      const response = await fetch(`${API_BASE}/api/ldm/tm/${tm.id}/activate`, {
        method: 'POST',
        headers: getAuthHeaders()
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      activeTmId = tm.id;
      logger.success('TM activated', { tmId: tm.id });
      await loadTMs();
    } catch (err) {
      logger.error('Failed to activate TM', { error: err.message });
    }
    closeContextMenu();
  }

  function showDeleteModal(tm) {
    closeContextMenu();
    confirmModal = {
      open: true,
      title: 'Delete Translation Memory',
      message: `Are you sure you want to delete "${tm.name}"? This will permanently remove ${tm.entry_count?.toLocaleString() || 0} entries.`,
      action: 'delete',
      tm
    };
  }

  async function handleConfirm() {
    if (confirmModal.action === 'delete' && confirmModal.tm) {
      await deleteTM(confirmModal.tm);
    }
  }

  async function deleteTM(tm) {
    try {
      logger.apiCall(`/api/ldm/tm/${tm.id}`, 'DELETE');
      const response = await fetch(`${API_BASE}/api/ldm/tm/${tm.id}`, {
        method: 'DELETE',
        headers: getAuthHeaders()
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      logger.success('TM deleted', { tmId: tm.id });
      await loadTMs();
    } catch (err) {
      logger.error('Failed to delete TM', { error: err.message });
    }
  }

  async function exportTM(tm) {
    try {
      logger.apiCall(`/api/ldm/tm/${tm.id}/export`, 'GET');
      const response = await fetch(`${API_BASE}/api/ldm/tm/${tm.id}/export`, {
        headers: getAuthHeaders()
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${tm.name}.tsv`;
      a.click();
      URL.revokeObjectURL(url);

      logger.success('TM exported', { tmId: tm.id });
    } catch (err) {
      logger.error('Failed to export TM', { error: err.message });
    }
    closeContextMenu();
  }

  function viewTM(tm) {
    // Navigate to full-page TM entries viewer
    openTMInGrid(tm);
    closeContextMenu();
  }

  // ========================================
  // Context Menu
  // ========================================

  function openContextMenu(event, tm) {
    event.preventDefault();
    contextMenu = {
      show: true,
      x: event.clientX,
      y: event.clientY,
      tm,
      isBackground: false
    };
  }

  function handleBackgroundContextMenu(event) {
    event.preventDefault();
    contextMenu = {
      show: true,
      x: event.clientX,
      y: event.clientY,
      tm: null,
      isBackground: true
    };
  }

  function closeContextMenu() {
    contextMenu = { show: false, x: 0, y: 0, tm: null, isBackground: false };
  }

  // ========================================
  // Event Handlers
  // ========================================

  function toggleSettings() {
    showSettings = !showSettings;
  }

  function handleUploadComplete() {
    showUploadModal = false;
    loadTMs();
    // Refresh grid after upload
    if (tmGridRef?.reload) {
      tmGridRef.reload();
    }
  }

  function handleTMSelect(tm) {
    selectedTMId = tm.tm_id;
    selectedTM = tm;
    dispatch('tmSelect', { tmId: tm.tm_id, tm });
  }

  function handleViewEntries(tm) {
    // Navigate to full-page TM entries viewer
    openTMInGrid({ id: tm.tm_id, name: tm.tm_name });
  }

  function handleGlobalClick(event) {
    if (contextMenu.show && !event.target.closest('.context-menu')) {
      closeContextMenu();
    }
  }

  onMount(() => {
    loadTMs();
    document.addEventListener('click', handleGlobalClick);
    return () => document.removeEventListener('click', handleGlobalClick);
  });
</script>

<div class="tm-page">
  <!-- Clean header -->
  <div class="tm-page-header">
    <div class="header-title">
      <h2>Translation Memories</h2>
    </div>
    <div class="header-actions">
      <button
        class="icon-button"
        onclick={() => showUploadModal = true}
        title="Upload TM"
      >
        <Upload size={20} />
      </button>
      <button
        class="icon-button"
        onclick={toggleSettings}
        title="Settings"
      >
        <Settings size={20} />
      </button>
    </div>
  </div>

  <!-- Main Content -->
  <div class="tm-content">
    <!-- TM Explorer Grid (Windows Explorer style - UI-108) -->
    <div class="tm-explorer">
      <TMExplorerGrid
        bind:this={tmGridRef}
        bind:selectedTMId={selectedTMId}
        onTMSelect={handleTMSelect}
        onViewEntries={handleViewEntries}
        onUploadTM={(scope) => {
          uploadTargetScope = scope || null;  // Sprint 5: Store target scope
          showUploadModal = true;
        }}
      />
    </div>

    <!-- Settings Panel (collapsible) -->
    {#if showSettings}
      <div class="tm-settings-panel">
        <div class="settings-header">
          <h3>Settings</h3>
          <button class="close-settings" onclick={toggleSettings}>×</button>
        </div>
        <div class="setting-item">
          <div class="setting-header">
            <span class="setting-label">Match Threshold</span>
            <span class="setting-value">{Math.round($preferences.tmThreshold * 100)}%</span>
          </div>
          <Slider
            min={50}
            max={100}
            value={Math.round($preferences.tmThreshold * 100)}
            step={1}
            hideTextInput={true}
            on:change={(e) => preferences.setTmThreshold(e.detail / 100)}
          />
          <p class="setting-hint">Minimum similarity for TM matches</p>
        </div>
      </div>
    {/if}
  </div>
</div>

<!-- Context menu handled by TMExplorerGrid -->

<!-- Upload Modal -->
<TMUploadModal
  bind:open={showUploadModal}
  targetScope={uploadTargetScope}
  on:uploaded={(e) => {
    uploadTargetScope = null;  // Reset scope after upload
    handleUploadComplete(e);
  }}
  on:close={() => uploadTargetScope = null}
/>

<!-- TM Viewer removed - now uses full-page navigation via openTMInGrid -->

<!-- Confirm Modal (Delete) -->
<ConfirmModal
  bind:open={confirmModal.open}
  title={confirmModal.title}
  message={confirmModal.message}
  confirmLabel="Delete"
  danger={true}
  onConfirm={handleConfirm}
/>

<style>
  .tm-page {
    display: flex;
    flex-direction: column;
    width: 100%;
    height: 100%;
    background: var(--cds-background);
  }

  .tm-page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.5rem 1rem;
    border-bottom: 1px solid var(--cds-border-subtle-01);
    background: var(--cds-layer-01);
  }

  .header-title h2 {
    margin: 0;
    font-size: 1rem;
    font-weight: 600;
    color: var(--cds-text-01);
  }

  .header-actions {
    display: flex;
    gap: 0.5rem;
  }

  .icon-button {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    padding: 0;
    background: transparent;
    border: none;
    border-radius: 4px;
    color: var(--cds-icon-secondary);
    cursor: pointer;
  }

  .icon-button:hover {
    background: var(--cds-layer-hover-01);
    color: var(--cds-icon-primary);
  }

  .tm-content {
    flex: 1;
    min-height: 0; /* Allow flex shrink */
    display: flex;
    overflow: hidden;
  }

  .tm-explorer {
    flex: 1;
    min-height: 0; /* Allow flex shrink */
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }

  /* Settings Panel */
  .tm-settings-panel {
    width: 280px;
    padding: 1rem;
    background: var(--cds-layer-01);
    border-left: 1px solid var(--cds-border-subtle-01);
    overflow-y: auto;
  }

  .settings-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
  }

  .tm-settings-panel h3 {
    margin: 0;
    font-size: 0.875rem;
    font-weight: 600;
    text-transform: uppercase;
    color: var(--cds-text-02);
  }

  .close-settings {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    padding: 0;
    background: transparent;
    border: none;
    font-size: 1.25rem;
    color: var(--cds-text-02);
    cursor: pointer;
  }

  .close-settings:hover {
    color: var(--cds-text-01);
  }

  .setting-item {
    margin-bottom: 1rem;
  }

  .setting-header {
    display: flex;
    justify-content: space-between;
    margin-bottom: 0.5rem;
  }

  .setting-label {
    font-size: 0.875rem;
    color: var(--cds-text-01);
  }

  .setting-value {
    font-weight: 600;
    color: var(--cds-text-01);
  }

  .setting-hint {
    margin: 0.5rem 0 0;
    font-size: 0.75rem;
    color: var(--cds-text-02);
  }

  /* Context Menu */
  .context-menu {
    position: fixed;
    z-index: 9999;
    min-width: 160px;
    background: var(--cds-layer-01);
    border: 1px solid var(--cds-border-subtle-01);
    border-radius: 4px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
    overflow: hidden;
  }

  .context-menu-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    width: 100%;
    padding: 0.75rem 1rem;
    background: transparent;
    border: none;
    color: var(--cds-text-01);
    font-size: 0.875rem;
    cursor: pointer;
    text-align: left;
  }

  .context-menu-item:hover {
    background: var(--cds-layer-hover-01);
  }

  .context-menu-item.danger {
    color: var(--cds-support-error);
  }

  .context-menu-divider {
    height: 1px;
    background: var(--cds-border-subtle-01);
    margin: 0.25rem 0;
  }
</style>
