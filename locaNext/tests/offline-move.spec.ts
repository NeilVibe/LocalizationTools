import { test, expect } from '@playwright/test';

test('Offline Storage move files to folders', async ({ page }) => {
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

  // Screenshot at root to see all items
  await page.screenshot({ path: 'test-results/root_view.png' });

  // 3. Double-click the FIRST "Offline Storage" row (the virtual folder with cloud icon)
  // It's the first row in the grid (class is grid-row, not explorer-grid-row)
  const firstRow = page.locator('.grid-row').first();
  await firstRow.dblclick();
  await page.waitForTimeout(1500);

  // Screenshot inside Offline Storage
  await page.screenshot({ path: 'test-results/inside_offline_storage.png' });
  console.log('Screenshot: inside_offline_storage.png');

  // Check breadcrumb to confirm we're in the right place
  const breadcrumb = await page.textContent('.breadcrumb, [class*="breadcrumb"]') || '';
  console.log('Breadcrumb: ' + breadcrumb);

  // 4. Right-click to open context menu
  await page.click('.explorer-grid', { button: 'right' });
  await page.waitForTimeout(500);
  await page.screenshot({ path: 'test-results/context_menu.png' });

  // Check if New Folder button exists (proves we're in Offline Storage virtual folder)
  const newFolderBtn = page.locator('button:has-text("New Folder"), .context-menu-item:has-text("New Folder")');
  const hasNewFolder = await newFolderBtn.isVisible();
  console.log('Has New Folder button: ' + hasNewFolder);

  if (hasNewFolder) {
    await newFolderBtn.click();
    await page.waitForTimeout(500);

    // Fill folder name in modal - use specific placeholder
    const folderInput = page.locator('input[placeholder="Enter folder name"]');
    if (await folderInput.isVisible()) {
      await folderInput.fill('TestMoveFolder');
      // Click Create button in the visible modal (use .is-visible class for open modals)
      await page.locator('.bx--modal.is-visible button:has-text("Create")').click();
      await page.waitForTimeout(1000);
      console.log('Created TestMoveFolder');
    }
  } else {
    // Close context menu
    await page.keyboard.press('Escape');
    console.log('No New Folder button - may be in wrong location');
  }

  // Screenshot after folder creation
  await page.screenshot({ path: 'test-results/after_folder_create.png' });

  // 5. Look for items to drag
  const rows = await page.locator('.grid-row').all();
  console.log('Found ' + rows.length + ' items');

  // Check each row's class
  for (let i = 0; i < rows.length; i++) {
    const row = rows[i];
    const classList = await row.getAttribute('class') || '';
    const text = await row.locator('.item-name').first().textContent() || 'unknown';
    console.log('Row ' + i + ': ' + text.trim() + ' - classes: ' + classList);
  }

  // Find file and folder
  let fileRow = null;
  let folderRow = null;

  for (const row of rows) {
    const classList = await row.getAttribute('class') || '';
    if (classList.includes('file') && !fileRow) {
      fileRow = row;
    }
    if (classList.includes('folder') && !folderRow) {
      folderRow = row;
    }
  }

  if (fileRow && folderRow) {
    console.log('Found both file and folder, attempting drag-drop...');

    const fileBox = await fileRow.boundingBox();
    const folderBox = await folderRow.boundingBox();

    if (fileBox && folderBox) {
      await page.mouse.move(fileBox.x + fileBox.width / 2, fileBox.y + fileBox.height / 2);
      await page.mouse.down();
      await page.waitForTimeout(100);
      await page.mouse.move(folderBox.x + folderBox.width / 2, folderBox.y + folderBox.height / 2, { steps: 10 });
      await page.waitForTimeout(100);
      await page.mouse.up();
      await page.waitForTimeout(1000);

      console.log('Drag-drop completed');
    }
  } else {
    console.log('File found: ' + (fileRow ? 'yes' : 'no'));
    console.log('Folder found: ' + (folderRow ? 'yes' : 'no'));
  }

  // Final screenshot
  await page.screenshot({ path: 'test-results/after_move.png' });
  console.log('Test completed - check screenshots');
});
