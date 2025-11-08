/**
 * Preload script for LocaNext
 * Exposes safe IPC methods to renderer process
 */

import { contextBridge, ipcRenderer } from 'electron';

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
   * Read file
   * @param {string} filePath
   * @returns {Promise<{success, data, error}>}
   */
  readFile: (filePath) => ipcRenderer.invoke('read-file', filePath),

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
  }
});

// Expose platform info
contextBridge.exposeInMainWorld('platform', {
  isElectron: true,
  node: process.versions.node,
  chrome: process.versions.chrome,
  electron: process.versions.electron
});

console.log('LocaNext preload script loaded');
