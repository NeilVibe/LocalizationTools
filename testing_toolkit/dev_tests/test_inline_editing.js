/**
 * Test: Inline Editing (Phase 2 MemoQ-style)
 * Verifies that double-clicking a Target cell activates inline editing
 */

const { chromium } = require('playwright');

const BASE_URL = 'http://localhost:5173';
const SCREENSHOT_DIR = '/home/neil1988/LocalizationTools/testing_toolkit/dev_tests/screenshots';

async function testInlineEditing() {
  console.log('🧪 Testing Inline Editing...\n');

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1400, height: 900 }
  });
  const page = await context.newPage();

  try {
    // 1. Navigate and login
    console.log('1. Navigating to app...');
    await page.goto(BASE_URL);
    await page.waitForTimeout(1000);

    // Check if login is needed
    const loginButton = await page.$('button:has-text("Login")');
    if (loginButton) {
      console.log('   Logging in...');
      await page.fill('input[type="text"]', 'testuser');
      await page.fill('input[type="password"]', 'testpass');
      await page.click('button:has-text("Login")');
      await page.waitForTimeout(2000);
    }

    // 2. Navigate to LDM
    console.log('2. Opening LDM...');
    // Click on LDM in the sidebar or menu
    const ldmLink = await page.$('a[href="/ldm"], button:has-text("LDM"), [data-app="ldm"]');
    if (ldmLink) {
      await ldmLink.click();
      await page.waitForTimeout(1500);
    } else {
      // Try direct navigation
      await page.goto(`${BASE_URL}/ldm`);
      await page.waitForTimeout(1500);
    }

    await page.screenshot({ path: `${SCREENSHOT_DIR}/inline_01_ldm_opened.png` });
    console.log('   ✓ LDM opened');

    // 3. Check if a project is loaded, if not load one
    console.log('3. Checking for loaded file...');

    // Look for the virtual grid
    const virtualGrid = await page.$('.virtual-grid, .scroll-container');
    if (!virtualGrid) {
      console.log('   No grid found, need to load a project first');

      // Try to find and click a project/file in the tree
      const treeItem = await page.$('.tree-item, .file-item, [data-type="file"]');
      if (treeItem) {
        await treeItem.click();
        await page.waitForTimeout(2000);
      }
    }

    await page.screenshot({ path: `${SCREENSHOT_DIR}/inline_02_grid_loaded.png` });

    // 4. Find a Target cell and double-click it
    console.log('4. Looking for Target cell...');

    // Wait for rows to load
    await page.waitForSelector('.virtual-row:not(.placeholder)', { timeout: 10000 }).catch(() => null);

    // Find a target cell (the editable one)
    const targetCell = await page.$('.cell.target');

    if (!targetCell) {
      console.log('   ❌ No target cell found - grid may be empty');
      await page.screenshot({ path: `${SCREENSHOT_DIR}/inline_error_no_target.png` });
      await browser.close();
      return false;
    }

    console.log('   ✓ Found target cell');

    // Get the original text
    const originalText = await targetCell.innerText();
    console.log(`   Original text: "${originalText.substring(0, 50)}..."`);

    // 5. Double-click to activate inline editing
    console.log('5. Double-clicking to edit...');
    await targetCell.dblclick();
    await page.waitForTimeout(500);

    await page.screenshot({ path: `${SCREENSHOT_DIR}/inline_03_after_dblclick.png` });

    // 6. Check if textarea appeared (inline editing activated)
    console.log('6. Checking for inline textarea...');
    const textarea = await page.$('.cell.target textarea, .inline-edit-textarea');

    if (!textarea) {
      console.log('   ❌ No textarea found - inline editing may not be working');
      await page.screenshot({ path: `${SCREENSHOT_DIR}/inline_error_no_textarea.png` });

      // Check if maybe the old modal appeared instead
      const modal = await page.$('.edit-modal, .edit-modal-overlay');
      if (modal) {
        console.log('   ⚠️  OLD MODAL appeared instead of inline editing!');
        await page.screenshot({ path: `${SCREENSHOT_DIR}/inline_error_modal_appeared.png` });
      }

      await browser.close();
      return false;
    }

    console.log('   ✓ Inline textarea activated!');

    // 7. Type some test text
    console.log('7. Typing test text...');
    const testText = `[INLINE TEST ${Date.now()}]`;

    // Clear and type
    await textarea.fill(testText);
    await page.waitForTimeout(300);

    await page.screenshot({ path: `${SCREENSHOT_DIR}/inline_04_typed_text.png` });
    console.log(`   Typed: "${testText}"`);

    // 8. Press Enter to save
    console.log('8. Pressing Enter to save...');
    await textarea.press('Enter');
    await page.waitForTimeout(1000);

    await page.screenshot({ path: `${SCREENSHOT_DIR}/inline_05_after_save.png` });

    // 9. Verify the textarea is gone (editing completed)
    console.log('9. Verifying edit completed...');
    const textareaAfter = await page.$('.cell.target textarea');

    if (textareaAfter) {
      console.log('   ⚠️  Textarea still visible - may have moved to next row');
    } else {
      console.log('   ✓ Inline editing closed');
    }

    // 10. Press Escape to cancel any active edit
    await page.keyboard.press('Escape');
    await page.waitForTimeout(500);

    await page.screenshot({ path: `${SCREENSHOT_DIR}/inline_06_final.png` });

    console.log('\n✅ Inline editing test PASSED!');
    console.log(`   Screenshots saved to: ${SCREENSHOT_DIR}/inline_*.png`);

    await browser.close();
    return true;

  } catch (error) {
    console.error('\n❌ Test FAILED:', error.message);
    await page.screenshot({ path: `${SCREENSHOT_DIR}/inline_error.png` });
    await browser.close();
    return false;
  }
}

// Run the test
testInlineEditing()
  .then(success => process.exit(success ? 0 : 1))
  .catch(err => {
    console.error('Fatal error:', err);
    process.exit(1);
  });
