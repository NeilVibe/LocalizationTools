<script>
  import {
    Modal,
    TextInput,
    Toggle,
    RadioButtonGroup,
    RadioButton,
    Button,
  } from "carbon-components-svelte";
  import { onDestroy } from "svelte";
  import { logger } from "$lib/utils/logger.js";
  import { getAuthHeaders, getApiBase } from "$lib/utils/api.js";
  import { stripColorTags } from "$lib/utils/colorParser.js";
  import {
    getDisplayRows,
    updateRow,
    updateRowHeight,
    getRowIndexById,
  } from "./grid/gridState.svelte.ts";

  const API_BASE = getApiBase();

  let {
    open = $bindable(false),
    fileId = null,
  } = $props();

  // Search inputs
  let findText = $state("");
  let replaceText = $state("");

  // Toggle options
  let useRegex = $state(false);
  let caseSensitive = $state(false);
  let wholeWord = $state(false);

  // Scope
  let scope = $state("target");

  // Matches
  let matches = $state([]);
  let currentMatchIndex = $state(0);
  let replacing = $state(false);

  const MAX_PREVIEW = 50;

  /**
   * Build a regex from the find text + options.
   * Returns null if findText is empty or regex is invalid.
   */
  function buildPattern() {
    if (!findText) return null;
    try {
      let pattern = findText;
      if (!useRegex) {
        pattern = pattern.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      }
      if (wholeWord) {
        pattern = `\\b${pattern}\\b`;
      }
      const flags = caseSensitive ? "g" : "gi";
      return new RegExp(pattern, flags);
    } catch (err) {
      logger.warning("Invalid regex pattern", { pattern: findText, error: err.message });
      return null;
    }
  }

  /**
   * Find all matches in displayRows based on current options.
   */
  function runSearch() {
    const regex = buildPattern();
    if (!regex) {
      matches = [];
      currentMatchIndex = 0;
      return;
    }

    /** @type {Array<{rowId: string, rowNum: number, field: string, original: string, replaced: string, row: any}>} */
    const found = [];

    for (const row of getDisplayRows()) {
      if (!row || row.placeholder) continue;

      const fields = scope === "both"
        ? ["target", "source"]
        : scope === "source"
          ? ["source"]
          : ["target"];

      for (const field of fields) {
        const text = row[field] || "";
        const clean = stripColorTags(text);
        regex.lastIndex = 0;
        if (regex.test(clean)) {
          regex.lastIndex = 0;
          const replaced = clean.replace(regex, replaceText);
          found.push({
            rowId: String(row.id),
            rowNum: row.row_num ?? 0,
            field,
            original: clean,
            replaced,
            row,
          });
        }
      }
      if (found.length >= MAX_PREVIEW) break;
    }

    matches = found;
    currentMatchIndex = 0;
    logger.info("Find & Replace search", { pattern: findText, matchCount: found.length, scope });
  }

  /**
   * Replace a single match.
   * @param {number} idx - index in matches array
   * @param {'translated'|'reviewed'} status
   */
  async function replaceSingle(idx, status) {
    const match = matches[idx];
    if (!match || replacing) return;

    if (match.field !== 'target') {
      logger.warning("Find & Replace: source field is read-only, skipping single replace");
      return;
    }

    replacing = true;
    try {
      const newTarget = match.replaced;

      // Optimistic UI update
      updateRow(match.rowId, { [match.field]: newTarget, status });
      const rowIndex = getRowIndexById(match.rowId);
      if (rowIndex !== undefined) {
        requestAnimationFrame(() => updateRowHeight(rowIndex, stripColorTags));
      }

      // API call
      const response = await fetch(`${API_BASE}/api/ldm/rows/${match.rowId}`, {
        method: "PUT",
        headers: { ...getAuthHeaders(), "Content-Type": "application/json" },
        body: JSON.stringify({ target: newTarget, status }),
      });

      if (!response.ok) {
        // Revert on failure
        updateRow(match.rowId, { [match.field]: match.original, status: match.row.status });
        logger.error("Find & Replace single save failed", { rowId: match.rowId, status: response.status });
        return;
      }

      logger.userAction("Find & Replace single", { rowId: match.rowId, field: match.field, status });

      // Remove from matches list and advance
      matches = matches.filter((_, i) => i !== idx);
      if (currentMatchIndex >= matches.length && matches.length > 0) {
        currentMatchIndex = matches.length - 1;
      }
    } finally {
      replacing = false;
    }
  }

  /**
   * Replace ALL matches.
   * @param {'translated'|'reviewed'} status
   */
  async function replaceAll(status) {
    if (matches.length === 0 || replacing) return;

    // We need ALL matches, not just first 50 preview — re-scan fully
    const regex = buildPattern();
    if (!regex) return;

    replacing = true;
    try {
      /** @type {Array<{row_id: number, target: string, status: string}>} */
      const updates = [];
      /** @type {Array<{rowId: string, original: string, oldStatus: string}>} */
      const rollbackInfo = [];

      for (const row of getDisplayRows()) {
        if (!row || row.placeholder) continue;

        const fields = scope === "both"
          ? ["target", "source"]
          : scope === "source"
            ? ["source"]
            : ["target"];

        for (const field of fields) {
          if (field !== "target") continue; // API only updates target
          const text = row[field] || "";
          const clean = stripColorTags(text);
          regex.lastIndex = 0;
          if (regex.test(clean)) {
            regex.lastIndex = 0;
            const replaced = clean.replace(regex, replaceText);
            const rowId = String(row.id);

            rollbackInfo.push({ rowId, original: text, oldStatus: row.status });

            // Optimistic update
            updateRow(rowId, { target: replaced, status });
            const rowIndex = getRowIndexById(rowId);
            if (rowIndex !== undefined) {
              updateRowHeight(rowIndex, stripColorTags);
            }

            updates.push({
              row_id: Number(row.id),
              target: replaced,
              status,
            });
          }
        }
      }

      if (updates.length === 0) {
        replacing = false;
        return;
      }

      logger.info("Find & Replace All — sending batch", { count: updates.length, status });

      const response = await fetch(`${API_BASE}/api/ldm/files/${fileId}/rows/batch-update`, {
        method: "PUT",
        headers: { ...getAuthHeaders(), "Content-Type": "application/json" },
        body: JSON.stringify({ updates }),
      });

      if (!response.ok) {
        // Revert all
        for (const rb of rollbackInfo) {
          updateRow(rb.rowId, { target: rb.original, status: rb.oldStatus });
        }
        logger.error("Find & Replace All batch failed", { status: response.status });
      } else {
        const result = await response.json();
        logger.userAction("Find & Replace All complete", { updated: result.updated, total: result.total, status });
        matches = [];
        currentMatchIndex = 0;
      }
    } finally {
      replacing = false;
    }
  }

  // Debounced search on input changes
  let searchTimer = null;
  function scheduleSearch() {
    if (searchTimer) clearTimeout(searchTimer);
    searchTimer = setTimeout(runSearch, 250);
  }

  onDestroy(() => { if (searchTimer) clearTimeout(searchTimer); });

  /**
   * Truncate text for preview display.
   * @param {string} text
   * @param {number} max
   */
  function truncate(text, max = 80) {
    if (!text) return "";
    return text.length > max ? text.substring(0, max) + "..." : text;
  }
</script>

<Modal
  bind:open
  modalHeading="Find & Replace"
  passiveModal
  size="lg"
  hasScrollingContent
>
  <div class="find-replace-container">
    <!-- Inputs -->
    <div class="input-row">
      <TextInput
        bind:value={findText}
        labelText="Find"
        placeholder="Search text or regex..."
        oninput={scheduleSearch}
      />
    </div>
    <div class="input-row">
      <TextInput
        bind:value={replaceText}
        labelText="Replace with"
        placeholder="Replacement text..."
        oninput={scheduleSearch}
      />
    </div>

    <!-- Options row -->
    <div class="options-row">
      <Toggle
        bind:toggled={useRegex}
        labelText="Regex"
        labelA="Off"
        labelB="On"
        size="sm"
        ontoggle={runSearch}
      />
      <Toggle
        bind:toggled={caseSensitive}
        labelText="Case sensitive"
        labelA="Off"
        labelB="On"
        size="sm"
        ontoggle={runSearch}
      />
      <Toggle
        bind:toggled={wholeWord}
        labelText="Whole word"
        labelA="Off"
        labelB="On"
        size="sm"
        ontoggle={runSearch}
      />
    </div>

    <!-- Scope -->
    <div class="scope-row">
      <RadioButtonGroup
        legendText="Scope"
        bind:selected={scope}
        onchange={runSearch}
      >
        <RadioButton labelText="Target only" value="target" />
        <RadioButton labelText="Source only" value="source" />
        <RadioButton labelText="Both" value="both" />
      </RadioButtonGroup>
    </div>

    <!-- Action buttons -->
    <div class="action-row">
      <Button
        kind="primary"
        size="small"
        disabled={matches.length === 0 || replacing}
        onclick={() => replaceSingle(currentMatchIndex, 'translated')}
      >
        Replace &rarr; Change
      </Button>
      <Button
        kind="secondary"
        size="small"
        disabled={matches.length === 0 || replacing}
        onclick={() => replaceSingle(currentMatchIndex, 'reviewed')}
      >
        Replace &rarr; Confirm
      </Button>
      <Button
        kind="danger"
        size="small"
        disabled={matches.length === 0 || replacing}
        onclick={() => replaceAll('translated')}
      >
        Change All ({matches.length})
      </Button>
      <Button
        kind="danger--tertiary"
        size="small"
        disabled={matches.length === 0 || replacing}
        onclick={() => replaceAll('reviewed')}
      >
        Confirm All ({matches.length})
      </Button>
    </div>

    <!-- Match list -->
    <div class="match-list-header">
      <span class="match-count">
        {#if findText}
          {matches.length >= MAX_PREVIEW ? `${MAX_PREVIEW}+ matches` : `${matches.length} match${matches.length !== 1 ? 'es' : ''}`}
        {:else}
          Type to search
        {/if}
      </span>
    </div>

    <div class="match-list" role="list">
      {#each matches as match, i (match.rowId + match.field)}
        <button
          class="match-item"
          class:active={i === currentMatchIndex}
          onclick={() => { currentMatchIndex = i; }}
          type="button"
        >
          <span class="match-row-num">#{match.rowNum}</span>
          <span class="match-field-tag">{match.field}</span>
          <div class="match-texts">
            <span class="match-original">{truncate(match.original)}</span>
            <span class="match-arrow">&rarr;</span>
            <span class="match-replaced">{truncate(match.replaced)}</span>
          </div>
        </button>
      {/each}
      {#if findText && matches.length === 0}
        <div class="no-matches">No matches found</div>
      {/if}
    </div>
  </div>
</Modal>

<style>
  .find-replace-container {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    padding: 0.5rem 0;
  }

  .input-row {
    width: 100%;
  }

  .options-row {
    display: flex;
    gap: 1.5rem;
    align-items: flex-end;
    flex-wrap: wrap;
  }

  .scope-row {
    margin: 0.25rem 0;
  }

  .action-row {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
    padding: 0.5rem 0;
    border-top: 1px solid var(--cds-border-subtle-01);
    border-bottom: 1px solid var(--cds-border-subtle-01);
  }

  .match-list-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .match-count {
    font-size: 0.75rem;
    color: var(--cds-text-02);
    font-weight: 500;
  }

  .match-list {
    max-height: 280px;
    overflow-y: auto;
    border: 1px solid var(--cds-border-subtle-01);
    border-radius: 4px;
    background: var(--cds-field-01);
  }

  .match-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    width: 100%;
    padding: 0.4rem 0.6rem;
    border: none;
    border-bottom: 1px solid var(--cds-border-subtle-01);
    background: transparent;
    cursor: pointer;
    text-align: left;
    color: var(--cds-text-01);
    font-size: 0.75rem;
    font-family: inherit;
  }

  .match-item:hover {
    background: var(--cds-layer-hover-01);
  }

  .match-item.active {
    background: var(--cds-layer-selected-01);
    outline: 2px solid var(--cds-focus);
    outline-offset: -2px;
  }

  .match-item:last-child {
    border-bottom: none;
  }

  .match-row-num {
    font-weight: 600;
    color: var(--cds-text-02);
    min-width: 3rem;
    font-family: var(--cds-code-01);
  }

  .match-field-tag {
    font-size: 0.65rem;
    padding: 0.1rem 0.35rem;
    border-radius: 3px;
    background: var(--cds-tag-background-blue);
    color: var(--cds-tag-color-blue);
    text-transform: uppercase;
    font-weight: 500;
    min-width: 3.5rem;
    text-align: center;
  }

  .match-texts {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    flex: 1;
    min-width: 0;
    overflow: hidden;
  }

  .match-original {
    color: var(--cds-text-error, #fa4d56);
    text-decoration: line-through;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 40%;
  }

  .match-arrow {
    color: var(--cds-text-02);
    flex-shrink: 0;
  }

  .match-replaced {
    color: var(--cds-support-success, #42be65);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 40%;
  }

  .no-matches {
    padding: 1rem;
    text-align: center;
    color: var(--cds-text-03);
    font-size: 0.8rem;
  }
</style>
