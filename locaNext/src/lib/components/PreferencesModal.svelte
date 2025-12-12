<script>
  import {
    Modal,
    Toggle,
    Select,
    SelectItem,
    FormGroup,
    InlineNotification,
    RadioButtonGroup,
    RadioButton,
    Checkbox
  } from "carbon-components-svelte";
  import { logger } from "$lib/utils/logger.js";
  import { preferences, theme, fontSize, fontWeight } from "$lib/stores/preferences.js";
  import { serverUrl } from "$lib/stores/app.js";
  import { get } from "svelte/store";
  import { onMount } from "svelte";

  export let open = false;

  // Local UI state
  let saved = false;

  // Local copies for binding (synced with store)
  let currentTheme = 'dark';
  let currentFontSize = 'medium';
  let currentFontWeight = 'normal';
  let notifications = true;
  let language = 'en';

  // Column visibility toggles
  let showIndex = false;
  let showStringId = false;
  let showReference = false;
  let showTmResults = false;
  let showQaResults = false;

  // TM and Reference settings
  let activeTmId = null;
  let referenceFileId = null;
  let referenceMatchMode = 'stringIdOnly';
  let availableTMs = [];
  let availableFiles = [];
  let loadingTMs = false;
  let loadingFiles = false;

  // Available languages for UI
  const languages = [
    { value: 'en', label: 'English' },
    { value: 'ko', label: 'Korean' },
    { value: 'ja', label: 'Japanese' },
    { value: 'zh', label: 'Chinese' }
  ];

  // Font size options
  const fontSizes = [
    { value: 'small', label: 'Small (12px)' },
    { value: 'medium', label: 'Medium (14px)' },
    { value: 'large', label: 'Large (16px)' }
  ];

  // Helper to get auth headers
  function getAuthHeaders() {
    const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
    return token ? { 'Authorization': `Bearer ${token}` } : {};
  }

  // Load available TMs from server
  async function loadTMs() {
    loadingTMs = true;
    try {
      const API_BASE = get(serverUrl);
      const response = await fetch(`${API_BASE}/api/ldm/tm`, {
        headers: getAuthHeaders()
      });
      if (response.ok) {
        const data = await response.json();
        availableTMs = data.tms || [];
      }
    } catch (err) {
      console.error('Failed to load TMs:', err);
    } finally {
      loadingTMs = false;
    }
  }

  // Load available files from server (for reference)
  async function loadFiles() {
    loadingFiles = true;
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
      loadingFiles = false;
    }
  }

  // Load preferences from store
  function loadFromStore() {
    const prefs = $preferences;
    currentTheme = prefs.theme || 'dark';
    currentFontSize = prefs.fontSize || 'medium';
    currentFontWeight = prefs.fontWeight || 'normal';
    // Column visibility
    showIndex = prefs.showIndex || false;
    showStringId = prefs.showStringId || false;
    showReference = prefs.showReference || false;
    showTmResults = prefs.showTmResults || false;
    showQaResults = prefs.showQaResults || false;
    // TM and Reference
    activeTmId = prefs.activeTmId;
    referenceFileId = prefs.referenceFileId;
    referenceMatchMode = prefs.referenceMatchMode || 'stringIdOnly';
  }

  // Handle theme toggle
  function handleThemeChange(isDark) {
    const newTheme = isDark ? 'dark' : 'light';
    currentTheme = newTheme;
    preferences.setTheme(newTheme);
    showSaved();
    logger.userAction("Theme changed", { theme: newTheme });
  }

  // Handle font size change
  function handleFontSizeChange(event) {
    const size = event.detail;
    currentFontSize = size;
    preferences.setFontSize(size);
    showSaved();
    logger.userAction("Font size changed", { fontSize: size });
  }

  // Handle font weight change
  function handleFontWeightChange(isBold) {
    const weight = isBold ? 'bold' : 'normal';
    currentFontWeight = weight;
    preferences.setFontWeight(weight);
    showSaved();
    logger.userAction("Font weight changed", { fontWeight: weight });
  }

  // Handle column visibility toggle
  function handleColumnToggle(column, checked) {
    preferences.setColumn(column, checked);
    showSaved();
    logger.userAction("Column visibility changed", { column, visible: checked });
  }

  // Handle TM selection
  function handleTmChange(e) {
    const tmId = e.target.value ? parseInt(e.target.value) : null;
    activeTmId = tmId;
    preferences.setActiveTm(tmId);
    showSaved();
    logger.userAction("Active TM changed", { tmId });
  }

  // Handle Reference file selection
  function handleReferenceFileChange(e) {
    const fileId = e.target.value ? parseInt(e.target.value) : null;
    referenceFileId = fileId;
    preferences.setReferenceFile(fileId);
    showSaved();
    logger.userAction("Reference file changed", { fileId });
  }

  // Handle Reference match mode change
  function handleMatchModeChange(e) {
    const mode = e.detail;
    referenceMatchMode = mode;
    preferences.setReferenceMatchMode(mode);
    showSaved();
    logger.userAction("Reference match mode changed", { mode });
  }

  function showSaved() {
    saved = true;
    setTimeout(() => saved = false, 2000);
  }

  function handleClose() {
    open = false;
  }

  // Load when modal opens
  $: if (open) {
    loadFromStore();
    loadTMs();
    loadFiles();
    saved = false;
  }

  onMount(() => {
    loadFromStore();
  });
</script>

<Modal
  bind:open
  modalHeading="Preferences"
  passiveModal
  on:close={handleClose}
  size="sm"
>
  <div class="preferences-content">
    {#if saved}
      <InlineNotification
        kind="success"
        title="Saved"
        subtitle="Preferences updated"
        hideCloseButton
        lowContrast
      />
    {/if}

    <FormGroup legendText="Theme">
      <Toggle
        labelText="Theme Mode"
        labelA="Light"
        labelB="Dark"
        toggled={currentTheme === 'dark'}
        on:toggle={(e) => handleThemeChange(e.detail.toggled)}
      />
      <p class="hint">Switch between light and dark themes.</p>
    </FormGroup>

    <FormGroup legendText="Font">
      <Select
        labelText="Font Size"
        selected={currentFontSize}
        on:change={(e) => handleFontSizeChange({ detail: e.target.value })}
      >
        {#each fontSizes as size}
          <SelectItem value={size.value} text={size.label} />
        {/each}
      </Select>

      <div class="toggle-row">
        <Toggle
          labelText="Bold Text"
          labelA="Normal"
          labelB="Bold"
          toggled={currentFontWeight === 'bold'}
          on:toggle={(e) => handleFontWeightChange(e.detail.toggled)}
        />
      </div>
      <p class="hint">Adjust text appearance for better readability.</p>
    </FormGroup>

    <FormGroup legendText="Grid Columns">
      <p class="hint" style="margin-bottom: 0.75rem;">Choose which columns to display in the LDM grid. Source and Target are always visible.</p>
      <div class="checkbox-group">
        <Checkbox
          labelText="Index Number"
          checked={showIndex}
          on:check={(e) => { showIndex = e.detail; handleColumnToggle('showIndex', e.detail); }}
        />
        <Checkbox
          labelText="String ID"
          checked={showStringId}
          on:check={(e) => { showStringId = e.detail; handleColumnToggle('showStringId', e.detail); }}
        />
        <Checkbox
          labelText="Reference Column"
          checked={showReference}
          on:check={(e) => { showReference = e.detail; handleColumnToggle('showReference', e.detail); }}
        />
        <Checkbox
          labelText="TM Results"
          checked={showTmResults}
          on:check={(e) => { showTmResults = e.detail; handleColumnToggle('showTmResults', e.detail); }}
        />
        <Checkbox
          labelText="QA Results"
          checked={showQaResults}
          on:check={(e) => { showQaResults = e.detail; handleColumnToggle('showQaResults', e.detail); }}
          disabled
        />
      </div>
      <p class="hint" style="margin-top: 0.5rem;">QA Results column will be available after QA features are implemented.</p>
    </FormGroup>

    <FormGroup legendText="Translation Memory">
      <Select
        labelText="Active TM"
        selected={activeTmId || ''}
        on:change={handleTmChange}
      >
        <SelectItem value="" text="None (disabled)" />
        {#each availableTMs as tm}
          <SelectItem value={tm.id} text="{tm.name} ({tm.entry_count || 0} entries)" />
        {/each}
      </Select>
      {#if loadingTMs}
        <p class="hint">Loading TMs...</p>
      {:else if availableTMs.length === 0}
        <p class="hint">No TMs available. Upload or register a TM first.</p>
      {:else}
        <p class="hint">Select a TM to get translation suggestions in the grid and edit modal.</p>
      {/if}
    </FormGroup>

    <FormGroup legendText="Reference File">
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
      {#if loadingFiles}
        <p class="hint">Loading files...</p>
      {:else}
        <p class="hint">Select a file to show reference translations in the grid.</p>
      {/if}

      <RadioButtonGroup
        legendText="Match Mode"
        selected={referenceMatchMode}
        on:change={handleMatchModeChange}
        style="margin-top: 1rem;"
      >
        <RadioButton value="stringIdOnly" labelText="Match by String ID only" />
        <RadioButton value="stringIdAndSource" labelText="Match by String ID + Source text" />
      </RadioButtonGroup>
      <p class="hint">Choose how to match rows between current file and reference file.</p>
    </FormGroup>

    <FormGroup legendText="Language">
      <Select
        labelText="Interface Language"
        bind:selected={language}
      >
        {#each languages as lang}
          <SelectItem value={lang.value} text={lang.label} />
        {/each}
      </Select>
      <p class="hint">Note: Language switching will be available in a future update.</p>
    </FormGroup>

    <FormGroup legendText="Notifications">
      <Toggle
        labelText="Show Notifications"
        labelA="Off"
        labelB="On"
        bind:toggled={notifications}
      />
      <p class="hint">Get notified about task completion and errors.</p>
    </FormGroup>
  </div>
</Modal>

<style>
  .preferences-content {
    padding: 1rem 0;
  }

  .hint {
    margin: 0.5rem 0 0 0;
    font-size: 0.75rem;
    color: var(--cds-text-02);
    opacity: 0.7;
  }

  .toggle-row {
    margin-top: 1rem;
  }

  .checkbox-group {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  :global(.bx--form-item) {
    margin-bottom: 1.5rem;
  }

  :global(.bx--inline-notification) {
    margin-bottom: 1rem;
  }

  :global(.bx--toggle__label-text) {
    font-size: 0.875rem;
  }

  :global(.bx--checkbox-label-text) {
    font-size: 0.875rem;
  }
</style>
