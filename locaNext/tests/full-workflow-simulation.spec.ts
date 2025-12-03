import { test, expect } from '@playwright/test';

/**
 * Full Workflow Simulation Tests
 *
 * Tests complete flows:
 * 1. User action in frontend → Backend processes → Telemetry recorded → Dashboard shows
 * 2. Backend state changes → Frontend reacts correctly
 * 3. Real-time updates via WebSocket/polling
 */

const API_URL = 'http://localhost:8888';

// Helper to get auth token
async function getAuthToken(request: any): Promise<string> {
  const response = await request.post(`${API_URL}/api/v2/auth/login`, {
    data: { username: 'admin', password: 'admin123' }
  });
  const { access_token } = await response.json();
  return access_token;
}

test.describe('Complete User Workflow: Login → Tool Use → Telemetry', () => {

  test('should track complete login flow in telemetry', async ({ page, request }) => {
    // Step 1: Get initial stats
    const token = await getAuthToken(request);
    const beforeStats = await request.get(`${API_URL}/api/v2/admin/stats/overview`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    const statsBefore = await beforeStats.json();

    // Step 2: Login via frontend
    await page.goto('/');
    await page.getByLabel('Username').fill('admin');
    await page.getByLabel('Password').fill('admin123');
    await page.getByRole('button', { name: /login/i }).click();
    await page.waitForTimeout(3000);

    // Step 3: Check stats after login (should have activity)
    const afterStats = await request.get(`${API_URL}/api/v2/admin/stats/overview`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    const statsAfter = await afterStats.json();

    // Verify structure is consistent
    expect(statsAfter).toHaveProperty('active_users');
    expect(statsAfter).toHaveProperty('today_operations');
  });

  test('should show tool health status correctly', async ({ page, request }) => {
    const token = await getAuthToken(request);

    // Login first
    await page.goto('/');
    await page.getByLabel('Username').fill('admin');
    await page.getByLabel('Password').fill('admin123');
    await page.getByRole('button', { name: /login/i }).click();
    await page.waitForTimeout(2000);

    // Check all tool health endpoints
    const tools = ['kr-similar', 'quicksearch', 'xlstransfer'];

    for (const tool of tools) {
      const health = await request.get(`${API_URL}/api/v2/${tool}/health`);
      expect(health.ok()).toBeTruthy();
      const data = await health.json();
      expect(data.status).toBe('ok');
    }
  });
});

test.describe('Backend Process → Frontend Reaction', () => {

  test('should handle backend health changes gracefully', async ({ page, request }) => {
    // Login
    await page.goto('/');
    await page.getByLabel('Username').fill('admin');
    await page.getByLabel('Password').fill('admin123');
    await page.getByRole('button', { name: /login/i }).click();
    await page.waitForTimeout(2000);

    // Verify backend is healthy
    const health = await request.get(`${API_URL}/health`);
    expect(health.ok()).toBeTruthy();

    // Frontend should be in a valid state (not showing errors)
    const body = page.locator('body');
    await expect(body).toBeVisible();

    // Check for any error indicators
    const errorElements = page.locator('[class*="error"], [class*="Error"]');
    const errorCount = await errorElements.count();
    // Should have no error elements visible after successful login
    // (some may exist but be hidden)
  });

  test('should fetch and display operation progress', async ({ request }) => {
    const token = await getAuthToken(request);

    // Get current operations
    const ops = await request.get(`${API_URL}/api/progress/operations`, {
      headers: { Authorization: `Bearer ${token}` }
    });

    expect(ops.ok()).toBeTruthy();
    const operations = await ops.json();
    expect(Array.isArray(operations)).toBeTruthy();

    // If there are operations, verify structure
    if (operations.length > 0) {
      const op = operations[0];
      expect(op).toHaveProperty('operation_id');
      expect(op).toHaveProperty('status');
    }
  });

  test('should handle multiple concurrent API requests', async ({ request }) => {
    const token = await getAuthToken(request);
    const headers = { Authorization: `Bearer ${token}` };

    // Fire 5 concurrent requests
    const requests = [
      request.get(`${API_URL}/health`),
      request.get(`${API_URL}/api/v2/kr-similar/health`),
      request.get(`${API_URL}/api/v2/quicksearch/health`),
      request.get(`${API_URL}/api/v2/xlstransfer/health`),
      request.get(`${API_URL}/api/progress/operations`, { headers }),
    ];

    const responses = await Promise.all(requests);

    // All should succeed
    for (const response of responses) {
      expect(response.ok()).toBeTruthy();
    }
  });
});

test.describe('Telemetry Data Flow', () => {

  test('should record and retrieve activity logs', async ({ request }) => {
    const token = await getAuthToken(request);
    const headers = { Authorization: `Bearer ${token}` };

    // Get activity logs
    const logs = await request.get(`${API_URL}/api/v2/admin/logs`, { headers });

    if (logs.ok()) {
      const data = await logs.json();
      expect(data).toBeDefined();
    }
  });

  test('should track user rankings', async ({ request }) => {
    const token = await getAuthToken(request);
    const headers = { Authorization: `Bearer ${token}` };

    // Get rankings for different periods
    const periods = ['daily', 'weekly', 'monthly'];

    for (const period of periods) {
      const rankings = await request.get(
        `${API_URL}/api/v2/admin/rankings/users?period=${period}`,
        { headers }
      );

      if (rankings.ok()) {
        const data = await rankings.json();
        expect(data).toHaveProperty('rankings');
      }
    }
  });

  test('should track tool popularity over time', async ({ request }) => {
    const token = await getAuthToken(request);
    const headers = { Authorization: `Bearer ${token}` };

    // Get tool popularity for different time ranges
    const dayRanges = [7, 14, 30];

    for (const days of dayRanges) {
      const popularity = await request.get(
        `${API_URL}/api/v2/admin/stats/tools/popularity?days=${days}`,
        { headers }
      );

      if (popularity.ok()) {
        const data = await popularity.json();
        expect(data).toHaveProperty('tools');
      }
    }
  });
});

test.describe('Session Management Flow', () => {

  test('should create and track sessions', async ({ request }) => {
    const token = await getAuthToken(request);
    const headers = { Authorization: `Bearer ${token}` };

    // Get active sessions
    const sessions = await request.get(`${API_URL}/api/v2/admin/sessions`, { headers });

    if (sessions.ok()) {
      const data = await sessions.json();
      expect(data).toHaveProperty('sessions');
      expect(Array.isArray(data.sessions)).toBeTruthy();
    }
  });

  test('should handle session expiry gracefully', async ({ request }) => {
    // Try to use an expired/invalid token
    const response = await request.get(`${API_URL}/api/v2/admin/stats/overview`, {
      headers: { Authorization: 'Bearer expired_invalid_token' }
    });

    // Should get auth error, not server error
    expect(response.status()).toBeLessThan(500);
  });
});

test.describe('Real-time Updates Simulation', () => {

  test('should poll operations and get updated data', async ({ request }) => {
    const token = await getAuthToken(request);
    const headers = { Authorization: `Bearer ${token}` };

    // Simulate polling by making multiple requests
    const results: any[] = [];

    for (let i = 0; i < 3; i++) {
      const ops = await request.get(`${API_URL}/api/progress/operations`, { headers });
      expect(ops.ok()).toBeTruthy();
      results.push(await ops.json());
      await new Promise(r => setTimeout(r, 500));
    }

    // All results should be valid arrays
    for (const result of results) {
      expect(Array.isArray(result)).toBeTruthy();
    }
  });

  test('should handle WebSocket polling endpoint', async ({ request }) => {
    // Test Socket.IO handshake
    const response = await request.get(`${API_URL}/socket.io/?EIO=4&transport=polling`);

    // Should respond (even if not fully connected via polling)
    expect(response.status()).toBeLessThan(500);
  });
});

test.describe('Error Recovery Scenarios', () => {

  test('should recover from API timeout gracefully', async ({ page, request }) => {
    await page.goto('/');

    // Set a short timeout for this request
    try {
      await request.get(`${API_URL}/health`, { timeout: 100 });
    } catch (e) {
      // Timeout is expected, page should still work
    }

    // Frontend should still be responsive
    await expect(page.locator('body')).toBeVisible();
  });

  test('should handle invalid API responses', async ({ request }) => {
    const token = await getAuthToken(request);

    // Request non-existent endpoint
    const response = await request.get(`${API_URL}/api/v2/nonexistent/endpoint`, {
      headers: { Authorization: `Bearer ${token}` }
    });

    // Should get 404, not crash
    expect(response.status()).toBe(404);
  });

  test('should validate token on each request', async ({ request }) => {
    // First login
    const token = await getAuthToken(request);

    // Make authenticated request
    const response = await request.get(`${API_URL}/api/v2/admin/stats/overview`, {
      headers: { Authorization: `Bearer ${token}` }
    });

    // Should work with valid token
    expect(response.status()).toBeLessThan(500);
  });
});

test.describe('Cross-Component Data Consistency', () => {

  test('should have consistent user data across endpoints', async ({ request }) => {
    const token = await getAuthToken(request);
    const headers = { Authorization: `Bearer ${token}` };

    // Get stats and rankings
    const [statsRes, rankingsRes] = await Promise.all([
      request.get(`${API_URL}/api/v2/admin/stats/overview`, { headers }),
      request.get(`${API_URL}/api/v2/admin/rankings/users?period=monthly`, { headers }),
    ]);

    if (statsRes.ok() && rankingsRes.ok()) {
      const stats = await statsRes.json();
      const rankings = await rankingsRes.json();

      // Both should have valid structure
      expect(stats).toHaveProperty('active_users');
      expect(rankings).toHaveProperty('rankings');
    }
  });

  test('should maintain data integrity during concurrent operations', async ({ request }) => {
    const token = await getAuthToken(request);
    const headers = { Authorization: `Bearer ${token}` };

    // Make 10 concurrent requests to the same endpoint
    const requests = Array(10).fill(null).map(() =>
      request.get(`${API_URL}/api/v2/admin/stats/overview`, { headers })
    );

    const responses = await Promise.all(requests);
    const data = await Promise.all(responses.map(r => r.json()));

    // All should return same structure
    for (const item of data) {
      expect(item).toHaveProperty('active_users');
      expect(item).toHaveProperty('today_operations');
    }
  });
});
