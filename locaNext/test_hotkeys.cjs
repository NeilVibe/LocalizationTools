const { chromium } = require('playwright');

(async () => {
  console.log('🧪 Testing Inline Editing & Hotkeys...\n');

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });

  // Capture browser console
  const consoleLogs = [];
  page.on('console', msg => {
    if (msg.text().includes('HOTKEY-v3')) {
      consoleLogs.push(msg.text());
      console.log('   [browser]', msg.text());
    }
  });

  try {
    // 1. Navigate to app
    console.log('1. Navigating to app...');
    await page.goto('http://localhost:5173');
    await page.waitForTimeout(2000);

    // 2. Login with correct selectors
    console.log('2. Logging in...');

    // Find inputs by placeholder
    const usernameInput = await page.locator('input[placeholder*="username"]').first();
    const passwordInput = await page.locator('input[placeholder*="password"]').first();

    if (await usernameInput.isVisible()) {
      await usernameInput.fill('admin');
      await passwordInput.fill('admin123');

      // Click login button
      await page.locator('button:has-text("Login")').click();
      await page.waitForTimeout(3000);
      console.log('   ✓ Login submitted');
    } else {
      console.log('   ⚠️ Already logged in or different page');
    }

    await page.screenshot({ path: '/tmp/hotkey_01_after_login.png' });

    // 3. Check if we're on dashboard or redirected
    const currentUrl = page.url();
    console.log('   Current URL:', currentUrl);

    // 4. Navigate to LDM
    console.log('3. Opening LDM...');
    await page.goto('http://localhost:5173/ldm');
    await page.waitForTimeout(3000);

    await page.screenshot({ path: '/tmp/hotkey_02_ldm_page.png' });

    // 5. Check page content
    console.log('4. Checking page content...');
    const pageContent = await page.content();

    // Check for login redirect (means auth failed) - check for login form specifically
    if (pageContent.includes('Enter your username') && pageContent.includes('Enter your password')) {
      console.log('   ❌ Still on login page - authentication failed');
      await page.screenshot({ path: '/tmp/hotkey_auth_failed.png' });
      await browser.close();
      return;
    }
    console.log('   ✓ Authenticated - on LDM page');

    // 6. Check for hotkey bar
    console.log('5. Checking for hotkey bar...');
    const hotkeyBar = await page.locator('.hotkey-bar').first();
    if (await hotkeyBar.isVisible()) {
      console.log('   ✅ Hotkey bar FOUND!');
      const hotkeyText = await hotkeyBar.innerText();
      console.log('   Contents:', hotkeyText.replace(/\n/g, ' | '));
    } else {
      console.log('   ❌ Hotkey bar NOT found');
      // Debug: what's on the page?
      const bodyText = await page.locator('body').innerText();
      console.log('   Page text (first 500 chars):', bodyText.substring(0, 500));
    }

    // 7. Look for projects in sidebar
    console.log('6. Looking for projects...');
    await page.waitForTimeout(1000);

    // Try various project selectors
    const projectCount = await page.locator('.tree-project, .project-item, [class*="project"]').count();
    console.log('   Found', projectCount, 'project-like elements');

    if (projectCount > 0) {
      await page.locator('.tree-project, .project-item').first().click();
      await page.waitForTimeout(2000);
      console.log('   ✓ Clicked first project');
    }

    await page.screenshot({ path: '/tmp/hotkey_03_after_project.png' });

    // 8. Look for files/tree nodes
    console.log('7. Looking for tree nodes (files)...');
    const treeNodeCount = await page.locator('.tree-node').count();
    console.log('   Found', treeNodeCount, 'tree nodes');

    if (treeNodeCount > 0) {
      // Click a file node (not folder)
      const fileNodes = page.locator('.tree-node:not(.folder)');
      const fileCount = await fileNodes.count();
      console.log('   Found', fileCount, 'file nodes');

      if (fileCount > 0) {
        await fileNodes.first().click();
        await page.waitForTimeout(2000);
        console.log('   ✓ Clicked file node');
      }
    }

    await page.screenshot({ path: '/tmp/hotkey_04_after_file.png' });

    // 9. Check for grid/cells
    console.log('8. Checking for grid cells...');
    const cellCount = await page.locator('.cell').count();
    const targetCellCount = await page.locator('.cell.target').count();
    console.log('   Total cells:', cellCount, '| Target cells:', targetCellCount);

    if (targetCellCount === 0) {
      console.log('   ⚠️ No target cells found');
      await page.screenshot({ path: '/tmp/hotkey_no_cells.png' });

      // Debug: check what containers exist
      const gridContainer = await page.locator('.virtual-grid, .grid-container, [class*="grid"]').count();
      console.log('   Grid containers:', gridContainer);

      await browser.close();
      return;
    }

    // 10. Test double-click inline editing
    console.log('9. Testing double-click inline edit...');
    const targetCell = page.locator('.cell.target').first();
    await targetCell.dblclick();
    await page.waitForTimeout(500);

    await page.screenshot({ path: '/tmp/hotkey_05_dblclick.png' });

    // 11. Check for textarea
    const textarea = page.locator('.cell.target textarea, textarea.inline-edit-textarea');
    const textareaVisible = await textarea.isVisible().catch(() => false);

    if (textareaVisible) {
      console.log('   ✅ INLINE EDITING WORKS!');

      // Test typing
      const testText = 'TEST_HOTKEY_' + Date.now();
      await textarea.fill(testText);
      console.log('   Typed:', testText);

      await page.screenshot({ path: '/tmp/hotkey_06_typed.png' });

      // Test Escape to cancel
      console.log('10. Testing Escape key...');
      await textarea.press('Escape');
      await page.waitForTimeout(300);

      const textareaAfterEsc = await page.locator('.cell.target textarea').isVisible().catch(() => false);
      if (!textareaAfterEsc) {
        console.log('   ✅ Escape key WORKS - edit cancelled');
      } else {
        console.log('   ⚠️ Textarea still visible after Escape');
      }

      // Print captured console logs
      console.log('   Browser console (HOTKEY):', consoleLogs.length ? consoleLogs.join(' | ') : 'No logs');

      await page.screenshot({ path: '/tmp/hotkey_07_after_esc.png' });

      // Test double-click again and Enter to save
      console.log('11. Testing Enter key (save & next)...');
      await targetCell.dblclick();
      await page.waitForTimeout(300);

      const textarea2 = page.locator('.cell.target textarea').first();
      if (await textarea2.isVisible()) {
        await textarea2.fill('Enter test');
        await textarea2.press('Enter');
        await page.waitForTimeout(300);
        console.log('   ✅ Enter key tested');
      }

      await page.screenshot({ path: '/tmp/hotkey_08_after_enter.png' });

    } else {
      console.log('   ❌ No textarea found after dblclick');

      // Check for old modal
      const modal = await page.locator('.edit-modal-overlay, .edit-modal, [class*="modal"]').count();
      if (modal > 0) {
        console.log('   ⚠️ OLD MODAL appeared instead!');
      }

      // Debug
      const allTextareas = await page.locator('textarea').count();
      console.log('   Total textareas on page:', allTextareas);
    }

    await page.screenshot({ path: '/tmp/hotkey_09_final.png' });
    console.log('\n✅ Test complete! Check /tmp/hotkey_*.png');

  } catch (err) {
    console.error('❌ Error:', err.message);
    await page.screenshot({ path: '/tmp/hotkey_error.png' }).catch(() => {});
  }

  await browser.close();
})();
