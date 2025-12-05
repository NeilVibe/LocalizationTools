/**
 * Preload script for LocaNext
 * Exposes safe IPC methods to renderer process
 *
 * NOTE: Uses CommonJS require() instead of ES modules import
 * because Electron's sandboxed preload context doesn't support ES modules
 */

const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods to renderer
contextBridge.exposeInMainWorld('electron', {
  /**
   * Execute Python script
   * @param {object} params - { scriptPath, args, cwd }
   * @returns {Promise<{success, output, error, exitCode}>}
   */
  executePython: (params) => ipcRenderer.invoke('execute-python', params),

  /**
   * Get system paths
   * @returns {Promise<object>}
   */
  getPaths: () => ipcRenderer.invoke('get-paths'),

  /**
   * Read file (text)
   * @param {string} filePath
   * @returns {Promise<{success, data, error}>}
   */
  readFile: (filePath) => ipcRenderer.invoke('read-file', filePath),

  /**
   * Read file as buffer (for binary files like Excel)
   * @param {string} filePath
   * @returns {Promise<{success, data (base64), mimeType, error}>}
   */
  readFileBuffer: (filePath) => ipcRenderer.invoke('read-file-buffer', filePath),

  /**
   * Write file
   * @param {object} params - { filePath, data }
   * @returns {Promise<{success, error}>}
   */
  writeFile: (params) => ipcRenderer.invoke('write-file', params),

  /**
   * Check if file exists
   * @param {string} filePath
   * @returns {Promise<{success, exists, error}>}
   */
  fileExists: (filePath) => ipcRenderer.invoke('file-exists', filePath),

  /**
   * Open file dialog
   * @param {object} options - { title, filters, properties }
   * @returns {Promise<string[]|null>} - Array of file paths or null if cancelled
   */
  selectFiles: (options) => ipcRenderer.invoke('select-files', options),

  /**
   * Show item in file explorer
   * @param {string} filePath - Full path to file
   * @returns {Promise<void>}
   */
  showItemInFolder: (filePath) => ipcRenderer.invoke('show-item-in-folder', filePath),

  /**
   * Listen for Python output events
   * @param {function} callback - Receives { type, data }
   */
  onPythonOutput: (callback) => {
    ipcRenderer.on('python-output', (event, data) => callback(data));
  },

  /**
   * Remove Python output listener
   */
  offPythonOutput: () => {
    ipcRenderer.removeAllListeners('python-output');
  },

  /**
   * Append log message to file (for frontend logging)
   * @param {object} params - { logPath, message }
   * @returns {Promise<{success, error}>}
   */
  appendLog: (params) => ipcRenderer.invoke('append-log', params)
});

// Expose platform info
contextBridge.exposeInMainWorld('platform', {
  isElectron: true,
  node: process.versions.node,
  chrome: process.versions.chrome,
  electron: process.versions.electron
});

// Expose setup progress API (for first-run setup window)
contextBridge.exposeInMainWorld('electronAPI', {
  /**
   * Listen for setup progress events
   * @param {function} callback - Receives { step, status, progress, message }
   */
  onSetupProgress: (callback) => {
    ipcRenderer.on('setup-progress', (event, data) => callback(data));
  },

  /**
   * Retry setup
   * @param {object} paths - App paths
   * @returns {Promise<boolean>}
   */
  retrySetup: (paths) => ipcRenderer.invoke('retry-setup', paths)
});

// Expose auto-update API
contextBridge.exposeInMainWorld('electronUpdate', {
  /**
   * Listen for update available event
   * @param {function} callback - Receives { version, releaseNotes, releaseDate }
   */
  onUpdateAvailable: (callback) => {
    ipcRenderer.on('update-available', (event, info) => callback(info));
  },

  /**
   * Listen for download progress event
   * @param {function} callback - Receives { percent, transferred, total, bytesPerSecond }
   */
  onUpdateProgress: (callback) => {
    ipcRenderer.on('update-progress', (event, progress) => callback(progress));
  },

  /**
   * Listen for update downloaded event
   * @param {function} callback - Receives { version, releaseNotes }
   */
  onUpdateDownloaded: (callback) => {
    ipcRenderer.on('update-downloaded', (event, info) => callback(info));
  },

  /**
   * Listen for update error event
   * @param {function} callback - Receives error message
   */
  onUpdateError: (callback) => {
    ipcRenderer.on('update-error', (event, error) => callback(error));
  },

  /**
   * Start downloading the update
   */
  downloadUpdate: () => ipcRenderer.invoke('download-update'),

  /**
   * Quit and install the downloaded update
   */
  quitAndInstall: () => ipcRenderer.invoke('quit-and-install'),

  /**
   * Check for updates manually
   * @returns {Promise<{success, updateInfo, error}>}
   */
  checkForUpdates: () => ipcRenderer.invoke('check-for-updates'),

  /**
   * Remove all update listeners
   */
  removeListeners: () => {
    ipcRenderer.removeAllListeners('update-available');
    ipcRenderer.removeAllListeners('update-progress');
    ipcRenderer.removeAllListeners('update-downloaded');
    ipcRenderer.removeAllListeners('update-error');
  }
});

// Expose repair/health API
contextBridge.exposeInMainWorld('electronHealth', {
  /**
   * Run health check
   * @returns {Promise<{success, result, error}>}
   */
  runHealthCheck: () => ipcRenderer.invoke('run-health-check'),

  /**
   * Run repair
   * @param {string[]} components - ['deps', 'model'] or subset
   * @returns {Promise<{success, error}>}
   */
  runRepair: (components) => ipcRenderer.invoke('run-repair', components),

  /**
   * Get app info (version, paths, etc.)
   * @returns {Promise<object>}
   */
  getAppInfo: () => ipcRenderer.invoke('get-app-info')
});

// Expose telemetry API (P12.5.7)
contextBridge.exposeInMainWorld('electronTelemetry', {
  /**
   * Send telemetry log to Central Server
   * @param {string} level - 'info', 'success', 'warning', 'error', 'critical'
   * @param {string} message - Log message
   * @param {string} component - Component name (e.g., 'XLSTransfer', 'QuickSearch')
   * @param {object} data - Additional data
   * @returns {Promise<{success, error}>}
   */
  log: (level, message, component = null, data = null) =>
    ipcRenderer.invoke('telemetry-log', { level, message, component, data }),

  /**
   * Convenience methods for each log level
   */
  info: (message, component, data) =>
    ipcRenderer.invoke('telemetry-log', { level: 'info', message, component, data }),
  success: (message, component, data) =>
    ipcRenderer.invoke('telemetry-log', { level: 'success', message, component, data }),
  warning: (message, component, data) =>
    ipcRenderer.invoke('telemetry-log', { level: 'warning', message, component, data }),
  error: (message, component, data) =>
    ipcRenderer.invoke('telemetry-log', { level: 'error', message, component, data }),
  critical: (message, component, data) =>
    ipcRenderer.invoke('telemetry-log', { level: 'critical', message, component, data }),

  /**
   * Get telemetry state (for debugging)
   * @returns {Promise<{enabled, serverUrl, installationId, sessionId, queueSize, isOnline}>}
   */
  getState: () => ipcRenderer.invoke('get-telemetry-state')
});

console.log('LocaNext preload script loaded');
