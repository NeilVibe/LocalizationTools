<script>
  /**
   * EditOverlay.svelte -- Floating edit panel with native <textarea>.
   *
   * Option B v2 redesign: replaces InlineEditor.svelte.
   * NO contenteditable, NO document.execCommand.
   * Enter = linebreak (native). Color markup typed as raw PAColor tags.
   *
   * Exports: startEdit, save, confirm, cancel, applyTMToRow, setDismissQADelegate
   */

  import { tick } from 'svelte';
  import { logger } from '$lib/utils/logger.js';
  import { getAuthHeaders, getApiBase } from '$lib/utils/api.js';
  import { lockRow, unlockRow, isRowLocked } from '$lib/stores/ldm.js';
  import { stripColorTags, hexToCSS } from '$lib/utils/colorParser.js';
  import TagText from '../TagText.svelte';
  import {
    grid,
    getRowById,
    getRowIndexById,
    getDisplayRows,
    updateRow,
    updateRowHeight,
    getRowTop,
    getRowHeight,
  } from '../grid/gridState.svelte.ts';

  // API base URL
  let API_BASE = $derived(getApiBase());

  // Props
  let {
    fileId = null,
    fileName = "",
    fileType = "translator",
    isLocalFile = false,
    onInlineEditStart = undefined,
    onRowUpdate = undefined,
    onRowSelect = undefined,
    onConfirmTranslation = undefined,
  } = $props();

  // ============================================================
  // EDITING STATE
  // ============================================================
  let editRowId = $state(null);
  let editValue = $state("");
  let textareaEl = $state(null);
  let isCancellingEdit = $state(false);
  let isConfirming = $state(false);
  let isSaving = $state(false);
  let scrollOffset = $state(0);

  // Color picker state
  let showColorPicker = $state(false);
  let colorPickerPosition = $state({ x: 0, y: 0 });
  let textSelection = $state({ start: 0, end: 0, text: "" });

  // Dismiss QA delegate (set by parent)
  let dismissQAIssuesDelegate = $state(null);

  // Default PAColor swatches
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

  // ============================================================
  // DERIVED STATE
  // ============================================================

  /** Active row being edited */
  let activeRow = $derived(editRowId ? getRowById(editRowId) : null);

  /** Overlay position: absolute, anchored below the selected row */
  let overlayTop = $derived.by(() => {
    if (!editRowId) return 0;
    const rowIndex = getRowIndexById(editRowId);
    if (rowIndex === undefined) return 0;
    return getRowTop(rowIndex) + getRowHeight(rowIndex) - scrollOffset;
  });

  /** Extract unique colors from source text for the color picker */
  let sourceColors = $derived.by(() => {
    if (!activeRow?.source) return [];
    const colorPattern = /<PAColor(0x[0-9a-fA-F]{6,8})>/gi;
    const uniqueColors = new Map();
    let match;
    while ((match = colorPattern.exec(activeRow.source)) !== null) {
      const hex = match[1].toLowerCase();
      if (!uniqueColors.has(hex)) {
        const css = hexToCSS(hex);
        const known = PAColors.find(c => c.hex.toLowerCase() === hex);
        uniqueColors.set(hex, { hex, css, name: known?.name || css });
      }
    }
    return Array.from(uniqueColors.values());
  });

  // ============================================================
  // SCROLL OFFSET TRACKING (reactive repositioning)
  // ============================================================
  $effect(() => {
    const container = grid.containerEl;
    if (!container || !editRowId) return;
    function onScroll() { scrollOffset = container.scrollTop; }
    scrollOffset = container.scrollTop;
    container.addEventListener('scroll', onScroll);
    return () => container.removeEventListener('scroll', onScroll);
  });

  // ============================================================
  // AUTO-GROW TEXTAREA
  // ============================================================
  $effect(() => {
    if (textareaEl && editValue !== undefined) {
      textareaEl.style.height = 'auto';
      textareaEl.style.height = textareaEl.scrollHeight + 'px';
    }
  });

  // ============================================================
  // TEXT FORMAT HELPERS
  // ============================================================

  /** Convert file-format linebreaks to actual newlines for textarea display */
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
      return text.replace(/\n/g, '<br/>');
    } else if (isExcel) {
      return text.replace(/\n/g, '<br>');
    } else {
      return text;
    }
  }

  // ============================================================
  // API SAVE (optimistic)
  // ============================================================

  /** Save row to API with optimistic update. Reverts on failure. */
  async function saveRowToAPI(row, textToSave, status) {
    const oldTarget = row.target;
    const oldStatus = row.status;

    // Optimistic — update instantly
    updateRow(row.id, { target: textToSave, status });
    const rowIndex = getRowIndexById(row.id);
    if (rowIndex !== undefined) {
      const oldHeight = getRowHeight(rowIndex);
      requestAnimationFrame(() => {
        updateRowHeight(rowIndex, stripColorTags);
        const newHeight = getRowHeight(rowIndex);
        if (Math.abs(newHeight - oldHeight) >= 1) {
          logger.info("EditOverlay: height updated for row", { rowIndex, oldHeight, newHeight });
        }
      });
    }

    try {
      const response = await fetch(`${API_BASE}/api/ldm/rows/${row.id}`, {
        method: 'PUT',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ target: textToSave, status })
      });
      if (!response.ok) {
        updateRow(row.id, { target: oldTarget, status: oldStatus });
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
      updateRow(row.id, { target: oldTarget, status: oldStatus });
      logger.error("API save network error — reverted", { rowId: row.id, error: err.message });
      return false;
    }
  }

  /** End editing, release lock, clear state, optionally move to next row */
  async function endEditAndMoveNext(moveToNext) {
    if (fileId && !isLocalFile) {
      unlockRow(fileId, parseInt(editRowId));
    }
    const currentRowId = editRowId;
    editRowId = null;
    editValue = "";
    if (moveToNext) {
      const currentIndex = getRowIndexById(currentRowId);
      if (currentIndex !== undefined && getDisplayRows()[currentIndex + 1]) {
        const nextRow = getDisplayRows()[currentIndex + 1];
        if (nextRow && !nextRow.placeholder) {
          grid.selectedRowId = nextRow.id;
          onRowSelect?.({ row: nextRow, isEditing: true });
          await startEdit(nextRow);
        }
      }
    }
  }

  // ============================================================
  // CORE EDITING FUNCTIONS (exported)
  // ============================================================

  /** Start editing a row */
  export async function startEdit(row) {
    if (!row) return;

    // Lock check (skip for orphaned/local files)
    if (!isLocalFile) {
      const lock = isRowLocked(parseInt(row.id));
      if (lock && lock.locked_by) {
        logger.warning("Row locked by another user", { rowId: row.id, lockedBy: lock.locked_by });
        return;
      }
      if (fileId) {
        const granted = await lockRow(fileId, parseInt(row.id));
        if (!granted) {
          logger.warning("Could not acquire lock for edit", { rowId: row.id });
          return;
        }
      }
    }

    editRowId = row.id;
    editValue = formatTextForDisplay(row.target || "");
    grid.selectedRowId = row.id;

    logger.info("EditOverlay: editing row", { rowId: row.id, rowNum: row.row_num });

    onInlineEditStart?.({
      rowId: row.id,
      row,
      column: row.extra_data?.editing_attr || 'Name',
      value: row.target || row.source || ''
    });

    await tick();
    if (textareaEl) {
      textareaEl.focus();
      // Place cursor at end
      textareaEl.selectionStart = textareaEl.selectionEnd = editValue.length;
    }
  }

  /** Save edit and optionally move to next row */
  export async function save(moveToNext = false) {
    if (!editRowId || isCancellingEdit || isSaving) return;
    isSaving = true;

    const row = getRowById(editRowId);
    if (!row) { isSaving = false; cancel(); return; }

    const textToSave = formatTextForSave(editValue);
    if (textToSave !== row.target) {
      try {
        const ok = await saveRowToAPI(row, textToSave, 'translated');
        if (ok) {
          logger.success("EditOverlay: saved row", { rowId: row.id, status: 'translated', moveToNext });
          onRowUpdate?.({ rowId: row.id });
        } else {
          logger.error("Failed to save edit");
        }
      } catch (err) {
        logger.error("Error saving edit", { error: err.message });
      }
    }

    await endEditAndMoveNext(moveToNext);
    isSaving = false;
  }

  /** Confirm translation: save as 'reviewed' + move next */
  export async function confirm() {
    if (!editRowId || isConfirming || isSaving) return;
    isConfirming = true;
    isSaving = true;

    const row = getRowById(editRowId);
    if (!row) { isConfirming = false; cancel(); return; }

    const textToSave = formatTextForSave(editValue);
    try {
      const ok = await saveRowToAPI(row, textToSave, 'reviewed');
      if (ok) {
        logger.success("EditOverlay: confirmed row", { rowId: row.id });
        onConfirmTranslation?.({ rowId: row.id, source: row.source, target: textToSave });
        onRowUpdate?.({ rowId: row.id });
      } else {
        logger.error("Failed to confirm translation");
      }
    } catch (err) {
      logger.error("Error confirming translation", { error: err.message });
    }

    await endEditAndMoveNext(true);
    setTimeout(() => { isConfirming = false; isSaving = false; }, 0);
  }

  /** Cancel edit without saving */
  export function cancel() {
    if (!editRowId) return;
    const rowId = editRowId;
    isCancellingEdit = true;

    if (fileId && !isLocalFile) {
      unlockRow(fileId, parseInt(rowId));
    }

    editRowId = null;
    editValue = "";
    showColorPicker = false;
    logger.info("EditOverlay: cancelled edit", { rowId });

    setTimeout(() => { isCancellingEdit = false; }, 0);
  }

  // ============================================================
  // STATUS CHANGE SHORTCUTS
  // ============================================================

  /** Ctrl+T: Mark as translated (needs review) */
  async function markAsTranslated() {
    if (!editRowId) return;
    const row = getRowById(editRowId);
    if (!row) return;

    try {
      const textToSave = formatTextForSave(editValue);
      const ok = await saveRowToAPI(row, textToSave, 'translated');
      if (ok) logger.success("Marked as translated (needs review)", { rowId: row.id });
    } catch (err) {
      logger.error("Failed to mark as translated", { error: err.message });
    }
    cancel();
  }

  /** Ctrl+U: Revert row status to untranslated */
  async function revertRowStatus() {
    const targetRowId = editRowId || grid.selectedRowId;
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
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'untranslated' })
      });
      if (response.ok) {
        updateRow(row.id, { status: 'untranslated' });
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
  // KEYBOARD HANDLER
  // ============================================================

  function handleKeydown(e) {
    if (e.ctrlKey && e.key === 's') {
      e.preventDefault();
      confirm();
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
    if (e.key === 'Escape') {
      e.preventDefault();
      e.stopPropagation();
      cancel();
      return;
    }
    if (e.key === 'Tab') {
      e.preventDefault();
      e.stopPropagation();
      save(true);
      return;
    }
    // Enter = native linebreak in textarea — NO special handling
  }

  // ============================================================
  // COLOR PICKER (right-click context menu)
  // ============================================================

  /** Apply color as raw PAColor tag markup in textarea */
  function applyColor(color) {
    if (!textareaEl || textSelection.text.length === 0) {
      closeColorPicker();
      return;
    }

    const start = textareaEl.selectionStart;
    const end = textareaEl.selectionEnd;
    const before = editValue.substring(0, start);
    const selected = editValue.substring(start, end);
    const after = editValue.substring(end);

    // Insert raw PAColor tags into the textarea text
    editValue = `${before}<PAColor${color.hex}>${selected}</PAColor>${after}`;

    logger.userAction("Applied color to text", { color: color.name, text: selected });
    closeColorPicker();

    tick().then(() => {
      if (textareaEl) {
        textareaEl.focus();
        const newCursorPos = before.length + `<PAColor${color.hex}>`.length + selected.length + '</PAColor>'.length;
        textareaEl.selectionStart = textareaEl.selectionEnd = newCursorPos;
      }
    });
  }

  function handleContextMenu(e) {
    if (!textareaEl) return;
    e.preventDefault();

    const start = textareaEl.selectionStart;
    const end = textareaEl.selectionEnd;
    const selectedText = editValue.substring(start, end);

    textSelection = { start, end, text: selectedText };
    colorPickerPosition = { x: e.clientX, y: e.clientY };
    showColorPicker = true;
    logger.userAction("Edit context menu opened", { hasSelection: selectedText.length > 0 });
  }

  function handleEditCut() {
    if (!textareaEl) return;
    // Use clipboard API for textarea
    const start = textareaEl.selectionStart;
    const end = textareaEl.selectionEnd;
    const selected = editValue.substring(start, end);
    if (selected && navigator.clipboard) {
      navigator.clipboard.writeText(selected);
      editValue = editValue.substring(0, start) + editValue.substring(end);
    }
    closeColorPicker();
    textareaEl.focus();
  }

  function handleEditCopy() {
    if (!textareaEl) return;
    const start = textareaEl.selectionStart;
    const end = textareaEl.selectionEnd;
    const selected = editValue.substring(start, end);
    if (selected && navigator.clipboard) {
      navigator.clipboard.writeText(selected);
    }
    closeColorPicker();
    textareaEl.focus();
  }

  async function handleEditPaste() {
    if (!textareaEl) return;
    try {
      const clipText = await navigator.clipboard.readText();
      const start = textareaEl.selectionStart;
      const end = textareaEl.selectionEnd;
      editValue = editValue.substring(0, start) + clipText + editValue.substring(end);
      await tick();
      if (textareaEl) {
        const newPos = start + clipText.length;
        textareaEl.selectionStart = textareaEl.selectionEnd = newPos;
      }
    } catch (err) {
      // Fallback: let native paste work
      textareaEl.focus();
    }
    closeColorPicker();
  }

  function handleEditSelectAll() {
    if (!textareaEl) return;
    closeColorPicker();
    textareaEl.selectionStart = 0;
    textareaEl.selectionEnd = editValue.length;
    textareaEl.focus();
  }

  function closeColorPicker() {
    showColorPicker = false;
    textSelection = { start: 0, end: 0, text: "" };
  }

  // ============================================================
  // TM APPLICATION (exported)
  // ============================================================

  /** Apply TM suggestion to a row */
  export async function applyTMToRow(row, targetText, markRowAsTMApplied) {
    await startEdit(row);
    editValue = formatTextForDisplay(targetText);
    await save(false);
    if (markRowAsTMApplied) markRowAsTMApplied(row.id, 'fuzzy');
  }

  /** Set the Ctrl+D dismiss QA delegate */
  export function setDismissQADelegate(fn) {
    dismissQAIssuesDelegate = fn;
  }

  /** Navigate to row and start editing */
  export async function openEditByRowId(rowId) {
    const row = getRowById(rowId);
    if (row) {
      await startEdit(row);
    } else {
      logger.warning("Row not loaded yet", { rowId });
    }
  }

  /** Check if currently editing */
  export function getEditRowId() { return editRowId; }
  export function getIsCancelling() { return isCancellingEdit; }
</script>

<!-- ============================================================ -->
<!-- EDIT OVERLAY (floating panel below selected row) -->
<!-- ============================================================ -->
{#if editRowId && activeRow}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div
    class="edit-overlay"
    style="top: {overlayTop}px;"
    onkeydown={handleKeydown}
  >
    <!-- Source (read-only) -->
    <div class="overlay-source">
      <span class="field-label">Source</span>
      <div class="source-display"><TagText text={activeRow.source || ''} /></div>
    </div>

    <!-- Target (editable textarea) -->
    <div class="overlay-target">
      <span class="field-label">Target</span>
      <textarea
        bind:this={textareaEl}
        bind:value={editValue}
        class="edit-textarea"
        placeholder="Enter translation..."
        spellcheck="true"
        oncontextmenu={handleContextMenu}
      ></textarea>
    </div>

    <!-- Footer with hotkeys + status -->
    <div class="overlay-footer">
      <span class="hotkey"><kbd>Enter</kbd> Linebreak</span>
      <span class="hotkey"><kbd>Tab</kbd> Save+Next</span>
      <span class="hotkey"><kbd>Ctrl+S</kbd> Confirm</span>
      <span class="hotkey"><kbd>Ctrl+T</kbd> Translated</span>
      <span class="hotkey"><kbd>Esc</kbd> Cancel</span>
      <span class="status-label">{activeRow.status || 'new'}</span>
    </div>
  </div>
{/if}

<!-- ============================================================ -->
<!-- COLOR PICKER / CONTEXT MENU -->
<!-- ============================================================ -->
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
  /* ============================================================ */
  /* EDIT OVERLAY */
  /* ============================================================ */
  .edit-overlay {
    position: absolute;
    left: 0;
    right: 0;
    z-index: 100;
    background: var(--cds-layer-02, #353535);
    border: 1px solid var(--cds-border-strong-01, #6f6f6f);
    border-radius: 4px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4), 0 2px 6px rgba(0, 0, 0, 0.2);
    padding: 0.75rem;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .field-label {
    display: block;
    font-size: 0.65rem;
    font-weight: 600;
    color: var(--cds-text-02, #c6c6c6);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 0.25rem;
  }

  .overlay-source {
    padding-bottom: 0.5rem;
    border-bottom: 1px solid var(--cds-border-subtle-01, #525252);
  }

  .source-display {
    font-size: 0.85rem;
    color: var(--cds-text-01, #f4f4f4);
    white-space: pre-wrap;
    word-wrap: break-word;
    line-height: 1.5;
    max-height: 200px;
    overflow-y: auto;
  }

  .overlay-target {
    display: flex;
    flex-direction: column;
  }

  .edit-textarea {
    width: 100%;
    min-height: 60px;
    max-height: 400px;
    padding: 0.5rem;
    font-family: inherit;
    font-size: 0.85rem;
    line-height: 1.5;
    color: var(--cds-text-01, #f4f4f4);
    background: var(--cds-field-01, #262626);
    border: 1px solid var(--cds-border-strong-01, #6f6f6f);
    border-radius: 2px;
    resize: none;
    overflow-y: auto;
    white-space: pre-wrap;
    word-wrap: break-word;
  }

  .edit-textarea:focus {
    outline: 2px solid var(--cds-focus, #0f62fe);
    outline-offset: -2px;
    border-color: transparent;
  }

  .edit-textarea::placeholder {
    color: var(--cds-text-03, #6f6f6f);
  }

  .overlay-footer {
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem;
    align-items: center;
    padding-top: 0.375rem;
    border-top: 1px solid var(--cds-border-subtle-01, #525252);
  }

  .hotkey {
    font-size: 0.7rem;
    color: var(--cds-text-02, #c6c6c6);
  }

  .hotkey kbd {
    display: inline-block;
    padding: 0.1rem 0.3rem;
    font-size: 0.6rem;
    font-family: monospace;
    background: var(--cds-field-01, #262626);
    border: 1px solid var(--cds-border-subtle-01, #525252);
    border-radius: 2px;
    color: var(--cds-text-01, #f4f4f4);
    margin-right: 0.15rem;
  }

  .status-label {
    margin-left: auto;
    font-size: 0.7rem;
    font-weight: 600;
    color: var(--cds-text-02, #c6c6c6);
    text-transform: capitalize;
  }

  /* ============================================================ */
  /* COLOR PICKER / CONTEXT MENU */
  /* ============================================================ */
  .color-picker-overlay {
    position: fixed;
    inset: 0;
    z-index: 999;
  }

  .edit-context-menu {
    position: fixed;
    z-index: 1000;
    min-width: 220px;
    background: var(--cds-layer-02, #353535);
    border: 1px solid var(--cds-border-strong-01, #6f6f6f);
    border-radius: 4px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    overflow: hidden;
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
    border-color: var(--cds-border-strong-01, #6f6f6f);
  }

  .color-swatch .color-name {
    font-size: 0.5rem;
    color: #000;
    text-shadow: 0 0 2px #fff, 0 0 2px #fff;
    font-weight: 600;
  }

  .color-picker-preview {
    padding: 0.5rem 0.75rem;
    background: var(--cds-layer-01, #262626);
    border-top: 1px solid var(--cds-border-subtle-01, #525252);
    font-size: 0.7rem;
    color: var(--cds-text-02, #c6c6c6);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .color-picker-preview .preview-text {
    font-style: italic;
  }

  .color-picker-preview .preview-label {
    color: var(--cds-text-02, #c6c6c6);
    margin-right: 0.25rem;
  }

  .edit-menu-section {
    padding: 0.25rem 0;
  }

  .edit-menu-header {
    padding: 0.5rem 0.75rem 0.25rem;
    font-size: 0.7rem;
    font-weight: 600;
    color: var(--cds-text-02, #c6c6c6);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .edit-menu-hint {
    padding: 0.5rem 0.75rem;
    font-size: 0.7rem;
    color: var(--cds-text-03, #6f6f6f);
    font-style: italic;
  }

  .edit-menu-divider {
    height: 1px;
    background: var(--cds-border-subtle-01, #525252);
    margin: 0.25rem 0;
  }

  .edit-menu-item {
    display: flex;
    align-items: center;
    width: 100%;
    padding: 0.5rem 0.75rem;
    background: none;
    border: none;
    color: var(--cds-text-01, #f4f4f4);
    font-size: 0.8rem;
    cursor: pointer;
    text-align: left;
    gap: 0.5rem;
  }

  .edit-menu-item:hover:not(:disabled) {
    background: var(--cds-layer-hover-02, #474747);
  }

  .edit-menu-item:disabled {
    color: var(--cds-text-03, #6f6f6f);
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
    color: var(--cds-text-03, #6f6f6f);
  }
</style>
