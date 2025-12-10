<script>
  import {
    TreeView,
    Button,
    Modal,
    TextInput,
    FileUploader,
    InlineLoading,
    ProgressBar,
    InlineNotification
  } from "carbon-components-svelte";
  import { Folder, Document, Add, TrashCan, Upload, FolderAdd } from "carbon-icons-svelte";
  import { createEventDispatcher } from "svelte";
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

  // Handle tree node selection
  function handleNodeSelect(event) {
    const node = event.detail;
    if (node.data.type === 'file') {
      selectedFileId = node.data.id;
      selectedFolderId = null;
      dispatch('fileSelect', { fileId: node.data.id, file: node.data });
    } else if (node.data.type === 'folder') {
      selectedFolderId = node.data.id;
      selectedFileId = null;
    }
  }

  // Watch for project selection changes
  $: if (selectedProjectId) {
    loadProjectTree(selectedProjectId);
  }
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
        <TreeView
          children={treeNodes}
          on:select={handleNodeSelect}
        />
      {:else}
        <p class="empty-message">No files yet. Upload a TXT or XML file.</p>
      {/if}
    {/if}
  {/if}
</div>

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

<style>
  .file-explorer {
    width: 280px;
    min-width: 280px;
    background: var(--cds-layer-01);
    border-right: 1px solid var(--cds-border-subtle-01);
    display: flex;
    flex-direction: column;
    height: 100%;
    overflow: hidden;
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
</style>
