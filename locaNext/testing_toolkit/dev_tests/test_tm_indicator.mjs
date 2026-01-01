import { chromium } from 'playwright';

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage();

try {
  console.log('1. Loading page...');
  await page.goto('http://localhost:5173', { waitUntil: 'networkidle' });
  await page.waitForTimeout(3000);
  
  // Take initial screenshot
  await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/tm-test-1-initial.png' });
  
  console.log('2. Checking for login form...');
  const loginInput = await page.locator('input').first();
  if (await loginInput.count() > 0) {
    console.log('   Found input fields, filling login...');
    const inputs = await page.locator('input').all();
    if (inputs.length >= 2) {
      await inputs[0].fill('admin');
      await inputs[1].fill('admin123');
      await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/tm-test-2-login.png' });
      
      const submitBtn = await page.locator('button[type="submit"]');
      if (await submitBtn.count() > 0) {
        await submitBtn.click();
        await page.waitForTimeout(2000);
      }
    }
  }
  
  await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/tm-test-3-after-login.png' });
  
  console.log('3. Looking for LDM...');
  const ldmLink = await page.locator('text=LDM').first();
  if (await ldmLink.count() > 0) {
    await ldmLink.click();
    await page.waitForTimeout(1500);
  }
  
  await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/tm-test-4-ldm.png' });
  
  console.log('4. Looking for project...');
  const project = await page.locator('text=Simple Test Project').first();
  if (await project.count() > 0) {
    await project.dblclick();
    await page.waitForTimeout(1000);
    await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/tm-test-5-project.png' });
    
    console.log('5. Opening file...');
    const file = await page.locator('text=simple_test.txt').first();
    if (await file.count() > 0) {
      await file.dblclick();
      await page.waitForTimeout(2500);
      
      await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/tm-test-6-file.png' });
      
      console.log('6. Checking TM indicator...');
      const tmBadge = await page.locator('.tm-badge').count();
      const tmNone = await page.locator('.tm-none').count();
      const tmIndicator = await page.locator('.tm-indicator').count();
      
      console.log('\nResults:');
      console.log('  TM Indicator element: ' + (tmIndicator > 0 ? 'YES' : 'NO'));
      console.log('  TM Badge: ' + (tmBadge > 0 ? 'YES' : 'NO'));
      console.log('  No TM text: ' + (tmNone > 0 ? 'YES' : 'NO'));
      
      if (tmBadge > 0) {
        const text = await page.locator('.tm-badge').textContent();
        console.log('  Badge text: "' + text.trim() + '"');
        
        await page.click('.tm-badge');
        await page.waitForTimeout(500);
        await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/tm-test-7-dropdown.png' });
        
        const dropdown = await page.locator('.tm-dropdown').count();
        console.log('  Dropdown: ' + (dropdown > 0 ? 'OPEN' : 'NOT OPEN'));
      }
      
      console.log('\nDone!');
    } else {
      console.log('File not found');
    }
  } else {
    console.log('Project not found');
  }
} catch (err) {
  console.error('Error:', err.message);
  await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/tm-test-error.png' });
} finally {
  await browser.close();
}
