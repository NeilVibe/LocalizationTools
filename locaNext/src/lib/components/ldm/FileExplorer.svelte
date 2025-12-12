<script>
  import {
    TreeView,
    Button,
    Modal,
    TextInput,
    FileUploader,
    InlineLoading,
    ProgressBar,
    InlineNotification,
    Select,
    SelectItem,
    TextArea
  } from "carbon-components-svelte";
  import { Folder, Document, Add, TrashCan, Upload, FolderAdd, Download, Search, TextCreation, DataBase } from "carbon-icons-svelte";
  import { createEventDispatcher, onMount, onDestroy } from "svelte";
  import { logger } from "$lib/utils/logger.js";

  const dispatch = createEventDispatcher();

  // API base URL
  const API_BASE = 'http://localhost:8888';

  // Props
  export let projects = [];
  export let selectedProjectId = null;
  export let selectedFileId = null;

  // State
  let loading = false;
  let projectTree = null;
  let treeNodes = [];

  // Modal states
  let showNewProjectModal = false;
  let showNewFolderModal = false;
  let showUploadModal = false;
  let newProjectName = "";
  let newFolderName = "";
  let selectedFolderId = null;
  let uploadFiles = [];
  let uploadProgress = 0;
  let uploadStatus = ""; // '', 'uploading', 'success', 'error'

  // Context menu state
  let showContextMenu = false;
  let contextMenuX = 0;
  let contextMenuY = 0;
  let contextMenuFile = null; // {id, name, type, format}

  // TM Registration modal state
  let showTMModal = false;
  let tmName = "";
  let tmProjectId = null;
  let tmLanguage = "en";
  let tmDescription = "";

  // Helper to get auth headers
  function getAuthHeaders() {
    const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
    return token ? { 'Authorization': `Bearer ${token}` } : {};
  }

  // Load projects list
  export async function loadProjects() {
    loading = true;
    try {
      const response = await fetch(`${API_BASE}/api/ldm/projects`, {
        headers: getAuthHeaders()
      });
      if (response.ok) {
        projects = await response.json();
        logger.info("Loaded projects", { count: projects.length });
      }
    } catch (err) {
      logger.error("Failed to load projects", { error: err.message });
    } finally {
      loading = false;
    }
  }

  // Load project tree
  async function loadProjectTree(projectId) {
    if (!projectId) return;
    loading = true;
    try {
      const response = await fetch(`${API_BASE}/api/ldm/projects/${projectId}/tree`, {
        headers: getAuthHeaders()
      });
      if (response.ok) {
        projectTree = await response.json();
        treeNodes = buildTreeNodes(projectTree.tree);
        logger.info("Loaded project tree", { projectId, nodes: treeNodes.length });
      }
    } catch (err) {
      logger.error("Failed to load project tree", { error: err.message });
    } finally {
      loading = false;
    }
  }

  // Build tree nodes for TreeView
  function buildTreeNodes(items, level = 0) {
    return items.map(item => {
      const node = {
        id: `${item.type}-${item.id}`,
        text: item.name,
        icon: item.type === 'folder' ? Folder : Document,
        data: item
      };
      if (item.type === 'folder' && item.children) {
        node.children = buildTreeNodes(item.children, level + 1);
      }
      return node;
    });
  }

  // Create new project
  async function createProject() {
    if (!newProjectName.trim()) return;
    try {
      const response = await fetch(`${API_BASE}/api/ldm/projects`, {
        method: 'POST',
        headers: {
          ...getAuthHeaders(),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ name: newProjectName })
      });
      if (response.ok) {
        const project = await response.json();
        logger.success("Project created", { id: project.id, name: project.name });
        await loadProjects();
        selectProject(project.id);
        showNewProjectModal = false;
        newProjectName = "";
      }
    } catch (err) {
      logger.error("Failed to create project", { error: err.message });
    }
  }

  // Create new folder
  async function createFolder() {
    if (!newFolderName.trim() || !selectedProjectId) return;
    try {
      const response = await fetch(`${API_BASE}/api/ldm/folders`, {
        method: 'POST',
        headers: {
          ...getAuthHeaders(),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          project_id: selectedProjectId,
          parent_id: selectedFolderId,
          name: newFolderName
        })
      });
      if (response.ok) {
        logger.success("Folder created", { name: newFolderName });
        await loadProjectTree(selectedProjectId);
        showNewFolderModal = false;
        newFolderName = "";
      }
    } catch (err) {
      logger.error("Failed to create folder", { error: err.message });
    }
  }

  // Upload file with progress feedback
  async function uploadFile() {
    if (!uploadFiles.length || !selectedProjectId) return;

    uploadStatus = "uploading";
    uploadProgress = 0;
    const totalFiles = uploadFiles.length;
    let completed = 0;
    let hasErrors = false;

    try {
      for (const file of uploadFiles) {
        const formData = new FormData();
        formData.append('project_id', selectedProjectId);
        if (selectedFolderId) {
          formData.append('folder_id', selectedFolderId);
        }
        formData.append('file', file);

        const response = await fetch(`${API_BASE}/api/ldm/files/upload`, {
          method: 'POST',
          headers: getAuthHeaders(),
          body: formData
        });

        completed++;
        uploadProgress = Math.round((completed / totalFiles) * 100);

        if (response.ok) {
          const result = await response.json();
          logger.success("File uploaded", { name: file.name, rows: result.row_count });
        } else {
          hasErrors = true;
          const error = await response.json();
          logger.error("Upload failed", { name: file.name, error: error.detail });
        }
      }

      await loadProjectTree(selectedProjectId);
      uploadStatus = hasErrors ? "error" : "success";

      // Auto-close modal after success
      setTimeout(() => {
        showUploadModal = false;
        uploadFiles = [];
        uploadStatus = "";
        uploadProgress = 0;
      }, 1500);

    } catch (err) {
      uploadStatus = "error";
      logger.error("Upload error", { error: err.message });
    }
  }

  // Select project
  function selectProject(projectId) {
    selectedProjectId = projectId;
    selectedFileId = null;
    selectedFolderId = null;
    loadProjectTree(projectId);
    dispatch('projectSelect', { projectId });
  }

  // Handle tree node selection (Carbon TreeView - deprecated)
  function handleNodeSelect(event) {
    const node = event.detail;

    // Carbon TreeView passes: {id: "file-1", text: "name.txt", leaf: true, ...}
    // Our node IDs are formatted as "{type}-{id}"
    if (!node || !node.id) {
      logger.warning("TreeView select: no node id", { node: JSON.stringify(node) });
      return;
    }

    // Parse our custom ID format: "file-{id}" or "folder-{id}"
    const idParts = node.id.split('-');
    if (idParts.length < 2) {
      logger.warning("TreeView select: invalid node id format", { id: node.id });
      return;
    }

    const nodeType = idParts[0];  // 'file' or 'folder'
    const nodeId = parseInt(idParts[1], 10);

    if (nodeType === 'file') {
      selectedFileId = nodeId;
      selectedFolderId = null;
      dispatch('fileSelect', { fileId: nodeId, file: { id: nodeId, name: node.text, type: 'file' } });
      logger.info("File selected", { fileId: nodeId, name: node.text });
    } else if (nodeType === 'folder') {
      selectedFolderId = nodeId;
      selectedFileId = null;
      logger.info("Folder selected", { folderId: nodeId, name: node.text });
    }
  }

  // Handle custom tree node click
  function handleNodeClick(node) {
    const data = node.data;
    if (data.type === 'file') {
      selectedFileId = data.id;
      selectedFolderId = null;
      dispatch('fileSelect', { fileId: data.id, file: data });
      logger.info("File selected", { fileId: data.id, name: data.name });
    } else if (data.type === 'folder') {
      selectedFolderId = data.id;
      selectedFileId = null;
      logger.info("Folder selected", { folderId: data.id, name: data.name });
    }
  }

  // Watch for project selection changes
  $: if (selectedProjectId) {
    loadProjectTree(selectedProjectId);
  }

  // ============== Context Menu Functions ==============

  // Show context menu on right-click
  function handleContextMenu(event, file) {
    event.preventDefault();
    event.stopPropagation();

    // Only show for files, not folders
    if (file.type !== 'file') return;

    contextMenuFile = file;
    contextMenuX = event.clientX;
    contextMenuY = event.clientY;
    showContextMenu = true;

    logger.info("Context menu opened", { file: file.name });
  }

  // Close context menu
  function closeContextMenu() {
    showContextMenu = false;
    contextMenuFile = null;
  }

  // Handle click outside to close menu
  function handleClickOutside(event) {
    if (showContextMenu) {
      closeContextMenu();
    }
  }

  // Download file
  async function downloadFile() {
    if (!contextMenuFile) return;
    closeContextMenu();

    try {
      const response = await fetch(`${API_BASE}/api/ldm/files/${contextMenuFile.id}/download`, {
        headers: getAuthHeaders()
      });

      if (response.ok) {
        const blob = await response.blob();
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = contextMenuFile.name || 'download';
        if (contentDisposition) {
          const match = contentDisposition.match(/filename="(.+)"/);
          if (match) filename = match[1];
        }

        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();

        logger.success("File downloaded", { name: filename });
      } else {
        logger.error("Download failed", { status: response.status });
      }
    } catch (err) {
      logger.error("Download error", { error: err.message });
    }
  }

  // Run Line Check QA
  async function runLineCheckQA() {
    if (!contextMenuFile) return;
    closeContextMenu();

    logger.info("Line Check QA started", { file: contextMenuFile.name });
    // TODO: Implement full line check QA
    // This will dispatch an event or open a modal to show progress
    dispatch('runQA', { fileId: contextMenuFile.id, type: 'line', fileName: contextMenuFile.name });
  }

  // Run Word Check QA
  async function runWordCheckQA() {
    if (!contextMenuFile) return;
    closeContextMenu();

    logger.info("Word Check QA started", { file: contextMenuFile.name });
    // TODO: Implement full word check QA
    dispatch('runQA', { fileId: contextMenuFile.id, type: 'word', fileName: contextMenuFile.name });
  }

  // Open TM Registration modal
  function openTMRegistration() {
    if (!contextMenuFile) return;
    closeContextMenu();

    // Pre-fill TM name from file name
    tmName = contextMenuFile.name.replace(/\.[^.]+$/, '') + "_TM";
    tmProjectId = selectedProjectId;
    tmLanguage = "en";
    tmDescription = "";
    showTMModal = true;

    logger.info("TM Registration opened", { file: contextMenuFile.name });
  }

  // Register file as TM
  async function registerAsTM() {
    if (!contextMenuFile || !tmName.trim()) return;

    try {
      const response = await fetch(`${API_BASE}/api/ldm/files/${contextMenuFile.id}/register-as-tm`, {
        method: 'POST',
        headers: {
          ...getAuthHeaders(),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          name: tmName,
          project_id: tmProjectId,
          language: tmLanguage,
          description: tmDescription
        })
      });

      if (response.ok) {
        const result = await response.json();
        logger.success("TM registered", { name: tmName, tmId: result.tm_id });
        showTMModal = false;

        // Dispatch event for Tasks panel to show progress
        dispatch('tmRegistered', {
          tmId: result.tm_id,
          name: tmName,
          fileId: contextMenuFile.id,
          fileName: contextMenuFile.name
        });
      } else {
        const error = await response.json();
        logger.error("TM registration failed", { error: error.detail });
      }
    } catch (err) {
      logger.error("TM registration error", { error: err.message });
    }
  }

  // Auto-load projects on mount
  onMount(async () => {
    logger.info("FileExplorer mounted, loading projects...");
    await loadProjects();

    // Add global click listener to close context menu
    document.addEventListener('click', handleClickOutside);
  });

  onDestroy(() => {
    document.removeEventListener('click', handleClickOutside);
  });
</script>

<div class="file-explorer">
  <div class="explorer-header">
    <h4>Projects</h4>
    <Button
      kind="ghost"
      size="small"
      icon={Add}
      iconDescription="New Project"
      on:click={() => showNewProjectModal = true}
    />
  </div>

  {#if loading}
    <InlineLoading description="Loading..." />
  {:else}
    <!-- Projects List -->
    <div class="projects-list">
      {#each projects as project}
        <button
          class="project-item"
          class:selected={selectedProjectId === project.id}
          on:click={() => selectProject(project.id)}
        >
          <Folder size={16} />
          <span>{project.name}</span>
        </button>
      {/each}
      {#if projects.length === 0}
        <p class="empty-message">No projects yet</p>
      {/if}
    </div>

    <!-- Project Tree -->
    {#if selectedProjectId && projectTree}
      <div class="tree-header">
        <h5>{projectTree.project.name}</h5>
        <div class="tree-actions">
          <Button
            kind="ghost"
            size="small"
            icon={FolderAdd}
            iconDescription="New Folder"
            on:click={() => showNewFolderModal = true}
          />
          <Button
            kind="ghost"
            size="small"
            icon={Upload}
            iconDescription="Upload File"
            on:click={() => showUploadModal = true}
          />
        </div>
      </div>

      {#if treeNodes.length > 0}
        <div class="custom-tree" on:contextmenu|preventDefault>
          {#each treeNodes as node}
            <div
              class="tree-node"
              class:selected={node.data.type === 'file' && selectedFileId === node.data.id}
              on:click={() => handleNodeClick(node)}
              on:contextmenu={(e) => handleContextMenu(e, node.data)}
              role="button"
              tabindex="0"
            >
              <svelte:component this={node.icon} size={16} />
              <span class="node-text">{node.text}</span>
            </div>
            {#if node.children && node.children.length > 0}
              <div class="tree-children">
                {#each node.children as child}
                  <div
                    class="tree-node"
                    class:selected={child.data.type === 'file' && selectedFileId === child.data.id}
                    on:click={() => handleNodeClick(child)}
                    on:contextmenu={(e) => handleContextMenu(e, child.data)}
                    role="button"
                    tabindex="0"
                  >
                    <svelte:component this={child.icon} size={16} />
                    <span class="node-text">{child.text}</span>
                  </div>
                {/each}
              </div>
            {/if}
          {/each}
        </div>
      {:else}
        <p class="empty-message">No files yet. Upload a TXT or XML file.</p>
      {/if}
    {/if}
  {/if}
</div>

<!-- Context Menu -->
{#if showContextMenu}
  <div
    class="context-menu"
    style="left: {contextMenuX}px; top: {contextMenuY}px;"
    on:click|stopPropagation
    role="menu"
  >
    <button class="context-menu-item" on:click={downloadFile} role="menuitem">
      <Download size={16} />
      <span>Download File</span>
    </button>
    <div class="context-menu-divider"></div>
    <button class="context-menu-item" on:click={runLineCheckQA} role="menuitem">
      <Search size={16} />
      <span>Run Full Line Check QA</span>
    </button>
    <button class="context-menu-item" on:click={runWordCheckQA} role="menuitem">
      <TextCreation size={16} />
      <span>Run Full Word Check QA</span>
    </button>
    <div class="context-menu-divider"></div>
    <button class="context-menu-item" on:click={openTMRegistration} role="menuitem">
      <DataBase size={16} />
      <span>Upload as TM...</span>
    </button>
  </div>
{/if}

<!-- New Project Modal -->
<Modal
  bind:open={showNewProjectModal}
  modalHeading="New Project"
  primaryButtonText="Create"
  secondaryButtonText="Cancel"
  on:click:button--primary={createProject}
  on:click:button--secondary={() => showNewProjectModal = false}
>
  <TextInput
    bind:value={newProjectName}
    labelText="Project Name"
    placeholder="My Translation Project"
  />
</Modal>

<!-- New Folder Modal -->
<Modal
  bind:open={showNewFolderModal}
  modalHeading="New Folder"
  primaryButtonText="Create"
  secondaryButtonText="Cancel"
  on:click:button--primary={createFolder}
  on:click:button--secondary={() => showNewFolderModal = false}
>
  <TextInput
    bind:value={newFolderName}
    labelText="Folder Name"
    placeholder="Game Assets"
  />
</Modal>

<!-- Upload File Modal -->
<Modal
  bind:open={showUploadModal}
  modalHeading="Upload File"
  primaryButtonText={uploadStatus === "uploading" ? "Uploading..." : "Upload"}
  primaryButtonDisabled={uploadStatus === "uploading"}
  secondaryButtonText="Cancel"
  on:click:button--primary={uploadFile}
  on:click:button--secondary={() => { showUploadModal = false; uploadFiles = []; uploadStatus = ""; uploadProgress = 0; }}
>
  {#if uploadStatus === "uploading"}
    <ProgressBar
      value={uploadProgress}
      max={100}
      labelText="Uploading files..."
      helperText="{uploadProgress}% complete"
    />
  {:else if uploadStatus === "success"}
    <InlineNotification
      kind="success"
      title="Success"
      subtitle="Files uploaded successfully!"
      hideCloseButton
    />
  {:else if uploadStatus === "error"}
    <InlineNotification
      kind="error"
      title="Error"
      subtitle="Some files failed to upload. Check console for details."
      hideCloseButton
    />
  {:else}
    <FileUploader
      labelTitle="Select localization file"
      labelDescription="Supported formats: TXT, TSV, XML"
      buttonLabel="Add file"
      accept={[".txt", ".tsv", ".xml"]}
      multiple
      bind:files={uploadFiles}
    />
  {/if}
</Modal>

<!-- TM Registration Modal -->
<Modal
  bind:open={showTMModal}
  modalHeading="Register as Translation Memory"
  primaryButtonText="Register TM"
  secondaryButtonText="Cancel"
  on:click:button--primary={registerAsTM}
  on:click:button--secondary={() => showTMModal = false}
>
  <div class="tm-form">
    <TextInput
      bind:value={tmName}
      labelText="TM Name"
      placeholder="BDO_EN_TM_v1.0"
      required
    />

    <Select
      bind:selected={tmProjectId}
      labelText="Assign to Project"
    >
      <SelectItem value={null} text="-- Select Project --" />
      {#each projects as project}
        <SelectItem value={project.id} text={project.name} />
      {/each}
    </Select>

    <Select
      bind:selected={tmLanguage}
      labelText="Language"
    >
      <SelectItem value="en" text="English (EN)" />
      <SelectItem value="ko" text="Korean (KO)" />
      <SelectItem value="ja" text="Japanese (JA)" />
      <SelectItem value="zh" text="Chinese (ZH)" />
      <SelectItem value="de" text="German (DE)" />
      <SelectItem value="fr" text="French (FR)" />
      <SelectItem value="es" text="Spanish (ES)" />
      <SelectItem value="pt" text="Portuguese (PT)" />
      <SelectItem value="ru" text="Russian (RU)" />
    </Select>

    <TextArea
      bind:value={tmDescription}
      labelText="Description (Optional)"
      placeholder="Notes about this TM..."
      rows={3}
    />

    <p class="tm-info">
      After registration, the TM will be processed locally (embeddings + FAISS index).
      Progress will be shown in the Tasks panel.
    </p>
  </div>
</Modal>

<style>
  .file-explorer {
    width: 280px;
    min-width: 280px;
    background: var(--cds-layer-01);
    border-right: 1px solid var(--cds-border-subtle-01);
    display: flex;
    flex-direction: column;
    height: 100%;
    /* Changed from overflow: hidden to allow tooltips to be visible */
    overflow: visible;
    position: relative;
  }

  .explorer-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.75rem 1rem;
    border-bottom: 1px solid var(--cds-border-subtle-01);
  }

  .explorer-header h4 {
    margin: 0;
    font-size: 0.875rem;
    font-weight: 600;
  }

  .projects-list {
    padding: 0.5rem;
    max-height: 150px;
    overflow-y: auto;
    border-bottom: 1px solid var(--cds-border-subtle-01);
  }

  .project-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    width: 100%;
    padding: 0.5rem;
    background: transparent;
    border: none;
    cursor: pointer;
    text-align: left;
    color: var(--cds-text-01);
    font-size: 0.875rem;
    border-radius: 4px;
  }

  .project-item:hover {
    background: var(--cds-layer-hover-01);
  }

  .project-item.selected {
    background: var(--cds-layer-selected-01);
  }

  .tree-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.5rem 1rem;
    border-bottom: 1px solid var(--cds-border-subtle-01);
  }

  .tree-header h5 {
    margin: 0;
    font-size: 0.8125rem;
    font-weight: 500;
  }

  .tree-actions {
    display: flex;
    gap: 0.25rem;
  }

  .empty-message {
    padding: 1rem;
    color: var(--cds-text-02);
    font-size: 0.8125rem;
    text-align: center;
  }

  :global(.file-explorer .bx--tree-view) {
    flex: 1;
    overflow-y: auto;
    padding: 0.5rem;
  }

  /* Custom Tree Styles */
  .custom-tree {
    flex: 1;
    overflow-y: auto;
    padding: 0.5rem;
  }

  .tree-node {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.375rem 0.5rem;
    cursor: pointer;
    border-radius: 4px;
    color: var(--cds-text-01);
    font-size: 0.875rem;
    user-select: none;
  }

  .tree-node:hover {
    background: var(--cds-layer-hover-01);
  }

  .tree-node.selected {
    background: var(--cds-layer-selected-01);
  }

  .tree-node .node-text {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .tree-children {
    padding-left: 1.25rem;
  }

  /* Context Menu Styles - Native OS Feel */
  .context-menu {
    position: fixed;
    z-index: 10000;
    background: var(--cds-layer-01);
    border: 1px solid var(--cds-border-subtle-01);
    border-radius: 4px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
    min-width: 200px;
    padding: 0.25rem 0;
    animation: context-menu-appear 0.1s ease-out;
  }

  @keyframes context-menu-appear {
    from {
      opacity: 0;
      transform: scale(0.95);
    }
    to {
      opacity: 1;
      transform: scale(1);
    }
  }

  .context-menu-item {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    width: 100%;
    padding: 0.5rem 0.75rem;
    background: transparent;
    border: none;
    cursor: pointer;
    text-align: left;
    color: var(--cds-text-01);
    font-size: 0.875rem;
  }

  .context-menu-item:hover {
    background: var(--cds-layer-hover-01);
  }

  .context-menu-item span {
    flex: 1;
  }

  .context-menu-divider {
    height: 1px;
    background: var(--cds-border-subtle-01);
    margin: 0.25rem 0;
  }

  /* TM Form Styles */
  .tm-form {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .tm-info {
    margin-top: 0.5rem;
    font-size: 0.8125rem;
    color: var(--cds-text-02);
    padding: 0.75rem;
    background: var(--cds-layer-02);
    border-radius: 4px;
  }
</style>
