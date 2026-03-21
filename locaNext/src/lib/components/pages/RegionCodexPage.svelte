<script>
  /**
   * RegionCodexPage.svelte - Region Codex main page with split layout
   *
   * Split view: left sidebar (FactionGroup tabs + tree navigation),
   * right area (interactive d3-zoom map + detail overlay).
   * Tree and map are bidirectionally synced via selectedStrkey.
   *
   * Phase 49: Region Codex UI + Interactive Map (Plan 02)
   */
  import { InlineLoading } from "carbon-components-svelte";
  import { Earth, ArrowLeft, Search, ChevronRight, ChevronDown } from "carbon-icons-svelte";
  import { getAuthHeaders, getApiBase } from "$lib/utils/api.js";
  import { logger } from "$lib/utils/logger.js";
  import { PageHeader, ErrorState } from "$lib/components/common";
  import RegionCodexMap from "$lib/components/ldm/RegionCodexMap.svelte";
  import RegionCodexDetail from "$lib/components/ldm/RegionCodexDetail.svelte";
  import { onMount } from "svelte";

  const API_BASE = getApiBase();

  // State: tree data
  let treeData = $state(null);
  let loadingTree = $state(true);
  let apiError = $state(null);

  // State: FactionGroup tab filtering
  let activeGroupStrkey = $state(null); // null = All

  // State: tree expansion
  let expandedGroups = $state(new Set());
  let expandedFactions = $state(new Set());

  // State: search
  let searchQuery = $state("");
  let searchTimer = null;
  let debouncedSearch = $state("");

  // State: selection & detail
  let selectedStrkey = $state(null);
  let selectedRegion = $state(null);
  let loadingDetail = $state(false);

  // Debounced search via $effect
  $effect(() => {
    const q = searchQuery;
    if (searchTimer) clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      debouncedSearch = q;
    }, 200);
    return () => {
      if (searchTimer) clearTimeout(searchTimer);
    };
  });

  // Derived: filtered tree based on active tab and search
  let filteredGroups = $derived.by(() => {
    if (!treeData?.groups) return [];

    let groups = treeData.groups;

    // Filter by active FactionGroup tab
    if (activeGroupStrkey) {
      groups = groups.filter(g => g.strkey === activeGroupStrkey);
    }

    // Filter by search query
    if (debouncedSearch) {
      const q = debouncedSearch.toLowerCase();
      groups = groups.map(group => {
        const filteredFactions = group.factions.map(faction => {
          const filteredRegions = faction.regions.filter(r =>
            r.name.toLowerCase().includes(q) ||
            r.strkey.toLowerCase().includes(q)
          );
          return { ...faction, regions: filteredRegions, region_count: filteredRegions.length };
        }).filter(f => f.regions.length > 0);

        return {
          ...group,
          factions: filteredFactions,
          faction_count: filteredFactions.length,
          region_count: filteredFactions.reduce((sum, f) => sum + f.region_count, 0)
        };
      }).filter(g => g.factions.length > 0);
    }

    return groups;
  });

  // Derived: all regions for the map (from filtered groups, with world_position info)
  let allRegionsForMap = $derived.by(() => {
    const regions = [];
    for (const group of filteredGroups) {
      for (const faction of group.factions) {
        for (const region of faction.regions) {
          regions.push(region);
        }
      }
    }
    return regions;
  });

  // Derived: total region count
  let totalRegions = $derived(treeData?.total_regions || 0);

  /**
   * Fetch faction tree from backend
   */
  async function fetchTree() {
    loadingTree = true;
    apiError = null;
    try {
      const response = await fetch(`${API_BASE}/api/ldm/codex/regions/tree`, {
        headers: getAuthHeaders()
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      treeData = await response.json();
      logger.info('Region Codex tree loaded', {
        groups: treeData.total_groups,
        factions: treeData.total_factions,
        regions: treeData.total_regions
      });
    } catch (err) {
      logger.error('Failed to fetch region tree', { error: err.message });
      apiError = 'Region Codex unavailable -- ensure gamedata folder is configured';
    } finally {
      loadingTree = false;
    }
  }

  /**
   * Fetch full region detail
   */
  async function fetchRegionDetail(strkey) {
    loadingDetail = true;
    try {
      const response = await fetch(
        `${API_BASE}/api/ldm/codex/regions/${encodeURIComponent(strkey)}`,
        { headers: getAuthHeaders() }
      );
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      selectedRegion = await response.json();
      logger.info('Region detail loaded', { strkey });
    } catch (err) {
      logger.error('Failed to fetch region detail', { error: err.message, strkey });
    } finally {
      loadingDetail = false;
    }
  }

  /**
   * Select a region (from tree or map click)
   */
  function selectRegion(strkey) {
    selectedStrkey = strkey;
    fetchRegionDetail(strkey);
  }

  /**
   * Handle map node click
   */
  function handleMapNodeClick(node) {
    selectRegion(node.strkey);

    // Auto-expand the tree to show this node
    if (treeData?.groups) {
      for (const group of treeData.groups) {
        for (const faction of group.factions) {
          if (faction.regions.some(r => r.strkey === node.strkey)) {
            const nextGroups = new Set(expandedGroups);
            nextGroups.add(group.strkey);
            expandedGroups = nextGroups;

            const nextFactions = new Set(expandedFactions);
            nextFactions.add(faction.strkey);
            expandedFactions = nextFactions;
            return;
          }
        }
      }
    }
  }

  /**
   * Clear selection (back button)
   */
  function clearSelection() {
    selectedStrkey = null;
    selectedRegion = null;
  }

  /**
   * Switch FactionGroup tab
   */
  function setActiveGroup(strkey) {
    activeGroupStrkey = strkey;
    // Auto-expand the selected group
    if (strkey) {
      const next = new Set(expandedGroups);
      next.add(strkey);
      expandedGroups = next;
    }
  }

  /**
   * Toggle group expand/collapse
   */
  function toggleGroup(strkey, event) {
    event.stopPropagation();
    const next = new Set(expandedGroups);
    if (next.has(strkey)) {
      next.delete(strkey);
    } else {
      next.add(strkey);
    }
    expandedGroups = next;
  }

  /**
   * Toggle faction expand/collapse
   */
  function toggleFaction(strkey, event) {
    event.stopPropagation();
    const next = new Set(expandedFactions);
    if (next.has(strkey)) {
      next.delete(strkey);
    } else {
      next.add(strkey);
    }
    expandedFactions = next;
  }

  /**
   * Get node_type color dot style
   */
  function getNodeDotColor(nodeType) {
    const colors = {
      Main: '#0f62fe',
      Sub: '#4589ff',
      Dungeon: '#da1e28',
      Town: '#24a148',
      Fortress: '#8a3ffc',
      Wilderness: '#007d79'
    };
    return colors[nodeType] || '#6f6f6f';
  }

  onMount(() => {
    fetchTree();
  });
</script>

<div class="region-codex-page">
  <!-- Header -->
  <PageHeader icon={Earth} title="Region Codex">
    {#if totalRegions > 0}
      <span class="region-count">{totalRegions} regions</span>
    {/if}
  </PageHeader>

  {#if apiError}
    <div class="region-state-container">
      <ErrorState message={apiError} onretry={fetchTree} />
    </div>
  {:else if loadingTree}
    <div class="region-loading" role="status" aria-live="polite">
      <InlineLoading description="Loading region data..." />
    </div>
  {:else if !treeData || treeData.total_regions === 0}
    <div class="region-state-container">
      <div class="empty-state">
        <Earth size={48} />
        <p>No region data available</p>
        <span class="empty-hint">Configure a gamedata folder to load region data</span>
      </div>
    </div>
  {:else}
    <!-- FactionGroup tabs -->
    <div class="group-tabs" role="tablist" aria-label="Faction group filter">
      <button
        class="group-tab"
        class:active={activeGroupStrkey === null}
        role="tab"
        aria-selected={activeGroupStrkey === null}
        onclick={() => setActiveGroup(null)}
      >
        All ({treeData.total_regions})
      </button>
      {#each treeData.groups as group (group.strkey)}
        <button
          class="group-tab"
          class:active={activeGroupStrkey === group.strkey}
          role="tab"
          aria-selected={activeGroupStrkey === group.strkey}
          onclick={() => setActiveGroup(group.strkey)}
        >
          {group.group_name} ({group.region_count})
        </button>
      {/each}
    </div>

    <!-- Split layout: tree + map -->
    <div class="region-layout">
      <!-- Left: Tree sidebar -->
      <aside class="tree-sidebar" aria-label="Region hierarchy">
        <!-- Search -->
        <div class="tree-search">
          <div class="search-wrapper">
            <Search size={14} />
            <input
              type="search"
              placeholder="Search regions..."
              bind:value={searchQuery}
              class="search-input"
              aria-label="Search regions"
            />
          </div>
        </div>

        <!-- Tree nodes -->
        <div class="tree-scroll">
          {#each filteredGroups as group (group.strkey)}
            {@const isGroupExpanded = expandedGroups.has(group.strkey)}
            <div class="tree-branch">
              <!-- FactionGroup header -->
              <button
                class="tree-node group-node"
                onclick={(e) => toggleGroup(group.strkey, e)}
                aria-expanded={isGroupExpanded}
              >
                <span class="tree-toggle">
                  {#if isGroupExpanded}
                    <ChevronDown size={14} />
                  {:else}
                    <ChevronRight size={14} />
                  {/if}
                </span>
                <span class="tree-node-name">{group.group_name}</span>
                <span class="tree-node-count">{group.region_count}</span>
              </button>

              {#if isGroupExpanded}
                {#each group.factions as faction (faction.strkey)}
                  {@const isFactionExpanded = expandedFactions.has(faction.strkey)}
                  <div class="tree-branch">
                    <!-- Faction sub-header -->
                    <button
                      class="tree-node faction-node"
                      onclick={(e) => toggleFaction(faction.strkey, e)}
                      aria-expanded={isFactionExpanded}
                    >
                      <span class="tree-toggle">
                        {#if isFactionExpanded}
                          <ChevronDown size={12} />
                        {:else}
                          <ChevronRight size={12} />
                        {/if}
                      </span>
                      <span class="tree-node-name">{faction.name}</span>
                      <span class="tree-node-count">{faction.region_count}</span>
                    </button>

                    {#if isFactionExpanded}
                      {#each faction.regions as region (region.strkey)}
                        <button
                          class="tree-node region-leaf"
                          class:selected={selectedStrkey === region.strkey}
                          onclick={() => selectRegion(region.strkey)}
                        >
                          <span
                            class="node-type-dot"
                            style="background: {getNodeDotColor(region.node_type)}"
                            title={region.node_type || 'Unknown'}
                          ></span>
                          <span class="tree-node-name">{region.name}</span>
                          {#if region.has_position}
                            <span class="position-indicator" title="Has world position">*</span>
                          {/if}
                        </button>
                      {/each}
                    {/if}
                  </div>
                {/each}
              {/if}
            </div>
          {/each}

          {#if filteredGroups.length === 0}
            <div class="tree-empty">
              <p>No regions found{debouncedSearch ? ` matching "${debouncedSearch}"` : ''}</p>
            </div>
          {/if}
        </div>
      </aside>

      <!-- Right: Map + Detail overlay -->
      <div class="map-and-detail">
        <!-- Map -->
        <div class="map-area" class:has-detail={selectedRegion !== null}>
          <RegionCodexMap
            regions={allRegionsForMap}
            {selectedStrkey}
            onNodeClick={handleMapNodeClick}
            onNodeHover={() => {}}
            onNodeLeave={() => {}}
          />
        </div>

        <!-- Detail panel overlay -->
        {#if selectedRegion || loadingDetail}
          <div class="detail-panel">
            <button class="back-btn" onclick={clearSelection} aria-label="Close detail panel">
              <ArrowLeft size={16} />
              <span>Back</span>
            </button>
            {#if loadingDetail && !selectedRegion}
              <div class="detail-loading">
                <InlineLoading description="Loading region detail..." />
              </div>
            {:else}
              <RegionCodexDetail region={selectedRegion} onback={clearSelection} />
            {/if}
          </div>
        {/if}
      </div>
    </div>
  {/if}
</div>

<style>
  .region-codex-page {
    display: flex;
    flex-direction: column;
    height: 100%;
    width: 100%;
    overflow: hidden;
  }

  .region-count {
    font-size: 0.8125rem;
    color: var(--cds-text-02);
  }

  .region-state-container {
    display: flex;
    align-items: center;
    justify-content: center;
    flex: 1;
  }

  .region-loading {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 32px;
  }

  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
    color: var(--cds-text-03);
    text-align: center;
  }

  .empty-state p {
    font-size: 1rem;
    font-weight: 500;
    color: var(--cds-text-02);
    margin: 0;
  }

  .empty-hint {
    font-size: 0.8125rem;
  }

  /* FactionGroup tabs */
  .group-tabs {
    display: flex;
    gap: 0;
    padding: 0 12px;
    background: var(--cds-layer-01);
    border-bottom: 2px solid var(--cds-border-subtle-01);
    overflow-x: auto;
    flex-shrink: 0;
  }

  .group-tab {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 8px 14px;
    border: none;
    background: transparent;
    color: var(--cds-text-02);
    font-size: 0.8125rem;
    cursor: pointer;
    border-bottom: 2px solid transparent;
    margin-bottom: -2px;
    white-space: nowrap;
    transition: all 0.15s;
  }

  .group-tab:hover {
    color: var(--cds-text-01);
    background: var(--cds-layer-hover-01);
  }

  .group-tab:focus {
    outline: 2px solid var(--cds-focus);
    outline-offset: -2px;
  }

  .group-tab.active {
    color: var(--cds-text-01);
    border-bottom-color: var(--cds-interactive-01, #0f62fe);
    font-weight: 600;
  }

  /* Split layout */
  .region-layout {
    display: flex;
    flex: 1;
    min-height: 0;
    overflow: hidden;
  }

  /* Tree sidebar */
  .tree-sidebar {
    width: 280px;
    flex-shrink: 0;
    border-right: 1px solid var(--cds-border-subtle-01);
    background: var(--cds-layer-01);
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .tree-search {
    padding: 8px 10px;
    border-bottom: 1px solid var(--cds-border-subtle-01);
    flex-shrink: 0;
  }

  .search-wrapper {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 10px;
    background: var(--cds-field-01);
    border: 1px solid var(--cds-border-strong-01);
    border-radius: 4px;
    color: var(--cds-text-03);
    transition: border-color 0.15s;
  }

  .search-wrapper:focus-within {
    border-color: var(--cds-focus);
    box-shadow: 0 0 0 1px var(--cds-focus);
    color: var(--cds-text-01);
  }

  .search-input {
    flex: 1;
    border: none;
    background: transparent;
    color: var(--cds-text-01);
    font-size: 0.8125rem;
    outline: none;
  }

  .search-input::placeholder {
    color: var(--cds-text-03);
  }

  .tree-scroll {
    flex: 1;
    overflow-y: auto;
    padding-bottom: 8px;
  }

  .tree-branch {
    display: flex;
    flex-direction: column;
  }

  .tree-node {
    display: flex;
    align-items: center;
    gap: 4px;
    width: 100%;
    padding: 6px 10px;
    border: none;
    background: transparent;
    color: var(--cds-text-02);
    font-size: 0.8125rem;
    cursor: pointer;
    text-align: left;
    transition: all 0.12s;
    border-left: 3px solid transparent;
  }

  .tree-node:hover {
    background: var(--cds-layer-hover-01);
    color: var(--cds-text-01);
  }

  .tree-node:focus {
    outline: 2px solid var(--cds-focus);
    outline-offset: -2px;
  }

  .group-node {
    padding-left: 8px;
    font-weight: 600;
    color: var(--cds-text-01);
    font-size: 0.8125rem;
    background: var(--cds-layer-02);
    border-bottom: 1px solid var(--cds-border-subtle-01);
  }

  .faction-node {
    padding-left: 24px;
    font-weight: 500;
    color: var(--cds-text-01);
    font-size: 0.8125rem;
  }

  .region-leaf {
    padding-left: 40px;
    font-weight: 400;
  }

  .region-leaf.selected {
    background: var(--cds-layer-selected-01, rgba(15, 98, 254, 0.1));
    color: var(--cds-text-01);
    border-left-color: var(--cds-interactive-01, #0f62fe);
    font-weight: 500;
  }

  .tree-toggle {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    width: 16px;
    height: 16px;
    color: var(--cds-text-03);
  }

  .tree-node-name {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .tree-node-count {
    font-size: 0.6875rem;
    color: var(--cds-text-03);
    background: var(--cds-layer-02);
    padding: 1px 6px;
    border-radius: 8px;
    flex-shrink: 0;
  }

  .node-type-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .position-indicator {
    font-size: 0.75rem;
    color: var(--cds-support-success, #24a148);
    font-weight: 700;
  }

  .tree-empty {
    padding: 24px 16px;
    text-align: center;
    color: var(--cds-text-03);
    font-size: 0.8125rem;
  }

  .tree-empty p {
    margin: 0;
  }

  /* Map and detail area */
  .map-and-detail {
    flex: 1;
    display: flex;
    min-width: 0;
    position: relative;
    overflow: hidden;
  }

  .map-area {
    flex: 1;
    min-width: 0;
    overflow: hidden;
  }

  .map-area.has-detail {
    flex: 1 1 0;
  }

  /* Detail panel */
  .detail-panel {
    width: 360px;
    flex-shrink: 0;
    border-left: 1px solid var(--cds-border-subtle-01);
    background: var(--cds-background);
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 12px;
  }

  .back-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px;
    border: 1px solid var(--cds-border-strong-01);
    border-radius: 4px;
    background: transparent;
    color: var(--cds-text-01);
    font-size: 0.8125rem;
    cursor: pointer;
    align-self: flex-start;
    transition: background 0.15s;
    flex-shrink: 0;
  }

  .back-btn:hover {
    background: var(--cds-layer-hover-01);
  }

  .back-btn:focus {
    outline: 2px solid var(--cds-focus);
    outline-offset: 1px;
  }

  .detail-loading {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 24px;
  }
</style>
