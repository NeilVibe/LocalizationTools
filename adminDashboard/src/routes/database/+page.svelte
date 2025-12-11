<script>
  import { onMount } from 'svelte';
  import { adminAPI } from '$lib/api/client.js';

  // SvelteKit auto-passes these props - declare them to avoid warnings
  export let params = undefined;

  let dbStats = null;
  let loading = true;
  let error = null;
  let expandedTables = {};

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

  onMount(() => {
    loadDatabaseStats();
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
      <button class="retry-btn" on:click={loadDatabaseStats}>Retry</button>
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
                  on:click={() => toggleTable(table.name)}
                  on:keydown={(e) => e.key === 'Enter' && toggleTable(table.name)}
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
</style>
