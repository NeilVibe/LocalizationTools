<script>
  /**
   * SelectionManager.svelte -- Row selection, keyboard navigation, hover tracking, context menu.
   *
   * Phase 84 Batch 2: Extracted from VirtualGrid.svelte.
   * Renderless component with context menu as only visible markup.
   * Parent delegates via bind:this.
   *
   * Writes to gridState: grid.selectedRowId, grid.hoveredRowId, grid.hoveredCell
   * Reads from gridState: grid, getRowById, getRowIndexById
   */

  import {
    grid,
    getRowById,
    getRowIndexById,
  } from './gridState.svelte.ts';
  import { logger } from '$lib/utils/logger.js';
  import { getAuthHeaders, getApiBase } from '$lib/utils/api.js';
  import { isRowLocked } from '$lib/stores/ldm.js';

  // API base URL
  let API_BASE = $derived(getApiBase());

  // Props via $props() (per D-05)
  let {
    // Callback props (forwarded from VirtualGrid parent)
    onRowSelect = undefined,
    onEditRequest = undefined,
    onRowUpdate = undefined,
    onConfirmTranslation = undefined,
    onDismissQA = undefined,
    onRunQA = undefined,
    onAddToTM = undefined,
    // TM pre-fetch callback
    onTMPrefetch = undefined,
  } = $props();

  // ============================================================
  // SELECTION STATE
  // ============================================================

  // Pre-fetch TM on cell click
  let prefetchedRowId = null;

  // ============================================================
  // CONTEXT MENU STATE
  // ============================================================
  let showContextMenu = $state(false);
  let contextMenuPosition = $state({ x: 0, y: 0 });
  let contextMenuRowId = $state(null);

  // ============================================================
  // EXPORTED FUNCTIONS (called by parent via bind:this)
  // ============================================================

  /**
   * Handle row click - selects the row and pre-fetches TM
   */
  export function handleRowClick(row, event) {
    if (!row || row.placeholder) return;

    // Select the row
    grid.selectedRowId = row.id;

    // Dispatch rowSelect event for side panel
    onRowSelect?.({ row });

    // Pre-fetch TM suggestions if not already fetched AND a TM is active
    if (prefetchedRowId !== row.id && row.source && onTMPrefetch) {
      prefetchedRowId = row.id;
      onTMPrefetch(row.source, row.id);
    }
  }

  /**
   * Handle cell mouse enter - tracks hover state
   */
  export function handleCellMouseEnter(row, cellType) {
    if (!row || row.placeholder) return;
    grid.hoveredRowId = row.id;
    grid.hoveredCell = cellType; // 'source' or 'target'
  }

  /**
   * Handle cell mouse leave - clears hover state
   */
  export function handleCellMouseLeave() {
    grid.hoveredRowId = null;
    grid.hoveredCell = null;
  }

  /**
   * Handle row mouse leave - clears hover state
   */
  export function handleRowMouseLeave() {
    grid.hoveredRowId = null;
    grid.hoveredCell = null;
  }

  /**
   * Handle keyboard events at grid level (selection mode)
   * Works when a row is selected but NOT being edited
   */
  export function handleKeyDown(e) {
    // Skip if in edit mode (EditOverlay handles its own keys)
    // EditOverlay captures focus, so this is a safety guard
    if (document.activeElement?.tagName === 'TEXTAREA') return;

    // Skip if no row selected
    if (!grid.selectedRowId) return;

    // Skip if focus is in search/filter inputs
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

    const row = getRowById(grid.selectedRowId);
    if (!row) return;

    // Ctrl+S: Confirm selected row
    if (e.ctrlKey && e.key === 's') {
      e.preventDefault();
      confirmSelectedRow(row);
      return;
    }

    // Ctrl+D: Dismiss QA for selected row
    if (e.ctrlKey && e.key === 'd') {
      e.preventDefault();
      dismissQAIssues();
      return;
    }

    // Enter: Start editing selected row
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      const lock = isRowLocked(parseInt(row.id));
      if (!lock) {
        onEditRequest?.(row);
      }
      return;
    }

    // Escape: Clear selection
    if (e.key === 'Escape') {
      e.preventDefault();
      grid.selectedRowId = null;
      return;
    }

    // Arrow Down: Move to next row
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      const currentIndex = getRowIndexById(grid.selectedRowId);
      if (currentIndex !== undefined && grid.rows[currentIndex + 1]) {
        grid.selectedRowId = grid.rows[currentIndex + 1].id;
        onRowSelect?.({ row: grid.rows[currentIndex + 1] });
      }
      return;
    }

    // Arrow Up: Move to previous row
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      const currentIndex = getRowIndexById(grid.selectedRowId);
      if (currentIndex !== undefined && currentIndex > 0 && grid.rows[currentIndex - 1]) {
        grid.selectedRowId = grid.rows[currentIndex - 1].id;
        onRowSelect?.({ row: grid.rows[currentIndex - 1] });
      }
      return;
    }
  }

  // ============================================================
  // CONTEXT MENU
  // ============================================================

  /**
   * Handle right-click on cell row
   */
  export function handleContextMenu(e, rowId) {
    e.preventDefault();
    e.stopPropagation();

    contextMenuRowId = rowId;
    contextMenuPosition = { x: e.clientX, y: e.clientY };
    showContextMenu = true;

    // Also select the row
    grid.selectedRowId = rowId;
    const row = getRowById(rowId);
    if (row) {
      onRowSelect?.({ row });
    }
  }

  /**
   * Close context menu
   */
  export function closeContextMenu() {
    showContextMenu = false;
    contextMenuRowId = null;
  }

  /**
   * Handle global click to close context menu
   */
  export function handleGlobalClick(e) {
    if (showContextMenu) {
      closeContextMenu();
    }
  }

  // ============================================================
  // CONTEXT MENU ACTIONS
  // ============================================================

  /**
   * Set row status via context menu
   */
  async function setRowStatus(status) {
    closeContextMenu();
    if (!contextMenuRowId) return;

    const row = getRowById(contextMenuRowId);
    if (!row || row.status === status) return;

    try {
      const response = await fetch(`${API_BASE}/api/ldm/rows/${row.id}`, {
        method: 'PUT',
        headers: {
          ...getAuthHeaders(),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ status })
      });

      if (response.ok) {
        row.status = status;
        logger.success(`Row status set to ${status}`, { rowId: row.id });
        onRowUpdate?.({ rowId: row.id });

        // If confirming, also dispatch for TM auto-add
        if (status === 'reviewed') {
          onConfirmTranslation?.({
            rowId: row.id,
            source: row.source,
            target: row.target
          });
        }
      }
    } catch (err) {
      logger.error("Error setting row status", { error: err.message });
    }
  }

  /**
   * Copy text to clipboard
   */
  async function copyToClipboard(text, label) {
    closeContextMenu();
    try {
      await navigator.clipboard.writeText(text);
      logger.success(`${label} copied to clipboard`);
    } catch (err) {
      logger.error("Failed to copy to clipboard", { error: err.message });
    }
  }

  /**
   * Run QA on row via context menu
   */
  function runQAOnRow() {
    closeContextMenu();
    if (!contextMenuRowId) return;

    const row = getRowById(contextMenuRowId);
    if (!row) return;

    onRunQA?.({ rowId: row.id, source: row.source, target: row.target });
    logger.userAction("QA check requested from context menu", { rowId: row.id });
  }

  /**
   * Dismiss QA via context menu
   */
  function dismissQAFromContextMenu() {
    closeContextMenu();
    if (!contextMenuRowId) return;

    onDismissQA?.({ rowId: contextMenuRowId });
    logger.userAction("QA dismissed from context menu", { rowId: contextMenuRowId });
  }

  /**
   * Add row to TM via context menu
   */
  function addToTMFromContextMenu() {
    closeContextMenu();
    if (!contextMenuRowId) return;

    const row = getRowById(contextMenuRowId);
    if (!row) return;

    onAddToTM?.({ rowId: row.id, source: row.source, target: row.target });
    logger.userAction("Add to TM requested from context menu", { rowId: row.id });
  }

  // ============================================================
  // INTERNAL HELPERS
  // ============================================================

  /**
   * Confirm selected row (mark as reviewed + add to TM) without editing
   */
  async function confirmSelectedRow(row) {
    if (!row) return;

    try {
      const response = await fetch(`${API_BASE}/api/ldm/rows/${row.id}`, {
        method: 'PUT',
        headers: {
          ...getAuthHeaders(),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          status: 'reviewed'
        })
      });

      if (response.ok) {
        row.status = 'reviewed';
        logger.success("Row confirmed (selection mode)", { rowId: row.id });

        onConfirmTranslation?.({
          rowId: row.id,
          source: row.source,
          target: row.target
        });

        onRowUpdate?.({ rowId: row.id });

        // Move to next row
        const currentIndex = getRowIndexById(row.id);
        if (currentIndex !== undefined && grid.rows[currentIndex + 1]) {
          grid.selectedRowId = grid.rows[currentIndex + 1].id;
          onRowSelect?.({ row: grid.rows[currentIndex + 1] });
        }
      }
    } catch (err) {
      logger.error("Error confirming row", { error: err.message });
    }
  }

  /**
   * Dismiss QA issues for current row (works in both edit mode and selection mode)
   */
  export function dismissQAIssues() {
    const targetRowId = grid.selectedRowId;
    if (!targetRowId) return;

    const row = getRowById(targetRowId);
    if (!row) return;

    onDismissQA?.({ rowId: row.id });
    logger.userAction("QA issues dismissed", { rowId: row.id });
  }
</script>

<!-- Context Menu (only visible markup for SelectionManager) -->
{#if showContextMenu}
  {@const contextRow = getRowById(contextMenuRowId)}
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div
    class="context-menu"
    style="left: {contextMenuPosition.x}px; top: {contextMenuPosition.y}px;"
    onclick={(e) => e.stopPropagation()}
  >
    <div class="context-menu-section">
      <button
        class="context-item"
        onclick={() => setRowStatus('reviewed')}
        disabled={contextRow?.status === 'reviewed'}
      >
        <span class="context-icon">✓</span>
        <span>Confirm</span>
        <span class="context-shortcut">Ctrl+S</span>
      </button>
      <button
        class="context-item"
        onclick={() => setRowStatus('translated')}
        disabled={contextRow?.status === 'translated'}
      >
        <span class="context-icon">📝</span>
        <span>Set as Translated</span>
      </button>
      <button
        class="context-item"
        onclick={() => setRowStatus('untranslated')}
        disabled={contextRow?.status === 'untranslated'}
      >
        <span class="context-icon">↩</span>
        <span>Set as Untranslated</span>
        <span class="context-shortcut">Ctrl+U</span>
      </button>
    </div>
    <div class="context-menu-divider"></div>
    <div class="context-menu-section">
      <button class="context-item" onclick={runQAOnRow}>
        <span class="context-icon">⚠</span>
        <span>Run QA on Row</span>
      </button>
      <button
        class="context-item"
        onclick={dismissQAFromContextMenu}
        disabled={!contextRow?.qa_flag_count}
      >
        <span class="context-icon">✗</span>
        <span>Dismiss QA Issues</span>
        <span class="context-shortcut">Ctrl+D</span>
      </button>
      <button class="context-item" onclick={addToTMFromContextMenu}>
        <span class="context-icon">+</span>
        <span>Add to TM</span>
      </button>
    </div>
    <div class="context-menu-divider"></div>
    <div class="context-menu-section">
      <button class="context-item" onclick={() => copyToClipboard(contextRow?.source || '', 'Source')}>
        <span class="context-icon">📋</span>
        <span>Copy Source</span>
      </button>
      <button class="context-item" onclick={() => copyToClipboard(contextRow?.target || '', 'Target')}>
        <span class="context-icon">📋</span>
        <span>Copy Target</span>
      </button>
      <button class="context-item" onclick={() => copyToClipboard(`${contextRow?.source || ''}\t${contextRow?.target || ''}`, 'Row')}>
        <span class="context-icon">📋</span>
        <span>Copy Row</span>
      </button>
    </div>
  </div>
{/if}

<style>
  /* UX-002: Cell Context Menu */
  .context-menu {
    position: fixed;
    z-index: 1000;
    min-width: 200px;
    background: var(--cds-layer-02, #262626);
    border: 1px solid var(--cds-border-subtle-01);
    border-radius: 4px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
    padding: 0.25rem 0;
  }

  .context-menu-section {
    padding: 0.25rem 0;
  }

  .context-menu-divider {
    height: 1px;
    background: var(--cds-border-subtle-01);
    margin: 0.25rem 0;
  }

  .context-item {
    display: flex;
    align-items: center;
    width: 100%;
    padding: 0.5rem 1rem;
    background: transparent;
    border: none;
    text-align: left;
    color: var(--cds-text-01);
    font-size: 0.875rem;
    cursor: pointer;
    transition: background 0.1s ease;
    gap: 0.75rem;
  }

  .context-item:hover:not(:disabled) {
    background: var(--cds-layer-hover-01);
  }

  .context-item:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .context-icon {
    width: 1rem;
    text-align: center;
    flex-shrink: 0;
  }

  .context-shortcut {
    margin-left: auto;
    font-size: 0.75rem;
    color: var(--cds-text-02);
    opacity: 0.7;
  }
</style>
