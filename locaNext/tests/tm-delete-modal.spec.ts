/**
 * TM Delete Modal Test
 *
 * Verifies that TM deletion uses a clean Svelte 5 modal
 * instead of ugly browser confirm().
 */
import { test, expect } from '@playwright/test';

test.describe('TM Delete Modal', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to app
    await page.goto('http://localhost:5173');
    await page.waitForTimeout(1000);

    // Click Login button on P9 launcher screen
    await page.getByRole('button', { name: /login/i }).click();
    await page.waitForTimeout(1000);

    // Fill login form using exact placeholders
    await page.getByPlaceholder('Enter username').fill('admin');
    await page.getByPlaceholder('Enter password').fill('admin123');

    // Submit login - use last Login button (the one in the form)
    await page.getByRole('button', { name: /login/i }).last().click();
    await page.waitForTimeout(3000);

    // Click TM tab
    await page.locator('text=TM').first().click();
    await page.waitForTimeout(2000);
  });

  test('Delete TM shows Carbon modal, not browser confirm', async ({ page }) => {
    // Find a TM item
    const tmItems = page.locator('.tm-item');
    const count = await tmItems.count();
    console.log('TM items found:', count);

    if (count === 0) {
      test.skip();
      return;
    }

    // Right-click to open context menu
    await tmItems.first().click({ button: 'right' });
    await page.waitForTimeout(500);

    // Click Delete TM option
    const deleteOption = page.locator('.context-menu-item.danger', { hasText: 'Delete TM' });
    if (await deleteOption.isVisible()) {
      await deleteOption.click();
      await page.waitForTimeout(500);

      // Verify Carbon Modal appears (not browser confirm)
      // Use .is-visible class since multiple modals exist on page
      const carbonModal = page.locator('.bx--modal.is-visible');
      const isModalVisible = await carbonModal.isVisible({ timeout: 2000 }).catch(() => false);
      console.log('Carbon Modal visible:', isModalVisible);
      expect(isModalVisible).toBe(true);

      // Verify modal has proper content
      const modalHeading = carbonModal.locator('.bx--modal-header__heading');
      await expect(modalHeading).toContainText('Delete Translation Memory');

      // Take screenshot to verify modal appearance
      await page.screenshot({ path: '/tmp/tm_delete_modal.png', fullPage: true });

      // Verify Cancel button exists
      const cancelButton = carbonModal.locator('button', { hasText: 'Cancel' });
      expect(await cancelButton.isVisible()).toBe(true);

      // Click Cancel to close modal (don't actually delete)
      await cancelButton.click();
      await page.waitForTimeout(300);
    }
  });

  test('Multi-select delete shows count in modal', async ({ page }) => {
    // Find TM items
    const tmItems = page.locator('.tm-item');
    const count = await tmItems.count();

    if (count < 2) {
      test.skip();
      return;
    }

    // Ctrl+click to select multiple TMs
    await tmItems.nth(0).click();
    await tmItems.nth(1).click({ modifiers: ['Control'] });
    await page.waitForTimeout(300);

    // Right-click for context menu
    await tmItems.nth(1).click({ button: 'right' });
    await page.waitForTimeout(500);

    // Look for multi-select delete option
    const deleteAllOption = page.locator('.context-menu-item.danger', { hasText: 'Delete All Selected' });
    if (await deleteAllOption.isVisible()) {
      await deleteAllOption.click();
      await page.waitForTimeout(500);

      // Verify Carbon Modal appears (use .is-visible for visible modal)
      const carbonModal = page.locator('.bx--modal.is-visible');
      expect(await carbonModal.isVisible({ timeout: 2000 })).toBe(true);

      // Verify heading mentions multiple TMs
      const modalHeading = carbonModal.locator('.bx--modal-header__heading');
      await expect(modalHeading).toContainText('Delete Selected Translation Memories');

      // Take screenshot of multi-select modal
      await page.screenshot({ path: '/tmp/tm_multiselect_delete_modal.png', fullPage: true });

      // Cancel to not delete
      const cancelButton = carbonModal.locator('button', { hasText: 'Cancel' });
      await cancelButton.click();
    }
  });
});
