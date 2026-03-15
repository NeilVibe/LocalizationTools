<script>
  /**
   * MapTooltip.svelte - Hover tooltip for world map nodes
   *
   * Shows region name, description, NPC list, and entity counts
   * at cursor position when hovering map nodes.
   *
   * Phase 20: Interactive World Map (Plan 02)
   */
  let { node = null, x = 0, y = 0 } = $props();
</script>

{#if node}
  <div
    class="map-tooltip"
    style="left: {x}px; top: {y}px;"
  >
    <span class="tooltip-name">{node.name}</span>
  </div>
{/if}

<style>
  .map-tooltip {
    position: fixed;
    z-index: 9999;
    pointer-events: none;
    padding: 8px 12px;
    background: var(--cds-layer-02, #262626);
    border: 1px solid var(--cds-border-subtle-01, #353535);
    border-radius: 4px;
    color: var(--cds-text-01, #f4f4f4);
    font-size: 0.8125rem;
    max-width: 280px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
  }

  .tooltip-name {
    font-weight: 600;
  }
</style>
