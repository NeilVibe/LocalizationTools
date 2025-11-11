<script>
  import { onMount, onDestroy } from 'svelte';
  import adminAPI from '$lib/api/client.js';
  import { websocket } from '$lib/api/websocket.js';
  import { logger } from '$lib/utils/logger.js';
  import { ChartLine, User, Activity, Apps, Function as FunctionIcon } from 'carbon-icons-svelte';

  // SvelteKit auto-passes these props - declare to avoid warnings
  export const data = {};

  let stats = {
    activeUsers: 0,
    todayOperations: 0,
    totalOperations: 0,
    mostUsedApp: { name: 'N/A', count: 0 },
    mostUsedFunction: { name: 'N/A', app: 'N/A', count: 0 }
  };
  let loading = true;
  let isLive = false;
  let unsubscribe;

  onMount(async () => {
    const startTime = performance.now();
    logger.component('Dashboard', 'mounted');

    try {
      logger.info("Loading dashboard data");

      // Load comprehensive stats
      const [overviewStats, appRankings, functionRankings] = await Promise.all([
        adminAPI.getOverviewStats().catch(() => ({
          active_users: 0,
          today_operations: 0
        })),
        adminAPI.getAppRankings('all_time').catch(() => ({ rankings: [] })),
        adminAPI.getFunctionRankings('all_time', 5).catch(() => ({ rankings: [] }))
      ]);

      // Set basic stats
      stats.activeUsers = overviewStats.active_users || 0;
      stats.todayOperations = overviewStats.today_operations || 0;

      // Calculate total operations from all apps
      stats.totalOperations = appRankings.rankings?.reduce((sum, app) => sum + (app.usage_count || 0), 0) || 0;

      // Most used app
      if (appRankings.rankings && appRankings.rankings.length > 0) {
        const topApp = appRankings.rankings[0];
        stats.mostUsedApp = {
          name: topApp.app_name,
          count: topApp.usage_count
        };
      }

      // Most used function
      if (functionRankings.rankings && functionRankings.rankings.length > 0) {
        const topFunc = functionRankings.rankings[0];
        stats.mostUsedFunction = {
          name: topFunc.function_name,
          app: topFunc.tool_name,
          count: topFunc.usage_count
        };
      }

      const elapsed = performance.now() - startTime;

      loading = false;
      logger.success('Dashboard data loaded', {
        activeUsers: stats.activeUsers,
        todayOperations: stats.todayOperations,
        totalOperations: stats.totalOperations,
        mostUsedApp: stats.mostUsedApp.name,
        mostUsedFunction: `${stats.mostUsedFunction.app}::${stats.mostUsedFunction.name}`,
        elapsed_ms: elapsed.toFixed(2)
      });

      // Connect to WebSocket for real-time updates
      logger.info("Connecting to WebSocket for real-time updates");
      websocket.connect();
      isLive = true;

      // Listen for new log entries to update stats
      unsubscribe = websocket.on('log_entry', (newLog) => {
        logger.info('New activity received via WebSocket', {
          logId: newLog?.log_id,
          tool: newLog?.tool_name,
          operation: newLog?.operation,
          status: newLog?.status
        });

        // Update today's operations count
        stats.todayOperations = stats.todayOperations + 1;
        stats.totalOperations = stats.totalOperations + 1;
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
    <h1 class="page-title">
      Dashboard Overview
      {#if isLive}
        <span class="live-indicator"></span>
      {/if}
    </h1>
    <p class="page-subtitle">
      {isLive ? '🔴 LIVE - Real-time system monitoring' : 'System activity and key metrics'}
    </p>
  </div>

  {#if loading}
    <div class="loading-container">
      <p>Loading dashboard...</p>
    </div>
  {:else}
    <!-- Key Metrics Grid -->
    <div class="stats-grid">
      <!-- Active Users -->
      <div class="stat-card">
        <div class="stat-card-content">
          <div>
            <div class="stat-value">{stats.activeUsers}</div>
            <div class="stat-label">Active Users (24h)</div>
          </div>
          <User size={32} class="stat-icon" />
        </div>
      </div>

      <!-- Today's Operations -->
      <div class="stat-card">
        <div class="stat-card-content">
          <div>
            <div class="stat-value">{stats.todayOperations}</div>
            <div class="stat-label">Today's Operations</div>
          </div>
          <Activity size={32} class="stat-icon" />
        </div>
      </div>

      <!-- Total Operations (All Time) -->
      <div class="stat-card">
        <div class="stat-card-content">
          <div>
            <div class="stat-value">{stats.totalOperations.toLocaleString()}</div>
            <div class="stat-label">Total Operations</div>
          </div>
          <ChartLine size={32} class="stat-icon" />
        </div>
      </div>

      <!-- Most Used App -->
      <div class="stat-card highlight">
        <div class="stat-card-content">
          <div>
            <div class="stat-value">{stats.mostUsedApp.name}</div>
            <div class="stat-label">Most Used App ({stats.mostUsedApp.count} uses)</div>
          </div>
          <Apps size={32} class="stat-icon-highlight" />
        </div>
      </div>

      <!-- Most Used Function -->
      <div class="stat-card highlight">
        <div class="stat-card-content">
          <div>
            <div class="stat-value function-name">{stats.mostUsedFunction.name}</div>
            <div class="stat-label">
              Most Used Function ({stats.mostUsedFunction.count} uses)
              <br/>
              <span class="app-name">in {stats.mostUsedFunction.app}</span>
            </div>
          </div>
          <FunctionIcon size={32} class="stat-icon-highlight" />
        </div>
      </div>
    </div>

    <!-- System Status -->
    <div class="card">
      <h2 class="card-title">System Status</h2>
      <div class="status-grid">
        <div class="status-item">
          <span class="status-indicator success"></span>
          <span class="status-text">Backend API</span>
        </div>
        <div class="status-item">
          <span class="status-indicator success"></span>
          <span class="status-text">Database</span>
        </div>
        <div class="status-item">
          <span class="status-indicator {isLive ? 'success' : 'warning'}"></span>
          <span class="status-text">WebSocket {isLive ? 'Connected' : 'Disconnected'}</span>
        </div>
      </div>
    </div>

    <!-- Quick Links -->
    <div class="quick-links-grid">
      <a href="/stats" class="quick-link-card">
        <ChartLine size={24} />
        <div>
          <div class="quick-link-title">Statistics</div>
          <div class="quick-link-desc">View detailed charts and trends</div>
        </div>
      </a>

      <a href="/rankings" class="quick-link-card">
        <Apps size={24} />
        <div>
          <div class="quick-link-title">Rankings</div>
          <div class="quick-link-desc">User, App & Function rankings</div>
        </div>
      </a>

      <a href="/users" class="quick-link-card">
        <User size={24} />
        <div>
          <div class="quick-link-title">Users</div>
          <div class="quick-link-desc">Manage users and permissions</div>
        </div>
      </a>

      <a href="/logs" class="quick-link-card">
        <Activity size={24} />
        <div>
          <div class="quick-link-title">System Logs</div>
          <div class="quick-link-desc">Browse and search all activity</div>
        </div>
      </a>
    </div>
  {/if}
</div>

<style>
  .live-indicator {
    display: inline-block;
    width: 8px;
    height: 8px;
    background: #24a148;
    border-radius: 50%;
    margin-left: 10px;
    animation: pulse 2s infinite;
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
  }

  .stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 20px;
    margin-bottom: 24px;
  }

  .stat-card {
    background: #262626;
    border: 1px solid #393939;
    border-radius: 4px;
    padding: 20px;
    transition: all 0.2s;
  }

  .stat-card:hover {
    border-color: #4589ff;
    box-shadow: 0 2px 8px rgba(69, 137, 255, 0.2);
  }

  .stat-card.highlight {
    background: linear-gradient(135deg, #262626 0%, #2d2d2d 100%);
    border-color: #4589ff;
  }

  .stat-card-content {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .stat-value {
    font-size: 2rem;
    font-weight: 700;
    color: #f4f4f4;
    margin-bottom: 8px;
    word-break: break-word;
  }

  .stat-value.function-name {
    font-size: 1.5rem;
    color: #78a9ff;
    font-family: 'Courier New', monospace;
  }

  .stat-label {
    font-size: 0.875rem;
    color: #c6c6c6;
  }

  .app-name {
    color: #78a9ff;
    font-weight: 500;
  }

  .stat-icon {
    color: #4589ff;
    opacity: 0.8;
  }

  .stat-icon-highlight {
    color: #ffb000;
    opacity: 0.9;
  }

  .status-grid {
    display: flex;
    gap: 32px;
    flex-wrap: wrap;
  }

  .status-item {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .status-indicator {
    width: 12px;
    height: 12px;
    border-radius: 50%;
  }

  .status-indicator.success {
    background: #24a148;
    box-shadow: 0 0 8px rgba(36, 161, 72, 0.6);
  }

  .status-indicator.warning {
    background: #f1c21b;
    box-shadow: 0 0 8px rgba(241, 194, 27, 0.6);
  }

  .status-text {
    color: #f4f4f4;
    font-size: 14px;
  }

  .quick-links-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 16px;
    margin-top: 24px;
  }

  .quick-link-card {
    display: flex;
    align-items: center;
    gap: 16px;
    background: #262626;
    border: 1px solid #393939;
    border-radius: 4px;
    padding: 16px;
    text-decoration: none;
    color: #f4f4f4;
    transition: all 0.2s;
  }

  .quick-link-card:hover {
    border-color: #4589ff;
    background: #2d2d2d;
    transform: translateY(-2px);
  }

  .quick-link-card :global(svg) {
    color: #4589ff;
    flex-shrink: 0;
  }

  .quick-link-title {
    font-weight: 600;
    font-size: 14px;
    margin-bottom: 4px;
  }

  .quick-link-desc {
    font-size: 12px;
    color: #c6c6c6;
  }
</style>
