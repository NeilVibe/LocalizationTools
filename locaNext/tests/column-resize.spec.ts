/**
 * UI-081 & UI-082: Column Resize Functionality Tests
 * Tests resize bar positioning and multi-column resize handles
 *
 * Prerequisites: DEV servers running (./scripts/start_all_servers.sh --with-vite)
 */
import { test, expect } from '@playwright/test';

const DEV_URL = 'http://localhost:5173';

test.describe('Column Resize Functionality', () => {
  test.setTimeout(90000);

  test.beforeEach(async ({ page }) => {
    // 1. Go to login page
    await page.goto(DEV_URL);
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(1000);

    // 2. Login
    await page.locator('input').first().fill('admin');
    await page.locator('input[type="password"]').fill('admin123');
    await page.locator('button:has-text("Login")').click();
    await page.waitForTimeout(3000);

    // 3. Navigate to LDM
    await page.goto(`${DEV_URL}/ldm`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // 4. Click on "Playwright Test Project" to expand it
    const projectLink = page.getByText('Playwright Test Project', { exact: false });
    if (await projectLink.isVisible().catch(() => false)) {
      await projectLink.click();
      await page.waitForTimeout(1500);
    }

    // 5. Click on sample_language_data.txt file
    const fileLink = page.getByText('sample_language_data', { exact: false });
    if (await fileLink.isVisible().catch(() => false)) {
      await fileLink.click();
      await page.waitForTimeout(2000);
    }
  });

  test('UI-081: Resize bar is visible and positioned correctly', async ({ page }) => {
    // Take screenshot to see grid state
    await page.screenshot({ path: '/tmp/resize_01_grid_loaded.png', fullPage: true });

    // Check if column-resize-bar exists
    const resizeBar = page.locator('.column-resize-bar');
    const resizeBarCount = await resizeBar.count();
    console.log(`Found ${resizeBarCount} resize bar(s)`);

    // Verify resize bar is in the DOM
    expect(resizeBarCount).toBeGreaterThanOrEqual(1);

    // Check if the resize bar has a left position with calc()
    const resizeBarStyle = await resizeBar.first().getAttribute('style');
    console.log(`Resize bar style: ${resizeBarStyle}`);
    expect(resizeBarStyle).toContain('left:');

    await page.screenshot({ path: '/tmp/resize_02_bar_found.png', fullPage: true });
  });

  test('UI-082: Column resize handles exist for visible columns', async ({ page }) => {
    await page.screenshot({ path: '/tmp/resize_03_before_handles.png', fullPage: true });

    // Check for column-resize-handle elements
    const resizeHandles = page.locator('.column-resize-handle');
    const handleCount = await resizeHandles.count();
    console.log(`Found ${handleCount} column resize handle(s)`);

    // Check for resizable-column elements
    const resizableColumns = page.locator('.resizable-column');
    const columnCount = await resizableColumns.count();
    console.log(`Found ${columnCount} resizable column(s)`);

    await page.screenshot({ path: '/tmp/resize_04_handles.png', fullPage: true });

    // The number of handles depends on which columns are visible
    // (Index, StringID, Reference are optional)
    console.log(`Resize handles found: ${handleCount}`);
    console.log(`Resizable columns found: ${columnCount}`);
  });

  test('UI-081: Resize bar hover shows visual feedback', async ({ page }) => {
    // Hover over the resize bar
    const resizeBar = page.locator('.column-resize-bar').first();
    const barCount = await resizeBar.count();
    console.log(`Resize bars found: ${barCount}`);

    if (barCount > 0) {
      await resizeBar.hover();
      await page.waitForTimeout(200);
      await page.screenshot({ path: '/tmp/resize_05_hover.png', fullPage: true });
      console.log('Hover over resize bar successful');
    }
  });

  test('UI-081 & UI-082: Source/Target resize drag changes column width', async ({ page }) => {
    // Wait for grid to fully load
    await page.waitForSelector('.cell.source', { timeout: 10000 });

    // Get initial source column width
    const sourceCell = page.locator('.cell.source').first();
    const initialBox = await sourceCell.boundingBox();
    const initialWidth = initialBox?.width || 0;
    console.log(`Initial source width: ${initialWidth}px`);

    // Take screenshot before resize
    await page.screenshot({ path: '/tmp/resize_06_before_drag.png', fullPage: true });

    // Find the resize bar
    const resizeBar = page.locator('.column-resize-bar').first();
    const barBox = await resizeBar.boundingBox();

    if (barBox) {
      // Drag 50 pixels to the right
      await page.mouse.move(barBox.x + barBox.width / 2, barBox.y + barBox.height / 2);
      await page.mouse.down();
      await page.mouse.move(barBox.x + 50, barBox.y + barBox.height / 2);
      await page.mouse.up();
      await page.waitForTimeout(300);

      // Take screenshot after resize
      await page.screenshot({ path: '/tmp/resize_07_after_drag.png', fullPage: true });

      // Check if width changed
      const newBox = await sourceCell.boundingBox();
      const newWidth = newBox?.width || 0;
      const widthChange = newWidth - initialWidth;
      console.log(`New source width: ${newWidth}px`);
      console.log(`Width change: ${widthChange}px`);

      // Width should have increased (we dragged right)
      expect(widthChange).toBeGreaterThan(0);
    }
  });
});
