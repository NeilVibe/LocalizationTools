<script>
  import { onMount } from 'svelte';
  import adminAPI from '$lib/api/client.js';
  import ExpandableCard from '$lib/components/ExpandableCard.svelte';
  import {
    WatsonHealthStackedScrolling_1 as Installations,
    Activity,
    Warning,
    CheckmarkFilled,
    Time,
    UserMultiple,
    ChartLine,
    Debug,
    WarningAlt,
    Renew
  } from 'carbon-icons-svelte';

  // Svelte 5: Reactive state
  let loading = $state(true);
  let activeTab = $state('overview');
  let autoRefresh = $state(true);

  // Non-reactive
  let refreshInterval = null;

  // Data
  let overview = $state(null);
  let installations = $state([]);
  let sessions = $state([]);
  let errorLogs = $state([]);
  let dailyStats = $state([]);

  // Filters
  let showInactive = $state(false);
  let sessionDays = $state(7);
  let errorHours = $state(24);

  onMount(async () => {
    await loadAllData();

    // Auto-refresh every 30 seconds
    if (autoRefresh) {
      refreshInterval = setInterval(loadAllData, 30000);
    }

    return () => {
      if (refreshInterval) clearInterval(refreshInterval);
    };
  });

  async function loadAllData() {
    try {
      loading = true;

      const [overviewData, installationsData, sessionsData, errorsData, statsData] = await Promise.all([
        adminAPI.getTelemetryOverview().catch(() => ({
          active_installations: 0,
          active_sessions: 0,
          online_now: 0,
          today_logs: 0,
          errors_24h: 0
        })),
        adminAPI.getInstallations(showInactive).catch(() => ({ installations: [] })),
        adminAPI.getTelemetrySessions(true, sessionDays, 50).catch(() => ({ sessions: [] })),
        adminAPI.getRemoteErrorLogs(errorHours, 50).catch(() => ({ logs: [] })),
        adminAPI.getDailyTelemetryStats(30).catch(() => ({ data: [] }))
      ]);

      overview = overviewData;
      installations = installationsData.installations || [];
      sessions = sessionsData.sessions || [];
      errorLogs = errorsData.logs || [];
      dailyStats = statsData.data || [];

      loading = false;
    } catch (error) {
      console.error('Failed to load telemetry data:', error);
      loading = false;
    }
  }

  function toggleAutoRefresh() {
    autoRefresh = !autoRefresh;
    if (autoRefresh) {
      refreshInterval = setInterval(loadAllData, 30000);
    } else if (refreshInterval) {
      clearInterval(refreshInterval);
      refreshInterval = null;
    }
  }

  function formatTimeAgo(dateStr) {
    if (!dateStr) return 'Never';
    const date = new Date(dateStr);
    const now = new Date();
    const diff = Math.floor((now - date) / 1000);

    if (diff < 60) return `${diff}s ago`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
  }

  function formatDuration(seconds) {
    if (!seconds) return '-';
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
    return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
  }

  function getStatusColor(isOnline) {
    return isOnline ? '#42be65' : '#8d8d8d';
  }

  function getLevelColor(level) {
    switch (level?.toUpperCase()) {
      case 'ERROR': return '#fa4d56';
      case 'CRITICAL': return '#da1e28';
      case 'WARNING': return '#f1c21b';
      case 'SUCCESS': return '#42be65';
      default: return '#78a9ff';
    }
  }
</script>

<div class="admin-content">
  <div class="page-header">
    <div class="header-top">
      <div>
        <h1 class="page-title">Telemetry Dashboard</h1>
        <p class="page-subtitle">Monitor remote desktop installations and sessions</p>
      </div>
      <div class="header-actions">
        <button class="refresh-btn" class:active={autoRefresh} onclick={toggleAutoRefresh}>
          <Renew size={16} />
          {autoRefresh ? 'Auto-refresh ON' : 'Auto-refresh OFF'}
        </button>
        <button class="refresh-btn" onclick={loadAllData}>
          <Renew size={16} />
          Refresh Now
        </button>
      </div>
    </div>
  </div>

  <!-- Tab Navigation -->
  <div class="tab-nav">
    <button class="tab-btn" class:active={activeTab === 'overview'} onclick={() => activeTab = 'overview'}>
      <ChartLine size={16} />
      Overview
    </button>
    <button class="tab-btn" class:active={activeTab === 'installations'} onclick={() => activeTab = 'installations'}>
      <Installations size={16} />
      Installations
    </button>
    <button class="tab-btn" class:active={activeTab === 'sessions'} onclick={() => activeTab = 'sessions'}>
      <Activity size={16} />
      Sessions
    </button>
    <button class="tab-btn" class:active={activeTab === 'errors'} onclick={() => activeTab = 'errors'}>
      <Warning size={16} />
      Errors
    </button>
  </div>

  {#if loading}
    <div class="loading-container">
      <p>Loading telemetry data...</p>
    </div>
  {:else}
    <!-- Overview Tab -->
    {#if activeTab === 'overview'}
      <div class="quick-stats">
        <div class="quick-stat">
          <Installations size={24} />
          <div class="quick-stat-value">{overview?.active_installations || 0}</div>
          <div class="quick-stat-label">Active Installations</div>
        </div>
        <div class="quick-stat highlight">
          <UserMultiple size={24} />
          <div class="quick-stat-value">{overview?.online_now || 0}</div>
          <div class="quick-stat-label">Online Now</div>
        </div>
        <div class="quick-stat">
          <Activity size={24} />
          <div class="quick-stat-value">{overview?.active_sessions || 0}</div>
          <div class="quick-stat-label">Active Sessions</div>
        </div>
        <div class="quick-stat">
          <Debug size={24} />
          <div class="quick-stat-value">{overview?.today_logs || 0}</div>
          <div class="quick-stat-label">Today's Logs</div>
        </div>
        <div class="quick-stat" class:warning={overview?.errors_24h > 0}>
          <WarningAlt size={24} />
          <div class="quick-stat-value">{overview?.errors_24h || 0}</div>
          <div class="quick-stat-label">Errors (24h)</div>
        </div>
      </div>

      <!-- Daily Stats Chart -->
      <div class="stats-grid">
        <ExpandableCard
          icon={ChartLine}
          stat={dailyStats.length}
          label="Days of Data"
          expanded={true}
        >
          <div class="chart-container">
            {#if dailyStats.length === 0}
              <div class="no-data">No telemetry data yet. Deploy the desktop app to start collecting data.</div>
            {:else}
              <div class="mini-chart">
                {#each dailyStats.slice(-14) as day}
                  <div class="chart-bar-group">
                    <div
                      class="chart-bar info"
                      style="height: {Math.min(100, (day.info_count / 100) * 100)}%"
                      title="{day.info_count} info logs"
                    ></div>
                    <div
                      class="chart-bar error"
                      style="height: {Math.min(100, (day.error_count / 10) * 100)}%"
                      title="{day.error_count} errors"
                    ></div>
                    <div class="chart-label">{day.date?.slice(5) || ''}</div>
                  </div>
                {/each}
              </div>
            {/if}
          </div>
        </ExpandableCard>

        <ExpandableCard
          icon={Installations}
          stat={installations.length}
          label="Registered Installations"
          expanded={true}
        >
          <div class="ranking-list">
            {#if installations.length === 0}
              <div class="no-data">No installations registered yet</div>
            {:else}
              {#each installations.slice(0, 5) as inst}
                <div class="ranking-item">
                  <span class="status-dot" style="background: {getStatusColor(inst.is_online)}"></span>
                  <div class="inst-info">
                    <span class="ranking-name">{inst.installation_name}</span>
                    <span class="inst-version">v{inst.version}</span>
                  </div>
                  <div class="inst-stats">
                    <span class="ranking-value">{inst.today_sessions} sessions</span>
                    {#if inst.errors_24h > 0}
                      <span class="error-badge">{inst.errors_24h} errors</span>
                    {/if}
                  </div>
                </div>
              {/each}
            {/if}
          </div>
        </ExpandableCard>
      </div>
    {/if}

    <!-- Installations Tab -->
    {#if activeTab === 'installations'}
      <div class="filter-bar">
        <label class="filter-toggle">
          <input type="checkbox" bind:checked={showInactive} onchange={loadAllData} />
          Show inactive installations
        </label>
      </div>

      <div class="table-container">
        <table class="data-table">
          <thead>
            <tr>
              <th>Status</th>
              <th>Installation Name</th>
              <th>Version</th>
              <th>Owner</th>
              <th>Last Seen</th>
              <th>Today Sessions</th>
              <th>Errors (24h)</th>
            </tr>
          </thead>
          <tbody>
            {#if installations.length === 0}
              <tr>
                <td colspan="7" class="no-data">No installations found</td>
              </tr>
            {:else}
              {#each installations as inst}
                <tr class:inactive={!inst.is_active}>
                  <td>
                    <span class="status-badge" class:online={inst.is_online} class:offline={!inst.is_online}>
                      {inst.is_online ? 'Online' : 'Offline'}
                    </span>
                  </td>
                  <td class="name-cell">{inst.installation_name}</td>
                  <td>v{inst.version}</td>
                  <td>{inst.owner_email || '-'}</td>
                  <td>{formatTimeAgo(inst.last_seen)}</td>
                  <td>{inst.today_sessions}</td>
                  <td>
                    {#if inst.errors_24h > 0}
                      <span class="error-count">{inst.errors_24h}</span>
                    {:else}
                      <span class="success-count"><CheckmarkFilled size={16} /></span>
                    {/if}
                  </td>
                </tr>
              {/each}
            {/if}
          </tbody>
        </table>
      </div>
    {/if}

    <!-- Sessions Tab -->
    {#if activeTab === 'sessions'}
      <div class="filter-bar">
        <label class="filter-label">
          Show sessions from last:
          <select bind:value={sessionDays} onchange={loadAllData}>
            <option value={1}>1 day</option>
            <option value={7}>7 days</option>
            <option value={14}>14 days</option>
            <option value={30}>30 days</option>
          </select>
        </label>
      </div>

      <div class="table-container">
        <table class="data-table">
          <thead>
            <tr>
              <th>Status</th>
              <th>Installation</th>
              <th>Version</th>
              <th>Started</th>
              <th>Duration</th>
              <th>Last Heartbeat</th>
            </tr>
          </thead>
          <tbody>
            {#if sessions.length === 0}
              <tr>
                <td colspan="6" class="no-data">No sessions found</td>
              </tr>
            {:else}
              {#each sessions as session}
                <tr>
                  <td>
                    <span class="status-badge" class:online={session.is_active} class:offline={!session.is_active}>
                      {session.is_active ? 'Active' : session.end_reason || 'Ended'}
                    </span>
                  </td>
                  <td class="name-cell">{session.installation_name}</td>
                  <td>v{session.app_version}</td>
                  <td>
                    <Time size={14} />
                    {formatTimeAgo(session.started_at)}
                  </td>
                  <td>{formatDuration(session.duration_seconds)}</td>
                  <td>{session.is_active ? formatTimeAgo(session.last_heartbeat) : '-'}</td>
                </tr>
              {/each}
            {/if}
          </tbody>
        </table>
      </div>
    {/if}

    <!-- Errors Tab -->
    {#if activeTab === 'errors'}
      <div class="filter-bar">
        <label class="filter-label">
          Show errors from last:
          <select bind:value={errorHours} onchange={loadAllData}>
            <option value={6}>6 hours</option>
            <option value={24}>24 hours</option>
            <option value={48}>48 hours</option>
            <option value={168}>7 days</option>
          </select>
        </label>
      </div>

      <div class="table-container">
        <table class="data-table">
          <thead>
            <tr>
              <th>Level</th>
              <th>Time</th>
              <th>Installation</th>
              <th>Component</th>
              <th>Message</th>
            </tr>
          </thead>
          <tbody>
            {#if errorLogs.length === 0}
              <tr>
                <td colspan="5" class="no-data success-msg">
                  <CheckmarkFilled size={20} />
                  No errors in the selected time period
                </td>
              </tr>
            {:else}
              {#each errorLogs as log}
                <tr>
                  <td>
                    <span class="level-badge" style="background: {getLevelColor(log.level)}">
                      {log.level}
                    </span>
                  </td>
                  <td>{formatTimeAgo(log.received_at)}</td>
                  <td>{log.installation_name}</td>
                  <td>{log.component || '-'}</td>
                  <td class="message-cell">{log.message}</td>
                </tr>
              {/each}
            {/if}
          </tbody>
        </table>
      </div>
    {/if}
  {/if}
</div>

<style>
  .header-top {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
  }

  .header-actions {
    display: flex;
    gap: 8px;
  }

  .refresh-btn {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 16px;
    background: #262626;
    border: 1px solid #393939;
    color: #c6c6c6;
    border-radius: 4px;
    cursor: pointer;
    font-size: 13px;
    transition: all 0.2s;
  }

  .refresh-btn:hover {
    background: #333333;
    border-color: #4589ff;
  }

  .refresh-btn.active {
    background: #0f62fe;
    border-color: #0f62fe;
    color: #ffffff;
  }

  .tab-nav {
    display: flex;
    gap: 4px;
    margin-bottom: 24px;
    background: #1a1a1a;
    padding: 4px;
    border-radius: 4px;
    width: fit-content;
  }

  .tab-btn {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 20px;
    background: transparent;
    border: none;
    color: #c6c6c6;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
    transition: all 0.2s;
  }

  .tab-btn:hover {
    background: #262626;
  }

  .tab-btn.active {
    background: #4589ff;
    color: #ffffff;
  }

  .quick-stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 16px;
    margin-bottom: 32px;
  }

  .quick-stat {
    background: #1a1a1a;
    border: 1px solid #2a2a2a;
    border-radius: 4px;
    padding: 20px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    transition: all 0.2s;
  }

  .quick-stat:hover {
    border-color: #4589ff;
    transform: translateY(-2px);
  }

  .quick-stat.highlight {
    border-color: #42be65;
    background: linear-gradient(135deg, #1a1a1a 0%, #1a2a1a 100%);
  }

  .quick-stat.warning {
    border-color: #fa4d56;
    background: linear-gradient(135deg, #1a1a1a 0%, #2a1a1a 100%);
  }

  .quick-stat :global(svg) {
    color: #4589ff;
  }

  .quick-stat.highlight :global(svg) {
    color: #42be65;
  }

  .quick-stat.warning :global(svg) {
    color: #fa4d56;
  }

  .quick-stat-value {
    font-size: 2rem;
    font-weight: 700;
    color: #f4f4f4;
  }

  .quick-stat-label {
    font-size: 0.75rem;
    color: #c6c6c6;
    text-align: center;
  }

  .stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
    gap: 20px;
    margin-bottom: 24px;
  }

  .filter-bar {
    display: flex;
    gap: 16px;
    margin-bottom: 16px;
    align-items: center;
  }

  .filter-toggle {
    display: flex;
    align-items: center;
    gap: 8px;
    color: #c6c6c6;
    font-size: 14px;
    cursor: pointer;
  }

  .filter-label {
    display: flex;
    align-items: center;
    gap: 8px;
    color: #c6c6c6;
    font-size: 14px;
  }

  .filter-label select {
    background: #262626;
    border: 1px solid #393939;
    color: #f4f4f4;
    padding: 6px 12px;
    border-radius: 4px;
    cursor: pointer;
  }

  .table-container {
    background: #1a1a1a;
    border: 1px solid #2a2a2a;
    border-radius: 4px;
    overflow: hidden;
  }

  .data-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 14px;
  }

  .data-table th {
    background: #262626;
    color: #c6c6c6;
    padding: 12px 16px;
    text-align: left;
    font-weight: 600;
    border-bottom: 1px solid #393939;
  }

  .data-table td {
    padding: 12px 16px;
    color: #f4f4f4;
    border-bottom: 1px solid #2a2a2a;
  }

  .data-table tr:hover td {
    background: #262626;
  }

  .data-table tr.inactive td {
    opacity: 0.5;
  }

  .name-cell {
    font-weight: 600;
    color: #78a9ff;
  }

  .message-cell {
    max-width: 400px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .status-badge {
    display: inline-block;
    padding: 4px 10px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 600;
  }

  .status-badge.online {
    background: rgba(66, 190, 101, 0.2);
    color: #42be65;
  }

  .status-badge.offline {
    background: rgba(141, 141, 141, 0.2);
    color: #8d8d8d;
  }

  .level-badge {
    display: inline-block;
    padding: 4px 10px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 600;
    color: #ffffff;
  }

  .error-count {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 24px;
    height: 24px;
    background: #fa4d56;
    color: #ffffff;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 600;
  }

  .success-count {
    color: #42be65;
  }

  .no-data {
    text-align: center;
    padding: 32px;
    color: #8d8d8d;
    font-style: italic;
  }

  .success-msg {
    color: #42be65;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
  }

  .loading-container {
    text-align: center;
    padding: 60px 20px;
    color: #c6c6c6;
  }

  .ranking-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .ranking-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px;
    background: #1a1a1a;
    border-radius: 4px;
    border: 1px solid #2a2a2a;
    transition: all 0.2s;
  }

  .ranking-item:hover {
    background: #2a2a2a;
    border-color: #4589ff;
  }

  .status-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
  }

  .inst-info {
    display: flex;
    flex-direction: column;
    flex: 1;
  }

  .ranking-name {
    color: #f4f4f4;
    font-weight: 600;
  }

  .inst-version {
    font-size: 12px;
    color: #8d8d8d;
  }

  .inst-stats {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 4px;
  }

  .ranking-value {
    color: #78a9ff;
    font-weight: 600;
    font-size: 0.875rem;
  }

  .error-badge {
    font-size: 11px;
    color: #fa4d56;
    background: rgba(250, 77, 86, 0.1);
    padding: 2px 8px;
    border-radius: 10px;
  }

  .chart-container {
    padding: 16px 0;
  }

  .mini-chart {
    display: flex;
    align-items: flex-end;
    gap: 8px;
    height: 120px;
    padding: 0 8px;
  }

  .chart-bar-group {
    display: flex;
    flex-direction: column;
    align-items: center;
    flex: 1;
    gap: 4px;
    height: 100%;
  }

  .chart-bar {
    width: 100%;
    min-height: 4px;
    border-radius: 2px;
    transition: height 0.3s ease;
  }

  .chart-bar.info {
    background: #4589ff;
  }

  .chart-bar.error {
    background: #fa4d56;
  }

  .chart-label {
    font-size: 10px;
    color: #8d8d8d;
    white-space: nowrap;
  }
</style>
