<script>
  import { onMount } from 'svelte';
  import adminAPI from '$lib/api/client.js';
  import { Trophy, Star, User, Apps, Function as FunctionIcon } from 'carbon-icons-svelte';

  let loading = true;
  let selectedPeriod = 'monthly'; // 'daily', 'weekly', 'monthly', 'all_time'
  let selectedLimit = 20;

  let userRankings = [];
  let userRankingsByTime = [];
  let appRankings = [];
  let functionRankings = [];
  let functionRankingsByTime = [];

  onMount(async () => {
    await loadRankings();
  });

  async function loadRankings() {
    try {
      loading = true;

      // Load all rankings in parallel
      const [users, usersByTime, apps, functions, functionsByTime] = await Promise.all([
        adminAPI.getUserRankings(selectedPeriod, selectedLimit).catch(() => ({ rankings: [] })),
        adminAPI.getUserRankingsByTime(selectedPeriod, selectedLimit).catch(() => ({ rankings: [] })),
        adminAPI.getAppRankings(selectedPeriod).catch(() => ({ rankings: [] })),
        adminAPI.getFunctionRankings(selectedPeriod, selectedLimit).catch(() => ({ rankings: [] })),
        adminAPI.getFunctionRankingsByTime(selectedPeriod, selectedLimit).catch(() => ({ rankings: [] }))
      ]);

      userRankings = users.rankings || [];
      userRankingsByTime = usersByTime.rankings || [];
      appRankings = apps.rankings || [];
      functionRankings = functions.rankings || [];
      functionRankingsByTime = functionsByTime.rankings || [];

      loading = false;
    } catch (error) {
      console.error('Failed to load rankings:', error);
      loading = false;
    }
  }

  async function changePeriod(period) {
    selectedPeriod = period;
    await loadRankings();
  }

  function getMedalColor(rank) {
    if (rank === 1) return '#ffd700'; // Gold
    if (rank === 2) return '#c0c0c0'; // Silver
    if (rank === 3) return '#cd7f32'; // Bronze
    return '#78a9ff';
  }

  function getMedalIcon(rank) {
    if (rank <= 3) return '🏆';
    if (rank <= 5) return '⭐';
    return '📊';
  }

  function formatTime(seconds) {
    if (!seconds) return '0s';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);

    if (hours > 0) return `${hours}h ${minutes}m`;
    if (minutes > 0) return `${minutes}m ${secs}s`;
    return `${secs}s`;
  }

  function formatTimeDetailed(timeString) {
    // Handles formats like "2h 45m" from backend
    return timeString || '0h 0m';
  }
</script>

<div class="admin-content">
  <div class="page-header">
    <div style="display: flex; align-items: center; gap: 12px;">
      <Trophy size={32} style="color: #ffd700;" />
      <div>
        <h1 class="page-title">Rankings & Leaderboards</h1>
        <p class="page-subtitle">Top performers across the platform</p>
      </div>
    </div>
  </div>

  <!-- Period Selector -->
  <div class="period-selector">
    <button
      class="period-btn {selectedPeriod === 'daily' ? 'active' : ''}"
      on:click={() => changePeriod('daily')}
    >
      Daily
    </button>
    <button
      class="period-btn {selectedPeriod === 'weekly' ? 'active' : ''}"
      on:click={() => changePeriod('weekly')}
    >
      Weekly
    </button>
    <button
      class="period-btn {selectedPeriod === 'monthly' ? 'active' : ''}"
      on:click={() => changePeriod('monthly')}
    >
      Monthly
    </button>
    <button
      class="period-btn {selectedPeriod === 'all_time' ? 'active' : ''}"
      on:click={() => changePeriod('all_time')}
    >
      All Time
    </button>
  </div>

  {#if loading}
    <div class="loading-container">
      <p>Loading rankings...</p>
    </div>
  {:else}
    <!-- Top 3 Podium - Users by Operations -->
    {#if userRankings.length >= 3}
      <div class="podium-section">
        <h2 class="section-title">
          <User size={24} /> Top Users by Operations ({selectedPeriod})
        </h2>
        <div class="podium">
          <!-- 2nd Place -->
          <div class="podium-place second">
            <div class="podium-medal">🥈</div>
            <div class="podium-rank">2nd</div>
            <div class="podium-name">{userRankings[1].username}</div>
            <div class="podium-stat">{userRankings[1].total_operations} ops</div>
            <div class="podium-detail">{userRankings[1].success_rate.toFixed(1)}% success</div>
          </div>

          <!-- 1st Place -->
          <div class="podium-place first">
            <div class="podium-medal">🥇</div>
            <div class="podium-rank">1st</div>
            <div class="podium-name">{userRankings[0].username}</div>
            <div class="podium-stat">{userRankings[0].total_operations} ops</div>
            <div class="podium-detail">{userRankings[0].success_rate.toFixed(1)}% success</div>
          </div>

          <!-- 3rd Place -->
          <div class="podium-place third">
            <div class="podium-medal">🥉</div>
            <div class="podium-rank">3rd</div>
            <div class="podium-name">{userRankings[2].username}</div>
            <div class="podium-stat">{userRankings[2].total_operations} ops</div>
            <div class="podium-detail">{userRankings[2].success_rate.toFixed(1)}% success</div>
          </div>
        </div>
      </div>
    {/if}

    <!-- Rankings Grid -->
    <div class="rankings-grid">
      <!-- User Rankings by Operations -->
      <div class="ranking-card">
        <h3 class="card-title">
          <User size={20} /> Top Users (by Operations)
        </h3>
        <div class="ranking-list">
          {#if userRankings.length > 0}
            {#each userRankings.slice(0, 10) as user}
              <div class="ranking-item">
                <div class="rank-badge" style="background: {getMedalColor(user.rank)};">
                  {user.rank}
                </div>
                <div class="ranking-details">
                  <div class="ranking-name">{user.username}</div>
                  <div class="ranking-stats">
                    {user.total_operations} operations • {user.success_rate.toFixed(1)}% success
                  </div>
                </div>
                <div class="ranking-value">
                  {getMedalIcon(user.rank)}
                </div>
              </div>
            {/each}
          {:else}
            <div class="empty-message">No user rankings available</div>
          {/if}
        </div>
      </div>

      <!-- User Rankings by Time -->
      <div class="ranking-card">
        <h3 class="card-title">
          <User size={20} /> Top Users (by Time Spent)
        </h3>
        <div class="ranking-list">
          {#if userRankingsByTime.length > 0}
            {#each userRankingsByTime.slice(0, 10) as user}
              <div class="ranking-item">
                <div class="rank-badge" style="background: {getMedalColor(user.rank)};">
                  {user.rank}
                </div>
                <div class="ranking-details">
                  <div class="ranking-name">{user.username}</div>
                  <div class="ranking-stats">
                    {formatTimeDetailed(user.time_spent)} • {user.active_days} active days
                  </div>
                </div>
                <div class="ranking-value">
                  {getMedalIcon(user.rank)}
                </div>
              </div>
            {/each}
          {:else}
            <div class="empty-message">No time-based rankings available</div>
          {/if}
        </div>
      </div>

      <!-- App Rankings -->
      <div class="ranking-card">
        <h3 class="card-title">
          <Apps size={20} /> Top Apps
        </h3>
        <div class="ranking-list">
          {#if appRankings.length > 0}
            {#each appRankings.slice(0, 10) as app}
              <div class="ranking-item">
                <div class="rank-badge" style="background: {getMedalColor(app.rank)};">
                  {app.rank}
                </div>
                <div class="ranking-details">
                  <div class="ranking-name">{app.tool_name}</div>
                  <div class="ranking-stats">
                    {app.total_operations} operations • {formatTime(app.total_time_seconds)}
                  </div>
                </div>
                <div class="ranking-value">
                  {getMedalIcon(app.rank)}
                </div>
              </div>
            {/each}
          {:else}
            <div class="empty-message">No app rankings available</div>
          {/if}
        </div>
      </div>

      <!-- Function Rankings by Usage -->
      <div class="ranking-card">
        <h3 class="card-title">
          <FunctionIcon size={20} /> Top Functions (by Usage)
        </h3>
        <div class="ranking-list">
          {#if functionRankings.length > 0}
            {#each functionRankings.slice(0, 10) as func}
              <div class="ranking-item">
                <div class="rank-badge" style="background: {getMedalColor(func.rank)};">
                  {func.rank}
                </div>
                <div class="ranking-details">
                  <div class="ranking-name">{func.function_name}</div>
                  <div class="ranking-stats">
                    {func.tool_name} • {func.usage_count} calls
                  </div>
                </div>
                <div class="ranking-value">
                  {getMedalIcon(func.rank)}
                </div>
              </div>
            {/each}
          {:else}
            <div class="empty-message">No function rankings available</div>
          {/if}
        </div>
      </div>

      <!-- Function Rankings by Time -->
      <div class="ranking-card">
        <h3 class="card-title">
          <FunctionIcon size={20} /> Top Functions (by Processing Time)
        </h3>
        <div class="ranking-list">
          {#if functionRankingsByTime.length > 0}
            {#each functionRankingsByTime.slice(0, 10) as func}
              <div class="ranking-item">
                <div class="rank-badge" style="background: {getMedalColor(func.rank)};">
                  {func.rank}
                </div>
                <div class="ranking-details">
                  <div class="ranking-name">{func.function_name}</div>
                  <div class="ranking-stats">
                    {func.tool_name} • {formatTime(func.total_time_seconds)} total
                  </div>
                </div>
                <div class="ranking-value">
                  {getMedalIcon(func.rank)}
                </div>
              </div>
            {/each}
          {:else}
            <div class="empty-message">No time-based function rankings available</div>
          {/if}
        </div>
      </div>
    </div>

    <!-- Detailed Tables -->
    <div class="tables-section">
      <!-- Full User Rankings Table -->
      <div class="card">
        <h3 class="section-title">Complete User Rankings</h3>
        <div class="data-table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th>Rank</th>
                <th>Username</th>
                <th>Operations</th>
                <th>Success Rate</th>
                <th>Avg Duration</th>
              </tr>
            </thead>
            <tbody>
              {#each userRankings as user}
                <tr>
                  <td>
                    <span class="rank-badge-table" style="background: {getMedalColor(user.rank)};">
                      {user.rank}
                    </span>
                  </td>
                  <td class="username-cell">
                    {getMedalIcon(user.rank)} {user.username}
                  </td>
                  <td>{user.total_operations}</td>
                  <td>
                    <span class="success-badge">{user.success_rate.toFixed(1)}%</span>
                  </td>
                  <td>{user.avg_duration ? user.avg_duration.toFixed(2) + 's' : 'N/A'}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  {/if}
</div>

<style>
  .period-selector {
    display: flex;
    gap: 12px;
    margin-bottom: 32px;
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

  /* Podium Section */
  .podium-section {
    margin-bottom: 48px;
  }

  .section-title {
    display: flex;
    align-items: center;
    gap: 12px;
    color: #f4f4f4;
    font-size: 24px;
    font-weight: 600;
    margin-bottom: 24px;
  }

  .podium {
    display: flex;
    justify-content: center;
    align-items: flex-end;
    gap: 24px;
    padding: 40px 20px;
    background: linear-gradient(180deg, #1a1a1a 0%, #262626 100%);
    border-radius: 8px;
    border: 1px solid #393939;
  }

  .podium-place {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 32px 24px;
    background: #2a2a2a;
    border-radius: 8px;
    border: 2px solid;
    min-width: 220px;
    transition: all 0.3s;
  }

  .podium-place:hover {
    transform: translateY(-8px);
  }

  .podium-place.first {
    border-color: #ffd700;
    background: linear-gradient(135deg, #2a2a2a 0%, #3a3000 100%);
    height: 280px;
  }

  .podium-place.second {
    border-color: #c0c0c0;
    background: linear-gradient(135deg, #2a2a2a 0%, #3a3a3a 100%);
    height: 240px;
  }

  .podium-place.third {
    border-color: #cd7f32;
    background: linear-gradient(135deg, #2a2a2a 0%, #3a2a1a 100%);
    height: 200px;
  }

  .podium-medal {
    font-size: 64px;
    margin-bottom: 16px;
  }

  .podium-rank {
    font-size: 18px;
    font-weight: 600;
    color: #c6c6c6;
    margin-bottom: 8px;
  }

  .podium-name {
    font-size: 22px;
    font-weight: 700;
    color: #f4f4f4;
    margin-bottom: 16px;
    text-align: center;
  }

  .podium-stat {
    font-size: 28px;
    font-weight: 600;
    color: #4589ff;
    margin-bottom: 8px;
  }

  .podium-detail {
    font-size: 14px;
    color: #42be65;
  }

  /* Rankings Grid */
  .rankings-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
    gap: 24px;
    margin-bottom: 32px;
  }

  .ranking-card {
    background: #262626;
    border: 1px solid #393939;
    border-radius: 8px;
    padding: 24px;
    transition: all 0.2s;
  }

  .ranking-card:hover {
    border-color: #4589ff;
  }

  .card-title {
    display: flex;
    align-items: center;
    gap: 8px;
    color: #f4f4f4;
    font-size: 18px;
    font-weight: 600;
    margin-bottom: 20px;
    padding-bottom: 12px;
    border-bottom: 1px solid #393939;
  }

  .ranking-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .ranking-item {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 16px;
    background: #1a1a1a;
    border-radius: 6px;
    border: 1px solid #2a2a2a;
    transition: all 0.2s;
  }

  .ranking-item:hover {
    background: #2a2a2a;
    border-color: #4589ff;
    transform: translateX(4px);
  }

  .rank-badge {
    min-width: 36px;
    height: 36px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    color: #161616;
    font-weight: 700;
    font-size: 16px;
  }

  .ranking-details {
    flex: 1;
  }

  .ranking-name {
    color: #f4f4f4;
    font-size: 15px;
    font-weight: 600;
    margin-bottom: 4px;
  }

  .ranking-stats {
    color: #c6c6c6;
    font-size: 13px;
  }

  .ranking-value {
    font-size: 24px;
  }

  .empty-message {
    color: #8d8d8d;
    text-align: center;
    padding: 40px 20px;
  }

  /* Tables Section */
  .tables-section {
    margin-top: 32px;
  }

  .rank-badge-table {
    display: inline-block;
    min-width: 32px;
    height: 32px;
    line-height: 32px;
    text-align: center;
    border-radius: 50%;
    color: #161616;
    font-weight: 700;
    font-size: 14px;
  }

  .username-cell {
    font-weight: 600;
    color: #78a9ff;
  }

  .success-badge {
    display: inline-block;
    background: #24a148;
    color: #ffffff;
    padding: 4px 12px;
    border-radius: 12px;
    font-size: 13px;
    font-weight: 600;
  }
</style>
