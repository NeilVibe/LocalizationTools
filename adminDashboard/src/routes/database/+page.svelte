<script>
  import { onMount } from 'svelte';
  import { adminAPI } from '$lib/api/client.js';

  // Svelte 5: Reactive state
  let dbStats = $state(null);
  let loading = $state(true);
  let error = $state(null);
  let expandedTables = $state({});
  let dbHealth = $state(null);
  let dbPoolStats = $state(null);
  let refreshInterval = $state(null);

  async function loadDatabaseStats() {
    loading = true;
    error = null;
    try {
      dbStats = await adminAPI.request('/admin/stats/database');
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  }

  async function loadDbHealth() {
    try {
      dbHealth = await adminAPI.request('/admin/db/health');
    } catch (e) {
      console.warn('DB health check failed:', e);
    }
  }

  async function loadDbPoolStats() {
    try {
      dbPoolStats = await adminAPI.request('/admin/db/stats');
    } catch (e) {
      console.warn('DB pool stats failed:', e);
    }
  }

  async function loadAll() {
    await Promise.all([loadDatabaseStats(), loadDbHealth(), loadDbPoolStats()]);
  }

  function toggleTable(table) {
    expandedTables[table] = !expandedTables[table];
    expandedTables = { ...expandedTables };
  }

  function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  function formatNumber(num) {
    return new Intl.NumberFormat().format(num);
  }

  onMount(async () => {
    await loadAll();
    refreshInterval = setInterval(loadAll, 5000);
    return () => {
      if (refreshInterval) clearInterval(refreshInterval);
    };
  });
</script>

<div class="admin-content">
  <div class="page-header">
    <h1 class="page-title">Database Monitoring</h1>
    <p class="page-subtitle">PostgreSQL database statistics and table information</p>
  </div>

  {#if loading}
    <div class="loading-container">
      <span>Loading database statistics...</span>
    </div>
  {:else if error}
    <div class="error-container">
      <div class="error-icon">!</div>
      <div class="error-text">
        <strong>Error loading database stats</strong>
        <p>{error}</p>
      </div>
      <button class="retry-btn" onclick={loadAll}>Retry</button>
    </div>
  {:else if dbStats}
    <!-- Overview Stats -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-icon">DB</div>
        <div class="stat-value">{formatBytes(dbStats.size_bytes || 0)}</div>
        <div class="stat-label">Database Size</div>
      </div>
      <div class="stat-card">
        <div class="stat-icon">TBL</div>
        <div class="stat-value">{dbStats.tables?.length || 0}</div>
        <div class="stat-label">Tables</div>
      </div>
      <div class="stat-card">
        <div class="stat-icon">ROW</div>
        <div class="stat-value">{formatNumber(dbStats.total_rows || 0)}</div>
        <div class="stat-label">Total Rows</div>
      </div>
      <div class="stat-card">
        <div class="stat-icon">IDX</div>
        <div class="stat-value">{dbStats.indexes_count || 0}</div>
        <div class="stat-label">Indexes</div>
      </div>
    </div>

    <!-- Connection Monitor -->
    {#if dbPoolStats?.connection_pool}
      {@const pool = dbPoolStats.connection_pool}
      {@const maxConn = pool.max_connections || 250}
      {@const activeConn = pool.active_connections || 0}
      {@const idleConn = pool.idle_connections || 0}
      {@const pct = Math.round((activeConn / maxConn) * 100)}
      <div class="monitor-card">
        <h3>Connections</h3>
        <div class="stat-row">
          <span class="stat-label">Active: {activeConn} / {maxConn}</span>
          <span class="stat-value" class:good={pct < 50} class:caution={pct >= 50 && pct < 80} class:warning={pct >= 80}>{pct}%</span>
        </div>
        <div class="progress-bar-container">
          <div class="progress-bar" class:good={pct < 50} class:caution={pct >= 50 && pct < 80} class:warning={pct >= 80} style="width: {pct}%"></div>
        </div>
        <div class="stat-details">
          Active: {activeConn} | Idle: {idleConn} | Waiting: {pool.waiting_connections || 0}
        </div>
      </div>
    {/if}

    <!-- Cache Performance -->
    {#if dbPoolStats?.performance}
      {@const perf = dbPoolStats.performance}
      {@const hitRatio = perf.cache_hit_ratio || 0}
      <div class="monitor-card">
        <h3>Cache Performance</h3>
        <div class="stat-row">
          <span class="stat-label">Hit Ratio</span>
          <span class="stat-value" class:good={hitRatio > 99} class:caution={hitRatio > 95 && hitRatio <= 99} class:warning={hitRatio <= 95}>{hitRatio.toFixed(1)}%</span>
        </div>
        <div class="progress-bar-container">
          <div class="progress-bar" class:good={hitRatio > 99} class:caution={hitRatio > 95 && hitRatio <= 99} class:warning={hitRatio <= 95} style="width: {hitRatio}%"></div>
        </div>
      </div>
    {/if}

    <!-- Health Recommendations -->
    {#if dbHealth?.issues?.length > 0}
      <div class="monitor-card">
        <h3>Health Check</h3>
        {#each dbHealth.issues as issue (issue.message)}
          <div class="health-issue" class:warning-bg={issue.severity === 'warning'} class:info-bg={issue.severity !== 'warning'}>
            <span class="issue-icon">{issue.severity === 'warning' ? '⚠️' : 'ℹ️'}</span>
            <span>{issue.message}</span>
          </div>
        {/each}
        {#if dbHealth.recommendations?.length > 0}
          {#each dbHealth.recommendations as rec (rec)}
            <div class="health-rec">💡 {rec}</div>
          {/each}
        {/if}
      </div>
    {/if}

    <!-- Database Tree View -->
    <div class="db-tree">
      <div class="tree-header">
        <span class="tree-icon">DB</span>
        <span class="tree-title">localizationtools.db</span>
        <span class="tree-badge">{formatBytes(dbStats.size_bytes || 0)}</span>
      </div>

      <div class="tree-content">
        <!-- Tables Section -->
        <div class="tree-section">
          <div class="section-header">
            <span class="tree-char">├─</span>
            <span class="section-icon">TBL</span>
            <span class="section-title">Tables ({dbStats.tables?.length || 0})</span>
          </div>

          {#if dbStats.tables && dbStats.tables.length > 0}
            {#each dbStats.tables as table, idx}
              <div class="table-item">
                <div
                  class="table-header"
                  onclick={() => toggleTable(table.name)}
                  onkeydown={(e) => e.key === 'Enter' && toggleTable(table.name)}
                  role="button"
                  tabindex="0"
                >
                  <span class="tree-char">{idx === dbStats.tables.length - 1 ? '│  └─' : '│  ├─'}</span>
                  <span class="expand-icon">{expandedTables[table.name] ? '▼' : '▶'}</span>
                  <span class="table-name">{table.name}</span>
                  <span class="table-count">{formatNumber(table.row_count)} rows</span>
                </div>

                {#if expandedTables[table.name]}
                  <div class="table-details">
                    {#if table.columns && table.columns.length > 0}
                      <div class="columns-header">
                        <span class="tree-char">{idx === dbStats.tables.length - 1 ? '      ├─' : '│     ├─'}</span>
                        <span class="detail-label">Columns ({table.columns.length})</span>
                      </div>
                      {#each table.columns as col, cidx}
                        <div class="column-item">
                          <span class="tree-char">{idx === dbStats.tables.length - 1 ? '      │  ' : '│     │  '}{cidx === table.columns.length - 1 ? '└─' : '├─'}</span>
                          <span class="column-name">{col.name}</span>
                          <span class="column-type">{col.type}</span>
                          {#if col.pk}
                            <span class="column-badge pk">PK</span>
                          {/if}
                          {#if col.notnull}
                            <span class="column-badge notnull">NOT NULL</span>
                          {/if}
                        </div>
                      {/each}
                    {/if}

                    {#if table.indexes && table.indexes.length > 0}
                      <div class="indexes-header">
                        <span class="tree-char">{idx === dbStats.tables.length - 1 ? '      └─' : '│     └─'}</span>
                        <span class="detail-label">Indexes ({table.indexes.length})</span>
                      </div>
                      {#each table.indexes as index, iidx}
                        <div class="index-item">
                          <span class="tree-char">{idx === dbStats.tables.length - 1 ? '         ' : '│        '}{iidx === table.indexes.length - 1 ? '└─' : '├─'}</span>
                          <span class="index-name">{index}</span>
                        </div>
                      {/each}
                    {/if}
                  </div>
                {/if}
              </div>
            {/each}
          {:else}
            <div class="no-data">
              <span class="tree-char">│  └─</span>
              <span class="empty-text">No tables found</span>
            </div>
          {/if}
        </div>

        <!-- Database Info Section -->
        <div class="tree-section">
          <div class="section-header">
            <span class="tree-char">└─</span>
            <span class="section-icon">INFO</span>
            <span class="section-title">Database Info</span>
          </div>
          <div class="info-items">
            <div class="info-item">
              <span class="tree-char">   ├─</span>
              <span class="info-label">Path:</span>
              <span class="info-value">{dbStats.path || 'N/A'}</span>
            </div>
            <div class="info-item">
              <span class="tree-char">   ├─</span>
              <span class="info-label">PostgreSQL Version:</span>
              <span class="info-value">{dbStats.postgres_version || dbStats.sqlite_version || 'N/A'}</span>
            </div>
            <div class="info-item">
              <span class="tree-char">   ├─</span>
              <span class="info-label">Page Size:</span>
              <span class="info-value">{formatBytes(dbStats.page_size || 0)}</span>
            </div>
            <div class="info-item">
              <span class="tree-char">   └─</span>
              <span class="info-label">Last Modified:</span>
              <span class="info-value">{dbStats.last_modified || 'N/A'}</span>
            </div>
          </div>
        </div>
      </div>
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

  .db-tree {
    background: #161616;
    border: 1px solid #393939;
    border-radius: 4px;
    font-family: 'Consolas', 'Courier New', monospace;
    overflow: hidden;
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
    background: #4589ff;
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

  .tree-badge {
    margin-left: auto;
    color: #8d8d8d;
    font-size: 0.8rem;
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

  .table-item {
    margin-left: 0;
  }

  .table-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.25rem 0;
    cursor: pointer;
    border-radius: 2px;
  }

  .table-header:hover {
    background: rgba(69, 137, 255, 0.1);
  }

  .expand-icon {
    color: #6f6f6f;
    font-size: 0.7rem;
    min-width: 12px;
  }

  .table-name {
    color: #ffb000;
    font-weight: 500;
  }

  .table-count {
    color: #6f6f6f;
    font-size: 0.75rem;
    margin-left: auto;
  }

  .table-details {
    padding-left: 0;
  }

  .columns-header, .indexes-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.25rem 0;
    color: #78a9ff;
    font-size: 0.75rem;
  }

  .detail-label {
    color: #78a9ff;
    font-weight: 500;
  }

  .column-item, .index-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.125rem 0;
    font-size: 0.75rem;
  }

  .column-name {
    color: #c6c6c6;
    min-width: 120px;
  }

  .column-type {
    color: #8d8d8d;
    font-size: 0.7rem;
  }

  .column-badge {
    font-size: 0.6rem;
    padding: 1px 4px;
    border-radius: 2px;
    font-weight: 600;
  }

  .column-badge.pk {
    background: rgba(36, 161, 72, 0.2);
    color: #24a148;
  }

  .column-badge.notnull {
    background: rgba(241, 194, 27, 0.2);
    color: #f1c21b;
  }

  .index-name {
    color: #a8a8a8;
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
    min-width: 120px;
  }

  .info-value {
    color: #c6c6c6;
    font-size: 0.8rem;
    word-break: break-all;
  }

  .no-data {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.25rem 0;
  }

  .empty-text {
    color: #6f6f6f;
    font-style: italic;
  }

  .monitor-card {
    background: var(--cds-layer-01, #262626);
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 16px;
  }
  .monitor-card h3 {
    font-size: 14px;
    font-weight: 600;
    margin-bottom: 12px;
    color: var(--cds-text-primary, #f4f4f4);
  }
  .stat-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
  }
  .stat-label { color: var(--cds-text-secondary, #c6c6c6); font-size: 13px; }
  .stat-value { font-size: 18px; font-weight: 600; }
  .good { color: #42be65; }
  .caution { color: #f1c21b; }
  .warning { color: #da1e28; }
  .stat-details { font-size: 12px; color: var(--cds-text-secondary, #c6c6c6); margin-top: 8px; }
  .progress-bar-container {
    background: var(--cds-layer-02, #393939);
    border-radius: 4px;
    height: 8px;
    overflow: hidden;
  }
  .progress-bar {
    height: 100%;
    border-radius: 4px;
    transition: width 0.3s ease;
  }
  .progress-bar.good { background: linear-gradient(90deg, #42be65, #24a148); }
  .progress-bar.caution { background: linear-gradient(90deg, #f1c21b, #d2a106); }
  .progress-bar.warning { background: linear-gradient(90deg, #da1e28, #ba1b23); }
  .health-issue {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px;
    font-size: 13px;
    border-radius: 4px;
    margin-bottom: 4px;
  }
  .warning-bg { background: rgba(241, 194, 27, 0.1); color: #f1c21b; }
  .info-bg { background: rgba(66, 190, 101, 0.1); color: #42be65; }
  .health-rec { font-size: 12px; color: var(--cds-text-secondary, #c6c6c6); padding: 4px 8px; }
</style>
