// Test Phase 10 UI fixes - Grid expansion and TM Viewer
import { chromium } from 'playwright';

async function test() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });

  try {
    // Login
    console.log('=== Logging in ===');
    await page.goto('http://localhost:5173');
    await page.waitForLoadState('networkidle');
    await page.locator('.bx--text-input').first().fill('admin');
    await page.locator('input[type="password"]').fill('admin123');
    await page.click('button[type="submit"]');
    await page.waitForSelector('.ldm-app', { timeout: 10000 });
    console.log('Logged in successfully');
    await page.waitForTimeout(1000);

    // === TEST 1: Files Page Grid Expansion ===
    console.log('\n=== TEST 1: Files Page Grid Expansion ===');

    // Take screenshot of files page
    await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/phase10-files-page.png' });

    // Check if grid container exists and has proper size
    const filesPage = await page.locator('.files-page').first();
    if (await filesPage.isVisible()) {
      const bbox = await filesPage.boundingBox();
      console.log(`Files page size: ${bbox.width}x${bbox.height}`);
      if (bbox.height > 500) {
        console.log('FILES PAGE: Grid expands properly');
      } else {
        console.log('FILES PAGE: Grid NOT expanding (height < 500)');
      }
    }

    // Check grid container
    const gridContainer = await page.locator('.grid-container').first();
    if (await gridContainer.isVisible().catch(() => false)) {
      const gcBox = await gridContainer.boundingBox();
      console.log(`Grid container size: ${gcBox.width}x${gcBox.height}`);
    }

    // Check explorer grid
    const explorerGrid = await page.locator('.explorer-grid').first();
    if (await explorerGrid.isVisible().catch(() => false)) {
      const egBox = await explorerGrid.boundingBox();
      console.log(`Explorer grid size: ${egBox.width}x${egBox.height}`);
    }

    // === TEST 2: Navigate to TM Page ===
    console.log('\n=== TEST 2: TM Page Grid Expansion ===');

    // Click on TM in navigation (look for dropdown or nav item)
    const tmNavItem = page.locator('text=Translation Memories, text=TM, [data-page="tm"]').first();
    if (await tmNavItem.isVisible().catch(() => false)) {
      await tmNavItem.click();
      await page.waitForTimeout(500);
    } else {
      // Try clicking dropdown menu
      const dropdown = page.locator('.bx--dropdown, .nav-dropdown').first();
      if (await dropdown.isVisible().catch(() => false)) {
        await dropdown.click();
        await page.waitForTimeout(300);
        const tmOption = page.locator('text=Translation Memories').first();
        if (await tmOption.isVisible().catch(() => false)) {
          await tmOption.click();
          await page.waitForTimeout(500);
        }
      }
    }

    await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/phase10-tm-page.png' });

    // Check TM page
    const tmPage = await page.locator('.tm-page').first();
    if (await tmPage.isVisible().catch(() => false)) {
      const tmBox = await tmPage.boundingBox();
      console.log(`TM page size: ${tmBox.width}x${tmBox.height}`);
      if (tmBox.height > 500) {
        console.log('TM PAGE: Grid expands properly');
      } else {
        console.log('TM PAGE: Grid NOT expanding (height < 500)');
      }
    } else {
      console.log('TM page not visible - may need different navigation');
    }

    // Check TM explorer grid
    const tmExplorerGrid = await page.locator('.tm-explorer-grid').first();
    if (await tmExplorerGrid.isVisible().catch(() => false)) {
      const tegBox = await tmExplorerGrid.boundingBox();
      console.log(`TM Explorer grid size: ${tegBox.width}x${tegBox.height}`);
    }

    // === TEST 3: Double-click TM to open viewer ===
    console.log('\n=== TEST 3: TM Viewer (double-click) ===');

    const tmRow = page.locator('.grid-row').first();
    if (await tmRow.isVisible().catch(() => false)) {
      console.log('Found TM row, double-clicking...');
      await tmRow.dblclick();
      await page.waitForTimeout(1000);

      await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/phase10-tm-viewer.png' });

      // Check if TMViewer modal opened (it uses Carbon Modal)
      const modal = page.locator('.bx--modal.is-visible, .bx--modal--open');
      if (await modal.isVisible().catch(() => false)) {
        console.log('TM VIEWER: Modal opened successfully');

        // Check modal heading
        const heading = await page.locator('.bx--modal-header__heading').textContent().catch(() => '');
        console.log(`Modal heading: ${heading}`);

        // Check if entries are loading/displayed
        const entriesTable = page.locator('.tm-entries-table, .entries-grid, table');
        if (await entriesTable.isVisible().catch(() => false)) {
          console.log('TM VIEWER: Entries table visible');
        }
      } else {
        console.log('TM VIEWER: Modal NOT visible - check TMViewer component');
      }
    } else {
      console.log('No TM rows found to test double-click');
    }

    // === TEST 4: Right-click context menu ===
    console.log('\n=== TEST 4: Context Menu ===');

    // Go back to files page
    await page.goto('http://localhost:5173');
    await page.waitForSelector('.ldm-app', { timeout: 5000 });
    await page.waitForTimeout(1000);

    // Right-click on empty area to see background menu
    await page.mouse.click(500, 400, { button: 'right' });
    await page.waitForTimeout(300);

    await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/phase10-context-menu.png' });

    const contextMenu = page.locator('.context-menu');
    if (await contextMenu.isVisible().catch(() => false)) {
      console.log('CONTEXT MENU: Visible');
      const items = await page.locator('.context-menu-item').allTextContents();
      console.log('Menu items:', items.map(i => i.trim()).join(', '));
    } else {
      console.log('CONTEXT MENU: Not visible');
    }

    console.log('\n=== TEST COMPLETE ===');

  } catch (error) {
    console.error('Test failed:', error.message);
    await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/phase10-error.png' });
  } finally {
    await browser.close();
  }
}

test();
