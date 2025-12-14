/**
 * Repair Module for LocaNext
 *
 * Automatically repairs broken components detected by health check.
 * Reuses first-run setup UI and scripts.
 *
 * Repair actions:
 * - deps: Re-run install_deps.py to install missing Python packages
 * - model: Re-run download_model.py to download Embedding Model (Qwen)
 * - full: Run both deps and model installation
 */

import { spawn } from 'child_process';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { BrowserWindow, Menu } from 'electron';
import { logger } from './logger.js';
import { recordRepairAttempt } from './health-check.js';

// ESM dirname equivalent (import.meta.dirname is undefined in Node 18)
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

let repairWindow = null;
let isRepairRunning = false;

/**
 * Create the repair window (similar to first-run setup)
 */
function createRepairWindow() {
  repairWindow = new BrowserWindow({
    width: 550,
    height: 520,
    resizable: false,
    minimizable: false,
    maximizable: false,
    closable: false,
    frame: true,
    autoHideMenuBar: true,
    title: 'LocaNext - Repairing Installation',
    backgroundColor: '#1a1a2e',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    }
  });

  // Remove menu bar completely for cleaner look
  repairWindow.setMenu(null);

  // Load repair HTML
  repairWindow.loadURL(`data:text/html,${encodeURIComponent(getRepairHtml())}`);
  return repairWindow;
}

/**
 * Inline HTML for repair window
 */
function getRepairHtml() {
  return `
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>LocaNext - Repairing</title>
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
    h1 { font-size: 24px; margin-bottom: 10px; color: #ffc107; }
    .subtitle { color: #888; margin-bottom: 30px; }
    .repair-icon { font-size: 48px; margin-bottom: 20px; }
    .step {
      width: 100%;
      margin-bottom: 16px;
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
    .step.active .step-icon { background: #ffc107; color: #000; }
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
      background: linear-gradient(90deg, #ffc107, #ff9800);
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
    .info-box {
      background: rgba(255, 193, 7, 0.1);
      border: 1px solid #ffc107;
      border-radius: 8px;
      padding: 12px;
      margin-bottom: 20px;
      font-size: 13px;
    }
  </style>
</head>
<body>
  <div class="repair-icon">🔧</div>
  <h1>Repairing LocaNext</h1>
  <p class="subtitle">Some components need to be reinstalled</p>

  <div class="info-box">
    This may take a few minutes. Please don't close this window.
  </div>

  <div id="step-deps" class="step">
    <div class="step-header">
      <div class="step-icon">1</div>
      <span class="step-title">Reinstalling Python packages</span>
    </div>
    <div class="progress-bar"><div class="progress-fill" id="progress-deps"></div></div>
    <div class="status" id="status-deps"></div>
  </div>

  <div id="step-model" class="step">
    <div class="step-header">
      <div class="step-icon">2</div>
      <span class="step-title">Redownloading Embedding Model</span>
    </div>
    <div class="progress-bar"><div class="progress-fill" id="progress-model"></div></div>
    <div class="status" id="status-model"></div>
  </div>

  <div id="step-verify" class="step">
    <div class="step-header">
      <div class="step-icon">3</div>
      <span class="step-title">Verifying repair</span>
    </div>
    <div class="progress-bar"><div class="progress-fill" id="progress-verify"></div></div>
    <div class="status" id="status-verify"></div>
  </div>

  <div id="error-msg" class="error-msg" style="display:none;"></div>

  <script>
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

      stepEl.className = 'step ' + status;

      if (progressEl) {
        progressEl.style.width = progress + '%';
      }

      if (statusEl && message) {
        statusEl.textContent = message;
      }

      const icon = stepEl.querySelector('.step-icon');
      if (icon) {
        if (status === 'done') icon.textContent = '✓';
        else if (status === 'error') icon.textContent = '✗';
      }

      if (status === 'error') {
        document.getElementById('error-msg').style.display = 'block';
        document.getElementById('error-msg').textContent = message || 'Repair failed';
      }
    }
  </script>
</body>
</html>`;
}

/**
 * Send progress update to repair window
 * Uses executeJavaScript since inline HTML doesn't have preload/electronAPI
 */
function sendProgress(step, status, progress, message) {
  if (repairWindow && !repairWindow.isDestroyed()) {
    // On error, make window closable so user can exit
    if (status === 'error') {
      repairWindow.setClosable(true);
    }
    // Escape message for JavaScript string
    const safeMessage = (message || '').replace(/'/g, "\\'").replace(/\n/g, '\\n').replace(/\r/g, '');
    const js = `if(typeof updateStep === 'function') updateStep('${step}', '${status}', ${progress}, '${safeMessage}')`;
    repairWindow.webContents.executeJavaScript(js).catch(() => {});
  }
  logger.info('Repair progress', { step, status, progress, message });
}

/**
 * Run a Python script for repair
 */
function runPythonScript(pythonExe, scriptPath, step) {
  return new Promise((resolve, reject) => {
    logger.info(`Repair: Running ${scriptPath}`);
    sendProgress(step, 'active', 0, 'Starting...');

    const proc = spawn(pythonExe, [scriptPath], {
      cwd: path.dirname(scriptPath),
      env: {
        ...process.env,
        PYTHONUNBUFFERED: '1',
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
      logger.info(`[repair-${step}] ${output.trim()}`);

      const progressMatch = output.match(/(\d+)%/);
      if (progressMatch) {
        lastProgress = parseInt(progressMatch[1]);
        sendProgress(step, 'active', lastProgress, output.trim());
      } else if (output.includes('[OK]')) {
        lastProgress = Math.min(lastProgress + 10, 95);
        sendProgress(step, 'active', lastProgress, output.trim());
      }
    });

    proc.stderr.on('data', (data) => {
      logger.warning(`[repair-${step}] stderr: ${data.toString().trim()}`);
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
 * Verify repair was successful
 */
async function verifyRepair(paths) {
  sendProgress('verify', 'active', 0, 'Checking repair...');

  // Check Python imports
  sendProgress('verify', 'active', 33, 'Checking Python packages...');
  try {
    await new Promise((resolve, reject) => {
      const proc = spawn(paths.pythonExe, ['-c', 'import fastapi; import torch; print("OK")'], {
        timeout: 30000,
        windowsHide: true,
        env: { ...process.env, PYTHONWARNINGS: 'ignore' }
      });
      let output = '';
      proc.stdout.on('data', (d) => output += d.toString());
      proc.on('close', (code) => code === 0 && output.includes('OK') ? resolve(true) : reject(new Error('Import check failed')));
      proc.on('error', reject);
    });
  } catch (e) {
    sendProgress('verify', 'error', 33, 'Python packages still missing');
    return false;
  }

  // Check model (models are at projectRoot, not in resources)
  sendProgress('verify', 'active', 66, 'Checking Embedding Model...');
  const modelConfig = path.join(paths.modelsPath, 'qwen-embedding', 'config.json');
  if (!fs.existsSync(modelConfig)) {
    sendProgress('verify', 'error', 66, 'Embedding Model still missing');
    return false;
  }

  sendProgress('verify', 'done', 100, 'Repair successful!');
  return true;
}

/**
 * Run repair for specified components
 * @param {object} paths - App paths
 * @param {string[]} components - Components to repair: 'deps', 'model', or both
 * @returns {Promise<boolean>} - Success status
 */
export async function runRepair(paths, components = ['deps', 'model']) {
  if (isRepairRunning) {
    logger.warning('Repair already running');
    return false;
  }

  isRepairRunning = true;
  logger.info('Starting repair', { components, paths });

  try {
    createRepairWindow();
    await new Promise(r => setTimeout(r, 500));

    const pythonExe = paths.pythonExe;
    const appRoot = paths.projectRoot;
    const toolsDir = paths.pythonToolsPath;  // tools are in resources/tools

    // Repair dependencies if needed
    if (components.includes('deps')) {
      const installDepsScript = path.join(toolsDir, 'install_deps.py');
      if (fs.existsSync(installDepsScript)) {
        try {
          await runPythonScript(pythonExe, installDepsScript, 'deps');
        } catch (err) {
          logger.error('Deps repair failed', { error: err.message });
          // Continue to try model anyway
        }
      } else {
        sendProgress('deps', 'error', 0, 'install_deps.py not found');
      }
    } else {
      sendProgress('deps', 'done', 100, 'Skipped');
    }

    // Repair model if needed
    if (components.includes('model')) {
      const downloadModelScript = path.join(toolsDir, 'download_model.py');
      if (fs.existsSync(downloadModelScript)) {
        try {
          await runPythonScript(pythonExe, downloadModelScript, 'model');
        } catch (err) {
          logger.error('Model repair failed', { error: err.message });
        }
      } else {
        sendProgress('model', 'error', 0, 'download_model.py not found');
      }
    } else {
      sendProgress('model', 'done', 100, 'Skipped');
    }

    // Verify repair
    const success = await verifyRepair(paths);

    // Record repair attempt
    recordRepairAttempt(appRoot, components);

    // Show result briefly
    await new Promise(r => setTimeout(r, success ? 1500 : 3000));

    // Close repair window
    if (repairWindow && !repairWindow.isDestroyed()) {
      repairWindow.close();
      repairWindow = null;
    }

    logger.info('Repair complete', { success });
    isRepairRunning = false;
    return success;

  } catch (error) {
    logger.error('Repair failed', { error: error.message });
    isRepairRunning = false;
    return false;
  }
}

/**
 * Check if repair is currently running
 */
export function isRepairing() {
  return isRepairRunning;
}

export default {
  runRepair,
  isRepairing
};
