// Test TM Page navigation and viewer
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
    console.log('Logged in');
    await page.waitForTimeout(1000);

    // Navigate to TM page via Files dropdown
    console.log('\n=== Navigating to TM Page ===');

    // Click on "Files" dropdown in the header
    const filesDropdown = page.locator('button:has-text("Files"), .bx--dropdown:has-text("Files")').first();
    await filesDropdown.click();
    await page.waitForTimeout(300);

    await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/tm-dropdown-open.png' });

    // Look for TM option
    const tmOption = page.locator('.bx--list-box__menu-item:has-text("Translation"), [role="option"]:has-text("Translation")').first();
    if (await tmOption.isVisible().catch(() => false)) {
      console.log('Found TM option in dropdown');
      await tmOption.click();
      await page.waitForTimeout(500);
    } else {
      console.log('TM option not found, trying alternative');
      // Try clicking any visible dropdown item
      const items = await page.locator('.bx--list-box__menu-item').allTextContents();
      console.log('Dropdown items:', items);
    }

    await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/tm-page-after-nav.png' });

    // Check if we're on TM page
    const tmPageHeader = page.locator('.tm-page-header, h2:has-text("Translation Memories")');
    if (await tmPageHeader.isVisible().catch(() => false)) {
      console.log('TM PAGE: Visible');

      // Check TM grid size
      const tmGrid = page.locator('.tm-explorer-grid');
      if (await tmGrid.isVisible().catch(() => false)) {
        const box = await tmGrid.boundingBox();
        console.log(`TM Grid size: ${box.width}x${box.height}`);
      }

      // Look for TM rows
      const tmRows = page.locator('.tm-explorer-grid .grid-row');
      const rowCount = await tmRows.count();
      console.log(`TM rows found: ${rowCount}`);

      if (rowCount > 0) {
        // Double-click first TM
        console.log('\n=== Double-clicking TM ===');
        await tmRows.first().dblclick();
        await page.waitForTimeout(1000);

        await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/tm-viewer-opened.png' });

        // Check for TMViewer modal
        const modal = page.locator('.bx--modal.is-visible');
        if (await modal.isVisible().catch(() => false)) {
          console.log('TM VIEWER: Modal opened');
          const heading = await modal.locator('.bx--modal-header__heading').textContent().catch(() => 'N/A');
          console.log(`Modal title: ${heading}`);
        } else {
          console.log('TM VIEWER: Modal NOT opened');
          // Check if any modal exists
          const anyModal = await page.locator('.bx--modal').count();
          console.log(`Total modals on page: ${anyModal}`);
        }
      }
    } else {
      console.log('TM PAGE: Not visible');
    }

    console.log('\n=== TEST COMPLETE ===');

  } catch (error) {
    console.error('Test failed:', error.message);
    await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/tm-test-error.png' });
  } finally {
    await browser.close();
  }
}

test();
