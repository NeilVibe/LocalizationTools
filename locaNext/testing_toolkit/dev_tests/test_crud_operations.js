// Test CRUD operations - Create folder, Upload file, etc.
import { chromium } from 'playwright';

const BASE_URL = 'http://localhost:5173';

async function testCRUD() {
  console.log('Testing CRUD Operations...\n');

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
  const page = await context.newPage();

  // Capture ALL console messages
  const logs = [];
  page.on('console', msg => {
    const text = msg.text();
    logs.push({ type: msg.type(), text: text.substring(0, 200) });
    if (msg.type() === 'error') {
      console.log(`  [CONSOLE ERROR] ${text.substring(0, 150)}`);
    }
  });

  // Capture network errors
  page.on('requestfailed', request => {
    console.log(`  [NETWORK FAIL] ${request.method()} ${request.url()} - ${request.failure()?.errorText}`);
  });

  // Capture response errors
  page.on('response', response => {
    if (response.status() >= 400) {
      console.log(`  [HTTP ${response.status()}] ${response.url()}`);
    }
  });

  try {
    // 1. Login
    console.log('1. Logging in...');
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
    await page.waitForSelector('.bx--text-input', { timeout: 10000 });
    await page.locator('.bx--text-input').first().fill('admin');
    await page.locator('input[type="password"]').fill('admin123');
    await page.click('button[type="submit"]');
    await page.waitForSelector('.ldm-app', { timeout: 10000 });
    console.log('   OK');

    await page.waitForTimeout(1000);

    // 2. Enter a project
    console.log('\n2. Entering project...');
    const firstProject = page.locator('.grid-row').first();
    if (await firstProject.isVisible()) {
      await firstProject.dblclick();
      await page.waitForTimeout(1000);
      console.log('   Entered project');
    } else {
      console.log('   No projects found!');
    }

    // 3. Try to create a folder via context menu
    console.log('\n3. Testing Create Folder...');

    // Right-click on empty area
    const gridBody = page.locator('.grid-body');
    if (await gridBody.isVisible()) {
      const box = await gridBody.boundingBox();
      await page.mouse.click(box.x + box.width / 2, box.y + box.height - 50, { button: 'right' });
      await page.waitForTimeout(500);

      // Check context menu
      const contextMenu = await page.locator('.context-menu').isVisible();
      console.log(`   Context menu visible: ${contextMenu}`);

      if (contextMenu) {
        // Screenshot before clicking
        await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/crud-context-menu.png' });

        // Click New Folder
        const newFolderItem = page.locator('.context-menu-item:has-text("New Folder")');
        if (await newFolderItem.isVisible()) {
          console.log('   Clicking "New Folder"...');
          await newFolderItem.click();
          await page.waitForTimeout(500);

          // Check if modal appeared
          const modal = page.locator('.bx--modal');
          const modalVisible = await modal.isVisible().catch(() => false);
          console.log(`   Modal appeared: ${modalVisible}`);

          if (modalVisible) {
            // Screenshot of modal
            await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/crud-folder-modal.png' });

            // Fill in folder name
            const input = page.locator('.bx--modal input[type="text"], .bx--modal .bx--text-input');
            if (await input.isVisible()) {
              await input.fill('TestFolder_' + Date.now());
              console.log('   Filled folder name');

              // Click Create button
              const createBtn = page.locator('.bx--modal button:has-text("Create")');
              if (await createBtn.isVisible()) {
                console.log('   Clicking Create...');
                await createBtn.click();
                await page.waitForTimeout(2000);

                // Screenshot after create
                await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/crud-after-create.png' });
              }
            }
          }
        } else {
          console.log('   "New Folder" not in context menu');
          // Screenshot to see what's there
          await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/crud-no-newfolder.png' });
        }
      }
    }

    // 4. Try to upload a file
    console.log('\n4. Testing Upload File...');

    // Right-click again
    const gridBody2 = page.locator('.grid-body');
    if (await gridBody2.isVisible()) {
      const box = await gridBody2.boundingBox();
      await page.mouse.click(box.x + box.width / 2, box.y + box.height - 50, { button: 'right' });
      await page.waitForTimeout(500);

      const uploadItem = page.locator('.context-menu-item:has-text("Upload")');
      if (await uploadItem.isVisible()) {
        console.log('   "Upload File" found in menu');

        // We can't actually upload without a file, but we can check if the input exists
        const fileInput = page.locator('input[type="file"]');
        const fileInputExists = await fileInput.count() > 0;
        console.log(`   Hidden file input exists: ${fileInputExists}`);
      } else {
        console.log('   "Upload File" not in context menu');
      }
    }

    // Close any open menu
    await page.keyboard.press('Escape');

    // 5. Print all console errors
    console.log('\n5. Console Errors Summary:');
    const errors = logs.filter(l => l.type === 'error');
    if (errors.length === 0) {
      console.log('   No console errors');
    } else {
      errors.forEach(e => console.log(`   - ${e.text}`));
    }

    // 6. Print all warnings that might indicate issues
    console.log('\n6. Warnings/Info:');
    const warnings = logs.filter(l => l.type === 'warning' || l.text.includes('fail') || l.text.includes('error'));
    warnings.slice(0, 10).forEach(w => console.log(`   - ${w.text}`));

    console.log('\nCRUD Test Complete!\n');

  } catch (error) {
    console.error('\nTest failed:', error.message);
    await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/crud-error.png' });
  } finally {
    await browser.close();
  }
}

testCRUD();
