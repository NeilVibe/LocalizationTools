<script>
  /**
   * ServerSettingsModal - Server Connection Settings
   *
   * Allows users to configure the PostgreSQL server connection:
   * - Mode: Offline (local) / Online (server)
   * - Server address + port
   * - Test connection
   * - View connection status
   */
  import {
    Modal,
    TextInput,
    RadioButtonGroup,
    RadioButton,
    Button,
    InlineNotification
  } from "carbon-components-svelte";
  import { Connection, Checkmark, WarningAlt } from "carbon-icons-svelte";
  import { logger } from "$lib/utils/logger.js";
  import { api } from "$lib/api/client.js";
  import { serverUrl } from "$lib/stores/app.js";

  let { open = $bindable(false) } = $props();

  // Connection settings
  let mode = $state("auto");
  let serverHost = $state("localhost");
  let serverPort = $state("5432");
  let dbUser = $state("locanext_service");
  let dbPassword = $state("");
  let dbName = $state("localizationtools");

  // Status
  let currentStatus = $state(null);
  let testing = $state(false);
  let testResult = $state(null);
  let saving = $state(false);
  let saved = $state(false);
  let error = $state(null);

  // Load config when modal opens (not on app startup)
  $effect(() => {
    if (open) loadConfig();
  });

  async function loadConfig() {
    try {
      const resp = await api.request("/api/server-config/config");
      if (resp) {
        serverHost = resp.postgres_host || "localhost";
        serverPort = String(resp.postgres_port || 5432);
        dbUser = resp.postgres_user || "locanext_service";
        dbName = resp.postgres_db || "localizationtools";
        mode = resp.database_mode || "auto";
      }
    } catch (e) {
      logger.warn("Failed to load server config", e);
    }

    try {
      const status = await api.request("/api/server-config/status");
      currentStatus = status;
    } catch (e) {
      logger.warn("Failed to load server status", e);
    }
  }

  async function testConnection() {
    testing = true;
    testResult = null;
    error = null;

    try {
      const result = await api.request("/api/server-config/test-connection", {
        method: "POST",
        body: JSON.stringify({
          postgres_host: serverHost,
          postgres_port: parseInt(serverPort),
          postgres_user: dbUser,
          postgres_password: dbPassword,
          postgres_db: dbName,
          database_mode: mode,
        }),
      });
      testResult = result;
    } catch (e) {
      testResult = { success: false, message: `Request failed: ${e.message}` };
    } finally {
      testing = false;
    }
  }

  async function saveConfig() {
    saving = true;
    saved = false;
    error = null;

    try {
      const result = await api.request("/api/server-config/config", {
        method: "POST",
        body: JSON.stringify({
          postgres_host: serverHost,
          postgres_port: parseInt(serverPort),
          postgres_user: dbUser,
          postgres_password: dbPassword,
          postgres_db: dbName,
          database_mode: mode,
        }),
      });

      if (result.success) {
        saved = true;
        logger.userAction("Server config saved", { host: serverHost, port: serverPort });
        // Also save to localStorage for frontend
        localStorage.setItem("locanext_server_host", serverHost);
        localStorage.setItem("locanext_server_port", serverPort);
        setTimeout(() => { saved = false; }, 3000);
      } else {
        error = result.message || "Failed to save configuration";
      }
    } catch (e) {
      error = `Save failed: ${e.message}`;
    } finally {
      saving = false;
    }
  }

  function handleClose() {
    open = false;
  }
</script>

<Modal
  bind:open
  modalHeading="Server Connection"
  passiveModal
  size="sm"
  onclose={handleClose}
>
  <div class="server-settings">
    <!-- Current Status -->
    {#if currentStatus}
      <div class="status-banner" class:online={currentStatus.is_online} class:offline={!currentStatus.is_online}>
        <div class="status-icon">
          {#if currentStatus.is_online}
            <Checkmark size={20} />
          {:else}
            <WarningAlt size={20} />
          {/if}
        </div>
        <div class="status-text">
          <strong>{currentStatus.is_online ? 'Online' : 'Offline'}</strong>
          <span>— {currentStatus.active_database === 'postgresql' ? `PostgreSQL at ${currentStatus.postgres_host}` : 'Local SQLite'}</span>
          {#if currentStatus.lan_ip}
            <div class="lan-ip">LAN IP: {currentStatus.lan_ip}</div>
          {/if}
        </div>
      </div>
    {/if}

    <!-- Database Mode -->
    <div class="section">
      <h4>Database Mode</h4>
      <RadioButtonGroup bind:selected={mode} legendText="">
        <RadioButton value="auto" labelText="Auto (try server, fallback to local)" />
        <RadioButton value="postgresql" labelText="Online Only (require server)" />
        <RadioButton value="sqlite" labelText="Offline Only (local storage)" />
      </RadioButtonGroup>
    </div>

    <!-- Server Connection (shown when not sqlite-only) -->
    {#if mode !== "sqlite"}
      <div class="section">
        <h4>PostgreSQL Server</h4>
        <div class="input-row">
          <TextInput
            bind:value={serverHost}
            labelText="Server Address"
            placeholder="192.168.1.100 or localhost"
            size="sm"
          />
          <TextInput
            bind:value={serverPort}
            labelText="Port"
            placeholder="5432"
            size="sm"
            style="max-width: 100px;"
          />
        </div>
        <div class="input-row">
          <TextInput
            bind:value={dbUser}
            labelText="Username"
            placeholder="locanext_service"
            size="sm"
          />
          <TextInput
            bind:value={dbPassword}
            labelText="Password"
            placeholder="Enter password"
            type="password"
            size="sm"
          />
        </div>
        <TextInput
          bind:value={dbName}
          labelText="Database Name"
          placeholder="localizationtools"
          size="sm"
        />

        <!-- Test + Save buttons -->
        <div class="button-row">
          <Button
            kind="secondary"
            size="small"
            icon={Connection}
            onclick={testConnection}
            disabled={testing}
          >
            {testing ? "Testing..." : "Test Connection"}
          </Button>
          <Button
            kind="primary"
            size="small"
            onclick={saveConfig}
            disabled={saving}
          >
            {saving ? "Saving..." : "Save & Restart Required"}
          </Button>
        </div>
      </div>
    {:else}
      <div class="section">
        <InlineNotification
          kind="info"
          title="Offline Mode"
          subtitle="All data stored locally. No server connection needed."
          hideCloseButton
        />
      </div>
    {/if}

    <!-- Test Result -->
    {#if testResult}
      <div class="section">
        {#if testResult.success}
          <InlineNotification
            kind="success"
            title="Connected!"
            subtitle="{testResult.message}{testResult.latency_ms ? ` (${testResult.latency_ms}ms)` : ''}"
            hideCloseButton
          />
          {#if testResult.pg_version}
            <div class="pg-version">{testResult.pg_version}</div>
          {/if}
        {:else}
          <InlineNotification
            kind="error"
            title="Connection Failed"
            subtitle={testResult.message}
            hideCloseButton
          />
        {/if}
      </div>
    {/if}

    <!-- Save feedback -->
    {#if saved}
      <InlineNotification
        kind="success"
        title="Saved"
        subtitle="Configuration saved. Restart LocaNext to apply changes."
        hideCloseButton
      />
    {/if}

    {#if error}
      <InlineNotification
        kind="error"
        title="Error"
        subtitle={error}
        hideCloseButton
      />
    {/if}

    <!-- Info section -->
    <div class="info-section">
      <h4>Setup Guide</h4>
      <ol>
        <li>Admin runs the setup script on the server machine</li>
        <li>Admin creates user accounts via the <strong>Admin Dashboard</strong></li>
        <li>Teammates enter the server address here</li>
        <li>Click <strong>Test Connection</strong> to verify</li>
        <li>Save and restart LocaNext</li>
      </ol>
    </div>
  </div>
</Modal>

<style>
  .server-settings {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .status-banner {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem 1rem;
    border-radius: 4px;
    border-left: 4px solid;
  }

  .status-banner.online {
    background: rgba(36, 161, 72, 0.1);
    border-color: #24a148;
  }

  .status-banner.offline {
    background: rgba(248, 210, 66, 0.1);
    border-color: #f1c21b;
  }

  .status-icon {
    flex-shrink: 0;
  }

  .status-text {
    font-size: 0.875rem;
  }

  .status-text strong {
    color: var(--cds-text-01);
  }

  .lan-ip {
    font-size: 0.75rem;
    color: var(--cds-text-02);
    margin-top: 0.25rem;
    font-family: monospace;
  }

  .section {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .section h4 {
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--cds-text-01);
    margin: 0;
  }

  .input-row {
    display: flex;
    gap: 0.5rem;
  }

  .button-row {
    display: flex;
    gap: 0.5rem;
    margin-top: 0.5rem;
  }

  .pg-version {
    font-size: 0.75rem;
    color: var(--cds-text-02);
    font-family: monospace;
    padding: 0.25rem 0;
  }

  .info-section {
    border-top: 1px solid var(--cds-ui-03);
    padding-top: 0.75rem;
  }

  .info-section h4 {
    font-size: 0.875rem;
    font-weight: 600;
    margin: 0 0 0.5rem;
  }

  .info-section ol {
    margin: 0;
    padding-left: 1.25rem;
    font-size: 0.8125rem;
    color: var(--cds-text-02);
    line-height: 1.6;
  }
</style>
