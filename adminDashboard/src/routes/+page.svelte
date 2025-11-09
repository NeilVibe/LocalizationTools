<script>
  import { onMount, onDestroy } from 'svelte';
  import adminAPI from '$lib/api/client.js';
  import { websocket } from '$lib/api/websocket.js';
  import { logger } from '$lib/utils/logger.js';
  import { ChartLine, User, Activity, CheckmarkFilled } from 'carbon-icons-svelte';

  let stats = {
    totalUsers: 0,
    totalLogs: 0,
    activeSessions: 0,
    successRate: 0
  };
  let recentActivity = [];
  let loading = true;
  let isLive = false;
  let unsubscribe;

  onMount(async () => {
    const startTime = performance.now();
    logger.component('Dashboard', 'mounted');

    try {
      logger.info("Loading dashboard data");
      logger.apiCall("/api/users", "GET");
      logger.apiCall("/api/logs", "GET", { limit: 10 });

      // Load stats and recent activity
      const [users, logs] = await Promise.all([
        adminAPI.getAllUsers().catch(() => []),
        adminAPI.getAllLogs({ limit: 10 }).catch(() => [])
      ]);

      stats.totalUsers = users.length || 0;
      stats.totalLogs = logs.length || 0;
      recentActivity = logs;

      const elapsed = performance.now() - startTime;

      loading = false;
      logger.success('Dashboard data loaded', {
        totalUsers: stats.totalUsers,
        totalLogs: stats.totalLogs,
        elapsed_ms: elapsed.toFixed(2)
      });

      // Connect to WebSocket for real-time updates
      logger.info("Connecting to WebSocket for real-time updates");
      websocket.connect();
      isLive = true;

      // Listen for new log entries to update recent activity
      unsubscribe = websocket.on('log_entry', (newLog) => {
        logger.info('New activity received via WebSocket', {
          logId: newLog?.log_id,
          tool: newLog?.tool_name,
          operation: newLog?.operation,
          status: newLog?.status
        });
        recentActivity = [newLog, ...recentActivity].slice(0, 10);
        stats.totalLogs = stats.totalLogs + 1;
      });

    } catch (error) {
      const elapsed = performance.now() - startTime;
      logger.error('Failed to load dashboard data', {
        error: error.message,
        error_type: error.name,
        elapsed_ms: elapsed.toFixed(2)
      });
      loading = false;
    }
  });

  onDestroy(() => {
    logger.component('Dashboard', 'destroyed');
    if (unsubscribe) {
      logger.info("Cleaning up WebSocket subscription");
      unsubscribe();
    }
  });
</script>

<div class="admin-content">
  <div class="page-header">
    <h1 class="page-title">Dashboard Overview</h1>
    <p class="page-subtitle">Monitor system activity and performance</p>
  </div>

  {#if loading}
    <div class="loading-container">
      <p>Loading dashboard...</p>
    </div>
  {:else}
    <div class="stats-grid">
      <div class="stat-card">
        <div style="display: flex; align-items: center; justify-content: space-between;">
          <div>
            <div class="stat-value">{stats.totalUsers}</div>
            <div class="stat-label">Total Users</div>
          </div>
          <User size={32} style="color: var(--cds-interactive-01);" />
        </div>
      </div>

      <div class="stat-card">
        <div style="display: flex; align-items: center; justify-content: space-between;">
          <div>
            <div class="stat-value">{stats.totalLogs}</div>
            <div class="stat-label">Total Operations</div>
          </div>
          <Activity size={32} style="color: var(--cds-interactive-01);" />
        </div>
      </div>

      <div class="stat-card">
        <div style="display: flex; align-items: center; justify-content: space-between;">
          <div>
            <div class="stat-value">{stats.activeSessions}</div>
            <div class="stat-label">Active Sessions</div>
          </div>
          <ChartLine size={32} style="color: var(--cds-interactive-01);" />
        </div>
      </div>

      <div class="stat-card">
        <div style="display: flex; align-items: center; justify-content: space-between;">
          <div>
            <div class="stat-value">{stats.successRate}%</div>
            <div class="stat-label">Success Rate</div>
          </div>
          <CheckmarkFilled size={32} style="color: #24a148;" />
        </div>
      </div>
    </div>

    <div class="card">
      <h2 class="card-title">Recent Activity</h2>
      {#if recentActivity.length > 0}
        <div class="data-table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th>User</th>
                <th>Operation</th>
                <th>Tool</th>
                <th>Status</th>
                <th>Time</th>
              </tr>
            </thead>
            <tbody>
              {#each recentActivity.slice(0, 5) as log}
                <tr>
                  <td>{log.user_id}</td>
                  <td>{log.operation || 'N/A'}</td>
                  <td>{log.tool_name || 'N/A'}</td>
                  <td>
                    <span class="status-badge {log.status === 'completed' ? 'success' : 'info'}">
                      {log.status}
                    </span>
                  </td>
                  <td>{new Date(log.timestamp).toLocaleString()}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {:else}
        <div class="empty-state">
          <h3>No recent activity</h3>
          <p>Activity will appear here as users interact with the system</p>
        </div>
      {/if}
    </div>
  {/if}
</div>
