// Test restored UI with all features
import { chromium } from 'playwright';

async function test() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });

  // Login
  await page.goto('http://localhost:5173');
  await page.waitForLoadState('networkidle');
  await page.locator('.bx--text-input').first().fill('admin');
  await page.locator('input[type="password"]').fill('admin123');
  await page.click('button[type="submit"]');
  await page.waitForSelector('.ldm-app', { timeout: 10000 });
  console.log('Logged in');
  await page.waitForTimeout(1000);

  // Take screenshot
  await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/restored-ui.png' });
  console.log('Screenshot: restored-ui.png');

  // Enter project by double-clicking
  const treeItems = page.locator('.tree-item, .file-explorer .project, [data-type="project"]');
  const count = await treeItems.count();
  console.log('Tree items found:', count);

  if (count > 0) {
    await treeItems.first().dblclick();
    await page.waitForTimeout(1000);
    await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/restored-project.png' });
    console.log('Screenshot: restored-project.png');
  }

  // Try to right-click on a file
  const fileItems = page.locator('.tree-item[data-type="file"], .file-item');
  const fileCount = await fileItems.count();
  console.log('File items found:', fileCount);

  if (fileCount > 0) {
    await fileItems.first().click({ button: 'right' });
    await page.waitForTimeout(500);
    await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/restored-context.png' });
    console.log('Screenshot: restored-context.png');

    // Check context menu items
    const menuItems = await page.locator('.context-menu-item').allTextContents();
    console.log('Context menu items:', menuItems);
  }

  await browser.close();
  console.log('Done');
}

test().catch(e => console.error('Test failed:', e.message));
