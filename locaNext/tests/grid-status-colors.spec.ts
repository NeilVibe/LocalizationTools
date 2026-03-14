/**
 * Test: 3-state status color coding (EDIT-02)
 * Verifies that rows display correct visual indicators based on status:
 * - Green: confirmed (reviewed/approved)
 * - Yellow/amber: draft (translated)
 * - Gray: empty (pending/untranslated)
 *
 * Prerequisites: DEV servers running (./scripts/start_all_servers.sh --with-vite)
 */
import { test, expect } from '@playwright/test';

const DEV_URL = 'http://localhost:5173';
const API_BASE = 'http://localhost:8888';

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
  await page.waitForTimeout(5000);

  // Navigate: Double-click through file explorer
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

test.describe.serial('Grid Status Colors (EDIT-02)', () => {
  test.setTimeout(120000);

  test('Confirmed row (reviewed) shows green left-border indicator', async ({ page, request }) => {
    // First ensure we have a reviewed row via API
    const loginResponse = await request.post(`${API_BASE}/api/auth/login`, {
      data: { username: 'admin', password: 'admin123' }
    });
    const { access_token: authToken } = await loginResponse.json();

    // Get rows and find/create a reviewed row
    const filesResponse = await request.get(`${API_BASE}/api/ldm/files`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });
    const files = await filesResponse.json();
    const file = files.find((f: any) => f.row_count > 0);

    const rowsResponse = await request.get(`${API_BASE}/api/ldm/files/${file.id}/rows?limit=5`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });
    const rowsData = await rowsResponse.json();
    const targetRow = rowsData.rows[0];

    // Set the row to "reviewed" status
    await request.put(`${API_BASE}/api/ldm/rows/${targetRow.id}`, {
      headers: {
        'Authorization': `Bearer ${authToken}`,
        'Content-Type': 'application/json'
      },
      data: { status: 'reviewed' }
    });

    // Now load the UI and check the visual
    await loginAndOpenFile(page);

    const targetCells = page.locator('.cell.target');
    await expect(targetCells.first()).toBeVisible({ timeout: 15000 });

    // Check that the first target cell has status-reviewed class
    const firstCell = targetCells.first();
    const hasReviewedClass = await firstCell.evaluate((el: Element) =>
      el.classList.contains('status-reviewed')
    );
    console.log(`First cell has status-reviewed class: ${hasReviewedClass}`);
    expect(hasReviewedClass).toBe(true);

    // Verify the green border-left color
    const borderColor = await firstCell.evaluate((el: Element) =>
      getComputedStyle(el).borderLeftColor
    );
    console.log(`Border left color: ${borderColor}`);
    // Should be green (#24a148 = rgb(36, 161, 72))
    expect(borderColor).toMatch(/rgb\(36,\s*161,\s*72\)/);

    await page.screenshot({ path: '/tmp/grid_status_green.png' }).catch(() => {});
  });

  test('Draft row (translated) shows yellow/amber left-border indicator', async ({ page, request }) => {
    await loginAndOpenFile(page);

    const targetCells = page.locator('.cell.target');
    await expect(targetCells.first()).toBeVisible({ timeout: 15000 });

    // Find a cell that has status-translated class, or edit a cell to make it translated
    // Edit the 3rd row using Enter (not Ctrl+S) to save as "translated" status
    await targetCells.nth(2).dblclick();
    await page.waitForTimeout(500);

    const editArea = page.locator('.inline-edit-textarea[contenteditable="true"]');
    await expect(editArea).toBeVisible({ timeout: 5000 });

    const testText = `YELLOW_TEST_${Date.now()}`;
    await page.keyboard.press('Control+a');
    await page.keyboard.type(testText);
    await page.waitForTimeout(300);

    // Press Enter to save as "translated" (NOT Ctrl+S which saves as "reviewed")
    await page.keyboard.press('Enter');
    await page.waitForTimeout(2000);

    // Escape from next row edit
    await page.keyboard.press('Escape');
    await page.waitForTimeout(500);

    // Check row 2 (index 2) now has status-translated class
    const editedCell = targetCells.nth(2);
    const hasTranslatedClass = await editedCell.evaluate((el: Element) =>
      el.classList.contains('status-translated')
    );
    console.log(`Edited cell has status-translated class: ${hasTranslatedClass}`);
    expect(hasTranslatedClass).toBe(true);

    // Verify yellow/amber border-left color
    const borderColor = await editedCell.evaluate((el: Element) =>
      getComputedStyle(el).borderLeftColor
    );
    console.log(`Border left color: ${borderColor}`);
    // Should be yellow/amber (#c6a300 = rgb(198, 163, 0))
    expect(borderColor).toMatch(/rgb\(198,\s*163,\s*0\)/);

    await page.screenshot({ path: '/tmp/grid_status_yellow.png' }).catch(() => {});
  });

  test('Empty row (pending) shows default gray styling', async ({ page }) => {
    await loginAndOpenFile(page);

    const targetCells = page.locator('.cell.target');
    await expect(targetCells.first()).toBeVisible({ timeout: 15000 });

    // Find a cell that doesn't have status-translated, status-reviewed, or status-approved
    // Check multiple cells until we find an unstyled one
    const cellCount = await targetCells.count();
    let foundGrayCell = false;

    for (let i = 0; i < Math.min(cellCount, 10); i++) {
      const cell = targetCells.nth(i);
      const hasStatusClass = await cell.evaluate((el: Element) =>
        el.classList.contains('status-translated') ||
        el.classList.contains('status-reviewed') ||
        el.classList.contains('status-approved')
      );

      if (!hasStatusClass) {
        console.log(`Cell ${i} is unstyled (gray/pending)`);
        // Verify it does NOT have a colored left border
        const borderStyle = await cell.evaluate((el: Element) =>
          getComputedStyle(el).borderLeftStyle
        );
        const borderWidth = await cell.evaluate((el: Element) =>
          getComputedStyle(el).borderLeftWidth
        );
        console.log(`Border: ${borderWidth} ${borderStyle}`);
        // Gray cells should not have a 3px solid border
        const has3pxBorder = borderWidth === '3px';
        // If it has 3px border, it should NOT be green or yellow
        if (has3pxBorder) {
          const borderColor = await cell.evaluate((el: Element) =>
            getComputedStyle(el).borderLeftColor
          );
          expect(borderColor).not.toMatch(/rgb\(36,\s*161,\s*72\)/);
          expect(borderColor).not.toMatch(/rgb\(198,\s*163,\s*0\)/);
        }
        foundGrayCell = true;
        break;
      }
    }
    expect(foundGrayCell).toBe(true);

    await page.screenshot({ path: '/tmp/grid_status_gray.png' }).catch(() => {});
  });

  test('Edit+Enter changes row from gray to yellow (draft)', async ({ page }) => {
    await loginAndOpenFile(page);

    const targetCells = page.locator('.cell.target');
    await expect(targetCells.first()).toBeVisible({ timeout: 15000 });

    // Find an unstyled cell
    const cellCount = await targetCells.count();
    let targetIndex = -1;
    for (let i = 3; i < Math.min(cellCount, 10); i++) {
      const hasStatusClass = await targetCells.nth(i).evaluate((el: Element) =>
        el.classList.contains('status-translated') ||
        el.classList.contains('status-reviewed') ||
        el.classList.contains('status-approved')
      );
      if (!hasStatusClass) {
        targetIndex = i;
        break;
      }
    }

    if (targetIndex === -1) {
      console.log('No unstyled cells found, using first cell');
      targetIndex = 0;
    }

    // Edit the cell and save with Enter (translated status)
    await targetCells.nth(targetIndex).dblclick();
    await page.waitForTimeout(500);

    const editArea = page.locator('.inline-edit-textarea[contenteditable="true"]');
    await expect(editArea).toBeVisible({ timeout: 5000 });

    const testText = `GRAY_TO_YELLOW_${Date.now()}`;
    await page.keyboard.press('Control+a');
    await page.keyboard.type(testText);
    await page.waitForTimeout(300);

    // Enter = save as translated
    await page.keyboard.press('Enter');
    await page.waitForTimeout(2000);
    await page.keyboard.press('Escape');
    await page.waitForTimeout(500);

    // Verify the cell now has status-translated
    const editedCell = targetCells.nth(targetIndex);
    const hasTranslatedClass = await editedCell.evaluate((el: Element) =>
      el.classList.contains('status-translated')
    );
    console.log(`Cell ${targetIndex} has status-translated after Enter: ${hasTranslatedClass}`);
    expect(hasTranslatedClass).toBe(true);

    await page.screenshot({ path: '/tmp/grid_status_gray_to_yellow.png' }).catch(() => {});
  });

  test('Confirm (Ctrl+S) changes row to green (confirmed)', async ({ page }) => {
    await loginAndOpenFile(page);

    const targetCells = page.locator('.cell.target');
    await expect(targetCells.first()).toBeVisible({ timeout: 15000 });

    // Edit a cell and confirm with Ctrl+S
    await targetCells.nth(4).dblclick();
    await page.waitForTimeout(500);

    const editArea = page.locator('.inline-edit-textarea[contenteditable="true"]');
    await expect(editArea).toBeVisible({ timeout: 5000 });

    const testText = `CONFIRM_GREEN_${Date.now()}`;
    await page.keyboard.press('Control+a');
    await page.keyboard.type(testText);
    await page.waitForTimeout(300);

    // Ctrl+S = confirm as reviewed (green)
    await page.keyboard.press('Control+s');
    await page.waitForTimeout(2000);
    await page.keyboard.press('Escape');
    await page.waitForTimeout(500);

    // Verify the cell now has status-reviewed
    const confirmedCell = targetCells.nth(4);
    const hasReviewedClass = await confirmedCell.evaluate((el: Element) =>
      el.classList.contains('status-reviewed')
    );
    console.log(`Cell 4 has status-reviewed after Ctrl+S: ${hasReviewedClass}`);
    expect(hasReviewedClass).toBe(true);

    // Verify green border
    const borderColor = await confirmedCell.evaluate((el: Element) =>
      getComputedStyle(el).borderLeftColor
    );
    console.log(`Border color: ${borderColor}`);
    expect(borderColor).toMatch(/rgb\(36,\s*161,\s*72\)/);

    await page.screenshot({ path: '/tmp/grid_status_confirm_green.png' }).catch(() => {});
  });
});
