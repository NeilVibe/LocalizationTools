<script>
  /**
   * EditOverlay.svelte -- Positioned-on-cell editor (Phase 106 v2 rewrite).
   *
   * Renders a textarea EXACTLY on top of the target cell.
   * Positioned OUTSIDE the virtual scroll each loop — never destroyed by scroll.
   * Visually identical to MemoQ: the cell appears to open for editing.
   *
   * Exports: startEdit, save, confirm, cancel, applyTMToRow, setDismissQADelegate
   */

  import { tick } from 'svelte';
  import { logger } from '$lib/utils/logger.js';
  import { getAuthHeaders, getApiBase } from '$lib/utils/api.js';
  import { lockRow, unlockRow, isRowLocked } from '$lib/stores/ldm.js';
  import { stripColorTags, hexToCSS } from '$lib/utils/colorParser.js';
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

  let API_BASE = $derived(getApiBase());

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
  // EDITING STATE (editRowId in grid state, editValue LOCAL)
  // ============================================================
  let editValue = $state("");
  let textareaEl = $state(null);
  let isCancellingEdit = $state(false);
  let isConfirming = $state(false);
  let isSaving = $state(false);
  let scrollOffset = $state(0);
  let heightDebounceTimer = null;

  // Color picker state
  let showColorPicker = $state(false);
  let colorPickerPosition = $state({ x: 0, y: 0 });
  let textSelection = $state({ start: 0, end: 0, text: "" });
  let dismissQAIssuesDelegate = $state(null);

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
  let activeRow = $derived(grid.editRowId ? getRowById(grid.editRowId) : null);

  // Target cell rect — measured from DOM on edit start and scroll
  let targetCellRect = $state({ top: 0, left: 0, width: 300, height: 36 });

  /** Measure the actual target cell position from the DOM */
  function measureTargetCell() {
    if (!grid.editRowId || !grid.containerEl) return;
    // Find the selected row's .cell.target element
    const row = grid.containerEl.querySelector('.virtual-row.selected .cell.target');
    if (row) {
      const containerRect = grid.containerEl.getBoundingClientRect();
      const cellRect = row.getBoundingClientRect();
      targetCellRect = {
        top: cellRect.top - containerRect.top + grid.containerEl.scrollTop,
        left: cellRect.left - containerRect.left,
        width: cellRect.width,
        height: cellRect.height,
      };
    }
  }

  /** Overlay positioned exactly on target cell */
  let overlayStyle = $derived.by(() => {
    if (!grid.editRowId) return 'display: none;';
    return `top: ${targetCellRect.top - scrollOffset}px; left: ${targetCellRect.left}px; width: ${targetCellRect.width}px; min-height: ${Math.max(targetCellRect.height, 36)}px;`;
  });

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
  // SCROLL OFFSET TRACKING
  // ============================================================
  $effect(() => {
    const container = grid.containerEl;
    if (!container || !grid.editRowId) return;
    function onScroll() { scrollOffset = container.scrollTop; }
    scrollOffset = container.scrollTop;
    container.addEventListener('scroll', onScroll);
    return () => container.removeEventListener('scroll', onScroll);
  });

  // ============================================================
  // AUTO-GROW TEXTAREA (debounced height update)
  // ============================================================
  $effect(() => {
    if (textareaEl && editValue !== undefined) {
      const prevH = textareaEl.offsetHeight;
      textareaEl.style.height = 'auto';
      const newH = textareaEl.scrollHeight;
      textareaEl.style.height = newH + 'px';
      if (Math.abs(newH - prevH) >= 1 && grid.editRowId) {
        clearTimeout(heightDebounceTimer);
        heightDebounceTimer = setTimeout(() => {
          const rowIndex = getRowIndexById(grid.editRowId);
          if (rowIndex !== undefined) {
            updateRowHeight(rowIndex, stripColorTags);
          }
        }, 200);
      }
    }
  });

  // ============================================================
  // TEXT FORMAT HELPERS
  // ============================================================
  function formatTextForDisplay(text) {
    if (!text) return "";
    return text.replace(/&lt;br\s*\/&gt;/gi, '\n').replace(/<br\s*\/?>/gi, '\n').replace(/\\n/g, '\n');
  }

  function formatTextForSave(text) {
    if (!text) return "";
    const isXML = fileName.toLowerCase().endsWith('.xml');
    const isExcel = fileName.toLowerCase().endsWith('.xlsx') || fileName.toLowerCase().endsWith('.xls');
    if (isXML) return text.replace(/\n/g, '<br/>');
    if (isExcel) return text.replace(/\n/g, '<br>');
    return text;
  }

  // ============================================================
  // API SAVE (optimistic)
  // ============================================================
  async function saveRowToAPI(row, textToSave, status) {
    const oldTarget = row.target;
    const oldStatus = row.status;
    updateRow(row.id, { target: textToSave, status });
    const rowIndex = getRowIndexById(row.id);
    if (rowIndex !== undefined) {
      clearTimeout(heightDebounceTimer);
      // Synchronous height update — must happen before edit closes
      updateRowHeight(rowIndex, stripColorTags);
    }

    try {
      const response = await fetch(`${API_BASE}/api/ldm/rows/${row.id}`, {
        method: 'PUT',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ target: textToSave, status })
      });
      if (!response.ok) {
        updateRow(row.id, { target: oldTarget, status: oldStatus });
        logger.error("API save failed -- reverted", { rowId: row.id, status: response.status });
        return false;
      }
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
      logger.error("API save network error -- reverted", { rowId: row.id, error: err.message });
      return false;
    }
  }

  async function endEditAndMoveNext(moveToNext) {
    if (fileId && !isLocalFile) {
      unlockRow(fileId, parseInt(grid.editRowId));
    }
    const currentRowId = grid.editRowId;
    grid.editRowId = null;
    editValue = "";
    clearTimeout(heightDebounceTimer);

    if (moveToNext) {
      const currentIndex = getRowIndexById(currentRowId);
      if (currentIndex !== undefined && getDisplayRows()[currentIndex + 1]) {
        const nextRow = getDisplayRows()[currentIndex + 1];
        if (nextRow && !nextRow.placeholder) {
          logger.info("GRID: auto-advance", { from: currentRowId, to: nextRow.id });
          grid.selectedRowId = nextRow.id;
          onRowSelect?.({ row: nextRow, isEditing: true });
          const container = grid.containerEl;
          if (container) {
            const nextIndex = currentIndex + 1;
            const nextTop = getRowTop(nextIndex);
            const nextHeight = getRowHeight(nextIndex);
            const viewTop = container.scrollTop;
            const viewBottom = viewTop + container.clientHeight;
            if (nextTop < viewTop || nextTop + nextHeight > viewBottom) {
              container.scrollTop = nextTop - 50;
            }
          }
          let rafCount = 0;
          const waitAndEdit = () => {
            rafCount++;
            if (rafCount >= 2) {
              startEdit(nextRow);
            } else {
              requestAnimationFrame(waitAndEdit);
            }
          };
          requestAnimationFrame(waitAndEdit);
        }
      }
    }
  }

  // ============================================================
  // CORE EDITING FUNCTIONS (exported)
  // ============================================================
  export async function startEdit(row) {
    if (!row) return;
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
    grid.editRowId = row.id;
    editValue = formatTextForDisplay(row.target || "");
    grid.selectedRowId = row.id;
    logger.info("EditOverlay: editing row", { rowId: row.id, rowNum: row.row_num });
    onInlineEditStart?.({ rowId: row.id, row, column: row.extra_data?.editing_attr || 'Name', value: row.target || row.source || '' });
    await tick();
    measureTargetCell();
    if (textareaEl) {
      textareaEl.focus();
      textareaEl.selectionStart = textareaEl.selectionEnd = editValue.length;
    }
  }

  export async function save(moveToNext = false) {
    if (!grid.editRowId || isCancellingEdit || isSaving) return;
    isSaving = true;
    const row = getRowById(grid.editRowId);
    if (!row) { isSaving = false; cancel(); return; }
    const textToSave = formatTextForSave(editValue);
    if (textToSave !== row.target) {
      try {
        const ok = await saveRowToAPI(row, textToSave, 'translated');
        if (ok) {
          logger.success("EditOverlay: saved row", { rowId: row.id, status: 'translated', moveToNext });
          onRowUpdate?.({ rowId: row.id });
        }
      } catch (err) {
        logger.error("Error saving edit", { error: err.message });
      }
    }
    await endEditAndMoveNext(moveToNext);
    isSaving = false;
  }

  export async function confirm() {
    if (!grid.editRowId || isConfirming || isSaving) return;
    isConfirming = true;
    isSaving = true;
    const row = getRowById(grid.editRowId);
    if (!row) { isConfirming = false; cancel(); return; }
    const textToSave = formatTextForSave(editValue);
    try {
      const ok = await saveRowToAPI(row, textToSave, 'reviewed');
      if (ok) {
        logger.success("EditOverlay: confirmed row", { rowId: row.id });
        onConfirmTranslation?.({ rowId: row.id, source: row.source, target: textToSave });
        onRowUpdate?.({ rowId: row.id });
      }
    } catch (err) {
      logger.error("Error confirming translation", { error: err.message });
    }
    await endEditAndMoveNext(false);
    setTimeout(() => { isConfirming = false; isSaving = false; }, 0);
  }

  export function cancel() {
    if (!grid.editRowId) return;
    const rowId = grid.editRowId;
    isCancellingEdit = true;
    if (fileId && !isLocalFile) unlockRow(fileId, parseInt(rowId));
    grid.editRowId = null;
    editValue = "";
    showColorPicker = false;
    clearTimeout(heightDebounceTimer);
    logger.info("EditOverlay: cancelled edit", { rowId });
    setTimeout(() => { isCancellingEdit = false; }, 0);
  }

  // ============================================================
  // STATUS SHORTCUTS
  // ============================================================
  async function markAsTranslated() {
    if (!grid.editRowId) return;
    const row = getRowById(grid.editRowId);
    if (!row) return;
    try {
      const textToSave = formatTextForSave(editValue);
      const ok = await saveRowToAPI(row, textToSave, 'translated');
      if (ok) logger.success("Marked as translated", { rowId: row.id });
    } catch (err) {
      logger.error("Failed to mark as translated", { error: err.message });
    }
    cancel();
  }

  async function revertRowStatus() {
    const targetRowId = grid.editRowId || grid.selectedRowId;
    if (!targetRowId) return;
    const row = getRowById(targetRowId);
    if (!row || row.status === 'untranslated') return;
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
      }
    } catch (err) {
      logger.error("Error reverting row status", { error: err.message });
    }
  }

  // ============================================================
  // KEYBOARD HANDLER
  // ============================================================
  function handleKeydown(e) {
    if (e.ctrlKey && e.key === 's') { e.preventDefault(); confirm(); return; }
    if (e.ctrlKey && e.key === 't') { e.preventDefault(); markAsTranslated(); return; }
    if (e.ctrlKey && e.key === 'd') { e.preventDefault(); dismissQAIssuesDelegate?.(); return; }
    if (e.ctrlKey && e.key === 'u') { e.preventDefault(); revertRowStatus(); return; }
    if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); cancel(); return; }
    if (e.key === 'Tab') { e.preventDefault(); e.stopPropagation(); save(true); return; }
  }

  // ============================================================
  // COLOR PICKER
  // ============================================================
  function applyColor(color) {
    if (!textareaEl || textSelection.text.length === 0) { closeColorPicker(); return; }
    const start = textareaEl.selectionStart;
    const end = textareaEl.selectionEnd;
    const before = editValue.substring(0, start);
    const selected = editValue.substring(start, end);
    const after = editValue.substring(end);
    editValue = `${before}<PAColor${color.hex}>${selected}</PAColor>${after}`;
    closeColorPicker();
    tick().then(() => {
      if (textareaEl) {
        textareaEl.focus();
        const newPos = before.length + `<PAColor${color.hex}>`.length + selected.length + '</PAColor>'.length;
        textareaEl.selectionStart = textareaEl.selectionEnd = newPos;
      }
    });
  }

  function handleContextMenu(e) {
    if (!textareaEl) return;
    e.preventDefault();
    textSelection = { start: textareaEl.selectionStart, end: textareaEl.selectionEnd, text: editValue.substring(textareaEl.selectionStart, textareaEl.selectionEnd) };
    colorPickerPosition = { x: e.clientX, y: e.clientY };
    showColorPicker = true;
  }

  function handleEditCut() {
    if (!textareaEl) return;
    const s = textareaEl.selectionStart, e = textareaEl.selectionEnd;
    const sel = editValue.substring(s, e);
    if (sel && navigator.clipboard) { navigator.clipboard.writeText(sel); editValue = editValue.substring(0, s) + editValue.substring(e); }
    closeColorPicker(); textareaEl.focus();
  }

  function handleEditCopy() {
    if (!textareaEl) return;
    const sel = editValue.substring(textareaEl.selectionStart, textareaEl.selectionEnd);
    if (sel && navigator.clipboard) navigator.clipboard.writeText(sel);
    closeColorPicker(); textareaEl.focus();
  }

  async function handleEditPaste() {
    if (!textareaEl) return;
    try {
      const clip = await navigator.clipboard.readText();
      const s = textareaEl.selectionStart, e = textareaEl.selectionEnd;
      editValue = editValue.substring(0, s) + clip + editValue.substring(e);
      await tick();
      if (textareaEl) { textareaEl.selectionStart = textareaEl.selectionEnd = s + clip.length; }
    } catch (_) { textareaEl.focus(); }
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
  export async function applyTMToRow(row, targetText, markRowAsTMApplied) {
    await startEdit(row);
    editValue = formatTextForDisplay(targetText);
    await save(false);
    if (markRowAsTMApplied) markRowAsTMApplied(row.id, 'fuzzy');
  }

  export function setDismissQADelegate(fn) { dismissQAIssuesDelegate = fn; }

  export async function openEditByRowId(rowId) {
    const row = getRowById(rowId);
    if (row) await startEdit(row);
    else logger.warning("Row not loaded yet", { rowId });
  }

  export function getEditRowId() { return grid.editRowId; }
  export function getIsCancelling() { return isCancellingEdit; }
</script>

<!-- Positioned-on-cell textarea (outside virtual scroll loop) -->
{#if grid.editRowId && activeRow}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="cell-editor-overlay" style={overlayStyle} onkeydown={handleKeydown}>
    <textarea
      bind:this={textareaEl}
      bind:value={editValue}
      class="cell-editor-textarea"
      placeholder="Enter translation..."
      spellcheck="true"
      oncontextmenu={handleContextMenu}
    ></textarea>
  </div>
{/if}

<!-- Color picker context menu -->
{#if showColorPicker}
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="color-picker-overlay" onclick={closeColorPicker}></div>
  <div class="edit-context-menu" style="left: {colorPickerPosition.x}px; top: {colorPickerPosition.y}px;">
    {#if sourceColors.length > 0 && textSelection.text.length > 0}
      <div class="edit-menu-section">
        <div class="edit-menu-header">Apply Color</div>
        <div class="color-picker-colors">
          {#each sourceColors as color (color.name)}
            <button class="color-swatch" style="background-color: {color.css};" title={color.name} onclick={() => applyColor(color)}>
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
      <div class="edit-menu-section"><div class="edit-menu-hint">No colors in source text</div></div>
      <div class="edit-menu-divider"></div>
    {/if}
    <div class="edit-menu-section">
      <button class="edit-menu-item" onclick={handleEditCut} disabled={!textSelection.text}><span class="edit-menu-icon">&#9986;</span><span>Cut</span><span class="edit-menu-shortcut">Ctrl+X</span></button>
      <button class="edit-menu-item" onclick={handleEditCopy} disabled={!textSelection.text}><span class="edit-menu-icon">&#128203;</span><span>Copy</span><span class="edit-menu-shortcut">Ctrl+C</span></button>
      <button class="edit-menu-item" onclick={handleEditPaste}><span class="edit-menu-icon">&#128221;</span><span>Paste</span><span class="edit-menu-shortcut">Ctrl+V</span></button>
      <div class="edit-menu-divider"></div>
      <button class="edit-menu-item" onclick={handleEditSelectAll}><span class="edit-menu-icon">&#9745;</span><span>Select All</span><span class="edit-menu-shortcut">Ctrl+A</span></button>
    </div>
  </div>
{/if}

<style>
  .cell-editor-overlay {
    position: absolute;
    z-index: 100;
  }

  .cell-editor-textarea {
    width: 100%;
    min-height: 36px;
    padding: 6px 8px;
    font-family: var(--grid-font-family, 'IBM Plex Sans', sans-serif);
    font-size: var(--grid-font-size, 0.8rem);
    line-height: 1.5;
    color: var(--cds-text-01, #f4f4f4);
    background: var(--cds-field-01, #262626);
    border: 2px solid var(--cds-focus, #0f62fe);
    border-radius: 0;
    resize: none;
    overflow-y: auto;
    white-space: pre-wrap;
    word-wrap: break-word;
    box-shadow: 0 0 0 1px var(--cds-focus, #0f62fe), 0 4px 12px rgba(0, 0, 0, 0.3);
  }

  .cell-editor-textarea:focus { outline: none; border-color: var(--cds-focus, #0f62fe); }
  .cell-editor-textarea::placeholder { color: var(--cds-text-03, #6f6f6f); }

  .color-picker-overlay { position: fixed; inset: 0; z-index: 999; }
  .edit-context-menu { position: fixed; z-index: 1000; min-width: 220px; background: var(--cds-layer-02, #353535); border: 1px solid var(--cds-border-strong-01, #6f6f6f); border-radius: 4px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3); overflow: hidden; }
  .color-picker-colors { display: grid; grid-template-columns: repeat(4, 1fr); gap: 4px; padding: 0.5rem; }
  .color-swatch { width: 100%; aspect-ratio: 1; border: 2px solid transparent; border-radius: 4px; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all 0.15s ease; }
  .color-swatch:hover { transform: scale(1.1); border-color: var(--cds-border-strong-01, #6f6f6f); }
  .color-swatch .color-name { font-size: 0.5rem; color: #000; text-shadow: 0 0 2px #fff, 0 0 2px #fff; font-weight: 600; }
  .color-picker-preview { padding: 0.5rem 0.75rem; background: var(--cds-layer-01, #262626); border-top: 1px solid var(--cds-border-subtle-01, #525252); font-size: 0.7rem; color: var(--cds-text-02, #c6c6c6); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .color-picker-preview .preview-text { font-style: italic; }
  .color-picker-preview .preview-label { margin-right: 0.25rem; }
  .edit-menu-section { padding: 0.25rem 0; }
  .edit-menu-header { padding: 0.5rem 0.75rem 0.25rem; font-size: 0.7rem; font-weight: 600; color: var(--cds-text-02, #c6c6c6); text-transform: uppercase; letter-spacing: 0.5px; }
  .edit-menu-hint { padding: 0.5rem 0.75rem; font-size: 0.7rem; color: var(--cds-text-03, #6f6f6f); font-style: italic; }
  .edit-menu-divider { height: 1px; background: var(--cds-border-subtle-01, #525252); margin: 0.25rem 0; }
  .edit-menu-item { display: flex; align-items: center; width: 100%; padding: 0.5rem 0.75rem; background: none; border: none; color: var(--cds-text-01, #f4f4f4); font-size: 0.8rem; cursor: pointer; text-align: left; gap: 0.5rem; }
  .edit-menu-item:hover:not(:disabled) { background: var(--cds-layer-hover-02, #474747); }
  .edit-menu-item:disabled { color: var(--cds-text-03, #6f6f6f); cursor: not-allowed; }
  .edit-menu-icon { width: 1rem; text-align: center; font-size: 0.9rem; }
  .edit-menu-item span:nth-child(2) { flex: 1; }
  .edit-menu-shortcut { font-size: 0.65rem; color: var(--cds-text-03, #6f6f6f); }
</style>
