/**
 * Auto-Update Full Debug Test
 *
 * This script:
 * 1. Launches LocaNext with CDP debugging
 * 2. Captures all console output
 * 3. Monitors for auto-updater events
 * 4. Logs everything to a file
 *
 * Run from Windows PowerShell:
 *   cd \\wsl.localhost\Ubuntu2\home\neil1988\LocalizationTools\testing_toolkit\cdp
 *   node auto_update_test.js
 */

const http = require('http');
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');
const WebSocket = require('ws');

const APP_PATH = 'C:\\NEIL_PROJECTS_WINDOWSBUILD\\LocaNextProject\\Playground\\LocaNext\\LocaNext.exe';
const CDP_PORT = 9222;
const LOG_FILE = 'auto_update_debug.log';

let logStream;

function log(msg) {
  const timestamp = new Date().toISOString();
  const line = `[${timestamp}] ${msg}`;
  console.log(line);
  if (logStream) logStream.write(line + '\n');
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function getCDPTargets() {
  return new Promise((resolve, reject) => {
    http.get(`http://127.0.0.1:${CDP_PORT}/json`, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          resolve(JSON.parse(data));
        } catch (e) {
          reject(e);
        }
      });
    }).on('error', reject);
  });
}

async function connectToTarget(wsUrl) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(wsUrl);
    ws.on('open', () => resolve(ws));
    ws.on('error', reject);
  });
}

async function sendCommand(ws, method, params = {}) {
  return new Promise((resolve) => {
    const id = Date.now();
    const handler = (data) => {
      const msg = JSON.parse(data);
      if (msg.id === id) {
        ws.removeListener('message', handler);
        resolve(msg);
      }
    };
    ws.on('message', handler);
    ws.send(JSON.stringify({ id, method, params }));
  });
}

async function main() {
  logStream = fs.createWriteStream(LOG_FILE, { flags: 'a' });

  log('========================================');
  log('AUTO-UPDATE DEBUG TEST');
  log('========================================');

  // Check current latest.yml
  log('');
  log('=== Step 1: Check Gitea latest.yml ===');

  await new Promise((resolve) => {
    http.get('http://172.28.150.120:3000/neilvibe/LocaNext/releases/download/latest/latest.yml', (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        log(`Gitea Status: ${res.statusCode}`);
        const versionMatch = data.match(/version:\s*(.+)/);
        if (versionMatch) {
          log(`Server Version: ${versionMatch[1].trim()}`);
        }
        log(`Full content:\n${data}`);
        resolve();
      });
    }).on('error', (err) => {
      log(`ERROR: Cannot reach Gitea: ${err.message}`);
      resolve();
    });
  });

  // Launch app
  log('');
  log('=== Step 2: Launch LocaNext ===');
  log(`App: ${APP_PATH}`);

  const app = spawn(APP_PATH, ['--remote-debugging-port=' + CDP_PORT], {
    detached: true,
    stdio: 'ignore'
  });
  app.unref();

  log(`Launched with PID: ${app.pid}`);
  log('Waiting for CDP...');

  // Wait for CDP
  let targets = null;
  for (let i = 0; i < 30; i++) {
    await sleep(1000);
    try {
      targets = await getCDPTargets();
      if (targets && targets.length > 0) {
        log(`CDP ready! Found ${targets.length} target(s)`);
        break;
      }
    } catch (e) {
      // Still waiting
    }
  }

  if (!targets) {
    log('ERROR: CDP not available after 30 seconds');
    process.exit(1);
  }

  // Connect to main page
  const mainTarget = targets.find(t => t.type === 'page');
  if (!mainTarget) {
    log('ERROR: No page target found');
    process.exit(1);
  }

  log(`Connecting to: ${mainTarget.title}`);
  log(`URL: ${mainTarget.url}`);

  const ws = await connectToTarget(mainTarget.webSocketDebuggerUrl);

  // Enable Console
  await sendCommand(ws, 'Console.enable');
  await sendCommand(ws, 'Runtime.enable');
  await sendCommand(ws, 'Log.enable');

  log('');
  log('=== Step 3: Monitoring Console Output ===');
  log('(Waiting 60 seconds for auto-updater activity...)');
  log('');

  // Listen for console messages
  ws.on('message', (data) => {
    const msg = JSON.parse(data);

    if (msg.method === 'Console.messageAdded') {
      const text = msg.params?.message?.text || '';
      if (text.toLowerCase().includes('update') ||
          text.toLowerCase().includes('version') ||
          text.toLowerCase().includes('download')) {
        log(`[CONSOLE] ${text}`);
      }
    }

    if (msg.method === 'Runtime.consoleAPICalled') {
      const args = msg.params?.args || [];
      const text = args.map(a => a.value || a.description || '').join(' ');
      if (text.toLowerCase().includes('update') ||
          text.toLowerCase().includes('version') ||
          text.toLowerCase().includes('download') ||
          text.toLowerCase().includes('auto')) {
        log(`[RUNTIME] ${text}`);
      }
    }

    if (msg.method === 'Log.entryAdded') {
      const text = msg.params?.entry?.text || '';
      if (text.toLowerCase().includes('update') ||
          text.toLowerCase().includes('version')) {
        log(`[LOG] ${text}`);
      }
    }
  });

  // Also inject a listener for IPC events
  await sendCommand(ws, 'Runtime.evaluate', {
    expression: `
      if (window.electronAPI) {
        console.log('[AUTO-UPDATE-TEST] electronAPI available');

        // Listen for update events
        const events = ['update-available', 'update-not-available', 'update-downloaded', 'update-error', 'update-progress'];
        events.forEach(event => {
          if (window.electronAPI['on' + event.replace(/-/g, '')]) {
            console.log('[AUTO-UPDATE-TEST] Listening for: ' + event);
          }
        });
      } else {
        console.log('[AUTO-UPDATE-TEST] electronAPI not available yet');
      }
    `
  });

  // Wait and collect logs
  await sleep(60000);

  log('');
  log('=== Test Complete ===');
  log(`Log saved to: ${LOG_FILE}`);

  ws.close();
  logStream.end();
  process.exit(0);
}

main().catch(err => {
  console.error('Error:', err);
  process.exit(1);
});
