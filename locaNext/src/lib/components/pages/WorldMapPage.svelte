<script>
  /**
   * WorldMapPage.svelte - Interactive World Map main page
   *
   * Fetches world map data from the API and composes MapCanvas with
   * MapTooltip and MapDetailPanel for hover/click interactions.
   *
   * Phase 20: Interactive World Map (Plan 02)
   */
  import { Earth } from "carbon-icons-svelte";
  import { getAuthHeaders, getApiBase } from "$lib/utils/api.js";
  import { logger } from "$lib/utils/logger.js";
  import { onMount } from "svelte";
  import { PageHeader, EmptyState, ErrorState } from "$lib/components/common";
  import MapCanvas from "$lib/components/ldm/MapCanvas.svelte";
  import MapTooltip from "$lib/components/ldm/MapTooltip.svelte";
  import MapDetailPanel from "$lib/components/ldm/MapDetailPanel.svelte";

  const API_BASE = getApiBase();

  // State
  let nodes = $state([]);
  let routes = $state([]);
  let bounds = $state({});
  let megaRegions = $state([]);
  let backgroundImage = $state(null);
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
      megaRegions = data.mega_regions || [];
      backgroundImage = data.background_image || null;

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
    if (selectedNode) return;  // Suppress tooltip when detail panel is open
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
    tooltipNode = null;  // Clear tooltip when panel opens
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
  <PageHeader icon={Earth} title="Interactive World Map">
    {#if nodes.length > 0}
      <span class="node-count">{nodes.length} regions, {routes.length} routes</span>
    {/if}
  </PageHeader>

  <!-- Content -->
  {#if apiError}
    <div class="worldmap-state-container">
      <ErrorState message={apiError} onretry={fetchMapData} />
    </div>
  {:else if loading}
    <div class="worldmap-loading" role="status" aria-live="polite" aria-label="Loading world map regions and routes">
      <div class="shimmer-skeleton shimmer-map-area"></div>
    </div>
  {:else if nodes.length === 0}
    <div class="worldmap-state-container">
      <EmptyState
        icon={Earth}
        headline="No map data available"
        description="Configure a gamedata folder in Game Data page to load world map regions"
      />
    </div>
  {:else}
    <div class="worldmap-content">
      <div class="map-area" class:has-panel={selectedNode !== null}>
        <MapCanvas
          {nodes}
          {routes}
          {bounds}
          {megaRegions}
          {backgroundImage}
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

  .node-count {
    font-size: 0.8125rem;
    color: var(--cds-text-02);
  }

  .worldmap-state-container {
    display: flex;
    align-items: center;
    justify-content: center;
    flex: 1;
  }

  .worldmap-loading {
    display: flex;
    align-items: center;
    justify-content: center;
    flex: 1;
    padding: 2rem;
  }

  .shimmer-skeleton {
    background: var(--skeleton-bg, var(--cds-layer-02));
    animation: skeleton-shimmer 1.5s ease-in-out infinite;
  }

  .shimmer-map-area {
    width: 100%;
    height: 400px;
    border-radius: 8px;
  }

  @keyframes skeleton-shimmer {
    0%, 100% { opacity: 0.4; }
    50% { opacity: 0.8; }
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
    flex: 1 1 0;
  }
</style>
