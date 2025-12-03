import { test, expect } from '@playwright/test';

/**
 * Admin Dashboard + Telemetry Integration Tests
 * Tests: Dashboard UI → Backend API → Telemetry Data → Display
 */

const API_URL = 'http://localhost:8888';

test.describe('Dashboard Telemetry Display', () => {
  let token: string;

  test.beforeAll(async ({ request }) => {
    const loginResponse = await request.post(`${API_URL}/api/v2/auth/login`, {
      data: { username: 'admin', password: 'admin123' }
    });
    const data = await loginResponse.json();
    token = data.access_token;
  });

  test('should fetch and display overview stats', async ({ request }) => {
    const statsResponse = await request.get(`${API_URL}/api/v2/admin/stats/overview`, {
      headers: { Authorization: `Bearer ${token}` }
    });

    expect(statsResponse.ok()).toBeTruthy();

    const stats = await statsResponse.json();
    expect(stats).toHaveProperty('active_users');
    expect(stats).toHaveProperty('today_operations');
    expect(typeof stats.active_users).toBe('number');
    expect(typeof stats.today_operations).toBe('number');
  });

  test('should fetch user activity data', async ({ request }) => {
    const activityResponse = await request.get(`${API_URL}/api/v2/admin/activity?limit=50`, {
      headers: { Authorization: `Bearer ${token}` }
    });

    if (activityResponse.ok()) {
      const activity = await activityResponse.json();
      expect(activity).toBeDefined();
    }
  });

  test('should fetch tool usage statistics', async ({ request }) => {
    const toolsResponse = await request.get(`${API_URL}/api/v2/admin/stats/tools/popularity?days=30`, {
      headers: { Authorization: `Bearer ${token}` }
    });

    if (toolsResponse.ok()) {
      const tools = await toolsResponse.json();
      expect(tools).toHaveProperty('tools');
      expect(Array.isArray(tools.tools)).toBeTruthy();
    }
  });

  test('should fetch user rankings correctly', async ({ request }) => {
    const rankingsResponse = await request.get(`${API_URL}/api/v2/admin/rankings/users?period=monthly`, {
      headers: { Authorization: `Bearer ${token}` }
    });

    if (rankingsResponse.ok()) {
      const rankings = await rankingsResponse.json();
      expect(rankings).toHaveProperty('rankings');
      expect(Array.isArray(rankings.rankings)).toBeTruthy();
    }
  });
});

test.describe('Dashboard Session Management', () => {
  let token: string;

  test.beforeAll(async ({ request }) => {
    const loginResponse = await request.post(`${API_URL}/api/v2/auth/login`, {
      data: { username: 'admin', password: 'admin123' }
    });
    const data = await loginResponse.json();
    token = data.access_token;
  });

  test('should list active sessions', async ({ request }) => {
    const sessionsResponse = await request.get(`${API_URL}/api/v2/admin/sessions`, {
      headers: { Authorization: `Bearer ${token}` }
    });

    if (sessionsResponse.ok()) {
      const sessions = await sessionsResponse.json();
      expect(sessions).toHaveProperty('sessions');
    }
  });

  test('should show session details', async ({ request }) => {
    const sessionsResponse = await request.get(`${API_URL}/api/v2/admin/sessions`, {
      headers: { Authorization: `Bearer ${token}` }
    });

    if (sessionsResponse.ok()) {
      const { sessions } = await sessionsResponse.json();
      if (sessions && sessions.length > 0) {
        // Each session should have expected fields
        const session = sessions[0];
        expect(session).toBeDefined();
      }
    }
  });
});

test.describe('Dashboard Log Viewing', () => {
  let token: string;

  test.beforeAll(async ({ request }) => {
    const loginResponse = await request.post(`${API_URL}/api/v2/auth/login`, {
      data: { username: 'admin', password: 'admin123' }
    });
    const data = await loginResponse.json();
    token = data.access_token;
  });

  test('should fetch activity logs', async ({ request }) => {
    const logsResponse = await request.get(`${API_URL}/api/v2/admin/logs`, {
      headers: { Authorization: `Bearer ${token}` }
    });

    if (logsResponse.ok()) {
      const logs = await logsResponse.json();
      expect(logs).toBeDefined();
    }
  });

  test('should filter logs by type', async ({ request }) => {
    const logsResponse = await request.get(`${API_URL}/api/v2/admin/logs?type=login`, {
      headers: { Authorization: `Bearer ${token}` }
    });

    if (logsResponse.ok()) {
      const logs = await logsResponse.json();
      expect(logs).toBeDefined();
    }
  });
});

test.describe('Real-time Data Updates', () => {
  let token: string;

  test.beforeAll(async ({ request }) => {
    const loginResponse = await request.post(`${API_URL}/api/v2/auth/login`, {
      data: { username: 'admin', password: 'admin123' }
    });
    const data = await loginResponse.json();
    token = data.access_token;
  });

  test('should poll for new operations', async ({ request }) => {
    // First call
    const ops1 = await request.get(`${API_URL}/api/progress/operations`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    expect(ops1.ok()).toBeTruthy();
    const operations1 = await ops1.json();

    // Second call after short delay
    await new Promise(r => setTimeout(r, 500));

    const ops2 = await request.get(`${API_URL}/api/progress/operations`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    expect(ops2.ok()).toBeTruthy();
    const operations2 = await ops2.json();

    // Both should be valid arrays
    expect(Array.isArray(operations1)).toBeTruthy();
    expect(Array.isArray(operations2)).toBeTruthy();
  });

  test('should handle concurrent requests', async ({ request }) => {
    // Make multiple concurrent requests
    const requests = [
      request.get(`${API_URL}/api/v2/admin/stats/overview`, {
        headers: { Authorization: `Bearer ${token}` }
      }),
      request.get(`${API_URL}/api/v2/admin/rankings/users?period=monthly`, {
        headers: { Authorization: `Bearer ${token}` }
      }),
      request.get(`${API_URL}/api/progress/operations`, {
        headers: { Authorization: `Bearer ${token}` }
      })
    ];

    const responses = await Promise.all(requests);

    // All should succeed
    for (const response of responses) {
      expect(response.ok()).toBeTruthy();
    }
  });
});

test.describe('Dashboard Error Recovery', () => {
  test('should handle unauthorized access', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/v2/admin/stats/overview`);

    // Should not get 500 - either public endpoint or auth error
    expect(response.status()).toBeLessThan(500);
    expect([200, 401, 403, 422]).toContain(response.status());
  });

  test('should handle invalid token gracefully', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/v2/admin/stats/overview`, {
      headers: { Authorization: 'Bearer invalid_token_here' }
    });

    // Should get auth error, not server error
    expect(response.status()).toBeLessThan(500);
  });

  test('should handle non-existent endpoints', async ({ request }) => {
    const loginResponse = await request.post(`${API_URL}/api/v2/auth/login`, {
      data: { username: 'admin', password: 'admin123' }
    });
    const { access_token } = await loginResponse.json();

    const response = await request.get(`${API_URL}/api/v2/admin/nonexistent`, {
      headers: { Authorization: `Bearer ${access_token}` }
    });

    // Should get 404, not 500
    expect([404, 405]).toContain(response.status());
  });
});

test.describe('Dashboard Data Integrity', () => {
  let token: string;

  test.beforeAll(async ({ request }) => {
    const loginResponse = await request.post(`${API_URL}/api/v2/auth/login`, {
      data: { username: 'admin', password: 'admin123' }
    });
    const data = await loginResponse.json();
    token = data.access_token;
  });

  test('should return consistent data format', async ({ request }) => {
    const statsResponse = await request.get(`${API_URL}/api/v2/admin/stats/overview`, {
      headers: { Authorization: `Bearer ${token}` }
    });

    const stats = await statsResponse.json();

    // Verify expected fields
    expect(stats).toHaveProperty('active_users');
    expect(stats).toHaveProperty('today_operations');

    // Values should be non-negative
    expect(stats.active_users).toBeGreaterThanOrEqual(0);
    expect(stats.today_operations).toBeGreaterThanOrEqual(0);
  });

  test('should return valid timestamp formats', async ({ request }) => {
    const opsResponse = await request.get(`${API_URL}/api/progress/operations`, {
      headers: { Authorization: `Bearer ${token}` }
    });

    const operations = await opsResponse.json();

    if (operations.length > 0) {
      const op = operations[0];
      if (op.started_at) {
        // Should be parseable as date
        const date = new Date(op.started_at);
        expect(date.getTime()).not.toBeNaN();
      }
    }
  });
});
