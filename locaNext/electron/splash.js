/**
 * Splash Screen for LocaNext
 *
 * Shows a loading screen immediately on startup while:
 * - Health check runs
 * - First-run setup runs (if needed)
 * - Backend server starts
 *
 * Provides visual feedback during long operations.
 */

import { BrowserWindow } from 'electron';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

let splashWindow = null;
let setupMode = false;

const SETUP_STEP_LABELS = [
  'Checking system requirements',
  'Initializing database',
  'Configuring network access',
  'Generating certificates',
  'Starting PostgreSQL',
  'Tuning performance',
  'Creating service account',
  'Creating database',
];

/**
 * Create and show splash screen
 * @returns {BrowserWindow} The splash window
 */
export function showSplash() {
  splashWindow = new BrowserWindow({
    width: 420,
    height: 320,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    skipTaskbar: true,
    resizable: false,
    hasShadow: false,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true
    }
  });

  // Load splash HTML
  splashWindow.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(getSplashHTML())}`);
  splashWindow.center();

  return splashWindow;
}

/**
 * Update splash screen status
 * @param {string} status - Status message to display
 * @param {number} progress - Progress percentage (0-100)
 */
export function updateSplash(status, progress = -1) {
  if (splashWindow && !splashWindow.isDestroyed()) {
    splashWindow.webContents.executeJavaScript(`
      document.getElementById('status').innerText = ${JSON.stringify(status)};
      ${progress >= 0 ? `
        document.getElementById('progress').style.width = '${progress}%';
        document.getElementById('progress-text').innerText = '${progress}%';
      ` : ''}
    `).catch(() => {});
  }
}

/**
 * Close splash screen
 */
export function closeSplash() {
  if (splashWindow && !splashWindow.isDestroyed()) {
    splashWindow.close();
  }
  splashWindow = null;
}

/**
 * Get splash window reference
 */
export function getSplashWindow() {
  return splashWindow;
}

/**
 * Generate splash HTML
 */
function getSplashHTML() {
  return `
<!DOCTYPE html>
<html>
<head>
  <style>
    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }
    html, body {
      overflow: hidden;
      width: 100%;
      height: 100%;
    }
    body {
      font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
      display: flex;
      justify-content: center;
      align-items: center;
      height: 100vh;
      background: transparent;
      -webkit-app-region: drag;
    }
    .splash-container {
      background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
      border-radius: 16px;
      padding: 40px;
      text-align: center;
      box-shadow: 0 20px 60px rgba(0,0,0,0.5);
      border: 1px solid rgba(255,255,255,0.1);
      width: 360px;
    }
    .logo {
      font-size: 48px;
      margin-bottom: 10px;
    }
    .title {
      font-size: 28px;
      font-weight: 600;
      color: #fff;
      margin-bottom: 8px;
    }
    .version {
      font-size: 12px;
      color: rgba(255,255,255,0.5);
      margin-bottom: 30px;
    }
    .progress-container {
      background: rgba(255,255,255,0.1);
      border-radius: 10px;
      height: 8px;
      overflow: hidden;
      margin-bottom: 15px;
    }
    .progress-bar {
      height: 100%;
      background: linear-gradient(90deg, #4facfe 0%, #00f2fe 100%);
      border-radius: 10px;
      width: 0%;
      transition: width 0.3s ease;
    }
    .status {
      font-size: 14px;
      color: rgba(255,255,255,0.7);
      min-height: 20px;
    }
    .progress-text {
      font-size: 12px;
      color: rgba(255,255,255,0.5);
      margin-top: 8px;
    }
    .dots {
      display: inline-block;
      animation: dots 1.5s infinite;
    }
    @keyframes dots {
      0%, 20% { content: '.'; }
      40% { content: '..'; }
      60%, 100% { content: '...'; }
    }
    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.5; }
    }
    .loading-indicator {
      display: inline-block;
      width: 6px;
      height: 6px;
      background: #4facfe;
      border-radius: 50%;
      margin-left: 8px;
      animation: pulse 1s infinite;
    }
  </style>
</head>
<body>
  <div class="splash-container">
    <div class="logo">🌐</div>
    <div class="title">LocaNext</div>
    <div class="version">Professional Localization Platform</div>
    <div class="progress-container">
      <div class="progress-bar" id="progress"></div>
    </div>
    <div class="status" id="status">Starting up<span class="loading-indicator"></span></div>
    <div class="progress-text" id="progress-text"></div>
  </div>
</body>
</html>
`;
}

/**
 * Switch splash window to setup mode with step-by-step progress.
 * Resizes the window and replaces content with setup UI.
 * @param {number} totalSteps - Number of setup steps (default: 7)
 */
export function showSetupMode(totalSteps = 7) {
  if (!splashWindow || splashWindow.isDestroyed()) return;
  setupMode = true;

  // Resize for setup content
  splashWindow.setSize(480, 440);
  splashWindow.center();

  const html = getSetupHTML(totalSteps);
  splashWindow.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(html)}`);

  // Listen for postMessage from the renderer (IPC via data URL workaround)
  splashWindow.webContents.on('console-message', (_event, _level, message) => {
    try {
      const parsed = JSON.parse(message);
      if (parsed.type === 'setup-ipc') {
        splashWindow.webContents.emit('setup-ipc', parsed.action);
      }
    } catch { /* not our message */ }
  });
}

/**
 * Update a specific setup step's status.
 * @param {number} index - Step index (0-based)
 * @param {object} step - Step info (used for label fallback)
 * @param {string} status - 'running' | 'done' | 'skipped' | 'failed'
 * @param {number} [durationMs] - Duration in milliseconds (for 'done' status)
 * @param {string} [error] - Error message (for 'failed' status)
 */
export function updateSetupStep(index, step, status, durationMs, error) {
  if (!splashWindow || splashWindow.isDestroyed()) return;

  // When starting the database step, allow firewall popup on top
  // Uses step name (not index) so reordering steps won't break this
  const isDbStep = step === 'start_database';
  if (isDbStep && status === 'running') {
    splashWindow.setAlwaysOnTop(false);
  }
  if (isDbStep && (status === 'done' || status === 'failed' || status === 'skipped')) {
    splashWindow.setAlwaysOnTop(true);
  }

  const totalSteps = SETUP_STEP_LABELS.length;
  const progressPct = Math.round(((index + (status === 'done' || status === 'skipped' ? 1 : 0.5)) / totalSteps) * 100);

  let iconHtml, detailHtml;
  switch (status) {
    case 'running':
      iconHtml = '<span class="step-icon spinner"></span>';
      detailHtml = '';
      break;
    case 'done':
      iconHtml = '<span class="step-icon done">&#10003;</span>';
      detailHtml = durationMs != null ? `<span class="step-detail">${formatDuration(durationMs)}</span>` : '';
      break;
    case 'skipped':
      iconHtml = '<span class="step-icon done">&#10003;</span>';
      detailHtml = '<span class="step-detail">(skipped)</span>';
      break;
    case 'failed':
      iconHtml = '<span class="step-icon failed">&#10007;</span>';
      detailHtml = error ? `<span class="step-detail failed-text">${escapeHtml(error)}</span>` : '';
      break;
    default:
      iconHtml = '<span class="step-icon pending">&#8226;</span>';
      detailHtml = '';
  }

  const safeIconHtml = JSON.stringify(iconHtml);
  const safeDetailHtml = JSON.stringify(detailHtml);
  const safeStatus = JSON.stringify(status);

  splashWindow.webContents.executeJavaScript(`
    (function() {
      var row = document.getElementById('step-${index}');
      if (!row) return;
      row.className = 'step-row ' + ${safeStatus};
      row.querySelector('.step-icon-cell').innerHTML = ${safeIconHtml};
      var detailEl = row.querySelector('.step-detail-cell');
      if (detailEl) detailEl.innerHTML = ${safeDetailHtml};

      var pbar = document.getElementById('setup-progress');
      if (pbar) pbar.style.width = '${progressPct}%';
      var ptext = document.getElementById('setup-progress-text');
      if (ptext) ptext.innerText = 'Step ${index + 1} of ${totalSteps}';
    })();
  `).catch(() => {});
}

/**
 * Show error panel with retry/offline/log buttons.
 * Buttons communicate back via console.log JSON (captured in main process).
 * @param {object} step - The step that failed
 * @param {string} errorCode - Error code identifier
 * @param {string} errorDetail - Detailed error description
 */
export function showSetupError(step, errorCode, errorDetail) {
  if (!splashWindow || splashWindow.isDestroyed()) return;

  const safeCode = JSON.stringify(escapeHtml(errorCode));
  const safeDetail = JSON.stringify(escapeHtml(errorDetail));

  splashWindow.webContents.executeJavaScript(`
    (function() {
      var existing = document.getElementById('error-panel');
      if (existing) existing.remove();

      var panel = document.createElement('div');
      panel.id = 'error-panel';

      var title = document.createElement('div');
      title.className = 'error-title';
      title.textContent = 'Setup Failed';
      panel.appendChild(title);

      var code = document.createElement('div');
      code.className = 'error-code';
      code.textContent = ${safeCode};
      panel.appendChild(code);

      var detail = document.createElement('div');
      detail.className = 'error-detail';
      detail.textContent = ${safeDetail};
      panel.appendChild(detail);

      var btnRow = document.createElement('div');
      btnRow.className = 'error-buttons';

      var btnLog = document.createElement('button');
      btnLog.className = 'btn btn-secondary';
      btnLog.textContent = 'Show Full Log';
      btnLog.addEventListener('click', function() {
        console.log(JSON.stringify({type:'setup-ipc',action:'setup-show-log'}));
      });
      btnRow.appendChild(btnLog);

      var btnRetry = document.createElement('button');
      btnRetry.className = 'btn btn-primary';
      btnRetry.textContent = 'Retry';
      btnRetry.addEventListener('click', function() {
        console.log(JSON.stringify({type:'setup-ipc',action:'setup-retry'}));
      });
      btnRow.appendChild(btnRetry);

      var btnOffline = document.createElement('button');
      btnOffline.className = 'btn btn-secondary';
      btnOffline.textContent = 'Start Offline';
      btnOffline.addEventListener('click', function() {
        console.log(JSON.stringify({type:'setup-ipc',action:'setup-offline'}));
      });
      btnRow.appendChild(btnOffline);

      panel.appendChild(btnRow);
      document.querySelector('.setup-container').appendChild(panel);
    })();
  `).catch(() => {});
}

/**
 * Show setup complete message with LAN IP, then auto-close after 2 seconds.
 * @param {string} lanIp - The LAN IP address of the server
 */
export function showSetupComplete(lanIp) {
  if (!splashWindow || splashWindow.isDestroyed()) return;

  const safeIp = JSON.stringify(escapeHtml(lanIp));

  splashWindow.webContents.executeJavaScript(`
    (function() {
      var container = document.querySelector('.setup-container');
      if (!container) return;

      // Clear existing content
      while (container.firstChild) container.removeChild(container.firstChild);

      var panel = document.createElement('div');
      panel.className = 'complete-panel';

      var icon = document.createElement('div');
      icon.className = 'complete-icon';
      icon.textContent = '\\u2713';
      panel.appendChild(icon);

      var title = document.createElement('div');
      title.className = 'complete-title';
      title.textContent = 'Server Ready!';
      panel.appendChild(title);

      var ip = document.createElement('div');
      ip.className = 'complete-ip';
      ip.textContent = 'LAN IP: ' + ${safeIp};
      panel.appendChild(ip);

      container.appendChild(panel);
    })();
  `).catch(() => {});

  setTimeout(() => {
    closeSplash();
  }, 2000);
}

/**
 * Listen for IPC actions from setup error buttons.
 * @param {string} action - The action to listen for ('setup-retry', 'setup-offline', 'setup-show-log')
 * @param {Function} callback - Callback when action is triggered
 */
export function onSetupAction(action, callback) {
  if (!splashWindow || splashWindow.isDestroyed()) return;
  splashWindow.webContents.on('setup-ipc', (receivedAction) => {
    if (receivedAction === action) callback();
  });
}

/**
 * Format milliseconds to human-readable duration.
 */
function formatDuration(ms) {
  if (ms < 1000) return `${ms}ms`;
  const seconds = (ms / 1000).toFixed(1);
  return `${seconds}s`;
}

/**
 * Escape HTML entities for safe insertion.
 */
function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/**
 * Generate setup mode HTML.
 */
function getSetupHTML(totalSteps) {
  const stepRows = SETUP_STEP_LABELS.slice(0, totalSteps).map((label, i) => `
    <div class="step-row pending" id="step-${i}">
      <span class="step-icon-cell"><span class="step-icon pending">&#8226;</span></span>
      <span class="step-label">${escapeHtml(label)}</span>
      <span class="step-detail-cell"></span>
    </div>
  `).join('');

  return `
<!DOCTYPE html>
<html>
<head>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    html, body { overflow: hidden; width: 100%; height: 100%; }
    body {
      font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
      display: flex; justify-content: center; align-items: center;
      height: 100vh; background: transparent;
      -webkit-app-region: drag;
    }
    .setup-container {
      background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
      border-radius: 16px; padding: 32px;
      box-shadow: 0 20px 60px rgba(0,0,0,0.5);
      border: 1px solid rgba(255,255,255,0.1);
      width: 420px; color: #fff;
      -webkit-app-region: no-drag;
    }
    .setup-title {
      font-size: 22px; font-weight: 600; text-align: center;
      margin-bottom: 24px; color: #fff;
    }
    .step-row {
      display: flex; align-items: center; gap: 10px;
      padding: 7px 8px; border-radius: 6px;
      font-size: 14px; color: rgba(255,255,255,0.45);
      transition: background 0.2s, color 0.2s;
    }
    .step-row.running {
      background: rgba(79,172,254,0.1);
      color: #fff;
    }
    .step-row.done { color: rgba(255,255,255,0.65); }
    .step-row.skipped { color: rgba(255,255,255,0.5); }
    .step-row.failed { color: #ff6b6b; }
    .step-icon-cell { width: 22px; text-align: center; flex-shrink: 0; }
    .step-icon { font-size: 14px; }
    .step-icon.done { color: #51cf66; }
    .step-icon.failed { color: #ff6b6b; font-weight: bold; }
    .step-icon.pending { color: rgba(255,255,255,0.25); }
    .step-label { flex: 1; }
    .step-detail-cell { font-size: 12px; color: rgba(255,255,255,0.4); flex-shrink: 0; }
    .failed-text { color: #ff6b6b; }

    /* CSS-only spinner */
    .spinner {
      display: inline-block; width: 14px; height: 14px;
      border: 2px solid rgba(79,172,254,0.3);
      border-top-color: #4facfe;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }
    @keyframes spin {
      to { transform: rotate(360deg); }
    }

    .progress-section {
      margin-top: 20px;
    }
    .progress-container {
      background: rgba(255,255,255,0.1);
      border-radius: 10px; height: 6px; overflow: hidden;
    }
    .progress-bar {
      height: 100%;
      background: linear-gradient(90deg, #4facfe 0%, #00f2fe 100%);
      border-radius: 10px; width: 0%;
      transition: width 0.4s ease;
    }
    .progress-text {
      font-size: 12px; color: rgba(255,255,255,0.45);
      text-align: center; margin-top: 8px;
    }

    /* Error panel */
    #error-panel {
      margin-top: 20px; padding: 16px;
      background: rgba(255,107,107,0.1);
      border: 1px solid rgba(255,107,107,0.3);
      border-radius: 10px;
    }
    .error-title { font-size: 16px; font-weight: 600; color: #ff6b6b; margin-bottom: 6px; }
    .error-code { font-size: 12px; color: rgba(255,255,255,0.5); font-family: monospace; margin-bottom: 8px; }
    .error-detail { font-size: 13px; color: rgba(255,255,255,0.7); margin-bottom: 16px; line-height: 1.4; }
    .error-buttons { display: flex; gap: 8px; }
    .btn {
      flex: 1; padding: 8px 12px; border: none; border-radius: 6px;
      font-size: 13px; font-weight: 500; cursor: pointer;
      transition: background 0.2s;
    }
    .btn-primary { background: #4facfe; color: #fff; }
    .btn-primary:hover { background: #3d9be8; }
    .btn-secondary { background: rgba(255,255,255,0.1); color: rgba(255,255,255,0.8); }
    .btn-secondary:hover { background: rgba(255,255,255,0.15); }

    /* Complete panel */
    .complete-panel { text-align: center; padding: 40px 0; }
    .complete-icon {
      font-size: 48px; color: #51cf66;
      width: 72px; height: 72px; line-height: 72px;
      border-radius: 50%; background: rgba(81,207,102,0.1);
      margin: 0 auto 16px;
    }
    .complete-title { font-size: 24px; font-weight: 600; margin-bottom: 8px; }
    .complete-ip { font-size: 14px; color: rgba(255,255,255,0.6); font-family: monospace; }
  </style>
</head>
<body>
  <div class="setup-container">
    <div class="setup-title">LocaNext &mdash; Server Setup</div>
    <div class="step-list">
      ${stepRows}
    </div>
    <div class="progress-section">
      <div class="progress-container">
        <div class="progress-bar" id="setup-progress"></div>
      </div>
      <div class="progress-text" id="setup-progress-text">Step 0 of ${totalSteps}</div>
    </div>
  </div>
</body>
</html>
`;
}

export default {
  showSplash,
  updateSplash,
  closeSplash,
  getSplashWindow,
  showSetupMode,
  updateSetupStep,
  showSetupError,
  showSetupComplete,
  onSetupAction,
  SETUP_STEP_LABELS,
};
