/**
 * Global Progress Store - P18.5.5
 *
 * Single source of truth for all active operations across tools.
 * Progress persists when navigating between apps.
 *
 * Usage:
 *   import { globalProgress, startOperation, updateProgress, completeOperation } from '$lib/stores/globalProgress.js';
 */

import { writable, derived, get } from 'svelte/store';

// Store for all active operations
// Map structure: operationId -> { tool, function, progress, message, startTime, logs }
const operations = writable(new Map());

// Store for status bar visibility
export const statusBarVisible = writable(true);

// Derived store: array of active operations for easy iteration
export const activeOperations = derived(operations, $ops => {
  return Array.from($ops.values()).sort((a, b) => b.startTime - a.startTime);
});

// Derived store: is there any active operation?
export const hasActiveOperations = derived(operations, $ops => $ops.size > 0);

// Derived store: current (most recent) operation
export const currentOperation = derived(activeOperations, $ops => $ops[0] || null);

/**
 * Start a new operation
 * @param {string} operationId - Unique ID for this operation
 * @param {string} tool - Tool name (e.g., 'XLSTransfer', 'QuickSearch', 'KRSimilar')
 * @param {string} functionName - Function being executed (e.g., 'createDictionary')
 */
export function startOperation(operationId, tool, functionName) {
  operations.update(ops => {
    ops.set(operationId, {
      id: operationId,
      tool,
      function: functionName,
      progress: 0,
      message: `Starting ${functionName}...`,
      startTime: Date.now(),
      logs: [],
      status: 'running'
    });
    return ops;
  });

  // Auto-show status bar when operation starts
  statusBarVisible.set(true);
}

/**
 * Update operation progress
 * @param {string} operationId - Operation ID
 * @param {number} progress - Progress percentage (0-100)
 * @param {string} message - Status message
 */
export function updateProgress(operationId, progress, message) {
  operations.update(ops => {
    const op = ops.get(operationId);
    if (op) {
      op.progress = progress;
      op.message = message;
      op.logs.push({ time: Date.now(), message });
      ops.set(operationId, op);
    }
    return ops;
  });
}

/**
 * Complete an operation
 * @param {string} operationId - Operation ID
 * @param {boolean} success - Whether operation succeeded
 * @param {string} finalMessage - Final status message
 */
export function completeOperation(operationId, success, finalMessage) {
  operations.update(ops => {
    const op = ops.get(operationId);
    if (op) {
      op.progress = 100;
      op.message = finalMessage;
      op.status = success ? 'completed' : 'failed';
      op.endTime = Date.now();
      op.duration = op.endTime - op.startTime;
      ops.set(operationId, op);

      // Remove from active after 5 seconds for completed operations
      setTimeout(() => {
        operations.update(innerOps => {
          const stillOp = innerOps.get(operationId);
          if (stillOp && stillOp.status !== 'running') {
            innerOps.delete(operationId);
          }
          return innerOps;
        });
      }, 5000);
    }
    return ops;
  });
}

/**
 * Cancel an operation
 * @param {string} operationId - Operation ID
 */
export function cancelOperation(operationId) {
  completeOperation(operationId, false, 'Operation cancelled');
}

/**
 * Get operation by ID
 * @param {string} operationId - Operation ID
 */
export function getOperation(operationId) {
  return get(operations).get(operationId);
}

/**
 * Generate unique operation ID
 */
export function generateOperationId() {
  return `op_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Toggle status bar visibility
 */
export function toggleStatusBar() {
  statusBarVisible.update(v => !v);
}

/**
 * Hide status bar
 */
export function hideStatusBar() {
  statusBarVisible.set(false);
}

/**
 * Show status bar
 */
export function showStatusBar() {
  statusBarVisible.set(true);
}

// Export the main store for direct subscription
export const globalProgress = {
  operations,
  activeOperations,
  hasActiveOperations,
  currentOperation,
  statusBarVisible,
  startOperation,
  updateProgress,
  completeOperation,
  cancelOperation,
  getOperation,
  generateOperationId,
  toggleStatusBar,
  hideStatusBar,
  showStatusBar
};

export default globalProgress;
