<script>
  /**
   * Launcher.svelte - The Beautiful First Screen
   *
   * Industry Giant style launcher (League/Steam/Epic):
   * - Logo and version at top
   * - Server status indicator
   * - [Start Offline] and [Login] buttons
   * - Update panel at bottom (auto-downloads)
   */

  import { onMount, onDestroy } from 'svelte';
  import { get } from 'svelte/store';
  import { Button, InlineLoading, ProgressBar, TextInput, PasswordInput, Checkbox, InlineNotification } from 'carbon-components-svelte';
  import { CloudOffline, Login as LoginIcon, Checkmark, Close, Restart, Flash, CloudApp } from 'carbon-icons-svelte';
  import { logger } from '$lib/utils/logger.js';
  import { serverUrl, isAuthenticated, user } from '$lib/stores/app.js';
  import { api } from '$lib/api/client.js';
  import {
    launcherPhase,
    launcherMode,
    serverStatus,
    updateState,
    showLauncher,
    loginDisabled,
    updateInProgress,
    updateSavings,
    setReady,
    startOffline,
    startOnline,
    showLoginForm,
    hideLoginForm,
    skipUpdate,
    setUpdateProgress,
    setUpdateAvailable,
    setUpdateDownloading,
    setUpdateDownloaded,
    setUpdateError
  } from '$lib/stores/launcher.js';
  import { connectionMode } from '$lib/stores/sync.js';

  // API base URL
  const API_BASE = get(serverUrl);

  // Svelte 5: Local state
  let currentVersion = $state('');
  let showLogin = $state(false);

  // Login form state
  let username = $state('');
  let password = $state('');
  let rememberMe = $state(false);
  let loginError = $state('');
  let loginLoading = $state(false);

  // ═══════════════════════════════════════════════════════════════════
  // LIFECYCLE
  // ═══════════════════════════════════════════════════════════════════

  onMount(async () => {
    logger.info('Launcher: Mounted');

    // 1. Get current version
    await fetchVersion();

    // 2. Check server status
    await checkServerStatus();

    // 3. Check for updates (auto-download if available)
    await checkForUpdates();

    // 4. Load saved credentials
    loadSavedCredentials();

    // 5. Set ready
    setReady();

    // Register update event listeners
    if (typeof window !== 'undefined' && window.electronUpdate) {
      window.electronUpdate.onUpdateAvailable(handleUpdateAvailable);
      window.electronUpdate.onUpdateProgress(handleUpdateProgress);
      window.electronUpdate.onUpdateDownloaded(handleUpdateDownloaded);
      window.electronUpdate.onUpdateError(handleUpdateError);

      if (window.electronUpdate.onPatchProgress) {
        window.electronUpdate.onPatchProgress(handlePatchProgress);
      }
    }
  });

  onDestroy(() => {
    if (typeof window !== 'undefined' && window.electronUpdate) {
      window.electronUpdate.removeListeners();
    }
  });

  // ═══════════════════════════════════════════════════════════════════
  // SERVER STATUS
  // ═══════════════════════════════════════════════════════════════════

  async function fetchVersion() {
    try {
      const response = await fetch(`${API_BASE}/health`);
      if (response.ok) {
        const health = await response.json();
        currentVersion = health.version || '';
      }
    } catch (err) {
      logger.warning('Launcher: Could not fetch version', { error: err.message });
    }
  }

  async function checkServerStatus() {
    serverStatus.set('checking');

    try {
      const response = await fetch(`${API_BASE}/health`, { timeout: 5000 });
      if (response.ok) {
        serverStatus.set('connected');
        connectionMode.set('online');
        logger.info('Launcher: Server connected');
      } else {
        serverStatus.set('offline');
        connectionMode.set('offline');
      }
    } catch (err) {
      serverStatus.set('offline');
      connectionMode.set('offline');
      logger.info('Launcher: Server offline', { error: err.message });
    }
  }

  // ═══════════════════════════════════════════════════════════════════
  // UPDATE HANDLING
  // ═══════════════════════════════════════════════════════════════════

  async function checkForUpdates() {
    if (typeof window === 'undefined' || !window.electronUpdate) {
      return;
    }

    updateState.update(s => ({ ...s, checking: true }));

    try {
      // ALWAYS check for patch updates FIRST - this is the preferred method
      // Patch updates are faster and don't require NSIS reinstall
      if (window.electronUpdate.checkPatchUpdate) {
        const patchResult = await window.electronUpdate.checkPatchUpdate();
        logger.info('Launcher: Patch update check result', {
          success: patchResult.success,
          available: patchResult.available,
          reason: patchResult.reason
        });

        if (patchResult.success && patchResult.available) {
          setUpdateAvailable(
            { version: patchResult.version },
            patchResult
          );

          // Auto-download patch update
          logger.info('Launcher: Using PATCH update (no NSIS reinstall)');
          startDownload();
          return;
        }
      }

      // Only fall back to full update if patch is not available
      // Check for pending full updates
      const state = await window.electronUpdate.getUpdateState();

      if (state.hasUpdate) {
        logger.info('Launcher: Using FULL update (patch not available)');
        await handleExistingUpdate(state);
        return;
      }

      // Check for full updates
      const result = await window.electronUpdate.checkForUpdates();

      if (result.updateInfo) {
        logger.info('Launcher: Full update detected');
        setUpdateAvailable(result.updateInfo, null);

        // Auto-download full update
        logger.info('Launcher: Auto-downloading full update');
        startDownload();
      } else {
        updateState.update(s => ({ ...s, checking: false }));
      }
    } catch (err) {
      logger.warning('Launcher: Update check failed', { error: err.message });
      updateState.update(s => ({ ...s, checking: false }));
    }
  }

  async function handleExistingUpdate(state) {
    setUpdateAvailable(state.updateInfo, null);

    if (state.state === 'downloading') {
      setUpdateDownloading();
    } else if (state.state === 'downloaded') {
      setUpdateDownloaded();
    } else if (state.state === 'available') {
      // Auto-download
      startDownload();
    }
  }

  function startDownload() {
    setUpdateDownloading();

    const state = get(updateState);

    if (state.mode === 'patch' && state.patchComponents.length > 0) {
      // Use patch update
      window.electronUpdate.applyPatchUpdate(state.patchComponents)
        .then(result => {
          if (result.success) {
            setUpdateDownloaded();
          } else {
            // Fallback to full update
            logger.warning('Launcher: Patch failed, trying full update');
            window.electronUpdate.downloadUpdate();
          }
        })
        .catch(err => {
          setUpdateError(err);
        });
    } else {
      // Full update
      window.electronUpdate.downloadUpdate();
    }
  }

  function handleUpdateAvailable(info) {
    setUpdateAvailable(info, null);
    startDownload();
  }

  function handleUpdateProgress(progressObj) {
    setUpdateProgress({
      percent: progressObj.percent || 0,
      transferred: progressObj.transferred || 0,
      total: progressObj.total || 0,
      speed: progressObj.bytesPerSecond || 0
    });
  }

  function handlePatchProgress(progressObj) {
    setUpdateProgress({
      percent: progressObj.overallProgress || 0,
      transferred: progressObj.transferred || 0,
      total: progressObj.total || 0,
      speed: 0,
      currentComponent: progressObj.component || ''
    });
  }

  function handleUpdateDownloaded(info) {
    setUpdateDownloaded();
    logger.success('Launcher: Update downloaded');
  }

  function handleUpdateError(err) {
    setUpdateError(err);
    logger.error('Launcher: Update error', { error: err });
  }

  function handleRestartNow() {
    logger.userAction('Launcher: User clicked restart now');

    const state = get(updateState);

    if (state.mode === 'patch') {
      // PATCH update: Files already hot-swapped, just restart the app
      // NO NSIS installer needed!
      logger.info('Launcher: Patch update - restarting app (no NSIS)');
      window.electronUpdate?.restartApp();
    } else {
      // FULL update: Need NSIS installer to apply the update
      // Use silent mode to avoid wizard
      logger.info('Launcher: Full update - running silent NSIS installer');
      window.electronUpdate?.quitAndInstall();
    }
  }

  function handleSkipUpdate() {
    logger.userAction('Launcher: User skipped update');
    skipUpdate();
  }

  // ═══════════════════════════════════════════════════════════════════
  // LOGIN HANDLING
  // ═══════════════════════════════════════════════════════════════════

  function loadSavedCredentials() {
    if (typeof localStorage === 'undefined') return;

    const remember = localStorage.getItem('locanext_remember');
    if (remember === 'true') {
      try {
        const creds = localStorage.getItem('locanext_creds');
        if (creds) {
          const decoded = JSON.parse(atob(creds));
          username = decoded.username || '';
          password = decoded.password || '';
          rememberMe = true;
        }
      } catch (err) {
        logger.warning('Launcher: Failed to load saved credentials');
      }
    }
  }

  function saveCredentials() {
    if (typeof localStorage === 'undefined') return;

    if (rememberMe && username && password) {
      localStorage.setItem('locanext_remember', 'true');
      localStorage.setItem('locanext_creds', btoa(JSON.stringify({ username, password })));
    } else {
      localStorage.removeItem('locanext_remember');
      localStorage.removeItem('locanext_creds');
    }
  }

  async function handleLogin() {
    loginError = '';
    loginLoading = true;

    try {
      await api.login(username, password);

      saveCredentials();

      logger.success('Launcher: Login successful');
      startOnline();
    } catch (err) {
      loginError = err.message || 'Login failed';
      logger.error('Launcher: Login failed', { error: err.message });
    } finally {
      loginLoading = false;
    }
  }

  function handleLoginClick() {
    showLogin = true;
    showLoginForm();
  }

  function handleBackClick() {
    showLogin = false;
    loginError = '';
    hideLoginForm();
  }

  // ═══════════════════════════════════════════════════════════════════
  // OFFLINE MODE
  // ═══════════════════════════════════════════════════════════════════

  async function handleStartOffline() {
    logger.userAction('Launcher: User clicked Start Offline');

    try {
      // Set offline mode in stores
      connectionMode.set('offline');

      // Create offline session
      if (api.startOfflineMode) {
        await api.startOfflineMode();
      } else {
        // Fallback: create local session manually
        user.set({
          user_id: 'OFFLINE',
          username: 'Offline User',
          role: 'admin',
          email: 'offline@localhost'
        });
        isAuthenticated.set(true);
      }

      startOffline();
      logger.success('Launcher: Started offline mode');
    } catch (err) {
      logger.error('Launcher: Failed to start offline mode', { error: err.message });
    }
  }

  // ═══════════════════════════════════════════════════════════════════
  // HELPERS
  // ═══════════════════════════════════════════════════════════════════

  function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  }

  function formatSpeed(bytesPerSecond) {
    return formatBytes(bytesPerSecond) + '/s';
  }
</script>

<div class="launcher">
  <!-- Background gradient -->
  <div class="launcher-bg"></div>

  <!-- Main content -->
  <div class="launcher-content">
    <!-- Logo and version -->
    <div class="launcher-header">
      <div class="logo">
        <span class="logo-text">LocaNext</span>
      </div>
      <p class="version">Professional Localization Platform</p>
      {#if currentVersion}
        <p class="version-number">v{currentVersion}</p>
      {/if}
    </div>

    <!-- Server status -->
    <div class="server-status" class:connected={$serverStatus === 'connected'} class:offline={$serverStatus === 'offline'}>
      {#if $serverStatus === 'checking'}
        <InlineLoading description="Checking server..." />
      {:else if $serverStatus === 'connected'}
        <span class="status-dot connected"></span>
        <span>Central Server Connected</span>
      {:else}
        <span class="status-dot offline"></span>
        <span>Central Server Offline</span>
      {/if}
    </div>

    <!-- Main buttons OR Login form -->
    {#if showLogin}
      <!-- Login Form -->
      <div class="login-form">
        <h3>Login to Central Server</h3>

        {#if loginError}
          <InlineNotification
            kind="error"
            title="Login failed"
            subtitle={loginError}
            hideCloseButton
          />
        {/if}

        <TextInput
          bind:value={username}
          labelText="Username"
          placeholder="Enter username"
          disabled={loginLoading}
        />

        <PasswordInput
          bind:value={password}
          labelText="Password"
          placeholder="Enter password"
          disabled={loginLoading}
          on:keydown={(e) => e.key === 'Enter' && handleLogin()}
        />

        <Checkbox
          bind:checked={rememberMe}
          labelText="Remember me"
          disabled={loginLoading}
        />

        <div class="login-buttons">
          <Button kind="secondary" on:click={handleBackClick} disabled={loginLoading}>
            Back
          </Button>
          <Button kind="primary" on:click={handleLogin} disabled={loginLoading || !username || !password}>
            {#if loginLoading}
              <InlineLoading description="Logging in..." />
            {:else}
              Login
            {/if}
          </Button>
        </div>
      </div>
    {:else}
      <!-- Main Buttons -->
      <div class="launcher-buttons">
        <button class="launcher-btn offline-btn" on:click={handleStartOffline}>
          <CloudOffline size={32} />
          <span class="btn-title">Start Offline</span>
          <span class="btn-subtitle">No account needed</span>
        </button>

        <button
          class="launcher-btn login-btn"
          on:click={handleLoginClick}
          disabled={$serverStatus !== 'connected'}
        >
          <LoginIcon size={32} />
          <span class="btn-title">Login</span>
          <span class="btn-subtitle">Connect to server</span>
        </button>
      </div>
    {/if}
  </div>

  <!-- Update Panel (bottom) -->
  {#if $updateState.available || $updateState.downloading || $updateState.downloaded}
    <div class="update-panel">
      {#if $updateState.downloaded}
        <!-- Downloaded state -->
        <div class="update-header">
          <Checkmark size={20} />
          <span class="update-title">Update Ready: v{$updateState.info?.version}</span>
          {#if $updateState.mode === 'patch'}
            <span class="savings-badge">Saved {formatBytes($updateState.fullInstallerSize - $updateState.patchTotalSize)}</span>
          {/if}
        </div>
        <div class="update-actions">
          <Button kind="ghost" size="small" on:click={handleSkipUpdate}>
            Later
          </Button>
          <Button kind="primary" size="small" on:click={handleRestartNow}>
            <Restart size={16} />
            Restart Now
          </Button>
        </div>
      {:else if $updateState.downloading}
        <!-- Downloading state -->
        <div class="update-header">
          <Flash size={20} />
          <span class="update-title">
            {$updateState.mode === 'patch' ? 'Smart Update' : 'Downloading Update'}
            {#if $updateState.info?.version}
              : v{$updateState.info.version}
            {/if}
          </span>
          {#if $updateState.mode === 'patch'}
            <span class="savings-badge">{$updateSavings}% smaller</span>
          {/if}
        </div>

        <div class="progress-section">
          <ProgressBar value={$updateState.progress.percent} />
          <div class="progress-details">
            <span class="progress-file">
              {#if $updateState.progress.currentComponent}
                {$updateState.progress.currentComponent}
              {:else}
                Downloading...
              {/if}
            </span>
            <span class="progress-stats">
              {formatBytes($updateState.progress.transferred)} / {formatBytes($updateState.progress.total)}
              {#if $updateState.progress.speed > 0}
                • {formatSpeed($updateState.progress.speed)}
              {/if}
            </span>
          </div>
        </div>

        <div class="update-actions">
          <Button kind="ghost" size="small" on:click={handleSkipUpdate}>
            Skip
          </Button>
        </div>
      {:else if $updateState.available && !$updateState.skipped}
        <!-- Available state (shouldn't show long due to auto-download) -->
        <div class="update-header">
          <Flash size={20} />
          <span class="update-title">Update Available: v{$updateState.info?.version}</span>
        </div>
      {/if}
    </div>
  {/if}
</div>

<style>
  .launcher {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    overflow: hidden;
  }

  .launcher-bg {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: linear-gradient(135deg, #0f0f0f 0%, #1a1a2e 50%, #16213e 100%);
    z-index: -1;
  }

  .launcher-content {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2rem;
    padding: 2rem;
    max-width: 480px;
    width: 100%;
  }

  /* Header */
  .launcher-header {
    text-align: center;
  }

  .logo {
    margin-bottom: 0.5rem;
  }

  .logo-text {
    font-size: 3rem;
    font-weight: 700;
    background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: -0.02em;
  }

  .version {
    margin: 0;
    font-size: 1rem;
    color: var(--cds-text-02, #c6c6c6);
  }

  .version-number {
    margin: 0.25rem 0 0;
    font-size: 0.875rem;
    color: var(--cds-text-03, #8d8d8d);
    font-family: 'IBM Plex Mono', monospace;
  }

  /* Server status */
  .server-status {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.75rem 1.5rem;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    font-size: 0.875rem;
    color: var(--cds-text-02);
  }

  .server-status.connected {
    border-color: rgba(36, 161, 72, 0.3);
    background: rgba(36, 161, 72, 0.1);
  }

  .server-status.offline {
    border-color: rgba(218, 30, 40, 0.3);
    background: rgba(218, 30, 40, 0.1);
  }

  .status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
  }

  .status-dot.connected {
    background: #24a148;
    box-shadow: 0 0 8px #24a148;
  }

  .status-dot.offline {
    background: #da1e28;
    box-shadow: 0 0 8px #da1e28;
  }

  /* Buttons */
  .launcher-buttons {
    display: flex;
    gap: 1.5rem;
    margin-top: 1rem;
  }

  .launcher-btn {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.5rem;
    padding: 2rem 2.5rem;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    cursor: pointer;
    transition: all 0.2s ease;
    color: var(--cds-text-01, #f4f4f4);
    min-width: 160px;
  }

  .launcher-btn:hover:not(:disabled) {
    background: rgba(255, 255, 255, 0.1);
    border-color: rgba(255, 255, 255, 0.2);
    transform: translateY(-2px);
  }

  .launcher-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .launcher-btn :global(svg) {
    color: #4facfe;
  }

  .offline-btn:hover:not(:disabled) {
    border-color: rgba(79, 172, 254, 0.5);
  }

  .login-btn:hover:not(:disabled) {
    border-color: rgba(0, 242, 254, 0.5);
  }

  .btn-title {
    font-size: 1.125rem;
    font-weight: 600;
  }

  .btn-subtitle {
    font-size: 0.75rem;
    color: var(--cds-text-03, #8d8d8d);
  }

  /* Login form */
  .login-form {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    width: 100%;
    max-width: 320px;
    padding: 1.5rem;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
  }

  .login-form h3 {
    margin: 0 0 0.5rem;
    font-size: 1.125rem;
    font-weight: 600;
    color: var(--cds-text-01);
    text-align: center;
  }

  .login-buttons {
    display: flex;
    gap: 1rem;
    justify-content: flex-end;
    margin-top: 0.5rem;
  }

  /* Update panel */
  .update-panel {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    padding: 1rem 2rem;
    background: linear-gradient(180deg, rgba(22, 33, 62, 0.95) 0%, rgba(26, 26, 46, 0.98) 100%);
    border-top: 1px solid rgba(79, 172, 254, 0.3);
    backdrop-filter: blur(10px);
  }

  .update-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.75rem;
  }

  .update-header :global(svg) {
    color: #4facfe;
  }

  .update-title {
    font-weight: 600;
    color: var(--cds-text-01);
  }

  .savings-badge {
    margin-left: auto;
    padding: 0.25rem 0.5rem;
    background: rgba(0, 242, 254, 0.2);
    border-radius: 4px;
    font-size: 0.75rem;
    color: #00f2fe;
    font-weight: 500;
  }

  .progress-section {
    margin-bottom: 0.75rem;
  }

  .progress-details {
    display: flex;
    justify-content: space-between;
    margin-top: 0.5rem;
    font-size: 0.75rem;
    color: var(--cds-text-02);
  }

  .progress-file {
    font-family: 'IBM Plex Mono', monospace;
  }

  .update-actions {
    display: flex;
    justify-content: flex-end;
    gap: 0.5rem;
  }

  /* Carbon overrides for dark theme */
  :global(.bx--text-input),
  :global(.bx--password-input) {
    background-color: rgba(255, 255, 255, 0.05) !important;
    border-bottom-color: rgba(255, 255, 255, 0.2) !important;
  }

  :global(.bx--label) {
    color: var(--cds-text-02) !important;
  }

  :global(.bx--progress-bar__bar) {
    background: linear-gradient(90deg, #4facfe 0%, #00f2fe 100%) !important;
  }

  :global(.bx--inline-notification) {
    margin-bottom: 1rem;
  }
</style>
