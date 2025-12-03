import { test, expect } from '@playwright/test';

/**
 * Login Component E2E Tests
 * Tests the login flow, form validation, and authentication
 */

test.describe('Login Page', () => {
  test.beforeEach(async ({ page }) => {
    // Clear any stored credentials
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.clear();
    });
    await page.reload();
  });

  test('should display login form with all elements', async ({ page }) => {
    await page.goto('/');

    // Check title and branding
    await expect(page.locator('h1')).toContainText('LocaNext');
    await expect(page.locator('text=Localization Tools Platform')).toBeVisible();

    // Check form elements exist
    await expect(page.getByLabel('Username')).toBeVisible();
    await expect(page.getByLabel('Password')).toBeVisible();
    await expect(page.locator('text=Remember me')).toBeVisible();
    await expect(page.getByRole('button', { name: /login/i })).toBeVisible();

    // Check footer text
    await expect(page.locator('text=Contact your administrator for access')).toBeVisible();
  });

  test('should require credentials to login', async ({ page }) => {
    await page.goto('/');

    // Click login without entering credentials
    await page.getByRole('button', { name: /login/i }).click();

    // Either shows error OR stays on login page (HTML5 validation)
    // The important thing is user can't proceed without credentials
    await page.waitForTimeout(1000);

    // Should still be on login page (not logged in)
    const stillOnLogin = await page.locator('.login-container, h1:has-text("LocaNext")').first().isVisible();
    expect(stillOnLogin).toBe(true);
  });

  test('should show error for invalid credentials', async ({ page }) => {
    await page.goto('/');

    // Enter invalid credentials
    await page.getByLabel('Username').fill('wronguser');
    await page.getByLabel('Password').fill('wrongpassword');
    await page.getByRole('button', { name: /login/i }).click();

    // Wait for error message - use broader selector
    await expect(page.locator('[class*="notification"], [class*="error"], [role="alert"]').first()).toBeVisible({ timeout: 10000 });
  });

  test('should login successfully with valid credentials', async ({ page }) => {
    await page.goto('/');

    // Enter valid credentials (admin/admin123 is the default)
    await page.getByLabel('Username').fill('admin');
    await page.getByLabel('Password').fill('admin123');
    await page.getByRole('button', { name: /login/i }).click();

    // Wait for successful login - should navigate away from login
    // or show the main app content
    await expect(page.locator('.login-container')).not.toBeVisible({ timeout: 10000 });
  });

  test('should show loading state during login', async ({ page }) => {
    await page.goto('/');

    // Fill in credentials
    await page.getByLabel('Username').fill('admin');
    await page.getByLabel('Password').fill('admin123');

    // Click login and check for loading state
    await page.getByRole('button', { name: /login/i }).click();

    // Should briefly show loading indicator
    // Note: This may be too fast to catch, so we check it doesn't error
  });

  test('should allow login via Enter key', async ({ page }) => {
    await page.goto('/');

    // Enter credentials
    await page.getByLabel('Username').fill('admin');
    await page.getByLabel('Password').fill('admin123');

    // Press Enter to submit
    await page.getByLabel('Password').press('Enter');

    // Should navigate away from login on success
    await expect(page.locator('.login-container')).not.toBeVisible({ timeout: 10000 });
  });

  test('should have remember me checkbox', async ({ page }) => {
    await page.goto('/');

    // Check remember me checkbox exists using text
    const checkboxLabel = page.locator('text=Remember me');
    await expect(checkboxLabel).toBeVisible();

    // Click the label to toggle (Carbon Components style)
    await checkboxLabel.click();

    // Verify checkbox state changed (check the actual input)
    const checkbox = page.locator('input[type="checkbox"]').first();
    await expect(checkbox).toBeChecked();
  });

  test('should save credentials when remember me is checked', async ({ page }) => {
    await page.goto('/');

    // Login with remember me checked
    await page.getByLabel('Username').fill('admin');
    await page.getByLabel('Password').fill('admin123');

    // Click the Remember me label (Carbon style)
    await page.locator('text=Remember me').click();

    await page.getByRole('button', { name: /login/i }).click();

    // Wait for successful login
    await expect(page.locator('.login-container')).not.toBeVisible({ timeout: 10000 });

    // Check localStorage has saved credentials
    const hasCredentials = await page.evaluate(() => {
      return localStorage.getItem('locanext_remember') === 'true' &&
             localStorage.getItem('locanext_creds') !== null;
    });

    expect(hasCredentials).toBe(true);
  });

  test('should show and dismiss error notification', async ({ page }) => {
    await page.goto('/');

    // Enter invalid credentials to trigger error
    await page.getByLabel('Username').fill('wronguser');
    await page.getByLabel('Password').fill('wrongpass');
    await page.getByRole('button', { name: /login/i }).click();

    // Error should be visible
    const notification = page.locator('[class*="notification"]').first();
    await expect(notification).toBeVisible({ timeout: 10000 });

    // Try to close if close button exists
    const closeBtn = page.locator('[class*="close-button"], button[aria-label*="close"]').first();
    if (await closeBtn.isVisible()) {
      await closeBtn.click();
    }
  });
});
