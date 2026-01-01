<script>
  import {
    Modal,
    Select,
    SelectItem,
    Slider,
    Checkbox,
    RadioButtonGroup,
    RadioButton,
    ProgressBar,
    InlineNotification,
    InlineLoading,
    Tag
  } from "carbon-components-svelte";
  import {
    Flash,
    Renew,
    CheckmarkFilled,
    WarningAlt,
    Document
  } from "carbon-icons-svelte";
  import { createEventDispatcher, onMount } from "svelte";
  import { logger } from "$lib/utils/logger.js";
  import { preferences } from "$lib/stores/preferences.js";
  import { getAuthHeaders, getApiBase } from "$lib/utils/api.js";

  const dispatch = createEventDispatcher();

  // API base URL
  const API_BASE = getApiBase();

  // Svelte 5: Props
  let {
    open = $bindable(false),
    file = null // {id, name, row_count, format}
  } = $props();

  // Svelte 5: State - Form
  let selectedTmId = $state(null);
  let engine = $state("standard");
  let threshold = $state(92);
  let skipExisting = $state(true);

  // Svelte 5: State - TM List
  let tmList = $state([]);
  let tmLoading = $state(false);

  // Svelte 5: State - Pretranslation
  let status = $state(""); // '' | 'running' | 'success' | 'error'
  let progress = $state(0);
  let errorMessage = $state("");
  let result = $state(null);

  // Load TM list
  async function loadTMs() {
    tmLoading = true;
    try {
      const response = await fetch(`${API_BASE}/api/ldm/tm`, {
        headers: getAuthHeaders()
      });
      if (response.ok) {
        tmList = await response.json();
        // Select active TM by default
        const activeTmId = $preferences.activeTmId;
        if (activeTmId && tmList.some(tm => tm.id === activeTmId)) {
          selectedTmId = activeTmId;
        } else if (tmList.length > 0) {
          // Select first ready TM
          const readyTm = tmList.find(tm => tm.status === 'ready');
          if (readyTm) selectedTmId = readyTm.id;
        }
        logger.info("Loaded TMs for pretranslate", { count: tmList.length });
      }
    } catch (err) {
      logger.error("Failed to load TMs", { error: err.message });
    } finally {
      tmLoading = false;
    }
  }

  // Run pretranslation
  async function runPretranslation() {
    if (!file || !selectedTmId) {
      errorMessage = "Please select a Translation Memory";
      return;
    }

    status = "running";
    progress = 10;
    errorMessage = "";
    result = null;

    // Simulate progress while running
    const progressInterval = setInterval(() => {
      if (progress < 90) {
        progress += 5;
      }
    }, 500);

    try {
      const response = await fetch(`${API_BASE}/api/ldm/pretranslate`, {
        method: 'POST',
        headers: {
          ...getAuthHeaders(),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          file_id: file.id,
          engine: engine,
          dictionary_id: selectedTmId,
          threshold: threshold / 100,
          skip_existing: skipExisting
        })
      });

      clearInterval(progressInterval);
      progress = 100;

      if (response.ok) {
        result = await response.json();
        status = "success";
        logger.success("Pretranslation complete", {
          matched: result.matched,
          total: result.total,
          time: result.time_seconds
        });

        // Dispatch event after delay
        setTimeout(() => {
          dispatch('completed', result);
          resetAndClose();
        }, 2000);

      } else {
        const error = await response.json();
        errorMessage = error.detail || "Pretranslation failed";
        status = "error";
        logger.error("Pretranslation failed", { error: errorMessage });
      }

    } catch (err) {
      clearInterval(progressInterval);
      errorMessage = err.message;
      status = "error";
      logger.error("Pretranslation error", { error: err.message });
    }
  }

  // Reset and close
  function resetAndClose() {
    status = "";
    progress = 0;
    errorMessage = "";
    result = null;
    open = false;
    dispatch('close');
  }

  // Handle close
  function handleClose() {
    if (status !== "running") {
      resetAndClose();
    }
  }

  // Get engine description (user-friendly, no technical details)
  function getEngineDescription(eng) {
    switch (eng) {
      case "standard":
        return "Best for general text matching";
      case "xls_transfer":
        return "Best for files with formatting codes";
      case "kr_similar":
        return "Best for Korean language content";
      default:
        return "";
    }
  }

  // Format count
  function formatCount(count) {
    if (count >= 1000000) return `${(count / 1000000).toFixed(1)}M`;
    if (count >= 1000) return `${(count / 1000).toFixed(1)}K`;
    return count?.toString() || "0";
  }

  // Initialize threshold from preferences
  $effect(() => {
    if (open) {
      threshold = Math.round($preferences.tmThreshold * 100);
      loadTMs();
    }
  });
</script>

<Modal
  bind:open
  modalHeading="Pretranslate File"
  primaryButtonText={status === "running" ? "Running..." : "Pretranslate"}
  primaryButtonDisabled={status === "running" || status === "success" || !selectedTmId}
  secondaryButtonText="Cancel"
  on:click:button--primary={runPretranslation}
  on:click:button--secondary={handleClose}
  on:close={handleClose}
>
  <div class="pretranslate-form">
    {#if status === "running"}
      <!-- Running State -->
      <div class="progress-container">
        <Flash size={32} class="running-icon" />
        <h4>Pretranslating...</h4>
        <ProgressBar
          value={progress}
          max={100}
          labelText="Processing rows..."
          helperText="{progress}% complete"
        />
        <p class="progress-note">
          This may take a moment for large files.
        </p>
      </div>

    {:else if status === "success" && result}
      <!-- Success State -->
      <div class="success-container">
        <CheckmarkFilled size={48} class="success-icon" />
        <h4>Pretranslation Complete!</h4>
        <div class="result-stats">
          <div class="stat">
            <span class="stat-value">{result.matched.toLocaleString()}</span>
            <span class="stat-label">Matched</span>
          </div>
          <div class="stat">
            <span class="stat-value">{result.skipped.toLocaleString()}</span>
            <span class="stat-label">Skipped</span>
          </div>
          <div class="stat">
            <span class="stat-value">{result.total.toLocaleString()}</span>
            <span class="stat-label">Total</span>
          </div>
        </div>
        <p class="time-note">
          Completed in {result.time_seconds.toFixed(1)}s at {Math.round(result.threshold * 100)}% threshold
        </p>
      </div>

    {:else if status === "error"}
      <!-- Error State -->
      <InlineNotification
        kind="error"
        title="Error"
        subtitle={errorMessage}
        on:close={() => { status = ""; errorMessage = ""; }}
      />
      <!-- Show form again after error -->
      <div class="form-fields">
        {@render formContent()}
      </div>

    {:else}
      <!-- Initial Form State -->
      <div class="form-fields">
        {@render formContent()}
      </div>
    {/if}
  </div>
</Modal>

{#snippet formContent()}
  <!-- File Info -->
  <div class="file-info">
    <Document size={20} />
    <div class="file-details">
      <span class="file-name">{file?.name || "No file selected"}</span>
      <span class="file-meta">{formatCount(file?.row_count)} rows • {file?.format?.toUpperCase()}</span>
    </div>
  </div>

  <!-- TM Selection -->
  <div class="form-section">
    {#if tmLoading}
      <InlineLoading description="Loading Translation Memories..." />
    {:else}
      <Select
        bind:selected={selectedTmId}
        labelText="Translation Memory"
        helperText="Select TM to use for matching"
      >
        <SelectItem value={null} text="-- Select TM --" disabled />
        {#each tmList as tm}
          {#if tm.status === 'ready'}
            <SelectItem
              value={tm.id}
              text="{tm.name} ({formatCount(tm.entry_count)} entries)"
            />
          {:else}
            <SelectItem
              value={tm.id}
              text="{tm.name} (Not Ready)"
              disabled
            />
          {/if}
        {/each}
      </Select>
      {#if tmList.length === 0}
        <p class="no-tms-hint">No Translation Memories available. Upload one first.</p>
      {/if}
    {/if}
  </div>

  <!-- Engine Selection -->
  <div class="form-section">
    <RadioButtonGroup
      legendText="Pretranslation Engine"
      bind:selected={engine}
    >
      <RadioButton
        labelText="Standard TM (Recommended)"
        value="standard"
      />
      <RadioButton
        labelText="XLS Transfer"
        value="xls_transfer"
      />
      <RadioButton
        labelText="KR Similar"
        value="kr_similar"
      />
    </RadioButtonGroup>
    <p class="engine-description">{getEngineDescription(engine)}</p>
  </div>

  <!-- Threshold Slider -->
  <div class="form-section">
    <div class="threshold-header">
      <span class="threshold-label">Match Threshold</span>
      <Tag type="blue" size="sm">{threshold}%</Tag>
    </div>
    <Slider
      min={50}
      max={100}
      bind:value={threshold}
      step={1}
      hideTextInput={true}
    />
    <p class="threshold-hint">
      {#if threshold >= 90}
        High precision: Only very close matches
      {:else if threshold >= 70}
        Balanced: Good matches with some flexibility
      {:else}
        Fuzzy: More matches, review recommended
      {/if}
    </p>
  </div>

  <!-- Options -->
  <div class="form-section options-section">
    <Checkbox
      bind:checked={skipExisting}
      labelText="Skip rows with existing translations"
    />
  </div>
{/snippet}

<style>
  .pretranslate-form {
    min-height: 280px;
  }

  .form-fields {
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
  }

  .file-info {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.875rem 1rem;
    background: var(--cds-layer-02);
    border-radius: 4px;
    border-left: 3px solid var(--cds-interactive-01);
  }

  .file-details {
    display: flex;
    flex-direction: column;
    gap: 0.125rem;
  }

  .file-name {
    font-weight: 500;
    color: var(--cds-text-01);
  }

  .file-meta {
    font-size: 0.75rem;
    color: var(--cds-text-02);
  }

  .form-section {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .engine-description {
    font-size: 0.75rem;
    color: var(--cds-text-02);
    margin: 0;
    padding-left: 1.5rem;
  }

  .threshold-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 0.25rem;
  }

  .threshold-label {
    font-size: 0.75rem;
    font-weight: 500;
    color: var(--cds-text-02);
    letter-spacing: 0.32px;
  }

  .threshold-hint {
    font-size: 0.75rem;
    color: var(--cds-text-02);
    margin: 0;
  }

  .options-section {
    padding-top: 0.5rem;
    border-top: 1px solid var(--cds-border-subtle-01);
  }

  .no-tms-hint {
    font-size: 0.75rem;
    color: var(--cds-support-warning);
    margin: 0.5rem 0 0 0;
  }

  /* Progress State */
  .progress-container {
    padding: 2rem;
    text-align: center;
  }

  .progress-container :global(.running-icon) {
    color: var(--cds-interactive-01);
    margin-bottom: 1rem;
    animation: pulse 1.5s ease-in-out infinite;
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
  }

  .progress-container h4 {
    margin: 0 0 1.5rem 0;
    color: var(--cds-text-01);
  }

  .progress-note {
    margin-top: 1rem;
    font-size: 0.875rem;
    color: var(--cds-text-02);
  }

  /* Success State */
  .success-container {
    padding: 2rem;
    text-align: center;
  }

  .success-container :global(.success-icon) {
    color: var(--cds-support-success);
    margin-bottom: 1rem;
  }

  .success-container h4 {
    margin: 0 0 1.5rem 0;
    color: var(--cds-text-01);
  }

  .result-stats {
    display: flex;
    justify-content: center;
    gap: 2rem;
    margin-bottom: 1rem;
  }

  .stat {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.25rem;
  }

  .stat-value {
    font-size: 1.5rem;
    font-weight: 600;
    color: var(--cds-text-01);
  }

  .stat-label {
    font-size: 0.75rem;
    color: var(--cds-text-02);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .time-note {
    font-size: 0.875rem;
    color: var(--cds-text-02);
    margin: 0;
  }
</style>
