<script>
  /**
   * WorldMapPage.svelte - Interactive World Map main page
   *
   * Fetches world map data from the API and composes MapCanvas with
   * MapTooltip and MapDetailPanel for hover/click interactions.
   *
   * Phase 20: Interactive World Map (Plan 02)
   */
  import { InlineLoading } from "carbon-components-svelte";
  import { Earth } from "carbon-icons-svelte";
  import { getAuthHeaders, getApiBase } from "$lib/utils/api.js";
  import { logger } from "$lib/utils/logger.js";
  import { onMount } from "svelte";
  import MapCanvas from "$lib/components/ldm/MapCanvas.svelte";
  import MapTooltip from "$lib/components/ldm/MapTooltip.svelte";
  import MapDetailPanel from "$lib/components/ldm/MapDetailPanel.svelte";

  const API_BASE = getApiBase();

  // State
  let nodes = $state([]);
  let routes = $state([]);
  let bounds = $state({});
  let loading = $state(true);
  let apiError = $state(null);

  // Interaction state
  let tooltipNode = $state(null);
  let tooltipX = $state(0);
  let tooltipY = $state(0);
  let selectedNode = $state(null);

  /**
   * Fetch world map data from backend API
   */
  async function fetchMapData() {
    loading = true;
    apiError = null;

    try {
      const response = await fetch(`${API_BASE}/api/ldm/worldmap/data`, {
        headers: getAuthHeaders()
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const data = await response.json();
      nodes = data.nodes || [];
      routes = data.routes || [];
      bounds = data.bounds || {};

      logger.info('World map data loaded', {
        nodes: nodes.length,
        routes: routes.length
      });
    } catch (err) {
      logger.error('Failed to fetch world map data', { error: err.message });
      apiError = 'Map data unavailable -- ensure gamedata folder is configured';
    } finally {
      loading = false;
    }
  }

  /**
   * Handle node hover from MapCanvas
   */
  function handleNodeHover(node, x, y) {
    tooltipNode = node;
    tooltipX = x + 12;
    tooltipY = y + 12;
  }

  /**
   * Handle node leave
   */
  function handleNodeLeave() {
    tooltipNode = null;
  }

  /**
   * Handle node click
   */
  function handleNodeClick(node) {
    selectedNode = node;
  }

  /**
   * Close detail panel
   */
  function closePanel() {
    selectedNode = null;
  }

  onMount(() => {
    fetchMapData();
  });
</script>

<div class="worldmap-page">
  <!-- Header -->
  <div class="worldmap-header">
    <div class="header-title">
      <Earth size={24} />
      <h1>Interactive World Map</h1>
    </div>
    {#if nodes.length > 0}
      <span class="node-count">{nodes.length} regions, {routes.length} routes</span>
    {/if}
  </div>

  <!-- Content -->
  {#if apiError}
    <div class="worldmap-error">
      <p>{apiError}</p>
    </div>
  {:else if loading}
    <div class="worldmap-loading">
      <InlineLoading description="Loading world map..." />
    </div>
  {:else}
    <div class="worldmap-content">
      <div class="map-area" class:has-panel={selectedNode !== null}>
        <MapCanvas
          {nodes}
          {routes}
          {bounds}
          onNodeHover={handleNodeHover}
          onNodeLeave={handleNodeLeave}
          onNodeClick={handleNodeClick}
        />
      </div>

      {#if selectedNode}
        <MapDetailPanel
          node={selectedNode}
          onClose={closePanel}
        />
      {/if}
    </div>
  {/if}

  <!-- Tooltip (rendered outside map for fixed positioning) -->
  <MapTooltip
    node={tooltipNode}
    x={tooltipX}
    y={tooltipY}
  />
</div>

<style>
  .worldmap-page {
    display: flex;
    flex-direction: column;
    height: 100%;
    width: 100%;
    overflow: hidden;
  }

  .worldmap-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 16px;
    background: var(--cds-layer-01);
    border-bottom: 1px solid var(--cds-border-subtle-01);
    flex-shrink: 0;
  }

  .header-title {
    display: flex;
    align-items: center;
    gap: 8px;
    color: var(--cds-text-01);
  }

  .header-title h1 {
    font-size: 1.125rem;
    font-weight: 600;
    margin: 0;
  }

  .node-count {
    font-size: 0.8125rem;
    color: var(--cds-text-02);
  }

  .worldmap-error {
    display: flex;
    align-items: center;
    justify-content: center;
    flex: 1;
    padding: 32px;
    color: var(--cds-text-02);
  }

  .worldmap-error p {
    font-size: 0.875rem;
  }

  .worldmap-loading {
    display: flex;
    align-items: center;
    justify-content: center;
    flex: 1;
    padding: 32px;
  }

  .worldmap-content {
    flex: 1;
    display: flex;
    min-height: 0;
    overflow: hidden;
  }

  .map-area {
    flex: 1;
    min-width: 0;
    overflow: hidden;
  }

  .map-area.has-panel {
    /* Shrink map when detail panel is open */
  }
</style>
