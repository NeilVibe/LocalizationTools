/**
 * Undo/Redo Stack for Explorer operations (EXPLORER-007)
 *
 * Tracks reversible actions like:
 * - Move (can undo by moving back)
 * - Rename (can undo by renaming back)
 * - Delete (can undo via Recycle Bin restore)
 * - Copy (can undo by deleting the copy)
 */

import { writable, get } from 'svelte/store';
import { logger } from '$lib/utils/logger.js';

const MAX_UNDO_STEPS = 50;

// Undo stack - stores completed actions that can be undone
const undoStack = writable([]);

// Redo stack - stores undone actions that can be redone
const redoStack = writable([]);

// Track if we're currently undoing/redoing to prevent infinite loops
let isProcessing = false;

/**
 * Action types for undo/redo
 */
export const ActionTypes = {
  MOVE: 'move',
  RENAME: 'rename',
  DELETE: 'delete',
  COPY: 'copy',
  CREATE: 'create'
};

/**
 * Push a new action onto the undo stack
 * @param {Object} action - The action to push
 * @param {string} action.type - ActionTypes value
 * @param {Object} action.data - Action-specific data for undo/redo
 * @param {Function} action.undo - Function to undo this action
 * @param {Function} action.redo - Function to redo this action
 * @param {string} action.description - Human-readable description
 */
export function pushAction(action) {
  if (isProcessing) return;

  undoStack.update(stack => {
    const newStack = [...stack, action].slice(-MAX_UNDO_STEPS);
    return newStack;
  });

  // Clear redo stack on new action
  redoStack.set([]);

  logger.debug('Action pushed to undo stack', { type: action.type, description: action.description });
}

/**
 * Undo the last action
 * @returns {Promise<boolean>} True if undo was successful
 */
export async function undo() {
  const stack = get(undoStack);
  if (stack.length === 0) {
    logger.info('Nothing to undo');
    return false;
  }

  isProcessing = true;
  try {
    const action = stack[stack.length - 1];

    if (typeof action.undo === 'function') {
      await action.undo();
      logger.success(`Undo: ${action.description}`);
    }

    // Move action to redo stack
    undoStack.update(s => s.slice(0, -1));
    redoStack.update(s => [...s, action]);

    return true;
  } catch (err) {
    logger.error('Undo failed', { error: err.message });
    return false;
  } finally {
    isProcessing = false;
  }
}

/**
 * Redo the last undone action
 * @returns {Promise<boolean>} True if redo was successful
 */
export async function redo() {
  const stack = get(redoStack);
  if (stack.length === 0) {
    logger.info('Nothing to redo');
    return false;
  }

  isProcessing = true;
  try {
    const action = stack[stack.length - 1];

    if (typeof action.redo === 'function') {
      await action.redo();
      logger.success(`Redo: ${action.description}`);
    }

    // Move action back to undo stack
    redoStack.update(s => s.slice(0, -1));
    undoStack.update(s => [...s, action]);

    return true;
  } catch (err) {
    logger.error('Redo failed', { error: err.message });
    return false;
  } finally {
    isProcessing = false;
  }
}

/**
 * Check if undo is available
 */
export function canUndo() {
  return get(undoStack).length > 0;
}

/**
 * Check if redo is available
 */
export function canRedo() {
  return get(redoStack).length > 0;
}

/**
 * Get the description of the action that would be undone
 */
export function getUndoDescription() {
  const stack = get(undoStack);
  if (stack.length === 0) return null;
  return stack[stack.length - 1].description;
}

/**
 * Get the description of the action that would be redone
 */
export function getRedoDescription() {
  const stack = get(redoStack);
  if (stack.length === 0) return null;
  return stack[stack.length - 1].description;
}

/**
 * Clear both stacks
 */
export function clearStacks() {
  undoStack.set([]);
  redoStack.set([]);
}

/**
 * Export stores for reactive bindings
 */
export { undoStack, redoStack };
