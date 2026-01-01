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

  console.log('3. Navigating to LDM...');
  const ldmLink = await page.locator('text=LDM').first();
  if (await ldmLink.count() > 0) {
    await ldmLink.click();
    await page.waitForTimeout(1500);
  }

  await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/hierarchy-1-root.png' });

  // Check root view
  console.log('\n=== Root View ===');
  const platforms = await page.locator('.grid-row.platform').count();
  const projects = await page.locator('.grid-row.project').count();
  console.log(`Platforms: ${platforms}, Unassigned Projects: ${projects}`);

  // Should see MyPlatform, no projects at root (since project is assigned to platform)
  if (platforms > 0 && projects === 0) {
    console.log('CORRECT: Projects are not shown at root when assigned to platform');
  } else if (projects > 0) {
    console.log('WARNING: Projects shown at root - they might not be assigned to platforms');
  }

  // Double-click platform to enter
  console.log('\n4. Entering MyPlatform...');
  const myPlatform = await page.locator('.grid-row.platform:has-text("MyPlatform")').first();
  if (await myPlatform.count() > 0) {
    await myPlatform.dblclick();
    await page.waitForTimeout(1500);
  }

  await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/hierarchy-2-platform.png' });

  // Check platform contents
  console.log('\n=== Inside Platform ===');
  const projectsInPlatform = await page.locator('.grid-row.project').count();
  console.log(`Projects in platform: ${projectsInPlatform}`);

  // Double-click project to enter
  console.log('\n5. Entering MyProject...');
  const myProject = await page.locator('.grid-row.project:has-text("MyProject")').first();
  if (await myProject.count() > 0) {
    await myProject.dblclick();
    await page.waitForTimeout(1500);
  }

  await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/hierarchy-3-project.png' });

  // Check project contents
  console.log('\n=== Inside Project ===');
  const files = await page.locator('.grid-row').count();
  console.log(`Items in project: ${files}`);

  // Double-click file to open in grid
  console.log('\n6. Opening file...');
  const myFile = await page.locator('.grid-row:has-text("mytest")').first();
  if (await myFile.count() > 0) {
    await myFile.dblclick();
    await page.waitForTimeout(2500);
  }

  await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/hierarchy-4-file.png' });

  // Check TM indicator (updated for simple display - no dropdown)
  console.log('\n=== TM Indicator Check ===');
  const tmIndicator = await page.locator('.tm-indicator').count();
  const tmInfo = await page.locator('.tm-info').count();
  const tmNone = await page.locator('.tm-none').count();
  const tmLoading = await page.locator('.tm-loading').count();

  console.log(`TM Indicator element: ${tmIndicator > 0 ? 'YES' : 'NO'}`);
  console.log(`TM Info (simple display): ${tmInfo > 0 ? 'YES' : 'NO'}`);
  console.log(`No TM text: ${tmNone > 0 ? 'YES' : 'NO'}`);
  console.log(`Loading state: ${tmLoading > 0 ? 'YES' : 'NO'}`);

  if (tmInfo > 0) {
    const infoText = await page.locator('.tm-info').textContent();
    console.log(`TM Info text: "${infoText.trim()}"`);

    await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/hierarchy-5-tm-info.png' });

    console.log('\nSUCCESS: TM indicator is working with hierarchy!');
  } else if (tmNone > 0) {
    console.log('\nFAILURE: TM indicator shows "No active TM"');
    console.log('Expected: TM should be active because file is in project assigned to platform with active TM');
  }

  console.log('\n=== TEST COMPLETE ===');

} catch (err) {
  console.error('Error:', err.message);
  await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/hierarchy-error.png' });
} finally {
  await browser.close();
}
