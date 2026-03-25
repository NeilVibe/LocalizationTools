<script>
  import {
    InlineLoading,
    Tag,
    Dropdown
  } from "carbon-components-svelte";
  import { ChevronDown, MachineLearningModel } from "carbon-icons-svelte";
  import { onMount, onDestroy, tick } from "svelte";
  import { get } from "svelte/store";
  import { logger } from "$lib/utils/logger.js";
  import { getAuthHeaders, getApiBase } from "$lib/utils/api.js";
  import { ldmStore, joinFile, leaveFile, lockRow, unlockRow, isRowLocked, onCellUpdate, ldmConnected } from "$lib/stores/ldm.js";
  import { preferences } from "$lib/stores/preferences.js";
  import PresenceBar from "./PresenceBar.svelte";
  import CategoryFilter from "./CategoryFilter.svelte";
  import { getStatusKind } from '$lib/utils/statusColors';

  // Phase 84: Shared grid state and extracted modules
  import {
    grid,
    rowIndexById,
    rowHeightCache,
    loadedPages,
    tmAppliedRows,
    referenceData as gridReferenceData,
    getRowById,
    getRowIndexById,
    resetGridState,
    rebuildCumulativeHeights,
    PAGE_SIZE,
  } from './grid/gridState.svelte.ts';
  import ScrollEngine from './grid/ScrollEngine.svelte';
  import StatusColors from './grid/StatusColors.svelte';
  import CellRenderer from './grid/CellRenderer.svelte';
  import SelectionManager from './grid/SelectionManager.svelte';

  // Phase 84 Batch 2: CATEGORY_COLORS, getCategoryColor moved to CellRenderer.svelte
  import { stripColorTags, paColorToHtml, htmlToPaColor, hexToCSS } from "$lib/utils/colorParser.js";
  import SemanticResults from "./SemanticResults.svelte";

  // API base URL - centralized in api.js
  let API_BASE = $derived(getApiBase());

  // Svelte 5: Props
  let {
    fileId = $bindable(null),
    fileName = "",
    fileType = "translator",
    activeTMs = [],
    isLocalFile = false,
    gamedevDynamicColumns = null,
    // Callback props (Svelte 5 migration)
    onInlineEditStart = undefined,
    onRowUpdate = undefined,
    onRowSelect = undefined,
    onConfirmTranslation = undefined,
    onDismissQA = undefined,
    onRunQA = undefined,
    onAddToTM = undefined
  } = $props();

  // Phase 84: Constants, rowHeightCache, cumulativeHeights moved to gridState.svelte.ts

  // Real-time subscription
  let cellUpdateUnsubscribe = null;

  // Phase 84: loading, initialLoading, rows, total moved to grid state object
  let searchTerm = $state("");
  let searchDebounceTimer = null;

  // Note: Clear button directly manipulates both searchTerm and DOM input value

  // Phase 84: activeFilter moved to grid state object
  const filterOptions = [
    { id: "all", text: "All Rows" },
    { id: "confirmed", text: "Confirmed" },
    { id: "unconfirmed", text: "Unconfirmed" },
    { id: "qa_flagged", text: "QA Flagged" }
  ];

  // Phase 84: selectedCategories moved to grid state object

  // P5: Advanced Search state
  let searchMode = $state("contain"); // 'contain' | 'exact' | 'not_contain' | 'fuzzy'
  const searchModeOptions = [
    { id: "contain", text: "Contains", icon: "⊃" },
    { id: "exact", text: "Exact", icon: "=" },
    { id: "not_contain", text: "Excludes", icon: "≠" },
    { id: "fuzzy", text: "Similar", icon: "≈" }
  ];

  let searchFields = $state(["source", "target"]); // Default search in source and target
  const searchFieldOptions = [
    { id: "string_id", text: "ID" },
    { id: "source", text: "Source" },
    { id: "target", text: "Target" }
  ];

  // P5: Search settings popover state
  let showSearchSettings = $state(false);

  // P4: Semantic search state (fuzzy/Similar mode)
  let semanticResults = $state([]);
  let semanticSearchTime = $state(0);
  let semanticLoading = $state(false);

  // Phase 84: tmAppliedRows moved to gridState.svelte.ts

  // Phase 84: scrollTop, containerHeight, visibleStart, visibleEnd, loadedPages, loadingPages moved to ScrollEngine/gridState
  let containerEl = $state(null);

  // Phase 84: rowIndexById, getRowById, getRowIndexById moved to gridState.svelte.ts

  // Go to row state - REMOVED (BUG-001 - not useful)

  // Phase 84: grid.inlineEditingRowId moved to grid.inlineEditingRowId
  let inlineEditValue = $state("");
  let inlineEditTextarea = $state(null);
  let isCancellingEdit = $state(false); // Flag to prevent blur-save race condition
  let isConfirming = $state(false); // Guard flag to prevent re-entry during confirm

  // Color picker state for inline editing
  let showColorPicker = $state(false);
  let colorPickerPosition = $state({ x: 0, y: 0 });
  let textSelection = $state({ start: 0, end: 0, text: "" });

  // Default colors for PAColor format (fallback if source has no colors)
  const PAColors = [
    { name: "Gold", hex: "0xffe9bd23", css: "#e9bd23" },
    { name: "Green", hex: "0xff67d173", css: "#67d173" },
    { name: "Blue", hex: "0xff4a90d9", css: "#4a90d9" },
    { name: "Red", hex: "0xffff4444", css: "#ff4444" },
    { name: "Purple", hex: "0xffb88fdc", css: "#b88fdc" },
    { name: "Orange", hex: "0xffff9500", css: "#ff9500" },
    { name: "Cyan", hex: "0xff00bcd4", css: "#00bcd4" },
    { name: "Pink", hex: "0xffe91e63", css: "#e91e63" }
  ];

  /**
   * UI-113: Extract unique colors from source text
   * Returns array of color objects {hex, css, name} found in source
   */
  function extractColorsFromSource(sourceText) {
    if (!sourceText) return [];

    const colorPattern = /<PAColor(0x[0-9a-fA-F]{6,8})>/gi;
    const uniqueColors = new Map();
    let match;

    while ((match = colorPattern.exec(sourceText)) !== null) {
      const hex = match[1].toLowerCase();
      if (!uniqueColors.has(hex)) {
        const css = hexToCSS(hex);
        // Try to find a matching name from PAColors
        const known = PAColors.find(c => c.hex.toLowerCase() === hex);
        uniqueColors.set(hex, {
          hex: hex,
          css: css,
          name: known?.name || css // Use CSS color as name if unknown
        });
      }
    }

    return Array.from(uniqueColors.values());
  }

  // UI-113: Derived state for colors available in current editing row's source
  let sourceColors = $derived.by(() => {
    if (!grid.inlineEditingRowId) return [];
    const row = getRowById(grid.inlineEditingRowId);
    return row ? extractColorsFromSource(row.source) : [];
  });

  // Phase 84: grid.selectedRowId, grid.hoveredRowId, grid.hoveredCell moved to grid state object

  // Phase 84: tmSuggestions, tmLoading, qaLoading, lastQaResult moved to StatusColors

  // Phase 84 Batch 2: Context menu state moved to SelectionManager.svelte
  let selectionManager = $state(null);

  // Phase 84 Batch 2: Column definitions, resize system, getVisibleColumns all moved to CellRenderer.svelte
  // Phase 84: referenceData and referenceLoading moved to StatusColors
  // Local derived for template access
  let referenceLoading = $derived(statusColors?.isReferenceLoading() ?? false);

  // Phase 84: calculateVisibleRange, ensureRowsLoaded, loadPage, prefetchAdjacentPages,
  // scrollToRowById, scrollToRowNum all moved to ScrollEngine.svelte
  // ScrollEngine component ref for delegation
  let scrollEngine = $state(null);
  let statusColors = $state(null);

  // Re-export scroll functions via delegation
  export function scrollToRowById(rowId) { return scrollEngine?.scrollToRowById(rowId) ?? false; }
  export function scrollToRowNum(rowNum) { return scrollEngine?.scrollToRowNum(rowNum) ?? false; }

  // BUG-037: Export function to navigate to row and start editing (for QA panel integration)
  // Phase 2: Now uses inline editing instead of modal
  export async function openEditModalByRowId(rowId) {
    // First scroll to and highlight the row
    scrollToRowById(rowId);

    // Use O(1) lookup
    const row = getRowById(rowId);
    if (row) {
      // Phase 2: Use inline editing instead of modal
      await startInlineEdit(row);
    } else {
      logger.warning("Row not loaded yet", { rowId });
    }
  }

  // Phase 84: updateRowQAFlag and handleQADismiss delegated to StatusColors
  export function updateRowQAFlag(rowId, flagCount) { return statusColors?.updateRowQAFlag(rowId, flagCount); }
  function handleQADismiss(rowId) { return statusColors?.handleQADismiss(rowId); }

  // Phase 84: loadRows delegates to ScrollEngine with pre-reset of interaction state
  export async function loadRows() {
    if (!fileId) return;

    // Reset interaction state that belongs in parent (per D-19)
    grid.inlineEditingRowId = null;
    grid.selectedRowId = null;
    grid.hoveredRowId = null;
    grid.hoveredCell = null;
    semanticResults = [];
    grid.activeFilter = "all";
    grid.selectedCategories = [];
    tmAppliedRows.clear();
    gridReferenceData.clear();
    searchTerm = "";
    const inputEl = document.getElementById('ldm-search-input');
    if (inputEl) inputEl.value = "";

    // Delegate actual loading to ScrollEngine
    return scrollEngine?.loadRows();
  }

  // Handle search with debounce
  function handleSearch(event) {
    logger.info("handleSearch triggered", { searchTerm, searchMode, event: event?.type || 'no event' });
    if (searchDebounceTimer) clearTimeout(searchDebounceTimer);
    searchDebounceTimer = setTimeout(() => {
      // P4: Semantic search for fuzzy/Similar mode
      if (searchMode === 'fuzzy') {
        performSemanticSearch();
        return;
      }
      // Clear semantic results when not in fuzzy mode
      semanticResults = [];
      semanticSearchTime = 0;

      logger.info("handleSearch executing search", { searchTerm });
      loadedPages.clear();
      grid.rows = [];
      loadRows();
    }, 300);
  }

  // P4: Perform semantic search via API
  async function performSemanticSearch() {
    const query = searchTerm?.trim();
    if (!query) {
      semanticResults = [];
      semanticSearchTime = 0;
      return;
    }

    // Need at least one active TM for semantic search
    if (!activeTMs || activeTMs.length === 0) {
      semanticResults = [];
      semanticSearchTime = 0;
      logger.info("Semantic search skipped - no active TMs");
      return;
    }

    semanticLoading = true;
    try {
      const tmId = activeTMs[0].tm_id;
      const params = new URLSearchParams({
        query,
        tm_id: tmId.toString(),
        threshold: '0.5',
        max_results: '20'
      });

      logger.apiCall(`/api/ldm/semantic-search?${params}`, 'GET');
      const response = await fetch(`${API_BASE}/api/ldm/semantic-search?${params}`, {
        headers: getAuthHeaders()
      });

      if (response.ok) {
        const data = await response.json();
        semanticResults = data.results || [];
        semanticSearchTime = data.search_time_ms || 0;
        logger.info("Semantic search results", { count: semanticResults.length, timeMs: semanticSearchTime });
      } else {
        logger.error("Semantic search failed", { status: response.status });
        semanticResults = [];
      }
    } catch (err) {
      logger.error("Semantic search error", { error: err.message });
      semanticResults = [];
    } finally {
      semanticLoading = false;
    }
  }

  // P4: Handle semantic result selection - scroll to matching row
  function handleSemanticResultSelect(result) {
    // Try to find a matching row in loaded data by source text
    const matchRow = grid.rows.find(r => r && r.source === result.source_text);
    if (matchRow) {
      scrollToRowById(matchRow.id);
    }
    // Close the overlay
    semanticResults = [];
    semanticSearchTime = 0;
    logger.userAction("Semantic result selected", { source: result.source_text?.substring(0, 30) });
  }

  // P4: Close semantic results overlay
  function closeSemanticResults() {
    semanticResults = [];
    semanticSearchTime = 0;
  }

  // P4: Apply TM suggestion to a row (called from GridPage via side panel)
  export function applyTMToRow(lineNumber, targetText) {
    // Find the row by line_number (row_num)
    const row = grid.rows.find(r => r && r.row_num === lineNumber);
    if (!row) {
      logger.warning("applyTMToRow: row not found", { lineNumber });
      return;
    }
    // Start inline edit with the TM target text pre-filled
    startInlineEdit(row);
    tick().then(() => {
      if (inlineEditTextarea) {
        inlineEditTextarea.innerText = targetText;
        // Save immediately
        saveInlineEdit(false);
        // Mark as TM-applied for AI badge
        markRowAsTMApplied(row.id, 'fuzzy');
      }
    });
    logger.userAction("Applied TM to row", { lineNumber, target: targetText?.substring(0, 30) });
  }

  // Phase 84: markRowAsTMApplied delegated to StatusColors
  export function markRowAsTMApplied(rowId, matchType = 'fuzzy') { return statusColors?.markRowAsTMApplied(rowId, matchType); }

  // P2: Handle filter change
  function handleFilterChange(event) {
    grid.activeFilter = event.detail.selectedId;
    loadedPages.clear();
    grid.rows = [];
    loadRows();
    logger.userAction("Filter changed", { filter: grid.activeFilter });
  }

  // P16: Category filter change handler
  function handleCategoryFilterChange(categories) {
    grid.selectedCategories = categories;
    loadedPages.clear();
    grid.rows = [];
    loadRows();
    logger.userAction("Category filter changed", { categories: grid.selectedCategories });
  }

  // Go to specific row - REMOVED (BUG-001 - not useful)

  // Phase 84: fetchTMSuggestions moved to StatusColors.svelte
  function fetchTMSuggestions(sourceText, rowId) { return statusColors?.fetchTMSuggestions(sourceText, rowId); }

  // Phase 84: runQACheck, fetchQAResults moved to StatusColors.svelte

  // Phase 84: Reference functions (loadReferenceData, getReferenceForRow) moved to StatusColors.svelte
  // getReferenceForRow is still needed in template -- delegate to statusColors
  function getReferenceForRow(row, matchMode) {
    return statusColors?.getReferenceForRow(row, matchMode) ?? null;
  }

  // Phase 84: TM Results (getTMResultForRow, fetchTMResultForRow, fetchTMSuggestions)
  // and TM cache management moved to StatusColors.svelte

  // ============================================
  // Phase 2: Inline Editing (MemoQ-style)
  // ============================================

  /**
   * Start inline editing on a cell (double-click)
   */
  async function startInlineEdit(row) {
    if (!row) return;

    // P9: Skip locking for orphaned files (Offline Storage) - no multi-user sync
    if (!isLocalFile) {
      // Check if row is locked by another user
      const lock = isRowLocked(parseInt(row.id));
      if (lock && lock.locked_by) {
        logger.warning("Row locked by another user", { rowId: row.id, lockedBy: lock.locked_by });
        return;
      }

      // Request row lock for editing
      if (fileId) {
        const granted = await lockRow(fileId, parseInt(row.id));
        if (!granted) {
          logger.warning("Could not acquire lock for inline edit", { rowId: row.id });
          return;
        }
      }
    }

    // Set inline editing state
    grid.inlineEditingRowId = row.id;
    // Convert file-format linebreaks to actual \n for editing, then to HTML for WYSIWYG
    const rawText = formatTextForDisplay(row.target || "");
    const htmlContent = paColorToHtml(rawText);
    grid.selectedRowId = row.id;

    // Push initial state to undo stack
    pushUndoState(row.id, row.target || "");

    logger.userAction("Inline edit started", { rowId: row.id });

    // Dispatch event for consumers (e.g., NamingPanel in GameDevPage)
    onInlineEditStart?.({
      rowId: row.id,
      row,
      column: row.extra_data?.editing_attr || 'Name',
      value: row.target || row.source || ''
    });

    // Focus the contenteditable after render and set initial content
    await tick();
    if (inlineEditTextarea) {
      // Set content directly (not via reactive binding to avoid cursor reset)
      inlineEditTextarea.innerHTML = htmlContent;
      inlineEditTextarea.focus();
      // Move cursor to end using selection API
      const range = document.createRange();
      const sel = window.getSelection();
      range.selectNodeContents(inlineEditTextarea);
      range.collapse(false);
      sel.removeAllRanges();
      sel.addRange(range);
    }
  }

  /**
   * Save inline edit and move to next row (or just save)
   */
  async function saveInlineEdit(moveToNext = false) {
    // Don't save if we're intentionally cancelling (Escape key)
    if (!grid.inlineEditingRowId || isCancellingEdit) return;

    const row = getRowById(grid.inlineEditingRowId);
    if (!row) {
      cancelInlineEdit();
      return;
    }

    // Convert from HTML (contenteditable) back to PAColor format, then to file format
    // Read directly from textarea to avoid cursor reset issue
    const currentHtml = inlineEditTextarea?.innerHTML || "";
    const rawText = htmlToPaColor(currentHtml);
    const textToSave = formatTextForSave(rawText);

    // Only save if value changed (compare formatted values)
    if (textToSave !== row.target) {
      try {
        // P9: Unified endpoint - backend handles both PostgreSQL and SQLite
        const response = await fetch(`${API_BASE}/api/ldm/rows/${row.id}`, {
          method: 'PUT',
          headers: {
            ...getAuthHeaders(),
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            target: textToSave,
            status: 'translated' // Mark as translated when edited
          })
        });

        if (response.ok) {
          // Update local row data with file-format text
          row.target = textToSave;
          row.status = 'translated';

          // Invalidate height cache for this row (content changed, height may differ)
          const rowIndex = getRowIndexById(row.id);
          if (rowIndex !== undefined) {
            rowHeightCache.delete(rowIndex);
            rebuildCumulativeHeights(stripColorTags); // Recalculate all positions
          }

          logger.success("Inline edit saved", { rowId: row.id, offline: isLocalFile });

          // Phase 18: Save back to XML file for gamedev mode
          if (fileType === 'gamedev' && row.extra_data?.source_xml_path) {
            try {
              await fetch(`${API_BASE}/api/ldm/gamedata/save`, {
                method: 'PUT',
                headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  xml_path: row.extra_data.source_xml_path,
                  entity_index: row.extra_data.entity_index ?? (row.row_num - 1),
                  attr_name: row.extra_data.editing_attr || 'Name',
                  new_value: textToSave
                })
              });
            } catch (err) {
              console.warn('XML save-back failed (DB row saved):', err);
              // Don't fail the edit -- DB row is already saved
            }
          }

          onRowUpdate?.({ rowId: row.id });
        } else {
          logger.error("Failed to save inline edit", { status: response.status });
        }
      } catch (err) {
        logger.error("Error saving inline edit", { error: err.message });
      }
    }

    // Release lock (fire-and-forget) - skip for orphaned files (no locking)
    if (fileId && !isLocalFile) {
      unlockRow(fileId, parseInt(row.id));
    }

    // Clear inline editing state
    const currentRowId = grid.inlineEditingRowId;
    grid.inlineEditingRowId = null;
    inlineEditValue = "";

    // Move to next row if requested
    if (moveToNext) {
      const currentIndex = getRowIndexById(currentRowId);
      if (currentIndex !== undefined && grid.rows[currentIndex + 1]) {
        const nextRow = grid.rows[currentIndex + 1];
        if (nextRow && !nextRow.placeholder) {
          grid.selectedRowId = nextRow.id;
          onRowSelect?.({ row: nextRow });
          // Auto-start editing on next row
          await startInlineEdit(nextRow);
        }
      }
    }
  }

  /**
   * Cancel inline edit without saving
   */
  function cancelInlineEdit() {
    if (!grid.inlineEditingRowId) return;

    const rowId = grid.inlineEditingRowId;

    // Set flag to prevent blur handler from saving
    isCancellingEdit = true;

    // Release lock (fire-and-forget, no return value)
    if (fileId) {
      unlockRow(fileId, parseInt(rowId));
    }

    grid.inlineEditingRowId = null;
    inlineEditValue = "";
    logger.userAction("Inline edit cancelled", { rowId });

    // Reset cancel flag after DOM update
    setTimeout(() => { isCancellingEdit = false; }, 0);
  }

  /**
   * Handle right-click in contenteditable to show color picker
   */
  let savedRange = null; // Store selection range for color picker

  /**
   * UI-113: Handle right-click in edit mode - show edit-specific context menu
   */
  function handleEditContextMenu(e) {
    if (!inlineEditTextarea) return;

    e.preventDefault();

    // Get text selection from contenteditable
    const sel = window.getSelection();
    const range = sel && sel.rangeCount > 0 ? sel.getRangeAt(0) : null;
    const selectedText = sel ? sel.toString() : "";

    // Save the range for color application
    if (range && selectedText.length > 0) {
      savedRange = range.cloneRange();
      textSelection = {
        start: 0,
        end: selectedText.length,
        text: selectedText
      };
    } else {
      savedRange = null;
      textSelection = { start: 0, end: 0, text: "" };
    }

    // Show edit context menu (not just color picker)
    colorPickerPosition = { x: e.clientX, y: e.clientY };
    showColorPicker = true;
    logger.userAction("Edit context menu opened", { hasSelection: selectedText.length > 0 });
  }

  /**
   * UI-113: Edit actions for context menu
   */
  function handleEditCut() {
    if (!inlineEditTextarea) return;
    document.execCommand('cut');
    closeColorPicker();
    inlineEditTextarea.focus();
  }

  function handleEditCopy() {
    if (!inlineEditTextarea) return;
    document.execCommand('copy');
    closeColorPicker();
    inlineEditTextarea.focus();
  }

  function handleEditPaste() {
    if (!inlineEditTextarea) return;
    document.execCommand('paste');
    closeColorPicker();
    inlineEditTextarea.focus();
  }

  function handleEditSelectAll() {
    if (!inlineEditTextarea) return;
    closeColorPicker();
    // Select all text in contenteditable
    const range = document.createRange();
    range.selectNodeContents(inlineEditTextarea);
    const sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(range);
    inlineEditTextarea.focus();
  }

  /**
   * Apply color to selected text in contenteditable
   */
  function applyColor(color) {
    if (!inlineEditTextarea || !savedRange || textSelection.text.length === 0) {
      closeColorPicker();
      return;
    }

    // Focus the contenteditable
    inlineEditTextarea.focus();

    // Restore the saved selection
    const sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(savedRange);

    // Create a colored span to wrap the selection
    const coloredSpan = document.createElement('span');
    coloredSpan.style.color = hexToCSS(color.hex);
    coloredSpan.setAttribute('data-pacolor', color.hex);

    // Extract contents and wrap in span
    coloredSpan.appendChild(savedRange.extractContents());
    savedRange.insertNode(coloredSpan);

    // Note: Don't update inlineEditValue here - we read directly from textarea on save

    logger.userAction("Applied color to text", { color: color.name, text: textSelection.text });
    closeColorPicker();

    // Move cursor after the colored span
    tick().then(() => {
      if (inlineEditTextarea) {
        inlineEditTextarea.focus();
        const range = document.createRange();
        range.setStartAfter(coloredSpan);
        range.collapse(true);
        const sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
      }
    });
  }

  /**
   * Close color picker
   */
  function closeColorPicker() {
    showColorPicker = false;
    textSelection = { start: 0, end: 0, text: "" };
  }

  // Phase 84 Batch 2: handleGridKeydown moved to SelectionManager.handleKeyDown
  // Delegate to selectionManager
  function handleGridKeydown(e) {
    selectionManager?.handleKeyDown(e);
  }

  // Phase 84 Batch 2: confirmSelectedRow moved to SelectionManager

  /**
   * Handle keyboard events during inline edit
   * Hotkeys:
   * - Escape: Cancel edit
   * - Enter: Save and move to next
   * - Tab: Save and move to next
   * - Shift+Enter: New line
   * - Ctrl+S: Confirm (save as reviewed + add to TM)
   * - Ctrl+D: Dismiss QA issue for current row
   * - Ctrl+Z: Undo last edit
   * - Ctrl+Y: Redo
   */
  function handleInlineEditKeydown(e) {
    // Ctrl+S: Confirm (save as reviewed status + add to TM)
    if (e.ctrlKey && e.key === 's') {
      e.preventDefault();
      confirmInlineEdit();
      return;
    }

    // Ctrl+T: Mark as translated/needs review (yellow status)
    if (e.ctrlKey && e.key === 't') {
      e.preventDefault();
      markAsTranslated();
      return;
    }

    // Ctrl+D: Dismiss QA issues for current row
    if (e.ctrlKey && e.key === 'd') {
      e.preventDefault();
      dismissQAIssues();
      return;
    }

    // Ctrl+U: Revert to untranslated (reset status)
    if (e.ctrlKey && e.key === 'u') {
      e.preventDefault();
      revertRowStatus();
      return;
    }

    // Ctrl+Z: Undo
    if (e.ctrlKey && e.key === 'z' && !e.shiftKey) {
      e.preventDefault();
      undoEdit();
      return;
    }

    // Ctrl+Y or Ctrl+Shift+Z: Redo
    if ((e.ctrlKey && e.key === 'y') || (e.ctrlKey && e.shiftKey && e.key === 'z')) {
      e.preventDefault();
      redoEdit();
      return;
    }

    if (e.key === 'Escape') {
      e.preventDefault();
      e.stopPropagation();
      cancelInlineEdit();
      return;
    } else if (e.key === 'Enter' && !e.shiftKey) {
      // Enter without shift = save and move to next
      e.preventDefault();
      saveInlineEdit(true);
    } else if (e.key === 'Tab') {
      // Tab = save and move to next
      e.preventDefault();
      saveInlineEdit(true);
    }
    // Shift+Enter = newline (default behavior, don't prevent)
  }

  /**
   * Confirm translation: Save as "reviewed" status and add to linked TM
   */
  /**
   * Mark translation as "translated" (needs review) — yellow status via Ctrl+T
   * Saves current text without adding to TM (unlike Ctrl+S confirm which = reviewed + TM)
   */
  async function markAsTranslated() {
    if (!grid.inlineEditingRowId) return;

    const row = getRowById(grid.inlineEditingRowId);
    if (!row) return;

    const currentHtml = inlineEditTextarea?.innerHTML || "";
    const rawText = htmlToPaColor(currentHtml);
    const textToSave = formatTextForSave(rawText);

    try {
      const response = await fetch(`${API_BASE}/api/ldm/rows/${row.id}`, {
        method: 'PUT',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ target: textToSave, status: 'translated' })
      });

      if (response.ok) {
        row.target = textToSave;
        row.status = 'translated';
        const rowIndex = getRowIndexById(row.id);
        if (rowIndex !== undefined) {
          rowHeightCache.delete(rowIndex);
          rebuildCumulativeHeights(stripColorTags);
        }
        logger.success("Marked as translated (needs review)", { rowId: row.id });
        cancelInlineEdit();
      }
    } catch (err) {
      logger.error("Failed to mark as translated", { error: err.message });
    }
  }

  async function confirmInlineEdit() {
    if (!grid.inlineEditingRowId || isConfirming) return;

    // Set guard flags to prevent re-entry and blur-triggered saves
    isConfirming = true;
    isCancellingEdit = true;

    const row = getRowById(grid.inlineEditingRowId);
    if (!row) {
      isConfirming = false;
      cancelInlineEdit();
      return;
    }

    // CRITICAL: Convert HTML spans back to PAColor tags FIRST, then format for file
    // Read directly from textarea to avoid cursor reset issue
    const currentHtml = inlineEditTextarea?.innerHTML || "";
    const rawText = htmlToPaColor(currentHtml);
    const textToSave = formatTextForSave(rawText);

    try {
      // Save with "reviewed" status
      const response = await fetch(`${API_BASE}/api/ldm/rows/${row.id}`, {
        method: 'PUT',
        headers: {
          ...getAuthHeaders(),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          target: textToSave,
          status: 'reviewed'  // Confirmed = reviewed status
        })
      });

      if (response.ok) {
        // Update local row data with file-format text
        row.target = textToSave;
        row.status = 'reviewed';

        // Invalidate height cache for this row (content changed, height may differ)
        const rowIndex = getRowIndexById(row.id);
        if (rowIndex !== undefined) {
          rowHeightCache.delete(rowIndex);
          rebuildCumulativeHeights(stripColorTags); // Recalculate all positions
        }

        logger.success("Translation confirmed", { rowId: row.id, status: 'reviewed' });

        // Dispatch event to add to linked TM (handled by LDM.svelte)
        onConfirmTranslation?.({
          rowId: row.id,
          source: row.source,
          target: textToSave
        });

        onRowUpdate?.({ rowId: row.id });
      } else {
        logger.error("Failed to confirm translation", { status: response.status });
      }
    } catch (err) {
      logger.error("Error confirming translation", { error: err.message });
    }

    // Release lock (fire-and-forget)
    if (fileId) {
      unlockRow(fileId, parseInt(row.id));
    }

    const currentRowId = grid.inlineEditingRowId;
    grid.inlineEditingRowId = null;
    inlineEditValue = "";

    // Move to next row
    const currentIndex = getRowIndexById(currentRowId);
    if (currentIndex !== undefined && grid.rows[currentIndex + 1]) {
      const nextRow = grid.rows[currentIndex + 1];
      if (nextRow && !nextRow.placeholder) {
        grid.selectedRowId = nextRow.id;
        onRowSelect?.({ row: nextRow });
        await startInlineEdit(nextRow);
      }
    }

    // Reset guard flags after move-to-next completes (via microtask to ensure blur has fired)
    setTimeout(() => {
      isCancellingEdit = false;
      isConfirming = false;
    }, 0);
  }

  // Phase 84 Batch 2: dismissQAIssues moved to SelectionManager
  // Keep local delegate for inline edit keyboard handler (Ctrl+D)
  function dismissQAIssues() { selectionManager?.dismissQAIssues?.(); }

  /**
   * Revert row status to untranslated (Ctrl+U)
   * Works in both edit mode and selection mode
   */
  async function revertRowStatus() {
    const targetRowId = grid.inlineEditingRowId || grid.selectedRowId;
    if (!targetRowId) return;

    const row = getRowById(targetRowId);
    if (!row) return;

    // Already untranslated? Nothing to do
    if (row.status === 'untranslated') {
      logger.info("Row already untranslated", { rowId: row.id });
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/api/ldm/rows/${row.id}`, {
        method: 'PUT',
        headers: {
          ...getAuthHeaders(),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          status: 'untranslated'
        })
      });

      if (response.ok) {
        row.status = 'untranslated';
        logger.success("Row reverted to untranslated", { rowId: row.id });
        onRowUpdate?.({ rowId: row.id });
      } else {
        logger.error("Failed to revert row status", { rowId: row.id, status: response.status });
      }
    } catch (err) {
      logger.error("Error reverting row status", { error: err.message });
    }
  }

  // Phase 84 Batch 2: Context menu functions (handleCellContextMenu, closeContextMenu,
  // setRowStatus, copyToClipboard, runQAOnRow, dismissQAFromContextMenu, addToTMFromContextMenu,
  // handleGlobalClick) all moved to SelectionManager.svelte
  // Delegate context menu and cell click to selectionManager
  function handleCellContextMenu(e, rowId) { selectionManager?.handleContextMenu(e, rowId); }
  function handleGlobalClick(e) { selectionManager?.handleGlobalClick(e); }

  // Undo/Redo state
  let undoStack = $state([]);
  let redoStack = $state([]);
  const MAX_UNDO_HISTORY = 50;

  /**
   * Push current state to undo stack (called before making changes)
   */
  function pushUndoState(rowId, oldValue) {
    undoStack = [...undoStack.slice(-MAX_UNDO_HISTORY + 1), { rowId, value: oldValue }];
    redoStack = []; // Clear redo when new edit is made
  }

  /**
   * Undo last edit
   */
  function undoEdit() {
    if (undoStack.length === 0) {
      logger.info("Nothing to undo");
      return;
    }

    const lastState = undoStack[undoStack.length - 1];
    undoStack = undoStack.slice(0, -1);

    // Save current value to redo stack
    if (grid.inlineEditingRowId && inlineEditTextarea) {
      redoStack = [...redoStack, { rowId: grid.inlineEditingRowId, value: inlineEditTextarea.innerHTML }];
    }

    // Restore the previous value by setting innerHTML directly
    if (inlineEditTextarea) {
      inlineEditTextarea.innerHTML = lastState.value;
    }
    logger.userAction("Undo", { rowId: lastState.rowId });
  }

  /**
   * Redo last undone edit
   */
  function redoEdit() {
    if (redoStack.length === 0) {
      logger.info("Nothing to redo");
      return;
    }

    const redoState = redoStack[redoStack.length - 1];
    redoStack = redoStack.slice(0, -1);

    // Save current value to undo stack
    if (grid.inlineEditingRowId && inlineEditTextarea) {
      undoStack = [...undoStack, { rowId: grid.inlineEditingRowId, value: inlineEditTextarea.innerHTML }];
    }

    // Restore the redo value by setting innerHTML directly
    if (inlineEditTextarea) {
      inlineEditTextarea.innerHTML = redoState.value;
    }
    logger.userAction("Redo", { rowId: redoState.rowId });
  }

  // ============================================
  // Phase 2: Modal Editing REMOVED
  // Replaced by inline editing (startInlineEdit, saveInlineEdit, cancelInlineEdit)
  // TM/QA display moved to TMQAPanel.svelte (side panel)
  // ============================================

  // Handle real-time cell updates from other users
  // SMART INDEXING: Uses O(1) lookup instead of O(n) findIndex
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

  // getStatusKind imported from $lib/utils/statusColors

  // Format text for grid display - show actual line breaks
  // Text is displayed with pre-wrap, so \n shows as real line breaks
  // XML &lt;br/&gt; is converted to visual line breaks for display
  function formatGridText(text) {
    if (!text) return "";
    // Convert XML-style line breaks to actual newlines for display
    let formatted = text.replace(/&lt;br\/&gt;/g, '\n');
    // Also handle escaped versions
    formatted = formatted.replace(/\\n/g, '\n');
    return formatted;
  }

  /**
   * Convert file-format linebreaks to actual newlines for display in textarea
   * Handles: \\n (escaped), &lt;br/&gt; (XML escaped), <br/> (XML), <br> (Excel)
   */
  function formatTextForDisplay(text) {
    if (!text) return "";
    let result = text;
    // 1. XML escaped: &lt;br/&gt; → \n
    result = result.replace(/&lt;br\s*\/&gt;/gi, '\n');
    // 2. XML unescaped: <br/> or <br /> → \n
    result = result.replace(/<br\s*\/?>/gi, '\n');
    // 3. Escaped newlines: \\n → \n (literal backslash-n in text files)
    result = result.replace(/\\n/g, '\n');
    return result;
  }

  /**
   * Convert actual newlines back to file-format for saving
   * XML files use &lt;br/&gt;, TXT files keep \n
   */
  function formatTextForSave(text) {
    if (!text) return "";
    // Determine file type from fileName
    const isXML = fileName.toLowerCase().endsWith('.xml');
    const isExcel = fileName.toLowerCase().endsWith('.xlsx') || fileName.toLowerCase().endsWith('.xls');

    if (isXML) {
      // XML: convert actual newlines to &lt;br/&gt; (escaped for XML content)
      return text.replace(/\n/g, '&lt;br/&gt;');
    } else if (isExcel) {
      // Excel: convert actual newlines to <br> (unescaped)
      return text.replace(/\n/g, '<br>');
    } else {
      // TXT and others: keep actual newlines
      return text;
    }
  }

  // Phase 84: countDisplayLines, estimateRowHeight, measureRowHeight, rebuildCumulativeHeights,
  // getRowTop, getRowHeight, getTotalHeight, findRowAtPosition all moved to gridState.svelte.ts
  // Phase 84 Batch 2: Local getRowHeight wrapper moved to CellRenderer.svelte

  // UI-029: downloadFile removed - users download via right-click on FileExplorer

  // Phase 84 Batch 2: handleCellClick, hover handlers, prefetchedRowId moved to SelectionManager
  // Delegate cell click to selectionManager
  function handleCellClick(row, event) { selectionManager?.handleRowClick(row, event); }
  function handleCellMouseEnter(row, cellType) { selectionManager?.handleCellMouseEnter(row, cellType); }
  function handleCellMouseLeave() { selectionManager?.handleCellMouseLeave(); }
  function handleRowMouseLeave() { selectionManager?.handleRowMouseLeave(); }

  // Phase 84 Batch 2: Resize handlers moved to CellRenderer.svelte
  // Phase 84: visibleRows moved to gridState.svelte.ts (cross-module derived)
  // Phase 84 Batch 2: CellRenderer component ref
  let cellRenderer = $state(null);

  // Svelte 5: Effect - Watch file changes AND subscribe to real-time updates
  // CRITICAL: Must track previousFileId to prevent infinite loop (BUG-001)
  let previousFileId = $state(null);
  $effect(() => {
    if (fileId && fileId !== previousFileId) {
      logger.info("fileId changed - resetting and subscribing", { from: previousFileId, to: fileId });
      previousFileId = fileId;

      // Reset search
      searchTerm = "";

      // Subscribe to WebSocket updates (was causing infinite loop without previousFileId check!)
      joinFile(fileId);
      if (cellUpdateUnsubscribe) {
        cellUpdateUnsubscribe();
      }
      cellUpdateUnsubscribe = onCellUpdate(handleCellUpdates);

      // Load rows
      loadRows();
    }
  });

  // Svelte 5: Effect - Watch searchTerm changes
  // Simple effect - triggers on any searchTerm change
  $effect(() => {
    // Access searchTerm to establish dependency
    const term = searchTerm;
    logger.info("searchTerm effect triggered", { searchTerm: term, hasFileId: !!fileId });

    // Only search if we have a file loaded
    if (fileId && term !== undefined) {
      handleSearch();
    }
  });

  // ResizeObserver to handle container size changes
  let resizeObserver = null;

  // Phase 84: Local handleScroll delegates to ScrollEngine
  function handleScroll() {
    scrollEngine?.handleScroll();
  }

  // Svelte 5: Effect - Setup scroll listener when container element is available
  // Phase 84: Scroll handling delegated to ScrollEngine, but event + resize observer stays here
  $effect(() => {
    if (containerEl) {
      // Add scroll listener (delegates to ScrollEngine)
      containerEl.addEventListener('scroll', handleScroll);
      scrollEngine?.calculateVisibleRange();

      // Add resize observer to recalculate when container size changes
      if (!resizeObserver) {
        resizeObserver = new ResizeObserver(() => {
          scrollEngine?.calculateVisibleRange();
          cellRenderer?.updateContainerWidth(); // UI-083: Update for resize bar positions
        });
      }
      resizeObserver.observe(containerEl);
      cellRenderer?.updateContainerWidth(); // Initial width calculation

      // Cleanup function returned from $effect
      return () => {
        containerEl.removeEventListener('scroll', handleScroll);
        if (resizeObserver) {
          resizeObserver.disconnect();
        }
      };
    }
  });

  // Keep onMount for backward compatibility
  onMount(() => {
    if (containerEl) {
      scrollEngine?.calculateVisibleRange();
    }
  });

  // Cleanup on destroy (scroll/resize cleanup handled in $effect above)
  onDestroy(() => {
    if (fileId) {
      leaveFile(fileId);
    }
    if (cellUpdateUnsubscribe) {
      cellUpdateUnsubscribe();
    }
    if (searchDebounceTimer) {
      clearTimeout(searchDebounceTimer);
    }
  });
</script>

<div
  class="virtual-grid"
  style="--grid-font-size: {gridFontSize}; --grid-font-weight: {gridFontWeight}; --grid-font-family: {gridFontFamily}; --grid-font-color: {gridFontColor};"
  onkeydown={handleGridKeydown}
  tabindex="-1"
>
  {#if fileId}
    <!-- Phase 84: ScrollEngine (renderless) handles scroll, load, viewport -->
    <ScrollEngine
      bind:this={scrollEngine}
      {fileId}
      {fileType}
      {searchTerm}
      {searchMode}
      {searchFields}
      {activeTMs}
      activeFilter={grid.activeFilter}
      selectedCategories={grid.selectedCategories}
      {containerEl}
    />
    <!-- Phase 84: StatusColors (renderless) handles QA, TM, reference data -->
    <StatusColors
      bind:this={statusColors}
      {fileId}
      {activeTMs}
    />
    <!-- Phase 84 Batch 2: SelectionManager handles row selection, keyboard nav, hover, context menu -->
    <SelectionManager
      bind:this={selectionManager}
      {onRowSelect}
      onEditRequest={(row) => startInlineEdit(row)}
      {onRowUpdate}
      {onConfirmTranslation}
      {onDismissQA}
      {onRunQA}
      {onAddToTM}
      onTMPrefetch={fetchTMSuggestions}
    />
    <div class="grid-header">
      <div class="header-left">
        <h4>{fileName || `File #${fileId}`}</h4>
        <span class="row-count">{grid.total.toLocaleString()} rows</span>
        <Tag type={fileType === 'gamedev' ? 'teal' : 'blue'} size="sm">
          {fileType === 'gamedev' ? 'Game Dev' : 'Translator'}
        </Tag>
      </div>
      <!-- UI-029: Removed download menu - users download via right-click on file list -->
      <div class="header-right">
        <PresenceBar />
      </div>
    </div>

    <div class="search-filter-bar">
      <!-- P5: Combined Search Control -->
      <div class="search-control">
        <!-- Mode indicator button -->
        <button
          class="search-mode-btn"
          onclick={() => showSearchSettings = !showSearchSettings}
          title="Search settings"
        >
          <span class="mode-icon">{searchModeOptions.find(m => m.id === searchMode)?.icon || "⊃"}</span>
          <ChevronDown size={12} />
        </button>

        <!-- Search input -->
        <div class="search-input-wrapper">
          <input
            type="text"
            id="ldm-search-input"
            class="search-input"
            placeholder="Search {searchFields.join(', ')}..."
            oninput={(e) => {
              searchTerm = e.target.value;
              logger.info("Search oninput", { value: searchTerm });
            }}
          />
          {#if searchTerm}
            <button
              type="button"
              class="search-clear"
              onclick={() => {
                searchTerm = "";
                const inputEl = document.getElementById('ldm-search-input');
                if (inputEl) inputEl.value = "";
              }}
              aria-label="Clear search"
            >
              <svg width="14" height="14" viewBox="0 0 16 16">
                <path d="M12 4.7L11.3 4 8 7.3 4.7 4 4 4.7 7.3 8 4 11.3 4.7 12 8 8.7 11.3 12 12 11.3 8.7 8z"/>
              </svg>
            </button>
          {/if}
        </div>

        <!-- Settings popover -->
        {#if showSearchSettings}
          <div class="search-settings-popover">
            <div class="settings-section">
              <div class="settings-label">Mode</div>
              <div class="mode-buttons">
                {#each searchModeOptions as mode (mode.id)}
                  <button
                    class="mode-option {searchMode === mode.id ? 'active' : ''}"
                    onclick={() => { searchMode = mode.id; if (searchTerm) handleSearch(); }}
                    title={mode.text}
                  >
                    <span class="mode-option-icon">{mode.icon}</span>
                    <span class="mode-option-text">{mode.text}</span>
                  </button>
                {/each}
              </div>
            </div>
            <div class="settings-section">
              <div class="settings-label">Fields</div>
              <div class="field-toggles">
                {#each searchFieldOptions as field (field.id)}
                  <label class="field-toggle {searchFields.includes(field.id) ? 'active' : ''}">
                    <input
                      type="checkbox"
                      checked={searchFields.includes(field.id)}
                      onchange={(e) => {
                        if (e.target.checked) {
                          searchFields = [...searchFields, field.id];
                        } else {
                          searchFields = searchFields.filter(f => f !== field.id);
                        }
                        if (searchTerm) handleSearch();
                      }}
                    />
                    <span>{field.text}</span>
                  </label>
                {/each}
              </div>
            </div>
          </div>
          <!-- Backdrop to close popover -->
          <div class="settings-backdrop" onclick={() => showSearchSettings = false}></div>
        {/if}

        <!-- P4: Semantic Search Results Overlay (fuzzy/Similar mode) -->
        {#if searchMode === 'fuzzy' && (!activeTMs || activeTMs.length === 0) && searchTerm?.trim()}
          <div class="semantic-no-tm">
            <MachineLearningModel size={14} />
            Assign a TM to enable semantic search
          </div>
        {/if}
        <SemanticResults
          bind:results={semanticResults}
          searchTimeMs={semanticSearchTime}
          visible={searchMode === 'fuzzy' && semanticResults.length > 0}
          onSelect={handleSemanticResultSelect}
          onClose={closeSemanticResults}
        />
      </div>

      <!-- P2: Filter Dropdown -->
      <div class="filter-wrapper">
        <Dropdown
          size="sm"
          selectedId={grid.activeFilter}
          items={filterOptions}
          on:select={handleFilterChange}
          titleText=""
          hideLabel
        />
      </div>

      <!-- P16: Category Filter -->
      {#if fileType !== 'gamedev'}
        <CategoryFilter
          bind:selectedCategories={grid.selectedCategories}
          onchange={handleCategoryFilterChange}
        />
      {/if}
    </div>

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

    <!-- Phase 84 Batch 2: CellRenderer handles row/cell rendering, resize bars, column layout -->
    <div class="scroll-wrapper">
      <CellRenderer
        bind:this={cellRenderer}
        {fileType}
        bind:containerEl={containerEl}
        {gamedevDynamicColumns}
        inlineEditingRowId={grid.inlineEditingRowId}
        bind:inlineEditTextarea={inlineEditTextarea}
        onRowClick={handleCellClick}
        onRowDoubleClick={(row) => startInlineEdit(row)}
        onCellContextMenu={handleCellContextMenu}
        onCellMouseEnter={handleCellMouseEnter}
        onCellMouseLeave={handleCellMouseLeave}
        onRowMouseLeave={handleRowMouseLeave}
        onInlineEditKeydown={handleInlineEditKeydown}
        onInlineEditBlur={() => saveInlineEdit(false)}
        onEditContextMenu={handleEditContextMenu}
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

    <!-- UI-041: Removed grid-footer (useless "Showing rows X-Y of Z") -->
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

  <!-- UI-113: Edit Mode Context Menu (Color Picker + Edit Actions) -->
  {#if showColorPicker}
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="color-picker-overlay" onclick={closeColorPicker}></div>
    <div
      class="edit-context-menu"
      style="left: {colorPickerPosition.x}px; top: {colorPickerPosition.y}px;"
    >
      <!-- Color Section (only if source has colors AND text is selected) -->
      {#if sourceColors.length > 0 && textSelection.text.length > 0}
        <div class="edit-menu-section">
          <div class="edit-menu-header">Apply Color</div>
          <div class="color-picker-colors">
            {#each sourceColors as color (color.name)}
              <button
                class="color-swatch"
                style="background-color: {color.css};"
                title={color.name}
                onclick={() => applyColor(color)}
              >
                <span class="color-name">{color.name}</span>
              </button>
            {/each}
          </div>
          {#if textSelection.text}
            <div class="color-picker-preview">
              <span class="preview-label">Selected:</span>
              <span class="preview-text">"{textSelection.text.length > 30 ? textSelection.text.substring(0, 30) + '...' : textSelection.text}"</span>
            </div>
          {/if}
        </div>
        <div class="edit-menu-divider"></div>
      {:else if textSelection.text.length > 0 && sourceColors.length === 0}
        <div class="edit-menu-section">
          <div class="edit-menu-hint">No colors in source text</div>
        </div>
        <div class="edit-menu-divider"></div>
      {/if}

      <!-- Edit Actions -->
      <div class="edit-menu-section">
        <button class="edit-menu-item" onclick={handleEditCut} disabled={!textSelection.text}>
          <span class="edit-menu-icon">✂</span>
          <span>Cut</span>
          <span class="edit-menu-shortcut">Ctrl+X</span>
        </button>
        <button class="edit-menu-item" onclick={handleEditCopy} disabled={!textSelection.text}>
          <span class="edit-menu-icon">📋</span>
          <span>Copy</span>
          <span class="edit-menu-shortcut">Ctrl+C</span>
        </button>
        <button class="edit-menu-item" onclick={handleEditPaste}>
          <span class="edit-menu-icon">📝</span>
          <span>Paste</span>
          <span class="edit-menu-shortcut">Ctrl+V</span>
        </button>
        <div class="edit-menu-divider"></div>
        <button class="edit-menu-item" onclick={handleEditSelectAll}>
          <span class="edit-menu-icon">☑</span>
          <span>Select All</span>
          <span class="edit-menu-shortcut">Ctrl+A</span>
        </button>
      </div>
    </div>
  {/if}

  <!-- Phase 84 Batch 2: Context menu markup moved to SelectionManager.svelte -->
</div>

<!-- svelte:window for closing context menu -->
<svelte:window onclick={handleGlobalClick} />

<!-- Phase 2: Edit Modal REMOVED - replaced by inline editing
     Double-click Target cell = inline edit
     TM matches displayed in side panel (TMQAPanel.svelte)
-->

<style>
  .virtual-grid {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    background: var(--cds-background);
    /* UI-053 FIX: min-height: 0 allows flex child to shrink below content size */
    min-height: 0;
  }

  .grid-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem 1.25rem; /* More spacious header */
    border-bottom: 1px solid var(--cds-border-subtle-01);
    background: var(--cds-layer-01);
  }

  .header-left {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .header-right {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .grid-header h4 {
    margin: 0;
    font-size: 0.875rem;
    font-weight: 600;
  }

  .row-count {
    font-size: 0.75rem;
    color: var(--cds-text-02);
  }

  /* P2: Search + Filter bar layout */
  .search-filter-bar {
    display: flex;
    gap: 0.75rem;
    padding: 0.5rem 1rem;
    background: var(--cds-layer-01);
    border-bottom: 1px solid var(--cds-border-subtle-01);
    align-items: center;
  }

  .search-wrapper {
    flex: 1;
    min-width: 200px;
  }

  .search-wrapper :global(.bx--search) {
    background: var(--cds-field-01);
  }

  .search-wrapper :global(.bx--search-input) {
    background: var(--cds-field-01);
    border-bottom: 1px solid var(--cds-border-strong-01);
  }

  .search-wrapper :global(.bx--search-input:focus) {
    border-bottom: 2px solid var(--cds-interactive-01);
  }

  .filter-wrapper {
    flex: 0 0 160px;
  }

  .filter-wrapper :global(.bx--dropdown) {
    background: var(--cds-field-01);
    height: 2rem; /* Match search input height (32px) */
  }

  .filter-wrapper :global(.bx--list-box) {
    height: 2rem; /* Match search input height (32px) */
  }

  .filter-wrapper :global(.bx--list-box__field) {
    height: 2rem; /* Match search input height (32px) */
  }

  /* P5: Combined Search Control */
  .search-control {
    display: flex;
    align-items: center;
    flex: 1;
    min-width: 200px;
    /* Removed max-width: 400px - was too restrictive, matching old search-wrapper behavior */
    position: relative;
  }

  .search-mode-btn {
    display: flex;
    align-items: center;
    gap: 2px;
    padding: 0 8px;
    height: 2rem;
    background: var(--cds-field-02);
    border: 1px solid var(--cds-border-subtle-01);
    border-right: none;
    border-radius: 4px 0 0 4px;
    cursor: pointer;
    color: var(--cds-text-01);
    font-size: 0.875rem;
    transition: background 0.15s;
  }

  .search-mode-btn:hover {
    background: var(--cds-layer-hover-01);
  }

  .mode-icon {
    font-size: 1rem;
    font-weight: 500;
  }

  .search-input-wrapper {
    flex: 1;
    position: relative;
  }

  .search-input {
    width: 100%;
    height: 2rem;
    padding: 0 2rem 0 0.75rem;
    background: var(--cds-field-01);
    border: 1px solid var(--cds-border-subtle-01);
    border-radius: 0 4px 4px 0;
    color: var(--cds-text-01);
    font-size: 0.875rem;
    outline: none;
  }

  .search-input:focus {
    border-color: var(--cds-focus);
    box-shadow: inset 0 0 0 1px var(--cds-focus);
  }

  .search-input::placeholder {
    color: var(--cds-text-05);
  }

  .search-clear {
    position: absolute;
    right: 4px;
    top: 50%;
    transform: translateY(-50%);
    display: flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    background: transparent;
    border: none;
    cursor: pointer;
    color: var(--cds-text-02);
    border-radius: 2px;
  }

  .search-clear:hover {
    background: var(--cds-layer-hover-01);
    color: var(--cds-text-01);
  }

  /* Search Settings Popover */
  .search-settings-popover {
    position: absolute;
    top: calc(100% + 4px);
    left: 0;
    z-index: 1000;
    background: var(--cds-layer-01);
    border: 1px solid var(--cds-border-subtle-01);
    border-radius: 6px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
    padding: 12px;
    min-width: 280px;
  }

  .settings-section {
    margin-bottom: 12px;
  }

  .settings-section:last-child {
    margin-bottom: 0;
  }

  .settings-label {
    font-size: 0.7rem;
    font-weight: 600;
    color: var(--cds-text-02);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 6px;
  }

  .mode-buttons {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 4px;
  }

  .mode-option {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 10px;
    background: var(--cds-field-01);
    border: 1px solid var(--cds-border-subtle-01);
    border-radius: 4px;
    cursor: pointer;
    transition: all 0.15s;
    color: var(--cds-text-02);
  }

  .mode-option:hover {
    background: var(--cds-layer-hover-01);
    color: var(--cds-text-01);
  }

  .mode-option.active {
    background: var(--cds-interactive-01);
    border-color: var(--cds-interactive-01);
    color: var(--cds-text-on-color);
  }

  .mode-option-icon {
    font-size: 1rem;
    font-weight: 600;
  }

  .mode-option-text {
    font-size: 0.8rem;
  }

  .field-toggles {
    display: flex;
    gap: 6px;
  }

  .field-toggle {
    display: flex;
    align-items: center;
    padding: 6px 10px;
    background: var(--cds-field-01);
    border: 1px solid var(--cds-border-subtle-01);
    border-radius: 4px;
    cursor: pointer;
    transition: all 0.15s;
    font-size: 0.8rem;
    color: var(--cds-text-02);
  }

  .field-toggle:hover {
    background: var(--cds-layer-hover-01);
  }

  .field-toggle.active {
    background: var(--cds-interactive-02);
    border-color: var(--cds-interactive-02);
    color: var(--cds-text-on-color);
  }

  .field-toggle input[type="checkbox"] {
    display: none;
  }

  .settings-backdrop {
    position: fixed;
    inset: 0;
    z-index: 999;
  }

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

  .table-header {
    display: flex;
    background: var(--cds-layer-accent-01);
    border-bottom: 2px solid var(--cds-border-subtle-02, #525252);
    font-weight: 600;
    font-size: 0.8125rem;
    text-transform: none; /* Cleaner look without uppercase */
    letter-spacing: normal;
    color: var(--cds-text-01);
    /* Sticky header for long scrolls */
    position: sticky;
    top: 0;
    z-index: 10;
  }

  /* Phase 84 Batch 2: column-resize-bar, th, th-source, th-target CSS moved to CellRenderer.svelte */

  /* FIX: Wrapper for scroll container + resize bars overlay */
  .scroll-wrapper {
    flex: 1;
    display: flex;
    flex-direction: column;
    position: relative;
    min-height: 0;
    height: 0; /* Critical for flex to work */
  }

  /* Phase 84 Batch 2: scroll-container, scroll-content, loading-overlay CSS moved to CellRenderer.svelte */

  /* Phase 84 Batch 2: virtual-row, cell, cell-content, inline-edit CSS moved to CellRenderer.svelte */

  /* Color Picker/Edit Context Menu CSS - stays in VirtualGrid (color picker is parent-owned, used in edit mode) */
  .color-picker-overlay {
    position: fixed;
    inset: 0;
    z-index: 999;
  }

  .color-picker-colors {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 4px;
    padding: 0.5rem;
  }

  .color-swatch {
    width: 100%;
    aspect-ratio: 1;
    border: 2px solid transparent;
    border-radius: 4px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.15s ease;
  }

  .color-swatch:hover {
    transform: scale(1.1);
    border-color: var(--cds-border-strong-01);
  }

  .color-swatch .color-name {
    font-size: 0.5rem;
    color: #000;
    text-shadow: 0 0 2px #fff, 0 0 2px #fff;
    font-weight: 600;
  }

  .color-picker-preview {
    padding: 0.5rem 0.75rem;
    background: var(--cds-layer-01);
    border-top: 1px solid var(--cds-border-subtle-01);
    font-size: 0.7rem;
    color: var(--cds-text-02);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .color-picker-preview .preview-text {
    font-style: italic;
  }

  .color-picker-preview .preview-label {
    color: var(--cds-text-02);
    margin-right: 0.25rem;
  }

  /* UI-113: Edit Context Menu (replaces simple color picker) */
  .edit-context-menu {
    position: fixed;
    z-index: 1000;
    min-width: 220px;
    background: var(--cds-layer-02);
    border: 1px solid var(--cds-border-strong-01);
    border-radius: 4px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    overflow: hidden;
  }

  .edit-menu-section {
    padding: 0.25rem 0;
  }

  .edit-menu-header {
    padding: 0.5rem 0.75rem 0.25rem;
    font-size: 0.7rem;
    font-weight: 600;
    color: var(--cds-text-02);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .edit-menu-hint {
    padding: 0.5rem 0.75rem;
    font-size: 0.7rem;
    color: var(--cds-text-03);
    font-style: italic;
  }

  .edit-menu-divider {
    height: 1px;
    background: var(--cds-border-subtle-01);
    margin: 0.25rem 0;
  }

  .edit-menu-item {
    display: flex;
    align-items: center;
    width: 100%;
    padding: 0.5rem 0.75rem;
    background: none;
    border: none;
    color: var(--cds-text-01);
    font-size: 0.8rem;
    cursor: pointer;
    text-align: left;
    gap: 0.5rem;
  }

  .edit-menu-item:hover:not(:disabled) {
    background: var(--cds-layer-hover-02);
  }

  .edit-menu-item:disabled {
    color: var(--cds-text-03);
    cursor: not-allowed;
  }

  .edit-menu-icon {
    width: 1rem;
    text-align: center;
    font-size: 0.9rem;
  }

  .edit-menu-item span:nth-child(2) {
    flex: 1;
  }

  .edit-menu-shortcut {
    font-size: 0.65rem;
    color: var(--cds-text-03);
  }

  /* Phase 84 Batch 2: Status cell colors, edit/lock icons, QA flags, reference, gamedev, TM match,
     loading-cell, placeholder-shimmer CSS all moved to CellRenderer.svelte */

  .loading-bar {
    padding: 0.25rem 1rem;
    background: var(--cds-layer-02);
    border-top: 1px solid var(--cds-border-subtle-01);
  }

  .empty-state {
    display: flex;
    justify-content: center;
    align-items: center;
    height: 100%;
    color: var(--cds-text-02);
  }

  .empty-state-content {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.75rem;
    text-align: center;
  }

  .empty-state-icon {
    color: var(--cds-text-03);
    margin-bottom: 0.25rem;
  }

  .empty-state-title {
    font-size: 1rem;
    font-weight: 500;
    color: var(--cds-text-01);
    margin: 0;
  }

  .empty-state-hint {
    font-size: 0.8125rem;
    color: var(--cds-text-03);
    margin: 0;
  }

  /* ========================================
     Phase 2: EDIT MODAL CSS REMOVED
     Replaced by:
     - Inline editing (double-click Target cell)
     - TMQAPanel.svelte (side panel for TM/QA)
     ======================================== */

  /* Phase 84 Batch 2: Context menu CSS moved to SelectionManager.svelte */

  /* Phase 84 Batch 2: ai-badge, translation-source-badge CSS moved to CellRenderer.svelte */

  /* P4: Semantic search no-TM message */
  .semantic-no-tm {
    position: absolute;
    top: calc(100% + 4px);
    left: 0;
    right: 0;
    z-index: 1001;
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 14px;
    background: var(--cds-layer-01);
    border: 1px solid var(--cds-border-subtle-01);
    border-radius: 6px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
    font-size: 0.8rem;
    color: var(--cds-text-02);
  }
</style>
