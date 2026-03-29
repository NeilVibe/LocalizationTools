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
    FileUploaderDropContainer,
    Tag
  } from "carbon-components-svelte";
  import { Merge, DocumentAdd, CheckmarkFilled, WarningAltFilled } from "carbon-icons-svelte";
  import { getApiBase, getAuthHeaders } from "$lib/utils/api.js";
  import { logger } from "$lib/utils/logger.js";
  import AppModal from '../common/AppModal.svelte';

  let {
    open = $bindable(false),
    targetFile = null,
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
  let sourceFile = $state(null);

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
      sourceFile = null;
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
      result = null;
      error = '';
    }
  });

  function handleFileAdd(e) {
    const files = e.detail;
    if (files?.length > 0) sourceFile = files[0];
  }

  async function executeMerge() {
    if (!sourceFile || !targetFile) return;
    phase = 'merging';
    merging = true;
    error = '';

    try {
      // Step 1: Upload source file
      const formData = new FormData();
      formData.append('file', sourceFile);
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

      // Step 2: Build merge request matching QuickTranslate params
      const mergeBody = {
        source_file_id: uploaded.id,
        match_mode: matchPrecision === 'fuzzy' ? 'fuzzy' : matchType,
        threshold: fuzzyThreshold / 100,
        is_cjk: true,
        // Extended options (backend must support these — passed as extra fields)
        transfer_scope: transferScope,
        all_categories: allCategories,
        non_script_only: nonScriptOnly,
        ignore_spaces: ignoreSpaces,
        ignore_punctuation: ignorePunctuation,
        unique_only: uniqueOnly,
      };

      const mergeRes = await fetch(`${API_BASE}/api/ldm/files/${targetFile.id}/merge`, {
        method: 'POST',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify(mergeBody)
      });
      if (!mergeRes.ok) {
        const err = await mergeRes.json().catch(() => ({}));
        throw new Error(err.detail || 'Merge failed');
      }

      result = await mergeRes.json();
      phase = 'done';
      logger.success('Merge complete', result);
      onmerged();
    } catch (err) {
      error = err.message;
      phase = 'configure';
    } finally {
      merging = false;
    }
  }
</script>

<AppModal
  bind:open
  modalHeading={phase === 'done' ? 'Merge Complete' : `Merge into ${targetFile?.name || 'file'}`}
  primaryButtonText={phase === 'configure' ? 'Merge' : phase === 'done' ? 'Close' : ''}
  primaryButtonDisabled={phase === 'configure' && !sourceFile}
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
      <!-- Target info -->
      <p class="target-info">
        Target: <strong>{targetFile?.name}</strong>
        <Tag size="sm" type="blue">{targetFile?.format || 'XML'}</Tag>
      </p>

      <!-- Source file picker -->
      <div class="section">
        <h5>Source File</h5>
        {#if sourceFile}
          <div class="selected-file">
            <DocumentAdd size={16} />
            <span>{sourceFile.name}</span>
            <button class="clear-btn" onclick={() => sourceFile = null}>&times;</button>
          </div>
        {:else}
          <FileUploaderDropContainer
            labelText="Drop file or click to browse"
            accept={['.xml', '.txt', '.tsv', '.xlsx']}
            on:add={handleFileAdd}
          />
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
      <ProgressBar helperText="Uploading and merging..." />
      <p>Merging <strong>{sourceFile?.name}</strong> into <strong>{targetFile?.name}</strong></p>
      <p class="mode-label">Mode: {MATCH_TYPES.find(m => m.value === matchType)?.label} ({matchPrecision})</p>
    </div>

  {:else if phase === 'done'}
    <div class="merge-result">
      <div class="result-header">
        <CheckmarkFilled size={24} class="success-icon" />
        <h4>Merge Successful</h4>
      </div>

      <div class="result-stats">
        <div class="stat"><span class="label">Matched</span><span class="value">{result?.matched || 0}</span></div>
        <div class="stat"><span class="label">Updated</span><span class="value">{result?.rows_updated || 0}</span></div>
        <div class="stat"><span class="label">Skipped</span><span class="value">{result?.skipped || 0}</span></div>
        <div class="stat"><span class="label">Total</span><span class="value">{result?.total || 0}</span></div>
      </div>

      {#if result?.match_type_counts}
        <div class="match-types-result">
          <h5>Match Breakdown</h5>
          {#each Object.entries(result.match_type_counts) as [type, count]}
            <div class="match-type-row">
              <span class="type-name">{type}</span>
              <Tag size="sm">{count}</Tag>
            </div>
          {/each}
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
  .result-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.5rem; }
  .stat { text-align: center; padding: 0.75rem; background: var(--cds-field-01); border-radius: 4px; }
  .stat .label { display: block; font-size: 0.65rem; color: var(--cds-text-02); text-transform: uppercase; letter-spacing: 0.5px; }
  .stat .value { display: block; font-size: 1.25rem; font-weight: 600; margin-top: 0.25rem; color: var(--cds-text-01); }
  .match-types-result { padding: 0.75rem; background: var(--cds-field-01); border-radius: 4px; }
  .match-types-result h5 { margin: 0 0 0.5rem; font-size: 0.75rem; text-transform: uppercase; color: var(--cds-text-02); }
  .match-type-row { display: flex; justify-content: space-between; align-items: center; padding: 0.25rem 0; font-size: 0.85rem; }
  .type-name { color: var(--cds-text-01); }
</style>
