<script>
  /**
   * GridColumnsModal - Configure visible columns in the LDM grid
   *
   * Purpose: ONLY column visibility settings
   * Part of UI-002: Compartmentalized preferences
   */
  import {
    Modal,
    Checkbox,
    InlineNotification
  } from "carbon-components-svelte";
  import { logger } from "$lib/utils/logger.js";
  import { preferences } from "$lib/stores/preferences.js";
  import { onMount } from "svelte";

  // Svelte 5 Runes
  let { open = $bindable(false) } = $props();

  // Local UI state
  let saved = $state(false);

  // Column visibility state
  let showIndex = $state(false);
  let showStringId = $state(false);
  let showReference = $state(false);

  // Load from store
  function loadFromStore() {
    const prefs = $preferences;
    showIndex = prefs.showIndex || false;
    showStringId = prefs.showStringId || false;
    showReference = prefs.showReference || false;
  }

  // Handle column toggle
  function handleColumnToggle(column, checked) {
    preferences.setColumn(column, checked);
    showSaved();
    logger.userAction("Column visibility changed", { column, visible: checked });
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
  modalHeading="Grid Columns"
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
      Choose which columns to display in the grid. Source and Target are always visible.
    </p>

    <div class="checkbox-list">
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
    </div>

    <p class="hint">
      Reference column shows translations from a reference file. Configure the reference file in Reference Settings.
    </p>
  </div>
</Modal>

<style>
  .modal-content {
    padding: 0.5rem 0;
  }

  .description {
    margin: 0 0 1rem 0;
    font-size: 0.875rem;
    color: var(--cds-text-02);
  }

  .checkbox-list {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    margin-bottom: 1rem;
  }

  .hint {
    margin: 0;
    font-size: 0.75rem;
    color: var(--cds-text-03);
    font-style: italic;
  }

  :global(.bx--inline-notification) {
    margin-bottom: 1rem;
  }
</style>
