/**
 * Admin Dashboard Logger (Browser-side)
 * Console logging with colored output by severity level.
 */

const LOG_LEVELS = {
  INFO: 'INFO',
  SUCCESS: 'SUCCESS',
  WARNING: 'WARNING',
  ERROR: 'ERROR',
  CRITICAL: 'CRITICAL'
};

function getTimestamp() {
  return new Date().toISOString().replace('T', ' ').slice(0, 19);
}

function formatLogMessage(level, message, data = null) {
  let logLine = `${getTimestamp()} | ${level.padEnd(8)} | ${message}`;
  if (data && Object.keys(data).length > 0) {
    logLine += ` | ${JSON.stringify(data)}`;
  }
  return logLine;
}

function log(level, message, data = null) {
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

export const logger = {
  info(message, data = null) { log(LOG_LEVELS.INFO, message, data); },
  success(message, data = null) { log(LOG_LEVELS.SUCCESS, message, data); },
  warning(message, data = null) { log(LOG_LEVELS.WARNING, message, data); },
  error(message, data = null) { log(LOG_LEVELS.ERROR, message, data); },
  critical(message, data = null) { log(LOG_LEVELS.CRITICAL, message, data); },

  component(componentName, event, data = null) {
    log(LOG_LEVELS.INFO, `Component: ${componentName} - ${event}`, data);
  },
  apiCall(endpoint, method, data = null) {
    log(LOG_LEVELS.INFO, `API ${method} ${endpoint}`, data);
  },
  apiResponse(endpoint, status, data = null) {
    const level = status >= 200 && status < 300 ? LOG_LEVELS.SUCCESS : LOG_LEVELS.ERROR;
    log(level, `API Response ${endpoint} - Status: ${status}`, data);
  },
  userAction(action, data = null) {
    log(LOG_LEVELS.INFO, `User Action: ${action}`, data);
  },
  performance(operation, duration, data = null) {
    log(LOG_LEVELS.INFO, `Performance: ${operation} - ${duration.toFixed(2)}ms`, { ...data, duration_ms: duration });
  }
};

export default logger;
