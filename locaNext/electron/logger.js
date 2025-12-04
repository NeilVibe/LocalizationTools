/**
 * Electron App Logger
 * Writes logs to file for monitoring and debugging
 *
 * FIXED v2: Uses app.getPath('userData') for reliable cross-platform logging
 * - In dev: logs go to locaNext/logs/
 * - In production: logs go to %APPDATA%/locanext/logs/ (standard Electron location)
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { app } from 'electron';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/**
 * Get the correct logs directory based on environment
 * - Development: project_root/logs/
 * - Production: %APPDATA%/locanext/logs/ (reliable, always writable)
 */
function getLogsDir() {
  // Check if we're running inside an ASAR archive (packaged app)
  const isPackaged = __dirname.includes('app.asar');

  if (isPackaged) {
    // Production: use Electron's userData path (standard, always writable)
    // Windows: C:\Users\{user}\AppData\Roaming\locanext\logs
    // This is the PROPER way to handle logs in Electron apps
    try {
      const userData = app.getPath('userData');
      return path.join(userData, 'logs');
    } catch (e) {
      // Fallback: try process.cwd() (usually the app root)
      return path.join(process.cwd(), 'logs');
    }
  } else {
    // Development: 2 levels up from electron/
    const projectRoot = path.join(__dirname, '../..');
    return path.join(projectRoot, 'logs');
  }
}

// Lazy-initialized paths (can't call app.getPath before app is ready)
let _logsDir = null;
let _locaNextLogFile = null;
let _locaNextErrorFile = null;
let _initialized = false;

/**
 * Initialize logs directory (called lazily on first log write)
 */
function initLogsDir() {
  if (_initialized) return;

  _logsDir = getLogsDir();
  _locaNextLogFile = path.join(_logsDir, 'locanext_app.log');
  _locaNextErrorFile = path.join(_logsDir, 'locanext_error.log');

  // Ensure logs directory exists
  try {
    if (!fs.existsSync(_logsDir)) {
      fs.mkdirSync(_logsDir, { recursive: true });
    }
    _initialized = true;
  } catch (err) {
    console.error('Failed to create logs directory:', _logsDir, err.message);
  }
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
  // Lazy init on first write (ensures app is ready)
  initLogsDir();

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
  if (_initialized && _locaNextLogFile) {
    try {
      fs.appendFileSync(_locaNextLogFile, logEntry);

      // Also write errors to separate error log
      if ((level === 'ERROR' || level === 'CRITICAL') && _locaNextErrorFile) {
        fs.appendFileSync(_locaNextErrorFile, logEntry);
      }
    } catch (err) {
      // File write failed - already logged to console above
      console.error('Failed to write to log file:', err.message);
    }
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
    initLogsDir();
    if (!_initialized || !_locaNextLogFile) return;

    try {
      const stats = fs.statSync(_locaNextLogFile);
      const daysOld = (Date.now() - stats.mtimeMs) / (1000 * 60 * 60 * 24);

      if (daysOld > 7) {
        // Archive old log
        const archiveDir = path.join(_logsDir, 'archive');
        if (!fs.existsSync(archiveDir)) {
          fs.mkdirSync(archiveDir, { recursive: true });
        }

        const timestamp = new Date().toISOString().split('T')[0];
        const archiveFile = path.join(archiveDir, `locanext_app_${timestamp}.log`);
        fs.renameSync(_locaNextLogFile, archiveFile);

        writeLog('INFO', 'Log file archived and rotated');
      }
    } catch (error) {
      // File doesn't exist yet, ignore
    }
  },

  /**
   * Get current logs directory (for diagnostics)
   */
  getLogsDir() {
    initLogsDir();
    return _logsDir;
  }
};

// NO auto-initialization - logs start when first writeLog is called
// This ensures app is ready before we try to get paths

export default logger;
