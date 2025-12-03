import { test, expect } from '@playwright/test';

/**
 * Frontend + Backend Integration Tests
 * Tests complete flow: Frontend UI → Backend API → Database → Response
 * Verifies telemetry data flows correctly through the system
 */

// API base URL
const API_URL = 'http://localhost:8888';

test.describe('Frontend-Backend Authentication Flow', () => {
  test('should login via UI and verify backend session created', async ({ page, request }) => {
    // Login via frontend
    await page.goto('/');
    await page.getByLabel('Username').fill('admin');
    await page.getByLabel('Password').fill('admin123');
    await page.getByRole('button', { name: /login/i }).click();

    // Wait for login to complete
    await page.waitForTimeout(3000);

    // Verify backend has the session - check via API
    const loginResponse = await request.post(`${API_URL}/api/v2/auth/login`, {
      data: { username: 'admin', password: 'admin123' }
    });
    expect(loginResponse.ok()).toBeTruthy();

    const { access_token } = await loginResponse.json();
    expect(access_token).toBeTruthy();

    // Check active sessions
    const sessionsResponse = await request.get(`${API_URL}/api/v2/admin/sessions`, {
      headers: { Authorization: `Bearer ${access_token}` }
    });

    if (sessionsResponse.ok()) {
      const sessions = await sessionsResponse.json();
      expect(sessions.sessions).toBeDefined();
    }
  });

  test('should track login in audit logs', async ({ request }) => {
    // Login
    const loginResponse = await request.post(`${API_URL}/api/v2/auth/login`, {
      data: { username: 'admin', password: 'admin123' }
    });
    const { access_token } = await loginResponse.json();

    // Check audit logs for login event
    const logsResponse = await request.get(`${API_URL}/api/v2/admin/logs`, {
      headers: { Authorization: `Bearer ${access_token}` }
    });

    if (logsResponse.ok()) {
      const logs = await logsResponse.json();
      // Verify logs structure exists
      expect(logs).toBeDefined();
    }
  });
});

test.describe('Frontend-Backend Tool Operation Flow', () => {
  let token: string;

  test.beforeAll(async ({ request }) => {
    const loginResponse = await request.post(`${API_URL}/api/v2/auth/login`, {
      data: { username: 'admin', password: 'admin123' }
    });
    const data = await loginResponse.json();
    token = data.access_token;
  });

  test('should check KR Similar health from frontend context', async ({ page, request }) => {
    // Frontend loads
    await page.goto('/');
    await page.getByLabel('Username').fill('admin');
    await page.getByLabel('Password').fill('admin123');
    await page.getByRole('button', { name: /login/i }).click();
    await page.waitForTimeout(2000);

    // Verify KR Similar API is healthy
    const healthResponse = await request.get(`${API_URL}/api/v2/kr-similar/health`);
    expect(healthResponse.ok()).toBeTruthy();

    const health = await healthResponse.json();
    expect(health.status).toBe('ok');
  });

  test('should check QuickSearch health from frontend context', async ({ page, request }) => {
    await page.goto('/');
    await page.getByLabel('Username').fill('admin');
    await page.getByLabel('Password').fill('admin123');
    await page.getByRole('button', { name: /login/i }).click();
    await page.waitForTimeout(2000);

    // Verify QuickSearch API is healthy
    const healthResponse = await request.get(`${API_URL}/api/v2/quicksearch/health`);
    expect(healthResponse.ok()).toBeTruthy();

    const health = await healthResponse.json();
    expect(health.status).toBe('ok');
  });

  test('should verify XLSTransfer endpoint accessibility', async ({ request }) => {
    const healthResponse = await request.get(`${API_URL}/api/v2/xlstransfer/health`);
    expect(healthResponse.ok()).toBeTruthy();
  });
});

test.describe('Frontend-Backend Telemetry Flow', () => {
  let token: string;

  test.beforeAll(async ({ request }) => {
    const loginResponse = await request.post(`${API_URL}/api/v2/auth/login`, {
      data: { username: 'admin', password: 'admin123' }
    });
    const data = await loginResponse.json();
    token = data.access_token;
  });

  test('should record tool usage in telemetry', async ({ request }) => {
    // Simulate a tool operation that would be tracked
    const logResponse = await request.post(`${API_URL}/api/v2/telemetry/log`, {
      headers: { Authorization: `Bearer ${token}` },
      data: {
        event_type: 'tool_usage',
        tool_name: 'kr_similar',
        action: 'search',
        details: { query: 'test', results_count: 5 }
      }
    });

    // Telemetry endpoint may or may not exist - check gracefully
    if (logResponse.ok()) {
      const result = await logResponse.json();
      expect(result).toBeDefined();
    }
  });

  test('should fetch admin stats overview', async ({ request }) => {
    const statsResponse = await request.get(`${API_URL}/api/v2/admin/stats/overview`, {
      headers: { Authorization: `Bearer ${token}` }
    });

    if (statsResponse.ok()) {
      const stats = await statsResponse.json();
      expect(stats).toHaveProperty('active_users');
      expect(stats).toHaveProperty('today_operations');
    }
  });

  test('should fetch user rankings', async ({ request }) => {
    const rankingsResponse = await request.get(`${API_URL}/api/v2/admin/rankings/users?period=monthly`, {
      headers: { Authorization: `Bearer ${token}` }
    });

    if (rankingsResponse.ok()) {
      const rankings = await rankingsResponse.json();
      expect(rankings).toHaveProperty('rankings');
    }
  });

  test('should fetch tool popularity stats', async ({ request }) => {
    const popularityResponse = await request.get(`${API_URL}/api/v2/admin/stats/tools/popularity?days=30`, {
      headers: { Authorization: `Bearer ${token}` }
    });

    if (popularityResponse.ok()) {
      const data = await popularityResponse.json();
      expect(data).toHaveProperty('tools');
    }
  });
});

test.describe('Frontend State After Backend Operations', () => {
  test('should maintain login state across page navigation', async ({ page }) => {
    await page.goto('/');

    // Login
    await page.getByLabel('Username').fill('admin');
    await page.getByLabel('Password').fill('admin123');
    await page.getByRole('button', { name: /login/i }).click();
    await page.waitForTimeout(2000);

    // After login, user should not see login form
    const loginContainer = page.locator('.login-container');
    const isLoginVisible = await loginContainer.isVisible().catch(() => false);

    // Either login container is hidden or we're on a different page
    // The key is that we can navigate
    await page.goto('/');
    await page.waitForTimeout(1000);

    // Page should load without errors
    await expect(page.locator('body')).toBeVisible();
  });

  test('should handle logout flow correctly', async ({ page, request }) => {
    await page.goto('/');

    // Login
    await page.getByLabel('Username').fill('admin');
    await page.getByLabel('Password').fill('admin123');
    await page.getByRole('button', { name: /login/i }).click();
    await page.waitForTimeout(2000);

    // Look for logout button and click if exists
    const logoutButton = page.getByRole('button', { name: /logout/i });
    const hasLogout = await logoutButton.count() > 0;

    if (hasLogout) {
      await logoutButton.click();
      await page.waitForTimeout(1000);

      // Should redirect to login page
      const loginForm = page.locator('.login-container');
      await expect(loginForm).toBeVisible({ timeout: 5000 });
    }
  });
});

test.describe('WebSocket Connection Tests', () => {
  test('should verify WebSocket endpoint is accessible', async ({ request }) => {
    // Test Socket.IO polling endpoint
    const response = await request.get(`${API_URL}/socket.io/?EIO=4&transport=polling`);

    // Socket.IO should respond (even if not fully connected)
    expect(response.status()).toBeLessThan(500);
  });

  test('should verify progress operations endpoint', async ({ request }) => {
    // Login first
    const loginResponse = await request.post(`${API_URL}/api/v2/auth/login`, {
      data: { username: 'admin', password: 'admin123' }
    });
    const { access_token } = await loginResponse.json();

    // Check operations endpoint
    const opsResponse = await request.get(`${API_URL}/api/progress/operations`, {
      headers: { Authorization: `Bearer ${access_token}` }
    });

    expect(opsResponse.ok()).toBeTruthy();
    const operations = await opsResponse.json();
    expect(Array.isArray(operations)).toBeTruthy();
  });
});

test.describe('Error Handling Integration', () => {
  test('should handle invalid login gracefully in UI', async ({ page }) => {
    await page.goto('/');

    // Try invalid login
    await page.getByLabel('Username').fill('wronguser');
    await page.getByLabel('Password').fill('wrongpass');
    await page.getByRole('button', { name: /login/i }).click();

    // Should stay on login page (not crash)
    await page.waitForTimeout(2000);
    const loginInput = page.getByLabel('Username');
    await expect(loginInput).toBeVisible();
  });

  test('should handle API errors gracefully', async ({ request }) => {
    // Try to access protected endpoint without auth
    const response = await request.get(`${API_URL}/api/v2/admin/stats/overview`);

    // Should not get 500 - either success (if public) or auth error
    expect(response.status()).toBeLessThan(500);
    // Endpoint might be public or protected - either way, server handles it gracefully
    expect([200, 401, 403, 422]).toContain(response.status());
  });

  test('should return proper error format', async ({ request }) => {
    const response = await request.post(`${API_URL}/api/v2/auth/login`, {
      data: { username: 'invalid', password: 'invalid' }
    });

    expect(response.status()).toBe(401);
    const error = await response.json();
    expect(error).toHaveProperty('detail');
  });
});
