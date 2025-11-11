<script>
  import { onMount, onDestroy } from 'svelte';
  import adminAPI from '$lib/api/client.js';
  import { websocket } from '$lib/api/websocket.js';
  import { logger } from '$lib/utils/logger.js';
  import { ChartLine, User, Activity, CheckmarkFilled } from 'carbon-icons-svelte';

  let stats = {
    activeUsers: 0,
    todayOperations: 0,
    successRate: 0,
    avgDuration: 0
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
      logger.apiCall("/admin/stats/overview", "GET");
      logger.apiCall("/logs/recent", "GET", { limit: 10 });

      // Load comprehensive stats and recent activity
      const [overviewStats, logs] = await Promise.all([
        adminAPI.getOverviewStats().catch(() => ({
          active_users: 0,
          today_operations: 0,
          success_rate: 0,
          avg_duration_seconds: 0
        })),
        adminAPI.getAllLogs({ limit: 10 }).catch(() => [])
      ]);

      stats.activeUsers = overviewStats.active_users || 0;
      stats.todayOperations = overviewStats.today_operations || 0;
      stats.successRate = overviewStats.success_rate || 0;
      stats.avgDuration = overviewStats.avg_duration_seconds || 0;
      recentActivity = logs;

      const elapsed = performance.now() - startTime;

      loading = false;
      logger.success('Dashboard data loaded', {
        activeUsers: stats.activeUsers,
        todayOperations: stats.todayOperations,
        successRate: stats.successRate.toFixed(1),
        avgDuration: stats.avgDuration.toFixed(2),
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
        stats.todayOperations = stats.todayOperations + 1;

        // Update success rate if operation completed
        if (newLog?.status === 'completed') {
          // Recalculate success rate (approximate)
          const successOps = Math.round(stats.todayOperations * (stats.successRate / 100));
          stats.successRate = ((successOps + 1) / stats.todayOperations) * 100;
        }
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
            <div class="stat-value">{stats.activeUsers}</div>
            <div class="stat-label">Active Users (24h)</div>
          </div>
          <User size={32} style="color: var(--cds-interactive-01);" />
        </div>
      </div>

      <div class="stat-card">
        <div style="display: flex; align-items: center; justify-content: space-between;">
          <div>
            <div class="stat-value">{stats.todayOperations}</div>
            <div class="stat-label">Today's Operations</div>
          </div>
          <Activity size={32} style="color: var(--cds-interactive-01);" />
        </div>
      </div>

      <div class="stat-card">
        <div style="display: flex; align-items: center; justify-content: space-between;">
          <div>
            <div class="stat-value">{stats.successRate.toFixed(1)}%</div>
            <div class="stat-label">Success Rate</div>
          </div>
          <CheckmarkFilled size={32} style="color: #24a148;" />
        </div>
      </div>

      <div class="stat-card">
        <div style="display: flex; align-items: center; justify-content: space-between;">
          <div>
            <div class="stat-value">{stats.avgDuration.toFixed(2)}s</div>
            <div class="stat-label">Avg Duration</div>
          </div>
          <ChartLine size={32} style="color: var(--cds-interactive-01);" />
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
