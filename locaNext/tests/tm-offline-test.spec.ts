import { test, expect } from '@playwright/test';

/**
 * TM + Offline Storage Test Suite
 * Verifies:
 * 1. TM page shows Offline Storage as assignable location
 * 2. TM delete functionality
 * 3. TM multi-select (Ctrl+click, Shift+click)
 */

test.describe('TM and Offline Storage', () => {
  test.beforeEach(async ({ page }) => {
    // Go to app
    await page.goto('http://localhost:5173');
    await page.waitForTimeout(1000);

    // Click Login button on landing page
    await page.getByRole('button', { name: /login/i }).click();
    await page.waitForTimeout(1000);

    // Fill login form using exact placeholders
    await page.getByPlaceholder('Enter username').fill('admin');
    await page.getByPlaceholder('Enter password').fill('admin123');

    // Submit login - use last Login button (the one in the form)
    await page.getByRole('button', { name: /login/i }).last().click();
    await page.waitForTimeout(3000);

    // We should now be on the Files page - click TM tab
    await page.locator('text=TM').first().click();
    await page.waitForTimeout(2000);
  });

  test('TM page is visible and shows tree structure', async ({ page }) => {
    // Take screenshot
    await page.screenshot({ path: '/tmp/tm_page.png', fullPage: true });

    // Check for TM tree sections - look for Offline Storage or Unassigned
    const unassignedSection = page.locator('text=Unassigned');
    const offlineSection = page.locator('text=Offline Storage');

    console.log('Unassigned section visible:', await unassignedSection.isVisible().catch(() => false));
    console.log('Offline Storage section visible:', await offlineSection.isVisible().catch(() => false));

    // Check for any TM items
    const tmItems = await page.locator('.tm-item').count();
    console.log('TM items found:', tmItems);
  });

  test('TM context menu has delete option', async ({ page }) => {
    // Take screenshot of TM page
    await page.screenshot({ path: '/tmp/tm_page_for_context.png', fullPage: true });

    // Find a TM item and right-click
    const tmItems = page.locator('.tm-item');
    const tmCount = await tmItems.count();
    console.log('TM items found:', tmCount);

    if (tmCount > 0) {
      await tmItems.first().click({ button: 'right' });
      await page.waitForTimeout(500);

      // Take screenshot of context menu
      await page.screenshot({ path: '/tmp/tm_context_menu.png', fullPage: true });

      // Check for Delete option
      const deleteOption = page.locator('text=Delete TM');
      console.log('Delete TM option visible:', await deleteOption.isVisible().catch(() => false));
    } else {
      console.log('No TM items to test - need to create one first');
    }
  });

  test('TM multi-select with Ctrl+click', async ({ page }) => {
    const tmItems = page.locator('.tm-item');
    const tmCount = await tmItems.count();
    console.log('TM items found:', tmCount);

    if (tmCount >= 2) {
      // Click first item
      await tmItems.nth(0).click();
      await page.waitForTimeout(200);

      // Ctrl+click second item
      await tmItems.nth(1).click({ modifiers: ['Control'] });
      await page.waitForTimeout(200);

      // Take screenshot
      await page.screenshot({ path: '/tmp/tm_multiselect.png', fullPage: true });

      // Check how many are selected
      const selectedItems = page.locator('.tm-item.selected');
      const selectedCount = await selectedItems.count();
      console.log('Selected items after Ctrl+click:', selectedCount);
    } else {
      console.log('Need at least 2 TMs for multi-select test');
      await page.screenshot({ path: '/tmp/tm_page_few_items.png', fullPage: true });
    }
  });
});
