<script>
  import { onMount, onDestroy } from 'svelte';
  import { adminAPI } from '$lib/api/client.js';

  // SvelteKit auto-passes these props - declare them to avoid warnings
  export let params = undefined;

  let serverStats = null;
  let loading = true;
  let error = null;
  let refreshInterval;

  async function loadServerStats() {
    error = null;
    try {
      serverStats = await adminAPI.request('/admin/stats/server');
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  }

  function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  function formatUptime(seconds) {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    let parts = [];
    if (days > 0) parts.push(`${days}d`);
    if (hours > 0) parts.push(`${hours}h`);
    if (mins > 0) parts.push(`${mins}m`);
    return parts.join(' ') || '< 1m';
  }

  function getStatusColor(percent) {
    if (percent >= 90) return '#fa4d56';
    if (percent >= 70) return '#f1c21b';
    return '#24a148';
  }

  onMount(() => {
    loadServerStats();
    refreshInterval = setInterval(loadServerStats, 10000); // Refresh every 10 seconds
  });

  onDestroy(() => {
    if (refreshInterval) clearInterval(refreshInterval);
  });
</script>

<div class="admin-content">
  <div class="page-header">
    <h1 class="page-title">Server Monitoring</h1>
    <p class="page-subtitle">Real-time server metrics and system information</p>
  </div>

  {#if loading && !serverStats}
    <div class="loading-container">
      <span>Loading server statistics...</span>
    </div>
  {:else if error && !serverStats}
    <div class="error-container">
      <div class="error-icon">!</div>
      <div class="error-text">
        <strong>Error loading server stats</strong>
        <p>{error}</p>
      </div>
      <button class="retry-btn" on:click={loadServerStats}>Retry</button>
    </div>
  {:else if serverStats}
    <!-- Stats Cards -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-icon cpu">CPU</div>
        <div class="stat-value">{serverStats.cpu?.percent || 0}%</div>
        <div class="stat-label">CPU Usage</div>
        <div class="stat-bar">
          <div class="stat-bar-fill" style="width: {serverStats.cpu?.percent || 0}%; background: {getStatusColor(serverStats.cpu?.percent || 0)}"></div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon mem">MEM</div>
        <div class="stat-value">{serverStats.memory?.percent || 0}%</div>
        <div class="stat-label">Memory Usage</div>
        <div class="stat-bar">
          <div class="stat-bar-fill" style="width: {serverStats.memory?.percent || 0}%; background: {getStatusColor(serverStats.memory?.percent || 0)}"></div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon disk">DISK</div>
        <div class="stat-value">{serverStats.disk?.percent || 0}%</div>
        <div class="stat-label">Disk Usage</div>
        <div class="stat-bar">
          <div class="stat-bar-fill" style="width: {serverStats.disk?.percent || 0}%; background: {getStatusColor(serverStats.disk?.percent || 0)}"></div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon time">UP</div>
        <div class="stat-value">{formatUptime(serverStats.uptime || 0)}</div>
        <div class="stat-label">Server Uptime</div>
      </div>
    </div>

    <!-- Server Tree View -->
    <div class="server-tree">
      <div class="tree-header">
        <span class="tree-icon">SRV</span>
        <span class="tree-title">LocaNext Server</span>
        <span class="tree-status" style="background: {serverStats.status === 'running' ? '#24a148' : '#fa4d56'}">
          {serverStats.status || 'unknown'}
        </span>
      </div>

      <div class="tree-content">
        <!-- System Section -->
        <div class="tree-section">
          <div class="section-header">
            <span class="tree-char">├─</span>
            <span class="section-icon">SYS</span>
            <span class="section-title">System</span>
          </div>
          <div class="info-items">
            <div class="info-item">
              <span class="tree-char">│  ├─</span>
              <span class="info-label">Platform:</span>
              <span class="info-value">{serverStats.system?.platform || 'N/A'}</span>
            </div>
            <div class="info-item">
              <span class="tree-char">│  ├─</span>
              <span class="info-label">Python:</span>
              <span class="info-value">{serverStats.system?.python_version || 'N/A'}</span>
            </div>
            <div class="info-item">
              <span class="tree-char">│  ├─</span>
              <span class="info-label">Hostname:</span>
              <span class="info-value">{serverStats.system?.hostname || 'N/A'}</span>
            </div>
            <div class="info-item">
              <span class="tree-char">│  └─</span>
              <span class="info-label">PID:</span>
              <span class="info-value">{serverStats.system?.pid || 'N/A'}</span>
            </div>
          </div>
        </div>

        <!-- CPU Section -->
        <div class="tree-section">
          <div class="section-header">
            <span class="tree-char">├─</span>
            <span class="section-icon">CPU</span>
            <span class="section-title">CPU Details</span>
          </div>
          <div class="info-items">
            <div class="info-item">
              <span class="tree-char">│  ├─</span>
              <span class="info-label">Cores:</span>
              <span class="info-value">{serverStats.cpu?.cores || 'N/A'}</span>
            </div>
            <div class="info-item">
              <span class="tree-char">│  ├─</span>
              <span class="info-label">Usage:</span>
              <span class="info-value metric" style="color: {getStatusColor(serverStats.cpu?.percent || 0)}">{serverStats.cpu?.percent || 0}%</span>
            </div>
            <div class="info-item">
              <span class="tree-char">│  └─</span>
              <span class="info-label">Load (1m/5m/15m):</span>
              <span class="info-value">{serverStats.cpu?.load_avg?.join(' / ') || 'N/A'}</span>
            </div>
          </div>
        </div>

        <!-- Memory Section -->
        <div class="tree-section">
          <div class="section-header">
            <span class="tree-char">├─</span>
            <span class="section-icon">MEM</span>
            <span class="section-title">Memory</span>
          </div>
          <div class="info-items">
            <div class="info-item">
              <span class="tree-char">│  ├─</span>
              <span class="info-label">Total:</span>
              <span class="info-value">{formatBytes(serverStats.memory?.total || 0)}</span>
            </div>
            <div class="info-item">
              <span class="tree-char">│  ├─</span>
              <span class="info-label">Used:</span>
              <span class="info-value">{formatBytes(serverStats.memory?.used || 0)}</span>
            </div>
            <div class="info-item">
              <span class="tree-char">│  ├─</span>
              <span class="info-label">Available:</span>
              <span class="info-value">{formatBytes(serverStats.memory?.available || 0)}</span>
            </div>
            <div class="info-item">
              <span class="tree-char">│  └─</span>
              <span class="info-label">Usage:</span>
              <span class="info-value metric" style="color: {getStatusColor(serverStats.memory?.percent || 0)}">{serverStats.memory?.percent || 0}%</span>
            </div>
          </div>
        </div>

        <!-- Disk Section -->
        <div class="tree-section">
          <div class="section-header">
            <span class="tree-char">├─</span>
            <span class="section-icon">DSK</span>
            <span class="section-title">Disk</span>
          </div>
          <div class="info-items">
            <div class="info-item">
              <span class="tree-char">│  ├─</span>
              <span class="info-label">Total:</span>
              <span class="info-value">{formatBytes(serverStats.disk?.total || 0)}</span>
            </div>
            <div class="info-item">
              <span class="tree-char">│  ├─</span>
              <span class="info-label">Used:</span>
              <span class="info-value">{formatBytes(serverStats.disk?.used || 0)}</span>
            </div>
            <div class="info-item">
              <span class="tree-char">│  ├─</span>
              <span class="info-label">Free:</span>
              <span class="info-value">{formatBytes(serverStats.disk?.free || 0)}</span>
            </div>
            <div class="info-item">
              <span class="tree-char">│  └─</span>
              <span class="info-label">Usage:</span>
              <span class="info-value metric" style="color: {getStatusColor(serverStats.disk?.percent || 0)}">{serverStats.disk?.percent || 0}%</span>
            </div>
          </div>
        </div>

        <!-- Network Section -->
        <div class="tree-section">
          <div class="section-header">
            <span class="tree-char">├─</span>
            <span class="section-icon">NET</span>
            <span class="section-title">Network</span>
          </div>
          <div class="info-items">
            <div class="info-item">
              <span class="tree-char">│  ├─</span>
              <span class="info-label">Connections:</span>
              <span class="info-value">{serverStats.network?.connections || 0}</span>
            </div>
            <div class="info-item">
              <span class="tree-char">│  ├─</span>
              <span class="info-label">Bytes Sent:</span>
              <span class="info-value">{formatBytes(serverStats.network?.bytes_sent || 0)}</span>
            </div>
            <div class="info-item">
              <span class="tree-char">│  └─</span>
              <span class="info-label">Bytes Received:</span>
              <span class="info-value">{formatBytes(serverStats.network?.bytes_recv || 0)}</span>
            </div>
          </div>
        </div>

        <!-- API Section -->
        <div class="tree-section">
          <div class="section-header">
            <span class="tree-char">└─</span>
            <span class="section-icon">API</span>
            <span class="section-title">API Status</span>
          </div>
          <div class="info-items">
            <div class="info-item">
              <span class="tree-char">   ├─</span>
              <span class="info-label">Port:</span>
              <span class="info-value">{serverStats.api?.port || 8888}</span>
            </div>
            <div class="info-item">
              <span class="tree-char">   ├─</span>
              <span class="info-label">Active Sessions:</span>
              <span class="info-value">{serverStats.api?.active_sessions || 0}</span>
            </div>
            <div class="info-item">
              <span class="tree-char">   ├─</span>
              <span class="info-label">WebSocket Clients:</span>
              <span class="info-value">{serverStats.api?.websocket_clients || 0}</span>
            </div>
            <div class="info-item">
              <span class="tree-char">   └─</span>
              <span class="info-label">Last Request:</span>
              <span class="info-value">{serverStats.api?.last_request || 'N/A'}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="refresh-note">
      Auto-refreshing every 10 seconds
      {#if error}
        <span class="refresh-error">Last refresh failed: {error}</span>
      {/if}
    </div>
  {/if}
</div>

<style>
  .error-container {
    background: rgba(218, 30, 40, 0.1);
    border: 1px solid rgba(218, 30, 40, 0.3);
    border-radius: 4px;
    padding: 1.5rem;
    display: flex;
    align-items: center;
    gap: 1rem;
  }

  .error-icon {
    width: 48px;
    height: 48px;
    background: rgba(218, 30, 40, 0.2);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.5rem;
    font-weight: 700;
    color: #fa4d56;
  }

  .error-text {
    flex: 1;
  }

  .error-text strong {
    color: #fa4d56;
  }

  .error-text p {
    color: #c6c6c6;
    margin-top: 0.25rem;
    font-size: 0.875rem;
  }

  .retry-btn {
    background: var(--cds-interactive-01);
    color: white;
    border: none;
    padding: 0.5rem 1rem;
    border-radius: 4px;
    cursor: pointer;
  }

  .stat-card {
    position: relative;
  }

  .stat-icon {
    font-size: 0.65rem;
    font-weight: 700;
    padding: 4px 8px;
    border-radius: 3px;
    color: white;
    margin-bottom: 0.75rem;
  }

  .stat-icon.cpu { background: #4589ff; }
  .stat-icon.mem { background: #8a3ffc; }
  .stat-icon.disk { background: #ffb000; }
  .stat-icon.time { background: #24a148; }

  .stat-bar {
    height: 4px;
    background: #393939;
    border-radius: 2px;
    margin-top: 0.75rem;
    overflow: hidden;
  }

  .stat-bar-fill {
    height: 100%;
    border-radius: 2px;
    transition: width 0.3s ease;
  }

  .server-tree {
    background: #161616;
    border: 1px solid #393939;
    border-radius: 4px;
    font-family: 'Consolas', 'Courier New', monospace;
    overflow: hidden;
    margin-top: 1.5rem;
  }

  .tree-header {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 1rem 1.25rem;
    background: #1a1a1a;
    border-bottom: 1px solid #393939;
  }

  .tree-icon {
    background: #24a148;
    color: white;
    padding: 4px 8px;
    border-radius: 3px;
    font-size: 0.7rem;
    font-weight: 700;
  }

  .tree-title {
    color: #e8e8e8;
    font-weight: 600;
  }

  .tree-status {
    margin-left: auto;
    padding: 2px 10px;
    border-radius: 10px;
    font-size: 0.7rem;
    font-weight: 600;
    color: white;
    text-transform: uppercase;
  }

  .tree-content {
    padding: 1rem;
    color: #c6c6c6;
    font-size: 0.8125rem;
    line-height: 1.6;
  }

  .tree-char {
    color: #525252;
    min-width: 60px;
    display: inline-block;
    font-family: monospace;
  }

  .tree-section {
    margin-bottom: 0.5rem;
  }

  .section-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.25rem 0;
  }

  .section-icon {
    background: #393939;
    color: #a8a8a8;
    padding: 2px 6px;
    border-radius: 2px;
    font-size: 0.65rem;
    font-weight: 600;
  }

  .section-title {
    color: #78a9ff;
    font-weight: 500;
  }

  .info-items {
    padding-left: 0;
  }

  .info-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.25rem 0;
  }

  .info-label {
    color: #78a9ff;
    font-weight: 500;
    min-width: 140px;
  }

  .info-value {
    color: #c6c6c6;
    font-size: 0.8rem;
  }

  .info-value.metric {
    font-weight: 600;
    font-size: 0.9rem;
  }

  .refresh-note {
    margin-top: 1rem;
    font-size: 0.75rem;
    color: #6f6f6f;
    text-align: center;
  }

  .refresh-error {
    display: block;
    color: #fa4d56;
    margin-top: 0.25rem;
  }
</style>
