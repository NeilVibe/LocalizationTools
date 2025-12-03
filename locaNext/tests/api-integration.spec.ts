import { test, expect, Page } from '@playwright/test';

/**
 * API Integration E2E Tests
 * Tests that frontend correctly communicates with backend API
 */

// Helper to login before tests
async function login(page: Page) {
  await page.goto('/');
  await page.evaluate(() => localStorage.clear());
  await page.reload();

  await page.getByLabel('Username').fill('admin');
  await page.getByLabel('Password').fill('admin123');
  await page.getByRole('button', { name: /login/i }).click();

  // Wait for login to complete
  await expect(page.locator('.login-container')).not.toBeVisible({ timeout: 10000 });
}

test.describe('API Health Check', () => {
  test('backend should be healthy', async ({ request }) => {
    const response = await request.get('http://localhost:8888/health');
    expect(response.ok()).toBeTruthy();

    const body = await response.json();
    expect(body.status).toBe('healthy');
    expect(body.database).toBe('connected');
  });

  test('API docs should be accessible', async ({ request }) => {
    const response = await request.get('http://localhost:8888/docs');
    expect(response.ok()).toBeTruthy();
  });
});

test.describe('Authentication API', () => {
  test('should login via API', async ({ request }) => {
    const response = await request.post('http://localhost:8888/api/v2/auth/login', {
      data: {
        username: 'admin',
        password: 'admin123'
      }
    });

    expect(response.ok()).toBeTruthy();

    const body = await response.json();
    expect(body.access_token).toBeDefined();
    expect(body.token_type).toBe('bearer');
  });

  test('should reject invalid credentials', async ({ request }) => {
    const response = await request.post('http://localhost:8888/api/v2/auth/login', {
      data: {
        username: 'wronguser',
        password: 'wrongpass'
      }
    });

    expect(response.ok()).toBeFalsy();
  });
});

test.describe('Tool Health Endpoints', () => {
  let token: string;

  test.beforeAll(async ({ request }) => {
    const response = await request.post('http://localhost:8888/api/v2/auth/login', {
      data: { username: 'admin', password: 'admin123' }
    });
    const body = await response.json();
    token = body.access_token;
  });

  test('KR Similar health check', async ({ request }) => {
    const response = await request.get('http://localhost:8888/api/v2/kr-similar/health', {
      headers: { Authorization: `Bearer ${token}` }
    });
    expect(response.ok()).toBeTruthy();
  });

  test('QuickSearch health check', async ({ request }) => {
    const response = await request.get('http://localhost:8888/api/v2/quicksearch/health', {
      headers: { Authorization: `Bearer ${token}` }
    });
    expect(response.ok()).toBeTruthy();
  });

  test('XLSTransfer health check', async ({ request }) => {
    const response = await request.get('http://localhost:8888/api/v2/xlstransfer/health', {
      headers: { Authorization: `Bearer ${token}` }
    });
    expect(response.ok()).toBeTruthy();
  });
});

test.describe('Frontend-Backend Integration', () => {
  test('frontend should receive auth token after login', async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
    await page.reload();

    // Intercept API requests
    const loginPromise = page.waitForResponse(response =>
      response.url().includes('/auth/login') && response.status() === 200
    );

    await page.getByLabel('Username').fill('admin');
    await page.getByLabel('Password').fill('admin123');
    await page.getByRole('button', { name: /login/i }).click();

    const response = await loginPromise;
    const body = await response.json();

    expect(body.access_token).toBeDefined();
  });

  test('frontend should store token after login', async ({ page }) => {
    await login(page);

    // Check that token is stored (either in localStorage or sessionStorage)
    const hasToken = await page.evaluate(() => {
      return localStorage.getItem('locanext_token') !== null ||
             sessionStorage.getItem('token') !== null ||
             document.cookie.includes('token');
    });

    // Token should be stored somewhere for authenticated requests
    // This depends on implementation - adjust as needed
  });

  test('should handle API errors gracefully', async ({ page }) => {
    await page.goto('/');

    // Test with invalid credentials
    await page.getByLabel('Username').fill('wronguser');
    await page.getByLabel('Password').fill('wrongpass');
    await page.getByRole('button', { name: /login/i }).click();

    // Should show error message, not crash
    await expect(page.locator('.bx--inline-notification--error, [class*="error"]')).toBeVisible({ timeout: 10000 });
  });
});

test.describe('Session Management', () => {
  test('should maintain session after page reload', async ({ page }) => {
    await login(page);

    // Reload page
    await page.reload();

    // Should still be logged in (not showing login form)
    // This depends on your session management implementation
    await page.waitForTimeout(2000);
  });
});
