<script>
  /**
   * ItemCodexPage.svelte - Item Codex encyclopedia page
   *
   * Browse, search, and inspect game items with card grid, group tabs,
   * client-side filtering, and knowledge resolution detail panel.
   *
   * Phase 102: Bulk load conversion (no pagination)
   */
  import { InlineLoading } from "carbon-components-svelte";
  import { Catalog, ArrowLeft } from "carbon-icons-svelte";
  import { getAuthHeaders, getApiBase } from "$lib/utils/api.js";
  import { logger } from "$lib/utils/logger.js";
  import CodexCard from "$lib/components/ldm/CodexCard.svelte";
  import ItemCodexDetail from "$lib/components/ldm/ItemCodexDetail.svelte";
  import SkeletonCard from "$lib/components/common/SkeletonCard.svelte";
  import { PageHeader, ErrorState } from "$lib/components/common";
  import { onMount } from "svelte";

  const API_BASE = getApiBase();

  // State
  let groups = $state([]);
  let activeGroup = $state(null);
  let allItems = $state([]);
  let selectedItem = $state(null);
  let searchQuery = $state("");
  let loadingGroups = $state(true);
  let loadingList = $state(true);
  let loadingDetail = $state(false);
  let apiError = $state(null);
  let failedImages = $state(new Set());

  // Derived: total item count for "All" tab
  let allItemCount = $derived(
    groups.reduce((sum, g) => sum + (g.item_count || 0), 0)
  );

  // Derived: client-side filtered items by group + search
  let filteredItems = $derived.by(() => {
    return allItems.filter(item => {
      if (activeGroup && item.group !== activeGroup) return false;
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        const searchable = `${item.name_kr || ''} ${item.name_translated || ''} ${item.strkey || ''} ${item.desc_kr || ''}`.toLowerCase();
        if (!searchable.includes(q)) return false;
      }
      return true;
    });
  });

  /**
   * Fetch item group hierarchy for tab navigation
   */
  async function fetchGroups() {
    loadingGroups = true;
    apiError = null;
    try {
      const response = await fetch(`${API_BASE}/api/ldm/codex/items/groups`, {
        headers: getAuthHeaders()
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      groups = data.groups || [];
      logger.info('Item Codex groups loaded', { count: groups.length, totalItems: data.total_items });
    } catch (err) {
      logger.error('Failed to fetch item groups', { error: err.message });
      apiError = 'Item Codex unavailable -- ensure gamedata folder is configured';
    } finally {
      loadingGroups = false;
    }
  }

  /**
   * Fetch all items in a single request (bulk load)
   */
  async function fetchAllItems() {
    loadingList = true;
    try {
      const response = await fetch(
        `${API_BASE}/api/ldm/codex/items`,
        { headers: getAuthHeaders() }
      );
      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const data = await response.json();
      allItems = data.items || [];
      logger.info('Item Codex bulk loaded', { total: allItems.length });
    } catch (err) {
      logger.error('Failed to fetch items', { error: err.message });
      apiError = 'Failed to load items';
    } finally {
      loadingList = false;
    }
  }

  /**
   * Fetch full item detail by strkey
   */
  async function fetchItemDetail(strkey) {
    loadingDetail = true;
    try {
      const response = await fetch(
        `${API_BASE}/api/ldm/codex/items/${encodeURIComponent(strkey)}`,
        { headers: getAuthHeaders() }
      );
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      selectedItem = await response.json();
      logger.info('Item detail loaded', { strkey });
    } catch (err) {
      logger.error('Failed to fetch item detail', { error: err.message, strkey });
    } finally {
      loadingDetail = false;
    }
  }

  /**
   * Handle group tab selection
   */
  function selectGroup(groupStrkey) {
    activeGroup = groupStrkey;
    selectedItem = null;
  }

  /**
   * Handle card click -- open detail panel
   */
  function selectCard(item) {
    fetchItemDetail(item.strkey);
  }

  /**
   * Navigate to related entity in detail panel
   */
  function handleSimilarNavigation(strkey) {
    fetchItemDetail(strkey);
  }

  /**
   * Back to card grid from detail view
   */
  function clearSelection() {
    selectedItem = null;
  }

  /**
   * Transform ItemCardResponse to CodexCard entity shape
   */
  function toCardEntity(item) {
    return {
      strkey: item.strkey,
      name: item.name_kr,
      entity_type: 'item',
      description: item.name_translated
        ? item.name_translated + (item.desc_kr ? '\n' + item.desc_kr : '')
        : item.desc_kr || '',
      image_texture: null,
      ai_image_url: item.image_urls?.length ? item.image_urls[0] : null,
      ai_image_urls: item.image_urls || [],
      related_entities: []
    };
  }

  onMount(() => {
    fetchGroups();
    fetchAllItems();
  });
</script>

<div class="item-codex-page">
  <!-- Header -->
  <PageHeader icon={Catalog} title="Item Codex" />

  <!-- Search Bar -->
  <div class="item-codex-search">
    <input
      type="search"
      placeholder="Search items by name, StrKey, or description..."
      bind:value={searchQuery}
      class="search-input"
      aria-label="Search items"
    />
  </div>

  {#if apiError}
    <div class="item-codex-state-container">
      <ErrorState message={apiError} onretry={() => { fetchGroups(); fetchAllItems(); }} />
    </div>
  {:else if loadingGroups}
    <div class="item-codex-loading" role="status" aria-live="polite">
      <InlineLoading description="Loading item groups..." />
    </div>
  {:else}
    <!-- Group Tabs -->
    <div class="item-codex-tabs" role="tablist" aria-label="Item group tabs">
      <button
        class="item-codex-tab"
        class:active={activeGroup === null}
        role="tab"
        aria-selected={activeGroup === null}
        onclick={() => selectGroup(null)}
      >
        <span class="tab-label">All</span>
        <span class="tab-count">{allItemCount}</span>
      </button>
      {#each groups as group (group.strkey)}
        <button
          class="item-codex-tab"
          class:active={activeGroup === group.strkey}
          role="tab"
          aria-selected={activeGroup === group.strkey}
          aria-label="{group.group_name} ({group.item_count})"
          onclick={() => selectGroup(group.strkey)}
        >
          <span class="tab-label">{group.group_name}</span>
          <span class="tab-count">{group.item_count}</span>
        </button>
      {/each}
    </div>

    <!-- Content Area -->
    <div class="item-codex-content">
      {#if selectedItem}
        <!-- Detail View -->
        <div class="detail-view">
          <button class="back-btn" onclick={clearSelection} aria-label="Back to item list">
            <ArrowLeft size={16} />
            <span>Back to list</span>
          </button>
          {#if loadingDetail}
            <InlineLoading description="Loading item details..." />
          {:else}
            <ItemCodexDetail
              item={selectedItem}
              onback={clearSelection}
              onsimilar={handleSimilarNavigation}
            />
          {/if}
        </div>
      {:else if loadingList}
        <div class="entity-grid">
          <SkeletonCard count={12} />
        </div>
      {:else}
        <!-- Card Grid -->
        <div class="entity-grid">
          {#each filteredItems as item (item.strkey)}
            <CodexCard
              entity={toCardEntity(item)}
              index={filteredItems.indexOf(item)}
              apiBase={API_BASE}
              {failedImages}
              onclick={() => selectCard(item)}
              onfailimage={(key) => {
                const next = new Set(failedImages);
                next.add(key);
                failedImages = next;
              }}
            />
          {/each}

          {#if filteredItems.length === 0 && !loadingList}
            <div class="no-entities">
              <p>No items found{searchQuery ? ` matching "${searchQuery}"` : ''}{activeGroup ? ` in this group` : ''} -- ensure gamedata files are loaded and indexed.</p>
            </div>
          {/if}
        </div>
      {/if}
    </div>
  {/if}
</div>

<style>
  .item-codex-page {
    display: flex;
    flex-direction: column;
    height: 100%;
    width: 100%;
    overflow: hidden;
  }

  .item-codex-state-container {
    display: flex;
    align-items: center;
    justify-content: center;
    flex: 1;
  }

  .item-codex-search {
    padding: 16px 16px 12px;
    background: var(--cds-layer-01);
    border-bottom: 1px solid var(--cds-border-subtle-01);
    flex-shrink: 0;
  }

  .search-input {
    width: 100%;
    padding: 8px 12px;
    background: var(--cds-field-01);
    border: 1px solid var(--cds-border-strong-01);
    border-radius: 4px;
    color: var(--cds-text-01);
    font-size: 0.875rem;
    outline: none;
    transition: border-color 0.15s;
  }

  .search-input:focus {
    border-color: var(--cds-focus);
    box-shadow: 0 0 0 1px var(--cds-focus);
  }

  .search-input::placeholder {
    color: var(--cds-text-03);
  }

  .item-codex-loading {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 32px;
  }

  .item-codex-tabs {
    display: flex;
    gap: 0;
    padding: 0 16px;
    background: var(--cds-layer-01);
    border-bottom: 2px solid var(--cds-border-subtle-01);
    flex-shrink: 0;
    overflow-x: auto;
  }

  .item-codex-tab {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 10px 16px;
    border: none;
    background: transparent;
    color: var(--cds-text-02);
    font-size: 0.875rem;
    cursor: pointer;
    border-bottom: 2px solid transparent;
    margin-bottom: -2px;
    white-space: nowrap;
    transition: all 0.15s;
  }

  .item-codex-tab:hover {
    color: var(--cds-text-01);
    background: var(--cds-layer-hover-01);
  }

  .item-codex-tab:focus {
    outline: 2px solid var(--cds-focus);
    outline-offset: -2px;
  }

  .item-codex-tab.active {
    color: var(--cds-text-01);
    border-bottom-color: var(--cds-interactive-01, #0f62fe);
    font-weight: 600;
  }

  .tab-count {
    font-size: 0.75rem;
    background: var(--cds-layer-02);
    padding: 1px 6px;
    border-radius: 8px;
  }

  .item-codex-content {
    flex: 1;
    overflow-y: auto;
    padding: var(--page-content-padding, 16px);
    min-height: 0;
  }

  .detail-view {
    display: flex;
    flex-direction: column;
    gap: 12px;
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
  }

  .back-btn:hover {
    background: var(--cds-layer-hover-01);
  }

  .back-btn:focus {
    outline: 2px solid var(--cds-focus);
    outline-offset: 1px;
  }

  .entity-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 16px;
  }

  .no-entities {
    grid-column: 1 / -1;
    text-align: center;
    padding: 32px;
    color: var(--cds-text-02);
    font-size: 0.875rem;
  }

</style>
