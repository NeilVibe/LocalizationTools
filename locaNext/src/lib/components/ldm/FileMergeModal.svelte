<script>
  /**
   * FileMergeModal — QuickTranslate-style merge with full match modes + options.
   *
   * Mirrors QuickTranslate's exact match types, transfer scope, and options:
   * - StringID Only (SCRIPT) — transfer all/untranslated, ALL categories on/off
   * - StringID + StrOrigin (STRICT) — perfect/fuzzy, non-script only, ignore spaces/punctuation
   * - StrOrigin Only — perfect/fuzzy, unique only, ignore spaces/punctuation
   * - StrOrigin + DescOrigin — perfect/fuzzy, ignore spaces/punctuation
   * - StrOrigin + FileName (2-pass) — perfect/fuzzy, ignore spaces/punctuation
   */
  import {
    Button,
    RadioButtonGroup,
    RadioButton,
    Toggle,
    Checkbox,
    Slider,
    InlineNotification,
    ProgressBar,
    Tag
  } from "carbon-components-svelte";
  import AppModal from '../common/AppModal.svelte';
  import { Merge, DocumentAdd, CheckmarkFilled, WarningAltFilled } from "carbon-icons-svelte";
  import { getApiBase, getAuthHeaders } from "$lib/utils/api.js";
  import { logger } from "$lib/utils/logger.js";

  let {
    open = $bindable(false),
    sourceFile = null,   // Right-clicked file = SOURCE (has corrections, already on server)
    onmerged = () => {},
  } = $props();

  const API_BASE = getApiBase();

  // === Match Types (exact QuickTranslate mirror) ===
  const MATCH_TYPES = [
    { value: 'stringid_only', label: 'StringID Only (SCRIPT)', desc: 'SCRIPT categories only — match by StringID' },
    { value: 'strict', label: 'StringID + StrOrigin (STRICT)', desc: 'Requires BOTH to match exactly' },
    { value: 'strorigin_only', label: 'StrOrigin Only', desc: 'Match by source text only — skips Dialog/Sequencer' },
    { value: 'strorigin_descorigin', label: 'StrOrigin + DescOrigin', desc: 'Requires BOTH StrOrigin AND DescOrigin to match' },
    { value: 'strorigin_filename', label: 'StrOrigin + FileName (2-pass)', desc: 'Match by StrOrigin + export filepath (precise)' },
  ];

  // === State ===
  let phase = $state('configure');
  let targetFile = $state(null);  // User picks TARGET via file picker (merge corrections INTO)

  // Match config (mirrors QuickTranslate)
  let matchType = $state('strict');
  let matchPrecision = $state('perfect');   // 'perfect' | 'fuzzy'
  let transferScope = $state('all');        // 'all' | 'untranslated'
  let fuzzyThreshold = $state(85);

  // Options
  let allCategories = $state(false);        // StringID Only: include ALL categories (not just SCRIPT)
  let nonScriptOnly = $state(false);        // Strict: exclude SCRIPT categories
  let ignoreSpaces = $state(false);
  let ignorePunctuation = $state(false);
  let uniqueOnly = $state(false);           // StrOrigin Only: skip duplicates

  // Progress
  let merging = $state(false);
  let mergeStep = $state('');
  let mergeLogs = $state([]);
  let uploadedFileId = $state(null);  // Track uploaded artifact for cleanup
  let result = $state(null);
  let error = $state('');

  // === Derived: which options to show per match type ===
  let showPrecision = $derived(['strict', 'strorigin_only', 'strorigin_descorigin', 'strorigin_filename'].includes(matchType));
  let showTransferScope = $derived(['stringid_only', 'strict', 'strorigin_only'].includes(matchType));
  let showAllCategories = $derived(matchType === 'stringid_only');
  let showNonScriptOnly = $derived(matchType === 'strict');
  let showUniqueOnly = $derived(matchType === 'strorigin_only');
  let showIgnoreOptions = $derived(['strict', 'strorigin_only', 'strorigin_descorigin', 'strorigin_filename'].includes(matchType));
  let showFuzzyThreshold = $derived(showPrecision && matchPrecision === 'fuzzy');

  // Reset on open
  $effect(() => {
    if (open) {
      phase = 'configure';
      targetFile = null;
      matchType = 'strict';
      matchPrecision = 'perfect';
      transferScope = 'all';
      fuzzyThreshold = 85;
      allCategories = false;
      nonScriptOnly = false;
      ignoreSpaces = false;
      ignorePunctuation = false;
      uniqueOnly = false;
      merging = false;
      mergeStep = '';
      mergeLogs = [];
      uploadedFileId = null;
      result = null;
      error = '';
    }
  });

  /** Pick target file via Electron file dialog or browser file input */
  async function pickTargetFile() {
    // Electron: use native file dialog to get path
    if (window.electronAPI?.showOpenDialog) {
      const result = await window.electronAPI.showOpenDialog({
        properties: ['openFile'],
        filters: [
          { name: 'Localization Files', extensions: ['xml', 'txt', 'tsv', 'xlsx'] }
        ]
      });
      if (result && !result.canceled && result.filePaths?.length > 0) {
        targetFile = { name: result.filePaths[0].split(/[\\/]/).pop(), path: result.filePaths[0] };
      }
    } else {
      // Browser fallback: use file input (gets File object, not path)
      const input = document.createElement('input');
      input.type = 'file';
      input.accept = '.xml,.txt,.tsv,.xlsx';
      input.onchange = (e) => {
        const files = e.target.files;
        if (files?.length > 0) targetFile = files[0];
      };
      input.click();
    }
  }

  async function executeMerge() {
    if (!sourceFile || !targetFile) return;
    phase = 'merging';
    merging = true;
    error = '';

    try {
      // Electron mode: merge directly to disk via path
      if (targetFile.path) {
        mergeStep = 'Merging corrections directly to file...';
        const mergeBody = {
          source_file_id: sourceFile.id,
          target_path: targetFile.path,
          match_mode: matchPrecision === 'fuzzy' ? 'fuzzy' : matchType,
          dry_run: false,
          only_untranslated: transferScope === 'untranslated',
          ignore_spaces: ignoreSpaces,
          ignore_punctuation: ignorePunctuation,
          all_categories: allCategories,
          non_script_only: nonScriptOnly,
          unique_only: uniqueOnly,
        };

        const mergeRes = await fetch(`${API_BASE}/api/ldm/merge/to-file`, {
          method: 'POST',
          headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
          body: JSON.stringify(mergeBody)
        });
        if (!mergeRes.ok) {
          const err = await mergeRes.json().catch(() => ({}));
          throw new Error(err.detail || 'Merge failed');
        }
        result = await mergeRes.json();
      } else {
        // Browser fallback: upload target, merge in DB, then offer download
        // (kept for DEV mode where we don't have filesystem access)
        mergeStep = 'Uploading target file...';
        const formData = new FormData();
        formData.append('file', targetFile);
        formData.append('storage', 'local');

        const uploadRes = await fetch(`${API_BASE}/api/ldm/files/upload`, {
          method: 'POST',
          headers: getAuthHeaders(),
          body: formData
        });
        if (!uploadRes.ok) {
          const err = await uploadRes.json().catch(() => ({}));
          throw new Error(err.detail || 'Upload failed');
        }
        const uploaded = await uploadRes.json();
        uploadedFileId = uploaded.id;

        mergeStep = 'Matching corrections...';
        mergeLogs = [];
        const mergeBody = {
          source_file_id: sourceFile.id,
          match_mode: matchPrecision === 'fuzzy' ? 'fuzzy' : matchType,
          threshold: fuzzyThreshold / 100,
          is_cjk: true,
          transfer_scope: transferScope,
          all_categories: allCategories,
          non_script_only: nonScriptOnly,
          ignore_spaces: ignoreSpaces,
          ignore_punctuation: ignorePunctuation,
          unique_only: uniqueOnly,
        };

        // BUG-14 fix: Use SSE streaming endpoint for live progress
        result = await new Promise((resolve, reject) => {
          fetch(`${API_BASE}/api/ldm/files/${uploaded.id}/merge-stream`, {
            method: 'POST',
            headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
            body: JSON.stringify(mergeBody)
          }).then(async (streamRes) => {
            if (!streamRes.ok) {
              // Fallback to non-streaming endpoint
              const mergeRes2 = await fetch(`${API_BASE}/api/ldm/files/${uploaded.id}/merge`, {
                method: 'POST',
                headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
                body: JSON.stringify(mergeBody)
              });
              if (!mergeRes2.ok) {
                const err = await mergeRes2.json().catch(() => ({}));
                reject(new Error(err.detail || 'Merge failed'));
                return;
              }
              resolve(await mergeRes2.json());
              return;
            }

            // Parse SSE stream
            const reader = streamRes.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
              const { done, value } = await reader.read();
              if (done) break;
              buffer += decoder.decode(value, { stream: true });

              // Process complete SSE events
              const lines = buffer.split('\n');
              buffer = lines.pop() || '';

              let eventType = '';
              for (const line of lines) {
                if (line.startsWith('event: ')) {
                  eventType = line.slice(7).trim();
                } else if (line.startsWith('data: ') && eventType) {
                  try {
                    const data = JSON.parse(line.slice(6));
                    if (eventType === 'progress') {
                      mergeStep = `${data.phase || 'Matching'}: ${data.matched || 0} matched, ${data.updated || 0} updated`;
                    } else if (eventType === 'log') {
                      mergeStep = data.message || '';
                      mergeLogs = [...mergeLogs, data.message];
                    } else if (eventType === 'complete') {
                      resolve(data);
                      return;
                    } else if (eventType === 'error') {
                      reject(new Error(data.message || 'Merge failed'));
                      return;
                    }
                  } catch (e) { /* ignore parse errors */ }
                  eventType = '';
                }
              }
            }
            // If stream ended without complete event
            reject(new Error('Merge stream ended unexpectedly'));
          }).catch(reject);
        });

        // Cleanup uploaded artifact
        if (uploadedFileId) {
          fetch(`${API_BASE}/api/ldm/files/${uploadedFileId}?permanent=true`, {
            method: 'DELETE', headers: getAuthHeaders()
          }).catch(() => {});
        }
      }

      phase = 'done';
      logger.success('Merge complete', result);
      onmerged();
    } catch (err) {
      error = err.message;
      phase = 'configure';
      if (uploadedFileId) {
        fetch(`${API_BASE}/api/ldm/files/${uploadedFileId}?permanent=true`, {
          method: 'DELETE', headers: getAuthHeaders()
        }).catch(() => {});
      }
    } finally {
      merging = false;
      uploadedFileId = null;
    }
  }
</script>

<AppModal
  bind:open
  modalHeading={phase === 'done' ? 'Merge Complete' : `Apply Corrections from ${sourceFile?.name || 'file'}`}
  primaryButtonText={phase === 'configure' ? 'Apply Corrections' : phase === 'done' ? 'Close' : ''}
  primaryButtonDisabled={phase === 'configure' && !targetFile}
  secondaryButtonText={phase === 'done' ? '' : 'Cancel'}
  onprimary={() => {
    if (phase === 'configure') executeMerge();
    else if (phase === 'done') open = false;
  }}
  onsecondary={() => open = false}
  size="md"
>
  {#if phase === 'configure'}
    <div class="merge-config">
      <!-- Source info (right-clicked file with corrections) -->
      <p class="target-info">
        Source (corrections): <strong>{sourceFile?.name}</strong>
        <Tag size="sm" type="teal">{sourceFile?.format || 'XML'}</Tag>
      </p>

      <!-- Target file picker (merge corrections INTO this file on disk) -->
      <div class="section">
        <h5>Target File (merge corrections into)</h5>
        {#if targetFile}
          <div class="selected-file">
            <DocumentAdd size={16} />
            <span>{targetFile.name}</span>
            {#if targetFile.path}
              <span class="file-path" title={targetFile.path}>{targetFile.path}</span>
            {/if}
            <button class="clear-btn" onclick={() => targetFile = null}>&times;</button>
          </div>
        {:else}
          <Button kind="tertiary" size="small" icon={DocumentAdd} onclick={pickTargetFile}>
            Select Target File...
          </Button>
          <p class="picker-hint">Corrections will be written directly into this file</p>
        {/if}
      </div>

      <!-- Match Type (radio buttons) -->
      <div class="section">
        <h5>Match Type</h5>
        <div class="match-types">
          {#each MATCH_TYPES as mt (mt.value)}
            <label class="match-type-option" class:active={matchType === mt.value}>
              <input type="radio" bind:group={matchType} value={mt.value} />
              <div class="match-type-content">
                <span class="match-type-label">{mt.label}</span>
                <span class="match-type-desc">{mt.desc}</span>
              </div>
            </label>
          {/each}
        </div>
      </div>

      <!-- Transfer Scope (Transfer ALL vs Only Untranslated) -->
      {#if showTransferScope}
        <div class="option-panel scope-panel">
          <h6>Transfer Scope</h6>
          <div class="radio-row">
            <label class:active={transferScope === 'all'}>
              <input type="radio" bind:group={transferScope} value="all" /> Transfer ALL (overwrite)
            </label>
            <label class:active={transferScope === 'untranslated'}>
              <input type="radio" bind:group={transferScope} value="untranslated" /> Only untranslated
            </label>
          </div>
        </div>
      {/if}

      <!-- StringID Only: ALL Categories toggle -->
      {#if showAllCategories}
        <div class="option-panel categories-panel">
          <Checkbox bind:checked={allCategories} labelText="ALL Categories (not just SCRIPT)" />
        </div>
      {/if}

      <!-- Match Precision (Perfect vs Fuzzy) -->
      {#if showPrecision}
        <div class="option-panel precision-panel">
          <h6>Match Precision</h6>
          <div class="radio-row">
            <label class:active={matchPrecision === 'perfect'}>
              <input type="radio" bind:group={matchPrecision} value="perfect" /> Perfect Match
            </label>
            <label class:active={matchPrecision === 'fuzzy'}>
              <input type="radio" bind:group={matchPrecision} value="fuzzy" /> Fuzzy Match (AI)
            </label>
          </div>
          {#if showFuzzyThreshold}
            <div class="fuzzy-threshold">
              <Slider labelText="Similarity Threshold" min={50} max={100} step={5} bind:value={fuzzyThreshold} />
            </div>
          {/if}
        </div>
      {/if}

      <!-- Non-Script Only (Strict mode) -->
      {#if showNonScriptOnly}
        <div class="option-panel nonscript-panel">
          <Checkbox bind:checked={nonScriptOnly} labelText="Non-Script only (exclude SCRIPT categories)" />
        </div>
      {/if}

      <!-- Unique Only (StrOrigin Only mode) -->
      {#if showUniqueOnly}
        <div class="option-panel unique-panel">
          <Checkbox bind:checked={uniqueOnly} labelText="Unique only (skip duplicate StrOrigin)" />
        </div>
      {/if}

      <!-- Ignore Spaces / Punctuation -->
      {#if showIgnoreOptions}
        <div class="option-panel ignore-panel">
          <Checkbox bind:checked={ignoreSpaces} labelText="Ignore Spaces" />
          <Checkbox bind:checked={ignorePunctuation} labelText="Ignore Punctuation" />
        </div>
      {/if}

      {#if error}
        <InlineNotification kind="error" title="Error" subtitle={error} hideCloseButton />
      {/if}
    </div>

  {:else if phase === 'merging'}
    <div class="merge-progress">
      <ProgressBar helperText={mergeStep || "Uploading and merging..."} />
      <p>Applying corrections from <strong>{sourceFile?.name}</strong> into <strong>{targetFile?.name}</strong></p>
      <p class="mode-label">Mode: {MATCH_TYPES.find(m => m.value === matchType)?.label} ({matchPrecision})</p>
      {#if mergeLogs.length > 0}
        <div class="merge-log">
          {#each mergeLogs as log}
            <div class="log-line">{log}</div>
          {/each}
        </div>
      {/if}
    </div>

  {:else if phase === 'done'}
    <div class="merge-result">
      <div class="result-header">
        {#if (result?.updated || 0) > 0}
          <CheckmarkFilled size={24} class="success-icon" />
          <h4>Merge Successful — {result.updated} rows changed</h4>
        {:else}
          <WarningAltFilled size={24} class="warning-icon" />
          <h4>No Changes — all {result?.matched || 0} matches were already identical</h4>
        {/if}
      </div>

      <div class="result-stats">
        <div class="stat"><span class="label">Matched</span><span class="value">{result?.matched || 0}</span></div>
        <div class="stat stat-updated"><span class="label">Updated</span><span class="value">{result?.updated || 0}</span></div>
        <div class="stat stat-unchanged"><span class="label">Unchanged</span><span class="value">{result?.unchanged || 0}</span></div>
        <div class="stat"><span class="label">Skipped</span><span class="value">{result?.skipped || 0}</span></div>
        <div class="stat"><span class="label">Total Rows</span><span class="value">{result?.total || 0}</span></div>
      </div>

      {#if result?.match_type_counts}
        <div class="match-types-result">
          <h5>Match Breakdown</h5>
          {#each Object.entries(result.match_type_counts).filter(([_, count]) => count > 0) as [type, count]}
            <div class="match-type-row">
              <span class="type-name">{type}</span>
              <Tag size="sm">{count}</Tag>
            </div>
          {/each}
        </div>
      {/if}

      {#if result?.by_category && Object.keys(result.by_category).length > 0}
        <div class="match-types-result">
          <h5>By Category</h5>
          {#each Object.entries(result.by_category).sort((a, b) => b[1].matched - a[1].matched) as [cat, stats]}
            <div class="match-type-row">
              <span class="type-name">{cat}</span>
              <span class="cat-stats">
                <Tag size="sm" type="green">{stats.updated} updated</Tag>
                {#if stats.unchanged > 0}<Tag size="sm" type="warm-gray">{stats.unchanged} unchanged</Tag>{/if}
              </span>
            </div>
          {/each}
        </div>
      {/if}

      {#if result?.not_found > 0}
        <div class="not-found-info">
          <WarningAltFilled size={16} />
          <span>{result.not_found.toLocaleString()} target rows had no matching correction</span>
        </div>
      {/if}
    </div>
  {/if}
</AppModal>

<style>
  .merge-config { display: flex; flex-direction: column; gap: 1rem; }
  .target-info { font-size: 0.875rem; color: var(--cds-text-02); display: flex; align-items: center; gap: 0.5rem; }
  .section h5 { margin: 0 0 0.5rem; font-size: 0.75rem; color: var(--cds-text-02); text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600; }
  .selected-file { display: flex; align-items: center; gap: 0.5rem; padding: 0.5rem 0.75rem; background: var(--cds-field-01); border: 1px solid var(--cds-border-subtle-01); border-radius: 4px; font-size: 0.875rem; }
  .clear-btn { background: none; border: none; cursor: pointer; color: var(--cds-text-02); font-size: 1.2rem; line-height: 1; padding: 0 0.25rem; }
  .clear-btn:hover { color: var(--cds-text-01); }
  .picker-hint { font-size: 0.7rem; color: var(--cds-text-03); margin-top: 0.25rem; }
  .file-path { font-size: 0.65rem; color: var(--cds-text-03); overflow: hidden; text-overflow: ellipsis; max-width: 300px; }

  /* Match type radio list */
  .match-types { display: flex; flex-direction: column; gap: 4px; }
  .match-type-option { display: flex; align-items: flex-start; gap: 0.5rem; padding: 0.5rem 0.75rem; background: var(--cds-field-01); border: 1px solid var(--cds-border-subtle-01); border-radius: 4px; cursor: pointer; transition: all 0.15s; }
  .match-type-option:hover { background: var(--cds-layer-hover-01); }
  .match-type-option.active { background: var(--cds-selected-ui); border-color: var(--cds-interactive-01); }
  .match-type-option input[type="radio"] { margin-top: 2px; accent-color: var(--cds-interactive-01); }
  .match-type-content { display: flex; flex-direction: column; }
  .match-type-label { font-size: 0.875rem; font-weight: 500; color: var(--cds-text-01); }
  .match-type-desc { font-size: 0.75rem; color: var(--cds-text-03); margin-top: 1px; }

  /* Option panels */
  .option-panel { padding: 0.75rem; background: var(--cds-field-01); border: 1px solid var(--cds-border-subtle-01); border-radius: 4px; }
  .option-panel h6 { margin: 0 0 0.5rem; font-size: 0.7rem; color: var(--cds-text-02); text-transform: uppercase; letter-spacing: 0.5px; }
  .scope-panel { background: #1a1a2e; }
  .precision-panel { background: #1a2e1a; }
  .categories-panel, .nonscript-panel, .unique-panel { background: #2e1a1a; }
  .ignore-panel { display: flex; gap: 1rem; background: #1a2e2e; }
  .radio-row { display: flex; gap: 1rem; }
  .radio-row label { display: flex; align-items: center; gap: 0.35rem; font-size: 0.85rem; cursor: pointer; padding: 0.25rem 0.5rem; border-radius: 3px; color: var(--cds-text-02); }
  .radio-row label.active { color: var(--cds-text-01); font-weight: 500; }
  .radio-row input[type="radio"] { accent-color: var(--cds-interactive-01); }
  .fuzzy-threshold { margin-top: 0.75rem; }

  /* Progress */
  .merge-progress { text-align: center; padding: 2rem 0; }
  .merge-progress p { margin-top: 0.75rem; color: var(--cds-text-02); font-size: 0.875rem; }
  .mode-label { font-size: 0.75rem; color: var(--cds-text-03); }

  /* Result */
  .merge-result { display: flex; flex-direction: column; gap: 1rem; }
  .result-header { display: flex; align-items: center; gap: 0.5rem; }
  .result-header :global(.success-icon) { color: var(--cds-support-02); }
  .result-header :global(.warning-icon) { color: var(--cds-support-03); }
  .result-stats { display: grid; grid-template-columns: repeat(5, 1fr); gap: 0.5rem; }
  .stat-updated .value { color: #42be65; }
  .stat-unchanged .value { color: #f1c21b; }
  .stat { text-align: center; padding: 0.75rem; background: var(--cds-field-01); border-radius: 4px; }
  .stat .label { display: block; font-size: 0.65rem; color: var(--cds-text-02); text-transform: uppercase; letter-spacing: 0.5px; }
  .stat .value { display: block; font-size: 1.25rem; font-weight: 600; margin-top: 0.25rem; color: var(--cds-text-01); }
  .match-types-result { padding: 0.75rem; background: var(--cds-field-01); border-radius: 4px; }
  .match-types-result h5 { margin: 0 0 0.5rem; font-size: 0.75rem; text-transform: uppercase; color: var(--cds-text-02); }
  .match-type-row { display: flex; justify-content: space-between; align-items: center; padding: 0.25rem 0; font-size: 0.85rem; }
  .type-name { color: var(--cds-text-01); }
  .cat-stats { display: flex; gap: 0.25rem; }
  .not-found-info { display: flex; align-items: center; gap: 0.5rem; padding: 0.5rem 0.75rem; background: var(--cds-field-01); border-radius: 4px; font-size: 0.8rem; color: var(--cds-text-02); }
  .not-found-info :global(svg) { color: var(--cds-support-03); flex-shrink: 0; }
  .merge-log { max-height: 120px; overflow-y: auto; margin-top: 0.75rem; padding: 0.5rem; background: #111; border-radius: 4px; font-family: monospace; font-size: 0.7rem; }
  .log-line { color: var(--cds-text-02); padding: 1px 0; }
</style>
