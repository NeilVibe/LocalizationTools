/**
 * LocaNext Main Process
 * GLOBAL ERROR HANDLERS MUST BE SET UP IMMEDIATELY AFTER IMPORTS
 */

import { app, BrowserWindow, Menu, ipcMain, dialog, shell } from 'electron';
import path from 'path';
import { fileURLToPath } from 'url';
import { spawn } from 'child_process';
import fs from 'fs';
import http from 'http';
import { logger } from './logger.js';
import { autoUpdaterConfig, isAutoUpdateEnabled } from './updater.js';
import { isFirstRunNeeded, runFirstRunSetup, setupFirstRunIPC } from './first-run-setup.js';
import { performHealthCheck, quickHealthCheck, wasRecentlyRepaired, HealthStatus } from './health-check.js';
import { runRepair } from './repair.js';
import { showSplash, updateSplash, closeSplash } from './splash.js';
import { initializeTelemetry, shutdownTelemetry, telemetryLog, getTelemetryState } from './telemetry.js';

// ==================== GLOBAL ERROR HANDLERS ====================
// These MUST be registered immediately to catch any startup errors

process.on('uncaughtException', (error) => {
  logger.crash(error);
  logger.critical('UNCAUGHT EXCEPTION', { message: error.message, stack: error.stack });
});

process.on('unhandledRejection', (reason, promise) => {
  logger.critical('UNHANDLED REJECTION', { reason: String(reason), promise: String(promise) });
});

// ==================== INTERCEPT ERROR DIALOGS ====================
// Capture error dialog content BEFORE it shows, log it, then show it
const originalShowErrorBox = dialog.showErrorBox;
dialog.showErrorBox = (title, content) => {
  // LOG THE ERROR FIRST
  logger.critical('ERROR DIALOG INTERCEPTED', { title, content });
  // Then show it to user
  originalShowErrorBox(title, content);
};

// Catch renderer/GPU crashes
app.on('render-process-gone', (event, webContents, details) => {
  logger.critical('RENDERER CRASHED', { reason: details.reason, exitCode: details.exitCode });
});

app.on('child-process-gone', (event, details) => {
  logger.critical('CHILD PROCESS GONE', { type: details.type, reason: details.reason });
});

// Log startup immediately
logger.info('================== APP STARTING ==================');
logger.info('Process info', {
  execPath: process.execPath,
  cwd: process.cwd(),
  argv: process.argv.slice(0, 3),
  platform: process.platform,
  version: process.version
});

// Auto-updater (only in production builds)
let autoUpdater = null;
logger.info('Auto-updater module loading', { NODE_ENV: process.env.NODE_ENV });
if (!process.env.NODE_ENV?.includes('development')) {
  try {
    const { autoUpdater: updater } = await import('electron-updater');
    autoUpdater = updater;
    logger.info('electron-updater loaded successfully');
  } catch (e) {
    // electron-updater not installed, skip auto-updates
    logger.warning('electron-updater not available', { error: e.message });
  }
} else {
  logger.info('Skipping auto-updater (development mode)');
}

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const isDev = process.env.NODE_ENV === 'development';

// DEBUG_MODE: Enable full debugging in production builds
// Set to true to enable: DevTools auto-open, verbose logging, show menu bar
// Launch with: --remote-debugging-port=9222 for CDP access
const DEBUG_MODE = false; // Production-ready: menu hidden, DevTools closed by default

let mainWindow;
let backendProcess = null;

// Get paths based on dev vs production
const getAppPaths = () => {
  if (isDev) {
    // Development: project structure
    const projectRoot = path.join(__dirname, '../..');
    return {
      projectRoot,
      pythonToolsPath: path.join(projectRoot, 'server', 'tools'),
      serverPath: path.join(projectRoot, 'server'),
      pythonExe: 'python3',  // Use system Python in dev
      modelsPath: path.join(projectRoot, 'models')
    };
  } else {
    // Production: installed app structure
    // app.asar is in resources/, extraResources also goes to resources/
    const resourcesPath = path.join(app.getAppPath(), '..');
    const appRoot = path.join(resourcesPath, '..');

    // QA FULL builds bundle models in resources/models (extraResources)
    // LIGHT builds download to appRoot/models post-install
    // Check bundled location first, fall back to download location
    const bundledModelsPath = path.join(resourcesPath, 'models');
    const downloadedModelsPath = path.join(appRoot, 'models');
    const modelsPath = fs.existsSync(path.join(bundledModelsPath, 'qwen-embedding', 'config.json'))
      ? bundledModelsPath  // QA FULL: use bundled model
      : downloadedModelsPath;  // LIGHT: use downloaded model

    return {
      projectRoot: appRoot,
      pythonToolsPath: path.join(resourcesPath, 'tools'),  // extraResources goes to resources/tools
      serverPath: path.join(resourcesPath, 'server'),      // extraResources: server → resources/server
      pythonExe: path.join(resourcesPath, 'tools', 'python', 'python.exe'),  // extraResources: tools/python → resources/tools/python
      modelsPath: modelsPath  // QA FULL: resources/models, LIGHT: appRoot/models (downloaded)
    };
  }
};

const paths = getAppPaths();
const projectRoot = paths.projectRoot;
const pythonToolsPath = paths.pythonToolsPath;

// ==================== BACKEND SERVER MANAGEMENT ====================

/**
 * Wait for backend server to be ready
 */
function waitForServer(url, maxRetries = 30, retryDelay = 1000) {
  return new Promise((resolve, reject) => {
    let retries = 0;

    const checkServer = () => {
      http.get(`${url}/health`, (res) => {
        if (res.statusCode === 200) {
          logger.success('Backend server is ready', { url });
          resolve(true);
        } else {
          retry();
        }
      }).on('error', () => {
        retry();
      });
    };

    const retry = () => {
      retries++;
      if (retries >= maxRetries) {
        logger.error('Backend server failed to start', { retries, url });
        reject(new Error('Backend server timeout'));
      } else {
        logger.info(`Waiting for backend... (${retries}/${maxRetries})`);
        setTimeout(checkServer, retryDelay);
      }
    };

    checkServer();
  });
}

/**
 * Start the Python backend server
 */
async function startBackendServer() {
  if (isDev) {
    // In development, assume server is running separately
    // Use 127.0.0.1 instead of localhost to avoid IPv6 resolution issues on Windows
    logger.info('Development mode - expecting backend server at 127.0.0.1:8888');
    try {
      await waitForServer('http://127.0.0.1:8888', 5, 500);
      return true;
    } catch {
      logger.warning('Backend server not running. Please start it manually: python3 server/main.py');
      return false;
    }
  }

  // Production: start embedded Python server
  logger.info('Starting embedded backend server...', {
    pythonExe: paths.pythonExe,
    serverPath: paths.serverPath
  });

  const serverScript = path.join(paths.serverPath, 'main.py');

  // Check if files exist
  if (!fs.existsSync(paths.pythonExe)) {
    logger.error('Python executable not found', { path: paths.pythonExe });
    return false;
  }
  if (!fs.existsSync(serverScript)) {
    logger.error('Server script not found', { path: serverScript });
    return false;
  }

  // Start the server process
  backendProcess = spawn(paths.pythonExe, [serverScript], {
    cwd: paths.projectRoot,
    env: {
      ...process.env,
      PYTHONUNBUFFERED: '1',
      PYTHONPATH: paths.projectRoot,
      LOCANEXT_MODELS_PATH: paths.modelsPath,
      // Suppress Python warnings (FutureWarning, UserWarning, etc.)
      PYTHONWARNINGS: 'ignore',
      // Suppress TensorFlow/transformers logs
      TF_CPP_MIN_LOG_LEVEL: '3',
      TRANSFORMERS_VERBOSITY: 'error',
      TOKENIZERS_PARALLELISM: 'false'
    },
    stdio: ['ignore', 'pipe', 'pipe'],
    detached: false,
    windowsHide: true
  });

  // Log server output
  backendProcess.stdout.on('data', (data) => {
    logger.info('[Backend]', { output: data.toString().trim() });
  });

  backendProcess.stderr.on('data', (data) => {
    logger.warning('[Backend stderr]', { output: data.toString().trim() });
  });

  backendProcess.on('error', (error) => {
    logger.error('Backend process error', { error: error.message });
  });

  backendProcess.on('exit', (code, signal) => {
    logger.info('Backend process exited', { code, signal });
    backendProcess = null;
  });

  // Wait for server to be ready
  // Use 127.0.0.1 instead of localhost to avoid IPv6 resolution issues on Windows
  try {
    await waitForServer('http://127.0.0.1:8888', 30, 1000);
    return true;
  } catch (error) {
    logger.error('Backend server failed to start', { error: error.message });
    return false;
  }
}

/**
 * Stop the backend server
 */
function stopBackendServer() {
  if (backendProcess) {
    logger.info('Stopping backend server...');

    // On Windows, we need to kill the process tree
    if (process.platform === 'win32') {
      spawn('taskkill', ['/pid', backendProcess.pid, '/f', '/t']);
    } else {
      backendProcess.kill('SIGTERM');
    }

    backendProcess = null;
    logger.success('Backend server stopped');
  }
}

// ==================== AUTO-UPDATER ====================

/**
 * Setup auto-updater to check for updates from your server
 */
function setupAutoUpdater() {
  logger.info('Auto-updater check', {
    autoUpdaterLoaded: !!autoUpdater,
    isAutoUpdateEnabled,
    NODE_ENV: process.env.NODE_ENV
  });

  if (!autoUpdater || !isAutoUpdateEnabled) {
    logger.info('Auto-updater disabled', {
      reason: !autoUpdater ? 'module not loaded' : 'disabled by config',
      autoUpdaterLoaded: !!autoUpdater,
      isAutoUpdateEnabled
    });
    return;
  }

  logger.info('Setting up auto-updater', { config: autoUpdaterConfig });

  // Configure update server
  autoUpdater.setFeedURL(autoUpdaterConfig);

  // Update available
  autoUpdater.on('update-available', (info) => {
    logger.info('Update available', { version: info.version });
    mainWindow?.webContents.send('update-available', info);
  });

  // No update available
  autoUpdater.on('update-not-available', (info) => {
    logger.info('App is up to date', { version: info.version });
  });

  // Download progress
  autoUpdater.on('download-progress', (progressObj) => {
    logger.info('Download progress', {
      percent: progressObj.percent,
      transferred: progressObj.transferred,
      total: progressObj.total
    });
    mainWindow?.webContents.send('update-progress', progressObj);
  });

  // Update downloaded - send to renderer (custom UI will handle it)
  autoUpdater.on('update-downloaded', (info) => {
    logger.success('Update downloaded', { version: info.version });
    mainWindow?.webContents.send('update-downloaded', info);
    // No system dialog - the UpdateModal in renderer will show restart options
  });

  // Error - send to renderer
  autoUpdater.on('error', (err) => {
    logger.error('Auto-updater error', { error: err.message });
    mainWindow?.webContents.send('update-error', err.message);
  });

  // Check for updates (silently)
  autoUpdater.checkForUpdates().catch((err) => {
    logger.warning('Failed to check for updates', { error: err.message });
  });
}

/**
 * IPC: Download update
 */
ipcMain.handle('download-update', async () => {
  if (!autoUpdater) {
    return { success: false, error: 'Auto-updater not available' };
  }

  try {
    logger.info('Starting update download...');
    await autoUpdater.downloadUpdate();
    return { success: true };
  } catch (error) {
    logger.error('Failed to download update', { error: error.message });
    return { success: false, error: error.message };
  }
});

/**
 * IPC: Quit and install update
 */
ipcMain.handle('quit-and-install', async () => {
  if (!autoUpdater) {
    return { success: false, error: 'Auto-updater not available' };
  }

  logger.info('Quitting and installing update...');
  autoUpdater.quitAndInstall();
  return { success: true };
});

/**
 * IPC: Exit app (used when setup fails)
 */
ipcMain.handle('exit-app', async () => {
  logger.info('User requested app exit');
  app.quit();
});

/**
 * IPC: Check for updates manually
 */
ipcMain.handle('check-for-updates', async () => {
  if (!autoUpdater) {
    return { success: false, error: 'Auto-updater not available' };
  }

  try {
    const result = await autoUpdater.checkForUpdates();
    return { success: true, updateInfo: result?.updateInfo };
  } catch (error) {
    return { success: false, error: error.message };
  }
});

// ==================== REPAIR IPC HANDLERS ====================

/**
 * IPC: Run health check
 */
ipcMain.handle('run-health-check', async () => {
  try {
    const result = await performHealthCheck(paths);
    return { success: true, result };
  } catch (error) {
    return { success: false, error: error.message };
  }
});

/**
 * IPC: Run manual repair
 */
ipcMain.handle('run-repair', async (event, components = ['deps', 'model']) => {
  try {
    logger.info('Manual repair requested', { components });
    const success = await runRepair(paths, components);
    return { success };
  } catch (error) {
    logger.error('Manual repair failed', { error: error.message });
    return { success: false, error: error.message };
  }
});

/**
 * IPC: Get app paths for frontend
 */
ipcMain.handle('get-app-info', async () => {
  return {
    version: app.getVersion(),
    paths: {
      projectRoot: paths.projectRoot,
      modelsPath: paths.modelsPath,
      serverPath: paths.serverPath
    },
    isPackaged: app.isPackaged,
    platform: process.platform
  };
});

/**
 * IPC: Toggle DevTools (for dev/debug access from Settings)
 */
ipcMain.handle('toggle-dev-tools', async () => {
  if (mainWindow) {
    if (mainWindow.webContents.isDevToolsOpened()) {
      mainWindow.webContents.closeDevTools();
      logger.info('DevTools closed via IPC');
      return { success: true, opened: false };
    } else {
      mainWindow.webContents.openDevTools();
      logger.info('DevTools opened via IPC');
      return { success: true, opened: true };
    }
  }
  return { success: false, error: 'No main window' };
});

/**
 * IPC: Check if DevTools is open
 */
ipcMain.handle('is-dev-tools-open', async () => {
  if (mainWindow) {
    return { success: true, opened: mainWindow.webContents.isDevToolsOpened() };
  }
  return { success: false, opened: false };
});

// ==================== TELEMETRY IPC HANDLERS (P12.5.7) ====================

/**
 * IPC: Send telemetry log from frontend
 */
ipcMain.handle('telemetry-log', async (event, { level, message, component, data }) => {
  try {
    telemetryLog[level.toLowerCase()]?.(message, component, data);
    return { success: true };
  } catch (error) {
    return { success: false, error: error.message };
  }
});

/**
 * IPC: Get telemetry state for debugging
 */
ipcMain.handle('get-telemetry-state', async () => {
  return getTelemetryState();
});

function createWindow() {
  logger.info('Creating main window', { isDev, DEBUG_MODE, width: 1400, height: 900 });

  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1200,
    minHeight: 700,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    },
    title: 'LocaNext',
    backgroundColor: '#0f0f0f',
    show: false // Don't show until ready
  });

  // Load the app
  if (isDev) {
    logger.info('Loading development URL', { url: 'http://localhost:5173' });
    mainWindow.loadURL('http://localhost:5173');
    // Open DevTools in development
    mainWindow.webContents.openDevTools();
  } else {
    const buildPath = path.join(__dirname, '../build/index.html');
    logger.info('Loading production build', { path: buildPath, DEBUG_MODE });
    mainWindow.loadFile(buildPath);

    // Open DevTools in production if DEBUG_MODE is enabled
    if (DEBUG_MODE) {
      logger.info('DEBUG_MODE: Opening DevTools in production');
      mainWindow.webContents.openDevTools();
    }
  }

  // ==================== RENDERER LOGGING ====================
  // Capture ALL console output from the frontend (Svelte)
  mainWindow.webContents.on('console-message', (event, level, message, line, sourceId) => {
    const levelMap = { 0: 'DEBUG', 1: 'INFO', 2: 'WARNING', 3: 'ERROR' };
    const levelName = levelMap[level] || 'LOG';
    logger.info(`[Renderer ${levelName}]`, { message, line, source: sourceId });
  });

  // Log when page starts loading
  mainWindow.webContents.on('did-start-loading', () => {
    logger.info('[Renderer] Page started loading');
  });

  // Log when page finishes loading
  mainWindow.webContents.on('did-finish-load', () => {
    logger.success('[Renderer] Page finished loading');
  });

  // Log DOM ready
  mainWindow.webContents.on('dom-ready', () => {
    logger.info('[Renderer] DOM ready');
  });

  // Capture load failures (critical for debugging black screen!)
  mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription, validatedURL) => {
    logger.error('[Renderer] FAILED TO LOAD', {
      errorCode,
      errorDescription,
      url: validatedURL
    });
  });

  // Capture preload script errors
  mainWindow.webContents.on('preload-error', (event, preloadPath, error) => {
    logger.error('[Renderer] PRELOAD ERROR', {
      preloadPath,
      error: error.message,
      stack: error.stack
    });
  });

  // Show window when ready
  mainWindow.once('ready-to-show', () => {
    logger.success('Main window ready and visible');
    closeSplash(); // Close splash screen
    updateSplash('Ready!', 100); // In case splash is still visible
    mainWindow.show();
  });

  // Handle window closed
  mainWindow.on('closed', () => {
    logger.info('Main window closed');
    mainWindow = null;
  });

  // Keyboard shortcuts for DevTools (Ctrl+Shift+I or F12)
  // Available even in production for debugging when needed
  mainWindow.webContents.on('before-input-event', (event, input) => {
    // F12 or Ctrl+Shift+I to toggle DevTools
    if (input.key === 'F12' || (input.control && input.shift && input.key.toLowerCase() === 'i')) {
      if (mainWindow.webContents.isDevToolsOpened()) {
        mainWindow.webContents.closeDevTools();
        logger.info('DevTools closed via keyboard shortcut');
      } else {
        mainWindow.webContents.openDevTools();
        logger.info('DevTools opened via keyboard shortcut');
      }
      event.preventDefault();
    }
  });

  // Create application menu (disable default menu in production, unless DEBUG_MODE)
  if (!isDev && !DEBUG_MODE) {
    Menu.setApplicationMenu(null);
    logger.info('Application menu disabled (production mode)');
  } else if (DEBUG_MODE) {
    logger.info('DEBUG_MODE: Application menu kept visible for debugging');
  }
}

// ==================== IPC HANDLERS ====================

/**
 * Execute Python script
 * Returns: { success, output, error }
 */
ipcMain.handle('execute-python', async (event, { scriptPath, args = [], cwd = null }) => {
  logger.ipc('execute-python', { scriptPath, args, cwd });

  return new Promise((resolve) => {
    // Use the correct Python executable (python.exe on Windows, python3 on Linux)
    const pythonExe = paths.pythonExe || 'python3';
    logger.info('Executing Python script', { pythonExe, scriptPath, args });

    const python = spawn(pythonExe, [scriptPath, ...args], {
      cwd: cwd || pythonToolsPath,
      env: {
        ...process.env,
        PYTHONUNBUFFERED: '1',
        PYTHONPATH: projectRoot  // Add project root to Python path
      }
    });

    let stdout = '';
    let stderr = '';

    python.stdout.on('data', (data) => {
      stdout += data.toString();
      // Send progress updates to renderer
      mainWindow?.webContents.send('python-output', {
        type: 'stdout',
        data: data.toString()
      });
    });

    python.stderr.on('data', (data) => {
      stderr += data.toString();
      mainWindow?.webContents.send('python-output', {
        type: 'stderr',
        data: data.toString()
      });
    });

    python.on('close', (code) => {
      const success = code === 0;
      logger.python(scriptPath, success, stdout || stderr);

      resolve({
        success,
        output: stdout,
        error: stderr,
        exitCode: code
      });
    });

    python.on('error', (error) => {
      logger.error('Python execution error', { scriptPath, error: error.message });

      resolve({
        success: false,
        output: '',
        error: error.message,
        exitCode: -1
      });
    });
  });
});

/**
 * Get system paths
 */
ipcMain.handle('get-paths', async () => {
  return {
    projectRoot,
    pythonToolsPath,
    appPath: app.getAppPath(),
    userData: app.getPath('userData'),
    temp: app.getPath('temp')
  };
});

/**
 * Read file (text)
 */
ipcMain.handle('read-file', async (event, filePath) => {
  try {
    const data = await fs.promises.readFile(filePath, 'utf-8');
    return { success: true, data };
  } catch (error) {
    return { success: false, error: error.message };
  }
});

/**
 * Read file as buffer (for binary files like Excel)
 */
ipcMain.handle('read-file-buffer', async (event, filePath) => {
  try {
    const buffer = await fs.promises.readFile(filePath);
    // Return as base64 for transfer to renderer
    return { success: true, data: buffer.toString('base64'), mimeType: getMimeType(filePath) };
  } catch (error) {
    return { success: false, error: error.message };
  }
});

function getMimeType(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  const mimeTypes = {
    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    '.xls': 'application/vnd.ms-excel',
    '.txt': 'text/plain',
    '.csv': 'text/csv',
    '.json': 'application/json'
  };
  return mimeTypes[ext] || 'application/octet-stream';
}

/**
 * Write file
 */
ipcMain.handle('write-file', async (event, { filePath, data }) => {
  try {
    await fs.promises.writeFile(filePath, data, 'utf-8');
    return { success: true };
  } catch (error) {
    return { success: false, error: error.message };
  }
});

/**
 * Check if file exists
 */
ipcMain.handle('file-exists', async (event, filePath) => {
  try {
    await fs.promises.access(filePath);
    return { success: true, exists: true };
  } catch {
    return { success: true, exists: false };
  }
});

/**
 * Open file dialog
 * Returns: array of file paths or null if cancelled
 */
ipcMain.handle('select-files', async (event, options = {}) => {
  logger.ipc('select-files', { title: options.title });

  try {
    const result = await dialog.showOpenDialog(mainWindow, {
      title: options.title || 'Select Files',
      filters: options.filters || [],
      properties: options.properties || ['openFile']
    });

    if (result.canceled) {
      logger.info('File dialog cancelled by user');
      return null;
    }

    logger.success('Files selected', { count: result.filePaths.length });
    return result.filePaths;
  } catch (error) {
    logger.error('File dialog error', { error: error.message });
    return null;
  }
});

/**
 * Open folder dialog
 * Returns: folder path or null if cancelled
 */
ipcMain.handle('select-folder', async (event, options = {}) => {
  logger.ipc('select-folder', { title: options.title });

  try {
    const result = await dialog.showOpenDialog(mainWindow, {
      title: options.title || 'Select Folder',
      properties: ['openDirectory']
    });

    if (result.canceled) {
      logger.info('Folder dialog cancelled by user');
      return null;
    }

    logger.success('Folder selected', { path: result.filePaths[0] });
    return result.filePaths[0];
  } catch (error) {
    logger.error('Folder dialog error', { error: error.message });
    return null;
  }
});

/**
 * Recursively collect files from folder matching extensions
 * Returns: array of { path, name, content (base64) }
 */
ipcMain.handle('collect-folder-files', async (event, { folderPath, extensions = ['.xml', '.txt', '.tsv'] }) => {
  logger.ipc('collect-folder-files', { folderPath, extensions });

  try {
    const files = [];

    // Recursive function to walk directory
    const walkDir = async (dir) => {
      const entries = await fs.promises.readdir(dir, { withFileTypes: true });

      for (const entry of entries) {
        const fullPath = path.join(dir, entry.name);

        if (entry.isDirectory()) {
          await walkDir(fullPath);
        } else if (entry.isFile()) {
          const ext = path.extname(entry.name).toLowerCase();
          if (extensions.includes(ext)) {
            // Read file content as base64
            const content = await fs.promises.readFile(fullPath);
            files.push({
              path: fullPath,
              name: entry.name,
              content: content.toString('base64')
            });
          }
        }
      }
    };

    await walkDir(folderPath);

    logger.success('Folder files collected', { count: files.length, folderPath });
    return { success: true, files };
  } catch (error) {
    logger.error('Failed to collect folder files', { error: error.message, folderPath });
    return { success: false, error: error.message, files: [] };
  }
});

/**
 * IPC Handler: Show item in file explorer
 * Opens file explorer and highlights the specified file
 */
ipcMain.handle('show-item-in-folder', async (event, filePath) => {
  logger.ipc('show-item-in-folder', { filePath });

  try {
    shell.showItemInFolder(filePath);
    logger.success('Opened file in explorer', { filePath });
  } catch (error) {
    logger.error('Failed to open file in explorer', { error: error.message, filePath });
  }
});

/**
 * IPC Handler: Append log message to file
 * Used by frontend logger to write logs to file
 */
ipcMain.handle('append-log', async (event, { logPath, message }) => {
  try {
    const fullPath = path.join(paths.projectRoot, logPath);

    // Ensure logs directory exists
    const logDir = path.dirname(fullPath);
    if (!fs.existsSync(logDir)) {
      fs.mkdirSync(logDir, { recursive: true });
    }

    // Append message with newline
    fs.appendFileSync(fullPath, message + '\n', 'utf8');
    return { success: true };
  } catch (error) {
    console.error('Failed to append log:', error.message);
    return { success: false, error: error.message };
  }
});

// ==================== APP LIFECYCLE ====================

// App ready
app.whenReady().then(async () => {
  logger.info('Electron app ready', {
    version: app.getVersion(),
    platform: process.platform,
    nodeVersion: process.version,
    isDev,
    paths: paths
  });

  // Show splash screen immediately (production only)
  if (!isDev) {
    showSplash();
    updateSplash('Initializing...', 5);
  }

  // Setup first-run IPC handlers
  setupFirstRunIPC();

  // Check if first-run setup is needed (production only)
  try {
    updateSplash('Checking installation...', 10);
    const needsFirstRun = !isDev && isFirstRunNeeded(paths.projectRoot);
    logger.info('First-run check complete', { needsFirstRun, isDev, projectRoot: paths.projectRoot });

    if (needsFirstRun) {
      logger.info('First-run setup needed - starting setup wizard');
      closeSplash(); // Close splash, first-run has its own UI
      const setupSuccess = await runFirstRunSetup(paths);
      if (!setupSuccess) {
        logger.error('First-run setup failed - cannot continue');
        dialog.showErrorBox(
          'Setup Failed',
          'First-time setup could not be completed.\n\n' +
          'Please check your internet connection and try again.\n\n' +
          'If the problem persists, contact support.'
        );
        app.quit();
        return;
      }
      logger.success('First-run setup completed successfully');
      // Re-show splash for remaining startup
      showSplash();
      updateSplash('Setup complete, starting app...', 50);
    }
  } catch (firstRunError) {
    logger.error('First-run setup crashed', { error: firstRunError.message, stack: firstRunError.stack });
    closeSplash();
    dialog.showErrorBox(
      'Setup Error',
      `First-time setup encountered an error:\n\n${firstRunError.message}\n\n` +
      'Please report this issue.'
    );
    // Continue anyway - let user see what happens
    showSplash();
  }

  // ==================== HEALTH CHECK & AUTO-REPAIR ====================
  // DISABLED: Set to true to enable automatic health check and repair on every launch
  // When disabled, repair is manual only (via Settings or IPC)
  const ENABLE_AUTO_HEALTH_CHECK = false;

  if (!isDev && ENABLE_AUTO_HEALTH_CHECK) {
    try {
      updateSplash('Running health check...', 20);
      logger.info('Running startup health check');

      // Full health check (includes Python import verification)
      const healthResult = await performHealthCheck(paths);
      logger.info('Health check result', { status: healthResult.status, repairNeeded: healthResult.repairNeeded });

      if (healthResult.status === HealthStatus.CRITICAL_FAILURE) {
        logger.error('Critical failure - essential components missing');
        closeSplash();
        dialog.showErrorBox(
          'Critical Error',
          'Essential components are missing.\n\n' +
          'Please reinstall LocaNext from the original installer.'
        );
        app.quit();
        return;
      }

      if (healthResult.status === HealthStatus.NEEDS_REPAIR) {
        logger.info('Repair needed', { components: healthResult.repairNeeded });

        // Check if we recently tried to repair (prevent loops)
        if (wasRecentlyRepaired(paths.projectRoot)) {
          logger.warning('Recently attempted repair - skipping to prevent loop');
          closeSplash();
          dialog.showMessageBox({
            type: 'warning',
            title: 'Repair Needed',
            message: 'Some components are still missing after a recent repair attempt.\n\n' +
                    'The app will try to continue, but some features may not work.\n\n' +
                    'You can manually repair via Settings > Repair Installation.',
            buttons: ['Continue Anyway']
          });
          showSplash();
          updateSplash('Continuing with warnings...', 40);
        } else {
          // Run auto-repair
          updateSplash('Repairing components...', 30);
          closeSplash(); // Close splash, repair has its own UI
          logger.info('Starting auto-repair');
          const repairSuccess = await runRepair(paths, healthResult.repairNeeded);

          if (!repairSuccess) {
            logger.error('Auto-repair failed');
            const response = await dialog.showMessageBox({
              type: 'warning',
              title: 'Repair Incomplete',
              message: 'Some components could not be repaired.\n\n' +
                      'The app will try to continue, but some features may not work.',
              buttons: ['Continue Anyway', 'Quit'],
              defaultId: 0
            });

            if (response.response === 1) {
              app.quit();
              return;
            }
          } else {
            logger.success('Auto-repair completed successfully');
          }
          // Re-show splash for remaining startup
          showSplash();
          updateSplash('Repair complete...', 50);
        }
      } else {
        updateSplash('System healthy', 40);
      }
    } catch (healthError) {
      logger.error('Health check failed', { error: healthError.message });
      // Continue anyway - don't block app startup
      updateSplash('Continuing...', 40);
    }
  } else if (!isDev) {
    logger.info('Auto health check DISABLED - skipping to app startup');
    updateSplash('Starting...', 40);
  }

  // Start backend server
  updateSplash('Starting backend server...', 50);
  const serverReady = await startBackendServer();
  if (!serverReady && !isDev) {
    logger.error('Failed to start backend server - app may not function correctly');
    closeSplash();
    // Show error dialog to user
    dialog.showErrorBox(
      'Backend Server Error',
      'Failed to start the backend server. The application may not function correctly.\n\n' +
      'Please try restarting the application or contact support.'
    );
  }

  updateSplash('Loading interface...', 80);
  createWindow();

  // Setup auto-updater (checks your internal server for updates)
  setupAutoUpdater();

  // Initialize telemetry (P12.5.7)
  // Connects to Central Server for monitoring (if CENTRAL_SERVER_URL is set)
  initializeTelemetry(logger).then((success) => {
    if (success) {
      logger.info('Telemetry initialized successfully');
      telemetryLog.info('App started', 'main', { version: app.getVersion() });
    }
  }).catch((err) => {
    logger.warning('Telemetry initialization failed:', err.message);
  });

  app.on('activate', () => {
    logger.info('App activated');
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

// Quit when all windows are closed (except macOS)
app.on('window-all-closed', async () => {
  logger.info('All windows closed');
  if (process.platform !== 'darwin') {
    logger.info('Quitting application');

    // Shutdown telemetry before quit
    try {
      await shutdownTelemetry();
    } catch (err) {
      logger.warning('Telemetry shutdown error:', err.message);
    }

    stopBackendServer();  // Stop the backend server
    app.quit();
  }
});

// Clean up on quit
app.on('will-quit', () => {
  logger.info('Application will quit');
  stopBackendServer();
});

// Handle app before-quit (macOS)
app.on('before-quit', async () => {
  logger.info('Application before quit');

  // Shutdown telemetry (end session, flush logs)
  try {
    await shutdownTelemetry();
  } catch (err) {
    logger.warning('Telemetry shutdown error:', err.message);
  }

  stopBackendServer();
});

// Handle uncaught exceptions
process.on('uncaughtException', (error) => {
  logger.critical('Uncaught exception', {
    error: error.message,
    stack: error.stack
  });
});

// Handle unhandled promise rejections
process.on('unhandledRejection', (reason, promise) => {
  logger.error('Unhandled promise rejection', {
    reason: reason?.toString(),
    promise: promise?.toString()
  });
});
