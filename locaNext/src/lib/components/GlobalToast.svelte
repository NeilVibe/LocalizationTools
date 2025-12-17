<script>
  /**
   * GlobalToast - BUG-016 Task Manager Toast Notifications
   *
   * Displays global toast notifications for Task Manager operations.
   * Should be placed in the root layout to appear on any page.
   */
  import { ToastNotification } from "carbon-components-svelte";
  import { toasts, removeToast } from "$lib/stores/toastStore.js";
  import { websocket } from "$lib/api/websocket.js";
  import { isAuthenticated } from "$lib/stores/app.js";
  import { toast } from "$lib/stores/toastStore.js";
  import { logger } from "$lib/utils/logger.js";
  import { onMount, onDestroy } from "svelte";

  // WebSocket unsubscribe functions
  let unsubscribeOperationStart;
  let unsubscribeOperationComplete;
  let unsubscribeOperationFailed;

  /**
   * Format duration from milliseconds to human readable
   */
  function formatDuration(startedAt, completedAt) {
    if (!startedAt || !completedAt) return null;

    const start = new Date(startedAt);
    const end = new Date(completedAt);
    const seconds = Math.round((end - start) / 1000);

    if (seconds < 60) {
      return `${seconds}s`;
    } else {
      const minutes = Math.floor(seconds / 60);
      const secs = seconds % 60;
      return `${minutes}m ${secs}s`;
    }
  }

  onMount(() => {
    // Only set up WebSocket listeners if authenticated
    if (!$isAuthenticated) return;

    logger.info("GlobalToast: Setting up WebSocket listeners for toast notifications");

    // Ensure WebSocket is connected
    if (!websocket.isConnected()) {
      websocket.connect();
    }

    // Subscribe to 'progress' room for real-time updates
    if (websocket.socket) {
      websocket.socket.emit('subscribe', { events: ['progress'] });
    }

    // Listen for operation_start
    unsubscribeOperationStart = websocket.on('operation_start', (data) => {
      logger.info("GlobalToast: Operation started", {
        operation_id: data.operation_id,
        operation_name: data.operation_name,
        tool_name: data.tool_name
      });

      toast.operationStarted(
        data.operation_name || 'Unknown operation',
        data.tool_name || 'Unknown'
      );
    });

    // Listen for operation_complete
    unsubscribeOperationComplete = websocket.on('operation_complete', (data) => {
      logger.info("GlobalToast: Operation completed", {
        operation_id: data.operation_id,
        operation_name: data.operation_name,
        tool_name: data.tool_name
      });

      const duration = formatDuration(data.started_at, data.completed_at);
      toast.operationCompleted(
        data.operation_name || 'Unknown operation',
        data.tool_name || 'Unknown',
        duration
      );
    });

    // Listen for operation_failed
    unsubscribeOperationFailed = websocket.on('operation_failed', (data) => {
      logger.error("GlobalToast: Operation failed", {
        operation_id: data.operation_id,
        operation_name: data.operation_name,
        tool_name: data.tool_name,
        error: data.error_message
      });

      toast.operationFailed(
        data.operation_name || 'Unknown operation',
        data.tool_name || 'Unknown',
        data.error_message
      );
    });
  });

  onDestroy(() => {
    logger.info("GlobalToast: Cleaning up WebSocket subscriptions");
    if (unsubscribeOperationStart) unsubscribeOperationStart();
    if (unsubscribeOperationComplete) unsubscribeOperationComplete();
    if (unsubscribeOperationFailed) unsubscribeOperationFailed();
  });
</script>

<!-- Toast Container - Fixed position in top-right corner -->
<div class="global-toast-container">
  {#each $toasts as t (t.id)}
    <div class="toast-wrapper" style="animation: slideIn 0.3s ease-out;">
      <ToastNotification
        kind={t.kind}
        title={t.title}
        subtitle={t.message}
        lowContrast
        on:close={() => removeToast(t.id)}
      />
    </div>
  {/each}
</div>

<style>
  .global-toast-container {
    position: fixed;
    top: 60px;  /* Below header */
    right: 16px;
    z-index: 9999;
    display: flex;
    flex-direction: column;
    gap: 8px;
    max-width: 400px;
    pointer-events: none;  /* Allow clicking through empty space */
  }

  .toast-wrapper {
    pointer-events: auto;  /* Make toasts clickable */
  }

  /* Slide in animation */
  @keyframes slideIn {
    from {
      transform: translateX(100%);
      opacity: 0;
    }
    to {
      transform: translateX(0);
      opacity: 1;
    }
  }

  /* Override Carbon toast styles for better dark mode */
  .global-toast-container :global(.bx--toast-notification) {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
    border-radius: 4px;
  }

  .global-toast-container :global(.bx--toast-notification__subtitle) {
    max-width: 300px;
    word-wrap: break-word;
  }
</style>
