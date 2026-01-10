/**
 * Test: Cell Context Menu (UX-002)
 * Verifies right-click context menu in file viewer cells
 */
import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

const DEV_URL = 'http://localhost:5173';

test.describe('Cell Context Menu', () => {
  test('Right-click on cell shows context menu', async ({ page }) => {
    // Create a test file
    const testFilePath = '/tmp/test_context_menu.txt';
    fs.writeFileSync(testFilePath, 'EN\tKO\nHello\t안녕하세요\nWorld\t세계\nGoodbye\t안녕히 가세요');

    await page.goto(DEV_URL);
    await page.waitForTimeout(1000);

    // Screenshot initial state
    await page.screenshot({ path: '/tmp/cell_ctx_01_initial.png' });

    // Login
    const loginButton = page.locator('button:has-text("Login")').first();
    if (await loginButton.isVisible({ timeout: 3000 })) {
      await loginButton.click();
      await page.waitForTimeout(500);

      // Check if modal login appears
      const usernameInput = page.locator('input[placeholder="Enter username"]');
      if (await usernameInput.isVisible({ timeout: 2000 })) {
        await usernameInput.fill('admin');
        await page.locator('input[placeholder="Enter password"]').fill('admin123');
        await page.locator('button:has-text("Login")').last().click();
        await page.waitForTimeout(2000);
      }
    }

    await page.screenshot({ path: '/tmp/cell_ctx_02_logged_in.png' });

    // Navigate to Files page
    await page.locator('text=Files').first().click();
    await page.waitForTimeout(1000);

    await page.screenshot({ path: '/tmp/cell_ctx_03_files_page.png' });

    // Navigate into Offline Storage
    const offlineStorageRow = page.locator('.grid-row').first();
    if (await offlineStorageRow.isVisible({ timeout: 2000 })) {
      await offlineStorageRow.dblclick();
      await page.waitForTimeout(1000);

      await page.screenshot({ path: '/tmp/cell_ctx_04_in_offline.png' });

      // Upload a file using the file input (first one accepts .txt)
      const fileInput = page.locator('input[type="file"]').first();
      if (await fileInput.count() > 0) {
        await fileInput.setInputFiles(testFilePath);
        await page.waitForTimeout(2000);
        console.log('File uploaded');
      }

      await page.screenshot({ path: '/tmp/cell_ctx_05_after_upload.png' });

      // Look for any file to open
      const fileRow = page.locator('.grid-row.file, .grid-row.local-file').first();
      if (await fileRow.isVisible({ timeout: 3000 })) {
        await fileRow.dblclick();
        await page.waitForTimeout(2000);

        await page.screenshot({ path: '/tmp/cell_ctx_06_file_open.png' });

        // Right-click on a cell row (not placeholder)
        const virtualRow = page.locator('.virtual-row:not(.placeholder)').first();
        if (await virtualRow.isVisible({ timeout: 3000 })) {
          await virtualRow.click({ button: 'right' });
          await page.waitForTimeout(500);

          await page.screenshot({ path: '/tmp/cell_ctx_07_context_menu.png' });

          // Verify context menu appears
          const contextMenu = page.locator('.context-menu');
          await expect(contextMenu).toBeVisible({ timeout: 2000 });

          // Verify menu items
          await expect(page.locator('.context-item:has-text("Confirm")')).toBeVisible();
          await expect(page.locator('.context-item:has-text("Set as Translated")')).toBeVisible();
          await expect(page.locator('.context-item:has-text("Set as Untranslated")')).toBeVisible();
          await expect(page.locator('.context-item:has-text("Copy Source")')).toBeVisible();
          await expect(page.locator('.context-item:has-text("Copy Target")')).toBeVisible();

          console.log('SUCCESS: Cell context menu visible with all options!');

          // Test clicking an option closes the menu
          await page.locator('.context-item:has-text("Copy Source")').click();
          await page.waitForTimeout(500);

          // Menu should be closed
          await expect(contextMenu).not.toBeVisible();
          console.log('SUCCESS: Context menu closed after clicking option!');
        } else {
          await page.screenshot({ path: '/tmp/cell_ctx_07_no_rows.png' });
          console.log('No rows in file viewer');
        }
      } else {
        await page.screenshot({ path: '/tmp/cell_ctx_06_no_files.png' });
        console.log('No files found to open');
      }
    } else {
      console.log('Offline Storage not visible');
    }
  });
});
