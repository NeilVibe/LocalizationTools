<script>
  // VirtualGrid.svelte -- Thin orchestrator composing 6 grid/ modules.
  // Owns: props, WebSocket sync, lifecycle, layout, 7 export wrappers.
  import {
    InlineLoading,
    Tag,
  } from "carbon-components-svelte";
  import { onMount, onDestroy } from "svelte";
  import { logger } from "$lib/utils/logger.js";
  import { joinFile, leaveFile, onCellUpdate } from "$lib/stores/ldm.js";
  import PresenceBar from "./PresenceBar.svelte";

  // Phase 84: Shared grid state and extracted modules
  import {
    grid,
    rowHeightCache,
    tmAppliedRows,
    referenceData as gridReferenceData,
    getRowIndexById,
    rebuildCumulativeHeights,
  } from './grid/gridState.svelte.ts';
  import ScrollEngine from './grid/ScrollEngine.svelte';
  import StatusColors from './grid/StatusColors.svelte';
  import CellRenderer from './grid/CellRenderer.svelte';
  import SelectionManager from './grid/SelectionManager.svelte';
  import InlineEditor from './grid/InlineEditor.svelte';
  import SearchEngine from './grid/SearchEngine.svelte';

  import { stripColorTags } from "$lib/utils/colorParser.js";

  let {
    fileId = $bindable(null),
    fileName = "",
    fileType = "translator",
    activeTMs = [],
    isLocalFile = false,
    gamedevDynamicColumns = null,
    onInlineEditStart = undefined,
    onRowUpdate = undefined,
    onRowSelect = undefined,
    onConfirmTranslation = undefined,
    onDismissQA = undefined,
    onRunQA = undefined,
    onAddToTM = undefined
  } = $props();

  let scrollEngine = $state(null);
  let statusColors = $state(null);
  let cellRenderer = $state(null);
  let selectionManager = $state(null);
  let inlineEditor = $state(null);
  let searchEngine = $state(null);

  // containerEl is now in gridState for cross-module reactivity
  // CellRenderer sets grid.containerEl via bind:this
  let resizeObserver = null;
  // Textarea element bridged between CellRenderer (owns DOM) and InlineEditor (owns logic)
  let inlineEditTextarea = $state(null);

  let referenceLoading = $derived(statusColors?.isReferenceLoading() ?? false);
  export function scrollToRowById(rowId) { return scrollEngine?.scrollToRowById(rowId) ?? false; }
  export function scrollToRowNum(rowNum) { return scrollEngine?.scrollToRowNum(rowNum) ?? false; }
  export function updateRowQAFlag(rowId, flagCount) { return statusColors?.updateRowQAFlag(rowId, flagCount); }
  export function markRowAsTMApplied(rowId, matchType = 'fuzzy') { return statusColors?.markRowAsTMApplied(rowId, matchType); }

  export async function openEditModalByRowId(rowId) {
    scrollToRowById(rowId);
    inlineEditor?.openEditModalByRowId(rowId);
  }

  export async function loadRows() {
    if (!fileId) return;
    grid.inlineEditingRowId = null;
    grid.selectedRowId = null;
    grid.hoveredRowId = null;
    grid.hoveredCell = null;
    grid.activeFilter = "all";
    grid.selectedCategories = [];
    tmAppliedRows.clear();
    gridReferenceData.clear();
    searchEngine?.resetSearch();
    return scrollEngine?.loadRows();
  }

  export function applyTMToRow(lineNumber, targetText) {
    const row = grid.rows.find(r => r && r.row_num === lineNumber);
    if (!row) {
      logger.warning("applyTMToRow: row not found", { lineNumber });
      return;
    }
    inlineEditor?.applyTMToRow(row, targetText, (rowId, matchType) => {
      statusColors?.markRowAsTMApplied(rowId, matchType);
    });
    logger.userAction("Applied TM to row", { lineNumber, target: targetText?.substring(0, 30) });
  }

  // WebSocket sync (per D-19: stays in parent)
  let cellUpdateUnsubscribe = null;

  function handleCellUpdates(updates) {
    let heightsChanged = false;
    updates.forEach(update => {
      const rowIndex = getRowIndexById(update.row_id);
      if (rowIndex !== undefined && grid.rows[rowIndex]) {
        grid.rows[rowIndex] = {
          ...grid.rows[rowIndex],
          target: update.target,
          status: update.status
        };
        rowHeightCache.delete(rowIndex);
        heightsChanged = true;
      }
    });
    if (heightsChanged) {
      rebuildCumulativeHeights(stripColorTags);
    }
    grid.rows = [...grid.rows];
    logger.info("Real-time updates applied", { count: updates.length });
  }

  function handleGridKeydown(e) { selectionManager?.handleKeyDown(e); }
  function handleCellClick(row, event) { selectionManager?.handleRowClick(row, event); }
  function handleCellMouseEnter(row, cellType) { selectionManager?.handleCellMouseEnter(row, cellType); }
  function handleCellMouseLeave() { selectionManager?.handleCellMouseLeave(); }
  function handleRowMouseLeave() { selectionManager?.handleRowMouseLeave(); }
  function handleCellContextMenu(e, rowId) { selectionManager?.handleContextMenu(e, rowId); }
  function handleGlobalClick(e) { selectionManager?.handleGlobalClick(e); }
  function handleQADismiss(rowId) { return statusColors?.handleQADismiss(rowId); }
  function fetchTMSuggestions(sourceText, rowId) { return statusColors?.fetchTMSuggestions(sourceText, rowId); }
  function getReferenceForRow(row, matchMode) { return statusColors?.getReferenceForRow(row, matchMode) ?? null; }
  function handleScroll() { scrollEngine?.handleScroll(); }

  let previousFileId = $state(null);

  $effect(() => {
    if (fileId && fileId !== previousFileId) {
      logger.info("fileId changed", { from: previousFileId, to: fileId });
      previousFileId = fileId;
      joinFile(fileId);
      if (cellUpdateUnsubscribe) cellUpdateUnsubscribe();
      cellUpdateUnsubscribe = onCellUpdate(handleCellUpdates);
      loadRows();
    }
  });

  // Bridge textarea from CellRenderer to InlineEditor
  $effect(() => {
    if (inlineEditor && inlineEditTextarea) {
      inlineEditor.setTextarea(inlineEditTextarea);
    }
  });

  // Wire delegates after modules mount
  $effect(() => {
    if (inlineEditor && selectionManager) {
      inlineEditor.setDismissQADelegate(() => selectionManager?.dismissQAIssues?.());
    }
  });

  $effect(() => {
    if (searchEngine) {
      searchEngine.setScrollToRowDelegate((rowId) => scrollToRowById(rowId));
    }
  });

  $effect(() => {
    if (grid.containerEl) {
      grid.containerEl.addEventListener('scroll', handleScroll);
      scrollEngine?.calculateVisibleRange();
      if (!resizeObserver) {
        resizeObserver = new ResizeObserver(() => {
          scrollEngine?.calculateVisibleRange();
          cellRenderer?.updateContainerWidth();
        });
      }
      resizeObserver.observe(grid.containerEl);
      cellRenderer?.updateContainerWidth();
      return () => {
        grid.containerEl.removeEventListener('scroll', handleScroll);
        if (resizeObserver) resizeObserver.disconnect();
      };
    }
  });

  onMount(() => { if (grid.containerEl) scrollEngine?.calculateVisibleRange(); });
  onDestroy(() => {
    if (fileId) leaveFile(fileId);
    if (cellUpdateUnsubscribe) cellUpdateUnsubscribe();
  });
</script>

<div
  class="virtual-grid"
  onkeydown={handleGridKeydown}
  tabindex="-1"
>
  {#if fileId}
    <!-- Renderless modules -->
    <ScrollEngine
      bind:this={scrollEngine}
      {fileId}
      {fileType}
      {activeTMs}
    />
    <StatusColors
      bind:this={statusColors}
      {fileId}
      {activeTMs}
    />
    <SelectionManager
      bind:this={selectionManager}
      {onRowSelect}
      onEditRequest={(row) => inlineEditor?.startInlineEdit(row)}
      {onRowUpdate}
      {onConfirmTranslation}
      {onDismissQA}
      {onRunQA}
      {onAddToTM}
      onTMPrefetch={fetchTMSuggestions}
    />
    <InlineEditor
      bind:this={inlineEditor}
      {fileId}
      {fileName}
      {fileType}
      {isLocalFile}
      {onInlineEditStart}
      {onRowUpdate}
      {onRowSelect}
      {onConfirmTranslation}
    />

    <!-- Header -->
    <div class="grid-header">
      <div class="header-left">
        <h4>{fileName || `File #${fileId}`}</h4>
        <span class="row-count">{grid.total.toLocaleString()} rows</span>
        <Tag type={fileType === 'gamedev' ? 'teal' : 'blue'} size="sm">
          {fileType === 'gamedev' ? 'Game Dev' : 'Translator'}
        </Tag>
      </div>
      <div class="header-right">
        <PresenceBar />
      </div>
    </div>

    <!-- Search/Filter bar (SearchEngine owns this markup) -->
    <SearchEngine
      bind:this={searchEngine}
      {fileId}
      {fileType}
      {activeTMs}
      onSearchComplete={() => loadRows()}
    />

    <!-- Hotkey Reference Bar -->
    <div class="hotkey-bar">
      <span class="hotkey"><kbd>Enter</kbd> Save & Next</span>
      <span class="hotkey"><kbd>Ctrl+S</kbd> Confirm</span>
      <span class="hotkey"><kbd>Ctrl+T</kbd> Translated</span>
      <span class="hotkey"><kbd>Esc</kbd> Cancel</span>
      <span class="hotkey"><kbd>Ctrl+D</kbd> Dismiss QA</span>
      <span class="hotkey"><kbd>Ctrl+Z</kbd> Undo</span>
      <span class="hotkey"><kbd>Ctrl+Y</kbd> Redo</span>
    </div>

    <!-- Row rendering -->
    <div class="scroll-wrapper">
      <CellRenderer
        bind:this={cellRenderer}
        {fileType}
        {gamedevDynamicColumns}
        inlineEditingRowId={grid.inlineEditingRowId}
        bind:inlineEditTextarea={inlineEditTextarea}
        onRowClick={handleCellClick}
        onRowDoubleClick={(row) => inlineEditor?.startInlineEdit(row)}
        onCellContextMenu={handleCellContextMenu}
        onCellMouseEnter={handleCellMouseEnter}
        onCellMouseLeave={handleCellMouseLeave}
        onRowMouseLeave={handleRowMouseLeave}
        onInlineEditKeydown={(e) => inlineEditor?.handleInlineEditKeydown(e)}
        onInlineEditBlur={() => inlineEditor?.saveInlineEdit(false)}
        onEditContextMenu={(e) => inlineEditor?.handleEditContextMenu(e)}
        onQADismiss={handleQADismiss}
        {getReferenceForRow}
        {referenceLoading}
      />
    </div>

    {#if grid.loading && !grid.initialLoading}
      <div class="loading-bar">
        <InlineLoading description="Loading more..." />
      </div>
    {/if}
  {:else}
    <div class="empty-state">
      <div class="empty-state-content">
        <svg class="empty-state-icon" width="48" height="48" viewBox="0 0 32 32" fill="currentColor" opacity="0.3">
          <path d="M25.7 9.3l-7-7A.908.908 0 0018 2H8a2.006 2.006 0 00-2 2v24a2.006 2.006 0 002 2h16a2.006 2.006 0 002-2V10a.908.908 0 00-.3-.7zM18 4.4l5.6 5.6H18zM24 28H8V4h8v6a2.006 2.006 0 002 2h6z"/>
        </svg>
        <p class="empty-state-title">No file selected</p>
        <p class="empty-state-hint">Select a file from the explorer to view its contents</p>
      </div>
    </div>
  {/if}
</div>

<!-- svelte:window for closing context menu -->
<svelte:window onclick={handleGlobalClick} />

<style>
  .virtual-grid {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    background: var(--cds-background);
    min-height: 0;
  }

  .grid-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem 1.25rem;
    border-bottom: 1px solid var(--cds-border-subtle-01);
    background: var(--cds-layer-01);
  }

  .header-left { display: flex; align-items: center; gap: 0.75rem; }
  .header-right { display: flex; align-items: center; gap: 0.5rem; }
  .grid-header h4 { margin: 0; font-size: 0.875rem; font-weight: 600; }
  .row-count { font-size: 0.75rem; color: var(--cds-text-02); }

  /* Hotkey Reference Bar */
  .hotkey-bar {
    display: flex;
    gap: 1rem;
    padding: 0.35rem 1rem;
    background: var(--cds-layer-accent-01);
    border-bottom: 1px solid var(--cds-border-subtle-01);
    font-size: 0.7rem;
    color: var(--cds-text-02);
    flex-wrap: wrap;
  }

  .hotkey {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
  }

  .hotkey kbd {
    display: inline-block;
    padding: 0.15rem 0.4rem;
    background: var(--cds-field-01);
    border: 1px solid var(--cds-border-strong-01);
    border-radius: 3px;
    font-family: var(--cds-code-01);
    font-size: 0.65rem;
    font-weight: 500;
    color: var(--cds-text-01);
    box-shadow: 0 1px 0 var(--cds-border-subtle-01);
  }

  /* Scroll wrapper */
  .scroll-wrapper {
    flex: 1;
    display: flex;
    flex-direction: column;
    position: relative;
    min-height: 0;
    height: 0;
  }

  .loading-bar { padding: 0.25rem 1rem; background: var(--cds-layer-02); border-top: 1px solid var(--cds-border-subtle-01); }
  .empty-state { display: flex; justify-content: center; align-items: center; height: 100%; color: var(--cds-text-02); }
  .empty-state-content { display: flex; flex-direction: column; align-items: center; gap: 0.75rem; text-align: center; }
  .empty-state-icon { color: var(--cds-text-03); margin-bottom: 0.25rem; }
  .empty-state-title { font-size: 1rem; font-weight: 500; color: var(--cds-text-01); margin: 0; }
  .empty-state-hint { font-size: 0.8125rem; color: var(--cds-text-03); margin: 0; }
</style>
