<script>
  /**
   * PropertiesPanel.svelte - Phase 10 UI Overhaul
   *
   * Shows details/properties of the selected item.
   * Similar to Windows Explorer properties panel.
   */
  import { Folder, Document, DataBase, Close } from 'carbon-icons-svelte';

  // Props
  let {
    item = null,        // Selected item (file, folder, project, or TM)
    type = 'file',      // 'file' | 'tm' - determines which properties to show
    onClose = null      // Callback to close panel
  } = $props();

  /**
   * Format date for display
   */
  function formatDate(dateStr) {
    if (!dateStr) return '-';
    try {
      const date = new Date(dateStr);
      return date.toLocaleString();
    } catch {
      return '-';
    }
  }

  /**
   * Get icon for item
   */
  function getIcon() {
    if (!item) return Document;
    if (type === 'tm') return DataBase;
    if (item.type === 'folder' || item.type === 'project') return Folder;
    return Document;
  }

  /**
   * Format file size/count
   */
  function formatSize() {
    if (!item) return '-';
    if (type === 'tm') {
      return `${(item.entry_count || 0).toLocaleString()} entries`;
    }
    if (item.type === 'folder' || item.type === 'project') {
      const count = item.file_count || 0;
      return count === 1 ? '1 item' : `${count} items`;
    }
    if (item.row_count) {
      return `${item.row_count.toLocaleString()} rows`;
    }
    return '-';
  }

  // Reactive icon
  const Icon = $derived(getIcon());
</script>

{#if item}
  <div class="properties-panel">
    <div class="panel-header">
      <h3>Properties</h3>
      {#if onClose}
        <button class="close-button" onclick={onClose} aria-label="Close properties">
          <Close size={16} />
        </button>
      {/if}
    </div>

    <div class="panel-content">
      <!-- Item preview -->
      <div class="item-preview">
        <div class="item-icon">
          <Icon size={48} />
        </div>
        <div class="item-name">{item.name || 'Unnamed'}</div>
        <div class="item-type">
          {#if type === 'tm'}
            Translation Memory
          {:else if item.type === 'project'}
            Project
          {:else if item.type === 'folder'}
            Folder
          {:else}
            {(item.format || 'File').toUpperCase()} File
          {/if}
        </div>
      </div>

      <!-- Properties list -->
      <div class="properties-list">
        <div class="property-item">
          <span class="property-label">Size</span>
          <span class="property-value">{formatSize()}</span>
        </div>

        {#if type === 'tm'}
          <div class="property-item">
            <span class="property-label">Status</span>
            <span class="property-value status-{item.status || 'pending'}">
              {item.status === 'ready' ? 'Ready' : item.status === 'indexing' ? 'Indexing' : 'Pending'}
            </span>
          </div>
          <div class="property-item">
            <span class="property-label">Active</span>
            <span class="property-value">{item.is_active ? 'Yes' : 'No'}</span>
          </div>
        {:else if item.format}
          <div class="property-item">
            <span class="property-label">Format</span>
            <span class="property-value">{item.format.toUpperCase()}</span>
          </div>
        {/if}

        <div class="property-item">
          <span class="property-label">Created</span>
          <span class="property-value">{formatDate(item.created_at)}</span>
        </div>

        <div class="property-item">
          <span class="property-label">Modified</span>
          <span class="property-value">{formatDate(item.updated_at || item.created_at)}</span>
        </div>

        {#if item.id}
          <div class="property-item">
            <span class="property-label">ID</span>
            <span class="property-value id-value">{item.id}</span>
          </div>
        {/if}
      </div>
    </div>
  </div>
{:else}
  <div class="properties-panel empty">
    <div class="panel-header">
      <h3>Properties</h3>
      {#if onClose}
        <button class="close-button" onclick={onClose} aria-label="Close properties">
          <Close size={16} />
        </button>
      {/if}
    </div>
    <div class="empty-message">
      <p>Select an item to view its properties</p>
    </div>
  </div>
{/if}

<style>
  .properties-panel {
    display: flex;
    flex-direction: column;
    width: 280px;
    height: 100%;
    background: var(--cds-layer-01);
    border-left: 1px solid var(--cds-border-subtle-01);
  }

  .panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.75rem 1rem;
    border-bottom: 1px solid var(--cds-border-subtle-01);
  }

  .panel-header h3 {
    margin: 0;
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--cds-text-01);
  }

  .close-button {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    padding: 0;
    background: transparent;
    border: none;
    color: var(--cds-text-02);
    cursor: pointer;
    border-radius: 2px;
  }

  .close-button:hover {
    background: var(--cds-layer-hover-01);
    color: var(--cds-text-01);
  }

  .panel-content {
    flex: 1;
    overflow-y: auto;
    padding: 1rem;
  }

  /* Item preview */
  .item-preview {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 1.5rem 0;
    border-bottom: 1px solid var(--cds-border-subtle-01);
    margin-bottom: 1rem;
  }

  .item-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 80px;
    height: 80px;
    margin-bottom: 1rem;
    background: var(--cds-layer-02);
    border-radius: 8px;
    color: var(--cds-icon-secondary);
  }

  .item-name {
    font-size: 1rem;
    font-weight: 600;
    color: var(--cds-text-01);
    text-align: center;
    word-break: break-word;
  }

  .item-type {
    margin-top: 0.25rem;
    font-size: 0.75rem;
    color: var(--cds-text-02);
    text-transform: uppercase;
  }

  /* Properties list */
  .properties-list {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .property-item {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 1rem;
  }

  .property-label {
    font-size: 0.75rem;
    color: var(--cds-text-02);
    text-transform: uppercase;
    flex-shrink: 0;
  }

  .property-value {
    font-size: 0.875rem;
    color: var(--cds-text-01);
    text-align: right;
    word-break: break-word;
  }

  .property-value.id-value {
    font-family: monospace;
    font-size: 0.75rem;
    color: var(--cds-text-02);
  }

  /* Status colors */
  .property-value.status-ready {
    color: var(--cds-support-success);
  }

  .property-value.status-indexing {
    color: var(--cds-support-warning);
  }

  .property-value.status-pending {
    color: var(--cds-text-02);
  }

  /* Empty state */
  .properties-panel.empty .panel-content,
  .empty-message {
    display: flex;
    align-items: center;
    justify-content: center;
    flex: 1;
  }

  .empty-message p {
    color: var(--cds-text-02);
    font-size: 0.875rem;
    text-align: center;
  }
</style>
