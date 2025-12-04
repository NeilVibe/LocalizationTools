/**
 * Electron App Logger
 * Writes logs to file for monitoring and debugging
 *
 * FIXED: Handles ASAR packaging correctly
 * - In dev: logs go to locaNext/logs/
 * - In production: logs go to install_dir/logs/ (outside ASAR)
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/**
 * Get the correct logs directory based on environment
 * - Development: project_root/logs/
 * - Production: install_dir/logs/ (NOT inside app.asar!)
 */
function getLogsDir() {
  // Check if we're running inside an ASAR archive (packaged app)
  const isPackaged = __dirname.includes('app.asar');

  if (isPackaged) {
    // Production: use process.resourcesPath to get outside ASAR
    // process.resourcesPath = C:\...\LocaNext\resources
    // We want: C:\...\LocaNext\logs
    const appRoot = path.join(process.resourcesPath, '..');
    return path.join(appRoot, 'logs');
  } else {
    // Development: 2 levels up from electron/
    const projectRoot = path.join(__dirname, '../..');
    return path.join(projectRoot, 'logs');
  }
}

const logsDir = getLogsDir();
const locaNextLogFile = path.join(logsDir, 'locanext_app.log');
const locaNextErrorFile = path.join(logsDir, 'locanext_error.log');

// Ensure logs directory exists (with error handling for production)
try {
  if (!fs.existsSync(logsDir)) {
    fs.mkdirSync(logsDir, { recursive: true });
  }
} catch (err) {
  // If we can't create logs dir, log to console only
  console.error('Failed to create logs directory:', logsDir, err.message);
}

/**
 * Format timestamp for log entries
 */
function getTimestamp() {
  const now = new Date();
  return now.toISOString().replace('T', ' ').substring(0, 19);
}

/**
 * Write log entry to file
 * Robust: won't crash if file write fails
 */
function writeLog(level, message, data = null) {
  const timestamp = getTimestamp();
  let logEntry = `${timestamp} | ${level.padEnd(8)} | ${message}`;

  if (data) {
    if (typeof data === 'object') {
      try {
        logEntry += ` | ${JSON.stringify(data)}`;
      } catch {
        logEntry += ` | [object - could not stringify]`;
      }
    } else {
      logEntry += ` | ${data}`;
    }
  }

  logEntry += '\n';

  // Always log to console in production too (helps with debugging)
  console.log(logEntry.trim());

  // Try to write to file, but don't crash if it fails
  try {
    fs.appendFileSync(locaNextLogFile, logEntry);

    // Also write errors to separate error log
    if (level === 'ERROR' || level === 'CRITICAL') {
      fs.appendFileSync(locaNextErrorFile, logEntry);
    }
  } catch (err) {
    // File write failed - already logged to console above
    console.error('Failed to write to log file:', err.message);
  }
}

/**
 * Public API
 */
export const logger = {
  info(message, data) {
    writeLog('INFO', message, data);
  },

  success(message, data) {
    writeLog('SUCCESS', message, data);
  },

  warning(message, data) {
    writeLog('WARNING', message, data);
  },

  error(message, data) {
    writeLog('ERROR', message, data);
  },

  critical(message, data) {
    writeLog('CRITICAL', message, data);
  },

  debug(message, data) {
    if (process.env.NODE_ENV === 'development') {
      writeLog('DEBUG', message, data);
    }
  },

  /**
   * Log IPC call
   */
  ipc(channel, data) {
    writeLog('IPC', `IPC call: ${channel}`, data);
  },

  /**
   * Log Python execution
   */
  python(scriptPath, success, output) {
    const level = success ? 'SUCCESS' : 'ERROR';
    writeLog(level, `Python: ${scriptPath}`, { success, output: output?.substring(0, 200) });
  },

  /**
   * Clear old logs (keep last 7 days)
   */
  cleanup() {
    try {
      const stats = fs.statSync(locaNextLogFile);
      const daysOld = (Date.now() - stats.mtimeMs) / (1000 * 60 * 60 * 24);

      if (daysOld > 7) {
        // Archive old log
        const archiveDir = path.join(logsDir, 'archive');
        if (!fs.existsSync(archiveDir)) {
          fs.mkdirSync(archiveDir, { recursive: true });
        }

        const timestamp = new Date().toISOString().split('T')[0];
        const archiveFile = path.join(archiveDir, `locanext_app_${timestamp}.log`);
        fs.renameSync(locaNextLogFile, archiveFile);

        writeLog('INFO', 'Log file archived and rotated');
      }
    } catch (error) {
      // File doesn't exist yet, ignore
    }
  }
};

// Initialize logger
logger.info('LocaNext Electron Logger initialized', { logsDir });

export default logger;
