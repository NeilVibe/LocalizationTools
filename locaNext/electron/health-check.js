/**
 * Health Check Module for LocaNext
 *
 * Performs quick verification of all components on EVERY app launch.
 * If something is broken, triggers auto-repair.
 *
 * Checks:
 * 1. Python executable exists and works
 * 2. Critical Python packages installed (fastapi, torch, transformers)
 * 3. AI model files present
 * 4. Server files present
 */

import { spawn } from 'child_process';
import fs from 'fs';
import path from 'path';
import { logger } from './logger.js';

/**
 * Health check result object
 */
export const HealthStatus = {
  OK: 'ok',
  NEEDS_REPAIR: 'needs_repair',
  CRITICAL_FAILURE: 'critical_failure'
};

/**
 * Run a quick Python import check
 * @param {string} pythonExe - Path to Python executable
 * @param {string[]} modules - Modules to check
 * @param {number} timeout - Timeout in ms
 * @returns {Promise<{success: boolean, missing: string[]}>}
 */
async function checkPythonImports(pythonExe, modules, timeout = 15000) {
  return new Promise((resolve) => {
    const importCode = modules.map(m => `import ${m}`).join('; ') + '; print("OK")';

    const proc = spawn(pythonExe, ['-c', importCode], {
      timeout,
      windowsHide: true,
      env: {
        ...process.env,
        PYTHONWARNINGS: 'ignore',
        TF_CPP_MIN_LOG_LEVEL: '3',
        TRANSFORMERS_VERBOSITY: 'error'
      }
    });

    let stdout = '';
    let stderr = '';

    proc.stdout.on('data', (d) => stdout += d.toString());
    proc.stderr.on('data', (d) => stderr += d.toString());

    const timeoutId = setTimeout(() => {
      proc.kill();
      resolve({ success: false, missing: modules, error: 'timeout' });
    }, timeout);

    proc.on('close', (code) => {
      clearTimeout(timeoutId);
      if (code === 0 && stdout.includes('OK')) {
        resolve({ success: true, missing: [] });
      } else {
        // Try to identify which module failed
        const missing = [];
        for (const mod of modules) {
          if (stderr.includes(`No module named '${mod}'`) || stderr.includes(`No module named "${mod}"`)) {
            missing.push(mod);
          }
        }
        resolve({ success: false, missing: missing.length > 0 ? missing : modules, error: stderr });
      }
    });

    proc.on('error', (err) => {
      clearTimeout(timeoutId);
      resolve({ success: false, missing: modules, error: err.message });
    });
  });
}

/**
 * Check if a file or directory exists
 */
function checkPath(filePath, description) {
  const exists = fs.existsSync(filePath);
  return {
    path: filePath,
    description,
    exists,
    status: exists ? 'ok' : 'missing'
  };
}

/**
 * Perform full health check
 * @param {object} paths - App paths from main.js
 * @returns {Promise<object>} Health check results
 */
export async function performHealthCheck(paths) {
  logger.info('Starting health check', { paths });
  const startTime = Date.now();

  const results = {
    status: HealthStatus.OK,
    checks: {},
    repairNeeded: [],
    timestamp: new Date().toISOString()
  };

  // 1. Check Python executable
  logger.info('Health check: Python executable');
  const pythonCheck = checkPath(paths.pythonExe, 'Python executable');
  results.checks.python = pythonCheck;
  if (!pythonCheck.exists) {
    results.status = HealthStatus.CRITICAL_FAILURE;
    results.repairNeeded.push('python');
    logger.error('Health check FAILED: Python executable missing', { path: paths.pythonExe });
    return results; // Can't continue without Python
  }

  // 2. Check server files
  logger.info('Health check: Server files');
  const serverMain = path.join(paths.serverPath, 'main.py');
  const serverCheck = checkPath(serverMain, 'Server main.py');
  results.checks.server = serverCheck;
  if (!serverCheck.exists) {
    results.status = HealthStatus.CRITICAL_FAILURE;
    results.repairNeeded.push('server');
    logger.error('Health check FAILED: Server files missing', { path: serverMain });
    return results;
  }

  // 3. Check critical Python packages (quick check - core only)
  logger.info('Health check: Core Python packages');
  const corePackages = await checkPythonImports(paths.pythonExe, ['fastapi', 'uvicorn'], 10000);
  results.checks.corePackages = {
    description: 'Core packages (fastapi, uvicorn)',
    ...corePackages
  };
  if (!corePackages.success) {
    results.status = HealthStatus.NEEDS_REPAIR;
    results.repairNeeded.push('deps');
    logger.warning('Health check: Core packages missing', { missing: corePackages.missing });
  }

  // 4. Check AI packages (torch, transformers)
  logger.info('Health check: AI packages');
  const aiPackages = await checkPythonImports(paths.pythonExe, ['torch', 'transformers', 'sentence_transformers'], 15000);
  results.checks.aiPackages = {
    description: 'AI packages (torch, transformers)',
    ...aiPackages
  };
  if (!aiPackages.success) {
    results.status = HealthStatus.NEEDS_REPAIR;
    if (!results.repairNeeded.includes('deps')) {
      results.repairNeeded.push('deps');
    }
    logger.warning('Health check: AI packages missing', { missing: aiPackages.missing });
  }

  // 5. Check AI model files
  logger.info('Health check: AI model files');
  const modelConfig = path.join(paths.modelsPath, 'kr-sbert', 'config.json');
  const modelCheck = checkPath(modelConfig, 'Korean BERT model');
  results.checks.model = modelCheck;
  if (!modelCheck.exists) {
    // Check if it's just placeholder
    const placeholder = path.join(paths.modelsPath, 'kr-sbert', 'model_placeholder.txt');
    if (fs.existsSync(placeholder)) {
      results.checks.model.status = 'placeholder_only';
    }
    results.status = HealthStatus.NEEDS_REPAIR;
    results.repairNeeded.push('model');
    logger.warning('Health check: AI model missing or placeholder only');
  }

  // Calculate elapsed time
  const elapsed = Date.now() - startTime;
  results.elapsedMs = elapsed;

  logger.info('Health check complete', {
    status: results.status,
    repairNeeded: results.repairNeeded,
    elapsedMs: elapsed
  });

  return results;
}

/**
 * Quick health check - only checks critical paths, no Python imports
 * Use this for fast startup, then do full check in background
 * @param {object} paths - App paths
 * @returns {object} Quick check results
 */
export function quickHealthCheck(paths) {
  logger.info('Quick health check starting');

  const results = {
    status: HealthStatus.OK,
    pythonExists: fs.existsSync(paths.pythonExe),
    serverExists: fs.existsSync(path.join(paths.serverPath, 'main.py')),
    modelExists: fs.existsSync(path.join(paths.modelsPath, 'kr-sbert', 'config.json'))
  };

  if (!results.pythonExists || !results.serverExists) {
    results.status = HealthStatus.CRITICAL_FAILURE;
  } else if (!results.modelExists) {
    results.status = HealthStatus.NEEDS_REPAIR;
  }

  logger.info('Quick health check complete', results);
  return results;
}

/**
 * Check if repair has been done recently (within last hour)
 * Prevents repair loops
 * @param {string} appRoot - App root directory
 * @returns {boolean}
 */
export function wasRecentlyRepaired(appRoot) {
  const repairLog = path.join(appRoot, 'last_repair.json');
  try {
    if (fs.existsSync(repairLog)) {
      const data = JSON.parse(fs.readFileSync(repairLog, 'utf-8'));
      const lastRepair = new Date(data.timestamp);
      const hourAgo = new Date(Date.now() - 60 * 60 * 1000);
      return lastRepair > hourAgo;
    }
  } catch (err) {
    logger.warning('Could not read repair log', { error: err.message });
  }
  return false;
}

/**
 * Record that repair was attempted
 * @param {string} appRoot - App root directory
 * @param {string[]} components - Components that were repaired
 */
export function recordRepairAttempt(appRoot, components) {
  const repairLog = path.join(appRoot, 'last_repair.json');
  const data = {
    timestamp: new Date().toISOString(),
    components,
    version: process.env.npm_package_version || 'unknown'
  };
  try {
    fs.writeFileSync(repairLog, JSON.stringify(data, null, 2));
    logger.info('Recorded repair attempt', data);
  } catch (err) {
    logger.error('Could not write repair log', { error: err.message });
  }
}

export default {
  performHealthCheck,
  quickHealthCheck,
  wasRecentlyRepaired,
  recordRepairAttempt,
  HealthStatus
};
