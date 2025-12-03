import { test } from '@playwright/test';

test('capture login page screenshot', async ({ page }) => {
  await page.goto('/');
  await page.waitForTimeout(2000);
  await page.screenshot({ path: 'login-screenshot.png', fullPage: true });
});
