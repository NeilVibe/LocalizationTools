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
  import { Modal, Button, ProgressBar, Tag } from 'carbon-components-svelte';
  import { Cloud, CloudOffline, Renew, Warning, TrashCan, Folder, Document, Application } from 'carbon-icons-svelte';
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
    unsubscribeFromOffline
  } from '$lib/stores/sync.js';

  // Dashboard modal state
  let showDashboard = $state(false);
  let reconnecting = $state(false);
  let subscriptions = $state([]);
  let loadingSubscriptions = $state(false);

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
    await tryReconnect();
    reconnecting = false;
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

  // Remove subscription
  async function removeSubscription(sub) {
    try {
      await unsubscribeFromOffline(sub.entity_type, sub.entity_id);
      subscriptions = subscriptions.filter(s => s.id !== sub.id);
    } catch (e) {
      // Error logged in store
    }
  }

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
  style="--status-color: {statusColor}"
  onclick={openDashboard}
  title="Click to open Sync Dashboard"
>
  <span class="status-icon">
    <svelte:component this={StatusIcon} size={16} />
  </span>
  <span class="status-label">{$statusLabel}</span>
  {#if $pendingChanges > 0}
    <span class="pending-badge">{$pendingChanges}</span>
  {/if}
</button>

<!-- Sync Dashboard Modal -->
<Modal
  bind:open={showDashboard}
  modalHeading="Sync Dashboard"
  passiveModal
  size="sm"
>
  <div class="dashboard-content">
    <!-- Connection Status -->
    <div class="status-section">
      <div class="status-header">
        <div class="status-indicator" style="background: {statusColor}"></div>
        <span class="status-text">{$statusLabel}</span>
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
        <span class="section-count">{subscriptions.length}</span>
      </div>

      {#if loadingSubscriptions}
        <div class="loading-text">Loading...</div>
      {:else if subscriptions.length === 0}
        <div class="empty-text">
          No items synced for offline.
          Right-click any file, project, or platform to enable offline sync.
        </div>
      {:else}
        <div class="subscriptions-list">
          {#each subscriptions as sub}
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

    <!-- Actions -->
    <div class="actions-section">
      {#if $connectionMode === 'offline'}
        <Button
          kind="primary"
          size="small"
          icon={Cloud}
          disabled={reconnecting}
          on:click={handleReconnect}
        >
          {reconnecting ? 'Connecting...' : 'Try Reconnect'}
        </Button>
      {:else}
        <Button
          kind="secondary"
          size="small"
          icon={CloudOffline}
          on:click={goOffline}
        >
          Go Offline
        </Button>
      {/if}
    </div>

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
    gap: 0.375rem;
    padding: 0.375rem 0.75rem;
    background: transparent;
    border: 1px solid var(--cds-border-subtle-01);
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.75rem;
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

  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.6; }
  }

  .status-icon {
    display: flex;
    align-items: center;
    color: var(--status-color);
  }

  .status-label {
    font-weight: 500;
  }

  .pending-badge {
    display: flex;
    align-items: center;
    justify-content: center;
    min-width: 18px;
    height: 18px;
    padding: 0 4px;
    background: var(--cds-support-warning);
    border-radius: 9px;
    font-size: 0.625rem;
    font-weight: 600;
    color: var(--cds-text-inverse);
  }

  /* Dashboard styles */
  .dashboard-content {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
  }

  .status-section {
    text-align: center;
    padding: 1rem;
    background: var(--cds-layer-02);
    border-radius: 8px;
  }

  .status-header {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
  }

  .status-indicator {
    width: 12px;
    height: 12px;
    border-radius: 50%;
  }

  .status-text {
    font-size: 1.25rem;
    font-weight: 600;
    color: var(--cds-text-01);
  }

  .error-message {
    margin-top: 0.5rem;
    font-size: 0.875rem;
    color: var(--cds-support-error);
  }

  .stats-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 1rem;
  }

  .stat-card {
    padding: 1rem;
    background: var(--cds-layer-02);
    border-radius: 8px;
    text-align: center;
  }

  .stat-label {
    font-size: 0.75rem;
    color: var(--cds-text-02);
    margin-bottom: 0.25rem;
  }

  .stat-value {
    font-size: 1.5rem;
    font-weight: 600;
    color: var(--cds-text-01);
  }

  .stat-value.has-pending {
    color: var(--cds-support-warning);
  }

  /* Subscriptions section */
  .subscriptions-section {
    background: var(--cds-layer-02);
    border-radius: 8px;
    padding: 1rem;
  }

  .section-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 0.75rem;
  }

  .section-title {
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--cds-text-01);
  }

  .section-count {
    font-size: 0.75rem;
    color: var(--cds-text-02);
    background: var(--cds-layer-01);
    padding: 0.125rem 0.5rem;
    border-radius: 10px;
  }

  .loading-text, .empty-text {
    font-size: 0.75rem;
    color: var(--cds-text-02);
    text-align: center;
    padding: 1rem 0;
  }

  .subscriptions-list {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    max-height: 200px;
    overflow-y: auto;
  }

  .subscription-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem;
    background: var(--cds-layer-01);
    border-radius: 4px;
  }

  .sub-icon {
    display: flex;
    color: var(--cds-text-02);
  }

  .sub-info {
    flex: 1;
    min-width: 0;
  }

  .sub-name {
    display: block;
    font-size: 0.75rem;
    font-weight: 500;
    color: var(--cds-text-01);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .sub-type {
    font-size: 0.625rem;
    color: var(--cds-text-02);
    text-transform: capitalize;
  }

  .sub-status {
    font-size: 0.625rem;
    color: var(--cds-text-02);
  }

  .sub-status.synced {
    color: var(--cds-support-success);
  }

  .sub-remove {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    background: transparent;
    border: none;
    border-radius: 4px;
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
    gap: 0.5rem;
  }

  .info-section {
    padding: 1rem;
    background: var(--cds-layer-02);
    border-radius: 8px;
    text-align: center;
  }

  .info-text {
    margin-top: 0.5rem;
    font-size: 0.875rem;
    color: var(--cds-text-02);
  }

  .sync-progress {
    text-align: center;
  }

  .sync-text {
    margin-top: 0.5rem;
    font-size: 0.875rem;
    color: var(--cds-text-02);
  }
</style>
