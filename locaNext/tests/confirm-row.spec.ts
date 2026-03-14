/**
 * Test: Row Confirmation UI (Ctrl+S) saves to database with 'reviewed' status
 * Verifies the confirm flow sets status correctly via API
 *
 * Prerequisites: DEV servers running (./scripts/start_all_servers.sh --with-vite)
 */
import { test, expect } from '@playwright/test';

const API_BASE = 'http://localhost:8888';
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

test.describe('Row Confirmation UI', () => {
  test.setTimeout(120000);

  test('Ctrl+S in edit mode sets row status to reviewed', async ({ page, request }) => {
    // Get auth token
    const loginResponse = await request.post(`${API_BASE}/api/auth/login`, {
      data: { username: 'admin', password: 'admin123' }
    });
    const { access_token: authToken } = await loginResponse.json();

    await loginAndOpenFile(page);

    const targetCells = page.locator('.cell.target');
    await expect(targetCells.first()).toBeVisible({ timeout: 15000 });

    // Intercept the PUT request to capture the response
    let putResponseStatus = '';
    let putRowId = '';
    page.on('response', async (response: any) => {
      if (response.url().includes('/api/ldm/rows/') && response.request().method() === 'PUT') {
        try {
          const data = await response.json();
          putResponseStatus = data.status;
          putRowId = data.id;
          console.log(`PUT response: row ${data.id}, status=${data.status}`);
        } catch (e) {
          // ignore
        }
      }
    });

    // Edit a row and confirm with Ctrl+S
    await targetCells.nth(5).dblclick();
    await page.waitForTimeout(500);

    const editArea = page.locator('.inline-edit-textarea[contenteditable="true"]');
    await expect(editArea).toBeVisible({ timeout: 5000 });

    const testText = `CONFIRM_TEST_${Date.now()}`;
    await page.keyboard.press('Control+a');
    await page.keyboard.type(testText);
    await page.waitForTimeout(300);

    // Ctrl+S to confirm
    await page.keyboard.press('Control+s');
    await page.waitForTimeout(3000);

    // Verify the API response set status to 'reviewed'
    console.log(`API confirmed status: ${putResponseStatus}`);
    expect(putResponseStatus).toBe('reviewed');

    // Double verify via API
    if (putRowId) {
      const verifyResponse = await request.get(`${API_BASE}/api/ldm/rows/${putRowId}`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
      });
      if (verifyResponse.ok()) {
        const rowData = await verifyResponse.json();
        console.log(`Verified via API: row ${rowData.id}, status=${rowData.status}`);
        expect(rowData.status).toBe('reviewed');
      }
    }

    await page.screenshot({ path: '/tmp/confirm_row_test.png' }).catch(() => {});
  });

  test('Enter save sets row status to translated (not reviewed)', async ({ page }) => {
    await loginAndOpenFile(page);

    const targetCells = page.locator('.cell.target');
    await expect(targetCells.first()).toBeVisible({ timeout: 15000 });

    // Intercept the PUT request
    let putResponseStatus = '';
    page.on('response', async (response: any) => {
      if (response.url().includes('/api/ldm/rows/') && response.request().method() === 'PUT') {
        try {
          const data = await response.json();
          putResponseStatus = data.status;
          console.log(`PUT response: status=${data.status}`);
        } catch (e) {
          // ignore
        }
      }
    });

    // Edit a row and save with Enter (not Ctrl+S)
    await targetCells.nth(6).dblclick();
    await page.waitForTimeout(500);

    const editArea = page.locator('.inline-edit-textarea[contenteditable="true"]');
    await expect(editArea).toBeVisible({ timeout: 5000 });

    const testText = `ENTER_SAVE_TEST_${Date.now()}`;
    await page.keyboard.press('Control+a');
    await page.keyboard.type(testText);
    await page.waitForTimeout(300);

    // Enter to save (translated status)
    await page.keyboard.press('Enter');
    await page.waitForTimeout(3000);

    console.log(`API saved status: ${putResponseStatus}`);
    expect(putResponseStatus).toBe('translated');

    await page.screenshot({ path: '/tmp/confirm_row_enter.png' }).catch(() => {});
  });
});
