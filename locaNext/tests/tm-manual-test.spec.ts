import { test } from '@playwright/test';

/**
 * Manual TM Test - Takes screenshots at each step for user verification
 */

test('Manual TM Assignment Walkthrough', async ({ page }) => {
  // Step 1: Login
  await page.goto('http://localhost:5173');
  await page.waitForTimeout(1000);
  await page.screenshot({ path: '/tmp/manual_01_landing.png', fullPage: true });

  await page.getByRole('button', { name: /login/i }).click();
  await page.waitForTimeout(1000);
  await page.getByPlaceholder('Enter username').fill('admin');
  await page.getByPlaceholder('Enter password').fill('admin123');
  await page.getByRole('button', { name: /login/i }).last().click();
  await page.waitForTimeout(3000);
  await page.screenshot({ path: '/tmp/manual_02_logged_in.png', fullPage: true });

  // Step 2: Go to TM tab
  await page.locator('text=TM').first().click();
  await page.waitForTimeout(2000);
  await page.screenshot({ path: '/tmp/manual_03_tm_page.png', fullPage: true });

  // Step 3: Show current state - expand Offline Storage
  const offlineStorage = page.locator('text=Offline Storage').first();
  await offlineStorage.click();
  await page.waitForTimeout(500);
  await page.screenshot({ path: '/tmp/manual_04_offline_expanded.png', fullPage: true });

  // Step 4: Drag a TM from Unassigned to Offline Storage
  const unassignedTMs = page.locator('.tree-section:has-text("Unassigned") .tm-item');
  const tmCount = await unassignedTMs.count();
  console.log('Unassigned TMs:', tmCount);

  if (tmCount > 0) {
    const firstTM = unassignedTMs.first();
    const tmName = await firstTM.textContent();
    console.log('Dragging TM:', tmName);

    const tmBox = await firstTM.boundingBox();
    const offlineBox = await offlineStorage.boundingBox();

    if (tmBox && offlineBox) {
      // Perform drag
      await page.mouse.move(tmBox.x + tmBox.width / 2, tmBox.y + tmBox.height / 2);
      await page.mouse.down();
      await page.mouse.move(offlineBox.x + offlineBox.width / 2, offlineBox.y + offlineBox.height / 2, { steps: 10 });
      await page.screenshot({ path: '/tmp/manual_05_dragging.png', fullPage: true });
      await page.mouse.up();
      await page.waitForTimeout(1000);
    }
  }

  // Step 5: Show result after drag
  await page.screenshot({ path: '/tmp/manual_06_after_drag.png', fullPage: true });

  // Step 6: Right-click on TM in Offline Storage to show context menu
  const offlineSection = page.locator('.tree-section:has-text("Offline Storage")');
  const tmsInOffline = offlineSection.locator('.tm-item');
  const offlineTMCount = await tmsInOffline.count();
  console.log('TMs in Offline Storage:', offlineTMCount);

  if (offlineTMCount > 0) {
    await tmsInOffline.first().click({ button: 'right' });
    await page.waitForTimeout(500);
    await page.screenshot({ path: '/tmp/manual_07_context_menu.png', fullPage: true });

    // Click Activate
    const activateBtn = page.locator('.context-menu button:has-text("Activate")');
    if (await activateBtn.isVisible()) {
      await activateBtn.click();
      await page.waitForTimeout(1000);
      await page.screenshot({ path: '/tmp/manual_08_activated.png', fullPage: true });
    }
  }

  console.log('Test complete - check /tmp/manual_*.png screenshots');
});
