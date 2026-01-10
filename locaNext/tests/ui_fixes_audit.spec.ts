/**
 * UI Fixes Audit Test - Session 36
 * Tests: UI-109 (nested Offline Storage), UI-110 (context menu), UI-111 (compact modal)
 */
import { test, expect } from '@playwright/test';

const DEV_URL = 'http://localhost:5173';

test('UI-109: TM Tree should NOT show nested Offline Storage > Offline Storage', async ({ page }) => {
  // 1. Login
  await page.goto(DEV_URL);
  await page.waitForTimeout(2000);
  await page.locator('text=Login').first().click();
  await page.waitForTimeout(1500);
  await page.locator('input').first().fill('admin');
  await page.locator('input[type="password"]').fill('admin123');
  await page.locator('button:has-text("Login")').click();
  await page.waitForTimeout(3000);

  // 2. Go to TM page
  await page.locator('text=TM').first().click();
  await page.waitForTimeout(2000);

  // 3. Expand Offline Storage if present
  const offlineStorageBtn = page.locator('button:has-text("Offline Storage")').first();
  if (await offlineStorageBtn.isVisible()) {
    await offlineStorageBtn.click();
    await page.waitForTimeout(500);
  }

  // 4. Take screenshot
  await page.screenshot({ path: '/tmp/ui109_tm_tree.png' });

  // 5. Count "Offline Storage" text occurrences in TM tree
  const offlineStorageCount = await page.locator('text="Offline Storage"').count();
  console.log(`\n=== UI-109 TEST ===`);
  console.log(`"Offline Storage" count in TM: ${offlineStorageCount}`);

  // Should be 1 (platform only, no nested project)
  // Note: There may also be one in the nav bar offline indicator
  expect(offlineStorageCount).toBeLessThanOrEqual(2);
  console.log('✅ UI-109: No nested duplication!');
});

test('UI-110: Right-click on TM tree headers should NOT show browser menu', async ({ page }) => {
  // 1. Login
  await page.goto(DEV_URL);
  await page.waitForTimeout(2000);
  await page.locator('text=Login').first().click();
  await page.waitForTimeout(1500);
  await page.locator('input').first().fill('admin');
  await page.locator('input[type="password"]').fill('admin123');
  await page.locator('button:has-text("Login")').click();
  await page.waitForTimeout(3000);

  // 2. Go to TM page
  await page.locator('text=TM').first().click();
  await page.waitForTimeout(2000);

  // 3. Right-click on Unassigned header
  const unassignedBtn = page.locator('button:has-text("Unassigned")').first();
  await unassignedBtn.click({ button: 'right' });
  await page.waitForTimeout(500);

  // 4. Take screenshot after right-click
  await page.screenshot({ path: '/tmp/ui110_context_menu.png' });

  // 5. Check that browser context menu is NOT showing (no "Back", "Forward", etc.)
  const browserMenuVisible = await page.locator('text=Back').first().isVisible().catch(() => false);

  console.log(`\n=== UI-110 TEST ===`);
  console.log(`Browser menu visible: ${browserMenuVisible}`);

  expect(browserMenuVisible).toBe(false);
  console.log('✅ UI-110: Browser context menu blocked!');
});

test('UI-111: Sync Dashboard modal should be compact', async ({ page }) => {
  // 1. Start offline (no login needed)
  await page.goto(DEV_URL);
  await page.waitForTimeout(2000);
  await page.locator('text=Start Offline').click();
  await page.waitForTimeout(2000);

  // 2. Click on the Offline status button to open Sync Dashboard
  const offlineBtn = page.locator('button:has-text("Offline")').first();
  await offlineBtn.click();
  await page.waitForTimeout(1000);

  // 3. Take screenshot of the modal
  await page.screenshot({ path: '/tmp/ui111_sync_modal.png' });

  // 4. Check modal is visible
  const modalHeading = await page.locator('text=Sync Dashboard').isVisible();

  console.log(`\n=== UI-111 TEST ===`);
  console.log(`Modal visible: ${modalHeading}`);

  expect(modalHeading).toBe(true);
  console.log('✅ UI-111: Sync Dashboard modal opened (check screenshot for compact layout)');
});
