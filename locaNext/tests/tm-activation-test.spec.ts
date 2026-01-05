import { test, expect } from '@playwright/test';

/**
 * TM Activation Test
 * Tests activating a TM assigned to Offline Storage
 */

test('Activate TM assigned to Offline Storage', async ({ page }) => {
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

  // Expand Offline Storage
  await page.locator('text=Offline Storage').first().click();
  await page.waitForTimeout(500);

  // Take initial screenshot
  await page.screenshot({ path: '/tmp/tm_activate_01_initial.png', fullPage: true });

  // Find TM in Offline Storage and right-click
  const offlineSection = page.locator('.tree-section:has-text("Offline Storage")');
  const tmInOffline = offlineSection.locator('.tm-item').first();
  const tmCount = await offlineSection.locator('.tm-item').count();
  console.log('TMs in Offline Storage:', tmCount);

  if (tmCount > 0) {
    const tmText = await tmInOffline.textContent();
    console.log('TM to activate:', tmText);

    // Right-click to get context menu
    await tmInOffline.click({ button: 'right' });
    await page.waitForTimeout(500);

    // Take screenshot of context menu
    await page.screenshot({ path: '/tmp/tm_activate_02_context.png', fullPage: true });

    // Click Activate
    const activateBtn = page.locator('text=Activate');
    if (await activateBtn.isVisible()) {
      await activateBtn.click();
      await page.waitForTimeout(1000);
      console.log('Clicked Activate');
    } else {
      console.log('Activate button not visible (TM may already be active)');
    }

    // Take screenshot after activation
    await page.screenshot({ path: '/tmp/tm_activate_03_after.png', fullPage: true });

    // Check if TM is now active (should have green checkmark)
    const activeTM = offlineSection.locator('.tm-item.active');
    const activeCount = await activeTM.count();
    console.log('Active TMs in Offline Storage:', activeCount);
  } else {
    console.log('No TMs in Offline Storage to activate');
  }
});
