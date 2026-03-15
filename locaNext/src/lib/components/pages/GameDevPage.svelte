<script>
  /**
   * GameDevPage.svelte - Phase 18: Game Dev Grid + File Explorer
   *
   * Split layout: FileExplorerTree (left panel) + GridPage (right).
   * Browse gamedata folders, select XML files, view/edit entities in grid.
   */
  import { openFile, openFileInGrid, gamedevBasePath } from '$lib/stores/navigation.js';
  import { logger } from '$lib/utils/logger.js';
  import { getAuthHeaders, getApiBase } from '$lib/utils/api.js';
  import FileExplorerTree from '$lib/components/ldm/FileExplorerTree.svelte';
  import VirtualGrid from '$lib/components/ldm/VirtualGrid.svelte';
  import NamingPanel from '$lib/components/ldm/NamingPanel.svelte';
  import { Button, TextInput } from 'carbon-components-svelte';
  import { Renew, FolderOpen } from 'carbon-icons-svelte';

  const API_BASE = getApiBase();

  // State (Svelte 5 Runes)
  let selectedGameDevFile = $state(null);
  let pathInput = $state($gamedevBasePath || '');
  let activePath = $state($gamedevBasePath || '');
  let dynamicColumns = $state(null);
  let fileLoading = $state(false);
  let virtualGrid = $state(null);

  // Naming panel state (Phase 21)
  let editingEntityName = $state('');
  let editingEntityType = $state('');

  // Derive file type for VirtualGrid
  let currentFileId = $derived($openFile?.id || null);
  let currentFileName = $derived($openFile?.name || '');

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
   * Handle file selection from FileExplorerTree
   */
  async function handleFileSelect(file) {
    selectedGameDevFile = file;
    fileLoading = true;
    dynamicColumns = null;

    try {
      // Step 1: Upload/parse the XML file via existing upload mechanism
      const formData = new FormData();
      // Create a reference to the server-side file path
      formData.append('server_path', file.path);
      formData.append('file_type', 'gamedev');

      logger.apiCall('/api/ldm/files/upload-path', 'POST');
      const uploadResponse = await fetch(`${API_BASE}/api/ldm/files/upload-path`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: formData
      });

      let fileData;
      if (uploadResponse.ok) {
        fileData = await uploadResponse.json();
      } else {
        // Fallback: try the standard upload endpoint with server_path
        logger.warning('upload-path failed, trying standard file object approach');
        // Create a minimal file object for navigation
        fileData = {
          id: null,
          name: file.name,
          path: file.path,
          format: 'xml',
          file_type: 'gamedev'
        };
      }

      // Step 2: Fetch dynamic columns
      try {
        const colResponse = await fetch(`${API_BASE}/api/ldm/gamedata/columns`, {
          method: 'POST',
          headers: {
            ...getAuthHeaders(),
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ xml_path: file.path })
        });

        if (colResponse.ok) {
          const colData = await colResponse.json();
          if (colData.columns && colData.columns.length > 0) {
            // Convert ColumnHint list to gameDevColumns-compatible object
            const cols = {
              row_num: { key: "row_num", label: "#", width: 60, prefKey: "showIndex" },
              node_name: { key: "source", label: "Node", width: 200, always: true }
            };
            for (const hint of colData.columns) {
              cols[hint.key] = {
                key: hint.key,
                label: hint.label,
                width: hint.editable ? 250 : 150,
                always: true
              };
            }
            cols.children_count = { key: "children_count", label: "Children", width: 100, always: true };
            dynamicColumns = cols;
            logger.success('Dynamic columns loaded', { count: colData.columns.length });
          }
        } else {
          logger.warning('Dynamic columns fetch failed, using defaults');
        }
      } catch (err) {
        logger.warning('Dynamic columns unavailable', { error: err.message });
      }

      // Step 3: Set the file in the openFile store so VirtualGrid loads it
      const gridFile = {
        id: fileData.id || Date.now(), // Use timestamp as fallback ID
        name: file.name,
        path: file.path,
        format: 'xml',
        file_type: 'gamedev',
        entity_count: file.entity_count
      };
      openFile.set(gridFile);

      logger.success('Game Dev file selected', { name: file.name, entity_count: file.entity_count });
    } catch (err) {
      logger.error('Failed to load game dev file', { error: err.message });
    } finally {
      fileLoading = false;
    }
  }

  /**
   * Refresh the file explorer tree
   */
  function refreshTree() {
    // Force re-render by toggling path
    const current = activePath;
    activePath = '';
    setTimeout(() => { activePath = current; }, 50);
  }

  /**
   * Handle keydown on path input
   */
  function handlePathKeydown(e) {
    if (e.key === 'Enter') {
      applyPath();
    }
  }

  /**
   * Phase 21: Handle inline edit start from VirtualGrid -- show naming panel
   * Only triggers when user actually starts editing a cell (double-click/Enter),
   * not on simple row selection.
   */
  function handleInlineEditStart(data) {
    const { row, column, value } = data || {};
    if (!row || !value) {
      editingEntityName = '';
      return;
    }

    editingEntityName = value;

    // Derive entity type from XML node name
    const nodeName = (row.source || '').toLowerCase();
    if (nodeName.includes('character')) editingEntityType = 'character';
    else if (nodeName.includes('item')) editingEntityType = 'item';
    else if (nodeName.includes('skill')) editingEntityType = 'skill';
    else if (nodeName.includes('gimmick')) editingEntityType = 'gimmick';
    else if (nodeName.includes('faction') || nodeName.includes('region')) editingEntityType = 'region';
    else editingEntityType = 'character'; // safe default

    logger.userAction('Inline edit started for naming panel', { name: value, column, entityType: editingEntityType });
  }

  /**
   * Phase 21: Apply naming suggestion -- copy to clipboard (respects AINAME-03)
   */
  async function handleNamingApply(name) {
    try {
      await navigator.clipboard.writeText(name);
      logger.userAction('Naming suggestion copied to clipboard', { name });
    } catch {
      logger.warning('Clipboard copy failed for naming suggestion', { name });
    }
  }
</script>

<div class="gamedev-page">
  <!-- Left Panel: File Explorer -->
  <div class="explorer-panel">
    <div class="explorer-header">
      <h3 class="explorer-title">Game Data</h3>
      <button class="icon-button" onclick={refreshTree} title="Refresh">
        <Renew size={16} />
      </button>
    </div>

    <div class="path-input-row">
      <input
        type="text"
        class="path-input"
        bind:value={pathInput}
        onkeydown={handlePathKeydown}
        placeholder="Enter gamedata folder path..."
      />
      <button class="browse-button" onclick={applyPath} title="Browse">
        <FolderOpen size={16} />
      </button>
    </div>

    <div class="explorer-tree-container">
      {#if activePath}
        <FileExplorerTree
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

  <!-- Right Panel: Grid or Placeholder -->
  <div class="grid-panel">
    {#if fileLoading}
      <div class="grid-placeholder">
        <p>Loading file...</p>
      </div>
    {:else if selectedGameDevFile && currentFileId}
      <VirtualGrid
        bind:this={virtualGrid}
        fileId={currentFileId}
        fileName={currentFileName}
        fileType="gamedev"
        gamedevDynamicColumns={dynamicColumns}
        onInlineEditStart={handleInlineEditStart}
      />
      {#if editingEntityName}
        <NamingPanel
          editingName={editingEntityName}
          entityType={editingEntityType}
          onApply={handleNamingApply}
        />
      {/if}
    {:else}
      <div class="grid-placeholder">
        <FolderOpen size={48} />
        <p>Select a file from the explorer to view entities</p>
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
</style>
