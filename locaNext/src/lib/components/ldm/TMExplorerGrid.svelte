<script>
  /**
   * TMExplorerGrid.svelte - UI-108 Grid View for TMs
   *
   * Windows/SharePoint style grid for Translation Memories.
   * Replaces the old dropdown tree style (TMExplorerTree).
   *
   * Features:
   * - Breadcrumb navigation (Home > Platform > Project)
   * - Grid rows with columns: Name, Entries, Status, Type
   * - Double-click to enter Platform/Project, view TM details
   * - Right-click context menu (Activate, Move, Delete)
   * - Drag-drop TM reassignment
   */
  import { onMount } from 'svelte';
  import {
    Home,
    ChevronRight,
    DataBase,
    Folder,
    Application,
    CheckmarkFilled,
    RadioButton,
    Archive,
    CloudOffline,
    DocumentBlank
  } from 'carbon-icons-svelte';
  import { logger } from '$lib/utils/logger.js';
  import { getAuthHeaders, getApiBase } from '$lib/utils/api.js';
  import ConfirmModal from '$lib/components/common/ConfirmModal.svelte';
  import { clipboard, copyToClipboard, cutToClipboard, clearClipboard, isItemCut } from '$lib/stores/clipboard.js';

  // Props
  let {
    selectedTMId = $bindable(null),
    onTMSelect = null,
    onViewEntries = null,
    onUploadTM = null  // Callback when user wants to upload TM
  } = $props();

  const API_BASE = getApiBase();

  // State
  let treeData = $state({ unassigned: [], platforms: [] });
  let loading = $state(false);

  // Navigation state - breadcrumb path
  // Each item: { type: 'home'|'platform'|'project', id, name }
  let breadcrumb = $state([{ type: 'home', id: null, name: 'Home' }]);

  // Current view items (what's displayed in the grid)
  let currentItems = $state([]);

  // Multi-select state
  let selectedIds = $state(new Set());
  let lastSelectedIndex = $state(-1);

  // Context menu state
  let contextMenu = $state({ show: false, x: 0, y: 0, item: null, isBackground: false });

  // Confirm modal state
  let confirmModal = $state({
    open: false,
    title: '',
    message: '',
    confirmLabel: 'Delete',
    pendingAction: null,
    pendingData: null
  });

  // Drag state
  let draggedItems = $state([]);
  let dropTargetId = $state(null);
  let isDragging = $state(false);

  // UX-003: Clipboard state (derived from store)
  let clipboardItems = $derived($clipboard.items);
  let clipboardOperation = $derived($clipboard.operation);

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

      // Update current view based on breadcrumb
      updateCurrentItems();
    } catch (err) {
      logger.error('Failed to load TM tree', { error: err.message });
      treeData = { unassigned: [], platforms: [] };
      currentItems = [];
    } finally {
      loading = false;
    }
  }

  // ========================================
  // Navigation & View Updates
  // ========================================

  // Helper: count TMs in a folder (including children)
  function countTMsInFolder(folder) {
    let count = folder.tms?.length || 0;
    for (const child of folder.children || []) {
      count += countTMsInFolder(child);
    }
    return count;
  }

  // Helper: find folder by ID in the tree
  function findFolderById(folderId) {
    for (const platform of treeData.platforms || []) {
      for (const project of platform.projects || []) {
        const folder = findFolderInTree(project.folders || [], folderId);
        if (folder) return folder;
      }
    }
    return null;
  }

  function findFolderInTree(folders, folderId) {
    for (const folder of folders) {
      if (folder.id === folderId) return folder;
      const found = findFolderInTree(folder.children || [], folderId);
      if (found) return found;
    }
    return null;
  }

  // Helper: find parent project/folder for a folder
  function findFolderParent(folderId) {
    for (const platform of treeData.platforms || []) {
      for (const project of platform.projects || []) {
        // Check if folder is direct child of project
        if ((project.folders || []).some(f => f.id === folderId)) {
          return { type: 'project', project, platform };
        }
        // Check nested folders
        const parent = findParentFolderInTree(project.folders || [], folderId);
        if (parent) {
          return { type: 'folder', folder: parent, project, platform };
        }
      }
    }
    return null;
  }

  function findParentFolderInTree(folders, folderId) {
    for (const folder of folders) {
      if ((folder.children || []).some(c => c.id === folderId)) {
        return folder;
      }
      const found = findParentFolderInTree(folder.children || [], folderId);
      if (found) return found;
    }
    return null;
  }

  function updateCurrentItems() {
    const currentLevel = breadcrumb[breadcrumb.length - 1];

    if (currentLevel.type === 'home') {
      // Home level: Show Unassigned section + all platforms
      const items = [];

      // Unassigned section (if has TMs)
      if (treeData.unassigned?.length > 0) {
        items.push({
          type: 'unassigned',
          id: 'unassigned',
          name: 'Unassigned',
          tm_count: treeData.unassigned.length,
          icon: 'archive'
        });
      }

      // Platforms
      for (const platform of treeData.platforms || []) {
        // Count TMs in platform (including in projects)
        let tmCount = platform.tms?.length || 0;
        for (const project of platform.projects || []) {
          tmCount += project.tms?.length || 0;
        }

        items.push({
          type: 'platform',
          id: platform.id,
          name: platform.name,
          tm_count: tmCount,
          project_count: platform.projects?.length || 0,
          icon: platform.name === 'Offline Storage' ? 'cloud-offline' : 'application'
        });
      }

      currentItems = items;
    } else if (currentLevel.type === 'unassigned') {
      // Unassigned level: Show all unassigned TMs
      currentItems = (treeData.unassigned || []).map(tm => ({
        type: 'tm',
        id: tm.tm_id,
        name: tm.tm_name,
        entry_count: tm.entry_count || 0,
        is_active: tm.is_active,
        tm_data: tm
      }));
    } else if (currentLevel.type === 'platform') {
      // Platform level: Show projects + platform-level TMs
      const platform = treeData.platforms?.find(p => p.id === currentLevel.id);
      if (!platform) {
        currentItems = [];
        return;
      }

      const items = [];

      // P9: Special handling for Offline Storage - show folders directly
      // (skip the nested "Offline Storage" project to avoid UI-109 duplicate)
      if (platform.name === 'Offline Storage') {
        // Find the Offline Storage project and show its folders directly
        const offlineProject = platform.projects?.find(p => p.name === 'Offline Storage');
        if (offlineProject) {
          // Show folders from the Offline Storage project
          for (const folder of offlineProject.folders || []) {
            items.push({
              type: 'folder',
              id: folder.id,
              name: folder.name,
              tm_count: countTMsInFolder(folder),
              icon: 'folder',
              folder_data: folder
            });
          }

          // Show TMs from the Offline Storage project
          for (const tm of offlineProject.tms || []) {
            items.push({
              type: 'tm',
              id: tm.tm_id,
              name: tm.tm_name,
              entry_count: tm.entry_count || 0,
              is_active: tm.is_active,
              tm_data: tm
            });
          }
        }
      } else {
        // Normal platform: show projects
        for (const project of platform.projects || []) {
          items.push({
            type: 'project',
            id: project.id,
            name: project.name,
            tm_count: project.tms?.length || 0,
            icon: 'folder'
          });
        }
      }

      // Platform-level TMs
      for (const tm of platform.tms || []) {
        items.push({
          type: 'tm',
          id: tm.tm_id,
          name: tm.tm_name,
          entry_count: tm.entry_count || 0,
          is_active: tm.is_active,
          tm_data: tm
        });
      }

      currentItems = items;
    } else if (currentLevel.type === 'project') {
      // Project level: Show folders + TMs in project
      // Find the project
      let project = null;
      for (const platform of treeData.platforms || []) {
        project = platform.projects?.find(p => p.id === currentLevel.id);
        if (project) break;
      }

      if (!project) {
        currentItems = [];
        return;
      }

      const items = [];

      // Folders in project (top-level folders only)
      for (const folder of project.folders || []) {
        items.push({
          type: 'folder',
          id: folder.id,
          name: folder.name,
          tm_count: countTMsInFolder(folder),
          icon: 'folder',
          folder_data: folder
        });
      }

      // Project-level TMs
      for (const tm of project.tms || []) {
        items.push({
          type: 'tm',
          id: tm.tm_id,
          name: tm.tm_name,
          entry_count: tm.entry_count || 0,
          is_active: tm.is_active,
          tm_data: tm
        });
      }

      currentItems = items;
    } else if (currentLevel.type === 'folder') {
      // Folder level: Show child folders + TMs in folder
      const folder = findFolderById(currentLevel.id);

      if (!folder) {
        currentItems = [];
        return;
      }

      const items = [];

      // Child folders
      for (const childFolder of folder.children || []) {
        items.push({
          type: 'folder',
          id: childFolder.id,
          name: childFolder.name,
          tm_count: countTMsInFolder(childFolder),
          icon: 'folder',
          folder_data: childFolder
        });
      }

      // Folder-level TMs
      for (const tm of folder.tms || []) {
        items.push({
          type: 'tm',
          id: tm.tm_id,
          name: tm.tm_name,
          entry_count: tm.entry_count || 0,
          is_active: tm.is_active,
          tm_data: tm
        });
      }

      currentItems = items;
    }
  }

  function navigateTo(item) {
    if (item.type === 'home') {
      breadcrumb = [{ type: 'home', id: null, name: 'Home' }];
    } else if (item.type === 'unassigned') {
      breadcrumb = [
        { type: 'home', id: null, name: 'Home' },
        { type: 'unassigned', id: 'unassigned', name: 'Unassigned' }
      ];
    } else if (item.type === 'platform') {
      breadcrumb = [
        { type: 'home', id: null, name: 'Home' },
        { type: 'platform', id: item.id, name: item.name }
      ];
    } else if (item.type === 'project') {
      // Find parent platform
      let parentPlatform = null;
      for (const platform of treeData.platforms || []) {
        if (platform.projects?.some(p => p.id === item.id)) {
          parentPlatform = platform;
          break;
        }
      }

      breadcrumb = [
        { type: 'home', id: null, name: 'Home' },
        { type: 'platform', id: parentPlatform?.id, name: parentPlatform?.name || 'Platform' },
        { type: 'project', id: item.id, name: item.name }
      ];
    } else if (item.type === 'folder') {
      // Build full breadcrumb path for folder
      const parentInfo = findFolderParent(item.id);
      if (!parentInfo) {
        // Fallback - shouldn't happen
        breadcrumb = [{ type: 'home', id: null, name: 'Home' }];
      } else {
        const newBreadcrumb = [
          { type: 'home', id: null, name: 'Home' },
          { type: 'platform', id: parentInfo.platform.id, name: parentInfo.platform.name },
          { type: 'project', id: parentInfo.project.id, name: parentInfo.project.name }
        ];

        // Add parent folders if folder is nested
        if (parentInfo.type === 'folder') {
          // Build folder path
          const folderPath = [];
          let currentFolder = parentInfo.folder;
          folderPath.unshift({ type: 'folder', id: currentFolder.id, name: currentFolder.name });

          // Walk up to find more parent folders
          let parentCheck = findFolderParent(currentFolder.id);
          while (parentCheck?.type === 'folder') {
            folderPath.unshift({ type: 'folder', id: parentCheck.folder.id, name: parentCheck.folder.name });
            parentCheck = findFolderParent(parentCheck.folder.id);
          }

          newBreadcrumb.push(...folderPath);
        }

        // Add the target folder
        newBreadcrumb.push({ type: 'folder', id: item.id, name: item.name });
        breadcrumb = newBreadcrumb;
      }
    }

    updateCurrentItems();
    // Clear selection when navigating
    selectedIds = new Set();
    lastSelectedIndex = -1;
  }

  function navigateToBreadcrumb(index) {
    breadcrumb = breadcrumb.slice(0, index + 1);
    updateCurrentItems();
    selectedIds = new Set();
    lastSelectedIndex = -1;
  }

  function goUp() {
    if (breadcrumb.length > 1) {
      navigateToBreadcrumb(breadcrumb.length - 2);
    }
  }

  // ========================================
  // Selection & Click Handlers
  // ========================================

  function handleClick(event, item, index) {
    if (event.ctrlKey || event.metaKey) {
      // Ctrl+click: toggle selection
      const newSet = new Set(selectedIds);
      if (newSet.has(item.id)) {
        newSet.delete(item.id);
      } else {
        newSet.add(item.id);
      }
      selectedIds = newSet;
      lastSelectedIndex = index;
    } else if (event.shiftKey && lastSelectedIndex >= 0) {
      // Shift+click: range selection
      const start = Math.min(lastSelectedIndex, index);
      const end = Math.max(lastSelectedIndex, index);
      const newSet = new Set(selectedIds);
      for (let i = start; i <= end; i++) {
        newSet.add(currentItems[i].id);
      }
      selectedIds = newSet;
    } else {
      // Normal click: single select
      selectedIds = new Set([item.id]);
      lastSelectedIndex = index;
    }

    // If TM selected, notify parent
    if (item.type === 'tm') {
      selectedTMId = item.id;
      if (onTMSelect) onTMSelect(item.tm_data);
    }
  }

  function handleDoubleClick(item) {
    if (item.type === 'tm') {
      // Double-click TM: view entries
      if (onViewEntries) onViewEntries(item.tm_data);
    } else {
      // Double-click folder-like item: navigate into it
      navigateTo(item);
    }
  }

  function isSelected(id) {
    return selectedIds.has(id);
  }

  // ========================================
  // TM Operations
  // ========================================

  async function activateTM(tm, active = true) {
    try {
      logger.apiCall(`/api/ldm/tm/${tm.tm_id}/activate`, 'PATCH');
      const response = await fetch(`${API_BASE}/api/ldm/tm/${tm.tm_id}/activate`, {
        method: 'PATCH',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ active })
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      logger.success(`TM ${active ? 'activated' : 'deactivated'}`, { tmId: tm.tm_id });
      await loadTree(); // Reload to show updated state
    } catch (err) {
      logger.error('Failed to toggle TM activation', { error: err.message });
    }
  }

  async function deleteTM(tm) {
    try {
      logger.apiCall(`/api/ldm/tm/${tm.tm_id}`, 'DELETE');
      const response = await fetch(`${API_BASE}/api/ldm/tm/${tm.tm_id}`, {
        method: 'DELETE',
        headers: getAuthHeaders()
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      logger.success('TM deleted', { tmId: tm.tm_id });
      await loadTree();
    } catch (err) {
      logger.error('Failed to delete TM', { error: err.message });
    }
  }

  function showDeleteConfirm(item) {
    closeContextMenu();
    confirmModal = {
      open: true,
      title: 'Delete Translation Memory',
      message: `Are you sure you want to delete "${item.name}"? This will permanently remove ${item.entry_count?.toLocaleString() || 0} entries.`,
      confirmLabel: 'Delete',
      pendingAction: 'delete',
      pendingData: item
    };
  }

  function handleModalConfirm() {
    if (confirmModal.pendingAction === 'delete' && confirmModal.pendingData?.tm_data) {
      deleteTM(confirmModal.pendingData.tm_data);
    }
    confirmModal.open = false;
  }

  function handleModalCancel() {
    confirmModal.open = false;
  }

  // ========================================
  // Context Menu
  // ========================================

  function handleContextMenu(event, item) {
    event.preventDefault();
    event.stopPropagation();
    contextMenu = {
      show: true,
      x: event.clientX,
      y: event.clientY,
      item,
      isBackground: false
    };
  }

  function handleBackgroundContextMenu(event) {
    if (event.target.closest('.grid-row')) return;
    event.preventDefault();
    event.stopPropagation();
    // Show background context menu with Upload option
    contextMenu = {
      show: true,
      x: event.clientX,
      y: event.clientY,
      item: null,
      isBackground: true
    };
  }

  function closeContextMenu() {
    contextMenu = { show: false, x: 0, y: 0, item: null, isBackground: false };
  }

  function handleActivateFromMenu() {
    if (contextMenu.item?.type === 'tm') {
      activateTM(contextMenu.item.tm_data, !contextMenu.item.is_active);
    }
    closeContextMenu();
  }

  function handleDeleteFromMenu() {
    if (contextMenu.item?.type === 'tm') {
      showDeleteConfirm(contextMenu.item);
    }
    closeContextMenu();
  }

  // ========================================
  // UX-003: Clipboard Operations (Cut/Copy/Paste)
  // ========================================

  /**
   * Copy selected TMs to clipboard
   */
  function handleCopy() {
    const tmsToClipboard = getSelectedTMs();
    logger.info('handleCopy called', {
      selectedCount: selectedIds.size,
      tmsFound: tmsToClipboard.length,
      currentItems: currentItems.length
    });

    if (tmsToClipboard.length === 0) {
      logger.warning('handleCopy: no TMs selected');
      return;
    }

    const items = tmsToClipboard.map(tm => ({
      type: 'tm',
      id: tm.id,
      name: tm.name,
      tm_data: tm.tm_data
    }));

    copyToClipboard(items);
    logger.success('TMs copied to clipboard', {
      count: items.length,
      tms: items.map(t => ({ id: t.id, name: t.name }))
    });
  }

  /**
   * Cut selected TMs to clipboard (for move operation)
   */
  function handleCut() {
    const tmsToClipboard = getSelectedTMs();
    logger.info('handleCut called', {
      selectedCount: selectedIds.size,
      tmsFound: tmsToClipboard.length,
      currentItems: currentItems.length
    });

    if (tmsToClipboard.length === 0) {
      logger.warning('handleCut: no TMs selected');
      return;
    }

    const items = tmsToClipboard.map(tm => ({
      type: 'tm',
      id: tm.id,
      name: tm.name,
      tm_data: tm.tm_data
    }));

    cutToClipboard(items);
    logger.success('TMs cut to clipboard', {
      count: items.length,
      tms: items.map(t => ({ id: t.id, name: t.name }))
    });
  }

  /**
   * Get selected TMs from currentItems
   */
  function getSelectedTMs() {
    return currentItems.filter(item => item.type === 'tm' && selectedIds.has(item.id));
  }

  /**
   * Paste clipboard items to current location
   */
  async function handlePaste() {
    logger.info('handlePaste called', {
      clipboardLength: clipboardItems.length,
      clipboardOperation,
      breadcrumb: breadcrumb.map(b => ({ type: b.type, id: b.id, name: b.name }))
    });

    if (clipboardItems.length === 0) {
      logger.warning('handlePaste: clipboard is empty');
      return;
    }

    // Only TMs can be pasted
    const tmsToPaste = clipboardItems.filter(item => item.type === 'tm');
    if (tmsToPaste.length === 0) {
      logger.info('No TMs in clipboard to paste');
      return;
    }

    logger.info('TMs to paste', {
      count: tmsToPaste.length,
      tms: tmsToPaste.map(t => ({ id: t.id, name: t.name }))
    });

    // Determine target based on current breadcrumb position
    const currentLocation = breadcrumb[breadcrumb.length - 1];
    logger.info('Current paste target location', {
      type: currentLocation.type,
      id: currentLocation.id,
      name: currentLocation.name
    });

    let assignmentData = {};

    if (currentLocation.type === 'home') {
      // Pasting at home = move to unassigned
      assignmentData = { platform_id: null, project_id: null, folder_id: null };
    } else if (currentLocation.type === 'platform') {
      assignmentData = { platform_id: currentLocation.id, project_id: null, folder_id: null };
    } else if (currentLocation.type === 'project') {
      assignmentData = { project_id: currentLocation.id, folder_id: null };
    } else if (currentLocation.type === 'folder') {
      // Check if this is a local folder (SQLite) - IDs start with "local-"
      const folderId = currentLocation.id;
      if (typeof folderId === 'string' && folderId.startsWith('local-')) {
        // Local folders (Offline Storage) can't have TMs assigned directly
        // They're stored in SQLite, not PostgreSQL
        logger.warning('Cannot paste TMs to local Offline Storage folders', {
          folderId,
          folderName: currentLocation.name
        });
        // For local folders, assign to the Offline Storage project instead
        // This keeps TMs accessible in Offline Storage context
        const offlineStoragePlatform = treeData.platforms?.find(p => p.name === 'Offline Storage');
        const offlineStorageProject = offlineStoragePlatform?.projects?.find(p => p.name === 'Offline Storage');
        if (offlineStorageProject) {
          logger.info('Redirecting local folder paste to Offline Storage project', {
            projectId: offlineStorageProject.id,
            originalFolderId: folderId
          });
          assignmentData = { project_id: offlineStorageProject.id, folder_id: null };
        } else {
          logger.error('Offline Storage project not found - pasting to unassigned', {
            platformFound: !!offlineStoragePlatform
          });
          // Fall back to unassigned if project not found
          assignmentData = { platform_id: null, project_id: null, folder_id: null };
        }
      } else {
        // Regular PostgreSQL folder
        assignmentData = { folder_id: folderId };
      }
    } else if (currentLocation.type === 'unassigned') {
      // Pasting in unassigned section = move to unassigned
      assignmentData = { platform_id: null, project_id: null, folder_id: null };
    } else {
      logger.warning('handlePaste: Unknown location type', { type: currentLocation.type });
      assignmentData = { platform_id: null, project_id: null, folder_id: null };
    }

    logger.info('Assignment data for paste', { assignmentData });

    // Move each TM
    let successCount = 0;
    let failCount = 0;
    for (const tm of tmsToPaste) {
      try {
        // Build URL with query parameters (backend expects query params, not body)
        const params = new URLSearchParams();
        if (assignmentData.platform_id !== undefined && assignmentData.platform_id !== null) {
          params.append('platform_id', assignmentData.platform_id.toString());
        }
        if (assignmentData.project_id !== undefined && assignmentData.project_id !== null) {
          params.append('project_id', assignmentData.project_id.toString());
        }
        if (assignmentData.folder_id !== undefined && assignmentData.folder_id !== null) {
          params.append('folder_id', assignmentData.folder_id.toString());
        }
        const queryString = params.toString();
        const url = `${API_BASE}/api/ldm/tm/${tm.id}/assign${queryString ? '?' + queryString : ''}`;
        logger.apiCall(url, 'PATCH', { params: assignmentData });
        const response = await fetch(url, {
          method: 'PATCH',
          headers: { ...getAuthHeaders() }
        });

        if (response.ok) {
          const result = await response.json();
          logger.success('TM paste API success', { tmId: tm.id, result });
          successCount++;
        } else {
          const errorText = await response.text();
          logger.error('Failed to paste TM', {
            tmId: tm.id,
            status: response.status,
            error: errorText
          });
          failCount++;
        }
      } catch (err) {
        logger.error('Error pasting TM', { error: err.message, tmId: tm.id });
        failCount++;
      }
    }

    logger.info('Paste operation complete', {
      successCount,
      failCount,
      target: currentLocation.name
    });

    if (successCount > 0) {
      logger.success('TMs pasted successfully', { count: successCount, target: currentLocation.name });
      clearClipboard();
      await loadTree();
    } else {
      logger.warning('Paste operation failed - no TMs were moved');
    }
  }

  /**
   * Check if a TM is in the clipboard (for cut visual feedback)
   */
  function isTMCut(tmId) {
    if (clipboardOperation !== 'cut') return false;
    return clipboardItems.some(item => item.type === 'tm' && item.id === tmId);
  }

  /**
   * Global keyboard handler for clipboard operations
   */
  function handleKeyDown(event) {
    // Escape clears clipboard
    if (event.key === 'Escape') {
      if (clipboardItems.length > 0) {
        clearClipboard();
        logger.info('Clipboard cleared');
        return;
      }
      // Clear selection
      selectedIds = new Set();
      return;
    }

    // Ctrl+C: Copy
    if (event.ctrlKey && event.key === 'c') {
      event.preventDefault();
      handleCopy();
      return;
    }

    // Ctrl+X: Cut
    if (event.ctrlKey && event.key === 'x') {
      event.preventDefault();
      handleCut();
      return;
    }

    // Ctrl+V: Paste
    if (event.ctrlKey && event.key === 'v') {
      event.preventDefault();
      handlePaste();
      return;
    }
  }

  // ========================================
  // Drag and Drop
  // ========================================

  function handleDragStart(event, item) {
    if (item.type !== 'tm') return;

    if (!isSelected(item.id)) {
      selectedIds = new Set([item.id]);
    }

    draggedItems = currentItems.filter(i => i.type === 'tm' && selectedIds.has(i.id));
    isDragging = true;

    event.dataTransfer.effectAllowed = 'move';
    event.dataTransfer.setData('text/plain', JSON.stringify(draggedItems.map(i => ({
      id: i.id,
      name: i.name,
      type: 'tm'
    }))));

    event.target.classList.add('dragging');
  }

  function handleDragEnd(event) {
    isDragging = false;
    draggedItems = [];
    dropTargetId = null;
    event.target.classList.remove('dragging');
  }

  function handleDragOver(event, item) {
    // Only platforms and projects can be drop targets
    if (item.type !== 'platform' && item.type !== 'project') return;
    if (draggedItems.length === 0) return;

    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
    dropTargetId = item.id;
  }

  function handleDragLeave(event, item) {
    if (dropTargetId === item.id) {
      dropTargetId = null;
    }
  }

  async function handleDrop(event, targetItem) {
    event.preventDefault();

    if (targetItem.type !== 'platform' && targetItem.type !== 'project') return;
    if (draggedItems.length === 0) return;

    // Move TMs to target
    for (const tm of draggedItems) {
      try {
        const assignmentData = targetItem.type === 'platform'
          ? { platform_id: targetItem.id, project_id: null }
          : { project_id: targetItem.id };

        logger.apiCall(`/api/ldm/tm/${tm.id}/assign`, 'PATCH');
        await fetch(`${API_BASE}/api/ldm/tm/${tm.id}/assign`, {
          method: 'PATCH',
          headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
          body: JSON.stringify(assignmentData)
        });
      } catch (err) {
        logger.error('Failed to reassign TM', { error: err.message, tmId: tm.id });
      }
    }

    logger.success('TMs reassigned', { count: draggedItems.length, target: targetItem.name });
    await loadTree();

    isDragging = false;
    draggedItems = [];
    dropTargetId = null;
  }

  // ========================================
  // Keyboard Navigation
  // ========================================

  function handleKeydown(event, item, index) {
    switch (event.key) {
      case 'Enter':
        handleDoubleClick(item);
        break;
      case 'Backspace':
        event.preventDefault();
        goUp();
        break;
      case 'Delete':
        if (item.type === 'tm') {
          event.preventDefault();
          showDeleteConfirm(item);
        }
        break;
    }
  }

  // ========================================
  // Icon Helpers
  // ========================================

  function getIcon(item) {
    if (item.type === 'unassigned') return Archive;
    if (item.type === 'platform') {
      return item.icon === 'cloud-offline' ? CloudOffline : Application;
    }
    if (item.type === 'project') return Folder;
    if (item.type === 'folder') return Folder;
    if (item.type === 'tm') {
      return item.is_active ? CheckmarkFilled : DataBase;
    }
    return DocumentBlank;
  }

  function formatEntryCount(item) {
    if (item.type === 'tm') {
      const count = item.entry_count || 0;
      return count === 0 ? 'Empty' : `${count.toLocaleString()} entries`;
    }
    if (item.type === 'platform') {
      if (item.tm_count > 0) return `${item.tm_count} TM${item.tm_count > 1 ? 's' : ''}`;
      return 'No TMs';
    }
    if (item.type === 'project') {
      if (item.tm_count > 0) return `${item.tm_count} TM${item.tm_count > 1 ? 's' : ''}`;
      return 'No TMs';
    }
    if (item.type === 'folder') {
      if (item.tm_count > 0) return `${item.tm_count} TM${item.tm_count > 1 ? 's' : ''}`;
      return 'No TMs';
    }
    if (item.type === 'unassigned') {
      return `${item.tm_count} TM${item.tm_count > 1 ? 's' : ''}`;
    }
    return '';
  }

  function formatStatus(item) {
    if (item.type === 'tm') {
      return item.is_active ? 'Active' : 'Inactive';
    }
    return '';
  }

  function formatType(item) {
    if (item.type === 'tm') return 'TM';
    if (item.type === 'platform') return 'Platform';
    if (item.type === 'project') return 'Project';
    if (item.type === 'folder') return 'Folder';
    if (item.type === 'unassigned') return 'Section';
    return '';
  }

  // ========================================
  // Lifecycle
  // ========================================

  onMount(() => {
    loadTree();

    // Close context menu on click outside
    const handleClickOutside = () => closeContextMenu();
    document.addEventListener('click', handleClickOutside);
    return () => document.removeEventListener('click', handleClickOutside);
  });

  // Expose reload for parent components
  export function reload() {
    return loadTree();
  }
</script>

<!-- UX-003: Global keyboard handler -->
<svelte:window onkeydown={handleKeyDown} />

<div class="tm-explorer-grid" oncontextmenu={handleBackgroundContextMenu}>
  <!-- UX-003: Clipboard indicator -->
  {#if clipboardItems.length > 0}
    <div class="clipboard-indicator">
      {#if clipboardOperation === 'cut'}
        <span class="clipboard-icon">✂</span>
      {:else}
        <span class="clipboard-icon">📋</span>
      {/if}
      <span>{clipboardItems.length} TM{clipboardItems.length > 1 ? 's' : ''} {clipboardOperation === 'cut' ? 'cut' : 'copied'}</span>
      <button class="clipboard-clear" onclick={() => clearClipboard()} title="Clear clipboard (Esc)">×</button>
    </div>
  {/if}
  <!-- Breadcrumb -->
  <nav class="breadcrumb" aria-label="TM navigation">
    {#each breadcrumb as crumb, i (i)}
      {#if i > 0}
        <ChevronRight size={16} class="breadcrumb-separator" />
      {/if}
      <button
        class="breadcrumb-item"
        class:current={i === breadcrumb.length - 1}
        onclick={() => navigateToBreadcrumb(i)}
      >
        {#if crumb.type === 'home'}
          <Home size={16} />
        {/if}
        <span>{crumb.name}</span>
      </button>
    {/each}
  </nav>

  <!-- Grid -->
  {#if loading}
    <div class="loading-state">
      <span>Loading...</span>
    </div>
  {:else if currentItems.length === 0}
    <div class="empty-state">
      <DocumentBlank size={48} />
      <p>No items here</p>
      <span>Right-click to create a new TM or upload</span>
    </div>
  {:else}
    <!-- Header row -->
    <div class="grid-header" role="row">
      <div class="grid-cell name-cell" role="columnheader">Name</div>
      <div class="grid-cell size-cell" role="columnheader">Entries</div>
      <div class="grid-cell status-cell" role="columnheader">Status</div>
      <div class="grid-cell type-cell" role="columnheader">Type</div>
    </div>

    <!-- Items -->
    <div class="grid-body">
      {#each currentItems as item, index (`${item.type}-${item.id}`)}
        {@const Icon = getIcon(item)}
        <button
          class="grid-row"
          class:selected={isSelected(item.id)}
          class:tm={item.type === 'tm'}
          class:active-tm={item.type === 'tm' && item.is_active}
          class:platform={item.type === 'platform'}
          class:project={item.type === 'project'}
          class:folder={item.type === 'folder'}
          class:drop-target={dropTargetId === item.id}
          class:dragging={isDragging && isSelected(item.id)}
          class:cut={item.type === 'tm' && isTMCut(item.id)}
          role="row"
          draggable={item.type === 'tm' ? 'true' : 'false'}
          onclick={(e) => handleClick(e, item, index)}
          ondblclick={() => handleDoubleClick(item)}
          oncontextmenu={(e) => handleContextMenu(e, item)}
          onkeydown={(e) => handleKeydown(e, item, index)}
          ondragstart={(e) => handleDragStart(e, item)}
          ondragend={handleDragEnd}
          ondragover={(e) => handleDragOver(e, item)}
          ondragleave={(e) => handleDragLeave(e, item)}
          ondrop={(e) => handleDrop(e, item)}
        >
          <div class="grid-cell name-cell" role="gridcell">
            {#if item.type === 'tm'}
              <button
                class="activation-toggle"
                onclick={(e) => { e.stopPropagation(); activateTM(item.tm_data, !item.is_active); }}
                title={item.is_active ? 'Deactivate TM' : 'Activate TM'}
              >
                {#if item.is_active}
                  <CheckmarkFilled size={18} class="tm-icon active" />
                {:else}
                  <RadioButton size={18} class="tm-icon inactive" />
                {/if}
              </button>
            {:else}
              <Icon size={20} class="item-icon" />
            {/if}
            <span class="item-name">{item.name}</span>
          </div>
          <div class="grid-cell size-cell" role="gridcell">
            {formatEntryCount(item)}
          </div>
          <div class="grid-cell status-cell" role="gridcell">
            {#if item.type === 'tm'}
              <span class="status-badge" class:active={item.is_active}>
                {formatStatus(item)}
              </span>
            {/if}
          </div>
          <div class="grid-cell type-cell" role="gridcell">
            {formatType(item)}
          </div>
        </button>
      {/each}
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
    {#if contextMenu.isBackground}
      <!-- Background right-click: Upload + Paste -->
      <button class="context-item" onclick={() => { if (onUploadTM) onUploadTM(); closeContextMenu(); }}>
        Upload TM
      </button>
      {#if clipboardItems.length > 0 && clipboardItems.some(i => i.type === 'tm')}
        <div class="context-divider"></div>
        <button class="context-item" onclick={() => { handlePaste(); closeContextMenu(); }}>
          Paste (Ctrl+V)
        </button>
      {/if}
    {:else if contextMenu.item?.type === 'tm'}
      <!-- TM right-click: Activate, Cut/Copy, Delete -->
      <button class="context-item" onclick={handleActivateFromMenu}>
        {contextMenu.item.is_active ? 'Deactivate' : 'Activate'}
      </button>
      <div class="context-divider"></div>
      <button class="context-item" onclick={() => { handleCut(); closeContextMenu(); }}>
        Cut (Ctrl+X)
      </button>
      <button class="context-item" onclick={() => { handleCopy(); closeContextMenu(); }}>
        Copy (Ctrl+C)
      </button>
      {#if clipboardItems.length > 0 && clipboardItems.some(i => i.type === 'tm')}
        <button class="context-item" onclick={() => { handlePaste(); closeContextMenu(); }}>
          Paste (Ctrl+V)
        </button>
      {/if}
      <div class="context-divider"></div>
      <button class="context-item danger" onclick={handleDeleteFromMenu}>
        Delete
      </button>
    {:else}
      <!-- Platform/Project right-click: Open + Paste -->
      <button class="context-item" onclick={() => { navigateTo(contextMenu.item); closeContextMenu(); }}>
        Open
      </button>
      {#if clipboardItems.length > 0 && clipboardItems.some(i => i.type === 'tm')}
        <div class="context-divider"></div>
        <button class="context-item" onclick={() => { handlePaste(); closeContextMenu(); }}>
          Paste Here (Ctrl+V)
        </button>
      {/if}
    {/if}
  </div>
{/if}

<!-- Confirm Modal -->
<ConfirmModal
  bind:open={confirmModal.open}
  title={confirmModal.title}
  message={confirmModal.message}
  confirmLabel={confirmModal.confirmLabel}
  danger={true}
  onConfirm={handleModalConfirm}
  onCancel={handleModalCancel}
/>

<style>
  .tm-explorer-grid {
    display: flex;
    flex-direction: column;
    width: 100%;
    height: 100%;
    flex: 1;
    min-height: 0;
    overflow: hidden;
    background: var(--cds-background);
  }

  /* Breadcrumb */
  .breadcrumb {
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
    padding: 0.25rem 0.5rem;
    background: transparent;
    border: none;
    border-radius: 4px;
    color: var(--cds-link-01, #78a9ff);
    font-size: 0.875rem;
    cursor: pointer;
    transition: background 0.15s ease;
  }

  .breadcrumb-item:hover {
    background: var(--cds-layer-hover-01);
  }

  .breadcrumb-item.current {
    color: var(--cds-text-01);
    cursor: default;
  }

  .breadcrumb-item.current:hover {
    background: transparent;
  }

  :global(.breadcrumb-separator) {
    color: var(--cds-text-02);
    flex-shrink: 0;
  }

  /* Loading / Empty states */
  .loading-state,
  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    flex: 1;
    padding: 2rem;
    color: var(--cds-text-02);
  }

  .empty-state p {
    margin: 1rem 0 0.25rem;
    font-size: 1rem;
    font-weight: 500;
    color: var(--cds-text-01);
  }

  .empty-state span {
    font-size: 0.875rem;
  }

  /* Grid header */
  .grid-header {
    display: flex;
    padding: 0.5rem 1rem;
    background: var(--cds-layer-01);
    border-bottom: 1px solid var(--cds-border-subtle-01);
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    color: var(--cds-text-02);
    user-select: none;
    flex-shrink: 0;
  }

  /* Grid body */
  .grid-body {
    flex: 1;
    overflow-y: auto;
    overflow-x: hidden;
  }

  /* Grid row */
  .grid-row {
    display: flex;
    width: 100%;
    padding: 0.625rem 1rem;
    background: transparent;
    border: none;
    border-bottom: 1px solid var(--cds-border-subtle-01, #393939);
    cursor: pointer;
    text-align: left;
    transition: background 0.15s ease;
    font-family: inherit;
    font-size: inherit;
    color: inherit;
  }

  .grid-row:hover {
    background: var(--cds-layer-hover-01, rgba(141, 141, 141, 0.16));
  }

  .grid-row:focus {
    outline: 2px solid var(--cds-focus, #0f62fe);
    outline-offset: -2px;
  }

  .grid-row.selected {
    background: var(--cds-layer-selected-01, rgba(141, 141, 141, 0.24));
  }

  .grid-row.selected:hover {
    background: var(--cds-layer-selected-hover-01, rgba(141, 141, 141, 0.32));
  }

  .grid-row.drop-target {
    background: rgba(15, 98, 254, 0.25) !important;
    outline: 2px dashed var(--cds-link-01, #78a9ff);
    outline-offset: -2px;
  }

  .grid-row.dragging {
    opacity: 0.5;
    background: rgba(100, 100, 100, 0.3);
  }

  /* Grid cells */
  .grid-cell {
    display: flex;
    align-items: center;
    overflow: hidden;
  }

  .name-cell {
    flex: 1;
    min-width: 200px;
    gap: 0.75rem;
  }

  .size-cell {
    width: 120px;
    color: var(--cds-text-02);
    font-size: 0.875rem;
  }

  .status-cell {
    width: 80px;
  }

  .type-cell {
    width: 80px;
    color: var(--cds-text-02);
    font-size: 0.75rem;
    text-transform: uppercase;
  }

  /* Item icons */
  .grid-row :global(.item-icon) {
    flex-shrink: 0;
    color: #a8b0b8;
  }

  .grid-row.platform :global(.item-icon) {
    color: #4589ff;
  }

  .grid-row.project :global(.item-icon) {
    color: #5a9a6e;
  }

  .grid-row.folder :global(.item-icon) {
    color: #d4a574;
  }

  /* TM activation toggle */
  .activation-toggle {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 2px;
    background: transparent;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    flex-shrink: 0;
  }

  .activation-toggle:hover {
    background: var(--cds-layer-hover-01);
  }

  :global(.tm-icon.active) {
    color: #24a148 !important;
  }

  :global(.tm-icon.inactive) {
    color: #6f6f6f !important;
  }

  .item-name {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: 0.875rem;
    color: var(--cds-text-01);
  }

  .grid-row.platform .item-name,
  .grid-row.project .item-name,
  .grid-row.folder .item-name {
    font-weight: 500;
  }

  /* Status badge */
  .status-badge {
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 0.75rem;
    background: var(--cds-layer-02);
    color: var(--cds-text-02);
  }

  .status-badge.active {
    background: rgba(36, 161, 72, 0.2);
    color: #24a148;
  }

  /* Context menu */
  .context-menu {
    position: fixed;
    z-index: 1000;
    min-width: 150px;
    background: var(--cds-layer-02, #262626);
    border: 1px solid var(--cds-border-subtle-01);
    border-radius: 4px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
    padding: 0.25rem 0;
  }

  .context-item {
    display: block;
    width: 100%;
    padding: 0.5rem 1rem;
    background: transparent;
    border: none;
    text-align: left;
    color: var(--cds-text-01);
    font-size: 0.875rem;
    cursor: pointer;
    transition: background 0.1s ease;
  }

  .context-item:hover {
    background: var(--cds-layer-hover-01);
  }

  .context-item.danger {
    color: var(--cds-support-error, #fa4d56);
  }

  .context-item.danger:hover {
    background: rgba(250, 77, 86, 0.1);
  }

  /* UX-003: Context menu divider */
  .context-divider {
    height: 1px;
    background: var(--cds-border-subtle-01);
    margin: 0.25rem 0;
  }

  /* UX-003: Clipboard indicator */
  .clipboard-indicator {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 1rem;
    background: var(--cds-layer-02, #262626);
    border-bottom: 1px solid var(--cds-border-subtle-01);
    font-size: 0.875rem;
    color: var(--cds-text-02);
  }

  .clipboard-icon {
    font-size: 1rem;
  }

  .clipboard-clear {
    margin-left: auto;
    background: transparent;
    border: none;
    color: var(--cds-text-02);
    cursor: pointer;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    font-size: 1rem;
    line-height: 1;
  }

  .clipboard-clear:hover {
    background: var(--cds-layer-hover-01);
    color: var(--cds-text-01);
  }

  /* UX-003: Cut visual feedback - striped/faded appearance */
  .grid-row.cut {
    opacity: 0.5;
    background: repeating-linear-gradient(
      45deg,
      transparent,
      transparent 5px,
      rgba(100, 100, 100, 0.1) 5px,
      rgba(100, 100, 100, 0.1) 10px
    );
  }

  /* Responsive */
  @media (max-width: 768px) {
    .type-cell {
      display: none;
    }
  }

  @media (max-width: 600px) {
    .status-cell {
      display: none;
    }
  }
</style>
