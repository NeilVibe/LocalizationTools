/**
 * Test: Ctrl+S save overflow bug (EDIT-04)
 * Verifies that saving a row does NOT leak text into the next row
 * and that rapid Ctrl+S presses do not cause double saves.
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
  await page.screenshot({ path: '/tmp/grid_test_01_explorer.png' }).catch(() => {});

  // Navigate: Double-click through file explorer hierarchy
  // Step 1: Double-click "BDO" platform row
  const bdoRow = page.locator('[role="row"]').filter({ hasText: 'BDO' }).first();
  await expect(bdoRow).toBeVisible({ timeout: 5000 });
  await bdoRow.dblclick();
  await page.waitForTimeout(2000);
  await page.screenshot({ path: '/tmp/grid_test_02_platform.png' }).catch(() => {});

  // Step 2: Double-click project row
  const projectRow = page.locator('[role="row"]').filter({ hasText: /ITEM|project/i }).first();
  await expect(projectRow).toBeVisible({ timeout: 5000 });
  await projectRow.dblclick();
  await page.waitForTimeout(2000);
  await page.screenshot({ path: '/tmp/grid_test_03_project.png' }).catch(() => {});

  // Step 3: Double-click file to open the LDM grid view
  const fileRow = page.locator('[role="row"]').filter({ hasText: /\.txt|\.xml/ }).first();
  await expect(fileRow).toBeVisible({ timeout: 5000 });
  await fileRow.dblclick();
  await page.waitForTimeout(3000);
  await page.screenshot({ path: '/tmp/grid_test_04_file.png' }).catch(() => {});
}

test.describe.serial('Grid Save No Overflow (EDIT-04)', () => {
  test.setTimeout(120000);

  test('Ctrl+S saves current row text and moves to next without duplicating text', async ({ page }) => {
    await loginAndOpenFile(page);

    // Wait for grid to render
    const targetCells = page.locator('.cell.target');
    await expect(targetCells.first()).toBeVisible({ timeout: 15000 });

    const cellCount = await targetCells.count();
    expect(cellCount).toBeGreaterThan(1);

    // Record original content of the SECOND row (index 1)
    const secondCellContent = await targetCells.nth(1).innerText();
    console.log(`Next row original content: "${secondCellContent}"`);

    // Double-click first target cell to enter edit mode
    await targetCells.first().dblclick();
    await page.waitForTimeout(500);

    // Verify we're in edit mode
    const editArea = page.locator('.inline-edit-textarea[contenteditable="true"]');
    await expect(editArea).toBeVisible({ timeout: 5000 });

    // Type unique test text
    const testText = `OVERFLOW_TEST_${Date.now()}`;
    await page.keyboard.press('Control+a');
    await page.keyboard.type(testText);
    await page.waitForTimeout(300);

    // Press Ctrl+S to confirm and move to next
    await page.keyboard.press('Control+s');
    await page.waitForTimeout(2000);

    // Escape any edit mode on next row
    await page.keyboard.press('Escape');
    await page.waitForTimeout(500);

    // Verify: the first row should now show our test text
    const firstRowText = await targetCells.first().innerText();
    console.log(`First row after save: "${firstRowText}"`);
    expect(firstRowText).toContain(testText);

    // Verify: the NEXT row should still have its original content (NO overflow)
    const nextRowText = await targetCells.nth(1).innerText();
    console.log(`Next row after save: "${nextRowText}"`);
    expect(nextRowText).not.toContain(testText);

    await page.screenshot({ path: '/tmp/grid_overflow_test_result.png' }).catch(() => {});
  });

  test('Rapid Ctrl+S does not cause duplicate saves on same row', async ({ page }) => {
    await loginAndOpenFile(page);

    const targetCells = page.locator('.cell.target');
    await expect(targetCells.first()).toBeVisible({ timeout: 15000 });

    // Double-click to edit
    await targetCells.first().dblclick();
    await page.waitForTimeout(500);

    const editArea = page.locator('.inline-edit-textarea[contenteditable="true"]');
    await expect(editArea).toBeVisible({ timeout: 5000 });

    // Type test text
    const testText = `DOUBLE_SAVE_TEST_${Date.now()}`;
    await page.keyboard.press('Control+a');
    await page.keyboard.type(testText);
    await page.waitForTimeout(200);

    // Intercept API calls to track PUT requests per row URL
    const putRequests: string[] = [];
    page.on('request', (req: any) => {
      if (req.method() === 'PUT' && req.url().includes('/api/ldm/rows/')) {
        putRequests.push(req.url());
      }
    });

    // Rapid Ctrl+S presses - should confirm current row once, then move to next rows
    await page.keyboard.press('Control+s');
    await page.keyboard.press('Control+s');
    await page.keyboard.press('Control+s');
    await page.waitForTimeout(3000);

    // Check that no single row URL was hit more than once (no double-save on same row)
    const urlCounts = new Map<string, number>();
    for (const url of putRequests) {
      urlCounts.set(url, (urlCounts.get(url) || 0) + 1);
    }
    console.log(`PUT requests captured: ${putRequests.length}, unique URLs: ${urlCounts.size}`);
    for (const [url, count] of urlCounts) {
      console.log(`  ${url}: ${count} times`);
      expect(count).toBeLessThanOrEqual(1);
    }

    await page.screenshot({ path: '/tmp/grid_double_save_test.png' }).catch(() => {});
  });

  test('After Ctrl+S, next row content is its own original content', async ({ page }) => {
    await loginAndOpenFile(page);

    const targetCells = page.locator('.cell.target');
    await expect(targetCells.first()).toBeVisible({ timeout: 15000 });

    const cellCount = await targetCells.count();
    expect(cellCount).toBeGreaterThan(2);

    // Record original content of rows
    const originalContents: string[] = [];
    for (let i = 0; i < Math.min(3, cellCount); i++) {
      originalContents.push(await targetCells.nth(i).innerText());
    }
    console.log('Original contents:', originalContents);

    // Edit row 0
    await targetCells.first().dblclick();
    await page.waitForTimeout(500);

    const editArea = page.locator('.inline-edit-textarea[contenteditable="true"]');
    await expect(editArea).toBeVisible({ timeout: 5000 });

    const testText = `ISOLATION_TEST_${Date.now()}`;
    await page.keyboard.press('Control+a');
    await page.keyboard.type(testText);
    await page.waitForTimeout(300);

    // Ctrl+S to confirm and move to next
    await page.keyboard.press('Control+s');
    await page.waitForTimeout(2000);

    // Escape any edit mode on next row
    await page.keyboard.press('Escape');
    await page.waitForTimeout(500);

    // Row 1 should have its own content, not the test text
    const row1After = await targetCells.nth(1).innerText();
    console.log(`Row 1 after row 0 save: "${row1After}"`);
    expect(row1After).not.toContain(testText);

    // Row 2 should be completely unchanged
    if (cellCount > 2) {
      const row2After = await targetCells.nth(2).innerText();
      console.log(`Row 2 after row 0 save: "${row2After}"`);
      expect(row2After).toBe(originalContents[2]);
    }

    await page.screenshot({ path: '/tmp/grid_isolation_test.png' }).catch(() => {});
  });
});
