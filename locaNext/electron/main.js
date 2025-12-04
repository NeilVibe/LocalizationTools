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
    closeSplash(); // Close splash screen
    updateSplash('Ready!', 100); // In case splash is still visible
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
  // Run on EVERY launch (not just first-run) to detect and fix issues
  if (!isDev) {
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
