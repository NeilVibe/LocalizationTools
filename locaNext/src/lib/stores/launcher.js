/**
 * Launcher Store - Manages launcher phase and mode state
 *
 * The launcher is the first screen users see, handling:
 * - Update checking and downloading (auto-download)
 * - Server status display
 * - Two entry paths: [Start Offline] or [Login]
 */

import { writable, derived } from 'svelte/store';

// ═══════════════════════════════════════════════════════════════════
// LAUNCHER PHASE
// ═══════════════════════════════════════════════════════════════════

/**
 * Current phase of the launcher
 * - 'startup': Initial load, checking server status
 * - 'update-check': Checking for updates
 * - 'updating': Downloading update in background
 * - 'ready': Ready to show buttons
 * - 'login': Login form is visible
 * - 'dismissed': Launcher dismissed, show main app
 */
export const launcherPhase = writable('startup');

// ═══════════════════════════════════════════════════════════════════
// LAUNCHER MODE
// ═══════════════════════════════════════════════════════════════════

/**
 * Mode selected by user
 * - null: No mode selected yet (show launcher)
 * - 'offline': User chose Start Offline
 * - 'online': User logged in successfully
 */
export const launcherMode = writable(null);

// ═══════════════════════════════════════════════════════════════════
// SERVER STATUS
// ═══════════════════════════════════════════════════════════════════

/**
 * Server connection status
 * - 'checking': Testing connection
 * - 'connected': Server reachable
 * - 'offline': Server not reachable
 * - 'error': Connection error
 */
export const serverStatus = writable('checking');

// ═══════════════════════════════════════════════════════════════════
// UPDATE STATE
// ═══════════════════════════════════════════════════════════════════

/**
 * Comprehensive update state for the launcher
 */
export const updateState = writable({
  // Status flags
  checking: false,
  available: false,
  downloading: false,
  downloaded: false,
  error: null,
  skipped: false,

  // Update info
  info: null, // { version, releaseNotes, releaseDate }

  // Progress
  progress: {
    percent: 0,
    transferred: 0,
    total: 0,
    speed: 0,
    currentComponent: ''
  },

  // Patch update specifics
  mode: 'full', // 'patch' | 'full'
  patchComponents: [],
  patchTotalSize: 0,
  fullInstallerSize: 624 * 1024 * 1024, // ~624 MB

  // Calculated
  savingsPercent: 0
});

// ═══════════════════════════════════════════════════════════════════
// DERIVED STORES
// ═══════════════════════════════════════════════════════════════════

/**
 * Whether to show the launcher
 * Shows when: phase is not 'dismissed' AND mode is not selected
 */
export const showLauncher = derived(
  [launcherPhase, launcherMode],
  ([$phase, $mode]) => $phase !== 'dismissed' && $mode === null
);

/**
 * Whether login button should be disabled
 * Disabled when server is offline
 */
export const loginDisabled = derived(
  serverStatus,
  ($status) => $status !== 'connected'
);

/**
 * Whether an update is in progress (checking or downloading)
 */
export const updateInProgress = derived(
  updateState,
  ($state) => $state.checking || $state.downloading
);

/**
 * Update savings percentage for patch updates
 */
export const updateSavings = derived(
  updateState,
  ($state) => {
    if ($state.mode !== 'patch' || $state.patchTotalSize <= 0) return 0;
    return Math.round((1 - $state.patchTotalSize / $state.fullInstallerSize) * 100);
  }
);

// ═══════════════════════════════════════════════════════════════════
// ACTIONS
// ═══════════════════════════════════════════════════════════════════

/**
 * Set launcher to ready state
 */
export function setReady() {
  launcherPhase.set('ready');
}

/**
 * Start offline mode
 */
export function startOffline() {
  launcherMode.set('offline');
  launcherPhase.set('dismissed');
}

/**
 * Start online mode (after successful login)
 */
export function startOnline() {
  launcherMode.set('online');
  launcherPhase.set('dismissed');
}

/**
 * Show login form
 */
export function showLoginForm() {
  launcherPhase.set('login');
}

/**
 * Hide login form, go back to ready
 */
export function hideLoginForm() {
  launcherPhase.set('ready');
}

/**
 * Skip update and continue
 */
export function skipUpdate() {
  updateState.update(state => ({
    ...state,
    skipped: true
  }));
}

/**
 * Reset launcher to initial state
 * Used when logging out to show launcher again
 */
export function resetLauncher() {
  launcherPhase.set('startup');
  launcherMode.set(null);
  serverStatus.set('checking');
  updateState.set({
    checking: false,
    available: false,
    downloading: false,
    downloaded: false,
    error: null,
    skipped: false,
    info: null,
    progress: {
      percent: 0,
      transferred: 0,
      total: 0,
      speed: 0,
      currentComponent: ''
    },
    mode: 'full',
    patchComponents: [],
    patchTotalSize: 0,
    fullInstallerSize: 624 * 1024 * 1024,
    savingsPercent: 0
  });
}

/**
 * Update the update progress
 */
export function setUpdateProgress(progress) {
  updateState.update(state => ({
    ...state,
    progress: { ...state.progress, ...progress }
  }));
}

/**
 * Set update available
 */
export function setUpdateAvailable(info, patchInfo = null) {
  updateState.update(state => {
    const newState = {
      ...state,
      checking: false,
      available: true,
      info
    };

    if (patchInfo && patchInfo.available) {
      newState.mode = 'patch';
      newState.patchComponents = patchInfo.updates || [];
      newState.patchTotalSize = patchInfo.totalSize || 0;
      newState.savingsPercent = Math.round((1 - newState.patchTotalSize / newState.fullInstallerSize) * 100);
    }

    return newState;
  });
}

/**
 * Set update downloading
 */
export function setUpdateDownloading() {
  updateState.update(state => ({
    ...state,
    downloading: true
  }));
  launcherPhase.set('updating');
}

/**
 * Set update downloaded
 */
export function setUpdateDownloaded() {
  updateState.update(state => ({
    ...state,
    downloading: false,
    downloaded: true
  }));
}

/**
 * Set update error
 */
export function setUpdateError(error) {
  updateState.update(state => ({
    ...state,
    checking: false,
    downloading: false,
    error: typeof error === 'string' ? error : error?.message || 'Unknown error'
  }));
}

export default {
  // Stores
  launcherPhase,
  launcherMode,
  serverStatus,
  updateState,
  showLauncher,
  loginDisabled,
  updateInProgress,
  updateSavings,

  // Actions
  setReady,
  startOffline,
  startOnline,
  showLoginForm,
  hideLoginForm,
  skipUpdate,
  resetLauncher,
  setUpdateProgress,
  setUpdateAvailable,
  setUpdateDownloading,
  setUpdateDownloaded,
  setUpdateError
};
