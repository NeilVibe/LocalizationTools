<script>
  import {
    DataTable,
    Toolbar,
    ToolbarContent,
    ToolbarSearch,
    Button,
    ProgressBar,
    Tag,
    InlineLoading,
    ToastNotification
  } from "carbon-components-svelte";
  import { TrashCan, Renew } from "carbon-icons-svelte";
  import { onMount, onDestroy } from "svelte";
  import { get } from "svelte/store";
  import { api } from "$lib/api/client.js";
  import { websocket } from "$lib/api/websocket.js";
  import { isAuthenticated, user, serverUrl } from "$lib/stores/app.js";

  // API base URL from store (never hardcode!)
  const API_BASE = get(serverUrl);
  import { logger } from "$lib/utils/logger.js";
  import {
    activeOperations as frontendOperations,
    completedHistory,
    clearCompletedHistory
  } from "$lib/stores/globalProgress.js";

  // Svelte 5 Runes - Task data from backend (ActiveOperation)
  let backendTasks = $state([]);
  let isLoading = $state(false);
  let showNotification = $state(false);
  let notificationMessage = $state('');
  let notificationType = $state('success');

  /**
   * Transform frontend operation to task format (matching backend format)
   */
  function transformFrontendOperation(op) {
    const startDate = new Date(op.startTime);
    const timestamp = startDate.toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    });

    // Calculate duration
    let duration = '-';
    const now = Date.now();
    const seconds = Math.round((op.endTime || now) - op.startTime) / 1000;

    if (seconds < 60) {
      duration = `${Math.round(seconds)}s`;
    } else {
      const minutes = Math.floor(seconds / 60);
      const secs = Math.round(seconds % 60);
      duration = op.status === 'running' ? `${minutes}m ${secs}s (running)` : `${minutes}m ${secs}s`;
    }

    // Build details string from metadata
    let details = null;
    if (op.metadata) {
      const parts = [];
      if (op.metadata.filename) parts.push(`File: ${op.metadata.filename}`);
      if (op.metadata.rowCount) parts.push(`${op.metadata.rowCount} rows`);
      if (op.metadata.pairs) parts.push(`${op.metadata.pairs} pairs`);
      if (op.metadata.matches) parts.push(`${op.metadata.matches} matches`);
      if (parts.length > 0) details = parts.join(' | ');
    }

    return {
      id: op.id,
      name: op.function || 'Unknown',
      app: op.tool || 'Unknown',
      status: op.status || 'running',
      progress: Math.round(op.progress || 0),
      current_step: op.message || null,
      details, // New field for metadata display
      timestamp,
      duration,
      source: 'frontend' // Mark as frontend operation
    };
  }

  // Svelte 5: Derived - Merge frontend active, frontend history, and backend tasks
  let tasks = $derived((() => {
    // Transform frontend active operations
    const frontendTasksList = $frontendOperations.map(transformFrontendOperation);

    // Transform completed history (from globalProgress store)
    const historyTasks = $completedHistory.map(transformFrontendOperation);

    // Get all existing IDs to avoid duplicates
    const activeIds = new Set(frontendTasksList.map(t => t.id));
    const backendIds = new Set(backendTasks.map(t => t.id));

    // Filter frontend tasks that aren't already in backend (no duplicates)
    const uniqueFrontendTasks = frontendTasksList.filter(t => !backendIds.has(t.id));

    // Filter history tasks that aren't in active or backend
    const uniqueHistoryTasks = historyTasks.filter(t =>
      !activeIds.has(t.id) && !backendIds.has(t.id)
    );

    // Merge: active first, then history, then backend
    return [...uniqueFrontendTasks, ...uniqueHistoryTasks, ...backendTasks].sort((a, b) => {
      // Sort by timestamp (most recent first)
      return new Date(b.timestamp) - new Date(a.timestamp);
    });
  })());

  // WebSocket unsubscribe functions
  let unsubscribeOperationStart;
  let unsubscribeProgressUpdate;
  let unsubscribeOperationComplete;
  let unsubscribeOperationFailed;

  /**
   * Transform ActiveOperation to task format
   */
  function transformOperationToTask(operation) {
    // Format timestamp in user's local timezone
    const date = new Date(operation.started_at);
    const timestamp = date.toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    });

    // Calculate duration (if completed)
    let duration = '-';
    if (operation.completed_at && operation.started_at) {
      const start = new Date(operation.started_at);
      const end = new Date(operation.completed_at);
      const seconds = Math.round((end - start) / 1000);

      if (seconds < 60) {
        duration = `${seconds}s`;
      } else {
        const minutes = Math.floor(seconds / 60);
        const secs = seconds % 60;
        duration = `${minutes}m ${secs}s`;
      }
    } else if (operation.status === 'running') {
      // Calculate running duration
      const start = new Date(operation.started_at);
      const now = new Date();
      const seconds = Math.round((now - start) / 1000);

      if (seconds < 60) {
        duration = `${seconds}s`;
      } else {
        const minutes = Math.floor(seconds / 60);
        const secs = seconds % 60;
        duration = `${minutes}m ${secs}s (running)`;
      }
    }

    return {
      id: operation.operation_id.toString(),
      name: operation.operation_name || 'Unknown',
      app: operation.tool_name || 'Unknown',
      status: operation.status || 'pending',
      progress: Math.round(operation.progress_percentage || 0),
      current_step: operation.current_step || null,
      timestamp,
      duration
    };
  }

  /**
   * Fetch tasks from backend (ActiveOperation API)
   * Uses smart updates to prevent UI flickering
   */
  async function fetchTasks(showLoading = false) {
    const startTime = performance.now();
    if (showLoading) {
      isLoading = true;
    }

    // Check if user is logged in
    const token = localStorage.getItem('auth_token');
    if (!token) {
      // Silently skip fetch if not logged in (expected on initial load)
      isLoading = false;
      backendTasks = []; // Show empty task list
      return;
    }

    logger.apiCall("/api/progress/operations", "GET");

    try {
      // Fetch ALL recent operations (not just running)
      // This shows users their task history including completed/failed tasks
      const response = await fetch(`${API_BASE}/api/progress/operations`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      const elapsed = performance.now() - startTime;

      if (response.ok) {
        const operations = await response.json();

        if (Array.isArray(operations)) {
          const newTasks = operations.map(transformOperationToTask);

          // Smart update: only update if tasks actually changed
          // This prevents flickering by avoiding unnecessary re-renders
          if (!areTasksEqual(backendTasks, newTasks)) {
            backendTasks = newTasks;

            logger.success("Backend tasks updated", {
              task_count: backendTasks.length,
              elapsed_ms: elapsed.toFixed(2)
            });
          }
        }
      } else {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
    } catch (error) {
      const elapsed = performance.now() - startTime;

      logger.error("Failed to fetch tasks", {
        error: error.message,
        error_type: error.name,
        elapsed_ms: elapsed.toFixed(2)
      });

      // Don't show notification for auth errors (user might not be logged in yet)
      if (!error.message.includes('401') && !error.message.includes('Unauthorized')) {
        showNotificationMessage('Failed to load tasks', 'error');
      }
    } finally {
      if (showLoading) {
        isLoading = false;
      }
    }
  }

  /**
   * Compare two task arrays to see if they're meaningfully different
   * Ignores duration changes for running tasks to prevent flicker
   */
  function areTasksEqual(oldTasks, newTasks) {
    if (oldTasks.length !== newTasks.length) return false;

    for (let i = 0; i < oldTasks.length; i++) {
      const oldTask = oldTasks[i];
      const newTask = newTasks[i];

      // Compare key fields (ignore duration for running tasks)
      if (oldTask.id !== newTask.id ||
          oldTask.name !== newTask.name ||
          oldTask.app !== newTask.app ||
          oldTask.status !== newTask.status ||
          oldTask.progress !== newTask.progress ||
          oldTask.current_step !== newTask.current_step) {
        return false;
      }

      // For completed/failed tasks, also compare duration
      if (oldTask.status !== 'running' && oldTask.duration !== newTask.duration) {
        return false;
      }
    }

    return true;
  }

  /**
   * Show notification
   */
  function showNotificationMessage(message, type = 'success') {
    notificationMessage = message;
    notificationType = type;
    showNotification = true;
    setTimeout(() => {
      showNotification = false;
    }, 5000);
  }

  const headers = [
    { key: "name", value: "Task Name" },
    { key: "app", value: "App" },
    { key: "status", value: "Status" },
    { key: "progress", value: "Progress" },
    { key: "details", value: "Details" },
    { key: "timestamp", value: "Started" },
    { key: "duration", value: "Duration" }
  ];

  let filteredRowIds = $state([]);

  function getStatusColor(status) {
    switch(status) {
      case 'completed': return 'green';
      case 'running': return 'blue';
      case 'failed': return 'red';
      case 'cancelled': return 'gray';
      case 'pending': return 'gray';
      default: return 'gray';
    }
  }

  /**
   * Clear all tasks: completed, failed, AND zombie running tasks (>60 min)
   */
  async function clearHistory() {
    const startTime = performance.now();

    // Identify zombie tasks: running for over 60 minutes
    const zombieThresholdMs = 60 * 60 * 1000; // 60 minutes
    const now = Date.now();

    const isZombie = (task) => {
      if (task.status !== 'running') return false;
      // Parse duration string like "1962m 49s"
      if (task.duration?.includes('m')) {
        const minutes = parseInt(task.duration.split('m')[0]) || 0;
        return minutes >= 60;
      }
      return false;
    };

    // Get backend tasks to delete: completed, failed, OR zombie running
    const backendToDelete = backendTasks.filter(t =>
      t.status === 'completed' || t.status === 'failed' || isZombie(t)
    );

    // Count frontend history
    const frontendHistoryCount = $completedHistory.length;
    const totalToDelete = backendToDelete.length + frontendHistoryCount;

    logger.userAction("Clear All button clicked", {
      backend_tasks: backendToDelete.length,
      frontend_history: frontendHistoryCount,
      zombies: backendToDelete.filter(isZombie).length
    });

    if (totalToDelete === 0) {
      logger.info("No tasks to clear");
      showNotificationMessage('No tasks to clear', 'info');
      return;
    }

    isLoading = true;
    try {
      logger.info("Deleting tasks", {
        backend_count: backendToDelete.length,
        frontend_count: frontendHistoryCount
      });

      // Clear frontend history first
      clearCompletedHistory();

      // Delete backend tasks (including zombies)
      if (backendToDelete.length > 0) {
        const token = localStorage.getItem('auth_token');
        for (const task of backendToDelete) {
          await fetch(`${API_BASE}/api/progress/operations/${task.id}`, {
            method: 'DELETE',
            headers: {
              'Authorization': `Bearer ${token}`
            }
          });
        }
        // Remove deleted tasks from local array
        const deletedIds = new Set(backendToDelete.map(t => t.id));
        backendTasks = backendTasks.filter(t => !deletedIds.has(t.id));
      }

      const elapsed = performance.now() - startTime;

      logger.success("All tasks cleared", {
        deleted_count: totalToDelete,
        remaining_count: backendTasks.length,
        elapsed_ms: elapsed.toFixed(2)
      });

      showNotificationMessage(`Cleared ${totalToDelete} tasks (including zombies)`, 'success');

      // Refresh to ensure UI is in sync
      await fetchTasks();
    } catch (error) {
      const elapsed = performance.now() - startTime;

      logger.error("Failed to clear tasks", {
        error: error.message,
        error_type: error.name,
        tasks_to_delete: totalToDelete,
        elapsed_ms: elapsed.toFixed(2)
      });

      showNotificationMessage('Failed to clear tasks', 'error');
    } finally {
      isLoading = false;
    }
  }

  // REMOVED: cleanupStaleTasks function - functionality merged into clearHistory
  // The "Clean Stale" button was confusing and redundant. Now "Clear All" handles everything.

  /**
   * DEPRECATED - left for reference, functionality merged into clearHistory
   */
  async function cleanupStaleTasks_DEPRECATED() {
    const startTime = performance.now();
    const staleRunningTasks = backendTasks.filter(t =>
      t.status === 'running' && t.duration && t.duration.includes('m')
    );

    if (staleRunningTasks.length === 0) {
      showNotificationMessage('No stale running tasks found', 'info');
      return;
    }

    logger.userAction("Cleanup stale tasks clicked", {
      stale_count: staleRunningTasks.length
    });

    isLoading = true;
    try {
      // Call backend to mark stale running tasks as failed
      const token = localStorage.getItem('auth_token');
      const response = await fetch(`${API_BASE}/api/progress/operations/cleanup/stale?minutes_old=60`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      const elapsed = performance.now() - startTime;
      logger.success("Stale tasks cleaned up", {
        marked_failed: data.marked_failed_count,
        elapsed_ms: elapsed.toFixed(2)
      });

      showNotificationMessage(`Marked ${data.marked_failed_count} stale tasks as failed`, 'success');

      // Refresh tasks
      await fetchTasks();
    } catch (error) {
      logger.error("Failed to cleanup stale tasks", { error: error.message });
      showNotificationMessage('Failed to cleanup stale tasks', 'error');
    } finally {
      isLoading = false;
    }
  }

  /**
   * Refresh tasks from backend
   */
  function refreshTasks() {
    logger.userAction("Refresh tasks button clicked");
    fetchTasks(true); // Show loading indicator for manual refresh
  }

  // Auto-refresh interval for running operations
  let refreshInterval;

  onMount(async () => {
    // Silently check if user is logged in first
    const token = localStorage.getItem('auth_token');
    if (!token) {
      // Not logged in, don't fetch or log anything
      return;
    }

    // Initial fetch with loading indicator
    await fetchTasks(true);

    // Set up auto-refresh every 3 seconds to catch new/updated operations
    refreshInterval = setInterval(async () => {
      const token = localStorage.getItem('auth_token');
      if (token) {
        // Always refresh to catch new operations and updates
        await fetchTasks();
      }
    }, 3000); // Poll every 3 seconds

    // Connect WebSocket
    logger.info("Connecting to WebSocket for real-time progress updates");
    websocket.connect();

    // Subscribe to 'progress' room for real-time updates
    logger.info("Subscribing to 'progress' WebSocket room");
    websocket.socket.emit('subscribe', { events: ['progress'] });

    // Listen for operation_start
    unsubscribeOperationStart = websocket.on('operation_start', (data) => {
      logger.info("WebSocket: Operation started", {
        operation_id: data.operation_id,
        operation_name: data.operation_name,
        user_id: data.user_id
      });

      const newTask = transformOperationToTask(data);

      // Add new task to beginning
      backendTasks = [newTask, ...backendTasks];
      showNotificationMessage(`Operation started: ${data.operation_name}`, 'info');
    });

    // Listen for progress_update
    unsubscribeProgressUpdate = websocket.on('progress_update', (data) => {
      logger.info("WebSocket: Progress update", {
        operation_id: data.operation_id,
        progress_percentage: data.progress_percentage,
        current_step: data.current_step
      });

      const index = backendTasks.findIndex(t => t.id === data.operation_id.toString());
      if (index >= 0) {
        // Update existing task
        backendTasks[index] = transformOperationToTask(data);
        backendTasks = [...backendTasks]; // Trigger reactivity
      }
    });

    // Listen for operation_complete
    unsubscribeOperationComplete = websocket.on('operation_complete', (data) => {
      logger.success("WebSocket: Operation completed", {
        operation_id: data.operation_id,
        operation_name: data.operation_name
      });

      const index = backendTasks.findIndex(t => t.id === data.operation_id.toString());
      if (index >= 0) {
        // Update task to completed
        backendTasks[index] = transformOperationToTask(data);
        backendTasks = [...backendTasks]; // Trigger reactivity
      }

      showNotificationMessage(`Operation completed: ${data.operation_name}`, 'success');

      // P12.5.9: Send telemetry for tool usage tracking
      if (typeof window !== 'undefined' && window.electronTelemetry) {
        const duration = data.completed_at && data.started_at
          ? Math.round((new Date(data.completed_at) - new Date(data.started_at)) / 1000)
          : null;

        window.electronTelemetry.success(
          `Tool operation completed: ${data.operation_name}`,
          data.tool_name || 'Unknown',
          {
            operation_id: data.operation_id,
            operation_name: data.operation_name,
            tool_name: data.tool_name,
            function_name: data.function_name,
            duration_seconds: duration,
            result: data.result || null
          }
        );
      }
    });

    // Listen for operation_failed
    unsubscribeOperationFailed = websocket.on('operation_failed', (data) => {
      logger.error("WebSocket: Operation failed", {
        operation_id: data.operation_id,
        operation_name: data.operation_name,
        error_message: data.error_message
      });

      const index = backendTasks.findIndex(t => t.id === data.operation_id.toString());
      if (index >= 0) {
        // Update task to failed
        backendTasks[index] = transformOperationToTask(data);
        backendTasks = [...backendTasks]; // Trigger reactivity
      }

      showNotificationMessage(`Operation failed: ${data.operation_name}`, 'error');

      // P12.5.9: Send telemetry for tool usage tracking (errors)
      if (typeof window !== 'undefined' && window.electronTelemetry) {
        const duration = data.completed_at && data.started_at
          ? Math.round((new Date(data.completed_at) - new Date(data.started_at)) / 1000)
          : null;

        window.electronTelemetry.error(
          `Tool operation failed: ${data.operation_name}`,
          data.tool_name || 'Unknown',
          {
            operation_id: data.operation_id,
            operation_name: data.operation_name,
            tool_name: data.tool_name,
            function_name: data.function_name,
            duration_seconds: duration,
            error_message: data.error_message || 'Unknown error'
          }
        );
      }
    });
  });

  onDestroy(() => {
    logger.component("TaskManager", "destroyed");

    // Clear auto-refresh interval
    if (refreshInterval) {
      clearInterval(refreshInterval);
      logger.info("Cleared auto-refresh interval");
    }

    // Clean up WebSocket subscriptions
    logger.info("Cleaning up WebSocket subscriptions");
    if (unsubscribeOperationStart) unsubscribeOperationStart();
    if (unsubscribeProgressUpdate) unsubscribeProgressUpdate();
    if (unsubscribeOperationComplete) unsubscribeOperationComplete();
    if (unsubscribeOperationFailed) unsubscribeOperationFailed();

    // Unsubscribe from progress room
    if (websocket.socket) {
      websocket.socket.emit('unsubscribe', { events: ['progress'] });
    }
  });
</script>

<div class="task-manager">
  {#if showNotification}
    <ToastNotification
      kind={notificationType}
      title={notificationType === 'success' ? 'Success' : notificationType === 'error' ? 'Error' : 'Info'}
      subtitle={notificationMessage}
      on:close={() => showNotification = false}
    />
  {/if}

  <div class="header">
    <h1>Task Manager</h1>
    <p>Monitor and manage your operation progress in real-time</p>
  </div>

  {#if isLoading}
    <InlineLoading description="Loading tasks..." />
  {/if}

  <DataTable
    {headers}
    rows={tasks}
    sortable
    bind:selectedRowIds={filteredRowIds}
  >
    <Toolbar>
      <ToolbarContent>
        <ToolbarSearch persistent shouldFilterRows />
        <Button
          icon={Renew}
          kind="secondary"
          on:click={refreshTasks}
        >
          Refresh
        </Button>
        <Button
          icon={TrashCan}
          kind="danger-tertiary"
          on:click={clearHistory}
          title="Clear completed, failed, and zombie tasks"
        >
          Clear All
        </Button>
      </ToolbarContent>
    </Toolbar>

    <span slot="cell" let:row let:cell>
      {#if cell.key === "status"}
        <Tag type={getStatusColor(cell.value)}>
          {cell.value.toUpperCase()}
        </Tag>
      {:else if cell.key === "progress"}
        <div style="width: 100%; min-width: 120px;">
          <ProgressBar
            value={cell.value}
            labelText=""
            hideLabel
            size="sm"
          />
          <div style="font-size: 0.75rem; margin-top: 0.25rem; color: var(--cds-text-02);">
            {cell.value}%
            {#if row.current_step}
              <div style="margin-top: 0.125rem; font-style: italic;">
                {row.current_step}
              </div>
            {/if}
          </div>
        </div>
      {:else if cell.key === "details"}
        {#if cell.value}
          <div style="font-size: 0.75rem; color: var(--cds-text-02); max-width: 200px;">
            {cell.value}
          </div>
        {:else}
          <span style="color: var(--cds-text-03);">-</span>
        {/if}
      {:else}
        {cell.value}
      {/if}
    </span>
  </DataTable>

  {#if tasks.length === 0}
    <div class="empty-state">
      <p>No active tasks. Start by running a tool from the Apps menu.</p>
    </div>
  {/if}
</div>

<style>
  .task-manager {
    padding: 2rem;
    height: 100%;
    overflow-y: auto;
  }

  .header {
    margin-bottom: 2rem;
  }

  .header h1 {
    font-size: 2rem;
    margin-bottom: 0.5rem;
    color: var(--cds-text-01);
  }

  .header p {
    color: var(--cds-text-02);
    font-size: 1rem;
  }

  .empty-state {
    text-align: center;
    padding: 4rem 2rem;
    color: var(--cds-text-02);
  }
</style>
