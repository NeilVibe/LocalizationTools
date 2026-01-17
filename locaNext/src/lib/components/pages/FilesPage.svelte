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
  import { get } from 'svelte/store';
  import { Modal, TextInput, Select, SelectItem, TextArea, ProgressBar, InlineLoading } from 'carbon-components-svelte';
  import { Home, ChevronRight, FolderAdd, DocumentAdd, Folder, Download, Renew, Translate, DataBase, TextMining, Flash, CloudUpload, CloudDownload, Edit, TrashCan, Merge, Application, Archive, Locked, Copy, Cut, CloudOffline } from 'carbon-icons-svelte';
  import ExplorerGrid from '$lib/components/ldm/ExplorerGrid.svelte';
  import PretranslateModal from '$lib/components/ldm/PretranslateModal.svelte';
  import InputModal from '$lib/components/common/InputModal.svelte';
  import ConfirmModal from '$lib/components/common/ConfirmModal.svelte';
  import { logger } from '$lib/utils/logger.js';
  import { createTracker } from '$lib/utils/trackedOperation.js';
  import { getAuthHeaders, getApiBase } from '$lib/utils/api.js';
  import { preferences } from '$lib/stores/preferences.js';
  import { savedFilesState } from '$lib/stores/navigation.js';
  import { user, offlineMode } from '$lib/stores/app.js';
  import AccessControl from '$lib/components/admin/AccessControl.svelte';
  import { subscribeForOffline, unsubscribeFromOffline, isSubscribed, autoSyncFileOnOpen, connectionMode as syncConnectionMode } from '$lib/stores/sync.js';
  import { clipboard, copyToClipboard, cutToClipboard, clearClipboard, getClipboard, isItemCut } from '$lib/stores/clipboard.js';
  import { pushAction, undo, redo, ActionTypes, undoStack, redoStack } from '$lib/stores/undoStack.js';
  import ExplorerSearch from '$lib/components/ldm/ExplorerSearch.svelte';

  const dispatch = createEventDispatcher();
  const API_BASE = getApiBase();

  // Props
  let {
    projects = $bindable([]),
    selectedProjectId = $bindable(null),
    selectedFileId = $bindable(null),
    selectedTMId = $bindable(),  // P11-FIX: Add missing prop that LDM.svelte binds to
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
  let showMoveConfirm = $state(false);  // EXPLORER-006: Move confirmation
  let pendingMoveOperation = $state(null);  // { items, targetProjectId, targetFolderId, operation }
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

  // P9: Offline mode permission checks
  // In offline mode, user can only work freely in Offline Storage
  // Downloaded content is read-only structure (can edit row content, not rename/move/delete)
  let isInOfflineStorage = $derived(currentPath[0]?.type === 'offline-storage');
  let canModifyStructure = $derived(!$offlineMode || isInOfflineStorage);

  // P9: Helper to check if item is any folder type (regular or local)
  function isFolderType(item) {
    return item?.type === 'folder' || item?.type === 'local-folder';
  }
  function isFileType(item) {
    return item?.type === 'file' || item?.type === 'local-file';
  }

  // P9: Track offline mode changes to reload root (show/hide Offline Storage)
  let prevOfflineMode = $state(false);
  $effect(() => {
    const currentOffline = $offlineMode;
    if (currentOffline !== prevOfflineMode) {
      prevOfflineMode = currentOffline;
      // Reload root to show/hide Offline Storage
      if (currentPath.length === 0) {
        loadRoot();
      }
    }
  });

  // Clipboard reactive state
  let clipboardItems = $derived($clipboard.items);
  let clipboardOperation = $derived($clipboard.operation);

  // Check if item is cut (for visual feedback)
  function checkItemCut(itemId) {
    return isItemCut(itemId);
  }

  // ============== Navigation ==============

  // Load root level: platforms + unassigned projects
  async function loadRoot() {
    loading = true;
    try {
      // P9: Check offline mode first - in offline mode, show Offline Storage even if APIs fail
      const isOffline = get(offlineMode);

      // Fetch platforms, projects, and local file count in parallel
      // Use Promise.allSettled to continue even if some fail (important for offline mode)
      const [platformsResult, projectsResult, localFilesResult] = await Promise.allSettled([
        fetch(`${API_BASE}/api/ldm/platforms`, { headers: getAuthHeaders() }),
        fetch(`${API_BASE}/api/ldm/projects`, { headers: getAuthHeaders() }),
        fetch(`${API_BASE}/api/ldm/offline/local-file-count`, { headers: getAuthHeaders() })
      ]);

      let platformList = [];
      if (platformsResult.status === 'fulfilled' && platformsResult.value.ok) {
        const data = await platformsResult.value.json();
        platformList = data.platforms || [];
        platforms = platformList;
      }

      let projectList = [];
      if (projectsResult.status === 'fulfilled' && projectsResult.value.ok) {
        projectList = await projectsResult.value.json();
        projects = projectList;
      }

      // P9: Check for local files (files in Offline Storage)
      let localFileCount = 0;
      if (localFilesResult.status === 'fulfilled' && localFilesResult.value.ok) {
        const data = await localFilesResult.value.json();
        localFileCount = data.count || 0;
      }

      // Build root items: Unassigned section + Platforms
      const items = [];

      // BUG-043: Always show Offline Storage so users can create folders even when empty
      // P9: In offline mode, it's the primary workspace
      // In online mode, it's for local/offline work
      logger.debug('loadRoot: isOffline =', isOffline, 'localFileCount =', localFileCount);
      items.push({
        type: 'offline-storage',
        id: 'offline-storage',
        name: 'Offline Storage',
        description: isOffline
          ? 'Your offline workspace - work here, sync when online'
          : localFileCount > 0
            ? `${localFileCount} file${localFileCount !== 1 ? 's' : ''} synced for offline`
            : 'Your local workspace for offline files',
        file_count: localFileCount,
        isOfflineMode: isOffline  // Flag for special styling
      });

      // P9: In offline mode, hide PostgreSQL data - only show Offline Storage
      // User's sandbox is Offline Storage; PostgreSQL data is read-only and confusing to show
      if (!isOffline) {
        // Add platforms (UI-107: Filter out "Offline Storage" platform to avoid duplicate with CloudOffline entry)
        platformList
          .filter(p => p.name !== 'Offline Storage')  // UI-107: Hide PostgreSQL platform, keep only CloudOffline
          .forEach(p => {
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
      }

      // EXPLORER-008: Add Recycle Bin at the end
      items.push({
        type: 'recycle-bin',
        id: 'trash',
        name: 'Recycle Bin',
        description: 'Deleted items (30-day retention)'
      });

      currentItems = items;
      currentPath = [];
      selectedProjectId = null;
      selectedPlatformId = null;
      logger.info('Loaded root', { platforms: platformList.length, localFiles: localFileCount, offlineMode: isOffline });
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
  // preservePath: if true, append project to existing path (for platform > project navigation)
  async function loadProjectContents(projectId, preservePath = false) {
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
        const projectCrumb = { type: 'project', id: projectId, name: data.project?.name || 'Project' };
        if (preservePath) {
          // Append project to existing path (keeps platform context)
          currentPath = [...currentPath, projectCrumb];
        } else {
          // Replace path (direct project access from root)
          currentPath = [projectCrumb];
        }
        selectedProjectId = projectId;
        logger.info('Loaded project contents', { projectId, items: items.length, preservePath });
      }
    } catch (err) {
      logger.error('Failed to load project contents', { error: err.message });
    } finally {
      loading = false;
    }
  }

  // Load folder contents (navigates INTO folder - appends to path)
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

  // Reload current folder contents (refresh only - does NOT modify path)
  async function reloadCurrentFolderContents(folderId) {
    loading = true;
    try {
      const response = await fetch(`${API_BASE}/api/ldm/folders/${folderId}`, {
        headers: getAuthHeaders()
      });
      if (response.ok) {
        const data = await response.json();
        currentItems = [
          ...(data.subfolders || []).map(f => ({ type: 'folder', id: f.id, name: f.name, file_count: f.file_count || 0 })),
          ...(data.files || []).map(f => ({ type: 'file', id: f.id, name: f.name, format: f.format, row_count: f.row_count }))
        ];
        logger.info('Reloaded folder contents', { folderId, items: currentItems.length });
      }
    } catch (err) {
      logger.error('Failed to reload folder contents', { error: err.message });
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
    } else if (index === 0 && currentPath[0]?.type === 'offline-storage') {
      // P9: Go to Offline Storage root
      loadOfflineStorageContents();
    } else if (index === 1 && currentPath[0]?.type === 'platform' && currentPath[1]?.type === 'project') {
      // Go to project inside platform - preserve platform context
      const projectId = currentPath[1].id;
      currentPath = [currentPath[0]]; // Keep platform only
      loadProjectContents(projectId, true); // preservePath = true to append project
    } else {
      // Go to specific folder
      const target = currentPath[index];
      currentPath = currentPath.slice(0, index);
      if (target.type === 'folder') {
        loadFolderContents(target.id, target.name);
      } else if (target.type === 'local-folder') {
        // P9: Navigate into local folder, update path first
        currentPath = [...currentPath, target];
        loadOfflineStorageContents(target.id);
      }
    }
  }

  // EXPLORER-004: Navigate to search result path (Svelte 5 callback prop)
  async function navigateToSearchResult(path) {
    if (!path || path.length === 0) return;

    const lastItem = path[path.length - 1];

    // Build navigation path (exclude the target item itself if it's a file)
    if (lastItem.type === 'file') {
      // For files, navigate to parent folder/project then select the file
      const parentPath = path.slice(0, -1);
      await navigateToPath(parentPath);
      // Select the file
      selectedFileId = lastItem.id;
      selectedItem = { ...lastItem, type: 'file' };
    } else {
      // For platforms/projects/folders, navigate directly
      await navigateToPath(path);
    }
  }

  async function navigateToPath(path) {
    if (!path || path.length === 0) {
      await loadRoot();
      return;
    }

    const first = path[0];
    if (first.type === 'platform') {
      await loadPlatformContents(first.id, first.name);
      if (path.length > 1) {
        const project = path[1];
        if (project.type === 'project') {
          await loadProjectContents(project.id);
          // Load subsequent folders
          for (let i = 2; i < path.length; i++) {
            const folder = path[i];
            if (folder.type === 'folder') {
              await loadFolderContents(folder.id, folder.name);
            }
          }
        }
      }
    } else if (first.type === 'project') {
      await loadProjectContents(first.id);
      // Load subsequent folders
      for (let i = 1; i < path.length; i++) {
        const folder = path[i];
        if (folder.type === 'folder') {
          await loadFolderContents(folder.id, folder.name);
        }
      }
    }
  }

  // EXPLORER-004: Search action handlers (Svelte 5 callback props)
  function handleSearchCopy(item) {
    copyToClipboard([item]);
    logger.info('Copied from search', { name: item.name });
  }

  function handleSearchCut(item) {
    cutToClipboard([item]);
    logger.info('Cut from search', { name: item.name });
  }

  async function handleSearchDelete(item) {
    const { type, id, name } = item;

    // Build URL based on type
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
        logger.success(`${type} deleted from search`, { name });
        // Refresh current view if we're viewing the affected area
        await refreshCurrentView();
      } else {
        const error = await response.json().catch(() => ({}));
        logger.error('Delete from search failed', { error: error.detail });
      }
    } catch (err) {
      logger.error('Delete from search error', { error: err.message });
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

    // P9: Determine target ID based on target folder type
    // For regular folders: use folder ID or null for project root
    // For local-folder: use folder ID or null for Offline Storage root
    // For offline-storage root: target is null
    let targetId;
    if (targetFolder.type === 'project' || targetFolder.type === 'offline-storage') {
      targetId = null;  // Root level
    } else {
      targetId = targetFolder.id;
    }

    // OPTIMISTIC UI: Immediately remove items from current view
    const movedItemIds = new Set(items.map(i => i.id));
    const originalItems = [...currentItems];  // Backup for rollback
    currentItems = currentItems.filter(item => !movedItemIds.has(item.id));

    // Clear selection since items are "gone"
    selectedIds = [];

    logger.success('Items moved', { count: items.length, target: targetFolder.name });

    // Background: Send API requests (don't block UI)
    const failedItems = [];

    for (const item of items) {
      try {
        let url;
        let response;

        if (item.type === 'file') {
          // Regular file move: PATCH with query param
          const params = targetId !== null ? `?folder_id=${targetId}` : '';
          url = `${API_BASE}/api/ldm/files/${item.id}/move${params}`;
          response = await fetch(url, {
            method: 'PATCH',
            headers: getAuthHeaders()
          });
        } else if (item.type === 'folder') {
          // Regular folder move: PATCH with query param
          const params = targetId !== null ? `?parent_folder_id=${targetId}` : '';
          url = `${API_BASE}/api/ldm/folders/${item.id}/move${params}`;
          response = await fetch(url, {
            method: 'PATCH',
            headers: getAuthHeaders()
          });
        } else if (item.type === 'local-file') {
          // P9: Local file move within Offline Storage
          const params = targetId !== null ? `?target_folder_id=${targetId}` : '';
          url = `${API_BASE}/api/ldm/offline/storage/files/${item.id}/move${params}`;
          response = await fetch(url, {
            method: 'PATCH',
            headers: getAuthHeaders()
          });
        } else if (item.type === 'local-folder') {
          // P9: Local folder move within Offline Storage
          const params = targetId !== null ? `?target_parent_id=${targetId}` : '';
          url = `${API_BASE}/api/ldm/offline/storage/folders/${item.id}/move${params}`;
          response = await fetch(url, {
            method: 'PATCH',
            headers: getAuthHeaders()
          });
        }

        if (response && !response.ok) {
          failedItems.push(item);
          const error = await response.json().catch(() => ({}));
          logger.error('Move failed', { item: item.name, error: error.detail });
        }
      } catch (err) {
        failedItems.push(item);
        logger.error('Move error', { item: item.name, error: err.message });
      }
    }

    // If any moves failed, restore those items to the view
    if (failedItems.length > 0) {
      const failedIds = new Set(failedItems.map(i => i.id));
      const itemsToRestore = originalItems.filter(item => failedIds.has(item.id));
      currentItems = [...currentItems, ...itemsToRestore];
      logger.error(`${failedItems.length} item(s) failed to move`);
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

    // GDP: BUG-042 Debug
    logger.warning('GDP: FilesPage handleEnterFolder received', {
      itemType: item.type,
      itemId: item.id,
      itemName: item.name
    });

    if (item.type === 'platform') {
      loadPlatformContents(item.id, item.name);
    } else if (item.type === 'project') {
      // If inside a platform, preserve platform in breadcrumb path
      const insidePlatform = currentPath.length > 0 && currentPath[0].type === 'platform';
      loadProjectContents(item.id, insidePlatform);
    } else if (item.type === 'folder') {
      loadFolderContents(item.id, item.name);
    } else if (item.type === 'local-folder') {
      // P9: Navigate into local folder in Offline Storage
      loadLocalFolderContents(item.id, item.name);
    } else if (item.type === 'recycle-bin') {
      // EXPLORER-008: Enter Recycle Bin
      loadTrashContents();
    } else if (item.type === 'offline-storage') {
      // P3-PHASE5: Enter Offline Storage
      loadOfflineStorageContents();
    }
  }

  // P9: Load local folder contents in Offline Storage
  async function loadLocalFolderContents(folderId, folderName) {
    // Add folder to path
    currentPath = [...currentPath, { type: 'local-folder', id: folderId, name: folderName }];
    await loadOfflineStorageContents(folderId);
  }

  // P9: Load Offline Storage contents (local files and folders)
  async function loadOfflineStorageContents(parentId = null) {
    loading = true;
    try {
      const url = parentId
        ? `${API_BASE}/api/ldm/offline/local-files?parent_id=${parentId}`
        : `${API_BASE}/api/ldm/offline/local-files`;

      const response = await fetch(url, {
        headers: getAuthHeaders()
      });

      if (response.ok) {
        const data = await response.json();

        // Convert local folders to display format
        const folders = (data.folders || []).map(f => ({
          type: 'local-folder',  // P9: Local folder in Offline Storage
          id: f.id,
          name: f.name,
          parent_id: f.parent_id,
          created_at: f.created_at
        }));

        // Convert local files to display format
        const files = data.files.map(f => ({
          type: 'local-file',  // P9: Local file in Offline Storage
          id: f.id,
          name: f.name,
          format: f.format,
          row_count: f.row_count,
          error_message: f.error_message,
          updated_at: f.updated_at
        }));

        currentItems = [...folders, ...files];

        // Update path only if at root (not navigating into subfolder)
        if (parentId === null) {
          currentPath = [{ type: 'offline-storage', id: 'offline-storage', name: 'Offline Storage' }];
        }

        selectedProjectId = null;
        selectedPlatformId = null;

        logger.info('Loaded offline storage', { folders: folders.length, files: files.length });
      }
    } catch (err) {
      logger.error('Failed to load offline storage', { error: err.message });
    } finally {
      loading = false;
    }
  }

  // EXPLORER-008 + P9-BIN-001: Load Recycle Bin contents (both PostgreSQL and SQLite)
  async function loadTrashContents() {
    // GDP: BUG-042 Debug
    logger.warning('GDP: loadTrashContents called');
    loading = true;
    try {
      let allTrashItems = [];

      // 1. Fetch PostgreSQL trash (online items)
      const pgResponse = await fetch(`${API_BASE}/api/ldm/trash`, {
        headers: getAuthHeaders()
      });

      if (pgResponse.ok) {
        const pgData = await pgResponse.json();
        const pgItems = pgData.items.map(item => ({
          type: 'trash-item',
          id: item.id,
          trash_id: item.id,
          item_type: item.item_type,
          item_id: item.item_id,
          name: item.item_name,
          deleted_at: item.deleted_at,
          expires_at: item.expires_at,
          parent_project_id: item.parent_project_id,
          parent_folder_id: item.parent_folder_id,
          isLocal: false  // PostgreSQL trash
        }));
        allTrashItems = allTrashItems.concat(pgItems);
      }

      // 2. P9-BIN-001: Fetch SQLite trash (local Offline Storage items)
      const localResponse = await fetch(`${API_BASE}/api/ldm/offline/trash`, {
        headers: getAuthHeaders()
      });

      if (localResponse.ok) {
        const localData = await localResponse.json();
        const localItems = localData.items.map(item => ({
          type: 'trash-item',
          id: `local-${item.id}`,  // Prefix to avoid ID collision
          trash_id: item.id,
          item_type: item.item_type,
          item_id: item.item_id,
          name: item.item_name,
          deleted_at: item.deleted_at,
          expires_at: item.expires_at,
          parent_folder_id: item.parent_folder_id,
          isLocal: true  // SQLite trash (Offline Storage)
        }));
        allTrashItems = allTrashItems.concat(localItems);
      }

      // Sort by deleted_at (newest first)
      allTrashItems.sort((a, b) => new Date(b.deleted_at) - new Date(a.deleted_at));

      currentItems = allTrashItems;
      currentPath = [{ type: 'recycle-bin', id: 'trash', name: 'Recycle Bin' }];
      selectedProjectId = null;
      selectedPlatformId = null;

      logger.info('Loaded trash contents', { count: allTrashItems.length });
    } catch (err) {
      logger.error('Failed to load trash', { error: err.message });
    } finally {
      loading = false;
    }
  }

  /**
   * EXPLORER-008: Restore item from trash
   * OPTIMISTIC UI: Item disappears from trash immediately
   * P9-BIN-001: Supports both PostgreSQL and SQLite trash
   */
  async function restoreFromTrash(trashId) {
    // OPTIMISTIC UI: Store original and remove immediately
    const restoredItem = currentItems.find(item => item.id === trashId || item.trash_id === trashId);
    const originalItems = [...currentItems];
    currentItems = currentItems.filter(item => item.id !== trashId && item.trash_id !== trashId);

    // P9-BIN-001: Check if this is a local (SQLite) trash item
    const isLocal = restoredItem?.isLocal === true;
    const actualTrashId = isLocal ? restoredItem.trash_id : trashId;
    const endpoint = isLocal
      ? `${API_BASE}/api/ldm/offline/trash/${actualTrashId}/restore`
      : `${API_BASE}/api/ldm/trash/${trashId}/restore`;

    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: getAuthHeaders()
      });

      if (response.ok) {
        const result = await response.json();
        const itemType = isLocal ? result.item_type : result.item_type;
        logger.success(`${itemType} restored`, { id: result.restored_id || result.item_id });
      } else {
        // OPTIMISTIC UI: Rollback on failure
        currentItems = originalItems;
        const error = await response.json();
        logger.error('Restore failed', { error: error.detail });
      }
    } catch (err) {
      // OPTIMISTIC UI: Rollback on error
      currentItems = originalItems;
      logger.error('Restore error', { error: err.message });
    }
  }

  /**
   * EXPLORER-008: Permanently delete from trash
   * OPTIMISTIC UI: Item disappears immediately
   * P9-BIN-001: Supports both PostgreSQL and SQLite trash
   */
  async function permanentDeleteFromTrash(trashId) {
    // OPTIMISTIC UI: Store original and remove immediately
    const deletedItem = currentItems.find(item => item.id === trashId || item.trash_id === trashId);
    const originalItems = [...currentItems];
    currentItems = currentItems.filter(item => item.id !== trashId && item.trash_id !== trashId);

    // P9-BIN-001: Check if this is a local (SQLite) trash item
    const isLocal = deletedItem?.isLocal === true;
    const actualTrashId = isLocal ? deletedItem.trash_id : trashId;
    const endpoint = isLocal
      ? `${API_BASE}/api/ldm/offline/trash/${actualTrashId}`
      : `${API_BASE}/api/ldm/trash/${trashId}`;

    try {
      const response = await fetch(endpoint, {
        method: 'DELETE',
        headers: getAuthHeaders()
      });

      if (response.ok) {
        logger.success('Item permanently deleted');
      } else {
        // OPTIMISTIC UI: Rollback on failure
        currentItems = originalItems;
        const error = await response.json();
        logger.error('Permanent delete failed', { error: error.detail });
      }
    } catch (err) {
      // OPTIMISTIC UI: Rollback on error
      currentItems = originalItems;
      logger.error('Permanent delete error', { error: err.message });
    }
  }

  /**
   * EXPLORER-008: Empty entire trash
   * OPTIMISTIC UI: All items disappear immediately
   * P9-BIN-001: Empties both PostgreSQL and SQLite trash
   */
  async function emptyTrash() {
    // OPTIMISTIC UI: Store original and clear immediately
    const originalItems = [...currentItems];
    currentItems = [];

    // P9-BIN-001: Check which trash sources have items
    const hasPostgresItems = originalItems.some(item => !item.isLocal);
    const hasLocalItems = originalItems.some(item => item.isLocal);

    let pgSuccess = true;
    let localSuccess = true;
    let pgResult = null;
    let localResult = null;

    try {
      // Empty PostgreSQL trash if it has items
      if (hasPostgresItems) {
        const pgResponse = await fetch(`${API_BASE}/api/ldm/trash/empty`, {
          method: 'POST',
          headers: getAuthHeaders()
        });
        pgSuccess = pgResponse.ok;
        if (pgSuccess) {
          pgResult = await pgResponse.json();
        }
      }

      // P9-BIN-001: Empty SQLite trash if it has items
      if (hasLocalItems) {
        const localResponse = await fetch(`${API_BASE}/api/ldm/offline/trash`, {
          method: 'DELETE',
          headers: getAuthHeaders()
        });
        localSuccess = localResponse.ok;
        if (localSuccess) {
          localResult = await localResponse.json();
        }
      }

      if (pgSuccess && localSuccess) {
        const totalDeleted = (pgResult?.deleted_count || 0) + (localResult?.deleted_count || 0);
        logger.success(`Recycle Bin emptied (${totalDeleted} items deleted)`);
      } else {
        // OPTIMISTIC UI: Partial rollback - keep items that failed to delete
        if (!pgSuccess) {
          currentItems = originalItems.filter(item => !item.isLocal);
        }
        if (!localSuccess) {
          currentItems = [...currentItems, ...originalItems.filter(item => item.isLocal)];
        }
        logger.error('Empty trash partially failed');
      }
    } catch (err) {
      // OPTIMISTIC UI: Rollback on error
      currentItems = originalItems;
      logger.error('Empty trash error', { error: err.message });
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
  // P9: These operations work for both 'file' (PostgreSQL) and 'local-file' (SQLite)
  // because the backend endpoints use unified fallback logic
  // Note: isFileType() and isFolderType() helpers are defined at the top of the script

  // Download
  async function downloadFile() {
    if (!isFileType(contextMenuItem)) return;
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
    if (!isFileType(contextMenuItem)) return;
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
    if (!isFileType(contextMenuItem)) return;
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
    if (!isFileType(contextMenuItem)) return;
    const file = { ...contextMenuItem };
    closeMenus();
    dispatch('runQA', { fileId: file.id, type: 'all', fileName: file.name });
  }

  // TM Registration
  let tmRegistrationFile = $state(null);

  function openTMRegistration() {
    if (!isFileType(contextMenuItem)) return;
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
    if (!isFileType(contextMenuItem)) return;
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
    if (!isFileType(contextMenuItem)) return;
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
    if (!isFileType(contextMenuItem)) return;
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

  /**
   * OPTIMISTIC UI: Project appears immediately, rollback on failure
   */
  async function createProject() {
    if (!newProjectName.trim()) return;

    const projectName = newProjectName.trim();
    const tempId = `temp_project_${Date.now()}`;

    // OPTIMISTIC UI: Add project immediately with temp ID
    const optimisticProject = {
      type: 'project',
      id: tempId,
      name: projectName,
      file_count: 0,
      platform_id: selectedPlatformId,
      _optimistic: true
    };
    currentItems = [...currentItems, optimisticProject];

    // Close modal immediately for snappy feel
    showCreateProjectModal = false;
    newProjectName = '';

    try {
      // Build request body - include platform_id if we're inside a platform
      const requestBody = { name: projectName };
      if (selectedPlatformId) {
        requestBody.platform_id = selectedPlatformId;
      }

      const response = await fetch(`${API_BASE}/api/ldm/projects`, {
        method: 'POST',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody)
      });

      if (response.ok) {
        logger.success('Project created', { name: projectName, platformId: selectedPlatformId });
        // Refresh to get real ID from server
        if (selectedPlatformId && currentPath.length > 0 && currentPath[0].type === 'platform') {
          await loadPlatformContents(selectedPlatformId, currentPath[0].name);
        } else {
          await loadRoot();
        }
      } else {
        // OPTIMISTIC UI: Rollback on failure
        currentItems = currentItems.filter(item => item.id !== tempId);
        const error = await response.json();
        logger.error('Failed to create project', { error: error.detail });
      }
    } catch (err) {
      // OPTIMISTIC UI: Rollback on error
      currentItems = currentItems.filter(item => item.id !== tempId);
      logger.error('Error creating project', { error: err.message });
    }
  }

  /**
   * OPTIMISTIC UI: Folder appears immediately, rollback on failure
   * P9: Uses offline endpoint when in Offline Storage
   */
  async function createFolder() {
    // GDP: BUG-043 Debug
    logger.warning('GDP: createFolder called', {
      folderName: newFolderName,
      isInOfflineStorage,
      selectedProjectId,
      currentPath: currentPath.map(p => ({ type: p.type, id: p.id, name: p.name }))
    });

    if (!newFolderName.trim()) {
      logger.warning('GDP: createFolder - empty name, returning');
      return;
    }

    // P9: In Offline Storage, we don't need selectedProjectId
    if (!isInOfflineStorage && !selectedProjectId) {
      logger.warning('GDP: createFolder - not in offline storage and no project selected, returning');
      return;
    }

    const folderName = newFolderName.trim();
    // FIX: Only use parent_id if we're inside a folder, not just inside a project
    const lastPathItem = currentPath[currentPath.length - 1];
    const parentFolderId = (lastPathItem?.type === 'folder' || lastPathItem?.type === 'local-folder') ? lastPathItem.id : null;
    const tempId = `temp_folder_${Date.now()}`;

    // OPTIMISTIC UI: Add folder immediately with temp ID
    const optimisticFolder = {
      type: isInOfflineStorage ? 'local-folder' : 'folder',  // P9: Use correct type
      id: tempId,
      name: folderName,
      file_count: 0,
      _optimistic: true
    };
    currentItems = [...currentItems, optimisticFolder];

    // Close modal immediately for snappy feel
    showCreateFolderModal = false;
    newFolderName = '';

    try {
      let response;

      if (isInOfflineStorage) {
        // P9: Create folder in SQLite Offline Storage
        logger.warning('GDP: Creating folder in Offline Storage', { folderName, parentFolderId });
        response = await fetch(`${API_BASE}/api/ldm/offline/storage/folders`, {
          method: 'POST',
          headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name: folderName,
            parent_id: parentFolderId
          })
        });
        logger.warning('GDP: Offline folder API response', { status: response.status, ok: response.ok });
      } else {
        // Standard PostgreSQL folder creation
        response = await fetch(`${API_BASE}/api/ldm/folders`, {
          method: 'POST',
          headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name: folderName,
            project_id: selectedProjectId,
            parent_id: parentFolderId
          })
        });
      }

      if (response.ok) {
        const data = await response.json();
        logger.success('Folder created', { name: data.name || folderName });

        if (isInOfflineStorage) {
          // P9: Update optimistic folder with real ID from server
          currentItems = currentItems.map(item =>
            item.id === tempId
              ? { ...item, id: data.id, name: data.name, _optimistic: false }
              : item
          );
        } else {
          // Refresh to get real ID from server (PostgreSQL)
          if (currentPath.length === 1) {
            await loadProjectContents(selectedProjectId);
          } else {
            const currentFolder = currentPath[currentPath.length - 1];
            await reloadCurrentFolderContents(currentFolder.id);
          }
        }
      } else {
        // OPTIMISTIC UI: Rollback on failure
        currentItems = currentItems.filter(item => item.id !== tempId);
        const error = await response.json();
        logger.error('Failed to create folder', { error: error.detail });
      }
    } catch (err) {
      // OPTIMISTIC UI: Rollback on error
      currentItems = currentItems.filter(item => item.id !== tempId);
      logger.error('Error creating folder', { error: err.message });
    }
  }

  /**
   * OPTIMISTIC UI: Platform appears immediately, rollback on failure
   */
  async function createPlatform() {
    if (!newPlatformName.trim()) return;

    const platformName = newPlatformName.trim();
    const tempId = `temp_platform_${Date.now()}`;

    // OPTIMISTIC UI: Add platform immediately with temp ID
    const optimisticPlatform = {
      type: 'platform',
      id: tempId,
      name: platformName,
      project_count: 0,
      _optimistic: true
    };
    currentItems = [...currentItems, optimisticPlatform];

    // Close modal immediately for snappy feel
    showCreatePlatformModal = false;
    newPlatformName = '';

    try {
      const response = await fetch(`${API_BASE}/api/ldm/platforms`, {
        method: 'POST',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: platformName })
      });

      if (response.ok) {
        logger.success('Platform created', { name: platformName });
        // Refresh to get real ID from server
        await loadRoot();
      } else {
        // OPTIMISTIC UI: Rollback on failure
        currentItems = currentItems.filter(item => item.id !== tempId);
        const error = await response.json();
        logger.error('Failed to create platform', { error: error.detail });
      }
    } catch (err) {
      // OPTIMISTIC UI: Rollback on error
      currentItems = currentItems.filter(item => item.id !== tempId);
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
    // P9: Allow upload when in Offline Storage (no projectId needed)
    const inOfflineStorage = currentPath[0]?.type === 'offline-storage';
    if (!selectedProjectId && !inOfflineStorage) return;

    // FIX: Only set folder_id if we're inside a folder, not just inside a project
    const lastItem = currentPath[currentPath.length - 1];
    uploadTargetFolderId = (lastItem?.type === 'folder' || lastItem?.type === 'local-folder') ? lastItem.id : null;
    if (fileInput) fileInput.click();
  }

  async function handleFileUpload(event) {
    const files = event.target.files;
    if (!files?.length) return;

    // P9: Check if uploading to Offline Storage
    const inOfflineStorage = currentPath[0]?.type === 'offline-storage';

    if (inOfflineStorage) {
      // P9: Upload to Offline Storage via unified endpoint with storage=local
      // Backend parses the file properly (same as PostgreSQL upload)

      // P9-FIX: Get current folder ID if inside a local folder
      // Path structure: [offline-storage, local-folder?, local-folder?, ...]
      const currentFolderId = currentPath.length > 1 && currentPath[currentPath.length - 1].type === 'local-folder'
        ? currentPath[currentPath.length - 1].id
        : null;

      for (const file of files) {
        // P11: Track upload in Task Manager
        const tracker = createTracker('LDM', `Upload: ${file.name}`);
        tracker.start();
        tracker.setMetadata({ filename: file.name });

        try {
          tracker.update(10, 'Preparing upload...');
          const formData = new FormData();
          formData.append('file', file);
          formData.append('storage', 'local');
          // P9-FIX: Include folder_id if inside a local folder
          if (currentFolderId !== null) {
            formData.append('folder_id', currentFolderId);
          }

          tracker.update(30, 'Uploading to server...');
          const response = await fetch(`${API_BASE}/api/ldm/files/upload`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: formData
          });

          if (response.ok) {
            const result = await response.json();
            tracker.setMetadata({ rowCount: result.row_count });
            tracker.complete(`Imported ${result.row_count} rows`, { rowCount: result.row_count });
            logger.success('File imported to Offline Storage', { name: file.name, rows: result.row_count });
          } else {
            const error = await response.json();
            tracker.fail(error.detail || 'Import failed');
            logger.error('Import failed', { name: file.name, error: error.detail });
          }
        } catch (err) {
          tracker.fail(err.message);
          logger.error('Import error', { error: err.message });
        }
      }

      // Refresh Offline Storage
      await loadOfflineStorageContents();
    } else {
      // Normal upload to project/folder
      if (!selectedProjectId) return;

      for (const file of files) {
        // P11: Track upload in Task Manager
        const tracker = createTracker('LDM', `Upload: ${file.name}`);
        tracker.start();
        tracker.setMetadata({ filename: file.name });

        const formData = new FormData();
        formData.append('project_id', selectedProjectId);
        if (uploadTargetFolderId) {
          formData.append('folder_id', uploadTargetFolderId);
        }
        formData.append('file', file);

        try {
          tracker.update(30, 'Uploading to server...');
          const response = await fetch(`${API_BASE}/api/ldm/files/upload`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: formData
          });
          if (response.ok) {
            const result = await response.json();
            tracker.setMetadata({ rowCount: result.row_count });
            tracker.complete(`Uploaded ${result.row_count} rows`, { rowCount: result.row_count });
            logger.success('File uploaded', { name: file.name, rows: result.row_count });
          } else {
            const error = await response.json();
            tracker.fail(error.detail || 'Upload failed');
            logger.error('Upload failed', { name: file.name, error: error.detail });
          }
        } catch (err) {
          tracker.fail(err.message);
          logger.error('Upload error', { error: err.message });
        }
      }

      // Refresh current view (stay in context)
      if (currentPath.length === 1) {
        await loadProjectContents(selectedProjectId);
      } else if (currentPath.length > 1) {
        // Inside a folder - reload without modifying path
        const currentFolder = currentPath[currentPath.length - 1];
        await reloadCurrentFolderContents(currentFolder.id);
      }
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

  /**
   * OPTIMISTIC UI: Rename updates immediately, rollback on failure
   */
  async function executeRename() {
    if (!contextMenuItem || !renameValue.trim()) return;
    const { type, id } = contextMenuItem;
    const newName = renameValue.trim();
    let url;
    let method = 'PATCH';
    let body = null;

    if (type === 'platform') {
      url = `${API_BASE}/api/ldm/platforms/${id}`;
      body = JSON.stringify({ name: newName });
    } else if (type === 'project') {
      url = `${API_BASE}/api/ldm/projects/${id}/rename?name=${encodeURIComponent(newName)}`;
    } else if (type === 'folder') {
      url = `${API_BASE}/api/ldm/folders/${id}/rename?name=${encodeURIComponent(newName)}`;
    } else if (type === 'file') {
      url = `${API_BASE}/api/ldm/files/${id}/rename?name=${encodeURIComponent(newName)}`;
    } else if (type === 'local-file') {
      // P9: Rename local file in Offline Storage
      url = `${API_BASE}/api/ldm/offline/storage/files/${id}/rename`;
      method = 'PUT';
      body = JSON.stringify({ new_name: newName });
    }

    // OPTIMISTIC UI: Store original name for rollback
    const originalName = contextMenuItem.name;

    // OPTIMISTIC UI: Update item name immediately
    currentItems = currentItems.map(item =>
      item.id === id && item.type === type
        ? { ...item, name: newName }
        : item
    );

    // Close modal immediately
    showRenameModal = false;

    try {
      const headers = body
        ? { ...getAuthHeaders(), 'Content-Type': 'application/json' }
        : getAuthHeaders();
      const response = await fetch(url, { method, headers, body });
      if (response.ok) {
        logger.success(`${type} renamed`, { id, newName });
      } else {
        // OPTIMISTIC UI: Rollback on failure
        currentItems = currentItems.map(item =>
          item.id === id && item.type === type
            ? { ...item, name: originalName }
            : item
        );
        const error = await response.json();
        logger.error('Rename failed', { error: error.detail });
      }
    } catch (err) {
      // OPTIMISTIC UI: Rollback on error
      currentItems = currentItems.map(item =>
        item.id === id && item.type === type
          ? { ...item, name: originalName }
          : item
      );
      logger.error('Rename error', { error: err.message });
    }
  }

  /**
   * Generate type-aware delete confirmation message (EXPLORER-006)
   */
  function getDeleteConfirmMessage(item) {
    // Multi-select delete
    if (selectedIds.length > 1) {
      const count = selectedIds.length;
      return `Delete ${count} selected items? Items will be moved to the Recycle Bin.`;
    }

    if (!item) return 'Are you sure you want to delete this item?';

    const name = item.name || 'this item';
    switch (item.type) {
      case 'platform':
        return `Delete platform "${name}" and ALL projects, folders, and files inside?`;
      case 'project':
        return `Delete project "${name}" and ALL folders and files inside?`;
      case 'folder':
        return `Delete folder "${name}" and ALL its contents?`;
      case 'file':
        return `Delete file "${name}"?`;
      case 'local-file':
        return `Delete "${name}" from Offline Storage? This action is permanent.`;
      default:
        return `Delete "${name}"?`;
    }
  }

  function openDelete() {
    // Allow delete if multi-select OR single context item
    if (selectedIds.length === 0 && !contextMenuItem) return;
    // Don't clear contextMenuItem - needed for executeDelete
    showContextMenu = false;
    showBackgroundMenu = false;
    showDeleteConfirm = true;
  }

  async function executeDelete() {
    // Determine items to delete: multi-select OR single context item
    let itemsToDelete = [];

    if (selectedIds.length > 1) {
      // Multi-select delete
      itemsToDelete = currentItems.filter(item => selectedIds.includes(item.id));
    } else if (contextMenuItem) {
      // Single item delete
      itemsToDelete = [contextMenuItem];
    }

    if (itemsToDelete.length === 0) return;

    // OPTIMISTIC UI: Remove all items immediately
    const originalItems = [...currentItems];
    const deleteIds = itemsToDelete.map(item => item.id);
    currentItems = currentItems.filter(item => !deleteIds.includes(item.id));
    showDeleteConfirm = false;

    // Track failures for partial rollback
    const failures = [];

    // Delete all items in parallel
    const deletePromises = itemsToDelete.map(async (item) => {
      const { type, id, name } = item;
      let url;
      if (type === 'platform') {
        url = `${API_BASE}/api/ldm/platforms/${id}`;
      } else if (type === 'project') {
        url = `${API_BASE}/api/ldm/projects/${id}`;
      } else if (type === 'folder') {
        url = `${API_BASE}/api/ldm/folders/${id}`;
      } else if (type === 'file') {
        url = `${API_BASE}/api/ldm/files/${id}`;
      } else if (type === 'local-file') {
        // P9: Delete local file from Offline Storage
        url = `${API_BASE}/api/ldm/offline/storage/files/${id}`;
      } else if (type === 'local-folder') {
        // P9: Delete local folder from Offline Storage
        url = `${API_BASE}/api/ldm/offline/storage/folders/${id}`;
      }

      try {
        const response = await fetch(url, { method: 'DELETE', headers: getAuthHeaders() });
        if (!response.ok) {
          failures.push(item);
          const error = await response.json().catch(() => ({}));
          logger.error('Delete failed', { item: name, error: error.detail });
        }
      } catch (err) {
        failures.push(item);
        logger.error('Delete error', { item: name, error: err.message });
      }
    });

    await Promise.all(deletePromises);

    // Handle results
    if (failures.length > 0) {
      // OPTIMISTIC UI: Partial rollback - restore failed items
      currentItems = [...currentItems, ...failures];
      logger.warning(`${failures.length} item(s) failed to delete`);
    }

    if (failures.length < itemsToDelete.length) {
      const successCount = itemsToDelete.length - failures.length;
      logger.success(`${successCount} item(s) deleted`);

      // EXPLORER-007: Push undo action (for single delete only)
      if (itemsToDelete.length === 1 && failures.length === 0) {
        const { type, id, name } = itemsToDelete[0];
        const trashResponse = await fetch(`${API_BASE}/api/ldm/trash`, { headers: getAuthHeaders() });
        if (trashResponse.ok) {
          const trashData = await trashResponse.json();
          const trashItem = trashData.items.find(t =>
            t.item_type === type && t.item_name === name
          );
          if (trashItem) {
            pushAction({
              type: ActionTypes.DELETE,
              data: { trashId: trashItem.id, itemType: type, itemName: name },
              description: `Delete ${type} "${name}"`,
              undo: async () => {
                await restoreFromTrash(trashItem.id);
              },
              redo: async () => {
                logger.warning('Redo delete not supported');
              }
            });
          }
        }
      }
    }

    // Clear selection
    contextMenuItem = null;
    selectedIds = [];
  }

  // ============== Clipboard Operations (EXPLORER-001) ==============

  /**
   * Handle copy operation (Ctrl+C)
   */
  function handleCopy() {
    const itemsToCopy = currentItems.filter(item => selectedIds.includes(item.id));
    if (itemsToCopy.length === 0 && selectedItem) {
      itemsToCopy.push(selectedItem);
    }
    if (itemsToCopy.length > 0) {
      copyToClipboard(itemsToCopy);
      logger.info('Copied to clipboard', { count: itemsToCopy.length, operation: 'copy' });
    }
  }

  /**
   * Handle cut operation (Ctrl+X)
   */
  function handleCut() {
    const itemsToCut = currentItems.filter(item => selectedIds.includes(item.id));
    if (itemsToCut.length === 0 && selectedItem) {
      itemsToCut.push(selectedItem);
    }
    if (itemsToCut.length > 0) {
      cutToClipboard(itemsToCut);
      logger.info('Cut to clipboard', { count: itemsToCut.length, operation: 'cut' });
    }
  }

  /**
   * Validate paste target based on hierarchy rules (EXPLORER-002)
   * Rules:
   * - Platform: Cannot receive files/folders (only projects)
   * - Project: Can only be pasted to platform or root
   * - Folder: Can be pasted to project or folder
   * - File: Can be pasted to project or folder
   */
  function validatePasteTarget(items, targetPath) {
    // Rule 1: Files/Folders cannot paste into platform directly
    if (targetPath.length === 1 && targetPath[0].type === 'platform') {
      const hasFilesOrFolders = items.some(i => i.type === 'file' || i.type === 'folder');
      if (hasFilesOrFolders) {
        return { valid: false, reason: 'Files and folders cannot be placed directly in platforms. Move to a project instead.' };
      }
    }

    // Rule 2: Projects can only go to platform or root (not inside folders)
    const hasProjects = items.some(i => i.type === 'project');
    if (hasProjects && targetPath.length > 1) {
      const lastItem = targetPath[targetPath.length - 1];
      if (lastItem.type === 'folder') {
        return { valid: false, reason: 'Projects cannot be placed inside folders. Move to a platform or root.' };
      }
    }

    // Rule 3: Cannot paste into self (circular reference)
    const itemIds = items.map(i => i.id);
    for (const crumb of targetPath) {
      if (itemIds.includes(crumb.id)) {
        return { valid: false, reason: 'Cannot paste an item into itself.' };
      }
    }

    return { valid: true };
  }

  /**
   * Check if move operation needs confirmation (EXPLORER-006)
   * Returns true for: project moves, cross-project folder/file moves
   */
  function needsMoveConfirmation(items, targetProjectId) {
    // Project moves always need confirmation
    if (items.some(i => i.type === 'project')) {
      return true;
    }

    // Cross-project moves need confirmation
    const crossProjectItems = items.filter(i =>
      (i.type === 'folder' || i.type === 'file') &&
      i.project_id && i.project_id !== targetProjectId
    );
    return crossProjectItems.length > 0;
  }

  /**
   * Get the current project name from path for confirmation message
   */
  function getTargetProjectName() {
    if (currentPath.length === 0) return 'root';
    // Find the project in the path
    for (const crumb of currentPath) {
      if (crumb.type === 'project') {
        return crumb.name;
      }
    }
    return currentPath[0]?.name || 'this location';
  }

  /**
   * Generate move confirmation message (EXPLORER-006)
   */
  function getMoveConfirmMessage(operation) {
    if (!operation) return 'Are you sure you want to move these items?';

    const { items, targetProjectName, isCrossProject } = operation;
    const itemNames = items.map(i => i.name).join(', ');
    const itemCount = items.length;

    if (items.some(i => i.type === 'project')) {
      // Project move
      const projectNames = items.filter(i => i.type === 'project').map(i => i.name).join(', ');
      return `Move project "${projectNames}" to "${targetProjectName}"? All files and folders will move with it.`;
    }

    if (isCrossProject) {
      // Cross-project move
      const sourceProject = items[0]?.project_name || 'source project';
      return `Move ${itemCount} item(s) from "${sourceProject}" to "${targetProjectName}"? This is a cross-project move.`;
    }

    return `Move "${itemNames}" to "${targetProjectName}"?`;
  }

  /**
   * Execute pending move operation after confirmation (EXPLORER-006)
   * OPTIMISTIC UI: Items appear in destination immediately
   */
  async function executePendingMove() {
    if (!pendingMoveOperation) return;

    const { items, targetProjectId, targetFolderId, isCrossProject, operation } = pendingMoveOperation;

    // Close modal immediately for snappy feel
    showMoveConfirm = false;

    // OPTIMISTIC UI: Store original state for rollback
    const originalItems = [...currentItems];

    // OPTIMISTIC UI: Add items to current view immediately
    const optimisticItems = items.map(item => ({
      ...item,
      _optimistic: true,
      project_id: targetProjectId,
      folder_id: targetFolderId
    }));
    currentItems = [...currentItems, ...optimisticItems];

    // Clear clipboard immediately
    clearClipboard();

    // Track failures
    const failures = [];

    try {
      for (const item of items) {
        let url;
        let method = 'PATCH';
        let body = null;

        if (item.type === 'file') {
          // EXPLORER-005: Check if cross-project move
          if (isCrossProject && item.project_id && item.project_id !== targetProjectId) {
            url = `${API_BASE}/api/ldm/files/${item.id}/move-cross-project?target_project_id=${targetProjectId}${targetFolderId !== null ? `&target_folder_id=${targetFolderId}` : ''}`;
          } else {
            const params = targetFolderId !== null ? `?folder_id=${targetFolderId}` : '';
            url = `${API_BASE}/api/ldm/files/${item.id}/move${params}`;
          }
        } else if (item.type === 'folder') {
          // EXPLORER-005: Check if cross-project move
          if (isCrossProject && item.project_id && item.project_id !== targetProjectId) {
            url = `${API_BASE}/api/ldm/folders/${item.id}/move-cross-project?target_project_id=${targetProjectId}${targetFolderId !== null ? `&target_parent_id=${targetFolderId}` : ''}`;
          } else {
            const params = targetFolderId !== null ? `?parent_folder_id=${targetFolderId}` : '';
            url = `${API_BASE}/api/ldm/folders/${item.id}/move${params}`;
          }
        } else if (item.type === 'project') {
          // Project move - update platform assignment
          const targetPlatformId = currentPath[0]?.type === 'platform' ? currentPath[0].id : null;
          url = `${API_BASE}/api/ldm/projects/${item.id}`;
          body = JSON.stringify({ platform_id: targetPlatformId });
        }

        if (url) {
          const response = await fetch(url, {
            method,
            headers: body ? { ...getAuthHeaders(), 'Content-Type': 'application/json' } : getAuthHeaders(),
            body
          });
          if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            logger.error('Move failed', { item: item.name, error: error.detail });
            failures.push(item.id);
          }
        }
      }

      // OPTIMISTIC UI: Handle failures
      if (failures.length > 0) {
        currentItems = currentItems.filter(item => !failures.includes(item.id));
        logger.warning('Some items failed to move', { failed: failures.length });
      } else {
        logger.success('Items moved', { count: items.length });
      }

      // Refresh to get server state
      await refreshCurrentView();

    } catch (err) {
      // OPTIMISTIC UI: Full rollback on error
      logger.error('Move error', { error: err.message });
      currentItems = originalItems;
    } finally {
      pendingMoveOperation = null;
    }
  }

  /**
   * Handle paste operation (Ctrl+V)
   * Copy: Creates duplicates with auto-rename
   * Cut: Moves items to current location
   * OPTIMISTIC UI: Items appear immediately before API completes
   */
  async function handlePaste() {
    const { items, operation } = getClipboard();
    if (items.length === 0) return;

    // EXPLORER-002: Validate hierarchy rules
    const validation = validatePasteTarget(items, currentPath);
    if (!validation.valid) {
      logger.warning('Paste rejected', { reason: validation.reason });
      return;
    }

    // Determine target folder/project
    // FIX: Only set folder_id if we're inside a folder, not just inside a project
    const lastPathItem = currentPath[currentPath.length - 1];
    const targetFolderId = (lastPathItem?.type === 'folder' || lastPathItem?.type === 'local-folder') ? lastPathItem.id : null;
    const targetProjectId = selectedProjectId;

    if (!targetProjectId && currentPath.length > 0 && currentPath[0].type !== 'platform') {
      logger.warning('Cannot paste here - no project context');
      return;
    }

    // EXPLORER-006: Check if move needs confirmation
    if (operation === 'cut') {
      const isCrossProject = items.some(i =>
        (i.type === 'folder' || i.type === 'file') &&
        i.project_id && i.project_id !== targetProjectId
      );

      if (needsMoveConfirmation(items, targetProjectId)) {
        pendingMoveOperation = {
          items,
          targetProjectId,
          targetFolderId,
          targetProjectName: getTargetProjectName(),
          isCrossProject,
          operation
        };
        showMoveConfirm = true;
        return; // Wait for user confirmation
      }
    }

    // OPTIMISTIC UI: Store original state for rollback
    const originalItems = [...currentItems];

    // OPTIMISTIC UI: Add items to current view immediately
    const tempIdBase = Date.now();
    const optimisticItems = items.map((item, idx) => ({
      ...item,
      id: operation === 'copy' ? `temp_${tempIdBase}_${idx}` : item.id,
      name: operation === 'copy' ? `${item.name} (copy)` : item.name,
      _optimistic: true, // Mark as optimistic for visual feedback
      project_id: targetProjectId,
      folder_id: targetFolderId
    }));

    // Add optimistic items to current view
    currentItems = [...currentItems, ...optimisticItems];

    // Clear clipboard immediately for snappy feel
    clearClipboard();

    // Track failures for rollback
    const failures = [];

    try {
      if (operation === 'cut') {
        // Direct move (no confirmation needed for simple folder/file moves)
        for (const item of items) {
          let url;
          if (item.type === 'file') {
            const params = targetFolderId !== null ? `?folder_id=${targetFolderId}` : '';
            url = `${API_BASE}/api/ldm/files/${item.id}/move${params}`;
          } else if (item.type === 'folder') {
            const params = targetFolderId !== null ? `?parent_folder_id=${targetFolderId}` : '';
            url = `${API_BASE}/api/ldm/folders/${item.id}/move${params}`;
          }

          if (url) {
            const response = await fetch(url, {
              method: 'PATCH',
              headers: getAuthHeaders()
            });
            if (!response.ok) {
              const error = await response.json().catch(() => ({}));
              logger.error('Move failed', { item: item.name, error: error.detail });
              failures.push(item.id);
            }
          }
        }
        if (failures.length === 0) {
          logger.success('Items moved', { count: items.length });
        }
      } else if (operation === 'copy') {
        // Copy operation
        for (let i = 0; i < items.length; i++) {
          const item = items[i];
          let url;
          let body = {};

          if (item.type === 'file') {
            url = `${API_BASE}/api/ldm/files/${item.id}/copy`;
            body = {
              target_project_id: targetProjectId,
              target_folder_id: targetFolderId
            };
          } else if (item.type === 'folder') {
            url = `${API_BASE}/api/ldm/folders/${item.id}/copy`;
            body = {
              target_project_id: targetProjectId,
              target_parent_id: targetFolderId
            };
          }

          if (url) {
            const response = await fetch(url, {
              method: 'POST',
              headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
              body: JSON.stringify(body)
            });
            if (!response.ok) {
              const error = await response.json().catch(() => ({}));
              logger.error('Copy failed', { item: item.name, error: error.detail });
              failures.push(`temp_${tempIdBase}_${i}`);
            }
          }
        }
        if (failures.length === 0) {
          logger.success('Items copied', { count: items.length });
        }
      }

      // OPTIMISTIC UI: If any failures, remove failed items
      if (failures.length > 0) {
        currentItems = currentItems.filter(item => !failures.includes(item.id));
        logger.warning('Some items failed to paste', { failed: failures.length });
      }

      // Refresh to get real IDs and server state
      await refreshCurrentView();

    } catch (err) {
      // OPTIMISTIC UI: Full rollback on error
      logger.error('Paste error', { error: err.message });
      currentItems = originalItems;
    }
  }

  /**
   * Global keyboard handler for clipboard operations
   */
  function handleGlobalKeydown(event) {
    // Ignore if typing in input/textarea
    if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') return;

    // Escape clears clipboard
    if (event.key === 'Escape') {
      if ($clipboard.items.length > 0) {
        clearClipboard();
        logger.info('Clipboard cleared');
      }
      return;
    }

    // Ctrl/Cmd shortcuts
    if (event.ctrlKey || event.metaKey) {
      switch (event.key.toLowerCase()) {
        case 'c':
          event.preventDefault();
          handleCopy();
          break;
        case 'x':
          event.preventDefault();
          handleCut();
          break;
        case 'v':
          event.preventDefault();
          handlePaste();
          break;
        case 'z':
          // EXPLORER-007: Undo (Ctrl+Z)
          event.preventDefault();
          undo().then(async (success) => {
            if (success) {
              // Refresh current view after undo
              await refreshCurrentView();
            }
          });
          break;
        case 'y':
          // EXPLORER-007: Redo (Ctrl+Y)
          event.preventDefault();
          redo().then(async (success) => {
            if (success) {
              // Refresh current view after redo
              await refreshCurrentView();
            }
          });
          break;
      }
    }
  }

  // EXPLORER-007: Refresh current view helper
  async function refreshCurrentView() {
    if (currentPath.length === 0) {
      await loadRoot();
    } else if (currentPath[0]?.type === 'recycle-bin') {
      await loadTrashContents();
    } else if (currentPath[0]?.type === 'platform' && currentPath.length === 1) {
      await loadPlatformContents(currentPath[0].id, currentPath[0].name);
    } else if (currentPath.length === 1) {
      await loadProjectContents(selectedProjectId);
    } else {
      // Length > 1: could be project or folder at end
      const lastItem = currentPath[currentPath.length - 1];
      if (lastItem.type === 'folder') {
        // Use reload (doesn't modify path) instead of load (appends to path)
        await reloadCurrentFolderContents(lastItem.id);
      } else if (lastItem.type === 'project') {
        await loadProjectContents(lastItem.id);
      }
    }
  }

  // ============== Background Menu Actions ==============

  function bgCreateProject() {
    closeMenus();
    showCreateProjectModal = true;
  }

  function bgCreateFolder() {
    closeMenus();
    // P9: Allow folder creation in Offline Storage (no projectId needed)
    if (selectedProjectId || isInOfflineStorage) {
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
    // EXPLORER-001: Global keyboard handler for clipboard operations
    document.addEventListener('keydown', handleGlobalKeydown);
  });

  onDestroy(() => {
    document.removeEventListener('click', handleClickOutside);
    document.removeEventListener('keydown', handleGlobalKeydown);
  });

  // Expose methods
  export { loadProjects, refreshCurrentView };
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
        {#if crumb.type === 'offline-storage' || crumb.name === 'Offline Storage'}
          <CloudOffline size={16} />
        {:else if crumb.type === 'platform'}
          <Application size={16} />
        {:else}
          <Folder size={16} />
        {/if}
        <span>{crumb.name}</span>
      </button>
    {/each}

    <!-- EXPLORER-004: Search bar -->
    <div class="search-wrapper">
      <ExplorerSearch
        apiBase={API_BASE}
        isOfflineMode={$offlineMode}
        onnavigate={navigateToSearchResult}
        oncopy={handleSearchCopy}
        oncut={handleSearchCut}
        ondelete={handleSearchDelete}
      />
    </div>

    <!-- EXPLORER-001: Clipboard status indicator -->
    {#if clipboardItems.length > 0}
      <div class="clipboard-indicator">
        {#if clipboardOperation === 'cut'}
          <Cut size={14} />
        {:else}
          <Copy size={14} />
        {/if}
        <span>{clipboardItems.length} {clipboardOperation === 'cut' ? 'cut' : 'copied'}</span>
        <button class="clipboard-clear" onclick={() => clearClipboard()} title="Clear clipboard (Esc)">×</button>
      </div>
    {/if}
  </div>

  <!-- Explorer Grid -->
  <div class="grid-container">
    <ExplorerGrid
      items={currentItems}
      selectedId={selectedItem?.id}
      bind:selectedIds
      {loading}
      isItemCut={checkItemCut}
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
      <button class="context-menu-item" onclick={() => { handleCopy(); closeMenus(); }}>Copy (Ctrl+C)</button>
      {#if canModifyStructure}
        <button class="context-menu-item" onclick={() => { handleCut(); closeMenus(); }}>Cut (Ctrl+X)</button>
      {/if}
      {#if clipboardItems.length > 0 && canModifyStructure}
        <button class="context-menu-item" onclick={() => { handlePaste(); closeMenus(); }}>Paste (Ctrl+V)</button>
      {/if}
      <div class="context-menu-divider"></div>
      {#if canModifyStructure}
        <button class="context-menu-item" onclick={openRename}><Edit size={16} /> Rename</button>
      {/if}
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
      {#if canModifyStructure}
        <div class="context-menu-divider"></div>
        <button class="context-menu-item danger" onclick={openDelete}><TrashCan size={16} /> Delete</button>
      {/if}
    {:else if contextMenuItem.type === 'folder'}
      <button class="context-menu-item" onclick={() => { handleCopy(); closeMenus(); }}>Copy (Ctrl+C)</button>
      {#if canModifyStructure}
        <button class="context-menu-item" onclick={() => { handleCut(); closeMenus(); }}>Cut (Ctrl+X)</button>
      {/if}
      {#if clipboardItems.length > 0 && canModifyStructure}
        <button class="context-menu-item" onclick={() => { handlePaste(); closeMenus(); }}>Paste Here (Ctrl+V)</button>
      {/if}
      <div class="context-menu-divider"></div>
      {#if canModifyStructure}
        <button class="context-menu-item" onclick={openRename}><Edit size={16} /> Rename</button>
        <button class="context-menu-item" onclick={bgUploadFile}><DocumentAdd size={16} /> Import File</button>
        <button class="context-menu-item" onclick={bgCreateFolder}><FolderAdd size={16} /> New Subfolder</button>
        <div class="context-menu-divider"></div>
        <button class="context-menu-item danger" onclick={openDelete}><TrashCan size={16} /> Delete</button>
      {/if}
    {:else if contextMenuItem.type === 'project'}
      {#if !$offlineMode}
        <button class="context-menu-item" onclick={() => { handleCopy(); closeMenus(); }}>Copy (Ctrl+C)</button>
        <button class="context-menu-item" onclick={() => { handleCut(); closeMenus(); }}>Cut (Ctrl+X)</button>
        {#if clipboardItems.length > 0 && clipboardItems.every(i => i.type === 'project')}
          <button class="context-menu-item" onclick={() => { handlePaste(); closeMenus(); }}>Paste Project Here</button>
        {/if}
        <div class="context-menu-divider"></div>
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
      {:else}
        <!-- P9: In offline mode, projects are read-only structure -->
        <div class="context-menu-item disabled">Project structure is read-only offline</div>
      {/if}
    {:else if contextMenuItem.type === 'platform'}
      {#if !$offlineMode}
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
      {:else}
        <!-- P9: In offline mode, platforms are read-only structure -->
        <div class="context-menu-item disabled">Platform structure is read-only offline</div>
      {/if}
    {:else if contextMenuItem.type === 'local-file'}
      <!-- P9: Local file context menu - SAME as regular file (unified endpoints handle both) -->
      <button class="context-menu-item" onclick={() => { handleCopy(); closeMenus(); }}>Copy (Ctrl+C)</button>
      <div class="context-menu-divider"></div>
      <button class="context-menu-item" onclick={openRename}><Edit size={16} /> Rename</button>
      <button class="context-menu-item" onclick={downloadFile}><Download size={16} /> Download</button>
      <div class="context-menu-divider"></div>
      <button class="context-menu-item" onclick={() => convertFile('xlsx')}><Renew size={16} /> Convert to XLSX</button>
      <button class="context-menu-item" onclick={() => convertFile('xml')}><Renew size={16} /> Convert to XML</button>
      <button class="context-menu-item" onclick={() => convertFile('tmx')}><Renew size={16} /> Convert to TMX</button>
      <div class="context-menu-divider"></div>
      <button class="context-menu-item pretranslate" onclick={openPretranslate}><Translate size={16} /> Pre-translate...</button>
      <button class="context-menu-item" onclick={runQA}><Flash size={16} /> Run QA</button>
      <button class="context-menu-item" onclick={openTMRegistration}><DataBase size={16} /> Register as TM</button>
      <button class="context-menu-item" onclick={extractGlossary}><TextMining size={16} /> Extract Glossary</button>
      <div class="context-menu-divider"></div>
      <button class="context-menu-item" onclick={openUploadToServer}><CloudUpload size={16} /> Upload to Server</button>
      <div class="context-menu-divider"></div>
      <button class="context-menu-item danger" onclick={openDelete}><TrashCan size={16} /> Delete</button>
    {:else if contextMenuItem.type === 'offline-storage'}
      <!-- P9: Offline Storage - no context actions, just close menu -->
      <div class="context-menu-item disabled">No actions available</div>
    {:else if contextMenuItem.type === 'trash-item'}
      <!-- EXPLORER-008: Trash item context menu -->
      <button class="context-menu-item" onclick={() => { restoreFromTrash(contextMenuItem.trash_id); closeMenus(); }}>
        <Renew size={16} /> Restore
      </button>
      <div class="context-menu-divider"></div>
      <button class="context-menu-item danger" onclick={() => { permanentDeleteFromTrash(contextMenuItem.trash_id); closeMenus(); }}>
        <TrashCan size={16} /> Delete Permanently
      </button>
    {/if}
  </div>
{/if}

<!-- Background Context Menu -->
{#if showBackgroundMenu}
  <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
  <div class="context-menu" style="left: {bgMenuX}px; top: {bgMenuY}px" role="menu" onclick={(e) => e.stopPropagation()}>
    {#if currentPath.length === 0}
      <!-- At root: can create platform or project (but NOT in offline mode) -->
      {#if $offlineMode}
        <div class="context-menu-item disabled">
          <Application size={16} /> New Platform (Online only)
        </div>
        <div class="context-menu-item disabled">
          <FolderAdd size={16} /> New Project (Online only)
        </div>
      {:else}
        <button class="context-menu-item" onclick={bgCreatePlatform}><Application size={16} /> New Platform</button>
        <button class="context-menu-item" onclick={bgCreateProject}><FolderAdd size={16} /> New Project</button>
      {/if}
    {:else if currentPath[0]?.type === 'recycle-bin'}
      <!-- EXPLORER-008: Inside Recycle Bin -->
      <button class="context-menu-item danger" onclick={() => { emptyTrash(); closeMenus(); }}>
        <TrashCan size={16} /> Empty Recycle Bin
      </button>
    {:else if currentPath[0]?.type === 'offline-storage'}
      <!-- P9: Inside Offline Storage: full CRUD (Session 31) -->
      {#if clipboardItems.length > 0}
        <button class="context-menu-item" onclick={() => { handlePaste(); closeMenus(); }}>
          Paste {clipboardItems.length} item{clipboardItems.length > 1 ? 's' : ''} (Ctrl+V)
        </button>
        <div class="context-menu-divider"></div>
      {/if}
      <button class="context-menu-item" onclick={bgUploadFile}><DocumentAdd size={16} /> Import File</button>
      <button class="context-menu-item" onclick={bgCreateFolder}><FolderAdd size={16} /> New Folder</button>
    {:else if currentPath[0]?.type === 'platform' && currentPath.length === 1}
      <!-- Inside a platform: can only create project (but NOT in offline mode) -->
      {#if $offlineMode}
        <div class="context-menu-item disabled">
          <FolderAdd size={16} /> New Project (Online only)
        </div>
      {:else}
        <button class="context-menu-item" onclick={bgCreateProject}><FolderAdd size={16} /> New Project</button>
      {/if}
    {:else}
      <!-- Inside project/folder: upload file or create folder -->
      {#if clipboardItems.length > 0 && canModifyStructure}
        <button class="context-menu-item" onclick={() => { handlePaste(); closeMenus(); }}>
          Paste {clipboardItems.length} item{clipboardItems.length > 1 ? 's' : ''} (Ctrl+V)
        </button>
        <div class="context-menu-divider"></div>
      {/if}
      {#if canModifyStructure}
        <button class="context-menu-item" onclick={bgUploadFile}><DocumentAdd size={16} /> Upload File</button>
        <button class="context-menu-item" onclick={bgCreateFolder}><FolderAdd size={16} /> New Folder</button>
      {:else}
        <div class="context-menu-item disabled">
          <DocumentAdd size={16} /> Upload File (Offline Storage only)
        </div>
        <div class="context-menu-item disabled">
          <FolderAdd size={16} /> New Folder (Offline Storage only)
        </div>
      {/if}
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
  message={getDeleteConfirmMessage(contextMenuItem)}
  danger={true}
  confirmLabel="Delete"
  onConfirm={executeDelete}
  onCancel={() => { contextMenuItem = null; }}
/>

<!-- EXPLORER-006: Move Confirmation Modal -->
<ConfirmModal
  bind:open={showMoveConfirm}
  title="Confirm Move"
  message={getMoveConfirmMessage(pendingMoveOperation)}
  danger={false}
  confirmLabel="Move"
  onConfirm={executePendingMove}
  onCancel={() => { pendingMoveOperation = null; }}
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

  /* EXPLORER-004: Search wrapper */
  .search-wrapper {
    flex: 1;
    display: flex;
    justify-content: center;
    padding: 0 1rem;
    max-width: 700px;
    margin: 0 auto;
  }

  /* EXPLORER-001: Clipboard status indicator */
  .clipboard-indicator {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    margin-left: auto;
    padding: 0.25rem 0.625rem;
    background: var(--cds-layer-02);
    border: 1px solid var(--cds-border-subtle-01);
    border-radius: 4px;
    font-size: 0.75rem;
    color: var(--cds-text-secondary);
  }

  .clipboard-indicator span {
    white-space: nowrap;
  }

  .clipboard-clear {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 16px;
    height: 16px;
    padding: 0;
    margin-left: 0.25rem;
    background: transparent;
    border: none;
    border-radius: 2px;
    cursor: pointer;
    font-size: 14px;
    font-weight: bold;
    color: var(--cds-text-secondary);
    transition: background 0.1s ease, color 0.1s ease;
  }

  .clipboard-clear:hover {
    background: var(--cds-layer-hover-01);
    color: var(--cds-text-primary);
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

  .context-menu-item.disabled {
    color: var(--cds-text-disabled);
    cursor: not-allowed;
    font-style: italic;
  }

  .context-menu-item.disabled:hover {
    background: transparent;
  }

  .context-menu-divider {
    height: 1px;
    background: var(--cds-border-subtle-01);
    margin: 0.25rem 0;
  }
</style>
