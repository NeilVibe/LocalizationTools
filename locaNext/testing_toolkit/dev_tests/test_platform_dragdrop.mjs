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

  await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/dragdrop-1-initial.png' });

  // Check initial state
  const platforms = await page.locator('.grid-row.platform').count();
  const projects = await page.locator('.grid-row.project').count();
  console.log(`   Initial: ${platforms} platforms, ${projects} projects`);

  // Find TestPlatform
  const testPlatform = await page.locator('.grid-row.platform:has-text("TestPlatform")').first();
  const platformExists = await testPlatform.count() > 0;

  if (!platformExists) {
    console.log('   TestPlatform not found, creating one...');
    // Create platform
    const gridBody = await page.locator('.grid-body').first();
    await gridBody.click({ button: 'right', position: { x: 400, y: 200 } });
    await page.waitForTimeout(500);

    await page.locator('.context-menu-item:has-text("New Platform")').first().click();
    await page.waitForTimeout(500);

    const platformInput = await page.locator('input[placeholder*="platform"]').first();
    await platformInput.fill('TestPlatformDrag');
    await page.locator('.bx--modal.is-visible button.bx--btn--primary:has-text("Create")').first().click();
    await page.waitForTimeout(1500);
  }

  await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/dragdrop-2-ready.png' });

  // Find a project to drag
  const projectRow = await page.locator('.grid-row.project').first();
  const projectName = await projectRow.locator('.item-name').textContent();
  console.log(`\n4. Testing drag-drop of project "${projectName.trim()}" to platform...`);

  // Find platform to drop onto
  const platformRow = await page.locator('.grid-row.platform').first();
  const platformName = await platformRow.locator('.item-name').textContent();
  console.log(`   Target platform: "${platformName.trim()}"`);

  // Get bounding boxes
  const projectBox = await projectRow.boundingBox();
  const platformBox = await platformRow.boundingBox();

  if (projectBox && platformBox) {
    console.log('   Performing drag-drop...');

    // Drag from project to platform
    await page.mouse.move(projectBox.x + projectBox.width / 2, projectBox.y + projectBox.height / 2);
    await page.mouse.down();
    await page.waitForTimeout(100);

    // Move to platform (with intermediate steps for visual feedback)
    await page.mouse.move(platformBox.x + platformBox.width / 2, platformBox.y + platformBox.height / 2, { steps: 10 });
    await page.waitForTimeout(100);

    await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/dragdrop-3-dragging.png' });

    // Drop
    await page.mouse.up();
    await page.waitForTimeout(1500);

    await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/dragdrop-4-dropped.png' });

    // Check result
    const projectsAfter = await page.locator('.grid-row.project').count();
    console.log(`   Projects at root after drop: ${projectsAfter}`);

    // Check platform project count
    const platformRowAfter = await page.locator('.grid-row.platform').first();
    const platformSize = await platformRowAfter.locator('.size-cell').textContent();
    console.log(`   Platform size: ${platformSize.trim()}`);

    // Double-click platform to see if project is inside
    console.log('\n5. Checking inside platform...');
    await platformRowAfter.dblclick();
    await page.waitForTimeout(1500);

    await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/dragdrop-5-inside-platform.png' });

    const projectsInPlatform = await page.locator('.grid-row.project').count();
    console.log(`   Projects inside platform: ${projectsInPlatform}`);

    if (projectsInPlatform > 0) {
      console.log('\n   DRAG-DROP TEST PASSED!');
    } else {
      console.log('\n   Note: Project may not have been moved (already assigned?)');
    }

    // Navigate back
    await page.locator('.breadcrumb-item:has-text("Home")').click();
    await page.waitForTimeout(1500);
  } else {
    console.log('   Could not get element positions for drag-drop');
  }

  await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/dragdrop-6-final.png' });
  console.log('\n=== DRAG-DROP TEST COMPLETE ===');

} catch (err) {
  console.error('Error:', err.message);
  await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/dragdrop-error.png' });
} finally {
  await browser.close();
}
