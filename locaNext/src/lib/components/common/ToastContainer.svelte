<script>
  /**
   * ToastContainer - Polished slide-in toast notifications (Phase 40)
   *
   * Replaces GlobalToast with warm accent borders, progress bar auto-dismiss,
   * and preserved WebSocket operation subscriptions.
   */
  import { toasts, removeToast, toast } from "$lib/stores/toastStore.js";
  import { websocket } from "$lib/api/websocket.js";
  import { isAuthenticated } from "$lib/stores/app.js";
  import { logger } from "$lib/utils/logger.js";
  import { onMount, onDestroy } from "svelte";
  import { fly } from "svelte/transition";
  import { cubicOut } from "svelte/easing";
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

  // Accent colors by kind
  const ACCENT_COLORS = {
    success: '#24a148',
    error: '#da1e28',
    warning: '#f1c21b',
    info: '#d49a5c'
  };

  function getIcon(kind) {
    switch (kind) {
      case 'success': return CheckmarkFilled;
      case 'error': return ErrorFilled;
      case 'warning': return WarningFilled;
      default: return InformationFilled;
    }
  }

  function getAccentColor(kind) {
    return ACCENT_COLORS[kind] || ACCENT_COLORS.info;
  }

  function getToastDuration(t) {
    return t.duration || 3000;
  }

  /**
   * Format duration from milliseconds to human readable
   */
  function formatDuration(startedAt, completedAt) {
    if (!startedAt || !completedAt) return null;
    const start = new Date(startedAt);
    const end = new Date(completedAt);
    const seconds = Math.round((end - start) / 1000);
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${minutes}m ${secs}s`;
  }

  // WebSocket subscriptions (preserved from GlobalToast)
  onMount(() => {
    if (!$isAuthenticated) return;

    logger.info("ToastContainer: Setting up WebSocket listeners for toast notifications");

    if (!websocket.isConnected()) {
      websocket.connect();
    }

    if (websocket.socket) {
      websocket.socket.emit('subscribe', { events: ['progress'] });
    }

    unsubscribeOperationStart = websocket.on('operation_start', (data) => {
      if (!data.operation_name || data.operation_name === 'Unknown operation') return;
      if (data.silent) {
        logger.debug("ToastContainer: Skipping silent operation", { operation_name: data.operation_name });
        return;
      }
      logger.info("ToastContainer: Operation started", {
        operation_id: data.operation_id,
        operation_name: data.operation_name,
        tool_name: data.tool_name
      });
      toast.operationStarted(data.operation_name, data.tool_name || 'LDM');
    });

    unsubscribeOperationComplete = websocket.on('operation_complete', (data) => {
      if (!data.operation_name || data.operation_name === 'Unknown operation') return;
      if (data.silent) {
        logger.debug("ToastContainer: Skipping silent operation complete", { operation_name: data.operation_name });
        return;
      }
      logger.info("ToastContainer: Operation completed", {
        operation_id: data.operation_id,
        operation_name: data.operation_name,
        tool_name: data.tool_name
      });
      const duration = formatDuration(data.started_at, data.completed_at);
      toast.operationCompleted(data.operation_name, data.tool_name || 'LDM', duration);
    });

    unsubscribeOperationFailed = websocket.on('operation_failed', (data) => {
      logger.error("ToastContainer: Operation failed", {
        operation_id: data.operation_id,
        operation_name: data.operation_name,
        tool_name: data.tool_name,
        error: data.error_message
      });
      toast.operationFailed(data.operation_name || 'Operation', data.tool_name || 'LDM', data.error_message);
    });
  });

  onDestroy(() => {
    logger.info("ToastContainer: Cleaning up WebSocket subscriptions");
    if (unsubscribeOperationStart) unsubscribeOperationStart();
    if (unsubscribeOperationComplete) unsubscribeOperationComplete();
    if (unsubscribeOperationFailed) unsubscribeOperationFailed();
  });
</script>

<div class="toast-container" aria-live="polite">
  {#each $toasts as t (t.id)}
    <div
      class="toast"
      style="border-left-color: {getAccentColor(t.kind)}"
      transition:fly={{ x: 360, duration: 200, easing: cubicOut }}
    >
      <div class="toast-icon" style="color: {getAccentColor(t.kind)}">
        <svelte:component this={getIcon(t.kind)} size={20} />
      </div>
      <div class="toast-text">
        {#if t.title}
          <div class="toast-title">{t.title}</div>
        {/if}
        <div class="toast-message">{t.message}</div>
      </div>
      <button class="toast-close" onclick={() => removeToast(t.id)} aria-label="Dismiss notification">
        <Close size={16} />
      </button>
      <!-- Progress bar for auto-dismiss -->
      <div
        class="toast-progress"
        style="background: {getAccentColor(t.kind)}; animation-duration: {getToastDuration(t)}ms"
      ></div>
    </div>
  {/each}
</div>

<style>
  .toast-container {
    position: fixed;
    top: 60px;
    right: 16px;
    z-index: 9200;
    display: flex;
    flex-direction: column;
    gap: 8px;
    pointer-events: none;
    max-width: 360px;
    width: 100%;
  }

  .toast {
    position: relative;
    background: var(--cds-layer-01);
    border: 1px solid var(--cds-border-subtle-01);
    border-radius: 8px;
    border-left: 4px solid;
    overflow: hidden;
    pointer-events: auto;
  }

  .toast > :not(.toast-progress) {
    display: flex;
  }

  /* Layout wrapper for icon + text + close */
  .toast {
    display: flex;
    flex-wrap: wrap;
    align-items: flex-start;
    padding: 0.75rem 2.25rem 0.75rem 1rem;
    gap: 0.5rem;
  }

  .toast-icon {
    display: flex;
    align-items: center;
    flex-shrink: 0;
    margin-top: 1px;
  }

  .toast-text {
    flex: 1;
    min-width: 0;
  }

  .toast-title {
    font-weight: 600;
    font-size: 0.8125rem;
    color: var(--cds-text-01);
    line-height: 1.3;
  }

  .toast-message {
    font-size: 0.75rem;
    color: var(--cds-text-02);
    margin-top: 2px;
    line-height: 1.4;
    word-break: break-word;
  }

  .toast-close {
    position: absolute;
    top: 8px;
    right: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 2px;
    background: transparent;
    border: none;
    border-radius: 4px;
    color: var(--cds-text-03);
    cursor: pointer;
    opacity: 0.6;
    transition: opacity 0.15s;
  }

  .toast-close:hover {
    opacity: 1;
    background: rgba(255, 255, 255, 0.08);
  }

  /* Progress bar (auto-dismiss countdown) */
  .toast-progress {
    position: absolute;
    bottom: 0;
    left: 0;
    height: 2px;
    width: 100%;
    animation: toast-progress linear forwards;
  }

  @keyframes toast-progress {
    from { width: 100%; }
    to { width: 0%; }
  }

  /* Reduced motion: instant appear/disappear, keep progress bar */
  @media (prefers-reduced-motion: reduce) {
    .toast {
      transition: none;
    }
  }

  /* Responsive */
  @media (max-width: 480px) {
    .toast-container {
      left: 16px;
      right: 16px;
      max-width: none;
    }
  }
</style>
