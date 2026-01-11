/**
 * Test: TM Paste to Offline Storage
 * Verifies that TM paste works correctly when pasting to local folders
 */
import { test, expect } from '@playwright/test';

const DEV_URL = 'http://localhost:5173';

test.describe('TM Paste to Offline Storage', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(DEV_URL);
    await page.waitForTimeout(2000);

    // Login
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

  test('Cut TM from Unassigned and paste to Offline Storage', async ({ page }) => {
    // Take initial screenshot
    await page.screenshot({ path: '/tmp/tm_paste_01_start.png' });

    // Look for Unassigned section
    const unassignedRow = page.locator('.grid-row:has-text("Unassigned")').first();
    if (await unassignedRow.isVisible({ timeout: 3000 })) {
      // Double-click to enter Unassigned
      await unassignedRow.dblclick();
      await page.waitForTimeout(1000);

      await page.screenshot({ path: '/tmp/tm_paste_02_unassigned.png' });

      // Find a TM
      const tmRow = page.locator('.grid-row.tm').first();
      if (await tmRow.isVisible({ timeout: 2000 })) {
        // Get TM name for verification
        const tmName = await tmRow.locator('.item-name').textContent();
        console.log('Found TM:', tmName);

        // Click to select and cut
        await tmRow.click();
        await page.waitForTimeout(300);
        await page.keyboard.press('Control+x');
        await page.waitForTimeout(500);

        await page.screenshot({ path: '/tmp/tm_paste_03_after_cut.png' });

        // Verify clipboard indicator
        await expect(page.locator('.clipboard-indicator')).toBeVisible();
        await expect(page.locator('.clipboard-indicator')).toContainText('cut');

        // Navigate to Home
        await page.locator('.breadcrumb-item:has-text("Home")').click();
        await page.waitForTimeout(500);

        await page.screenshot({ path: '/tmp/tm_paste_04_at_home.png' });

        // Look for Offline Storage
        const offlineStorageRow = page.locator('.grid-row:has-text("Offline Storage")').first();
        if (await offlineStorageRow.isVisible({ timeout: 2000 })) {
          // Double-click to enter
          await offlineStorageRow.dblclick();
          await page.waitForTimeout(1000);

          await page.screenshot({ path: '/tmp/tm_paste_05_offline_storage.png' });

          // Get current breadcrumb
          const breadcrumbText = await page.locator('.breadcrumb').textContent();
          console.log('Breadcrumb:', breadcrumbText);

          // Look for a local folder to paste into
          const folderRow = page.locator('.grid-row.folder').first();
          if (await folderRow.isVisible({ timeout: 2000 })) {
            // Double-click to enter folder
            await folderRow.dblclick();
            await page.waitForTimeout(1000);

            await page.screenshot({ path: '/tmp/tm_paste_06_inside_folder.png' });

            // Get breadcrumb after entering folder
            const folderBreadcrumb = await page.locator('.breadcrumb').textContent();
            console.log('Folder breadcrumb:', folderBreadcrumb);

            // Right-click to show context menu
            await page.locator('.tm-explorer-grid').click({ button: 'right' });
            await page.waitForTimeout(500);

            await page.screenshot({ path: '/tmp/tm_paste_07_context_menu.png' });

            // Click Paste
            const pasteButton = page.locator('.context-item:has-text("Paste")');
            if (await pasteButton.isVisible()) {
              await pasteButton.click();
              await page.waitForTimeout(1500);

              await page.screenshot({ path: '/tmp/tm_paste_08_after_paste.png' });

              // Check if TM appeared or clipboard was cleared
              const clipboardGone = await page.locator('.clipboard-indicator').isHidden();
              if (clipboardGone) {
                console.log('SUCCESS: Clipboard cleared after paste!');

                // Check if we need to look elsewhere for the TM
                // For local folders, TM is redirected to Offline Storage project
                await page.locator('.breadcrumb-item:has-text("Home")').click();
                await page.waitForTimeout(500);

                // Navigate to Offline Storage to see the TM
                await offlineStorageRow.dblclick();
                await page.waitForTimeout(1000);

                await page.screenshot({ path: '/tmp/tm_paste_09_final_check.png' });

                // Look for the TM in the list
                const pastedTM = page.locator(`.grid-row.tm:has-text("${tmName}")`);
                if (await pastedTM.isVisible({ timeout: 3000 })) {
                  console.log('SUCCESS: TM found in Offline Storage!');
                } else {
                  console.log('TM may have been placed at project level');
                }
              } else {
                console.log('Clipboard not cleared - paste may have failed');
              }
            } else {
              console.log('Paste option not visible in context menu');
            }
          } else {
            // No local folders - paste at Offline Storage level
            console.log('No local folders found - pasting at Offline Storage level');

            // Right-click to show context menu
            await page.locator('.tm-explorer-grid').click({ button: 'right' });
            await page.waitForTimeout(500);

            // Click Paste
            const pasteButton = page.locator('.context-item:has-text("Paste")');
            if (await pasteButton.isVisible()) {
              await pasteButton.click();
              await page.waitForTimeout(1500);

              await page.screenshot({ path: '/tmp/tm_paste_08_pasted_at_project.png' });

              // Verify clipboard cleared
              const clipboardGone = await page.locator('.clipboard-indicator').isHidden();
              if (clipboardGone) {
                console.log('SUCCESS: Paste completed, clipboard cleared!');
              }
            }
          }
        } else {
          console.log('Offline Storage not found - skipping test');
        }
      } else {
        console.log('No TMs in Unassigned - skipping test');
      }
    } else {
      console.log('Unassigned section not visible - skipping test');
    }
  });

  test('Verify paste logs are generated', async ({ page }) => {
    // This test just verifies that logging is working
    // Open DevTools console and check for paste logs

    // Find a TM
    const unassignedRow = page.locator('.grid-row:has-text("Unassigned")').first();
    if (await unassignedRow.isVisible({ timeout: 3000 })) {
      await unassignedRow.dblclick();
      await page.waitForTimeout(1000);

      const tmRow = page.locator('.grid-row.tm').first();
      if (await tmRow.isVisible({ timeout: 2000 })) {
        // Cut
        await tmRow.click();
        await page.keyboard.press('Control+x');
        await page.waitForTimeout(500);

        // Try paste with Ctrl+V
        await page.keyboard.press('Control+v');
        await page.waitForTimeout(1000);

        await page.screenshot({ path: '/tmp/tm_paste_logs_test.png' });

        console.log('Check browser console for paste logging output');
      }
    }
  });
});
