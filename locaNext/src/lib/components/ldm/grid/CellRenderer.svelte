<script>
  /**
   * CellRenderer.svelte -- Column layout, cell markup, text formatting, TagText integration.
   *
   * Phase 84 Batch 2: Extracted from VirtualGrid.svelte.
   * Owns the {#each visibleRows} loop, row rendering, column definitions,
   * column resize system, and all cell/row CSS.
   *
   * Reads from gridState: grid, visibleRows, measureRowHeight, tmAppliedRows, qaFlags
   * Does NOT write to gridState (display-only).
   */

  import { Tag } from "carbon-components-svelte";
  import LoadingScreen from '$lib/components/ldm/LoadingScreen.svelte';
  import { Edit, Locked, MachineLearningModel } from "carbon-icons-svelte";
  import {
    grid,
    getVisibleRows,
    measureRowHeight,
    tmAppliedRows,
    getRowById,
    getRowTop,
    getRowHeight as gridGetRowHeight,
    getTotalHeight,
    gameDevDynamicColumns,
    rowHeightCache,
    rebuildCumulativeHeights,
  } from './gridState.svelte.ts';
  import TagText from '$lib/components/ldm/TagText.svelte';
  import QAInlineBadge from '$lib/components/ldm/QAInlineBadge.svelte';
  import { preferences, getFontSizeValue, getFontFamilyValue, getFontColorValue } from '$lib/stores/preferences.js';
  import { ldmConnected, isRowLocked } from '$lib/stores/ldm.js';
  import { stripColorTags, hexToCSS } from '$lib/utils/colorParser.js';
  import { getStatusKind } from '$lib/utils/statusColors';

  // Props via $props() (per D-05)
  let {
    fileType = "translator",
    // containerEl is now in gridState — set directly via bind:this on scroll-container
    gamedevDynamicColumns = null,
    // Inline editing state passed from parent (InlineEditor owns these, Batch 3)
    inlineEditingRowId = null,
    inlineEditTextarea = $bindable(null),
    // Callback props forwarded from parent
    onRowClick = undefined,
    onRowDoubleClick = undefined,
    onCellContextMenu = undefined,
    onCellMouseEnter = undefined,
    onCellMouseLeave = undefined,
    onRowMouseLeave = undefined,
    onInlineEditKeydown = undefined,
    onInlineEditBlur = undefined,
    onEditContextMenu = undefined,
    onQADismiss = undefined,
    // Reference column
    getReferenceForRow = undefined,
    referenceLoading = false,
    // Column resize callback
    onColumnResize = undefined,
  } = $props();

  // Category color map (synced with CategoryFilter)
  const CATEGORY_COLORS = {
    "Item": "#D9D2E9", "Character": "#F8CBAD", "Quest": "#D9D2E9",
    "Skill": "#D9D2E9", "Region": "#F8CBAD", "Gimmick": "#D9D2E9",
    "Knowledge": "#D9D2E9", "UI": "#A9D08E", "Other": "#D9D9D9",
    "Uncategorized": "#D9D9D9",
  };

  function getCategoryColor(category) {
    return CATEGORY_COLORS[category] || "#D9D9D9";
  }

  // ============================================================
  // COLUMN DEFINITIONS
  // ============================================================

  // Translator columns
  const translatorColumns = {
    row_num: { key: "row_num", label: "#", width: 60, prefKey: "showIndex" },
    string_id: { key: "string_id", label: "StringID", width: 150, prefKey: "showStringId" },
    category: { key: "category", label: "Category", width: 140, minWidth: 80, prefKey: "showCategory" },
    source: { key: "source", label: "Source (KR)", width: 350, always: true },
    target: { key: "target", label: "Target", width: 350, always: true },
    reference: { key: "reference", label: "Reference", width: 300, prefKey: "showReference" },
    tm_result: { key: "tm_result", label: "TM Match", width: 300, prefKey: "showTmResults" }
  };

  // Game Dev columns
  const gameDevColumns = {
    row_num: { key: "row_num", label: "#", width: 60, prefKey: "showIndex" },
    node_name: { key: "source", label: "Node", width: 200, always: true },
    attributes: { key: "target", label: "Attributes", width: 300, always: true },
    values: { key: "values", label: "Values", width: 250, always: true },
    children_count: { key: "children_count", label: "Children", width: 100, always: true }
  };

  // Dual UI Mode: switch columns based on file type
  let allColumns = $derived(
    fileType === 'gamedev'
      ? (gamedevDynamicColumns || gameDevColumns)
      : translatorColumns
  );

  // FIX-02: visibleColumns $derived and getVisibleColumns were dead code (never consumed).
  // Column visibility is handled directly in the template via $preferences checks.

  // ============================================================
  // UNIFIED COLUMN RESIZE SYSTEM (UI-083)
  // ============================================================

  // Column widths (px for fixed, % for source/target split)
  let indexColumnWidth = $state(60);
  let stringIdColumnWidth = $state(150);
  let categoryColumnWidth = $state(140);
  let sourceWidthPercent = $state(50);
  let referenceColumnWidth = $state(300);

  // Column width limits (min, max)
  const COLUMN_LIMITS = {
    index: { min: 40, max: 120 },
    stringId: { min: 80, max: 300 },
    category: { min: 80, max: 250 },
    source: { min: 20, max: 80 }, // percentage
    reference: { min: 150, max: 500 }
  };

  // Resize state
  let isResizing = $state(false);
  let resizeColumn = $state(null);
  let resizeStartX = $state(0);
  let resizeStartValue = $state(0);

  // Container width for position calculations
  let containerWidth = $state(800);

  // Update container width when it changes
  export function updateContainerWidth() {
    if (grid.containerEl) {
      containerWidth = grid.containerEl.clientWidth;
    }
  }

  function getFixedWidthBefore() {
    let width = 0;
    if ($preferences.showIndex) width += indexColumnWidth;
    if ($preferences.showStringId) width += stringIdColumnWidth;
    if ($preferences.showCategory && fileType !== 'gamedev') width += categoryColumnWidth;
    return width;
  }

  function getFixedWidthAfter() {
    if (fileType === 'gamedev') {
      // existing 350px + new LDE columns: category(100) + fileName(120) + textState(90)
      return 350 + 310;
    }
    return $preferences.showReference ? referenceColumnWidth : 0;
  }

  // Get visible resize bars based on preferences
  let visibleResizeBars = $derived.by(() => {
    const bars = [];
    if ($preferences.showIndex) bars.push('index');
    if ($preferences.showStringId) bars.push('stringId');
    if ($preferences.showCategory && fileType !== 'gamedev') bars.push('category');
    bars.push('source');
    if ($preferences.showReference) bars.push('reference');
    return bars;
  });

  // Pre-compute resize bar positions (REACTIVE)
  let resizeBarPositions = $derived.by(() => {
    const positions = {};
    let pos = 0;

    if ($preferences.showIndex) {
      positions['index'] = indexColumnWidth;
      pos += indexColumnWidth;
    }

    if ($preferences.showStringId) {
      positions['stringId'] = pos + stringIdColumnWidth;
      pos += stringIdColumnWidth;
    }

    if ($preferences.showCategory && fileType !== 'gamedev') {
      positions['category'] = pos + categoryColumnWidth;
      pos += categoryColumnWidth;
    }

    const fixedAfter = $preferences.showReference ? referenceColumnWidth : 0;
    const fixedTotal = pos + fixedAfter;
    const flexWidth = containerWidth - fixedTotal;
    positions['source'] = pos + (flexWidth * sourceWidthPercent / 100);

    if ($preferences.showReference) {
      positions['reference'] = containerWidth - referenceColumnWidth;
    }

    return positions;
  });

  function startResize(event, column = 'source') {
    event.preventDefault();
    event.stopPropagation();

    if (column === 'source') {
      resizeStartValue = sourceWidthPercent;
    } else if (column === 'index') {
      resizeStartValue = indexColumnWidth;
    } else if (column === 'stringId') {
      resizeStartValue = stringIdColumnWidth;
    } else if (column === 'category') {
      resizeStartValue = categoryColumnWidth;
    } else if (column === 'reference') {
      resizeStartValue = referenceColumnWidth;
    }

    isResizing = true;
    resizeColumn = column;
    resizeStartX = event.clientX;

    document.addEventListener('mousemove', handleResize);
    document.addEventListener('mouseup', stopResize);
  }

  function handleResize(event) {
    if (!isResizing || !grid.containerEl) return;

    const deltaX = event.clientX - resizeStartX;
    const limits = COLUMN_LIMITS[resizeColumn];
    if (!limits) return;

    if (resizeColumn === 'source') {
      const cw = grid.containerEl.clientWidth;
      const fixedTotal = getFixedWidthBefore() + getFixedWidthAfter();
      const flexWidth = cw - fixedTotal;
      if (flexWidth <= 0) return;
      const deltaPercent = (deltaX / flexWidth) * 100;
      const newPercent = resizeStartValue + deltaPercent;
      sourceWidthPercent = Math.max(limits.min, Math.min(limits.max, newPercent));
    } else if (resizeColumn === 'reference') {
      const newWidth = resizeStartValue - deltaX;
      referenceColumnWidth = Math.max(limits.min, Math.min(limits.max, newWidth));
    } else if (resizeColumn === 'index') {
      const newWidth = resizeStartValue + deltaX;
      indexColumnWidth = Math.max(limits.min, Math.min(limits.max, newWidth));
    } else if (resizeColumn === 'stringId') {
      const newWidth = resizeStartValue + deltaX;
      stringIdColumnWidth = Math.max(limits.min, Math.min(limits.max, newWidth));
    } else if (resizeColumn === 'category') {
      const newWidth = resizeStartValue + deltaX;
      categoryColumnWidth = Math.max(limits.min, Math.min(limits.max, newWidth));
    }
  }

  function stopResize() {
    isResizing = false;
    resizeColumn = null;
    document.removeEventListener('mousemove', handleResize);
    document.removeEventListener('mouseup', stopResize);
  }

  // ============================================================
  // DERIVED STATE
  // ============================================================

  // Font styles from preferences
  let visibleRows = $derived.by(() => {
    // Read rowsVersion to establish dependency — re-evaluates when rows are batch-mutated
    const _v = grid.rowsVersion;
    const start = grid.visibleStart;
    const end = grid.visibleEnd;
    return Array.from({ length: end - start }, (_, i) => {
      const index = start + i;
      return grid.rows[index] || { row_num: index + 1, placeholder: true };
    });
  });
  let gridFontSize = $derived(getFontSizeValue($preferences.fontSize));
  let gridFontWeight = $derived($preferences.fontWeight === 'bold' ? '600' : '400');
  let gridFontFamily = $derived(getFontFamilyValue($preferences.fontFamily));
  let gridFontColor = $derived(getFontColorValue($preferences.fontColor));

  // Total height from gridState
  let totalHeight = $derived(getTotalHeight());

  // Local wrapper for getRowHeight (needs stripColorTags parameter)
  function getRowHeight(index) {
    return gridGetRowHeight(index, stripColorTags);
  }

  /** Live resize: when contenteditable content changes, measure and grow the row.
   *  Uses incremental height update (O(n) shift) instead of full rebuild (O(n) too but with
   *  snapshot overhead). Debounced via rAF to avoid per-keystroke thrash. */
  let resizeRafId = null;
  function handleEditInput(rowIndex) {
    if (resizeRafId) cancelAnimationFrame(resizeRafId);
    resizeRafId = requestAnimationFrame(() => {
      resizeRafId = null;
      if (!inlineEditTextarea) return;
      // Measure the contenteditable's natural scroll height + row chrome (border + padding)
      const editHeight = inlineEditTextarea.scrollHeight + 24;
      const currentCached = rowHeightCache.get(rowIndex) || 48;
      const newHeight = Math.max(48, editHeight);
      // Only update if height changed meaningfully
      if (Math.abs(newHeight - currentCached) > 4) {
        const delta = newHeight - currentCached;
        rowHeightCache.set(rowIndex, newHeight);
        // Incremental shift: update cumulative heights from this row onward
        const cum = heightData.cumulativeHeights;
        if (cum.length > rowIndex + 1) {
          for (let i = rowIndex + 1; i < cum.length; i++) {
            cum[i] += delta;
          }
          // Trigger reactivity by reassigning
          heightData.cumulativeHeights = cum;
        }
      }
    });
  }
</script>

<!-- Resize Bars: OUTSIDE scroll container so they don't scroll -->
{#each visibleResizeBars as column (column)}
  <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
  <div
    class="column-resize-bar"
    class:resize-active={isResizing && resizeColumn === column}
    style="left: {resizeBarPositions[column] || 0}px;"
    onmousedown={(e) => startResize(e, column)}
    role="separator"
    aria-orientation="vertical"
    aria-label="Resize {column} column"
  ></div>
{/each}

<!-- Scroll Container: owns the scrollbar, parent binds grid.containerEl from here -->
<div class="scroll-container" bind:this={grid.containerEl}>
{#if grid.initialLoading}
  <div class="loading-overlay">
    <LoadingScreen message={grid.loadingFileName ? `Loading ${grid.loadingFileName}...` : 'Loading rows...'} progress={0} showPercentage={false} />
  </div>
{:else}
  <div class="scroll-content" style="height: {totalHeight}px;">
    {#each visibleRows as row, i (row.row_num)}
      {@const rowIndex = grid.visibleStart + i}
      {@const rowLock = $ldmConnected && row.id ? isRowLocked(parseInt(row.id)) : null}
      <div
        class="virtual-row"
        class:placeholder={row.placeholder}
        class:locked={rowLock}
        class:selected={grid.selectedRowId === row.id}
        class:row-hovered={grid.hoveredRowId === row.id}
        style="top: {getRowTop(rowIndex)}px; min-height: {getRowHeight(rowIndex)}px;
          --grid-font-size: {gridFontSize}; --grid-font-weight: {gridFontWeight}; --grid-font-family: {gridFontFamily}; --grid-font-color: {gridFontColor};"
        use:measureRowHeight={{ index: rowIndex }}
        onclick={(e) => onRowClick?.(row, e)}
        onkeydown={(e) => { if (!inlineEditingRowId && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); onRowClick?.(row, e); } }}
        oncontextmenu={(e) => !row.placeholder && onCellContextMenu?.(e, row.id)}
        onmouseleave={() => onRowMouseLeave?.()}
        role="row"
        tabindex="0"
      >
        {#if row.placeholder}
          <!-- Placeholder rows match actual column structure -->
          {#if $preferences.showIndex}
            <div class="cell row-num" style="width: {indexColumnWidth}px;">{row.row_num}</div>
          {/if}
          {#if $preferences.showStringId}
            <div class="cell string-id loading-cell" style="width: {stringIdColumnWidth}px;">
              <div class="placeholder-shimmer"></div>
            </div>
          {/if}
          {#if $preferences.showCategory && fileType !== 'gamedev'}
            <div class="cell category loading-cell" style="width: {categoryColumnWidth}px;">
              <div class="placeholder-shimmer"></div>
            </div>
          {/if}
          <div class="cell source loading-cell" style="flex: {sourceWidthPercent} 1 0;">
            <div class="placeholder-shimmer"></div>
          </div>
          <div class="cell target loading-cell" style="flex: {100 - sourceWidthPercent} 1 0;">
            <div class="placeholder-shimmer"></div>
          </div>
          {#if $preferences.showReference && fileType !== 'gamedev'}
            <div class="cell reference loading-cell" style="width: {referenceColumnWidth}px;">
              <div class="placeholder-shimmer"></div>
            </div>
          {/if}
          {#if fileType === 'gamedev'}
            <div class="cell gamedev-category loading-cell" style="width: 100px;">
              <div class="placeholder-shimmer"></div>
            </div>
            <div class="cell gamedev-filename loading-cell" style="width: 120px;">
              <div class="placeholder-shimmer"></div>
            </div>
            <div class="cell gamedev-textstate loading-cell" style="width: 90px;">
              <div class="placeholder-shimmer"></div>
            </div>
            <div class="cell gamedev-values loading-cell" style="width: 250px;">
              <div class="placeholder-shimmer"></div>
            </div>
            <div class="cell gamedev-children loading-cell" style="width: 100px;">
              <div class="placeholder-shimmer"></div>
            </div>
          {/if}
        {:else}
          <!-- Row number (conditional) -->
          {#if $preferences.showIndex}
            <div class="cell row-num" style="width: {indexColumnWidth}px;">
              {row.row_num}
            </div>
          {/if}

          <!-- StringID (conditional) -->
          {#if $preferences.showStringId}
            <div class="cell string-id" style="width: {stringIdColumnWidth}px;">
              {row.string_id || "-"}
            </div>
          {/if}

          <!-- Category column (translator mode only) -->
          {#if $preferences.showCategory && fileType !== 'gamedev'}
            <div class="cell category" style="width: {categoryColumnWidth}px;">
              {#if row.category}
                <Tag type="outline" size="sm" style="--cds-tag-background-color: {getCategoryColor(row.category)}; --cds-tag-color: #333; background-color: {getCategoryColor(row.category)}30; border-color: {getCategoryColor(row.category)};">
                  {row.category}
                </Tag>
              {:else}
                <span class="category-empty">-</span>
              {/if}
            </div>
          {/if}

          <!-- Source (always visible, READ-ONLY) -->
          <div
            class="cell source"
            class:source-hovered={grid.hoveredRowId === row.id && grid.hoveredCell === 'source'}
            class:row-active={grid.hoveredRowId === row.id || grid.selectedRowId === row.id}
            class:cell-selected={grid.selectedRowId === row.id}
            style="flex: {sourceWidthPercent} 1 0;{fileType === 'gamedev' ? ` padding-left: ${(row.extra_data?.depth || 0) * 20 + 8}px` : ''}"
            onmouseenter={() => onCellMouseEnter?.(row, 'source')}
            role="gridcell"
            tabindex="-1"
          >
            <span class="cell-content"><TagText text={row.source || ""} /></span>
            <!-- Translation source badge (AI/TM indicator) -->
            {#if row.translation_source === 'ai'}
              <span class="translation-source-badge ai" title="AI Translated">
                <MachineLearningModel size={10} />
                <span class="badge-text">AI</span>
              </span>
            {:else if row.translation_source === 'tm'}
              <span class="translation-source-badge tm" title="TM Match">
                <span class="badge-text">TM</span>
              </span>
            {/if}
          </div>

          <!-- Target (always visible, EDITABLE) -->
          <div
            class="cell target"
            class:locked={rowLock}
            class:target-hovered={grid.hoveredRowId === row.id && grid.hoveredCell === 'target'}
            class:row-active={grid.hoveredRowId === row.id || grid.selectedRowId === row.id}
            class:cell-selected={grid.selectedRowId === row.id}
            class:inline-editing={inlineEditingRowId === row.id}
            class:status-translated={row.status === 'translated'}
            class:status-reviewed={row.status === 'reviewed'}
            class:status-approved={row.status === 'approved'}
            class:qa-flagged={row.qa_flag_count > 0}
            style="flex: {100 - sourceWidthPercent} 1 0;"
            onmouseenter={() => onCellMouseEnter?.(row, 'target')}
            ondblclick={() => !rowLock && onRowDoubleClick?.(row)}
            role="button"
            tabindex="0"
            onkeydown={(e) => e.key === 'Enter' && !e.shiftKey && !rowLock && !inlineEditingRowId && onRowDoubleClick?.(row)}
          >
            {#if inlineEditingRowId === row.id}
              <!-- WYSIWYG inline editing - colors render directly -->
              <div class="inline-edit-container">
                <div
                  bind:this={inlineEditTextarea}
                  contenteditable="true"
                  class="inline-edit-textarea"
                  role="textbox"
                  tabindex="0"
                  onkeydown={(e) => onInlineEditKeydown?.(e)}
                  oninput={() => handleEditInput(rowIndex)}
                  onblur={() => onInlineEditBlur?.()}
                  oncontextmenu={(e) => onEditContextMenu?.(e)}
                  data-placeholder="Enter translation..."
                ></div>
              </div>
            {:else}
              <!-- Display mode -->
              <span class="cell-content"><TagText text={row.target || ""} /></span>
              {#if tmAppliedRows.has(row.id)}
                {@const tmInfo = tmAppliedRows.get(row.id)}
                <span class="ai-badge" title="AI-matched ({tmInfo.match_type})">
                  <MachineLearningModel size={12} />
                </span>
              {/if}
              {#if row.qa_flag_count > 0}
                <QAInlineBadge qaFlagCount={row.qa_flag_count} rowId={row.id} onDismiss={onQADismiss} />
              {/if}
              {#if rowLock}
                <span class="lock-icon"><Locked size={12} /></span>
              {:else}
                <span class="edit-icon"><Edit size={12} /></span>
              {/if}
            {/if}
          </div>

          <!-- Reference Column (conditional, hidden in Game Dev mode) -->
          {#if $preferences.showReference && fileType !== 'gamedev'}
            {@const refText = getReferenceForRow?.(row, $preferences.referenceMatchMode)}
            <div
              class="cell reference"
              class:has-match={refText}
              class:no-match={!refText}
              style="width: {referenceColumnWidth}px;"
              title={refText ? `Reference: ${refText}` : 'No reference match'}
            >
              {#if referenceLoading}
                <span class="cell-loading">Loading...</span>
              {:else if refText}
                <span class="cell-content ref-match"><TagText text={refText || ""} /></span>
              {:else}
                <span class="cell-content no-match">No match</span>
              {/if}
            </div>
          {/if}

          <!-- Game Dev extra_data columns (LDE graft: category + fileName + textState) -->
          {#if fileType === 'gamedev'}
            <div class="cell gamedev-category" style="width: 100px;">
              {#if row.extra_data?.category}
                <span class="gamedev-category-tag" style="background-color: {getCategoryColor(row.extra_data.category)}30; border-color: {getCategoryColor(row.extra_data.category)}; color: #ccc;">
                  {row.extra_data.category}
                </span>
              {:else}
                <span class="category-empty">-</span>
              {/if}
            </div>
            <div class="cell gamedev-filename" style="width: 120px;" title={row.extra_data?.file_name || ''}>
              <span class="cell-content gamedev-filename-text">{row.extra_data?.file_name || '-'}</span>
            </div>
            <div class="cell gamedev-textstate" style="width: 90px;">
              {#if row.extra_data?.text_state === 'KOREAN'}
                <span class="textstate-badge textstate-korean">KOREAN</span>
              {:else}
                <span class="textstate-badge textstate-translated">TRANSLATED</span>
              {/if}
            </div>
            <div class="cell gamedev-values" style="width: 250px;">
              <span class="cell-content">{row.extra_data?.values || ''}</span>
            </div>
            <div class="cell gamedev-children" style="width: 100px;">
              <span class="cell-content">{row.extra_data?.children_count ?? 0}</span>
            </div>
          {/if}
        {/if}
      </div>
    {/each}
  </div>
{/if}
</div>

<style>
  /* UI-083: Full-height column resize bars (unified system) */
  .column-resize-bar {
    position: absolute;
    top: 0;
    bottom: 0;
    width: 10px;
    margin-left: -5px;
    cursor: col-resize;
    background: transparent;
    z-index: 20;
    transition: background-color 0.15s;
  }

  .column-resize-bar:hover {
    background: rgba(15, 98, 254, 0.35);
  }

  .column-resize-bar:active,
  .column-resize-bar.resize-active {
    background: var(--cds-interactive-01, #0f62fe);
  }

  .scroll-container {
    flex: 1;
    overflow-y: auto;
    overflow-x: hidden;
    position: relative;
    height: 0;
    min-height: 200px;
    scrollbar-gutter: stable;
  }

  .scroll-container::-webkit-scrollbar {
    width: 8px;
  }

  .scroll-container::-webkit-scrollbar-track {
    background: var(--cds-layer-01);
  }

  .scroll-container::-webkit-scrollbar-thumb {
    background: var(--cds-border-subtle-02, #525252);
    border-radius: 4px;
    border: 2px solid var(--cds-layer-01);
  }

  .scroll-container::-webkit-scrollbar-thumb:hover {
    background: var(--cds-text-03);
  }

  .loading-overlay {
    display: flex;
    justify-content: center;
    align-items: center;
    height: 100%;
    min-height: 300px;
  }

  .scroll-content {
    position: relative;
    width: 100%;
  }

  .virtual-row {
    position: absolute;
    left: 0;
    right: 0;
    display: flex;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    background: var(--cds-layer-01);
    transition: background-color 0.15s ease;
    box-sizing: border-box;
  }

  /* HOVER SYSTEM: Row-level hover */
  .virtual-row:hover,
  .virtual-row.row-hovered {
    background: var(--cds-layer-hover-01);
  }

  /* Selected row takes priority over hover */
  .virtual-row.selected {
    background: var(--cds-layer-selected-01) !important;
    border-left: 3px solid var(--cds-interactive-01, #0f62fe);
    box-shadow: inset 0 0 0 1px rgba(15, 98, 254, 0.2);
  }

  .virtual-row.selected:hover,
  .virtual-row.selected.row-hovered {
    background: var(--cds-layer-selected-hover-01, rgba(15, 98, 254, 0.18)) !important;
  }

  .virtual-row.placeholder {
    opacity: 0.5;
  }

  .virtual-row.locked {
    background: var(--cds-layer-02);
  }

  .cell {
    padding: 0.5rem 0.75rem;
    font-size: var(--grid-font-size, 14px);
    font-weight: var(--grid-font-weight, 400);
    font-family: var(--grid-font-family, inherit);
    color: var(--grid-font-color, var(--cds-text-01));
    border-right: 1px solid rgba(255, 255, 255, 0.06);
    display: flex;
    align-items: flex-start;
    overflow: hidden;
    text-overflow: ellipsis;
    min-width: 0;
    align-self: stretch;
    box-sizing: border-box;
  }

  .cell-content {
    word-break: break-word;
    white-space: pre-wrap;
    line-height: 1.6;
    width: 100%;
  }

  .cell.row-num {
    justify-content: center;
    align-items: center;
    color: var(--cds-text-02);
    font-size: 0.75rem;
    flex: none;
  }

  .cell.string-id {
    font-family: monospace;
    font-size: 0.75rem;
    word-break: break-all;
    flex: none;
  }

  .cell.source {
    background: var(--cds-layer-02);
    color: var(--cds-text-02);
    transition: background-color 0.15s ease;
    border-right: 1px solid var(--cds-border-subtle-02, #525252);
    cursor: default;
  }

  .cell.source.row-active {
    background: var(--cds-layer-hover-01);
  }

  .cell.source.source-hovered {
    background: var(--cds-layer-accent-hover-01, var(--cds-layer-hover-01));
    border-left: 2px solid var(--cds-border-subtle-02, #525252);
  }

  .cell.target {
    position: relative;
    cursor: pointer;
    padding-right: 1.5rem;
    transition: all 0.15s ease;
  }

  .cell.target.row-active {
    background: var(--cds-layer-hover-01);
  }

  .cell.target.target-hovered {
    background: rgba(69, 137, 255, 0.15);
    border-left: 3px solid var(--cds-interactive-01, #0f62fe);
    box-shadow: inset 0 0 0 1px rgba(15, 98, 254, 0.3);
  }

  .cell.target.target-hovered .edit-icon {
    opacity: 1;
    color: var(--cds-interactive-01, #0f62fe);
  }

  .cell.target.locked {
    cursor: not-allowed;
    background: var(--cds-layer-02);
  }

  /* Inline editing mode — overflow visible so cell grows with content */
  .cell.target.inline-editing {
    padding: 0;
    background: var(--cds-field-01);
    border: 2px solid var(--cds-interactive-01);
    box-shadow: 0 0 0 2px rgba(15, 98, 254, 0.3);
    overflow: visible;
  }

  .inline-edit-textarea {
    width: 100%;
    min-height: 48px;
    padding: 0.5rem;
    border: none;
    background: var(--cds-field-01);
    color: var(--grid-font-color, var(--cds-text-01));
    font-family: var(--grid-font-family, inherit);
    font-size: var(--grid-font-size, 0.875rem);
    font-weight: var(--grid-font-weight, 400);
    line-height: 1.5;
    outline: none;
    overflow-y: visible;
    white-space: pre-wrap;
    word-wrap: break-word;
    cursor: text;
  }

  .inline-edit-textarea:focus {
    outline: none;
  }

  .inline-edit-textarea:empty:before {
    content: attr(data-placeholder);
    color: var(--cds-text-02);
    font-style: italic;
    pointer-events: none;
  }

  .inline-edit-container {
    display: flex;
    flex-direction: column;
    width: 100%;
    min-height: 48px;
  }

  .inline-edit-container .inline-edit-textarea {
    flex: 1;
    min-height: 48px;
  }

  /* Status-based cell colors */
  .cell.target.status-translated {
    background: rgba(141, 141, 141, 0.10);
    border-left: 3px solid #8d8d8d;
  }

  .cell.target.status-reviewed {
    background: rgba(0, 157, 154, 0.15);
    border-left: 3px solid #009d9a;
  }

  .cell.target.status-approved {
    background: rgba(0, 157, 154, 0.15);
    border-left: 3px solid #009d9a;
  }

  .cell.target.status-translated:hover,
  .cell.target.status-reviewed:hover,
  .cell.target.status-approved:hover {
    filter: brightness(1.1);
  }

  .edit-icon, .lock-icon {
    position: absolute;
    right: 0.25rem;
    opacity: 0;
    color: var(--cds-icon-02);
    transition: opacity 0.15s ease;
  }

  .cell.target:hover .edit-icon {
    opacity: 1;
  }

  /* Selected cell states */
  .cell.cell-selected {
    background: var(--cds-layer-selected-01);
  }

  .cell.target.cell-selected {
    background: rgba(69, 137, 255, 0.1);
    border-left: 3px solid var(--cds-interactive-01, #0f62fe);
  }

  .cell.target.cell-selected .edit-icon {
    opacity: 0.7;
    color: var(--cds-interactive-01, #0f62fe);
  }

  .cell.target.cell-selected:hover .edit-icon,
  .cell.target.cell-selected.target-hovered .edit-icon {
    opacity: 1;
  }

  .cell.target.locked .lock-icon {
    opacity: 0.8;
    color: var(--cds-support-03);
  }

  /* QA Flag Styles */
  .cell.target.qa-flagged {
    border-left: 3px solid var(--cds-support-01, #da1e28);
    background: rgba(218, 30, 40, 0.08);
  }

  .cell.target.qa-flagged .edit-icon {
    right: 0.35rem;
  }

  .cell.target.qa-flagged:hover {
    background: rgba(218, 30, 40, 0.12);
  }

  /* Reference Column */
  .cell.reference {
    background: var(--cds-layer-02);
    color: var(--cds-text-02);
    font-size: 0.8rem;
    flex: none;
  }

  .cell.reference.has-match {
    background: rgba(36, 161, 72, 0.08);
    border-left: 2px solid var(--cds-support-02);
  }

  .cell.reference .ref-match {
    color: var(--cds-text-01);
  }

  .cell.reference .no-match {
    color: var(--cds-text-03);
    font-style: italic;
    font-size: 0.75rem;
    opacity: 0.7;
  }

  /* Game Dev Columns */
  .cell.gamedev-values,
  .cell.gamedev-children,
  .cell.gamedev-category,
  .cell.gamedev-filename,
  .cell.gamedev-textstate {
    background: var(--cds-layer-02);
    color: var(--cds-text-02);
    font-size: 0.8rem;
    flex: none;
  }

  .cell.gamedev-children {
    text-align: center;
    font-variant-numeric: tabular-nums;
  }

  /* LDE Category tag (gamedev grid) */
  .gamedev-category-tag {
    display: inline-block;
    padding: 1px 6px;
    border-radius: 3px;
    font-size: 0.7rem;
    font-weight: 500;
    border: 1px solid;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 90px;
  }

  /* FileName column (gamedev grid) */
  .gamedev-filename-text {
    font-family: monospace;
    font-size: 0.7rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  /* TextState badge (gamedev grid) */
  .textstate-badge {
    display: inline-block;
    padding: 1px 6px;
    border-radius: 3px;
    font-size: 0.65rem;
    font-weight: 600;
    letter-spacing: 0.3px;
    white-space: nowrap;
  }

  .textstate-korean {
    background: rgba(245, 158, 11, 0.2);
    color: #f59e0b;
    border: 1px solid rgba(245, 158, 11, 0.4);
  }

  .textstate-translated {
    background: rgba(34, 197, 94, 0.15);
    color: #22c55e;
    border: 1px solid rgba(34, 197, 94, 0.3);
  }

  .loading-cell {
    justify-content: center;
  }

  .placeholder-shimmer {
    width: 60%;
    height: 16px;
    background: #3a3a3a;
    border-radius: 4px;
  }

  /* AI Badge - TM-applied translations */
  .ai-badge {
    display: inline-flex;
    align-items: center;
    margin-left: 4px;
    color: #0f62fe;
    opacity: 0.7;
    vertical-align: middle;
  }

  .ai-badge:hover {
    opacity: 1;
  }

  /* Translation source badge (AI/TM indicator in source cell) */
  .translation-source-badge {
    display: inline-flex;
    align-items: center;
    gap: 2px;
    margin-left: 6px;
    padding: 1px 5px;
    border-radius: 3px;
    font-size: 0.5625rem;
    font-weight: 600;
    letter-spacing: 0.3px;
    vertical-align: middle;
    flex-shrink: 0;
    opacity: 0.85;
    transition: opacity 0.15s ease;
  }

  .translation-source-badge:hover {
    opacity: 1;
  }

  .translation-source-badge.ai {
    background: rgba(139, 92, 246, 0.15);
    color: #8b5cf6;
    border: 1px solid rgba(139, 92, 246, 0.3);
  }

  .translation-source-badge.tm {
    background: rgba(15, 98, 254, 0.12);
    color: #0f62fe;
    border: 1px solid rgba(15, 98, 254, 0.25);
  }

  .translation-source-badge .badge-text {
    line-height: 1;
  }
</style>
