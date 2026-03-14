import { test, expect } from '@playwright/test';

/**
 * Search Verification Test
 *
 * Quick smoke test that search reduces row count in VirtualGrid.
 * Uses existing SMALLTESTFILEFORQUICKSEARCH.txt (1183 rows) in BDO > ITEM project.
 *
 * Requirements: EDIT-03
 */

test.describe('Search Verification Test', () => {
  test('search filters rows and reduces count', async ({ page }) => {
    test.setTimeout(120000);

    // Navigate to app and handle Mode Selection
    await page.goto('http://localhost:5173');
    await page.waitForLoadState('domcontentloaded');

    // Handle Mode Selection screen
    const startOfflineBtn = page.locator('button:has-text("Start Offline")');
    await expect(startOfflineBtn).toBeVisible({ timeout: 15000 });
    await expect(page.locator('text=Central Server Connected')).toBeVisible({ timeout: 15000 });
    const loginBtn = page.locator('button.login-btn');
    await expect(loginBtn).toBeEnabled({ timeout: 5000 });
    await loginBtn.click();
    await expect(page.locator('input[type="password"]')).toBeVisible({ timeout: 5000 });

    // Login
    await page.locator('input').first().fill('admin');
    await page.locator('input[type="password"]').fill('admin123');
    await page.getByRole('button', { name: /login/i }).click();
    await expect(page.getByRole('button', { name: 'Files' })).toBeVisible({ timeout: 15000 });

    // Navigate through explorer: BDO platform > ITEM project > file
    await expect(page.locator('.grid-row').first()).toBeVisible({ timeout: 10000 });

    // Double-click BDO platform
    const bdoRow = page.locator('.grid-row:has(.item-name:text-is("BDO"))');
    await expect(bdoRow).toBeVisible({ timeout: 5000 });
    await bdoRow.dblclick();
    await page.waitForTimeout(1500);

    // Double-click ITEM project
    await expect(page.locator('.grid-row').first()).toBeVisible({ timeout: 10000 });
    const itemRow = page.locator('.grid-row:has(.item-name:text-is("ITEM"))');
    await expect(itemRow).toBeVisible({ timeout: 5000 });
    await itemRow.dblclick();
    await page.waitForTimeout(1500);

    // Double-click SMALLTESTFILEFORQUICKSEARCH.txt
    await expect(page.locator('.grid-row').first()).toBeVisible({ timeout: 10000 });
    const fileRow = page.locator('.grid-row:has(.item-name:has-text("SMALLTESTFILE"))');
    await expect(fileRow).toBeVisible({ timeout: 5000 });
    await fileRow.dblclick();

    // Wait for VirtualGrid to load
    await expect(page.locator('.row-count')).toBeVisible({ timeout: 20000 });
    await page.waitForTimeout(3000);

    // Get initial count
    const initialCountText = await page.textContent('.row-count') || '';
    const initialMatch = initialCountText.match(/([\d,]+)/);
    const initialCount = initialMatch ? parseInt(initialMatch[1].replace(/,/g, '')) : 0;
    expect(initialCount).toBeGreaterThan(0);

    // Type search term and trigger search
    const searchInput = page.locator('#ldm-search-input');
    await expect(searchInput).toBeVisible({ timeout: 5000 });
    await searchInput.focus();

    const responsePromise = page.waitForResponse(
      (resp: any) => resp.url().includes('/rows') && resp.status() === 200,
      { timeout: 15000 }
    );
    await searchInput.fill('dragon');
    await page.keyboard.press('Enter');
    await responsePromise;
    await page.waitForTimeout(500);

    // Get filtered count
    const filteredCountText = await page.textContent('.row-count') || '';
    const filteredMatch = filteredCountText.match(/([\d,]+)/);
    const filteredCount = filteredMatch ? parseInt(filteredMatch[1].replace(/,/g, '')) : 0;

    // Assert search reduces row count
    expect(filteredCount).toBeLessThan(initialCount);
    expect(filteredCount).toBeGreaterThan(0);
  });
});
