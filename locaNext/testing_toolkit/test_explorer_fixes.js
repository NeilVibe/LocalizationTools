// Test for Windows Explorer fixes
// Tests: full width layout, context menu, button functions

import { chromium } from 'playwright';

const BASE_URL = 'http://localhost:5173';

async function testExplorerFixes() {
  console.log('Testing Explorer Fixes...\n');

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
  const page = await context.newPage();

  // Capture console
  page.on('console', msg => {
    if (msg.type() === 'error' && !msg.text().includes('favicon')) {
      console.log('  Console error:', msg.text().substring(0, 100));
    }
  });

  try {
    // 1. Login
    console.log('1. Logging in...');
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
    await page.waitForSelector('.bx--text-input', { timeout: 10000 });
    await page.locator('.bx--text-input').first().fill('admin');
    await page.locator('input[type=\"password\"]').fill('admin123');
    await page.click('button[type=\"submit\"]');
    await page.waitForSelector('.ldm-app', { timeout: 10000 });
    console.log('   OK');

    // 2. Check full width layout
    console.log('\n2. Checking full width layout...');
    await page.waitForTimeout(500);

    // Take screenshot at full resolution
    await page.screenshot({
      path: 'testing_toolkit/dev_tests/screenshots/explorer-fullwidth.png',
      fullPage: true
    });
    console.log('   Screenshot saved');

    // Check explorer grid width
    const gridWidth = await page.evaluate(() => {
      const grid = document.querySelector('.explorer-grid');
      return grid ? grid.getBoundingClientRect().width : 0;
    });
    const viewportWidth = 1920;
    console.log(`   Grid width: ${gridWidth}px (viewport: ${viewportWidth}px)`);
    console.log(`   Full width: ${gridWidth > viewportWidth * 0.8 ? 'YES' : 'NO - ISSUE!'}`);

    // 3. Test right-click on empty space (background context menu)
    console.log('\n3. Testing right-click on empty space...');

    // Right-click on the grid body background
    const gridBody = page.locator('.grid-body');
    if (await gridBody.isVisible()) {
      // Get bounding box and click in empty area
      const box = await gridBody.boundingBox();
      if (box) {
        // Click below the rows in empty space
        await page.mouse.click(box.x + box.width / 2, box.y + box.height - 50, { button: 'right' });
        await page.waitForTimeout(300);

        const bgContextMenu = await page.locator('.context-menu').isVisible().catch(() => false);
        console.log(`   Background context menu: ${bgContextMenu ? 'YES' : 'NO'}`);

        if (bgContextMenu) {
          // Check for New Project option (at root level)
          const hasNewProject = await page.locator('.context-menu-item:has-text("New Project")').isVisible().catch(() => false);
          const hasRefresh = await page.locator('.context-menu-item:has-text("Refresh")').isVisible().catch(() => false);
          console.log(`   - New Project option: ${hasNewProject ? 'YES' : 'NO'}`);
          console.log(`   - Refresh option: ${hasRefresh ? 'YES' : 'NO'}`);

          // Take screenshot
          await page.screenshot({
            path: 'testing_toolkit/dev_tests/screenshots/explorer-context-menu-bg.png',
            fullPage: true
          });
          console.log('   Context menu screenshot saved');

          // Close menu
          await page.keyboard.press('Escape');
        }
      }
    }

    // 4. Test right-click on item
    console.log('\n4. Testing right-click on item...');
    const firstRow = page.locator('.grid-row').first();
    if (await firstRow.isVisible()) {
      await firstRow.click({ button: 'right' });
      await page.waitForTimeout(300);

      const itemContextMenu = await page.locator('.context-menu').isVisible().catch(() => false);
      console.log(`   Item context menu: ${itemContextMenu ? 'YES' : 'NO'}`);

      if (itemContextMenu) {
        const hasOpen = await page.locator('.context-menu-item:has-text("Open")').isVisible().catch(() => false);
        const hasRename = await page.locator('.context-menu-item:has-text("Rename")').isVisible().catch(() => false);
        const hasDelete = await page.locator('.context-menu-item:has-text("Delete")').isVisible().catch(() => false);
        const hasProperties = await page.locator('.context-menu-item:has-text("Properties")').isVisible().catch(() => false);

        console.log(`   - Open: ${hasOpen ? 'YES' : 'NO'}`);
        console.log(`   - Rename: ${hasRename ? 'YES' : 'NO'}`);
        console.log(`   - Delete: ${hasDelete ? 'YES' : 'NO'}`);
        console.log(`   - Properties: ${hasProperties ? 'YES' : 'NO'}`);

        // Take screenshot
        await page.screenshot({
          path: 'testing_toolkit/dev_tests/screenshots/explorer-context-menu-item.png',
          fullPage: true
        });
        console.log('   Item context menu screenshot saved');

        // Close menu
        await page.keyboard.press('Escape');
      }
    }

    // 5. Test header buttons
    console.log('\n5. Testing header buttons...');
    const newProjectBtn = page.locator('button:has-text("New Project")');
    const uploadBtn = page.locator('button:has-text("Upload")');

    const hasNewProjectBtn = await newProjectBtn.isVisible().catch(() => false);
    console.log(`   - New Project button: ${hasNewProjectBtn ? 'YES' : 'NO'}`);

    // Enter a project to see New Folder/Upload buttons
    const gridRows = await page.locator('.grid-row').count();
    if (gridRows > 0) {
      await page.locator('.grid-row').first().dblclick();
      await page.waitForTimeout(500);

      const hasNewFolderBtn = await page.locator('button:has-text("New Folder")').isVisible().catch(() => false);
      const hasUploadBtn = await page.locator('button:has-text("Upload")').isVisible().catch(() => false);
      console.log(`   - New Folder button (in project): ${hasNewFolderBtn ? 'YES' : 'NO'}`);
      console.log(`   - Upload button (in project): ${hasUploadBtn ? 'YES' : 'NO'}`);

      // Take screenshot inside project
      await page.screenshot({
        path: 'testing_toolkit/dev_tests/screenshots/explorer-inside-project.png',
        fullPage: true
      });
      console.log('   Project view screenshot saved');
    }

    console.log('\nExplorer Fixes Test COMPLETE!\n');

  } catch (error) {
    console.error('\nTest failed:', error.message);
    await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/explorer-error.png' });
    process.exit(1);
  } finally {
    await browser.close();
  }
}

testExplorerFixes();
