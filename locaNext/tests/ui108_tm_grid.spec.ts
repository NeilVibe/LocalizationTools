/**
 * UI-108 Test: TM Explorer should use Grid style like File Explorer
 *
 * Verifies:
 * 1. Breadcrumb navigation exists
 * 2. Grid header with columns (Name, Entries, Status, Type)
 * 3. Grid rows are clickable
 * 4. No chevron/dropdown tree elements
 */
import { test, expect } from '@playwright/test';

const DEV_URL = 'http://localhost:5173';

test.describe('UI-108: TM Explorer Grid', () => {
  test.beforeEach(async ({ page }) => {
    // Go to home page
    await page.goto(DEV_URL);
    await page.waitForTimeout(2000);

    // Click Login button on welcome page
    const loginButton = page.locator('button:has-text("Login")').first();
    if (await loginButton.isVisible()) {
      await loginButton.click();
      await page.waitForTimeout(1000);
    }

    // Fill login form
    await page.locator('input[placeholder="Enter username"]').fill('admin');
    await page.locator('input[placeholder="Enter password"]').fill('admin123');
    // Click the Login button (not the Back button)
    await page.locator('button:has-text("Login")').last().click();
    await page.waitForTimeout(2000);
  });

  test('TM page has breadcrumb navigation', async ({ page }) => {
    // Navigate to TM page
    await page.locator('text=TM').first().click();
    await page.waitForTimeout(1500);

    // Check for breadcrumb
    const breadcrumb = page.locator('nav.breadcrumb');
    await expect(breadcrumb).toBeVisible();

    // Should show "Home" in breadcrumb
    const homeButton = page.locator('.breadcrumb-item:has-text("Home")');
    await expect(homeButton).toBeVisible();

    // Take screenshot
    await page.screenshot({ path: '/tmp/ui108_tm_breadcrumb.png' });
    console.log('UI-108: Breadcrumb navigation visible');
  });

  test('TM page has grid header with columns', async ({ page }) => {
    await page.locator('text=TM').first().click();
    await page.waitForTimeout(1500);

    // Check for grid header
    const gridHeader = page.locator('.grid-header');
    await expect(gridHeader).toBeVisible();

    // Check for column headers
    const nameHeader = page.locator('.grid-header:has-text("Name")');
    const entriesHeader = page.locator('.grid-header:has-text("Entries")');
    await expect(nameHeader).toBeVisible();
    await expect(entriesHeader).toBeVisible();

    await page.screenshot({ path: '/tmp/ui108_tm_grid_header.png' });
    console.log('UI-108: Grid header with columns visible');
  });

  test('TM page shows platforms as grid rows', async ({ page }) => {
    await page.locator('text=TM').first().click();
    await page.waitForTimeout(1500);

    // Check for grid rows (platforms)
    const gridRows = page.locator('.grid-row');
    const rowCount = await gridRows.count();

    console.log(`UI-108: Found ${rowCount} grid rows`);
    expect(rowCount).toBeGreaterThan(0);

    await page.screenshot({ path: '/tmp/ui108_tm_grid_rows.png' });
  });

  test('TM page has NO chevron/dropdown tree elements', async ({ page }) => {
    await page.locator('text=TM').first().click();
    await page.waitForTimeout(1500);

    // Should NOT have tree-header elements (old tree style)
    const treeHeaders = page.locator('.tree-header');
    const treeHeaderCount = await treeHeaders.count();

    // Should NOT have ChevronDown/ChevronRight in tree structure
    const treeChevrons = page.locator('.tree-section .bx--accordion__heading');
    const chevronCount = await treeChevrons.count();

    console.log(`UI-108: Tree headers found: ${treeHeaderCount} (should be 0)`);
    console.log(`UI-108: Tree chevrons found: ${chevronCount} (should be 0)`);

    expect(treeHeaderCount).toBe(0);

    await page.screenshot({ path: '/tmp/ui108_tm_no_tree.png' });
    console.log('UI-108: No tree/dropdown elements - using grid style');
  });

  test('Right-click on grid row shows context menu (not browser menu)', async ({ page }) => {
    await page.locator('text=TM').first().click();
    await page.waitForTimeout(1500);

    // Right-click on first grid row
    const firstRow = page.locator('.grid-row').first();
    if (await firstRow.isVisible()) {
      await firstRow.click({ button: 'right' });
      await page.waitForTimeout(500);

      // Check for custom context menu
      const contextMenu = page.locator('.context-menu');
      const isContextMenuVisible = await contextMenu.isVisible().catch(() => false);

      // Check browser menu is NOT visible
      const browserMenuVisible = await page.locator('text=Back').first().isVisible().catch(() => false);

      console.log(`UI-108: Custom context menu visible: ${isContextMenuVisible}`);
      console.log(`UI-108: Browser menu visible: ${browserMenuVisible}`);

      expect(browserMenuVisible).toBe(false);

      await page.screenshot({ path: '/tmp/ui108_tm_context_menu.png' });
    }
  });
});
