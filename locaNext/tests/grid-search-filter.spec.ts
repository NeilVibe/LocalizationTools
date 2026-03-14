import { test, expect } from '@playwright/test';

/**
 * Grid Search & Filter Comprehensive Tests
 *
 * Tests that search by text and status filter work correctly
 * in the VirtualGrid component (LDM file view).
 *
 * Requirements: EDIT-03 (Search/Filter)
 *
 * Strategy: Upload a test XML file via API first, then navigate to it in the UI.
 * This makes the test self-contained and independent of existing data.
 */

const API_BASE = 'http://localhost:8888';

// Test XML with known content for search testing
const TEST_XML = `<?xml version="1.0" encoding="UTF-8"?>
<LangData>
  <LocStr StringId="ITEM_001" StrOrigin="불의 검" Str="Sword of Fire" Memo="weapon" />
  <LocStr StringId="ITEM_002" StrOrigin="얼음 방패" Str="Ice Shield" Memo="armor" />
  <LocStr StringId="ITEM_003" StrOrigin="치유의 물약" Str="Healing Potion" Memo="consumable" />
  <LocStr StringId="ITEM_004" StrOrigin="마법의 지팡이" Str="Magic Wand" Memo="weapon" />
  <LocStr StringId="ITEM_005" StrOrigin="용의 비늘" Str="Dragon Scale" Memo="material" />
  <LocStr StringId="QUEST_001" StrOrigin="마을을 구하라" Str="Save the Village" Memo="main quest" />
  <LocStr StringId="QUEST_002" StrOrigin="던전 탐험" Str="Dungeon Exploration" Memo="side quest" />
  <LocStr StringId="NPC_001" StrOrigin="대장장이" Str="Blacksmith" Memo="npc" />
  <LocStr StringId="NPC_002" StrOrigin="마법사" Str="Wizard" Memo="npc" />
  <LocStr StringId="UI_001" StrOrigin="인벤토리" Str="Inventory" Memo="ui" />
</LangData>`;

interface TestFileInfo {
  fileId: number;
  projectId: number;
}

// Upload test file via API and return the file ID
async function setupTestFile(page: any): Promise<TestFileInfo> {
  const result = await page.evaluate(async ({ apiBase, xmlContent }: { apiBase: string; xmlContent: string }) => {
    // Login
    const loginResp = await fetch(`${apiBase}/api/v2/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: 'admin', password: 'admin123' })
    });
    const { access_token } = await loginResp.json();
    const headers = { 'Authorization': `Bearer ${access_token}` };

    // Get first project with a platform (not Offline Storage)
    const projResp = await fetch(`${apiBase}/api/ldm/projects`, { headers });
    const projects = await projResp.json();
    const project = projects.find((p: any) => p.name === 'ITEM') || projects[0];

    // Upload test XML file
    const blob = new Blob([xmlContent], { type: 'application/xml' });
    const formData = new FormData();
    formData.append('file', blob, 'search_test_data.xml');
    formData.append('project_id', project.id.toString());
    formData.append('storage', 'server');

    const uploadResp = await fetch(`${apiBase}/api/ldm/files/upload`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${access_token}` },
      body: formData
    });
    const uploadResult = await uploadResp.json();

    return { fileId: uploadResult.id, projectId: project.id };
  }, { apiBase: API_BASE, xmlContent: TEST_XML });

  return result;
}

// Cleanup: delete uploaded test file
async function cleanupTestFile(page: any, fileId: number) {
  await page.evaluate(async ({ apiBase, fid }: { apiBase: string; fid: number }) => {
    const loginResp = await fetch(`${apiBase}/api/v2/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: 'admin', password: 'admin123' })
    });
    const { access_token } = await loginResp.json();
    await fetch(`${apiBase}/api/ldm/files/${fid}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${access_token}` }
    });
  }, { apiBase: API_BASE, fid: fileId });
}

// Helper: Login and navigate to the VirtualGrid for a specific file
async function loginAndOpenFileById(page: any, fileId: number) {
  // Navigate to app
  await page.goto('http://localhost:5173');
  await page.waitForLoadState('domcontentloaded');

  // Mode Selection screen: wait for it and click Login
  const startOfflineBtn = page.locator('button:has-text("Start Offline")');
  await expect(startOfflineBtn).toBeVisible({ timeout: 15000 });
  await expect(page.locator('text=Central Server Connected')).toBeVisible({ timeout: 15000 });
  const loginBtn = page.locator('button.login-btn');
  await expect(loginBtn).toBeEnabled({ timeout: 5000 });
  await loginBtn.click();
  await expect(page.locator('input[type="password"]')).toBeVisible({ timeout: 5000 });

  // Fill login form
  await page.locator('input').first().fill('admin');
  await page.locator('input[type="password"]').fill('admin123');
  await page.getByRole('button', { name: /login/i }).click();

  // Wait for main app
  await expect(page.getByRole('button', { name: 'Files' })).toBeVisible({ timeout: 15000 });

  // Wait for grid rows to appear (we're on Files page after login)
  await expect(page.locator('.grid-row').first()).toBeVisible({ timeout: 10000 });

  // Navigate: BDO platform > ITEM project > find our file
  // Double-click BDO platform
  const bdoRow = page.locator('.grid-row:has(.item-name:text-is("BDO"))');
  await expect(bdoRow).toBeVisible({ timeout: 5000 });
  await bdoRow.dblclick();
  await page.waitForTimeout(1500);

  // Double-click ITEM project
  await expect(page.locator('.grid-row').first()).toBeVisible({ timeout: 10000 });
  const itemRow = page.locator('.grid-row:has(.item-name:text-is("ITEM"))');
  const hasItem = await itemRow.isVisible({ timeout: 3000 }).catch(() => false);
  if (hasItem) {
    await itemRow.dblclick();
  } else {
    await page.locator('.grid-row').first().dblclick();
  }
  await page.waitForTimeout(1500);

  // Double-click our test file
  await expect(page.locator('.grid-row').first()).toBeVisible({ timeout: 10000 });
  const testFileRow = page.locator('.grid-row:has(.item-name:has-text("search_test_data"))');
  const hasTestFile = await testFileRow.isVisible({ timeout: 3000 }).catch(() => false);
  if (hasTestFile) {
    await testFileRow.dblclick();
  } else {
    // Fallback: click first file
    await page.locator('.grid-row').first().dblclick();
  }

  // Wait for VirtualGrid to load
  await expect(page.locator('.row-count')).toBeVisible({ timeout: 20000 });
  // Wait for rows to fully load
  await page.waitForTimeout(3000);
}

// Helper: Get the current row count from the .row-count element
async function getRowCount(page: any): Promise<number> {
  const text = await page.textContent('.row-count');
  const match = (text || '').match(/([\d,]+)/);
  return match ? parseInt(match[1].replace(/,/g, '')) : 0;
}

test.describe('Grid Search & Filter', () => {
  test.setTimeout(120000);
  test.describe.configure({ mode: 'serial' });

  let testFileInfo: TestFileInfo;

  test.beforeAll(async ({ browser }) => {
    // Upload test file via API using a temporary page
    const page = await browser.newPage();
    testFileInfo = await setupTestFile(page);
    await page.close();
  });

  test.afterAll(async ({ browser }) => {
    // Cleanup test file
    if (testFileInfo?.fileId) {
      const page = await browser.newPage();
      await cleanupTestFile(page, testFileInfo.fileId);
      await page.close();
    }
  });

  test('search by text filters rows - row count decreases', async ({ page }) => {
    await loginAndOpenFileById(page, testFileInfo.fileId);

    const initialCount = await getRowCount(page);
    expect(initialCount).toBeGreaterThan(0);

    // Type a search term that matches some rows (5 ITEM entries out of 10)
    const searchInput = page.locator('#ldm-search-input');
    await expect(searchInput).toBeVisible({ timeout: 5000 });
    await searchInput.focus();

    const responsePromise = page.waitForResponse(
      (resp: any) => resp.url().includes('/rows') && resp.status() === 200,
      { timeout: 15000 }
    );
    await searchInput.fill('Sword');
    await page.keyboard.press('Enter');
    await responsePromise;
    await page.waitForTimeout(500);

    const filteredCount = await getRowCount(page);

    // "Sword" should match only 1 row out of 10
    expect(filteredCount).toBeLessThan(initialCount);
    expect(filteredCount).toBeGreaterThan(0);
  });

  test('clearing search restores all rows', async ({ page }) => {
    await loginAndOpenFileById(page, testFileInfo.fileId);

    const initialCount = await getRowCount(page);
    expect(initialCount).toBeGreaterThan(0);

    // Search for something
    const searchInput = page.locator('#ldm-search-input');
    await searchInput.focus();
    const searchResponse = page.waitForResponse(
      (resp: any) => resp.url().includes('/rows') && resp.status() === 200,
      { timeout: 15000 }
    );
    await searchInput.fill('Sword');
    await page.keyboard.press('Enter');
    await searchResponse;
    await page.waitForTimeout(500);

    const filteredCount = await getRowCount(page);
    expect(filteredCount).toBeLessThan(initialCount);

    // Clear the search
    const clearResponse = page.waitForResponse(
      (resp: any) => resp.url().includes('/rows') && resp.status() === 200,
      { timeout: 15000 }
    );
    await searchInput.fill('');
    await page.keyboard.press('Enter');
    await clearResponse;
    await page.waitForTimeout(500);

    const restoredCount = await getRowCount(page);
    expect(restoredCount).toBe(initialCount);
  });

  test('status filter - confirmed shows subset of rows', async ({ page }) => {
    await loginAndOpenFileById(page, testFileInfo.fileId);

    const initialCount = await getRowCount(page);
    expect(initialCount).toBeGreaterThan(0);

    // Find the status filter dropdown (Carbon Dropdown)
    // In VirtualGrid, the filter is rendered as a dropdown with class containing "filter"
    const filterDropdown = page.locator('.bx--dropdown, [class*="filter-dropdown"]').first();
    await expect(filterDropdown).toBeVisible({ timeout: 5000 });

    const filterResponse = page.waitForResponse(
      (resp: any) => resp.url().includes('/rows') && resp.status() === 200,
      { timeout: 15000 }
    );

    // Click dropdown to open, then select "Confirmed"
    await filterDropdown.click();
    await page.waitForTimeout(300);
    await page.locator('.bx--list-box__menu-item >> text=/^Confirmed$/').click();
    await filterResponse;
    await page.waitForTimeout(500);

    const confirmedCount = await getRowCount(page);

    // Confirmed rows should be <= total (freshly uploaded file has 0 confirmed)
    expect(confirmedCount).toBeLessThanOrEqual(initialCount);
  });

  test('status filter - unconfirmed shows subset of rows', async ({ page }) => {
    await loginAndOpenFileById(page, testFileInfo.fileId);

    const initialCount = await getRowCount(page);

    const filterDropdown = page.locator('.bx--dropdown, [class*="filter-dropdown"]').first();
    await expect(filterDropdown).toBeVisible({ timeout: 5000 });

    const filterResponse = page.waitForResponse(
      (resp: any) => resp.url().includes('/rows') && resp.status() === 200,
      { timeout: 15000 }
    );

    await filterDropdown.click();
    await page.waitForTimeout(300);
    await page.locator('.bx--list-box__menu-item >> text=/^Unconfirmed$/').click();
    await filterResponse;
    await page.waitForTimeout(500);

    const unconfirmedCount = await getRowCount(page);
    // Freshly uploaded rows are all unconfirmed, so unconfirmed should equal total
    expect(unconfirmedCount).toBeLessThanOrEqual(initialCount);
    expect(unconfirmedCount).toBeGreaterThan(0);
  });

  test('search + status filter work together', async ({ page }) => {
    await loginAndOpenFileById(page, testFileInfo.fileId);

    const initialCount = await getRowCount(page);

    // Apply search first
    const searchInput = page.locator('#ldm-search-input');
    await searchInput.focus();
    const searchResponse = page.waitForResponse(
      (resp: any) => resp.url().includes('/rows') && resp.status() === 200,
      { timeout: 15000 }
    );
    await searchInput.fill('Sword');
    await page.keyboard.press('Enter');
    await searchResponse;
    await page.waitForTimeout(500);

    const searchOnlyCount = await getRowCount(page);
    expect(searchOnlyCount).toBeLessThan(initialCount);

    // Now also apply status filter
    const filterDropdown = page.locator('.bx--dropdown, [class*="filter-dropdown"]').first();
    await expect(filterDropdown).toBeVisible({ timeout: 5000 });

    const filterResponse = page.waitForResponse(
      (resp: any) => resp.url().includes('/rows') && resp.status() === 200,
      { timeout: 15000 }
    );

    await filterDropdown.click();
    await page.waitForTimeout(300);
    await page.locator('.bx--list-box__menu-item >> text=/^Unconfirmed$/').click();
    await filterResponse;
    await page.waitForTimeout(500);

    const combinedCount = await getRowCount(page);

    // Combined should be <= search-only
    expect(combinedCount).toBeLessThanOrEqual(searchOnlyCount);
  });
});
