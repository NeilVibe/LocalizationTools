<script>
  /**
   * FileMergeModal — Right-click file merge with match mode selection.
   *
   * Flow: Select source file → Pick match mode → Upload → Merge → Show results.
   * Uses existing POST /api/ldm/files/upload + POST /api/ldm/files/{id}/merge APIs.
   */
  import {
    Modal,
    Button,
    RadioButtonGroup,
    RadioButton,
    Toggle,
    InlineNotification,
    ProgressBar,
    FileUploaderDropContainer
  } from "carbon-components-svelte";
  import { Merge, DocumentAdd, CheckmarkFilled } from "carbon-icons-svelte";
  import { getApiBase, getAuthHeaders } from "$lib/utils/api.js";
  import { logger } from "$lib/utils/logger.js";

  let {
    open = $bindable(false),
    targetFile = null,  // { id, name, format }
    onmerged = () => {},
  } = $props();

  const API_BASE = getApiBase();

  const MATCH_MODES = [
    { value: 'cascade', label: 'Cascade (Auto)', desc: 'Tries all modes: StringID → Strict → StrOrigin → Fuzzy' },
    { value: 'stringid_only', label: 'StringID Only', desc: 'Match by StringID (case-insensitive)' },
    { value: 'strict', label: 'StringID + StrOrigin', desc: 'Both must match (strict 2-key)' },
    { value: 'strorigin_only', label: 'StrOrigin Only', desc: 'Match by source text only' },
    { value: 'fuzzy', label: 'Fuzzy (Similarity)', desc: 'AI-powered similarity matching' },
  ];

  // State
  let phase = $state('configure');  // configure | merging | done
  let matchMode = $state('cascade');
  let threshold = $state(0.85);
  let sourceFile = $state(null);
  let merging = $state(false);
  let result = $state(null);
  let error = $state('');

  // Reset on open
  $effect(() => {
    if (open) {
      phase = 'configure';
      matchMode = 'cascade';
      sourceFile = null;
      merging = false;
      result = null;
      error = '';
    }
  });

  function handleFileSelect(e) {
    const files = e.detail;
    if (files && files.length > 0) {
      sourceFile = files[0];
    }
  }

  function handleFileDrop(e) {
    const files = e.detail;
    if (files && files.length > 0) {
      sourceFile = files[0];
    }
  }

  async function executeMerge() {
    if (!sourceFile || !targetFile) return;

    phase = 'merging';
    merging = true;
    error = '';

    try {
      // Step 1: Upload source file to get a file ID
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
      logger.info('Merge source uploaded', { id: uploaded.id, rows: uploaded.row_count });

      // Step 2: Merge source into target
      const mergeRes = await fetch(`${API_BASE}/api/ldm/files/${targetFile.id}/merge`, {
        method: 'POST',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_file_id: uploaded.id,
          match_mode: matchMode,
          threshold: threshold,
        })
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
      logger.error('Merge failed', { error: err.message });
    } finally {
      merging = false;
    }
  }
</script>

<Modal
  bind:open
  modalHeading={phase === 'done' ? 'Merge Complete' : `Merge into ${targetFile?.name || 'file'}`}
  primaryButtonText={phase === 'configure' ? 'Merge' : phase === 'done' ? 'Close' : ''}
  primaryButtonDisabled={phase === 'configure' && !sourceFile}
  secondaryButtonText={phase === 'done' ? '' : 'Cancel'}
  on:click:button--primary={() => {
    if (phase === 'configure') executeMerge();
    else if (phase === 'done') open = false;
  }}
  on:click:button--secondary={() => open = false}
  size="sm"
>
  {#if phase === 'configure'}
    <div class="merge-config">
      <p class="target-info">
        Target: <strong>{targetFile?.name}</strong> ({targetFile?.format})
      </p>

      <div class="section">
        <h5>Source File</h5>
        {#if sourceFile}
          <div class="selected-file">
            <DocumentAdd size={16} />
            <span>{sourceFile.name}</span>
            <button class="clear-btn" onclick={() => sourceFile = null}>x</button>
          </div>
        {:else}
          <FileUploaderDropContainer
            labelText="Drop file or click to browse"
            accept={['.xml', '.txt', '.tsv']}
            on:add={handleFileSelect}
          />
        {/if}
      </div>

      <div class="section">
        <h5>Match Mode</h5>
        <RadioButtonGroup bind:selected={matchMode} legendText="">
          {#each MATCH_MODES as mode (mode.value)}
            <RadioButton value={mode.value} labelText={mode.label} />
          {/each}
        </RadioButtonGroup>
        <p class="mode-desc">{MATCH_MODES.find(m => m.value === matchMode)?.desc}</p>
      </div>

      {#if matchMode === 'fuzzy'}
        <div class="section">
          <h5>Similarity Threshold: {threshold}</h5>
          <input type="range" min="0.5" max="1.0" step="0.05" bind:value={threshold} />
        </div>
      {/if}

      {#if error}
        <InlineNotification kind="error" title="Error" subtitle={error} />
      {/if}
    </div>

  {:else if phase === 'merging'}
    <div class="merge-progress">
      <ProgressBar helperText="Uploading and merging..." />
      <p>Merging {sourceFile?.name} into {targetFile?.name}...</p>
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
        <div class="match-types">
          <h5>Match Types</h5>
          {#each Object.entries(result.match_type_counts) as [type, count]}
            <div class="match-type"><span>{type}</span><span>{count}</span></div>
          {/each}
        </div>
      {/if}
    </div>
  {/if}
</Modal>

<style>
  .merge-config { display: flex; flex-direction: column; gap: 1.25rem; }
  .target-info { font-size: 0.875rem; color: var(--cds-text-02); }
  .section h5 { margin: 0 0 0.5rem; font-size: 0.8rem; color: var(--cds-text-02); text-transform: uppercase; letter-spacing: 0.5px; }
  .mode-desc { font-size: 0.75rem; color: var(--cds-text-03); margin-top: 0.25rem; }
  .selected-file { display: flex; align-items: center; gap: 0.5rem; padding: 0.5rem; background: var(--cds-field-01); border-radius: 4px; font-size: 0.875rem; }
  .clear-btn { background: none; border: none; cursor: pointer; color: var(--cds-text-02); font-size: 1rem; }
  .merge-progress { text-align: center; padding: 2rem 0; }
  .merge-progress p { margin-top: 1rem; color: var(--cds-text-02); }
  .merge-result { display: flex; flex-direction: column; gap: 1rem; }
  .result-header { display: flex; align-items: center; gap: 0.5rem; }
  .result-header :global(.success-icon) { color: var(--cds-support-02); }
  .result-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.5rem; }
  .stat { text-align: center; padding: 0.75rem; background: var(--cds-field-01); border-radius: 4px; }
  .stat .label { display: block; font-size: 0.7rem; color: var(--cds-text-02); text-transform: uppercase; }
  .stat .value { display: block; font-size: 1.25rem; font-weight: 600; margin-top: 0.25rem; }
  .match-types { padding: 0.75rem; background: var(--cds-field-01); border-radius: 4px; }
  .match-types h5 { margin: 0 0 0.5rem; }
  .match-type { display: flex; justify-content: space-between; padding: 0.25rem 0; font-size: 0.8rem; }
</style>
