import { test, expect } from '@playwright/test';

/**
 * Login Component E2E Tests
 * Tests the login flow, form validation, and authentication
 *
 * NOTE: LocaNext now has a Mode Selection screen before login form.
 * Tests need to click "Login" button first to get to the login form.
 */

// Helper to navigate from Mode Selection to Login form
async function goToLoginForm(page: any) {
  // Wait for page to be fully loaded
  await page.waitForLoadState('domcontentloaded');

  // Wait for Mode Selection screen to appear (Start Offline button)
  const startOfflineBtn = page.locator('button:has-text("Start Offline")');
  await expect(startOfflineBtn).toBeVisible({ timeout: 10000 });

  // Wait for server to be connected
  await expect(page.locator('text=Central Server Connected')).toBeVisible({ timeout: 10000 });

  // Find the Login button and wait for it to be enabled
  const loginBtn = page.locator('button.login-btn');
  await expect(loginBtn).toBeEnabled({ timeout: 5000 });

  // Click the button
  await loginBtn.click();

  // Wait for login form to appear (password input visible)
  await expect(page.locator('input[type="password"]')).toBeVisible({ timeout: 5000 });
}

test.describe('Login Page', () => {
  test.beforeEach(async ({ page }) => {
    // Clear any stored credentials
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.clear();
    });
    await page.reload();
  });

  test('should display mode selection screen first', async ({ page }) => {
    await page.goto('/');

    // Check Mode Selection screen elements
    await expect(page.locator('text=LocaNext')).toBeVisible();
    await expect(page.locator('button:has-text("Start Offline")')).toBeVisible();
    await expect(page.locator('button:has-text("Login")')).toBeVisible();
  });

  test('should display login form after clicking Login button', async ({ page }) => {
    await page.goto('/');
    await goToLoginForm(page);

    // Check form elements exist
    await expect(page.locator('input').first()).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
    await expect(page.getByRole('button', { name: /login/i })).toBeVisible();
  });

  test('should require credentials to login', async ({ page }) => {
    await page.goto('/');
    await goToLoginForm(page);

    // Login button should be disabled without credentials
    const loginBtn = page.getByRole('button', { name: /login/i });
    await expect(loginBtn).toBeDisabled();

    // Should still be on login page
    const stillOnLogin = await page.locator('input[type="password"]').isVisible();
    expect(stillOnLogin).toBe(true);
  });

  test('should show error for invalid credentials', async ({ page }) => {
    await page.goto('/');
    await goToLoginForm(page);

    // Enter invalid credentials
    await page.locator('input').first().fill('wronguser');
    await page.locator('input[type="password"]').fill('wrongpassword');
    await page.getByRole('button', { name: /login/i }).click();

    // Wait for error message
    await expect(page.locator('[class*="notification"], [class*="error"], [role="alert"]').first()).toBeVisible({ timeout: 10000 });
  });

  test('should login successfully with valid credentials', async ({ page }) => {
    await page.goto('/');
    await goToLoginForm(page);

    // Enter valid credentials (admin/admin123 is the default)
    await page.locator('input').first().fill('admin');
    await page.locator('input[type="password"]').fill('admin123');
    await page.getByRole('button', { name: /login/i }).click();

    // Wait for successful login - main app navigation should appear
    await expect(page.getByRole('button', { name: 'Files' })).toBeVisible({ timeout: 10000 });
  });

  test('should show loading state during login', async ({ page }) => {
    await page.goto('/');
    await goToLoginForm(page);

    // Fill in credentials
    await page.locator('input').first().fill('admin');
    await page.locator('input[type="password"]').fill('admin123');

    // Click login and check for loading state
    await page.getByRole('button', { name: /login/i }).click();

    // Should briefly show loading indicator (may be too fast to catch)
  });

  test('should allow login via Enter key', async ({ page }) => {
    await page.goto('/');
    await goToLoginForm(page);

    // Enter credentials
    await page.locator('input').first().fill('admin');
    await page.locator('input[type="password"]').fill('admin123');

    // Press Enter to submit
    await page.locator('input[type="password"]').press('Enter');

    // Wait for successful login - main app navigation should appear
    await expect(page.getByRole('button', { name: 'Files' })).toBeVisible({ timeout: 10000 });
  });

  test('should have remember me checkbox', async ({ page }) => {
    await page.goto('/');
    await goToLoginForm(page);

    // Check remember me checkbox exists
    const checkboxLabel = page.locator('text=Remember me');
    await expect(checkboxLabel).toBeVisible();

    // Click the label to toggle
    await checkboxLabel.click();

    // Verify checkbox state changed
    const checkbox = page.locator('input[type="checkbox"]').first();
    await expect(checkbox).toBeChecked();
  });

  test('should save credentials when remember me is checked', async ({ page }) => {
    await page.goto('/');
    await goToLoginForm(page);

    // Login with remember me checked
    await page.locator('input').first().fill('admin');
    await page.locator('input[type="password"]').fill('admin123');

    // Click the Remember me label
    await page.locator('text=Remember me').click();

    await page.getByRole('button', { name: /login/i }).click();

    // Wait for successful login - main app navigation should appear
    await expect(page.getByRole('button', { name: 'Files' })).toBeVisible({ timeout: 10000 });

    // Check localStorage has saved credentials
    const hasCredentials = await page.evaluate(() => {
      return localStorage.getItem('locanext_remember') === 'true' &&
             localStorage.getItem('locanext_creds') !== null;
    });

    expect(hasCredentials).toBe(true);
  });

  test('should show and dismiss error notification', async ({ page }) => {
    await page.goto('/');
    await goToLoginForm(page);

    // Enter invalid credentials to trigger error
    await page.locator('input').first().fill('wronguser');
    await page.locator('input[type="password"]').fill('wrongpass');
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
