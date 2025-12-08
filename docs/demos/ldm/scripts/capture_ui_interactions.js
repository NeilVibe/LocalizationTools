const { chromium } = require('@playwright/test');

async function captureUIInteractions() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 }
  });
  const page = await context.newPage();

  const baseDir = '/home/neil1988/LocalizationTools/docs/demos/ldm/05-ui-interactions';

  try {
    // Login first
    console.log('1. Logging in...');
    await page.goto('http://localhost:5173/', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Check if we need to login
    const loginButton = await page.$('button:has-text("Login")');
    if (loginButton) {
      await page.fill('input[type="text"]', 'admin');
      await page.fill('input[type="password"]', 'admin123');
      await page.click('button:has-text("Login")');
      await page.waitForTimeout(2000);
    }

    // Navigate to LDM
    console.log('2. Navigating to LDM...');
    await page.click('text=Apps');
    await page.waitForTimeout(500);
    await page.click('text=LDM');
    await page.waitForTimeout(3000);

    // Select a project with data
    console.log('3. Selecting project with data...');
    const projectItems = await page.$$('.project-item');
    if (projectItems.length > 0) {
      await projectItems[0].click();
      await page.waitForTimeout(1000);
    }

    // Select a file to load the grid
    console.log('4. Selecting file to load grid...');
    const fileItems = await page.$$('.file-item');
    if (fileItems.length > 0) {
      await fileItems[0].click();
      await page.waitForTimeout(2000);
    }

    // Screenshot 1: Normal grid state
    console.log('5. Capturing normal grid state...');
    await page.screenshot({ path: `${baseDir}/ui_01_grid_normal.png` });
    console.log('   Saved: ui_01_grid_normal.png');

    // Screenshot 2: Row hover effect
    console.log('6. Capturing row hover effect...');
    const rows = await page.$$('.virtual-row:not(.placeholder)');
    if (rows.length >= 3) {
      await rows[2].hover();
      await page.waitForTimeout(300); // Wait for transition
      await page.screenshot({ path: `${baseDir}/ui_02_row_hover.png` });
      console.log('   Saved: ui_02_row_hover.png');
    }

    // Screenshot 3: Row selected state
    console.log('7. Capturing row selected state...');
    if (rows.length >= 3) {
      await rows[2].click();
      await page.waitForTimeout(300);
      await page.screenshot({ path: `${baseDir}/ui_03_row_selected.png` });
      console.log('   Saved: ui_03_row_selected.png');
    }

    // Screenshot 4: Target cell hover
    console.log('8. Capturing target cell hover...');
    const targetCells = await page.$$('.cell.target');
    if (targetCells.length >= 3) {
      await targetCells[2].hover();
      await page.waitForTimeout(300);
      await page.screenshot({ path: `${baseDir}/ui_04_cell_hover.png` });
      console.log('   Saved: ui_04_cell_hover.png');
    }

    // Screenshot 5: Edit modal with TM suggestions
    console.log('9. Capturing edit modal...');
    if (targetCells.length >= 1) {
      await targetCells[0].dblclick();
      await page.waitForTimeout(1500); // Wait for modal + TM fetch
      await page.screenshot({ path: `${baseDir}/ui_05_edit_modal.png` });
      console.log('   Saved: ui_05_edit_modal.png');

      // Close modal
      await page.click('button:has-text("Cancel")');
      await page.waitForTimeout(500);
    }

    console.log('\nDone! Screenshots saved to:', baseDir);

  } catch (err) {
    console.error('Error:', err.message);
    await page.screenshot({ path: `${baseDir}/error_state.png` });
  } finally {
    await browser.close();
  }
}

captureUIInteractions();
