<script>
  /**
   * GameDataContextPanel.svelte - Phase 30: Context Intelligence Panel
   *
   * Tabbed right panel for GameData tree view with 4 tabs:
   * Details (existing NodeDetailPanel), Cross-Refs (forward + backward),
   * Related (FAISS + TM suggestions), Media (image + audio).
   *
   * Replaces the plain NodeDetailPanel wrapper in GameDevPage.
   */
  import {
    ChevronLeft,
    ChevronRight,
    DataStructured,
    ConnectionSignal,
    Search,
    Image,
    Translate,
    MachineLearningModel
  } from 'carbon-icons-svelte';
  import { SkeletonText, InlineLoading } from 'carbon-components-svelte';
  import { logger } from '$lib/utils/logger.js';
  import { getAuthHeaders, getApiBase } from '$lib/utils/api.js';
  import NodeDetailPanel from '$lib/components/ldm/NodeDetailPanel.svelte';

  const API_BASE = getApiBase();

  // Props
  let {
    node = null,
    filePath = '',
    onChildClick = () => {},
    onNavigateToNode = () => {},
    collapsed = $bindable(false),
    width = $bindable(320)
  } = $props();

  // Tab definitions
  const tabs = [
    { id: 'details', label: 'Details', icon: DataStructured },
    { id: 'crossrefs', label: 'Cross-Refs', icon: ConnectionSignal },
    { id: 'related', label: 'Related', icon: Search },
    { id: 'media', label: 'Media', icon: Image }
  ];

  // State
  let activeTab = $state('details');
  let contextData = $state(null);
  let contextLoading = $state(false);
  let contextError = $state(null);
  let contextCache = $state(new Map());

  // Progressive loading states
  let crossRefsLoading = $state(false);
  let relatedLoading = $state(false);
  let mediaLoading = $state(false);

  // AI Summary state (on-demand)
  let aiSummary = $state('');
  let aiLoading = $state(false);
  let aiAvailable = $state(true);

  // Resize state
  let isResizing = $state(false);
  let resizeStartX = $state(0);
  let resizeStartWidth = $state(320);
  const MIN_WIDTH = 240;
  const MAX_WIDTH = 500;

  // AbortController for fetch cancellation
  let abortController = null;

  // Icon map for entity types (reuse from GameDataTree)
  const ENTITY_TYPE_COLORS = {
    SkillTreeInfo: '#a855f7',
    SkillInfo: '#a855f7',
    SkillNode: '#c084fc',
    ItemInfo: '#06b6d4',
    CharacterInfo: '#8b5cf6',
    GimmickGroupInfo: '#f59e0b',
    GimmickInfo: '#fbbf24',
    KnowledgeInfo: '#10b981',
    QuestInfo: '#f97316',
    RegionInfo: '#14b8a6',
    SceneObjectData: '#14b8a6',
    SealDataInfo: '#6366f1',
    FactionGroup: '#ec4899',
    NodeWaypointInfo: '#94a3b8',
  };

  function getEntityColor(tag) {
    return ENTITY_TYPE_COLORS[tag] || '#64748b';
  }

  // ========================================
  // Context Fetch
  // ========================================

  $effect(() => {
    if (node) {
      fetchContext(node);
    } else {
      contextData = null;
      contextLoading = false;
      contextError = null;
      crossRefsLoading = false;
      relatedLoading = false;
      mediaLoading = false;
      aiSummary = '';
    }
  });

  async function fetchContext(nodeData) {
    const cacheKey = nodeData.node_id;

    // Reset AI summary on node change
    aiSummary = '';
    aiLoading = false;

    // Check cache
    if (contextCache.has(cacheKey)) {
      contextData = contextCache.get(cacheKey);
      contextLoading = false;
      crossRefsLoading = false;
      relatedLoading = false;
      mediaLoading = false;
      contextError = null;
      return;
    }

    // Abort previous fetch
    if (abortController) {
      abortController.abort();
    }
    abortController = new AbortController();

    contextLoading = true;
    crossRefsLoading = true;
    relatedLoading = true;
    mediaLoading = true;
    contextError = null;

    try {
      const response = await fetch(`${API_BASE}/api/ldm/gamedata/context`, {
        method: 'POST',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({
          node_id: nodeData.node_id,
          tag: nodeData.tag,
          attributes: nodeData.attributes || {},
          editable_attrs: nodeData.editable_attrs || []
        }),
        signal: abortController.signal
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }));
        throw new Error(errData.detail || `Context fetch failed (HTTP ${response.status})`);
      }

      const data = await response.json();
      contextData = data;

      // Progressive reveal: cross-refs first (instant), related staggered, media last
      crossRefsLoading = false;
      setTimeout(() => { relatedLoading = false; }, 50);
      setTimeout(() => { mediaLoading = false; }, 100);

      // Update cache
      const newCache = new Map(contextCache);
      newCache.set(cacheKey, data);
      contextCache = newCache;

      logger.debug('Context loaded', {
        nodeId: cacheKey,
        forwardRefs: data.cross_refs?.forward?.length || 0,
        backwardRefs: data.cross_refs?.backward?.length || 0,
        related: data.related?.length || 0,
        tmSuggestions: data.tm_suggestions?.length || 0,
        hasStrkey: data.has_strkey,
      });
    } catch (err) {
      if (err.name === 'AbortError') return;
      contextError = err.message;
      crossRefsLoading = false;
      relatedLoading = false;
      mediaLoading = false;
      logger.error('Context fetch failed', { error: err.message });
    } finally {
      contextLoading = false;
    }
  }

  // ========================================
  // AI Summary (on-demand)
  // ========================================

  async function requestAISummary() {
    if (!node || aiLoading) return;
    aiLoading = true;
    try {
      const response = await fetch(`${API_BASE}/api/ldm/gamedata/context/ai-summary`, {
        method: 'POST',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({
          node_id: node.node_id,
          tag: node.tag,
          attributes: node.attributes || {},
          editable_attrs: node.editable_attrs || []
        })
      });
      if (response.ok) {
        const data = await response.json();
        aiSummary = data.summary;
        aiAvailable = data.available;
      }
    } catch (err) {
      logger.error('AI summary failed', { error: err.message });
    } finally {
      aiLoading = false;
    }
  }

  // ========================================
  // Resize
  // ========================================

  function startResize(e) {
    isResizing = true;
    resizeStartX = e.clientX;
    resizeStartWidth = width;
    document.addEventListener('mousemove', handleResize);
    document.addEventListener('mouseup', stopResize);
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  }

  function handleResize(e) {
    if (!isResizing) return;
    const delta = resizeStartX - e.clientX;
    width = Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, resizeStartWidth + delta));
  }

  function stopResize() {
    isResizing = false;
    document.removeEventListener('mousemove', handleResize);
    document.removeEventListener('mouseup', stopResize);
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
  }

  function toggleCollapse() {
    collapsed = !collapsed;
  }

  // ========================================
  // Cross-Ref Grouping
  // ========================================

  function groupByTag(items) {
    const groups = {};
    for (const item of items) {
      if (!groups[item.tag]) groups[item.tag] = [];
      groups[item.tag].push(item);
    }
    return Object.entries(groups);
  }

  // ========================================
  // Helpers
  // ========================================

  function getTierBadgeClass(matchType) {
    if (matchType === 'perfect_whole' || matchType === 'perfect_line') return 'tier-exact';
    if (matchType === 'whole_embedding' || matchType === 'line_embedding') return 'tier-semantic';
    if (matchType === 'ngram') return 'tier-ngram';
    return 'tier-semantic';
  }

  function formatScore(score) {
    return `${Math.round(score * 100)}%`;
  }

  function truncate(text, maxLen = 60) {
    if (!text || text.length <= maxLen) return text || '';
    return text.substring(0, maxLen) + '...';
  }
</script>

{#if node}
  <div class="context-panel" class:collapsed style="width: {collapsed ? '40px' : `${width}px`};">
    <!-- Resize handle -->
    {#if !collapsed}
      <div
        class="resize-handle"
        onmousedown={startResize}
        role="separator"
        aria-label="Resize panel"
      ></div>
    {/if}

    <!-- Collapse button -->
    <button class="collapse-btn" onclick={toggleCollapse} title={collapsed ? 'Expand panel' : 'Collapse panel'}>
      {#if collapsed}
        <ChevronLeft size={16} />
      {:else}
        <ChevronRight size={16} />
      {/if}
    </button>

    {#if !collapsed}
      <div class="panel-content">
        <!-- Tab bar -->
        <div class="tab-bar">
          {#each tabs as tab (tab.id)}
            <button
              class="tab-btn"
              class:active={activeTab === tab.id}
              onclick={() => { activeTab = tab.id; }}
              title={tab.label}
            >
              <svelte:component this={tab.icon} size={14} />
              <span class="tab-label">{tab.label}</span>
            </button>
          {/each}
        </div>

        <!-- Tab content -->
        {#key activeTab}
        <div class="tab-content">

          <!-- Details Tab -->
          {#if activeTab === 'details'}
            <NodeDetailPanel {node} {filePath} {onChildClick} />

          <!-- Cross-Refs Tab -->
          {:else if activeTab === 'crossrefs'}
            {#if crossRefsLoading}
              <div class="loading-section">
                <SkeletonText lines={4} />
              </div>
            {:else if contextError}
              <div class="error-section">
                <p class="error-text">{contextError}</p>
              </div>
            {:else if contextData?.cross_refs}
              <!-- Forward References -->
              <div class="crossref-section">
                <h4 class="section-header">
                  References ({contextData.cross_refs.forward?.length || 0})
                </h4>
                {#if contextData.cross_refs.forward?.length > 0}
                  {#each groupByTag(contextData.cross_refs.forward) as [tag, items] (tag)}
                    <div class="crossref-group">
                      <div class="group-header">
                        <span class="group-dot" style="background: {getEntityColor(tag)};"></span>
                        <span class="group-name">{tag} ({items.length})</span>
                      </div>
                      {#each items as item (item.node_id + item.via_attr)}
                        <button class="crossref-item" onclick={() => onNavigateToNode(item.node_id)}>
                          <span class="item-name">{item.name}</span>
                          <span class="item-via">via {item.via_attr}</span>
                        </button>
                      {/each}
                    </div>
                  {/each}
                {:else}
                  <p class="empty-text">No outgoing references</p>
                {/if}
              </div>

              <!-- Backward References -->
              <div class="crossref-section">
                <h4 class="section-header">
                  Referenced By ({contextData.cross_refs.backward?.length || 0})
                </h4>
                {#if contextData.cross_refs.backward?.length > 0}
                  {#each groupByTag(contextData.cross_refs.backward) as [tag, items] (tag)}
                    <div class="crossref-group">
                      <div class="group-header">
                        <span class="group-dot" style="background: {getEntityColor(tag)};"></span>
                        <span class="group-name">{tag} ({items.length})</span>
                      </div>
                      {#each items as item (item.node_id + item.via_attr)}
                        <button class="crossref-item" onclick={() => onNavigateToNode(item.node_id)}>
                          <span class="item-name">{item.name}</span>
                          <span class="item-via">via {item.via_attr}</span>
                        </button>
                      {/each}
                    </div>
                  {/each}
                {:else}
                  <p class="empty-text">No incoming references</p>
                {/if}
              </div>
            {:else}
              <div class="empty-section">
                <ConnectionSignal size={32} />
                <p class="empty-text">No cross-references found</p>
              </div>
            {/if}

          <!-- Related Tab -->
          {:else if activeTab === 'related'}
            {#if relatedLoading}
              <div class="loading-section">
                <SkeletonText lines={4} />
              </div>
            {:else if contextError}
              <div class="error-section">
                <p class="error-text">{contextError}</p>
              </div>
            {:else}
              <!-- Similar Entities (FAISS) -->
              <div class="related-section">
                <h4 class="section-header">Similar Entities</h4>
                {#if contextData?.related?.length > 0}
                  {#each contextData.related as item (item.node_id + item.entity_name)}
                    <button class="related-item" onclick={() => onNavigateToNode(item.node_id)}>
                      <span class="related-dot" style="background: {getEntityColor(item.tag)};"></span>
                      <div class="related-info">
                        <span class="related-name">{item.entity_name}</span>
                        {#if item.entity_desc}
                          <span class="related-desc">{truncate(item.entity_desc, 40)}</span>
                        {/if}
                      </div>
                      <span class="tier-badge {getTierBadgeClass(item.match_type)}">
                        {#if item.match_type === 'perfect_whole' || item.match_type === 'perfect_line'}
                          exact
                        {:else if item.match_type?.includes('embedding')}
                          semantic {formatScore(item.score)}
                        {:else if item.match_type === 'ngram'}
                          n-gram {formatScore(item.score)}
                        {:else}
                          {formatScore(item.score)}
                        {/if}
                      </span>
                    </button>
                  {/each}
                {:else}
                  <p class="empty-text">No related entities found</p>
                {/if}
              </div>

              <!-- Language Data Matches (TM suggestions) -->
              {#if contextData?.has_strkey}
                <div class="related-section tm-section">
                  <h4 class="section-header tm-header">
                    <Translate size={14} />
                    Language Data Matches ({contextData.tm_suggestions?.length || 0})
                  </h4>
                  {#if contextData.tm_suggestions?.length > 0}
                    {#each contextData.tm_suggestions as suggestion, i (i)}
                      <div class="tm-item">
                        <div class="tm-source">{truncate(suggestion.source, 60)}</div>
                        {#if suggestion.target}
                          <div class="tm-target">{truncate(suggestion.target, 60)}</div>
                        {/if}
                        <span class="tier-badge tier-semantic">
                          {formatScore(suggestion.similarity)}
                        </span>
                      </div>
                    {/each}
                  {:else}
                    <p class="empty-text">No similar strings found in loaded language data</p>
                  {/if}
                </div>
              {/if}

              <!-- AI Context Summary (on-demand) -->
              <div class="ai-summary-section">
                <button class="ai-summary-btn" onclick={requestAISummary} disabled={aiLoading || !aiAvailable}>
                  {#if aiLoading}
                    <InlineLoading description="Generating..." />
                  {:else}
                    <MachineLearningModel size={14} />
                    Generate AI Context
                  {/if}
                </button>
                {#if !aiAvailable}
                  <span class="ai-unavailable">Ollama not running</span>
                {/if}
                {#if aiSummary}
                  <div class="ai-summary-text">{aiSummary}</div>
                {/if}
              </div>
            {/if}

          <!-- Media Tab -->
          {:else if activeTab === 'media'}
            {#if mediaLoading}
              <div class="loading-section">
                <SkeletonText lines={2} />
              </div>
            {:else if contextData?.media}
              {#if contextData.media.has_image}
                <div class="media-section">
                  <h4 class="section-header">Image</h4>
                  <img
                    class="media-image"
                    src="{API_BASE}{contextData.media.thumbnail_url}"
                    alt={node?.attributes?.[node?.editable_attrs?.[0]] || node?.tag || 'Entity image'}
                    loading="lazy"
                  />
                  <span class="media-label">{contextData.media.texture_name}</span>
                </div>
              {/if}

              {#if contextData.media.has_audio}
                <div class="media-section">
                  <h4 class="section-header">Audio</h4>
                  <audio controls class="media-audio">
                    <source src="{API_BASE}{contextData.media.stream_url}" />
                    Your browser does not support audio playback.
                  </audio>
                  <span class="media-label">{contextData.media.voice_id}</span>
                </div>
              {/if}

              {#if !contextData.media.has_image && !contextData.media.has_audio}
                <div class="empty-section">
                  <Image size={32} />
                  <p class="empty-text">No media associated with this entity</p>
                </div>
              {/if}
            {:else}
              <div class="empty-section">
                <Image size={32} />
                <p class="empty-text">No media associated with this entity</p>
              </div>
            {/if}
          {/if}

        </div>
        {/key}
      </div>
    {/if}
  </div>
{/if}

<style>
  .context-panel {
    display: flex;
    flex-direction: column;
    background: var(--cds-layer-01);
    border-left: 1px solid var(--cds-border-subtle-01);
    position: relative;
    transition: width 0.15s ease;
    overflow: hidden;
  }

  .context-panel.collapsed {
    min-width: 40px;
    max-width: 40px;
  }

  /* Resize handle */
  .resize-handle {
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    width: 4px;
    cursor: col-resize;
    background: transparent;
    z-index: 10;
  }

  .resize-handle:hover {
    background: var(--cds-interactive-01);
    transition: background 0.15s ease;
  }

  /* Collapse button */
  .collapse-btn {
    position: absolute;
    top: 8px;
    left: 8px;
    width: 24px;
    height: 24px;
    border: none;
    background: var(--cds-layer-02);
    border-radius: 4px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--cds-text-01);
    z-index: 5;
  }

  .collapse-btn:hover {
    background: var(--cds-layer-hover-01);
  }

  /* Panel content */
  .panel-content {
    display: flex;
    flex-direction: column;
    padding-top: 40px;
    overflow: hidden;
    flex: 1;
  }

  /* Tab bar */
  .tab-bar {
    display: flex;
    border-bottom: 1px solid var(--cds-border-subtle-01);
    padding: 0 12px;
    flex-shrink: 0;
  }

  .tab-btn {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 8px 10px;
    border: none;
    background: transparent;
    color: var(--cds-text-02);
    font-size: 0.6875rem;
    font-weight: 500;
    cursor: pointer;
    border-bottom: 2px solid transparent;
    transition: color 0.15s ease, border-color 0.15s ease;
    white-space: nowrap;
  }

  .tab-btn:hover {
    color: var(--cds-text-01);
    background: var(--cds-layer-hover-01);
  }

  .tab-btn.active {
    color: var(--cds-interactive-01);
    border-bottom-color: var(--cds-interactive-01);
  }

  .tab-label {
    display: inline;
  }

  /* Tab content area */
  .tab-content {
    flex: 1;
    overflow-y: auto;
    min-height: 0;
    animation: tabFadeIn 0.15s ease;
  }

  @keyframes tabFadeIn {
    from { opacity: 0; transform: translateY(4px); }
    to { opacity: 1; transform: translateY(0); }
  }

  /* Section styles */
  .section-header {
    margin: 0 0 0.5rem;
    font-size: 0.6875rem;
    font-weight: 600;
    color: var(--cds-text-02);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    display: flex;
    align-items: center;
    gap: 0.375rem;
  }

  .loading-section {
    padding: 1rem;
  }

  .error-section {
    padding: 1rem;
  }

  .error-text {
    margin: 0;
    font-size: 0.8125rem;
    color: var(--cds-support-error);
  }

  .empty-section {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 2rem 1rem;
    color: var(--cds-text-03);
    gap: 0.5rem;
  }

  .empty-text {
    margin: 0;
    font-size: 0.8125rem;
    color: var(--cds-text-03);
  }

  /* Cross-Refs */
  .crossref-section {
    padding: 0.75rem;
    border-bottom: 1px solid var(--cds-border-subtle-01);
  }

  .crossref-group {
    margin-bottom: 0.5rem;
  }

  .group-header {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    margin-bottom: 0.25rem;
    font-size: 0.75rem;
    font-weight: 500;
    color: var(--cds-text-02);
  }

  .group-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .group-name {
    font-size: 0.6875rem;
  }

  .crossref-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    width: 100%;
    padding: 0.375rem 0.5rem;
    margin-left: 0.5rem;
    background: transparent;
    border: 1px solid var(--cds-border-subtle-01);
    border-radius: 4px;
    cursor: pointer;
    text-align: left;
    font-family: inherit;
    font-size: 0.75rem;
    color: var(--cds-text-01);
    transition: background 0.1s, border-color 0.1s;
    margin-bottom: 0.25rem;
  }

  .crossref-item:hover {
    background: var(--cds-layer-hover-01);
    border-color: var(--cds-border-strong-01);
  }

  .crossref-item:focus {
    outline: 2px solid var(--cds-focus);
    outline-offset: 1px;
  }

  .item-name {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    flex: 1;
  }

  .item-via {
    font-size: 0.625rem;
    color: var(--cds-text-03);
    flex-shrink: 0;
    margin-left: 0.5rem;
  }

  /* Related entities */
  .related-section {
    padding: 0.75rem;
    border-bottom: 1px solid var(--cds-border-subtle-01);
  }

  .tm-section {
    border-bottom: none;
  }

  .tm-header {
    color: var(--cds-link-01);
  }

  .related-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    width: 100%;
    padding: 0.5rem;
    background: transparent;
    border: 1px solid var(--cds-border-subtle-01);
    border-radius: 4px;
    cursor: pointer;
    text-align: left;
    font-family: inherit;
    font-size: 0.75rem;
    color: var(--cds-text-01);
    transition: background 0.1s;
    margin-bottom: 0.25rem;
  }

  .related-item:hover {
    background: var(--cds-layer-hover-01);
  }

  .related-item:focus {
    outline: 2px solid var(--cds-focus);
    outline-offset: 1px;
  }

  .related-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .related-info {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 0.125rem;
    min-width: 0;
  }

  .related-name {
    font-weight: 500;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .related-desc {
    font-size: 0.6875rem;
    color: var(--cds-text-03);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  /* Tier badge */
  .tier-badge {
    font-size: 0.625rem;
    font-weight: 600;
    padding: 1px 6px;
    border-radius: 8px;
    flex-shrink: 0;
    line-height: 1.3;
  }

  .tier-exact {
    background: rgba(36, 161, 72, 0.15);
    color: #24a148;
  }

  .tier-semantic {
    background: rgba(0, 114, 195, 0.15);
    color: #0072c3;
  }

  .tier-ngram {
    background: rgba(245, 158, 11, 0.15);
    color: #d97706;
  }

  /* TM suggestion items */
  .tm-item {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    padding: 0.5rem;
    border: 1px solid var(--cds-border-subtle-01);
    border-radius: 4px;
    margin-bottom: 0.25rem;
    position: relative;
  }

  .tm-source {
    font-size: 0.75rem;
    color: var(--cds-text-01);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .tm-target {
    font-size: 0.6875rem;
    color: var(--cds-text-02);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .tm-item .tier-badge {
    position: absolute;
    top: 0.375rem;
    right: 0.375rem;
  }

  /* Media */
  .media-section {
    padding: 0.75rem;
    border-bottom: 1px solid var(--cds-border-subtle-01);
  }

  .media-image {
    max-width: 100%;
    border-radius: 6px;
    border: 1px solid var(--cds-border-subtle-01);
    margin-bottom: 0.5rem;
  }

  .media-audio {
    width: 100%;
    margin-bottom: 0.5rem;
  }

  .media-label {
    display: block;
    font-size: 0.6875rem;
    color: var(--cds-text-03);
    font-family: 'IBM Plex Mono', monospace;
  }

  /* AI Summary */
  .ai-summary-section {
    margin-top: 1rem;
    padding: 0.75rem;
    padding-top: 0.75rem;
    border-top: 1px solid var(--cds-border-subtle-01);
  }

  .ai-summary-btn {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    padding: 0.5rem 0.75rem;
    background: var(--cds-field-01);
    border: 1px solid var(--cds-border-strong-01);
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.75rem;
    font-family: inherit;
    color: var(--cds-text-01);
  }

  .ai-summary-btn:hover {
    background: var(--cds-layer-hover-01);
  }

  .ai-summary-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .ai-summary-text {
    margin-top: 0.5rem;
    padding: 0.75rem;
    background: var(--cds-field-01);
    border-radius: 4px;
    font-size: 0.8125rem;
    color: var(--cds-text-01);
    line-height: 1.5;
  }

  .ai-unavailable {
    font-size: 0.6875rem;
    color: var(--cds-text-03);
    margin-left: 0.5rem;
  }
</style>
