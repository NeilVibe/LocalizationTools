<script>
  /**
   * GameDataTree.svelte - v3.4: Chrome DevTools-style XML Viewer
   *
   * Renders XML game data as syntax-highlighted inline XML with:
   * - Line numbers + fold gutters + indent guides
   * - One Dark Pro color scheme
   * - Collapsible nodes with animated fold arrows
   * - Cross-reference links (blue, clickable)
   * - Inline editable attribute values (dashed underline)
   * - Collapsed nodes show inline "N children" badge
   * - Keyboard navigation (arrows, enter, space)
   * - Search bar with cascade index
   * - IME-safe Korean text editing
   */
  import {
    ChevronRight,
    ArrowRight
  } from 'carbon-icons-svelte';
  import { SkeletonText } from 'carbon-components-svelte';
  import { EmptyState, ErrorState } from '$lib/components/common';
  import { logger } from '$lib/utils/logger.js';
  import { getAuthHeaders, getApiBase } from '$lib/utils/api.js';
  import AttributeEditModal from './AttributeEditModal.svelte';

  // Props
  let {
    filePath = null,
    folderPath = null,
    onNodeSelect = () => {}
  } = $props();

  const API_BASE = getApiBase();

  // === State ===
  let treeData = $state(null);
  let expandedNodes = $state(new Set());
  let selectedNodeId = $state(null);
  let loading = $state(false);
  let error = $state(null);

  // Index state (Phase 29)
  let indexReady = $state(false);
  let indexing = $state(false);
  let indexStats = $state(null);
  let searchQuery = $state('');
  let searchResults = $state([]);
  let searching = $state(false);
  let searchDebounceTimer = null;

  // Cleanup all timers on component unmount
  $effect(() => {
    return () => {
      clearTimeout(searchDebounceTimer);
      clearTimeout(hoverTimer);
      clearTimeout(copyToastTimer);
    };
  });

  // Flat visible rows for rendering + keyboard nav
  let visibleRows = $derived(buildVisibleRows());

  // Line counter derived from visible rows
  let lineCounter = $derived(visibleRows.length > 0 ? visibleRows[visibleRows.length - 1].line : 0);

  // === Constants ===

  const EDITABLE_ATTRS = {
    ItemInfo: ['ItemName', 'ItemDesc'],
    CharacterInfo: ['CharacterName', 'CharacterDesc'],
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

  /** Entity type icons (emoji for lightweight rendering) */
  const ENTITY_ICONS = {
    SkillTreeInfo: '\u26A1', SkillInfo: '\u26A1', SkillNode: '\u26A1',
    ItemInfo: '\uD83D\uDECD', CharacterInfo: '\uD83D\uDC64',
    GimmickGroupInfo: '\u2699', GimmickInfo: '\u2699',
    KnowledgeInfo: '\uD83D\uDCD6', QuestInfo: '\uD83D\uDCCB',
    RegionInfo: '\uD83C\uDF0E', SceneObjectData: '\uD83C\uDF0E',
    SealDataInfo: '\uD83D\uDD12', FactionGroup: '\uD83D\uDC65',
    NodeWaypointInfo: '\u2B50'
  };

  const ENTITY_COLORS = {
    SkillTreeInfo: '#a855f7', SkillInfo: '#a855f7', SkillNode: '#c084fc',
    ItemInfo: '#06b6d4', CharacterInfo: '#8b5cf6',
    GimmickGroupInfo: '#f59e0b', GimmickInfo: '#fbbf24',
    KnowledgeInfo: '#10b981', QuestInfo: '#f97316',
    RegionInfo: '#14b8a6', SceneObjectData: '#14b8a6',
    SealDataInfo: '#6366f1', FactionGroup: '#ec4899',
    NodeWaypointInfo: '#94a3b8'
  };

  /** Cross-reference attribute names */
  const CROSS_REF_ATTRS = new Set([
    'LearnKnowledgeKey', 'RequireSkillKey', 'LinkedQuestKey', 'RegionKey',
    'ParentNodeId', 'ParentId', 'TargetKey', 'ItemKey', 'CharacterKey',
    'GimmickKey', 'SealKey', 'FactionKey', 'SkillKey', 'KnowledgeKey',
    'RewardKey'
  ]);

  const IDENTITY_ATTRS = new Set(['Key', 'NodeId', 'Id', 'StrKey']);

  /** Semantic attribute categories for color highlighting (WOW-01) */
  const ATTR_CATEGORIES = {
    identity: new Set(['Key', 'StrKey', 'Id', 'StringID', 'NodeId']),
    crossref: CROSS_REF_ATTRS,
    editable: new Set([
      'CharacterName', 'CharacterDesc', 'ItemName', 'ItemDesc',
      'SkillName', 'SkillDesc', 'QuestName', 'QuestDesc',
      'RegionName', 'AliasName', 'Desc', 'Name', 'GimmickName',
      'SealName', 'ObjectName', 'ObjectDesc', 'UIPageName'
    ]),
    stat: new Set([
      'Level', 'HP', 'MP', 'CooldownSec', 'Damage', 'Defense',
      'Weight', 'Price', 'DropRate', 'SpawnRate', 'Radius',
      'MinLevel', 'MaxLevel', 'RequireLevel', 'SkillLevel',
      'AttackPower', 'Speed', 'CritRate', 'Age'
    ]),
    media: new Set([
      'UITextureName', 'VoicePath', 'IconPath', 'TexturePath',
      'SoundPath', 'AnimationPath', 'ModelPath'
    ])
  };

  function classifyAttr(attrName) {
    for (const [category, names] of Object.entries(ATTR_CATEGORIES)) {
      if (names.has(attrName)) return category;
    }
    if (attrName.endsWith('Key') || attrName.endsWith('Id')) return 'crossref';
    return 'default';
  }

  function isCrossRefAttr(attrName) {
    if (CROSS_REF_ATTRS.has(attrName)) return true;
    if ((attrName.endsWith('Key') || attrName.endsWith('Id')) && !IDENTITY_ATTRS.has(attrName)) return true;
    return false;
  }

  function getEntityIcon(tag) { return ENTITY_ICONS[tag] || '\uD83D\uDCC4'; }
  function getEntityColor(tag) { return ENTITY_COLORS[tag] || '#64748b'; }

  // === Node Index (for cross-ref resolution) ===
  let nodeIndex = $state(new Map());

  $effect(() => {
    if (!treeData || treeData.length === 0) { nodeIndex = new Map(); return; }
    const index = new Map();
    function indexNode(node) {
      index.set(node.node_id, node);
      if (node.attributes?.Key) index.set(`key:${node.attributes.Key}`, node);
      if (node.attributes?.NodeId) index.set(`nodeid:${node.attributes.NodeId}`, node);
      if (node.attributes?.Id) index.set(`id:${node.attributes.Id}`, node);
      for (const child of node.children || []) indexNode(child);
    }
    for (const fileTree of treeData) {
      for (const root of fileTree.roots || []) indexNode(root);
    }
    nodeIndex = index;
  });

  function getAncestorIds(node) {
    const ancestors = [];
    let currentId = node.parent_id;
    while (currentId) {
      ancestors.push(currentId);
      const parent = nodeIndex.get(currentId);
      currentId = parent?.parent_id || null;
    }
    return ancestors;
  }

  function resolveCrossRef(attrName, attrValue) {
    if (!attrValue || attrValue === '0' || attrValue === '') return null;
    for (const prefix of ['key:', 'nodeid:', 'id:']) {
      const target = nodeIndex.get(`${prefix}${attrValue}`);
      if (target) return target.node_id;
    }
    return null;
  }

  // === Row Building (flat list for rendering) ===

  /**
   * Row types:
   * - 'open': <Tag attr="val"> with children
   * - 'self-close': <Tag attr="val" />
   * - 'close': </Tag>
   * - 'collapsed': <Tag attr="val">...N children...</Tag>  (inline)
   * - 'comment': <!-- text -->
   * - 'file-header': file group header
   */
  function buildVisibleRows() {
    if (!treeData) return [];
    const rows = [];
    let line = 1;

    function addNodeRows(node, depth) {
      const hasChildren = node.children?.length > 0;
      const isExpanded = expandedNodes.has(node.node_id);

      if (hasChildren && isExpanded) {
        // Opening tag
        rows.push({ type: 'open', node, depth, line: line++ });
        // Children
        for (const child of node.children) {
          addNodeRows(child, depth + 1);
        }
        // Closing tag
        rows.push({ type: 'close', node, depth, line: line++ });
      } else if (hasChildren && !isExpanded) {
        // Collapsed: show inline with child count
        rows.push({ type: 'collapsed', node, depth, line: line++ });
      } else {
        // Self-closing leaf
        rows.push({ type: 'self-close', node, depth, line: line++ });
      }
    }

    if (treeData.length === 1) {
      for (const root of treeData[0].roots || []) {
        addNodeRows(root, 0);
      }
    } else {
      for (const fileData of treeData) {
        const fileKey = `file:${fileData.file_path}`;
        const fileName = fileData.file_path.split('/').pop() || fileData.file_path;
        rows.push({ type: 'file-header', fileKey, fileName, nodeCount: fileData.node_count, line: line++ });

        if (expandedNodes.has(fileKey)) {
          for (const root of fileData.roots || []) {
            addNodeRows(root, 1);
          }
        }
      }
    }

    return rows;
  }

  // === API Integration ===

  async function fetchTree(endpoint, path, onSuccess, logLabel) {
    if (!path) return;
    loading = true;
    error = null;
    try {
      const response = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
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
    } finally {
      loading = false;
    }
  }

  function loadFileTree(path) {
    fetchTree('/api/ldm/gamedata/tree', path, (data) => {
      treeData = [data];
      expandedNodes = new Set((data.roots || []).map(r => r.node_id));
      const dirPath = path.substring(0, path.lastIndexOf('/'));
      if (dirPath) buildIndex(dirPath);
    }, 'file tree');
  }

  function loadFolderTree(path) {
    fetchTree('/api/ldm/gamedata/tree/folder', path, (data) => {
      for (const fileEntry of (data.files || [])) {
        const annotate = (node) => {
          node._filePath = fileEntry.file_path;
          for (const child of (node.children || [])) annotate(child);
        };
        for (const root of (fileEntry.roots || [])) annotate(root);
      }
      treeData = data.files || [];
      expandedNodes = new Set(treeData.map(f => `file:${f.file_path}`));
      buildIndex(path);
    }, 'folder tree');
  }

  $effect(() => {
    if (filePath) loadFileTree(filePath);
    else if (folderPath) loadFolderTree(folderPath);
  });

  // === Node Interaction ===

  function toggleExpand(nodeId) {
    const newSet = new Set(expandedNodes);
    if (newSet.has(nodeId)) newSet.delete(nodeId);
    else newSet.add(nodeId);
    expandedNodes = newSet;
  }

  function selectNode(node) {
    selectedNodeId = node.node_id;
    onNodeSelect?.(node);
  }

  function selectAndRevealNode(targetNodeId) {
    const targetNode = nodeIndex.get(targetNodeId);
    if (!targetNode) return false;
    const ancestors = getAncestorIds(targetNode);
    const newExpanded = new Set(expandedNodes);
    for (const id of ancestors) newExpanded.add(id);
    expandedNodes = newExpanded;
    selectedNodeId = targetNode.node_id;
    onNodeSelect?.(targetNode);
    requestAnimationFrame(() => {
      const el = document.querySelector(`[data-node-id="${targetNode.node_id}"]`);
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    });
    return true;
  }

  export function navigateToNode(nodeId) { return selectAndRevealNode(nodeId); }
  export function reload() {
    if (filePath) loadFileTree(filePath);
    else if (folderPath) loadFolderTree(folderPath);
  }

  // === Keyboard Navigation ===

  function getNodeRows() {
    return visibleRows.filter(r => r.node && (r.type === 'open' || r.type === 'self-close' || r.type === 'collapsed'));
  }

  function handleKeydown(event) {
    const nodeRows = getNodeRows();
    if (!nodeRows.length) return;
    const currentIdx = nodeRows.findIndex(r => r.node.node_id === selectedNodeId);
    const currentRow = currentIdx >= 0 ? nodeRows[currentIdx] : null;

    switch (event.key) {
      case 'ArrowDown': {
        event.preventDefault();
        const next = currentIdx < nodeRows.length - 1 ? currentIdx + 1 : 0;
        selectNode(nodeRows[next].node);
        scrollToNode(nodeRows[next].node.node_id);
        break;
      }
      case 'ArrowUp': {
        event.preventDefault();
        const prev = currentIdx > 0 ? currentIdx - 1 : nodeRows.length - 1;
        selectNode(nodeRows[prev].node);
        scrollToNode(nodeRows[prev].node.node_id);
        break;
      }
      case 'ArrowRight': {
        event.preventDefault();
        if (currentRow?.node?.children?.length > 0 && !expandedNodes.has(currentRow.node.node_id)) {
          toggleExpand(currentRow.node.node_id);
        }
        break;
      }
      case 'ArrowLeft': {
        event.preventDefault();
        if (currentRow?.node && expandedNodes.has(currentRow.node.node_id)) {
          toggleExpand(currentRow.node.node_id);
        } else if (currentRow?.node?.parent_id) {
          const parent = nodeIndex.get(currentRow.node.parent_id);
          if (parent) { selectNode(parent); scrollToNode(parent.node_id); }
        }
        break;
      }
      case 'Enter': {
        event.preventDefault();
        if (currentRow?.node?.children?.length > 0) toggleExpand(currentRow.node.node_id);
        break;
      }
      case ' ': {
        event.preventDefault();
        if (currentRow?.node) selectNode(currentRow.node);
        break;
      }
    }
  }

  function scrollToNode(nodeId) {
    requestAnimationFrame(() => {
      const el = document.querySelector(`[data-node-id="${nodeId}"]`);
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    });
  }

  // === Index / Search (Phase 29) ===

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
      }
    } catch (err) {
      logger.error('Index build failed', { error: err.message });
    } finally {
      indexing = false;
    }
  }

  async function searchEntities(query) {
    if (!query.trim() || !indexReady) { searchResults = []; return; }
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

  function handleSearchInput(event) {
    searchQuery = event.target.value;
    clearTimeout(searchDebounceTimer);
    searchDebounceTimer = setTimeout(() => searchEntities(searchQuery), 300);
  }

  function navigateToResult(result) {
    if (selectAndRevealNode(result.node_id)) {
      searchResults = [];
      searchQuery = '';
      // Add highlight pulse (WOW-04)
      requestAnimationFrame(() => {
        const el = document.querySelector(`[data-node-id="${result.node_id}"]`);
        if (el) {
          el.classList.add('search-highlight-pulse');
          setTimeout(() => el.classList.remove('search-highlight-pulse'), 1000);
        }
      });
    }
  }

  // === Helpers ===

  /** Get the primary display label for a node (for badges) */
  function getNodeLabel(node) {
    const primaryAttr = EDITABLE_ATTRS[node.tag]?.[0];
    const primaryVal = primaryAttr && node.attributes?.[primaryAttr];
    if (primaryVal) return primaryVal;
    return node.attributes?.Key || node.attributes?.NodeId || node.attributes?.Name || null;
  }

  /** Check if a row's node is selected */
  function isRowSelected(row) {
    if (!row.node) return false;
    return row.node.node_id === selectedNodeId;
  }

  /** Line gutter width based on total lines */
  let gutterWidth = $derived(lineCounter > 999 ? 56 : lineCounter > 99 ? 48 : 40);

  // === Attribute Edit Modal ===
  let editModal = $state({ open: false, attrName: '', attrValue: '', filePath: '', entityIndex: 0 });

  function handleAttrDoubleClick(event, node, attrName, attrValue) {
    event.preventDefault();
    event.stopPropagation();
    // Extract entity index from node_id (e.g., "r0" -> 0, "r2" -> 2)
    const match = node.node_id?.match(/r(\d+)/);
    const entityIndex = match ? parseInt(match[1]) : 0;
    // Resolve file path: annotated _filePath (folder mode) or component prop
    const resolvedPath = node._filePath || filePath || '';
    editModal = {
      open: true,
      attrName,
      attrValue: String(attrValue ?? ''),
      filePath: resolvedPath,
      entityIndex
    };
  }

  function handleEditSave(attrName, newValue) {
    editModal = { ...editModal, open: false };
    // Reload tree to reflect saved changes
    if (filePath) loadFileTree(filePath);
    else if (folderPath) loadFolderTree(folderPath);
  }

  // === Context Menu ===
  let contextMenu = $state({ show: false, x: 0, y: 0, node: null });

  function handleContextMenu(event, node) {
    event.preventDefault();
    event.stopPropagation();
    contextMenu = { show: true, x: event.clientX, y: event.clientY, node };
  }

  function closeContextMenu() {
    contextMenu = { show: false, x: 0, y: 0, node: null };
  }

  function handleGlobalClick() {
    if (contextMenu.show) closeContextMenu();
  }

  // === Hover Preview Tooltip (WOW-02) ===
  let previewCache = new Map();
  let hoveredRef = $state(null);
  let hoverTimer = null;
  let tooltipPos = $state({ x: 0, y: 0 });

  function onRefMouseEnter(event, attrValue) {
    clearTimeout(hoverTimer);
    hoverTimer = setTimeout(async () => {
      const cacheKey = attrValue;
      if (!previewCache.has(cacheKey)) {
        try {
          const resp = await fetch(`${API_BASE}/api/ldm/gamedata/index/search`, {
            method: 'POST',
            headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: attrValue, top_k: 1 })
          });
          if (resp.ok) {
            const data = await resp.json();
            if (data.results?.length > 0) {
              previewCache.set(cacheKey, data.results[0]);
              // LRU eviction at 100 entries
              if (previewCache.size > 100) {
                const firstKey = previewCache.keys().next().value;
                previewCache.delete(firstKey);
              }
            }
          }
        } catch (err) {
          logger.error('Preview fetch failed', { error: err.message });
        }
      }
      const result = previewCache.get(cacheKey);
      if (result) {
        hoveredRef = result;
        // Position with viewport edge detection
        const rect = event.target.getBoundingClientRect();
        let x = rect.right + 8;
        let y = rect.top - 4;
        // Flip left if overflowing right
        if (x + 290 > window.innerWidth) x = rect.left - 290;
        // Flip up if overflowing bottom
        if (y + 130 > window.innerHeight) y = window.innerHeight - 140;
        if (y < 8) y = 8;
        tooltipPos = { x, y };
      }
    }, 300);
  }

  function onRefMouseLeave() {
    clearTimeout(hoverTimer);
    hoveredRef = null;
  }

  // === Copy-on-Click (WOW-04) ===
  let copyToast = $state(null);
  let copyToastTimer = null;

  async function copyAttrValue(event, value) {
    // Don't stopPropagation — let the click bubble to selectNode on the xml-row
    try {
      await navigator.clipboard.writeText(value);
      // Create ripple at click position
      const target = event.currentTarget;
      const ripple = document.createElement('span');
      ripple.className = 'copy-ripple';
      const rect = target.getBoundingClientRect();
      ripple.style.left = `${event.clientX - rect.left}px`;
      ripple.style.top = `${event.clientY - rect.top}px`;
      target.style.position = 'relative';
      target.appendChild(ripple);
      setTimeout(() => ripple.remove(), 400);
      // Show toast
      clearTimeout(copyToastTimer);
      copyToast = value.length > 30 ? value.slice(0, 30) + '...' : value;
      copyToastTimer = setTimeout(() => { copyToast = null; }, 1500);
    } catch (err) {
      logger.error('Copy failed', { error: err.message });
    }
  }
</script>

<div class="xml-viewer" role="tree" tabindex="0" onkeydown={handleKeydown} onclick={handleGlobalClick}>
  <!-- Search bar -->
  {#if folderPath || filePath}
    <div class="viewer-search">
      <svg class="search-icon" width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
        <path d="M11.742 10.344a6.5 6.5 0 1 0-1.397 1.398h-.001c.03.04.062.078.098.115l3.85 3.85a1 1 0 0 0 1.415-1.414l-3.85-3.85a1.007 1.007 0 0 0-.115-.1zM12 6.5a5.5 5.5 0 1 1-11 0 5.5 5.5 0 0 1 11 0z"/>
      </svg>
      <input
        type="search"
        class="search-input"
        placeholder={indexReady ? `Search ${indexStats?.entity_count || ''} entities...` : indexing ? 'Indexing...' : 'Search entities...'}
        value={searchQuery}
        oninput={handleSearchInput}
        disabled={!indexReady}
      />
      {#if indexing}
        <span class="search-status">Indexing...</span>
      {:else if indexReady}
        <span class="search-status ready">{indexStats?.entity_count || 0} indexed</span>
      {/if}
      {#if searchResults.length > 0}
        <div class="search-dropdown">
          {#each searchResults as result (result.node_id + result.entity_name)}
            <button class="search-result" onclick={() => navigateToResult(result)}>
              <span class="result-icon">{getEntityIcon(result.tag)}</span>
              <span class="result-name">{result.entity_name}</span>
              <span class="result-tag">{result.tag}</span>
              <span class="result-score">{result.match_type}</span>
            </button>
          {/each}
        </div>
      {/if}
    </div>
  {/if}

  <!-- Content -->
  {#if loading}
    <div class="viewer-loading">
      {#each Array(12) as _, i (i)}
        <div class="skeleton-row" style="padding-left: {(i % 4) * 20 + 66}px;">
          <SkeletonText width="{70 - (i % 4) * 12}%" />
        </div>
      {/each}
    </div>
  {:else if error}
    <ErrorState message={error} onretry={reload} />
  {:else if visibleRows.length > 0}
    <div class="xml-content">
      {#each visibleRows as row (row.type === 'file-header' ? row.fileKey : `${row.node?.node_id}_${row.type}_${row.line}`)}
        {#if row.type === 'file-header'}
          {@render fileHeaderRow(row)}
        {:else if row.type === 'open'}
          {@render openTagRow(row)}
        {:else if row.type === 'self-close'}
          {@render selfCloseRow(row)}
        {:else if row.type === 'collapsed'}
          {@render collapsedRow(row)}
        {:else if row.type === 'close'}
          {@render closeTagRow(row)}
        {/if}
      {/each}
    </div>
  {:else if treeData}
    <EmptyState headline="No data" description="This file contains no XML nodes" />
  {:else}
    <EmptyState headline="No file loaded" description="Select a file from the explorer" />
  {/if}

  <!-- Status bar -->
  {#if treeData}
    <div class="status-bar">
      <span>{lineCounter} lines</span>
      <span class="status-sep">|</span>
      <span>{visibleRows.filter(r => r.node).length} visible</span>
      {#if indexReady}
        <span class="status-sep">|</span>
        <span class="status-ready">Index Ready</span>
      {/if}
    </div>
  {/if}

  {#if contextMenu.show}
    <div
      class="context-menu"
      style="left: {contextMenu.x}px; top: {contextMenu.y}px;"
    >
      <button class="context-item" onclick={() => { navigator.clipboard.writeText(contextMenu.node?.attributes?.Key || contextMenu.node?.node_id || ''); closeContextMenu(); }}>
        Copy Key
      </button>
      <button class="context-item" onclick={() => { navigator.clipboard.writeText(JSON.stringify(contextMenu.node?.attributes || {}, null, 2)); closeContextMenu(); }}>
        Copy All Attributes
      </button>
      <div class="context-divider"></div>
      <button class="context-item" onclick={() => { onNodeSelect?.(contextMenu.node); closeContextMenu(); }}>
        View Details
      </button>
      <button class="context-item" onclick={() => { closeContextMenu(); }}>
        Generate AI Context
      </button>
    </div>
  {/if}

  {#if hoveredRef}
    <div
      class="preview-tooltip"
      style="left: {tooltipPos.x}px; top: {tooltipPos.y}px;"
    >
      <div class="preview-thumb" style="background: {getEntityColor(hoveredRef.tag)}20; color: {getEntityColor(hoveredRef.tag)};">
        {getEntityIcon(hoveredRef.tag)}
      </div>
      <div class="preview-info">
        <div class="preview-key" title={hoveredRef.entity_name || hoveredRef.node_id}>
          {(hoveredRef.entity_name || hoveredRef.node_id || '').slice(0, 28)}{(hoveredRef.entity_name || hoveredRef.node_id || '').length > 28 ? '...' : ''}
        </div>
        <div class="preview-type">
          <span class="preview-type-badge" style="background: {getEntityColor(hoveredRef.tag)}20; color: {getEntityColor(hoveredRef.tag)}; border: 1px solid {getEntityColor(hoveredRef.tag)}40;">
            {hoveredRef.tag}
          </span>
        </div>
        {#if hoveredRef.attributes?.Key}
          <div class="preview-detail">{hoveredRef.attributes.Key}</div>
        {/if}
      </div>
    </div>
  {/if}

  {#if copyToast}
    <div class="copy-toast">
      Copied: {copyToast}
    </div>
  {/if}
</div>

<AttributeEditModal
  bind:open={editModal.open}
  attrName={editModal.attrName}
  attrValue={editModal.attrValue}
  filePath={editModal.filePath}
  entityIndex={editModal.entityIndex}
  onSave={handleEditSave}
  onCancel={() => { editModal.open = false; }}
/>

<!-- ===== SNIPPETS ===== -->

{#snippet fileHeaderRow(row)}
  <div
    class="xml-row file-header-row"
    class:expanded={expandedNodes.has(row.fileKey)}
    style="--entity-color: {getEntityColor('')}"
    onclick={() => toggleExpand(row.fileKey)}
  >
    <span class="line-gutter" style="width: {gutterWidth}px;">{row.line}</span>
    <span class="fold-gutter">
      <span class="fold-arrow" class:expanded={expandedNodes.has(row.fileKey)}>
        <ChevronRight size={12} />
      </span>
    </span>
    <div class="xml-content-inner">
      <span class="file-header-icon">&#128196;</span>
      <span class="file-header-name">{row.fileName}</span>
      <span class="count-badge">{row.nodeCount} nodes</span>
    </div>
  </div>
{/snippet}

{#snippet openTagRow(row)}
  {@const node = row.node}
  {@const color = getEntityColor(node.tag)}
  <div
    class="xml-row"
    class:selected={isRowSelected(row)}
    style="--entity-color: {color}"
    data-node-id={node.node_id}
    onclick={() => selectNode(node)}
    oncontextmenu={(e) => handleContextMenu(e, node)}
  >
    <span class="line-gutter" style="width: {gutterWidth}px;">{row.line}</span>
    <span class="fold-gutter" onclick={(e) => { e.stopPropagation(); toggleExpand(node.node_id); }}>
      <span class="fold-arrow expanded">
        <ChevronRight size={12} />
      </span>
    </span>
    {@render indentGuides(row.depth)}
    <div class="xml-content-inner">
      <span class="t-bracket">&lt;</span><span class="t-tag" style="color: {color};">{node.tag}</span>
      {@render attributeTokens(node)}
      <span class="t-bracket">&gt;</span>
      {#if node.children?.length > 0}
        <span class="entity-badge" style="color: {color};">
          {getEntityIcon(node.tag)} {node.children.length}
        </span>
      {/if}
    </div>
  </div>
{/snippet}

{#snippet selfCloseRow(row)}
  {@const node = row.node}
  {@const color = getEntityColor(node.tag)}
  <div
    class="xml-row"
    class:selected={isRowSelected(row)}
    style="--entity-color: {color}"
    data-node-id={node.node_id}
    onclick={() => selectNode(node)}
    oncontextmenu={(e) => handleContextMenu(e, node)}
  >
    <span class="line-gutter" style="width: {gutterWidth}px;">{row.line}</span>
    <span class="fold-gutter"></span>
    {@render indentGuides(row.depth)}
    <div class="xml-content-inner">
      <span class="t-bracket">&lt;</span><span class="t-tag" style="color: {color};">{node.tag}</span>
      {@render attributeTokens(node)}
      <span class="t-bracket"> /&gt;</span>
    </div>
  </div>
{/snippet}

{#snippet collapsedRow(row)}
  {@const node = row.node}
  {@const color = getEntityColor(node.tag)}
  <div
    class="xml-row"
    class:selected={isRowSelected(row)}
    style="--entity-color: {color}"
    data-node-id={node.node_id}
    onclick={() => selectNode(node)}
    oncontextmenu={(e) => handleContextMenu(e, node)}
  >
    <span class="line-gutter" style="width: {gutterWidth}px;">{row.line}</span>
    <span class="fold-gutter" onclick={(e) => { e.stopPropagation(); toggleExpand(node.node_id); }}>
      <span class="fold-arrow">
        <ChevronRight size={12} />
      </span>
    </span>
    {@render indentGuides(row.depth)}
    <div class="xml-content-inner">
      <span class="t-bracket">&lt;</span><span class="t-tag" style="color: {color};">{node.tag}</span>
      {@render attributeTokens(node)}
      <span class="t-bracket">&gt;</span>
      <span class="collapsed-indicator" onclick={(e) => { e.stopPropagation(); toggleExpand(node.node_id); }}>
        {node.children?.length || 0} {node.children?.length === 1 ? 'child' : 'children'}
      </span>
      <span class="t-bracket">&lt;/</span><span class="t-tag" style="color: {color};">{node.tag}</span><span class="t-bracket">&gt;</span>
    </div>
  </div>
{/snippet}

{#snippet closeTagRow(row)}
  {@const node = row.node}
  {@const color = getEntityColor(node.tag)}
  <div
    class="xml-row close-row"
    class:selected={isRowSelected(row)}
    style="--entity-color: {color}"
  >
    <span class="line-gutter" style="width: {gutterWidth}px;">{row.line}</span>
    <span class="fold-gutter"></span>
    {@render indentGuides(row.depth)}
    <div class="xml-content-inner">
      <span class="t-bracket">&lt;/</span><span class="t-tag" style="color: {color};">{node.tag}</span><span class="t-bracket">&gt;</span>
    </div>
  </div>
{/snippet}

{#snippet indentGuides(depth)}
  {#if depth > 0}
    <div class="indent-area" style="width: {depth * 20}px;">
      {#each Array(depth) as _, i (i)}
        <div class="indent-guide" style="left: {i * 20 + 10}px;"></div>
      {/each}
    </div>
  {/if}
{/snippet}

{#snippet attributeTokens(node)}
  {#each Object.entries(node.attributes || {}) as [attrName, attrValue] (attrName)}
    {@const isXref = isCrossRefAttr(attrName)}
    {@const xrefTarget = isXref ? resolveCrossRef(attrName, String(attrValue)) : null}
    {@const isEditable = (EDITABLE_ATTRS[node.tag] || []).includes(attrName)}
    {@const category = classifyAttr(attrName)}
    {' '}<span class="attr-pair"><span class="t-attr">{attrName}</span><span class="t-bracket">=</span>{#if xrefTarget}<button
        class="t-xref"
        title="Navigate to {attrName}: {attrValue}"
        onclick={(e) => { e.stopPropagation(); selectAndRevealNode(xrefTarget); }}
        ondblclick={(e) => handleAttrDoubleClick(e, node, attrName, attrValue)}
        onmouseenter={(e) => onRefMouseEnter(e, String(attrValue))}
        onmouseleave={onRefMouseLeave}
      >"{attrValue}"</button>{:else if isEditable}<span
        class="t-value editable"
        title="Double-click to edit"
        role="button"
        tabindex="-1"
        ondblclick={(e) => handleAttrDoubleClick(e, node, attrName, attrValue)}
      >"{attrValue}"</span>{:else}<span
        class="t-value attr-val-{category}"
        role="button"
        tabindex="-1"
        onclick={(e) => copyAttrValue(e, String(attrValue))}
        ondblclick={(e) => handleAttrDoubleClick(e, node, attrName, attrValue)}
        onmouseenter={category === 'crossref' ? (e) => onRefMouseEnter(e, String(attrValue)) : undefined}
        onmouseleave={category === 'crossref' ? onRefMouseLeave : undefined}
      >"{attrValue}"</span>{/if}</span>
  {/each}
{/snippet}

<style>
  /* ===== BASE LAYOUT ===== */
  .xml-viewer {
    display: flex;
    flex-direction: column;
    width: 100%;
    height: 100%;
    overflow: hidden;
    background: var(--xml-bg, #1e1e1e);
    font-family: 'D2Coding', 'Noto Sans Mono CJK KR', 'IBM Plex Mono', 'Consolas', monospace;
    font-size: 13px;
    line-height: 1.6;
    --xml-bg: #1e1e1e;
    --xml-bg-hover: #2c313a;
    --xml-bg-selected: #264f78;
    --xml-border: #3c3c3c;
    --xml-border-subtle: #2d2d2d;
    --xml-tag: #e06c75;
    --xml-attr: #d19a66;
    --xml-value: #98c379;
    --xml-bracket: #636d83;
    --xml-comment: #5c6370;
    --xml-text: #abb2bf;
    --xml-text-bright: #d4d4d4;
    --xml-text-dim: #6b7280;
    --xml-link: #61afef;
    --xml-indent-guide: rgba(255,255,255,0.06);
    --xml-indent-guide-active: rgba(255,255,255,0.15);
    color: var(--xml-text);
  }

  .xml-viewer:focus { outline: none; }

  /* ===== SEARCH BAR ===== */
  .viewer-search {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 12px;
    background: #252526;
    border-bottom: 1px solid var(--xml-border);
    flex-shrink: 0;
    position: relative;
  }

  .search-icon { color: var(--xml-text-dim); flex-shrink: 0; }

  .search-input {
    flex: 1;
    background: rgba(255,255,255,0.04);
    border: 1px solid var(--xml-border);
    border-radius: 4px;
    padding: 4px 8px;
    color: var(--xml-text);
    font-family: inherit;
    font-size: 12px;
    outline: none;
  }

  .search-input:focus {
    border-color: #528bff;
    box-shadow: 0 0 0 1px #528bff;
  }

  .search-input:disabled { opacity: 0.4; cursor: not-allowed; }
  .search-input::placeholder { color: var(--xml-text-dim); }

  .search-status {
    font-size: 11px;
    color: var(--xml-text-dim);
    white-space: nowrap;
    flex-shrink: 0;
  }

  .search-status.ready { color: #10b981; }

  .search-dropdown {
    position: absolute;
    left: 12px;
    right: 12px;
    top: 100%;
    max-height: 300px;
    overflow-y: auto;
    z-index: 10;
    background: #252526;
    border: 1px solid var(--xml-border);
    border-radius: 0 0 4px 4px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
  }

  .search-result {
    display: flex;
    align-items: center;
    gap: 8px;
    width: 100%;
    padding: 6px 10px;
    background: transparent;
    border: none;
    border-bottom: 1px solid var(--xml-border-subtle);
    cursor: pointer;
    font-family: inherit;
    font-size: 12px;
    color: var(--xml-text);
    text-align: left;
  }

  .search-result:last-child { border-bottom: none; }
  .search-result:hover { background: var(--xml-bg-hover); }

  .result-icon { flex-shrink: 0; }
  .result-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 500; }
  .result-tag { font-size: 11px; color: var(--xml-text-dim); flex-shrink: 0; }
  .result-score { font-size: 10px; color: var(--xml-text-dim); padding: 1px 4px; background: rgba(255,255,255,0.04); border-radius: 3px; flex-shrink: 0; }

  /* ===== LOADING ===== */
  .viewer-loading { padding: 8px 0; }
  .skeleton-row { padding: 3px 16px; }

  /* ===== XML CONTENT ===== */
  .xml-content {
    flex: 1;
    overflow-y: auto;
    overflow-x: auto;
    padding: 4px 0;
    scrollbar-width: thin;
    scrollbar-color: var(--xml-border) transparent;
  }

  .xml-content::-webkit-scrollbar { width: 8px; height: 8px; }
  .xml-content::-webkit-scrollbar-track { background: transparent; }
  .xml-content::-webkit-scrollbar-thumb { background: var(--xml-border); border-radius: 4px; }

  /* ===== XML ROW ===== */
  .xml-row {
    display: flex;
    align-items: flex-start;
    min-height: 24px;
    padding: 1px 16px 1px 0;
    cursor: pointer;
    position: relative;
    overflow: hidden;
    transition: background 0.15s cubic-bezier(0.34, 1.56, 0.64, 1),
                box-shadow 0.15s ease;
  }

  /* === GAME UI HOVER (Entity-Aware) === */
  .xml-row:hover {
    background: color-mix(in srgb, var(--entity-color, #61afef) 8%, transparent);
    box-shadow: inset 0 0 12px color-mix(in srgb, var(--entity-color, #61afef) 10%, transparent);
  }

  .xml-row.selected {
    background: linear-gradient(
      90deg,
      color-mix(in srgb, var(--entity-color, #61afef) 18%, transparent) 0%,
      color-mix(in srgb, var(--entity-color, #61afef) 8%, transparent) 50%,
      transparent 100%
    );
    box-shadow:
      inset 0 0 0 1px color-mix(in srgb, var(--entity-color, #61afef) 30%, transparent),
      0 0 16px color-mix(in srgb, var(--entity-color, #61afef) 20%, transparent);
  }

  .xml-row.selected::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 3px;
    height: 100%;
    background: var(--entity-color, #61afef);
    box-shadow: 0 0 12px color-mix(in srgb, var(--entity-color, #61afef) 60%, transparent);
  }

  .xml-row:hover .indent-guide { background: var(--xml-indent-guide-active); }

  /* ===== LINE GUTTER ===== */
  .line-gutter {
    min-width: 40px;
    text-align: right;
    padding-right: 10px;
    color: var(--xml-text-dim);
    font-size: 12px;
    user-select: none;
    flex-shrink: 0;
    opacity: 0.5;
  }

  /* ===== FOLD GUTTER ===== */
  .fold-gutter {
    width: 16px;
    min-width: 16px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    color: var(--xml-text-dim);
    user-select: none;
  }

  .fold-gutter:hover {
    color: var(--xml-text-bright);
    background: rgba(255, 255, 255, 0.05);
    border-radius: 3px;
  }

  .fold-arrow {
    display: flex;
    align-items: center;
    justify-content: center;
    transition: transform 0.15s ease;
    cursor: pointer;
  }

  .fold-arrow.expanded { transform: rotate(90deg); }

  /* ===== INDENT GUIDES ===== */
  .indent-area {
    position: relative;
    flex-shrink: 0;
    align-self: stretch;
  }

  .indent-guide {
    position: absolute;
    top: 0;
    bottom: 0;
    width: 1px;
    background: var(--xml-indent-guide);
    transition: background 0.1s ease;
  }

  /* ===== XML CONTENT INNER ===== */
  .xml-content-inner {
    flex: 1;
    white-space: pre-wrap;
    word-break: break-all;
    overflow-wrap: break-word;
    min-width: 0;
    padding: 0 4px;
  }

  /* ===== SYNTAX TOKENS ===== */
  .t-bracket { color: #808080; }
  .t-tag { color: var(--xml-tag); font-weight: 500; }
  .t-attr { color: var(--xml-attr); }

  .t-value { color: var(--xml-value); }

  .t-value.editable {
    cursor: text;
    border-bottom: 1px dashed rgba(152, 195, 121, 0.3);
    padding: 0 1px;
    border-radius: 2px;
  }

  .t-value.editable:hover {
    background: rgba(152, 195, 121, 0.1);
    border-bottom-color: var(--xml-value);
  }

  /* Semantic attribute value colors (WOW-01) */
  .attr-val-identity   { color: #e5c07b; font-weight: 600; border-bottom: 1px solid rgba(229, 192, 123, 0.25); }
  .attr-val-crossref   { color: #61afef; text-decoration: underline; cursor: pointer;
                         transition: text-shadow 0.15s ease; }
  .attr-val-crossref:hover { text-shadow: 0 0 6px rgba(97,175,239,0.4); }
  .attr-val-stat       { color: #56b6c2; font-family: 'JetBrains Mono', 'D2Coding', monospace;
                         font-variant-numeric: tabular-nums; }
  .attr-val-media      { color: #c678dd; font-style: italic; }
  .attr-val-default    { color: #e06c75; }

  .t-xref {
    color: var(--xml-link);
    cursor: pointer;
    background: none;
    border: none;
    border-bottom: 1px dotted var(--xml-link);
    font-family: inherit;
    font-size: inherit;
    padding: 0;
    line-height: inherit;
  }

  .t-xref:hover {
    text-decoration: underline;
    color: #8cc4f0;
  }

  /* ===== BADGES ===== */
  .entity-badge {
    display: inline-flex;
    align-items: center;
    gap: 3px;
    font-size: 10px;
    padding: 0 5px;
    margin-left: 8px;
    border-radius: 3px;
    background: rgba(255,255,255,0.06);
    font-weight: 400;
    vertical-align: middle;
  }

  .count-badge {
    font-size: 10px;
    padding: 1px 6px;
    background: rgba(255,255,255,0.06);
    border-radius: 10px;
    color: var(--xml-text-dim);
    margin-left: 6px;
  }

  .collapsed-indicator {
    display: inline-block;
    padding: 0 6px;
    margin: 0 3px;
    background: rgba(255,255,255,0.06);
    border-radius: 3px;
    color: var(--xml-text-dim);
    font-size: 11px;
    cursor: pointer;
    border: 1px solid var(--xml-border-subtle);
    transition: all 0.1s ease;
  }

  .collapsed-indicator:hover {
    background: rgba(255,255,255,0.1);
    color: var(--xml-text);
    border-color: var(--xml-border);
  }

  /* ===== FILE HEADER ===== */
  .file-header-row {
    background: #252526;
    border-bottom: 1px solid var(--xml-border-subtle);
    margin-bottom: 2px;
  }

  .file-header-row:hover { background: var(--xml-bg-hover); }

  .file-header-icon { margin-right: 4px; }

  .file-header-name {
    font-weight: 600;
    color: var(--xml-text-bright);
  }

  /* ===== CLOSE ROW ===== */
  .close-row { opacity: 0.7; }

  /* ===== STATUS BAR ===== */
  .status-bar {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 2px 12px;
    background: #252526;
    border-top: 1px solid var(--xml-border);
    font-size: 11px;
    color: var(--xml-text-dim);
    flex-shrink: 0;
    height: 22px;
  }

  .status-sep { color: var(--xml-border); }
  .status-ready { color: #10b981; }

  /* ===== SELECTED ROW ===== */

  /* ===== ACTIVE INDENT GUIDES ON SELECTED ROW ===== */
  .xml-row.selected .indent-guide {
    background: rgba(255,255,255,0.2);
  }

  /* ===== ANIMATIONS ===== */
  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(-2px); }
    to { opacity: 1; transform: translateY(0); }
  }

  /* Removed: rowFadeIn, selectPulse, selectedAccentPulse — CSS animations
     replay on every Svelte re-render causing flash/stutter. Use CSS transitions
     for smooth state changes instead. */

  /* ===== CONTEXT MENU ===== */
  .context-menu {
    position: fixed;
    z-index: 1000;
    min-width: 180px;
    background: #21252b;
    border: 1px solid rgba(212, 154, 92, 0.2);
    border-radius: 8px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5), 0 0 16px rgba(212, 154, 92, 0.1);
    padding: 4px 0;
    animation: fadeSlideIn 0.15s ease-out;
  }
  .context-item {
    display: block;
    width: 100%;
    padding: 8px 14px;
    background: transparent;
    border: none;
    text-align: left;
    color: #abb2bf;
    font-size: 12px;
    font-family: 'IBM Plex Sans', sans-serif;
    cursor: pointer;
    transition: background 0.1s ease;
  }
  .context-item:hover {
    background: rgba(212, 154, 92, 0.1);
    color: #d4d4d4;
  }
  .context-divider {
    height: 1px;
    background: #3c3c3c;
    margin: 4px 0;
  }
  @keyframes fadeSlideIn {
    from { opacity: 0; transform: translateY(-4px); }
    to { opacity: 1; transform: translateY(0); }
  }

  /* === Copy Ripple (WOW-04) === */
  :global(.copy-ripple) {
    position: absolute;
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background: rgba(152, 195, 121, 0.3);
    animation: rippleExpand 0.4s ease-out;
    pointer-events: none;
    transform: translate(-50%, -50%);
  }

  @keyframes rippleExpand {
    from { transform: translate(-50%, -50%) scale(0); opacity: 1; }
    to   { transform: translate(-50%, -50%) scale(4); opacity: 0; }
  }

  /* === Copy Toast === */
  .copy-toast {
    position: absolute;
    bottom: 40px;
    left: 50%;
    transform: translateX(-50%);
    background: #1e1e2e;
    color: #98c379;
    border: 1px solid #3c3c4c;
    padding: 6px 14px;
    border-radius: 6px;
    font-size: 12px;
    z-index: 50;
    animation: toastSlideIn 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    pointer-events: none;
    white-space: nowrap;
    max-width: 300px;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  @keyframes toastSlideIn {
    from { opacity: 0; transform: translateX(-50%) translateY(8px); }
    to   { opacity: 1; transform: translateX(-50%) translateY(0); }
  }

  /* === Search Highlight Pulse (WOW-04) === */
  .search-highlight-pulse {
    animation: highlightPulse 1s ease-out;
  }

  @keyframes highlightPulse {
    0%   { background-color: rgba(97, 175, 239, 0.3); }
    50%  { background-color: rgba(97, 175, 239, 0.1); }
    100% { background-color: transparent; }
  }

  /* === Hover Preview Tooltip (WOW-02) === */
  .preview-tooltip {
    position: fixed;
    z-index: 100;
    display: flex;
    gap: 10px;
    align-items: flex-start;
    width: 280px;
    padding: 10px 12px;
    background: #1e1e2e;
    border: 1px solid #3c3c4c;
    border-radius: 8px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.4);
    animation: tooltipFadeIn 0.15s cubic-bezier(0.4, 0, 0.2, 1);
    pointer-events: none;
  }

  @keyframes tooltipFadeIn {
    from { opacity: 0; transform: translateY(4px); }
    to   { opacity: 1; transform: translateY(0); }
  }

  .preview-thumb {
    width: 44px;
    height: 44px;
    border-radius: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
    flex-shrink: 0;
  }

  .preview-info {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 3px;
  }

  .preview-key {
    font-size: 12px;
    font-weight: 600;
    color: #d4d4d4;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .preview-type { display: flex; align-items: center; gap: 6px; }

  .preview-type-badge {
    font-size: 10px;
    padding: 1px 6px;
    border-radius: 4px;
    white-space: nowrap;
  }

  .preview-detail {
    font-size: 11px;
    color: #8b8b9b;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  /* === ATTRIBUTE PAIR HOVER === */
  .attr-pair {
    position: relative;
    padding: 0 1px;
    border-radius: 3px;
    transition: background-color 0.12s ease;
  }

  .attr-pair:hover {
    background: rgba(209, 154, 102, 0.1);
  }

  .attr-pair:hover .t-attr {
    color: #e8b85f;
    font-weight: 600;
    transition: color 0.1s ease;
  }

  .attr-pair:hover .t-bracket {
    color: #8b8b9b;
  }

  .attr-pair:hover :global(.attr-val-crossref) {
    color: #8cc4f0;
    text-shadow: 0 0 8px rgba(97, 175, 239, 0.5);
    text-decoration-style: wavy;
  }

  .attr-pair:hover :global(.attr-val-identity) {
    color: #ffd666;
    font-weight: 700;
  }

  .attr-pair:hover :global(.attr-val-media) {
    color: #d9a0f0;
  }

  .attr-pair:hover :global(.attr-val-stat) {
    color: #7ce8f0;
  }

  /* === REDUCED MOTION === */
  @media (prefers-reduced-motion: reduce) {
    .xml-row.selected::after { animation: none; }
    .xml-row { transition-duration: 0.01s; }
  }
</style>
