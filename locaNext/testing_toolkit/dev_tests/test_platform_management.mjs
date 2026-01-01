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

  await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/platform-1-after-login.png' });

  console.log('3. Navigating to LDM...');
  const ldmLink = await page.locator('text=LDM').first();
  if (await ldmLink.count() > 0) {
    await ldmLink.click();
    await page.waitForTimeout(1500);
  }

  await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/platform-2-ldm.png' });

  console.log('4. Checking root view for platforms...');
  // Check what's in the explorer grid
  const gridRows = await page.locator('.grid-row').count();
  console.log(`   Grid rows visible: ${gridRows}`);

  // Check for platform items (blue icon)
  const platformItems = await page.locator('.grid-row.platform').count();
  console.log(`   Platform items: ${platformItems}`);

  // Check for project items (green icon)
  const projectItems = await page.locator('.grid-row.project').count();
  console.log(`   Project items: ${projectItems}`);

  await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/platform-3-root-view.png' });

  console.log('\n5. Testing right-click context menu on empty space...');
  // Right-click on empty space in the grid
  const gridBody = await page.locator('.grid-body').first();
  if (await gridBody.count() > 0) {
    await gridBody.click({ button: 'right', position: { x: 400, y: 200 } });
    await page.waitForTimeout(500);

    await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/platform-4-context-menu.png' });

    // Check for "New Platform" option
    const newPlatformBtn = await page.locator('text=New Platform').count();
    console.log(`   "New Platform" menu option: ${newPlatformBtn > 0 ? 'YES' : 'NO'}`);

    // Check for "New Project" option
    const newProjectBtn = await page.locator('text=New Project').count();
    console.log(`   "New Project" menu option: ${newProjectBtn > 0 ? 'YES' : 'NO'}`);

    // Close menu
    await page.click('body');
    await page.waitForTimeout(300);
  }

  console.log('\n6. Testing creating a new platform...');
  // Right-click again and click "New Platform"
  await gridBody.click({ button: 'right', position: { x: 400, y: 200 } });
  await page.waitForTimeout(500);

  const newPlatformMenu = await page.locator('.context-menu-item:has-text("New Platform")').first();
  if (await newPlatformMenu.count() > 0) {
    await newPlatformMenu.click();
    await page.waitForTimeout(500);

    await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/platform-5-create-modal.png' });

    // Check for modal
    const modal = await page.locator('.bx--modal').count();
    console.log(`   Modal open: ${modal > 0 ? 'YES' : 'NO'}`);

    // Type platform name
    const platformInput = await page.locator('input[placeholder*="platform"]').first();
    if (await platformInput.count() > 0) {
      await platformInput.fill('TestPlatform_Sprint5');
      await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/platform-6-name-entered.png' });

      // Click Create button inside the open modal
      const createBtn = await page.locator('.bx--modal.is-visible button.bx--btn--primary:has-text("Create")').first();
      if (await createBtn.count() > 0) {
        await createBtn.click();
        await page.waitForTimeout(1500);
      }
    }
  }

  await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/platform-7-after-create.png' });

  // Check if platform was created
  const newPlatform = await page.locator('text=TestPlatform_Sprint5').count();
  console.log(`   Platform created: ${newPlatform > 0 ? 'YES' : 'NO'}`);

  // Check for platform icon (blue)
  const platformCount = await page.locator('.grid-row.platform').count();
  console.log(`   Total platforms now: ${platformCount}`);

  console.log('\n7. Testing platform right-click menu...');
  if (newPlatform > 0) {
    await page.locator('text=TestPlatform_Sprint5').first().click({ button: 'right' });
    await page.waitForTimeout(500);

    await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/platform-8-platform-context.png' });

    // Check for Rename and Delete options
    const renameOption = await page.locator('.context-menu-item:has-text("Rename")').count();
    const deleteOption = await page.locator('.context-menu-item:has-text("Delete")').count();
    console.log(`   Rename option: ${renameOption > 0 ? 'YES' : 'NO'}`);
    console.log(`   Delete option: ${deleteOption > 0 ? 'YES' : 'NO'}`);

    await page.click('body');
    await page.waitForTimeout(300);
  }

  console.log('\n8. Testing double-click to enter platform...');
  if (newPlatform > 0) {
    await page.locator('text=TestPlatform_Sprint5').first().dblclick();
    await page.waitForTimeout(1500);

    await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/platform-9-inside-platform.png' });

    // Check breadcrumb
    const breadcrumb = await page.locator('.breadcrumb-bar').textContent();
    console.log(`   Breadcrumb: "${breadcrumb.trim()}"`);

    // Check for Application icon in breadcrumb (platform icon)
    const platformInBreadcrumb = breadcrumb.includes('TestPlatform_Sprint5');
    console.log(`   Platform in breadcrumb: ${platformInBreadcrumb ? 'YES' : 'NO'}`);
  }

  console.log('\n9. Cleaning up - delete test platform...');
  // Navigate back to home
  await page.locator('.breadcrumb-item:has-text("Home")').click();
  await page.waitForTimeout(1500);

  // Right-click on test platform and delete
  const testPlatform = await page.locator('text=TestPlatform_Sprint5').first();
  if (await testPlatform.count() > 0) {
    await testPlatform.click({ button: 'right' });
    await page.waitForTimeout(500);

    const deleteBtn = await page.locator('.context-menu-item:has-text("Delete")');
    if (await deleteBtn.count() > 0) {
      await deleteBtn.click();
      await page.waitForTimeout(500);

      await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/platform-10-delete-confirm.png' });

      // Confirm delete
      const confirmBtn = await page.locator('button:has-text("Delete")');
      if (await confirmBtn.count() > 0) {
        await confirmBtn.click();
        await page.waitForTimeout(1500);
      }
    }
  }

  await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/platform-11-final.png' });

  const platformAfterDelete = await page.locator('text=TestPlatform_Sprint5').count();
  console.log(`   Platform deleted: ${platformAfterDelete === 0 ? 'YES' : 'NO'}`);

  console.log('\n=== SPRINT 5 PLATFORM MANAGEMENT TEST COMPLETE ===');

} catch (err) {
  console.error('Error:', err.message);
  await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/platform-error.png' });
} finally {
  await browser.close();
}
