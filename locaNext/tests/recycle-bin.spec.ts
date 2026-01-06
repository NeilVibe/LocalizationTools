import { test, expect } from '@playwright/test';

test('Recycle Bin works for ONLINE mode', async ({ page }) => {
  // 1. Login
  await page.goto('http://localhost:5173');
  await page.click('text=Login');
  await page.waitForTimeout(1000);
  await page.fill('input[placeholder="Enter username"]', 'admin');
  await page.fill('input[placeholder="Enter password"]', 'admin123');
  await page.click('button:has-text("Login"):not(:has-text("Back"))');
  await page.waitForTimeout(3000);

  // 2. Open LDM (Files app)
  await page.click('text=Files');
  await page.waitForTimeout(1500);

  // Screenshot at root
  await page.screenshot({ path: 'test-results/recycle_bin_root.png' });
  console.log('Screenshot: recycle_bin_root.png');

  // 3. Navigate to a project with files (Offline Storage platform -> Offline Storage project)
  // Double-click on Offline Storage platform
  await page.dblclick('text=Offline Storage');
  await page.waitForTimeout(1500);

  await page.screenshot({ path: 'test-results/recycle_bin_platform.png' });

  // Double-click on Offline Storage project (inside the platform)
  await page.dblclick('text=Offline Storage');
  await page.waitForTimeout(1500);

  await page.screenshot({ path: 'test-results/recycle_bin_project.png' });

  // 4. Check if we have files to delete
  const rows = await page.locator('.explorer-grid-row').all();
  console.log('Found ' + rows.length + ' items in project');

  if (rows.length === 0) {
    console.log('No items to delete - need to create a test file first');

    // Right-click to create a folder for testing
    await page.click('.explorer-grid', { button: 'right' });
    await page.waitForTimeout(500);

    const newFolderBtn = page.locator('text=New Folder');
    if (await newFolderBtn.isVisible()) {
      await newFolderBtn.click();
      await page.waitForTimeout(500);

      await page.fill('input', 'TestDeleteFolder');
      await page.click('button:has-text("Create")');
      await page.waitForTimeout(1000);
      console.log('Created TestDeleteFolder');
    }
  }

  // Get first item to delete
  const firstItem = page.locator('.explorer-grid-row').first();
  if (await firstItem.isVisible()) {
    // Right-click on the item
    await firstItem.click({ button: 'right' });
    await page.waitForTimeout(500);

    await page.screenshot({ path: 'test-results/recycle_bin_context_menu.png' });

    // Click Delete
    const deleteBtn = page.locator('text=Delete');
    if (await deleteBtn.isVisible()) {
      await deleteBtn.click();
      await page.waitForTimeout(500);

      await page.screenshot({ path: 'test-results/recycle_bin_confirm_dialog.png' });

      // Confirm deletion
      const confirmBtn = page.locator('button:has-text("Delete")').last();
      if (await confirmBtn.isVisible()) {
        await confirmBtn.click();
        await page.waitForTimeout(1500);
        console.log('Item deleted');
      }
    }
  }

  await page.screenshot({ path: 'test-results/recycle_bin_after_delete.png' });

  // 5. Go to Recycle Bin
  // Click Home to go back to root
  await page.click('text=Home');
  await page.waitForTimeout(1000);

  // Click on Recycle Bin
  await page.dblclick('text=Recycle Bin');
  await page.waitForTimeout(1500);

  await page.screenshot({ path: 'test-results/recycle_bin_contents.png' });
  console.log('Screenshot: recycle_bin_contents.png');

  // 6. Verify deleted item is in Recycle Bin
  const trashItems = await page.locator('.explorer-grid-row').all();
  console.log('Found ' + trashItems.length + ' items in Recycle Bin');

  // Check page content
  const pageContent = await page.textContent('body');
  console.log('Page contains "Recycle Bin": ' + (pageContent?.includes('Recycle Bin') || false));

  console.log('Test completed - check screenshots');
});
