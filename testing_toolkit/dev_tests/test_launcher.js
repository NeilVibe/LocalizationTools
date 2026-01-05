/**
 * Quick test to verify Launcher appears on app load
 */
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  
  console.log('📱 Loading app...');
  await page.goto('http://localhost:5173', { waitUntil: 'networkidle' });
  
  // Wait a moment for auth check
  await page.waitForTimeout(1000);
  
  // Take screenshot
  await page.screenshot({ path: '/tmp/launcher_test.png', fullPage: true });
  console.log('📸 Screenshot saved: /tmp/launcher_test.png');
  
  // Check for launcher elements
  const logoText = await page.locator('.logo-text').textContent().catch(() => null);
  const serverStatus = await page.locator('.server-status').isVisible().catch(() => false);
  const offlineBtn = await page.locator('.offline-btn').isVisible().catch(() => false);
  const loginBtn = await page.locator('.login-btn').isVisible().catch(() => false);
  
  console.log('\n--- Launcher Elements ---');
  console.log('Logo text:', logoText);
  console.log('Server status visible:', serverStatus);
  console.log('Offline button visible:', offlineBtn);
  console.log('Login button visible:', loginBtn);
  
  if (logoText === 'LocaNext' && serverStatus && offlineBtn && loginBtn) {
    console.log('\n✅ Launcher is displaying correctly!');
  } else {
    console.log('\n⚠️ Some launcher elements missing');
  }
  
  await browser.close();
})();
