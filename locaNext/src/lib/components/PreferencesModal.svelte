<script>
  /**
   * PreferencesModal - Display/Appearance Settings
   *
   * Purpose: ONLY font and display settings
   * Part of UI-002: Compartmentalized preferences
   *
   * Other settings are in dedicated modals:
   * - GridColumnsModal: Column visibility
   * - ReferenceSettingsModal: Reference file config
   * - TMManager: TM selection and activation
   */
  import {
    Modal,
    Select,
    SelectItem,
    Toggle,
    InlineNotification
  } from "carbon-components-svelte";
  import { logger } from "$lib/utils/logger.js";
  import { preferences } from "$lib/stores/preferences.js";
  import { onMount } from "svelte";

  // Svelte 5 Runes
  let { open = $bindable(false) } = $props();

  // Local UI state
  let saved = $state(false);

  // Font settings
  let currentFontSize = $state('medium');
  let currentFontWeight = $state('normal');
  let currentFontFamily = $state('system');
  let currentFontColor = $state('default');

  // Font size options
  const fontSizes = [
    { value: 'small', label: 'Small (12px)' },
    { value: 'medium', label: 'Medium (14px)' },
    { value: 'large', label: 'Large (16px)' }
  ];

  // Font family options (P2: includes CJK-friendly fonts)
  const fontFamilies = [
    { value: 'system', label: 'System Default' },
    { value: 'inter', label: 'Inter' },
    { value: 'roboto', label: 'Roboto' },
    { value: 'noto-sans', label: 'Noto Sans (CJK)' },
    { value: 'source-han', label: 'Source Han Sans (CJK)' },
    { value: 'consolas', label: 'Consolas (Mono)' }
  ];

  // Font color options (P2: contrast levels)
  const fontColors = [
    { value: 'default', label: 'Default' },
    { value: 'high-contrast', label: 'High Contrast' },
    { value: 'soft', label: 'Soft' }
  ];

  // Load from store
  function loadFromStore() {
    const prefs = $preferences;
    currentFontSize = prefs.fontSize || 'medium';
    currentFontWeight = prefs.fontWeight || 'normal';
    currentFontFamily = prefs.fontFamily || 'system';
    currentFontColor = prefs.fontColor || 'default';
  }

  // Handle font size change
  function handleFontSizeChange(e) {
    const size = e.target.value;
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

  // Handle font family change (P2)
  function handleFontFamilyChange(e) {
    const family = e.target.value;
    currentFontFamily = family;
    preferences.setFontFamily(family);
    showSaved();
    logger.userAction("Font family changed", { fontFamily: family });
  }

  // Handle font color change (P2)
  function handleFontColorChange(e) {
    const color = e.target.value;
    currentFontColor = color;
    preferences.setFontColor(color);
    showSaved();
    logger.userAction("Font color changed", { fontColor: color });
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
  modalHeading="Display Settings"
  passiveModal
  on:close={handleClose}
  size="xs"
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
      Adjust text appearance for better readability.
    </p>

    <div class="form-section">
      <Select
        labelText="Font Size"
        selected={currentFontSize}
        on:change={handleFontSizeChange}
      >
        {#each fontSizes as size}
          <SelectItem value={size.value} text={size.label} />
        {/each}
      </Select>
    </div>

    <div class="form-section">
      <Toggle
        labelText="Bold Text"
        labelA="Normal"
        labelB="Bold"
        toggled={currentFontWeight === 'bold'}
        on:toggle={(e) => handleFontWeightChange(e.detail.toggled)}
      />
    </div>

    <div class="form-section">
      <Select
        labelText="Font Family"
        selected={currentFontFamily}
        on:change={handleFontFamilyChange}
      >
        {#each fontFamilies as family}
          <SelectItem value={family.value} text={family.label} />
        {/each}
      </Select>
    </div>

    <div class="form-section">
      <Select
        labelText="Text Contrast"
        selected={currentFontColor}
        on:change={handleFontColorChange}
      >
        {#each fontColors as color}
          <SelectItem value={color.value} text={color.label} />
        {/each}
      </Select>
    </div>

    <p class="hint">
      CJK fonts recommended for Korean/Chinese/Japanese text.
    </p>
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

  .hint {
    margin: 1rem 0 0 0;
    font-size: 0.75rem;
    color: var(--cds-text-03);
    font-style: italic;
  }

  :global(.bx--inline-notification) {
    margin-bottom: 1rem;
  }
</style>
