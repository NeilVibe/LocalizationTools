/**
 * Clipboard Store - EXPLORER-001
 *
 * Manages clipboard state for file/folder copy/cut operations.
 * State persists across folder navigation, clears on:
 * - New copy/cut operation
 * - Paste operation
 * - Escape key press
 */

import { writable, get } from 'svelte/store';

// Clipboard state
const initialState = {
  items: [],      // Array of { type, id, name, format, ... }
  operation: null // 'copy' | 'cut' | null
};

// Create the store
const clipboardStore = writable(initialState);

/**
 * Copy items to clipboard
 * @param {Array} items - Items to copy
 */
export function copyToClipboard(items) {
  if (!items || items.length === 0) return;
  clipboardStore.set({
    items: [...items],
    operation: 'copy'
  });
}

/**
 * Cut items to clipboard (for move operation)
 * @param {Array} items - Items to cut
 */
export function cutToClipboard(items) {
  if (!items || items.length === 0) return;
  clipboardStore.set({
    items: [...items],
    operation: 'cut'
  });
}

/**
 * Get current clipboard contents
 * @returns {{ items: Array, operation: string|null }}
 */
export function getClipboard() {
  return get(clipboardStore);
}

/**
 * Clear clipboard
 */
export function clearClipboard() {
  clipboardStore.set(initialState);
}

/**
 * Check if an item is in clipboard (for cut operation visual feedback)
 * @param {number} itemId - Item ID to check
 * @returns {boolean}
 */
export function isItemCut(itemId) {
  const state = get(clipboardStore);
  if (state.operation !== 'cut') return false;
  return state.items.some(item => item.id === itemId);
}

/**
 * Check if clipboard has items
 * @returns {boolean}
 */
export function hasClipboardItems() {
  const state = get(clipboardStore);
  return state.items.length > 0;
}

/**
 * Get clipboard operation type
 * @returns {'copy'|'cut'|null}
 */
export function getClipboardOperation() {
  const state = get(clipboardStore);
  return state.operation;
}

// Export the store for reactive access
export const clipboard = clipboardStore;
