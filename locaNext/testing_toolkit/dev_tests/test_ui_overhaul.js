// Test Phase 10 UI Overhaul - Clean Windows Explorer Style
// Tests: Context menus, modals, no ugly buttons

import { chromium } from 'playwright';

const BASE_URL = 'http://localhost:5173';

async function testUIOverhaul() {
  console.log('Testing Phase 10 UI Overhaul...\n');

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
  const page = await context.newPage();

  // Capture console errors
  const consoleErrors = [];
  page.on('console', msg => {
    if (msg.type() === 'error' && !msg.text().includes('favicon')) {
      consoleErrors.push(msg.text().substring(0, 100));
    }
  });

  try {
    // 1. Login
    console.log('1. Logging in...');
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
    await page.waitForSelector('.bx--text-input', { timeout: 10000 });
    await page.locator('.bx--text-input').first().fill('admin');
    await page.locator('input[type="password"]').fill('admin123');
    await page.click('button[type="submit"]');
    await page.waitForSelector('.ldm-app', { timeout: 10000 });
    console.log('   OK - Logged in');

    // 2. Check Files Page - should have NO ugly buttons
    console.log('\n2. Checking Files Page (no ugly buttons)...');
    await page.waitForTimeout(500);

    // Check for ugly buttons that should NOT exist
    const newProjectBtn = await page.locator('button:has-text("New Project")').isVisible().catch(() => false);
    const newFolderBtn = await page.locator('button:has-text("New Folder")').isVisible().catch(() => false);
    const uploadBtn = await page.locator('button:has-text("Upload")').isVisible().catch(() => false);
    const infoBtn = await page.locator('button[iconDescription="Properties"]').isVisible().catch(() => false);

    console.log(`   - New Project button: ${newProjectBtn ? 'FOUND (should be removed)' : 'REMOVED OK'}`);
    console.log(`   - New Folder button: ${newFolderBtn ? 'FOUND (should be removed)' : 'REMOVED OK'}`);
    console.log(`   - Upload button: ${uploadBtn ? 'FOUND (should be removed)' : 'REMOVED OK'}`);
    console.log(`   - Info button: ${infoBtn ? 'FOUND (should be removed)' : 'REMOVED OK'}`);

    // Screenshot of clean Files page
    await page.screenshot({
      path: 'testing_toolkit/dev_tests/screenshots/ui-overhaul-files-clean.png',
      fullPage: true
    });
    console.log('   Screenshot saved');

    // 3. Test right-click context menu on empty space (background)
    console.log('\n3. Testing right-click on empty space...');
    const gridBody = page.locator('.grid-body, .empty-state');
    if (await gridBody.first().isVisible()) {
      const box = await gridBody.first().boundingBox();
      if (box) {
        await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2, { button: 'right' });
        await page.waitForTimeout(300);

        const contextMenu = await page.locator('.context-menu').isVisible().catch(() => false);
        console.log(`   Context menu appears: ${contextMenu ? 'YES' : 'NO'}`);

        if (contextMenu) {
          const hasNewProject = await page.locator('.context-menu-item:has-text("New Project")').isVisible().catch(() => false);
          const hasRefresh = await page.locator('.context-menu-item:has-text("Refresh")').isVisible().catch(() => false);
          console.log(`   - New Project in menu: ${hasNewProject ? 'YES' : 'NO'}`);
          console.log(`   - Refresh in menu: ${hasRefresh ? 'YES' : 'NO'}`);

          await page.screenshot({
            path: 'testing_toolkit/dev_tests/screenshots/ui-overhaul-context-menu.png',
            fullPage: true
          });
          console.log('   Context menu screenshot saved');

          // Close menu
          await page.keyboard.press('Escape');
        }
      }
    }

    // 4. Test input modal (New Project)
    console.log('\n4. Testing Carbon Input Modal...');
    // Right-click again and click New Project
    const gridBodyAgain = page.locator('.grid-body, .empty-state');
    if (await gridBodyAgain.first().isVisible()) {
      const box = await gridBodyAgain.first().boundingBox();
      if (box) {
        await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2, { button: 'right' });
        await page.waitForTimeout(300);

        const newProjectItem = page.locator('.context-menu-item:has-text("New Project")');
        if (await newProjectItem.isVisible()) {
          await newProjectItem.click();
          await page.waitForTimeout(300);

          // Check if Carbon Modal appeared (not ugly prompt)
          const modal = await page.locator('.bx--modal').isVisible().catch(() => false);
          const modalHeading = await page.locator('.bx--modal-header__heading').textContent().catch(() => '');
          console.log(`   Carbon Modal appeared: ${modal ? 'YES' : 'NO'}`);
          console.log(`   Modal title: "${modalHeading}"`);

          await page.screenshot({
            path: 'testing_toolkit/dev_tests/screenshots/ui-overhaul-input-modal.png',
            fullPage: true
          });
          console.log('   Input modal screenshot saved');

          // Close modal
          await page.keyboard.press('Escape');
          await page.waitForTimeout(300);
        }
      }
    }

    // 5. Check TM Page
    console.log('\n5. Checking TM Page...');
    // Click on TM tab
    const tmTab = page.locator('[role="tab"]:has-text("Translation Memory"), button:has-text("TM")');
    if (await tmTab.first().isVisible()) {
      await tmTab.first().click();
      await page.waitForTimeout(500);

      // Check for ugly buttons on TM page
      const uploadTMBtn = await page.locator('button:has-text("Upload TM")').isVisible().catch(() => false);
      const refreshBtn = await page.locator('button:has-text("Refresh")').isVisible().catch(() => false);
      console.log(`   - Upload TM button: ${uploadTMBtn ? 'FOUND (should be context menu)' : 'REMOVED OK'}`);
      console.log(`   - Refresh button: ${refreshBtn ? 'FOUND (should be context menu)' : 'REMOVED OK'}`);

      // Right-click on TM page
      await page.mouse.click(960, 540, { button: 'right' });
      await page.waitForTimeout(300);

      const tmContextMenu = await page.locator('.context-menu').isVisible().catch(() => false);
      console.log(`   - Right-click context menu: ${tmContextMenu ? 'YES' : 'NO'}`);

      if (tmContextMenu) {
        const hasUploadTM = await page.locator('.context-menu-item:has-text("Upload TM")').isVisible().catch(() => false);
        const hasRefreshMenu = await page.locator('.context-menu-item:has-text("Refresh")').isVisible().catch(() => false);
        console.log(`   - Upload TM in menu: ${hasUploadTM ? 'YES' : 'NO'}`);
        console.log(`   - Refresh in menu: ${hasRefreshMenu ? 'YES' : 'NO'}`);

        await page.screenshot({
          path: 'testing_toolkit/dev_tests/screenshots/ui-overhaul-tm-context-menu.png',
          fullPage: true
        });
        console.log('   TM context menu screenshot saved');

        await page.keyboard.press('Escape');
      }
    }

    // 6. Summary
    console.log('\n=== Test Summary ===');
    console.log(`Console errors: ${consoleErrors.length}`);
    if (consoleErrors.length > 0) {
      consoleErrors.forEach(e => console.log(`   - ${e}`));
    }

    console.log('\nUI Overhaul Test COMPLETE!\n');

  } catch (error) {
    console.error('\nTest failed:', error.message);
    await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/ui-overhaul-error.png' });
    process.exit(1);
  } finally {
    await browser.close();
  }
}

testUIOverhaul();
