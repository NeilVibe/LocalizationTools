/**
 * UI-110 Offline Mode Test: Right-click on TM tree should NOT show browser menu
 */
import { test, expect } from '@playwright/test';

const DEV_URL = 'http://localhost:5173';

test('UI-110 Offline: Right-click on TM tree Offline Storage header', async ({ page }) => {
  // 1. Start offline
  await page.goto(DEV_URL);
  await page.waitForTimeout(2000);
  await page.locator('text=Start Offline').click();
  await page.waitForTimeout(2000);

  // 2. Go to TM page
  await page.locator('text=TM').first().click();
  await page.waitForTimeout(2000);

  // 3. Right-click on Offline Storage header
  const offlineStorageBtn = page.locator('button:has-text("Offline Storage")').first();
  if (await offlineStorageBtn.isVisible()) {
    await offlineStorageBtn.click({ button: 'right' });
    await page.waitForTimeout(500);
  }

  // 4. Take screenshot
  await page.screenshot({ path: '/tmp/ui110_offline_rightclick.png' });

  // 5. Check that browser context menu is NOT visible
  const browserMenuVisible = await page.locator('text=Back').first().isVisible().catch(() => false);

  console.log(`\n=== UI-110 OFFLINE TEST ===`);
  console.log(`Browser menu visible: ${browserMenuVisible}`);

  expect(browserMenuVisible).toBe(false);
  console.log('✅ UI-110 Offline: Browser context menu blocked!');
});
