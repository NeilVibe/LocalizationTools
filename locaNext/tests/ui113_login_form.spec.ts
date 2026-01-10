/**
 * UI-113: Login form in Sync Dashboard should be fully visible
 */
import { test, expect } from '@playwright/test';

const DEV_URL = 'http://localhost:5173';

test('UI-113: Login form should show all fields (username, password, buttons)', async ({ page }) => {
  // 1. Start offline
  await page.goto(DEV_URL);
  await page.waitForTimeout(2000);
  await page.locator('text=Start Offline').click();
  await page.waitForTimeout(2000);

  // 2. Open Sync Dashboard
  const offlineBtn = page.locator('button:has-text("Offline")').first();
  await offlineBtn.click();
  await page.waitForTimeout(1000);

  // 3. Click "Switch to Online" to show login form
  const switchBtn = page.locator('button:has-text("Switch to Online")');
  if (await switchBtn.isVisible()) {
    await switchBtn.click();
    await page.waitForTimeout(500);
  }

  // 4. Take screenshot
  await page.screenshot({ path: '/tmp/ui113_login_form.png' });

  // 5. Verify all elements are visible (use label selectors to be more specific)
  const usernameField = await page.locator('label:has-text("Username")').first().isVisible();
  const passwordField = await page.locator('label:has-text("Password")').first().isVisible();
  const connectBtn = await page.locator('button:has-text("Connect")').isVisible();

  console.log(`\n=== UI-113 TEST ===`);
  console.log(`Username field visible: ${usernameField}`);
  console.log(`Password field visible: ${passwordField}`);
  console.log(`Connect button visible: ${connectBtn}`);

  expect(usernameField).toBe(true);
  expect(passwordField).toBe(true);
  expect(connectBtn).toBe(true);

  console.log('✅ UI-113: All login form fields visible!');
});
