/**
 * P3 Offline/Online Mode - Sync Store
 *
 * Manages connection state, sync status, and offline mode.
 *
 * States:
 * - online: Connected to server, working normally
 * - offline: No server connection, working on local SQLite
 * - syncing: Sync operation in progress
 * - pending: Has local changes not yet synced
 */

import { writable, derived } from 'svelte/store';
import { getApiBase, getAuthHeaders } from '$lib/utils/api.js';
import { logger } from '$lib/utils/logger.js';

// =============================================================================
// Core State
// =============================================================================

/**
 * Connection mode: 'online' | 'offline'
 */
export const connectionMode = writable('online');

/**
 * Whether currently syncing
 */
export const isSyncing = writable(false);

/**
 * Count of pending local changes
 */
export const pendingChanges = writable(0);

/**
 * Last sync timestamp
 */
export const lastSync = writable(null);

/**
 * Server URL being used
 */
export const serverUrl = writable(getApiBase());

/**
 * Connection error message (if any)
 */
export const connectionError = writable(null);

// =============================================================================
// Derived State
// =============================================================================

/**
 * Display status for mode indicator
 * Returns: 'online' | 'offline' | 'syncing' | 'pending'
 */
export const displayStatus = derived(
  [connectionMode, isSyncing, pendingChanges],
  ([$mode, $syncing, $pending]) => {
    if ($syncing) return 'syncing';
    if ($mode === 'offline' && $pending > 0) return 'pending';
    return $mode;
  }
);

/**
 * Status icon for mode indicator
 */
export const statusIcon = derived(displayStatus, ($status) => {
  switch ($status) {
    case 'online': return '🟢';
    case 'offline': return '🔴';
    case 'syncing': return '🟡';
    case 'pending': return '🟠';
    default: return '⚪';
  }
});

/**
 * Status label for mode indicator
 */
export const statusLabel = derived(displayStatus, ($status) => {
  switch ($status) {
    case 'online': return 'Online';
    case 'offline': return 'Offline';
    case 'syncing': return 'Syncing...';
    case 'pending': return 'Pending';
    default: return 'Unknown';
  }
});

/**
 * Whether offline mode is available (has downloaded data)
 */
export const offlineAvailable = writable(false);

// =============================================================================
// Connection Management
// =============================================================================

let healthCheckInterval = null;
const HEALTH_CHECK_INTERVAL = 30000; // 30 seconds

/**
 * Check server connectivity
 */
export async function checkConnection() {
  const url = getApiBase();

  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 5000);

    const response = await fetch(`${url}/health`, {
      signal: controller.signal
    });

    clearTimeout(timeout);

    if (response.ok) {
      connectionMode.set('online');
      connectionError.set(null);
      return true;
    } else {
      throw new Error(`Server returned ${response.status}`);
    }
  } catch (error) {
    logger.warn('Server connection failed', { error: error.message });
    connectionMode.set('offline');
    connectionError.set(error.message);
    return false;
  }
}

/**
 * Start periodic health checks
 */
export function startHealthChecks() {
  if (healthCheckInterval) return;

  // Initial check
  checkConnection();

  // Periodic checks
  healthCheckInterval = setInterval(checkConnection, HEALTH_CHECK_INTERVAL);
  logger.debug('Health checks started');
}

/**
 * Stop periodic health checks
 */
export function stopHealthChecks() {
  if (healthCheckInterval) {
    clearInterval(healthCheckInterval);
    healthCheckInterval = null;
    logger.debug('Health checks stopped');
  }
}

/**
 * Force switch to offline mode
 */
export function goOffline() {
  stopHealthChecks();
  connectionMode.set('offline');
  logger.info('Switched to offline mode');
}

/**
 * Try to reconnect to server
 */
export async function tryReconnect() {
  const connected = await checkConnection();
  if (connected) {
    startHealthChecks();
    logger.info('Reconnected to server');
  }
  return connected;
}

// =============================================================================
// Sync Operations (placeholders for Phase 3)
// =============================================================================

/**
 * Download a file for offline use
 * @param {number} fileId - Server file ID
 * @returns {Promise<{success: boolean, message: string}>}
 */
export async function downloadFileForOffline(fileId) {
  const url = getApiBase();

  try {
    isSyncing.set(true);

    const response = await fetch(`${url}/api/ldm/files/${fileId}/download-for-offline`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders()
      }
    });

    if (response.ok) {
      const result = await response.json();
      logger.success('File downloaded for offline', {
        fileId,
        fileName: result.file_name,
        rows: result.row_count
      });
      offlineAvailable.set(true);
      return { success: true, message: result.message };
    } else {
      const error = await response.json();
      throw new Error(error.detail || 'Download failed');
    }
  } catch (error) {
    logger.error('Download for offline failed', { fileId, error: error.message });
    throw error;
  } finally {
    isSyncing.set(false);
  }
}

/**
 * Sync local changes to server
 * @param {number} fileId - File ID to sync
 */
export async function syncFileToServer(fileId) {
  // Will be implemented in Phase 3
  logger.info('Sync to server requested', { fileId });
  // TODO: Push local changes to server
}

/**
 * Get sync status for a file
 * @param {number} fileId - File ID
 * @returns {Object} Sync status info
 */
export function getFileSyncStatus(fileId) {
  // Will be implemented in Phase 2
  return {
    isDownloaded: false,
    hasChanges: false,
    lastSync: null
  };
}

// =============================================================================
// Initialize
// =============================================================================

/**
 * Initialize sync system
 */
export async function initSync() {
  logger.info('Initializing sync system');
  startHealthChecks();
  await refreshOfflineStatus();
}

/**
 * Refresh offline status from server
 */
export async function refreshOfflineStatus() {
  const url = getApiBase();

  try {
    const response = await fetch(`${url}/api/ldm/offline/status`, {
      headers: getAuthHeaders()
    });

    if (response.ok) {
      const status = await response.json();
      offlineAvailable.set(status.offline_available);
      pendingChanges.set(status.pending_changes);
      if (status.last_sync) {
        lastSync.set(status.last_sync);
      }
      logger.debug('Offline status refreshed', {
        files: status.file_count,
        pending: status.pending_changes
      });
    }
  } catch (error) {
    logger.debug('Could not refresh offline status', { error: error.message });
  }
}

/**
 * Cleanup sync system
 */
export function cleanupSync() {
  stopHealthChecks();
}
