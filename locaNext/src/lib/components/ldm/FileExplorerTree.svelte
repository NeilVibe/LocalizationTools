<script>
  /**
   * FileExplorerTree.svelte - Phase 18: Game Dev File Explorer
   *
   * VS Code-like recursive folder/file tree browser for gamedata.
   * Expand/collapse folders, select XML files to load into grid.
   * Follows TMExplorerTree patterns (Svelte 5 Runes).
   */
  import { onMount } from 'svelte';
  import {
    ChevronDown,
    ChevronRight,
    Folder,
    FolderOpen,
    Code,
    Renew
  } from 'carbon-icons-svelte';
  import { SkeletonText } from 'carbon-components-svelte';
  import { logger } from '$lib/utils/logger.js';
  import { getAuthHeaders, getApiBase } from '$lib/utils/api.js';

  // Props
  let {
    basePath = '',
    onFileSelect = () => {}
  } = $props();

  const API_BASE = getApiBase();

  // State (Svelte 5 Runes)
  let treeData = $state(null);
  let expandedNodes = $state(new Set());
  let selectedFilePath = $state(null);
  let loading = $state(false);
  let error = $state(null);

  /**
   * Fetch folder tree from backend
   */
  async function loadTree() {
    if (!basePath) return;

    loading = true;
    error = null;

    try {
      logger.apiCall('/api/ldm/gamedata/browse', 'POST');
      const response = await fetch(`${API_BASE}/api/ldm/gamedata/browse`, {
        method: 'POST',
        headers: {
          ...getAuthHeaders(),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ path: basePath })
      });

      if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }));
        throw new Error(err.detail || `HTTP ${response.status}`);
      }

      treeData = await response.json();

      // Auto-expand root level
      if (treeData?.path) {
        const newSet = new Set(expandedNodes);
        newSet.add(treeData.path);
        expandedNodes = newSet;
      }

      logger.success('File explorer tree loaded', {
        folders: treeData?.subfolders?.length || 0,
        files: treeData?.xml_files?.length || 0
      });
    } catch (err) {
      error = err.message;
      logger.error('Failed to load file explorer tree', { error: err.message });
    } finally {
      loading = false;
    }
  }

  /**
   * Toggle folder expand/collapse (TMExplorerTree pattern)
   */
  function toggleNode(folderPath) {
    const newSet = new Set(expandedNodes);
    if (newSet.has(folderPath)) {
      newSet.delete(folderPath);
    } else {
      newSet.add(folderPath);
    }
    expandedNodes = newSet;
  }

  /**
   * Select a file and notify parent
   */
  function selectFile(file) {
    selectedFilePath = file.path;
    onFileSelect({
      name: file.name,
      path: file.path,
      entity_count: file.entity_count
    });
  }

  // Reload when basePath changes
  $effect(() => {
    if (basePath) {
      loadTree();
    }
  });
</script>

<div class="file-explorer-tree">
  {#if loading}
    <div class="loading-state">
      <SkeletonText lines={5} />
    </div>
  {:else if error}
    <div class="error-state">
      <p class="error-message">Failed to load folder</p>
      <p class="error-detail">{error}</p>
      <button class="retry-button" onclick={() => loadTree()}>
        <Renew size={14} />
        Retry
      </button>
    </div>
  {:else if treeData}
    <div class="tree-content">
      {#snippet renderFolder(folder, depth)}
        <div class="tree-item">
          <button
            class="tree-node folder-node"
            style="padding-left: {depth * 16 + 8}px"
            onclick={() => toggleNode(folder.path)}
          >
            {#if expandedNodes.has(folder.path)}
              <ChevronDown size={14} />
              <FolderOpen size={16} class="folder-icon" />
            {:else}
              <ChevronRight size={14} />
              <Folder size={16} class="folder-icon" />
            {/if}
            <span class="node-name">{folder.name}</span>
            {#if (folder.xml_files?.length || 0) > 0}
              <span class="count-badge">{folder.xml_files.length}</span>
            {/if}
          </button>

          {#if expandedNodes.has(folder.path)}
            <div class="tree-children">
              {#each folder.subfolders || [] as subfolder (subfolder.path)}
                {@render renderFolder(subfolder, depth + 1)}
              {/each}
              {#each folder.xml_files || [] as file (file.path)}
                <button
                  class="tree-node file-node"
                  class:selected={selectedFilePath === file.path}
                  style="padding-left: {(depth + 1) * 16 + 8}px"
                  onclick={() => selectFile(file)}
                >
                  <Code size={16} class="file-icon" />
                  <span class="node-name">{file.name}</span>
                  {#if file.entity_count > 0}
                    <span class="entity-badge">{file.entity_count}</span>
                  {/if}
                </button>
              {/each}
              {#if (folder.subfolders?.length || 0) === 0 && (folder.xml_files?.length || 0) === 0}
                <div class="empty-hint" style="padding-left: {(depth + 1) * 16 + 8}px">
                  No XML files found
                </div>
              {/if}
            </div>
          {/if}
        </div>
      {/snippet}

      {@render renderFolder(treeData, 0)}
    </div>
  {:else}
    <div class="empty-state">
      <Folder size={32} />
      <p>Enter a gamedata folder path to browse</p>
    </div>
  {/if}
</div>

<style>
  .file-explorer-tree {
    display: flex;
    flex-direction: column;
    width: 100%;
    height: 100%;
    overflow: hidden;
    background: var(--cds-layer-01);
    font-family: 'IBM Plex Mono', 'Consolas', monospace;
    font-size: 13px;
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

  .tree-node {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    width: 100%;
    padding: 0.375rem 0.5rem;
    background: transparent;
    border: none;
    border-radius: 2px;
    cursor: pointer;
    font-family: inherit;
    font-size: inherit;
    color: var(--cds-text-01);
    text-align: left;
    transition: background 0.1s ease;
    line-height: 1.4;
  }

  .tree-node:hover {
    background: var(--cds-layer-hover-01);
  }

  .folder-node {
    font-weight: 500;
  }

  .file-node.selected {
    background: var(--cds-layer-selected-01);
    outline: 2px solid var(--cds-link-01);
    outline-offset: -2px;
  }

  :global(.folder-icon) {
    flex-shrink: 0;
    color: #c9a227;
  }

  :global(.file-icon) {
    flex-shrink: 0;
    color: var(--cds-link-01);
  }

  .node-name {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .count-badge {
    font-size: 0.6875rem;
    padding: 0.0625rem 0.375rem;
    background: var(--cds-layer-02);
    border-radius: 10px;
    color: var(--cds-text-03);
    flex-shrink: 0;
  }

  .entity-badge {
    font-size: 0.6875rem;
    padding: 0.0625rem 0.375rem;
    background: rgba(15, 98, 254, 0.15);
    border-radius: 10px;
    color: var(--cds-link-01);
    flex-shrink: 0;
  }

  .tree-children {
    /* No extra margin needed -- indentation handled via padding-left */
  }

  .empty-hint {
    font-size: 0.75rem;
    color: var(--cds-text-03);
    font-style: italic;
    padding: 0.375rem 0.5rem;
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
</style>
