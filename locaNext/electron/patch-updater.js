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
  console.log('[PatchUpdater] Generating initial state from installed files...');

  const state = {
    version: 'unknown',
    installedAt: new Date().toISOString(),
    components: {}
  };

  // Try to get version from package.json in app.asar
  try {
    const { app } = require('electron');
    state.version = app.getVersion();
    console.log(`[PatchUpdater] Got version from app: ${state.version}`);
  } catch (err) {
    console.log('[PatchUpdater] Could not get version from app');
  }

  // Hash app.asar if it exists
  const asarPath = path.join(RESOURCES_PATH, 'app.asar');
  if (fs.existsSync(asarPath)) {
    try {
      const hash = crypto.createHash('sha256');
      const content = fs.readFileSync(asarPath);
      hash.update(content);
      const sha256 = hash.digest('hex');
      const stats = fs.statSync(asarPath);

      state.components['app.asar'] = {
        sha256,
        size: stats.size,
        installedAt: new Date().toISOString()
      };
      console.log(`[PatchUpdater] Hashed app.asar: ${sha256.substring(0, 16)}... (${(stats.size / 1024 / 1024).toFixed(2)} MB)`);
    } catch (err) {
      console.error('[PatchUpdater] Failed to hash app.asar:', err.message);
    }
  } else {
    console.log('[PatchUpdater] app.asar not found at:', asarPath);
  }

  // Save the generated state for future runs
  try {
    saveLocalState(state);
    console.log('[PatchUpdater] Saved initial state');
  } catch (err) {
    console.error('[PatchUpdater] Failed to save initial state:', err.message);
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
  console.log(`[PatchUpdater:download] Starting download from: ${url}`);
  console.log(`[PatchUpdater:download] Destination: ${destPath}`);

  return new Promise((resolve, reject) => {
    const client = url.startsWith('https') ? https : http;
    console.log(`[PatchUpdater:download] Using ${url.startsWith('https') ? 'HTTPS' : 'HTTP'} client`);

    // Ensure temp directory exists
    fs.mkdirSync(path.dirname(destPath), { recursive: true });
    console.log(`[PatchUpdater:download] Directory ensured: ${path.dirname(destPath)}`);

    const file = fs.createWriteStream(destPath);
    console.log(`[PatchUpdater:download] File stream created`);

    const req = client.get(url, { timeout: 120000 }, (res) => {
      console.log(`[PatchUpdater:download] Response status: ${res.statusCode}`);
      console.log(`[PatchUpdater:download] Content-Length: ${res.headers['content-length']}`);

      if (res.statusCode !== 200) {
        try { fs.unlinkSync(destPath); } catch (e) { }
        return reject(new Error(`HTTP ${res.statusCode}`));
      }

      const totalSize = parseInt(res.headers['content-length'], 10);
      let downloadedSize = 0;
      let lastLogPercent = 0;

      res.on('data', chunk => {
        downloadedSize += chunk.length;
        const percent = (downloadedSize / totalSize) * 100;

        // Log every 20%
        if (percent - lastLogPercent >= 20) {
          console.log(`[PatchUpdater:download] ${percent.toFixed(0)}% (${(downloadedSize / 1024 / 1024).toFixed(1)} MB)`);
          lastLogPercent = percent;
        }

        if (onProgress) {
          onProgress({
            percent,
            transferred: downloadedSize,
            total: totalSize
          });
        }
      });

      res.pipe(file);

      file.on('finish', () => {
        file.close();
        console.log(`[PatchUpdater:download] Download complete: ${destPath}`);
        resolve(destPath);
      });

      file.on('error', (err) => {
        console.error(`[PatchUpdater:download] File write error: ${err.message}`);
        try { fs.unlinkSync(destPath); } catch (e) { }
        reject(err);
      });

    });

    req.on('error', err => {
      console.error(`[PatchUpdater:download] Request error: ${err.message}`);
      try { fs.unlinkSync(destPath); } catch (e) { }
      reject(err);
    });

    req.on('timeout', () => {
      console.error(`[PatchUpdater:download] Request timeout`);
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
  console.log('[PatchUpdater] ========== PATCH UPDATE START ==========');
  console.log('[PatchUpdater] Updates to process:', updates?.length);
  console.log('[PatchUpdater] STAGING_DIR:', STAGING_DIR);
  console.log('[PatchUpdater] RESOURCES_PATH:', RESOURCES_PATH);

  // Clean staging directory
  if (fs.existsSync(STAGING_DIR)) {
    fs.rmSync(STAGING_DIR, { recursive: true });
  }
  fs.mkdirSync(STAGING_DIR, { recursive: true });

  const results = { success: [], failed: [] };
  const pendingUpdates = [];

  let completedSize = 0;
  const totalSize = updates.reduce((sum, u) => sum + u.size, 0);

  for (const update of updates) {
    console.log(`[PatchUpdater] ===== Processing: ${update.name} =====`);
    console.log(`[PatchUpdater] Update size: ${(update.size / 1024 / 1024).toFixed(2)} MB`);

    try {
      // Build full URL
      const url = update.url.startsWith('http')
        ? update.url
        : `${UPDATE_BASE_URL}/${REPO_PATH}/releases/download/latest/${update.url}`;

      console.log(`[PatchUpdater] Download URL: ${url}`);

      const stagingPath = path.join(STAGING_DIR, update.name);
      console.log(`[PatchUpdater] Staging path: ${stagingPath}`);
      console.log(`[PatchUpdater] Starting download...`);

      // Download with progress
      await downloadFile(url, stagingPath, (progress) => {
        // Log progress every 10%
        if (Math.floor(progress.percent) % 10 === 0) {
          console.log(`[PatchUpdater] Progress: ${progress.percent.toFixed(0)}%`);
        }
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

      console.log(`[PatchUpdater] Download completed for: ${update.name}`);

      // Verify hash
      console.log(`[PatchUpdater] Verifying hash...`);
      const hash = await hashFile(stagingPath);
      if (hash !== update.sha256) {
        throw new Error(`Hash mismatch: expected ${update.sha256.substring(0, 16)}..., got ${hash.substring(0, 16)}...`);
      }
      console.log(`[PatchUpdater] Hash verified: ${hash.substring(0, 16)}...`);

      console.log(`[PatchUpdater] Verified and staged: ${update.name}`);

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
      console.error(`[PatchUpdater] Failed: ${update.name}:`, err.message);
      results.failed.push({ name: update.name, error: err.message });
    }
  }

  // Save pending updates info (applied on restart)
  if (pendingUpdates.length > 0 && results.failed.length === 0) {
    const pendingInfo = {
      version: updates[0].version,
      createdAt: new Date().toISOString(),
      updates: pendingUpdates,
      resourcesPath: RESOURCES_PATH
    };
    fs.writeFileSync(PENDING_FILE, JSON.stringify(pendingInfo, null, 2));
    console.log(`[PatchUpdater] Staged ${pendingUpdates.length} update(s) - will apply on restart`);
    results.needsRestart = true;
  }

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
