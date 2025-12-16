<script>
  /**
   * ReferenceSettingsModal - Configure reference file for comparison
   *
   * Purpose: ONLY reference file configuration
   * Part of UI-002: Compartmentalized preferences
   */
  import {
    Modal,
    Select,
    SelectItem,
    RadioButtonGroup,
    RadioButton,
    InlineNotification,
    InlineLoading
  } from "carbon-components-svelte";
  import { logger } from "$lib/utils/logger.js";
  import { preferences } from "$lib/stores/preferences.js";
  import { serverUrl } from "$lib/stores/app.js";
  import { get } from "svelte/store";
  import { onMount } from "svelte";

  // Svelte 5 Runes
  let { open = $bindable(false) } = $props();

  // Local UI state
  let saved = $state(false);
  let loading = $state(false);

  // Reference settings
  let referenceFileId = $state(null);
  let referenceMatchMode = $state('stringIdOnly');
  let availableFiles = $state([]);

  // Helper to get auth headers
  function getAuthHeaders() {
    const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
    return token ? { 'Authorization': `Bearer ${token}` } : {};
  }

  // Load available files from server
  async function loadFiles() {
    loading = true;
    try {
      const API_BASE = get(serverUrl);
      const response = await fetch(`${API_BASE}/api/ldm/files?limit=100`, {
        headers: getAuthHeaders()
      });
      if (response.ok) {
        const data = await response.json();
        availableFiles = data.files || [];
      }
    } catch (err) {
      console.error('Failed to load files:', err);
    } finally {
      loading = false;
    }
  }

  // Load from store
  function loadFromStore() {
    const prefs = $preferences;
    referenceFileId = prefs.referenceFileId;
    referenceMatchMode = prefs.referenceMatchMode || 'stringIdOnly';
  }

  // Handle reference file change
  function handleReferenceFileChange(e) {
    const fileId = e.target.value ? parseInt(e.target.value) : null;
    referenceFileId = fileId;
    preferences.setReferenceFile(fileId);
    showSaved();
    logger.userAction("Reference file changed", { fileId });
  }

  // Handle match mode change
  function handleMatchModeChange(e) {
    const mode = e.detail;
    referenceMatchMode = mode;
    preferences.setReferenceMatchMode(mode);
    showSaved();
    logger.userAction("Reference match mode changed", { mode });
  }

  function showSaved() {
    saved = true;
    setTimeout(() => saved = false, 1500);
  }

  function handleClose() {
    open = false;
  }

  // Load when modal opens
  $effect(() => {
    if (open) {
      loadFromStore();
      loadFiles();
      saved = false;
    }
  });

  onMount(() => {
    loadFromStore();
  });
</script>

<Modal
  bind:open
  modalHeading="Reference Settings"
  passiveModal
  on:close={handleClose}
  size="sm"
>
  <div class="modal-content">
    {#if saved}
      <InlineNotification
        kind="success"
        title="Saved"
        hideCloseButton
        lowContrast
      />
    {/if}

    <p class="description">
      Configure a reference file to show comparison translations in the grid.
    </p>

    <div class="form-section">
      <Select
        labelText="Reference File"
        selected={referenceFileId || ''}
        on:change={handleReferenceFileChange}
      >
        <SelectItem value="" text="None (disabled)" />
        {#each availableFiles as file}
          <SelectItem value={file.id} text="{file.name} ({file.row_count || 0} rows)" />
        {/each}
      </Select>

      {#if loading}
        <InlineLoading description="Loading files..." />
      {:else if availableFiles.length === 0}
        <p class="hint">No files available. Upload files to your project first.</p>
      {/if}
    </div>

    <div class="form-section">
      <RadioButtonGroup
        legendText="Match Mode"
        selected={referenceMatchMode}
        on:change={handleMatchModeChange}
      >
        <RadioButton value="stringIdOnly" labelText="Match by String ID only" />
        <RadioButton value="stringIdAndSource" labelText="Match by String ID + Source text" />
      </RadioButtonGroup>

      <p class="hint">
        "String ID + Source" is more accurate but slower for large files.
      </p>
    </div>
  </div>
</Modal>

<style>
  .modal-content {
    padding: 0.5rem 0;
  }

  .description {
    margin: 0 0 1.5rem 0;
    font-size: 0.875rem;
    color: var(--cds-text-02);
  }

  .form-section {
    margin-bottom: 1.5rem;
  }

  .hint {
    margin: 0.5rem 0 0 0;
    font-size: 0.75rem;
    color: var(--cds-text-03);
  }

  :global(.bx--inline-notification) {
    margin-bottom: 1rem;
  }

  :global(.bx--radio-button-group) {
    margin-top: 1rem;
  }
</style>
