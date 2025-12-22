/**
 * First-Run Setup Module
 *
 * Handles automatic setup on first app launch:
 * 1. Check if setup is needed (flag file)
 * 2. Install Python dependencies
 * 3. Download Embedding Model (Qwen/Qwen3-Embedding-0.6B)
 * 4. Create flag file when complete
 *
 * All with progress feedback to the UI.
 */

import { spawn } from 'child_process';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { BrowserWindow, ipcMain, Menu } from 'electron';
import { logger } from './logger.js';

// ESM dirname equivalent (import.meta.dirname is undefined in Node 18)
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Setup state
let setupWindow = null;
let isSetupRunning = false;

/**
 * Check if first-run setup is needed
 */
export function isFirstRunNeeded(appRoot) {
  const flagFile = path.join(appRoot, 'first_run_complete.flag');
  const exists = fs.existsSync(flagFile);
  logger.info('First-run check', { flagFile, exists, needed: !exists });
  return !exists;
}

/**
 * Create the setup complete flag file
 */
function createFlagFile(appRoot) {
  const flagFile = path.join(appRoot, 'first_run_complete.flag');
  const content = JSON.stringify({
    completedAt: new Date().toISOString(),
    version: process.env.npm_package_version || 'unknown'
  }, null, 2);
  fs.writeFileSync(flagFile, content);
  logger.success('First-run flag file created', { flagFile });
}

/**
 * Create the setup window
 */
function createSetupWindow() {
  setupWindow = new BrowserWindow({
    width: 550,
    height: 480,
    resizable: false,
    minimizable: false,
    maximizable: false,
    closable: false, // Can't close during setup
    frame: true,
    autoHideMenuBar: true,
    title: 'LocaNext - First Time Setup',
    backgroundColor: '#1a1a2e',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    }
  });

  // Remove menu bar completely for cleaner look
  setupWindow.setMenu(null);

  // Load setup HTML
  const setupHtml = path.join(__dirname, 'setup.html');
  if (fs.existsSync(setupHtml)) {
    setupWindow.loadFile(setupHtml);
  } else {
    // Fallback: create inline HTML
    setupWindow.loadURL(`data:text/html,${encodeURIComponent(getSetupHtml())}`);
  }

  return setupWindow;
}

/**
 * Inline HTML for setup window (fallback)
 */
function getSetupHtml() {
  return `
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>LocaNext - First Time Setup</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    html, body { overflow: hidden; width: 100%; height: 100%; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
      color: #fff;
      height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 40px;
    }
    h1 { font-size: 24px; margin-bottom: 10px; }
    .subtitle { color: #888; margin-bottom: 40px; }
    .step {
      width: 100%;
      margin-bottom: 20px;
      opacity: 0.5;
    }
    .step.active { opacity: 1; }
    .step.done { opacity: 0.7; }
    .step-header {
      display: flex;
      align-items: center;
      margin-bottom: 8px;
    }
    .step-icon {
      width: 24px;
      height: 24px;
      border-radius: 50%;
      background: #333;
      margin-right: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 12px;
    }
    .step.active .step-icon { background: #4a9eff; }
    .step.done .step-icon { background: #4caf50; }
    .step.error .step-icon { background: #f44336; }
    .step-title { font-weight: 500; }
    .progress-bar {
      width: 100%;
      height: 6px;
      background: #333;
      border-radius: 3px;
      overflow: hidden;
    }
    .progress-fill {
      height: 100%;
      background: linear-gradient(90deg, #4a9eff, #7c3aed);
      width: 0%;
      transition: width 0.3s ease;
    }
    .status {
      color: #888;
      font-size: 12px;
      margin-top: 4px;
      min-height: 16px;
    }
    .error-msg {
      color: #f44336;
      margin-top: 20px;
      text-align: center;
    }
    .button-row {
      margin-top: 20px;
      display: none;
      gap: 12px;
    }
    .btn {
      padding: 10px 30px;
      color: white;
      border: none;
      border-radius: 6px;
      cursor: pointer;
    }
    .btn-primary { background: #4a9eff; }
    .btn-primary:hover { background: #3a8eef; }
    .btn-danger { background: #666; }
    .btn-danger:hover { background: #f44336; }
  </style>
</head>
<body>
  <h1>First Time Setup</h1>
  <p class="subtitle">This only happens once</p>

  <div id="step-deps" class="step">
    <div class="step-header">
      <div class="step-icon">1</div>
      <span class="step-title">Installing Python dependencies</span>
    </div>
    <div class="progress-bar"><div class="progress-fill" id="progress-deps"></div></div>
    <div class="status" id="status-deps"></div>
  </div>

  <div id="step-model" class="step">
    <div class="step-header">
      <div class="step-icon">2</div>
      <span class="step-title">Downloading Embedding Model</span>
    </div>
    <div class="progress-bar"><div class="progress-fill" id="progress-model"></div></div>
    <div class="status" id="status-model"></div>
  </div>

  <div id="step-verify" class="step">
    <div class="step-header">
      <div class="step-icon">3</div>
      <span class="step-title">Verifying installation</span>
    </div>
    <div class="progress-bar"><div class="progress-fill" id="progress-verify"></div></div>
    <div class="status" id="status-verify"></div>
  </div>

  <div id="error-msg" class="error-msg" style="display:none;"></div>
  <div id="button-row" class="button-row">
    <button class="btn btn-primary" onclick="retrySetup()">Retry Setup</button>
    <button class="btn btn-danger" onclick="exitApp()">Exit</button>
  </div>

  <script>
    // Listen for progress updates from main process
    if (window.electronAPI) {
      window.electronAPI.onSetupProgress((data) => {
        updateStep(data.step, data.status, data.progress, data.message);
      });
    }

    function updateStep(step, status, progress, message) {
      const stepEl = document.getElementById('step-' + step);
      const progressEl = document.getElementById('progress-' + step);
      const statusEl = document.getElementById('status-' + step);

      if (!stepEl) return;

      // Update classes
      stepEl.className = 'step ' + status;

      // Update progress bar
      if (progressEl) {
        progressEl.style.width = progress + '%';
      }

      // Update status text
      if (statusEl && message) {
        statusEl.textContent = message;
      }

      // Update icon
      const icon = stepEl.querySelector('.step-icon');
      if (icon) {
        if (status === 'done') icon.textContent = '✓';
        else if (status === 'error') icon.textContent = '✗';
      }

      // Show error UI if needed
      if (status === 'error') {
        document.getElementById('error-msg').style.display = 'block';
        document.getElementById('error-msg').textContent = message || 'Setup failed';
        document.getElementById('button-row').style.display = 'flex';
      }
    }

    function retrySetup() {
      // Reset UI
      document.getElementById('error-msg').style.display = 'none';
      document.getElementById('button-row').style.display = 'none';
      document.querySelectorAll('.step').forEach(s => s.className = 'step');
      document.querySelectorAll('.progress-fill').forEach(p => p.style.width = '0%');
      document.querySelectorAll('.status').forEach(s => s.textContent = '');
      document.querySelectorAll('.step-icon').forEach((icon, i) => icon.textContent = (i + 1).toString());
      // Signal main process to retry
      if (window.electronAPI && window.electronAPI.retrySetup) {
        window.electronAPI.retrySetup();
      } else {
        location.reload();
      }
    }

    function exitApp() {
      if (window.electronAPI && window.electronAPI.exitApp) {
        window.electronAPI.exitApp();
      } else {
        window.close();
      }
    }
  </script>
</body>
</html>`;
}

/**
 * Send progress update to setup window
 * Uses executeJavaScript since inline HTML doesn't have preload/electronAPI
 */
function sendProgress(step, status, progress, message) {
  if (setupWindow && !setupWindow.isDestroyed()) {
    // On error, make window closable so user can exit
    if (status === 'error') {
      setupWindow.setClosable(true);
    }
    // Escape message for JavaScript string
    const safeMessage = (message || '').replace(/'/g, "\\'").replace(/\n/g, '\\n').replace(/\r/g, '');
    const js = `if(typeof updateStep === 'function') updateStep('${step}', '${status}', ${progress}, '${safeMessage}')`;
    setupWindow.webContents.executeJavaScript(js).catch(() => {});
  }
  logger.info('Setup progress', { step, status, progress, message });
}

/**
 * Run a Python script and capture progress
 */
function runPythonScript(pythonExe, scriptPath, step) {
  return new Promise((resolve, reject) => {
    logger.info(`Running Python script: ${scriptPath}`);
    sendProgress(step, 'active', 0, 'Starting...');

    const proc = spawn(pythonExe, [scriptPath], {
      cwd: path.dirname(scriptPath),
      env: {
        ...process.env,
        PYTHONUNBUFFERED: '1',
        // Suppress all Python warnings - user sees progress UI only
        PYTHONWARNINGS: 'ignore',
        TF_CPP_MIN_LOG_LEVEL: '3',
        TRANSFORMERS_VERBOSITY: 'error',
        TOKENIZERS_PARALLELISM: 'false'
      },
      stdio: ['ignore', 'pipe', 'pipe'],
      windowsHide: true
    });

    let lastProgress = 0;

    proc.stdout.on('data', (data) => {
      const output = data.toString();
      logger.info(`[${step}] stdout:`, output.trim());

      // Parse progress from output (look for percentage or status messages)
      const progressMatch = output.match(/(\d+)%/);
      if (progressMatch) {
        lastProgress = parseInt(progressMatch[1]);
        sendProgress(step, 'active', lastProgress, output.trim());
      } else if (output.includes('[OK]')) {
        lastProgress = Math.min(lastProgress + 10, 95);
        sendProgress(step, 'active', lastProgress, output.trim());
      } else if (output.includes('[...]')) {
        sendProgress(step, 'active', lastProgress, output.trim());
      }
    });

    proc.stderr.on('data', (data) => {
      const output = data.toString();
      logger.warning(`[${step}] stderr:`, output.trim());
      // Don't treat all stderr as error - Python often writes info to stderr
    });

    proc.on('close', (code) => {
      if (code === 0) {
        sendProgress(step, 'done', 100, 'Complete!');
        resolve(true);
      } else {
        sendProgress(step, 'error', lastProgress, `Failed with exit code ${code}`);
        reject(new Error(`Script exited with code ${code}`));
      }
    });

    proc.on('error', (err) => {
      sendProgress(step, 'error', 0, err.message);
      reject(err);
    });
  });
}

/**
 * Verify installation
 */
async function verifyInstallation(paths) {
  sendProgress('verify', 'active', 0, 'Checking installation...');

  // Check 1: Python can import core deps
  sendProgress('verify', 'active', 25, 'Checking Python imports...');
  try {
    const result = await new Promise((resolve, reject) => {
      const proc = spawn(paths.pythonExe, ['-c', 'import fastapi; import torch; import transformers; print("OK")'], {
        timeout: 30000,
        windowsHide: true,
        env: {
          ...process.env,
          PYTHONWARNINGS: 'ignore',
          TF_CPP_MIN_LOG_LEVEL: '3',
          TRANSFORMERS_VERBOSITY: 'error'
        }
      });
      let output = '';
      proc.stdout.on('data', (d) => output += d.toString());
      proc.on('close', (code) => code === 0 && output.includes('OK') ? resolve(true) : reject(new Error('Import failed')));
      proc.on('error', reject);
    });
  } catch (e) {
    sendProgress('verify', 'error', 25, 'Python dependencies not working');
    throw new Error('Python imports failed: ' + e.message);
  }

  // Check 2: Model exists (models are at projectRoot, not in resources)
  sendProgress('verify', 'active', 50, 'Checking Embedding Model...');
  const modelPath = path.join(paths.modelsPath, 'qwen-embedding', 'config.json');
  if (!fs.existsSync(modelPath)) {
    sendProgress('verify', 'error', 50, 'Embedding Model not found');
    throw new Error('Embedding Model not found at: ' + modelPath);
  }

  // Check 3: Server directory exists (server is in resources/)
  sendProgress('verify', 'active', 75, 'Checking server files...');
  const serverMain = path.join(paths.serverPath, 'main.py');
  if (!fs.existsSync(serverMain)) {
    sendProgress('verify', 'error', 75, 'Server files not found');
    throw new Error('Server not found at: ' + serverMain);
  }

  sendProgress('verify', 'done', 100, 'All checks passed!');
  return true;
}

/**
 * Run the complete first-run setup
 */
export async function runFirstRunSetup(paths) {
  if (isSetupRunning) {
    logger.warning('Setup already running');
    return false;
  }

  isSetupRunning = true;
  logger.info('Starting first-run setup', { paths });

  try {
    // Create setup window
    createSetupWindow();

    // Give window time to load
    await new Promise(r => setTimeout(r, 500));

    const pythonExe = paths.pythonExe;
    const appRoot = paths.projectRoot;
    const toolsDir = paths.pythonToolsPath;  // tools are in resources/tools

    // Step 1: Install Python dependencies
    const installDepsScript = path.join(toolsDir, 'install_deps.py');
    if (fs.existsSync(installDepsScript)) {
      await runPythonScript(pythonExe, installDepsScript, 'deps');
    } else {
      logger.warning('install_deps.py not found, skipping');
      sendProgress('deps', 'done', 100, 'Skipped (not found)');
    }

    // Step 2: Download AI model (skip if bundled in QA FULL build)
    const modelConfig = path.join(paths.modelsPath, 'qwen-embedding', 'config.json');
    if (fs.existsSync(modelConfig)) {
      // QA FULL build: model already bundled, skip download
      logger.info('Model already bundled (QA FULL build), skipping download');
      sendProgress('model', 'done', 100, 'Model bundled (offline installer)');
    } else {
      // LIGHT build: need to download model
      const downloadModelScript = path.join(toolsDir, 'download_model.py');
      if (fs.existsSync(downloadModelScript)) {
        await runPythonScript(pythonExe, downloadModelScript, 'model');
      } else {
        logger.warning('download_model.py not found, skipping');
        sendProgress('model', 'done', 100, 'Skipped (not found)');
      }
    }

    // Step 3: Verify installation
    await verifyInstallation(paths);

    // Success! Create flag file
    createFlagFile(appRoot);

    // Show success message briefly
    await new Promise(r => setTimeout(r, 1500));

    // Close setup window
    if (setupWindow && !setupWindow.isDestroyed()) {
      setupWindow.setClosable(true);  // Must enable closing first (window created with closable: false)
      setupWindow.close();
      setupWindow = null;
    }

    logger.success('First-run setup completed successfully');
    isSetupRunning = false;
    return true;

  } catch (error) {
    logger.error('First-run setup failed', { error: error.message });
    isSetupRunning = false;

    // Keep window open to show error
    // User will need to close app and retry
    return false;
  }
}

/**
 * Setup IPC handlers for setup window
 */
export function setupFirstRunIPC() {
  ipcMain.handle('retry-setup', async (event, paths) => {
    if (setupWindow && !setupWindow.isDestroyed()) {
      setupWindow.close();
      setupWindow = null;
    }
    return runFirstRunSetup(paths);
  });
}
