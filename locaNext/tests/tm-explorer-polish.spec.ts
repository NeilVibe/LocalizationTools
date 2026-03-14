/**
 * Test: TM Explorer Visual Polish + Tab Verification
 * Verifies tree rendering, tab structure, and captures screenshots for human review.
 *
 * Prerequisites: DEV servers running (./scripts/start_all_servers.sh --with-vite)
 */
import { test, expect } from '@playwright/test';

const DEV_URL = 'http://localhost:5173';

/** Helper: Login to the app */
async function loginToApp(page: any) {
  await page.goto(DEV_URL);

  // Mode Selection: click "Login"
  await page.click('text=Login');
  await page.waitForTimeout(500);

  // Login form
  await page.fill('input[placeholder="Enter username"]', 'admin');
  await page.fill('input[placeholder="Enter password"]', 'admin123');
  await page.click('button:has-text("Login"):not(:text-is("Back"))');
  await page.waitForTimeout(5000);
}

/** Helper: Navigate into file explorer and open a file to reach the grid */
async function navigateToGrid(page: any) {
  // Double-click through hierarchy to open a file
  const platformRow = page.locator('[role="row"]').filter({ hasText: 'BDO' }).first();
  await expect(platformRow).toBeVisible({ timeout: 5000 });
  await platformRow.dblclick();
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

test.describe('TM Explorer Polish + Tab Verification', () => {
  test.setTimeout(120000);

  test('Right panel tab bar has all 4 tabs with correct icons and labels', async ({ page }) => {
    await loginToApp(page);
    await navigateToGrid(page);

    // Wait for grid to load
    const targetCells = page.locator('.cell.target');
    await expect(targetCells.first()).toBeVisible({ timeout: 15000 });

    // Verify tab bar exists
    const tabBar = page.locator('[data-testid="right-panel-tabs"]');
    await expect(tabBar).toBeVisible({ timeout: 5000 });

    // Verify all 4 tabs exist and have labels
    const tmTab = page.locator('[data-testid="tab-tm"]');
    const imageTab = page.locator('[data-testid="tab-image"]');
    const audioTab = page.locator('[data-testid="tab-audio"]');
    const contextTab = page.locator('[data-testid="tab-context"]');

    await expect(tmTab).toBeVisible();
    await expect(imageTab).toBeVisible();
    await expect(audioTab).toBeVisible();
    await expect(contextTab).toBeVisible();

    // Verify labels
    await expect(tmTab).toContainText('TM');
    await expect(imageTab).toContainText('Image');
    await expect(audioTab).toContainText('Audio');
    await expect(contextTab).toContainText('AI Context');
  });

  test('Switching tabs changes content area', async ({ page }) => {
    await loginToApp(page);
    await navigateToGrid(page);

    const targetCells = page.locator('.cell.target');
    await expect(targetCells.first()).toBeVisible({ timeout: 15000 });

    // TM tab is active by default
    const tmTab = page.locator('[data-testid="tab-tm"]');
    await expect(tmTab).toHaveClass(/active/);

    // Click Image tab - content should change
    await page.click('[data-testid="tab-image"]');
    await expect(page.locator('.placeholder-tab')).toBeVisible({ timeout: 2000 });
    await expect(page.locator('.placeholder-tab')).toContainText('Image Context');

    // Click Audio tab
    await page.click('[data-testid="tab-audio"]');
    await expect(page.locator('.placeholder-tab')).toContainText('Audio Context');

    // Click AI Context tab
    await page.click('[data-testid="tab-context"]');
    await expect(page.locator('.placeholder-tab')).toContainText('AI Context');

    // Click back to TM - should show tm-tab content
    await page.click('[data-testid="tab-tm"]');
    await expect(page.locator('.tm-tab')).toBeVisible({ timeout: 2000 });
  });

  test('Screenshot: Grid page with right panel tabs for human review', async ({ page }) => {
    await loginToApp(page);
    await navigateToGrid(page);

    const targetCells = page.locator('.cell.target');
    await expect(targetCells.first()).toBeVisible({ timeout: 15000 });

    // Click a row to activate TM search
    const firstSourceCell = page.locator('.cell.source').first();
    await firstSourceCell.click();
    await page.waitForTimeout(3000);

    // Capture full grid page with right panel
    await page.screenshot({ path: '/tmp/tm-grid-with-panel.png', fullPage: false });
    console.log('Screenshot saved: /tmp/tm-grid-with-panel.png');
  });

  test('Screenshot: File explorer tree for human review', async ({ page }) => {
    await loginToApp(page);

    // Wait for file explorer to render
    await page.waitForTimeout(2000);

    // Capture the file explorer
    await page.screenshot({ path: '/tmp/tm-file-explorer.png', fullPage: false });
    console.log('Screenshot saved: /tmp/tm-file-explorer.png');
  });

  test('Screenshot: TM page for human review', async ({ page }) => {
    await loginToApp(page);

    // Navigate to TM page if possible
    const tmNav = page.locator('text=Translation Memor').first();
    const hasTmNav = await tmNav.isVisible().catch(() => false);

    if (hasTmNav) {
      await tmNav.click();
      await page.waitForTimeout(2000);

      const heading = page.locator('h2:has-text("Translation Memories")');
      await expect(heading).toBeVisible({ timeout: 5000 });

      await page.screenshot({ path: '/tmp/tm-page-explorer.png', fullPage: false });
      console.log('Screenshot saved: /tmp/tm-page-explorer.png');
    } else {
      console.log('TM navigation not found - skipping TM page screenshot');
    }
  });
});
