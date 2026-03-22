<script>
  /**
   * ProjectSettingsModal — Phase 56, Plan 02
   *
   * Modal for configuring per-project LOC PATH and EXPORT PATH settings.
   * Validates paths against the backend endpoint and persists to localStorage.
   */
  import {
    Modal,
    TextInput,
    Button,
    InlineNotification,
    InlineLoading
  } from "carbon-components-svelte";
  import { getProjectSettings, setProjectSettings } from "$lib/stores/projectSettings.js";
  import { logger } from "$lib/utils/logger.js";

  // Props (Svelte 5 Runes)
  let { open = $bindable(false), projectId = null, projectName = '' } = $props();

  // State
  let locPath = $state('');
  let exportPath = $state('');
  let locPathError = $state('');
  let exportPathError = $state('');
  let locPathValid = $state(false);
  let exportPathValid = $state(false);
  let locPathInfo = $state('');
  let exportPathInfo = $state('');
  let validating = $state(false);
  let saved = $state(false);

  // Load settings when modal opens
  $effect(() => {
    if (open && projectId) {
      const settings = getProjectSettings(projectId);
      locPath = settings.locPath;
      exportPath = settings.exportPath;
      locPathError = '';
      exportPathError = '';
      locPathValid = false;
      exportPathValid = false;
      locPathInfo = '';
      exportPathInfo = '';
      saved = false;
    }
  });

  /**
   * Validate a path against the backend endpoint.
   * @param {string} path - The path to validate
   * @param {'loc' | 'export'} type - Which path field to update
   */
  async function validatePath(path, type) {
    if (!path.trim()) {
      if (type === 'loc') {
        locPathError = 'Path cannot be empty';
        locPathValid = false;
        locPathInfo = '';
      } else {
        exportPathError = 'Path cannot be empty';
        exportPathValid = false;
        exportPathInfo = '';
      }
      return;
    }

    validating = true;

    try {
      const res = await fetch('/api/settings/validate-path', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path })
      });

      const data = await res.json();

      if (!res.ok || !data.valid) {
        const errorMsg = data.error || 'Validation failed';
        const hint = data.hint || '';
        if (type === 'loc') {
          locPathError = hint ? `${errorMsg}. ${hint}` : errorMsg;
          locPathValid = false;
          locPathInfo = '';
        } else {
          exportPathError = hint ? `${errorMsg}. ${hint}` : errorMsg;
          exportPathValid = false;
          exportPathInfo = '';
        }
      } else {
        if (type === 'loc') {
          locPathError = '';
          locPathValid = true;
          locPathInfo = `${data.files_found} languagedata file${data.files_found !== 1 ? 's' : ''} found`;
        } else {
          exportPathError = '';
          exportPathValid = true;
          exportPathInfo = `${data.files_found} languagedata file${data.files_found !== 1 ? 's' : ''} found`;
        }
      }
    } catch (err) {
      const errorMsg = 'Failed to validate path (server unreachable)';
      if (type === 'loc') {
        locPathError = errorMsg;
        locPathValid = false;
        locPathInfo = '';
      } else {
        exportPathError = errorMsg;
        exportPathValid = false;
        exportPathInfo = '';
      }
    } finally {
      validating = false;
    }
  }

  function handleSave() {
    if (!projectId) return;
    setProjectSettings(projectId, { locPath, exportPath });
    saved = true;
    logger.userAction("Project settings saved", { projectId, locPath, exportPath });
    setTimeout(() => {
      open = false;
      saved = false;
    }, 1000);
  }

  function handleClose() {
    open = false;
    saved = false;
  }
</script>

<Modal
  bind:open
  modalHeading="Project Settings — {projectName || 'Unknown'}"
  primaryButtonText="Save"
  secondaryButtonText="Cancel"
  on:click:button--primary={handleSave}
  on:click:button--secondary={handleClose}
  onclose={handleClose}
  size="sm"
>
  <div class="modal-content">
    {#if saved}
      <InlineNotification
        kind="success"
        title="Settings saved"
        subtitle="Paths have been stored for this project."
        hideCloseButton
        lowContrast
      />
    {/if}

    {#if validating}
      <InlineLoading description="Validating path..." />
    {/if}

    <!-- LOC PATH -->
    <div class="path-section">
      <h4>LOC PATH</h4>
      <p class="path-description">
        Path to the LOC/LOCDEV folder containing languagedata files for this project.
      </p>
      <div class="path-input-row">
        <TextInput
          bind:value={locPath}
          placeholder="/mnt/c/path/to/LOC"
          invalid={!!locPathError}
          invalidText={locPathError}
          labelText=""
        />
        <Button
          kind="ghost"
          size="small"
          on:click={() => validatePath(locPath, 'loc')}
          disabled={validating}
        >
          Validate
        </Button>
      </div>
      {#if locPathValid}
        <InlineNotification
          kind="success"
          title="Path valid"
          subtitle={locPathInfo}
          hideCloseButton
          lowContrast
        />
      {/if}
    </div>

    <div class="section-divider"></div>

    <!-- EXPORT PATH -->
    <div class="path-section">
      <h4>EXPORT PATH</h4>
      <p class="path-description">
        Path where exported/translated files are stored.
      </p>
      <div class="path-input-row">
        <TextInput
          bind:value={exportPath}
          placeholder="/mnt/c/path/to/EXPORT"
          invalid={!!exportPathError}
          invalidText={exportPathError}
          labelText=""
        />
        <Button
          kind="ghost"
          size="small"
          on:click={() => validatePath(exportPath, 'export')}
          disabled={validating}
        >
          Validate
        </Button>
      </div>
      {#if exportPathValid}
        <InlineNotification
          kind="success"
          title="Path valid"
          subtitle={exportPathInfo}
          hideCloseButton
          lowContrast
        />
      {/if}
    </div>
  </div>
</Modal>

<style>
  .modal-content {
    padding: 0.5rem 0;
  }

  .path-section {
    margin-bottom: 1rem;
  }

  .path-section h4 {
    margin: 0 0 0.25rem 0;
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--cds-text-01);
  }

  .path-description {
    margin: 0 0 0.75rem 0;
    font-size: 0.75rem;
    color: var(--cds-text-03);
  }

  .path-input-row {
    display: flex;
    align-items: flex-start;
    gap: 0.5rem;
  }

  .path-input-row :global(.bx--text-input-wrapper) {
    flex: 1;
  }

  .section-divider {
    height: 1px;
    background: var(--cds-ui-03, #393939);
    margin: 1.5rem 0;
  }

  :global(.bx--inline-notification) {
    margin-top: 0.5rem;
    margin-bottom: 0.5rem;
  }
</style>
