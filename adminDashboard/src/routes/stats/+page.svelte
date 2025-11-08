<script>
  import { onMount } from 'svelte';
  import adminAPI from '$lib/api/client.js';
  import Chart from 'chart.js/auto';

  let summary = null;
  let toolStats = [];
  let loading = true;

  // Chart instances
  let operationsChartEl;
  let successRateChartEl;
  let toolUsageChartEl;
  let timeDistributionChartEl;

  let operationsChart;
  let successRateChart;
  let toolUsageChart;
  let timeDistributionChart;

  onMount(async () => {
    await loadStats();
    createCharts();
  });

  async function loadStats() {
    try {
      summary = await adminAPI.getStats();
      toolStats = await adminAPI.getToolStats();
      loading = false;
    } catch (error) {
      console.error('Failed to load stats:', error);
      loading = false;
    }
  }

  function createCharts() {
    if (!summary || !toolStats.length) return;

    // Operations Over Time Chart (mock data for now)
    if (operationsChartEl) {
      const ctx = operationsChartEl.getContext('2d');
      operationsChart = new Chart(ctx, {
        type: 'line',
        data: {
          labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
          datasets: [{
            label: 'Operations',
            data: generateMockData(7, summary.total_operations / 7),
            borderColor: '#4589ff',
            backgroundColor: 'rgba(69, 137, 255, 0.1)',
            tension: 0.4,
            fill: true
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              labels: { color: '#f4f4f4' }
            }
          },
          scales: {
            y: {
              beginAtZero: true,
              ticks: { color: '#c6c6c6' },
              grid: { color: '#393939' }
            },
            x: {
              ticks: { color: '#c6c6c6' },
              grid: { color: '#393939' }
            }
          }
        }
      });
    }

    // Success Rate by Tool
    if (successRateChartEl && toolStats.length > 0) {
      const ctx = successRateChartEl.getContext('2d');
      const successRates = toolStats.map(tool => {
        const total = tool.success_count + (tool.error_count || 0);
        return total > 0 ? (tool.success_count / total) * 100 : 0;
      });

      successRateChart = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: toolStats.map(t => t.tool_name),
          datasets: [{
            label: 'Success Rate (%)',
            data: successRates,
            backgroundColor: '#42be65',
            borderColor: '#24a148',
            borderWidth: 1
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              labels: { color: '#f4f4f4' }
            }
          },
          scales: {
            y: {
              beginAtZero: true,
              max: 100,
              ticks: { color: '#c6c6c6' },
              grid: { color: '#393939' }
            },
            x: {
              ticks: { color: '#c6c6c6' },
              grid: { color: '#393939' }
            }
          }
        }
      });
    }

    // Tool Usage Distribution
    if (toolUsageChartEl && toolStats.length > 0) {
      const ctx = toolUsageChartEl.getContext('2d');
      toolUsageChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
          labels: toolStats.map(t => t.tool_name),
          datasets: [{
            data: toolStats.map(t => t.total_operations),
            backgroundColor: [
              '#4589ff',
              '#42be65',
              '#ff8389',
              '#78a9ff',
              '#82cfff',
              '#42be65'
            ],
            borderColor: '#161616',
            borderWidth: 2
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              position: 'bottom',
              labels: { color: '#f4f4f4' }
            }
          }
        }
      });
    }

    // Average Duration by Tool
    if (timeDistributionChartEl && toolStats.length > 0) {
      const ctx = timeDistributionChartEl.getContext('2d');
      timeDistributionChart = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: toolStats.map(t => t.tool_name),
          datasets: [{
            label: 'Avg Duration (seconds)',
            data: toolStats.map(t => t.avg_duration || 0),
            backgroundColor: '#78a9ff',
            borderColor: '#4589ff',
            borderWidth: 1
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              labels: { color: '#f4f4f4' }
            }
          },
          scales: {
            y: {
              beginAtZero: true,
              ticks: { color: '#c6c6c6' },
              grid: { color: '#393939' }
            },
            x: {
              ticks: { color: '#c6c6c6' },
              grid: { color: '#393939' }
            }
          }
        }
      });
    }
  }

  function generateMockData(days, avgValue) {
    return Array.from({ length: days }, () =>
      Math.floor(avgValue * (0.7 + Math.random() * 0.6))
    );
  }

  function formatDuration(seconds) {
    if (!seconds) return '0s';
    if (seconds < 60) return `${seconds.toFixed(1)}s`;
    if (seconds < 3600) return `${(seconds / 60).toFixed(1)}m`;
    return `${(seconds / 3600).toFixed(1)}h`;
  }
</script>

<div class="admin-content">
  <div class="page-header">
    <h1 class="page-title">Statistics & Analytics</h1>
    <p class="page-subtitle">System usage metrics and performance data</p>
  </div>

  {#if loading}
    <div class="loading-container">
      <p>Loading statistics...</p>
    </div>
  {:else if summary}
    <!-- Summary Stats -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-icon">📊</div>
        <div class="stat-value">{summary.total_operations || 0}</div>
        <div class="stat-label">Total Operations</div>
      </div>

      <div class="stat-card">
        <div class="stat-icon">✅</div>
        <div class="stat-value">{summary.successful_operations || 0}</div>
        <div class="stat-label">Successful</div>
      </div>

      <div class="stat-card">
        <div class="stat-icon">❌</div>
        <div class="stat-value">{summary.failed_operations || 0}</div>
        <div class="stat-label">Failed</div>
      </div>

      <div class="stat-card">
        <div class="stat-icon">📈</div>
        <div class="stat-value">
          {summary.total_operations > 0
            ? ((summary.successful_operations / summary.total_operations) * 100).toFixed(1)
            : 0}%
        </div>
        <div class="stat-label">Success Rate</div>
      </div>

      <div class="stat-card">
        <div class="stat-icon">👥</div>
        <div class="stat-value">{summary.total_users || 0}</div>
        <div class="stat-label">Total Users</div>
      </div>

      <div class="stat-card">
        <div class="stat-icon">🔧</div>
        <div class="stat-value">{toolStats.length}</div>
        <div class="stat-label">Active Tools</div>
      </div>
    </div>

    <!-- Charts Grid -->
    <div class="charts-grid">
      <div class="chart-card">
        <h3 class="chart-title">Operations Over Time</h3>
        <div class="chart-container">
          <canvas bind:this={operationsChartEl}></canvas>
        </div>
      </div>

      <div class="chart-card">
        <h3 class="chart-title">Success Rate by Tool</h3>
        <div class="chart-container">
          <canvas bind:this={successRateChartEl}></canvas>
        </div>
      </div>

      <div class="chart-card">
        <h3 class="chart-title">Tool Usage Distribution</h3>
        <div class="chart-container">
          <canvas bind:this={toolUsageChartEl}></canvas>
        </div>
      </div>

      <div class="chart-card">
        <h3 class="chart-title">Average Duration by Tool</h3>
        <div class="chart-container">
          <canvas bind:this={timeDistributionChartEl}></canvas>
        </div>
      </div>
    </div>

    <!-- Tool Statistics Table -->
    {#if toolStats.length > 0}
      <div class="data-table-container">
        <h3 class="section-title">Tool Performance Details</h3>
        <table class="data-table">
          <thead>
            <tr>
              <th>Tool</th>
              <th>Total Ops</th>
              <th>Success</th>
              <th>Failed</th>
              <th>Success Rate</th>
              <th>Avg Duration</th>
              <th>Total Time</th>
            </tr>
          </thead>
          <tbody>
            {#each toolStats as tool}
              <tr>
                <td class="tool-name">{tool.tool_name}</td>
                <td>{tool.total_operations}</td>
                <td class="success-count">{tool.success_count}</td>
                <td class="error-count">{tool.error_count || 0}</td>
                <td>
                  <span class="success-rate">
                    {((tool.success_count / tool.total_operations) * 100).toFixed(1)}%
                  </span>
                </td>
                <td>{formatDuration(tool.avg_duration)}</td>
                <td>{formatDuration(tool.total_duration)}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  {:else}
    <div class="empty-state">
      <h3>No statistics available</h3>
      <p>Statistics will appear once operations are performed</p>
    </div>
  {/if}
</div>

<style>
  .stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 20px;
    margin-bottom: 32px;
  }

  .stat-card {
    background: #262626;
    border: 1px solid #393939;
    border-radius: 4px;
    padding: 24px;
    text-align: center;
    transition: all 0.2s;
  }

  .stat-card:hover {
    border-color: #4589ff;
    transform: translateY(-2px);
  }

  .stat-icon {
    font-size: 32px;
    margin-bottom: 12px;
  }

  .stat-value {
    font-size: 32px;
    font-weight: 600;
    color: #f4f4f4;
    margin-bottom: 8px;
  }

  .stat-label {
    color: #c6c6c6;
    font-size: 14px;
  }

  .charts-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
    gap: 24px;
    margin-bottom: 32px;
  }

  .chart-card {
    background: #262626;
    border: 1px solid #393939;
    border-radius: 4px;
    padding: 24px;
  }

  .chart-title {
    color: #f4f4f4;
    font-size: 18px;
    margin-bottom: 16px;
    font-weight: 500;
  }

  .chart-container {
    height: 300px;
    position: relative;
  }

  .section-title {
    color: #f4f4f4;
    font-size: 20px;
    margin-bottom: 16px;
    font-weight: 500;
  }

  .tool-name {
    font-weight: 500;
    color: #78a9ff;
  }

  .success-count {
    color: #42be65;
  }

  .error-count {
    color: #ff8389;
  }

  .success-rate {
    color: #42be65;
    font-weight: 500;
  }
</style>
