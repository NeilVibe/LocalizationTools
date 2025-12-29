const { chromium } = require('playwright');

(async () => {
  console.log('🧪 Testing Ctrl+D QA Dismiss (Full Flow)...\n');

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });

  // Capture browser console
  const consoleLogs = [];
  page.on('console', msg => {
    const text = msg.text();
    consoleLogs.push(text);
    if (text.includes('QA') || text.includes('dismiss') || text.includes('resolve')) {
      console.log('   [browser]', text);
    }
  });

  // Capture network requests
  const apiCalls = [];
  page.on('request', request => {
    const url = request.url();
    if (url.includes('/api/ldm/')) {
      apiCalls.push({ method: request.method(), url });
    }
  });

  try {
    // 1. Login
    console.log('1. Logging in...');
    await page.goto('http://localhost:5173');
    await page.waitForTimeout(2000);

    const usernameInput = await page.locator('input[placeholder*="username"]').first();
    if (await usernameInput.isVisible()) {
      await usernameInput.fill('admin');
      await page.locator('input[placeholder*="password"]').first().fill('admin123');
      await page.locator('button:has-text("Login")').click();
      await page.waitForTimeout(3000);
    }

    // 2. Navigate to LDM
    console.log('2. Opening LDM...');
    await page.goto('http://localhost:5173/ldm');
    await page.waitForTimeout(3000);

    // 3. Click project and file
    console.log('3. Loading file...');
    await page.locator('.tree-project, .project-item').first().click();
    await page.waitForTimeout(2000);
    await page.locator('.tree-node:not(.folder)').first().click();
    await page.waitForTimeout(2000);

    const cellCount = await page.locator('.cell.target').count();
    console.log(`   ✓ Loaded ${cellCount} target cells`);

    // 4. Single click to select a row (selection mode)
    console.log('\n4. Selecting a row (single click)...');
    const targetCell = page.locator('.cell.target').first();
    await targetCell.click();
    await page.waitForTimeout(500);

    // 5. Check if QA issues loaded (API call)
    console.log('\n5. Checking for QA API calls...');
    const qaResultsCalls = apiCalls.filter(c => c.url.includes('qa-results'));
    console.log(`   QA results API calls: ${qaResultsCalls.length}`);
    qaResultsCalls.forEach(c => console.log(`   - ${c.method} ${c.url}`));

    // 6. Focus grid and press Ctrl+D
    console.log('\n6. Pressing Ctrl+D to dismiss QA...');
    await page.locator('.virtual-grid').focus();
    await page.waitForTimeout(100);

    // Clear API calls to track new ones
    const callsBefore = apiCalls.length;

    await page.keyboard.press('Control+d');
    await page.waitForTimeout(1000);

    // 7. Check for resolve API calls
    console.log('\n7. Checking for resolve API calls...');
    const newCalls = apiCalls.slice(callsBefore);
    const resolveCalls = newCalls.filter(c => c.url.includes('resolve'));
    console.log(`   New API calls after Ctrl+D: ${newCalls.length}`);
    newCalls.forEach(c => console.log(`   - ${c.method} ${c.url}`));

    if (resolveCalls.length > 0) {
      console.log('\n   ✅ Resolve API was called!');
    } else {
      console.log('\n   ⚠️ No resolve API calls (may have no QA issues to dismiss)');
    }

    // 8. Check console logs for QA messages
    console.log('\n8. QA-related console logs:');
    const qaLogs = consoleLogs.filter(l =>
      l.includes('QA') || l.includes('dismiss') || l.includes('resolve')
    );
    if (qaLogs.length === 0) {
      console.log('   (no QA logs found)');
    }

    await page.screenshot({ path: '/tmp/ctrl_d_test.png' });
    console.log('\n✅ Test complete! Screenshot: /tmp/ctrl_d_test.png');

  } catch (err) {
    console.error('❌ Error:', err.message);
    await page.screenshot({ path: '/tmp/ctrl_d_error.png' }).catch(() => {});
  }

  await browser.close();
})();
