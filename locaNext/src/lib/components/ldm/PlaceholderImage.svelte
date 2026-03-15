<script>
  /**
   * PlaceholderImage.svelte - Styled SVG image placeholder with category-specific Carbon icon
   *
   * Renders a deterministic placeholder when entity images are missing.
   * Uses Carbon icons mapped to entity types for visual differentiation.
   *
   * Phase 21: AI Naming Coherence + Placeholders (Plan 02)
   */
  import { User, ShoppingCart, Lightning, GameWireless, Earth } from "carbon-icons-svelte";

  // Props
  let { entityType = '', entityName = '' } = $props();

  // Category-specific icon mapping
  const ICON_MAP = {
    character: User,
    item: ShoppingCart,
    skill: Lightning,
    gimmick: GameWireless,
    region: Earth
  };

  // Deterministic display
  let IconComponent = $derived(ICON_MAP[entityType] || User);
  let displayName = $derived(
    (entityName || entityType || 'Entity').slice(0, 20)
  );
</script>

<svg class="placeholder-image" viewBox="0 0 160 120" xmlns="http://www.w3.org/2000/svg">
  <rect
    x="0" y="0" width="160" height="120"
    rx="4" ry="4"
    fill="var(--cds-layer-02)"
  />
  <!-- Carbon icon centered via foreignObject -->
  <foreignObject x="56" y="20" width="48" height="48">
    <div class="icon-container" xmlns="http://www.w3.org/1999/xhtml">
      <IconComponent size={48} />
    </div>
  </foreignObject>
  <!-- Entity name at bottom -->
  <text
    x="80" y="100"
    text-anchor="middle"
    fill="var(--cds-text-03)"
    font-size="11"
    font-family="'IBM Plex Sans', sans-serif"
  >
    {displayName}
  </text>
</svg>

<style>
  .placeholder-image {
    width: 100%;
    max-width: 200px;
    border-radius: 4px;
  }

  .icon-container {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 48px;
    height: 48px;
    color: var(--cds-text-03);
  }
</style>
