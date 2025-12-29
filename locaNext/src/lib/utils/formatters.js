/**
 * Formatters - Centralized formatting utilities
 *
 * Consolidates duplicate formatDate functions from:
 * - TMDataGrid.svelte
 * - TMManager.svelte
 * - TMViewer.svelte
 */

/**
 * Format date with full details (year, month, day, hour, minute)
 * @param {string|Date} dateStr - Date string or Date object
 * @returns {string} Formatted date or "-" if invalid
 */
export function formatDate(dateStr) {
  if (!dateStr) return "-";
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
}

/**
 * Format date without time (year, month, day only)
 * @param {string|Date} dateStr - Date string or Date object
 * @returns {string} Formatted date or "-" if invalid
 */
export function formatDateShort(dateStr) {
  if (!dateStr) return "-";
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  });
}

/**
 * Format date compactly (month, day - skips year if current year)
 * Used for inline metadata display
 * @param {string|Date} dateStr - Date string or Date object
 * @returns {string} Formatted date or empty string if invalid
 */
export function formatDateCompact(dateStr) {
  if (!dateStr) return "";
  const date = new Date(dateStr);
  const now = new Date();
  const isThisYear = date.getFullYear() === now.getFullYear();

  if (isThisYear) {
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  }
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}
