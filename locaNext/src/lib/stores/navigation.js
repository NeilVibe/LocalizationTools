import { writable, derived } from 'svelte/store';

// =============================================================================
// Navigation Store - Phase 10 UI Overhaul
// =============================================================================

/**
 * Current page in the LDM app
 * - 'files': File Explorer page (browse projects/folders/files)
 * - 'tm': TM Explorer page (manage translation memories)
 * - 'grid': Grid viewer (viewing/editing a file)
 * - 'tm-entries': TM entries viewer (viewing TM entries full-page)
 */
export const currentPage = writable('files');

/**
 * Currently selected/open file (when in grid view)
 */
export const openFile = writable(null);

/**
 * Currently selected/open TM (when viewing TM entries)
 */
export const openTM = writable(null);

/**
 * Navigation breadcrumb path
 * Empty at root (Projects list), populated when inside project/folder
 * Example: [{ type: 'project', id: 1, name: 'BDO_EN' }, { type: 'folder', id: 5, name: 'Strings' }]
 */
export const breadcrumbPath = writable([]);

/**
 * Navigation history for back/forward (future use)
 */
export const navigationHistory = writable([]);

/**
 * Saved Files page path - restored when returning from grid view
 * Stores: { path: [...], projectId: number|null, folderId: number|null }
 */
export const savedFilesState = writable(null);

// =============================================================================
// Navigation Actions
// =============================================================================

/**
 * Navigate to Files page
 */
export function goToFiles() {
  currentPage.set('files');
  openFile.set(null);
}

/**
 * Navigate to TM page
 */
export function goToTM() {
  currentPage.set('tm');
  openFile.set(null);
}

/**
 * Open a file in the grid viewer
 * @param {Object} file - File object with id, name, format, etc.
 * @param {Object} filesState - Current files page state to restore on back
 */
export function openFileInGrid(file, filesState = null) {
  if (filesState) {
    savedFilesState.set(filesState);
  }
  openFile.set(file);
  currentPage.set('grid');
}

/**
 * Close the grid and return to files
 */
export function closeGrid() {
  openFile.set(null);
  currentPage.set('files');
}

/**
 * Open a TM in the entries viewer (full-page)
 * @param {Object} tm - TM object with id, name, entry_count, etc.
 */
export function openTMInGrid(tm) {
  openTM.set(tm);
  currentPage.set('tm-entries');
}

/**
 * Close TM entries viewer and return to TM list
 */
export function closeTMGrid() {
  openTM.set(null);
  currentPage.set('tm');
}

/**
 * Update breadcrumb path
 * @param {Array} path - Array of breadcrumb items
 */
export function setBreadcrumb(path) {
  breadcrumbPath.set(path);
}

/**
 * Navigate up one level in breadcrumb
 */
export function navigateUp() {
  breadcrumbPath.update(path => {
    if (path.length > 1) {
      return path.slice(0, -1);
    }
    return path;
  });
}

// =============================================================================
// Derived Stores
// =============================================================================

/**
 * Whether we're currently viewing a file
 */
export const isViewingFile = derived(currentPage, $page => $page === 'grid');

/**
 * Current breadcrumb as string (for display)
 */
export const breadcrumbString = derived(breadcrumbPath, $path =>
  $path.map(item => item.name).join(' > ')
);
