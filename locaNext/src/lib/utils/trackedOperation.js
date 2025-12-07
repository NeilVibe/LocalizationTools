/**
 * Tracked Operation Module - P18.6 FACTOR ARCHITECTURE
 *
 * Centralized progress tracking for ALL async operations.
 * "Mega Trunk" - Graftable to ANY process.
 *
 * USAGE:
 *   // Wrapper style (recommended):
 *   const result = await withProgress('XLSTransfer', 'Create Dictionary', async (progress) => {
 *     progress.update(50, 'Processing...');
 *     return someResult;
 *   });
 *
 *   // Python execution (auto-tracks stderr):
 *   const result = await executePythonTracked(scriptPath, args, {
 *     tool: 'XLSTransfer',
 *     operation: 'Create Dictionary'
 *   });
 */

import {
  startOperation,
  updateProgress,
  completeOperation,
  generateOperationId
} from '$lib/stores/globalProgress.js';

/**
 * Parse progress from stderr output
 * Centralized parser - supports multiple formats
 *
 * @param {string} line - stderr line
 * @returns {{ progress: number, message: string } | null}
 */
export function parseProgress(line) {
  if (!line || typeof line !== 'string') return null;

  const trimmed = line.trim();
  if (!trimmed) return null;

  // Pattern 1: "XX%" or "XX.X%"
  const percentMatch = trimmed.match(/(\d+(?:\.\d+)?)\s*%/);
  if (percentMatch) {
    return {
      progress: parseFloat(percentMatch[1]),
      message: trimmed
    };
  }

  // Pattern 2: "Row X/Y" or "X/Y rows"
  const rowMatch = trimmed.match(/(?:row\s+)?(\d+)\s*\/\s*(\d+)/i);
  if (rowMatch) {
    const current = parseInt(rowMatch[1]);
    const total = parseInt(rowMatch[2]);
    if (total > 0) {
      return {
        progress: Math.round((current / total) * 100),
        message: trimmed
      };
    }
  }

  // Pattern 3: "Step X of Y"
  const stepMatch = trimmed.match(/step\s+(\d+)\s+of\s+(\d+)/i);
  if (stepMatch) {
    const current = parseInt(stepMatch[1]);
    const total = parseInt(stepMatch[2]);
    if (total > 0) {
      return {
        progress: Math.round((current / total) * 100),
        message: trimmed
      };
    }
  }

  // Pattern 4: "Processing X of Y"
  const processingMatch = trimmed.match(/processing\s+(\d+)\s+of\s+(\d+)/i);
  if (processingMatch) {
    const current = parseInt(processingMatch[1]);
    const total = parseInt(processingMatch[2]);
    if (total > 0) {
      return {
        progress: Math.round((current / total) * 100),
        message: trimmed
      };
    }
  }

  // No progress pattern found, but still a valid message
  return {
    progress: null,
    message: trimmed
  };
}

/**
 * Wrapper function that auto-tracks any async operation
 *
 * @param {string} tool - Tool name (e.g., 'XLSTransfer')
 * @param {string} operation - Operation name (e.g., 'Create Dictionary')
 * @param {function} asyncFn - Async function to execute. Receives progress object.
 * @returns {Promise<any>} - Result of asyncFn
 *
 * @example
 * const result = await withProgress('XLSTransfer', 'Create Dict', async (progress) => {
 *   progress.update(25, 'Loading file...');
 *   await loadFile();
 *   progress.update(75, 'Processing...');
 *   await process();
 *   return { success: true };
 * });
 */
export async function withProgress(tool, operation, asyncFn) {
  const opId = generateOperationId();

  // Progress helper object passed to the function
  const progress = {
    id: opId,
    update: (percent, message) => {
      updateProgress(opId, percent, message);
    },
    log: (message) => {
      // Update with same progress, new message
      updateProgress(opId, null, message);
    }
  };

  // Start tracking
  startOperation(opId, tool, operation);

  try {
    // Execute the wrapped function
    const result = await asyncFn(progress);

    // Auto-complete on success
    const successMsg = result?.message || `${operation} completed successfully`;
    completeOperation(opId, true, successMsg);

    return result;
  } catch (error) {
    // Auto-complete on failure
    const errorMsg = error?.message || `${operation} failed`;
    completeOperation(opId, false, errorMsg);
    throw error;
  }
}

/**
 * Execute Python script with automatic progress tracking
 * Intercepts stderr for progress updates
 *
 * @param {string} scriptPath - Path to Python script
 * @param {Array} args - Script arguments
 * @param {Object} options - Options
 * @param {string} options.tool - Tool name
 * @param {string} options.operation - Operation name
 * @param {function} [options.onOutput] - Optional callback for each output line
 * @returns {Promise<Object>} - { success, output, error }
 *
 * @example
 * const result = await executePythonTracked(
 *   'xlstransfer/create_dictionary.py',
 *   [filePath],
 *   { tool: 'XLSTransfer', operation: 'Create Dictionary' }
 * );
 */
export async function executePythonTracked(scriptPath, args, options) {
  const { tool, operation, onOutput } = options;
  const opId = generateOperationId();

  // Check if we're in Electron
  const isElectron = typeof window !== 'undefined' && window.electron;
  if (!isElectron) {
    console.warn('executePythonTracked: Not in Electron environment');
    return { success: false, error: 'Not in Electron environment' };
  }

  // Start tracking
  startOperation(opId, tool, operation);

  // Set up progress handler for stderr
  const progressHandler = (data) => {
    if (data.type === 'stderr' && data.data) {
      const parsed = parseProgress(data.data);
      if (parsed) {
        if (parsed.progress !== null) {
          updateProgress(opId, parsed.progress, parsed.message);
        } else if (parsed.message) {
          // Just update message without changing progress
          updateProgress(opId, null, parsed.message);
        }

        // Call optional callback
        if (onOutput) {
          onOutput(parsed);
        }
      }
    }
  };

  // Subscribe to Python output
  window.electron.onPythonOutput(progressHandler);

  try {
    // Execute Python script
    const result = await window.electron.executePython({
      scriptPath,
      args
    });

    if (result.success) {
      completeOperation(opId, true, `${operation} completed`);
    } else {
      completeOperation(opId, false, result.error || `${operation} failed`);
    }

    return result;
  } catch (error) {
    completeOperation(opId, false, error.message);
    return { success: false, error: error.message };
  } finally {
    // Unsubscribe from Python output
    window.electron.offPythonOutput(progressHandler);
  }
}

/**
 * Create a manual tracker for complex operations
 * Use when you need fine-grained control
 *
 * @param {string} tool - Tool name
 * @param {string} operation - Operation name
 * @returns {Object} - Tracker object with start, update, complete, fail methods
 *
 * @example
 * const tracker = createTracker('XLSTransfer', 'Translate Excel');
 * tracker.start();
 * // ... do work ...
 * tracker.update(50, 'Halfway done');
 * // ... more work ...
 * tracker.complete('All done!');
 */
export function createTracker(tool, operation) {
  const opId = generateOperationId();
  let started = false;

  return {
    id: opId,

    start: () => {
      if (!started) {
        startOperation(opId, tool, operation);
        started = true;
      }
    },

    update: (percent, message) => {
      if (!started) {
        startOperation(opId, tool, operation);
        started = true;
      }
      updateProgress(opId, percent, message);
    },

    complete: (message) => {
      completeOperation(opId, true, message || `${operation} completed`);
    },

    fail: (message) => {
      completeOperation(opId, false, message || `${operation} failed`);
    }
  };
}

// Export everything
export default {
  parseProgress,
  withProgress,
  executePythonTracked,
  createTracker
};
