<script>
  import { onMount } from 'svelte';
  import adminAPI from '$lib/api/client.js';
  import Chart from 'chart.js/auto';

  // SvelteKit auto-passes these props - declare to avoid warnings
  export const data = {};

  let overviewStats = null;
  let dailyStats = [];
  let toolPopularity = null;
  let loading = true;
  let selectedPeriod = 'daily'; // 'daily', 'weekly', 'monthly'
  let selectedDays = 30;

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
      loading = true;

      // Load comprehensive stats from new API
      const [overview, daily, popularity] = await Promise.all([
        adminAPI.getOverviewStats().catch(() => ({
          active_users: 0,
          today_operations: 0,
          success_rate: 0,
          avg_duration_seconds: 0
        })),
        adminAPI.getDailyStats(selectedDays).catch(() => ({ data: [] })),
        adminAPI.getToolPopularity(selectedDays).catch(() => ({ tools: [] }))
      ]);

      overviewStats = overview;
      dailyStats = daily.data || [];
      toolPopularity = popularity;

      loading = false;

      // Recreate charts with new data
      if (operationsChart) operationsChart.destroy();
      if (successRateChart) successRateChart.destroy();
      if (toolUsageChart) toolUsageChart.destroy();
      if (timeDistributionChart) timeDistributionChart.destroy();

      createCharts();
    } catch (error) {
      console.error('Failed to load stats:', error);
      loading = false;
    }
  }

  async function changePeriod(period) {
    selectedPeriod = period;
    if (period === 'daily') selectedDays = 30;
    else if (period === 'weekly') selectedDays = 90;
    else if (period === 'monthly') selectedDays = 365;

    await loadStats();
  }

  function createCharts() {
    if (!overviewStats || !dailyStats.length) return;

    // Operations Over Time Chart (real data from daily stats)
    if (operationsChartEl) {
      const ctx = operationsChartEl.getContext('2d');

      const labels = dailyStats.map(day => {
        const date = new Date(day.date);
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      });

      const operationsData = dailyStats.map(day => day?.operations || 0);
      const uniqueUsersData = dailyStats.map(day => day?.unique_users || 0);

      operationsChart = new Chart(ctx, {
        type: 'line',
        data: {
          labels: labels,
          datasets: [
            {
              label: 'Operations',
              data: operationsData,
              borderColor: '#4589ff',
              backgroundColor: 'rgba(69, 137, 255, 0.1)',
              tension: 0.4,
              fill: true,
              yAxisID: 'y'
            },
            {
              label: 'Unique Users',
              data: uniqueUsersData,
              borderColor: '#42be65',
              backgroundColor: 'rgba(66, 190, 101, 0.1)',
              tension: 0.4,
              fill: true,
              yAxisID: 'y1'
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          interaction: {
            mode: 'index',
            intersect: false,
          },
          plugins: {
            legend: {
              labels: { color: '#f4f4f4' }
            },
            tooltip: {
              backgroundColor: '#262626',
              titleColor: '#f4f4f4',
              bodyColor: '#c6c6c6',
              borderColor: '#393939',
              borderWidth: 1
            }
          },
          scales: {
            y: {
              type: 'linear',
              display: true,
              position: 'left',
              beginAtZero: true,
              ticks: { color: '#c6c6c6' },
              grid: { color: '#393939' },
              title: {
                display: true,
                text: 'Operations',
                color: '#4589ff'
              }
            },
            y1: {
              type: 'linear',
              display: true,
              position: 'right',
              beginAtZero: true,
              ticks: { color: '#c6c6c6' },
              grid: { drawOnChartArea: false },
              title: {
                display: true,
                text: 'Users',
                color: '#42be65'
              }
            },
            x: {
              ticks: {
                color: '#c6c6c6',
                maxRotation: 45,
                minRotation: 45
              },
              grid: { color: '#393939' }
            }
          }
        }
      });
    }

    // Success Rate Over Time
    if (successRateChartEl && dailyStats.length > 0) {
      const ctx = successRateChartEl.getContext('2d');

      const labels = dailyStats.map(day => {
        const date = new Date(day.date);
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      });

      const successRateData = dailyStats.map(day => {
        if (!day || !day.operations || day.operations === 0) return 0;
        const successOps = day.successful_ops || 0;
        return ((successOps / day.operations) * 100).toFixed(1);
      });

      successRateChart = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: labels,
          datasets: [{
            label: 'Success Rate (%)',
            data: successRateData,
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
            },
            tooltip: {
              backgroundColor: '#262626',
              titleColor: '#f4f4f4',
              bodyColor: '#c6c6c6',
              borderColor: '#393939',
              borderWidth: 1,
              callbacks: {
                label: function(context) {
                  return `Success Rate: ${context.parsed.y}%`;
                }
              }
            }
          },
          scales: {
            y: {
              beginAtZero: true,
              max: 100,
              ticks: {
                color: '#c6c6c6',
                callback: function(value) {
                  return value + '%';
                }
              },
              grid: { color: '#393939' }
            },
            x: {
              ticks: {
                color: '#c6c6c6',
                maxRotation: 45,
                minRotation: 45
              },
              grid: { color: '#393939' }
            }
          }
        }
      });
    }

    // Tool Usage Distribution (Doughnut)
    if (toolUsageChartEl && toolPopularity && toolPopularity.tools && toolPopularity.tools.length > 0) {
      const ctx = toolUsageChartEl.getContext('2d');

      const colors = [
        '#4589ff',
        '#42be65',
        '#ff8389',
        '#78a9ff',
        '#82cfff',
        '#d4bbff',
        '#ffb784',
        '#ff7eb6'
      ];

      toolUsageChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
          labels: toolPopularity.tools.map(t => t.tool_name),
          datasets: [{
            data: toolPopularity.tools.map(t => t.usage_count),
            backgroundColor: colors.slice(0, toolPopularity.tools.length),
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
            },
            tooltip: {
              backgroundColor: '#262626',
              titleColor: '#f4f4f4',
              bodyColor: '#c6c6c6',
              borderColor: '#393939',
              borderWidth: 1,
              callbacks: {
                label: function(context) {
                  const percentage = context.parsed;
                  const label = context.label;
                  const value = context.raw;
                  return `${label}: ${value} ops (${percentage.toFixed(1)}%)`;
                }
              }
            }
          }
        }
      });
    }

    // Average Duration Over Time
    if (timeDistributionChartEl && dailyStats.length > 0) {
      const ctx = timeDistributionChartEl.getContext('2d');

      const labels = dailyStats.map(day => {
        const date = new Date(day.date);
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      });

      const durationData = dailyStats.map(day => (day && typeof day.avg_duration === 'number') ? day.avg_duration : 0);

      timeDistributionChart = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: labels,
          datasets: [{
            label: 'Avg Duration (seconds)',
            data: durationData,
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
            },
            tooltip: {
              backgroundColor: '#262626',
              titleColor: '#f4f4f4',
              bodyColor: '#c6c6c6',
              borderColor: '#393939',
              borderWidth: 1,
              callbacks: {
                label: function(context) {
                  return `Duration: ${context.parsed.y.toFixed(2)}s`;
                }
              }
            }
          },
          scales: {
            y: {
              beginAtZero: true,
              ticks: {
                color: '#c6c6c6',
                callback: function(value) {
                  return value.toFixed(1) + 's';
                }
              },
              grid: { color: '#393939' }
            },
            x: {
              ticks: {
                color: '#c6c6c6',
                maxRotation: 45,
                minRotation: 45
              },
              grid: { color: '#393939' }
            }
          }
        }
      });
    }
  }

  function formatDuration(seconds) {
    if (!seconds) return '0s';
    if (seconds < 60) return `${seconds.toFixed(1)}s`;
    if (seconds < 3600) return `${(seconds / 60).toFixed(1)}m`;
    return `${(seconds / 3600).toFixed(1)}h`;
  }

  function calculateTotalOps() {
    return dailyStats.reduce((sum, day) => sum + day.operations, 0);
  }

  function calculateTotalSuccess() {
    return dailyStats.reduce((sum, day) => sum + day.successful_ops, 0);
  }

  function calculateTotalFailed() {
    const total = calculateTotalOps();
    const success = calculateTotalSuccess();
    return total - success;
  }

  function calculateOverallSuccessRate() {
    const total = calculateTotalOps();
    const success = calculateTotalSuccess();
    return total > 0 ? ((success / total) * 100).toFixed(1) : 0;
  }
</script>

<div class="admin-content">
  <div class="page-header">
    <h1 class="page-title">Statistics & Analytics</h1>
    <p class="page-subtitle">System usage metrics and performance data</p>
  </div>

  <!-- Period Selector -->
  <div class="period-selector">
    <button
      class="period-btn {selectedPeriod === 'daily' ? 'active' : ''}"
      on:click={() => changePeriod('daily')}
    >
      Last 30 Days
    </button>
    <button
      class="period-btn {selectedPeriod === 'weekly' ? 'active' : ''}"
      on:click={() => changePeriod('weekly')}
    >
      Last 90 Days
    </button>
    <button
      class="period-btn {selectedPeriod === 'monthly' ? 'active' : ''}"
      on:click={() => changePeriod('monthly')}
    >
      Last Year
    </button>
  </div>

  {#if loading}
    <div class="loading-container">
      <p>Loading statistics...</p>
    </div>
  {:else if overviewStats && dailyStats.length > 0}
    <!-- Summary Stats -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-icon">📊</div>
        <div class="stat-value">{calculateTotalOps()}</div>
        <div class="stat-label">Total Operations ({selectedDays} days)</div>
      </div>

      <div class="stat-card">
        <div class="stat-icon">✅</div>
        <div class="stat-value">{calculateTotalSuccess()}</div>
        <div class="stat-label">Successful</div>
      </div>

      <div class="stat-card">
        <div class="stat-icon">❌</div>
        <div class="stat-value">{calculateTotalFailed()}</div>
        <div class="stat-label">Failed</div>
      </div>

      <div class="stat-card">
        <div class="stat-icon">📈</div>
        <div class="stat-value">{calculateOverallSuccessRate()}%</div>
        <div class="stat-label">Success Rate</div>
      </div>

      <div class="stat-card">
        <div class="stat-icon">👥</div>
        <div class="stat-value">{overviewStats.active_users}</div>
        <div class="stat-label">Active Users (24h)</div>
      </div>

      <div class="stat-card">
        <div class="stat-icon">🔧</div>
        <div class="stat-value">{toolPopularity?.tools?.length || 0}</div>
        <div class="stat-label">Active Tools</div>
      </div>
    </div>

    <!-- Charts Grid -->
    <div class="charts-grid">
      <div class="chart-card">
        <h3 class="chart-title">Operations & Users Over Time</h3>
        <div class="chart-container">
          <canvas bind:this={operationsChartEl}></canvas>
        </div>
      </div>

      <div class="chart-card">
        <h3 class="chart-title">Success Rate Over Time</h3>
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
        <h3 class="chart-title">Average Duration Over Time</h3>
        <div class="chart-container">
          <canvas bind:this={timeDistributionChartEl}></canvas>
        </div>
      </div>
    </div>

    <!-- Tool Statistics Table -->
    {#if toolPopularity && toolPopularity.tools && toolPopularity.tools.length > 0}
      <div class="card">
        <h3 class="section-title">Tool Performance Details</h3>
        <div class="data-table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th>Tool</th>
                <th>Total Operations</th>
                <th>Usage Share</th>
                <th>Percentage</th>
              </tr>
            </thead>
            <tbody>
              {#each toolPopularity.tools as tool}
                <tr>
                  <td class="tool-name">{tool.tool_name}</td>
                  <td>{tool.usage_count}</td>
                  <td>
                    <div class="usage-bar-container">
                      <div class="usage-bar" style="width: {tool.percentage}%;"></div>
                      <span class="usage-bar-text">{tool.usage_count} ops</span>
                    </div>
                  </td>
                  <td>
                    <span class="percentage-badge">{(tool?.percentage || 0).toFixed(1)}%</span>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
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
  .period-selector {
    display: flex;
    gap: 12px;
    margin-bottom: 24px;
  }

  .period-btn {
    background: #262626;
    border: 1px solid #393939;
    color: #c6c6c6;
    padding: 10px 20px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
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
    font-weight: 500;
  }

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
    grid-template-columns: repeat(auto-fit, minmax(450px, 1fr));
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

  .usage-bar-container {
    position: relative;
    width: 100%;
    height: 28px;
    background: #161616;
    border-radius: 4px;
    overflow: hidden;
  }

  .usage-bar {
    position: absolute;
    left: 0;
    top: 0;
    height: 100%;
    background: linear-gradient(90deg, #4589ff, #78a9ff);
    transition: width 0.3s ease;
  }

  .usage-bar-text {
    position: relative;
    z-index: 1;
    color: #f4f4f4;
    font-size: 12px;
    line-height: 28px;
    padding: 0 12px;
    font-weight: 500;
  }

  .percentage-badge {
    display: inline-block;
    background: #393939;
    color: #78a9ff;
    padding: 4px 12px;
    border-radius: 12px;
    font-size: 13px;
    font-weight: 500;
  }
</style>
