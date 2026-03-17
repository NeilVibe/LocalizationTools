<script>
  /**
   * MapTooltip.svelte - Fantasy-styled hover tooltip for world map nodes
   *
   * Shows region name (Korean), danger zone indicator, description,
   * NPC list, and entity counts at cursor position when hovering map nodes.
   *
   * Phase 38: Fantasy World Map (Plan 03)
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
      <span class="tooltip-name">{node.name_kr || node.name}</span>
      <Tag type={TYPE_TAG_COLORS[node.region_type] || 'gray'} size="sm">
        {node.region_type}
      </Tag>
    </div>

    {#if node.danger_level}
      <div class="tooltip-danger">
        <span class="danger-dot danger-{node.danger_level}"></span>
        <span>{node.danger_level === 1 ? 'Safe' : node.danger_level === 2 ? 'Moderate' : 'Dangerous'} Zone</span>
      </div>
    {/if}

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
    padding: 0.625rem 0.875rem;
    background: rgba(26, 20, 8, 0.95);
    border: 1px solid rgba(212, 154, 92, 0.3);
    border-radius: 6px;
    color: rgba(240, 184, 120, 0.85);
    font-size: 0.8125rem;
    max-width: 300px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.6), 0 0 0 1px rgba(212, 154, 92, 0.1);
    backdrop-filter: blur(8px);
    display: flex;
    flex-direction: column;
    gap: 0.375rem;
  }

  .tooltip-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .tooltip-name {
    font-weight: 700;
    font-size: 0.9375rem;
    color: rgba(240, 184, 120, 0.95);
    font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
  }

  .tooltip-danger {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    font-size: 0.6875rem;
    font-weight: 500;
    color: rgba(212, 154, 92, 0.7);
  }

  .danger-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .danger-dot.danger-1 { background: #24a148; }
  .danger-dot.danger-2 { background: #f1c21b; }
  .danger-dot.danger-3 { background: #da1e28; }

  .tooltip-desc {
    margin: 0;
    font-size: 0.75rem;
    color: rgba(212, 154, 92, 0.6);
    line-height: 1.4;
    overflow-wrap: break-word;
  }

  .tooltip-npcs,
  .tooltip-counts {
    font-size: 0.75rem;
    color: rgba(212, 154, 92, 0.6);
  }

  .tooltip-label {
    font-weight: 600;
    color: rgba(240, 184, 120, 0.8);
    margin-right: 0.25rem;
  }
</style>
