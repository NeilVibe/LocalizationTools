<script>
  /**
   * ServerConfigModal.svelte
   * BUG-012 Fix: Server Configuration Modal
   *
   * Allows users to configure PostgreSQL server connection settings.
   * Saves to %APPDATA%/LocaNext/server-config.json
   */
  import {
    Modal,
    TextInput,
    PasswordInput,
    NumberInput,
    Button,
    InlineNotification,
    InlineLoading
  } from "carbon-components-svelte";
  import {
    CheckmarkFilled,
    Error,
    ConnectionSignal,
    Save,
    Renew
  } from "carbon-icons-svelte";
  import { onMount } from "svelte";
  import { logger } from "$lib/utils/logger.js";
  import { serverUrl } from "$lib/stores/app.js";
  import { get } from "svelte/store";

  // Svelte 5: Props
  let { open = $bindable(false) } = $props();

  // Svelte 5: State
  let loading = $state(false);
  let testing = $state(false);
  let saving = $state(false);
  let testResult = $state(null);
  let saveResult = $state(null);
  let errorMessage = $state("");

  // Form fields
  let postgresHost = $state("");
  let postgresPort = $state(5432);
  let postgresUser = $state("");
  let postgresPassword = $state("");
  let postgresDb = $state("");
  let configFilePath = $state("");
  let configFileExists = $state(false);
  let passwordSet = $state(false);

  // Derived API base URL
  let API_BASE = $derived(get(serverUrl));

  // Helper to get auth headers
  function getAuthHeaders() {
    const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
    return token ? { 'Authorization': `Bearer ${token}` } : {};
  }

  // Load current configuration
  async function loadConfig() {
    loading = true;
    errorMessage = "";

    try {
      const response = await fetch(`${API_BASE}/api/server-config`, {
        headers: getAuthHeaders()
      });

      if (response.ok) {
        const config = await response.json();
        postgresHost = config.postgres_host || "";
        postgresPort = config.postgres_port || 5432;
        postgresUser = config.postgres_user || "";
        postgresDb = config.postgres_db || "";
        configFilePath = config.config_file_path || "";
        configFileExists = config.config_file_exists || false;
        passwordSet = config.postgres_password_set || false;

        // Don't load password for security - show placeholder if set
        postgresPassword = "";

        logger.info("Loaded server config", { host: postgresHost, port: postgresPort });
      } else {
        errorMessage = "Failed to load server configuration";
      }
    } catch (err) {
      errorMessage = err.message;
      logger.error("Failed to load server config", { error: err.message });
    } finally {
      loading = false;
    }
  }

  // Test connection with provided settings
  async function testConnection() {
    testing = true;
    testResult = null;

    try {
      const response = await fetch(`${API_BASE}/api/server-config/test`, {
        method: "POST",
        headers: {
          ...getAuthHeaders(),
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          postgres_host: postgresHost,
          postgres_port: postgresPort,
          postgres_user: postgresUser,
          postgres_password: postgresPassword,
          postgres_db: postgresDb
        })
      });

      testResult = await response.json();
      logger.info("Connection test result", testResult);
    } catch (err) {
      testResult = { success: false, message: err.message };
      logger.error("Connection test failed", { error: err.message });
    } finally {
      testing = false;
    }
  }

  // Save configuration
  async function saveConfig() {
    saving = true;
    saveResult = null;

    try {
      const response = await fetch(`${API_BASE}/api/server-config`, {
        method: "POST",
        headers: {
          ...getAuthHeaders(),
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          postgres_host: postgresHost,
          postgres_port: postgresPort,
          postgres_user: postgresUser,
          postgres_password: postgresPassword,
          postgres_db: postgresDb
        })
      });

      saveResult = await response.json();

      if (saveResult.success) {
        configFileExists = true;
        passwordSet = true;
        logger.info("Server config saved", saveResult);
      }
    } catch (err) {
      saveResult = { success: false, message: err.message };
      logger.error("Failed to save server config", { error: err.message });
    } finally {
      saving = false;
    }
  }

  // Watch open state
  $effect(() => {
    if (open) {
      loadConfig();
      testResult = null;
      saveResult = null;
    }
  });
</script>

<Modal
  bind:open
  modalHeading="Server Configuration"
  primaryButtonText="Save Configuration"
  secondaryButtonText="Cancel"
  primaryButtonDisabled={saving || !postgresHost || !postgresUser || !postgresPassword || !postgresDb}
  on:click:button--primary={saveConfig}
  on:click:button--secondary={() => open = false}
  on:close={() => open = false}
  size="sm"
>
  <div class="config-content">
    {#if loading}
      <div class="loading-container">
        <InlineLoading description="Loading configuration..." />
      </div>
    {:else}
      <!-- Instructions -->
      <InlineNotification
        kind="info"
        title="Configure Central Server"
        subtitle="Enter your PostgreSQL server connection details. Changes require app restart."
        hideCloseButton
        lowContrast
      />

      <!-- Config file status -->
      <div class="config-status">
        <span class="status-label">Config file:</span>
        <span class="status-value">{configFilePath}</span>
        {#if configFileExists}
          <CheckmarkFilled size={16} class="status-icon success" />
        {:else}
          <span class="status-note">(not created yet)</span>
        {/if}
      </div>

      <!-- Form -->
      <div class="form-section">
        <TextInput
          labelText="PostgreSQL Host"
          placeholder="e.g., 172.28.150.120 or postgres.example.com"
          bind:value={postgresHost}
          required
        />

        <NumberInput
          label="Port"
          min={1}
          max={65535}
          bind:value={postgresPort}
        />

        <TextInput
          labelText="Database Name"
          placeholder="e.g., locanext"
          bind:value={postgresDb}
          required
        />

        <TextInput
          labelText="Username"
          placeholder="e.g., locanext_user"
          bind:value={postgresUser}
          required
        />

        <PasswordInput
          labelText="Password"
          placeholder={passwordSet ? "(password saved)" : "Enter password"}
          bind:value={postgresPassword}
          required
        />
      </div>

      <!-- Test Connection -->
      <div class="test-section">
        <Button
          kind="tertiary"
          size="small"
          icon={testing ? null : ConnectionSignal}
          disabled={testing || !postgresHost || !postgresUser || !postgresPassword || !postgresDb}
          on:click={testConnection}
        >
          {#if testing}
            <InlineLoading description="Testing..." />
          {:else}
            Test Connection
          {/if}
        </Button>

        {#if testResult}
          <div class="test-result" class:success={testResult.success} class:error={!testResult.success}>
            {#if testResult.success}
              <CheckmarkFilled size={16} />
            {:else}
              <Error size={16} />
            {/if}
            <span>{testResult.message}</span>
          </div>
        {/if}
      </div>

      <!-- Save Result -->
      {#if saveResult}
        <InlineNotification
          kind={saveResult.success ? "success" : "error"}
          title={saveResult.success ? "Configuration Saved" : "Save Failed"}
          subtitle={saveResult.message}
          hideCloseButton
          lowContrast
        />
      {/if}
    {/if}
  </div>
</Modal>

<style>
  .config-content {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    padding: 0.5rem 0;
  }

  .loading-container {
    display: flex;
    justify-content: center;
    padding: 2rem;
  }

  .config-status {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem;
    background: var(--cds-layer-02);
    border-radius: 4px;
    font-size: 0.75rem;
  }

  .status-label {
    color: var(--cds-text-02);
  }

  .status-value {
    font-family: monospace;
    color: var(--cds-text-01);
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .status-note {
    color: var(--cds-text-03);
    font-style: italic;
  }

  :global(.status-icon.success) {
    color: var(--cds-support-success, #24a148);
  }

  .form-section {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .test-section {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding-top: 0.5rem;
  }

  .test-result {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.875rem;
  }

  .test-result.success {
    color: var(--cds-support-success, #24a148);
  }

  .test-result.error {
    color: var(--cds-support-error, #da1e28);
  }

  :global(.bx--form-item) {
    margin-bottom: 0;
  }

  :global(.bx--inline-notification) {
    max-width: 100%;
  }
</style>
