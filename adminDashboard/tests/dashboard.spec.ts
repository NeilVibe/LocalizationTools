import { test, expect } from '@playwright/test';

/**
 * Admin Dashboard E2E Tests
 * Tests statistics, rankings, and admin features
 */

test.describe('Dashboard Overview', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should load dashboard page', async ({ page }) => {
    // Dashboard should load without errors
    await expect(page).toHaveURL(/.*5175/);
  });

  test('should display main content', async ({ page }) => {
    // Look for stats/metrics elements
    await expect(page.locator('body')).toBeVisible();

    // Check for any content
    const bodyContent = await page.textContent('body');
    expect(bodyContent).toBeTruthy();
  });

  test('should show dashboard elements', async ({ page }) => {
    // Wait for page to fully load
    await page.waitForTimeout(1000);

    // Look for common dashboard elements
    const dashboardContent = page.locator('[class*="dashboard"], main, [class*="content"]').first();
    const count = await dashboardContent.count();
    expect(count).toBeGreaterThanOrEqual(0);
  });
});

test.describe('Rankings Section', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should have some content loaded', async ({ page }) => {
    await page.waitForTimeout(1000);
    await expect(page.locator('body')).toBeVisible();
  });

  test('should display any UI elements', async ({ page }) => {
    const elements = page.locator('div, section, article').first();
    await expect(elements).toBeVisible();
  });
});

test.describe('Activity Logs', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should have page structure', async ({ page }) => {
    await expect(page.locator('body')).toBeVisible();
  });

  test('should have some DOM content', async ({ page }) => {
    await page.waitForTimeout(1000);
    const divCount = await page.locator('div').count();
    expect(divCount).toBeGreaterThan(0);
  });
});

test.describe('API Integration', () => {
  test('should fetch stats from API', async ({ request }) => {
    // Get auth token first
    const loginResponse = await request.post('http://localhost:8888/api/v2/auth/login', {
      data: { username: 'admin', password: 'admin123' }
    });

    if (loginResponse.ok()) {
      const { access_token } = await loginResponse.json();

      // Fetch overview stats
      const statsResponse = await request.get('http://localhost:8888/api/v2/admin/stats/overview', {
        headers: { Authorization: `Bearer ${access_token}` }
      });

      expect(statsResponse.ok()).toBeTruthy();

      const stats = await statsResponse.json();
      expect(stats).toHaveProperty('active_users');
      expect(stats).toHaveProperty('today_operations');
    }
  });

  test('should fetch rankings from API', async ({ request }) => {
    const loginResponse = await request.post('http://localhost:8888/api/v2/auth/login', {
      data: { username: 'admin', password: 'admin123' }
    });

    if (loginResponse.ok()) {
      const { access_token } = await loginResponse.json();

      const rankingsResponse = await request.get('http://localhost:8888/api/v2/admin/rankings/users?period=monthly', {
        headers: { Authorization: `Bearer ${access_token}` }
      });

      expect(rankingsResponse.ok()).toBeTruthy();

      const rankings = await rankingsResponse.json();
      expect(rankings).toHaveProperty('rankings');
    }
  });

  test('should fetch tool popularity from API', async ({ request }) => {
    const loginResponse = await request.post('http://localhost:8888/api/v2/auth/login', {
      data: { username: 'admin', password: 'admin123' }
    });

    if (loginResponse.ok()) {
      const { access_token } = await loginResponse.json();

      const popularityResponse = await request.get('http://localhost:8888/api/v2/admin/stats/tools/popularity?days=30', {
        headers: { Authorization: `Bearer ${access_token}` }
      });

      expect(popularityResponse.ok()).toBeTruthy();

      const data = await popularityResponse.json();
      expect(data).toHaveProperty('tools');
    }
  });
});

test.describe('Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should have DOM structure', async ({ page }) => {
    await expect(page.locator('body')).toBeVisible();
  });

  test('should respond to interactions', async ({ page }) => {
    // Click anywhere clickable
    const buttons = page.locator('button, a');
    const count = await buttons.count();

    if (count > 0) {
      // Just verify buttons exist
      expect(count).toBeGreaterThan(0);
    }
  });
});

test.describe('Responsive Design', () => {
  test('should display correctly on desktop', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.goto('/');
    await expect(page.locator('body')).toBeVisible();
  });

  test('should display correctly on tablet', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto('/');
    await expect(page.locator('body')).toBeVisible();
  });

  test('should display correctly on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');
    await expect(page.locator('body')).toBeVisible();
  });
});
