/**
 * LDM (LanguageData Manager) Store
 *
 * Manages real-time state for collaborative editing:
 * - WebSocket connection management (join/leave file)
 * - Real-time cell updates from other users
 * - Presence tracking (who's viewing the file)
 * - Row locking (prevent conflicts)
 *
 * Usage:
 *   import { ldmStore, joinFile, leaveFile, lockRow, unlockRow } from '$lib/stores/ldm.js';
 */

import { writable, derived, get } from 'svelte/store';
import { websocket } from '$lib/api/websocket.js';

// ============================================================================
// Stores
// ============================================================================

// Current file being viewed
export const currentFileId = writable(null);

// Viewers on current file: [{user_id, username}]
export const fileViewers = writable([]);

// Locked rows: Map<row_id, {locked_by, user_id}>
const rowLocks = writable(new Map());

// Pending cell updates (received before we apply them)
const pendingUpdates = writable([]);

// Connection status
export const ldmConnected = writable(false);

// ============================================================================
// Derived Stores
// ============================================================================

// Number of viewers
export const viewerCount = derived(fileViewers, $v => $v.length);

// List of locked row IDs
export const lockedRowIds = derived(rowLocks, $locks => Array.from($locks.keys()));

// Check if a specific row is locked (returns lock info or null)
// Returns null if no active file connection (prevents stale lock display)
export function isRowLocked(rowId) {
  // Don't show locks if we're not connected to a file
  const connected = get(ldmConnected);
  if (!connected) {
    return null;
  }
  const locks = get(rowLocks);
  return locks.get(rowId) || null;
}

// ============================================================================
// WebSocket Event Handlers
// ============================================================================

let unsubscribers = [];

function setupEventListeners() {
  // Cleanup any existing listeners
  cleanupEventListeners();

  // File room events
  unsubscribers.push(
    websocket.on('ldm_file_joined', (data) => {
      console.log('[LDM] Joined file:', data.file_id);
      ldmConnected.set(true);
    })
  );

  // Presence updates
  unsubscribers.push(
    websocket.on('ldm_presence', (data) => {
      console.log('[LDM] Presence update:', data.viewers.length, 'viewers');
      fileViewers.set(data.viewers);
    })
  );

  // Cell updates from other users
  unsubscribers.push(
    websocket.on('ldm_cell_update', (data) => {
      console.log('[LDM] Cell update:', data);
      pendingUpdates.update(updates => [...updates, data]);
    })
  );

  // Row lock events
  unsubscribers.push(
    websocket.on('ldm_lock_granted', (data) => {
      console.log('[LDM] Lock granted:', data.row_id);
    })
  );

  unsubscribers.push(
    websocket.on('ldm_lock_denied', (data) => {
      console.log('[LDM] Lock denied:', data.row_id, 'by', data.locked_by);
      // Could show notification here
    })
  );

  unsubscribers.push(
    websocket.on('ldm_row_locked', (data) => {
      console.log('[LDM] Row locked by another user:', data);
      rowLocks.update(locks => {
        locks.set(data.row_id, {
          locked_by: data.locked_by,
          user_id: data.user_id
        });
        return locks;
      });
    })
  );

  unsubscribers.push(
    websocket.on('ldm_row_unlocked', (data) => {
      console.log('[LDM] Row unlocked:', data.row_id);
      rowLocks.update(locks => {
        locks.delete(data.row_id);
        return locks;
      });
    })
  );

  unsubscribers.push(
    websocket.on('ldm_locks', (data) => {
      console.log('[LDM] Initial locks:', data.locks.length);
      rowLocks.update(locks => {
        locks.clear();
        data.locks.forEach(lock => {
          locks.set(lock.row_id, {
            locked_by: lock.locked_by,
            user_id: lock.user_id
          });
        });
        return locks;
      });
    })
  );

  // Handle errors
  unsubscribers.push(
    websocket.on('ldm_error', (data) => {
      console.error('[LDM] Error:', data.message);
    })
  );
}

function cleanupEventListeners() {
  unsubscribers.forEach(unsub => unsub());
  unsubscribers = [];
}

// ============================================================================
// Actions
// ============================================================================

/**
 * Join a file for real-time updates
 * @param {number} fileId - File ID to join
 */
export function joinFile(fileId) {
  if (!fileId) return;

  // Leave current file first
  const current = get(currentFileId);
  if (current && current !== fileId) {
    leaveFile(current);
  }

  // Clear any stale lock state before joining new file
  rowLocks.set(new Map());
  ldmConnected.set(false);

  // Setup event listeners if not already
  setupEventListeners();

  // Join the new file
  currentFileId.set(fileId);
  websocket.send('ldm_join_file', { file_id: fileId });

  // Get initial locks
  websocket.send('ldm_get_locks', { file_id: fileId });

  // Get initial presence
  websocket.send('ldm_get_presence', { file_id: fileId });

  console.log('[LDM] Joining file:', fileId);
}

/**
 * Leave current file
 * @param {number} fileId - File ID to leave (optional, defaults to current)
 */
export function leaveFile(fileId = null) {
  const id = fileId || get(currentFileId);
  if (!id) return;

  websocket.send('ldm_leave_file', { file_id: id });

  // Clear state
  currentFileId.set(null);
  fileViewers.set([]);
  rowLocks.set(new Map());
  ldmConnected.set(false);

  console.log('[LDM] Left file:', id);
}

/**
 * Lock a row before editing
 * @param {number} fileId - File ID
 * @param {number} rowId - Row ID to lock
 * @returns {Promise<boolean>} - True if lock was granted
 */
export async function lockRow(fileId, rowId) {
  return new Promise((resolve) => {
    console.log('[LDM] lockRow called:', { fileId, rowId, wsConnected: websocket.isConnected() });

    // Check if already locked by someone else (ignore stale locks with no username)
    const existingLock = isRowLocked(rowId);
    if (existingLock && existingLock.locked_by) {
      console.log('[LDM] Row already locked by', existingLock.locked_by);
      resolve(false);
      return;
    } else if (existingLock) {
      console.log('[LDM] Ignoring stale lock with no username');
    }

    // Request lock
    console.log('[LDM] Sending ldm_lock_row event...');
    websocket.send('ldm_lock_row', { file_id: fileId, row_id: rowId });

    // Wait for response (with timeout)
    const timeout = setTimeout(() => {
      cleanup();
      resolve(false);
    }, 3000);

    const grantedHandler = (data) => {
      if (data.row_id === rowId) {
        cleanup();
        resolve(true);
      }
    };

    const deniedHandler = (data) => {
      if (data.row_id === rowId) {
        cleanup();
        resolve(false);
      }
    };

    const grantedUnsub = websocket.on('ldm_lock_granted', grantedHandler);
    const deniedUnsub = websocket.on('ldm_lock_denied', deniedHandler);

    function cleanup() {
      clearTimeout(timeout);
      grantedUnsub();
      deniedUnsub();
    }
  });
}

/**
 * Unlock a row after editing
 * @param {number} fileId - File ID
 * @param {number} rowId - Row ID to unlock
 */
export function unlockRow(fileId, rowId) {
  websocket.send('ldm_unlock_row', { file_id: fileId, row_id: rowId });
}

/**
 * Get pending updates and clear them
 * @returns {Array} - Pending cell updates
 */
export function consumePendingUpdates() {
  const updates = get(pendingUpdates);
  pendingUpdates.set([]);
  return updates;
}

/**
 * Subscribe to pending updates
 * @param {Function} callback - Called when new updates arrive
 * @returns {Function} - Unsubscribe function
 */
export function onCellUpdate(callback) {
  return pendingUpdates.subscribe(updates => {
    if (updates.length > 0) {
      callback(updates);
    }
  });
}

// ============================================================================
// Cleanup
// ============================================================================

/**
 * Cleanup LDM state (call on component unmount)
 */
export function cleanup() {
  const fileId = get(currentFileId);
  if (fileId) {
    leaveFile(fileId);
  }
  cleanupEventListeners();
}

// ============================================================================
// Export Store Object
// ============================================================================

export const ldmStore = {
  currentFileId,
  fileViewers,
  viewerCount,
  lockedRowIds,
  ldmConnected,
  joinFile,
  leaveFile,
  lockRow,
  unlockRow,
  isRowLocked,
  onCellUpdate,
  consumePendingUpdates,
  cleanup
};

export default ldmStore;
