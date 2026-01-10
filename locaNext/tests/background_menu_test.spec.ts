/**
 * Test: Right-click on empty space shows Upload TM option
 */
import { test, expect } from '@playwright/test';

test('Right-click on empty space in TM grid shows Upload TM', async ({ page }) => {
  await page.goto('http://localhost:5173');
  await page.waitForTimeout(2000);

  // Login
  await page.locator('button:has-text("Login")').first().click();
  await page.waitForTimeout(1000);
  await page.locator('input[placeholder="Enter username"]').fill('admin');
  await page.locator('input[placeholder="Enter password"]').fill('admin123');
  await page.locator('button:has-text("Login")').last().click();
  await page.waitForTimeout(2500);

  // Go to TM
  await page.locator('text=TM').first().click();
  await page.waitForTimeout(1500);

  // Enter Offline Storage
  await page.locator('.grid-row').first().dblclick();
  await page.waitForTimeout(1000);

  // Right-click on empty area (use specific selector for TM grid)
  await page.locator('.tm-explorer-grid .empty-state').click({ button: 'right' });
  await page.waitForTimeout(500);

  // Screenshot
  await page.screenshot({ path: '/tmp/background_context_menu.png' });

  // Check Upload TM option in context menu
  const uploadOption = page.locator('.context-menu .context-item:has-text("Upload TM")');
  await expect(uploadOption).toBeVisible();

  console.log('SUCCESS: Upload TM option visible on right-click!');
});
