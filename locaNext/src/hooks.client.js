/**
 * SvelteKit Client Hooks
 *
 * NOTE: The main routing fix for Electron is in electron/main.js
 * using a custom app:// protocol. This file is kept minimal.
 */

/**
 * Handle client-side errors
 */
export function handleError({ error, event, status, message }) {
  console.error('[hooks.client] Error:', status, message, error);
  return {
    message: message || 'An error occurred'
  };
}
