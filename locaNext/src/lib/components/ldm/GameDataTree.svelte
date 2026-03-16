<script>
  /**
   * GameDataTree.svelte - Phase 28: Hierarchical Game Data Tree
   *
   * Renders XML game data as an expandable tree with per-entity-type icons,
   * keyboard navigation, and API integration to Phase 27 tree endpoints.
   * Replaces VirtualGrid as the primary Game Dev view.
   */
  import {
    ChevronDown,
    ChevronRight,
    ArrowRight,
    Lightning,
    ShoppingCatalog,
    UserAvatar,
    GameWireless,
    Book,
    Task,
    Map,
    Locked,
    GroupPresentation,
    LocationStar,
    DataStructured,
    Code,
    Renew
  } from 'carbon-icons-svelte';
  import { SkeletonText } from 'carbon-components-svelte';
  import { logger } from '$lib/utils/logger.js';
  import { getAuthHeaders, getApiBase } from '$lib/utils/api.js';

  // Props
  let {
    filePath = null,
    folderPath = null,
    onNodeSelect = () => {}
  } = $props();

  const API_BASE = getApiBase();

  // State (Svelte 5 Runes)
  let treeData = $state(null);
  let expandedNodes = $state(new Set());
  let selectedNodeId = $state(null);
  let loading = $state(false);
  let error = $state(null);
  let hoveredNodeId = $state(null);
  let hoverTimer = null;

  // Index state (Phase 29: auto-index + search)
  let indexReady = $state(false);
  let indexing = $state(false);
  let indexStats = $state(null);
  let searchQuery = $state('');
  let searchResults = $state([]);
  let searching = $state(false);
  let searchDebounceTimer = null;

  // Flat list of visible nodes for keyboard navigation
  let visibleNodes = $derived(buildVisibleNodes());

  // Editable attributes mapping (mirrors backend EDITABLE_ATTRS)
  const EDITABLE_ATTRS = {
    ItemInfo: ['ItemName', 'ItemDesc'],
    CharacterInfo: ['CharacterName'],
    SkillInfo: ['SkillName', 'SkillDesc'],
    GimmickGroupInfo: ['GimmickName'],
    GimmickInfo: ['GimmickName'],
    KnowledgeInfo: ['Name', 'Desc'],
    FactionGroup: ['GroupName'],
    QuestInfo: ['QuestName', 'QuestDesc'],
    RegionInfo: ['RegionName', 'RegionDesc'],
    SceneObjectData: ['ObjectName', 'ObjectDesc', 'AliasName'],
    SealDataInfo: ['SealName', 'Desc'],
    SkillTreeInfo: ['UIPageName'],
    NodeWaypointInfo: []
  };

  // Icon mapping by entity tag
  const ICON_MAP = {
    SkillTreeInfo: Lightning,
    SkillInfo: Lightning,
    SkillNode: Lightning,
    ItemInfo: ShoppingCatalog,
    CharacterInfo: UserAvatar,
    GimmickGroupInfo: GameWireless,
    GimmickInfo: GameWireless,
    KnowledgeInfo: Book,
    QuestInfo: Task,
    RegionInfo: Map,
    SceneObjectData: Map,
    SealDataInfo: Locked,
    FactionGroup: GroupPresentation,
    NodeWaypointInfo: LocationStar
  };

  /**
   * Get the icon component for a given tag name
   */
  function getNodeIcon(tag) {
    return ICON_MAP[tag] || DataStructured;
  }

  // Entity type color palette for row accents and badges
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

  function getNodeColor(tag) {
    return ENTITY_TYPE_COLORS[tag] || '#64748b';
  }

  /**
   * Get the primary display label for a node
   */
  function getNodeLabel(node) {
    const primaryAttr = EDITABLE_ATTRS[node.tag]?.[0];
    const primaryVal = primaryAttr && node.attributes?.[primaryAttr];
    if (primaryVal) return primaryVal;
    return node.attributes?.Key || node.attributes?.NodeId || node.attributes?.Name || node.tag;
  }

  // ========================================
  // Cross-Reference Detection & Navigation
  // ========================================

  /** Known cross-reference attribute names */
  const CROSS_REF_ATTRS = new Set([
    'LearnKnowledgeKey', 'RequireSkillKey', 'LinkedQuestKey', 'RegionKey',
    'ParentNodeId', 'ParentId', 'TargetKey', 'ItemKey', 'CharacterKey',
    'GimmickKey', 'SealKey', 'FactionKey', 'SkillKey', 'KnowledgeKey',
    'RewardKey'
  ]);

  /** Identity attribute names that should NOT be treated as cross-references */
  const IDENTITY_ATTRS = new Set(['Key', 'NodeId', 'Id', 'StrKey']);

  /**
   * Check if an attribute name is a cross-reference
   */
  function isCrossRefAttr(attrName) {
    if (CROSS_REF_ATTRS.has(attrName)) return true;
    // Heuristic: any attr ending in "Key" or "Id" that is NOT the node's own identifier
    if ((attrName.endsWith('Key') || attrName.endsWith('Id')) && !IDENTITY_ATTRS.has(attrName)) return true;
    return false;
  }

  /** Global node lookup index -- maps various keys to node objects */
  let nodeIndex = $state(new Map());

  // Build node index when tree data loads
  $effect(() => {
    if (!treeData || treeData.length === 0) {
      nodeIndex = new Map();
      return;
    }
    const index = new Map();
    function indexNode(node) {
      // Index by node_id
      index.set(node.node_id, node);
      // Index by Key attribute
      if (node.attributes?.Key) index.set(`key:${node.attributes.Key}`, node);
      // Index by NodeId attribute
      if (node.attributes?.NodeId) index.set(`nodeid:${node.attributes.NodeId}`, node);
      // Index by Id attribute
      if (node.attributes?.Id) index.set(`id:${node.attributes.Id}`, node);
      for (const child of node.children || []) indexNode(child);
    }
    for (const fileTree of treeData) {
      for (const root of fileTree.roots || []) indexNode(root);
    }
    nodeIndex = index;
  });

  /**
   * Get ancestor node_ids by walking up via parent_id
   */
  function getAncestorIds(node) {
    const ancestors = [];
    let currentId = node.parent_id;
    while (currentId) {
      ancestors.push(currentId);
      const parent = nodeIndex.get(currentId);
      if (parent) {
        currentId = parent.parent_id;
      } else {
        break;
      }
    }
    return ancestors;
  }

  /** Prefixes to try when resolving cross-reference lookups */
  const CROSS_REF_PREFIXES = ['key:', 'nodeid:', 'id:'];

  /**
   * Resolve a cross-reference attribute to a target node_id
   */
  function resolveCrossRef(attrName, attrValue) {
    if (!attrValue || attrValue === '0' || attrValue === '') return null;
    for (const prefix of CROSS_REF_PREFIXES) {
      const target = nodeIndex.get(`${prefix}${attrValue}`);
      if (target) return target.node_id;
    }
    return null;
  }

  /**
   * Navigate to a target node: expand ancestors, select it, scroll into view
   */
  function selectAndRevealNode(targetNodeId) {
    const targetNode = nodeIndex.get(targetNodeId);
    if (!targetNode) {
      logger.warning('Cross-ref target not found', { targetNodeId });
      return false;
    }

    // Expand all ancestors to reveal the target
    const ancestors = getAncestorIds(targetNode);
    const newExpanded = new Set(expandedNodes);
    for (const id of ancestors) newExpanded.add(id);
    expandedNodes = newExpanded;

    // Select the target
    selectedNodeId = targetNode.node_id;
    onNodeSelect?.(targetNode);

    // Scroll into view after DOM update
    requestAnimationFrame(() => {
      const el = document.querySelector(`[data-node-id="${targetNode.node_id}"]`);
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    });

    return true;
  }

  /**
   * Public method for external cross-ref navigation (e.g., NodeDetailPanel)
   */
  export function navigateToNode(nodeId) {
    return selectAndRevealNode(nodeId);
  }

  /**
   * Build flat list of visible nodes (for keyboard navigation)
   */
  function buildVisibleNodes() {
    if (!treeData) return [];
    const nodes = [];

    function walkNode(node) {
      nodes.push(node);
      if (expandedNodes.has(node.node_id) && node.children?.length > 0) {
        for (const child of node.children) {
          walkNode(child);
        }
      }
    }

    for (const fileData of treeData) {
      for (const root of fileData.roots || []) {
        walkNode(root);
      }
    }
    return nodes;
  }

  // ========================================
  // API Integration
  // ========================================

  /**
   * Shared fetch helper for tree endpoints
   */
  async function fetchTree(endpoint, path, onSuccess, logLabel) {
    if (!path) return;
    loading = true;
    error = null;

    try {
      logger.apiCall(endpoint, 'POST');
      const response = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: {
          ...getAuthHeaders(),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ path })
      });

      if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }));
        throw new Error(err.detail || `HTTP ${response.status}`);
      }

      const data = await response.json();
      onSuccess(data);
      selectedNodeId = null;
    } catch (err) {
      error = err.message;
      treeData = null;
      logger.error(`Failed to load ${logLabel}`, { error: err.message, path });
    } finally {
      loading = false;
    }
  }

  /**
   * Load tree for a single file
   */
  function loadFileTree(path) {
    fetchTree('/api/ldm/gamedata/tree', path, (data) => {
      treeData = [data];
      expandedNodes = new Set((data.roots || []).map(r => r.node_id));
      logger.success('File tree loaded', {
        file: path,
        nodeCount: data.node_count,
        entityType: data.entity_type
      });
      // Phase 29: Auto-build index for single file (extract directory)
      const dirPath = path.substring(0, path.lastIndexOf('/'));
      if (dirPath) buildIndex(dirPath);
    }, 'file tree');
  }

  /**
   * Load tree for entire folder
   */
  function loadFolderTree(path) {
    fetchTree('/api/ldm/gamedata/tree/folder', path, (data) => {
      // Annotate each node with its source file path for save operations
      for (const fileEntry of (data.files || [])) {
        const annotate = (node) => {
          node._filePath = fileEntry.file_path;
          for (const child of (node.children || [])) annotate(child);
        };
        for (const root of (fileEntry.roots || [])) annotate(root);
      }
      treeData = data.files || [];
      expandedNodes = new Set(treeData.map(f => `file:${f.file_path}`));
      logger.success('Folder tree loaded', {
        path,
        fileCount: treeData.length,
        totalNodes: data.total_nodes
      });
      // Phase 29: Auto-build index after folder tree loads (fire-and-forget)
      buildIndex(path);
    }, 'folder tree');
  }

  // ========================================
  // Reactive Loading
  // ========================================

  $effect(() => {
    if (filePath) {
      loadFileTree(filePath);
    } else if (folderPath) {
      loadFolderTree(folderPath);
    }
  });

  // ========================================
  // Node Interaction
  // ========================================

  /**
   * Toggle expand/collapse for a node
   */
  function toggleExpand(nodeId) {
    const newSet = new Set(expandedNodes);
    if (newSet.has(nodeId)) {
      newSet.delete(nodeId);
    } else {
      newSet.add(nodeId);
    }
    expandedNodes = newSet;
  }

  /**
   * Select a node and notify parent
   */
  function selectNode(node) {
    selectedNodeId = node.node_id;
    onNodeSelect?.(node);
  }

  /**
   * Find parent node for keyboard navigation (uses nodeIndex for O(1) lookup)
   */
  function findParentNode(nodeId) {
    const node = nodeIndex.get(nodeId);
    if (!node?.parent_id) return null;
    return nodeIndex.get(node.parent_id) || null;
  }

  /**
   * Keyboard navigation handler
   */
  function handleKeydown(event) {
    if (!visibleNodes.length) return;

    const currentIdx = visibleNodes.findIndex(n => n.node_id === selectedNodeId);
    const currentNode = currentIdx >= 0 ? visibleNodes[currentIdx] : null;

    switch (event.key) {
      case 'ArrowDown': {
        event.preventDefault();
        const nextIdx = currentIdx < visibleNodes.length - 1 ? currentIdx + 1 : 0;
        selectNode(visibleNodes[nextIdx]);
        break;
      }
      case 'ArrowUp': {
        event.preventDefault();
        const prevIdx = currentIdx > 0 ? currentIdx - 1 : visibleNodes.length - 1;
        selectNode(visibleNodes[prevIdx]);
        break;
      }
      case 'ArrowRight': {
        event.preventDefault();
        if (currentNode) {
          if (currentNode.children?.length > 0 && !expandedNodes.has(currentNode.node_id)) {
            toggleExpand(currentNode.node_id);
          } else if (currentNode.children?.length > 0) {
            // Move to first child
            const nextIdx = currentIdx + 1;
            if (nextIdx < visibleNodes.length) {
              selectNode(visibleNodes[nextIdx]);
            }
          }
        }
        break;
      }
      case 'ArrowLeft': {
        event.preventDefault();
        if (currentNode) {
          if (expandedNodes.has(currentNode.node_id) && currentNode.children?.length > 0) {
            toggleExpand(currentNode.node_id);
          } else {
            // Move to parent
            const parent = findParentNode(currentNode.node_id);
            if (parent) {
              selectNode(parent);
            }
          }
        }
        break;
      }
      case 'Enter': {
        event.preventDefault();
        if (currentNode?.children?.length > 0) {
          toggleExpand(currentNode.node_id);
        }
        break;
      }
      case ' ': {
        event.preventDefault();
        if (currentNode) {
          selectNode(currentNode);
        }
        break;
      }
    }
  }

  /**
   * Hover handlers for tooltip display (300ms delay)
   */
  function handleNodeMouseEnter(nodeId) {
    if (hoverTimer) clearTimeout(hoverTimer);
    hoverTimer = setTimeout(() => {
      hoveredNodeId = nodeId;
    }, 300);
  }

  function handleNodeMouseLeave() {
    if (hoverTimer) clearTimeout(hoverTimer);
    hoverTimer = null;
    hoveredNodeId = null;
  }

  /**
   * Public reload method
   */
  export function reload() {
    if (filePath) loadFileTree(filePath);
    else if (folderPath) loadFolderTree(folderPath);
  }

  // ========================================
  // Index Integration (Phase 29)
  // ========================================

  /**
   * Build search index for the loaded folder (fire-and-forget after tree load)
   */
  async function buildIndex(path) {
    indexing = true;
    indexReady = false;
    try {
      const response = await fetch(`${API_BASE}/api/ldm/gamedata/index/build`, {
        method: 'POST',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ path })
      });
      if (response.ok) {
        const data = await response.json();
        indexStats = data;
        indexReady = true;
        logger.success('Index built', { entities: data.entity_count, ms: data.build_time_ms });
      } else {
        logger.error('Index build returned error', { status: response.status });
      }
    } catch (err) {
      logger.error('Index build failed', { error: err.message });
    } finally {
      indexing = false;
    }
  }

  /**
   * Search entities via cascade search API
   */
  async function searchEntities(query) {
    if (!query.trim() || !indexReady) {
      searchResults = [];
      return;
    }
    searching = true;
    try {
      const response = await fetch(`${API_BASE}/api/ldm/gamedata/index/search`, {
        method: 'POST',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: query.trim(), top_k: 10 })
      });
      if (response.ok) {
        const data = await response.json();
        searchResults = data.results || [];
      }
    } catch (err) {
      logger.error('Search failed', { error: err.message });
    } finally {
      searching = false;
    }
  }

  /**
   * Debounced search handler (300ms)
   */
  function handleSearchInput(event) {
    searchQuery = event.target.value;
    clearTimeout(searchDebounceTimer);
    searchDebounceTimer = setTimeout(() => searchEntities(searchQuery), 300);
  }

  /**
   * Navigate to a search result node: expand parents, select, scroll into view
   */
  function navigateToResult(result) {
    const targetNodeId = result.node_id;
    const found = selectAndRevealNode(targetNodeId);
    if (found) {
      searchResults = [];
      searchQuery = '';
    } else {
      logger.warning('Search result node not found in tree', { node_id: targetNodeId });
    }
  }
</script>

<div class="gamedata-tree" role="tree" tabindex="0" onkeydown={handleKeydown}>
  <!-- Phase 29: Search bar (visible when folder/file is loaded) -->
  {#if folderPath || filePath}
    <div class="tree-search">
      <input
        type="search"
        placeholder={indexReady ? `Search ${indexStats?.entity_count || ''} entities...` : indexing ? 'Indexing...' : 'Search entities...'}
        value={searchQuery}
        oninput={handleSearchInput}
        disabled={!indexReady}
        class="search-input"
      />
      {#if indexing}
        <span class="index-status">Indexing...</span>
      {/if}
      {#if searching}
        <span class="index-status">Searching...</span>
      {/if}
      {#if searchResults.length > 0}
        <div class="search-dropdown">
          {#each searchResults as result (result.node_id + result.entity_name)}
            <button class="search-result" onclick={() => navigateToResult(result)}>
              <span class="result-name">{result.entity_name}</span>
              <span class="result-tag">{result.tag}</span>
              <span class="result-score">{result.match_type}</span>
            </button>
          {/each}
        </div>
      {/if}
    </div>
  {/if}

  {#if loading}
    <div class="loading-state">
      <SkeletonText lines={8} />
    </div>
  {:else if error}
    <div class="error-state">
      <p class="error-message">Failed to load tree</p>
      <p class="error-detail">{error}</p>
      <button class="retry-button" onclick={() => reload()} aria-label="Retry loading tree">
        <Renew size={14} />
        Retry
      </button>
    </div>
  {:else if treeData && treeData.length > 0}
    <div class="tree-content">
      {#if treeData.length === 1}
        <!-- Single file mode: render roots directly -->
        {#each treeData[0].roots || [] as rootNode (rootNode.node_id)}
          {@render renderNode(rootNode, 0)}
        {/each}
      {:else}
        <!-- Folder mode: group by file -->
        {#each treeData as fileData (fileData.file_path)}
          {@render renderFileGroup(fileData)}
        {/each}
      {/if}
    </div>
  {:else}
    <div class="empty-state">
      <DataStructured size={32} />
      <p>Select a file from the explorer to view its tree structure</p>
    </div>
  {/if}
</div>

{#snippet renderFileGroup(fileData)}
  {@const fileKey = `file:${fileData.file_path}`}
  {@const fileName = fileData.file_path.split('/').pop() || fileData.file_path}
  {@const isFileExpanded = expandedNodes.has(fileKey)}
  <div class="file-group">
    <button
      class="file-group-header"
      role="treeitem"
      aria-expanded={isFileExpanded}
      onclick={() => toggleExpand(fileKey)}
    >
      {#if isFileExpanded}
        <ChevronDown size={14} />
      {:else}
        <ChevronRight size={14} />
      {/if}
      <Code size={16} class="file-icon" />
      <span class="file-name">{fileName}</span>
      <span class="count-badge">{fileData.node_count} nodes</span>
    </button>

    {#if isFileExpanded}
      <div class="file-group-children" role="group">
        {#each fileData.roots || [] as rootNode (rootNode.node_id)}
          {@render renderNode(rootNode, 1)}
        {/each}
      </div>
    {/if}
  </div>
{/snippet}

{#snippet renderNode(node, depth)}
  {@const hasChildren = node.children?.length > 0}
  {@const isExpanded = expandedNodes.has(node.node_id)}
  {@const isSelected = selectedNodeId === node.node_id}
  {@const NodeIcon = getNodeIcon(node.tag)}
  {@const label = getNodeLabel(node)}
  {@const nodeColor = getNodeColor(node.tag)}
  <div class="tree-item" style="position: relative;">
    <button
      class="tree-node"
      class:selected={isSelected}
      class:has-children={hasChildren}
      class:depth-gt-0={depth > 0}
      data-node-id={node.node_id}
      role="treeitem"
      aria-expanded={hasChildren ? isExpanded : undefined}
      aria-selected={isSelected}
      style="--indent-px: {depth * 20 + 8}px; padding-left: {depth * 20 + 8}px; border-left-color: {isSelected ? 'var(--cds-link-01)' : nodeColor};"
      onclick={() => selectNode(node)}
      ondblclick={() => { if (hasChildren) toggleExpand(node.node_id); }}
      onmouseenter={() => handleNodeMouseEnter(node.node_id)}
      onmouseleave={handleNodeMouseLeave}
    >
      <!-- Chevron (animated rotation) -->
      {#if hasChildren}
        <span
          class="chevron"
          role="button"
          tabindex="-1"
          onclick={(e) => { e.stopPropagation(); toggleExpand(node.node_id); }}
        >
          <span class="chevron-icon" class:rotated={isExpanded}>
            <ChevronRight size={14} />
          </span>
        </span>
      {:else}
        <span class="chevron-spacer"></span>
      {/if}

      <!-- Entity type icon (colored by entity type) -->
      <span class="entity-icon-wrap" style="color: {nodeColor};">
        <NodeIcon size={16} />
      </span>

      <!-- Tag name -->
      <span class="node-tag">{node.tag}</span>

      <!-- Primary label -->
      {#if label !== node.tag}
        <span class="node-label">{label}</span>
      {/if}

      <!-- Children count badge (entity-color tinted) -->
      {#if hasChildren}
        <span class="count-badge" style="background: {nodeColor}20; color: {nodeColor};">{node.children.length}</span>
      {/if}

      <!-- Cross-reference links (max 2 per row) -->
      {#each Object.entries(node.attributes || {}).filter(([attr, val]) => isCrossRefAttr(attr) && resolveCrossRef(attr, val)).slice(0, 2) as [attr, val]}
        <button
          class="cross-ref-link"
          title="{attr}: {val} (click to navigate)"
          onclick={(e) => { e.stopPropagation(); selectAndRevealNode(resolveCrossRef(attr, val)); }}
        >
          <ArrowRight size={12} />
        </button>
      {/each}
    </button>

    <!-- Hover tooltip (first 3 attributes) -->
    {#if hoveredNodeId === node.node_id}
      <div class="node-tooltip" style="left: {depth * 20 + 40}px;">
        {#each Object.entries(node.attributes || {}).slice(0, 3) as [key, val]}
          <div class="tooltip-row">
            <span class="tooltip-key">{key}:</span>
            <span class="tooltip-val">{String(val).substring(0, 40)}</span>
          </div>
        {/each}
        {#if Object.keys(node.attributes || {}).length > 3}
          <div class="tooltip-more">+{Object.keys(node.attributes).length - 3} more</div>
        {/if}
      </div>
    {/if}

    <!-- Children (animated wrapper) -->
    {#if hasChildren}
      <div class="tree-children-wrapper" class:collapsed={!isExpanded} class:expanded={isExpanded}>
        <div class="tree-children" role="group">
          {#each node.children as child (child.node_id)}
            {@render renderNode(child, depth + 1)}
          {/each}
        </div>
      </div>
    {/if}
  </div>
{/snippet}

<style>
  .gamedata-tree {
    display: flex;
    flex-direction: column;
    width: 100%;
    height: 100%;
    overflow: hidden;
    background: var(--cds-layer-01);
    font-family: 'IBM Plex Mono', 'Consolas', monospace;
    font-size: 13px;
  }

  .gamedata-tree:focus {
    outline: none;
  }

  .loading-state {
    padding: 1rem;
  }

  .error-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.5rem;
    padding: 1.5rem 1rem;
    text-align: center;
  }

  .error-message {
    margin: 0;
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--cds-support-error);
  }

  .error-detail {
    margin: 0;
    font-size: 0.75rem;
    color: var(--cds-text-02);
    word-break: break-word;
  }

  .retry-button {
    display: flex;
    align-items: center;
    gap: 0.25rem;
    padding: 0.375rem 0.75rem;
    margin-top: 0.5rem;
    background: transparent;
    border: 1px solid var(--cds-border-strong-01);
    border-radius: 4px;
    color: var(--cds-text-01);
    cursor: pointer;
    font-size: 0.8125rem;
  }

  .retry-button:hover {
    background: var(--cds-layer-hover-01);
  }

  .retry-button:focus {
    outline: 2px solid var(--cds-focus);
    outline-offset: 1px;
  }

  .tree-content {
    flex: 1;
    overflow-y: auto;
    padding: 0.25rem 0;
    scrollbar-width: thin;
    scrollbar-color: var(--cds-border-subtle-01) transparent;
  }

  .tree-content::-webkit-scrollbar {
    width: 6px;
  }

  .tree-content::-webkit-scrollbar-track {
    background: transparent;
  }

  .tree-content::-webkit-scrollbar-thumb {
    background: var(--cds-border-subtle-01);
    border-radius: 3px;
  }

  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    flex: 1;
    padding: 2rem;
    color: var(--cds-text-02);
    text-align: center;
  }

  .empty-state p {
    margin: 0.5rem 0 0;
    font-size: 0.8125rem;
  }

  /* File Group (folder mode) */
  .file-group {
    margin-bottom: 2px;
  }

  .file-group-header {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    width: 100%;
    padding: 0.5rem 0.75rem;
    background: var(--cds-layer-02);
    border: none;
    border-radius: 2px;
    cursor: pointer;
    font-family: inherit;
    font-size: inherit;
    font-weight: 600;
    color: var(--cds-text-01);
    text-align: left;
    transition: background 0.1s ease;
  }

  .file-group-header:hover {
    background: var(--cds-layer-hover-01);
  }

  .file-group-header:focus {
    outline: 2px solid var(--cds-focus);
    outline-offset: -2px;
  }

  :global(.file-icon) {
    flex-shrink: 0;
    color: var(--cds-link-01);
  }

  .file-name {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .file-group-children {
    margin-left: 0.5rem;
    border-left: 1px solid var(--cds-border-subtle-01);
    padding-left: 0.25rem;
  }

  /* Tree Node */
  .tree-node {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    width: 100%;
    padding: 0.3125rem 0.5rem;
    background: transparent;
    border: none;
    border-left: 3px solid transparent;
    border-radius: 0 2px 2px 0;
    cursor: pointer;
    font-family: inherit;
    font-size: inherit;
    color: var(--cds-text-01);
    text-align: left;
    transition: background 0.15s ease, border-color 0.15s ease;
    line-height: 1.4;
    position: relative;
  }

  /* Tree connector lines (vertical + horizontal) for nested nodes */
  .tree-node.depth-gt-0::before {
    content: '';
    position: absolute;
    left: calc(var(--indent-px) - 12px);
    top: 0;
    height: 100%;
    width: 1px;
    background: var(--cds-border-subtle-01);
    pointer-events: none;
  }

  .tree-node.depth-gt-0::after {
    content: '';
    position: absolute;
    left: calc(var(--indent-px) - 12px);
    top: 50%;
    width: 8px;
    height: 1px;
    background: var(--cds-border-subtle-01);
    pointer-events: none;
  }

  .tree-node:hover {
    background: var(--cds-layer-hover-01);
  }

  .tree-node:focus {
    outline: 2px solid var(--cds-focus);
    outline-offset: -2px;
  }

  .tree-node.selected {
    background: var(--cds-layer-selected-01);
    border-left-color: var(--cds-link-01) !important;
    border-left-width: 3px;
  }

  /* Chevron with rotation animation */
  .chevron {
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    width: 16px;
    height: 16px;
    border: none;
    background: transparent;
    padding: 0;
    cursor: pointer;
    color: var(--cds-text-02);
  }

  .chevron:hover {
    color: var(--cds-text-01);
  }

  .chevron-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    transition: transform 200ms ease;
  }

  .chevron-icon.rotated {
    transform: rotate(90deg);
  }

  .chevron-spacer {
    width: 16px;
    flex-shrink: 0;
  }

  /* Entity icon wrapper (colored inline by entity type) */
  .entity-icon-wrap {
    display: flex;
    align-items: center;
    flex-shrink: 0;
  }

  /* Expand/collapse animation */
  .tree-children-wrapper {
    overflow: hidden;
    transition: max-height 200ms ease-out, opacity 200ms ease-out;
  }

  .tree-children-wrapper.collapsed {
    max-height: 0;
    opacity: 0;
  }

  .tree-children-wrapper.expanded {
    max-height: 10000px;
    opacity: 1;
  }

  /* Node label parts */
  .node-tag {
    font-weight: 500;
    color: var(--cds-text-02);
    font-size: 0.75rem;
    flex-shrink: 0;
  }

  .node-label {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: var(--cds-text-01);
    font-weight: 400;
  }

  .count-badge {
    font-size: 0.6875rem;
    padding: 0.0625rem 0.375rem;
    background: var(--cds-layer-02);
    border-radius: 10px;
    color: var(--cds-text-03);
    flex-shrink: 0;
  }

  /* Hover tooltip */
  .node-tooltip {
    position: absolute;
    top: 100%;
    z-index: 100;
    padding: 6px 10px;
    background: var(--cds-layer-02);
    border: 1px solid var(--cds-border-subtle-01);
    border-radius: 4px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    font-size: 0.6875rem;
    white-space: nowrap;
    pointer-events: none;
    max-width: 300px;
  }

  .tooltip-row {
    display: flex;
    gap: 4px;
  }

  .tooltip-key {
    color: var(--cds-text-03);
    flex-shrink: 0;
  }

  .tooltip-val {
    color: var(--cds-text-01);
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .tooltip-more {
    color: var(--cds-text-03);
    font-style: italic;
    margin-top: 2px;
  }

  /* Cross-reference link buttons */
  .cross-ref-link {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 18px;
    height: 18px;
    padding: 0;
    margin-left: 2px;
    background: transparent;
    border: 1px solid var(--cds-link-01);
    border-radius: 3px;
    color: var(--cds-link-01);
    cursor: pointer;
    flex-shrink: 0;
    transition: background 0.15s ease, color 0.15s ease;
  }

  .cross-ref-link:hover {
    background: var(--cds-link-01);
    color: var(--cds-inverse-01);
  }

  /* Tree children indentation guide */
  .tree-children {
    /* Indentation handled via padding-left on each node */
  }

  /* Phase 29: Search Bar */
  .tree-search {
    position: relative;
    padding: 0.5rem;
    border-bottom: 1px solid var(--cds-border-subtle-01);
    flex-shrink: 0;
  }

  .search-input {
    width: 100%;
    padding: 0.375rem 0.5rem;
    background: var(--cds-field-01);
    border: 1px solid var(--cds-border-subtle-01);
    border-radius: 4px;
    color: var(--cds-text-01);
    font-size: 0.75rem;
    font-family: inherit;
    outline: none;
    box-sizing: border-box;
  }

  .search-input:focus {
    border-color: var(--cds-focus);
    box-shadow: 0 0 0 1px var(--cds-focus);
  }

  .search-input:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .search-input::placeholder {
    color: var(--cds-text-03);
  }

  .index-status {
    display: block;
    margin-top: 0.25rem;
    font-size: 0.6875rem;
    color: var(--cds-text-03);
  }

  .search-dropdown {
    position: absolute;
    left: 0.5rem;
    right: 0.5rem;
    top: calc(100% - 2px);
    max-height: 300px;
    overflow-y: auto;
    z-index: 10;
    background: var(--cds-layer-02);
    border: 1px solid var(--cds-border-subtle-01);
    border-radius: 0 0 4px 4px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
  }

  .search-result {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    width: 100%;
    padding: 0.375rem 0.5rem;
    background: transparent;
    border: none;
    border-bottom: 1px solid var(--cds-border-subtle-01);
    cursor: pointer;
    font-family: inherit;
    font-size: 0.75rem;
    color: var(--cds-text-01);
    text-align: left;
  }

  .search-result:last-child {
    border-bottom: none;
  }

  .search-result:hover {
    background: var(--cds-layer-hover-01);
  }

  .result-name {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-weight: 500;
  }

  .result-tag {
    font-size: 0.6875rem;
    color: var(--cds-text-02);
    flex-shrink: 0;
  }

  .result-score {
    font-size: 0.625rem;
    color: var(--cds-text-03);
    flex-shrink: 0;
    padding: 1px 4px;
    background: var(--cds-layer-01);
    border-radius: 3px;
  }
</style>
