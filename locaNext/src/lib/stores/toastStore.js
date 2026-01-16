/**
 * Global Toast Store - BUG-016 Task Manager Toast Notifications
 *
 * Provides global toast notifications that appear on any page when
 * Task Manager operations start/complete/fail.
 *
 * Usage:
 *   import { toasts, addToast, removeToast } from '$lib/stores/toastStore.js';
 */

import { writable, get } from 'svelte/store';

// Store for active toasts
const toasts = writable([]);

// Auto-increment ID for toasts
let nextId = 1;

// Default toast duration in ms
const DEFAULT_DURATION = 4000;

// Max visible toasts at once
const MAX_TOASTS = 3;

// Deduplication - track recent toast signatures
const recentToasts = new Map(); // signature -> timestamp
const DEDUPE_WINDOW = 2000; // Don't show same toast within 2 seconds

/**
 * Add a new toast notification
 * @param {Object} options - Toast options
 * @param {string} options.message - Toast message
 * @param {string} options.kind - Toast kind: 'success', 'error', 'warning', 'info'
 * @param {string} options.title - Toast title (optional, defaults based on kind)
 * @param {number} options.duration - Duration in ms (optional, defaults to 4000, 0 = no auto-dismiss)
 * @returns {number} Toast ID or -1 if deduplicated
 */
export function addToast({ message, kind = 'info', title = null, duration = DEFAULT_DURATION }) {
  // Deduplicate - check if same toast was shown recently
  const signature = `${kind}:${title}:${message}`;
  const now = Date.now();
  const lastShown = recentToasts.get(signature);
  if (lastShown && (now - lastShown) < DEDUPE_WINDOW) {
    return -1; // Skip duplicate
  }
  recentToasts.set(signature, now);

  // Clean old entries from dedup map
  for (const [sig, ts] of recentToasts) {
    if (now - ts > DEDUPE_WINDOW * 2) {
      recentToasts.delete(sig);
    }
  }

  const id = nextId++;

  // Default titles based on kind
  const defaultTitles = {
    success: 'Success',
    error: 'Error',
    warning: 'Warning',
    info: 'Info'
  };

  const toast = {
    id,
    message,
    kind,
    title: title || defaultTitles[kind] || 'Notification',
    timestamp: now
  };

  toasts.update(t => {
    const updated = [...t, toast];
    // Limit to MAX_TOASTS - remove oldest if over limit
    if (updated.length > MAX_TOASTS) {
      return updated.slice(-MAX_TOASTS);
    }
    return updated;
  });

  // Auto-remove after duration (unless duration is 0)
  if (duration > 0) {
    setTimeout(() => {
      removeToast(id);
    }, duration);
  }

  return id;
}

/**
 * Remove a toast by ID
 * @param {number} id - Toast ID
 */
export function removeToast(id) {
  toasts.update(t => t.filter(toast => toast.id !== id));
}

/**
 * Clear all toasts
 */
export function clearToasts() {
  toasts.set([]);
}

/**
 * Convenience functions for common toast types
 */
export const toast = {
  success: (message, title = 'Success') => addToast({ message, kind: 'success', title }),
  error: (message, title = 'Error') => addToast({ message, kind: 'error', title }),
  warning: (message, title = 'Warning') => addToast({ message, kind: 'warning', title }),
  info: (message, title = 'Info') => addToast({ message, kind: 'info', title }),

  // Task Manager specific toasts (minimal - check Task Manager for details)
  operationStarted: (operationName, toolName) => addToast({
    message: operationName,
    kind: 'info',
    title: `${toolName}`,
    duration: 2000  // Very short - just a heads up
  }),

  operationCompleted: (operationName, toolName, duration) => addToast({
    message: duration ? `${operationName} (${duration})` : operationName,
    kind: 'success',
    title: `${toolName}`,
    duration: 3000  // Brief success notification
  }),

  operationFailed: (operationName, toolName, error) => addToast({
    message: error ? `${error}` : operationName,
    kind: 'error',
    title: `${toolName} Failed`,
    duration: 6000  // Longer for errors - user needs to see this
  })
};

// Export the store for subscription
export { toasts };

export default toast;
