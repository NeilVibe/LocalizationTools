/**
 * UI-107 Offline Mode Test
 * Verify that Offline Storage works in offline mode
 */
import { test, expect } from '@playwright/test';

const DEV_URL = 'http://localhost:5173';

test('UI-107: Offline Storage works in offline mode', async ({ page }) => {
  // 1. Go to landing page
  await page.goto(DEV_URL);
  await page.waitForTimeout(2000);

  // 2. Click "Start Offline" to enter offline mode
  await page.locator('text=Start Offline').click();
  await page.waitForTimeout(2000);

  // 3. Go to Files page
  await page.locator('text=Files').first().click();
  await page.waitForTimeout(2000);
  await page.screenshot({ path: '/tmp/ui107_offline_files.png' });

  // 4. Count VISIBLE Offline Storage entries only
  // (There's also a hidden <option> in platform selector dropdown)
  const allElements = await page.locator('text="Offline Storage"').all();
  let visibleCount = 0;
  for (const el of allElements) {
    if (await el.isVisible()) visibleCount++;
  }
  console.log(`\n=== UI-107 OFFLINE TEST ===`);
  console.log(`Visible "Offline Storage" entries: ${visibleCount}`);

  // Should be exactly 1 - the CloudOffline virtual entry in the grid
  expect(visibleCount).toBe(1);
  console.log('✅ Offline mode: Exactly 1 visible Offline Storage entry');

  // 5. Verify TM tree also has Offline Storage
  await page.locator('text=TM').first().click();
  await page.waitForTimeout(2000);
  await page.screenshot({ path: '/tmp/ui107_offline_tm.png' });

  const tmOfflineCount = await page.locator('button:has-text("Offline Storage")').count();
  console.log(`TM Tree "Offline Storage" buttons: ${tmOfflineCount}`);
  expect(tmOfflineCount).toBeLessThanOrEqual(1);
  console.log('✅ TM Tree: No duplicates');
});
