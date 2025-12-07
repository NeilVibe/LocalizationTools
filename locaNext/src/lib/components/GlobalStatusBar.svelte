<script>
  /**
   * Global Status Bar - P18.5.5
   *
   * Fixed bottom bar showing active operations.
   * Persists across navigation, can be minimized.
   */
  import { ProgressBar, Button, Tag } from "carbon-components-svelte";
  import { Close, ChevronUp, ChevronDown, TaskView } from "carbon-icons-svelte";
  import {
    activeOperations,
    hasActiveOperations,
    statusBarVisible,
    currentOperation,
    hideStatusBar,
    showStatusBar
  } from "$lib/stores/globalProgress.js";
  import { currentView } from "$lib/stores/app.js";

  let expanded = false;

  function toggleExpand() {
    expanded = !expanded;
  }

  function goToTaskManager() {
    $currentView = "tasks";
  }

  function formatDuration(ms) {
    if (!ms) return "";
    const seconds = Math.floor(ms / 1000);
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${minutes}m ${secs}s`;
  }

  function getProgressColor(op) {
    if (op.status === "failed") return "red";
    if (op.status === "completed") return "green";
    return "blue";
  }
</script>

{#if $hasActiveOperations}
  <!-- Minimized indicator when hidden -->
  {#if !$statusBarVisible}
    <button
      class="minimized-indicator"
      on:click={showStatusBar}
      title="Show progress"
    >
      <span class="pulse"></span>
      <span class="count">{$activeOperations.length}</span>
    </button>
  {:else}
    <!-- Full status bar -->
    <div class="global-status-bar" class:expanded>
      <!-- Header -->
      <div class="status-header">
        <div class="header-left">
          <Tag type="blue" size="sm">
            {$activeOperations.length} active
          </Tag>
          {#if $currentOperation}
            <span class="current-op">
              <strong>{$currentOperation.tool}</strong> - {$currentOperation.function}
            </span>
          {/if}
        </div>
        <div class="header-right">
          <Button
            kind="ghost"
            size="small"
            icon={TaskView}
            iconDescription="View in Task Manager"
            on:click={goToTaskManager}
          />
          <Button
            kind="ghost"
            size="small"
            icon={expanded ? ChevronDown : ChevronUp}
            iconDescription={expanded ? "Collapse" : "Expand"}
            on:click={toggleExpand}
          />
          <Button
            kind="ghost"
            size="small"
            icon={Close}
            iconDescription="Hide (progress continues)"
            on:click={hideStatusBar}
          />
        </div>
      </div>

      <!-- Current operation progress -->
      {#if $currentOperation}
        <div class="progress-section">
          <div class="progress-info">
            <span class="message">{$currentOperation.message}</span>
            <span class="percentage">{$currentOperation.progress}%</span>
          </div>
          <ProgressBar
            value={$currentOperation.progress}
            max={100}
            size="sm"
            status={$currentOperation.status === "failed" ? "error" : "active"}
          />
          {#if $currentOperation.startTime}
            <span class="duration">
              Elapsed: {formatDuration(Date.now() - $currentOperation.startTime)}
            </span>
          {/if}
        </div>
      {/if}

      <!-- Expanded: show all operations -->
      {#if expanded}
        <div class="expanded-content">
          <div class="operations-list">
            {#each $activeOperations as op (op.id)}
              <div class="operation-item" class:completed={op.status === "completed"} class:failed={op.status === "failed"}>
                <div class="op-header">
                  <Tag type={op.status === "running" ? "blue" : op.status === "completed" ? "green" : "red"} size="sm">
                    {op.status}
                  </Tag>
                  <span class="op-tool">{op.tool}</span>
                  <span class="op-function">{op.function}</span>
                </div>
                <div class="op-progress">
                  <ProgressBar value={op.progress} max={100} size="sm" />
                  <span>{op.progress}%</span>
                </div>
                <div class="op-message">{op.message}</div>
              </div>
            {/each}
          </div>
        </div>
      {/if}
    </div>
  {/if}
{/if}

<style>
  .global-status-bar {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background: var(--cds-ui-01, #f4f4f4);
    border-top: 2px solid var(--cds-interactive-01, #0f62fe);
    padding: 0.5rem 1rem;
    z-index: 9999;
    box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.15);
    transition: max-height 0.3s ease;
    max-height: 80px;
    overflow: hidden;
  }

  .global-status-bar.expanded {
    max-height: 400px;
    overflow-y: auto;
  }

  .status-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.25rem;
  }

  .header-left {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .header-right {
    display: flex;
    align-items: center;
    gap: 0.25rem;
  }

  .current-op {
    font-size: 0.875rem;
    color: var(--cds-text-01, #161616);
  }

  .progress-section {
    margin-top: 0.25rem;
  }

  .progress-info {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 0.75rem;
    margin-bottom: 0.25rem;
  }

  .message {
    color: var(--cds-text-02, #525252);
    max-width: 80%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .percentage {
    font-weight: 600;
    color: var(--cds-interactive-01, #0f62fe);
  }

  .duration {
    font-size: 0.75rem;
    color: var(--cds-text-02, #525252);
    margin-top: 0.25rem;
  }

  .expanded-content {
    margin-top: 1rem;
    padding-top: 1rem;
    border-top: 1px solid var(--cds-ui-03, #e0e0e0);
  }

  .operations-list {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .operation-item {
    background: var(--cds-ui-background, #fff);
    padding: 0.75rem;
    border-radius: 4px;
    border: 1px solid var(--cds-ui-03, #e0e0e0);
  }

  .operation-item.completed {
    border-color: var(--cds-support-02, #198038);
    opacity: 0.7;
  }

  .operation-item.failed {
    border-color: var(--cds-support-01, #da1e28);
  }

  .op-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.5rem;
  }

  .op-tool {
    font-weight: 600;
  }

  .op-function {
    color: var(--cds-text-02, #525252);
  }

  .op-progress {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.25rem;
  }

  .op-progress span {
    font-size: 0.75rem;
    min-width: 40px;
    text-align: right;
  }

  .op-message {
    font-size: 0.75rem;
    color: var(--cds-text-02, #525252);
  }

  /* Minimized indicator */
  .minimized-indicator {
    position: fixed;
    bottom: 1rem;
    right: 1rem;
    width: 48px;
    height: 48px;
    border-radius: 50%;
    background: var(--cds-interactive-01, #0f62fe);
    border: none;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
    z-index: 9999;
    transition: transform 0.2s;
  }

  .minimized-indicator:hover {
    transform: scale(1.1);
  }

  .minimized-indicator .pulse {
    position: absolute;
    width: 100%;
    height: 100%;
    border-radius: 50%;
    background: var(--cds-interactive-01, #0f62fe);
    animation: pulse 2s infinite;
  }

  .minimized-indicator .count {
    position: relative;
    color: white;
    font-weight: 600;
    font-size: 1rem;
  }

  @keyframes pulse {
    0% {
      transform: scale(1);
      opacity: 1;
    }
    50% {
      transform: scale(1.3);
      opacity: 0.5;
    }
    100% {
      transform: scale(1.5);
      opacity: 0;
    }
  }
</style>
