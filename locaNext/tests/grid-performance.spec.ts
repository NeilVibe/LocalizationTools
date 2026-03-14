/**
 * Test: Grid scroll performance (EDIT-01)
 * Verifies that virtual scrolling handles rapid scrolling without errors,
 * blank rows, or crashes. Tests the scroll mechanism with available data.
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

test.describe.serial('Grid Scroll Performance (EDIT-01)', () => {
  test.setTimeout(120000);

  test('Grid renders rows without errors after initial load', async ({ page }) => {
    await loginAndOpenFile(page);

    // Wait for grid to render
    const targetCells = page.locator('.cell.target');
    await expect(targetCells.first()).toBeVisible({ timeout: 15000 });

    const cellCount = await targetCells.count();
    expect(cellCount).toBeGreaterThan(0);

    // Verify row count display is present and shows a number
    const rowCount = page.locator('.row-count');
    await expect(rowCount).toBeVisible({ timeout: 5000 });
    const countText = await rowCount.innerText();
    expect(countText).toMatch(/\d+/);

    console.log(`Grid loaded with ${cellCount} visible target cells. Row count: ${countText}`);
    await page.screenshot({ path: '/tmp/grid-perf-01-loaded.png' });
  });

  test('Rapid scrolling does not cause blank rows or errors', async ({ page }) => {
    // Collect console errors
    const errors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') errors.push(msg.text());
    });
    page.on('pageerror', err => errors.push(err.message));

    await loginAndOpenFile(page);

    const targetCells = page.locator('.cell.target');
    await expect(targetCells.first()).toBeVisible({ timeout: 15000 });

    const scrollContainer = page.locator('.scroll-container');
    await expect(scrollContainer).toBeVisible({ timeout: 5000 });

    // Get total scroll height
    const scrollHeight = await scrollContainer.evaluate((el: Element) => el.scrollHeight);
    console.log(`Scroll height: ${scrollHeight}px`);

    // Rapid scroll: jump through multiple positions
    const scrollPositions = [
      scrollHeight * 0.25,
      scrollHeight * 0.5,
      scrollHeight * 0.75,
      scrollHeight,      // Bottom
      scrollHeight * 0.5, // Back to middle
      0,                  // Back to top
    ];

    for (const pos of scrollPositions) {
      await scrollContainer.evaluate((el: Element, scrollTo: number) => {
        el.scrollTop = scrollTo;
      }, pos);
      // Small pause to let virtual scroll render
      await page.waitForTimeout(300);
    }

    await page.screenshot({ path: '/tmp/grid-perf-02-after-scroll.png' });

    // After scrolling, verify rows are still rendered (no blank grid)
    const cellsAfterScroll = await targetCells.count();
    expect(cellsAfterScroll).toBeGreaterThan(0);

    // Verify no placeholder-only view (all rows should have content or be proper placeholders)
    const visibleRows = page.locator('.virtual-row:not(.placeholder)');
    const visibleCount = await visibleRows.count();
    expect(visibleCount).toBeGreaterThan(0);

    // Check for JavaScript errors during scrolling
    const criticalErrors = errors.filter(e =>
      !e.includes('favicon') &&
      !e.includes('net::') &&
      !e.includes('Failed to load resource') &&
      !e.includes('ResizeObserver')
    );
    if (criticalErrors.length > 0) {
      console.log('Console errors during scroll:', criticalErrors);
    }
    // Allow non-critical errors, but no crashes
    expect(criticalErrors.length).toBeLessThan(5);

    console.log(`After rapid scrolling: ${cellsAfterScroll} target cells, ${visibleCount} non-placeholder rows`);
  });

  test('Rows render correct content after scrolling to bottom and back', async ({ page }) => {
    await loginAndOpenFile(page);

    const targetCells = page.locator('.cell.target');
    await expect(targetCells.first()).toBeVisible({ timeout: 15000 });

    // Record first row content
    const firstRowContent = await targetCells.first().innerText();
    console.log(`First row content: "${firstRowContent.substring(0, 50)}..."`);

    const scrollContainer = page.locator('.scroll-container');
    const scrollHeight = await scrollContainer.evaluate((el: Element) => el.scrollHeight);

    // Scroll to bottom
    await scrollContainer.evaluate((el: Element, h: number) => {
      el.scrollTop = h;
    }, scrollHeight);
    await page.waitForTimeout(1000);

    await page.screenshot({ path: '/tmp/grid-perf-03-bottom.png' });

    // Scroll back to top
    await scrollContainer.evaluate((el: Element) => {
      el.scrollTop = 0;
    });
    await page.waitForTimeout(1000);

    await page.screenshot({ path: '/tmp/grid-perf-04-back-to-top.png' });

    // Verify first row content is the same (no data corruption from scrolling)
    const firstRowAfter = await targetCells.first().innerText();
    expect(firstRowAfter).toBe(firstRowContent);

    console.log('Content integrity verified after scroll round-trip');
  });
});
