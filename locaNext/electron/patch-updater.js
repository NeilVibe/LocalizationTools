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
  return new Promise((resolve, reject) => {
    const client = url.startsWith('https') ? https : http;

    // Ensure temp directory exists
    fs.mkdirSync(path.dirname(destPath), { recursive: true });

    const file = fs.createWriteStream(destPath);

    client.get(url, { timeout: 60000 }, (res) => {
      if (res.statusCode !== 200) {
        fs.unlinkSync(destPath);
        return reject(new Error(`HTTP ${res.statusCode}`));
      }

      const totalSize = parseInt(res.headers['content-length'], 10);
      let downloadedSize = 0;

      res.on('data', chunk => {
        downloadedSize += chunk.length;
        if (onProgress) {
          onProgress({
            percent: (downloadedSize / totalSize) * 100,
            transferred: downloadedSize,
            total: totalSize
          });
        }
      });

      res.pipe(file);

      file.on('finish', () => {
        file.close();
        resolve(destPath);
      });
    }).on('error', err => {
      fs.unlinkSync(destPath);
      reject(err);
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

/**
 * Download and apply patch updates
 */
export async function applyPatchUpdate(updates, onProgress) {
  console.log('[PatchUpdater] Applying patch update...');

  // Clean temp directory
  if (fs.existsSync(TEMP_DIR)) {
    fs.rmSync(TEMP_DIR, { recursive: true });
  }
  fs.mkdirSync(TEMP_DIR, { recursive: true });

  const localState = loadLocalState();
  const results = { success: [], failed: [] };

  let completedSize = 0;
  const totalSize = updates.reduce((sum, u) => sum + u.size, 0);

  for (const update of updates) {
    console.log(`[PatchUpdater] Downloading: ${update.name}`);

    try {
      // Build full URL
      const url = update.url.startsWith('http')
        ? update.url
        : `${UPDATE_BASE_URL}/${REPO_PATH}/releases/download/latest/${update.url}`;

      const tempPath = path.join(TEMP_DIR, update.name);

      // Download with progress
      await downloadFile(url, tempPath, (progress) => {
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

      // Verify hash
      const hash = await hashFile(tempPath);
      if (hash !== update.sha256) {
        throw new Error(`Hash mismatch: expected ${update.sha256.substring(0, 16)}..., got ${hash.substring(0, 16)}...`);
      }

      console.log(`[PatchUpdater] Verified: ${update.name}`);

      // Apply update
      const destPath = path.join(RESOURCES_PATH, update.name);

      // Backup original (in case we need to rollback)
      const backupPath = path.join(TEMP_DIR, `${update.name}.backup`);
      if (fs.existsSync(destPath)) {
        fs.copyFileSync(destPath, backupPath);
      }

      // Copy new file
      fs.copyFileSync(tempPath, destPath);

      console.log(`[PatchUpdater] Applied: ${update.name}`);

      // Update local state
      localState.components[update.name] = {
        version: update.version,
        sha256: update.sha256,
        updatedAt: new Date().toISOString()
      };

      results.success.push(update.name);
      completedSize += update.size;

    } catch (err) {
      console.error(`[PatchUpdater] Failed: ${update.name}:`, err.message);
      results.failed.push({ name: update.name, error: err.message });
    }
  }

  // Update version if all succeeded
  if (results.failed.length === 0) {
    localState.version = updates[0].version;
    localState.lastUpdate = new Date().toISOString();
  }

  saveLocalState(localState);

  // Cleanup temp directory
  try {
    fs.rmSync(TEMP_DIR, { recursive: true });
  } catch (err) {
    // Ignore cleanup errors
  }

  return results;
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
  initPatchUpdater
};
