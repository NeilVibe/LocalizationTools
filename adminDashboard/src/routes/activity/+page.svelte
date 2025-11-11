<script>
  import { onMount, onDestroy } from 'svelte';
  import adminAPI from '$lib/api/client.js';
  import { websocket } from '$lib/api/websocket.js';

  // SvelteKit auto-passes these props - declare to avoid warnings
  export const data = {};

  let activities = [];
  let loading = true;
  let isLive = false;
  let unsubscribe;

  onMount(async () => {
    try {
      activities = await adminAPI.getAllLogs({ limit: 50 });
      loading = false;

      // Connect to WebSocket for real-time updates
      websocket.connect();
      isLive = true;

      // Listen for new log entries
      unsubscribe = websocket.on('log_entry', (newLog) => {
        console.log('🔴 LIVE: New activity received!', newLog);
        activities = [newLog, ...activities].slice(0, 50);
      });

    } catch (error) {
      console.error('Failed to load activity:', error);
      loading = false;
    }
  });

  onDestroy(() => {
    if (unsubscribe) unsubscribe();
  });
</script>

<div class="admin-content">
  <div class="page-header">
    <div style="display: flex; justify-content: space-between; align-items: center;">
      <div>
        <h1 class="page-title">
          Live Activity Feed
          {#if isLive}
            <span class="live-indicator"></span>
          {/if}
        </h1>
        <p class="page-subtitle">
          {isLive ? '🔴 LIVE - Updates in real-time' : 'Real-time system operations and events'}
        </p>
      </div>
      {#if isLive}
        <div class="activity-count">
          {activities.length} activities
        </div>
      {/if}
    </div>
  </div>

  {#if loading}
    <div class="loading-container">
      <p>Loading activity...</p>
    </div>
  {:else if activities.length > 0}
    <div class="activity-feed">
      {#each activities as activity}
        <div class="activity-item">
          <div class="activity-icon">
            {activity.status === 'success' ? '✅' : activity.status === 'error' ? '❌' : '⏳'}
          </div>
          <div class="activity-content">
            <div class="activity-title">
              <span class="label">APP:</span>
              <span class="app-name">{activity.tool_name || 'Unknown'}</span>
              <span class="separator">→</span>
              <span class="label">FUNCTION:</span>
              <span class="function-name">{activity.function_name || 'Unknown'}</span>
            </div>
            <div class="activity-meta">
              <span class="meta-item">
                <strong>User:</strong> {activity.username || `ID ${activity.user_id}`}
              </span>
              <span class="meta-separator">•</span>
              <span class="meta-item">
                <strong>Time:</strong> {new Date(activity.timestamp).toLocaleString()}
              </span>
              <span class="meta-separator">•</span>
              <span class="meta-item">
                <strong>Duration:</strong> {activity.duration_seconds ? `${activity.duration_seconds.toFixed(2)}s` : 'N/A'}
              </span>
              <span class="meta-separator">•</span>
              <span class="status-badge {activity.status}">
                {activity.status.toUpperCase()}
              </span>
            </div>
            {#if activity.error_message}
              <div class="error-message">
                ❌ Error: {activity.error_message}
              </div>
            {/if}
          </div>
        </div>
      {/each}
    </div>
  {:else}
    <div class="empty-state">
      <h3>No activity yet</h3>
      <p>Activity will appear here as users perform operations</p>
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

  .activity-count {
    color: #c6c6c6;
    font-size: 0.875rem;
  }

  .activity-feed {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .activity-item {
    display: flex;
    gap: 16px;
    background: #262626;
    border: 1px solid #393939;
    border-radius: 4px;
    padding: 16px;
    transition: all 0.2s;
  }

  .activity-item:hover {
    border-color: #4589ff;
    box-shadow: 0 2px 8px rgba(69, 137, 255, 0.1);
  }

  .activity-icon {
    font-size: 1.5rem;
    flex-shrink: 0;
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .activity-content {
    flex: 1;
  }

  .activity-title {
    font-size: 1rem;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }

  .label {
    font-size: 0.75rem;
    color: #8d8d8d;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .app-name {
    color: #78a9ff;
    font-weight: 600;
    font-size: 1rem;
  }

  .separator {
    color: #4589ff;
    font-weight: 700;
    font-size: 1.2rem;
  }

  .function-name {
    color: #ffb000;
    font-weight: 600;
    font-family: 'Courier New', monospace;
    font-size: 1rem;
  }

  .activity-meta {
    font-size: 0.875rem;
    color: #c6c6c6;
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }

  .meta-item strong {
    color: #8d8d8d;
    font-weight: 500;
  }

  .meta-separator {
    color: #525252;
  }

  .status-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 3px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
  }

  .status-badge.success {
    background: rgba(36, 161, 72, 0.2);
    color: #42be65;
    border: 1px solid #24a148;
  }

  .status-badge.error {
    background: rgba(218, 30, 40, 0.2);
    color: #ff8389;
    border: 1px solid #da1e28;
  }

  .status-badge.pending,
  .status-badge.info {
    background: rgba(69, 137, 255, 0.2);
    color: #78a9ff;
    border: 1px solid #4589ff;
  }

  .error-message {
    margin-top: 8px;
    padding: 8px 12px;
    background: rgba(218, 30, 40, 0.1);
    border-left: 3px solid #da1e28;
    color: #ff8389;
    font-size: 0.875rem;
    border-radius: 2px;
  }

  .empty-state {
    background: #262626;
    border: 1px solid #393939;
    border-radius: 4px;
    padding: 48px 24px;
    text-align: center;
  }

  .empty-state h3 {
    color: #f4f4f4;
    margin-bottom: 8px;
  }

  .empty-state p {
    color: #c6c6c6;
  }
</style>
