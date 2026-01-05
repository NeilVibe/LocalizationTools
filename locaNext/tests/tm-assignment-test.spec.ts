import { test, expect } from '@playwright/test';

/**
 * TM Assignment to Offline Storage Test
 * Tests drag-and-drop TM assignment
 */

test('Drag and drop TM to Offline Storage', async ({ page }) => {
  // Login
  await page.goto('http://localhost:5173');
  await page.waitForTimeout(1000);
  await page.getByRole('button', { name: /login/i }).click();
  await page.waitForTimeout(1000);
  await page.getByPlaceholder('Enter username').fill('admin');
  await page.getByPlaceholder('Enter password').fill('admin123');
  await page.getByRole('button', { name: /login/i }).last().click();
  await page.waitForTimeout(3000);

  // Go to TM tab
  await page.locator('text=TM').first().click();
  await page.waitForTimeout(2000);

  // Take initial screenshot
  await page.screenshot({ path: '/tmp/tm_drag_01_initial.png', fullPage: true });

  // Get first TM in Unassigned
  const unassignedTM = page.locator('.tm-item').first();
  const tmBox = await unassignedTM.boundingBox();
  console.log('TM bounding box:', tmBox);

  // Get Offline Storage header
  const offlineStorage = page.locator('text=Offline Storage').first();
  const offlineBox = await offlineStorage.boundingBox();
  console.log('Offline Storage bounding box:', offlineBox);

  if (tmBox && offlineBox) {
    // Drag from TM to Offline Storage
    await page.mouse.move(tmBox.x + tmBox.width / 2, tmBox.y + tmBox.height / 2);
    await page.mouse.down();
    await page.mouse.move(offlineBox.x + offlineBox.width / 2, offlineBox.y + offlineBox.height / 2, { steps: 10 });

    // Take screenshot during drag
    await page.screenshot({ path: '/tmp/tm_drag_02_dragging.png', fullPage: true });

    await page.mouse.up();
    await page.waitForTimeout(1000);

    // Take screenshot after drop
    await page.screenshot({ path: '/tmp/tm_drag_03_after_drop.png', fullPage: true });

    // Expand Offline Storage to see if TM was moved there
    await offlineStorage.click();
    await page.waitForTimeout(500);

    // Take final screenshot
    await page.screenshot({ path: '/tmp/tm_drag_04_expanded.png', fullPage: true });

    // Check if Offline Storage now has any TMs
    const offlineSection = page.locator('.tree-section:has-text("Offline Storage")');
    const tmsInOffline = await offlineSection.locator('.tm-item').count();
    console.log('TMs in Offline Storage:', tmsInOffline);
  }
});
