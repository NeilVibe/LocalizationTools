/**
 * Launcher Tests - P9: Launcher + Offline/Online Mode
 *
 * Tests the beautiful launcher screen that appears before login
 */
import { test, expect } from '@playwright/test';

test.describe('Launcher Screen', () => {
  // Clear auth before each test to ensure launcher shows
  test.beforeEach(async ({ page }) => {
    // Clear any stored auth tokens
    await page.goto('http://localhost:5173');
    await page.evaluate(() => {
      localStorage.removeItem('auth_token');
      localStorage.removeItem('locanext_remember');
      localStorage.removeItem('locanext_creds');
    });
    // Reload to show launcher
    await page.reload();
  });

  test('displays launcher with logo and buttons', async ({ page }) => {
    // Wait for launcher to appear
    await page.waitForSelector('.launcher', { timeout: 10000 });

    // Check logo
    const logo = page.locator('.logo-text');
    await expect(logo).toBeVisible();
    await expect(logo).toHaveText('LocaNext');

    // Check server status indicator
    const serverStatus = page.locator('.server-status');
    await expect(serverStatus).toBeVisible();

    // Check main buttons
    const offlineBtn = page.locator('.offline-btn');
    const loginBtn = page.locator('.login-btn');

    await expect(offlineBtn).toBeVisible();
    await expect(loginBtn).toBeVisible();

    // Check button text
    await expect(offlineBtn.locator('.btn-title')).toHaveText('Start Offline');
    await expect(loginBtn.locator('.btn-title')).toHaveText('Login');
  });

  test('shows server connected status when backend is running', async ({ page }) => {
    await page.waitForSelector('.server-status', { timeout: 10000 });

    // Wait for status check to complete
    await page.waitForTimeout(2000);

    // Should show connected (backend is running)
    const statusDot = page.locator('.status-dot.connected');
    await expect(statusDot).toBeVisible();

    // Login button should be enabled
    const loginBtn = page.locator('.login-btn');
    await expect(loginBtn).toBeEnabled();
  });

  test('Start Offline button works', async ({ page }) => {
    await page.waitForSelector('.offline-btn', { timeout: 10000 });

    // Click Start Offline
    await page.click('.offline-btn');

    // Wait for launcher to dismiss
    await page.waitForTimeout(500);

    // Should now see main app (launcher dismissed)
    const launcher = page.locator('.launcher');
    await expect(launcher).not.toBeVisible();

    // Should see the main app header
    const header = page.locator('.bx--header');
    await expect(header).toBeVisible();
  });

  test('Login button shows login form', async ({ page }) => {
    await page.waitForSelector('.login-btn', { timeout: 10000 });

    // Wait for server status
    await page.waitForTimeout(2000);

    // Click Login
    await page.click('.login-btn');

    // Should show login form
    const loginForm = page.locator('.login-form');
    await expect(loginForm).toBeVisible();

    // Check form elements
    await expect(page.locator('input[placeholder="Enter username"]')).toBeVisible();
    await expect(page.locator('input[placeholder="Enter password"]')).toBeVisible();

    // Back button should be visible
    const backBtn = page.locator('button:has-text("Back")');
    await expect(backBtn).toBeVisible();
  });

  test('successful login dismisses launcher', async ({ page }) => {
    await page.waitForSelector('.login-btn', { timeout: 10000 });
    await page.waitForTimeout(2000);

    // Click Login to show form
    await page.click('.login-btn');

    // Fill credentials
    await page.fill('input[placeholder="Enter username"]', 'admin');
    await page.fill('input[placeholder="Enter password"]', 'admin123');

    // Submit
    await page.click('button:has-text("Login"):not(:has-text("Back"))');

    // Wait for login
    await page.waitForTimeout(2000);

    // Launcher should be dismissed
    const launcher = page.locator('.launcher');
    await expect(launcher).not.toBeVisible();

    // Main app should be visible
    const header = page.locator('.bx--header');
    await expect(header).toBeVisible();
  });

  test('Back button returns to main launcher view', async ({ page }) => {
    await page.waitForSelector('.login-btn', { timeout: 10000 });
    await page.waitForTimeout(2000);

    // Go to login form
    await page.click('.login-btn');
    await expect(page.locator('.login-form')).toBeVisible();

    // Click Back
    await page.click('button:has-text("Back")');

    // Should see main buttons again
    await expect(page.locator('.launcher-buttons')).toBeVisible();
    await expect(page.locator('.offline-btn')).toBeVisible();
  });
});

test.describe('Mode Switching (Offline → Online)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('http://localhost:5173');
    await page.evaluate(() => {
      localStorage.removeItem('auth_token');
      localStorage.removeItem('locanext_remember');
      localStorage.removeItem('locanext_creds');
    });
    await page.reload();
  });

  test('can switch from offline to online mode via Sync Dashboard', async ({ page }) => {
    // Start in offline mode
    await page.waitForSelector('.offline-btn', { timeout: 10000 });
    await page.click('.offline-btn');
    await page.waitForTimeout(1000);

    // Open sync dashboard
    const syncBtn = page.locator('.sync-status-button');
    await expect(syncBtn).toBeVisible();
    await syncBtn.click();
    await page.waitForTimeout(500);

    // Should see Offline status and Switch to Online button
    await expect(page.locator('.status-text.offline')).toContainText('Offline');
    await expect(page.locator('button:has-text("Switch to Online")')).toBeVisible();

    // Click Switch to Online
    await page.click('button:has-text("Switch to Online")');
    await page.waitForTimeout(500);

    // Should see login form
    await expect(page.locator('.login-title')).toContainText('Switch to Online Mode');
    await expect(page.locator('input[placeholder="Enter username"]')).toBeVisible();
    await expect(page.locator('input[placeholder="Enter password"]')).toBeVisible();

    // Fill and submit
    await page.fill('input[placeholder="Enter username"]', 'admin');
    await page.fill('input[placeholder="Enter password"]', 'admin123');
    await page.click('button:has-text("Connect")');
    await page.waitForTimeout(2000);

    // Should now be online
    await expect(page.locator('.status-text.online')).toContainText('Online');
    await expect(page.locator('button:has-text("Sync Now")')).toBeVisible();
    await expect(page.locator('button:has-text("Go Offline")')).toBeVisible();
  });

  test('can cancel login form', async ({ page }) => {
    // Start offline
    await page.waitForSelector('.offline-btn', { timeout: 10000 });
    await page.click('.offline-btn');
    await page.waitForTimeout(1000);

    // Open sync dashboard
    await page.click('.sync-status-button');
    await page.waitForTimeout(500);

    // Click Switch to Online
    await page.click('button:has-text("Switch to Online")');
    await page.waitForTimeout(500);

    // Click Cancel
    await page.click('button:has-text("Cancel")');
    await page.waitForTimeout(300);

    // Should be back to Switch to Online button
    await expect(page.locator('button:has-text("Switch to Online")')).toBeVisible();
  });
});
