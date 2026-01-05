/**
 * Test right-clicking on Offline Storage item
 */

const { chromium } = require('playwright');

async function testOfflineStorageContext() {
  console.log('Testing Offline Storage right-click...\n');

  const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
  const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const page = await context.newPage();

  try {
    // Start offline mode
    await page.goto('http://localhost:5173', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    const offlineBtn = page.locator('.offline-btn');
    if (await offlineBtn.count() > 0) {
      await offlineBtn.first().click();
      await page.waitForTimeout(2000);
    }

    // Right-click on Offline Storage item (in the root list)
    console.log('Right-clicking on Offline Storage item...');
    const offlineStorageItem = page.getByText('Offline Storage').first();
    await offlineStorageItem.click({ button: 'right' });
    await page.waitForTimeout(500);

    await page.screenshot({ path: '/tmp/locanext/context_offline_storage.png' });
    console.log('Screenshot: /tmp/locanext/context_offline_storage.png');

    console.log('\n✅ Done');

  } catch (error) {
    console.error('Error:', error.message);
    await page.screenshot({ path: '/tmp/locanext/context_error.png' });
  } finally {
    await browser.close();
  }
}

testOfflineStorageContext();
