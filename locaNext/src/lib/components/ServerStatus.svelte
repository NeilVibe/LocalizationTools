<script>
  import {
    Modal,
    InlineLoading,
    Tag,
    Button
  } from "carbon-components-svelte";
  import {
    CheckmarkFilled,
    WarningAlt,
    Error,
    Renew,
    ConnectionSignal,
    DataBase,
    Wifi,
    Settings
  } from "carbon-icons-svelte";
  import { onMount, onDestroy } from "svelte";
  import { logger } from "$lib/utils/logger.js";
  import { serverUrl } from "$lib/stores/app.js";
  import { get } from "svelte/store";
  import ServerConfigModal from "./ServerConfigModal.svelte";

  // Svelte 5: Props
  let { open = $bindable(false) } = $props();

  // Svelte 5: State
  let status = $state(null);
  let loading = $state(false);
  let errorMessage = $state("");
  let pollInterval = $state(null);
  let configModalOpen = $state(false);

  // Svelte 5: Derived - API base URL from store
  let API_BASE = $derived(get(serverUrl));

  // Helper to get auth headers
  function getAuthHeaders() {
    const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
    return token ? { 'Authorization': `Bearer ${token}` } : {};
  }

  // Fetch simple health status
  async function checkHealth() {
    loading = true;
    errorMessage = "";

    try {
      const response = await fetch(`${API_BASE}/api/health/simple`, {
        headers: getAuthHeaders()
      });

      if (response.ok) {
        status = await response.json();
        logger.info("Health check passed", status);
      } else {
        const error = await response.json();
        errorMessage = error.detail || "Failed to check health";
        status = {
          status: "unhealthy",
          api: "error",
          database: "error",
          websocket: "disconnected"
        };
      }
    } catch (err) {
      errorMessage = err.message;
      status = {
        status: "unhealthy",
        api: "error",
        database: "error",
        websocket: "disconnected"
      };
      logger.error("Health check failed", { error: err.message });
    } finally {
      loading = false;
    }
  }

  // Get status color
  function getStatusColor(status) {
    switch (status) {
      case 'healthy':
      case 'connected':
      case 'active':
        return 'green';
      case 'degraded':
      case 'slow':
        return 'orange';
      case 'unhealthy':
      case 'error':
      case 'disconnected':
        return 'red';
      default:
        return 'gray';
    }
  }

  // Get status icon
  function getStatusIcon(status) {
    switch (status) {
      case 'healthy':
      case 'connected':
      case 'active':
        return CheckmarkFilled;
      case 'degraded':
      case 'slow':
        return WarningAlt;
      case 'unhealthy':
      case 'error':
      case 'disconnected':
        return Error;
      default:
        return WarningAlt;
    }
  }

  // Start polling when modal opens
  function startPolling() {
    checkHealth();
    pollInterval = setInterval(checkHealth, 30000); // Poll every 30 seconds
  }

  // Stop polling when modal closes
  function stopPolling() {
    if (pollInterval) {
      clearInterval(pollInterval);
      pollInterval = null;
    }
  }

  // Svelte 5: Effect - Watch open state
  $effect(() => {
    if (open) {
      startPolling();
    } else {
      stopPolling();
    }
  });

  onDestroy(() => {
    stopPolling();
  });
</script>

<Modal
  bind:open
  modalHeading="Server Status"
  passiveModal
  size="sm"
  on:close={() => open = false}
>
  <div class="status-panel">
    {#if loading && !status}
      <div class="loading-container">
        <InlineLoading description="Checking server status..." />
      </div>
    {:else if status}
      <!-- Overall Status -->
      {@const StatusIcon = getStatusIcon(status.status)}
      <div class="overall-status" class:healthy={status.status === 'healthy'} class:degraded={status.status === 'degraded'} class:unhealthy={status.status === 'unhealthy'}>
        <StatusIcon size={24} />
        <span class="status-text">
          {#if status.status === 'healthy'}
            All Systems Operational
          {:else if status.status === 'degraded'}
            Some Services Degraded
          {:else}
            System Issues Detected
          {/if}
        </span>
      </div>

      <!-- Individual Services -->
      <div class="services-list">
        <!-- API Server -->
        <div class="service-item">
          <div class="service-icon">
            <ConnectionSignal size={20} />
          </div>
          <div class="service-info">
            <span class="service-name">API Server</span>
            <span class="service-url">{API_BASE}</span>
          </div>
          <div class="service-status" class:connected={status.api === 'connected'} class:error={status.api === 'error'}>
            <span class="status-dot"></span>
            <span class="status-label">{status.api}</span>
          </div>
        </div>

        <!-- Database -->
        <div class="service-item">
          <div class="service-icon">
            <DataBase size={20} />
          </div>
          <div class="service-info">
            <span class="service-name">Database</span>
            <span class="service-url">PostgreSQL</span>
          </div>
          <div class="service-status" class:connected={status.database === 'connected'} class:slow={status.database === 'slow'} class:error={status.database === 'error'}>
            <span class="status-dot"></span>
            <span class="status-label">{status.database}</span>
          </div>
        </div>

        <!-- WebSocket -->
        <div class="service-item">
          <div class="service-icon">
            <Wifi size={20} />
          </div>
          <div class="service-info">
            <span class="service-name">WebSocket</span>
            <span class="service-url">Real-time Sync</span>
          </div>
          <div class="service-status" class:connected={status.websocket === 'connected'} class:error={status.websocket === 'disconnected'}>
            <span class="status-dot"></span>
            <span class="status-label">{status.websocket}</span>
          </div>
        </div>
      </div>

      <!-- Actions -->
      <div class="actions-section">
        <Button
          kind="ghost"
          size="small"
          icon={Renew}
          iconDescription="Refresh"
          disabled={loading}
          on:click={checkHealth}
        >
          Refresh
        </Button>
        <Button
          kind="tertiary"
          size="small"
          icon={Settings}
          iconDescription="Configure Server"
          on:click={() => configModalOpen = true}
        >
          Configure Server
        </Button>
      </div>
      <span class="refresh-note">Auto-refreshes every 30 seconds</span>
    {:else if errorMessage}
      <div class="error-state">
        <Error size={32} />
        <p>{errorMessage}</p>
        <Button kind="tertiary" size="small" on:click={checkHealth}>Retry</Button>
      </div>
    {/if}
  </div>
</Modal>

<!-- Server Configuration Modal -->
<ServerConfigModal bind:open={configModalOpen} />

<style>
  .status-panel {
    min-height: 200px;
  }

  .loading-container {
    display: flex;
    justify-content: center;
    padding: 2rem;
  }

  .overall-status {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 1rem;
    border-radius: 8px;
    margin-bottom: 1.5rem;
  }

  .overall-status.healthy {
    background: rgba(36, 161, 72, 0.1);
    color: var(--cds-support-success, #24a148);
  }

  .overall-status.degraded {
    background: rgba(255, 131, 43, 0.1);
    color: var(--cds-support-warning, #ff832b);
  }

  .overall-status.unhealthy {
    background: rgba(218, 30, 40, 0.1);
    color: var(--cds-support-error, #da1e28);
  }

  .status-text {
    font-weight: 600;
    font-size: 1rem;
  }

  .services-list {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .service-item {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem;
    background: var(--cds-layer-02);
    border-radius: 4px;
  }

  .service-icon {
    color: var(--cds-icon-02);
  }

  .service-info {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 0.125rem;
  }

  .service-name {
    font-weight: 500;
    font-size: 0.875rem;
    color: var(--cds-text-01);
  }

  .service-url {
    font-size: 0.75rem;
    color: var(--cds-text-02);
  }

  .service-status {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 500;
  }

  .status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
  }

  .service-status.connected .status-dot {
    background: var(--cds-support-success, #24a148);
  }

  .service-status.connected .status-label {
    color: var(--cds-support-success, #24a148);
  }

  .service-status.slow .status-dot {
    background: var(--cds-support-warning, #ff832b);
  }

  .service-status.slow .status-label {
    color: var(--cds-support-warning, #ff832b);
  }

  .service-status.error .status-dot {
    background: var(--cds-support-error, #da1e28);
  }

  .service-status.error .status-label {
    color: var(--cds-support-error, #da1e28);
  }

  .actions-section {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-top: 1.5rem;
    padding-top: 1rem;
    border-top: 1px solid var(--cds-border-subtle-01);
  }

  .refresh-note {
    font-size: 0.75rem;
    color: var(--cds-text-03);
    margin-top: 0.5rem;
  }

  .error-state {
    text-align: center;
    padding: 2rem;
    color: var(--cds-support-error);
  }

  .error-state p {
    margin: 1rem 0;
    color: var(--cds-text-01);
  }
</style>
