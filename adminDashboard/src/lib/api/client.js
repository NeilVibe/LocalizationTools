/**
 * Admin Dashboard API Client
 * Connects to FastAPI backend for admin operations
 */

const API_BASE_URL = 'http://localhost:8888/api/v2';

class AdminAPIClient {
  constructor() {
    this.token = null;
    this.loadToken();
  }

  loadToken() {
    if (typeof window !== 'undefined') {
      this.token = localStorage.getItem('admin_token');
    }
  }

  saveToken(token) {
    this.token = token;
    if (typeof window !== 'undefined') {
      localStorage.setItem('admin_token', token);
    }
  }

  clearToken() {
    this.token = null;
    if (typeof window !== 'undefined') {
      localStorage.removeItem('admin_token');
    }
  }

  getHeaders() {
    const headers = { 'Content-Type': 'application/json' };
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }
    return headers;
  }

  async request(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    const config = {
      ...options,
      headers: { ...this.getHeaders(), ...options.headers }
    };

    try {
      const response = await fetch(url, config);
      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Request failed' }));
        throw new Error(error.detail || `HTTP ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error('API Request failed:', error);
      throw error;
    }
  }

  // AUTH
  async login(username, password) {
    const data = await this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password })
    });
    if (data.access_token) this.saveToken(data.access_token);
    return data;
  }

  async logout() {
    try {
      await this.request('/auth/logout', { method: 'POST' });
    } finally {
      this.clearToken();
    }
  }

  async getCurrentUser() {
    return await this.request('/auth/me');
  }

  // USERS
  async getAllUsers() { return await this.request('/auth/users'); }
  async getUser(userId) { return await this.request(`/auth/users/${userId}`); }

  // Admin User Management
  async adminCreateUser(userData) {
    return await this.request('/auth/admin/users', {
      method: 'POST',
      body: JSON.stringify(userData)
    });
  }

  async adminUpdateUser(userId, userData) {
    return await this.request(`/auth/admin/users/${userId}`, {
      method: 'PUT',
      body: JSON.stringify(userData)
    });
  }

  async adminResetPassword(userId, newPassword, mustChangePassword = true) {
    return await this.request(`/auth/admin/users/${userId}/reset-password`, {
      method: 'PUT',
      body: JSON.stringify({ new_password: newPassword, must_change_password: mustChangePassword })
    });
  }

  async adminDeleteUser(userId) {
    return await this.request(`/auth/admin/users/${userId}`, {
      method: 'DELETE'
    });
  }

  async activateUser(userId) {
    return await this.request(`/auth/users/${userId}/activate`, {
      method: 'PUT'
    });
  }

  async deactivateUser(userId) {
    return await this.request(`/auth/users/${userId}/deactivate`, {
      method: 'PUT'
    });
  }

  // LOGS
  async getAllLogs(params = {}) {
    const query = new URLSearchParams(params).toString();
    return await this.request(`/logs/recent?${query}`);
  }

  async getUserLogs(userId, params = {}) {
    const query = new URLSearchParams(params).toString();
    return await this.request(`/logs/user/${userId}?${query}`);
  }

  async getErrors(params = {}) {
    const query = new URLSearchParams(params).toString();
    return await this.request(`/logs/errors?${query}`);
  }

  // STATS (OLD - keeping for backward compatibility)
  async getStats(params = {}) {
    return await this.request('/logs/stats/summary');
  }

  async getToolStats() {
    return await this.request('/logs/stats/by-tool');
  }

  // DASHBOARD STATISTICS (NEW - comprehensive analytics)
  async getOverviewStats() {
    return await this.request('/admin/stats/overview');
  }

  async getDailyStats(days = 30) {
    return await this.request(`/admin/stats/daily?days=${days}`);
  }

  async getWeeklyStats(weeks = 12) {
    return await this.request(`/admin/stats/weekly?weeks=${weeks}`);
  }

  async getMonthlyStats(months = 12) {
    return await this.request(`/admin/stats/monthly?months=${months}`);
  }

  async getToolPopularity(days = 30) {
    return await this.request(`/admin/stats/tools/popularity?days=${days}`);
  }

  async getFunctionStats(toolName, days = 30) {
    return await this.request(`/admin/stats/tools/${toolName}/functions?days=${days}`);
  }

  async getFastestFunctions(limit = 10, days = 30) {
    return await this.request(`/admin/stats/performance/fastest?limit=${limit}&days=${days}`);
  }

  async getSlowestFunctions(limit = 10, days = 30) {
    return await this.request(`/admin/stats/performance/slowest?limit=${limit}&days=${days}`);
  }

  async getErrorRate(days = 30) {
    return await this.request(`/admin/stats/errors/rate?days=${days}`);
  }

  async getTopErrors(limit = 10, days = 30) {
    return await this.request(`/admin/stats/errors/top?limit=${limit}&days=${days}`);
  }

  async getServerLogs(lines = 100) {
    return await this.request(`/admin/stats/server-logs?lines=${lines}`);
  }

  // TEAM & LANGUAGE ANALYTICS
  async getTeamAnalytics(days = 30) {
    return await this.request(`/admin/stats/analytics/by-team?days=${days}`);
  }

  async getLanguageAnalytics(days = 30) {
    return await this.request(`/admin/stats/analytics/by-language?days=${days}`);
  }

  async getUserRankingsWithProfile(days = 30, limit = 20) {
    return await this.request(`/admin/stats/analytics/user-rankings?days=${days}&limit=${limit}`);
  }

  // RANKINGS
  async getUserRankings(period = 'monthly', limit = 20) {
    return await this.request(`/admin/rankings/users?period=${period}&limit=${limit}`);
  }

  async getUserRankingsByTime(period = 'monthly', limit = 20) {
    return await this.request(`/admin/rankings/users/by-time?period=${period}&limit=${limit}`);
  }

  async getAppRankings(period = 'all_time') {
    return await this.request(`/admin/rankings/apps?period=${period}`);
  }

  async getFunctionRankings(period = 'monthly', limit = 20, toolName = null) {
    const params = new URLSearchParams({ period, limit });
    if (toolName) params.append('tool_name', toolName);
    return await this.request(`/admin/rankings/functions?${params.toString()}`);
  }

  async getFunctionRankingsByTime(period = 'monthly', limit = 20, toolName = null) {
    const params = new URLSearchParams({ period, limit });
    if (toolName) params.append('tool_name', toolName);
    return await this.request(`/admin/rankings/functions/by-time?${params.toString()}`);
  }

  async getTopRankings(period = 'all_time') {
    return await this.request(`/admin/rankings/top?period=${period}`);
  }

  // SESSIONS
  async getActiveSessions() {
    return await this.request('/sessions/active');
  }

  async getUserSessions(userId) {
    return await this.request(`/sessions/user/${userId}`);
  }

  // HEALTH
  async getSystemHealth() {
    const response = await fetch('http://localhost:8888/health');
    return await response.json();
  }

  // ============================================================================
  // TELEMETRY (Central Server Monitoring)
  // ============================================================================

  // Overview
  async getTelemetryOverview() {
    return await this.request('/admin/telemetry/overview');
  }

  // Installations
  async getInstallations(includeInactive = false) {
    return await this.request(`/admin/telemetry/installations?include_inactive=${includeInactive}`);
  }

  async getInstallationDetail(installationId) {
    return await this.request(`/admin/telemetry/installations/${installationId}`);
  }

  // Sessions
  async getTelemetrySessions(activeOnly = true, days = 7, limit = 100) {
    return await this.request(`/admin/telemetry/sessions?active_only=${activeOnly}&days=${days}&limit=${limit}`);
  }

  // Logs
  async getRemoteLogs(installationId = null, level = null, hours = 24, limit = 100) {
    const params = new URLSearchParams({ hours, limit });
    if (installationId) params.append('installation_id', installationId);
    if (level) params.append('level', level);
    return await this.request(`/admin/telemetry/logs?${params.toString()}`);
  }

  async getRemoteErrorLogs(hours = 24, limit = 100) {
    return await this.request(`/admin/telemetry/logs/errors?hours=${hours}&limit=${limit}`);
  }

  // Statistics
  async getDailyTelemetryStats(days = 30) {
    return await this.request(`/admin/telemetry/stats/daily?days=${days}`);
  }

  async getStatsByInstallation(days = 30) {
    return await this.request(`/admin/telemetry/stats/by-installation?days=${days}`);
  }
}

export const adminAPI = new AdminAPIClient();
export default adminAPI;
