<script>
  /**
   * GameDevPage.svelte - Phase 18: Game Dev Grid + File Explorer
   *
   * Split layout: FileExplorerTree (left panel) + GridPage (right).
   * Browse gamedata folders, select XML files, view/edit entities in grid.
   */
  import { gamedevBasePath } from '$lib/stores/navigation.js';
  import { logger } from '$lib/utils/logger.js';
  import { getAuthHeaders, getApiBase } from '$lib/utils/api.js';
  import FileExplorerTree from '$lib/components/ldm/FileExplorerTree.svelte';
  import GameDataTree from '$lib/components/ldm/GameDataTree.svelte';
  import NodeDetailPanel from '$lib/components/ldm/NodeDetailPanel.svelte';
  import { Renew, FolderOpen, ArrowRight, TreeView } from 'carbon-icons-svelte';

  const API_BASE = getApiBase();

  // Check if running in Electron (for native folder picker)
  const isElectron = typeof window !== 'undefined' && window.electron;
  // Check if browser supports File System Access API (Chrome/Edge)
  const hasFileSystemAccess = typeof window !== 'undefined' && 'showDirectoryPicker' in window;

  // State (Svelte 5 Runes)
  let pathInput = $state($gamedevBasePath || '');
  let activePath = $state($gamedevBasePath || '');
  let treeRef = $state(null);

  // Phase 28: Tree view state
  let treeFilePath = $state(null);
  let folderTreePath = $state(null);
  let selectedTreeNode = $state(null);

  // NAV-04: Auto-load indicator state
  let autoLoading = $state(false);

  // DEV mode: auto-load mock gamedata if no path is set
  $effect(() => {
    if (!activePath && !$gamedevBasePath) {
      autoLoading = true;
      // Try to auto-detect mock gamedata via API
      fetch(`${API_BASE}/api/ldm/gamedata/browse`, {
        method: 'POST',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ base_path: '' })
      })
        .then(r => r.ok ? r.json() : null)
        .then(data => {
          if (data?.base_path) {
            pathInput = data.base_path;
            activePath = data.base_path;
            gamedevBasePath.set(data.base_path);
            logger.info('Auto-loaded mock gamedata path', { path: data.base_path });
          }
        })
        .catch(() => { /* silent — user can set path manually */ })
        .finally(() => { autoLoading = false; });
    }
  });

  /**
   * Handle path input submission
   */
  function applyPath() {
    const trimmed = pathInput.trim();
    if (!trimmed) return;
    activePath = trimmed;
    // Store in localStorage via the store
    gamedevBasePath.set(trimmed);
    logger.userAction('Game Dev path set', { path: trimmed });
  }

  /**
   * Open folder picker dialog.
   * Electron: native dialog. Browser: File System Access API. Fallback: apply text input.
   */
  async function browseFolder() {
    // Electron: native folder dialog
    if (isElectron) {
      try {
        const folderPath = await window.electron.selectFolder({
          title: 'Select Gamedata Folder'
        });
        if (!folderPath) {
          logger.info('Folder selection cancelled');
          return;
        }
        pathInput = folderPath;
        activePath = folderPath;
        gamedevBasePath.set(folderPath);
        logger.userAction('Game Dev folder selected via Electron dialog', { path: folderPath });
        return;
      } catch (err) {
        logger.error('Electron folder picker failed', { error: err.message });
      }
    }

    // Browser: File System Access API (Chrome/Edge)
    if (hasFileSystemAccess) {
      try {
        const dirHandle = await window.showDirectoryPicker({ mode: 'read' });
        // Send the directory handle to the backend via a special endpoint
        // that registers the handle and returns a virtual path
        const response = await fetch(`${API_BASE}/api/ldm/gamedata/register-browser-folder`, {
          method: 'POST',
          headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
          body: JSON.stringify({ folder_name: dirHandle.name })
        });
        if (response.ok) {
          const data = await response.json();
          pathInput = data.path || dirHandle.name;
          activePath = pathInput;
          gamedevBasePath.set(pathInput);
          logger.userAction('Game Dev folder selected via browser picker', { path: pathInput });
        } else {
          // Fallback: use the folder name directly
          pathInput = dirHandle.name;
          applyPath();
        }
        return;
      } catch (err) {
        if (err.name === 'AbortError') {
          logger.info('Folder selection cancelled');
          return;
        }
        logger.warning('Browser folder picker failed, falling back to text input', { error: err.message });
      }
    }

    // Fallback: apply whatever is in the text input
    applyPath();
  }

  /**
   * Handle file selection from FileExplorerTree -- load tree view (Phase 28)
   */
  function handleFileSelect(file) {
    treeFilePath = file.path;
    folderTreePath = null;
    selectedTreeNode = null;
    logger.userAction('Game Dev file selected for tree view', { name: file.name, path: file.path });
  }

  /**
   * Phase 28: Load all files in active folder as combined tree
   */
  function loadAllTrees() {
    if (!activePath) return;
    folderTreePath = activePath;
    treeFilePath = null;
    selectedTreeNode = null;
    logger.userAction('Loading all files as tree', { path: activePath });
  }

  /**
   * Phase 28: Handle tree node selection
   */
  function handleNodeSelect(node) {
    selectedTreeNode = node;
    logger.userAction('Tree node selected', { nodeId: node.node_id, tag: node.tag });
  }

  /**
   * Phase 28: Derive active file path for save operations
   * Single file mode: use treeFilePath. Folder mode: extract from treeData context.
   */
  let activeTreeFilePath = $derived(treeFilePath || selectedTreeNode?._filePath || '');

  /**
   * Phase 28: Handle child node click from NodeDetailPanel
   * Sets the child as the selected node (navigates into it)
   */
  function handleChildClick(childNode) {
    selectedTreeNode = childNode;
    logger.userAction('Child node navigated', { nodeId: childNode.node_id, tag: childNode.tag });
  }

  /**
   * Refresh the file explorer tree
   */
  function refreshTree() {
    if (treeRef?.reload) {
      treeRef.reload();
    }
    logger.userAction('Game Dev tree refreshed');
  }

  /**
   * Handle keydown on path input
   */
  function handlePathKeydown(e) {
    if (e.key === 'Enter') {
      applyPath();
    }
  }

</script>

<div class="gamedev-page">
  <!-- Left Panel: File Explorer -->
  <div class="explorer-panel">
    <div class="explorer-header">
      <h3 class="explorer-title">Game Data</h3>
      <div class="explorer-actions">
        <button class="icon-button" onclick={loadAllTrees} title="Load all files as tree" aria-label="Load all files as tree">
          <TreeView size={16} />
        </button>
        <button class="icon-button" onclick={refreshTree} title="Refresh" aria-label="Refresh file tree">
          <Renew size={16} />
        </button>
      </div>
    </div>

    <div class="path-input-row">
      <input
        type="text"
        class="path-input"
        bind:value={pathInput}
        onkeydown={handlePathKeydown}
        placeholder="Enter gamedata folder path..."
      />
      <button class="browse-button" onclick={browseFolder} title="Browse for folder" aria-label="Browse for folder">
        <FolderOpen size={16} />
      </button>
      <button class="browse-button apply-button" onclick={applyPath} title="Apply path" aria-label="Apply path" disabled={!pathInput.trim()}>
        <ArrowRight size={16} />
      </button>
    </div>

    {#if autoLoading}
      <div class="auto-load-indicator">
        <span class="auto-load-dot"></span>
        Loading game data...
      </div>
    {/if}

    <div class="explorer-tree-container">
      {#if activePath}
        <FileExplorerTree
          bind:this={treeRef}
          basePath={activePath}
          onFileSelect={handleFileSelect}
        />
      {:else}
        <div class="explorer-placeholder">
          <p>Enter a gamedata folder path above to browse XML files</p>
        </div>
      {/if}
    </div>
  </div>

  <!-- Resize Handle -->
  <div class="resize-handle"></div>

  <!-- Right Panel: Tree View or Placeholder -->
  <div class="grid-panel">
    {#if treeFilePath || folderTreePath}
      <div class="tree-and-detail">
        <div class="tree-panel-main">
          <GameDataTree
            filePath={treeFilePath}
            folderPath={folderTreePath}
            onNodeSelect={handleNodeSelect}
          />
        </div>
        {#if selectedTreeNode}
          <div class="detail-panel">
            <NodeDetailPanel
              node={selectedTreeNode}
              filePath={activeTreeFilePath}
              onChildClick={handleChildClick}
            />
          </div>
        {/if}
      </div>
    {:else}
      <div class="grid-placeholder">
        <FolderOpen size={48} />
        <p>Select a file from the explorer to view its tree</p>
      </div>
    {/if}
  </div>
</div>

<style>
  .gamedev-page {
    display: flex;
    width: 100%;
    height: 100%;
    overflow: hidden;
    background: var(--cds-background);
  }

  /* Left Panel */
  .explorer-panel {
    display: flex;
    flex-direction: column;
    width: 280px;
    min-width: 200px;
    max-width: 500px;
    border-right: 1px solid var(--cds-border-subtle-01);
    background: var(--cds-layer-01);
    overflow: hidden;
  }

  .explorer-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.5rem 0.75rem;
    border-bottom: 1px solid var(--cds-border-subtle-01);
    flex-shrink: 0;
  }

  .explorer-actions {
    display: flex;
    align-items: center;
    gap: 2px;
  }

  .explorer-title {
    margin: 0;
    font-size: 0.8125rem;
    font-weight: 600;
    color: var(--cds-text-01);
  }

  .icon-button {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 4px;
    background: transparent;
    border: none;
    border-radius: 4px;
    color: var(--cds-icon-01);
    cursor: pointer;
  }

  .icon-button:hover {
    background: var(--cds-layer-hover-01);
  }

  .icon-button:focus {
    outline: 2px solid var(--cds-focus);
    outline-offset: 1px;
  }

  .path-input-row {
    display: flex;
    gap: 4px;
    padding: 0.5rem;
    border-bottom: 1px solid var(--cds-border-subtle-01);
    flex-shrink: 0;
  }

  .path-input {
    flex: 1;
    padding: 0.375rem 0.5rem;
    background: var(--cds-field-01);
    border: 1px solid var(--cds-border-strong-01);
    border-radius: 4px;
    color: var(--cds-text-01);
    font-size: 0.75rem;
    font-family: 'IBM Plex Mono', monospace;
    outline: none;
  }

  .path-input:focus {
    border-color: var(--cds-focus);
    box-shadow: 0 0 0 1px var(--cds-focus);
  }

  .path-input::placeholder {
    color: var(--cds-text-03);
  }

  .browse-button {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0.375rem;
    background: var(--cds-field-01);
    border: 1px solid var(--cds-border-strong-01);
    border-radius: 4px;
    color: var(--cds-icon-01);
    cursor: pointer;
  }

  .browse-button:hover {
    background: var(--cds-layer-hover-01);
  }

  .browse-button:focus {
    outline: 2px solid var(--cds-focus);
    outline-offset: 1px;
  }

  .browse-button:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  .browse-button:disabled:hover {
    background: var(--cds-field-01);
  }

  .apply-button {
    color: var(--cds-link-01);
  }

  .auto-load-indicator {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.375rem 0.75rem;
    font-size: 0.75rem;
    color: var(--cds-text-02);
    border-bottom: 1px solid var(--cds-border-subtle-01);
    flex-shrink: 0;
  }

  .auto-load-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--cds-interactive);
    animation: pulse-dot 1s ease-in-out infinite;
  }

  @keyframes pulse-dot {
    0%, 100% { opacity: 0.4; }
    50% { opacity: 1; }
  }

  .explorer-tree-container {
    flex: 1;
    min-height: 0;
    overflow: hidden;
  }

  .explorer-placeholder {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    padding: 1rem;
    color: var(--cds-text-02);
    font-size: 0.8125rem;
    text-align: center;
  }

  /* Resize Handle */
  .resize-handle {
    width: 4px;
    cursor: col-resize;
    background: transparent;
    flex-shrink: 0;
  }

  .resize-handle:hover {
    background: var(--cds-link-01);
  }

  /* Right Panel */
  .grid-panel {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .grid-placeholder {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    flex: 1;
    gap: 1rem;
    color: var(--cds-text-02);
    font-size: 0.875rem;
  }

  .grid-placeholder p {
    margin: 0;
  }

  /* Phase 28: Tree + Detail layout */
  .tree-and-detail {
    display: flex;
    flex: 1;
    min-height: 0;
    overflow: hidden;
  }

  .tree-panel-main {
    flex: 1;
    min-width: 0;
    overflow: hidden;
  }

  .detail-panel {
    width: 320px;
    min-width: 240px;
    max-width: 500px;
    border-left: 1px solid var(--cds-border-subtle-01);
    overflow-y: auto;
    background: var(--cds-layer-01);
    scrollbar-width: thin;
    scrollbar-color: var(--cds-border-subtle-01) transparent;
  }
</style>
