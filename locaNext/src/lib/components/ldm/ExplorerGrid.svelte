<script>
  /**
   * ExplorerGrid.svelte - Phase 10 UI Overhaul
   *
   * Windows/SharePoint style file explorer grid.
   * Shows folders and files in flat list with metadata.
   * Double-click to enter folder or open file.
   *
   * Keyboard shortcuts:
   * - Arrow Up/Down: Navigate items
   * - Enter: Open/enter selected item
   * - Backspace: Go up one level
   * - Delete: Delete selected item
   * - F2: Rename selected item
   * - Home/End: Go to first/last item
   */
  import { createEventDispatcher } from 'svelte';
  import { Folder, Document, DocumentBlank, Table, Code, Application, Locked, TrashCan, CloudOffline } from 'carbon-icons-svelte';

  // Props
  let {
    items = [],           // Array of { type: 'folder'|'file', id, name, ...metadata }
    selectedId = null,    // Currently selected item ID (single)
    selectedIds = $bindable([]), // Multi-select IDs
    loading = false,
    isItemCut = () => false  // EXPLORER-001: Function to check if item is cut
  } = $props();

  const dispatch = createEventDispatcher();

  // Track grid container for focus management
  let gridBody = $state(null);

  // Multi-select state
  let lastSelectedIndex = $state(-1);

  // Drag-drop state
  let draggedItems = $state([]);
  let dropTargetId = $state(null);
  let isDragging = $state(false);

  /**
   * Get icon for item based on type/format
   */
  function getIcon(item) {
    if (item.type === 'platform') return Application;
    if (item.type === 'folder') return Folder;
    if (item.type === 'local-folder') return Folder;  // P9: Local folder in Offline Storage
    if (item.type === 'project') return Folder;
    // EXPLORER-008: Recycle Bin types
    if (item.type === 'recycle-bin') return TrashCan;
    if (item.type === 'trash-item') {
      // Show icon based on original item type
      if (item.item_type === 'platform') return Application;
      if (item.item_type === 'project') return Folder;
      if (item.item_type === 'folder') return Folder;
      return Document; // file
    }
    // P9: Offline Storage types
    if (item.type === 'offline-storage') return CloudOffline;
    if (item.type === 'local-file') return Document;

    // File icons based on format
    const format = (item.format || item.name?.split('.').pop() || '').toLowerCase();
    switch (format) {
      case 'xlsx':
      case 'xls':
        return Table;
      case 'xml':
      case 'tmx':
        return Code;
      case 'txt':
      case 'tsv':
      default:
        return Document;
    }
  }

  /**
   * Format file size
   */
  function formatSize(item) {
    if (item.type === 'platform') {
      const count = item.project_count || 0;
      return count === 1 ? '1 project' : `${count} projects`;
    }
    if (item.type === 'folder' || item.type === 'local-folder' || item.type === 'project') {
      const count = item.file_count || item.children?.length || 0;
      return count === 1 ? '1 item' : `${count} items`;
    }
    // EXPLORER-008: Recycle Bin types
    if (item.type === 'recycle-bin') {
      return 'Deleted items';
    }
    if (item.type === 'trash-item') {
      return `Deleted ${item.item_type}`;
    }
    // P3-PHASE5: Offline Storage types
    if (item.type === 'offline-storage') {
      const count = item.file_count || 0;
      // P9: User-friendly text, avoid technical "orphaned" term
      return count === 0 ? 'Empty' : count === 1 ? '1 file' : `${count} files`;
    }
    if (item.type === 'local-file') {
      // P9: Show row count for local files (they're editable in offline mode)
      if (item.row_count) {
        return `${item.row_count.toLocaleString()} rows`;
      }
      return item.error_message || 'Empty file';
    }
    if (item.row_count) {
      return `${item.row_count.toLocaleString()} rows`;
    }
    return '';
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

      // Less than 24 hours
      if (diff < 86400000) {
        const hours = Math.floor(diff / 3600000);
        if (hours < 1) return 'Just now';
        return `${hours}h ago`;
      }

      // Less than 7 days
      if (diff < 604800000) {
        const days = Math.floor(diff / 86400000);
        return `${days}d ago`;
      }

      // Older - show date
      return date.toLocaleDateString();
    } catch {
      return '';
    }
  }

  /**
   * Handle single click (select with multi-select support)
   */
  function handleClick(event, item) {
    const index = items.findIndex(i => i.id === item.id);

    if (event.ctrlKey || event.metaKey) {
      // Ctrl+click: toggle selection
      if (selectedIds.includes(item.id)) {
        selectedIds = selectedIds.filter(id => id !== item.id);
      } else {
        selectedIds = [...selectedIds, item.id];
      }
      lastSelectedIndex = index;
    } else if (event.shiftKey && lastSelectedIndex >= 0) {
      // Shift+click: range selection
      const start = Math.min(lastSelectedIndex, index);
      const end = Math.max(lastSelectedIndex, index);
      const rangeIds = items.slice(start, end + 1).map(i => i.id);
      selectedIds = [...new Set([...selectedIds, ...rangeIds])];
    } else {
      // Normal click: single select
      selectedIds = [item.id];
      lastSelectedIndex = index;
    }

    dispatch('select', { item, selectedIds });
  }

  /**
   * Check if item is selected
   */
  function isSelected(item) {
    return selectedIds.includes(item.id) || selectedId === item.id;
  }

  /**
   * Handle double click (open/enter)
   */
  function handleDoubleClick(item) {
    if (item.type === 'folder' || item.type === 'local-folder' || item.type === 'project' || item.type === 'platform' || item.type === 'recycle-bin' || item.type === 'offline-storage') {
      dispatch('enterFolder', { item });
    } else if (item.type === 'trash-item') {
      // EXPLORER-008: Double-click on trash item does nothing (use context menu to restore)
      return;
    } else if (item.type === 'local-file') {
      // P9: Local files ARE openable - they're real files in Offline Storage
      dispatch('openFile', { item });
    } else {
      dispatch('openFile', { item });
    }
  }

  // ============== Drag and Drop ==============

  /**
   * Handle drag start
   */
  function handleDragStart(event, item) {
    // If dragging a non-selected item, select it first
    if (!isSelected(item)) {
      selectedIds = [item.id];
    }

    // Get all selected items for dragging
    draggedItems = items.filter(i => selectedIds.includes(i.id));
    isDragging = true;

    // Set drag data
    event.dataTransfer.effectAllowed = 'move';
    event.dataTransfer.setData('text/plain', JSON.stringify(draggedItems.map(i => ({ id: i.id, type: i.type, name: i.name }))));

    // Visual feedback
    event.target.classList.add('dragging');
  }

  /**
   * Handle drag end
   */
  function handleDragEnd(event) {
    isDragging = false;
    draggedItems = [];
    dropTargetId = null;
    event.target.classList.remove('dragging');
  }

  /**
   * Handle drag over (for drop targets)
   */
  function handleDragOver(event, item) {
    // Folders, projects, and platforms can be drop targets
    if (item.type !== 'folder' && item.type !== 'project' && item.type !== 'platform') return;

    // Can't drop on self
    if (draggedItems.some(d => d.id === item.id)) return;

    // Platforms can only accept projects (not files or folders)
    if (item.type === 'platform') {
      const hasNonProject = draggedItems.some(d => d.type !== 'project');
      if (hasNonProject) return;
    }

    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
    dropTargetId = item.id;
  }

  /**
   * Handle drag leave
   */
  function handleDragLeave(event, item) {
    if (dropTargetId === item.id) {
      dropTargetId = null;
    }
  }

  /**
   * Handle drop
   */
  function handleDrop(event, targetItem) {
    event.preventDefault();

    if (targetItem.type !== 'folder' && targetItem.type !== 'project' && targetItem.type !== 'platform') return;
    if (draggedItems.length === 0) return;

    // Platforms can only accept projects
    if (targetItem.type === 'platform') {
      const projectsOnly = draggedItems.filter(d => d.type === 'project');
      if (projectsOnly.length === 0) return;

      // Dispatch assignToPlatform event for projects dropped on platforms
      dispatch('assignToPlatform', {
        projects: projectsOnly,
        platform: targetItem
      });
    } else {
      // Dispatch move event with items to move and target folder
      dispatch('moveItems', {
        items: draggedItems,
        targetFolder: targetItem
      });
    }

    // Reset state
    isDragging = false;
    draggedItems = [];
    dropTargetId = null;
  }

  /**
   * Handle right click on item (context menu)
   */
  function handleContextMenu(event, item) {
    event.preventDefault();
    event.stopPropagation();
    dispatch('contextMenu', { event, item });
  }

  /**
   * Handle right click on empty space (background context menu)
   */
  function handleBackgroundContextMenu(event) {
    // Only trigger if clicking on grid body background, not on a row
    if (event.target.closest('.grid-row')) return;
    event.preventDefault();
    dispatch('backgroundContextMenu', { event });
  }

  /**
   * Get current selected index
   */
  function getSelectedIndex() {
    if (!selectedId || items.length === 0) return -1;
    return items.findIndex(item => item.id === selectedId);
  }

  /**
   * Select item by index and focus its row
   */
  function selectByIndex(index) {
    if (index < 0 || index >= items.length) return;
    const item = items[index];
    dispatch('select', { item });

    // Focus the row button
    if (gridBody) {
      const rows = gridBody.querySelectorAll('.grid-row');
      if (rows[index]) {
        rows[index].focus();
      }
    }
  }

  /**
   * Handle keyboard navigation on individual row
   */
  function handleKeydown(event, item) {
    const currentIndex = getSelectedIndex();

    switch (event.key) {
      case 'Enter':
        handleDoubleClick(item);
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

      case 'Backspace':
        event.preventDefault();
        dispatch('goUp');
        break;

      case 'Delete':
        event.preventDefault();
        dispatch('delete', { item });
        break;

      case 'F2':
        event.preventDefault();
        dispatch('rename', { item });
        break;
    }
  }

  /**
   * Handle grid-level keydown (when grid has focus but no row selected)
   */
  function handleGridKeydown(event) {
    if (items.length === 0) return;

    // If no item selected and arrow key pressed, select first item
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

<div class="explorer-grid" role="grid" aria-label="File explorer" oncontextmenu={handleBackgroundContextMenu}>
  {#if loading}
    <div class="loading-state">
      <span>Loading...</span>
    </div>
  {:else if items.length === 0}
    <div class="empty-state">
      <DocumentBlank size={48} />
      <p>This folder is empty</p>
      <span>Right-click to create a new folder or upload files</span>
    </div>
  {:else}
    <!-- Header row -->
    <div class="grid-header" role="row">
      <div class="grid-cell name-cell" role="columnheader">Name</div>
      <div class="grid-cell size-cell" role="columnheader">Size</div>
      <div class="grid-cell date-cell" role="columnheader">Modified</div>
      <div class="grid-cell type-cell" role="columnheader">Type</div>
    </div>

    <!-- Items -->
    <div
      class="grid-body"
      bind:this={gridBody}
      onkeydown={handleGridKeydown}
      tabindex="-1"
    >
      {#each items as item (`${item.type}-${item.id}`)}
        {@const Icon = getIcon(item)}
        <button
          class="grid-row"
          class:selected={isSelected(item)}
          class:folder={item.type === 'folder' || item.type === 'local-folder'}
          class:project={item.type === 'project'}
          class:platform={item.type === 'platform'}
          class:drop-target={dropTargetId === item.id}
          class:dragging={isDragging && isSelected(item)}
          class:cut={isItemCut(item.id)}
          role="row"
          draggable="true"
          onclick={(e) => handleClick(e, item)}
          ondblclick={() => handleDoubleClick(item)}
          oncontextmenu={(e) => handleContextMenu(e, item)}
          onkeydown={(e) => handleKeydown(e, item)}
          ondragstart={(e) => handleDragStart(e, item)}
          ondragend={handleDragEnd}
          ondragover={(e) => handleDragOver(e, item)}
          ondragleave={(e) => handleDragLeave(e, item)}
          ondrop={(e) => handleDrop(e, item)}
        >
          <div class="grid-cell name-cell" role="gridcell">
            <Icon size={20} class="item-icon" />
            <span class="item-name">{item.name}</span>
            {#if item.is_restricted}
              <span class="restricted-badge" title="Restricted - Admin managed access">
                <Locked size={14} />
              </span>
            {/if}
          </div>
          <div class="grid-cell size-cell" role="gridcell">
            {formatSize(item)}
          </div>
          <div class="grid-cell date-cell" role="gridcell">
            {formatDate(item.updated_at || item.created_at)}
          </div>
          <div class="grid-cell type-cell" role="gridcell">
            {#if item.type === 'folder' || item.type === 'local-folder'}
              Folder
            {:else if item.type === 'project'}
              Project
            {:else}
              {(item.format || 'File').toUpperCase()}
            {/if}
          </div>
        </button>
      {/each}
    </div>
  {/if}
</div>

<style>
  .explorer-grid {
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
    padding: 0.625rem 1rem;
    background: transparent;
    border: none;
    border-bottom: 1px solid var(--cds-border-subtle-01, #393939);
    cursor: pointer;
    text-align: left;
    transition: background 0.15s ease;
    font-family: inherit;
    font-size: inherit;
    color: inherit;
  }

  .grid-row:hover {
    background: var(--cds-layer-hover-01, rgba(141, 141, 141, 0.16));
  }

  .grid-row:focus {
    outline: 2px solid var(--cds-focus, #0f62fe);
    outline-offset: -2px;
  }

  .grid-row.selected {
    background: var(--cds-layer-selected-01, rgba(141, 141, 141, 0.24));
  }

  .grid-row.selected:hover {
    background: var(--cds-layer-selected-hover-01, rgba(141, 141, 141, 0.32));
  }

  /* Drag and drop states */
  .grid-row.dragging {
    opacity: 0.5;
    background: rgba(100, 100, 100, 0.3);
  }

  /* EXPLORER-001: Cut items (waiting for paste) */
  .grid-row.cut {
    opacity: 0.5;
    background: repeating-linear-gradient(
      45deg,
      transparent,
      transparent 10px,
      rgba(100, 100, 100, 0.1) 10px,
      rgba(100, 100, 100, 0.1) 20px
    );
  }

  .grid-row.cut:hover {
    opacity: 0.6;
  }

  .grid-row.cut .item-name {
    font-style: italic;
  }

  .grid-row.drop-target {
    background: rgba(15, 98, 254, 0.25) !important;
    outline: 2px dashed var(--cds-link-01, #78a9ff);
    outline-offset: -2px;
  }

  .grid-row.drop-target :global(.item-icon) {
    color: var(--cds-link-01, #78a9ff);
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

  .size-cell {
    width: 100px;
    color: var(--cds-text-02);
    font-size: 0.875rem;
  }

  .date-cell {
    width: 100px;
    color: var(--cds-text-02);
    font-size: 0.875rem;
  }

  .type-cell {
    width: 80px;
    color: var(--cds-text-02);
    font-size: 0.75rem;
    text-transform: uppercase;
  }

  /* Item styling - use :global for Carbon icons */
  .grid-row :global(.item-icon) {
    flex-shrink: 0;
    color: #a8b0b8; /* Light gray for files */
  }

  /* Platforms - blue accent */
  .grid-row.platform :global(.item-icon) {
    color: #4589ff;
  }

  /* Project folders - muted green */
  .grid-row.project :global(.item-icon) {
    color: #5a9a6e;
  }

  /* Regular folders - muted amber/yellow */
  .grid-row.folder :global(.item-icon) {
    color: #c9a227;
  }

  .item-name {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: 0.875rem;
    color: var(--cds-text-01);
  }

  .grid-row.folder .item-name,
  .grid-row.project .item-name,
  .grid-row.platform .item-name {
    font-weight: 500;
  }

  /* Restricted badge */
  .restricted-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    margin-left: 0.5rem;
    padding: 2px;
    color: var(--cds-text-02);
    opacity: 0.7;
    cursor: help;
  }

  .restricted-badge:hover {
    opacity: 1;
    color: var(--cds-support-warning);
  }

  /* Responsive - hide columns on smaller screens */
  @media (max-width: 768px) {
    .type-cell {
      display: none;
    }
  }

  @media (max-width: 600px) {
    .date-cell {
      display: none;
    }
  }
</style>
