/**
 * Test: TM Clipboard Operations (UX-003)
 * Verifies Cut/Copy/Paste for TMs in TM Explorer
 */
import { test, expect } from '@playwright/test';

const DEV_URL = 'http://localhost:5173';

test.describe('TM Clipboard Operations', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(DEV_URL);
    await page.waitForTimeout(2000);

    // Login (using working pattern from background_menu_test)
    await page.locator('button:has-text("Login")').first().click();
    await page.waitForTimeout(1000);
    await page.locator('input[placeholder="Enter username"]').fill('admin');
    await page.locator('input[placeholder="Enter password"]').fill('admin123');
    await page.locator('button:has-text("Login")').last().click();
    await page.waitForTimeout(2500);

    // Navigate to TM page
    await page.locator('text=TM').first().click();
    await page.waitForTimeout(1500);
  });

  test('Right-click TM shows Cut/Copy options', async ({ page }) => {
    await page.screenshot({ path: '/tmp/tm_clip_01_tm_page.png' });

    // Find a TM row
    const tmRow = page.locator('.grid-row.tm').first();
    if (await tmRow.isVisible({ timeout: 3000 })) {
      // Right-click on TM
      await tmRow.click({ button: 'right' });
      await page.waitForTimeout(500);

      await page.screenshot({ path: '/tmp/tm_clip_02_context_menu.png' });

      // Verify Cut/Copy options
      await expect(page.locator('.context-item:has-text("Cut")')).toBeVisible();
      await expect(page.locator('.context-item:has-text("Copy")')).toBeVisible();

      console.log('SUCCESS: Cut/Copy options visible in context menu!');
    } else {
      // Navigate into a platform to find TMs
      const platformRow = page.locator('.grid-row.platform, .grid-row:not(.tm)').first();
      if (await platformRow.isVisible({ timeout: 2000 })) {
        await platformRow.dblclick();
        await page.waitForTimeout(1000);

        await page.screenshot({ path: '/tmp/tm_clip_02_inside_platform.png' });

        // Try to find TMs again
        const tmRowInPlatform = page.locator('.grid-row.tm').first();
        if (await tmRowInPlatform.isVisible({ timeout: 2000 })) {
          await tmRowInPlatform.click({ button: 'right' });
          await page.waitForTimeout(500);

          await page.screenshot({ path: '/tmp/tm_clip_03_context_menu.png' });

          await expect(page.locator('.context-item:has-text("Cut")')).toBeVisible();
          console.log('SUCCESS: Cut option found!');
        } else {
          console.log('No TMs found to test');
        }
      }
    }
  });

  test('Ctrl+X cuts TM and shows clipboard indicator', async ({ page }) => {
    // Find and select a TM
    const tmRow = page.locator('.grid-row.tm').first();

    // Navigate to find TMs if not visible at home
    if (!await tmRow.isVisible({ timeout: 2000 })) {
      const platformRow = page.locator('.grid-row:not(.tm)').first();
      if (await platformRow.isVisible()) {
        await platformRow.dblclick();
        await page.waitForTimeout(1000);
      }
    }

    const tmRowFound = page.locator('.grid-row.tm').first();
    if (await tmRowFound.isVisible({ timeout: 3000 })) {
      // Click to select
      await tmRowFound.click();
      await page.waitForTimeout(300);

      // Press Ctrl+X to cut
      await page.keyboard.press('Control+x');
      await page.waitForTimeout(500);

      await page.screenshot({ path: '/tmp/tm_clip_04_after_cut.png' });

      // Verify clipboard indicator appears
      const clipboardIndicator = page.locator('.clipboard-indicator');
      await expect(clipboardIndicator).toBeVisible();
      await expect(clipboardIndicator).toContainText('cut');

      // Verify TM has cut visual feedback
      await expect(tmRowFound).toHaveClass(/cut/);

      console.log('SUCCESS: TM cut, clipboard indicator visible!');
    } else {
      console.log('No TMs found to test cut');
    }
  });

  test('Escape clears clipboard', async ({ page }) => {
    // Find and select a TM
    const tmRow = page.locator('.grid-row.tm').first();

    if (!await tmRow.isVisible({ timeout: 2000 })) {
      const platformRow = page.locator('.grid-row:not(.tm)').first();
      if (await platformRow.isVisible()) {
        await platformRow.dblclick();
        await page.waitForTimeout(1000);
      }
    }

    const tmRowFound = page.locator('.grid-row.tm').first();
    if (await tmRowFound.isVisible({ timeout: 3000 })) {
      // Click to select and cut
      await tmRowFound.click();
      await page.keyboard.press('Control+x');
      await page.waitForTimeout(500);

      // Verify clipboard indicator
      await expect(page.locator('.clipboard-indicator')).toBeVisible();

      // Press Escape
      await page.keyboard.press('Escape');
      await page.waitForTimeout(300);

      await page.screenshot({ path: '/tmp/tm_clip_05_after_escape.png' });

      // Clipboard should be cleared
      await expect(page.locator('.clipboard-indicator')).not.toBeVisible();

      console.log('SUCCESS: Escape cleared clipboard!');
    } else {
      console.log('No TMs found to test');
    }
  });
});
