// Phase 10 Step 4: TM Explorer Test
// Tests Windows Explorer style TM page

import { chromium } from 'playwright';

const BASE_URL = 'http://localhost:5173';

async function testTMExplorer() {
  console.log('Testing Phase 10 Step 4: TM Explorer Style...\n');

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  // Track console logs
  const consoleLogs = [];
  page.on('console', msg => {
    consoleLogs.push(`[${msg.type()}] ${msg.text()}`);
    if (msg.type() === 'error' && !msg.text().includes('favicon')) {
      console.log('Console error:', msg.text());
    }
  });

  try {
    // 1. Go to app
    console.log('1. Loading app...');
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    // 2. Login
    console.log('2. Logging in...');
    await page.waitForSelector('.bx--text-input', { timeout: 10000 });
    await page.locator('.bx--text-input').first().fill('admin');
    await page.locator('input[type=\"password\"]').fill('admin123');
    await page.click('button[type=\"submit\"]');
    await page.waitForSelector('.ldm-app', { timeout: 10000 });
    console.log('   Logged in');

    // 3. Navigate to TM page via LDM navigation dropdown
    console.log('3. Navigating to TM page...');
    await page.waitForTimeout(500);

    // The navigation has a .ldm-nav-button that opens a dropdown menu
    const ldmNavButton = page.locator('.ldm-nav-button');
    if (await ldmNavButton.isVisible()) {
      await ldmNavButton.click();
      await page.waitForTimeout(300);
      console.log('   Opened LDM navigation dropdown');

      // Click the TM option in the menu (has "Translation Memories" text)
      const tmOption = page.locator('.ldm-nav-item:has-text("TM")');
      if (await tmOption.isVisible()) {
        await tmOption.click();
        console.log('   Clicked TM option');
      } else {
        console.log('   TM option not found in menu');
      }
    } else {
      console.log('   LDM nav button not found');
    }
    await page.waitForTimeout(500);

    // 4. Check TM page structure
    console.log('4. Checking TM page structure...');
    const tmPage = await page.locator('.tm-page').isVisible().catch(() => false);
    const tmHeader = await page.locator('.tm-page-header').isVisible().catch(() => false);
    const tmExplorerGrid = await page.locator('.tm-explorer-grid').isVisible().catch(() => false);

    console.log(`   - TMPage visible: ${tmPage ? 'YES' : 'NO'}`);
    console.log(`   - Header visible: ${tmHeader ? 'YES' : 'NO'}`);
    console.log(`   - TMExplorerGrid visible: ${tmExplorerGrid ? 'YES' : 'NO'}`);

    // Take screenshot
    await page.screenshot({
      path: 'testing_toolkit/dev_tests/screenshots/phase10-tm-explorer.png',
      fullPage: true
    });
    console.log('   Screenshot saved');

    // 5. Check for TM items in grid
    console.log('5. Checking for TM items...');
    const gridRows = await page.locator('.tm-explorer-grid .grid-row').count();
    const gridHeader = await page.locator('.tm-explorer-grid .grid-header').isVisible().catch(() => false);
    const emptyState = await page.locator('.tm-explorer-grid .empty-state').isVisible().catch(() => false);

    console.log(`   - Grid header visible: ${gridHeader ? 'YES' : 'NO'}`);
    console.log(`   - TM rows found: ${gridRows}`);
    console.log(`   - Empty state visible: ${emptyState ? 'YES' : 'NO'}`);

    // 6. Check header actions
    console.log('6. Checking header actions...');
    const uploadButton = await page.locator('button:has-text("Upload TM")').isVisible().catch(() => false);
    const settingsButton = await page.locator('.header-actions button[aria-label="Settings"], .header-actions button:has(svg)').first().isVisible().catch(() => false);
    console.log(`   - Upload TM button: ${uploadButton ? 'YES' : 'NO'}`);
    console.log(`   - Settings button area: ${settingsButton ? 'YES' : 'NO'}`);

    // 7. If there are TMs, test selection
    if (gridRows > 0) {
      console.log('7. Testing TM selection...');
      await page.locator('.tm-explorer-grid .grid-row').first().click();
      await page.waitForTimeout(300);

      const selected = await page.locator('.tm-explorer-grid .grid-row.selected').count();
      console.log(`   - Selected rows: ${selected}`);

      // 8. Test double-click (should open viewer)
      console.log('8. Testing double-click to view entries...');
      await page.locator('.tm-explorer-grid .grid-row').first().dblclick();
      await page.waitForTimeout(700);

      // Check if TM viewer opened (Carbon modal with "TM Viewer" heading)
      const viewerVisible = await page.locator('.bx--modal.is-visible, .bx--modal-header__heading:has-text("TM Viewer")').first().isVisible().catch(() => false);
      console.log(`   - TM Viewer opened: ${viewerVisible ? 'YES' : 'NO'}`);

      // Take screenshot after double-click
      await page.screenshot({
        path: 'testing_toolkit/dev_tests/screenshots/phase10-tm-viewer.png',
        fullPage: true
      });
      console.log('   Viewer screenshot saved');

      // Close viewer by clicking close button on the visible modal
      const closeButton = page.locator('.bx--modal.is-visible .bx--modal-close');
      if (await closeButton.isVisible()) {
        await closeButton.click();
        await page.waitForTimeout(300);
        console.log('   Closed TM Viewer');
      }
    } else {
      console.log('7. No TMs found, skipping selection tests');
      console.log('8. Skipping viewer test (no TMs)');
    }

    // 9. Test settings panel
    console.log('9. Testing settings panel...');
    const settingsBtn = await page.locator('.header-actions button').first();
    if (await settingsBtn.isVisible()) {
      await settingsBtn.click();
      await page.waitForTimeout(300);

      const settingsPanel = await page.locator('.tm-settings-panel').isVisible().catch(() => false);
      console.log(`   - Settings panel visible: ${settingsPanel ? 'YES' : 'NO'}`);

      if (settingsPanel) {
        // Take screenshot with settings panel
        await page.screenshot({
          path: 'testing_toolkit/dev_tests/screenshots/phase10-tm-settings.png',
          fullPage: true
        });
        console.log('   Settings panel screenshot saved');
      }
    }

    console.log('\nPhase 10 Step 4 TM Explorer Test COMPLETE!\n');

    // Print summary
    console.log('Summary:');
    console.log('  - TMPage: ' + (tmPage ? 'OK' : 'MISSING'));
    console.log('  - TMExplorerGrid: ' + (tmExplorerGrid ? 'OK' : 'MISSING'));
    console.log('  - Grid Header: ' + (gridHeader ? 'OK' : 'MISSING'));
    console.log('  - TM Items: ' + gridRows);

  } catch (error) {
    console.error('\nTest failed:', error.message);
    console.log('\nRecent console logs:');
    consoleLogs.slice(-10).forEach(log => console.log('  ' + log));
    await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/phase10-tm-error.png' });
    console.log('Error screenshot saved');
    process.exit(1);
  } finally {
    await browser.close();
  }
}

testTMExplorer();
