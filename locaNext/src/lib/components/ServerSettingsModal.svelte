<script>
  /**
   * ServerSettingsModal - Server Connection Settings
   *
   * TWO MODES:
   * - Light Build (no local PG): Simple "Server Address" field → connects to admin's FastAPI
   * - Admin Build (has PG): Shows internal PG config (managed by setup wizard)
   *
   * Option B architecture: Light Build frontend → Admin's FastAPI (port 8888) → PG
   */
  import {
    Modal,
    TextInput,
    RadioButtonGroup,
    RadioButton,
    Button,
    InlineNotification
  } from "carbon-components-svelte";
  import { IotConnect, Checkmark, WarningAlt, Close } from "carbon-icons-svelte";
  import { logger } from "$lib/utils/logger.js";
  import { api } from "$lib/api/client.js";
  import { serverUrl } from "$lib/stores/app.js";
  import { get } from "svelte/store";

  let { open = $bindable(false) } = $props();

  // Detect light mode (no local PG = user build)
  // Light mode = localStorage flag OR no local backend responding on localhost
  let isLightMode = $state(false);

  // === Light Mode State (LAN sync) ===
  let remoteAddress = $state("");
  let testingRemote = $state(false);
  let remoteTestResult = $state(null);
  let savingRemote = $state(false);
  let savedRemote = $state(false);
  let remoteError = $state(null);
  let hasRemoteConfig = $state(false);
  // LAN login (to fetch PG creds from Admin's server automatically)
  let lanUsername = $state("");
  let lanPassword = $state("");
  let connecting = $state(false);
  let remoteServerInfo = $state(null); // {version, server_mode, database_type}

  // === Admin Mode State (PG config) ===
  let mode = $state("auto");
  let serverHost = $state("localhost");
  let serverPort = $state("5432");
  let dbUser = $state("locanext_service");
  let dbPassword = $state("");
  let dbName = $state("localizationtools");
  let currentStatus = $state(null);
  let testing = $state(false);
  let testResult = $state(null);
  let saving = $state(false);
  let saved = $state(false);
  let error = $state(null);

  // Load config when modal opens
  $effect(() => {
    if (open) loadConfig();
  });

  async function loadConfig() {
    // Phase 111: Check Electron's remote-server.json (not localStorage which is now cleared)
    if (window.electronRemote) {
      try {
        const remoteConfig = await window.electronRemote.getRemoteServer();
        if (remoteConfig?.url) {
          hasRemoteConfig = true;
          remoteAddress = remoteConfig.url.replace(/^https?:\/\//, '').replace(/:8888\/?$/, '');
          // PG creds stored but not shown — auto-fetched during connect flow
        }
      } catch { /* no remote config */ }
    }
    // Legacy fallback: check localStorage
    const savedRemoteUrl = localStorage.getItem('locanext_remote_server');
    if (savedRemoteUrl && !hasRemoteConfig) {
      remoteAddress = savedRemoteUrl.replace(/^https?:\/\//, '').replace(/:8888\/?$/, '');
    }

    // Detection priority:
    // 1. Electron IPC (most reliable — reads light-mode.flag)
    // 2. Saved remote server URL (user already configured as light client)
    // 3. Health endpoint heuristic (fallback)
    if (window.electronRemote) {
      // Authoritative: Electron knows if light-mode.flag exists
      if (window.electronRemote.isLightMode) {
        isLightMode = true;
      }
    }

    // Heuristic fallback: check if local backend has PG (admin) or not
    if (!isLightMode && !savedRemoteUrl) {
      try {
        const healthRes = await fetch("http://localhost:8888/health", { signal: AbortSignal.timeout(2000) });
        if (healthRes.ok) {
          const health = await healthRes.json();
          // Admin build has PG — show admin UI. Light build has SQLite — show light UI.
          isLightMode = health.database_type === "sqlite" && health.server_mode === "standalone";
        } else {
          isLightMode = true;
        }
      } catch (e) {
        logger.info("Local backend not reachable — assuming light mode", { error: e?.message });
        isLightMode = true;
      }
    }

    // If saved remote URL exists, always light mode
    if (savedRemoteUrl) isLightMode = true;

    // Load admin config if in admin mode AND logged in (avoid 401 pre-login)
    // Also check token isn't an expired/OFFLINE token
    const storedToken = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
    const hasValidToken = storedToken && !storedToken.startsWith('OFFLINE_MODE_');
    if (!isLightMode && hasValidToken) {
      loadAdminConfig();
    }
  }

  // === Light Mode Functions ===

  async function testRemoteConnection() {
    testingRemote = true;
    remoteTestResult = null;
    remoteError = null;
    remoteServerInfo = null;

    const address = remoteAddress.trim();
    if (!address) {
      remoteTestResult = { success: false, message: "Enter a server address" };
      testingRemote = false;
      return;
    }

    const url = `http://${address}:8888/health`;

    try {
      const res = await fetch(url, { signal: AbortSignal.timeout(5000) });
      if (res.ok) {
        try {
          const data = await res.json();
          if (!data.version) {
            remoteTestResult = { success: false, message: "Server responded but doesn't appear to be LocaNext" };
          } else {
            remoteServerInfo = {
              version: data.version,
              server_mode: data.server_mode || "standalone",
              database_type: data.database_type || "unknown",
              status: data.status || "unknown",
            };
            remoteTestResult = {
              success: true,
              message: `Connected — LocaNext v${data.version}`,
            };
            logger.info("Remote server test passed", { address, version: data.version });
          }
        } catch {
          remoteTestResult = { success: false, message: "Server responded but returned invalid data — is this a LocaNext server?" };
        }
      } else {
        remoteTestResult = { success: false, message: `Server responded with HTTP ${res.status}` };
      }
    } catch (e) {
      remoteTestResult = {
        success: false,
        message: `Cannot reach ${address}:8888 — check the address and ensure the admin server is running`,
      };
    } finally {
      testingRemote = false;
    }
  }

  async function connectToServer() {
    const address = remoteAddress.trim();
    if (!address) { remoteError = "Enter a server address first"; return; }
    if (!lanUsername.trim() || !lanPassword.trim()) {
      remoteError = "Enter your username and password to connect";
      return;
    }

    const url = `http://${address}:8888`;
    connecting = true;
    remoteError = null;

    try {
      // 1. Login to Admin's server
      const loginRes = await fetch(`${url}/api/v2/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: lanUsername.trim(), password: lanPassword }),
        signal: AbortSignal.timeout(10000),
      });
      if (!loginRes.ok) {
        const err = await loginRes.json().catch(() => ({}));
        remoteError = err.detail || `Login failed (HTTP ${loginRes.status})`;
        return;
      }
      const loginData = await loginRes.json();
      const token = loginData.access_token;
      if (!token) { remoteError = "Login succeeded but no token received"; return; }

      // 2. Fetch PG credentials from Admin's server
      const credRes = await fetch(`${url}/api/server-config/lan-credentials`, {
        headers: { 'Authorization': `Bearer ${token}` },
        signal: AbortSignal.timeout(5000),
      });
      if (!credRes.ok) {
        const err = await credRes.json().catch(() => ({}));
        remoteError = err.detail || `Failed to get database credentials (HTTP ${credRes.status})`;
        return;
      }
      const creds = await credRes.json();

      // 3. Save full config (URL + PG creds) to remote-server.json
      if (window.electronRemote) {
        const result = await window.electronRemote.setRemoteServer(JSON.stringify({
          url,
          token,
          pg_host: creds.postgres_host,
          pg_port: creds.postgres_port,
          pg_user: creds.postgres_user,
          pg_password: creds.postgres_password,
          pg_db: creds.postgres_db,
        }));
        if (!result?.success) {
          remoteError = result?.error || "Failed to save config";
          return;
        }
      }

      hasRemoteConfig = true;
      savedRemote = true;
      logger.userAction("Connected to server -- restarting app", { url, user: lanUsername });

      // Auto-restart after 2s so user sees success message
      const restart = window.electronRemote?.restartApp;
      if (restart) {
        setTimeout(() => { try { restart(); } catch { /* app closing */ } }, 2000);
      }
    } catch (e) {
      remoteError = e.name === 'TimeoutError'
        ? `Cannot reach ${address}:8888 -- check the address`
        : `Connection failed: ${e.message}`;
      logger.error("LAN connect failed", e);
    } finally {
      connecting = false;
    }
  }

  async function disconnectRemote() {
    localStorage.removeItem('locanext_remote_server');

    try {
      if (window.electronRemote) {
        const result = await window.electronRemote.setRemoteServer(null);
        if (!result?.success) {
          remoteError = "Failed to remove config file";
          return;
        }
      }
    } catch (e) {
      remoteError = `Disconnect failed: ${e.message}`;
      return;
    }

    hasRemoteConfig = false;
    remoteAddress = "";
    lanPassword = "";
    remoteTestResult = null;
    remoteServerInfo = null;
    savedRemote = false;
    logger.userAction("LAN sync disconnected — restart app to use local mode");
  }

  // === Admin Mode Functions ===

  async function loadAdminConfig() {
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
      logger.warning("Failed to load server config", e);
    }

    try {
      const status = await api.request("/api/server-config/status");
      currentStatus = status;
    } catch (e) {
      logger.warning("Failed to load server status", e);
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
  size="md"
  onclose={handleClose}
>
  <div class="server-settings">

    {#if isLightMode}
      <!-- ============================================================ -->
      <!-- LIGHT BUILD MODE: Simple Server Address -->
      <!-- ============================================================ -->

      <div class="mode-badge light">User Mode</div>

      <!-- Current connection status -->
      {#if remoteServerInfo}
        <div class="status-banner online">
          <div class="status-icon"><Checkmark size={20} /></div>
          <div class="status-text">
            <strong>Connected</strong>
            <span>— LocaNext v{remoteServerInfo.version}</span>
            <div class="server-detail">{remoteServerInfo.database_type} | {remoteServerInfo.server_mode}</div>
          </div>
        </div>
      {:else if remoteAddress}
        <div class="status-banner offline">
          <div class="status-icon"><WarningAlt size={20} /></div>
          <div class="status-text">
            <strong>Not tested</strong>
            <span>— click Test Connection</span>
          </div>
        </div>
      {/if}

      <!-- Server Address input -->
      <div class="section">
        <h4>Server Address</h4>
        <p class="hint">Enter the admin server's IP address (ask your admin)</p>
        <div class="input-row">
          <TextInput
            bind:value={remoteAddress}
            placeholder="192.168.1.100"
            size="sm"
            on:keydown={(e) => { if (e.key === 'Enter') testRemoteConnection(); }}
            on:input={() => { remoteTestResult = null; }}
          />
        </div>

        <Button
          kind="secondary"
          size="small"
          icon={IotConnect}
          onclick={testRemoteConnection}
          disabled={testingRemote || !remoteAddress.trim()}
        >
          {testingRemote ? "Testing..." : "Test Connection"}
        </Button>
      </div>

      <!-- Test Result -->
      {#if remoteTestResult}
        <div class="section">
          {#if remoteTestResult.success}
            <InlineNotification
              kind="success"
              title="Server Found"
              subtitle={remoteTestResult.message}
              hideCloseButton
            />

            <!-- Login to fetch PG credentials automatically -->
            <div class="login-section">
              <h4>Login to Connect</h4>
              <p class="hint">Enter your LocaNext account (created by admin)</p>
              <TextInput
                bind:value={lanUsername}
                placeholder="Username"
                size="sm"
              />
              <TextInput
                bind:value={lanPassword}
                placeholder="Password"
                size="sm"
                type="password"
                on:keydown={(e) => { if (e.key === 'Enter') connectToServer(); }}
              />
              <div class="button-row" style="margin-top: 8px;">
                <Button
                  kind="primary"
                  size="small"
                  onclick={connectToServer}
                  disabled={connecting || !lanUsername.trim() || !lanPassword.trim()}
                >
                  {connecting ? "Connecting..." : "Connect & Sync"}
                </Button>
                {#if hasRemoteConfig}
                  <Button
                    kind="danger-tertiary"
                    size="small"
                    icon={Close}
                    onclick={disconnectRemote}
                  >
                    Disconnect
                  </Button>
                {/if}
              </div>
            </div>
          {:else}
            <InlineNotification
              kind="error"
              title="Connection Failed"
              subtitle={remoteTestResult.message}
              hideCloseButton
            />
          {/if}
        </div>
      {/if}

      {#if remoteError}
        <InlineNotification
          kind="error"
          title="Error"
          subtitle={remoteError}
          hideCloseButton
        />
      {/if}

      {#if savedRemote}
        <InlineNotification
          kind="success"
          title="Connected!"
          subtitle="Database credentials saved. Restart the app to sync with the server."
          hideCloseButton
        />
      {/if}

      <!-- remoteError already shown above -->

      <!-- Setup Guide -->
      <div class="info-section">
        <h4>How it works</h4>
        <ol>
          <li>Your admin runs LocaNext on the server PC</li>
          <li>Admin creates your account in the <strong>Admin Dashboard</strong></li>
          <li>Admin gives you the server IP address</li>
          <li>Enter it here, test, and save</li>
          <li>Log in with the credentials your admin created</li>
        </ol>
      </div>

    {:else}
      <!-- ============================================================ -->
      <!-- ADMIN BUILD MODE: Internal PG Config -->
      <!-- ============================================================ -->

      <div class="mode-badge admin">Admin Mode</div>

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
          <h4>PostgreSQL Server <span class="internal-badge">Internal</span></h4>
          <p class="hint">Managed automatically by the setup wizard. Change only if you know what you're doing.</p>
          <div class="input-row">
            <TextInput bind:value={serverHost} labelText="Host" placeholder="localhost" size="sm" />
            <TextInput bind:value={serverPort} labelText="Port" placeholder="5432" size="sm" style="max-width: 100px;" />
          </div>
          <div class="input-row">
            <TextInput bind:value={dbUser} labelText="Username" placeholder="locanext_service" size="sm" />
            <TextInput bind:value={dbPassword} labelText="Password" placeholder="Enter password" type="password" size="sm" />
          </div>
          <TextInput bind:value={dbName} labelText="Database Name" placeholder="localizationtools" size="sm" />

          <div class="button-row">
            <Button kind="secondary" size="small" icon={IotConnect} onclick={testConnection} disabled={testing || !localStorage.getItem('auth_token')}>
              {testing ? "Testing..." : "Test Connection"}
            </Button>
            <Button kind="primary" size="small" onclick={saveConfig} disabled={saving || !localStorage.getItem('auth_token')}>
              {saving ? "Saving..." : "Save & Restart Required"}
            </Button>
            {#if !localStorage.getItem('auth_token')}
              <p class="hint">Login first to manage server settings</p>
            {/if}
          </div>
        </div>
      {:else}
        <div class="section">
          <InlineNotification kind="info" title="Offline Mode" subtitle="All data stored locally. No server connection needed." hideCloseButton />
        </div>
      {/if}

      <!-- Test Result -->
      {#if testResult}
        <div class="section">
          {#if testResult.success}
            <InlineNotification kind="success" title="Connected!" subtitle="{testResult.message}{testResult.latency_ms ? ` (${testResult.latency_ms}ms)` : ''}" hideCloseButton />
            {#if testResult.pg_version}
              <div class="pg-version">{testResult.pg_version}</div>
            {/if}
          {:else}
            <InlineNotification kind="error" title="Connection Failed" subtitle={testResult.message} hideCloseButton />
          {/if}
        </div>
      {/if}

      {#if saved}
        <InlineNotification kind="success" title="Saved" subtitle="Configuration saved. Restart LocaNext to apply changes." hideCloseButton />
      {/if}

      {#if error}
        <InlineNotification kind="error" title="Error" subtitle={error} hideCloseButton />
      {/if}
    {/if}
  </div>
</Modal>

<style>
  .server-settings {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .mode-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 3px;
    font-size: 0.6875rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    width: fit-content;
  }

  .mode-badge.light {
    background: #4589ff;
    color: #161616;
  }

  .mode-badge.admin {
    background: #393939;
    color: #c6c6c6;
  }

  .internal-badge {
    font-size: 0.625rem;
    padding: 1px 6px;
    border-radius: 3px;
    background: var(--cds-layer-02);
    color: var(--cds-text-03);
    font-weight: 400;
    text-transform: uppercase;
    letter-spacing: 0.3px;
    vertical-align: middle;
    margin-left: 6px;
  }

  .hint {
    font-size: 0.75rem;
    color: var(--cds-text-03);
    margin: 0 0 0.5rem;
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

  .status-icon { flex-shrink: 0; }

  .status-text { font-size: 0.875rem; }
  .status-text strong { color: var(--cds-text-01); }

  .server-detail {
    font-size: 0.6875rem;
    color: var(--cds-text-03);
    margin-top: 2px;
    text-transform: uppercase;
    letter-spacing: 0.3px;
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
    flex-wrap: wrap;
  }

  .login-section {
    margin-top: 1rem;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
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
