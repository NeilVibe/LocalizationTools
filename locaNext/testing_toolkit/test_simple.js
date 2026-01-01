// Simple page load test
import { chromium } from 'playwright';

async function test() {
  console.log('Testing simple page load...');
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  // Capture ALL console messages
  const consoleLogs = [];
  page.on('console', msg => {
    consoleLogs.push(`[${msg.type()}] ${msg.text()}`);
  });

  // Capture page errors
  page.on('pageerror', error => {
    console.log('PAGE ERROR:', error.message);
  });

  try {
    console.log('1. Navigating to localhost:5173...');
    await page.goto('http://localhost:5173', { waitUntil: 'networkidle', timeout: 30000 });
    console.log('   Page loaded');

    // Wait a bit for JS to execute
    await page.waitForTimeout(3000);

    // Check what's visible
    console.log('\n2. Checking page content...');
    const body = await page.locator('body');
    const bodyHTML = await body.innerHTML();
    console.log('   Body HTML length:', bodyHTML.length);

    // Check for login form
    const hasLoginInput = await page.locator('input').count();
    console.log('   Input count:', hasLoginInput);

    const hasButton = await page.locator('button').count();
    console.log('   Button count:', hasButton);

    // Check for loading state
    const loading = await page.locator('.auth-loading').isVisible().catch(() => false);
    console.log('   Auth loading visible:', loading);

    // Check for login form
    const loginVisible = await page.locator('input[type="text"]').isVisible().catch(() => false);
    console.log('   Login input visible:', loginVisible);

    // Screenshot
    await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/simple-test.png', fullPage: true });
    console.log('\n3. Screenshot saved to testing_toolkit/dev_tests/screenshots/simple-test.png');

    // Show console logs
    if (consoleLogs.length > 0) {
      console.log('\n4. Console logs:');
      consoleLogs.slice(-20).forEach(log => console.log('   ' + log));
    }

  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    await browser.close();
  }
}

test();
