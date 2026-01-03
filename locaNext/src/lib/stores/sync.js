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

// Track if reconnect is in progress (prevent rapid toggles)
let isReconnecting = false;

/**
 * Force switch to offline mode
 */
export function goOffline() {
  // Cancel any pending reconnect
  isReconnecting = false;
  stopHealthChecks();
  connectionMode.set('offline');
  connectionError.set(null);
  logger.info('Switched to offline mode');
}

/**
 * Try to reconnect to server
 */
export async function tryReconnect() {
  // Prevent rapid toggles
  if (isReconnecting) {
    logger.debug('Reconnect already in progress, skipping');
    return false;
  }

  isReconnecting = true;
  try {
    const connected = await checkConnection();
    if (connected) {
      startHealthChecks();
      logger.info('Reconnected to server');
    }
    return connected;
  } finally {
    isReconnecting = false;
  }
}

// =============================================================================
// Sync Operations (placeholders for Phase 3)
// =============================================================================

/**
 * Subscribe an entity for offline sync
 * @param {string} entityType - 'platform', 'project', or 'file'
 * @param {number} entityId - Entity ID
 * @param {string} entityName - Entity name for display
 * @returns {Promise<{success: boolean, message: string}>}
 */
export async function subscribeForOffline(entityType, entityId, entityName) {
  const url = getApiBase();

  try {
    isSyncing.set(true);

    const response = await fetch(`${url}/api/ldm/offline/subscribe`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders()
      },
      body: JSON.stringify({
        entity_type: entityType,
        entity_id: entityId,
        entity_name: entityName
      })
    });

    if (response.ok) {
      const result = await response.json();
      logger.success('Enabled offline sync', { entityType, entityId, entityName });
      offlineAvailable.set(true);
      await refreshOfflineStatus();
      return { success: true, message: result.message };
    } else {
      const error = await response.json();
      throw new Error(error.detail || 'Subscribe failed');
    }
  } catch (error) {
    logger.error('Subscribe for offline failed', { entityType, entityId, error: error.message });
    throw error;
  } finally {
    isSyncing.set(false);
  }
}

/**
 * Unsubscribe an entity from offline sync
 * @param {string} entityType - 'platform', 'project', or 'file'
 * @param {number} entityId - Entity ID
 * @returns {Promise<{success: boolean}>}
 */
export async function unsubscribeFromOffline(entityType, entityId) {
  const url = getApiBase();

  try {
    const response = await fetch(`${url}/api/ldm/offline/subscribe/${entityType}/${entityId}`, {
      method: 'DELETE',
      headers: getAuthHeaders()
    });

    if (response.ok) {
      logger.success('Disabled offline sync', { entityType, entityId });
      await refreshOfflineStatus();
      return { success: true };
    } else {
      const error = await response.json();
      throw new Error(error.detail || 'Unsubscribe failed');
    }
  } catch (error) {
    logger.error('Unsubscribe failed', { entityType, entityId, error: error.message });
    throw error;
  }
}

/**
 * Check if an entity is subscribed for offline sync
 * @param {string} entityType - 'platform', 'project', or 'file'
 * @param {number} entityId - Entity ID
 * @returns {Promise<boolean>}
 */
export async function isSubscribed(entityType, entityId) {
  const url = getApiBase();

  try {
    const response = await fetch(`${url}/api/ldm/offline/subscriptions`, {
      headers: getAuthHeaders()
    });

    if (response.ok) {
      const data = await response.json();
      return data.subscriptions.some(
        s => s.entity_type === entityType && s.entity_id === entityId
      );
    }
    return false;
  } catch (error) {
    logger.debug('Could not check subscription', { error: error.message });
    return false;
  }
}

/**
 * Get all sync subscriptions
 * @returns {Promise<Array>}
 */
export async function getSubscriptions() {
  const url = getApiBase();

  try {
    const response = await fetch(`${url}/api/ldm/offline/subscriptions`, {
      headers: getAuthHeaders()
    });

    if (response.ok) {
      const data = await response.json();
      return data.subscriptions;
    }
    return [];
  } catch (error) {
    logger.debug('Could not get subscriptions', { error: error.message });
    return [];
  }
}

/**
 * Auto-sync a file when opened (background, non-blocking)
 * Only syncs if not already subscribed
 * @param {number} fileId - File ID
 * @param {string} fileName - File name for display
 */
export function autoSyncFileOnOpen(fileId, fileName) {
  // Run in background - don't block file opening
  (async () => {
    try {
      // Check if already subscribed
      const alreadySubscribed = await isSubscribed('file', fileId);
      if (alreadySubscribed) {
        logger.debug('File already synced for offline', { fileId });
        return;
      }

      // Subscribe with auto flag
      const url = getApiBase();
      const response = await fetch(`${url}/api/ldm/offline/subscribe`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders()
        },
        body: JSON.stringify({
          entity_type: 'file',
          entity_id: fileId,
          entity_name: fileName,
          auto_subscribed: true
        })
      });

      if (response.ok) {
        logger.debug('Auto-synced file for offline', { fileId, fileName });
        offlineAvailable.set(true);
      }
    } catch (error) {
      // Silent fail - auto-sync is best effort
      logger.debug('Auto-sync failed (non-critical)', { fileId, error: error.message });
    }
  })();
}

/**
 * Get preview of changes to push for a file
 * @param {number} fileId - File ID
 * @returns {Promise<{file_id: number, file_name: string, modified_rows: number, new_rows: number, total_changes: number}>}
 */
export async function getPushPreview(fileId) {
  const url = getApiBase();

  try {
    const response = await fetch(`${url}/api/ldm/offline/push-preview/${fileId}`, {
      headers: getAuthHeaders()
    });

    if (response.ok) {
      return await response.json();
    } else {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get push preview');
    }
  } catch (error) {
    logger.error('Get push preview failed', { fileId, error: error.message });
    throw error;
  }
}

/**
 * Sync local changes to server (P3 Phase 3)
 * @param {number} fileId - File ID to sync
 * @returns {Promise<{success: boolean, rows_pushed: number, message: string}>}
 */
export async function syncFileToServer(fileId) {
  const url = getApiBase();

  try {
    isSyncing.set(true);
    logger.info('Pushing changes to server', { fileId });

    const response = await fetch(`${url}/api/ldm/offline/push-changes`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders()
      },
      body: JSON.stringify({ file_id: fileId })
    });

    if (response.ok) {
      const result = await response.json();
      logger.success('Changes pushed to server', {
        fileId,
        rowsPushed: result.rows_pushed
      });

      // Refresh offline status
      await refreshOfflineStatus();

      return result;
    } else {
      const error = await response.json();
      throw new Error(error.detail || 'Push failed');
    }
  } catch (error) {
    logger.error('Push to server failed', { fileId, error: error.message });
    throw error;
  } finally {
    isSyncing.set(false);
  }
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
// Continuous Sync
// =============================================================================

let continuousSyncInterval = null;
const CONTINUOUS_SYNC_INTERVAL = 60000; // 60 seconds

/**
 * Sync all subscribed items (background refresh)
 * This keeps offline data fresh with server changes.
 */
export async function syncAllSubscriptions() {
  const url = getApiBase();

  // Don't sync if offline or already syncing
  let currentMode;
  connectionMode.subscribe(v => currentMode = v)();
  if (currentMode === 'offline') {
    logger.debug('Skipping sync - offline mode');
    return;
  }

  let syncing;
  isSyncing.subscribe(v => syncing = v)();
  if (syncing) {
    logger.debug('Skipping sync - already syncing');
    return;
  }

  try {
    isSyncing.set(true);

    // Get all subscriptions
    const subs = await getSubscriptions();
    if (subs.length === 0) {
      logger.debug('No subscriptions to sync');
      return;
    }

    logger.info(`Syncing ${subs.length} subscriptions...`);

    // Sync each subscription
    for (const sub of subs) {
      try {
        const response = await fetch(`${url}/api/ldm/offline/sync-subscription`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...getAuthHeaders()
          },
          body: JSON.stringify({
            entity_type: sub.entity_type,
            entity_id: sub.entity_id
          })
        });

        if (response.ok) {
          const result = await response.json();
          logger.debug(`Synced ${sub.entity_type}:${sub.entity_id}`, {
            updated: result.updated_count
          });
        } else {
          logger.warn(`Failed to sync ${sub.entity_type}:${sub.entity_id}`);
        }
      } catch (error) {
        logger.warn(`Sync error for ${sub.entity_type}:${sub.entity_id}`, {
          error: error.message
        });
      }
    }

    // Update last sync time
    lastSync.set(new Date().toISOString());
    await refreshOfflineStatus();

    logger.success(`Continuous sync complete: ${subs.length} subscriptions`);
  } catch (error) {
    logger.error('Continuous sync failed', { error: error.message });
  } finally {
    isSyncing.set(false);
  }
}

/**
 * Start continuous background sync
 */
export function startContinuousSync() {
  if (continuousSyncInterval) return;

  // Initial sync after 5 seconds
  setTimeout(() => {
    syncAllSubscriptions();
  }, 5000);

  // Periodic sync
  continuousSyncInterval = setInterval(syncAllSubscriptions, CONTINUOUS_SYNC_INTERVAL);
  logger.info('Continuous sync started', { interval: CONTINUOUS_SYNC_INTERVAL / 1000 + 's' });
}

/**
 * Stop continuous background sync
 */
export function stopContinuousSync() {
  if (continuousSyncInterval) {
    clearInterval(continuousSyncInterval);
    continuousSyncInterval = null;
    logger.info('Continuous sync stopped');
  }
}

/**
 * Manually trigger a sync of all subscriptions
 */
export async function manualSync() {
  logger.info('Manual sync triggered');
  await syncAllSubscriptions();
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
  startContinuousSync();
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
  stopContinuousSync();
}
