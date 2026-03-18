<script>
  /**
   * GameDataContextPanel.svelte - v3.4: Tab-First Layout
   *
   * 4 tabs: Dictionary | Context | Media | Info
   * Tabs at TOP, content fills remaining space.
   * One Dark Pro theme matching the XML viewer.
   */
  import { ChevronRight, ChevronLeft, Pin } from 'carbon-icons-svelte';
  import { logger } from '$lib/utils/logger.js';
  import { getAuthHeaders, getApiBase } from '$lib/utils/api.js';

  const API_BASE = getApiBase();

  // Props (same interface as before)
  let {
    node = null,
    filePath = '',
    onChildClick = () => {},
    onNavigateToNode = () => {},
    collapsed = $bindable(false),
    width = $bindable(320)
  } = $props();

  // ========================================
  // Tab State
  // ========================================

  let activeTab = $state('dictionary');
  let loadedTabs = $state(new Set());
  let pinned = $state(false);

  // === Image shimmer state (WOW-03) ===
  let imageLoadStates = $state(new Map()); // key -> 'loading' | 'loaded' | 'error'

  function switchTab(tab) {
    activeTab = tab;
    const next = new Set(loadedTabs);
    next.add(tab);
    loadedTabs = next;
    // Force fetch on explicit tab switch (fixes lazy-load race with auto-switch effects)
    if (tab === 'dictionary' && node && dictNodeId !== node.node_id) fetchDictionary();
    if (tab === 'context' && node && aiNodeId !== node.node_id) fetchAISummary();
    if (tab === 'media' && node && mediaNodeId !== node.node_id) fetchMedia();
  }

  // ========================================
  // Constants
  // ========================================

  const ENTITY_TYPE_COLORS = {
    SkillTreeInfo: '#a855f7', SkillInfo: '#a855f7', SkillNode: '#c084fc',
    ItemInfo: '#06b6d4', CharacterInfo: '#8b5cf6',
    GimmickGroupInfo: '#f59e0b', GimmickInfo: '#fbbf24',
    KnowledgeInfo: '#10b981', QuestInfo: '#f97316',
    RegionInfo: '#14b8a6', SceneObjectData: '#14b8a6',
    SealDataInfo: '#6366f1', FactionGroup: '#ec4899',
    NodeWaypointInfo: '#94a3b8'
  };

  const CROSS_REF_ATTRS = new Set([
    'LearnKnowledgeKey', 'RequireSkillKey', 'LinkedQuestKey', 'RegionKey',
    'ParentNodeId', 'ParentId', 'TargetKey', 'ItemKey', 'CharacterKey',
    'GimmickKey', 'SealKey', 'FactionKey', 'SkillKey', 'KnowledgeKey', 'RewardKey'
  ]);
  const IDENTITY_ATTRS = new Set(['Key', 'NodeId', 'Id', 'StrKey']);

  const INFO_IDENTITY_KEYS = new Set(['Key', 'StrKey', 'CharacterType', 'ItemType', 'NodeId', 'Id']);
  const INFO_STATS_KEYS = new Set(['Level', 'Job', 'Race', 'Gender', 'Age', 'Title', 'Grade', 'RequireLevel', 'AttackPower', 'Defense', 'HP', 'MP', 'Speed', 'CritRate']);

  function isCrossRef(attrName) {
    if (CROSS_REF_ATTRS.has(attrName)) return true;
    if ((attrName.endsWith('Key') || attrName.endsWith('Id')) && !IDENTITY_ATTRS.has(attrName)) return true;
    return false;
  }

  function getEntityColor(tag) { return ENTITY_TYPE_COLORS[tag] || '#64748b'; }

  // Entity label: use first editable attr, or Key, or node_id
  let entityLabel = $derived.by(() => {
    if (!node) return '';
    const primary = (node.editable_attrs || [])[0];
    return node.attributes?.[primary] || node.attributes?.Key || node.node_id || '';
  });

  // Info tab: group attributes
  let infoIdentity = $derived.by(() => {
    if (!node?.attributes) return [];
    return Object.entries(node.attributes).filter(([k]) => INFO_IDENTITY_KEYS.has(k));
  });

  let infoStats = $derived.by(() => {
    if (!node?.attributes) return [];
    return Object.entries(node.attributes).filter(([k]) => INFO_STATS_KEYS.has(k));
  });

  let infoRefs = $derived.by(() => {
    if (!node?.attributes) return [];
    return Object.entries(node.attributes).filter(([k]) => k.endsWith('Key') && !IDENTITY_ATTRS.has(k) && !INFO_IDENTITY_KEYS.has(k));
  });

  let infoOther = $derived.by(() => {
    if (!node?.attributes) return [];
    const used = new Set([...INFO_IDENTITY_KEYS, ...INFO_STATS_KEYS]);
    return Object.entries(node.attributes).filter(([k]) => {
      if (used.has(k)) return false;
      if (k.endsWith('Key') && !IDENTITY_ATTRS.has(k)) return false;
      // Skip editable attrs (they're text content, not info)
      if ((node.editable_attrs || []).includes(k)) return false;
      return true;
    });
  });

  // ========================================
  // Dictionary State (lazy-load)
  // ========================================

  let dictResults = $state(null);
  let dictLoading = $state(false);
  let dictError = $state(null);
  let dictNodeId = $state(null);

  // ========================================
  // Context / AI Summary State (lazy-load)
  // ========================================

  let aiSummary = $state('');
  let aiLoading = $state(false);
  let aiError = $state(null);
  let aiAvailable = $state(true);
  let aiSourceFile = $state('');
  let aiNodeId = $state(null);

  // ========================================
  // Media State (lazy-load)
  // ========================================

  let mediaData = $state(null);
  let mediaLoading = $state(false);
  let mediaError = $state(null);
  let mediaNodeId = $state(null);
  let imageOverlay = $state(null);
  let audioPlaying = $state(false);
  let audioEl = $state(null);

  // ========================================
  // AbortControllers
  // ========================================

  let dictAbort = null;
  let aiAbort = null;
  let mediaAbort = null;

  // ========================================
  // Resize State
  // ========================================

  let isResizing = $state(false);
  let resizeStartX = $state(0);
  let resizeStartWidth = $state(320);
  const MIN_WIDTH = 240;
  const MAX_WIDTH = 500;

  // ========================================
  // Reset on node change
  // ========================================

  $effect(() => {
    if (node) {
      // Reset lazy-loaded sections on node change
      dictResults = null;
      dictError = null;
      dictNodeId = null;
      aiSummary = '';
      aiError = null;
      aiNodeId = null;
      mediaData = null;
      mediaError = null;
      mediaNodeId = null;
      imageLoadStates = new Map();

      // Reset loaded tabs on node change
      loadedTabs = new Set();
    }
  });

  // ========================================
  // Lazy-load triggers: fetch when tab is active
  // ========================================

  $effect(() => {
    if (activeTab === 'dictionary' && node && dictNodeId !== node.node_id) {
      fetchDictionary();
    }
  });

  $effect(() => {
    if (activeTab === 'context' && node && aiNodeId !== node.node_id) {
      fetchAISummary();
    }
  });

  $effect(() => {
    if (activeTab === 'media' && node && mediaNodeId !== node.node_id) {
      fetchMedia();
    }
  });

  // Media attribute names that indicate this node has linked media
  const MEDIA_IMAGE_ATTRS = ['UITextureName', 'TextureKey', 'IconKey', 'TexturePath', 'IconPath', 'PortraitPath'];
  const MEDIA_AUDIO_ATTRS = ['VoicePath', 'VoiceId', 'VoiceKey', 'AudioPath'];

  function nodeHasMediaHint(n) {
    if (!n?.attributes) return false;
    for (const attr of MEDIA_IMAGE_ATTRS) {
      if (n.attributes[attr]) return true;
    }
    for (const attr of MEDIA_AUDIO_ATTRS) {
      if (n.attributes[attr]) return true;
    }
    return false;
  }

  function getNodeImageAttr(n) {
    if (!n?.attributes) return null;
    for (const attr of MEDIA_IMAGE_ATTRS) {
      if (n.attributes[attr]) return { name: attr, value: n.attributes[attr] };
    }
    return null;
  }

  function getNodeAudioAttr(n) {
    if (!n?.attributes) return null;
    for (const attr of MEDIA_AUDIO_ATTRS) {
      if (n.attributes[attr]) return { name: attr, value: n.attributes[attr] };
    }
    return null;
  }

  // Auto-switch to media tab if node has image/audio hint
  $effect(() => {
    if (node && nodeHasMediaHint(node)) {
      activeTab = 'media';
      // Don't read loadedTabs here to avoid infinite loop
      loadedTabs = new Set(['media']);
    }
  });

  // ========================================
  // API: Dictionary Lookup
  // ========================================

  async function fetchDictionary() {
    if (!node) return;
    dictAbort?.abort();
    dictAbort = new AbortController();
    dictLoading = true;
    dictError = null;
    dictNodeId = node.node_id;

    const text = (node.editable_attrs || [])
      .map(a => node.attributes?.[a] || '')
      .filter(Boolean)
      .join(' ');

    if (!text.trim()) {
      dictResults = [];
      dictLoading = false;
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/api/ldm/gamedata/dictionary-lookup`, {
        method: 'POST',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: text.trim(), threshold: 0.3, top_k: 15 }),
        signal: dictAbort.signal
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      dictResults = data.results || data.matches || [];
    } catch (err) {
      if (err.name === 'AbortError') return;
      dictError = err.message;
      logger.error('Dictionary lookup failed', { error: err.message });
    } finally {
      dictLoading = false;
    }
  }

  // ========================================
  // API: AI Summary
  // ========================================

  async function fetchAISummary() {
    if (!node) return;
    aiAbort?.abort();
    aiAbort = new AbortController();
    aiLoading = true;
    aiError = null;
    aiNodeId = node.node_id;

    try {
      const response = await fetch(`${API_BASE}/api/ldm/gamedata/context/ai-summary`, {
        method: 'POST',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({
          node_id: node.node_id,
          tag: node.tag,
          attributes: node.attributes || {},
          editable_attrs: node.editable_attrs || []
        }),
        signal: aiAbort.signal
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      aiSummary = data.summary || '';
      aiAvailable = data.available !== false;
      aiSourceFile = data.source_file || filePath?.split('/').pop() || '';
    } catch (err) {
      if (err.name === 'AbortError') return;
      aiError = err.message;
      aiAvailable = false;
      logger.error('AI summary failed', { error: err.message });
    } finally {
      aiLoading = false;
    }
  }

  function regenerateAI() {
    aiNodeId = null; // force re-fetch
    fetchAISummary();
  }

  // ========================================
  // API: Media
  // ========================================

  async function fetchMedia() {
    if (!node) return;
    mediaAbort?.abort();
    mediaAbort = new AbortController();
    mediaLoading = true;
    mediaError = null;
    mediaNodeId = node.node_id;

    try {
      const response = await fetch(`${API_BASE}/api/ldm/gamedata/context`, {
        method: 'POST',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({
          node_id: node.node_id,
          tag: node.tag,
          attributes: node.attributes || {},
          editable_attrs: node.editable_attrs || []
        }),
        signal: mediaAbort.signal
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      mediaData = data.media || null;
    } catch (err) {
      if (err.name === 'AbortError') return;
      mediaError = err.message;
      logger.error('Media fetch failed', { error: err.message });
    } finally {
      mediaLoading = false;
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

  function toggleCollapse() { collapsed = !collapsed; }

  // ========================================
  // Helpers
  // ========================================

  function truncate(text, maxLen = 60) {
    if (!text || text.length <= maxLen) return text || '';
    return text.substring(0, maxLen) + '...';
  }

  function getDictTierClass(tier) {
    if (tier <= 1) return 'tier-exact';
    if (tier <= 4) return 'tier-similar';
    return 'tier-fuzzy';
  }

  function formatScore(score) {
    return `${Math.round((score ?? 0) * 100)}%`;
  }

  function playAudio(url) {
    if (audioEl) { audioEl.pause(); audioEl = null; audioPlaying = false; }
    audioEl = new Audio(url);
    audioEl.onended = () => { audioPlaying = false; };
    audioEl.onerror = () => { audioPlaying = false; logger.warning('Audio playback failed', { url }); };
    audioEl.play().catch(() => { audioPlaying = false; });
    audioPlaying = true;
  }

  function stopAudio() {
    if (audioEl) { audioEl.pause(); audioEl = null; }
    audioPlaying = false;
  }

  // Tab item counts
  let dictCount = $derived(dictResults?.length ?? 0);
  let mediaCount = $derived.by(() => {
    if (mediaData?.has_image || mediaData?.has_audio) {
      return (mediaData.has_image ? 1 : 0) + (mediaData.has_audio ? 1 : 0);
    }
    // Fallback: count client-side detected media attributes
    let count = 0;
    if (getNodeImageAttr(node)) count++;
    if (getNodeAudioAttr(node)) count++;
    return count;
  });

  let infoCount = $derived((infoIdentity?.length ?? 0) + (infoStats?.length ?? 0) + (infoRefs?.length ?? 0) + (infoOther?.length ?? 0));
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
        <!-- Panel Header -->
        <div class="panel-header">
          <div class="header-accent" style="background: {getEntityColor(node.tag)};"></div>
          <div class="header-info">
            <span class="header-tag">{node.tag}</span>
            <span class="header-label">{truncate(entityLabel, 30)}</span>
          </div>
          <button
            class="pin-btn"
            class:active={pinned}
            onclick={() => { pinned = !pinned; }}
            title={pinned ? 'Unpin panel' : 'Pin panel'}
          >
            <Pin size={14} />
          </button>
        </div>

        <!-- TAB BAR (at TOP, right after header) -->
        <div class="tab-bar">
          <button
            class="tab-btn"
            class:active={activeTab === 'dictionary'}
            onclick={() => switchTab('dictionary')}
          >
            Dict{#if dictCount > 0} <span class="tab-count">{dictCount}</span>{/if}
          </button>
          <button
            class="tab-btn"
            class:active={activeTab === 'context'}
            onclick={() => switchTab('context')}
          >
            Context{#if aiSummary} <span class="tab-count">1</span>{/if}
          </button>
          <button
            class="tab-btn"
            class:active={activeTab === 'media'}
            onclick={() => switchTab('media')}
          >
            Media{#if mediaCount > 0} <span class="tab-count">{mediaCount}</span>{/if}
          </button>
          <button
            class="tab-btn"
            class:active={activeTab === 'info'}
            onclick={() => switchTab('info')}
          >
            Info{#if infoCount > 0} <span class="tab-count">{infoCount}</span>{/if}
          </button>
        </div>

        <!-- TAB CONTENT (fills ALL remaining space) -->
        <div class="tab-content">
          <div class="tab-content-animated">

          <!-- Dictionary Tab -->
          {#if activeTab === 'dictionary'}
            <div class="tab-body">
              {#if dictLoading}
                {@render shimmerRows(3)}
              {:else if dictError}
                <p class="section-error">{dictError}</p>
              {:else if dictResults && dictResults.length === 0}
                <p class="section-empty">No matching terms found</p>
              {:else if dictResults}
                {#each dictResults as match, i (i)}
                  <div class="dict-row dict-result-item {getDictTierClass(match.tier ?? 5)}">
                    <div class="dict-header">
                      <span class="dict-source">{match.source || match.kr || ''}</span>
                      <span class="dict-badge {getDictTierClass(match.tier ?? 5)}">{formatScore(match.score ?? match.similarity ?? 0)}</span>
                    </div>
                    <span class="dict-target">{(match.target || match.en || '').replace(/<br\/>/g, '\n')}</span>
                  </div>
                {/each}
              {/if}
            </div>
          {/if}

          <!-- Context Tab -->
          {#if activeTab === 'context'}
            <div class="tab-body">
              <!-- AI Summary -->
              <div class="context-section">
                <div class="context-section-label">AI 컨텍스트</div>
                {#if aiLoading}
                  {@render shimmerRows(3)}
                {:else if aiError}
                  <div class="ai-error">
                    <span class="ai-error-icon">!</span>
                    <span>AI 사용 불가 — Ollama를 시작하세요</span>
                  </div>
                {:else if aiSummary}
                  <div class="ai-summary">{aiSummary}</div>
                  {#if aiSourceFile}
                    <span class="ai-source">Based on: <button class="source-link" onclick={() => {}}>{aiSourceFile}</button></span>
                  {/if}
                  <button class="regen-btn" onclick={regenerateAI}>다시 생성</button>
                {:else if !aiLoading && aiNodeId}
                  <p class="section-empty">요약을 생성하려면 클릭하세요</p>
                  <button class="regen-btn" onclick={regenerateAI}>생성</button>
                {:else}
                  <p class="section-empty">요약을 생성하려면 클릭하세요</p>
                  <button class="regen-btn" onclick={regenerateAI}>생성</button>
                {/if}
              </div>

              <!-- Attribute Summary -->
              <div class="context-section">
                <div class="context-section-label">속성 요약</div>
                <div class="attr-summary">
                  {#each Object.entries(node?.attributes || {}).filter(([k, v]) => v && !['Key', 'StrKey', 'UITextureName', 'VoicePath'].includes(k)).slice(0, 8) as [key, value] (key)}
                    <div class="attr-summary-row">
                      <span class="attr-summary-key">{key}</span>
                      <span class="attr-summary-value">{truncate(String(value), 40)}</span>
                    </div>
                  {/each}
                </div>
              </div>
            </div>
          {/if}

          <!-- Media Tab -->
          {#if activeTab === 'media'}
            <div class="tab-body media-tab-body">
              {#if mediaLoading}
                {@render shimmerRows(2)}
              {:else if mediaError}
                <p class="section-error">{mediaError}</p>
              {:else if mediaData && (mediaData.has_image || mediaData.has_audio)}
                {#if mediaData.has_image}
                  {@const thumbUrl = `${API_BASE}${mediaData.thumbnail_url}?v=${Date.now()}`}
                  {@const imgKey = mediaData.texture_name || 'main-image'}
                  <div class="media-card">
                    <button class="media-image-wrap" onclick={() => { imageOverlay = thumbUrl; }}>
                      <div class="image-container">
                        {#if imageLoadStates.get(imgKey) !== 'loaded'}
                          <div class="image-shimmer"></div>
                        {/if}
                        <img
                          class="media-image"
                          class:image-reveal={imageLoadStates.get(imgKey) === 'loaded'}
                          class:image-hidden={imageLoadStates.get(imgKey) !== 'loaded'}
                          src={thumbUrl}
                          alt={entityLabel}
                          loading="lazy"
                          onload={() => {
                            const next = new Map(imageLoadStates);
                            next.set(imgKey, 'loaded');
                            imageLoadStates = next;
                          }}
                          onerror={(e) => {
                            e.target.classList.add('broken');
                            const next = new Map(imageLoadStates);
                            next.set(imgKey, 'error');
                            imageLoadStates = next;
                          }}
                        />
                      </div>
                    </button>
                    <span class="media-card-name">{entityLabel}</span>
                    <span class="media-card-label">{mediaData.texture_name || 'image'}</span>
                  </div>
                {/if}
                {#if mediaData.has_audio}
                  <div class="media-audio-wrap">
                    {#key mediaData.stream_url}
                      <audio controls preload="metadata" crossorigin="anonymous" class="media-audio-player"
                        onerror={() => logger.warning('Audio playback failed', { url: mediaData.stream_url })}
                        src="{API_BASE}{mediaData.stream_url}"
                      >
                      </audio>
                    {/key}
                    <span class="media-label">{mediaData.voice_id || 'audio'}</span>
                  </div>
                {/if}
              {:else if nodeHasMediaHint(node)}
                <!-- Client-side fallback: show detected media attributes from node -->
                {@const imgAttr = getNodeImageAttr(node)}
                {@const audAttr = getNodeAudioAttr(node)}
                {#if imgAttr}
                  <div class="media-attr-row">
                    <span class="media-attr-icon">&#128444;</span>
                    <div class="media-attr-info">
                      <span class="media-attr-name">{imgAttr.name}</span>
                      <span class="media-attr-value">{imgAttr.value}</span>
                    </div>
                  </div>
                {/if}
                {#if audAttr}
                  <div class="media-attr-row">
                    <span class="media-attr-icon">&#127925;</span>
                    <div class="media-attr-info">
                      <span class="media-attr-name">{audAttr.name}</span>
                      <span class="media-attr-value">{audAttr.value}</span>
                    </div>
                  </div>
                {/if}
              {:else}
                <p class="section-empty">No media linked to this node</p>
              {/if}
            </div>
          {/if}

          <!-- Info Tab -->
          {#if activeTab === 'info'}
            <div class="tab-body">
              {#if node}
                <!-- Identity -->
                {#if infoIdentity.length > 0}
                  <div class="info-group">
                    <div class="info-group-label">식별 정보</div>
                    {#each infoIdentity as [key, value] (key)}
                      <div class="info-row">
                        <span class="info-key">{key}</span>
                        <span class="info-value">{value}</span>
                      </div>
                    {/each}
                  </div>
                {/if}

                <!-- Stats -->
                {#if infoStats.length > 0}
                  <div class="info-group">
                    <div class="info-group-label">기본 정보</div>
                    {#each infoStats as [key, value] (key)}
                      <div class="info-row">
                        <span class="info-key">{key}</span>
                        <span class="info-value">{value}</span>
                      </div>
                    {/each}
                  </div>
                {/if}

                <!-- References (clickable) -->
                {#if infoRefs.length > 0}
                  <div class="info-group">
                    <div class="info-group-label">참조 링크</div>
                    {#each infoRefs as [key, value] (key)}
                      <div class="info-row">
                        <span class="info-key">{key}</span>
                        <button class="info-link" onclick={() => onNavigateToNode(String(value))}>{value}</button>
                      </div>
                    {/each}
                  </div>
                {/if}

                <!-- Other attributes -->
                {#if infoOther.length > 0}
                  <div class="info-group">
                    <div class="info-group-label">기타</div>
                    {#each infoOther as [key, value] (key)}
                      <div class="info-row">
                        <span class="info-key">{key}</span>
                        <span class="info-value" title={String(value ?? '')}>{truncate(String(value ?? ''), 50)}</span>
                      </div>
                    {/each}
                  </div>
                {/if}

                {#if infoCount === 0}
                  <p class="section-empty">No attributes to display</p>
                {/if}
              {/if}
            </div>
          {/if}

          </div>
        </div>
      </div>
    {/if}
  </div>

  <!-- Image overlay -->
  {#if imageOverlay}
    <div class="overlay-backdrop" onclick={() => { imageOverlay = null; }}>
      <img class="overlay-img" src={imageOverlay} alt="Full preview" />
    </div>
  {/if}
{/if}

<!-- ===== SNIPPETS ===== -->

{#snippet shimmerRows(n)}
  <div class="shimmer-wrap">
    {#each Array(n) as _, i (i)}
      <div class="shimmer-row">
        <div class="shimmer-line" style="width: {75 - i * 10}%;"></div>
      </div>
    {/each}
  </div>
{/snippet}

<style>
  /* ===== THEME VARS ===== */
  .context-panel {
    --panel-bg: #252526;
    --panel-bg-hover: #2c313a;
    --panel-border: #3c3c3c;
    --panel-border-subtle: #2d2d2d;
    --section-header-bg: #21252b;
    --prop-key-color: #d19a66;
    --prop-value-color: #abb2bf;
    --badge-exact: #2d5a3d;
    --badge-similar: #5a4a2d;
    --badge-fuzzy: #3a3a3a;
    --ai-border-confident: #10b981;
    --text-bright: #d4d4d4;
    --text-dim: #6b7280;
    --link-color: #61afef;
    --green-value: #98c379;
    --warm: #d49a5c;
    --warm-bright: #f0b878;
    --warm-hot: #e88a3a;
    --warm-glow: rgba(212, 154, 92, 0.3);

    display: flex;
    flex-direction: column;
    background: var(--panel-bg);
    border-left: 1px solid var(--panel-border);
    box-shadow:
      -4px 0 20px rgba(0, 0, 0, 0.4),
      0 0 0 1px rgba(255, 255, 255, 0.02),
      -1px 0 40px rgba(212, 154, 92, 0.08),
      inset 0 1px 0 rgba(255, 255, 255, 0.03);
    position: relative;
    transition: width 0.15s ease;
    overflow: hidden;
    color: var(--prop-value-color);
    font-family: 'IBM Plex Sans', -apple-system, sans-serif;
    font-size: 13px;
  }

  .context-panel.collapsed {
    min-width: 40px;
    max-width: 40px;
  }

  /* ===== RESIZE HANDLE ===== */
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
  .resize-handle:hover { background: #528bff; transition: background 0.15s ease; }

  /* ===== COLLAPSE BUTTON ===== */
  .collapse-btn {
    position: absolute;
    top: 8px;
    left: 8px;
    width: 24px;
    height: 24px;
    border: none;
    background: var(--section-header-bg);
    border-radius: 4px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--prop-value-color);
    z-index: 5;
  }
  .collapse-btn:hover { background: var(--panel-bg-hover); }

  /* ===== PANEL CONTENT ===== */
  .panel-content {
    display: flex;
    flex-direction: column;
    padding-top: 40px;
    overflow: hidden;
    flex: 1;
  }

  /* Tab crossfade animated wrapper (WOW-03) */
  .tab-content-animated {
    height: 100%;
    overflow-y: auto;
    overflow-x: hidden;
  }

  /* ===== PANEL HEADER ===== */
  .panel-header {
    display: flex;
    align-items: center;
    gap: 0;
    padding: 0;
    border-bottom: 1px solid var(--panel-border);
    flex-shrink: 0;
    min-height: 42px;
    backdrop-filter: blur(8px);
    background: rgba(33, 37, 43, 0.85);
  }

  .header-accent {
    width: 4px;
    align-self: stretch;
    flex-shrink: 0;
  }

  .header-info {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 1px;
    padding: 6px 10px;
    min-width: 0;
  }

  .header-tag {
    font-size: 14px;
    font-weight: 600;
    color: var(--text-bright);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .header-label {
    font-size: 11px;
    color: var(--text-dim);
    font-family: 'IBM Plex Mono', monospace;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .pin-btn {
    flex-shrink: 0;
    width: 28px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: transparent;
    border: none;
    color: var(--text-dim);
    cursor: pointer;
    border-radius: 4px;
    margin-right: 6px;
  }
  .pin-btn:hover { background: var(--panel-bg-hover); color: var(--prop-value-color); }
  .pin-btn.active { color: var(--link-color); }

  /* ===== TAB BAR ===== */
  .tab-bar {
    display: flex;
    background: #21252b;
    border-bottom: 1px solid #3c3c3c;
    gap: 0;
    flex-shrink: 0;
  }

  .tab-btn {
    flex: 1;
    padding: 8px 4px;
    border: none;
    background: transparent;
    color: #6b7280;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    cursor: pointer;
    border-bottom: 2px solid transparent;
    transition: color 0.15s, border-color 0.15s;
    font-family: inherit;
  }

  .tab-btn:hover { color: #abb2bf; }

  .tab-btn.active {
    color: var(--warm-bright);
    border-bottom-color: var(--warm);
    animation: tabBreathe 3s ease-in-out infinite;
  }

  .tab-count {
    font-size: 9px;
    font-weight: 500;
    padding: 0 4px;
    border-radius: 6px;
    background: rgba(212, 154, 92, 0.15);
    color: var(--warm-bright);
    box-shadow: 0 0 6px rgba(212, 154, 92, 0.2);
    margin-left: 4px;
    vertical-align: middle;
  }

  /* ===== TAB CONTENT (fills ALL remaining space) ===== */
  .tab-content {
    flex: 1;
    overflow-y: auto;
    overflow-x: hidden;
    min-height: 0;
    animation: fadeSlideIn 0.2s ease-out;
    scrollbar-width: thin;
    scrollbar-color: var(--panel-border) transparent;
  }
  .tab-content::-webkit-scrollbar { width: 6px; }
  .tab-content::-webkit-scrollbar-track { background: transparent; }
  .tab-content::-webkit-scrollbar-thumb { background: var(--panel-border); border-radius: 3px; }

  .tab-body {
    padding: 8px 10px;
  }

  .section-error {
    margin: 0;
    font-size: 12px;
    color: #e06c75;
  }

  .section-empty {
    margin: 0;
    font-size: 12px;
    color: var(--text-dim);
    font-style: italic;
  }

  /* ===== CONTEXT SECTION ===== */
  .context-section { margin-bottom: 16px; }
  .context-section-label {
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--warm);
    padding: 6px 0 4px;
    border-bottom: 1px solid var(--panel-border);
    margin-bottom: 8px;
  }

  /* ===== CHILDREN ===== */
  .child-btn {
    display: flex;
    align-items: center;
    gap: 6px;
    width: 100%;
    padding: 4px 6px;
    background: transparent;
    border: 1px solid var(--panel-border-subtle);
    border-radius: 4px;
    cursor: pointer;
    font-family: inherit;
    font-size: 11px;
    color: var(--prop-value-color);
    text-align: left;
    margin-bottom: 3px;
  }
  .child-btn:hover { background: var(--panel-bg-hover); border-color: var(--panel-border); }

  .child-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .child-tag {
    font-size: 10px;
    font-weight: 600;
    color: var(--text-dim);
    flex-shrink: 0;
  }

  .child-name {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .more-children {
    font-size: 11px;
    color: var(--text-dim);
    padding: 2px 6px;
    display: block;
  }

  /* ===== ATTRIBUTE SUMMARY ===== */
  .attr-summary { margin-top: 4px; }
  .attr-summary-row {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    padding: 3px 0;
    gap: 8px;
    border-bottom: 1px solid var(--panel-border-subtle);
  }
  .attr-summary-row:last-child { border-bottom: none; }
  .attr-summary-key {
    font-size: 11px;
    color: var(--prop-key-color);
    flex-shrink: 0;
  }
  .attr-summary-value {
    font-size: 11px;
    color: var(--text-dim);
    text-align: right;
    word-break: break-word;
  }

  /* ===== DICTIONARY ===== */
  .dict-row {
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: 8px 10px;
    margin-bottom: 4px;
    border-radius: 6px;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
  }

  /* Dictionary staggered fade-in (WOW-03) */
  .dict-result-item {
    animation: staggerFadeIn 0.2s cubic-bezier(0.4, 0, 0.2, 1) both;
  }
  .dict-result-item:nth-child(1) { animation-delay: 0ms; }
  .dict-result-item:nth-child(2) { animation-delay: 50ms; }
  .dict-result-item:nth-child(3) { animation-delay: 50ms; }
  .dict-result-item:nth-child(4) { animation-delay: 100ms; }
  .dict-result-item:nth-child(5) { animation-delay: 150ms; }
  .dict-result-item:nth-child(n+6) { animation-delay: 200ms; }

  @keyframes staggerFadeIn {
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: translateY(0); }
  }
  .dict-row:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3), 0 0 8px var(--warm-glow);
  }
  .dict-row.tier-exact { background: var(--badge-exact); }
  .dict-row.tier-similar { background: var(--badge-similar); }
  .dict-row.tier-fuzzy { background: var(--badge-fuzzy); }

  .dict-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }

  .dict-source {
    font-size: 13px;
    font-weight: 600;
    background: linear-gradient(135deg, var(--warm), var(--warm-bright));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .dict-target {
    font-size: 11px;
    color: var(--text-dim);
    line-height: 1.5;
    white-space: pre-wrap;
    word-break: break-word;
  }

  .dict-badge {
    font-size: 10px;
    font-weight: 600;
    padding: 1px 6px;
    border-radius: 6px;
    color: var(--prop-value-color);
    flex-shrink: 0;
  }
  .dict-badge.tier-exact { background: rgba(16, 185, 129, 0.3); }
  .dict-badge.tier-similar { background: rgba(245, 158, 11, 0.3); }
  .dict-badge.tier-fuzzy { background: rgba(255, 255, 255, 0.08); }

  /* ===== AI CONTEXT ===== */
  .ai-summary {
    padding: 12px 14px 12px 14px;
    background: rgba(212, 154, 92, 0.04);
    border-left: 3px solid var(--warm);
    border-radius: 0 8px 8px 0;
    font-size: 12px;
    line-height: 1.6;
    color: var(--prop-value-color);
    white-space: pre-wrap;
    animation: fadeSlideIn 0.25s ease-out backwards;
  }

  .ai-source {
    display: block;
    font-size: 10px;
    color: var(--text-dim);
    margin-top: 6px;
  }

  .source-link {
    background: none;
    border: none;
    color: var(--link-color);
    cursor: pointer;
    font-family: inherit;
    font-size: 10px;
    padding: 0;
    text-decoration: underline;
  }

  .regen-btn {
    margin-top: 6px;
    padding: 3px 10px;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid var(--panel-border);
    border-radius: 4px;
    cursor: pointer;
    font-family: inherit;
    font-size: 11px;
    color: var(--prop-value-color);
  }
  .regen-btn:hover { background: var(--panel-bg-hover); }

  .ai-error {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 8px;
    background: rgba(224, 108, 117, 0.1);
    border-radius: 4px;
    font-size: 12px;
    color: #e06c75;
  }

  .ai-error-icon {
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: rgba(224, 108, 117, 0.2);
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 11px;
    flex-shrink: 0;
  }

  /* ===== MEDIA (CHARACTER CARD style) ===== */
  .media-tab-body {
    display: flex;
    flex-direction: column;
    align-items: center;
  }

  .media-card {
    display: flex;
    flex-direction: column;
    align-items: center;
    width: 100%;
    margin-bottom: 12px;
    animation: fadeSlideIn 0.25s ease-out backwards;
  }

  .media-image-wrap {
    display: block;
    width: 100%;
    padding: 0;
    border: 1px solid var(--panel-border);
    border-radius: 16px;
    cursor: pointer;
    background: #1a1a2e;
    overflow: hidden;
  }
  .media-image-wrap:hover { border-color: var(--link-color); box-shadow: 0 0 12px var(--warm-glow); }

  .media-image {
    width: 100%;
    max-height: 300px;
    object-fit: contain;
    border-radius: 16px;
    background: #1a1a2e;
    display: block;
  }
  .media-image.broken {
    border: 2px solid #e06c75;
    opacity: 0.4;
  }

  .media-card-name {
    font-size: 13px;
    font-weight: 600;
    color: var(--text-bright);
    margin-top: 8px;
    text-align: center;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 100%;
  }

  .media-card-label {
    font-size: 10px;
    color: var(--text-dim);
    font-family: 'IBM Plex Mono', monospace;
    margin-top: 2px;
    text-align: center;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .media-audio-player {
    width: 100%;
    height: 36px;
    border-radius: 4px;
  }

  .media-audio-wrap {
    display: flex;
    flex-direction: column;
    gap: 6px;
    width: 100%;
    margin-top: 8px;
  }

  .media-label {
    display: block;
    font-size: 10px;
    color: var(--text-dim);
    font-family: 'IBM Plex Mono', monospace;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .play-btn {
    width: 36px;
    height: 36px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    border: 1px solid var(--panel-border);
    background: rgba(255, 255, 255, 0.04);
    color: var(--text-bright);
    cursor: pointer;
    font-size: 16px;
    flex-shrink: 0;
  }
  .play-btn:hover { background: var(--panel-bg-hover); border-color: var(--link-color); }
  .play-btn.playing { background: rgba(97, 175, 239, 0.15); border-color: var(--link-color); color: var(--link-color); }

  /* ===== MEDIA ATTRIBUTE FALLBACK ===== */
  .media-attr-row {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 8px;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid var(--panel-border-subtle);
    border-radius: 4px;
    margin-bottom: 6px;
    width: 100%;
  }

  .media-attr-icon {
    font-size: 18px;
    flex-shrink: 0;
    opacity: 0.7;
  }

  .media-attr-info {
    display: flex;
    flex-direction: column;
    gap: 1px;
    min-width: 0;
  }

  .media-attr-name {
    font-size: 10px;
    font-weight: 600;
    color: var(--prop-key-color);
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }

  .media-attr-value {
    font-size: 12px;
    color: var(--prop-value-color);
    font-family: 'IBM Plex Mono', monospace;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  /* ===== INFO TAB ===== */
  .info-group { margin-bottom: 12px; }
  .info-group-label {
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--warm);
    padding: 6px 0 4px;
    border-bottom: 1px solid var(--panel-border);
    margin-bottom: 4px;
    text-shadow: 0 0 8px rgba(212, 154, 92, 0.2);
  }
  .info-row {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    padding: 3px 0;
    gap: 8px;
  }
  .info-key {
    font-size: 11px;
    color: var(--prop-key-color);
    flex-shrink: 0;
  }
  .info-value {
    font-size: 12px;
    color: var(--text-bright);
    text-align: right;
    word-break: break-word;
  }
  .info-link {
    font-size: 12px;
    color: var(--link-color);
    background: none;
    border: none;
    cursor: pointer;
    text-align: right;
    padding: 0;
    font-family: inherit;
    border-bottom: 1px dotted var(--link-color);
  }
  .info-link:hover { text-decoration: underline; }

  /* ===== SHIMMER ===== */
  .shimmer-wrap {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 4px 0;
  }

  .shimmer-row { height: 14px; }

  .shimmer-line {
    height: 100%;
    border-radius: 4px;
    background: linear-gradient(90deg, rgba(255,255,255,0.04) 25%, rgba(255,255,255,0.08) 50%, rgba(255,255,255,0.04) 75%);
    background-size: 200% 100%;
    animation: shimmer 1.5s infinite;
  }

  @keyframes shimmer {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
  }

  @keyframes tabBreathe {
    0%, 100% { text-shadow: 0 0 8px rgba(212, 154, 92, 0.3); }
    50% { text-shadow: 0 0 16px rgba(212, 154, 92, 0.5); }
  }

  @keyframes fadeSlideIn {
    from { opacity: 0; transform: translateY(8px); }
    to { opacity: 1; transform: translateY(0); }
  }

  @keyframes statusPulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
  }

  /* === Image Shimmer to Reveal (WOW-03) === */
  .image-container {
    position: relative;
    border-radius: 16px;
    overflow: hidden;
    min-height: 100px;
    width: 100%;
  }

  .image-shimmer {
    position: absolute;
    inset: 0;
    background: linear-gradient(90deg, #2d2d3d 25%, #3d3d4d 50%, #2d2d3d 75%);
    background-size: 200% 100%;
    animation: imageShimmer 1.5s infinite;
    border-radius: 16px;
  }

  @keyframes imageShimmer {
    0%   { background-position: 200% 0; }
    100% { background-position: -200% 0; }
  }

  .image-hidden {
    opacity: 0;
  }

  .image-reveal {
    animation: imageReveal 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  }

  @keyframes imageReveal {
    from { opacity: 0; filter: blur(8px); }
    to   { opacity: 1; filter: blur(0); }
  }

  /* ===== IMAGE OVERLAY ===== */
  .overlay-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.75);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
    cursor: pointer;
  }

  .overlay-img {
    max-width: 80vw;
    max-height: 80vh;
    border-radius: 8px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
  }
</style>
