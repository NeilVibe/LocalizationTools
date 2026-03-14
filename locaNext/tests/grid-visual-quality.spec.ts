/**
 * Test: Grid visual quality screenshot baseline (UI-01)
 * Captures screenshots of the polished grid for human review.
 * Does NOT use pixel-perfect comparison (too brittle).
 *
 * Screenshots saved to /tmp/grid-visual-quality-*.png
 *
 * Prerequisites: DEV servers running (./scripts/start_all_servers.sh --with-vite)
 */
import { test, expect } from '@playwright/test';

const DEV_URL = 'http://localhost:5173';

/** Helper: Login and navigate to a file with rows in the grid */
async function loginAndOpenFile(page: any) {
  await page.goto(DEV_URL);

  // Mode Selection: click "Login"
  await page.click('text=Login');
  await page.waitForTimeout(500);

  // Login form
  await page.fill('input[placeholder="Enter username"]', 'admin');
  await page.fill('input[placeholder="Enter password"]', 'admin123');
  await page.click('button:has-text("Login"):not(:text-is("Back"))');

  // Wait for main file explorer to load
  await page.waitForTimeout(5000);

  // Navigate: Double-click through file explorer hierarchy
  const bdoRow = page.locator('[role="row"]').filter({ hasText: 'BDO' }).first();
  await expect(bdoRow).toBeVisible({ timeout: 5000 });
  await bdoRow.dblclick();
  await page.waitForTimeout(2000);

  const projectRow = page.locator('[role="row"]').filter({ hasText: /ITEM|project/i }).first();
  await expect(projectRow).toBeVisible({ timeout: 5000 });
  await projectRow.dblclick();
  await page.waitForTimeout(2000);

  const fileRow = page.locator('[role="row"]').filter({ hasText: /\.txt|\.xml/ }).first();
  await expect(fileRow).toBeVisible({ timeout: 5000 });
  await fileRow.dblclick();
  await page.waitForTimeout(3000);
}

test.describe.serial('Grid Visual Quality Baseline (UI-01)', () => {
  test.setTimeout(120000);

  test('Capture grid with rows loaded', async ({ page }) => {
    await loginAndOpenFile(page);

    // Wait for grid to render
    const targetCells = page.locator('.cell.target');
    await expect(targetCells.first()).toBeVisible({ timeout: 15000 });

    // Full page screenshot showing grid layout
    await page.screenshot({
      path: '/tmp/grid-visual-quality-01-full-grid.png',
      fullPage: false
    });

    // Grid area only
    const gridArea = page.locator('.virtual-grid');
    if (await gridArea.isVisible()) {
      await gridArea.screenshot({
        path: '/tmp/grid-visual-quality-02-grid-area.png'
      });
    }

    console.log('Grid with rows screenshot captured');
  });

  test('Capture hover state on rows', async ({ page }) => {
    await loginAndOpenFile(page);

    const targetCells = page.locator('.cell.target');
    await expect(targetCells.first()).toBeVisible({ timeout: 15000 });

    // Hover over a source cell (avoids column resize bar interception)
    const thirdSource = page.locator('.cell.source').nth(2);
    if (await thirdSource.isVisible()) {
      await thirdSource.hover({ force: true });
      await page.waitForTimeout(300); // Let transition complete
    }

    await page.screenshot({
      path: '/tmp/grid-visual-quality-03-hover-state.png',
      fullPage: false
    });

    // Hover over target cell specifically to show edit indicator
    const secondTarget = targetCells.nth(1);
    if (await secondTarget.isVisible()) {
      await secondTarget.hover({ force: true });
      await page.waitForTimeout(300);
    }

    await page.screenshot({
      path: '/tmp/grid-visual-quality-04-target-hover.png',
      fullPage: false
    });

    console.log('Hover state screenshots captured');
  });

  test('Capture status colors visible', async ({ page }) => {
    await loginAndOpenFile(page);

    const targetCells = page.locator('.cell.target');
    await expect(targetCells.first()).toBeVisible({ timeout: 15000 });

    // Check for status color indicators
    const draftCells = page.locator('.cell.target.status-translated');
    const confirmedCells = page.locator('.cell.target.status-reviewed, .cell.target.status-approved');

    const draftCount = await draftCells.count();
    const confirmedCount = await confirmedCells.count();

    console.log(`Status cells: ${draftCount} draft (yellow), ${confirmedCount} confirmed (green)`);

    await page.screenshot({
      path: '/tmp/grid-visual-quality-05-status-colors.png',
      fullPage: false
    });

    // Capture header area separately for typography review
    const header = page.locator('.table-header');
    if (await header.isVisible()) {
      await header.screenshot({
        path: '/tmp/grid-visual-quality-06-header.png'
      });
    }

    console.log('Status color and header screenshots captured');
  });
});
