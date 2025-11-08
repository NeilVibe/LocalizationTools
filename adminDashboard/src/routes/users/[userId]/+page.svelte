<script>
  import { onMount, onDestroy } from 'svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import adminAPI from '$lib/api/client.js';
  import websocket from '$lib/api/websocket.js';

  let userId;
  let user = null;
  let logs = [];
  let loading = true;
  let logsLoading = true;
  let error = null;

  // Filters
  let searchQuery = '';
  let statusFilter = 'all';
  let toolFilter = 'all';
  let dateFilter = 'all';

  // Pagination
  let limit = 50;
  let offset = 0;
  let hasMore = true;

  $: userId = $page.params.userId;
  $: filteredLogs = filterLogs(logs, searchQuery, statusFilter, toolFilter, dateFilter);

  onMount(async () => {
    await loadUserData();
    await loadUserLogs();

    // Subscribe to real-time log updates for this user
    websocket.on('log_entry', handleNewLog);
  });

  onDestroy(() => {
    websocket.off('log_entry', handleNewLog);
  });

  function handleNewLog(data) {
    // Only add logs for this specific user
    if (data.user_id === parseInt(userId)) {
      console.log('🔴 LIVE: New log for user', userId, data);
      logs = [data, ...logs];
    }
  }

  async function loadUserData() {
    try {
      user = await adminAPI.getUser(userId);
      loading = false;
    } catch (err) {
      console.error('Failed to load user:', err);
      error = 'Failed to load user data';
      loading = false;
    }
  }

  async function loadUserLogs() {
    try {
      logsLoading = true;
      const params = { limit, offset };
      const response = await adminAPI.getUserLogs(userId, params);
      logs = response;
      hasMore = response.length === limit;
      logsLoading = false;
    } catch (err) {
      console.error('Failed to load user logs:', err);
      logsLoading = false;
    }
  }

  function filterLogs(allLogs, search, status, tool, date) {
    let filtered = allLogs;

    // Search filter
    if (search) {
      const query = search.toLowerCase();
      filtered = filtered.filter(log =>
        log.function_name?.toLowerCase().includes(query) ||
        log.tool_name?.toLowerCase().includes(query) ||
        log.error_message?.toLowerCase().includes(query)
      );
    }

    // Status filter
    if (status !== 'all') {
      filtered = filtered.filter(log => log.status === status);
    }

    // Tool filter
    if (tool !== 'all') {
      filtered = filtered.filter(log => log.tool_name === tool);
    }

    // Date filter
    if (date !== 'all') {
      const now = new Date();
      const cutoff = new Date();

      if (date === 'today') cutoff.setHours(0, 0, 0, 0);
      else if (date === 'week') cutoff.setDate(now.getDate() - 7);
      else if (date === 'month') cutoff.setMonth(now.getMonth() - 1);

      filtered = filtered.filter(log => new Date(log.timestamp) >= cutoff);
    }

    return filtered;
  }

  function resetFilters() {
    searchQuery = '';
    statusFilter = 'all';
    toolFilter = 'all';
    dateFilter = 'all';
  }

  function formatDuration(seconds) {
    if (!seconds) return 'N/A';
    if (seconds < 1) return `${(seconds * 1000).toFixed(0)}ms`;
    if (seconds < 60) return `${seconds.toFixed(1)}s`;
    return `${(seconds / 60).toFixed(1)}m`;
  }

  function getStatusEmoji(status) {
    if (status === 'success') return '✅';
    if (status === 'error') return '❌';
    if (status === 'warning') return '⚠️';
    return '⏳';
  }

  async function exportLogsAsCSV() {
    const csv = [
      ['Timestamp', 'Tool', 'Function', 'Status', 'Duration', 'Error Message'].join(','),
      ...filteredLogs.map(log => [
        new Date(log.timestamp).toISOString(),
        log.tool_name,
        log.function_name,
        log.status,
        log.duration_seconds || 0,
        log.error_message || ''
      ].join(','))
    ].join('\n');

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `user_${userId}_logs_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  async function exportLogsAsJSON() {
    const json = JSON.stringify(filteredLogs, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `user_${userId}_logs_${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }
</script>

<div class="admin-content">
  <div class="page-header">
    <button class="back-button" on:click={() => goto('/users')}>
      ← Back to Users
    </button>

    {#if loading}
      <h1 class="page-title">Loading...</h1>
    {:else if user}
      <div class="user-header">
        <h1 class="page-title">{user.username}</h1>
        <div class="user-meta">
          <span class="meta-item">ID: {user.user_id}</span>
          <span class="meta-item">Role: {user.role || 'user'}</span>
          <span class="meta-item">Email: {user.email || 'N/A'}</span>
          <span class="meta-item">Joined: {new Date(user.created_at).toLocaleDateString()}</span>
        </div>
      </div>
    {:else}
      <h1 class="page-title">User not found</h1>
    {/if}
  </div>

  {#if error}
    <div class="error-state">
      <h3>Error</h3>
      <p>{error}</p>
    </div>
  {:else if !loading && user}
    <!-- Filters Section -->
    <div class="filters-section">
      <div class="filters-row">
        <input
          type="text"
          placeholder="Search logs..."
          bind:value={searchQuery}
          class="search-input"
        />

        <select bind:value={statusFilter} class="filter-select">
          <option value="all">All Statuses</option>
          <option value="success">Success</option>
          <option value="error">Error</option>
          <option value="warning">Warning</option>
          <option value="pending">Pending</option>
        </select>

        <select bind:value={toolFilter} class="filter-select">
          <option value="all">All Tools</option>
          <option value="XLSTransfer">XLSTransfer</option>
        </select>

        <select bind:value={dateFilter} class="filter-select">
          <option value="all">All Time</option>
          <option value="today">Today</option>
          <option value="week">Last Week</option>
          <option value="month">Last Month</option>
        </select>

        <button class="btn-secondary" on:click={resetFilters}>
          Reset Filters
        </button>
      </div>

      <div class="actions-row">
        <span class="results-count">{filteredLogs.length} logs found</span>
        <div class="export-buttons">
          <button class="btn-secondary" on:click={exportLogsAsCSV}>
            Export CSV
          </button>
          <button class="btn-secondary" on:click={exportLogsAsJSON}>
            Export JSON
          </button>
        </div>
      </div>
    </div>

    <!-- Logs Table -->
    {#if logsLoading}
      <div class="loading-container">
        <p>Loading user activity...</p>
      </div>
    {:else if filteredLogs.length > 0}
      <div class="data-table-container">
        <table class="data-table logs-table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Tool</th>
              <th>Function</th>
              <th>Status</th>
              <th>Duration</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody>
            {#each filteredLogs as log}
              <tr class="log-row {log.status}">
                <td class="timestamp">
                  {new Date(log.timestamp).toLocaleString()}
                </td>
                <td class="tool-name">{log.tool_name}</td>
                <td class="function-name">{log.function_name}</td>
                <td class="status-cell">
                  <span class="status-badge {log.status}">
                    {getStatusEmoji(log.status)} {log.status}
                  </span>
                </td>
                <td class="duration">{formatDuration(log.duration_seconds)}</td>
                <td class="details">
                  {#if log.error_message}
                    <span class="error-text">{log.error_message}</span>
                  {:else if log.file_info}
                    <span class="file-info">
                      {log.file_info.filename || 'File processed'}
                    </span>
                  {:else}
                    <span class="success-text">Completed successfully</span>
                  {/if}
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {:else}
      <div class="empty-state">
        <h3>No activity found</h3>
        <p>This user hasn't performed any operations yet</p>
      </div>
    {/if}
  {/if}
</div>

<style>
  .back-button {
    background: transparent;
    border: 1px solid #393939;
    color: #f4f4f4;
    padding: 8px 16px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
    margin-bottom: 16px;
    transition: all 0.2s;
  }

  .back-button:hover {
    border-color: #4589ff;
    color: #4589ff;
  }

  .user-header {
    margin-bottom: 24px;
  }

  .user-meta {
    display: flex;
    gap: 24px;
    margin-top: 8px;
    font-size: 14px;
    color: #c6c6c6;
  }

  .meta-item {
    padding: 4px 0;
  }

  .filters-section {
    background: #262626;
    border: 1px solid #393939;
    border-radius: 4px;
    padding: 20px;
    margin-bottom: 24px;
  }

  .filters-row {
    display: flex;
    gap: 12px;
    margin-bottom: 16px;
    flex-wrap: wrap;
  }

  .search-input {
    flex: 1;
    min-width: 200px;
    background: #161616;
    border: 1px solid #393939;
    color: #f4f4f4;
    padding: 10px 12px;
    border-radius: 4px;
    font-size: 14px;
  }

  .search-input:focus {
    outline: none;
    border-color: #4589ff;
  }

  .filter-select {
    background: #161616;
    border: 1px solid #393939;
    color: #f4f4f4;
    padding: 10px 12px;
    border-radius: 4px;
    font-size: 14px;
    cursor: pointer;
  }

  .filter-select:focus {
    outline: none;
    border-color: #4589ff;
  }

  .btn-secondary {
    background: transparent;
    border: 1px solid #393939;
    color: #f4f4f4;
    padding: 10px 16px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
    transition: all 0.2s;
  }

  .btn-secondary:hover {
    border-color: #4589ff;
    color: #4589ff;
  }

  .actions-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .results-count {
    color: #c6c6c6;
    font-size: 14px;
  }

  .export-buttons {
    display: flex;
    gap: 8px;
  }

  .logs-table {
    width: 100%;
  }

  .log-row.error {
    background: rgba(218, 30, 40, 0.05);
  }

  .log-row.success {
    background: rgba(36, 161, 72, 0.05);
  }

  .timestamp {
    font-size: 13px;
    color: #c6c6c6;
  }

  .tool-name {
    font-weight: 500;
  }

  .function-name {
    color: #78a9ff;
  }

  .status-cell {
    text-align: center;
  }

  .duration {
    font-family: 'Courier New', monospace;
    font-size: 13px;
  }

  .details {
    font-size: 13px;
  }

  .error-text {
    color: #ff8389;
  }

  .success-text {
    color: #42be65;
  }

  .file-info {
    color: #c6c6c6;
  }

  .error-state {
    background: rgba(218, 30, 40, 0.1);
    border: 1px solid #da1e28;
    border-radius: 4px;
    padding: 24px;
    text-align: center;
  }

  .error-state h3 {
    color: #ff8389;
    margin-bottom: 8px;
  }
</style>
