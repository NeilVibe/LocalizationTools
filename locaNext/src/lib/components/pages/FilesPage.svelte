<script>
  /**
   * FilesPage.svelte - Phase 10 UI Overhaul
   *
   * Full-page Windows Explorer style file browser.
   * Uses ExplorerGrid for display + all feature handlers from FileExplorer.
   *
   * Features:
   * - Download, Convert, Pre-translate, QA, TM Registration, Extract Glossary
   * - Merge, Upload to Server
   * - Create Project, Create Folder, Upload File
   * - Breadcrumb navigation
   */
  import { createEventDispatcher, onMount, onDestroy } from 'svelte';
  import { Modal, TextInput, Select, SelectItem, TextArea, ProgressBar, InlineLoading } from 'carbon-components-svelte';
  import { Home, ChevronRight, FolderAdd, DocumentAdd, Folder, Download, Renew, Translate, DataBase, TextMining, Flash, CloudUpload, CloudDownload, Edit, TrashCan, Merge, Application, Archive, Locked } from 'carbon-icons-svelte';
  import ExplorerGrid from '$lib/components/ldm/ExplorerGrid.svelte';
  import PretranslateModal from '$lib/components/ldm/PretranslateModal.svelte';
  import InputModal from '$lib/components/common/InputModal.svelte';
  import ConfirmModal from '$lib/components/common/ConfirmModal.svelte';
  import { logger } from '$lib/utils/logger.js';
  import { getAuthHeaders, getApiBase } from '$lib/utils/api.js';
  import { preferences } from '$lib/stores/preferences.js';
  import { savedFilesState } from '$lib/stores/navigation.js';
  import { user } from '$lib/stores/app.js';
  import AccessControl from '$lib/components/admin/AccessControl.svelte';
  import { subscribeForOffline, unsubscribeFromOffline, isSubscribed, autoSyncFileOnOpen, connectionMode as syncConnectionMode } from '$lib/stores/sync.js';

  const dispatch = createEventDispatcher();
  const API_BASE = getApiBase();

  // Props
  let {
    projects = $bindable([]),
    selectedProjectId = $bindable(null),
    selectedFileId = $bindable(null),
    linkedTM = $bindable(null),
    connectionMode = 'online'
  } = $props();

  // Navigation state
  let currentPath = $state([]); // [{type, id, name}, ...] breadcrumb path
  let currentItems = $state([]); // Items to display in grid
  let loading = $state(false);
  let selectedItem = $state(null);
  let selectedIds = $state([]);  // Multi-select

  // Platform state
  let platforms = $state([]);
  let selectedPlatformId = $state(null);

  // Context menu state
  let showContextMenu = $state(false);
  let contextMenuX = $state(0);
  let contextMenuY = $state(0);
  let contextMenuItem = $state(null); // {type, id, name, ...}

  // Background context menu (right-click empty space)
  let showBackgroundMenu = $state(false);
  let bgMenuX = $state(0);
  let bgMenuY = $state(0);

  // Modal states
  let showCreateProjectModal = $state(false);
  let showCreateFolderModal = $state(false);
  let showCreatePlatformModal = $state(false);
  let showAssignPlatformModal = $state(false);
  let showRenameModal = $state(false);
  let showDeleteConfirm = $state(false);
  let showTMRegistrationModal = $state(false);
  let showPretranslateModal = $state(false);
  let showUploadToServerModal = $state(false);

  // Modal data
  let newProjectName = $state('');
  let newFolderName = $state('');
  let newPlatformName = $state('');
  let assignPlatformTarget = $state(null);  // project to assign
  let assignPlatformValue = $state(null);   // selected platform_id (null = unassigned)
  let renameValue = $state('');
  let tmName = $state('');
  let tmLanguage = $state('en');
  let tmDescription = $state('');
  let pretranslateFile = $state(null);
  let uploadToServerFile = $state(null);
  let uploadToServerProjects = $state([]);
  let uploadToServerDestination = $state(null);
  let uploadToServerLoading = $state(false);

  // Hidden file inputs
  let fileInput = $state(null);
  let mergeFileInput = $state(null);
  let mergeTargetFile = $state(null);
  let uploadTargetFolderId = $state(null);

  // DESIGN-001: Access control modal
  let showAccessControlModal = $state(false);
  let accessControlResource = $state(null);  // { type, id, name }

  // Check if current user is admin
  let isAdmin = $derived($user?.role === 'admin' || $user?.role === 'superadmin');

  // ============== Navigation ==============

  // Load root level: platforms + unassigned projects
  async function loadRoot() {
    loading = true;
    try {
      // Fetch platforms and projects in parallel
      const [platformsRes, projectsRes] = await Promise.all([
        fetch(`${API_BASE}/api/ldm/platforms`, { headers: getAuthHeaders() }),
        fetch(`${API_BASE}/api/ldm/projects`, { headers: getAuthHeaders() })
      ]);

      let platformList = [];
      if (platformsRes.ok) {
        const data = await platformsRes.json();
        platformList = data.platforms || [];
        platforms = platformList;
      }

      let projectList = [];
      if (projectsRes.ok) {
        projectList = await projectsRes.json();
        projects = projectList;
      }

      // Build root items: Unassigned section + Platforms
      const items = [];

      // Add platforms
      platformList.forEach(p => {
        items.push({
          type: 'platform',
          id: p.id,
          name: p.name,
          description: p.description,
          project_count: p.project_count || 0,
          is_restricted: p.is_restricted || false
        });
      });

      // Add unassigned projects (projects without platform_id)
      const unassignedProjects = projectList.filter(p => !p.platform_id);
      if (unassignedProjects.length > 0 || platformList.length === 0) {
        // If there are unassigned projects OR no platforms exist, show them at root
        unassignedProjects.forEach(p => {
          items.push({
            type: 'project',
            id: p.id,
            name: p.name,
            file_count: p.file_count || 0,
            platform_id: null,
            created_at: p.created_at,
            updated_at: p.updated_at,
            is_restricted: p.is_restricted || false
          });
        });
      }

      currentItems = items;
      currentPath = [];
      selectedProjectId = null;
      selectedPlatformId = null;
      logger.info('Loaded root', { platforms: platformList.length, unassigned: unassignedProjects.length });
    } catch (err) {
      logger.error('Failed to load root', { error: err.message });
    } finally {
      loading = false;
    }
  }

  // Load projects list (deprecated - kept for compatibility)
  async function loadProjects() {
    await loadRoot();
  }

  // Load platform contents (projects assigned to this platform)
  async function loadPlatformContents(platformId, platformName) {
    loading = true;
    try {
      const response = await fetch(`${API_BASE}/api/ldm/projects`, {
        headers: getAuthHeaders()
      });
      if (response.ok) {
        const allProjects = await response.json();
        // Filter projects belonging to this platform
        const platformProjects = allProjects.filter(p => p.platform_id === platformId);

        currentItems = platformProjects.map(p => ({
          type: 'project',
          id: p.id,
          name: p.name,
          file_count: p.file_count || 0,
          platform_id: p.platform_id,
          created_at: p.created_at,
          updated_at: p.updated_at,
          is_restricted: p.is_restricted || false
        }));
        currentPath = [{ type: 'platform', id: platformId, name: platformName }];
        selectedPlatformId = platformId;
        logger.info('Loaded platform contents', { platformId, projects: platformProjects.length });
      }
    } catch (err) {
      logger.error('Failed to load platform contents', { error: err.message });
    } finally {
      loading = false;
    }
  }

  // Load project contents (folders + files)
  async function loadProjectContents(projectId) {
    loading = true;
    try {
      const response = await fetch(`${API_BASE}/api/ldm/projects/${projectId}/tree`, {
        headers: getAuthHeaders()
      });
      if (response.ok) {
        const data = await response.json();
        // Flatten tree to get direct children only
        const items = (data.tree || []).map(item => ({
          type: item.type,
          id: item.id,
          name: item.name,
          format: item.format,
          row_count: item.row_count,
          file_count: item.children?.length || 0,
          created_at: item.created_at,
          updated_at: item.updated_at
        }));
        currentItems = items;
        currentPath = [{ type: 'project', id: projectId, name: data.project?.name || 'Project' }];
        selectedProjectId = projectId;
        logger.info('Loaded project contents', { projectId, items: items.length });
      }
    } catch (err) {
      logger.error('Failed to load project contents', { error: err.message });
    } finally {
      loading = false;
    }
  }

  // Load folder contents
  async function loadFolderContents(folderId, folderName) {
    loading = true;
    try {
      const response = await fetch(`${API_BASE}/api/ldm/folders/${folderId}`, {
        headers: getAuthHeaders()
      });
      if (response.ok) {
        const data = await response.json();
        const items = [
          ...(data.subfolders || []).map(f => ({ type: 'folder', id: f.id, name: f.name, file_count: f.file_count || 0 })),
          ...(data.files || []).map(f => ({ type: 'file', id: f.id, name: f.name, format: f.format, row_count: f.row_count }))
        ];
        currentItems = items;
        currentPath = [...currentPath, { type: 'folder', id: folderId, name: folderName }];
        logger.info('Loaded folder contents', { folderId, items: items.length });
      }
    } catch (err) {
      logger.error('Failed to load folder contents', { error: err.message });
    } finally {
      loading = false;
    }
  }

  // Navigate to breadcrumb
  function navigateTo(index) {
    if (index < 0) {
      // Go to root (platforms + unassigned projects)
      loadRoot();
    } else if (index === 0 && currentPath[0]?.type === 'platform') {
      // Go to platform contents
      loadPlatformContents(currentPath[0].id, currentPath[0].name);
    } else if (index === 0 && currentPath[0]?.type === 'project') {
      // Go to project root
      loadProjectContents(currentPath[0].id);
    } else if (index === 1 && currentPath[0]?.type === 'platform' && currentPath[1]?.type === 'project') {
      // Go to project inside platform
      loadProjectContents(currentPath[1].id);
    } else {
      // Go to specific folder
      const target = currentPath[index];
      currentPath = currentPath.slice(0, index);
      if (target.type === 'folder') {
        loadFolderContents(target.id, target.name);
      }
    }
  }

  // ============== Grid Event Handlers ==============

  function handleSelect(event) {
    selectedItem = event.detail.item;
    if (event.detail.selectedIds) {
      selectedIds = event.detail.selectedIds;
    }
    // Only update selectedFileId, don't open file (that's double-click)
    if (selectedItem?.type === 'file') {
      selectedFileId = selectedItem.id;
    }
  }

  async function handleMoveItems(event) {
    const { items, targetFolder } = event.detail;
    if (!items || items.length === 0 || !targetFolder) return;

    const targetId = targetFolder.type === 'project' ? null : targetFolder.id;

    try {
      for (const item of items) {
        let url;
        let response;

        if (item.type === 'file') {
          // File move: PATCH with query param
          const params = targetId !== null ? `?folder_id=${targetId}` : '';
          url = `${API_BASE}/api/ldm/files/${item.id}/move${params}`;
          response = await fetch(url, {
            method: 'PATCH',
            headers: getAuthHeaders()
          });
        } else if (item.type === 'folder') {
          // Folder move: PATCH with query param
          const params = targetId !== null ? `?parent_folder_id=${targetId}` : '';
          url = `${API_BASE}/api/ldm/folders/${item.id}/move${params}`;
          response = await fetch(url, {
            method: 'PATCH',
            headers: getAuthHeaders()
          });
        }

        if (response && !response.ok) {
          const error = await response.json().catch(() => ({}));
          logger.error('Move failed', { item: item.name, error: error.detail });
        }
      }

      logger.success('Items moved', { count: items.length, target: targetFolder.name });

      // Refresh current view
      if (currentPath.length === 0) {
        await loadProjects();
      } else if (currentPath.length === 1) {
        await loadProjectContents(selectedProjectId);
      } else {
        const currentFolder = currentPath[currentPath.length - 1];
        await loadFolderContents(currentFolder.id, currentFolder.name);
      }
    } catch (err) {
      logger.error('Move error', { error: err.message });
    }
  }

  /**
   * Handle drag-drop of projects onto platforms
   */
  async function handleAssignToPlatform(event) {
    const { projects, platform } = event.detail;
    if (!projects || projects.length === 0 || !platform) return;

    try {
      for (const project of projects) {
        const url = `${API_BASE}/api/ldm/projects/${project.id}/platform?platform_id=${platform.id}`;
        const response = await fetch(url, {
          method: 'PATCH',
          headers: getAuthHeaders()
        });

        if (!response.ok) {
          const error = await response.json().catch(() => ({}));
          logger.error('Failed to assign project to platform', { project: project.name, error: error.detail });
        }
      }

      logger.success('Projects assigned to platform', { count: projects.length, platform: platform.name });

      // Refresh current view
      if (currentPath.length === 0) {
        await loadRoot();
      } else if (currentPath[0]?.type === 'platform') {
        await loadPlatformContents(currentPath[0].id, currentPath[0].name);
      }
    } catch (err) {
      logger.error('Assign to platform error', { error: err.message });
    }
  }

  function handleEnterFolder(event) {
    const item = event.detail.item;
    if (item.type === 'platform') {
      loadPlatformContents(item.id, item.name);
    } else if (item.type === 'project') {
      // If inside a platform, include platform in path
      if (currentPath.length > 0 && currentPath[0].type === 'platform') {
        // Keep platform in path, add project
        const platformCrumb = currentPath[0];
        currentPath = [platformCrumb];
      }
      loadProjectContents(item.id);
    } else if (item.type === 'folder') {
      loadFolderContents(item.id, item.name);
    }
  }

  function handleOpenFile(event) {
    const file = event.detail.item;
    selectedFileId = file.id;

    // P3: Auto-sync file for offline when opened (background, non-blocking)
    if ($syncConnectionMode === 'online') {
      autoSyncFileOnOpen(file.id, file.name);
    }

    // Include current navigation state so we can restore on back
    const filesState = {
      path: [...currentPath],
      projectId: selectedProjectId,
      items: [...currentItems]
    };
    dispatch('fileSelect', { fileId: file.id, file, filesState });
  }

  function handleGoUp() {
    if (currentPath.length > 1) {
      navigateTo(currentPath.length - 2);
    } else if (currentPath.length === 1) {
      loadProjects();
    }
  }

  // ============== Context Menu ==============

  function handleContextMenu(event) {
    const { event: e, item } = event.detail;
    contextMenuItem = item;
    contextMenuX = e.clientX;
    contextMenuY = e.clientY;
    showContextMenu = true;
    showBackgroundMenu = false;
    // Check if this item is subscribed for offline
    checkContextItemSubscription();
  }

  function handleBackgroundContextMenu(event) {
    const { event: e } = event.detail;
    bgMenuX = e.clientX;
    bgMenuY = e.clientY;
    showBackgroundMenu = true;
    showContextMenu = false;
  }

  function closeMenus() {
    showContextMenu = false;
    showBackgroundMenu = false;
    contextMenuItem = null;
  }

  // DESIGN-001: Open access control modal
  function openAccessControl() {
    if (!contextMenuItem) return;
    if (contextMenuItem.type !== 'platform' && contextMenuItem.type !== 'project') return;
    accessControlResource = {
      type: contextMenuItem.type,
      id: contextMenuItem.id,
      name: contextMenuItem.name
    };
    closeMenus();
    showAccessControlModal = true;
  }

  // Handle access control change (refresh view when restriction toggled)
  async function handleAccessControlChange(event) {
    // Refresh current view to update lock icons
    if (currentPath.length === 0) {
      await loadRoot();
    } else if (currentPath[0]?.type === 'platform' && currentPath.length === 1) {
      await loadPlatformContents(currentPath[0].id, currentPath[0].name);
    }
  }

  // ============== File Operations ==============

  // Download
  async function downloadFile() {
    if (!contextMenuItem || contextMenuItem.type !== 'file') return;
    const file = { ...contextMenuItem };
    closeMenus();

    try {
      const response = await fetch(`${API_BASE}/api/ldm/files/${file.id}/download`, {
        headers: getAuthHeaders()
      });
      if (response.ok) {
        const blob = await response.blob();
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = file.name || 'download';
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
        logger.success('File downloaded', { name: filename });
      }
    } catch (err) {
      logger.error('Download error', { error: err.message });
    }
  }

  // P3: Enable/Disable Offline Sync
  async function handleToggleOfflineSync() {
    if (!contextMenuItem) return;
    const item = { ...contextMenuItem };
    closeMenus();

    try {
      const subscribed = await isSubscribed(item.type, item.id);
      if (subscribed) {
        await unsubscribeFromOffline(item.type, item.id);
        logger.success('Disabled offline sync', { type: item.type, name: item.name });
      } else {
        await subscribeForOffline(item.type, item.id, item.name);
        logger.success('Enabled offline sync', { type: item.type, name: item.name });
      }
    } catch (err) {
      logger.error('Offline sync toggle failed', { error: err.message });
    }
  }

  // Track subscription status for context menu items
  let contextItemSubscribed = $state(false);

  // Check subscription when context menu opens
  async function checkContextItemSubscription() {
    if (contextMenuItem) {
      contextItemSubscribed = await isSubscribed(contextMenuItem.type, contextMenuItem.id);
    }
  }

  // Convert
  async function convertFile(targetFormat) {
    if (!contextMenuItem || contextMenuItem.type !== 'file') return;
    const file = { ...contextMenuItem };
    closeMenus();

    try {
      const response = await fetch(`${API_BASE}/api/ldm/files/${file.id}/convert?format=${targetFormat}`, {
        headers: getAuthHeaders()
      });
      if (response.ok) {
        const blob = await response.blob();
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = file.name.replace(/\.[^.]+$/, '') + '_converted.' + targetFormat;
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
        logger.success('File converted', { filename });
      } else {
        const error = await response.json().catch(() => ({}));
        logger.error('Conversion failed', { error: error.detail });
      }
    } catch (err) {
      logger.error('Conversion error', { error: err.message });
    }
  }

  // Pre-translate
  function openPretranslate() {
    if (!contextMenuItem || contextMenuItem.type !== 'file') return;
    pretranslateFile = {
      id: contextMenuItem.id,
      name: contextMenuItem.name,
      row_count: contextMenuItem.row_count || 0,
      format: contextMenuItem.format || 'txt'
    };
    closeMenus();
    showPretranslateModal = true;
  }

  function handlePretranslateComplete(event) {
    showPretranslateModal = false;
    pretranslateFile = null;
    dispatch('pretranslateComplete', event.detail);
    if (selectedFileId) {
      dispatch('fileSelect', { fileId: selectedFileId });
    }
  }

  // Run QA
  function runQA() {
    if (!contextMenuItem || contextMenuItem.type !== 'file') return;
    const file = { ...contextMenuItem };
    closeMenus();
    dispatch('runQA', { fileId: file.id, type: 'all', fileName: file.name });
  }

  // TM Registration
  let tmRegistrationFile = $state(null);

  function openTMRegistration() {
    if (!contextMenuItem || contextMenuItem.type !== 'file') return;
    tmRegistrationFile = { ...contextMenuItem }; // Store before closing menu
    tmName = tmRegistrationFile.name.replace(/\.[^.]+$/, '') + '_TM';
    tmLanguage = 'en';
    tmDescription = '';
    closeMenus();
    showTMRegistrationModal = true;
  }

  async function registerAsTM() {
    if (!tmRegistrationFile || !tmName.trim()) return;
    try {
      const response = await fetch(`${API_BASE}/api/ldm/files/${tmRegistrationFile.id}/register-as-tm`, {
        method: 'POST',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: tmName,
          project_id: selectedProjectId,
          language: tmLanguage,
          description: tmDescription
        })
      });
      if (response.ok) {
        const result = await response.json();
        logger.success('TM registered', { name: tmName, tmId: result.tm_id });
        showTMRegistrationModal = false;
        tmRegistrationFile = null;
        dispatch('tmRegistered', { tmId: result.tm_id, name: tmName });
      } else {
        const error = await response.json();
        logger.error('TM registration failed', { error: error.detail });
      }
    } catch (err) {
      logger.error('TM registration error', { error: err.message });
    }
  }

  // Extract Glossary
  async function extractGlossary() {
    if (!contextMenuItem || contextMenuItem.type !== 'file') return;
    const file = { ...contextMenuItem };
    closeMenus();

    try {
      const response = await fetch(`${API_BASE}/api/ldm/files/${file.id}/extract-glossary`, {
        headers: getAuthHeaders()
      });
      if (response.ok) {
        const blob = await response.blob();
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = file.name.replace(/\.[^.]+$/, '') + '_glossary.xlsx';
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
        logger.success('Glossary extracted', { name: filename });
      }
    } catch (err) {
      logger.error('Glossary extraction error', { error: err.message });
    }
  }

  // Merge
  function openMerge() {
    if (!contextMenuItem || contextMenuItem.type !== 'file') return;
    const format = contextMenuItem.format?.toLowerCase() || '';
    if (!['txt', 'xml'].includes(format)) {
      logger.warning('Merge not supported for this format', { format });
      closeMenus();
      return;
    }
    mergeTargetFile = { ...contextMenuItem };
    closeMenus();
    if (mergeFileInput) {
      mergeFileInput.accept = format === 'txt' ? '.txt,.tsv' : '.xml';
      mergeFileInput.click();
    }
  }

  async function handleMergeFileSelected(event) {
    const file = event.target.files?.[0];
    if (!file || !mergeTargetFile) {
      mergeTargetFile = null;
      return;
    }

    try {
      const formData = new FormData();
      formData.append('original_file', file);
      const response = await fetch(`${API_BASE}/api/ldm/files/${mergeTargetFile.id}/merge`, {
        method: 'POST',
        headers: { 'Authorization': getAuthHeaders().Authorization },
        body: formData
      });

      if (response.ok) {
        const edited = response.headers.get('X-Merge-Edited') || '0';
        const added = response.headers.get('X-Merge-Added') || '0';
        const total = response.headers.get('X-Merge-Total') || '0';
        const blob = await response.blob();
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = file.name.replace(/\.[^.]+$/, '') + '_merged' + (mergeTargetFile.format === 'txt' ? '.txt' : '.xml');
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
        logger.success('Merge complete', { filename, edited, added, total });
      } else {
        const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
        logger.error('Merge failed', { error: error.detail });
      }
    } catch (err) {
      logger.error('Merge error', { error: err.message });
    } finally {
      mergeTargetFile = null;
      if (mergeFileInput) mergeFileInput.value = '';
    }
  }

  // Upload to Server
  async function openUploadToServer() {
    if (!contextMenuItem || contextMenuItem.type !== 'file') return;
    uploadToServerFile = { ...contextMenuItem };
    uploadToServerDestination = null;
    uploadToServerLoading = true;
    closeMenus();

    try {
      const response = await fetch(`${API_BASE}/api/ldm/projects`, { headers: getAuthHeaders() });
      if (response.ok) {
        uploadToServerProjects = await response.json();
      }
    } catch (err) {
      uploadToServerProjects = [];
    } finally {
      uploadToServerLoading = false;
    }
    showUploadToServerModal = true;
  }

  async function executeUploadToServer() {
    if (!uploadToServerFile || !uploadToServerDestination) return;
    uploadToServerLoading = true;

    try {
      const response = await fetch(`${API_BASE}/api/ldm/sync-to-central`, {
        method: 'POST',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({
          file_id: uploadToServerFile.id,
          destination_project_id: uploadToServerDestination
        })
      });

      if (response.ok) {
        const result = await response.json();
        logger.success('File synced to server', { file: uploadToServerFile.name, newFileId: result.new_file_id });
        dispatch('uploadToServer', { fileId: result.new_file_id, fileName: uploadToServerFile.name });
        showUploadToServerModal = false;
      } else {
        const error = await response.json();
        logger.error('Sync failed', { error: error.detail });
      }
    } catch (err) {
      logger.error('Sync error', { error: err.message });
    } finally {
      uploadToServerLoading = false;
    }
  }

  // ============== Create/Upload Operations ==============

  // Create Project
  async function createProject() {
    if (!newProjectName.trim()) return;
    try {
      const response = await fetch(`${API_BASE}/api/ldm/projects`, {
        method: 'POST',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newProjectName.trim() })
      });
      if (response.ok) {
        logger.success('Project created', { name: newProjectName });
        showCreateProjectModal = false;
        newProjectName = '';
        await loadProjects();
      } else {
        const error = await response.json();
        logger.error('Failed to create project', { error: error.detail });
      }
    } catch (err) {
      logger.error('Error creating project', { error: err.message });
    }
  }

  // Create Folder
  async function createFolder() {
    if (!newFolderName.trim() || !selectedProjectId) return;
    const parentFolderId = currentPath.length > 1 ? currentPath[currentPath.length - 1].id : null;

    try {
      const response = await fetch(`${API_BASE}/api/ldm/folders`, {
        method: 'POST',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: newFolderName.trim(),
          project_id: selectedProjectId,
          parent_id: parentFolderId
        })
      });
      if (response.ok) {
        logger.success('Folder created', { name: newFolderName });
        showCreateFolderModal = false;
        newFolderName = '';
        // Refresh current view
        if (currentPath.length === 1) {
          await loadProjectContents(selectedProjectId);
        } else {
          const currentFolder = currentPath[currentPath.length - 1];
          currentPath = currentPath.slice(0, -1);
          await loadFolderContents(currentFolder.id, currentFolder.name);
        }
      } else {
        const error = await response.json();
        logger.error('Failed to create folder', { error: error.detail });
      }
    } catch (err) {
      logger.error('Error creating folder', { error: err.message });
    }
  }

  // Create Platform
  async function createPlatform() {
    if (!newPlatformName.trim()) return;
    try {
      const response = await fetch(`${API_BASE}/api/ldm/platforms`, {
        method: 'POST',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newPlatformName.trim() })
      });
      if (response.ok) {
        logger.success('Platform created', { name: newPlatformName });
        showCreatePlatformModal = false;
        newPlatformName = '';
        await loadRoot();
      } else {
        const error = await response.json();
        logger.error('Failed to create platform', { error: error.detail });
      }
    } catch (err) {
      logger.error('Error creating platform', { error: err.message });
    }
  }

  // Assign project to platform
  function openAssignPlatform() {
    if (!contextMenuItem || contextMenuItem.type !== 'project') return;
    assignPlatformTarget = { ...contextMenuItem };
    assignPlatformValue = assignPlatformTarget.platform_id || null;
    closeMenus();
    showAssignPlatformModal = true;
  }

  async function executeAssignPlatform() {
    if (!assignPlatformTarget) return;
    try {
      const url = `${API_BASE}/api/ldm/projects/${assignPlatformTarget.id}/platform${assignPlatformValue ? `?platform_id=${assignPlatformValue}` : ''}`;
      const response = await fetch(url, {
        method: 'PATCH',
        headers: getAuthHeaders()
      });
      if (response.ok) {
        logger.success('Project assigned to platform', {
          projectId: assignPlatformTarget.id,
          platformId: assignPlatformValue
        });
        showAssignPlatformModal = false;
        assignPlatformTarget = null;
        // Refresh view
        if (currentPath.length === 0) {
          await loadRoot();
        } else if (currentPath[0]?.type === 'platform') {
          await loadPlatformContents(currentPath[0].id, currentPath[0].name);
        }
      } else {
        const error = await response.json();
        logger.error('Failed to assign platform', { error: error.detail });
      }
    } catch (err) {
      logger.error('Error assigning platform', { error: err.message });
    }
  }

  // Upload File
  function triggerFileUpload() {
    if (!selectedProjectId) return;
    uploadTargetFolderId = currentPath.length > 1 ? currentPath[currentPath.length - 1].id : null;
    if (fileInput) fileInput.click();
  }

  async function handleFileUpload(event) {
    const files = event.target.files;
    if (!files?.length || !selectedProjectId) return;

    for (const file of files) {
      const formData = new FormData();
      formData.append('project_id', selectedProjectId);
      if (uploadTargetFolderId) {
        formData.append('folder_id', uploadTargetFolderId);
      }
      formData.append('file', file);

      try {
        const response = await fetch(`${API_BASE}/api/ldm/files/upload`, {
          method: 'POST',
          headers: getAuthHeaders(),
          body: formData
        });
        if (response.ok) {
          const result = await response.json();
          logger.success('File uploaded', { name: file.name, rows: result.row_count });
        } else {
          const error = await response.json();
          logger.error('Upload failed', { name: file.name, error: error.detail });
        }
      } catch (err) {
        logger.error('Upload error', { error: err.message });
      }
    }

    // Refresh current view
    if (currentPath.length === 1) {
      await loadProjectContents(selectedProjectId);
    } else if (currentPath.length > 1) {
      const currentFolder = currentPath[currentPath.length - 1];
      currentPath = currentPath.slice(0, -1);
      await loadFolderContents(currentFolder.id, currentFolder.name);
    }

    if (fileInput) fileInput.value = '';
  }

  // ============== Rename/Delete ==============

  function openRename() {
    if (!contextMenuItem) return;
    renameValue = contextMenuItem.name;
    // Don't clear contextMenuItem - needed for executeRename
    showContextMenu = false;
    showBackgroundMenu = false;
    showRenameModal = true;
  }

  async function executeRename() {
    if (!contextMenuItem || !renameValue.trim()) return;
    const { type, id } = contextMenuItem;
    let url;
    let method = 'PATCH';
    let body = null;

    if (type === 'platform') {
      url = `${API_BASE}/api/ldm/platforms/${id}`;
      body = JSON.stringify({ name: renameValue.trim() });
    } else if (type === 'project') {
      url = `${API_BASE}/api/ldm/projects/${id}/rename?name=${encodeURIComponent(renameValue.trim())}`;
    } else if (type === 'folder') {
      url = `${API_BASE}/api/ldm/folders/${id}/rename?name=${encodeURIComponent(renameValue.trim())}`;
    } else if (type === 'file') {
      url = `${API_BASE}/api/ldm/files/${id}/rename?name=${encodeURIComponent(renameValue.trim())}`;
    }

    try {
      const headers = body
        ? { ...getAuthHeaders(), 'Content-Type': 'application/json' }
        : getAuthHeaders();
      const response = await fetch(url, { method, headers, body });
      if (response.ok) {
        logger.success(`${type} renamed`, { id, newName: renameValue });
        showRenameModal = false;
        // Refresh
        if (currentPath.length === 0) {
          await loadRoot();
        } else if (currentPath[0]?.type === 'platform' && currentPath.length === 1) {
          await loadPlatformContents(currentPath[0].id, currentPath[0].name);
        } else if (currentPath.length === 1) {
          await loadProjectContents(selectedProjectId);
        } else {
          const currentFolder = currentPath[currentPath.length - 1];
          currentPath = currentPath.slice(0, -1);
          await loadFolderContents(currentFolder.id, currentFolder.name);
        }
      } else {
        const error = await response.json();
        logger.error('Rename failed', { error: error.detail });
      }
    } catch (err) {
      logger.error('Rename error', { error: err.message });
    }
  }

  function openDelete() {
    if (!contextMenuItem) return;
    // Don't clear contextMenuItem - needed for executeDelete
    showContextMenu = false;
    showBackgroundMenu = false;
    showDeleteConfirm = true;
  }

  async function executeDelete() {
    if (!contextMenuItem) return;
    const { type, id } = contextMenuItem;
    let url;
    if (type === 'platform') {
      url = `${API_BASE}/api/ldm/platforms/${id}`;
    } else if (type === 'project') {
      url = `${API_BASE}/api/ldm/projects/${id}`;
    } else if (type === 'folder') {
      url = `${API_BASE}/api/ldm/folders/${id}`;
    } else if (type === 'file') {
      url = `${API_BASE}/api/ldm/files/${id}`;
    }

    try {
      const response = await fetch(url, { method: 'DELETE', headers: getAuthHeaders() });
      if (response.ok) {
        logger.success(`${type} deleted`, { id });
        showDeleteConfirm = false;
        contextMenuItem = null;
        // Refresh
        if (currentPath.length === 0) {
          await loadRoot();
        } else if (currentPath[0]?.type === 'platform' && currentPath.length === 1) {
          await loadPlatformContents(currentPath[0].id, currentPath[0].name);
        } else if (currentPath.length === 1) {
          await loadProjectContents(selectedProjectId);
        } else {
          const currentFolder = currentPath[currentPath.length - 1];
          currentPath = currentPath.slice(0, -1);
          await loadFolderContents(currentFolder.id, currentFolder.name);
        }
      } else {
        const error = await response.json();
        logger.error('Delete failed', { error: error.detail });
      }
    } catch (err) {
      logger.error('Delete error', { error: err.message });
    }
  }

  // ============== Background Menu Actions ==============

  function bgCreateProject() {
    closeMenus();
    showCreateProjectModal = true;
  }

  function bgCreateFolder() {
    closeMenus();
    if (selectedProjectId) {
      showCreateFolderModal = true;
    }
  }

  function bgUploadFile() {
    closeMenus();
    triggerFileUpload();
  }

  function bgCreatePlatform() {
    closeMenus();
    showCreatePlatformModal = true;
  }

  // ============== Lifecycle ==============

  function handleClickOutside() {
    closeMenus();
  }

  onMount(() => {
    // Check if we have saved state to restore (returning from grid view)
    const saved = $savedFilesState;
    if (saved && saved.path && saved.path.length > 0) {
      // Restore previous navigation state
      currentPath = saved.path;
      selectedProjectId = saved.projectId;
      currentItems = saved.items || [];
      // Clear saved state
      savedFilesState.set(null);
    } else {
      // Normal mount - load projects
      loadProjects();
    }
    document.addEventListener('click', handleClickOutside);
  });

  onDestroy(() => {
    document.removeEventListener('click', handleClickOutside);
  });

  // Expose methods
  export { loadProjects };
  export function refreshCurrentView() {
    if (currentPath.length === 0) {
      loadProjects();
    } else if (currentPath.length === 1) {
      loadProjectContents(selectedProjectId);
    } else {
      const currentFolder = currentPath[currentPath.length - 1];
      currentPath = currentPath.slice(0, -1);
      loadFolderContents(currentFolder.id, currentFolder.name);
    }
  }
</script>

<!-- Hidden file inputs -->
<input type="file" bind:this={fileInput} onchange={handleFileUpload} multiple accept=".txt,.tsv,.xlsx,.xls,.xml,.tmx" style="display: none" />
<input type="file" bind:this={mergeFileInput} onchange={handleMergeFileSelected} style="display: none" />

<div class="files-page">
  <!-- Breadcrumb Navigation -->
  <div class="breadcrumb-bar">
    <button class="breadcrumb-item" onclick={() => navigateTo(-1)}>
      <Home size={16} />
      <span>Home</span>
    </button>
    {#each currentPath as crumb, i}
      <ChevronRight size={16} class="breadcrumb-sep" />
      <button class="breadcrumb-item" onclick={() => navigateTo(i)}>
        {#if crumb.type === 'platform'}
          <Application size={16} />
        {:else}
          <Folder size={16} />
        {/if}
        <span>{crumb.name}</span>
      </button>
    {/each}
  </div>

  <!-- Explorer Grid -->
  <div class="grid-container">
    <ExplorerGrid
      items={currentItems}
      selectedId={selectedItem?.id}
      bind:selectedIds
      {loading}
      on:select={handleSelect}
      on:enterFolder={handleEnterFolder}
      on:openFile={handleOpenFile}
      on:goUp={handleGoUp}
      on:contextMenu={handleContextMenu}
      on:backgroundContextMenu={handleBackgroundContextMenu}
      on:delete={openDelete}
      on:rename={openRename}
      on:moveItems={handleMoveItems}
      on:assignToPlatform={handleAssignToPlatform}
    />
  </div>
</div>

<!-- Item Context Menu -->
{#if showContextMenu && contextMenuItem}
  <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
  <div class="context-menu" style="left: {contextMenuX}px; top: {contextMenuY}px" role="menu" onclick={(e) => e.stopPropagation()}>
    {#if contextMenuItem.type === 'file'}
      <button class="context-menu-item" onclick={openRename}><Edit size={16} /> Rename</button>
      <button class="context-menu-item" onclick={downloadFile}><Download size={16} /> Download</button>
      {#if $syncConnectionMode === 'online'}
        <button class="context-menu-item" onclick={handleToggleOfflineSync}>
          <CloudDownload size={16} />
          {contextItemSubscribed ? 'Disable Offline Sync' : 'Enable Offline Sync'}
        </button>
      {/if}
      <button class="context-menu-item" onclick={openMerge}><Merge size={16} /> Merge...</button>
      <div class="context-menu-divider"></div>
      <button class="context-menu-item" onclick={() => convertFile('xlsx')}><Renew size={16} /> Convert to XLSX</button>
      <button class="context-menu-item" onclick={() => convertFile('xml')}><Renew size={16} /> Convert to XML</button>
      <button class="context-menu-item" onclick={() => convertFile('tmx')}><Renew size={16} /> Convert to TMX</button>
      <div class="context-menu-divider"></div>
      <button class="context-menu-item pretranslate" onclick={openPretranslate}><Translate size={16} /> Pre-translate...</button>
      <button class="context-menu-item" onclick={runQA}><Flash size={16} /> Run QA</button>
      <button class="context-menu-item" onclick={openTMRegistration}><DataBase size={16} /> Register as TM</button>
      <button class="context-menu-item" onclick={extractGlossary}><TextMining size={16} /> Extract Glossary</button>
      {#if connectionMode === 'offline'}
        <div class="context-menu-divider"></div>
        <button class="context-menu-item" onclick={openUploadToServer}><CloudUpload size={16} /> Upload to Server</button>
      {/if}
      <div class="context-menu-divider"></div>
      <button class="context-menu-item danger" onclick={openDelete}><TrashCan size={16} /> Delete</button>
    {:else if contextMenuItem.type === 'folder'}
      <button class="context-menu-item" onclick={openRename}><Edit size={16} /> Rename</button>
      <button class="context-menu-item" onclick={bgUploadFile}><DocumentAdd size={16} /> Import File</button>
      <button class="context-menu-item" onclick={bgCreateFolder}><FolderAdd size={16} /> New Subfolder</button>
      <div class="context-menu-divider"></div>
      <button class="context-menu-item danger" onclick={openDelete}><TrashCan size={16} /> Delete</button>
    {:else if contextMenuItem.type === 'project'}
      <button class="context-menu-item" onclick={openRename}><Edit size={16} /> Rename</button>
      <button class="context-menu-item" onclick={openAssignPlatform}><Application size={16} /> Assign to Platform...</button>
      {#if $syncConnectionMode === 'online'}
        <button class="context-menu-item" onclick={handleToggleOfflineSync}>
          <CloudDownload size={16} />
          {contextItemSubscribed ? 'Disable Offline Sync' : 'Enable Offline Sync'}
        </button>
      {/if}
      {#if isAdmin}
        <div class="context-menu-divider"></div>
        <button class="context-menu-item" onclick={openAccessControl}><Locked size={16} /> Manage Access...</button>
      {/if}
      <div class="context-menu-divider"></div>
      <button class="context-menu-item danger" onclick={openDelete}><TrashCan size={16} /> Delete</button>
    {:else if contextMenuItem.type === 'platform'}
      <button class="context-menu-item" onclick={openRename}><Edit size={16} /> Rename</button>
      {#if $syncConnectionMode === 'online'}
        <button class="context-menu-item" onclick={handleToggleOfflineSync}>
          <CloudDownload size={16} />
          {contextItemSubscribed ? 'Disable Offline Sync' : 'Enable Offline Sync'}
        </button>
      {/if}
      {#if isAdmin}
        <div class="context-menu-divider"></div>
        <button class="context-menu-item" onclick={openAccessControl}><Locked size={16} /> Manage Access...</button>
      {/if}
      <div class="context-menu-divider"></div>
      <button class="context-menu-item danger" onclick={openDelete}><TrashCan size={16} /> Delete</button>
    {/if}
  </div>
{/if}

<!-- Background Context Menu -->
{#if showBackgroundMenu}
  <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
  <div class="context-menu" style="left: {bgMenuX}px; top: {bgMenuY}px" role="menu" onclick={(e) => e.stopPropagation()}>
    {#if currentPath.length === 0}
      <!-- At root: can create platform or project -->
      <button class="context-menu-item" onclick={bgCreatePlatform}><Application size={16} /> New Platform</button>
      <button class="context-menu-item" onclick={bgCreateProject}><FolderAdd size={16} /> New Project</button>
    {:else if currentPath[0]?.type === 'platform' && currentPath.length === 1}
      <!-- Inside a platform: can only create project -->
      <button class="context-menu-item" onclick={bgCreateProject}><FolderAdd size={16} /> New Project</button>
    {:else}
      <!-- Inside project/folder: upload file or create folder -->
      <button class="context-menu-item" onclick={bgUploadFile}><DocumentAdd size={16} /> Upload File</button>
      <button class="context-menu-item" onclick={bgCreateFolder}><FolderAdd size={16} /> New Folder</button>
    {/if}
  </div>
{/if}

<!-- Modals -->
<InputModal
  bind:open={showCreateProjectModal}
  title="New Project"
  label="Project Name"
  placeholder="Enter project name"
  submitLabel="Create"
  bind:value={newProjectName}
  onSubmit={createProject}
  onCancel={() => { newProjectName = ''; }}
/>

<InputModal
  bind:open={showCreateFolderModal}
  title="New Folder"
  label="Folder Name"
  placeholder="Enter folder name"
  submitLabel="Create"
  bind:value={newFolderName}
  onSubmit={createFolder}
  onCancel={() => { newFolderName = ''; }}
/>

<InputModal
  bind:open={showCreatePlatformModal}
  title="New Platform"
  label="Platform Name"
  placeholder="Enter platform name (e.g., PC, Mobile, Console)"
  submitLabel="Create"
  bind:value={newPlatformName}
  onSubmit={createPlatform}
  onCancel={() => { newPlatformName = ''; }}
/>

<!-- Assign Platform Modal -->
<Modal
  bind:open={showAssignPlatformModal}
  modalHeading="Assign to Platform"
  primaryButtonText="Assign"
  secondaryButtonText="Cancel"
  on:click:button--primary={executeAssignPlatform}
  on:click:button--secondary={() => { showAssignPlatformModal = false; assignPlatformTarget = null; }}
>
  <p style="margin-bottom: 1rem;">Assign project "{assignPlatformTarget?.name}" to a platform:</p>
  <Select labelText="Platform" bind:selected={assignPlatformValue}>
    <SelectItem value={null} text="(Unassigned)" />
    {#each platforms as platform}
      <SelectItem value={platform.id} text={platform.name} />
    {/each}
  </Select>
</Modal>

<InputModal
  bind:open={showRenameModal}
  title="Rename"
  label="New Name"
  submitLabel="Rename"
  bind:value={renameValue}
  onSubmit={executeRename}
  onCancel={() => {}}
/>

<ConfirmModal
  bind:open={showDeleteConfirm}
  title="Delete {contextMenuItem?.type || 'item'}"
  message="Are you sure you want to delete '{contextMenuItem?.name}'? This cannot be undone."
  danger={true}
  confirmLabel="Delete"
  onConfirm={executeDelete}
  onCancel={() => { contextMenuItem = null; }}
/>

<!-- TM Registration Modal -->
<Modal
  bind:open={showTMRegistrationModal}
  modalHeading="Register as Translation Memory"
  primaryButtonText="Register"
  secondaryButtonText="Cancel"
  on:click:button--primary={registerAsTM}
  on:click:button--secondary={() => { showTMRegistrationModal = false; }}
>
  <TextInput labelText="TM Name" bind:value={tmName} placeholder="Enter TM name" />
  <Select labelText="Language" bind:selected={tmLanguage}>
    <SelectItem value="en" text="English" />
    <SelectItem value="ko" text="Korean" />
    <SelectItem value="ja" text="Japanese" />
    <SelectItem value="zh" text="Chinese" />
  </Select>
  <TextArea labelText="Description (optional)" bind:value={tmDescription} placeholder="Enter description" />
</Modal>

<!-- Pre-translate Modal -->
{#if pretranslateFile}
  <PretranslateModal
    bind:open={showPretranslateModal}
    file={pretranslateFile}
    on:complete={handlePretranslateComplete}
    on:close={() => { showPretranslateModal = false; pretranslateFile = null; }}
  />
{/if}

<!-- Upload to Server Modal -->
<Modal
  bind:open={showUploadToServerModal}
  modalHeading="Upload to Central Server"
  primaryButtonText="Upload"
  primaryButtonDisabled={!uploadToServerDestination || uploadToServerLoading}
  secondaryButtonText="Cancel"
  on:click:button--primary={executeUploadToServer}
  on:click:button--secondary={() => { showUploadToServerModal = false; }}
>
  {#if uploadToServerLoading}
    <InlineLoading description="Loading..." />
  {:else}
    <p style="margin-bottom: 1rem;">Upload "{uploadToServerFile?.name}" to central server</p>
    <Select labelText="Destination Project" bind:selected={uploadToServerDestination}>
      <SelectItem value={null} text="Select a project..." />
      {#each uploadToServerProjects as project}
        <SelectItem value={project.id} text={project.name} />
      {/each}
    </Select>
  {/if}
</Modal>

<!-- DESIGN-001: Access Control Modal -->
{#if accessControlResource}
  <AccessControl
    bind:open={showAccessControlModal}
    resourceType={accessControlResource.type}
    resourceId={accessControlResource.id}
    resourceName={accessControlResource.name}
    on:change={handleAccessControlChange}
    on:close={() => { showAccessControlModal = false; accessControlResource = null; }}
  />
{/if}

<style>
  .files-page {
    display: flex;
    flex-direction: column;
    width: 100%;
    height: 100%;
    overflow: hidden;
    background: var(--cds-background);
  }

  .breadcrumb-bar {
    display: flex;
    align-items: center;
    gap: 0.25rem;
    padding: 0.75rem 1rem;
    background: var(--cds-layer-01);
    border-bottom: 1px solid var(--cds-border-subtle-01);
    flex-shrink: 0;
  }

  .breadcrumb-item {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    padding: 0.375rem 0.625rem;
    background: transparent;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.875rem;
    color: var(--cds-text-secondary);
    transition: background 0.1s ease, color 0.1s ease;
  }

  .breadcrumb-item:hover {
    background: var(--cds-layer-hover-01);
    color: var(--cds-text-primary);
  }

  .breadcrumb-item:last-child {
    color: var(--cds-text-primary);
    font-weight: 500;
  }

  :global(.breadcrumb-sep) {
    color: var(--cds-text-disabled);
  }

  .grid-container {
    flex: 1;
    min-height: 0; /* Allow flex shrink */
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }

  /* Context Menu */
  .context-menu {
    position: fixed;
    z-index: 10000;
    min-width: 180px;
    background: var(--cds-layer-01);
    border: 1px solid var(--cds-border-subtle-01);
    border-radius: 4px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
    padding: 0.25rem 0;
  }

  .context-menu-item {
    display: flex;
    align-items: center;
    gap: 0.625rem;
    width: 100%;
    padding: 0.5rem 1rem;
    background: transparent;
    border: none;
    cursor: pointer;
    font-size: 0.875rem;
    color: var(--cds-text-primary);
    text-align: left;
    transition: background 0.15s ease, color 0.15s ease;
  }

  .context-menu-item:hover {
    background: rgba(255, 255, 255, 0.1);
    color: var(--cds-text-01);
  }

  .context-menu-item:active {
    background: rgba(255, 255, 255, 0.15);
  }

  .context-menu-item.pretranslate {
    color: var(--cds-link-01);
    font-weight: 500;
  }

  .context-menu-item.danger {
    color: var(--cds-support-error);
  }

  .context-menu-item.danger:hover {
    background: var(--cds-support-error);
    color: white;
  }

  .context-menu-divider {
    height: 1px;
    background: var(--cds-border-subtle-01);
    margin: 0.25rem 0;
  }
</style>
