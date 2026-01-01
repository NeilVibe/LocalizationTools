<script>
  /**
   * TMExplorerGrid.svelte - Phase 10 UI Overhaul
   *
   * Windows Explorer style grid for Translation Memories.
   * Matches the ExplorerGrid pattern for consistency.
   *
   * Keyboard shortcuts:
   * - Arrow Up/Down: Navigate TMs
   * - Enter: View entries
   * - Delete: Delete selected TM
   * - F2: Rename selected TM
   * - Home/End: Go to first/last TM
   */
  import { createEventDispatcher } from 'svelte';
  import { DataBase, CheckmarkFilled } from 'carbon-icons-svelte';
  import { Tag } from 'carbon-components-svelte';

  // Props
  let {
    items = [],           // Array of TM objects
    selectedId = null,    // Currently selected TM ID
    activeId = null,      // Active TM ID
    loading = false
  } = $props();

  const dispatch = createEventDispatcher();

  // Track grid body for focus management
  let gridBody = $state(null);

  /**
   * Format entry count
   */
  function formatEntries(count) {
    if (!count) return '0 entries';
    return `${count.toLocaleString()} entries`;
  }

  /**
   * Format date
   */
  function formatDate(dateStr) {
    if (!dateStr) return '';
    try {
      const date = new Date(dateStr);
      const now = new Date();
      const diff = now - date;

      if (diff < 86400000) {
        const hours = Math.floor(diff / 3600000);
        if (hours < 1) return 'Just now';
        return `${hours}h ago`;
      }

      if (diff < 604800000) {
        const days = Math.floor(diff / 86400000);
        return `${days}d ago`;
      }

      return date.toLocaleDateString();
    } catch {
      return '';
    }
  }

  /**
   * Handle single click (select)
   */
  function handleClick(tm) {
    dispatch('select', { tm });
  }

  /**
   * Handle double click (view entries)
   */
  function handleDoubleClick(tm) {
    dispatch('viewEntries', { tm });
  }

  /**
   * Handle right click (context menu)
   */
  function handleContextMenu(event, tm) {
    event.preventDefault();
    dispatch('contextMenu', { event, tm });
  }

  /**
   * Get current selected index
   */
  function getSelectedIndex() {
    if (!selectedId || items.length === 0) return -1;
    return items.findIndex(tm => tm.id === selectedId);
  }

  /**
   * Select TM by index and focus its row
   */
  function selectByIndex(index) {
    if (index < 0 || index >= items.length) return;
    const tm = items[index];
    dispatch('select', { tm });

    // Focus the row button
    if (gridBody) {
      const rows = gridBody.querySelectorAll('.grid-row');
      if (rows[index]) {
        rows[index].focus();
      }
    }
  }

  /**
   * Handle keyboard navigation
   */
  function handleKeydown(event, tm) {
    const currentIndex = getSelectedIndex();

    switch (event.key) {
      case 'Enter':
        handleDoubleClick(tm);
        break;

      case 'ArrowUp':
        event.preventDefault();
        if (currentIndex > 0) {
          selectByIndex(currentIndex - 1);
        }
        break;

      case 'ArrowDown':
        event.preventDefault();
        if (currentIndex < items.length - 1) {
          selectByIndex(currentIndex + 1);
        }
        break;

      case 'Home':
        event.preventDefault();
        selectByIndex(0);
        break;

      case 'End':
        event.preventDefault();
        selectByIndex(items.length - 1);
        break;

      case 'Delete':
        event.preventDefault();
        dispatch('delete', { tm });
        break;

      case 'F2':
        event.preventDefault();
        dispatch('rename', { tm });
        break;
    }
  }

  /**
   * Handle grid-level keydown
   */
  function handleGridKeydown(event) {
    if (items.length === 0) return;

    if (getSelectedIndex() === -1) {
      if (event.key === 'ArrowDown' || event.key === 'ArrowUp' || event.key === 'Home') {
        event.preventDefault();
        selectByIndex(0);
      } else if (event.key === 'End') {
        event.preventDefault();
        selectByIndex(items.length - 1);
      }
    }
  }
</script>

<div class="tm-explorer-grid" role="grid" aria-label="Translation Memories">
  {#if loading}
    <div class="loading-state">
      <span>Loading...</span>
    </div>
  {:else if items.length === 0}
    <div class="empty-state">
      <DataBase size={48} />
      <p>No Translation Memories</p>
      <span>Upload a TM to get started</span>
    </div>
  {:else}
    <!-- Header row -->
    <div class="grid-header" role="row">
      <div class="grid-cell name-cell" role="columnheader">Name</div>
      <div class="grid-cell entries-cell" role="columnheader">Entries</div>
      <div class="grid-cell status-cell" role="columnheader">Status</div>
      <div class="grid-cell date-cell" role="columnheader">Modified</div>
    </div>

    <!-- Items -->
    <div
      class="grid-body"
      bind:this={gridBody}
      onkeydown={handleGridKeydown}
      tabindex="-1"
    >
      {#each items as tm (tm.id)}
        {@const isActive = activeId === tm.id}
        <button
          class="grid-row"
          class:selected={selectedId === tm.id}
          class:active={isActive}
          role="row"
          onclick={() => handleClick(tm)}
          ondblclick={() => handleDoubleClick(tm)}
          oncontextmenu={(e) => handleContextMenu(e, tm)}
          onkeydown={(e) => handleKeydown(e, tm)}
        >
          <div class="grid-cell name-cell" role="gridcell">
            {#if isActive}
              <CheckmarkFilled size={20} class="tm-icon active-icon" />
            {:else}
              <DataBase size={20} class="tm-icon" />
            {/if}
            <span class="tm-name">{tm.name}</span>
            {#if isActive}
              <Tag type="green" size="sm">Active</Tag>
            {/if}
          </div>
          <div class="grid-cell entries-cell" role="gridcell">
            {formatEntries(tm.entry_count)}
          </div>
          <div class="grid-cell status-cell" role="gridcell">
            {#if tm.status === 'ready'}
              <span class="status-ready">Ready</span>
            {:else if tm.status === 'indexing'}
              <span class="status-indexing">Indexing...</span>
            {:else}
              <span class="status-pending">Pending</span>
            {/if}
          </div>
          <div class="grid-cell date-cell" role="gridcell">
            {formatDate(tm.updated_at || tm.created_at)}
          </div>
        </button>
      {/each}
    </div>
  {/if}
</div>

<style>
  .tm-explorer-grid {
    display: flex;
    flex-direction: column;
    width: 100%;
    height: 100%;
    flex: 1; /* Expand in flex container */
    min-height: 0; /* Allow flex shrink */
    overflow: hidden;
    background: var(--cds-background);
  }

  .loading-state,
  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    flex: 1;
    padding: 2rem;
    color: var(--cds-text-02);
  }

  .empty-state p {
    margin: 1rem 0 0.25rem;
    font-size: 1rem;
    font-weight: 500;
    color: var(--cds-text-01);
  }

  .empty-state span {
    font-size: 0.875rem;
  }

  /* Grid header */
  .grid-header {
    display: flex;
    padding: 0.5rem 1rem;
    background: var(--cds-layer-01);
    border-bottom: 1px solid var(--cds-border-subtle-01);
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    color: var(--cds-text-02);
    user-select: none;
  }

  /* Grid body */
  .grid-body {
    flex: 1;
    overflow-y: auto;
    overflow-x: hidden;
  }

  /* Grid row */
  .grid-row {
    display: flex;
    width: 100%;
    padding: 0.75rem 1rem;
    background: transparent;
    border: none;
    border-bottom: 1px solid var(--cds-border-subtle-01);
    cursor: pointer;
    text-align: left;
    transition: background 0.1s ease;
  }

  .grid-row:hover {
    background: var(--cds-layer-hover-01);
  }

  .grid-row:focus {
    outline: 2px solid var(--cds-focus);
    outline-offset: -2px;
  }

  .grid-row.selected {
    background: var(--cds-layer-selected-01);
  }

  .grid-row.active {
    border-left: 3px solid var(--cds-support-success);
  }

  /* Grid cells */
  .grid-cell {
    display: flex;
    align-items: center;
    overflow: hidden;
  }

  .name-cell {
    flex: 1;
    min-width: 200px;
    gap: 0.75rem;
  }

  .entries-cell {
    width: 120px;
    color: var(--cds-text-02);
    font-size: 0.875rem;
  }

  .status-cell {
    width: 100px;
    font-size: 0.875rem;
  }

  .date-cell {
    width: 100px;
    color: var(--cds-text-02);
    font-size: 0.875rem;
  }

  /* TM styling */
  .tm-icon {
    flex-shrink: 0;
    color: var(--cds-icon-secondary);
  }

  .tm-icon.active-icon {
    color: var(--cds-support-success);
  }

  .tm-name {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--cds-text-01);
  }

  /* Status colors */
  .status-ready {
    color: var(--cds-support-success);
  }

  .status-indexing {
    color: var(--cds-support-warning);
  }

  .status-pending {
    color: var(--cds-text-02);
  }

  /* Responsive */
  @media (max-width: 768px) {
    .date-cell {
      display: none;
    }
  }

  @media (max-width: 600px) {
    .status-cell {
      display: none;
    }
  }
</style>
