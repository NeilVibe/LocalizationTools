/**
 * Shared API Utilities
 * Centralizes auth headers and API base URL to avoid code duplication
 *
 * Previously: getAuthHeaders() was duplicated in 11 Svelte files
 * Now: Import from this single source
 */

import { get } from 'svelte/store';
import { serverUrl } from '$lib/stores/app.js';

/**
 * Get authentication headers for API requests
 * @returns {Object} Headers object with Authorization if token exists
 */
export function getAuthHeaders() {
  const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
  return token ? { 'Authorization': `Bearer ${token}` } : {};
}

/**
 * Get the current API base URL
 * @returns {string} The server URL (e.g., 'http://localhost:8888')
 */
export function getApiBase() {
  return get(serverUrl);
}

/**
 * Make an authenticated fetch request
 * @param {string} endpoint - API endpoint (e.g., '/api/ldm/files')
 * @param {Object} options - Fetch options
 * @returns {Promise<Response>}
 */
export async function apiFetch(endpoint, options = {}) {
  const base = getApiBase();
  const url = endpoint.startsWith('http') ? endpoint : `${base}${endpoint}`;

  const headers = {
    ...getAuthHeaders(),
    ...options.headers
  };

  return fetch(url, {
    ...options,
    headers
  });
}

/**
 * Make an authenticated JSON POST request
 * @param {string} endpoint - API endpoint
 * @param {Object} data - JSON data to send
 * @returns {Promise<Response>}
 */
export async function apiPost(endpoint, data) {
  return apiFetch(endpoint, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(data)
  });
}

/**
 * Make an authenticated JSON PATCH request
 * @param {string} endpoint - API endpoint
 * @param {Object} data - JSON data to send
 * @returns {Promise<Response>}
 */
export async function apiPatch(endpoint, data) {
  return apiFetch(endpoint, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(data)
  });
}
