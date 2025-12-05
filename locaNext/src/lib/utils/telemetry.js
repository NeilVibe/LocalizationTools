/**
 * Telemetry Utility - Tool Usage Tracking for Central Server
 *
 * Priority 12.5.9 - Sends tool usage data to central telemetry server.
 * Works with electronTelemetry API (from preload.js) in Electron mode.
 *
 * Usage:
 *   import { telemetry } from '$lib/utils/telemetry.js';
 *
 *   // Track tool operation
 *   telemetry.trackOperation('XLSTransfer', 'create_dictionary', {
 *     duration_ms: 1500,
 *     rows_processed: 1000,
 *     status: 'success'
 *   });
 */

// Check if running in Electron with telemetry support
const isElectron = typeof window !== 'undefined' && window.electronTelemetry;

/**
 * Get telemetry state (enabled status, connection info)
 */
async function getState() {
  if (!isElectron) {
    return { enabled: false, reason: 'Not running in Electron' };
  }
  try {
    return await window.electronTelemetry.getState();
  } catch (e) {
    return { enabled: false, reason: e.message };
  }
}

/**
 * Log a message to telemetry
 */
async function log(level, message, component, data = {}) {
  if (!isElectron) return { success: false, reason: 'Not in Electron' };

  try {
    return await window.electronTelemetry.log(level, message, component, data);
  } catch (e) {
    console.warn('Telemetry log failed:', e.message);
    return { success: false, reason: e.message };
  }
}

/**
 * Track a tool operation
 *
 * @param {string} toolName - Tool name (e.g., 'XLSTransfer', 'QuickSearch')
 * @param {string} functionName - Function name (e.g., 'create_dictionary', 'search')
 * @param {Object} metrics - Operation metrics
 * @param {number} metrics.duration_ms - Operation duration in milliseconds
 * @param {string} metrics.status - 'success' or 'error'
 * @param {number} [metrics.rows_processed] - Number of rows processed
 * @param {number} [metrics.files_count] - Number of files involved
 * @param {string} [metrics.error_message] - Error message if status is 'error'
 */
async function trackOperation(toolName, functionName, metrics = {}) {
  const level = metrics.status === 'error' ? 'ERROR' : 'SUCCESS';
  const message = `${toolName}.${functionName} ${metrics.status === 'error' ? 'failed' : 'completed'}`;

  const data = {
    tool_name: toolName,
    function_name: functionName,
    duration_ms: metrics.duration_ms || 0,
    duration_seconds: (metrics.duration_ms || 0) / 1000,
    status: metrics.status || 'unknown',
    ...metrics
  };

  // Remove undefined values
  Object.keys(data).forEach(key => {
    if (data[key] === undefined) delete data[key];
  });

  return await log(level, message, toolName, data);
}

/**
 * Track start of a tool operation
 */
async function trackOperationStart(toolName, functionName, details = {}) {
  return await log('INFO', `${toolName}.${functionName} started`, toolName, {
    tool_name: toolName,
    function_name: functionName,
    event: 'operation_start',
    ...details
  });
}

/**
 * Track successful completion of a tool operation
 */
async function trackOperationSuccess(toolName, functionName, startTime, details = {}) {
  const duration_ms = Date.now() - startTime;
  return await trackOperation(toolName, functionName, {
    duration_ms,
    status: 'success',
    ...details
  });
}

/**
 * Track failed tool operation
 */
async function trackOperationError(toolName, functionName, startTime, error, details = {}) {
  const duration_ms = Date.now() - startTime;
  return await trackOperation(toolName, functionName, {
    duration_ms,
    status: 'error',
    error_message: error?.message || String(error),
    error_type: error?.name || 'Error',
    ...details
  });
}

/**
 * Track user action (button click, navigation, etc.)
 */
async function trackUserAction(action, component, details = {}) {
  return await log('INFO', `User action: ${action}`, component, {
    event: 'user_action',
    action,
    ...details
  });
}

// Export telemetry object
export const telemetry = {
  // Core methods
  getState,
  log,

  // Convenience methods
  info: (message, component, data) => log('INFO', message, component, data),
  success: (message, component, data) => log('SUCCESS', message, component, data),
  warning: (message, component, data) => log('WARNING', message, component, data),
  error: (message, component, data) => log('ERROR', message, component, data),

  // Tool tracking methods
  trackOperation,
  trackOperationStart,
  trackOperationSuccess,
  trackOperationError,
  trackUserAction,

  // State check
  isEnabled: () => isElectron
};

export default telemetry;
