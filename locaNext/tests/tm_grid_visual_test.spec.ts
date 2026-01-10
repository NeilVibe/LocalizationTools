/**
 * TM Grid Visual Test - Full Screenshots
 *
 * Takes screenshots to visually verify the new TM Explorer Grid UI
 */
import { test, expect } from '@playwright/test';

const DEV_URL = 'http://localhost:5173';

test.describe('TM Grid Visual Test', () => {
  test('Full TM Grid visual verification', async ({ page }) => {
    // 1. Go to app
    await page.goto(DEV_URL);
    await page.waitForTimeout(2000);

    // 2. Login
    const loginButton = page.locator('button:has-text("Login")').first();
    if (await loginButton.isVisible()) {
      await loginButton.click();
      await page.waitForTimeout(1000);
    }

    await page.locator('input[placeholder="Enter username"]').fill('admin');
    await page.locator('input[placeholder="Enter password"]').fill('admin123');
    await page.locator('button:has-text("Login")').last().click();
    await page.waitForTimeout(2500);

    // Screenshot 1: Main app after login
    await page.screenshot({ path: '/tmp/tm_grid_01_after_login.png', fullPage: true });
    console.log('Screenshot 1: After login - saved');

    // 3. Navigate to TM page
    await page.locator('text=TM').first().click();
    await page.waitForTimeout(2000);

    // Screenshot 2: TM Grid Home view
    await page.screenshot({ path: '/tmp/tm_grid_02_home_view.png', fullPage: true });
    console.log('Screenshot 2: TM Grid Home view - saved');

    // Check for breadcrumb
    const breadcrumb = page.locator('nav.breadcrumb');
    const hasBreadcrumb = await breadcrumb.isVisible();
    console.log(`Breadcrumb visible: ${hasBreadcrumb}`);

    // Check for grid header
    const gridHeader = page.locator('.grid-header');
    const hasGridHeader = await gridHeader.isVisible();
    console.log(`Grid header visible: ${hasGridHeader}`);

    // Check for grid rows
    const gridRows = page.locator('.grid-row');
    const rowCount = await gridRows.count();
    console.log(`Grid rows found: ${rowCount}`);

    // 4. If there are rows, click on first one to enter
    if (rowCount > 0) {
      const firstRow = gridRows.first();
      const rowName = await firstRow.locator('.item-name').textContent();
      console.log(`First row name: ${rowName}`);

      // Double-click to enter
      await firstRow.dblclick();
      await page.waitForTimeout(1500);

      // Screenshot 3: Inside platform/project
      await page.screenshot({ path: '/tmp/tm_grid_03_inside_platform.png', fullPage: true });
      console.log('Screenshot 3: Inside platform - saved');

      // Check breadcrumb updated
      const breadcrumbText = await page.locator('nav.breadcrumb').textContent();
      console.log(`Breadcrumb after navigation: ${breadcrumbText}`);
    }

    // 5. Right-click test
    const currentRows = page.locator('.grid-row');
    const currentRowCount = await currentRows.count();

    if (currentRowCount > 0) {
      await currentRows.first().click({ button: 'right' });
      await page.waitForTimeout(500);

      // Screenshot 4: Context menu
      await page.screenshot({ path: '/tmp/tm_grid_04_context_menu.png', fullPage: true });
      console.log('Screenshot 4: Context menu - saved');

      // Check context menu visible
      const contextMenu = page.locator('.context-menu');
      const hasContextMenu = await contextMenu.isVisible();
      console.log(`Context menu visible: ${hasContextMenu}`);

      // Close context menu
      await page.click('body');
      await page.waitForTimeout(300);
    }

    // 6. Go back to home via breadcrumb
    await page.locator('.breadcrumb-item:has-text("Home")').click();
    await page.waitForTimeout(1000);

    // Screenshot 5: Back at home
    await page.screenshot({ path: '/tmp/tm_grid_05_back_home.png', fullPage: true });
    console.log('Screenshot 5: Back at home - saved');

    console.log('\n=== TM GRID VISUAL TEST COMPLETE ===');
    console.log('Screenshots saved to /tmp/tm_grid_*.png');
  });
});
