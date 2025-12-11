<script>
  import {
    Modal,
    Toggle,
    Select,
    SelectItem,
    FormGroup,
    InlineNotification,
    RadioButtonGroup,
    RadioButton
  } from "carbon-components-svelte";
  import { logger } from "$lib/utils/logger.js";
  import { preferences, theme, fontSize, fontWeight } from "$lib/stores/preferences.js";
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

  // Load preferences from store
  function loadFromStore() {
    const prefs = $preferences;
    currentTheme = prefs.theme || 'dark';
    currentFontSize = prefs.fontSize || 'medium';
    currentFontWeight = prefs.fontWeight || 'normal';
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

  :global(.bx--form-item) {
    margin-bottom: 1.5rem;
  }

  :global(.bx--inline-notification) {
    margin-bottom: 1rem;
  }

  :global(.bx--toggle__label-text) {
    font-size: 0.875rem;
  }
</style>
