/**
 * Electron App Logger - BULLETPROOF VERSION
 *
 * Uses process.execPath for 100% reliable path detection
 * - In dev: C:\...\electron.exe -> locaNext/logs/
 * - In production: C:\...\LocaNext\LocaNext.exe -> LocaNext/logs/
 *
 * NO ELECTRON IMPORTS - pure Node.js only
 */

import fs from 'fs';
import path from 'path';

// ===============================================================
// BULLETPROOF PATH DETECTION
// process.execPath is ALWAYS available and ALWAYS correct
// ===============================================================

function getLogsDir() {
  // process.execPath examples:
  // Dev:  C:\Users\...\AppData\Local\electron\Cache\...\electron.exe
  // Prod: C:\Users\MYCOM\Desktop\LocaNext\LocaNext.exe

  const exePath = process.execPath;
  const exeDir = path.dirname(exePath);
  const exeName = path.basename(exePath).toLowerCase();

  // Is this a packaged app? Check if exe is named LocaNext.exe
  const isPackaged = exeName === 'locanext.exe';

  if (isPackaged) {
    // Production: logs go next to the exe
    // C:\...\LocaNext\LocaNext.exe -> C:\...\LocaNext\logs\
    return path.join(exeDir, 'logs');
  } else {
    // Development: we're running from electron.exe
    // Use current working directory (project root)
    return path.join(process.cwd(), 'locaNext', 'logs');
  }
}

// Initialize paths IMMEDIATELY (no lazy init - we need this ASAP)
let _logsDir = null;
let _logFile = null;
let _errorFile = null;
let _crashFile = null;
let _initError = null;

try {
  _logsDir = getLogsDir();

  // Create logs directory
  if (!fs.existsSync(_logsDir)) {
    fs.mkdirSync(_logsDir, { recursive: true });
  }

  _logFile = path.join(_logsDir, 'locanext_app.log');
  _errorFile = path.join(_logsDir, 'locanext_error.log');
  _crashFile = path.join(_logsDir, 'locanext_crash.log');

  // Write startup marker immediately
  const startupMsg = `\n${'='.repeat(60)}\n` +
    `[${new Date().toISOString()}] Logger initialized\n` +
    `  execPath: ${process.execPath}\n` +
    `  logsDir: ${_logsDir}\n` +
    `  cwd: ${process.cwd()}\n` +
    `${'='.repeat(60)}\n`;

  fs.appendFileSync(_logFile, startupMsg);

} catch (err) {
  _initError = err;
  // Fallback: try to write to a crash file in the exe directory
  try {
    const fallbackDir = path.dirname(process.execPath);
    const fallbackFile = path.join(fallbackDir, 'LOGGER_INIT_ERROR.txt');
    fs.writeFileSync(fallbackFile, `Logger init failed: ${err.message}\n${err.stack}`);
  } catch {
    // Absolutely nothing we can do
  }
}

/**
 * Format timestamp
 */
function timestamp() {
  return new Date().toISOString().replace('T', ' ').substring(0, 19);
}

/**
 * Write to log file
 */
function writeLog(level, message, data = null) {
  let entry = `${timestamp()} | ${level.padEnd(8)} | ${message}`;

  if (data !== null) {
    try {
      entry += ` | ${typeof data === 'object' ? JSON.stringify(data) : data}`;
    } catch {
      entry += ' | [unstringifiable data]';
    }
  }
  entry += '\n';

  // Always console log
  console.log(entry.trim());

  // Write to file if initialized
  if (_logFile) {
    try {
      fs.appendFileSync(_logFile, entry);

      // Errors also go to error log
      if (level === 'ERROR' || level === 'CRITICAL') {
        fs.appendFileSync(_errorFile, entry);
      }
    } catch (err) {
      console.error('Log write failed:', err.message);
    }
  }
}

/**
 * Write crash/exception to crash log
 */
function writeCrash(error) {
  const entry = `\n${'!'.repeat(60)}\n` +
    `[${timestamp()}] CRASH/EXCEPTION\n` +
    `Message: ${error.message}\n` +
    `Stack: ${error.stack || 'no stack'}\n` +
    `${'!'.repeat(60)}\n`;

  console.error(entry);

  if (_crashFile) {
    try {
      fs.appendFileSync(_crashFile, entry);
    } catch {
      // Nothing we can do
    }
  }
}

/**
 * Public API
 */
export const logger = {
  info: (msg, data) => writeLog('INFO', msg, data),
  success: (msg, data) => writeLog('SUCCESS', msg, data),
  warning: (msg, data) => writeLog('WARNING', msg, data),
  error: (msg, data) => writeLog('ERROR', msg, data),
  critical: (msg, data) => writeLog('CRITICAL', msg, data),
  debug: (msg, data) => {
    if (process.env.NODE_ENV === 'development') {
      writeLog('DEBUG', msg, data);
    }
  },

  // IPC logging
  ipc: (channel, data) => writeLog('IPC', `IPC: ${channel}`, data),

  // Python execution logging
  python: (script, success, output) => {
    writeLog(success ? 'SUCCESS' : 'ERROR', `Python: ${script}`,
      { success, output: output?.substring(0, 200) });
  },

  // Crash logging
  crash: writeCrash,

  // Get logs directory (for diagnostics)
  getLogsDir: () => _logsDir,

  // Get any init error
  getInitError: () => _initError,

  // Log cleanup (keep last 7 days)
  cleanup: () => {
    if (!_logFile) return;

    try {
      const stats = fs.statSync(_logFile);
      const daysOld = (Date.now() - stats.mtimeMs) / (1000 * 60 * 60 * 24);

      if (daysOld > 7) {
        const archiveDir = path.join(_logsDir, 'archive');
        if (!fs.existsSync(archiveDir)) {
          fs.mkdirSync(archiveDir, { recursive: true });
        }
        const archiveFile = path.join(archiveDir, `locanext_${new Date().toISOString().split('T')[0]}.log`);
        fs.renameSync(_logFile, archiveFile);
        writeLog('INFO', 'Log archived and rotated');
      }
    } catch {
      // File might not exist yet
    }
  }
};

export default logger;
