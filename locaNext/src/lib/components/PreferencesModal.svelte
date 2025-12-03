<script>
  import {
    Modal,
    Toggle,
    Select,
    SelectItem,
    FormGroup,
    InlineNotification
  } from "carbon-components-svelte";
  import { logger } from "$lib/utils/logger.js";
  import { onMount } from "svelte";

  export let open = false;

  // Preferences state
  let darkMode = true;
  let language = 'en';
  let notifications = true;
  let saved = false;

  // Available languages for UI
  const languages = [
    { value: 'en', label: 'English' },
    { value: 'ko', label: 'Korean' },
    { value: 'ja', label: 'Japanese' },
    { value: 'zh', label: 'Chinese' }
  ];

  // Load preferences from localStorage
  function loadPreferences() {
    if (typeof window !== 'undefined') {
      const prefs = localStorage.getItem('locanext_preferences');
      if (prefs) {
        try {
          const parsed = JSON.parse(prefs);
          darkMode = parsed.darkMode ?? true;
          language = parsed.language ?? 'en';
          notifications = parsed.notifications ?? true;
        } catch (e) {
          logger.error("Failed to parse preferences", { error: e.message });
        }
      }
    }
  }

  // Save preferences to localStorage
  function savePreferences() {
    if (typeof window !== 'undefined') {
      const prefs = { darkMode, language, notifications };
      localStorage.setItem('locanext_preferences', JSON.stringify(prefs));
      logger.userAction("Preferences saved", prefs);
      saved = true;
      setTimeout(() => saved = false, 2000);
    }
  }

  // Auto-save on change
  function handleChange() {
    savePreferences();
  }

  function handleClose() {
    open = false;
  }

  onMount(() => {
    loadPreferences();
  });

  // Load when modal opens
  $: if (open) {
    loadPreferences();
    saved = false;
  }
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

    <FormGroup legendText="Appearance">
      <Toggle
        labelText="Dark Mode"
        labelA="Light"
        labelB="Dark"
        bind:toggled={darkMode}
        on:toggle={handleChange}
      />
      <p class="hint">Note: Dark mode is always enabled in this version.</p>
    </FormGroup>

    <FormGroup legendText="Language">
      <Select
        labelText="Interface Language"
        bind:selected={language}
        on:change={handleChange}
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
        on:toggle={handleChange}
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
