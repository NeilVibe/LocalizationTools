/**
 * Login Helper for Playwright Tests
 *
 * Usage:
 *   import { login } from '../helpers/login';
 *   await login(page);
 */

import { Page } from '@playwright/test';

export const DEFAULT_CREDENTIALS = {
  username: 'admin',
  password: 'admin123'
};

export const DEV_URL = 'http://localhost:5173';
export const API_URL = 'http://localhost:8888';

/**
 * Login to the application
 *
 * NOTE: LocaNext has a Mode Selection screen before login.
 * Need to click "Login" button first to get to the login form.
 */
export async function login(
  page: Page,
  credentials = DEFAULT_CREDENTIALS,
  options: { timeout?: number; screenshot?: string } = {}
): Promise<void> {
  const { timeout = 10000, screenshot } = options;

  await page.goto(DEV_URL);
  await page.waitForLoadState('domcontentloaded');
  await page.waitForTimeout(1000);

  // Check if we're on Mode Selection screen (has "Start Offline" button)
  const modeSelectionVisible = await page.locator('button:has-text("Start Offline")').isVisible().catch(() => false);
  if (modeSelectionVisible) {
    // Wait for server to be connected
    await page.waitForSelector('text=Central Server Connected', { timeout: 10000 }).catch(() => {});
    // Click "Login" button to get to login form
    await page.locator('button.login-btn').click();
    // Wait for login form to appear
    await page.waitForSelector('input[type="password"]', { timeout: 5000 }).catch(() => {});
  }

  // Now on login form - fill credentials
  // LocaNext uses label-based form, not placeholders
  // First input is username, second (type=password) is password
  await page.locator('input').first().fill(credentials.username);
  await page.locator('input[type="password"]').fill(credentials.password);
  await page.locator('button:has-text("Login")').click();

  // Wait for login to complete
  await page.waitForTimeout(3000);

  if (screenshot) {
    await page.screenshot({ path: screenshot }).catch(() => {});
  }
}

/**
 * Get API token via login
 */
export async function getApiToken(credentials = DEFAULT_CREDENTIALS): Promise<string> {
  const resp = await fetch(`${API_URL}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(credentials)
  });
  const data = await resp.json();
  return data.access_token;
}

/**
 * Navigate to LDM page after login
 */
export async function navigateToLDM(page: Page): Promise<void> {
  await page.goto(`${DEV_URL}/ldm`);
  await page.waitForTimeout(2000);
}

/**
 * Full login and navigate to LDM flow
 */
export async function loginAndGoToLDM(
  page: Page,
  credentials = DEFAULT_CREDENTIALS
): Promise<void> {
  await login(page, credentials);
  await navigateToLDM(page);
}
