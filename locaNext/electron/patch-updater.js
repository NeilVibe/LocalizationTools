/**
 * LAUNCHER-Style Patch Updater
 *
 * Downloads only changed components instead of full installer.
 * Falls back to full installer if patch update fails.
 *
 * Flow:
 * 1. Fetch remote manifest.json
 * 2. Compare with local component-state.json
 * 3. Download only changed components
 * 4. Verify hashes
 * 5. Apply updates (hot-swap)
 * 6. Update local state
 * 7. Restart app
 *
 * Build 471: Test staging + swap script approach
 */

import { app } from 'electron';
import fs from 'fs';
import path from 'path';
import crypto from 'crypto';
import https from 'https';
import http from 'http';

// CRITICAL: Use original-fs to bypass Electron's ASAR interception
// When running inside app.asar, regular fs.readFileSync('app.asar') tries to
// read from INSIDE the archive, which fails. original-fs reads the actual file.
import originalFs from 'original-fs';

// GDP: Debug log file for granular visibility into main process
const DEBUG_LOG_FILE = path.join(app.getPath('userData'), 'patch-updater-debug.log');

function debugLog(message, data = {}) {
  const timestamp = new Date().toISOString();
  const dataStr = Object.keys(data).length > 0 ? ' ' + JSON.stringify(data) : '';
  const logLine = `[${timestamp}] ${message}${dataStr}\n`;
  console.log(logLine.trim());
  try {
    fs.appendFileSync(DEBUG_LOG_FILE, logLine);
  } catch (e) {
    // Ignore write errors
  }
}

// Configuration
const UPDATE_BASE_URL = process.env.GITEA_URL || 'http://172.28.150.120:3000';
const REPO_PATH = 'neilvibe/LocaNext';
const MANIFEST_URL = `${UPDATE_BASE_URL}/${REPO_PATH}/releases/download/latest/manifest.json`;

// Paths
const RESOURCES_PATH = process.resourcesPath || path.join(app.getAppPath(), '..');
// Store state in user's AppData (writable) not resources (might be read-only)
const USER_DATA_PATH = app.getPath('userData');
const STATE_FILE = path.join(USER_DATA_PATH, 'component-state.json');
const TEMP_DIR = path.join(app.getPath('temp'), 'locanext-patch-update');

/**
 * Calculate SHA256 hash of a file
 */
function hashFile(filePath) {
  return new Promise((resolve, reject) => {
    const hash = crypto.createHash('sha256');
    const stream = fs.createReadStream(filePath);
    stream.on('data', data => hash.update(data));
    stream.on('end', () => resolve(hash.digest('hex')));
    stream.on('error', reject);
  });
}

/**
 * Load local component state
 */
function loadLocalState() {
  try {
    if (fs.existsSync(STATE_FILE)) {
      return JSON.parse(fs.readFileSync(STATE_FILE, 'utf8'));
    }
  } catch (err) {
    console.error('[PatchUpdater] Failed to load local state:', err.message);
  }

  // Generate initial state from current files
  return generateInitialState();
}

/**
 * Generate initial state from installed files
 * This is called when component-state.json doesn't exist (first run after install)
 */
function generateInitialState() {
  // GDP Level 1: Entry point
  debugLog('generateInitialState CALLED', {
    RESOURCES_PATH,
    USER_DATA_PATH,
    STATE_FILE,
    processResourcesPath: process.resourcesPath,
    appPath: app.getAppPath()
  });

  const state = {
    version: 'unknown',
    installedAt: new Date().toISOString(),
    components: {}
  };

  // GDP Level 2: Decision point - getting version
  try {
    state.version = app.getVersion();
    debugLog('Got version from app', { version: state.version });
  } catch (err) {
    debugLog('FAILED to get version', { error: err.message, stack: err.stack });
  }

  // GDP Level 3: Variable state - check asar path
  const asarPath = path.join(RESOURCES_PATH, 'app.asar');
  debugLog('Checking app.asar path', {
    asarPath,
    RESOURCES_PATH,
    exists: fs.existsSync(asarPath)
  });

  // GDP Level 2: Decision point - does asar exist?
  // CRITICAL: Use originalFs to bypass ASAR interception!
  if (originalFs.existsSync(asarPath)) {
    debugLog('app.asar EXISTS - attempting hash with original-fs', { asarPath });

    try {
      // GDP Level 4: Pre-action logging
      debugLog('Starting hash computation (using original-fs to bypass ASAR)');

      const hash = crypto.createHash('sha256');
      // Use originalFs to read the actual app.asar file, not from inside it
      const content = originalFs.readFileSync(asarPath);

      debugLog('File read complete', {
        bytesRead: content.length,
        sizeMB: (content.length / 1024 / 1024).toFixed(2)
      });

      hash.update(content);
      const sha256 = hash.digest('hex');
      const stats = originalFs.statSync(asarPath);

      // GDP Level 5: Post-action logging
      debugLog('Hash computed successfully', {
        sha256: sha256.substring(0, 32) + '...',
        size: stats.size,
        sizeMB: (stats.size / 1024 / 1024).toFixed(2)
      });

      state.components['app.asar'] = {
        sha256,
        size: stats.size,
        installedAt: new Date().toISOString()
      };

      debugLog('Component added to state', {
        componentName: 'app.asar',
        stateComponents: Object.keys(state.components)
      });
    } catch (err) {
      // GDP: Log failure with full context
      debugLog('HASH FAILED', {
        error: err.message,
        code: err.code,
        stack: err.stack?.split('\n').slice(0, 3).join(' | ')
      });
    }
  } else {
    // GDP: Log why we didn't hash
    debugLog('app.asar NOT FOUND', {
      checkedPath: asarPath,
      RESOURCES_PATH,
      parentExists: originalFs.existsSync(path.dirname(asarPath)),
      parentContents: originalFs.existsSync(path.dirname(asarPath)) ?
        originalFs.readdirSync(path.dirname(asarPath)).slice(0, 10) : []
    });
  }

  // GDP Level 4: Pre-save logging
  debugLog('About to save initial state', {
    version: state.version,
    componentCount: Object.keys(state.components).length,
    components: Object.keys(state.components)
  });

  // Save the generated state for future runs
  try {
    saveLocalState(state);
    debugLog('Initial state SAVED', { file: STATE_FILE });
  } catch (err) {
    debugLog('SAVE FAILED', { error: err.message });
  }

  return state;
}

/**
 * Save local component state
 */
function saveLocalState(state) {
  try {
    fs.writeFileSync(STATE_FILE, JSON.stringify(state, null, 2));
  } catch (err) {
    console.error('[PatchUpdater] Failed to save local state:', err.message);
  }
}

/**
 * Fetch JSON from URL
 */
function fetchJson(url) {
  return new Promise((resolve, reject) => {
    const client = url.startsWith('https') ? https : http;

    client.get(url, { timeout: 10000 }, (res) => {
      if (res.statusCode === 404) {
        // Manifest not found - patch updates not available yet
        return resolve(null);
      }

      if (res.statusCode !== 200) {
        return reject(new Error(`HTTP ${res.statusCode}`));
      }

      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          resolve(JSON.parse(data));
        } catch (err) {
          reject(new Error('Invalid JSON'));
        }
      });
    }).on('error', reject);
  });
}

/**
 * Download file with progress callback
 */
function downloadFile(url, destPath, onProgress) {
  // GDP Level 1: Entry point
  debugLog('downloadFile CALLED', { url, destPath });

  return new Promise((resolve, reject) => {
    const isHttps = url.startsWith('https');
    const client = isHttps ? https : http;
    debugLog('Client selected', { protocol: isHttps ? 'HTTPS' : 'HTTP' });

    // GDP Level 4: Pre-action - ensure directory
    const dir = path.dirname(destPath);
    debugLog('Ensuring directory', { dir });

    try {
      fs.mkdirSync(dir, { recursive: true });
      debugLog('Directory created/verified', { dir, exists: fs.existsSync(dir) });
    } catch (err) {
      debugLog('DIRECTORY CREATE FAILED', { error: err.message });
      return reject(err);
    }

    // GDP Level 4: Pre-action - create file stream
    let file;
    try {
      file = fs.createWriteStream(destPath);
      debugLog('File stream created', { destPath });
    } catch (err) {
      debugLog('FILE STREAM FAILED', { error: err.message });
      return reject(err);
    }

    debugLog('Starting HTTP request', { url, timeout: 120000 });

    const req = client.get(url, { timeout: 120000 }, (res) => {
      // GDP Level 5: Response logging
      debugLog('HTTP RESPONSE received', {
        statusCode: res.statusCode,
        contentLength: res.headers['content-length'],
        contentType: res.headers['content-type']
      });

      if (res.statusCode !== 200) {
        try { fs.unlinkSync(destPath); } catch (e) { }
        debugLog('HTTP ERROR - non-200 status', { statusCode: res.statusCode });
        return reject(new Error(`HTTP ${res.statusCode}`));
      }

      const totalSize = parseInt(res.headers['content-length'], 10);
      let downloadedSize = 0;
      let lastLogPercent = 0;
      let chunkCount = 0;

      res.on('data', chunk => {
        chunkCount++;
        downloadedSize += chunk.length;
        const percent = (downloadedSize / totalSize) * 100;

        // GDP: Log first chunk and every 20%
        if (chunkCount === 1 || percent - lastLogPercent >= 20) {
          debugLog('Download progress', {
            percent: percent.toFixed(1),
            downloadedMB: (downloadedSize / 1024 / 1024).toFixed(2),
            totalMB: (totalSize / 1024 / 1024).toFixed(2),
            chunks: chunkCount
          });
          lastLogPercent = Math.floor(percent / 20) * 20;
        }

        if (onProgress) {
          onProgress({ percent, transferred: downloadedSize, total: totalSize });
        }
      });

      res.pipe(file);

      file.on('finish', () => {
        file.close();
        debugLog('DOWNLOAD COMPLETE', {
          destPath,
          finalSize: downloadedSize,
          chunks: chunkCount
        });
        resolve(destPath);
      });

      file.on('error', (err) => {
        debugLog('FILE WRITE ERROR', { error: err.message, code: err.code });
        try { fs.unlinkSync(destPath); } catch (e) { }
        reject(err);
      });

    });

    req.on('error', err => {
      debugLog('REQUEST ERROR', { error: err.message, code: err.code });
      try { fs.unlinkSync(destPath); } catch (e) { }
      reject(err);
    });

    req.on('timeout', () => {
      debugLog('REQUEST TIMEOUT');
      req.destroy();
      try { fs.unlinkSync(destPath); } catch (e) { }
      reject(new Error('Download timeout'));
    });
  });
}

/**
 * Check for patch updates
 * Returns: { available: boolean, updates: [], totalSize: number, version: string }
 */
export async function checkForPatchUpdate() {
  console.log('[PatchUpdater] Checking for patch updates...');

  try {
    // Fetch remote manifest
    const manifest = await fetchJson(MANIFEST_URL);

    if (!manifest) {
      console.log('[PatchUpdater] No manifest found - patch updates not available');
      return { available: false, reason: 'no-manifest' };
    }

    // Load local state
    const localState = loadLocalState();

    console.log(`[PatchUpdater] Local: ${localState.version}, Remote: ${manifest.version}`);

    // Compare versions
    if (localState.version === manifest.version) {
      console.log('[PatchUpdater] Already up to date');
      return { available: false, reason: 'up-to-date' };
    }

    // Check minimum version requirement
    if (manifest.minVersion && compareVersions(localState.version, manifest.minVersion) < 0) {
      console.log('[PatchUpdater] Version too old - full update required');
      return { available: false, reason: 'version-too-old', minVersion: manifest.minVersion };
    }

    // Find changed components
    const updates = [];
    for (const [name, component] of Object.entries(manifest.components)) {
      const localComponent = localState.components[name];

      if (!localComponent || localComponent.sha256 !== component.sha256) {
        updates.push({
          name,
          ...component,
          isNew: !localComponent
        });
      }
    }

    if (updates.length === 0) {
      // Version changed but no component changes? Update state anyway
      console.log('[PatchUpdater] No component changes detected');
      localState.version = manifest.version;
      saveLocalState(localState);
      return { available: false, reason: 'no-changes' };
    }

    const totalSize = updates.reduce((sum, u) => sum + u.size, 0);

    console.log(`[PatchUpdater] ${updates.length} component(s) to update, ${(totalSize / 1024 / 1024).toFixed(2)} MB`);

    return {
      available: true,
      version: manifest.version,
      updates,
      totalSize,
      releaseNotes: manifest.releaseNotes
    };
  } catch (err) {
    console.error('[PatchUpdater] Check failed:', err.message);
    return { available: false, reason: 'error', error: err.message };
  }
}

// Staging directory for pending updates (in AppData, survives restarts)
const STAGING_DIR = path.join(USER_DATA_PATH, 'pending-updates');
const PENDING_FILE = path.join(USER_DATA_PATH, 'pending-update.json');

/**
 * Download and stage patch updates (don't apply yet - files are locked)
 * The actual swap happens on restart via applyPendingUpdates()
 */
export async function applyPatchUpdate(updates, onProgress) {
  // GDP Level 1: Entry point with full context
  debugLog('========== applyPatchUpdate CALLED ==========', {
    updatesCount: updates?.length,
    updateNames: updates?.map(u => u.name),
    STAGING_DIR,
    RESOURCES_PATH,
    UPDATE_BASE_URL
  });

  if (!updates || updates.length === 0) {
    debugLog('NO UPDATES - returning early');
    return { success: [], failed: [], noUpdates: true };
  }

  // GDP Level 4: Pre-action - clean staging
  debugLog('Cleaning staging directory', { exists: fs.existsSync(STAGING_DIR) });
  if (fs.existsSync(STAGING_DIR)) {
    try {
      fs.rmSync(STAGING_DIR, { recursive: true });
      debugLog('Staging cleaned');
    } catch (err) {
      debugLog('STAGING CLEAN FAILED', { error: err.message });
    }
  }

  try {
    fs.mkdirSync(STAGING_DIR, { recursive: true });
    debugLog('Staging directory created', { STAGING_DIR, exists: fs.existsSync(STAGING_DIR) });
  } catch (err) {
    debugLog('STAGING MKDIR FAILED', { error: err.message });
    return { success: [], failed: [{ name: 'staging', error: err.message }] };
  }

  const results = { success: [], failed: [] };
  const pendingUpdates = [];

  let completedSize = 0;
  const totalSize = updates.reduce((sum, u) => sum + u.size, 0);
  debugLog('Total download size', { totalMB: (totalSize / 1024 / 1024).toFixed(2) });

  for (let i = 0; i < updates.length; i++) {
    const update = updates[i];

    // GDP Level 2: Each iteration
    debugLog(`Processing update ${i + 1}/${updates.length}`, {
      name: update.name,
      sizeMB: (update.size / 1024 / 1024).toFixed(2),
      url: update.url,
      sha256: update.sha256?.substring(0, 16) + '...'
    });

    try {
      // Build full URL
      const url = update.url.startsWith('http')
        ? update.url
        : `${UPDATE_BASE_URL}/${REPO_PATH}/releases/download/latest/${update.url}`;

      debugLog('URL resolved', { originalUrl: update.url, resolvedUrl: url });

      const stagingPath = path.join(STAGING_DIR, update.name);
      debugLog('Staging path', { stagingPath });

      // GDP Level 4: Pre-download
      debugLog('Starting download...');

      // Download with progress
      await downloadFile(url, stagingPath, (progress) => {
        if (onProgress) {
          const overallProgress = ((completedSize + progress.transferred) / totalSize) * 100;
          onProgress({
            component: update.name,
            componentProgress: progress.percent,
            overallProgress,
            transferred: completedSize + progress.transferred,
            total: totalSize
          });
        }
      });

      // GDP Level 5: Post-download
      debugLog('Download COMPLETE', {
        name: update.name,
        stagingPath,
        fileExists: fs.existsSync(stagingPath),
        fileSize: fs.existsSync(stagingPath) ? fs.statSync(stagingPath).size : 0
      });

      // Verify hash
      debugLog('Starting hash verification');
      const hash = await hashFile(stagingPath);
      debugLog('Hash computed', {
        computed: hash.substring(0, 16) + '...',
        expected: update.sha256.substring(0, 16) + '...',
        match: hash === update.sha256
      });

      if (hash !== update.sha256) {
        throw new Error(`Hash mismatch: expected ${update.sha256.substring(0, 16)}..., got ${hash.substring(0, 16)}...`);
      }

      debugLog('Update VERIFIED and STAGED', { name: update.name });

      // Record pending update
      pendingUpdates.push({
        name: update.name,
        stagingPath,
        destPath: path.join(RESOURCES_PATH, update.name),
        sha256: update.sha256,
        version: update.version,
        size: update.size
      });

      results.success.push(update.name);
      completedSize += update.size;

    } catch (err) {
      debugLog('UPDATE FAILED', {
        name: update.name,
        error: err.message,
        code: err.code,
        stack: err.stack?.split('\n').slice(0, 3).join(' | ')
      });
      results.failed.push({ name: update.name, error: err.message });
    }
  }

  // GDP Level 5: Final state
  debugLog('Processing complete', {
    successCount: results.success.length,
    failedCount: results.failed.length,
    pendingCount: pendingUpdates.length
  });

  // Save pending updates info (applied on restart)
  if (pendingUpdates.length > 0 && results.failed.length === 0) {
    const pendingInfo = {
      version: updates[0].version,
      createdAt: new Date().toISOString(),
      updates: pendingUpdates,
      resourcesPath: RESOURCES_PATH
    };

    debugLog('Saving pending update file', { PENDING_FILE, pendingInfo });

    try {
      fs.writeFileSync(PENDING_FILE, JSON.stringify(pendingInfo, null, 2));
      debugLog('PENDING FILE SAVED');
      results.needsRestart = true;
    } catch (err) {
      debugLog('PENDING FILE SAVE FAILED', { error: err.message });
    }
  }

  debugLog('========== applyPatchUpdate COMPLETE ==========', results);
  return results;
}

/**
 * Check if there are pending updates to apply
 */
export function hasPendingUpdates() {
  return fs.existsSync(PENDING_FILE);
}

/**
 * Apply pending updates (call this EARLY in startup, before loading heavy resources)
 * Returns true if updates were applied and app should restart
 */
export function applyPendingUpdates() {
  if (!fs.existsSync(PENDING_FILE)) {
    return false;
  }

  console.log('[PatchUpdater] Found pending updates, applying...');

  try {
    const pending = JSON.parse(fs.readFileSync(PENDING_FILE, 'utf8'));
    const localState = loadLocalState();

    for (const update of pending.updates) {
      console.log(`[PatchUpdater] Applying: ${update.name}`);

      if (!fs.existsSync(update.stagingPath)) {
        console.error(`[PatchUpdater] Staging file missing: ${update.stagingPath}`);
        continue;
      }

      // Verify hash again
      const hash = crypto.createHash('sha256');
      hash.update(fs.readFileSync(update.stagingPath));
      if (hash.digest('hex') !== update.sha256) {
        console.error(`[PatchUpdater] Hash mismatch for ${update.name}`);
        continue;
      }

      // Backup and replace
      const backupPath = update.destPath + '.backup';
      if (fs.existsSync(update.destPath)) {
        try {
          fs.copyFileSync(update.destPath, backupPath);
        } catch (err) {
          console.log(`[PatchUpdater] Could not backup (file may be locked): ${err.message}`);
        }
      }

      try {
        fs.copyFileSync(update.stagingPath, update.destPath);
        console.log(`[PatchUpdater] Applied: ${update.name}`);

        // Update state
        localState.components[update.name] = {
          sha256: update.sha256,
          version: update.version,
          updatedAt: new Date().toISOString()
        };

        // Remove backup
        if (fs.existsSync(backupPath)) {
          fs.unlinkSync(backupPath);
        }
      } catch (err) {
        console.error(`[PatchUpdater] Failed to apply ${update.name}: ${err.message}`);
        // Restore backup if apply failed
        if (fs.existsSync(backupPath)) {
          fs.copyFileSync(backupPath, update.destPath);
          fs.unlinkSync(backupPath);
        }
      }
    }

    // Update version
    localState.version = pending.version;
    localState.lastUpdate = new Date().toISOString();
    saveLocalState(localState);

    // Cleanup
    fs.unlinkSync(PENDING_FILE);
    if (fs.existsSync(STAGING_DIR)) {
      fs.rmSync(STAGING_DIR, { recursive: true });
    }

    console.log('[PatchUpdater] Pending updates applied successfully');
    return true;
  } catch (err) {
    console.error('[PatchUpdater] Failed to apply pending updates:', err.message);
    // Cleanup failed state
    try {
      if (fs.existsSync(PENDING_FILE)) fs.unlinkSync(PENDING_FILE);
      if (fs.existsSync(STAGING_DIR)) fs.rmSync(STAGING_DIR, { recursive: true });
    } catch (e) {
      // Ignore cleanup errors
    }
    return false;
  }
}

/**
 * Get path to the update swap script (for restart)
 */
export function getSwapScriptPath() {
  if (process.platform === 'win32') {
    return path.join(USER_DATA_PATH, 'apply-update.ps1');
  }
  return path.join(USER_DATA_PATH, 'apply-update.sh');
}

/**
 * Create the update swap script for restart
 * This script waits for the app to close, then swaps files
 */
export function createSwapScript() {
  if (!fs.existsSync(PENDING_FILE)) {
    return null;
  }

  const pending = JSON.parse(fs.readFileSync(PENDING_FILE, 'utf8'));
  const scriptPath = getSwapScriptPath();

  if (process.platform === 'win32') {
    // PowerShell script for Windows
    const exePath = process.execPath;
    const script = `
# LocaNext Update Swap Script
# Waits for app to close, swaps files, restarts

$ErrorActionPreference = "SilentlyContinue"

# Wait for main process to exit
$processName = "LocaNext"
$maxWait = 30
$waited = 0
while ((Get-Process -Name $processName -ErrorAction SilentlyContinue) -and $waited -lt $maxWait) {
    Start-Sleep -Milliseconds 500
    $waited++
}

# Small extra delay to ensure file handles are released
Start-Sleep -Seconds 1

# Apply updates
${pending.updates.map(u => `
try {
    Copy-Item -Path "${u.stagingPath.replace(/\\/g, '\\\\')}" -Destination "${u.destPath.replace(/\\/g, '\\\\')}" -Force
    Write-Host "Applied: ${u.name}"
} catch {
    Write-Host "Failed: ${u.name}: $_"
}`).join('\n')}

# Cleanup
Remove-Item -Path "${PENDING_FILE.replace(/\\/g, '\\\\')}" -Force -ErrorAction SilentlyContinue
Remove-Item -Path "${STAGING_DIR.replace(/\\/g, '\\\\')}" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "${scriptPath.replace(/\\/g, '\\\\')}" -Force -ErrorAction SilentlyContinue

# Restart app
Start-Process -FilePath "${exePath.replace(/\\/g, '\\\\')}"
`;
    fs.writeFileSync(scriptPath, script, 'utf8');
  } else {
    // Bash script for Linux/Mac
    const script = `#!/bin/bash
# Wait for app to close
sleep 2

# Apply updates
${pending.updates.map(u => `cp "${u.stagingPath}" "${u.destPath}" && echo "Applied: ${u.name}"`).join('\n')}

# Cleanup
rm -f "${PENDING_FILE}"
rm -rf "${STAGING_DIR}"
rm -f "${scriptPath}"

# Restart
"${process.execPath}" &
`;
    fs.writeFileSync(scriptPath, script, { mode: 0o755 });
  }

  return scriptPath;
}

/**
 * Compare version strings (YY.MMDD.HHMM format)
 * Returns: -1 if a < b, 0 if a == b, 1 if a > b
 */
function compareVersions(a, b) {
  const partsA = a.split('.').map(Number);
  const partsB = b.split('.').map(Number);

  for (let i = 0; i < 3; i++) {
    if (partsA[i] < partsB[i]) return -1;
    if (partsA[i] > partsB[i]) return 1;
  }

  return 0;
}

/**
 * Initialize patch updater (create initial state if needed)
 */
export function initPatchUpdater() {
  const state = loadLocalState();
  if (state.version === 'unknown') {
    console.log('[PatchUpdater] Initializing component state...');
    saveLocalState(state);
  }
  return state;
}

export default {
  checkForPatchUpdate,
  applyPatchUpdate,
  initPatchUpdater,
  hasPendingUpdates,
  applyPendingUpdates,
  createSwapScript,
  getSwapScriptPath
};
