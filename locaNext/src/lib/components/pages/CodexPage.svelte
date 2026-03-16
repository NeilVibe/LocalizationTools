<script>
  /**
   * CodexPage.svelte - Game World Codex main page
   *
   * Entity type browsing with tabs, semantic search, and rich entity detail views.
   * Accessible from both Translator and Game Dev navigation modes.
   *
   * Phase 19: Game World Codex (Plan 02)
   */
  import { InlineLoading, Tag, Button, ProgressBar, InlineNotification } from "carbon-components-svelte";
  import { Book, ArrowLeft, ImageReference, Close } from "carbon-icons-svelte";
  import { getAuthHeaders, getApiBase } from "$lib/utils/api.js";
  import { logger } from "$lib/utils/logger.js";
  import { websocket } from "$lib/api/websocket.js";
  import CodexSearchBar from "$lib/components/ldm/CodexSearchBar.svelte";
  import PlaceholderImage from "$lib/components/ldm/PlaceholderImage.svelte";
  import CodexEntityDetail from "$lib/components/ldm/CodexEntityDetail.svelte";
  import InfiniteScroll from "$lib/components/common/InfiniteScroll.svelte";
  import SkeletonCard from "$lib/components/common/SkeletonCard.svelte";
  import { PageHeader, ErrorState } from "$lib/components/common";
  import { onMount } from "svelte";
  import { get } from "svelte/store";
  import { codexSearchQuery } from "$lib/stores/navigation.js";

  const API_BASE = getApiBase();

  // Type badge colors
  const TYPE_COLORS = {
    character: 'purple',
    item: 'cyan',
    skill: 'magenta',
    region: 'teal',
    gimmick: 'warm-gray'
  };

  // Display labels for entity types
  const TYPE_LABELS = {
    character: 'Characters',
    item: 'Items',
    skill: 'Skills',
    region: 'Regions',
    gimmick: 'Gimmicks'
  };

  // State
  let entityTypes = $state({}); // { type: count }
  let activeTab = $state('');
  let entities = $state([]);
  let selectedEntity = $state(null);
  let loadingTypes = $state(true);
  let loadingList = $state(false);
  let loadingDetail = $state(false);
  let apiError = $state(null);
  let failedImages = $state(new Set());

  // Pagination state
  let currentPage = $state(0);
  let hasMore = $state(true);
  let loadingMore = $state(false);
  const PAGE_SIZE = 50;

  // Per-tab cache: Map<entityType, { entities: [], currentPage: number, hasMore: boolean }>
  let tabCache = $state(new Map());

  // AI image generation state
  let imageGenAvailable = $state(false);
  let batchPreview = $state(null);
  let batchInProgress = $state(false);
  let batchProgress = $state(0);
  let batchStatus = $state('');
  let batchOperationId = $state(null);
  let batchError = $state(null);

  // Image-gen availability checked in onMount below

  // WebSocket listeners for batch progress
  let unsubProgress;
  let unsubComplete;
  let unsubFailed;

  $effect(() => {
    if (!batchInProgress || !batchOperationId) return;

    websocket.socket?.emit('subscribe', { events: ['progress'] });

    unsubProgress = websocket.on('progress_update', (data) => {
      if (data.operation_id === batchOperationId) {
        batchProgress = data.progress_percentage ?? 0;
        batchStatus = data.current_step ?? `${data.completed_steps}/${data.total_steps} images generated`;
      }
    });

    unsubComplete = websocket.on('operation_complete', (data) => {
      if (data.operation_id === batchOperationId) {
        batchInProgress = false;
        batchProgress = 100;
        batchStatus = 'Complete';
        batchOperationId = null;
        // Invalidate cache for this tab so fresh data is fetched
        tabCache.delete(activeTab);
        tabCache = new Map(tabCache);
        fetchEntityPage(activeTab, 0);
      }
    });

    unsubFailed = websocket.on('operation_failed', (data) => {
      if (data.operation_id === batchOperationId) {
        batchInProgress = false;
        batchError = data.error_message;
        batchOperationId = null;
      }
    });

    return () => {
      unsubProgress?.();
      unsubComplete?.();
      unsubFailed?.();
    };
  });

  /**
   * Preview batch generation (cost estimate)
   */
  async function previewBatchGenerate() {
    batchError = null;
    try {
      const response = await fetch(
        `${API_BASE}/api/ldm/codex/batch-generate/${activeTab}?confirm=false`,
        { method: 'POST', headers: getAuthHeaders() }
      );
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      batchPreview = await response.json();
    } catch (err) {
      logger.error('Batch preview failed', { error: err.message });
      batchError = err.message;
    }
  }

  /**
   * Confirm and start batch generation
   */
  async function confirmBatchGenerate() {
    batchPreview = null;
    batchError = null;
    try {
      const response = await fetch(
        `${API_BASE}/api/ldm/codex/batch-generate/${activeTab}?confirm=true`,
        { method: 'POST', headers: getAuthHeaders() }
      );
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      batchInProgress = true;
      batchOperationId = data.operation_id;
      batchProgress = 0;
      batchStatus = `0/${data.to_generate} images generated`;
    } catch (err) {
      logger.error('Batch generation start failed', { error: err.message });
      batchError = err.message;
    }
  }

  /**
   * Cancel running batch generation
   */
  async function cancelBatchGenerate() {
    if (!batchOperationId) return;
    const previousStatus = batchStatus;
    batchStatus = 'Cancelling...';
    try {
      await fetch(
        `${API_BASE}/api/ldm/codex/batch-generate/cancel/${batchOperationId}`,
        { method: 'POST', headers: getAuthHeaders() }
      );
    } catch (err) {
      logger.error('Batch cancel failed', { error: err.message });
      batchStatus = previousStatus;
      batchError = 'Failed to cancel: ' + (err.message || 'Unknown error');
    }
  }

  // Sorted tab list (exclude 'knowledge' internal type)
  let tabList = $derived(
    Object.entries(entityTypes)
      .filter(([type]) => type !== 'knowledge')
      .sort(([a], [b]) => {
        const order = ['character', 'item', 'skill', 'region', 'gimmick'];
        const idxA = order.indexOf(a);
        const idxB = order.indexOf(b);
        // Unknown types (-1) sort last by mapping to a high number
        return (idxA === -1 ? 999 : idxA) - (idxB === -1 ? 999 : idxB);
      })
  );

  /**
   * Fetch available entity types with counts
   */
  async function fetchTypes() {
    loadingTypes = true;
    apiError = null;

    try {
      const response = await fetch(`${API_BASE}/api/ldm/codex/types`, {
        headers: getAuthHeaders()
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      entityTypes = await response.json();
      logger.info('Codex entity types loaded', entityTypes);

      // Auto-select first non-knowledge tab
      const firstTab = Object.keys(entityTypes).find(t => t !== 'knowledge');
      if (firstTab) {
        activeTab = firstTab;
        await fetchEntityPage(firstTab, 0);
      }
    } catch (err) {
      logger.error('Failed to fetch codex types', { error: err.message });
      apiError = 'Codex unavailable -- ensure gamedata folder is configured';
    } finally {
      loadingTypes = false;
    }
  }

  /**
   * Fetch a page of entities for a given type (paginated)
   */
  async function fetchEntityPage(entityType, page) {
    if (loadingMore && page > 0) return;
    if (page === 0) { loadingList = true; entities = []; }
    else { loadingMore = true; }

    try {
      const offset = page * PAGE_SIZE;
      const response = await fetch(
        `${API_BASE}/api/ldm/codex/list/${entityType}?offset=${offset}&limit=${PAGE_SIZE}`,
        { headers: getAuthHeaders() }
      );

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const data = await response.json();
      const batch = data.entities || [];

      // Guard against stale responses from rapid tab switching
      if (entityType !== activeTab) return;

      if (page === 0) {
        entities = batch;
      } else {
        entities = [...entities, ...batch];
      }
      hasMore = data.has_more ?? (batch.length === PAGE_SIZE);
      currentPage = page;

      // Update tab cache for instant switching
      tabCache.set(entityType, { entities, currentPage, hasMore });
      tabCache = new Map(tabCache);

      logger.info('Codex entity page loaded', { type: entityType, page, count: batch.length, total: data.total });
    } catch (err) {
      logger.error('Failed to fetch entity page', { error: err.message });
      if (page === 0) apiError = 'Failed to load entities';
    } finally {
      loadingList = false;
      loadingMore = false;
    }
  }

  /**
   * Load more entities (called by InfiniteScroll sentinel)
   */
  function loadMore() {
    if (hasMore && !loadingMore) {
      fetchEntityPage(activeTab, currentPage + 1);
    }
  }

  /**
   * Handle tab selection
   */
  function selectTab(type) {
    activeTab = type;
    selectedEntity = null;

    // Check cache for instant tab switching
    const cached = tabCache.get(type);
    if (cached) {
      entities = cached.entities;
      currentPage = cached.currentPage;
      hasMore = cached.hasMore;
      return;
    }

    // No cache -- fetch from page 0
    currentPage = 0;
    hasMore = true;
    fetchEntityPage(type, 0);
  }

  /**
   * Handle entity card click
   */
  function selectEntity(entity) {
    selectedEntity = entity;
  }

  /**
   * Handle search result selection
   */
  function handleSearchResult(entity) {
    selectedEntity = entity;
    // Switch to entity's tab if different
    if (entity.entity_type !== activeTab && entity.entity_type !== 'knowledge') {
      activeTab = entity.entity_type;
      currentPage = 0;
      hasMore = true;
      fetchEntityPage(entity.entity_type, 0);
    }
  }

  /**
   * Handle similar/related entity navigation
   */
  async function handleSimilarNavigation(strkey) {
    loadingDetail = true;

    try {
      // Try to find the entity type by searching all types
      const response = await fetch(`${API_BASE}/api/ldm/codex/search?q=${encodeURIComponent(strkey)}&limit=1`, {
        headers: getAuthHeaders()
      });

      if (response.ok) {
        const data = await response.json();
        if (data.results && data.results.length > 0) {
          selectedEntity = data.results[0].entity;
          if (selectedEntity.entity_type !== activeTab && selectedEntity.entity_type !== 'knowledge') {
            activeTab = selectedEntity.entity_type;
            currentPage = 0;
            hasMore = true;
            fetchEntityPage(selectedEntity.entity_type, 0);
          }
        }
      }
    } catch (err) {
      logger.error('Failed to navigate to entity', { strkey, error: err.message });
    } finally {
      loadingDetail = false;
    }
  }

  /**
   * Back to entity list
   */
  function clearSelection() {
    selectedEntity = null;
  }

  /**
   * Truncate description for card display
   */
  function truncate(text, maxLen = 60) {
    if (!text) return '';
    const clean = text.replace(/<br\s*\/?>/gi, ' ');
    return clean.length > maxLen ? clean.slice(0, maxLen) + '...' : clean;
  }

  onMount(() => {
    // Check image-gen availability
    fetch(`${API_BASE}/api/ldm/codex/image-gen/status`, { headers: getAuthHeaders() })
      .then(r => r.json())
      .then(data => { imageGenAvailable = data.available; })
      .catch((err) => { logger.warning('Image gen status check failed', { error: err?.message }); imageGenAvailable = false; });

    fetchTypes().then(() => {
      // Consume codexSearchQuery if set (e.g., navigated from MapDetailPanel NPC click)
      const pendingQuery = get(codexSearchQuery);
      if (pendingQuery) {
        codexSearchQuery.set('');
        handleSimilarNavigation(pendingQuery);
      }
    });
  });
</script>

<div class="codex-page">
  <!-- Header -->
  <PageHeader icon={Book} title="Game World Codex" />

  <!-- Search Bar -->
  <div class="codex-search">
    <CodexSearchBar onresult={handleSearchResult} />
  </div>

  {#if apiError}
    <div class="codex-state-container">
      <ErrorState message={apiError} onretry={fetchTypes} />
    </div>
  {:else if loadingTypes}
    <div class="codex-loading" role="status" aria-live="polite">
      <InlineLoading description="Loading Codex entity types..." />
    </div>
  {:else}
    <!-- Entity Type Tabs -->
    <div class="codex-tabs" role="tablist" aria-label="Entity type tabs">
      {#each tabList as [type, count] (type)}
        <button
          class="codex-tab"
          class:active={activeTab === type}
          role="tab"
          aria-selected={activeTab === type}
          aria-label="{TYPE_LABELS[type] || type} ({count})"
          onclick={() => selectTab(type)}
        >
          <span class="tab-label">{TYPE_LABELS[type] || type}</span>
          <span class="tab-count">{count}</span>
        </button>
      {/each}
    </div>

    <!-- Batch Generation Controls -->
    {#if imageGenAvailable && activeTab}
      <div class="batch-controls">
        {#if batchInProgress}
          <div class="batch-progress">
            <ProgressBar value={batchProgress} labelText={batchStatus} />
            <Button kind="ghost" size="small" icon={Close} iconDescription="Cancel" onclick={cancelBatchGenerate}>Cancel</Button>
          </div>
        {:else if batchPreview}
          <InlineNotification
            kind="info"
            lowContrast
            hideCloseButton
            title="Batch Generation"
            subtitle="{batchPreview.to_generate} entities need images. Estimated cost: {batchPreview.estimated_cost}"
          />
          <div class="batch-confirm">
            <Button kind="primary" size="small" onclick={confirmBatchGenerate}>Generate</Button>
            <Button kind="ghost" size="small" onclick={() => { batchPreview = null; }}>Cancel</Button>
          </div>
        {:else}
          <Button
            kind="ghost"
            size="small"
            icon={ImageReference}
            iconDescription="Generate All Images"
            onclick={previewBatchGenerate}
          >Generate All Images</Button>
        {/if}
        {#if batchError}
          <InlineNotification
            kind="error"
            lowContrast
            hideCloseButton
            title="Error"
            subtitle={batchError}
            onclose={() => { batchError = null; }}
          />
        {/if}
      </div>
    {/if}

    <!-- Content Area -->
    <div class="codex-content">
      {#if selectedEntity}
        <!-- Detail View -->
        <div class="detail-view">
          <button class="back-btn" onclick={clearSelection} aria-label="Back to entity list">
            <ArrowLeft size={16} />
            <span>Back to list</span>
          </button>
          {#if loadingDetail}
            <InlineLoading description="Loading entity..." />
          {:else}
            <CodexEntityDetail
              entity={selectedEntity}
              onsimilar={handleSimilarNavigation}
            />
          {/if}
        </div>
      {:else if loadingList}
        <div class="entity-grid">
          <SkeletonCard count={12} />
        </div>
      {:else}
        <!-- Entity Grid -->
        <div class="entity-grid">
          {#each entities as entity (entity.strkey)}
            <button class="entity-card" onclick={() => selectEntity(entity)} aria-label="View {entity.name} ({entity.entity_type})">
              <div class="card-image">
                {#if entity.ai_image_url && !failedImages.has('ai_' + entity.strkey)}
                  <img
                    src="{API_BASE}{entity.ai_image_url}"
                    alt={entity.name}
                    class="card-thumb"
                    loading="lazy"
                    onerror={() => {
                      const next = new Set(failedImages);
                      next.add('ai_' + entity.strkey);
                      failedImages = next;
                    }}
                  />
                {:else if entity.image_texture && !failedImages.has(entity.strkey)}
                  <img
                    src="{API_BASE}/api/ldm/mapdata/thumbnail/{entity.image_texture}"
                    alt={entity.name}
                    class="card-thumb"
                    loading="lazy"
                    onerror={() => {
                      const next = new Set(failedImages);
                      next.add(entity.strkey);
                      failedImages = next;
                    }}
                  />
                {:else}
                  <PlaceholderImage entityType={entity.entity_type} entityName={entity.name} />
                {/if}
              </div>
              <div class="card-info">
                <span class="card-name">{entity.name}</span>
                <Tag type={TYPE_COLORS[entity.entity_type] || 'gray'} size="sm">
                  {entity.entity_type}
                </Tag>
                {#if entity.description}
                  <span class="card-desc">{truncate(entity.description)}</span>
                {/if}
              </div>
            </button>
          {/each}

          {#if entities.length === 0 && !loadingList}
            <div class="no-entities">
              <p>No entities found for this type -- ensure gamedata files are loaded and indexed.</p>
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
  .codex-page {
    display: flex;
    flex-direction: column;
    height: 100%;
    width: 100%;
    overflow: hidden;
  }

  .codex-state-container {
    display: flex;
    align-items: center;
    justify-content: center;
    flex: 1;
  }

  .codex-search {
    padding: 16px 16px 12px;
    background: var(--cds-layer-01);
    border-bottom: 1px solid var(--cds-border-subtle-01);
    flex-shrink: 0;
  }

  .codex-loading {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 32px;
  }

  .codex-tabs {
    display: flex;
    gap: 0;
    padding: 0 16px;
    background: var(--cds-layer-01);
    border-bottom: 2px solid var(--cds-border-subtle-01);
    flex-shrink: 0;
    overflow-x: auto;
  }

  .codex-tab {
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

  .codex-tab:hover {
    color: var(--cds-text-01);
    background: var(--cds-layer-hover-01);
  }

  .codex-tab:focus {
    outline: 2px solid var(--cds-focus);
    outline-offset: -2px;
  }

  .codex-tab.active {
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

  .codex-content {
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
    grid-template-columns: repeat(3, 1fr);
    gap: var(--card-gap, 12px);
  }

  @media (max-width: 1200px) {
    .entity-grid {
      grid-template-columns: repeat(2, 1fr);
    }
  }

  @media (max-width: 768px) {
    .entity-grid {
      grid-template-columns: 1fr;
    }
  }

  .entity-card {
    display: flex;
    gap: var(--card-gap, 10px);
    padding: var(--card-padding, 10px);
    background: var(--cds-layer-01);
    border: 1px solid var(--cds-border-subtle-01);
    border-radius: var(--card-radius, 6px);
    cursor: pointer;
    text-align: left;
    color: var(--cds-text-01);
    transition: background var(--transition-fast, 0.15s ease),
                border-color var(--transition-fast, 0.15s ease);
  }

  .entity-card:hover {
    background: var(--cds-layer-hover-01);
    border-color: var(--cds-border-strong-01);
  }

  .entity-card:focus {
    outline: 2px solid var(--cds-focus);
    outline-offset: 1px;
  }

  .card-image {
    width: 48px;
    height: 48px;
    flex-shrink: 0;
    border-radius: 4px;
    overflow: hidden;
    background: var(--cds-layer-02);
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .card-thumb {
    width: 100%;
    height: 100%;
    object-fit: contain;
  }

  .card-info {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 4px;
    min-width: 0;
  }

  .card-name {
    font-size: 0.8125rem;
    font-weight: 600;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .card-desc {
    font-size: 0.75rem;
    color: var(--cds-text-02);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .no-entities {
    grid-column: 1 / -1;
    text-align: center;
    padding: 32px;
    color: var(--cds-text-02);
    font-size: 0.875rem;
  }

  .batch-controls {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 16px;
    background: var(--cds-layer-01);
    border-bottom: 1px solid var(--cds-border-subtle-01);
    flex-shrink: 0;
    flex-wrap: wrap;
  }

  .batch-progress {
    display: flex;
    align-items: center;
    gap: 8px;
    flex: 1;
    min-width: 200px;
  }

  .batch-progress :global(.bx--progress-bar) {
    flex: 1;
  }

  .batch-confirm {
    display: flex;
    gap: 4px;
  }

  .skeleton-loading-grid {
    padding: 0;
    margin-top: 12px;
  }
</style>
