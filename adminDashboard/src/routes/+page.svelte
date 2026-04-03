<script>
  import { onMount, onDestroy } from 'svelte';
  import adminAPI from '$lib/api/client.js';
  import { websocket } from '$lib/api/websocket.js';
  import ExpandableCard from '$lib/components/ExpandableCard.svelte';
  import TerminalLog from '$lib/components/TerminalLog.svelte';
  import { Apps, Function as FunctionIcon, User, Activity, ChartLine } from 'carbon-icons-svelte';

  // Svelte 5: Reactive state
  let loading = $state(true);
  let isLive = $state(false);
  let overviewStats = $state(null);
  let activityStats = $state(null);
  let appRankings = $state([]);
  let functionRankings = $state([]);
  let recentLogs = $state([]);
  let recentActivity = $state([]);

  // Svelte 5: Derived value
  let totalOps = $derived(appRankings.reduce((sum, app) => sum + (app.usage_count || 0), 0));

  // Non-reactive
  let unsubscribe;
  let refreshTimer;

  onMount(async () => {
    await loadData();

    // Connect to WebSocket
    websocket.connect();
    isLive = true;

    // Listen for new activity — debounce to avoid re-fetch storm
    unsubscribe = websocket.on('log_entry', (newLog) => {
      recentLogs = [newLog, ...recentLogs].slice(0, 10);
      clearTimeout(refreshTimer);
      refreshTimer = setTimeout(loadData, 3000);
    });
  });

  onDestroy(() => {
    if (unsubscribe) unsubscribe();
  });

  async function loadData() {
    try {
      loading = true;

      const [overview, actStats, apps, functions, logs, activity] = await Promise.all([
        adminAPI.getOverviewStats().catch(() => ({
          active_users: 0,
          today_operations: 0,
          success_rate: 0
        })),
        adminAPI.getActivityStats(24).catch(() => ({
          rows_edited: 0, rows_confirmed: 0, active_users: 0, tool_operations: 0
        })),
        adminAPI.getAppRankings('all_time').catch(() => ({ rankings: [] })),
        adminAPI.getFunctionRankings('all_time', 5).catch(() => ({ rankings: [] })),
        adminAPI.getAllLogs({ limit: 10 }).catch(() => []),
        adminAPI.getRecentActivity(20, 24).catch(() => ({ activities: [] }))
      ]);

      overviewStats = overview;
      activityStats = actStats;
      appRankings = apps.rankings || [];
      functionRankings = functions.rankings || [];
      recentLogs = logs;
      recentActivity = activity.activities || [];

      loading = false;
    } catch (error) {
      console.error('Failed to load data:', error);
      loading = false;
    }
  }
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
      {isLive ? '🔴 LIVE - Real-time monitoring' : 'System status and key metrics'}
    </p>
  </div>

  {#if loading}
    <div class="loading-container">
      <p>Loading dashboard...</p>
    </div>
  {:else}
    <!-- Compact Stats Row -->
    <div class="compact-stats">
      <div class="compact-stat">
        <div class="compact-stat-icon"><Activity size={20} /></div>
        <div>
          <div class="compact-stat-value">{activityStats?.active_users || overviewStats.active_users || 0}</div>
          <div class="compact-stat-label">Active Translators (24h)</div>
        </div>
      </div>
      <div class="compact-stat">
        <div class="compact-stat-icon"><ChartLine size={20} /></div>
        <div>
          <div class="compact-stat-value">{activityStats?.rows_edited || 0}</div>
          <div class="compact-stat-label">Rows Edited (24h)</div>
        </div>
      </div>
      <div class="compact-stat highlight">
        <div class="compact-stat-icon"><ChartLine size={20} /></div>
        <div>
          <div class="compact-stat-value">{activityStats?.rows_confirmed || 0}</div>
          <div class="compact-stat-label">Strings Confirmed (24h)</div>
        </div>
      </div>
      <div class="compact-stat">
        <div class="compact-stat-icon"><ChartLine size={20} /></div>
        <div>
          <div class="compact-stat-value">{activityStats?.tool_operations || overviewStats.today_operations || 0}</div>
          <div class="compact-stat-label">Tool Operations</div>
        </div>
      </div>
    </div>

    <!-- Main Content Grid -->
    <div class="dashboard-grid">
      <!-- Top App (Expandable) -->
      <ExpandableCard
        icon={Apps}
        stat={appRankings[0]?.app_name || 'N/A'}
        label="Most Used App"
        highlight={true}
      >
        <div class="mini-ranking">
          {#each appRankings.slice(0, 3) as app, i}
            <div class="mini-rank-item">
              <span class="mini-rank">{i + 1}</span>
              <span class="mini-name">{app.app_name}</span>
              <span class="mini-value">{app.usage_count} ops</span>
            </div>
          {/each}
        </div>
        <a href="/stats" class="card-link">View all stats →</a>
      </ExpandableCard>

      <!-- Top Function (Expandable) -->
      <ExpandableCard
        icon={FunctionIcon}
        stat={functionRankings[0]?.function_name || 'N/A'}
        label="Most Used Function"
        highlight={true}
      >
        <div class="mini-ranking">
          {#each functionRankings.slice(0, 3) as func, i}
            <div class="mini-rank-item">
              <span class="mini-rank">{i + 1}</span>
              <span class="mini-name">{func.function_name}</span>
              <span class="mini-app">({func.tool_name})</span>
              <span class="mini-value">{func.usage_count} calls</span>
            </div>
          {/each}
        </div>
        <a href="/stats" class="card-link">View all stats →</a>
      </ExpandableCard>
    </div>

    <!-- Translation Activity Feed (Phase 111) -->
    {#if recentActivity.length > 0}
      <div class="recent-activity">
        <h2 class="section-title">Translation Activity (24h)</h2>
        <div class="activity-feed">
          {#each recentActivity.slice(0, 15) as act (act.timestamp)}
            <div class="activity-item {act.type}">
              <span class="activity-time">{new Date(act.timestamp).toLocaleTimeString()}</span>
              <span class="activity-user">{act.user}</span>
              {#if act.type === 'row_edit'}
                <span class="activity-action">{act.action}</span>
                <span class="activity-detail">{act.details?.string_id || ''} in {act.details?.file_name || ''}</span>
              {:else}
                <span class="activity-action">{act.details?.function || act.action}</span>
                <span class="activity-detail">{act.details?.tool || ''} {act.details?.status === 'success' ? '' : `(${act.details?.status})`}</span>
              {/if}
            </div>
          {/each}
        </div>
        <a href="/logs" class="view-all-link">View all activity →</a>
      </div>
    {/if}

    <!-- Tool Operations Terminal -->
    <div class="recent-activity">
      <h2 class="section-title">Tool Operations</h2>
      <TerminalLog
        logs={recentLogs}
        title="Last 10 Operations"
        height="250px"
        live={isLive}
      />
      <a href="/logs" class="view-all-link">View all logs →</a>
    </div>

    <!-- System Status -->
    <div class="system-status">
      <h3 class="status-title">System Status</h3>
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
        <div class="status-item">
          <span class="status-indicator success"></span>
          <span class="status-text">{appRankings.length} Apps Active</span>
        </div>
      </div>
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

  .compact-stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 12px;
    margin-bottom: 24px;
  }

  .compact-stat {
    display: flex;
    align-items: center;
    gap: 12px;
    background: #1a1a1a;
    border: 1px solid #2a2a2a;
    border-radius: 4px;
    padding: 16px;
    transition: all 0.2s;
  }

  .compact-stat:hover {
    border-color: #4589ff;
    transform: translateY(-2px);
  }

  .compact-stat.highlight {
    border-color: #42be65;
    background: linear-gradient(135deg, #1a1a1a 0%, #1a2a1a 100%);
  }

  .compact-stat-icon {
    color: #4589ff;
    flex-shrink: 0;
  }

  .compact-stat.highlight .compact-stat-icon {
    color: #42be65;
  }

  .compact-stat-value {
    font-size: 1.5rem;
    font-weight: 700;
    color: #f4f4f4;
  }

  .compact-stat-label {
    font-size: 0.75rem;
    color: #c6c6c6;
  }

  .dashboard-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
    gap: 20px;
    margin-bottom: 24px;
  }

  .mini-ranking {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-bottom: 12px;
  }

  .mini-rank-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px;
    background: #1a1a1a;
    border-radius: 3px;
  }

  .mini-rank {
    min-width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #4589ff;
    color: #161616;
    border-radius: 50%;
    font-weight: 700;
    font-size: 0.75rem;
  }

  .mini-name {
    color: #f4f4f4;
    font-weight: 600;
    flex: 1;
    font-size: 0.875rem;
  }

  .mini-app {
    color: #8d8d8d;
    font-size: 0.75rem;
  }

  .mini-value {
    color: #78a9ff;
    font-weight: 600;
    font-size: 0.8125rem;
  }

  .card-link {
    display: inline-block;
    color: #4589ff;
    font-size: 0.875rem;
    text-decoration: none;
    font-weight: 500;
    transition: color 0.2s;
  }

  .card-link:hover {
    color: #78a9ff;
    text-decoration: underline;
  }

  .recent-activity {
    margin-bottom: 24px;
  }

  .activity-feed {
    background: #1a1a2e;
    border: 1px solid #333;
    border-radius: 6px;
    max-height: 400px;
    overflow-y: auto;
  }

  .activity-item {
    display: flex;
    gap: 8px;
    padding: 6px 12px;
    font-size: 0.8125rem;
    border-bottom: 1px solid #222;
    align-items: baseline;
  }

  .activity-item:last-child { border-bottom: none; }
  .activity-item.row_edit { color: #78a9ff; }
  .activity-item.tool_operation { color: #a8a8a8; }

  .activity-time {
    color: #6f6f6f;
    font-family: monospace;
    font-size: 0.75rem;
    min-width: 70px;
  }

  .activity-user {
    color: #42be65;
    font-weight: 600;
    min-width: 80px;
  }

  .activity-action {
    color: #be95ff;
    min-width: 70px;
  }

  .activity-detail {
    color: #c6c6c6;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .section-title {
    color: #f4f4f4;
    font-size: 1.125rem;
    font-weight: 600;
    margin-bottom: 12px;
  }

  .view-all-link {
    display: inline-block;
    margin-top: 12px;
    color: #4589ff;
    font-size: 0.875rem;
    text-decoration: none;
    font-weight: 500;
    transition: color 0.2s;
  }

  .view-all-link:hover {
    color: #78a9ff;
    text-decoration: underline;
  }

  .system-status {
    background: #1a1a1a;
    border: 1px solid #2a2a2a;
    border-radius: 4px;
    padding: 20px;
  }

  .status-title {
    color: #f4f4f4;
    font-size: 1rem;
    font-weight: 600;
    margin-bottom: 16px;
  }

  .status-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 16px;
  }

  .status-item {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .status-indicator {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    flex-shrink: 0;
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
    color: #c6c6c6;
    font-size: 0.875rem;
  }

  .loading-container {
    text-align: center;
    padding: 60px 20px;
    color: #c6c6c6;
  }
</style>
