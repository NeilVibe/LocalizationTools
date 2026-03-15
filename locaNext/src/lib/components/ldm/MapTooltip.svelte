<script>
  /**
   * MapTooltip.svelte - Hover tooltip for world map nodes
   *
   * Shows region name, description, NPC list, and entity counts
   * at cursor position when hovering map nodes.
   *
   * Phase 20: Interactive World Map (Plan 02)
   */
  import { Tag } from "carbon-components-svelte";

  let { node = null, x = 0, y = 0 } = $props();

  // Clamp position to viewport to prevent off-screen rendering
  const TOOLTIP_WIDTH = 300;
  const TOOLTIP_HEIGHT_ESTIMATE = 150;
  const VIEWPORT_PADDING = 8;

  let clampedX = $derived(
    typeof window !== 'undefined'
      ? Math.min(x, window.innerWidth - TOOLTIP_WIDTH - VIEWPORT_PADDING)
      : x
  );

  let clampedY = $derived(
    typeof window !== 'undefined'
      ? Math.min(y, window.innerHeight - TOOLTIP_HEIGHT_ESTIMATE - VIEWPORT_PADDING)
      : y
  );

  // Region type colors for Carbon Tag
  const TYPE_TAG_COLORS = {
    Main: 'blue',
    Sub: 'cyan',
    Dungeon: 'red',
    Town: 'green',
    Fortress: 'purple',
    Wilderness: 'teal'
  };

  /**
   * Truncate description for tooltip display
   */
  function truncate(text, maxLen = 100) {
    if (!text) return '';
    const clean = text.replace(/<br\s*\/?>/gi, ' ');
    return clean.length > maxLen ? clean.slice(0, maxLen) + '...' : clean;
  }

  /**
   * Format entity type counts
   */
  let entityCountText = $derived(
    node?.entity_type_counts
      ? Object.entries(node.entity_type_counts)
          .filter(([, count]) => count > 0)
          .map(([type, count]) => `${count} ${type}${count !== 1 ? 's' : ''}`)
          .join(', ')
      : ''
  );
</script>

{#if node}
  <div
    class="map-tooltip"
    style="left: {clampedX}px; top: {clampedY}px;"
    role="tooltip"
  >
    <div class="tooltip-header">
      <span class="tooltip-name">{node.name}</span>
      <Tag type={TYPE_TAG_COLORS[node.region_type] || 'gray'} size="sm">
        {node.region_type}
      </Tag>
    </div>

    {#if node.description}
      <p class="tooltip-desc">{truncate(node.description)}</p>
    {/if}

    {#if node.npcs && node.npcs.length > 0}
      <div class="tooltip-npcs">
        <span class="tooltip-label">NPCs:</span>
        <span>{node.npcs.join(', ')}</span>
      </div>
    {/if}

    {#if entityCountText}
      <div class="tooltip-counts">
        <span class="tooltip-label">Entities:</span>
        <span>{entityCountText}</span>
      </div>
    {/if}
  </div>
{/if}

<style>
  .map-tooltip {
    position: fixed;
    z-index: 9999;
    pointer-events: none;
    padding: 10px 14px;
    background: var(--cds-layer-02, #262626);
    border: 1px solid var(--cds-border-subtle-01, #353535);
    border-radius: 4px;
    color: var(--cds-text-01, #f4f4f4);
    font-size: 0.8125rem;
    max-width: 300px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .tooltip-header {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .tooltip-name {
    font-weight: 600;
    font-size: 0.875rem;
  }

  .tooltip-desc {
    margin: 0;
    font-size: 0.75rem;
    color: var(--cds-text-02, #c6c6c6);
    line-height: 1.4;
    overflow-wrap: break-word;
  }

  .tooltip-npcs,
  .tooltip-counts {
    font-size: 0.75rem;
    color: var(--cds-text-02, #c6c6c6);
  }

  .tooltip-label {
    font-weight: 600;
    color: var(--cds-text-01, #f4f4f4);
    margin-right: 4px;
  }
</style>
