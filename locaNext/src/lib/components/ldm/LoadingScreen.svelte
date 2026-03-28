<script>
  /**
   * LoadingScreen.svelte - Professional loading indicator
   * Replaces shimmer skeletons with centered progress bar + percentage.
   * Uses Carbon Design System token colors for consistency.
   */

  let {
    progress = 0,       // 0-100
    message = 'Loading...',
    showPercentage = true
  } = $props();

  let displayProgress = $derived(Math.min(100, Math.max(0, Math.round(progress))));
  let isIndeterminate = $derived(displayProgress === 0);
</script>

<div class="loading-screen">
  <div class="loading-content">
    <div class="loading-icon">
      <div class="pulse-ring"></div>
      <div class="pulse-dot"></div>
    </div>

    {#if message}
      <p class="loading-message">{message}</p>
    {/if}

    <div class="progress-container">
      <div class="progress-track">
        <div
          class="progress-fill"
          class:indeterminate={isIndeterminate}
          style="width: {isIndeterminate ? '30%' : `${displayProgress}%`}"
        ></div>
      </div>
      {#if showPercentage && !isIndeterminate}
        <span class="progress-text">{displayProgress}%</span>
      {/if}
    </div>
  </div>
</div>

<style>
  .loading-screen {
    display: flex;
    align-items: center;
    justify-content: center;
    flex: 1;
    min-height: 200px;
    width: 100%;
    height: 100%;
  }

  .loading-content {
    text-align: center;
    max-width: 320px;
    width: 100%;
    padding: 2rem 1.5rem;
  }

  /* Pulse animation container */
  .loading-icon {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 48px;
    height: 48px;
    margin: 0 auto 1.25rem;
  }

  .pulse-dot {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: var(--cds-interactive, #4589ff);
    animation: pulse 1.5s ease-in-out infinite;
    z-index: 1;
  }

  .pulse-ring {
    position: absolute;
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: var(--cds-interactive, #4589ff);
    animation: ring-pulse 1.5s ease-out infinite;
  }

  @keyframes pulse {
    0%, 100% {
      transform: scale(1);
      opacity: 0.8;
    }
    50% {
      transform: scale(1.2);
      opacity: 1;
    }
  }

  @keyframes ring-pulse {
    0% {
      transform: scale(1);
      opacity: 0.4;
    }
    100% {
      transform: scale(2.5);
      opacity: 0;
    }
  }

  /* Message text */
  .loading-message {
    font-size: 0.875rem;
    color: var(--cds-text-01, #f4f4f4);
    margin: 0 0 1rem;
    font-weight: 400;
    letter-spacing: 0.01em;
  }

  /* Progress bar */
  .progress-container {
    width: 100%;
  }

  .progress-track {
    height: 4px;
    background: var(--cds-layer-02, #393939);
    border-radius: 2px;
    overflow: hidden;
    position: relative;
  }

  .progress-fill {
    height: 100%;
    background: var(--cds-interactive, #4589ff);
    border-radius: 2px;
    transition: width 0.3s ease;
    will-change: width;
  }

  /* Indeterminate animation when progress is 0 */
  .progress-fill.indeterminate {
    animation: indeterminate 1.5s ease-in-out infinite;
  }

  @keyframes indeterminate {
    0% {
      transform: translateX(-100%);
    }
    100% {
      transform: translateX(400%);
    }
  }

  /* Percentage text */
  .progress-text {
    display: inline-block;
    font-size: 0.75rem;
    color: var(--cds-text-02, #c6c6c6);
    margin-top: 0.5rem;
    font-variant-numeric: tabular-nums;
  }
</style>
