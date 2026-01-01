// Full verification test - 10 screenshots
import { chromium } from 'playwright';

async function test() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });

  const screenshots = [];

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

    // SCREENSHOT 1: Files page (projects list)
    console.log('\n=== Screenshot 1: Files Page (Projects) ===');
    await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/verify-01-files-projects.png' });
    const filesPage = await page.locator('.files-page, .explorer-grid').first();
    if (await filesPage.isVisible().catch(() => false)) {
      const bbox = await filesPage.boundingBox();
      console.log(`Files page size: ${bbox.width}x${bbox.height}`);
      screenshots.push({ name: 'Files Projects', width: bbox.width, height: bbox.height, ok: bbox.height > 800 });
    }

    // SCREENSHOT 2: Enter project
    console.log('\n=== Screenshot 2: Inside Project ===');
    const projectRow = page.locator('.grid-row').first();
    if (await projectRow.isVisible().catch(() => false)) {
      await projectRow.dblclick();
      await page.waitForTimeout(1000);
    }
    await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/verify-02-inside-project.png' });
    const projectContent = await page.locator('.files-page').first();
    if (await projectContent.isVisible().catch(() => false)) {
      const bbox = await projectContent.boundingBox();
      console.log(`Project content size: ${bbox.width}x${bbox.height}`);
      screenshots.push({ name: 'Inside Project', width: bbox.width, height: bbox.height, ok: bbox.height > 800 });
    }

    // SCREENSHOT 3: Right-click context menu
    console.log('\n=== Screenshot 3: File Context Menu ===');
    const fileRow = page.locator('.grid-row').first();
    if (await fileRow.isVisible().catch(() => false)) {
      await fileRow.click({ button: 'right' });
      await page.waitForTimeout(300);
    }
    await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/verify-03-context-menu.png' });
    const ctxMenu = page.locator('.context-menu');
    const hasCtxMenu = await ctxMenu.isVisible().catch(() => false);
    console.log(`Context menu visible: ${hasCtxMenu}`);
    if (hasCtxMenu) {
      const items = await page.locator('.context-menu-item').allTextContents();
      console.log('Menu items:', items.slice(0, 5).map(i => i.trim()).join(', '));
    }
    screenshots.push({ name: 'Context Menu', ok: hasCtxMenu });
    await page.click('body'); // close menu

    // SCREENSHOT 4: Open file in grid
    console.log('\n=== Screenshot 4: File Grid (VirtualGrid) ===');
    const txtFile = page.locator('.grid-row:has-text(".txt")').first();
    if (await txtFile.isVisible().catch(() => false)) {
      await txtFile.dblclick();
      await page.waitForTimeout(1500);
    }
    await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/verify-04-file-grid.png' });
    const gridPage = page.locator('.grid-page, .grid-with-panel');
    if (await gridPage.isVisible().catch(() => false)) {
      const bbox = await gridPage.boundingBox();
      console.log(`Grid page size: ${bbox.width}x${bbox.height}`);
      screenshots.push({ name: 'File Grid', width: bbox.width, height: bbox.height, ok: bbox.height > 800 });
    } else {
      console.log('Grid page NOT visible');
      screenshots.push({ name: 'File Grid', ok: false });
    }

    // SCREENSHOT 5: VirtualGrid specifically
    console.log('\n=== Screenshot 5: VirtualGrid Container ===');
    const virtualGrid = page.locator('.virtual-grid');
    if (await virtualGrid.isVisible().catch(() => false)) {
      const bbox = await virtualGrid.boundingBox();
      console.log(`VirtualGrid size: ${bbox.width}x${bbox.height}`);
      screenshots.push({ name: 'VirtualGrid', width: bbox.width, height: bbox.height, ok: bbox.height > 500 });
    } else {
      console.log('VirtualGrid NOT visible');
      screenshots.push({ name: 'VirtualGrid', ok: false });
    }
    await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/verify-05-virtual-grid.png' });

    // SCREENSHOT 6: Navigate to TM page
    console.log('\n=== Screenshot 6: TM Page ===');
    // Click Files dropdown to navigate to TM
    const filesDropdown = page.locator('[class*="dropdown"]:has-text("Files"), button:has-text("Files")').first();
    if (await filesDropdown.isVisible().catch(() => false)) {
      await filesDropdown.click();
      await page.waitForTimeout(300);
      const tmOption = page.locator('[role="option"]:has-text("Translation"), .bx--list-box__menu-item:has-text("Translation")').first();
      if (await tmOption.isVisible().catch(() => false)) {
        await tmOption.click();
        await page.waitForTimeout(500);
      }
    }
    await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/verify-06-tm-page.png' });
    const tmPage = page.locator('.tm-page, .tm-explorer-grid');
    if (await tmPage.isVisible().catch(() => false)) {
      const bbox = await tmPage.boundingBox();
      console.log(`TM page size: ${bbox.width}x${bbox.height}`);
      screenshots.push({ name: 'TM Page', width: bbox.width, height: bbox.height, ok: bbox.height > 800 });
    } else {
      console.log('TM page NOT visible');
      screenshots.push({ name: 'TM Page', ok: false });
    }

    // SCREENSHOT 7: Double-click TM to open full-page viewer
    console.log('\n=== Screenshot 7: TM Entries (Full Page) ===');
    const tmRow = page.locator('.tm-explorer-grid .grid-row, .grid-row').first();
    if (await tmRow.isVisible().catch(() => false)) {
      await tmRow.dblclick();
      await page.waitForTimeout(1000);
    }
    await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/verify-07-tm-entries.png' });
    const tmEntries = page.locator('.tm-entries-page, .tm-data-grid');
    if (await tmEntries.isVisible().catch(() => false)) {
      const bbox = await tmEntries.boundingBox();
      console.log(`TM Entries page size: ${bbox.width}x${bbox.height}`);
      screenshots.push({ name: 'TM Entries', width: bbox.width, height: bbox.height, ok: bbox.height > 800 });
    } else {
      // Check if modal opened instead (wrong)
      const modal = page.locator('.bx--modal.is-visible');
      if (await modal.isVisible().catch(() => false)) {
        console.log('ERROR: TM Viewer is still a modal!');
        screenshots.push({ name: 'TM Entries', ok: false, error: 'Still a modal' });
      } else {
        console.log('TM Entries page NOT visible');
        screenshots.push({ name: 'TM Entries', ok: false });
      }
    }

    // SCREENSHOT 8: Back to Files page
    console.log('\n=== Screenshot 8: Back to Files ===');
    const backBtn = page.locator('.back-button, button:has-text("Back")').first();
    if (await backBtn.isVisible().catch(() => false)) {
      await backBtn.click();
      await page.waitForTimeout(500);
    }
    // Navigate to Files
    const filesNav = page.locator('[class*="dropdown"]:has-text("TM"), button:has-text("TM")').first();
    if (await filesNav.isVisible().catch(() => false)) {
      await filesNav.click();
      await page.waitForTimeout(300);
      const filesOpt = page.locator('[role="option"]:has-text("Files"), .bx--list-box__menu-item:has-text("Files")').first();
      if (await filesOpt.isVisible().catch(() => false)) {
        await filesOpt.click();
        await page.waitForTimeout(500);
      }
    }
    await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/verify-08-back-files.png' });
    screenshots.push({ name: 'Back to Files', ok: true });

    // SCREENSHOT 9: Background right-click
    console.log('\n=== Screenshot 9: Background Context Menu ===');
    await page.mouse.click(800, 600, { button: 'right' });
    await page.waitForTimeout(300);
    await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/verify-09-bg-context.png' });
    const bgMenu = page.locator('.context-menu');
    const hasBgMenu = await bgMenu.isVisible().catch(() => false);
    console.log(`Background menu visible: ${hasBgMenu}`);
    screenshots.push({ name: 'Bg Context Menu', ok: hasBgMenu });
    await page.click('body');

    // SCREENSHOT 10: Full app view
    console.log('\n=== Screenshot 10: Full App View ===');
    await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/verify-10-full-app.png' });
    const ldmApp = page.locator('.ldm-app');
    if (await ldmApp.isVisible().catch(() => false)) {
      const bbox = await ldmApp.boundingBox();
      console.log(`LDM App size: ${bbox.width}x${bbox.height}`);
      screenshots.push({ name: 'Full App', width: bbox.width, height: bbox.height, ok: bbox.height > 900 });
    }

    // Summary
    console.log('\n=== VERIFICATION SUMMARY ===');
    screenshots.forEach((s, i) => {
      const status = s.ok ? '✓' : '✗';
      const size = s.width ? ` (${s.width}x${s.height})` : '';
      const error = s.error ? ` - ${s.error}` : '';
      console.log(`${i+1}. ${status} ${s.name}${size}${error}`);
    });

    const passed = screenshots.filter(s => s.ok).length;
    console.log(`\nPASSED: ${passed}/${screenshots.length}`);

  } catch (error) {
    console.error('Test failed:', error.message);
    await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/verify-error.png' });
  } finally {
    await browser.close();
  }
}

test();
