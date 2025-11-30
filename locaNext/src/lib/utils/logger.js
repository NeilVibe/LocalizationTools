/**
 * Frontend Logger Utility for LocaNext
 *
 * Provides comprehensive logging capabilities for browser and Electron modes.
 * Logs to both console and rotating log files.
 *
 * Based on LOGGING_PROTOCOL.md
 */

import { writable } from 'svelte/store';

const LOG_LEVELS = {
  INFO: 'INFO',
  SUCCESS: 'SUCCESS',
  WARNING: 'WARNING',
  ERROR: 'ERROR',
  CRITICAL: 'CRITICAL'
};

// Store for log messages (can be used by UI components)
export const logMessages = writable([]);

// Check if running in Electron
const isElectron = typeof window !== 'undefined' && window.electron;

// Configuration
const config = {
  logToConsole: true,
  logToFile: true,
  maxLogMessages: 1000, // Max messages in store
  logFilePath: 'logs/locanext_app.log',
  errorLogFilePath: 'logs/locanext_error.log'
};

/**
 * Format timestamp for log entries
 */
function getTimestamp() {
  const now = new Date();
  return now.toISOString().replace('T', ' ').slice(0, 19);
}

/**
 * Format log message with timestamp and level
 */
function formatLogMessage(level, message, data = null) {
  const timestamp = getTimestamp();
  let logLine = `${timestamp} | ${level.padEnd(8)} | ${message}`;

  if (data && Object.keys(data).length > 0) {
    logLine += ` | ${JSON.stringify(data)}`;
  }

  return logLine;
}

/**
 * Write log to file (Electron mode only)
 */
async function writeToFile(level, message, data) {
  if (!isElectron || !config.logToFile) return;

  try {
    const logLine = formatLogMessage(level, message, data);

    // Write to main log file
    await window.electron.appendLog({
      logPath: config.logFilePath,
      message: logLine
    });

    // Write errors to separate error log
    if (level === LOG_LEVELS.ERROR || level === LOG_LEVELS.CRITICAL) {
      await window.electron.appendLog({
        logPath: config.errorLogFilePath,
        message: logLine
      });
    }
  } catch (error) {
    console.error('Failed to write to log file:', error);
  }
}

/**
 * Core logging function
 */
function log(level, message, data = null) {
  const logEntry = {
    timestamp: getTimestamp(),
    level,
    message,
    data
  };

  // Add to store
  logMessages.update(messages => {
    const updated = [...messages, logEntry];
    // Keep only last N messages
    if (updated.length > config.maxLogMessages) {
      return updated.slice(-config.maxLogMessages);
    }
    return updated;
  });

  // Console output
  if (config.logToConsole) {
    const consoleMessage = formatLogMessage(level, message, data);

    switch (level) {
      case LOG_LEVELS.INFO:
        console.log(`%c${consoleMessage}`, 'color: #0066cc');
        break;
      case LOG_LEVELS.SUCCESS:
        console.log(`%c${consoleMessage}`, 'color: #008800; font-weight: bold');
        break;
      case LOG_LEVELS.WARNING:
        console.warn(consoleMessage);
        break;
      case LOG_LEVELS.ERROR:
        console.error(consoleMessage);
        break;
      case LOG_LEVELS.CRITICAL:
        console.error(`%c${consoleMessage}`, 'color: #ff0000; font-weight: bold; font-size: 14px');
        break;
      default:
        console.log(consoleMessage);
    }
  }

  // File output (Electron only)
  writeToFile(level, message, data);
}

/**
 * Public API
 */
export const logger = {
  /**
   * Log informational message
   * @param {string} message - The message to log
   * @param {object} data - Optional structured data
   */
  info(message, data = null) {
    log(LOG_LEVELS.INFO, message, data);
  },

  /**
   * Log success message
   * @param {string} message - The message to log
   * @param {object} data - Optional structured data
   */
  success(message, data = null) {
    log(LOG_LEVELS.SUCCESS, message, data);
  },

  /**
   * Log warning message
   * @param {string} message - The message to log
   * @param {object} data - Optional structured data
   */
  warning(message, data = null) {
    log(LOG_LEVELS.WARNING, message, data);
  },

  /**
   * Log error message
   * @param {string} message - The message to log
   * @param {object} data - Optional structured data (include error object)
   */
  error(message, data = null) {
    log(LOG_LEVELS.ERROR, message, data);
  },

  /**
   * Log critical error message
   * @param {string} message - The message to log
   * @param {object} data - Optional structured data
   */
  critical(message, data = null) {
    log(LOG_LEVELS.CRITICAL, message, data);
  },

  /**
   * Log component lifecycle events
   * @param {string} componentName - Name of the component
   * @param {string} event - Event name (mounted, destroyed, updated, etc.)
   * @param {object} data - Optional event data
   */
  component(componentName, event, data = null) {
    const message = `Component: ${componentName} - ${event}`;
    log(LOG_LEVELS.INFO, message, data);
  },

  /**
   * Log API call
   * @param {string} endpoint - API endpoint
   * @param {string} method - HTTP method
   * @param {object} data - Optional request data
   */
  apiCall(endpoint, method, data = null) {
    const message = `API ${method} ${endpoint}`;
    log(LOG_LEVELS.INFO, message, data);
  },

  /**
   * Log API response
   * @param {string} endpoint - API endpoint
   * @param {number} status - HTTP status code
   * @param {object} data - Optional response data
   */
  apiResponse(endpoint, status, data = null) {
    const message = `API Response ${endpoint} - Status: ${status}`;
    const level = status >= 200 && status < 300 ? LOG_LEVELS.SUCCESS : LOG_LEVELS.ERROR;
    log(level, message, data);
  },

  /**
   * Log file operation
   * @param {string} operation - Operation type (upload, download, select, etc.)
   * @param {string} filename - Filename
   * @param {object} data - Optional file data (size, type, etc.)
   */
  file(operation, filename, data = null) {
    const message = `File ${operation}: ${filename}`;
    log(LOG_LEVELS.INFO, message, data);
  },

  /**
   * Log user action
   * @param {string} action - Action description
   * @param {object} data - Optional action data
   */
  userAction(action, data = null) {
    const message = `User Action: ${action}`;
    log(LOG_LEVELS.INFO, message, data);
  },

  /**
   * Log performance metric
   * @param {string} operation - Operation name
   * @param {number} duration - Duration in milliseconds
   * @param {object} data - Optional additional data
   */
  performance(operation, duration, data = null) {
    const message = `Performance: ${operation} - ${duration.toFixed(2)}ms`;
    const enrichedData = { ...data, duration_ms: duration };
    log(LOG_LEVELS.INFO, message, enrichedData);
  }
};

// Export configuration for external modification
export const loggerConfig = config;

// Log initialization
logger.info('Logger initialized', {
  mode: isElectron ? 'electron' : 'browser',
  logToConsole: config.logToConsole,
  logToFile: config.logToFile && isElectron
});
