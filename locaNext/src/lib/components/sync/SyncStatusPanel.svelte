<script>
  /**
   * SyncStatusPanel.svelte - P3 Offline/Online Mode
   *
   * Mode indicator shown in the top-right of the app bar.
   * Click to open sync dashboard modal.
   *
   * States:
   * - 🟢 Online: Connected to server
   * - 🔴 Offline: Working locally
   * - 🟡 Syncing: Sync in progress
   * - 🟠 Pending: Has local changes
   */
  import { onMount } from 'svelte';
  import { Modal, Button, ProgressBar, Tag, TextInput, PasswordInput, Checkbox, InlineNotification } from 'carbon-components-svelte';
  import { Cloud, CloudOffline, Renew, Warning, TrashCan, Folder, Document, Application, Login } from 'carbon-icons-svelte';
  import { Upload } from 'carbon-icons-svelte';
  import {
    connectionMode,
    displayStatus,
    statusLabel,
    pendingChanges,
    lastSync,
    isSyncing,
    connectionError,
    offlineAvailable,
    tryReconnect,
    goOffline,
    getSubscriptions,
    unsubscribeFromOffline,
    manualSync,
    syncFileToServer
  } from '$lib/stores/sync.js';
  import { launcherMode, startOnline } from '$lib/stores/launcher.js';
  import { offlineMode } from '$lib/stores/app.js';
  import { api } from '$lib/api/client.js';
  import { logger } from '$lib/utils/logger.js';

  // Dashboard modal state
  let showDashboard = $state(false);
  let reconnecting = $state(false);
  let subscriptions = $state([]);
  let loadingSubscriptions = $state(false);
  let deletingIds = $state(new Set());  // Track items being deleted (prevents flicker)

  // P9: Switch to Online - Login form state
  let showLoginForm = $state(false);
  let loginUsername = $state('');
  let loginPassword = $state('');
  let loginRememberMe = $state(false);
  let loginError = $state('');
  let loginLoading = $state(false);

  // P9: Check if we started in offline mode (from launcher)
  let isLauncherOffline = $derived($launcherMode === 'offline');

  // Get icon component based on status
  function getStatusIcon(status) {
    switch (status) {
      case 'online': return Cloud;
      case 'offline': return CloudOffline;
      case 'syncing': return Renew;
      case 'pending': return Warning;
      default: return Cloud;
    }
  }

  // Get status color
  function getStatusColor(status) {
    switch (status) {
      case 'online': return 'var(--cds-support-success)';
      case 'offline': return 'var(--cds-support-error)';
      case 'syncing': return 'var(--cds-support-warning)';
      case 'pending': return 'var(--cds-support-warning)';
      default: return 'var(--cds-text-02)';
    }
  }

  // Get entity icon
  function getEntityIcon(type) {
    switch (type) {
      case 'platform': return Application;
      case 'project': return Folder;
      case 'file': return Document;
      default: return Document;
    }
  }

  // Handle reconnect attempt
  async function handleReconnect() {
    reconnecting = true;
    try {
      await tryReconnect();
      // Reload subscriptions after reconnect
      await loadSubscriptions();
    } catch (e) {
      console.error('Reconnect failed:', e);
    } finally {
      // ALWAYS reset reconnecting state
      reconnecting = false;
    }
  }

  // P9: Switch to Online Mode - Show login form
  function handleSwitchToOnline() {
    showLoginForm = true;
    loginError = '';
  }

  // P9: Cancel login form
  function handleCancelLogin() {
    showLoginForm = false;
    loginError = '';
    loginUsername = '';
    loginPassword = '';
  }

  // P9: Handle login for switching to online mode
  async function handleLoginForOnline() {
    loginError = '';
    loginLoading = true;

    try {
      // Authenticate with server
      await api.login(loginUsername, loginPassword);

      // Save credentials if remember me
      if (loginRememberMe && typeof localStorage !== 'undefined') {
        localStorage.setItem('locanext_remember', 'true');
        localStorage.setItem('locanext_creds', btoa(JSON.stringify({
          username: loginUsername,
          password: loginPassword
        })));
      }

      logger.success('SyncPanel: Switched to online mode');

      // Switch to online mode
      connectionMode.set('online');
      offlineMode.set(false);  // P9: Clear offline mode flag
      startOnline();

      // Reset form and close
      showLoginForm = false;
      loginUsername = '';
      loginPassword = '';

      // Reload subscriptions
      await loadSubscriptions();
    } catch (err) {
      loginError = err.message || 'Login failed';
      logger.error('SyncPanel: Login failed', { error: err.message });
    } finally {
      loginLoading = false;
    }
  }

  // Handle manual sync
  async function handleSync() {
    await manualSync();
    await loadSubscriptions();
  }

  // Handle push changes to server (P3 Phase 3)
  let pushing = $state(false);
  async function handlePushChanges() {
    pushing = true;
    try {
      // Push changes for all subscribed files
      for (const sub of subscriptions) {
        if (sub.entity_type === 'file') {
          await syncFileToServer(sub.entity_id);
        }
      }
      await loadSubscriptions();
    } catch (e) {
      console.error('Push failed:', e);
    } finally {
      pushing = false;
    }
  }

  // Load subscriptions
  async function loadSubscriptions() {
    loadingSubscriptions = true;
    try {
      subscriptions = await getSubscriptions();
    } catch (e) {
      subscriptions = [];
    } finally {
      loadingSubscriptions = false;
    }
  }

  // Open dashboard and load subscriptions
  async function openDashboard() {
    showDashboard = true;
    await loadSubscriptions();
  }

  // Remove subscription - Svelte 5 proper pattern
  // Uses deletingIds to hide item immediately and prevent flicker on re-render
  async function removeSubscription(sub) {
    // 1. Mark as deleting IMMEDIATELY (hides from UI via derived filter)
    deletingIds = new Set([...deletingIds, sub.id]);

    // 2. Call server
    try {
      await unsubscribeFromOffline(sub.entity_type, sub.entity_id);
      // 3. Success - remove from actual array using Svelte 5 splice
      const index = subscriptions.findIndex(s => s.id === sub.id);
      if (index !== -1) {
        subscriptions.splice(index, 1);
      }
    } catch (e) {
      // Server failed - show the item again by removing from deletingIds
      console.error('Unsubscribe failed:', e);
    } finally {
      // Clean up deletingIds
      const newSet = new Set(deletingIds);
      newSet.delete(sub.id);
      deletingIds = newSet;
    }
  }

  // Derived: visible subscriptions (excludes items being deleted)
  let visibleSubscriptions = $derived(
    subscriptions.filter(s => !deletingIds.has(s.id))
  );

  // Format last sync time
  function formatLastSync(timestamp) {
    if (!timestamp) return 'Never';
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;

    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)} min ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)} hours ago`;
    return date.toLocaleDateString();
  }

  // Reactive values
  let StatusIcon = $derived(getStatusIcon($displayStatus));
  let statusColor = $derived(getStatusColor($displayStatus));
</script>

<!-- Mode Indicator Button -->
<button
  class="sync-status-button"
  class:syncing={$displayStatus === 'syncing'}
  class:online={$displayStatus === 'online'}
  class:offline={$displayStatus === 'offline'}
  class:launcher-offline={isLauncherOffline}
  style="--status-color: {statusColor}"
  onclick={openDashboard}
  title={isLauncherOffline ? "Click to switch to Online mode" : "Click to open Sync Dashboard"}
>
  <span class="status-dot" class:online={$displayStatus === 'online'} class:offline={$displayStatus === 'offline'}></span>
  <span class="status-icon">
    <svelte:component this={StatusIcon} size={16} />
  </span>
  <span class="status-label">{$statusLabel}</span>
  {#if isLauncherOffline}
    <span class="go-online-hint">Click to Go Online</span>
  {:else if $pendingChanges > 0}
    <span class="pending-badge">{$pendingChanges}</span>
  {/if}
</button>

<!-- Sync Dashboard Modal -->
<Modal
  bind:open={showDashboard}
  modalHeading="Sync Dashboard"
  passiveModal
  size="lg"
>
  <div class="dashboard-content">
    <!-- Connection Status -->
    <div class="status-section" class:online={$displayStatus === 'online'} class:offline={$displayStatus === 'offline'}>
      <div class="status-header">
        <div class="status-indicator" class:online={$displayStatus === 'online'} class:offline={$displayStatus === 'offline'}></div>
        <span class="status-text" class:online={$displayStatus === 'online'} class:offline={$displayStatus === 'offline'}>{$statusLabel}</span>
      </div>

      {#if $connectionError && $connectionMode === 'offline'}
        <p class="error-message">{$connectionError}</p>
      {/if}
    </div>

    <!-- Stats Grid -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-label">Last Sync</div>
        <div class="stat-value">{formatLastSync($lastSync)}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Pending Changes</div>
        <div class="stat-value" class:has-pending={$pendingChanges > 0}>
          {$pendingChanges}
        </div>
      </div>
    </div>

    <!-- Synced for Offline Section -->
    <div class="subscriptions-section">
      <div class="section-header">
        <span class="section-title">Synced for Offline</span>
        <span class="section-count">{visibleSubscriptions.length}</span>
      </div>

      {#if loadingSubscriptions}
        <div class="loading-text">Loading...</div>
      {:else if visibleSubscriptions.length === 0}
        <div class="empty-text">
          No items synced for offline.
          Right-click any file, project, or platform to enable offline sync.
        </div>
      {:else}
        <div class="subscriptions-list">
          <!-- Svelte 5: Use key (sub.id) for proper DOM diffing -->
          {#each visibleSubscriptions as sub (sub.id)}
            <div class="subscription-item">
              <span class="sub-icon">
                <svelte:component this={getEntityIcon(sub.entity_type)} size={16} />
              </span>
              <div class="sub-info">
                <span class="sub-name">{sub.entity_name}</span>
                <span class="sub-type">{sub.entity_type}</span>
              </div>
              <span class="sub-status" class:synced={sub.sync_status === 'synced'}>
                {sub.sync_status === 'synced' ? '✓' : sub.sync_status}
              </span>
              <button
                class="sub-remove"
                onclick={() => removeSubscription(sub)}
                title="Remove from offline sync"
              >
                <TrashCan size={14} />
              </button>
            </div>
          {/each}
        </div>
      {/if}
    </div>

    <!-- P9: Login Form Overlay (for switching offline → online) -->
    {#if showLoginForm}
      <div class="login-overlay">
        <div class="login-form-card">
          <h3 class="login-title">Switch to Online Mode</h3>
          <p class="login-subtitle">Login to connect to central server</p>

          {#if loginError}
            <InlineNotification
              kind="error"
              title="Login failed"
              subtitle={loginError}
              hideCloseButton
            />
          {/if}

          <div class="login-fields">
            <TextInput
              bind:value={loginUsername}
              labelText="Username"
              placeholder="Enter username"
              disabled={loginLoading}
            />

            <PasswordInput
              bind:value={loginPassword}
              labelText="Password"
              placeholder="Enter password"
              disabled={loginLoading}
              onkeydown={(e) => e.key === 'Enter' && handleLoginForOnline()}
            />

            <Checkbox
              bind:checked={loginRememberMe}
              labelText="Remember me"
              disabled={loginLoading}
            />
          </div>

          <div class="login-actions">
            <Button kind="secondary" size="small" onclick={handleCancelLogin} disabled={loginLoading}>
              Cancel
            </Button>
            <Button
              kind="primary"
              size="small"
              icon={Login}
              onclick={handleLoginForOnline}
              disabled={loginLoading || !loginUsername || !loginPassword}
            >
              {loginLoading ? 'Connecting...' : 'Connect'}
            </Button>
          </div>
        </div>
      </div>
    {:else}
      <!-- Actions -->
      <div class="actions-section">
        {#if $connectionMode === 'offline'}
          {#if isLauncherOffline}
            <!-- P9: Started in offline mode - show Switch to Online -->
            <Button
              kind="primary"
              size="small"
              icon={Login}
              onclick={handleSwitchToOnline}
            >
              Switch to Online
            </Button>
          {:else}
            <!-- Regular offline - just try reconnect -->
            <Button
              kind="primary"
              size="small"
              icon={Cloud}
              disabled={reconnecting}
              onclick={handleReconnect}
            >
              {reconnecting ? 'Connecting...' : 'Try Reconnect'}
            </Button>
          {/if}
        {:else}
          <Button
            kind="primary"
            size="small"
            icon={Renew}
            disabled={$isSyncing || visibleSubscriptions.length === 0}
            onclick={handleSync}
          >
            {$isSyncing ? 'Syncing...' : 'Sync Now'}
          </Button>
          {#if $pendingChanges > 0}
            <Button
              kind="danger"
              size="small"
              icon={Upload}
              disabled={pushing || $isSyncing}
              onclick={handlePushChanges}
            >
              {pushing ? 'Pushing...' : `Push ${$pendingChanges} Changes`}
            </Button>
          {/if}
          <Button
            kind="secondary"
            size="small"
            icon={CloudOffline}
            onclick={goOffline}
          >
            Go Offline
          </Button>
        {/if}
      </div>
    {/if}

    <!-- Offline Info -->
    {#if $connectionMode === 'offline'}
      <div class="info-section">
        <Tag type="blue">Offline Mode</Tag>
        <p class="info-text">
          You can view and edit synced files.
          Changes will sync when you reconnect.
        </p>
      </div>
    {/if}

    <!-- Syncing Progress -->
    {#if $isSyncing}
      <div class="sync-progress">
        <ProgressBar />
        <p class="sync-text">Syncing changes...</p>
      </div>
    {/if}
  </div>
</Modal>

<style>
  .sync-status-button {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 1rem;
    background: transparent;
    border: 1px solid var(--cds-border-subtle-01);
    border-radius: 6px;
    cursor: pointer;
    font-size: 0.875rem;
    color: var(--cds-text-01);
    transition: all 0.15s ease;
  }

  .sync-status-button:hover {
    background: var(--cds-layer-hover-01);
    border-color: var(--cds-border-strong-01);
  }

  .sync-status-button.syncing {
    animation: pulse 1.5s ease-in-out infinite;
  }

  /* PROMINENT ONLINE STYLING - Green glow effect */
  .sync-status-button.online {
    border-color: #24a148;
    background: rgba(36, 161, 72, 0.08);
  }

  .sync-status-button.online:hover {
    background: rgba(36, 161, 72, 0.15);
  }

  .sync-status-button.offline {
    border-color: #da1e28;
    background: rgba(218, 30, 40, 0.08);
  }

  /* P9: Enhanced offline button when started from launcher - more inviting */
  .sync-status-button.launcher-offline {
    border-color: #0f62fe;
    background: rgba(15, 98, 254, 0.1);
    animation: pulse-invite 2s ease-in-out infinite;
  }

  .sync-status-button.launcher-offline:hover {
    background: rgba(15, 98, 254, 0.2);
    border-color: #0043ce;
  }

  @keyframes pulse-invite {
    0%, 100% { box-shadow: 0 0 0 0 rgba(15, 98, 254, 0.4); }
    50% { box-shadow: 0 0 0 4px rgba(15, 98, 254, 0); }
  }

  .go-online-hint {
    font-size: 0.7rem;
    color: #0f62fe;
    font-weight: 500;
    padding: 0.125rem 0.5rem;
    background: rgba(15, 98, 254, 0.15);
    border-radius: 8px;
    white-space: nowrap;
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.6; }
  }

  @keyframes glow {
    0%, 100% { box-shadow: 0 0 4px #24a148, 0 0 8px #24a148; }
    50% { box-shadow: 0 0 8px #24a148, 0 0 16px #24a148; }
  }

  /* Glowing status dot */
  .status-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: var(--cds-text-02);
    flex-shrink: 0;
  }

  .status-dot.online {
    background: #24a148;
    box-shadow: 0 0 6px #24a148, 0 0 12px #24a148;
    animation: glow 2s ease-in-out infinite;
  }

  .status-dot.offline {
    background: #da1e28;
    box-shadow: 0 0 4px #da1e28;
  }

  .status-icon {
    display: flex;
    align-items: center;
    color: var(--status-color);
  }

  .status-label {
    font-weight: 600;
    letter-spacing: 0.01em;
  }

  .pending-badge {
    display: flex;
    align-items: center;
    justify-content: center;
    min-width: 20px;
    height: 20px;
    padding: 0 6px;
    background: var(--cds-support-warning);
    border-radius: 10px;
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--cds-text-inverse);
  }

  /* Dashboard styles - SPACIOUS and EXPLORER-STYLE */
  .dashboard-content {
    display: flex;
    flex-direction: column;
    gap: 2rem;
    padding: 0.5rem;
  }

  .status-section {
    text-align: center;
    padding: 1.5rem 2rem;
    background: var(--cds-layer-02);
    border-radius: 12px;
  }

  .status-header {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.75rem;
  }

  .status-indicator {
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: var(--cds-text-02);
  }

  .status-indicator.online {
    background: #24a148;
    box-shadow: 0 0 8px #24a148, 0 0 16px #24a148, 0 0 24px rgba(36, 161, 72, 0.5);
    animation: glow-modal 2s ease-in-out infinite;
  }

  .status-indicator.offline {
    background: #da1e28;
    box-shadow: 0 0 6px #da1e28;
  }

  @keyframes glow-modal {
    0%, 100% { box-shadow: 0 0 8px #24a148, 0 0 16px #24a148; }
    50% { box-shadow: 0 0 12px #24a148, 0 0 24px #24a148, 0 0 32px rgba(36, 161, 72, 0.4); }
  }

  .status-text {
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--cds-text-01);
    letter-spacing: 0.02em;
  }

  .status-text.online {
    color: #24a148;
    text-shadow: 0 0 10px rgba(36, 161, 72, 0.3);
  }

  .status-text.offline {
    color: #da1e28;
  }

  .status-section.online {
    background: rgba(36, 161, 72, 0.08);
    border: 1px solid rgba(36, 161, 72, 0.3);
  }

  .status-section.offline {
    background: rgba(218, 30, 40, 0.08);
    border: 1px solid rgba(218, 30, 40, 0.3);
  }

  .error-message {
    margin-top: 0.75rem;
    font-size: 0.9rem;
    color: var(--cds-support-error);
  }

  .stats-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 1.25rem;
  }

  .stat-card {
    padding: 1.25rem 1.5rem;
    background: var(--cds-layer-02);
    border-radius: 12px;
    text-align: center;
    border: 1px solid var(--cds-border-subtle-01);
  }

  .stat-label {
    font-size: 0.875rem;
    color: var(--cds-text-02);
    margin-bottom: 0.5rem;
    font-weight: 500;
  }

  .stat-value {
    font-size: 2rem;
    font-weight: 700;
    color: var(--cds-text-01);
  }

  .stat-value.has-pending {
    color: var(--cds-support-warning);
  }

  /* Subscriptions section - EXPLORER STYLE */
  .subscriptions-section {
    background: var(--cds-layer-02);
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
    border: 1px solid var(--cds-border-subtle-01);
  }

  .section-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 1rem;
    padding-bottom: 0.75rem;
    border-bottom: 1px solid var(--cds-border-subtle-01);
  }

  .section-title {
    font-size: 1rem;
    font-weight: 600;
    color: var(--cds-text-01);
    letter-spacing: 0.01em;
  }

  .section-count {
    font-size: 0.875rem;
    font-weight: 600;
    color: #24a148;
    background: rgba(36, 161, 72, 0.15);
    padding: 0.25rem 0.75rem;
    border-radius: 12px;
  }

  .loading-text, .empty-text {
    font-size: 0.9rem;
    color: var(--cds-text-02);
    text-align: center;
    padding: 2rem 1rem;
    line-height: 1.5;
  }

  .subscriptions-list {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    max-height: 320px;
    overflow-y: auto;
    padding-right: 0.5rem;
  }

  /* Custom scrollbar for list */
  .subscriptions-list::-webkit-scrollbar {
    width: 6px;
  }

  .subscriptions-list::-webkit-scrollbar-track {
    background: var(--cds-layer-01);
    border-radius: 3px;
  }

  .subscriptions-list::-webkit-scrollbar-thumb {
    background: var(--cds-border-strong-01);
    border-radius: 3px;
  }

  /* EXPLORER-STYLE ITEM - larger, more visual */
  .subscription-item {
    display: flex;
    align-items: center;
    gap: 0.875rem;
    padding: 0.875rem 1rem;
    background: var(--cds-layer-01);
    border-radius: 8px;
    border: 1px solid transparent;
    transition: all 0.15s ease;
  }

  .subscription-item:hover {
    border-color: var(--cds-border-strong-01);
    background: var(--cds-layer-hover-01);
  }

  .sub-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 36px;
    background: var(--cds-layer-02);
    border-radius: 8px;
    color: var(--cds-icon-02);
  }

  .sub-info {
    flex: 1;
    min-width: 0;
  }

  .sub-name {
    display: block;
    font-size: 0.9rem;
    font-weight: 500;
    color: var(--cds-text-01);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    margin-bottom: 0.125rem;
  }

  .sub-type {
    font-size: 0.75rem;
    color: var(--cds-text-02);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-weight: 500;
  }

  .sub-status {
    font-size: 0.75rem;
    color: var(--cds-text-02);
    padding: 0.25rem 0.5rem;
    background: var(--cds-layer-02);
    border-radius: 4px;
  }

  .sub-status.synced {
    color: #24a148;
    background: rgba(36, 161, 72, 0.15);
    font-weight: 500;
  }

  .sub-remove {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    background: transparent;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    color: var(--cds-text-02);
    transition: all 0.15s;
  }

  .sub-remove:hover {
    background: var(--cds-support-error);
    color: white;
  }

  .actions-section {
    display: flex;
    justify-content: center;
    gap: 1rem;
    padding-top: 0.5rem;
  }

  .info-section {
    padding: 1.25rem 1.5rem;
    background: var(--cds-layer-02);
    border-radius: 12px;
    text-align: center;
  }

  .info-text {
    margin-top: 0.75rem;
    font-size: 0.9rem;
    color: var(--cds-text-02);
    line-height: 1.5;
  }

  .sync-progress {
    text-align: center;
    padding: 1rem;
  }

  .sync-text {
    margin-top: 0.75rem;
    font-size: 0.9rem;
    color: var(--cds-text-02);
  }

  /* P9: Login Form Overlay Styles */
  .login-overlay {
    padding: 1rem;
  }

  .login-form-card {
    background: var(--cds-layer-02);
    border-radius: 12px;
    padding: 2rem;
    border: 1px solid var(--cds-border-subtle-01);
  }

  .login-title {
    margin: 0 0 0.5rem;
    font-size: 1.25rem;
    font-weight: 600;
    color: var(--cds-text-01);
    text-align: center;
  }

  .login-subtitle {
    margin: 0 0 1.5rem;
    font-size: 0.875rem;
    color: var(--cds-text-02);
    text-align: center;
  }

  .login-fields {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    margin-bottom: 1.5rem;
  }

  .login-actions {
    display: flex;
    justify-content: flex-end;
    gap: 1rem;
  }

  .login-form-card :global(.bx--inline-notification) {
    margin-bottom: 1rem;
  }
</style>
