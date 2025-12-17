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
const DEFAULT_DURATION = 5000;

/**
 * Add a new toast notification
 * @param {Object} options - Toast options
 * @param {string} options.message - Toast message
 * @param {string} options.kind - Toast kind: 'success', 'error', 'warning', 'info'
 * @param {string} options.title - Toast title (optional, defaults based on kind)
 * @param {number} options.duration - Duration in ms (optional, defaults to 5000, 0 = no auto-dismiss)
 * @returns {number} Toast ID
 */
export function addToast({ message, kind = 'info', title = null, duration = DEFAULT_DURATION }) {
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
    timestamp: Date.now()
  };

  toasts.update(t => [...t, toast]);

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

  // Task Manager specific toasts
  operationStarted: (operationName, toolName) => addToast({
    message: `${operationName}`,
    kind: 'info',
    title: `${toolName} Started`,
    duration: 3000  // Shorter duration for start notifications
  }),

  operationCompleted: (operationName, toolName, duration) => addToast({
    message: duration ? `${operationName} (${duration})` : operationName,
    kind: 'success',
    title: `${toolName} Complete`,
    duration: 5000
  }),

  operationFailed: (operationName, toolName, error) => addToast({
    message: error ? `${operationName}: ${error}` : operationName,
    kind: 'error',
    title: `${toolName} Failed`,
    duration: 8000  // Longer duration for errors
  })
};

// Export the store for subscription
export { toasts };

export default toast;
