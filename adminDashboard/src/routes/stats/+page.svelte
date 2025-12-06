<script>
  import { onMount } from 'svelte';
  import adminAPI from '$lib/api/client.js';
  import ExpandableCard from '$lib/components/ExpandableCard.svelte';
  import { Apps, Function as FunctionIcon, ChartLine, User, Trophy, Activity, UserMultiple, Language } from 'carbon-icons-svelte';

  export const data = {};
  export let params = undefined;

  let loading = true;
  let selectedPeriod = 'monthly';

  // Data
  let overviewStats = null;
  let appRankings = [];
  let functionRankings = [];
  let userRankings = [];
  let dailyStats = [];
  let teamStats = [];
  let languageStats = [];
  let userRankingsWithProfile = [];

  onMount(async () => {
    await loadData();
  });

  async function loadData() {
    try {
      loading = true;

      const [overview, apps, functions, users, daily, teams, languages, usersProfile] = await Promise.all([
        adminAPI.getOverviewStats().catch(() => ({
          active_users: 0,
          today_operations: 0,
          success_rate: 0,
          avg_duration_seconds: 0
        })),
        adminAPI.getAppRankings(selectedPeriod).catch(() => ({ rankings: [] })),
        adminAPI.getFunctionRankings(selectedPeriod, 20).catch(() => ({ rankings: [] })),
        adminAPI.getUserRankings(selectedPeriod, 10).catch(() => ({ rankings: [] })),
        adminAPI.getDailyStats(30).catch(() => ({ data: [] })),
        adminAPI.getTeamAnalytics(30).catch(() => ({ teams: [] })),
        adminAPI.getLanguageAnalytics(30).catch(() => ({ languages: [] })),
        adminAPI.getUserRankingsWithProfile(30, 10).catch(() => ({ rankings: [] }))
      ]);

      overviewStats = overview;
      appRankings = apps.rankings || [];
      functionRankings = functions.rankings || [];
      userRankings = users.rankings || [];
      dailyStats = daily.data || [];
      teamStats = teams.teams || [];
      languageStats = languages.languages || [];
      userRankingsWithProfile = usersProfile.rankings || [];

      loading = false;
    } catch (error) {
      console.error('Failed to load data:', error);
      loading = false;
    }
  }

  async function changePeriod(period) {
    selectedPeriod = period;
    await loadData();
  }

  function getTotalOps() {
    return appRankings.reduce((sum, app) => sum + (app.usage_count || 0), 0);
  }

  function getMedalIcon(rank) {
    if (rank === 1) return '🥇';
    if (rank === 2) return '🥈';
    if (rank === 3) return '🥉';
    if (rank <= 5) return '⭐';
    return '📊';
  }
</script>

<div class="admin-content">
  <div class="page-header">
    <h1 class="page-title">Statistics & Rankings</h1>
    <p class="page-subtitle">Comprehensive analytics and performance metrics</p>
  </div>

  <!-- Period Selector -->
  <div class="period-selector">
    <button class="period-btn {selectedPeriod === 'daily' ? 'active' : ''}" on:click={() => changePeriod('daily')}>Daily</button>
    <button class="period-btn {selectedPeriod === 'weekly' ? 'active' : ''}" on:click={() => changePeriod('weekly')}>Weekly</button>
    <button class="period-btn {selectedPeriod === 'monthly' ? 'active' : ''}" on:click={() => changePeriod('monthly')}>Monthly</button>
    <button class="period-btn {selectedPeriod === 'all_time' ? 'active' : ''}" on:click={() => changePeriod('all_time')}>All Time</button>
  </div>

  {#if loading}
    <div class="loading-container">
      <p>Loading statistics...</p>
    </div>
  {:else}
    <!-- Quick Stats Grid -->
    <div class="quick-stats">
      <div class="quick-stat">
        <Activity size={24} />
        <div class="quick-stat-value">{overviewStats.active_users}</div>
        <div class="quick-stat-label">Active Users (24h)</div>
      </div>
      <div class="quick-stat">
        <ChartLine size={24} />
        <div class="quick-stat-value">{overviewStats.today_operations}</div>
        <div class="quick-stat-label">Today's Operations</div>
      </div>
      <div class="quick-stat">
        <Trophy size={24} />
        <div class="quick-stat-value">{getTotalOps()}</div>
        <div class="quick-stat-label">Total Operations ({selectedPeriod})</div>
      </div>
      <div class="quick-stat">
        <ChartLine size={24} />
        <div class="quick-stat-value">{overviewStats.success_rate ? overviewStats.success_rate.toFixed(1) : 0}%</div>
        <div class="quick-stat-label">Success Rate</div>
      </div>
    </div>

    <!-- Main Stats Grid with Expandable Cards -->
    <div class="stats-grid">
      <!-- Most Used App -->
      <ExpandableCard
        icon={Apps}
        stat={appRankings[0]?.app_name || 'N/A'}
        label="Most Used App ({appRankings[0]?.usage_count || 0} ops)"
        highlight={true}
        expanded={true}
      >
        <div class="ranking-list">
          {#each appRankings.slice(0, 5) as app, i}
            <div class="ranking-item">
              <span class="rank-badge">{i + 1}</span>
              <span class="ranking-name">{app.app_name}</span>
              <span class="ranking-value">{app.usage_count} ops</span>
              <span class="medal">{getMedalIcon(i + 1)}</span>
            </div>
          {/each}
        </div>
      </ExpandableCard>

      <!-- Most Used Function (All Apps) -->
      <ExpandableCard
        icon={FunctionIcon}
        stat={functionRankings[0]?.function_name || 'N/A'}
        label="Most Used Function ({functionRankings[0]?.usage_count || 0} calls)"
        highlight={true}
        expanded={true}
      >
        <div class="ranking-list">
          {#each functionRankings.slice(0, 5) as func, i}
            <div class="ranking-item">
              <span class="rank-badge">{i + 1}</span>
              <span class="ranking-name">{func.function_name}</span>
              <span class="ranking-app">({func.tool_name})</span>
              <span class="ranking-value">{func.usage_count} calls</span>
              <span class="medal">{getMedalIcon(i + 1)}</span>
            </div>
          {/each}
        </div>
      </ExpandableCard>

      <!-- App Rankings - Full List -->
      <ExpandableCard
        icon={Apps}
        stat={appRankings.length}
        label="Active Apps"
      >
        <div class="ranking-list">
          {#each appRankings as app, i}
            <div class="ranking-item">
              <span class="rank-badge">{i + 1}</span>
              <span class="ranking-name">{app.app_name}</span>
              <span class="ranking-value">{app.usage_count} ops</span>
              <div class="usage-bar">
                <div class="usage-bar-fill" style="width: {app.usage_count / appRankings[0]?.usage_count * 100}%"></div>
              </div>
            </div>
          {/each}
        </div>
      </ExpandableCard>

      <!-- Function Rankings - Full List -->
      <ExpandableCard
        icon={FunctionIcon}
        stat={functionRankings.length}
        label="Functions Tracked"
      >
        <div class="ranking-list">
          {#each functionRankings as func, i}
            <div class="ranking-item">
              <span class="rank-badge">{i + 1}</span>
              <span class="ranking-name">{func.function_name}</span>
              <span class="ranking-app">({func.tool_name})</span>
              <span class="ranking-value">{func.usage_count} calls</span>
            </div>
          {/each}
        </div>
      </ExpandableCard>

      <!-- Top Users -->
      <ExpandableCard
        icon={User}
        stat={userRankings.length}
        label="Active Users"
      >
        <div class="ranking-list">
          {#each userRankings as user, i}
            <div class="ranking-item">
              <span class="rank-badge">{i + 1}</span>
              <span class="ranking-name">{user.username}</span>
              <span class="ranking-value">{user.total_operations} ops</span>
              <span class="medal">{getMedalIcon(i + 1)}</span>
            </div>
          {/each}
        </div>
      </ExpandableCard>

      <!-- Performance Stats -->
      <ExpandableCard
        icon={ChartLine}
        stat={overviewStats.avg_duration_seconds ? overviewStats.avg_duration_seconds.toFixed(2) + 's' : 'N/A'}
        label="Avg Operation Duration"
      >
        <div class="stats-detail">
          <div class="detail-row">
            <span class="detail-label">Success Rate:</span>
            <span class="detail-value success">{overviewStats.success_rate ? overviewStats.success_rate.toFixed(1) : 0}%</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">Active Users (24h):</span>
            <span class="detail-value">{overviewStats.active_users}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">Today's Operations:</span>
            <span class="detail-value">{overviewStats.today_operations}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">Total Operations:</span>
            <span class="detail-value">{getTotalOps()}</span>
          </div>
        </div>
      </ExpandableCard>

      <!-- Activity by Team -->
      <ExpandableCard
        icon={UserMultiple}
        stat={teamStats.length}
        label="Teams Active"
        expanded={true}
      >
        <div class="ranking-list">
          {#if teamStats.length === 0}
            <div class="no-data">No team data available</div>
          {:else}
            {#each teamStats as team, i}
              <div class="ranking-item">
                <span class="rank-badge">{i + 1}</span>
                <div class="team-info">
                  <span class="ranking-name">{team.team}</span>
                  <span class="team-tool">{team.most_used_tool || 'N/A'}</span>
                </div>
                <div class="team-stats">
                  <span class="ranking-value">{team.total_ops} ops</span>
                  <span class="team-users">{team.unique_users} users</span>
                </div>
                <span class="medal">{getMedalIcon(i + 1)}</span>
              </div>
            {/each}
          {/if}
        </div>
      </ExpandableCard>

      <!-- Activity by Language -->
      <ExpandableCard
        icon={Language}
        stat={languageStats.length}
        label="Languages Active"
        expanded={true}
      >
        <div class="ranking-list">
          {#if languageStats.length === 0}
            <div class="no-data">No language data available</div>
          {:else}
            {#each languageStats as lang, i}
              <div class="ranking-item">
                <span class="rank-badge">{i + 1}</span>
                <div class="team-info">
                  <span class="ranking-name">{lang.language}</span>
                  <span class="team-tool">{lang.most_used_tool || 'N/A'}</span>
                </div>
                <div class="team-stats">
                  <span class="ranking-value">{lang.total_ops} ops</span>
                  <span class="team-users">{lang.unique_users} users</span>
                </div>
                <span class="medal">{getMedalIcon(i + 1)}</span>
              </div>
            {/each}
          {/if}
        </div>
      </ExpandableCard>

      <!-- User Rankings with Profile -->
      <ExpandableCard
        icon={Trophy}
        stat={userRankingsWithProfile.length}
        label="Top Users"
        expanded={true}
      >
        <div class="ranking-list">
          {#if userRankingsWithProfile.length === 0}
            <div class="no-data">No user data available</div>
          {:else}
            {#each userRankingsWithProfile as user, i}
              <div class="ranking-item">
                <span class="rank-badge">{user.rank}</span>
                <div class="user-profile">
                  <span class="ranking-name">{user.display_name}</span>
                  <span class="user-meta">{user.team} | {user.language}</span>
                </div>
                <div class="team-stats">
                  <span class="ranking-value">{user.total_ops} ops</span>
                  <span class="success-badge">{user.success_rate}%</span>
                </div>
                <span class="medal">{getMedalIcon(user.rank)}</span>
              </div>
            {/each}
          {/if}
        </div>
      </ExpandableCard>
    </div>
  {/if}
</div>

<style>
  .period-selector {
    display: flex;
    gap: 12px;
    margin-bottom: 24px;
  }

  .period-btn {
    background: #262626;
    border: 1px solid #393939;
    color: #c6c6c6;
    padding: 10px 24px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
    font-weight: 500;
    transition: all 0.2s;
  }

  .period-btn:hover {
    background: #333333;
    border-color: #4589ff;
  }

  .period-btn.active {
    background: #4589ff;
    border-color: #4589ff;
    color: #ffffff;
  }

  .quick-stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
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

  .quick-stat :global(svg) {
    color: #4589ff;
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

  .rank-badge {
    min-width: 28px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #4589ff;
    color: #161616;
    border-radius: 50%;
    font-weight: 700;
    font-size: 0.875rem;
  }

  .ranking-name {
    color: #f4f4f4;
    font-weight: 600;
    flex: 1;
  }

  .ranking-app {
    color: #8d8d8d;
    font-size: 0.875rem;
  }

  .ranking-value {
    color: #78a9ff;
    font-weight: 600;
    font-size: 0.875rem;
  }

  .medal {
    font-size: 1.25rem;
  }

  .usage-bar {
    width: 100px;
    height: 6px;
    background: #2a2a2a;
    border-radius: 3px;
    overflow: hidden;
  }

  .usage-bar-fill {
    height: 100%;
    background: linear-gradient(90deg, #4589ff, #78a9ff);
    transition: width 0.3s ease;
  }

  .stats-detail {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .detail-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 12px;
    background: #1a1a1a;
    border-radius: 4px;
  }

  .detail-label {
    color: #c6c6c6;
    font-size: 0.875rem;
  }

  .detail-value {
    color: #f4f4f4;
    font-weight: 600;
    font-size: 1rem;
  }

  .detail-value.success {
    color: #42be65;
  }

  .loading-container {
    text-align: center;
    padding: 60px 20px;
    color: #c6c6c6;
  }

  .no-data {
    text-align: center;
    padding: 24px;
    color: #8d8d8d;
    font-style: italic;
  }

  .team-info, .user-profile {
    display: flex;
    flex-direction: column;
    gap: 2px;
    flex: 1;
  }

  .team-tool, .user-meta {
    font-size: 0.75rem;
    color: #8d8d8d;
  }

  .team-stats {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 2px;
  }

  .team-users {
    font-size: 0.75rem;
    color: #8d8d8d;
  }

  .success-badge {
    font-size: 0.75rem;
    color: #42be65;
    background: rgba(66, 190, 101, 0.1);
    padding: 2px 8px;
    border-radius: 10px;
  }
</style>
