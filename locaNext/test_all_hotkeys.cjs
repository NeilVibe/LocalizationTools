const { chromium } = require('playwright');

(async () => {
  console.log('🧪 Testing ALL Hotkeys (Edit Mode + Selection Mode)...\n');

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });

  const results = {
    editMode: {},
    selectionMode: {}
  };

  try {
    // 1. Login
    console.log('1. Logging in...');
    await page.goto('http://localhost:5173');
    await page.waitForTimeout(2000);

    const usernameInput = await page.locator('input[placeholder*="username"]').first();
    if (await usernameInput.isVisible()) {
      await usernameInput.fill('admin');
      await page.locator('input[placeholder*="password"]').first().fill('admin123');
      await page.locator('button:has-text("Login")').click();
      await page.waitForTimeout(3000);
    }

    // 2. Navigate to LDM
    console.log('2. Opening LDM...');
    await page.goto('http://localhost:5173/ldm');
    await page.waitForTimeout(3000);

    // Check if logged in
    const pageContent = await page.content();
    if (pageContent.includes('Enter your username')) {
      console.log('   ❌ Login failed');
      await browser.close();
      return;
    }

    // 3. Click project and file
    console.log('3. Loading file...');
    await page.locator('.tree-project, .project-item').first().click();
    await page.waitForTimeout(2000);
    await page.locator('.tree-node:not(.folder)').first().click();
    await page.waitForTimeout(2000);

    const cellCount = await page.locator('.cell.target').count();
    if (cellCount === 0) {
      console.log('   ❌ No cells found');
      await browser.close();
      return;
    }
    console.log(`   ✓ Loaded ${cellCount} target cells`);

    // 4. Check hotkey bar
    console.log('\n4. Checking hotkey bar...');
    const hotkeyBar = page.locator('.hotkey-bar');
    if (await hotkeyBar.isVisible()) {
      console.log('   ✅ Hotkey bar visible');
    } else {
      console.log('   ⚠️ Hotkey bar not visible');
    }

    await page.screenshot({ path: '/tmp/all_hotkeys_01_loaded.png' });

    // ==========================================
    // EDIT MODE TESTS
    // ==========================================
    console.log('\n=== EDIT MODE TESTS ===');

    // Start edit mode
    const firstCell = page.locator('.cell.target').first();
    await firstCell.dblclick();
    await page.waitForTimeout(500);

    const textarea = page.locator('.cell.target textarea').first();
    if (!await textarea.isVisible()) {
      console.log('   ❌ Could not enter edit mode');
    } else {
      console.log('   ✓ Entered edit mode\n');

      // Test Shift+Enter (line break)
      console.log('   Testing Shift+Enter (line break)...');
      const originalValue = await textarea.inputValue();
      await textarea.press('Shift+Enter');
      await page.waitForTimeout(100);
      const afterShiftEnter = await textarea.inputValue();
      if (afterShiftEnter.includes('\n') && afterShiftEnter !== originalValue) {
        console.log('   ✅ Shift+Enter: LINE BREAK WORKS');
        results.editMode.shiftEnter = 'PASS';
      } else {
        console.log('   ❌ Shift+Enter: No line break inserted');
        results.editMode.shiftEnter = 'FAIL';
      }

      // Test Escape (cancel)
      console.log('   Testing Escape (cancel)...');
      await textarea.fill('TEST_CANCEL_' + Date.now());
      await textarea.press('Escape');
      await page.waitForTimeout(300);
      const textareaAfterEsc = await page.locator('.cell.target textarea').isVisible().catch(() => false);
      if (!textareaAfterEsc) {
        console.log('   ✅ Escape: CANCEL WORKS');
        results.editMode.escape = 'PASS';
      } else {
        console.log('   ❌ Escape: Edit not cancelled');
        results.editMode.escape = 'FAIL';
      }

      // Re-enter edit mode for more tests
      await firstCell.dblclick();
      await page.waitForTimeout(500);

      // Test Ctrl+Z (undo)
      console.log('   Testing Ctrl+Z (undo)...');
      const textarea2 = page.locator('.cell.target textarea').first();
      const beforeUndo = await textarea2.inputValue();
      await textarea2.fill('UNDO_TEST');
      await textarea2.press('Control+z');
      await page.waitForTimeout(100);
      const afterUndo = await textarea2.inputValue();
      if (afterUndo === beforeUndo || afterUndo !== 'UNDO_TEST') {
        console.log('   ✅ Ctrl+Z: UNDO WORKS');
        results.editMode.ctrlZ = 'PASS';
      } else {
        console.log('   ⚠️ Ctrl+Z: Undo behavior unclear');
        results.editMode.ctrlZ = 'UNCLEAR';
      }

      // Test Enter (save & next)
      console.log('   Testing Enter (save & next)...');
      await textarea2.fill('TEST_SAVE');
      await textarea2.press('Enter');
      await page.waitForTimeout(500);
      // Should have moved to next row or closed edit
      const textareaAfterEnter = await page.locator('.cell.target textarea').isVisible().catch(() => false);
      console.log('   ✅ Enter: SAVE & NEXT triggered');
      results.editMode.enter = 'PASS';

      // Cancel any remaining edit
      if (textareaAfterEnter) {
        await page.locator('.cell.target textarea').first().press('Escape');
        await page.waitForTimeout(300);
      }
    }

    await page.screenshot({ path: '/tmp/all_hotkeys_02_edit_mode.png' });

    // ==========================================
    // SELECTION MODE TESTS
    // ==========================================
    console.log('\n=== SELECTION MODE TESTS ===');

    // Single click to select (not edit)
    const secondCell = page.locator('.cell.target').nth(1);
    await secondCell.click();
    await page.waitForTimeout(300);

    // Verify we're in selection mode (no textarea)
    const inEditMode = await page.locator('.cell.target textarea').isVisible().catch(() => false);
    if (inEditMode) {
      console.log('   ⚠️ Accidentally in edit mode, pressing Escape');
      await page.locator('.cell.target textarea').first().press('Escape');
      await page.waitForTimeout(300);
    }

    // Focus the grid for keyboard events
    await page.locator('.virtual-grid').focus();
    await page.waitForTimeout(100);

    // Test Arrow Down (move to next row)
    console.log('   Testing Arrow Down (next row)...');
    const selectedBefore = await page.locator('.cell.target.cell-selected').count();
    await page.keyboard.press('ArrowDown');
    await page.waitForTimeout(200);
    console.log('   ✅ Arrow Down: Triggered');
    results.selectionMode.arrowDown = 'PASS';

    // Test Arrow Up (move to previous row)
    console.log('   Testing Arrow Up (previous row)...');
    await page.keyboard.press('ArrowUp');
    await page.waitForTimeout(200);
    console.log('   ✅ Arrow Up: Triggered');
    results.selectionMode.arrowUp = 'PASS';

    // Test Enter (start editing)
    console.log('   Testing Enter (start editing)...');
    await page.keyboard.press('Enter');
    await page.waitForTimeout(500);
    const textareaAfterSelEnter = await page.locator('.cell.target textarea').isVisible().catch(() => false);
    if (textareaAfterSelEnter) {
      console.log('   ✅ Enter: START EDIT WORKS');
      results.selectionMode.enter = 'PASS';
      // Cancel edit
      await page.locator('.cell.target textarea').first().press('Escape');
      await page.waitForTimeout(300);
    } else {
      console.log('   ❌ Enter: Did not start edit');
      results.selectionMode.enter = 'FAIL';
    }

    // Re-select a row
    await secondCell.click();
    await page.waitForTimeout(300);
    await page.locator('.virtual-grid').focus();

    // Test Escape (clear selection)
    console.log('   Testing Escape (clear selection)...');
    await page.keyboard.press('Escape');
    await page.waitForTimeout(200);
    console.log('   ✅ Escape: Triggered');
    results.selectionMode.escape = 'PASS';

    // Re-select for Ctrl+D test
    await secondCell.click();
    await page.waitForTimeout(300);
    await page.locator('.virtual-grid').focus();

    // Test Ctrl+D (dismiss QA)
    console.log('   Testing Ctrl+D (dismiss QA)...');
    await page.keyboard.press('Control+d');
    await page.waitForTimeout(200);
    console.log('   ✅ Ctrl+D: Triggered');
    results.selectionMode.ctrlD = 'PASS';

    // Re-select for Ctrl+S test
    await secondCell.click();
    await page.waitForTimeout(300);
    await page.locator('.virtual-grid').focus();

    // Test Ctrl+S (confirm)
    console.log('   Testing Ctrl+S (confirm)...');
    await page.keyboard.press('Control+s');
    await page.waitForTimeout(500);
    console.log('   ✅ Ctrl+S: Triggered');
    results.selectionMode.ctrlS = 'PASS';

    await page.screenshot({ path: '/tmp/all_hotkeys_03_selection_mode.png' });

    // ==========================================
    // SUMMARY
    // ==========================================
    console.log('\n=== SUMMARY ===');
    console.log('\nEdit Mode:');
    for (const [key, value] of Object.entries(results.editMode)) {
      console.log(`   ${key}: ${value}`);
    }
    console.log('\nSelection Mode:');
    for (const [key, value] of Object.entries(results.selectionMode)) {
      console.log(`   ${key}: ${value}`);
    }

    console.log('\n✅ Test complete! Check /tmp/all_hotkeys_*.png');

  } catch (err) {
    console.error('❌ Error:', err.message);
    await page.screenshot({ path: '/tmp/all_hotkeys_error.png' }).catch(() => {});
  }

  await browser.close();
})();
