<script>
  import { Tile } from "carbon-components-svelte";
  import { Apps } from "carbon-icons-svelte";
  import { onMount } from "svelte";
  import { logger } from "$lib/utils/logger.js";

  onMount(() => {
    logger.component("Welcome", "mounted");
  });
</script>

<div class="welcome-container">
  <Tile class="welcome-tile">
    <div class="welcome-content">
      <Apps size={64} class="welcome-icon" />
      <h1>Welcome to LocaNext</h1>
      <p class="subtitle">Professional Desktop Platform for Localization Tools</p>

      <div class="instructions">
        <h3>Getting Started</h3>
        <ol>
          <li>Click <strong>Apps</strong> in the top menu to select a tool</li>
          <li>Click <strong>Tasks</strong> to view your operation history</li>
          <li>All tools run locally on your machine</li>
        </ol>
      </div>

      <div class="stats">
        <div class="stat-item">
          <div class="stat-number">1</div>
          <div class="stat-label">Tools Available</div>
        </div>
        <div class="stat-item">
          <div class="stat-number">7</div>
          <div class="stat-label">Functions</div>
        </div>
      </div>
    </div>
  </Tile>
</div>

<style>
  .welcome-container {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    padding: 2rem;
  }

  :global(.welcome-tile) {
    max-width: 800px;
    width: 100%;
  }

  .welcome-content {
    text-align: center;
    padding: 3rem 2rem;
  }

  :global(.welcome-icon) {
    color: var(--cds-interactive-01);
    margin-bottom: 1.5rem;
  }

  h1 {
    font-size: 2.5rem;
    margin-bottom: 0.5rem;
    color: var(--cds-text-01);
  }

  .subtitle {
    font-size: 1.125rem;
    color: var(--cds-text-02);
    margin-bottom: 3rem;
  }

  .instructions {
    text-align: left;
    max-width: 500px;
    margin: 0 auto 3rem;
    padding: 1.5rem;
    background: var(--cds-ui-02);
    border-radius: 4px;
  }

  .instructions h3 {
    margin-top: 0;
    margin-bottom: 1rem;
    color: var(--cds-text-01);
  }

  .instructions ol {
    margin: 0;
    padding-left: 1.5rem;
  }

  .instructions li {
    margin-bottom: 0.75rem;
    color: var(--cds-text-02);
    line-height: 1.6;
  }

  .stats {
    display: flex;
    justify-content: center;
    gap: 4rem;
    margin-top: 2rem;
  }

  .stat-item {
    text-align: center;
  }

  .stat-number {
    font-size: 3rem;
    font-weight: 600;
    color: var(--cds-interactive-01);
    line-height: 1;
  }

  .stat-label {
    font-size: 0.875rem;
    color: var(--cds-text-02);
    margin-top: 0.5rem;
  }
</style>
