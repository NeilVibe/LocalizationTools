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

export default {
  showSplash,
  updateSplash,
  closeSplash,
  getSplashWindow
};
