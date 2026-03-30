<script>
  /**
   * InlineEditor.svelte -- Textarea editing, color picker, undo/redo, save/cancel.
   *
   * Phase 84 Batch 3: Extracted from VirtualGrid.svelte.
   * Owns all inline editing UX: start/save/cancel/confirm, keyboard shortcuts,
   * color picker, undo/redo stack, text format conversion.
   *
   * Writes to gridState: grid.inlineEditingRowId, grid.selectedRowId, grid.rows[index] (on save)
   * Reads from gridState: grid, getRowById, getRowIndexById
   */

  import { tick } from 'svelte';
  import { logger } from '$lib/utils/logger.js';
  import { getAuthHeaders, getApiBase } from '$lib/utils/api.js';
  import { lockRow, unlockRow, isRowLocked } from '$lib/stores/ldm.js';
  import { stripColorTags, paColorToHtml, htmlToPaColor, hexToCSS } from '$lib/utils/colorParser.js';
  import {
    grid,
    getRowById,
    getRowIndexById,
    rowHeightCache,
    rebuildCumulativeHeights,
  } from './gridState.svelte.ts';

  // API base URL
  let API_BASE = $derived(getApiBase());

  // Props via $props() (per D-05)
  let {
    fileId = null,
    fileName = "",
    fileType = "translator",
    isLocalFile = false,
    // Callback props forwarded from parent
    onInlineEditStart = undefined,
    onRowUpdate = undefined,
    onRowSelect = undefined,
    onConfirmTranslation = undefined,
    // FIX-03: onSaveComplete was dead (declared but never called) — removed
  } = $props();

  // ============================================================
  // INLINE EDITING STATE (module-local)
  // ============================================================
  let inlineEditValue = $state("");
  let inlineEditTextarea = $state(null);
  let isCancellingEdit = $state(false);
  let isConfirming = $state(false);
  let isSaving = $state(false);

  // Color picker state
  let showColorPicker = $state(false);
  let colorPickerPosition = $state({ x: 0, y: 0 });
  let textSelection = $state({ start: 0, end: 0, text: "" });
  let savedRange = null;

  // Default colors for PAColor format
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

  // Undo/Redo state
  let undoStack = $state([]);
  let redoStack = $state([]);
  const MAX_UNDO_HISTORY = 50;

  // ============================================================
  // DERIVED STATE
  // ============================================================

  /** UI-113: Extract unique colors from source text */
  function extractColorsFromSource(sourceText) {
    if (!sourceText) return [];
    const colorPattern = /<PAColor(0x[0-9a-fA-F]{6,8})>/gi;
    const uniqueColors = new Map();
    let match;
    while ((match = colorPattern.exec(sourceText)) !== null) {
      const hex = match[1].toLowerCase();
      if (!uniqueColors.has(hex)) {
        const css = hexToCSS(hex);
        const known = PAColors.find(c => c.hex.toLowerCase() === hex);
        uniqueColors.set(hex, {
          hex: hex,
          css: css,
          name: known?.name || css
        });
      }
    }
    return Array.from(uniqueColors.values());
  }

  let sourceColors = $derived.by(() => {
    if (!grid.inlineEditingRowId) return [];
    const row = getRowById(grid.inlineEditingRowId);
    return row ? extractColorsFromSource(row.source) : [];
  });

  // ============================================================
  // TEXT FORMAT HELPERS
  // ============================================================

  /** Convert file-format linebreaks to actual newlines for display in textarea */
  function formatTextForDisplay(text) {
    if (!text) return "";
    let result = text;
    result = result.replace(/&lt;br\s*\/&gt;/gi, '\n');
    result = result.replace(/<br\s*\/?>/gi, '\n');
    result = result.replace(/\\n/g, '\n');
    return result;
  }

  /** Convert actual newlines back to file-format for saving */
  function formatTextForSave(text) {
    if (!text) return "";
    const isXML = fileName.toLowerCase().endsWith('.xml');
    const isExcel = fileName.toLowerCase().endsWith('.xlsx') || fileName.toLowerCase().endsWith('.xls');
    if (isXML) {
      return text.replace(/\n/g, '&lt;br/&gt;');
    } else if (isExcel) {
      return text.replace(/\n/g, '<br>');
    } else {
      return text;
    }
  }

  // ============================================================
  // COMMON SAVE HELPERS
  // ============================================================

  /** Read current textarea content, convert to save format */
  function getCurrentTextToSave() {
    const currentHtml = inlineEditTextarea?.innerHTML || "";
    const rawText = htmlToPaColor(currentHtml);
    return formatTextForSave(rawText);
  }

  /** Save row to API, update local state, invalidate height cache.
   *  OPTIMISTIC: updates local state IMMEDIATELY, then fires API in background.
   *  If API fails, reverts the local change. */
  async function saveRowToAPI(row, textToSave, status) {
    // Optimistic update — instant UI feedback, no waiting for network
    const oldTarget = row.target;
    const oldStatus = row.status;
    row.target = textToSave;
    row.status = status;
    const rowIndex = getRowIndexById(row.id);
    if (rowIndex !== undefined) {
      rowHeightCache.delete(rowIndex);
      // Defer height rebuild to next frame — don't block the edit flow
      requestAnimationFrame(() => rebuildCumulativeHeights(stripColorTags));
    }

    // Fire API call (non-blocking for the edit flow)
    try {
      const response = await fetch(`${API_BASE}/api/ldm/rows/${row.id}`, {
        method: 'PUT',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ target: textToSave, status })
      });
      if (!response.ok) {
        // Revert on failure
        row.target = oldTarget;
        row.status = oldStatus;
        logger.error("API save failed — reverted", { rowId: row.id, status: response.status });
        return false;
      }
      // Save back to XML for gamedev mode
      if (fileType === 'gamedev' && row.extra_data?.source_xml_path) {
        fetch(`${API_BASE}/api/ldm/gamedata/save`, {
          method: 'PUT',
          headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
          body: JSON.stringify({
            xml_path: row.extra_data.source_xml_path,
            entity_index: row.extra_data.entity_index ?? (row.row_num - 1),
            attr_name: row.extra_data.editing_attr || 'Name',
            new_value: textToSave
          })
        }).catch(err => console.warn('XML save-back failed (DB row saved):', err));
      }
      return true;
    } catch (err) {
      // Network error — revert
      row.target = oldTarget;
      row.status = oldStatus;
      logger.error("API save network error — reverted", { rowId: row.id, error: err.message });
      return false;
    }
  }

  /** End editing, release lock, clear state, optionally move to next row */
  async function endEditAndMoveNext(moveToNext) {
    if (fileId && !isLocalFile) {
      unlockRow(fileId, parseInt(grid.inlineEditingRowId));
    }
    const currentRowId = grid.inlineEditingRowId;
    grid.inlineEditingRowId = null;
    inlineEditValue = "";
    if (moveToNext) {
      const currentIndex = getRowIndexById(currentRowId);
      if (currentIndex !== undefined && grid.rows[currentIndex + 1]) {
        const nextRow = grid.rows[currentIndex + 1];
        if (nextRow && !nextRow.placeholder) {
          grid.selectedRowId = nextRow.id;
          // Flag isEditing so GridPage skips TM fetch during edit-to-edit transitions
          onRowSelect?.({ row: nextRow, isEditing: true });
          await startInlineEdit(nextRow);
        }
      }
    }
  }

  // ============================================================
  // CORE EDITING FUNCTIONS (exported for parent delegation)
  // ============================================================

  /** Start inline editing on a row (double-click or programmatic) */
  export async function startInlineEdit(row) {
    if (!row) return;

    // P9: Skip locking for orphaned files (Offline Storage)
    if (!isLocalFile) {
      const lock = isRowLocked(parseInt(row.id));
      if (lock && lock.locked_by) {
        logger.warning("Row locked by another user", { rowId: row.id, lockedBy: lock.locked_by });
        return;
      }
      if (fileId) {
        const granted = await lockRow(fileId, parseInt(row.id));
        if (!granted) {
          logger.warning("Could not acquire lock for inline edit", { rowId: row.id });
          return;
        }
      }
    }

    grid.inlineEditingRowId = row.id;
    const rawText = formatTextForDisplay(row.target || "");
    const htmlContent = paColorToHtml(rawText);
    grid.selectedRowId = row.id;

    pushUndoState(row.id, row.target || "");

    logger.userAction("Inline edit started", { rowId: row.id });

    onInlineEditStart?.({
      rowId: row.id,
      row,
      column: row.extra_data?.editing_attr || 'Name',
      value: row.target || row.source || ''
    });

    await tick();
    if (inlineEditTextarea) {
      inlineEditTextarea.innerHTML = htmlContent;
      inlineEditTextarea.focus();
      const range = document.createRange();
      const sel = window.getSelection();
      range.selectNodeContents(inlineEditTextarea);
      range.collapse(false);
      sel.removeAllRanges();
      sel.addRange(range);
    }
  }

  /** Save inline edit and optionally move to next row.
   *  isSaving guard prevents double-save from blur + keyboard racing. */
  export async function saveInlineEdit(moveToNext = false) {
    if (!grid.inlineEditingRowId || isCancellingEdit || isSaving) return;
    isSaving = true;

    const row = getRowById(grid.inlineEditingRowId);
    if (!row) { isSaving = false; cancelInlineEdit(); return; }

    const textToSave = getCurrentTextToSave();
    if (textToSave !== row.target) {
      try {
        const ok = await saveRowToAPI(row, textToSave, 'translated');
        if (ok) {
          logger.success("Inline edit saved", { rowId: row.id, offline: isLocalFile });
          onRowUpdate?.({ rowId: row.id });
        } else {
          logger.error("Failed to save inline edit");
        }
      } catch (err) {
        logger.error("Error saving inline edit", { error: err.message });
      }
    }

    await endEditAndMoveNext(moveToNext);
    isSaving = false;
  }

  /** Cancel inline edit without saving */
  export function cancelInlineEdit() {
    if (!grid.inlineEditingRowId) return;

    const rowId = grid.inlineEditingRowId;
    isCancellingEdit = true;

    if (fileId) {
      unlockRow(fileId, parseInt(rowId));
    }

    grid.inlineEditingRowId = null;
    inlineEditValue = "";
    logger.userAction("Inline edit cancelled", { rowId });

    setTimeout(() => { isCancellingEdit = false; }, 0);
  }

  /** Navigate to row and start editing (exported for parent delegation) */
  export async function openEditModalByRowId(rowId) {
    const row = getRowById(rowId);
    if (row) {
      await startInlineEdit(row);
    } else {
      logger.warning("Row not loaded yet", { rowId });
    }
  }

  // ============================================================
  // CONFIRM / STATUS CHANGE
  // ============================================================

  /** Confirm translation: Save as "reviewed" + add to TM */
  async function confirmInlineEdit() {
    if (!grid.inlineEditingRowId || isConfirming || isSaving) return;
    isConfirming = true;
    isSaving = true;
    isCancellingEdit = true;

    const row = getRowById(grid.inlineEditingRowId);
    if (!row) { isConfirming = false; cancelInlineEdit(); return; }

    const textToSave = getCurrentTextToSave();
    try {
      const ok = await saveRowToAPI(row, textToSave, 'reviewed');
      if (ok) {
        logger.success("Translation confirmed", { rowId: row.id, status: 'reviewed' });
        onConfirmTranslation?.({ rowId: row.id, source: row.source, target: textToSave });
        onRowUpdate?.({ rowId: row.id });
      } else {
        logger.error("Failed to confirm translation");
      }
    } catch (err) {
      logger.error("Error confirming translation", { error: err.message });
    }

    await endEditAndMoveNext(true);
    setTimeout(() => { isCancellingEdit = false; isConfirming = false; isSaving = false; }, 0);
  }

  /** Mark as translated (needs review) via Ctrl+T */
  async function markAsTranslated() {
    if (!grid.inlineEditingRowId) return;
    const row = getRowById(grid.inlineEditingRowId);
    if (!row) return;

    try {
      const ok = await saveRowToAPI(row, getCurrentTextToSave(), 'translated');
      if (ok) logger.success("Marked as translated (needs review)", { rowId: row.id });
    } catch (err) {
      logger.error("Failed to mark as translated", { error: err.message });
    }
    cancelInlineEdit();
  }

  /** Revert row status to untranslated (Ctrl+U) */
  async function revertRowStatus() {
    const targetRowId = grid.inlineEditingRowId || grid.selectedRowId;
    if (!targetRowId) return;

    const row = getRowById(targetRowId);
    if (!row) return;

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
        body: JSON.stringify({ status: 'untranslated' })
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

  // ============================================================
  // KEYBOARD HANDLER (exported for CellRenderer callback)
  // ============================================================

  /** Handle keyboard events during inline edit */
  export function handleInlineEditKeydown(e) {
    if (e.ctrlKey && e.key === 's') {
      e.preventDefault();
      confirmInlineEdit();
      return;
    }
    if (e.ctrlKey && e.key === 't') {
      e.preventDefault();
      markAsTranslated();
      return;
    }
    if (e.ctrlKey && e.key === 'd') {
      e.preventDefault();
      dismissQAIssuesDelegate?.();
      return;
    }
    if (e.ctrlKey && e.key === 'u') {
      e.preventDefault();
      revertRowStatus();
      return;
    }
    if (e.ctrlKey && e.key === 'z' && !e.shiftKey) {
      e.preventDefault();
      undoEdit();
      return;
    }
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
    } else if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      // Ctrl+Enter = save and confirm
      e.preventDefault();
      saveInlineEdit(true);
    } else if (e.key === 'Enter' && !e.shiftKey) {
      // Enter = insert visual linebreak (saved as <br/> in XML)
      // insertHTML puts an actual <br> element in the contenteditable div
      // On save, htmlToPaColor converts <br> → \n → formatTextForSave → &lt;br/&gt;
      e.preventDefault();
      // Single <br> for line break. At end-of-content, browsers need a trailing
      // <br> to show the cursor on the new line, so we check and add one if needed.
      const sel = window.getSelection();
      const range = sel?.getRangeAt(0);
      const atEnd = range && range.endContainer === inlineEditTextarea &&
        range.endOffset === inlineEditTextarea.childNodes.length;
      document.execCommand('insertHTML', false, atEnd ? '<br><br>' : '<br>');
    } else if (e.key === 'Tab') {
      e.preventDefault();
      saveInlineEdit(true);
    }
  }

  // Delegate for Ctrl+D (dismiss QA) -- set by parent
  let dismissQAIssuesDelegate = $state(null);
  export function setDismissQADelegate(fn) { dismissQAIssuesDelegate = fn; }

  function pushUndoState(rowId, oldValue) {
    undoStack = [...undoStack.slice(-MAX_UNDO_HISTORY + 1), { rowId, value: oldValue }];
    redoStack = [];
  }

  function undoEdit() {
    if (undoStack.length === 0) {
      logger.info("Nothing to undo");
      return;
    }
    const lastState = undoStack[undoStack.length - 1];
    undoStack = undoStack.slice(0, -1);
    if (grid.inlineEditingRowId && inlineEditTextarea) {
      redoStack = [...redoStack, { rowId: grid.inlineEditingRowId, value: inlineEditTextarea.innerHTML }];
    }
    if (inlineEditTextarea) {
      inlineEditTextarea.innerHTML = lastState.value;
    }
    logger.userAction("Undo", { rowId: lastState.rowId });
  }

  function redoEdit() {
    if (redoStack.length === 0) {
      logger.info("Nothing to redo");
      return;
    }
    const redoState = redoStack[redoStack.length - 1];
    redoStack = redoStack.slice(0, -1);
    if (grid.inlineEditingRowId && inlineEditTextarea) {
      undoStack = [...undoStack, { rowId: grid.inlineEditingRowId, value: inlineEditTextarea.innerHTML }];
    }
    if (inlineEditTextarea) {
      inlineEditTextarea.innerHTML = redoState.value;
    }
    logger.userAction("Redo", { rowId: redoState.rowId });
  }

  /** Handle right-click in edit mode -- show color picker */
  export function handleEditContextMenu(e) {
    if (!inlineEditTextarea) return;
    e.preventDefault();

    const sel = window.getSelection();
    const range = sel && sel.rangeCount > 0 ? sel.getRangeAt(0) : null;
    const selectedText = sel ? sel.toString() : "";

    if (range && selectedText.length > 0) {
      savedRange = range.cloneRange();
      textSelection = { start: 0, end: selectedText.length, text: selectedText };
    } else {
      savedRange = null;
      textSelection = { start: 0, end: 0, text: "" };
    }

    colorPickerPosition = { x: e.clientX, y: e.clientY };
    showColorPicker = true;
    logger.userAction("Edit context menu opened", { hasSelection: selectedText.length > 0 });
  }

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
    const range = document.createRange();
    range.selectNodeContents(inlineEditTextarea);
    const sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(range);
    inlineEditTextarea.focus();
  }

  function applyColor(color) {
    if (!inlineEditTextarea || !savedRange || textSelection.text.length === 0) {
      closeColorPicker();
      return;
    }
    inlineEditTextarea.focus();
    const sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(savedRange);

    const coloredSpan = document.createElement('span');
    coloredSpan.style.color = hexToCSS(color.hex);
    coloredSpan.setAttribute('data-pacolor', color.hex);
    coloredSpan.appendChild(savedRange.extractContents());
    savedRange.insertNode(coloredSpan);

    logger.userAction("Applied color to text", { color: color.name, text: textSelection.text });
    closeColorPicker();

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

  function closeColorPicker() {
    showColorPicker = false;
    textSelection = { start: 0, end: 0, text: "" };
  }

  /** Apply TM suggestion to a row (called from parent's export wrapper) */
  export async function applyTMToRow(row, targetText, markRowAsTMApplied) {
    await startInlineEdit(row);
    if (inlineEditTextarea) {
      inlineEditTextarea.innerText = targetText;
      saveInlineEdit(false);
      if (markRowAsTMApplied) markRowAsTMApplied(row.id, 'fuzzy');
    }
  }

  export function getTextarea() { return inlineEditTextarea; }
  export function setTextarea(el) { inlineEditTextarea = el; }
  export function getIsCancelling() { return isCancellingEdit; }
</script>

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
        <span class="edit-menu-icon">&#9986;</span>
        <span>Cut</span>
        <span class="edit-menu-shortcut">Ctrl+X</span>
      </button>
      <button class="edit-menu-item" onclick={handleEditCopy} disabled={!textSelection.text}>
        <span class="edit-menu-icon">&#128203;</span>
        <span>Copy</span>
        <span class="edit-menu-shortcut">Ctrl+C</span>
      </button>
      <button class="edit-menu-item" onclick={handleEditPaste}>
        <span class="edit-menu-icon">&#128221;</span>
        <span>Paste</span>
        <span class="edit-menu-shortcut">Ctrl+V</span>
      </button>
      <div class="edit-menu-divider"></div>
      <button class="edit-menu-item" onclick={handleEditSelectAll}>
        <span class="edit-menu-icon">&#9745;</span>
        <span>Select All</span>
        <span class="edit-menu-shortcut">Ctrl+A</span>
      </button>
    </div>
  </div>
{/if}

<style>
  /* Color Picker/Edit Context Menu CSS */
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

  /* UI-113: Edit Context Menu */
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
</style>
