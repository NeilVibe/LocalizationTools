<script>
  /**
   * FilePickerDialog - Browse and select files from projects
   *
   * Purpose: Hierarchical file browser for selecting files
   * Part of UI-096: Reference file picker overhaul
   */
  import {
    Modal,
    Select,
    SelectItem,
    InlineLoading,
    Tag
  } from "carbon-components-svelte";
  import { Folder, Document, ChevronRight } from "carbon-icons-svelte";
  import { createEventDispatcher } from "svelte";
  import { logger } from "$lib/utils/logger.js";
  import { getAuthHeaders, getApiBase } from "$lib/utils/api.js";

  const dispatch = createEventDispatcher();
  const API_BASE = getApiBase();

  // Props
  let {
    open = $bindable(false),
    title = "Select File",
    selectedFileId = null
  } = $props();

  // State
  let projects = $state([]);
  let selectedProjectId = $state(null);
  let treeNodes = $state([]);
  let loading = $state(false);
  let projectLoading = $state(false);
  let selectedFile = $state(null);
  let expandedFolders = $state(new Set());

  // Load projects
  async function loadProjects() {
    projectLoading = true;
    try {
      const response = await fetch(`${API_BASE}/api/ldm/projects`, {
        headers: getAuthHeaders()
      });
      if (response.ok) {
        projects = await response.json();
        logger.info("FilePickerDialog: loaded projects", { count: projects.length });
      }
    } catch (err) {
      logger.error("FilePickerDialog: failed to load projects", { error: err.message });
    } finally {
      projectLoading = false;
    }
  }

  // Load project tree
  async function loadProjectTree(projectId) {
    if (!projectId) {
      treeNodes = [];
      return;
    }
    loading = true;
    try {
      const response = await fetch(`${API_BASE}/api/ldm/projects/${projectId}/tree`, {
        headers: getAuthHeaders()
      });
      if (response.ok) {
        const data = await response.json();
        treeNodes = buildTreeNodes(data.tree || []);
        // Auto-expand first level
        expandedIds = treeNodes
          .filter(n => n.children && n.children.length > 0)
          .map(n => n.id);
        logger.info("FilePickerDialog: loaded tree", { projectId, nodes: treeNodes.length });
      }
    } catch (err) {
      logger.error("FilePickerDialog: failed to load tree", { error: err.message });
    } finally {
      loading = false;
    }
  }

  // Build tree nodes from API response
  function buildTreeNodes(items) {
    return items.map(item => {
      const node = {
        id: item.id,
        text: item.name,
        type: item.type,
        icon: item.type === 'folder' ? Folder : Document,
        data: item
      };
      if (item.type === 'folder' && item.children) {
        node.children = buildTreeNodes(item.children);
      }
      return node;
    });
  }

  // Handle project selection
  function handleProjectChange(e) {
    const projectId = e.target.value ? parseInt(e.target.value) : null;
    selectedProjectId = projectId;
    selectedFile = null;
    expandedFolders = new Set();
    if (projectId) {
      loadProjectTree(projectId);
    } else {
      treeNodes = [];
    }
  }

  // Handle node click
  function handleNodeClick(node) {
    if (node.type === 'file') {
      selectedFile = {
        id: node.data.id,
        name: node.data.name,
        row_count: node.data.row_count || 0,
        format: node.data.format || 'xlsx'
      };
      logger.info("FilePickerDialog: file selected", { file: selectedFile });
    } else if (node.type === 'folder') {
      // Toggle folder expansion
      const newExpanded = new Set(expandedFolders);
      if (newExpanded.has(node.id)) {
        newExpanded.delete(node.id);
      } else {
        newExpanded.add(node.id);
      }
      expandedFolders = newExpanded;
    }
  }

  // Confirm selection
  function confirmSelection() {
    if (selectedFile) {
      dispatch('select', selectedFile);
      open = false;
    }
  }

  // Cancel
  function handleClose() {
    open = false;
    dispatch('close');
  }

  // Initialize when opened
  $effect(() => {
    if (open) {
      loadProjects();
      // Reset state
      selectedFile = null;
      treeNodes = [];
      expandedFolders = new Set();
    }
  });

  // Find and highlight pre-selected file when tree loads
  $effect(() => {
    if (selectedFileId && treeNodes.length > 0) {
      function findNode(nodes) {
        for (const node of nodes) {
          if (node.type === 'file' && node.id === selectedFileId) {
            return node;
          }
          if (node.children) {
            const found = findNode(node.children);
            if (found) return found;
          }
        }
        return null;
      }
      const found = findNode(treeNodes);
      if (found) {
        selectedFile = {
          id: found.data.id,
          name: found.data.name,
          row_count: found.data.row_count || 0,
          format: found.data.format || 'xlsx'
        };
      }
    }
  });
</script>

<Modal
  bind:open
  modalHeading={title}
  primaryButtonText="Select"
  primaryButtonDisabled={!selectedFile}
  secondaryButtonText="Cancel"
  on:click:button--primary={confirmSelection}
  on:click:button--secondary={handleClose}
  on:close={handleClose}
  size="sm"
>
  <div class="file-picker">
    <!-- Project Selector -->
    <div class="project-selector">
      {#if projectLoading}
        <InlineLoading description="Loading projects..." />
      {:else}
        <Select
          labelText="Project"
          selected={selectedProjectId || ''}
          on:change={handleProjectChange}
          size="sm"
        >
          <SelectItem value="" text="-- Select Project --" disabled />
          {#each projects as project}
            <SelectItem value={project.id} text={project.name} />
          {/each}
        </Select>
      {/if}
    </div>

    <!-- File Tree -->
    <div class="tree-container">
      {#if loading}
        <div class="loading-state">
          <InlineLoading description="Loading files..." />
        </div>
      {:else if treeNodes.length === 0}
        <div class="empty-state">
          {#if selectedProjectId}
            <p>No files in this project.</p>
          {:else}
            <p>Select a project to browse files.</p>
          {/if}
        </div>
      {:else}
        <!-- Custom tree rendering -->
        {#snippet renderNode(node, depth = 0)}
          {@const NodeIcon = node.icon}
          <div
            class="tree-node"
            class:selected={node.type === 'file' && selectedFile?.id === node.id}
            class:folder={node.type === 'folder'}
            style="padding-left: {depth * 16 + 8}px;"
            onclick={() => handleNodeClick(node)}
            role="button"
            tabindex="0"
          >
            {#if node.type === 'folder'}
              <span class="folder-chevron" class:expanded={expandedFolders.has(node.id)}>
                <ChevronRight size={14} />
              </span>
            {/if}
            <NodeIcon size={16} />
            <span class="node-text">{node.text}</span>
            {#if node.type === 'file' && node.data.row_count}
              <span class="row-count">({node.data.row_count})</span>
            {/if}
          </div>
          {#if node.type === 'folder' && node.children && expandedFolders.has(node.id)}
            {#each node.children as child}
              {@render renderNode(child, depth + 1)}
            {/each}
          {/if}
        {/snippet}

        <div class="custom-tree">
          {#each treeNodes as node}
            {@render renderNode(node, 0)}
          {/each}
        </div>
      {/if}
    </div>

    <!-- Selected File Info -->
    {#if selectedFile}
      <div class="selected-info">
        <Document size={16} />
        <span class="file-name">{selectedFile.name}</span>
        <Tag type="gray" size="sm">{selectedFile.row_count} rows</Tag>
      </div>
    {/if}
  </div>
</Modal>

<style>
  .file-picker {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    min-height: 300px;
  }

  .project-selector {
    flex-shrink: 0;
  }

  .tree-container {
    flex: 1;
    min-height: 200px;
    max-height: 300px;
    overflow-y: auto;
    border: 1px solid var(--cds-border-subtle-01);
    border-radius: 4px;
    background: var(--cds-layer-01);
  }

  .loading-state,
  .empty-state {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    min-height: 100px;
    color: var(--cds-text-02);
    font-size: 0.875rem;
  }

  .empty-state p {
    margin: 0;
  }

  .selected-info {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.75rem;
    background: var(--cds-layer-02);
    border-radius: 4px;
    border-left: 3px solid var(--cds-interactive-01);
  }

  .file-name {
    flex: 1;
    font-weight: 500;
    color: var(--cds-text-01);
  }

  /* Custom tree styling */
  .custom-tree {
    padding: 0.5rem 0;
  }

  .tree-node {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.375rem 0.5rem;
    cursor: pointer;
    border-radius: 2px;
    color: var(--cds-text-01);
    transition: background 0.1s;
  }

  .tree-node:hover {
    background: var(--cds-layer-hover-01);
  }

  .tree-node.selected {
    background: var(--cds-selected-ui);
  }

  .tree-node.folder {
    color: var(--cds-text-02);
  }

  .folder-chevron {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 14px;
    transition: transform 0.15s;
  }

  .folder-chevron.expanded {
    transform: rotate(90deg);
  }

  .node-text {
    flex: 1;
    font-size: 0.875rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .row-count {
    font-size: 0.75rem;
    color: var(--cds-text-02);
  }
</style>
