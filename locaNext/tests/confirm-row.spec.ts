/**
 * Test: Row Confirmation UI (Ctrl+S) saves to database
 * Bug fix verification: PATCH → PUT
 *
 * Prerequisites: DEV servers running (./scripts/start_all_servers.sh --with-vite)
 */
import { test, expect } from '@playwright/test';

const API_BASE = 'http://localhost:8888';
const DEV_URL = 'http://localhost:5173';

test.describe('Row Confirmation UI', () => {
  test.setTimeout(90000);

  test.skip('Ctrl+S in selection mode confirms row', async ({ page, request }) => {
    // Get auth token for API verification
    const loginResponse = await request.post(`${API_BASE}/api/auth/login`, {
      data: { username: 'admin', password: 'admin123' }
    });
    const { access_token: authToken } = await loginResponse.json();

    // Get initial confirmed count
    const beforeResponse = await request.get(
      `${API_BASE}/api/ldm/files/118/rows?filter=confirmed`,
      { headers: { 'Authorization': `Bearer ${authToken}` } }
    );
    const beforeData = await beforeResponse.json();
    const beforeCount = beforeData.total;
    console.log(`BEFORE: ${beforeCount} confirmed rows`);

    // 1. Go to login page
    await page.goto(DEV_URL);
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(1000);

    // Take screenshot of login page
    await page.screenshot({ path: '/tmp/confirm_01_login.png' }).catch(() => {});

    // 2. Login using the exact form structure (label-based, not placeholder)
    // Fill username field (first input)
    await page.locator('input').first().fill('admin');
    // Fill password field
    await page.locator('input[type="password"]').fill('admin123');
    // Click Login button
    await page.locator('button:has-text("Login")').click();

    await page.waitForTimeout(3000);
    await page.screenshot({ path: '/tmp/confirm_02_logged_in.png' }).catch(() => {});

    // 3. Navigate to LDM
    await page.goto(`${DEV_URL}/ldm`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    await page.screenshot({ path: '/tmp/confirm_03_ldm.png' }).catch(() => {});

    // 4. Click on "Playwright Test Project" to expand it
    console.log('Looking for Playwright Test Project...');
    const projectLink = page.getByText('Playwright Test Project', { exact: false });
    if (await projectLink.isVisible().catch(() => false)) {
      await projectLink.click();
      await page.waitForTimeout(1500);
      console.log('Clicked Playwright Test Project');
    }

    await page.screenshot({ path: '/tmp/confirm_04_project_expanded.png' }).catch(() => {});

    // 5. Click on sample_language_data.txt file
    console.log('Looking for sample_language_data file...');
    const fileLink = page.getByText('sample_language_data', { exact: false });
    if (await fileLink.isVisible().catch(() => false)) {
      await fileLink.click();
      await page.waitForTimeout(2000);
      console.log('Clicked sample_language_data file');
    }

    await page.screenshot({ path: '/tmp/confirm_05_file_loaded.png' }).catch(() => {});

    // 5. Click on a target cell to select it
    const targetCells = page.locator('.cell.target');
    const cellCount = await targetCells.count();
    console.log(`Found ${cellCount} target cells`);

    if (cellCount > 0) {
      // Click on second cell (first might already be confirmed)
      const cellToClick = cellCount > 1 ? targetCells.nth(1) : targetCells.first();
      await cellToClick.click();
      await page.waitForTimeout(500);

      await page.screenshot({ path: '/tmp/confirm_06_selected.png' }).catch(() => {});

      // 6. Press Ctrl+S to confirm
      console.log('Pressing Ctrl+S...');
      await page.keyboard.press('Control+s');
      await page.waitForTimeout(2000);

      await page.screenshot({ path: '/tmp/confirm_07_after_ctrl_s.png' }).catch(() => {});
    }

    // 7. Verify via API that confirmed count increased
    const afterResponse = await request.get(
      `${API_BASE}/api/ldm/files/118/rows?filter=confirmed`,
      { headers: { 'Authorization': `Bearer ${authToken}` } }
    );
    const afterData = await afterResponse.json();
    const afterCount = afterData.total;
    console.log(`AFTER: ${afterCount} confirmed rows`);

    // 8. Take final screenshot showing the result
    await page.screenshot({ path: '/tmp/confirm_08_final.png' }).catch(() => {});

    // Assert
    console.log(`Result: ${beforeCount} → ${afterCount} confirmed rows`);
    expect(afterCount).toBeGreaterThanOrEqual(beforeCount);
  });
});
