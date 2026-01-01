<script>
  /**
   * TMExplorerTree.svelte - TM Hierarchy System (Sprint 3)
   *
   * Hierarchical tree view for Translation Memories.
   * Mirrors File Explorer structure: Platform > Project > Folder
   *
   * Features:
   * - "Unassigned" section for orphaned TMs
   * - Activation toggle (green = active)
   * - Drag-drop TM reassignment
   * - Context menu (Activate, Move, Delete)
   */
  import { createEventDispatcher, onMount } from 'svelte';
  import {
    ChevronDown,
    ChevronRight,
    DataBase,
    Folder,
    FolderOpen,
    Application,
    CheckmarkFilled,
    RadioButton,
    Archive
  } from 'carbon-icons-svelte';
  import { logger } from '$lib/utils/logger.js';
  import { getAuthHeaders, getApiBase } from '$lib/utils/api.js';

  // Props
  let {
    selectedTMId = $bindable(null),
    onTMSelect = null,
    onViewEntries = null
  } = $props();

  const dispatch = createEventDispatcher();
  const API_BASE = getApiBase();

  // State
  let treeData = $state({ unassigned: [], platforms: [] });
  let loading = $state(false);
  let expandedNodes = $state(new Set(['unassigned'])); // Track expanded nodes

  // Context menu state
  let contextMenu = $state({ show: false, x: 0, y: 0, tm: null, scope: null });

  // Drag state
  let draggedTM = $state(null);
  let dropTargetId = $state(null);
  let dropTargetType = $state(null);

  // ========================================
  // Data Loading
  // ========================================

  async function loadTree() {
    loading = true;
    try {
      logger.apiCall('/api/ldm/tm-tree', 'GET');
      const response = await fetch(`${API_BASE}/api/ldm/tm-tree`, {
        headers: getAuthHeaders()
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      treeData = await response.json();
      logger.success('TM tree loaded', {
        unassigned: treeData.unassigned?.length || 0,
        platforms: treeData.platforms?.length || 0
      });
    } catch (err) {
      logger.error('Failed to load TM tree', { error: err.message });
      treeData = { unassigned: [], platforms: [] };
    } finally {
      loading = false;
    }
  }

  // ========================================
  // TM Operations
  // ========================================

  async function activateTM(tm, active = true) {
    try {
      logger.apiCall(`/api/ldm/tm/${tm.tm_id}/activate`, 'PATCH');
      const response = await fetch(`${API_BASE}/api/ldm/tm/${tm.tm_id}/activate?active=${active}`, {
        method: 'PATCH',
        headers: getAuthHeaders()
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      logger.success(`TM ${active ? 'activated' : 'deactivated'}`, { tmId: tm.tm_id });
      await loadTree(); // Reload to show updated state
    } catch (err) {
      logger.error('Failed to toggle TM activation', { error: err.message });
    }
  }

  async function assignTM(tmId, scope) {
    try {
      let url = `${API_BASE}/api/ldm/tm/${tmId}/assign?`;
      if (scope.type === 'platform') {
        url += `platform_id=${scope.id}`;
      } else if (scope.type === 'project') {
        url += `project_id=${scope.id}`;
      } else if (scope.type === 'folder') {
        url += `folder_id=${scope.id}`;
      }
      // If no scope type, assign to unassigned (no params)

      logger.apiCall(url, 'PATCH');
      const response = await fetch(url, {
        method: 'PATCH',
        headers: getAuthHeaders()
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      logger.success('TM assigned', { tmId, scope });
      await loadTree();
    } catch (err) {
      logger.error('Failed to assign TM', { error: err.message });
    }
  }

  // ========================================
  // Node Expansion
  // ========================================

  function toggleNode(nodeId) {
    const newSet = new Set(expandedNodes);
    if (newSet.has(nodeId)) {
      newSet.delete(nodeId);
    } else {
      newSet.add(nodeId);
    }
    expandedNodes = newSet;
  }

  function isExpanded(nodeId) {
    return expandedNodes.has(nodeId);
  }

  // ========================================
  // Selection & Events
  // ========================================

  function selectTM(tm) {
    selectedTMId = tm.tm_id;
    dispatch('select', { tm });
    if (onTMSelect) onTMSelect(tm);
  }

  function handleDoubleClick(tm) {
    dispatch('viewEntries', { tm });
    if (onViewEntries) onViewEntries(tm);
  }

  // ========================================
  // Context Menu
  // ========================================

  function openContextMenu(event, tm, scope) {
    event.preventDefault();
    event.stopPropagation();
    contextMenu = {
      show: true,
      x: event.clientX,
      y: event.clientY,
      tm,
      scope
    };
  }

  function closeContextMenu() {
    contextMenu = { show: false, x: 0, y: 0, tm: null, scope: null };
  }

  function handleGlobalClick(event) {
    if (contextMenu.show && !event.target.closest('.context-menu')) {
      closeContextMenu();
    }
  }

  // ========================================
  // Drag and Drop
  // ========================================

  function handleDragStart(event, tm) {
    draggedTM = tm;
    event.dataTransfer.effectAllowed = 'move';
    event.dataTransfer.setData('text/plain', JSON.stringify(tm));
  }

  function handleDragEnd() {
    draggedTM = null;
    dropTargetId = null;
    dropTargetType = null;
  }

  function handleDragOver(event, targetId, targetType) {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
    dropTargetId = targetId;
    dropTargetType = targetType;
  }

  function handleDragLeave() {
    dropTargetId = null;
    dropTargetType = null;
  }

  function handleDrop(event, targetId, targetType) {
    event.preventDefault();
    if (draggedTM) {
      assignTM(draggedTM.tm_id, { type: targetType, id: targetId });
    }
    draggedTM = null;
    dropTargetId = null;
    dropTargetType = null;
  }

  function handleActivationClick(event, tm) {
    event.stopPropagation();
    activateTM(tm, !tm.is_active);
  }

  // ========================================
  // Lifecycle
  // ========================================

  onMount(() => {
    loadTree();
    document.addEventListener('click', handleGlobalClick);
    return () => document.removeEventListener('click', handleGlobalClick);
  });

  // Expose refresh method
  export function refresh() {
    loadTree();
  }
</script>

<div class="tm-explorer-tree">
  {#if loading}
    <div class="loading-state">Loading...</div>
  {:else}
    <div class="tree-content">
      <!-- Unassigned Section -->
      <div
        class="tree-section"
        class:drop-target={dropTargetId === 'unassigned'}
        ondragover={(e) => handleDragOver(e, 'unassigned', 'unassigned')}
        ondragleave={handleDragLeave}
        ondrop={(e) => handleDrop(e, null, 'unassigned')}
      >
        <button class="tree-header" onclick={() => toggleNode('unassigned')}>
          {#if isExpanded('unassigned')}
            <ChevronDown size={16} />
          {:else}
            <ChevronRight size={16} />
          {/if}
          <Archive size={18} class="section-icon unassigned-icon" />
          <span class="section-name">Unassigned</span>
          <span class="section-count">{treeData.unassigned?.length || 0}</span>
        </button>

        {#if isExpanded('unassigned')}
          <div class="tree-children">
            {#each treeData.unassigned || [] as tm (tm.tm_id)}
              <button
                class="tm-item"
                class:selected={selectedTMId === tm.tm_id}
                class:active={tm.is_active}
                draggable="true"
                onclick={() => selectTM(tm)}
                ondblclick={() => handleDoubleClick(tm)}
                oncontextmenu={(e) => openContextMenu(e, tm, 'unassigned')}
                ondragstart={(e) => handleDragStart(e, tm)}
                ondragend={handleDragEnd}
              >
                {#if tm.is_active}
                  <CheckmarkFilled size={16} class="tm-icon active" />
                {:else}
                  <DataBase size={16} class="tm-icon" />
                {/if}
                <span class="tm-name">{tm.tm_name}</span>
              </button>
            {/each}
            {#if (treeData.unassigned?.length || 0) === 0}
              <div class="empty-hint">No unassigned TMs</div>
            {/if}
          </div>
        {/if}
      </div>

      <!-- Platforms -->
      {#each treeData.platforms || [] as platform (platform.id)}
        <div
          class="tree-section"
          class:drop-target={dropTargetId === `platform-${platform.id}`}
          ondragover={(e) => handleDragOver(e, `platform-${platform.id}`, 'platform')}
          ondragleave={handleDragLeave}
          ondrop={(e) => handleDrop(e, platform.id, 'platform')}
        >
          <button class="tree-header platform" onclick={() => toggleNode(`platform-${platform.id}`)}>
            {#if isExpanded(`platform-${platform.id}`)}
              <ChevronDown size={16} />
            {:else}
              <ChevronRight size={16} />
            {/if}
            <Application size={18} class="section-icon platform-icon" />
            <span class="section-name">{platform.name}</span>
            {#if platform.tms?.length > 0}
              <span class="section-count tm-count">{platform.tms.length} TM</span>
            {/if}
          </button>

          {#if isExpanded(`platform-${platform.id}`)}
            <div class="tree-children">
              <!-- Platform-level TMs -->
              {#each platform.tms || [] as tm (tm.tm_id)}
                <div
                  class="tm-item"
                  class:selected={selectedTMId === tm.tm_id}
                  class:active={tm.is_active}
                  draggable="true"
                  role="button"
                  tabindex="0"
                  onclick={() => selectTM(tm)}
                  ondblclick={() => handleDoubleClick(tm)}
                  oncontextmenu={(e) => openContextMenu(e, tm, { type: 'platform', id: platform.id })}
                  ondragstart={(e) => handleDragStart(e, tm)}
                  ondragend={handleDragEnd}
                  onkeydown={(e) => e.key === 'Enter' && selectTM(tm)}
                >
                  <button
                    class="activation-toggle"
                    onclick={(e) => handleActivationClick(e, tm)}
                    title={tm.is_active ? 'Deactivate TM' : 'Activate TM'}
                  >
                    {#if tm.is_active}
                      <CheckmarkFilled size={16} class="tm-icon active" />
                    {:else}
                      <RadioButton size={16} class="tm-icon inactive" />
                    {/if}
                  </button>
                  <span class="tm-name">{tm.tm_name}</span>
                </div>
              {/each}

              <!-- Projects under platform -->
              {#each platform.projects || [] as project (project.id)}
                <div
                  class="tree-subsection"
                  class:drop-target={dropTargetId === `project-${project.id}`}
                  ondragover={(e) => handleDragOver(e, `project-${project.id}`, 'project')}
                  ondragleave={handleDragLeave}
                  ondrop={(e) => handleDrop(e, project.id, 'project')}
                >
                  <button class="tree-header project" onclick={() => toggleNode(`project-${project.id}`)}>
                    {#if isExpanded(`project-${project.id}`)}
                      <ChevronDown size={16} />
                      <FolderOpen size={18} class="section-icon project-icon" />
                    {:else}
                      <ChevronRight size={16} />
                      <Folder size={18} class="section-icon project-icon" />
                    {/if}
                    <span class="section-name">{project.name}</span>
                    {#if project.tms?.length > 0}
                      <span class="section-count tm-count">{project.tms.length} TM</span>
                    {/if}
                  </button>

                  {#if isExpanded(`project-${project.id}`)}
                    <div class="tree-children">
                      <!-- Project-level TMs -->
                      {#each project.tms || [] as tm (tm.tm_id)}
                        <div
                          class="tm-item"
                          class:selected={selectedTMId === tm.tm_id}
                          class:active={tm.is_active}
                          draggable="true"
                          role="button"
                          tabindex="0"
                          onclick={() => selectTM(tm)}
                          ondblclick={() => handleDoubleClick(tm)}
                          oncontextmenu={(e) => openContextMenu(e, tm, { type: 'project', id: project.id })}
                          ondragstart={(e) => handleDragStart(e, tm)}
                          ondragend={handleDragEnd}
                          onkeydown={(e) => e.key === 'Enter' && selectTM(tm)}
                        >
                          <button
                            class="activation-toggle"
                            onclick={(e) => handleActivationClick(e, tm)}
                            title={tm.is_active ? 'Deactivate TM' : 'Activate TM'}
                          >
                            {#if tm.is_active}
                              <CheckmarkFilled size={16} class="tm-icon active" />
                            {:else}
                              <RadioButton size={16} class="tm-icon inactive" />
                            {/if}
                          </button>
                          <span class="tm-name">{tm.tm_name}</span>
                        </div>
                      {/each}

                      <!-- Folders under project -->
                      {#each project.folders || [] as folder (folder.id)}
                        <div
                          class="tree-subsection"
                          class:drop-target={dropTargetId === `folder-${folder.id}`}
                          ondragover={(e) => handleDragOver(e, `folder-${folder.id}`, 'folder')}
                          ondragleave={handleDragLeave}
                          ondrop={(e) => handleDrop(e, folder.id, 'folder')}
                        >
                          <button class="tree-header folder" onclick={() => toggleNode(`folder-${folder.id}`)}>
                            {#if isExpanded(`folder-${folder.id}`)}
                              <ChevronDown size={16} />
                              <FolderOpen size={18} class="section-icon folder-icon" />
                            {:else}
                              <ChevronRight size={16} />
                              <Folder size={18} class="section-icon folder-icon" />
                            {/if}
                            <span class="section-name">{folder.name}</span>
                            {#if folder.tms?.length > 0}
                              <span class="section-count tm-count">{folder.tms.length} TM</span>
                            {/if}
                          </button>

                          {#if isExpanded(`folder-${folder.id}`)}
                            <div class="tree-children">
                              <!-- Folder-level TMs -->
                              {#each folder.tms || [] as tm (tm.tm_id)}
                                <div
                                  class="tm-item"
                                  class:selected={selectedTMId === tm.tm_id}
                                  class:active={tm.is_active}
                                  draggable="true"
                                  role="button"
                                  tabindex="0"
                                  onclick={() => selectTM(tm)}
                                  ondblclick={() => handleDoubleClick(tm)}
                                  oncontextmenu={(e) => openContextMenu(e, tm, { type: 'folder', id: folder.id })}
                                  ondragstart={(e) => handleDragStart(e, tm)}
                                  ondragend={handleDragEnd}
                                  onkeydown={(e) => e.key === 'Enter' && selectTM(tm)}
                                >
                                  <button
                                    class="activation-toggle"
                                    onclick={(e) => handleActivationClick(e, tm)}
                                    title={tm.is_active ? 'Deactivate TM' : 'Activate TM'}
                                  >
                                    {#if tm.is_active}
                                      <CheckmarkFilled size={16} class="tm-icon active" />
                                    {:else}
                                      <RadioButton size={16} class="tm-icon inactive" />
                                    {/if}
                                  </button>
                                  <span class="tm-name">{tm.tm_name}</span>
                                </div>
                              {/each}
                            </div>
                          {/if}
                        </div>
                      {/each}
                    </div>
                  {/if}
                </div>
              {/each}
            </div>
          {/if}
        </div>
      {/each}

      {#if (treeData.platforms?.length || 0) === 0 && (treeData.unassigned?.length || 0) === 0}
        <div class="empty-state">
          <DataBase size={32} />
          <p>No Translation Memories</p>
          <span>Upload a TM to get started</span>
        </div>
      {/if}
    </div>
  {/if}
</div>

<!-- Context Menu -->
{#if contextMenu.show}
  <div
    class="context-menu"
    style="left: {contextMenu.x}px; top: {contextMenu.y}px;"
    role="menu"
  >
    <button class="context-menu-item" onclick={() => { handleDoubleClick(contextMenu.tm); closeContextMenu(); }}>
      View Entries
    </button>
    {#if contextMenu.tm?.is_active}
      <button class="context-menu-item" onclick={() => { activateTM(contextMenu.tm, false); closeContextMenu(); }}>
        Deactivate
      </button>
    {:else}
      <button class="context-menu-item" onclick={() => { activateTM(contextMenu.tm, true); closeContextMenu(); }}>
        Activate
      </button>
    {/if}
    <div class="context-menu-divider"></div>
    <button class="context-menu-item" onclick={() => { assignTM(contextMenu.tm.tm_id, {}); closeContextMenu(); }}>
      Move to Unassigned
    </button>
  </div>
{/if}

<style>
  .tm-explorer-tree {
    display: flex;
    flex-direction: column;
    width: 100%;
    height: 100%;
    overflow: hidden;
    background: var(--cds-background);
  }

  .loading-state {
    display: flex;
    align-items: center;
    justify-content: center;
    flex: 1;
    color: var(--cds-text-02);
  }

  .tree-content {
    flex: 1;
    overflow-y: auto;
    padding: 0.5rem 0;
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
    margin: 0.5rem 0 0.25rem;
    font-size: 0.875rem;
    color: var(--cds-text-01);
  }

  .empty-hint {
    padding: 0.5rem 1rem 0.5rem 2.5rem;
    font-size: 0.75rem;
    color: var(--cds-text-03);
    font-style: italic;
  }

  /* Tree Section */
  .tree-section {
    margin-bottom: 0.25rem;
  }

  .tree-subsection {
    margin-left: 1rem;
  }

  /* Tree Header (collapsible nodes) */
  .tree-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    width: 100%;
    padding: 0.5rem 0.75rem;
    background: transparent;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-family: inherit;
    font-size: 0.875rem;
    color: var(--cds-text-01);
    text-align: left;
  }

  .tree-header:hover {
    background: var(--cds-layer-hover-01);
  }

  .tree-header.platform {
    font-weight: 600;
  }

  .tree-header.project {
    font-weight: 500;
  }

  .section-name {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .section-count {
    font-size: 0.75rem;
    color: var(--cds-text-03);
    padding: 0.125rem 0.5rem;
    background: var(--cds-layer-02);
    border-radius: 10px;
  }

  .section-count.tm-count {
    color: var(--cds-support-success);
    background: rgba(36, 161, 72, 0.15);
  }

  /* Section Icons */
  :global(.section-icon) {
    flex-shrink: 0;
  }

  :global(.unassigned-icon) {
    color: var(--cds-text-03);
  }

  :global(.platform-icon) {
    color: #0f62fe; /* Blue for platforms */
  }

  :global(.project-icon) {
    color: #5a9a6e; /* Green for projects */
  }

  :global(.folder-icon) {
    color: #c9a227; /* Amber for folders */
  }

  /* Tree Children */
  .tree-children {
    margin-left: 0.5rem;
    border-left: 1px solid var(--cds-border-subtle-01);
    padding-left: 0.5rem;
  }

  /* TM Item */
  .tm-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    width: 100%;
    padding: 0.375rem 0.75rem;
    margin: 1px 0;
    background: transparent;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-family: inherit;
    font-size: 0.8125rem;
    color: var(--cds-text-01);
    text-align: left;
    transition: background 0.1s ease;
  }

  .tm-item:hover {
    background: var(--cds-layer-hover-01);
  }

  .tm-item.selected {
    background: var(--cds-layer-selected-01);
  }

  .tm-item.active {
    background: rgba(36, 161, 72, 0.08);
  }

  .tm-item.active:hover {
    background: rgba(36, 161, 72, 0.15);
  }

  .tm-name {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  /* Activation Toggle */
  .activation-toggle {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 2px;
    background: transparent;
    border: none;
    cursor: pointer;
    border-radius: 50%;
  }

  .activation-toggle:hover {
    background: var(--cds-layer-hover-02);
  }

  /* TM Icons */
  :global(.tm-icon) {
    flex-shrink: 0;
    color: var(--cds-icon-secondary);
  }

  :global(.tm-icon.active) {
    color: var(--cds-support-success);
  }

  :global(.tm-icon.inactive) {
    color: var(--cds-text-03);
  }

  /* Drop Target */
  .drop-target {
    background: rgba(15, 98, 254, 0.1) !important;
    outline: 2px dashed var(--cds-link-01);
    outline-offset: -2px;
    border-radius: 4px;
  }

  /* Context Menu */
  .context-menu {
    position: fixed;
    z-index: 9999;
    min-width: 160px;
    background: var(--cds-layer-01);
    border: 1px solid var(--cds-border-subtle-01);
    border-radius: 4px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
    overflow: hidden;
  }

  .context-menu-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    width: 100%;
    padding: 0.75rem 1rem;
    background: transparent;
    border: none;
    color: var(--cds-text-01);
    font-size: 0.875rem;
    cursor: pointer;
    text-align: left;
  }

  .context-menu-item:hover {
    background: var(--cds-layer-hover-01);
  }

  .context-menu-divider {
    height: 1px;
    background: var(--cds-border-subtle-01);
    margin: 0.25rem 0;
  }
</style>
