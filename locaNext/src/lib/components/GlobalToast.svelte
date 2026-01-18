<script>
  /**
   * GlobalToast - Minimal, Slick Toast Notifications (Svelte 5)
   *
   * Redesigned for minimal footprint - users can check Task Manager for details.
   * Shows brief notifications that auto-dismiss quickly.
   */
  import { toasts, removeToast } from "$lib/stores/toastStore.js";
  import { websocket } from "$lib/api/websocket.js";
  import { isAuthenticated } from "$lib/stores/app.js";
  import { toast } from "$lib/stores/toastStore.js";
  import { logger } from "$lib/utils/logger.js";
  import { onMount, onDestroy } from "svelte";
  import {
    CheckmarkFilled,
    ErrorFilled,
    WarningFilled,
    InformationFilled,
    Close
  } from "carbon-icons-svelte";

  // WebSocket unsubscribe functions
  let unsubscribeOperationStart;
  let unsubscribeOperationComplete;
  let unsubscribeOperationFailed;

  /**
   * Get icon component based on toast kind
   */
  function getIcon(kind) {
    switch (kind) {
      case 'success': return CheckmarkFilled;
      case 'error': return ErrorFilled;
      case 'warning': return WarningFilled;
      default: return InformationFilled;
    }
  }

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

    // Listen for operation_start - only show if we have valid data
    unsubscribeOperationStart = websocket.on('operation_start', (data) => {
      // Skip if no meaningful operation name
      if (!data.operation_name || data.operation_name === 'Unknown operation') {
        return;
      }

      // Skip silent operations (e.g., FAISS auto-sync)
      if (data.silent) {
        logger.debug("GlobalToast: Skipping silent operation", { operation_name: data.operation_name });
        return;
      }

      logger.info("GlobalToast: Operation started", {
        operation_id: data.operation_id,
        operation_name: data.operation_name,
        tool_name: data.tool_name
      });

      toast.operationStarted(
        data.operation_name,
        data.tool_name || 'LDM'
      );
    });

    // Listen for operation_complete - only show if we have valid data
    unsubscribeOperationComplete = websocket.on('operation_complete', (data) => {
      // Skip if no meaningful operation name
      if (!data.operation_name || data.operation_name === 'Unknown operation') {
        return;
      }

      // Skip silent operations (e.g., FAISS auto-sync)
      if (data.silent) {
        logger.debug("GlobalToast: Skipping silent operation complete", { operation_name: data.operation_name });
        return;
      }

      logger.info("GlobalToast: Operation completed", {
        operation_id: data.operation_id,
        operation_name: data.operation_name,
        tool_name: data.tool_name
      });

      const duration = formatDuration(data.started_at, data.completed_at);
      toast.operationCompleted(
        data.operation_name,
        data.tool_name || 'LDM',
        duration
      );
    });

    // Listen for operation_failed - always show errors (never skip)
    unsubscribeOperationFailed = websocket.on('operation_failed', (data) => {
      logger.error("GlobalToast: Operation failed", {
        operation_id: data.operation_id,
        operation_name: data.operation_name,
        tool_name: data.tool_name,
        error: data.error_message
      });

      toast.operationFailed(
        data.operation_name || 'Operation',
        data.tool_name || 'LDM',
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

<!-- Minimal Toast Container - Fixed position bottom-right -->
<div class="toast-container">
  {#each $toasts as t (t.id)}
    <div class="toast toast-{t.kind}">
      <div class="toast-icon">
        <svelte:component this={getIcon(t.kind)} size={16} />
      </div>
      <div class="toast-content">
        <span class="toast-message">{t.message}</span>
      </div>
      <button class="toast-close" onclick={() => removeToast(t.id)} aria-label="Dismiss">
        <Close size={14} />
      </button>
    </div>
  {/each}
</div>

<style>
  .toast-container {
    position: fixed;
    /* UI-114 FIX: Use safe area insets to avoid being cut off */
    bottom: max(16px, env(safe-area-inset-bottom, 16px));
    right: max(16px, env(safe-area-inset-right, 16px));
    z-index: 9999;
    display: flex;
    flex-direction: column-reverse;
    gap: 8px;
    pointer-events: none;
    /* UI-114 FIX: Ensure toast stays within viewport */
    max-height: calc(100vh - 100px);
    overflow-y: auto;
  }

  .toast {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    padding: 10px 12px;
    border-radius: 6px;
    background: var(--cds-layer-02, #262626);
    border-left: 3px solid;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
    pointer-events: auto;
    /* UI-114 FIX: Wider toast and allow wrapping */
    max-width: min(400px, calc(100vw - 32px));
    animation: slideIn 0.2s ease-out;
    font-size: 0.8125rem;
  }

  .toast-success {
    border-left-color: #42be65;
  }

  .toast-error {
    border-left-color: #fa4d56;
  }

  .toast-warning {
    border-left-color: #f1c21b;
  }

  .toast-info {
    border-left-color: #4589ff;
  }

  .toast-icon {
    display: flex;
    align-items: center;
    flex-shrink: 0;
  }

  .toast-success .toast-icon {
    color: #42be65;
  }

  .toast-error .toast-icon {
    color: #fa4d56;
  }

  .toast-warning .toast-icon {
    color: #f1c21b;
  }

  .toast-info .toast-icon {
    color: #4589ff;
  }

  .toast-content {
    flex: 1;
    min-width: 0;
  }

  .toast-message {
    color: var(--cds-text-primary, #f4f4f4);
    /* UI-114 FIX: Allow text wrapping instead of truncating */
    white-space: normal;
    word-break: break-word;
    display: block;
    line-height: 1.4;
  }

  .toast-close {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 4px;
    background: transparent;
    border: none;
    border-radius: 4px;
    color: var(--cds-text-secondary, #c6c6c6);
    cursor: pointer;
    opacity: 0.6;
    transition: opacity 0.15s;
    flex-shrink: 0;
  }

  .toast-close:hover {
    opacity: 1;
    background: rgba(255, 255, 255, 0.1);
  }

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

  /* Responsive - even smaller on mobile */
  @media (max-width: 480px) {
    .toast-container {
      left: 16px;
      right: 16px;
      bottom: max(16px, env(safe-area-inset-bottom, 16px));
    }

    .toast {
      max-width: none;
    }
  }

  /* UI-114: Ensure toast is always visible above any fixed elements */
  @media (max-height: 600px) {
    .toast-container {
      bottom: 8px;
      max-height: calc(100vh - 60px);
    }
  }
</style>
