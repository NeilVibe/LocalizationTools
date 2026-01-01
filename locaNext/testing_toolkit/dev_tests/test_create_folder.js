// Test Create Folder operation
import { chromium } from 'playwright';

async function test() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });

  // Capture API responses
  page.on('response', async r => {
    if (r.url().includes('/api/ldm/') && r.request().method() !== 'GET') {
      const status = r.status();
      let body = '';
      try { body = await r.text(); } catch(e) {}
      console.log(`[${status}] ${r.request().method()} ${r.url().split('/api/')[1]}`);
      if (body) console.log(`   Response: ${body.substring(0, 200)}`);
    }
  });

  page.on('console', msg => {
    if (msg.type() === 'error') {
      console.log(`[CONSOLE ERROR] ${msg.text().substring(0, 150)}`);
    }
  });

  try {
    // Login
    await page.goto('http://localhost:5173');
    await page.waitForLoadState('networkidle');
    await page.waitForSelector('.bx--text-input', { timeout: 10000 });
    await page.locator('.bx--text-input').first().fill('admin');
    await page.locator('input[type="password"]').fill('admin123');
    await page.click('button[type="submit"]');
    await page.waitForSelector('.ldm-app', { timeout: 10000 });
    console.log('Logged in');

    await page.waitForTimeout(500);

    // Enter project
    await page.locator('.grid-row').first().dblclick();
    await page.waitForTimeout(1000);
    console.log('Inside project');

    // Right-click and create folder
    await page.mouse.click(960, 500, { button: 'right' });
    await page.waitForTimeout(300);
    await page.locator('.context-menu-item:has-text("New Folder")').click();
    await page.waitForTimeout(500);

    // Use specific modal selector (visible one)
    const modal = page.locator('.bx--modal.is-visible');
    console.log('Modal visible:', await modal.isVisible());

    await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/test-folder-modal.png' });

    // Fill in name
    const folderName = 'TestFolder_' + Date.now();
    await page.locator('.bx--modal.is-visible .bx--text-input').fill(folderName);
    console.log('Filled name:', folderName);

    // Click Create
    console.log('Clicking Create...');
    await page.locator('.bx--modal.is-visible .bx--btn--primary').click();

    // Wait for API call
    await page.waitForTimeout(2000);

    await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/test-after-create.png' });

    // Check if folder appeared
    const folders = await page.locator('.grid-row').count();
    console.log('Items in grid after create:', folders);

    console.log('Test complete!');

  } catch (error) {
    console.error('Test failed:', error.message);
    await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/test-error.png' });
  } finally {
    await browser.close();
  }
}

test();
