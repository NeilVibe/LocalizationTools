/**
 * Electron App Logger
 * Writes logs to file for monitoring and debugging
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Get project root (2 levels up from electron/)
const projectRoot = path.join(__dirname, '../..');
const logsDir = path.join(projectRoot, 'logs');
const locaNextLogFile = path.join(logsDir, 'locanext_app.log');
const locaNextErrorFile = path.join(logsDir, 'locanext_error.log');

// Ensure logs directory exists
if (!fs.existsSync(logsDir)) {
  fs.mkdirSync(logsDir, { recursive: true });
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
 */
function writeLog(level, message, data = null) {
  const timestamp = getTimestamp();
  let logEntry = `${timestamp} | ${level.padEnd(8)} | ${message}`;

  if (data) {
    if (typeof data === 'object') {
      logEntry += ` | ${JSON.stringify(data)}`;
    } else {
      logEntry += ` | ${data}`;
    }
  }

  logEntry += '\n';

  // Write to main log file
  fs.appendFileSync(locaNextLogFile, logEntry);

  // Also write errors to separate error log
  if (level === 'ERROR' || level === 'CRITICAL') {
    fs.appendFileSync(locaNextErrorFile, logEntry);
  }

  // Also log to console for development
  if (process.env.NODE_ENV === 'development') {
    console.log(logEntry.trim());
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
