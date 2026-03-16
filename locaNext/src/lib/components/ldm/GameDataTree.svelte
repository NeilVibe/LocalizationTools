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

  /**
   * Get the primary display label for a node
   */
  function getNodeLabel(node) {
    const attrs = EDITABLE_ATTRS[node.tag];
    if (attrs && attrs.length > 0) {
      const val = node.attributes?.[attrs[0]];
      if (val) return val;
    }
    return node.attributes?.Key || node.attributes?.NodeId || node.attributes?.Name || node.tag;
  }

  /**
   * Build flat list of visible nodes (for keyboard navigation)
   */
  function buildVisibleNodes() {
    if (!treeData) return [];
    const nodes = [];

    function walkFile(fileData) {
      for (const root of fileData.roots || []) {
        walkNode(root);
      }
    }

    function walkNode(node) {
      nodes.push(node);
      if (expandedNodes.has(node.node_id) && node.children?.length > 0) {
        for (const child of node.children) {
          walkNode(child);
        }
      }
    }

    if (Array.isArray(treeData)) {
      for (const fileData of treeData) {
        walkFile(fileData);
      }
    }
    return nodes;
  }

  // ========================================
  // API Integration
  // ========================================

  /**
   * Load tree for a single file
   */
  async function loadFileTree(path) {
    if (!path) return;
    loading = true;
    error = null;

    try {
      logger.apiCall('/api/ldm/gamedata/tree', 'POST');
      const response = await fetch(`${API_BASE}/api/ldm/gamedata/tree`, {
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
      treeData = [data];

      // Auto-expand root level
      const newSet = new Set();
      for (const root of data.roots || []) {
        newSet.add(root.node_id);
      }
      expandedNodes = newSet;
      selectedNodeId = null;

      logger.success('File tree loaded', {
        file: path,
        nodeCount: data.node_count,
        entityType: data.entity_type
      });
    } catch (err) {
      error = err.message;
      treeData = null;
      logger.error('Failed to load file tree', { error: err.message, path });
    } finally {
      loading = false;
    }
  }

  /**
   * Load tree for entire folder
   */
  async function loadFolderTree(path) {
    if (!path) return;
    loading = true;
    error = null;

    try {
      logger.apiCall('/api/ldm/gamedata/tree/folder', 'POST');
      const response = await fetch(`${API_BASE}/api/ldm/gamedata/tree/folder`, {
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
      treeData = data.files || [];

      // Auto-expand file groups
      const newSet = new Set();
      for (const fileData of treeData) {
        newSet.add(`file:${fileData.file_path}`);
      }
      expandedNodes = newSet;
      selectedNodeId = null;

      logger.success('Folder tree loaded', {
        path,
        fileCount: treeData.length,
        totalNodes: data.total_nodes
      });
    } catch (err) {
      error = err.message;
      treeData = null;
      logger.error('Failed to load folder tree', { error: err.message, path });
    } finally {
      loading = false;
    }
  }

  // ========================================
  // Reactive Loading
  // ========================================

  $effect(() => {
    if (filePath) {
      loadFileTree(filePath);
    }
  });

  $effect(() => {
    if (folderPath) {
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
    onNodeSelect(node);
  }

  /**
   * Find parent node for keyboard navigation
   */
  function findParentNode(nodeId) {
    function search(nodes) {
      for (const node of nodes) {
        if (node.children?.some(c => c.node_id === nodeId)) {
          return node;
        }
        if (node.children?.length > 0) {
          const found = search(node.children);
          if (found) return found;
        }
      }
      return null;
    }

    if (!treeData) return null;
    for (const fileData of treeData) {
      const found = search(fileData.roots || []);
      if (found) return found;
    }
    return null;
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
   * Public reload method
   */
  export function reload() {
    if (filePath) loadFileTree(filePath);
    else if (folderPath) loadFolderTree(folderPath);
  }
</script>

<div class="gamedata-tree" role="tree" tabindex="0" onkeydown={handleKeydown}>
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
  <div class="tree-item">
    <button
      class="tree-node"
      class:selected={isSelected}
      class:has-children={hasChildren}
      role="treeitem"
      aria-expanded={hasChildren ? isExpanded : undefined}
      aria-selected={isSelected}
      style="padding-left: {depth * 20 + 8}px"
      onclick={() => selectNode(node)}
      ondblclick={() => { if (hasChildren) toggleExpand(node.node_id); }}
    >
      <!-- Chevron -->
      {#if hasChildren}
        <span
          class="chevron"
          role="button"
          tabindex="-1"
          onclick|stopPropagation={() => toggleExpand(node.node_id)}
        >
          {#if isExpanded}
            <ChevronDown size={14} />
          {:else}
            <ChevronRight size={14} />
          {/if}
        </span>
      {:else}
        <span class="chevron-spacer"></span>
      {/if}

      <!-- Entity type icon -->
      <NodeIcon size={16} class="entity-icon entity-icon-{node.tag.toLowerCase()}" />

      <!-- Tag name -->
      <span class="node-tag">{node.tag}</span>

      <!-- Primary label -->
      {#if label !== node.tag}
        <span class="node-label">{label}</span>
      {/if}

      <!-- Children count badge -->
      {#if hasChildren}
        <span class="count-badge">{node.children.length}</span>
      {/if}
    </button>

    <!-- Children -->
    {#if hasChildren && isExpanded}
      <div class="tree-children" role="group">
        {#each node.children as child (child.node_id)}
          {@render renderNode(child, depth + 1)}
        {/each}
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
    transition: background 0.1s ease, border-color 0.1s ease;
    line-height: 1.4;
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
    border-left-color: var(--cds-link-01);
  }

  /* Chevron */
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

  .chevron-spacer {
    width: 16px;
    flex-shrink: 0;
  }

  /* Entity icon colors */
  :global(.entity-icon) {
    flex-shrink: 0;
  }

  :global(.entity-icon-skillinfo),
  :global(.entity-icon-skilltreeinfo),
  :global(.entity-icon-skillnode) {
    color: #a56eff; /* Purple for skills */
  }

  :global(.entity-icon-iteminfo) {
    color: #0072c3; /* Cyan for items */
  }

  :global(.entity-icon-characterinfo) {
    color: #ee5396; /* Magenta for characters */
  }

  :global(.entity-icon-gimmickgroupinfo),
  :global(.entity-icon-gimmickinfo) {
    color: #ff832b; /* Orange for gimmicks */
  }

  :global(.entity-icon-knowledgeinfo) {
    color: #009d9a; /* Teal for knowledge */
  }

  :global(.entity-icon-questinfo) {
    color: #0f62fe; /* Blue for quests */
  }

  :global(.entity-icon-regioninfo),
  :global(.entity-icon-sceneobjectdata) {
    color: #24a148; /* Green for regions */
  }

  :global(.entity-icon-sealdatainfo) {
    color: #d4bbff; /* Light purple for seals */
  }

  :global(.entity-icon-factiongroup) {
    color: #c9a227; /* Gold for factions */
  }

  :global(.entity-icon-nodewaypointinfo) {
    color: #82cfff; /* Light blue for waypoints */
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

  /* Tree children indentation guide */
  .tree-children {
    /* Indentation handled via padding-left on each node */
  }
</style>
