<script>
  /**
   * ReferenceSettingsModal - Configure reference file for comparison
   *
   * Purpose: ONLY reference file configuration
   * Part of UI-002: Compartmentalized preferences
   * UI-096: Enhanced with FilePickerDialog for hierarchical browsing
   */
  import {
    Modal,
    RadioButtonGroup,
    RadioButton,
    InlineNotification,
    Button,
    Tag
  } from "carbon-components-svelte";
  import { Document, FolderOpen, Close } from "carbon-icons-svelte";
  import { logger } from "$lib/utils/logger.js";
  import { preferences } from "$lib/stores/preferences.js";
  import { serverUrl } from "$lib/stores/app.js";
  import { get } from "svelte/store";
  import { onMount } from "svelte";
  import FilePickerDialog from "$lib/components/ldm/FilePickerDialog.svelte";

  // Svelte 5 Runes
  let { open = $bindable(false) } = $props();

  // Local UI state
  let saved = $state(false);
  let showFilePicker = $state(false);

  // Reference settings
  let referenceFileId = $state(null);
  let referenceFileName = $state(null);
  let referenceFileRowCount = $state(0);
  let referenceMatchMode = $state('stringIdOnly');

  // Helper to get auth headers
  function getAuthHeaders() {
    const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
    return token ? { 'Authorization': `Bearer ${token}` } : {};
  }

  // Load file info if we have a reference file ID
  async function loadFileInfo(fileId) {
    if (!fileId) {
      referenceFileName = null;
      referenceFileRowCount = 0;
      return;
    }
    try {
      const API_BASE = get(serverUrl);
      const response = await fetch(`${API_BASE}/api/ldm/files/${fileId}`, {
        headers: getAuthHeaders()
      });
      if (response.ok) {
        const file = await response.json();
        referenceFileName = file.name;
        referenceFileRowCount = file.row_count || 0;
      }
    } catch (err) {
      console.error('Failed to load file info:', err);
    }
  }

  // Load from store
  function loadFromStore() {
    const prefs = $preferences;
    referenceFileId = prefs.referenceFileId;
    referenceMatchMode = prefs.referenceMatchMode || 'stringIdOnly';
    if (referenceFileId) {
      loadFileInfo(referenceFileId);
    }
  }

  // Handle file selection from picker
  function handleFileSelect(e) {
    const file = e.detail;
    referenceFileId = file.id;
    referenceFileName = file.name;
    referenceFileRowCount = file.row_count || 0;
    preferences.setReferenceFile(file.id);
    showSaved();
    logger.userAction("Reference file changed", { fileId: file.id, fileName: file.name });
  }

  // Clear reference file
  function clearReferenceFile() {
    referenceFileId = null;
    referenceFileName = null;
    referenceFileRowCount = 0;
    preferences.setReferenceFile(null);
    showSaved();
    logger.userAction("Reference file cleared");
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
      <span class="field-label">Reference File</span>

      {#if referenceFileId && referenceFileName}
        <!-- Selected file display -->
        <div class="selected-file">
          <Document size={16} />
          <div class="file-info">
            <span class="file-name">{referenceFileName}</span>
            <Tag type="gray" size="sm">{referenceFileRowCount} rows</Tag>
          </div>
          <div class="file-actions">
            <Button
              kind="ghost"
              size="small"
              icon={FolderOpen}
              iconDescription="Change file"
              on:click={() => showFilePicker = true}
            />
            <Button
              kind="ghost"
              size="small"
              icon={Close}
              iconDescription="Clear reference"
              on:click={clearReferenceFile}
            />
          </div>
        </div>
      {:else}
        <!-- No file selected -->
        <div class="no-file">
          <Button
            kind="tertiary"
            size="small"
            icon={FolderOpen}
            on:click={() => showFilePicker = true}
          >
            Browse Files...
          </Button>
          <span class="no-file-text">No reference file selected</span>
        </div>
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

<!-- File Picker Dialog -->
<FilePickerDialog
  bind:open={showFilePicker}
  title="Select Reference File"
  selectedFileId={referenceFileId}
  on:select={handleFileSelect}
/>

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

  .field-label {
    display: block;
    font-size: 0.75rem;
    font-weight: 500;
    color: var(--cds-text-02);
    margin-bottom: 0.5rem;
    letter-spacing: 0.32px;
  }

  .selected-file {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem;
    background: var(--cds-layer-02);
    border-radius: 4px;
    border-left: 3px solid var(--cds-interactive-01);
  }

  .file-info {
    flex: 1;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .file-name {
    font-weight: 500;
    color: var(--cds-text-01);
  }

  .file-actions {
    display: flex;
    gap: 0.25rem;
  }

  .no-file {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 0.5rem 0;
  }

  .no-file-text {
    font-size: 0.875rem;
    color: var(--cds-text-02);
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
