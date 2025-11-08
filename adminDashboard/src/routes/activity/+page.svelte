<script>
  import { onMount, onDestroy } from 'svelte';
  import adminAPI from '$lib/api/client.js';
  import { websocket } from '$lib/api/websocket.js';

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
            <span style="display: inline-block; width: 8px; height: 8px; background: #24a148; border-radius: 50%; margin-left: 10px; animation: pulse 2s infinite;"></span>
          {/if}
        </h1>
        <p class="page-subtitle">
          {isLive ? '🔴 LIVE - Updates in real-time' : 'Real-time system operations and events'}
        </p>
      </div>
      {#if isLive}
        <div style="color: var(--cds-text-03); font-size: 0.875rem;">
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
            📊
          </div>
          <div class="activity-content">
            <div class="activity-title">
              {activity.operation || 'Operation'} - {activity.tool_name || 'Unknown Tool'}
            </div>
            <div class="activity-meta">
              User ID: {activity.user_id} • 
              {new Date(activity.timestamp).toLocaleString()} • 
              <span class="status-badge {activity.status === 'completed' ? 'success' : 'info'}">
                {activity.status}
              </span>
            </div>
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
