import { chromium } from 'playwright';

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage();

try {
  console.log('1. Loading page...');
  await page.goto('http://localhost:5173', { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);

  console.log('2. Logging in as admin...');
  const inputs = await page.locator('input').all();
  if (inputs.length >= 2) {
    await inputs[0].fill('admin');
    await inputs[1].fill('admin123');

    const submitBtn = await page.locator('button[type="submit"]');
    if (await submitBtn.count() > 0) {
      await submitBtn.click();
      await page.waitForTimeout(2000);
    }
  }

  await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/tm-visual-1-after-login.png' });

  console.log('3. Navigating to LDM...');
  const ldmLink = await page.locator('text=LDM').first();
  if (await ldmLink.count() > 0) {
    await ldmLink.click();
    await page.waitForTimeout(1500);
  }

  await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/tm-visual-2-ldm.png' });

  console.log('4. Looking for dzad project (admin\'s project)...');
  // Look for dzad project (project 72)
  const projectItems = await page.locator('.file-tree-item, [data-project]').all();
  console.log(`   Found ${projectItems.length} tree items`);

  // Look for project by text
  const projectByName = await page.locator('text=dzad').first();
  if (await projectByName.count() > 0) {
    console.log('   Found dzad project, double-clicking...');
    await projectByName.dblclick();
    await page.waitForTimeout(1500);
  } else {
    // Try looking for any project
    console.log('   dzad not found, looking for alternatives...');
    const allText = await page.content();
    console.log('   Page has dzad:', allText.includes('dzad'));

    // Screenshot the current state
    await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/tm-visual-3-projects.png' });
  }

  await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/tm-visual-4-project-open.png' });

  console.log('5. Looking for test_file_proper.txt...');
  const testFile = await page.locator('text=test_file_proper').first();
  if (await testFile.count() > 0) {
    console.log('   Found test file, double-clicking...');
    await testFile.dblclick();
    await page.waitForTimeout(2500);

    await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/tm-visual-5-file-open.png' });

    console.log('6. Checking TM indicator...');

    // Check for TM indicator elements
    const tmIndicator = await page.locator('.tm-indicator').count();
    const tmBadge = await page.locator('.tm-badge').count();
    const tmNone = await page.locator('.tm-none').count();
    const tmLoading = await page.locator('.tm-loading').count();

    console.log('\nResults:');
    console.log('  TM Indicator element: ' + (tmIndicator > 0 ? '✓ YES' : '✗ NO'));
    console.log('  TM Badge: ' + (tmBadge > 0 ? '✓ YES' : '✗ NO'));
    console.log('  No TM text: ' + (tmNone > 0 ? 'YES' : 'NO'));
    console.log('  Loading state: ' + (tmLoading > 0 ? 'YES' : 'NO'));

    if (tmBadge > 0) {
      const badgeText = await page.locator('.tm-badge').textContent();
      console.log('  Badge text: "' + badgeText.trim() + '"');

      // Take screenshot of the grid with TM indicator
      await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/tm-visual-6-tm-badge.png' });

      // Click to open dropdown
      console.log('\n7. Testing dropdown...');
      await page.click('.tm-badge');
      await page.waitForTimeout(500);

      const dropdown = await page.locator('.tm-dropdown').count();
      console.log('  Dropdown visible: ' + (dropdown > 0 ? '✓ YES' : '✗ NO'));

      if (dropdown > 0) {
        await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/tm-visual-7-dropdown-open.png' });

        const items = await page.locator('.tm-dropdown-item').count();
        console.log('  TM items in dropdown: ' + items);

        // Get item text
        const itemTexts = await page.locator('.tm-dropdown-item').allTextContents();
        itemTexts.forEach((t, i) => console.log(`    Item ${i+1}: ${t.trim().substring(0, 50)}...`));
      }

      console.log('\n✅ TM INDICATOR TEST PASSED!');
    } else if (tmNone > 0) {
      console.log('\n⚠️ TM indicator shows "No active TM" - hierarchy may not be set up correctly');
    } else {
      console.log('\n❌ TM indicator not found - check component rendering');
    }

  } else {
    console.log('   test_file_proper.txt not found in file tree');
    // Check what's visible
    const fileItems = await page.locator('.file-item, [data-file]').allTextContents();
    console.log('   Visible files:', fileItems.slice(0, 5));
  }

} catch (err) {
  console.error('Error:', err.message);
  await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/tm-visual-error.png' });
} finally {
  await browser.close();
}
