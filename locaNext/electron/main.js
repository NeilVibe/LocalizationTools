import { app, BrowserWindow, Menu, ipcMain } from 'electron';
import path from 'path';
import { fileURLToPath } from 'url';
import { spawn } from 'child_process';
import fs from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const isDev = process.env.NODE_ENV === 'development';

let mainWindow;

// Get project root directory (parent of locaNext folder)
const projectRoot = path.join(__dirname, '../..');
const pythonToolsPath = path.join(projectRoot, 'client', 'tools');

function createWindow() {
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
    mainWindow.loadURL('http://localhost:5173');
    // Open DevTools in development
    mainWindow.webContents.openDevTools();
  } else {
    mainWindow.loadFile(path.join(__dirname, '../build/index.html'));
  }

  // Show window when ready
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  // Handle window closed
  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  // Create application menu (disable default menu in production)
  if (!isDev) {
    Menu.setApplicationMenu(null);
  }
}

// ==================== IPC HANDLERS ====================

/**
 * Execute Python script
 * Returns: { success, output, error }
 */
ipcMain.handle('execute-python', async (event, { scriptPath, args = [], cwd = null }) => {
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
      resolve({
        success: code === 0,
        output: stdout,
        error: stderr,
        exitCode: code
      });
    });

    python.on('error', (error) => {
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

// ==================== APP LIFECYCLE ====================

// App ready
app.whenReady().then(() => {
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

// Quit when all windows are closed (except macOS)
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// Handle uncaught exceptions
process.on('uncaughtException', (error) => {
  console.error('Uncaught exception:', error);
});
