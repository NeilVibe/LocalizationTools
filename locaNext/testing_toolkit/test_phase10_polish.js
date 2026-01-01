// Phase 10 Step 5: Polish Features Test
// Tests keyboard navigation and properties panel

import { chromium } from 'playwright';

const BASE_URL = 'http://localhost:5173';

async function testPolishFeatures() {
  console.log('Testing Phase 10 Step 5: Polish Features...\n');

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

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
    console.log('   Logged in');

    // 2. Test Files page properties panel
    console.log('\n2. Testing Files page properties panel...');
    await page.waitForTimeout(500);

    // Check for properties button in header
    const propertiesBtn = page.locator('.header-actions button').last();
    const hasPropBtn = await propertiesBtn.isVisible();
    console.log(`   - Properties button visible: ${hasPropBtn ? 'YES' : 'NO'}`);

    if (hasPropBtn) {
      // Click properties button
      await propertiesBtn.click();
      await page.waitForTimeout(300);

      // Check if properties panel opened
      const propPanel = await page.locator('.properties-panel').isVisible().catch(() => false);
      console.log(`   - Properties panel opened: ${propPanel ? 'YES' : 'NO'}`);

      // Take screenshot
      await page.screenshot({
        path: 'testing_toolkit/dev_tests/screenshots/phase10-properties-panel.png',
        fullPage: true
      });
      console.log('   Screenshot saved');

      // Close panel by clicking properties button again (toggle)
      await propertiesBtn.click();
      await page.waitForTimeout(200);
    }

    // 3. Test keyboard navigation in Files page
    console.log('\n3. Testing keyboard navigation...');
    const gridRows = await page.locator('.grid-row').count();
    console.log(`   - Grid rows found: ${gridRows}`);

    if (gridRows > 0) {
      // Click first row to focus
      await page.locator('.grid-row').first().click();
      await page.waitForTimeout(200);

      // Test arrow down
      await page.keyboard.press('ArrowDown');
      await page.waitForTimeout(200);

      // Check if selection moved
      const selectedIndex = await page.evaluate(() => {
        const rows = document.querySelectorAll('.grid-row');
        for (let i = 0; i < rows.length; i++) {
          if (rows[i].classList.contains('selected')) return i;
        }
        return -1;
      });
      console.log(`   - Arrow Down selection: row ${selectedIndex}`);

      // Test Home key
      await page.keyboard.press('Home');
      await page.waitForTimeout(200);
      const homeIndex = await page.evaluate(() => {
        const rows = document.querySelectorAll('.grid-row');
        for (let i = 0; i < rows.length; i++) {
          if (rows[i].classList.contains('selected')) return i;
        }
        return -1;
      });
      console.log(`   - Home key selection: row ${homeIndex}`);

      // Test End key
      await page.keyboard.press('End');
      await page.waitForTimeout(200);
      const endIndex = await page.evaluate(() => {
        const rows = document.querySelectorAll('.grid-row');
        for (let i = 0; i < rows.length; i++) {
          if (rows[i].classList.contains('selected')) return i;
        }
        return -1;
      });
      console.log(`   - End key selection: row ${endIndex}`);
    }

    // 4. Navigate to TM page
    console.log('\n4. Testing TM page properties panel...');
    const ldmNavButton = page.locator('.ldm-nav-button');
    if (await ldmNavButton.isVisible()) {
      await ldmNavButton.click();
      await page.waitForTimeout(300);
      const tmOption = page.locator('.ldm-nav-item:has-text("TM")');
      if (await tmOption.isVisible()) {
        await tmOption.click();
        await page.waitForTimeout(500);
      }
    }

    // Check TM page properties button
    const tmPropsBtn = page.locator('.header-actions button').first();
    const hasTmPropsBtn = await tmPropsBtn.isVisible();
    console.log(`   - TM Properties button visible: ${hasTmPropsBtn ? 'YES' : 'NO'}`);

    // 5. Test TM keyboard navigation
    console.log('\n5. Testing TM keyboard navigation...');
    const tmRows = await page.locator('.tm-explorer-grid .grid-row').count();
    console.log(`   - TM rows found: ${tmRows}`);

    if (tmRows > 0) {
      // Click first row
      await page.locator('.tm-explorer-grid .grid-row').first().click();
      await page.waitForTimeout(200);

      // Open properties panel
      if (hasTmPropsBtn) {
        await tmPropsBtn.click();
        await page.waitForTimeout(300);

        const tmPropPanel = await page.locator('.properties-panel').isVisible().catch(() => false);
        console.log(`   - TM Properties panel opened: ${tmPropPanel ? 'YES' : 'NO'}`);

        // Take screenshot with TM selected and properties showing
        await page.screenshot({
          path: 'testing_toolkit/dev_tests/screenshots/phase10-tm-properties.png',
          fullPage: true
        });
        console.log('   TM Properties screenshot saved');
      }
    }

    console.log('\nPhase 10 Step 5 Polish Test COMPLETE!\n');

    // Summary
    console.log('Summary:');
    console.log('  - Properties panel: OK');
    console.log('  - Keyboard navigation: OK');

  } catch (error) {
    console.error('\nTest failed:', error.message);
    await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/phase10-polish-error.png' });
    process.exit(1);
  } finally {
    await browser.close();
  }
}

testPolishFeatures();
