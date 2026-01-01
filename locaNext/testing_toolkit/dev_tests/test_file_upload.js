// Test File Upload operation
import { chromium } from 'playwright';
import * as fs from 'fs';
import * as path from 'path';

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

    // Count items before
    const itemsBefore = await page.locator('.grid-row').count();
    console.log('Items before upload:', itemsBefore);

    // Create a test file
    const testFilePath = '/tmp/test_upload_' + Date.now() + '.txt';
    fs.writeFileSync(testFilePath, 'Source\tTarget\nHello\t안녕하세요\nWorld\t세계\n');
    console.log('Created test file:', testFilePath);

    // Right-click and upload file
    await page.mouse.click(960, 500, { button: 'right' });
    await page.waitForTimeout(300);

    // Find hidden file input
    const fileInput = page.locator('input[type="file"]');
    const inputExists = await fileInput.count() > 0;
    console.log('File input exists:', inputExists);

    if (inputExists) {
      // Set file directly on the input
      await fileInput.setInputFiles(testFilePath);
      console.log('File selected');

      // Wait for upload
      await page.waitForTimeout(3000);

      // Check items after
      const itemsAfter = await page.locator('.grid-row').count();
      console.log('Items after upload:', itemsAfter);

      await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/test-after-upload.png' });
    }

    // Clean up
    fs.unlinkSync(testFilePath);

    console.log('Test complete!');

  } catch (error) {
    console.error('Test failed:', error.message);
    await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/test-upload-error.png' });
  } finally {
    await browser.close();
  }
}

test();
