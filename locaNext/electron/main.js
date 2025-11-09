import { app, BrowserWindow, Menu, ipcMain, dialog, shell } from 'electron';
import path from 'path';
import { fileURLToPath } from 'url';
import { spawn } from 'child_process';
import fs from 'fs';
import { logger } from './logger.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const isDev = process.env.NODE_ENV === 'development';

let mainWindow;

// Get project root directory (parent of locaNext folder)
const projectRoot = path.join(__dirname, '../..');
const pythonToolsPath = path.join(projectRoot, 'client', 'tools');

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
app.whenReady().then(() => {
  logger.info('Electron app ready', {
    version: app.getVersion(),
    platform: process.platform,
    nodeVersion: process.version
  });

  createWindow();

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
    app.quit();
  }
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
