// Test context menu features
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

  // Click on project arrow to expand
  const projectExpand = page.locator('.tree-item-expand, .chevron, [class*="expand"]').first();
  if (await projectExpand.isVisible().catch(() => false)) {
    await projectExpand.click();
    await page.waitForTimeout(500);
  } else {
    // Try clicking on the project name itself
    const projectName = page.locator('.tree-item-content, .project-name').first();
    if (await projectName.isVisible().catch(() => false)) {
      await projectName.click();
      await page.waitForTimeout(500);
    }
  }

  await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/expanded-project.png' });
  console.log('Screenshot: expanded-project.png');

  // Find a file and right-click
  const fileItem = page.locator('.tree-item.file, [data-type="file"], .file-node').first();
  const fileCount = await fileItem.count();
  console.log('File items found:', fileCount);

  if (fileCount > 0) {
    await fileItem.click({ button: 'right' });
    await page.waitForTimeout(500);
    await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/file-context-menu.png' });

    // Check menu items
    const menuItems = await page.locator('.context-menu-item').allTextContents();
    console.log('\n=== Context Menu Items ===');
    menuItems.forEach(item => console.log(' -', item.trim()));

    // Check for specific features
    const hasQA = menuItems.some(m => m.toLowerCase().includes('qa'));
    const hasConvert = menuItems.some(m => m.toLowerCase().includes('convert'));
    const hasDownload = menuItems.some(m => m.toLowerCase().includes('download'));
    const hasPreTranslate = menuItems.some(m => m.toLowerCase().includes('pre-translate') || m.toLowerCase().includes('pretranslate'));

    console.log('\n=== Feature Check ===');
    console.log('QA:', hasQA ? 'YES' : 'NO');
    console.log('Convert:', hasConvert ? 'YES' : 'NO');
    console.log('Download:', hasDownload ? 'YES' : 'NO');
    console.log('Pre-translate:', hasPreTranslate ? 'YES' : 'NO');
  } else {
    console.log('No files found - trying to find any context menu');
    // Right click somewhere on the explorer
    await page.mouse.click(100, 200, { button: 'right' });
    await page.waitForTimeout(500);
    await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/any-context-menu.png' });
  }

  await browser.close();
  console.log('\nDone');
}

test().catch(e => console.error('Test failed:', e.message));
