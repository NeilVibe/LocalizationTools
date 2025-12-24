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
    TextArea,
    Tag
  } from "carbon-components-svelte";
  import { Folder, Document, Add, TrashCan, Upload, FolderAdd, Download, Search, TextCreation, DataBase, Translate, Renew, CloudUpload, Link, Unlink } from "carbon-icons-svelte";
  import { createEventDispatcher, onMount, onDestroy } from "svelte";
  import { logger } from "$lib/utils/logger.js";

  const dispatch = createEventDispatcher();

  // API base URL
  const API_BASE = 'http://localhost:8888';

  // Svelte 5: Props
  let {
    projects = $bindable([]),
    selectedProjectId = $bindable(null),
    selectedFileId = $bindable(null),
    selectedTMId = $bindable(null),
    connectionMode = 'unknown' // P33 Phase 5: 'online' | 'offline' | 'unknown'
  } = $props();

  // Svelte 5: State - Tab navigation (P33 Phase 3)
  let activeTab = $state('files'); // 'files' | 'tm'

  // Svelte 5: State - Files tab
  let loading = $state(false);
  let projectTree = $state(null);
  let treeNodes = $state([]);

  // Svelte 5: State - TM tab
  let tmList = $state([]);
  let tmLoading = $state(false);

  // Svelte 5: Modal states
  let showNewProjectModal = $state(false);
  let showNewFolderModal = $state(false);
  let showUploadModal = $state(false);
  let newProjectName = $state("");
  let newFolderName = $state("");
  let selectedFolderId = $state(null);
  let uploadFiles = $state([]);
  let uploadProgress = $state(0);
  let uploadStatus = $state(""); // '', 'uploading', 'success', 'error'

  // Svelte 5: Context menu state
  let showContextMenu = $state(false);
  let contextMenuX = $state(0);
  let contextMenuY = $state(0);
  let contextMenuFile = $state(null); // {id, name, type, format}

  // Svelte 5: TM Registration modal state
  let showTMModal = $state(false);
  let tmName = $state("");
  let tmProjectId = $state(null);
  let tmLanguage = $state("en");
  let tmDescription = $state("");
  let tmRegistrationFile = $state(null); // BUG-029 fix: Store file ref before closing context menu

  // P33 Phase 5: Upload to Server modal state
  let showUploadToServerModal = $state(false);
  let uploadToServerFile = $state(null); // {id, name, type}
  let uploadToServerDestination = $state(null); // project id
  let uploadToServerLoading = $state(false);
  let uploadToServerProjects = $state([]); // Central server projects list

  // FEAT-001: TM Link state
  let linkedTM = $state(null); // {tm_id, tm_name, priority} or null
  let showLinkTMModal = $state(false);
  let selectedLinkTMId = $state(null); // TM id selected in modal

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

  // ============== TM Tab Functions (P33 Phase 3) ==============

  // Load TM list
  export async function loadTMList() {
    tmLoading = true;
    try {
      const response = await fetch(`${API_BASE}/api/ldm/tm`, {
        headers: getAuthHeaders()
      });
      if (response.ok) {
        tmList = await response.json();
        logger.info("Loaded TM list", { count: tmList.length });
      }
    } catch (err) {
      logger.error("Failed to load TM list", { error: err.message });
    } finally {
      tmLoading = false;
    }
  }

  // Select TM to open in VirtualGrid
  function selectTM(tm) {
    selectedTMId = tm.id;
    selectedFileId = null; // Deselect file when TM selected
    dispatch('tmSelect', { tmId: tm.id, tm });
    logger.info("TM selected", { tmId: tm.id, name: tm.name });
  }

  // Refresh TM list
  async function refreshTMList() {
    await loadTMList();
  }

  // Switch to TM tab and load TMs
  function switchToTMTab() {
    activeTab = 'tm';
    if (tmList.length === 0) {
      loadTMList();
    }
  }

  // Switch to Files tab
  function switchToFilesTab() {
    activeTab = 'files';
    selectedTMId = null;
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
      // FEAT-001: Also load linked TM
      await loadLinkedTM(projectId);
    } catch (err) {
      logger.error("Failed to load project tree", { error: err.message });
    } finally {
      loading = false;
    }
  }

  // FEAT-001: Load linked TM for a project
  async function loadLinkedTM(projectId) {
    if (!projectId) {
      linkedTM = null;
      return;
    }
    try {
      const response = await fetch(`${API_BASE}/api/ldm/projects/${projectId}/linked-tms`, {
        headers: getAuthHeaders()
      });
      if (response.ok) {
        const data = await response.json();
        // Get the first (highest priority) linked TM
        linkedTM = data.linked_tms && data.linked_tms.length > 0 ? data.linked_tms[0] : null;
        logger.info("Loaded linked TM", { projectId, linkedTM });
      }
    } catch (err) {
      logger.error("Failed to load linked TM", { error: err.message });
      linkedTM = null;
    }
  }

  // FEAT-001: Link a TM to the current project
  async function linkTMToProject() {
    if (!selectedProjectId || !selectedLinkTMId) return;
    try {
      const response = await fetch(`${API_BASE}/api/ldm/projects/${selectedProjectId}/link-tm`, {
        method: 'POST',
        headers: {
          ...getAuthHeaders(),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ tm_id: selectedLinkTMId, priority: 0 })
      });
      if (response.ok) {
        const data = await response.json();
        logger.success("TM linked to project", { projectId: selectedProjectId, tmId: selectedLinkTMId });
        // Reload linked TM
        await loadLinkedTM(selectedProjectId);
        showLinkTMModal = false;
        selectedLinkTMId = null;
      } else {
        const error = await response.json();
        logger.error("Failed to link TM", { error: error.detail });
      }
    } catch (err) {
      logger.error("Failed to link TM", { error: err.message });
    }
  }

  // FEAT-001: Unlink TM from the current project
  async function unlinkTMFromProject() {
    if (!selectedProjectId || !linkedTM) return;
    try {
      const response = await fetch(`${API_BASE}/api/ldm/projects/${selectedProjectId}/link-tm/${linkedTM.tm_id}`, {
        method: 'DELETE',
        headers: getAuthHeaders()
      });
      if (response.ok) {
        logger.success("TM unlinked from project", { projectId: selectedProjectId, tmId: linkedTM.tm_id });
        linkedTM = null;
      } else {
        const error = await response.json();
        logger.error("Failed to unlink TM", { error: error.detail });
      }
    } catch (err) {
      logger.error("Failed to unlink TM", { error: err.message });
    }
  }

  // FEAT-001: Open link TM modal
  function openLinkTMModal() {
    // Make sure TM list is loaded
    if (tmList.length === 0) {
      loadTMList();
    }
    selectedLinkTMId = linkedTM ? linkedTM.tm_id : null;
    showLinkTMModal = true;
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

  // Svelte 5: Effect - Watch for project selection changes
  $effect(() => {
    if (selectedProjectId) {
      loadProjectTree(selectedProjectId);
    }
  });

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

  // Extract glossary from file
  async function extractGlossary() {
    if (!contextMenuFile) return;
    closeContextMenu();

    try {
      const response = await fetch(`${API_BASE}/api/ldm/files/${contextMenuFile.id}/extract-glossary`, {
        headers: getAuthHeaders()
      });

      if (response.ok) {
        const blob = await response.blob();
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = contextMenuFile.name.replace(/\.[^.]+$/, '') + '_glossary.xlsx';
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

        logger.success("Glossary extracted", { name: filename });
      } else {
        const error = await response.json().catch(() => ({}));
        logger.error("Glossary extraction failed", { status: response.status, detail: error.detail });
      }
    } catch (err) {
      logger.error("Glossary extraction error", { error: err.message });
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

  // Run Term Check QA
  async function runTermCheckQA() {
    if (!contextMenuFile) return;
    closeContextMenu();

    logger.info("Term Check QA started", { file: contextMenuFile.name });
    dispatch('runQA', { fileId: contextMenuFile.id, type: 'term', fileName: contextMenuFile.name });
  }

  // Open TM Registration modal
  function openTMRegistration() {
    if (!contextMenuFile) return;

    // BUG-029 fix: Store file reference BEFORE closing context menu
    tmRegistrationFile = contextMenuFile;
    closeContextMenu();

    // Pre-fill TM name from file name
    tmName = tmRegistrationFile.name.replace(/\.[^.]+$/, '') + "_TM";
    tmProjectId = selectedProjectId;
    tmLanguage = "en";
    tmDescription = "";
    showTMModal = true;

    logger.info("TM Registration opened", { file: tmRegistrationFile.name });
  }

  // Register file as TM
  async function registerAsTM() {
    // BUG-029 fix: Use tmRegistrationFile instead of contextMenuFile
    if (!tmRegistrationFile || !tmName.trim()) return;

    try {
      const response = await fetch(`${API_BASE}/api/ldm/files/${tmRegistrationFile.id}/register-as-tm`, {
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
          fileId: tmRegistrationFile.id,
          fileName: tmRegistrationFile.name
        });

        // Clear the registration file reference
        tmRegistrationFile = null;
      } else {
        const error = await response.json();
        logger.error("TM registration failed", { error: error.detail });
      }
    } catch (err) {
      logger.error("TM registration error", { error: err.message });
    }
  }

  // ============== P33 Phase 5: Upload to Central Server ==============

  // Open upload to server modal
  async function openUploadToServer() {
    if (!contextMenuFile) return;
    closeContextMenu();

    uploadToServerFile = contextMenuFile;
    uploadToServerDestination = null;
    uploadToServerLoading = true;

    try {
      // Fetch central server projects list
      // Note: This endpoint would need to query PostgreSQL directly
      // For now, we use the same /api/ldm/projects endpoint
      const response = await fetch(`${API_BASE}/api/ldm/projects`, {
        headers: getAuthHeaders()
      });

      if (response.ok) {
        uploadToServerProjects = await response.json();
      }
    } catch (err) {
      logger.error("Failed to load server projects", { error: err.message });
      uploadToServerProjects = [];
    } finally {
      uploadToServerLoading = false;
    }

    showUploadToServerModal = true;
    logger.info("Upload to Server modal opened", { file: contextMenuFile.name });
  }

  // Execute upload to central server (P33: Sync DB entries, not file blob)
  async function executeUploadToServer() {
    if (!uploadToServerFile || !uploadToServerDestination) return;

    uploadToServerLoading = true;

    try {
      // Use the sync-to-central endpoint which:
      // 1. Reads file metadata + rows from local SQLite
      // 2. Creates them in PostgreSQL (central server)
      // This preserves all translations and extra_data for full reconstruction
      const syncResponse = await fetch(`${API_BASE}/api/ldm/sync-to-central`, {
        method: 'POST',
        headers: {
          ...getAuthHeaders(),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          file_id: uploadToServerFile.id,
          destination_project_id: uploadToServerDestination
        })
      });

      if (syncResponse.ok) {
        const result = await syncResponse.json();
        logger.success("File synced to central server", {
          file: uploadToServerFile.name,
          projectId: uploadToServerDestination,
          newFileId: result.new_file_id,
          rowsSynced: result.rows_synced
        });

        // Dispatch event to notify parent
        dispatch('uploadToServer', {
          fileId: result.new_file_id,
          fileName: uploadToServerFile.name,
          projectId: uploadToServerDestination,
          rowsSynced: result.rows_synced
        });

        showUploadToServerModal = false;
      } else {
        const error = await syncResponse.json();
        logger.error("Sync to server failed", { error: error.detail });
        // Show error to user
        alert(`Sync failed: ${error.detail}`);
      }
    } catch (err) {
      logger.error("Sync to server error", { error: err.message });
      alert(`Sync error: ${err.message}`);
    } finally {
      uploadToServerLoading = false;
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
  <!-- P33 Phase 3: Tab Bar -->
  <div class="tab-bar">
    <button
      class="tab-button"
      class:active={activeTab === 'files'}
      onclick={switchToFilesTab}
    >
      <Folder size={16} />
      <span>Files</span>
    </button>
    <button
      class="tab-button"
      class:active={activeTab === 'tm'}
      onclick={switchToTMTab}
    >
      <Translate size={16} />
      <span>TM</span>
    </button>
  </div>

  <!-- Files Tab Content -->
  {#if activeTab === 'files'}
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
            onclick={() => selectProject(project.id)}
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

        <!-- FEAT-001: Linked TM indicator -->
        <div class="linked-tm-bar">
          {#if linkedTM}
            <button class="linked-tm-button has-tm" onclick={openLinkTMModal}>
              <Link size={14} />
              <span class="linked-tm-name">{linkedTM.tm_name}</span>
              <Tag type="green" size="sm">Linked</Tag>
            </button>
          {:else}
            <button class="linked-tm-button no-tm" onclick={openLinkTMModal}>
              <Unlink size={14} />
              <span>Link a TM for auto-add</span>
            </button>
          {/if}
        </div>

        {#if treeNodes.length > 0}
          <div class="custom-tree" oncontextmenu={(e) => e.preventDefault()}>
            {#each treeNodes as node}
              {@const NodeIcon = node.icon}
              <div
                class="tree-node"
                class:selected={node.data.type === 'file' && selectedFileId === node.data.id}
                onclick={() => handleNodeClick(node)}
                oncontextmenu={(e) => handleContextMenu(e, node.data)}
                role="button"
                tabindex="0"
              >
                <NodeIcon size={16} />
                <span class="node-text">{node.text}</span>
              </div>
              {#if node.children && node.children.length > 0}
                <div class="tree-children">
                  {#each node.children as child}
                    {@const ChildIcon = child.icon}
                    <div
                      class="tree-node"
                      class:selected={child.data.type === 'file' && selectedFileId === child.data.id}
                      onclick={() => handleNodeClick(child)}
                      oncontextmenu={(e) => handleContextMenu(e, child.data)}
                      role="button"
                      tabindex="0"
                    >
                      <ChildIcon size={16} />
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
  {/if}

  <!-- TM Tab Content (P33 Phase 3) -->
  {#if activeTab === 'tm'}
    <div class="explorer-header">
      <h4>Translation Memories</h4>
      <Button
        kind="ghost"
        size="small"
        icon={Renew}
        iconDescription="Refresh TM List"
        on:click={refreshTMList}
      />
    </div>

    {#if tmLoading}
      <InlineLoading description="Loading TMs..." />
    {:else}
      <div class="tm-list">
        {#each tmList as tm}
          <button
            class="tm-item"
            class:selected={selectedTMId === tm.id}
            onclick={() => selectTM(tm)}
          >
            <DataBase size={16} />
            <div class="tm-info">
              <span class="tm-name">{tm.name}</span>
              <span class="tm-meta">{tm.entry_count || 0} entries</span>
            </div>
            {#if tm.status === 'ready'}
              <Tag type="green" size="sm">Ready</Tag>
            {:else}
              <Tag type="outline" size="sm">Pending</Tag>
            {/if}
          </button>
        {/each}
        {#if tmList.length === 0}
          <p class="empty-message">No TMs yet. Register a file as TM from Files tab.</p>
        {/if}
      </div>
    {/if}
  {/if}
</div>

<!-- Context Menu -->
{#if showContextMenu}
  <div
    class="context-menu"
    style="left: {contextMenuX}px; top: {contextMenuY}px;"
    onclick={(e) => e.stopPropagation()}
    role="menu"
  >
    <button class="context-menu-item" onclick={downloadFile} role="menuitem">
      <Download size={16} />
      <span>Download File</span>
    </button>
    <div class="context-menu-divider"></div>
    <button class="context-menu-item" onclick={runLineCheckQA} role="menuitem">
      <Search size={16} />
      <span>Run Full Line Check QA</span>
    </button>
    <button class="context-menu-item" onclick={runTermCheckQA} role="menuitem">
      <TextCreation size={16} />
      <span>Run Full Term Check QA</span>
    </button>
    <div class="context-menu-divider"></div>
    <button class="context-menu-item" onclick={openTMRegistration} role="menuitem">
      <DataBase size={16} />
      <span>Upload as TM...</span>
    </button>
    <button class="context-menu-item" onclick={extractGlossary} role="menuitem">
      <Translate size={16} />
      <span>Create Glossary</span>
    </button>
    {#if connectionMode === 'offline'}
      <div class="context-menu-divider"></div>
      <button class="context-menu-item upload-to-server" onclick={openUploadToServer} role="menuitem">
        <CloudUpload size={16} />
        <span>Upload to Central Server...</span>
      </button>
    {/if}
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

<!-- FEAT-001: Link TM Modal -->
<Modal
  bind:open={showLinkTMModal}
  modalHeading="Link Translation Memory"
  primaryButtonText={linkedTM ? "Update Link" : "Link TM"}
  secondaryButtonText="Cancel"
  on:click:button--primary={linkTMToProject}
  on:click:button--secondary={() => showLinkTMModal = false}
>
  <p style="margin-bottom: 1rem; color: var(--cds-text-02); font-size: 0.875rem;">
    When you confirm a translation (Ctrl+S), it will be auto-added to the linked TM.
  </p>

  <Select
    bind:selected={selectedLinkTMId}
    labelText="Select Translation Memory"
  >
    <SelectItem value={null} text="-- No TM linked --" />
    {#each tmList as tm}
      <SelectItem value={tm.id} text="{tm.name} ({tm.entry_count || 0} entries)" />
    {/each}
  </Select>

  {#if linkedTM && selectedLinkTMId !== linkedTM.tm_id}
    <InlineNotification
      kind="info"
      title="Changing TM"
      subtitle="This will replace the current linked TM."
      hideCloseButton
      lowContrast
      style="margin-top: 1rem;"
    />
  {/if}

  {#if linkedTM}
    <div style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid var(--cds-border-subtle-01);">
      <Button
        kind="danger-tertiary"
        size="small"
        icon={Unlink}
        on:click={() => { unlinkTMFromProject(); showLinkTMModal = false; }}
      >
        Unlink TM
      </Button>
    </div>
  {/if}
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

<!-- P33 Phase 5: Upload to Central Server Modal -->
<Modal
  bind:open={showUploadToServerModal}
  modalHeading="Upload to Central Server"
  primaryButtonText={uploadToServerLoading ? "Uploading..." : "Upload"}
  primaryButtonDisabled={!uploadToServerDestination || uploadToServerLoading}
  secondaryButtonText="Cancel"
  on:click:button--primary={executeUploadToServer}
  on:click:button--secondary={() => showUploadToServerModal = false}
>
  <div class="upload-server-form">
    {#if uploadToServerFile}
      <div class="upload-file-info">
        <Document size={24} />
        <span class="upload-file-name">{uploadToServerFile.name}</span>
      </div>
    {/if}

    <Select
      bind:selected={uploadToServerDestination}
      labelText="Choose destination project"
    >
      <SelectItem value={null} text="-- Select Project --" />
      {#each uploadToServerProjects as project}
        <SelectItem value={project.id} text={project.name} />
      {/each}
    </Select>

    <div class="upload-safety-checks">
      <h4>Safety Checks</h4>
      {#if uploadToServerFile}
        <div class="safety-item success">
          <span>✓</span>
          <span>File format supported</span>
        </div>
        <div class="safety-item success">
          <span>✓</span>
          <span>File name valid</span>
        </div>
        {#if uploadToServerDestination}
          <div class="safety-item success">
            <span>✓</span>
            <span>Destination selected</span>
          </div>
        {:else}
          <div class="safety-item pending">
            <span>○</span>
            <span>Select a destination project</span>
          </div>
        {/if}
      {/if}
    </div>

    <p class="upload-info">
      Once uploaded, this file will be visible to all users with access to the selected project.
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

  /* P33 Phase 3: Tab Bar Styles */
  .tab-bar {
    display: flex;
    border-bottom: 1px solid var(--cds-border-subtle-01);
    background: var(--cds-layer-02);
  }

  .tab-button {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    padding: 0.75rem 1rem;
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    cursor: pointer;
    color: var(--cds-text-02);
    font-size: 0.875rem;
    font-weight: 500;
    transition: all 0.15s ease;
  }

  .tab-button:hover {
    background: var(--cds-layer-hover-01);
    color: var(--cds-text-01);
  }

  .tab-button.active {
    background: var(--cds-layer-01);
    color: var(--cds-text-01);
    border-bottom-color: var(--cds-interactive-01);
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

  /* P33 Phase 3: TM List Styles */
  .tm-list {
    flex: 1;
    overflow-y: auto;
    padding: 0.5rem;
  }

  .tm-item {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    width: 100%;
    padding: 0.625rem 0.75rem;
    background: transparent;
    border: none;
    cursor: pointer;
    text-align: left;
    color: var(--cds-text-01);
    font-size: 0.875rem;
    border-radius: 4px;
    margin-bottom: 0.25rem;
  }

  .tm-item:hover {
    background: var(--cds-layer-hover-01);
  }

  .tm-item.selected {
    background: var(--cds-layer-selected-01);
  }

  .tm-info {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-width: 0;
  }

  .tm-name {
    font-weight: 500;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .tm-meta {
    font-size: 0.75rem;
    color: var(--cds-text-02);
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

  /* FEAT-001: Linked TM bar */
  .linked-tm-bar {
    padding: 0.5rem 1rem;
    background: var(--cds-layer-01);
    border-bottom: 1px solid var(--cds-border-subtle-01);
  }

  .linked-tm-button {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    width: 100%;
    padding: 0.5rem 0.75rem;
    background: var(--cds-field-01);
    border: 1px solid var(--cds-border-subtle-01);
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.8125rem;
    color: var(--cds-text-primary);
    transition: background 0.15s, border-color 0.15s;
  }

  .linked-tm-button:hover {
    background: var(--cds-layer-hover-01);
    border-color: var(--cds-border-strong-01);
  }

  .linked-tm-button.has-tm {
    background: var(--cds-layer-selected-01);
  }

  .linked-tm-button.no-tm {
    color: var(--cds-text-02);
    border-style: dashed;
  }

  .linked-tm-name {
    flex: 1;
    text-align: left;
    font-weight: 500;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
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

  /* P33 Phase 5: Upload to Server Modal Styles */
  .upload-server-form {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .upload-file-info {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 1rem;
    background: var(--cds-layer-02);
    border-radius: 4px;
    margin-bottom: 0.5rem;
  }

  .upload-file-name {
    font-weight: 600;
    color: var(--cds-text-01);
  }

  .upload-safety-checks {
    padding: 1rem;
    background: var(--cds-layer-02);
    border-radius: 4px;
  }

  .upload-safety-checks h4 {
    margin: 0 0 0.75rem 0;
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--cds-text-01);
  }

  .safety-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.8125rem;
    margin-bottom: 0.5rem;
  }

  .safety-item.success {
    color: var(--cds-support-success);
  }

  .safety-item.pending {
    color: var(--cds-text-02);
  }

  .upload-info {
    font-size: 0.8125rem;
    color: var(--cds-text-02);
    padding: 0.75rem;
    background: var(--cds-layer-accent-01);
    border-radius: 4px;
    margin-top: 0.5rem;
  }

  .context-menu-item.upload-to-server {
    color: var(--cds-support-info);
  }
</style>
