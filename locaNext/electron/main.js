import { app, BrowserWindow, Menu, ipcMain, dialog, shell } from 'electron';
import path from 'path';
import { fileURLToPath } from 'url';
import { spawn } from 'child_process';
import fs from 'fs';
import http from 'http';
import { logger } from './logger.js';
import { autoUpdaterConfig, isAutoUpdateEnabled } from './updater.js';

// Auto-updater (only in production builds)
let autoUpdater = null;
if (!process.env.NODE_ENV?.includes('development')) {
  try {
    const { autoUpdater: updater } = await import('electron-updater');
    autoUpdater = updater;
  } catch (e) {
    // electron-updater not installed, skip auto-updates
    logger.warning('electron-updater not available, auto-updates disabled');
  }
}

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const isDev = process.env.NODE_ENV === 'development';

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
    // app.asar is in resources/, app root is one level up
    const appRoot = path.join(app.getAppPath(), '..', '..');
    return {
      projectRoot: appRoot,
      pythonToolsPath: path.join(appRoot, 'tools'),
      serverPath: path.join(appRoot, 'server'),
      pythonExe: path.join(appRoot, 'tools', 'python', 'python.exe'),
      modelsPath: path.join(appRoot, 'models')
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
    logger.info('Development mode - expecting backend server at localhost:8888');
    try {
      await waitForServer('http://localhost:8888', 5, 500);
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
      LOCANEXT_MODELS_PATH: paths.modelsPath
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
  try {
    await waitForServer('http://localhost:8888', 30, 1000);
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
  if (!autoUpdater || !isAutoUpdateEnabled) {
    logger.info('Auto-updater disabled (development mode or not installed)');
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

  // Update downloaded
  autoUpdater.on('update-downloaded', (info) => {
    logger.success('Update downloaded', { version: info.version });
    mainWindow?.webContents.send('update-downloaded', info);

    // Prompt user to restart
    dialog.showMessageBox(mainWindow, {
      type: 'info',
      title: 'Update Ready',
      message: `Version ${info.version} has been downloaded.`,
      detail: 'The application will restart to install the update.',
      buttons: ['Restart Now', 'Later']
    }).then((result) => {
      if (result.response === 0) {
        autoUpdater.quitAndInstall();
      }
    });
  });

  // Error
  autoUpdater.on('error', (err) => {
    logger.error('Auto-updater error', { error: err.message });
  });

  // Check for updates (silently)
  autoUpdater.checkForUpdates().catch((err) => {
    logger.warning('Failed to check for updates', { error: err.message });
  });
}

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

function createWindow() {
  logger.info('Creating main window', { isDev, width: 1400, height: 900 });

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
    logger.info('Loading production build', { path: buildPath });
    mainWindow.loadFile(buildPath);
  }

  // Show window when ready
  mainWindow.once('ready-to-show', () => {
    logger.success('Main window ready and visible');
    mainWindow.show();
  });

  // Handle window closed
  mainWindow.on('closed', () => {
    logger.info('Main window closed');
    mainWindow = null;
  });

  // Create application menu (disable default menu in production)
  if (!isDev) {
    Menu.setApplicationMenu(null);
    logger.info('Application menu disabled (production mode)');
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
    const python = spawn('python3', [scriptPath, ...args], {
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
 * Read file
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

  // Start backend server first
  const serverReady = await startBackendServer();
  if (!serverReady && !isDev) {
    logger.error('Failed to start backend server - app may not function correctly');
    // Show error dialog to user
    dialog.showErrorBox(
      'Backend Server Error',
      'Failed to start the backend server. The application may not function correctly.\n\n' +
      'Please try restarting the application or contact support.'
    );
  }

  createWindow();

  // Setup auto-updater (checks your internal server for updates)
  setupAutoUpdater();

  app.on('activate', () => {
    logger.info('App activated');
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

// Quit when all windows are closed (except macOS)
app.on('window-all-closed', () => {
  logger.info('All windows closed');
  if (process.platform !== 'darwin') {
    logger.info('Quitting application');
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
app.on('before-quit', () => {
  logger.info('Application before quit');
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
