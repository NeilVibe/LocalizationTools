<script>
  /**
   * SkeletonCard — Animated shimmer placeholders matching Codex entity-card dimensions.
   * Renders `count` skeleton cards with 48x48 image + text lines.
   */
  let { count = 6 } = $props();
</script>

<div class="skeleton-grid">
  {#each Array(count) as _, i (i)}
    <div class="skeleton-card">
      <div class="skeleton-image"></div>
      <div class="skeleton-text">
        <div class="skeleton-line skeleton-line--wide"></div>
        <div class="skeleton-line skeleton-line--tag"></div>
        <div class="skeleton-line skeleton-line--narrow"></div>
      </div>
    </div>
  {/each}
</div>

<style>
  .skeleton-grid {
    display: flex;
    flex-wrap: wrap;
    gap: var(--card-gap);
  }

  .skeleton-card {
    display: flex;
    flex-direction: row;
    align-items: flex-start;
    gap: var(--card-gap);
    padding: var(--card-padding);
    border-radius: var(--card-radius);
    background: var(--cds-layer-01);
    border: 1px solid var(--cds-border-subtle-01);
    min-width: 200px;
    flex: 1 1 200px;
    animation: skeleton-shimmer 1.5s ease-in-out infinite;
  }

  .skeleton-image {
    width: 48px;
    height: 48px;
    border-radius: 4px;
    background: var(--skeleton-bg);
    flex-shrink: 0;
  }

  .skeleton-text {
    display: flex;
    flex-direction: column;
    gap: 6px;
    flex: 1;
    min-width: 0;
  }

  .skeleton-line {
    height: 12px;
    border-radius: 4px;
    background: var(--skeleton-bg);
  }

  .skeleton-line--wide {
    width: 70%;
  }

  .skeleton-line--tag {
    width: 40px;
    height: 16px;
    border-radius: 8px;
    background: var(--skeleton-bg);
  }

  .skeleton-line--narrow {
    width: 85%;
  }

  @keyframes skeleton-shimmer {
    0%, 100% { opacity: 0.4; }
    50% { opacity: 0.8; }
  }
</style>
