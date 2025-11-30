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
  import { api } from "$lib/api/client.js";
  import { websocket } from "$lib/api/websocket.js";
  import { isAuthenticated, user } from "$lib/stores/app.js";
  import { logger } from "$lib/utils/logger.js";

  // Task data from backend (ActiveOperation)
  let tasks = [];
  let isLoading = false;
  let showNotification = false;
  let notificationMessage = '';
  let notificationType = 'success';

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
      tasks = []; // Show empty task list
      return;
    }

    logger.apiCall("/api/progress/operations", "GET");

    try {
      // Fetch ALL recent operations (not just running)
      // This shows users their task history including completed/failed tasks
      const response = await fetch('http://localhost:8888/api/progress/operations', {
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
          if (!areTasksEqual(tasks, newTasks)) {
            tasks = newTasks;

            logger.success("Tasks updated", {
              task_count: tasks.length,
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
    { key: "timestamp", value: "Started" },
    { key: "duration", value: "Duration" }
  ];

  let filteredRowIds = [];

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
   * Clear completed and failed tasks
   */
  async function clearHistory() {
    const startTime = performance.now();
    const tasksToDelete = tasks.filter(t => t.status === 'completed' || t.status === 'failed');

    logger.userAction("Clear History button clicked", { tasks_to_delete: tasksToDelete.length });

    if (tasksToDelete.length === 0) {
      logger.info("No tasks to clear");
      showNotificationMessage('No tasks to clear', 'info');
      return;
    }

    isLoading = true;
    try {
      logger.info("Deleting tasks from backend", { count: tasksToDelete.length });

      const token = localStorage.getItem('auth_token');

      // Delete each task from backend (ActiveOperation API)
      for (const task of tasksToDelete) {
        await fetch(`http://localhost:8888/api/progress/operations/${task.id}`, {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
      }

      const elapsed = performance.now() - startTime;

      // Remove from local array
      tasks = tasks.filter(t => t.status === 'running');

      logger.success("Task history cleared", {
        deleted_count: tasksToDelete.length,
        remaining_count: tasks.length,
        elapsed_ms: elapsed.toFixed(2)
      });

      showNotificationMessage(`Cleared ${tasksToDelete.length} tasks`, 'success');
    } catch (error) {
      const elapsed = performance.now() - startTime;

      logger.error("Failed to clear history", {
        error: error.message,
        error_type: error.name,
        tasks_to_delete: tasksToDelete.length,
        elapsed_ms: elapsed.toFixed(2)
      });

      showNotificationMessage('Failed to clear history', 'error');
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
      tasks = [newTask, ...tasks];
      showNotificationMessage(`Operation started: ${data.operation_name}`, 'info');
    });

    // Listen for progress_update
    unsubscribeProgressUpdate = websocket.on('progress_update', (data) => {
      logger.info("WebSocket: Progress update", {
        operation_id: data.operation_id,
        progress_percentage: data.progress_percentage,
        current_step: data.current_step
      });

      const index = tasks.findIndex(t => t.id === data.operation_id.toString());
      if (index >= 0) {
        // Update existing task
        tasks[index] = transformOperationToTask(data);
        tasks = [...tasks]; // Trigger reactivity
      }
    });

    // Listen for operation_complete
    unsubscribeOperationComplete = websocket.on('operation_complete', (data) => {
      logger.success("WebSocket: Operation completed", {
        operation_id: data.operation_id,
        operation_name: data.operation_name
      });

      const index = tasks.findIndex(t => t.id === data.operation_id.toString());
      if (index >= 0) {
        // Update task to completed
        tasks[index] = transformOperationToTask(data);
        tasks = [...tasks]; // Trigger reactivity
      }

      showNotificationMessage(`Operation completed: ${data.operation_name}`, 'success');
    });

    // Listen for operation_failed
    unsubscribeOperationFailed = websocket.on('operation_failed', (data) => {
      logger.error("WebSocket: Operation failed", {
        operation_id: data.operation_id,
        operation_name: data.operation_name,
        error_message: data.error_message
      });

      const index = tasks.findIndex(t => t.id === data.operation_id.toString());
      if (index >= 0) {
        // Update task to failed
        tasks[index] = transformOperationToTask(data);
        tasks = [...tasks]; // Trigger reactivity
      }

      showNotificationMessage(`Operation failed: ${data.operation_name}`, 'error');
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
        >
          Clear History
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
