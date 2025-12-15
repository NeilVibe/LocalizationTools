/**
 * API Client for LocaNext
 * Connects to FastAPI backend server
 */

import { get } from 'svelte/store';
import { serverUrl, user, isAuthenticated } from '$lib/stores/app.js';

class APIClient {
  constructor() {
    this.baseURL = get(serverUrl);
    this.token = null;
  }

  /**
   * Set authentication token
   */
  setToken(token) {
    this.token = token;
    if (typeof window !== 'undefined') {
      localStorage.setItem('auth_token', token);
    }
  }

  /**
   * Get authentication token
   */
  getToken() {
    if (!this.token && typeof window !== 'undefined') {
      this.token = localStorage.getItem('auth_token');
    }
    return this.token;
  }

  /**
   * Clear authentication
   */
  clearAuth() {
    this.token = null;
    if (typeof window !== 'undefined') {
      localStorage.removeItem('auth_token');
      // Also clear remember me credentials
      localStorage.removeItem('locanext_remember');
      localStorage.removeItem('locanext_creds');
    }
    isAuthenticated.set(false);
    user.set(null);
  }

  /**
   * Make HTTP request
   */
  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const token = this.getToken();

    const headers = {
      'Content-Type': 'application/json',
      ...options.headers
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers
      });

      if (response.status === 401) {
        this.clearAuth();
        throw new Error('Unauthorized - please login');
      }

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(error.detail || `HTTP ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('API request failed:', error);
      throw error;
    }
  }

  // ==================== AUTH ENDPOINTS ====================

  /**
   * Login
   */
  async login(username, password) {
    const response = await this.request('/api/v2/auth/login', {
      method: 'POST',
      body: JSON.stringify({
        username,
        password
      })
    });

    this.setToken(response.access_token);
    user.set(response.user);
    isAuthenticated.set(true);

    return response;
  }

  /**
   * P33: Auto-login for SQLite offline mode
   * Uses auto_token from health endpoint - no credentials needed
   * @returns {boolean} - true if auto-login succeeded
   */
  async tryLocalModeLogin() {
    try {
      const health = await this.getHealth();

      // Check if we're in local mode (SQLite)
      if (health.local_mode && health.auto_token) {
        console.log('[Auth] SQLite local mode detected - auto-login enabled');

        // Set the token from health response
        this.setToken(health.auto_token);

        // Set user info for local mode
        user.set({
          user_id: 'LOCAL',
          username: 'LOCAL',
          role: 'admin',
          email: 'local@localhost'
        });
        isAuthenticated.set(true);

        console.log('[Auth] Local mode auto-login successful');
        return true;
      }

      return false;
    } catch (error) {
      console.error('[Auth] Local mode check failed:', error);
      return false;
    }
  }

  /**
   * Get current user
   */
  async getCurrentUser() {
    return await this.request('/api/v2/auth/me');
  }

  /**
   * Change password (self-service)
   * @param {string} currentPassword - Current password
   * @param {string} newPassword - New password
   * @param {string} confirmPassword - Confirm new password
   */
  async changePassword(currentPassword, newPassword, confirmPassword) {
    return await this.request('/api/v2/auth/me/password', {
      method: 'PUT',
      body: JSON.stringify({
        current_password: currentPassword,
        new_password: newPassword,
        confirm_password: confirmPassword
      })
    });
  }

  /**
   * Refresh token
   */
  async refreshToken() {
    return await this.request('/api/v2/auth/refresh', { method: 'POST' });
  }

  // ==================== LOG ENDPOINTS ====================

  /**
   * Submit log entry
   */
  async submitLog(logData) {
    return await this.request('/api/v2/logs/submit', {
      method: 'POST',
      body: JSON.stringify(logData)
    });
  }

  /**
   * Get logs with filters
   */
  async getLogs(filters = {}) {
    const params = new URLSearchParams(filters);
    return await this.request(`/api/v2/logs?${params}`);
  }

  /**
   * Get log by ID
   */
  async getLog(logId) {
    return await this.request(`/api/v2/logs/${logId}`);
  }

  /**
   * Delete log
   */
  async deleteLog(logId) {
    return await this.request(`/api/v2/logs/${logId}`, { method: 'DELETE' });
  }

  /**
   * Get user's logs
   */
  async getUserLogs(userId, filters = {}) {
    const params = new URLSearchParams(filters);
    return await this.request(`/api/v2/logs/user/${userId}?${params}`);
  }

  // ==================== SESSION ENDPOINTS ====================

  /**
   * Start new session
   */
  async startSession(sessionData) {
    return await this.request('/api/v2/sessions/start', {
      method: 'POST',
      body: JSON.stringify(sessionData)
    });
  }

  /**
   * End session
   */
  async endSession(sessionId) {
    return await this.request(`/api/v2/sessions/${sessionId}/end`, {
      method: 'POST'
    });
  }

  /**
   * Get active sessions
   */
  async getActiveSessions() {
    return await this.request('/api/v2/sessions/active');
  }

  /**
   * Get user sessions
   */
  async getUserSessions(userId) {
    return await this.request(`/api/v2/sessions/user/${userId}`);
  }

  // ==================== HEALTH CHECK ====================

  /**
   * Check server health (returns boolean)
   */
  async healthCheck() {
    try {
      const response = await fetch(`${this.baseURL}/health`);
      return response.ok;
    } catch {
      return false;
    }
  }

  /**
   * Get server health details (version, build info)
   */
  async getHealth() {
    const response = await fetch(`${this.baseURL}/health`);
    if (!response.ok) {
      throw new Error('Health check failed');
    }
    return await response.json();
  }

  // ==================== XLSTRANSFER API ====================

  /**
   * Create dictionary from Excel files
   * @param {FileList|File[]} files - Excel files to upload
   * @param {Object} selections - Optional selections {filename: {sheetName: {kr_column, trans_column}}}
   * @returns {Promise} - Dictionary creation result
   */
  async xlsTransferCreateDictionary(files, selections = null) {
    const formData = new FormData();

    // Add files to FormData
    for (let i = 0; i < files.length; i++) {
      formData.append('files', files[i]);
    }

    // Add selections if provided (for Upload Settings Modal)
    if (selections) {
      formData.append('selections', JSON.stringify(selections));
    }

    const token = this.getToken();
    const headers = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${this.baseURL}/api/v2/xlstransfer/test/create-dictionary`, {
      method: 'POST',
      headers,
      body: formData
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return await response.json();
  }

  /**
   * Load existing dictionary
   * @returns {Promise} - Load result
   */
  async xlsTransferLoadDictionary() {
    return await this.request('/api/v2/xlstransfer/test/load-dictionary', {
      method: 'POST',
      body: JSON.stringify({})
    });
  }

  /**
   * Translate text using loaded dictionary
   * @param {string} text - Text to translate
   * @param {number} threshold - Similarity threshold (0-1)
   * @returns {Promise} - Translation result
   */
  async xlsTransferTranslateText(text, threshold = 0.99) {
    return await this.request('/api/v2/xlstransfer/test/translate-text', {
      method: 'POST',
      body: JSON.stringify({ text, threshold })
    });
  }

  /**
   * Translate file using loaded dictionary
   * @param {File} file - File to translate (.txt or .xlsx)
   * @param {number} threshold - Similarity threshold (0-1)
   * @returns {Promise} - Translation result with download URL
   */
  async xlsTransferTranslateFile(file, threshold = 0.99) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('threshold', threshold.toString());

    const token = this.getToken();
    const headers = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${this.baseURL}/api/v2/xlstransfer/test/translate-file`, {
      method: 'POST',
      headers,
      body: formData
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return await response.json();
  }

  /**
   * Get sheet names from an Excel file
   * @param {File} file - Excel file
   * @returns {Promise} - Sheet names
   */
  async xlsTransferGetSheets(file) {
    const formData = new FormData();
    formData.append('file', file);

    const token = this.getToken();
    const headers = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${this.baseURL}/api/v2/xlstransfer/test/get-sheets`, {
      method: 'POST',
      headers,
      body: formData
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return await response.json();
  }

  /**
   * Create dictionary with selections (full upload settings workflow)
   * @param {Object} selections - File/sheet/column selections
   * @returns {Promise} - Dictionary creation result
   */
  async xlsTransferCreateDictionaryWithSelections(files, selections) {
    const formData = new FormData();

    // Add files
    for (let i = 0; i < files.length; i++) {
      formData.append('files', files[i]);
    }

    // Add selections as JSON
    formData.append('selections', JSON.stringify(selections));

    const token = this.getToken();
    const headers = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${this.baseURL}/api/v2/xlstransfer/test/create-dictionary-with-selections`, {
      method: 'POST',
      headers,
      body: formData
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return await response.json();
  }

  /**
   * Translate Excel files with sheet/column selections
   * @param {FileList|File[]} files - Excel files to translate
   * @param {Object} selections - Sheet/column selections {filename: {sheetName: {kr_column, trans_column}}}
   * @param {number} threshold - Similarity threshold (0-1)
   * @returns {Promise<Blob>} - Translated Excel file as blob for download
   */
  async xlsTransferTranslateExcel(files, selections, threshold = 0.99) {
    const formData = new FormData();

    // Add files to FormData
    for (let i = 0; i < files.length; i++) {
      formData.append('files', files[i]);
    }

    // Add selections as JSON
    formData.append('selections', JSON.stringify(selections));

    // Add threshold
    formData.append('threshold', threshold.toString());

    const token = this.getToken();
    const headers = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${this.baseURL}/api/v2/xlstransfer/test/translate-excel`, {
      method: 'POST',
      headers,
      body: formData
    });

    // Handle 202 Accepted (async operation)
    if (response.status === 202) {
      const data = await response.json();
      return {
        async: true,
        operation_id: data.operation_id,
        operation_name: data.operation_name,
        message: data.message
      };
    }

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    // Return blob for file download (sync operations only)
    return await response.blob();
  }
}

// Export singleton instance
export const api = new APIClient();
