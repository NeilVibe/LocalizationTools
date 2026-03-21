<script>
  /**
   * ItemCodexPage.svelte - Item Codex encyclopedia page
   *
   * Browse, search, and inspect game items with card grid, group tabs,
   * infinite scroll, and knowledge resolution detail panel.
   *
   * Phase 46: Item Codex UI (Plan 02)
   */
  import { InlineLoading } from "carbon-components-svelte";
  import { Catalog, ArrowLeft } from "carbon-icons-svelte";
  import { getAuthHeaders, getApiBase } from "$lib/utils/api.js";
  import { logger } from "$lib/utils/logger.js";
  import CodexCard from "$lib/components/ldm/CodexCard.svelte";
  import ItemCodexDetail from "$lib/components/ldm/ItemCodexDetail.svelte";
  import InfiniteScroll from "$lib/components/common/InfiniteScroll.svelte";
  import SkeletonCard from "$lib/components/common/SkeletonCard.svelte";
  import { PageHeader, ErrorState } from "$lib/components/common";
  import { onMount } from "svelte";

  const API_BASE = getApiBase();
  const PAGE_SIZE = 50;

  // State
  let groups = $state([]);
  let activeGroup = $state(null);
  let items = $state([]);
  let totalItems = $state(0);
  let selectedItem = $state(null);
  let searchQuery = $state("");
  let loadingGroups = $state(true);
  let loadingList = $state(false);
  let loadingDetail = $state(false);
  let apiError = $state(null);
  let failedImages = $state(new Set());
  let currentPage = $state(0);
  let hasMore = $state(true);
  let loadingMore = $state(false);

  // Debounce search
  let searchTimer = null;
  let abortController = null;

  // Derived: total item count for "All" tab
  let allItemCount = $derived(
    groups.reduce((sum, g) => sum + (g.item_count || 0), 0)
  );

  // Debounced search via $effect
  $effect(() => {
    const q = searchQuery;
    if (searchTimer) clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      currentPage = 0;
      hasMore = true;
      fetchItems(0, activeGroup, q);
    }, 300);
    return () => {
      if (searchTimer) clearTimeout(searchTimer);
    };
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
      totalItems = data.total_items || 0;
      logger.info('Item Codex groups loaded', { count: groups.length, totalItems });
    } catch (err) {
      logger.error('Failed to fetch item groups', { error: err.message });
      apiError = 'Item Codex unavailable -- ensure gamedata folder is configured';
    } finally {
      loadingGroups = false;
    }
  }

  /**
   * Fetch paginated items with optional group/search filtering
   */
  async function fetchItems(page, group, query) {
    if (abortController) abortController.abort();
    abortController = new AbortController();

    if (page === 0) {
      loadingList = true;
      items = [];
    } else {
      loadingMore = true;
    }

    try {
      const params = new URLSearchParams();
      params.set('offset', String(page * PAGE_SIZE));
      params.set('limit', String(PAGE_SIZE));
      if (group) params.set('group', group);
      if (query) params.set('q', query);

      const response = await fetch(
        `${API_BASE}/api/ldm/codex/items?${params.toString()}`,
        { headers: getAuthHeaders(), signal: abortController.signal }
      );
      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const data = await response.json();
      const batch = data.items || [];

      if (page === 0) {
        items = batch;
      } else {
        items = [...items, ...batch];
      }
      hasMore = data.has_more ?? false;
      currentPage = page;
      totalItems = data.total ?? totalItems;

      logger.info('Item Codex items loaded', { page, count: batch.length, total: data.total });
    } catch (err) {
      if (err.name === 'AbortError') return;
      logger.error('Failed to fetch items', { error: err.message });
      if (page === 0) apiError = 'Failed to load items';
    } finally {
      loadingList = false;
      loadingMore = false;
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
   * Load more items (InfiniteScroll callback)
   */
  function loadMore() {
    if (hasMore && !loadingMore) {
      fetchItems(currentPage + 1, activeGroup, searchQuery);
    }
  }

  /**
   * Handle group tab selection
   */
  function selectGroup(groupStrkey) {
    activeGroup = groupStrkey;
    selectedItem = null;
    currentPage = 0;
    hasMore = true;
    fetchItems(0, groupStrkey, searchQuery);
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
      ai_image_url: item.image_url || null,
      related_entities: []
    };
  }

  onMount(() => {
    fetchGroups().then(() => {
      fetchItems(0, null, "");
    });
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
      <ErrorState message={apiError} onretry={() => { fetchGroups(); fetchItems(0, null, ""); }} />
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
          {#each items as item (item.strkey)}
            <CodexCard
              entity={toCardEntity(item)}
              index={items.indexOf(item)}
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

          {#if items.length === 0 && !loadingList}
            <div class="no-entities">
              <p>No items found{searchQuery ? ` matching "${searchQuery}"` : ''} -- ensure gamedata files are loaded and indexed.</p>
            </div>
          {/if}
        </div>

        <InfiniteScroll
          onloadmore={loadMore}
          loading={loadingMore}
          {hasMore}
        />

        {#if loadingMore}
          <div class="skeleton-loading-grid">
            <SkeletonCard count={6} />
          </div>
        {/if}
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

  .skeleton-loading-grid {
    padding: 0;
    margin-top: 12px;
  }
</style>
