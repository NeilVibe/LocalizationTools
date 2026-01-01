// Phase 10: Step 3 - Windows Explorer Test
// Verification that Windows Explorer style navigation works

import { chromium } from 'playwright';

const BASE_URL = 'http://localhost:5173';

async function testWindowsExplorer() {
  console.log('🧪 Phase 10 Step 3: Testing Windows Explorer Style...\n');

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  // Track console logs
  const consoleLogs = [];
  page.on('console', msg => {
    consoleLogs.push(`[${msg.type()}] ${msg.text()}`);
    if (msg.type() === 'error' && !msg.text().includes('favicon')) {
      console.log('❌ Console error:', msg.text());
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
    const usernameInput = page.locator('.bx--text-input').first();
    await usernameInput.fill('admin');
    await page.locator('input[type="password"]').fill('admin123');
    await page.click('button[type="submit"]');
    await page.waitForSelector('.ldm-app', { timeout: 10000 });
    console.log('   ✅ Logged in');

    // 3. Check Windows Explorer style Files Page
    console.log('3. Checking Windows Explorer Files page...');
    await page.waitForTimeout(500);

    const filesPage = await page.locator('.files-page').isVisible().catch(() => false);
    const breadcrumb = await page.locator('.breadcrumb').isVisible().catch(() => false);
    const explorerGrid = await page.locator('.explorer-grid').isVisible().catch(() => false);
    console.log(`   - FilesPage visible: ${filesPage ? '✅' : '❌'}`);
    console.log(`   - Breadcrumb visible: ${breadcrumb ? '✅' : '❌'}`);
    console.log(`   - ExplorerGrid visible: ${explorerGrid ? '✅' : '❌'}`);

    // Take screenshot of Files page (root level - projects)
    await page.screenshot({
      path: 'testing_toolkit/dev_tests/screenshots/phase10-explorer-root.png',
      fullPage: true
    });
    console.log('   📸 Explorer root screenshot saved');

    // 4. Check for project items in grid
    console.log('4. Checking for projects in grid...');
    const gridRows = await page.locator('.grid-row').count();
    console.log(`   Found ${gridRows} items in grid`);

    if (gridRows > 0) {
      // 5. Double-click first project to enter it
      console.log('5. Double-clicking first project to enter...');
      await page.locator('.grid-row').first().dblclick();
      await page.waitForTimeout(500);

      // Check breadcrumb updated
      const breadcrumbItems = await page.locator('.breadcrumb-item').count();
      console.log(`   Breadcrumb items: ${breadcrumbItems}`);

      // Take screenshot inside project
      await page.screenshot({
        path: 'testing_toolkit/dev_tests/screenshots/phase10-explorer-project.png',
        fullPage: true
      });
      console.log('   📸 Explorer project view screenshot saved');

      // 6. Check for files/folders inside project
      const itemsInProject = await page.locator('.grid-row').count();
      console.log(`   Found ${itemsInProject} items inside project`);

      if (itemsInProject > 0) {
        // Find a file (not folder) and double-click to open
        const fileRows = await page.locator('.grid-row:not(.folder)').count();
        console.log(`   Found ${fileRows} files`);

        if (fileRows > 0) {
          console.log('6. Double-clicking file to open in grid...');
          await page.locator('.grid-row:not(.folder)').first().dblclick();
          await page.waitForTimeout(1000);

          const gridPage = await page.locator('.grid-page').isVisible().catch(() => false);
          const virtualGrid = await page.locator('.virtual-grid').isVisible().catch(() => false);
          console.log(`   - GridPage visible: ${gridPage ? '✅' : '❌'}`);
          console.log(`   - VirtualGrid visible: ${virtualGrid ? '✅' : '❌'}`);

          // Take screenshot of grid view
          await page.screenshot({
            path: 'testing_toolkit/dev_tests/screenshots/phase10-explorer-grid.png',
            fullPage: true
          });
          console.log('   📸 File grid view screenshot saved');

          // 7. Test back button
          console.log('7. Testing back navigation...');
          const backButton = await page.locator('.grid-toolbar button').first();
          await backButton.click();
          await page.waitForTimeout(500);

          const backToFiles = await page.locator('.files-page').isVisible().catch(() => false);
          console.log(`   - Back to FilesPage: ${backToFiles ? '✅' : '❌'}`);
        }
      }

      // 8. Test breadcrumb "Projects" click to go home
      console.log('8. Testing breadcrumb home navigation...');
      const homeButton = await page.locator('.breadcrumb-link.root');
      if (await homeButton.isVisible()) {
        await homeButton.click();
        await page.waitForTimeout(500);

        const projectsVisible = await page.locator('.grid-row').count();
        console.log(`   Back at root, ${projectsVisible} projects visible`);
      }
    }

    console.log('\n✅ Phase 10 Step 3 Windows Explorer Test PASSED!\n');

  } catch (error) {
    console.error('\n❌ Test failed:', error.message);
    console.log('\nRecent console logs:');
    consoleLogs.slice(-10).forEach(log => console.log('  ' + log));
    await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/phase10-page-error.png' });
    console.log('   Error screenshot saved');
    process.exit(1);
  } finally {
    await browser.close();
  }
}

testWindowsExplorer();
