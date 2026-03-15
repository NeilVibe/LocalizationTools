<script>
  /**
   * PlaceholderImage.svelte - Styled image placeholder with category-specific Carbon icon
   *
   * Renders a deterministic placeholder when entity images are missing.
   * Uses Carbon icons mapped to entity types for visual differentiation.
   * Uses div+CSS layout for Chromium/Electron compatibility (no SVG wrapping).
   *
   * Phase 21: AI Naming Coherence + Placeholders (Plan 02)
   * Phase 24: UX-04 - Replaced SVG with div layout for Electron compat
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

<div class="placeholder-image">
  <div class="icon-container">
    <IconComponent size={48} />
  </div>
  <span class="placeholder-name">{displayName}</span>
</div>

<style>
  .placeholder-image {
    width: 100%;
    max-width: 200px;
    aspect-ratio: 160 / 120;
    border-radius: 4px;
    background: var(--cds-layer-02);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 8px;
  }

  .icon-container {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 48px;
    height: 48px;
    color: var(--cds-text-03);
  }

  .placeholder-name {
    font-size: 11px;
    font-family: 'IBM Plex Sans', sans-serif;
    color: var(--cds-text-03);
    text-align: center;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 90%;
  }
</style>
