<script>
  /**
   * BranchDriveSettingsModal - Configure branch/drive for MapData context
   *
   * Purpose: Branch name, drive letter, and metadata reading toggle
   * for resolving Perforce paths to game assets (images, audio).
   * Phase 5: Visual Polish and Integration (Plan 01)
   */
  import {
    Modal,
    Select,
    SelectItem,
    TextInput,
    Toggle,
    InlineNotification,
    Button
  } from "carbon-components-svelte";
  import { Reset } from "carbon-icons-svelte";
  import { logger } from "$lib/utils/logger.js";
  import { preferences } from "$lib/stores/preferences.js";
  import { serverUrl } from "$lib/stores/app.js";
  import { get } from "svelte/store";
  import { getAuthHeaders } from "$lib/utils/api.js";

  // Svelte 5 Runes
  let { open = $bindable(false) } = $props();

  // Known branches (matches MapDataGenerator config.py)
  const KNOWN_BRANCHES = ["mainline", "cd_beta", "cd_alpha", "cd_lambda"];

  // Path templates for preview (subset of MapDataGenerator PATH_TEMPLATES)
  const PATH_PREVIEW_KEYS = [
    { key: 'texture', label: 'Textures', template: '{drive}:\\perforce\\common\\{branch}\\commonresource\\ui\\texture\\image' },
    { key: 'audio', label: 'Audio (EN)', template: '{drive}:\\perforce\\cd\\{branch}\\resource\\sound\\windows\\English(US)' },
    { key: 'loc', label: 'Localization', template: '{drive}:\\perforce\\cd\\{branch}\\resource\\GameData\\stringtable\\loc' },
  ];

  // Local UI state
  let saved = $state(false);
  let error = $state(null);
  let selectedBranch = $state('mainline');
  let driveInput = $state('F');
  let metadataReading = $state(true);

  // Computed path preview
  let pathPreviews = $derived(
    PATH_PREVIEW_KEYS.map(item => ({
      label: item.label,
      path: item.template
        .replace('{drive}', driveInput.toUpperCase())
        .replace('{branch}', selectedBranch)
    }))
  );

  // Load from store
  function loadFromStore() {
    const prefs = get(preferences);
    selectedBranch = prefs.mdgBranch || 'mainline';
    driveInput = prefs.mdgDrive || 'F';
    metadataReading = prefs.mdgMetadataReading !== false;
  }

  // Save settings
  async function handleSave() {
    error = null;

    // Validate drive letter
    const drive = driveInput.trim().toUpperCase();
    if (!drive || drive.length !== 1 || !/^[A-Z]$/.test(drive)) {
      error = "Drive must be a single letter (A-Z)";
      return;
    }

    // Update preferences store
    preferences.update(prefs => ({
      ...prefs,
      mdgBranch: selectedBranch,
      mdgDrive: drive,
      mdgMetadataReading: metadataReading,
    }));

    // Notify backend
    try {
      const API_BASE = get(serverUrl);
      const response = await fetch(`${API_BASE}/api/ldm/mapdata/configure`, {
        method: 'POST',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ branch: selectedBranch, drive }),
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        const detail = data.detail;
        error = typeof detail === 'string' ? detail : `Server error: ${response.status}`;
        return;
      }
    } catch (err) {
      // Non-blocking: backend may not be running (offline mode)
      logger.warning("MapData configure request failed (non-blocking)", { error: err.message });
    }

    driveInput = drive;
    showSaved();
    logger.userAction("MapData settings saved", { branch: selectedBranch, drive, metadataReading });
  }

  // Reset to defaults
  function handleReset() {
    selectedBranch = 'mainline';
    driveInput = 'F';
    metadataReading = true;
    error = null;
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
      error = null;
    }
  });
</script>

<Modal
  bind:open
  modalHeading="Branch & Drive Settings"
  passiveModal
  onclose={handleClose}
  size="sm"
>
  <div class="modal-content">
    {#if saved}
      <InlineNotification
        kind="success"
        title="Settings saved"
        hideCloseButton
        lowContrast
      />
    {/if}

    {#if error}
      <InlineNotification
        kind="error"
        title="Error"
        subtitle={error}
        hideCloseButton
        lowContrast
      />
    {/if}

    <p class="description">
      Configure the Perforce branch and drive letter for resolving game asset paths
      (textures, audio, localization data).
    </p>

    <div class="form-section">
      <Select
        data-testid="settings-branch-select"
        labelText="Branch"
        bind:selected={selectedBranch}
      >
        {#each KNOWN_BRANCHES as branch}
          <SelectItem value={branch} text={branch} />
        {/each}
      </Select>
    </div>

    <div class="form-section">
      <TextInput
        data-testid="settings-drive-input"
        labelText="Drive Letter"
        bind:value={driveInput}
        maxlength={1}
        placeholder="F"
        helperText="Single letter (e.g., F, D, E)"
      />
    </div>

    <div class="form-section">
      <Toggle
        data-testid="settings-metadata-toggle"
        labelText="Metadata Reading"
        labelA="Disabled"
        labelB="Enabled"
        bind:toggled={metadataReading}
      />
      <p class="hint">
        When enabled, loads image and audio context from game data files.
      </p>
    </div>

    <!-- Path Preview -->
    <div class="form-section path-preview">
      <span class="field-label">Resolved Paths Preview</span>
      {#each pathPreviews as preview}
        <div class="path-item">
          <span class="path-label">{preview.label}</span>
          <code class="path-value">{preview.path}</code>
        </div>
      {/each}
    </div>

    <!-- Action buttons -->
    <div class="actions">
      <Button
        data-testid="settings-save-btn"
        kind="primary"
        size="small"
        onclick={handleSave}
      >
        Save
      </Button>
      <Button
        kind="ghost"
        size="small"
        icon={Reset}
        iconDescription="Reset to defaults"
        onclick={handleReset}
      >
        Reset
      </Button>
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
    margin-bottom: 1.25rem;
  }

  .field-label {
    display: block;
    font-size: 0.75rem;
    font-weight: 500;
    color: var(--cds-text-02);
    margin-bottom: 0.5rem;
    letter-spacing: 0.32px;
  }

  .path-preview {
    background: var(--cds-layer-02);
    border-radius: 4px;
    padding: 0.75rem;
  }

  .path-item {
    display: flex;
    flex-direction: column;
    gap: 0.125rem;
    margin-bottom: 0.5rem;
  }

  .path-item:last-child {
    margin-bottom: 0;
  }

  .path-label {
    font-size: 0.6875rem;
    font-weight: 500;
    color: var(--cds-text-02);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .path-value {
    font-size: 0.75rem;
    color: var(--cds-text-01);
    word-break: break-all;
    font-family: 'Consolas', 'Monaco', monospace;
    opacity: 0.85;
  }

  .hint {
    margin: 0.25rem 0 0 0;
    font-size: 0.75rem;
    color: var(--cds-text-03);
  }

  .actions {
    display: flex;
    gap: 0.5rem;
    margin-top: 1.5rem;
    padding-top: 1rem;
    border-top: 1px solid var(--cds-border-subtle-01);
  }

  :global(.bx--inline-notification) {
    margin-bottom: 1rem;
  }
</style>
