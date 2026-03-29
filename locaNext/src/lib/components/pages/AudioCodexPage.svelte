<script>
  /**
   * AudioCodexPage.svelte - Audio Codex encyclopedia page
   *
   * Browse, search, and play audio entries with category tree sidebar,
   * list layout (not card grid), inline audio playback, and detail panel.
   *
   * UNIQUE layout: Two-column with sidebar tree + list (text-heavy entries).
   *
   * Phase 48: Audio Codex UI (Plan 02)
   */
  import { InlineLoading } from "carbon-components-svelte";
  import { Music, ArrowLeft, Search, ChevronRight, ChevronDown, PlayFilledAlt, StopFilledAlt } from "carbon-icons-svelte";
  import { getAuthHeaders, getApiBase } from "$lib/utils/api.js";
  import { logger } from "$lib/utils/logger.js";
  import AudioCodexDetail from "$lib/components/ldm/AudioCodexDetail.svelte";
  import InfiniteScroll from "$lib/components/common/InfiniteScroll.svelte";
  import { PageHeader, ErrorState } from "$lib/components/common";
  import { onMount } from "svelte";

  const API_BASE = getApiBase();
  const PAGE_SIZE = 50;

  // State
  let categories = $state([]);
  let activeCategory = $state(null);
  let items = $state([]);
  let totalItems = $state(0);
  let selectedAudio = $state(null);
  let searchQuery = $state("");
  let loadingCategories = $state(true);
  let loadingList = $state(false);
  let loadingMore = $state(false);
  let apiError = $state(null);
  let currentPage = $state(0);
  let hasMore = $state(true);
  let totalEvents = $state(0);
  let expandedCategories = $state(new Set());
  let playingEvent = $state(null);

  // Debounce search
  let searchTimer = null;
  let abortController = null;

  // Debounced search via $effect
  $effect(() => {
    const q = searchQuery;
    if (searchTimer) clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      currentPage = 0;
      hasMore = true;
      fetchItems(0, activeCategory, q);
    }, 300);
    return () => {
      if (searchTimer) clearTimeout(searchTimer);
    };
  });

  /**
   * Fetch hierarchical category tree from D20 export_path grouping
   */
  async function fetchCategories() {
    loadingCategories = true;
    apiError = null;
    try {
      const response = await fetch(`${API_BASE}/api/ldm/codex/audio/categories`, {
        headers: getAuthHeaders()
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      categories = data.categories || [];
      totalEvents = data.total_events || 0;
      logger.info('Audio Codex categories loaded', { count: categories.length, totalEvents });
    } catch (err) {
      logger.error('Failed to fetch audio categories', { error: err.message });
      apiError = 'Audio Codex unavailable -- ensure gamedata folder is configured';
    } finally {
      loadingCategories = false;
    }
  }

  /**
   * Fetch paginated audio entries with optional category/search filtering
   */
  async function fetchItems(page, category, query) {
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
      if (category) params.set('category', category);
      if (query) params.set('q', query);

      const response = await fetch(
        `${API_BASE}/api/ldm/codex/audio?${params.toString()}`,
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

      logger.info('Audio Codex items loaded', { page, count: batch.length, total: data.total });
    } catch (err) {
      if (err.name === 'AbortError') return;
      logger.error('Failed to fetch audio items', { error: err.message });
      if (page === 0) apiError = 'Failed to load audio entries';
    } finally {
      loadingList = false;
      loadingMore = false;
    }
  }

  /**
   * Fetch full audio detail for a single event
   */
  async function fetchAudioDetail(eventName) {
    try {
      const response = await fetch(
        `${API_BASE}/api/ldm/codex/audio/${encodeURIComponent(eventName)}`,
        { headers: getAuthHeaders() }
      );
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      selectedAudio = await response.json();
      logger.info('Audio detail loaded', { eventName });
    } catch (err) {
      logger.error('Failed to fetch audio detail', { error: err.message, eventName });
    }
  }

  /**
   * Load more items (InfiniteScroll callback)
   */
  function loadMore() {
    if (hasMore && !loadingMore) {
      fetchItems(currentPage + 1, activeCategory, searchQuery);
    }
  }

  /**
   * Handle category tree node click -- filter list by that category
   */
  function selectCategory(fullPath) {
    activeCategory = fullPath;
    selectedAudio = null;
    currentPage = 0;
    hasMore = true;
    fetchItems(0, fullPath, searchQuery);
  }

  /**
   * Toggle expand/collapse of a category tree node
   */
  function toggleCategory(fullPath, event) {
    event.stopPropagation();
    const next = new Set(expandedCategories);
    if (next.has(fullPath)) {
      next.delete(fullPath);
    } else {
      next.add(fullPath);
    }
    expandedCategories = next;
  }

  /**
   * Handle list row click -- open detail panel
   */
  function selectRow(item) {
    fetchAudioDetail(item.event_name);
  }

  /**
   * Handle inline play button click
   */
  function togglePlay(eventName, event) {
    event.stopPropagation();
    if (playingEvent === eventName) {
      playingEvent = null;
    } else {
      playingEvent = eventName;
    }
  }

  /**
   * Back to list from detail view
   */
  function clearSelection() {
    selectedAudio = null;
  }

  /**
   * Get the last segment of an export path for badge display
   */
  function getCategoryBadge(exportPath) {
    if (!exportPath) return null;
    const parts = exportPath.split('/');
    return parts[parts.length - 1];
  }

  /**
   * Truncate text to a max length
   */
  function truncate(text, maxLen = 80) {
    if (!text) return '';
    return text.length > maxLen ? text.slice(0, maxLen) + '...' : text;
  }

  /**
   * Build audio stream URL with cache-bust
   */
  function getStreamUrl(eventName) {
    return `${API_BASE}/api/ldm/codex/audio/stream/${encodeURIComponent(eventName)}?v=${Date.now()}`;
  }

  onMount(() => {
    fetchCategories().then(() => {
      fetchItems(0, null, "");
    });
  });
</script>

<div class="audio-codex-page">
  <!-- Header -->
  <PageHeader icon={Music} title="Audio Codex" />

  {#if apiError}
    <div class="audio-codex-state-container">
      <ErrorState message={apiError} onretry={() => { fetchCategories(); fetchItems(0, null, ""); }} />
    </div>
  {:else if loadingCategories}
    <div class="audio-codex-loading" role="status" aria-live="polite">
      <InlineLoading description="Loading audio categories..." />
    </div>
  {:else}
    <div class="audio-codex-layout">
      <!-- Left: Category tree sidebar -->
      <aside class="category-sidebar" aria-label="Audio categories">
        <div class="sidebar-header">
          <span class="sidebar-title">Categories</span>
        </div>

        <!-- All category -->
        <button
          class="tree-node depth-0"
          class:active={activeCategory === null}
          onclick={() => selectCategory(null)}
          aria-label="All audio entries ({totalEvents})"
        >
          <span class="tree-node-name">All</span>
          <span class="tree-node-count">{totalEvents}</span>
        </button>

        <!-- Recursive category tree -->
        {#each categories as cat (cat.full_path)}
          {@const isExpanded = expandedCategories.has(cat.full_path)}
          <div class="tree-branch">
            <button
              class="tree-node depth-0"
              class:active={activeCategory === cat.full_path}
              onclick={() => selectCategory(cat.full_path)}
            >
              {#if cat.children && cat.children.length > 0}
                <span
                  class="tree-toggle"
                  role="button"
                  tabindex="0"
                  onclick={(e) => toggleCategory(cat.full_path, e)}
                  onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleCategory(cat.full_path, e); } }}
                  aria-label={isExpanded ? 'Collapse' : 'Expand'}
                >
                  {#if isExpanded}
                    <ChevronDown size={14} />
                  {:else}
                    <ChevronRight size={14} />
                  {/if}
                </span>
              {:else}
                <span class="tree-toggle-spacer"></span>
              {/if}
              <span class="tree-node-name">{cat.name}</span>
              <span class="tree-node-count">{cat.count}</span>
            </button>

            {#if isExpanded && cat.children}
              {#each cat.children as child (child.full_path)}
                {@const isChildExpanded = expandedCategories.has(child.full_path)}
                <div class="tree-branch">
                  <button
                    class="tree-node depth-1"
                    class:active={activeCategory === child.full_path}
                    onclick={() => selectCategory(child.full_path)}
                  >
                    {#if child.children && child.children.length > 0}
                      <span
                        class="tree-toggle"
                        role="button"
                        tabindex="0"
                        onclick={(e) => toggleCategory(child.full_path, e)}
                        onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleCategory(child.full_path, e); } }}
                        aria-label={isChildExpanded ? 'Collapse' : 'Expand'}
                      >
                        {#if isChildExpanded}
                          <ChevronDown size={14} />
                        {:else}
                          <ChevronRight size={14} />
                        {/if}
                      </span>
                    {:else}
                      <span class="tree-toggle-spacer"></span>
                    {/if}
                    <span class="tree-node-name">{child.name}</span>
                    <span class="tree-node-count">{child.count}</span>
                  </button>

                  {#if isChildExpanded && child.children}
                    {#each child.children as grandchild (grandchild.full_path)}
                      <button
                        class="tree-node depth-2"
                        class:active={activeCategory === grandchild.full_path}
                        onclick={() => selectCategory(grandchild.full_path)}
                      >
                        <span class="tree-toggle-spacer"></span>
                        <span class="tree-node-name">{grandchild.name}</span>
                        <span class="tree-node-count">{grandchild.count}</span>
                      </button>
                    {/each}
                  {/if}
                </div>
              {/each}
            {/if}
          </div>
        {/each}
      </aside>

      <!-- Right: Audio list + detail -->
      <div class="audio-content">
        {#if selectedAudio}
          <!-- Detail View -->
          <div class="detail-view">
            <button class="back-btn" onclick={clearSelection} aria-label="Back to audio list">
              <ArrowLeft size={16} />
              <span>Back to list</span>
            </button>
            <AudioCodexDetail audio={selectedAudio} onback={clearSelection} />
          </div>
        {:else}
          <!-- Search Bar -->
          <div class="audio-search">
            <div class="search-wrapper">
              <Search size={16} />
              <input
                type="search"
                placeholder="Search audio by event name, script text, or StringId..."
                bind:value={searchQuery}
                class="search-input"
                aria-label="Search audio entries"
              />
            </div>
            <span class="result-count">{totalItems} entries</span>
          </div>

          <!-- Audio List -->
          {#if loadingList}
            <div class="audio-loading">
              <InlineLoading description="Loading audio entries..." />
            </div>
          {:else}
            <div class="audio-list" role="list" aria-label="Audio entries">
              {#each items as item (item.event_name)}
                <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
                <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
                <div
                  class="audio-row"
                  role="listitem"
                  tabindex="0"
                  onclick={() => selectRow(item)}
                  onkeydown={(e) => { if (e.key === 'Enter') selectRow(item); }}
                >
                  <!-- Play/Stop button -->
                  <button
                    class="play-btn"
                    class:playing={playingEvent === item.event_name}
                    onclick={(e) => togglePlay(item.event_name, e)}
                    aria-label={playingEvent === item.event_name ? 'Stop audio' : 'Play audio'}
                    disabled={!item.has_wem}
                  >
                    {#if playingEvent === item.event_name}
                      <StopFilledAlt size={18} />
                    {:else}
                      <PlayFilledAlt size={18} />
                    {/if}
                  </button>

                  <!-- Event info -->
                  <div class="audio-info">
                    <div class="audio-info-top">
                      <span class="event-name">{item.event_name}</span>
                      <span class="wem-dot" class:has-wem={item.has_wem} title={item.has_wem ? 'Audio available' : 'No audio file'}></span>
                      {#if getCategoryBadge(item.export_path)}
                        <span class="category-badge">{getCategoryBadge(item.export_path)}</span>
                      {/if}
                    </div>
                    {#if item.script_kr}
                      <span class="script-preview kr">{truncate(item.script_kr)}</span>
                    {/if}
                    {#if item.script_eng}
                      <span class="script-preview eng">{truncate(item.script_eng)}</span>
                    {/if}
                  </div>

                  <!-- Inline audio player (shown when playing) -->
                  {#if playingEvent === item.event_name && item.has_wem}
                    <!-- svelte-ignore a11y_no_static_element_interactions -->
                    <div class="inline-player" onclick={(e) => e.stopPropagation()} onkeydown={() => {}}>
                      {#key item.event_name}
                        <audio
                          controls
                          autoplay
                          preload="none"
                          class="mini-audio"
                          crossorigin="anonymous"
                          src={getStreamUrl(item.event_name)}
                          onended={() => { playingEvent = null; }}
                          onerror={() => { playingEvent = null; }}
                        >
                          Your browser does not support the audio element.
                        </audio>
                      {/key}
                    </div>
                  {/if}
                </div>
              {/each}

              {#if items.length === 0 && !loadingList}
                <div class="no-entries">
                  <Music size={32} />
                  <p>No audio entries found{searchQuery ? ` matching "${searchQuery}"` : ''}{activeCategory ? ` in "${activeCategory}"` : ''}</p>
                </div>
              {/if}
            </div>

            <InfiniteScroll
              onloadmore={loadMore}
              loading={loadingMore}
              {hasMore}
            />

            {#if loadingMore}
              <div class="audio-loading-more">
                <InlineLoading description="Loading more..." />
              </div>
            {/if}
          {/if}
        {/if}
      </div>
    </div>
  {/if}
</div>

<style>
  .audio-codex-page {
    display: flex;
    flex-direction: column;
    height: 100%;
    width: 100%;
    overflow: hidden;
  }

  .audio-codex-state-container {
    display: flex;
    align-items: center;
    justify-content: center;
    flex: 1;
  }

  .audio-codex-loading {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 32px;
  }

  /* Two-column layout: sidebar + content */
  .audio-codex-layout {
    display: flex;
    flex: 1;
    min-height: 0;
    overflow: hidden;
  }

  /* Category sidebar */
  .category-sidebar {
    width: 250px;
    flex-shrink: 0;
    border-right: 1px solid var(--cds-border-subtle-01);
    background: var(--cds-layer-01);
    overflow-y: auto;
    display: flex;
    flex-direction: column;
  }

  .sidebar-header {
    padding: 12px 16px;
    border-bottom: 1px solid var(--cds-border-subtle-01);
  }

  .sidebar-title {
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--cds-text-03);
    text-transform: uppercase;
    letter-spacing: 0.5px;
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
    padding: 8px 12px;
    border: none;
    background: transparent;
    color: var(--cds-text-02);
    font-size: 0.8125rem;
    cursor: pointer;
    text-align: left;
    transition: all 0.12s;
    border-left: 3px solid transparent;
  }

  .tree-node.depth-0 { padding-left: 12px; }
  .tree-node.depth-1 { padding-left: 28px; }
  .tree-node.depth-2 { padding-left: 44px; }

  .tree-node:hover {
    background: var(--cds-layer-hover-01);
    color: var(--cds-text-01);
  }

  .tree-node:focus {
    outline: 2px solid var(--cds-focus);
    outline-offset: -2px;
  }

  .tree-node.active {
    background: var(--cds-layer-selected-01, rgba(15, 98, 254, 0.1));
    color: var(--cds-text-01);
    border-left-color: var(--cds-interactive-01, #0f62fe);
    font-weight: 500;
  }

  .tree-toggle {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0;
    border: none;
    background: transparent;
    color: var(--cds-text-03);
    cursor: pointer;
    flex-shrink: 0;
    width: 18px;
    height: 18px;
  }

  .tree-toggle:hover {
    color: var(--cds-text-01);
  }

  .tree-toggle-spacer {
    display: inline-block;
    width: 18px;
    flex-shrink: 0;
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

  /* Audio content area */
  .audio-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-width: 0;
    overflow-y: auto;
  }

  /* Search */
  .audio-search {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 16px;
    background: var(--cds-layer-01);
    border-bottom: 1px solid var(--cds-border-subtle-01);
    flex-shrink: 0;
  }

  .search-wrapper {
    display: flex;
    align-items: center;
    gap: 8px;
    flex: 1;
    padding: 8px 12px;
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
    font-size: 0.875rem;
    outline: none;
  }

  .search-input::placeholder {
    color: var(--cds-text-03);
  }

  .result-count {
    font-size: 0.75rem;
    color: var(--cds-text-03);
    white-space: nowrap;
  }

  .audio-loading {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 32px;
  }

  .audio-loading-more {
    padding: 12px;
    text-align: center;
  }

  /* Audio list rows */
  .audio-list {
    flex: 1;
    overflow-y: auto;
  }

  .audio-row {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    padding: 12px 16px;
    border-bottom: 1px solid var(--cds-border-subtle-01);
    cursor: pointer;
    transition: background 0.12s;
    flex-wrap: wrap;
  }

  .audio-row:hover {
    background: var(--cds-layer-hover-01);
  }

  /* Play button */
  .play-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    border-radius: 50%;
    border: none;
    background: var(--cds-interactive-01, #0f62fe);
    color: var(--cds-text-on-color, #fff);
    cursor: pointer;
    flex-shrink: 0;
    transition: all 0.15s;
    margin-top: 2px;
  }

  .play-btn:hover {
    background: var(--cds-hover-primary, #0353e9);
  }

  .play-btn:focus {
    outline: 2px solid var(--cds-focus);
    outline-offset: 2px;
  }

  .play-btn:disabled {
    background: var(--cds-disabled-02, #525252);
    color: var(--cds-disabled-03, #8d8d8d);
    cursor: not-allowed;
  }

  .play-btn.playing {
    background: var(--cds-support-error, #da1e28);
  }

  .play-btn.playing:hover {
    background: var(--cds-hover-danger, #b81921);
  }

  /* Audio info */
  .audio-info {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 4px;
    min-width: 0;
  }

  .audio-info-top {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }

  .event-name {
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--cds-text-01);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 400px;
  }

  .wem-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--cds-text-03);
    flex-shrink: 0;
  }

  .wem-dot.has-wem {
    background: var(--cds-support-success, #24a148);
  }

  .category-badge {
    font-size: 0.6875rem;
    padding: 1px 8px;
    border-radius: 8px;
    background: var(--cds-layer-02);
    color: var(--cds-text-02);
    white-space: nowrap;
  }

  .script-preview {
    font-size: 0.8125rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    line-height: 1.4;
  }

  .script-preview.kr {
    color: var(--cds-text-01);
  }

  .script-preview.eng {
    color: var(--cds-text-03);
    font-size: 0.75rem;
  }

  /* Inline audio player */
  .inline-player {
    width: 100%;
    padding-top: 8px;
  }

  .mini-audio {
    width: 100%;
    height: 32px;
    filter: invert(1) hue-rotate(180deg);
    opacity: 0.85;
  }

  /* Detail view */
  .detail-view {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 16px;
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

  /* Empty state */
  .no-entries {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
    padding: 48px 16px;
    color: var(--cds-text-03);
    text-align: center;
  }

  .no-entries p {
    font-size: 0.875rem;
    margin: 0;
    color: var(--cds-text-02);
  }
</style>
