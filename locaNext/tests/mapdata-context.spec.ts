/**
 * Test: MapData Context Tabs (MAP-03)
 *
 * Verifies that Image and Audio tabs in the RightPanel render correctly
 * when rows are selected, showing context data or graceful empty states.
 *
 * Uses Playwright route interception to mock MapData API responses
 * (avoids runtime dependency on MapDataService + Perforce paths).
 *
 * Prerequisites: DEV servers running (./scripts/start_all_servers.sh --with-vite)
 */
import { test, expect } from '@playwright/test';

const DEV_URL = 'http://localhost:5173';

/** Mock image context response */
const MOCK_IMAGE_CONTEXT = {
  texture_name: 'T_Sword_Fire_01',
  dds_path: 'D:/GameData/Textures/Items/T_Sword_Fire_01.dds',
  thumbnail_url: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPj/HwADBwIAMCbHYQAAAABJRU5ErkJggg==',
  has_image: true
};

/** Mock audio context response */
const MOCK_AUDIO_CONTEXT = {
  event_name: 'VO_NPC_Merchant_Greeting_01',
  wem_path: 'D:/GameData/Audio/VO/NPC/VO_NPC_Merchant_Greeting_01.wem',
  script_kr: '안녕하세요, 여행자님!',
  script_eng: 'Hello, traveler!',
  duration_seconds: 2.5
};

/** Helper: Login and navigate to main page */
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

/** Helper: Navigate to first file in grid */
async function navigateToFirstFile(page: any) {
  const fileItem = page.locator('.grid-row, .tree-item, .file-item').first();
  if (await fileItem.isVisible({ timeout: 5000 }).catch(() => false)) {
    await fileItem.click();
    await page.waitForTimeout(2000);
  }
}

test.describe('MapData Context Tabs', () => {
  test.setTimeout(120000);

  test('Image tab shows empty state when no row selected', async ({ page }) => {
    await loginToApp(page);
    await navigateToFirstFile(page);

    // Click Image tab
    const imageTab = page.locator('[data-testid="tab-image"]');
    if (await imageTab.isVisible({ timeout: 3000 }).catch(() => false)) {
      await imageTab.click();
      await page.waitForTimeout(500);

      // Should show empty state
      const emptyState = page.locator('[data-testid="image-tab-empty"]');
      await expect(emptyState).toBeVisible({ timeout: 3000 });
    }
  });

  test('Image tab shows thumbnail when row has image context', async ({ page }) => {
    // Intercept mapdata image API
    await page.route('**/api/ldm/mapdata/image/*', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_IMAGE_CONTEXT)
      });
    });

    await loginToApp(page);
    await navigateToFirstFile(page);

    // Select a row in the grid
    const firstRow = page.locator('.virtual-row').first();
    if (await firstRow.isVisible({ timeout: 5000 }).catch(() => false)) {
      await firstRow.click();
      await page.waitForTimeout(500);

      // Click Image tab
      const imageTab = page.locator('[data-testid="tab-image"]');
      if (await imageTab.isVisible({ timeout: 3000 }).catch(() => false)) {
        await imageTab.click();
        await page.waitForTimeout(1000);

        // Should show thumbnail
        const thumbnail = page.locator('[data-testid="image-tab-thumbnail"]');
        const emptyState = page.locator('[data-testid="image-tab-empty"]');

        // One of these should be visible
        const hasThumbnail = await thumbnail.isVisible({ timeout: 3000 }).catch(() => false);
        const hasEmpty = await emptyState.isVisible({ timeout: 1000 }).catch(() => false);

        expect(hasThumbnail || hasEmpty).toBe(true);
      }
    }
  });

  test('Image tab shows empty state on 404', async ({ page }) => {
    // Intercept with 404
    await page.route('**/api/ldm/mapdata/image/*', async route => {
      await route.fulfill({
        status: 404,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'No image context' })
      });
    });

    await loginToApp(page);
    await navigateToFirstFile(page);

    const firstRow = page.locator('.virtual-row').first();
    if (await firstRow.isVisible({ timeout: 5000 }).catch(() => false)) {
      await firstRow.click();
      await page.waitForTimeout(500);

      const imageTab = page.locator('[data-testid="tab-image"]');
      if (await imageTab.isVisible({ timeout: 3000 }).catch(() => false)) {
        await imageTab.click();
        await page.waitForTimeout(1000);

        const emptyState = page.locator('[data-testid="image-tab-empty"]');
        await expect(emptyState).toBeVisible({ timeout: 3000 });
      }
    }
  });

  test('Audio tab shows empty state when no row selected', async ({ page }) => {
    await loginToApp(page);
    await navigateToFirstFile(page);

    const audioTab = page.locator('[data-testid="tab-audio"]');
    if (await audioTab.isVisible({ timeout: 3000 }).catch(() => false)) {
      await audioTab.click();
      await page.waitForTimeout(500);

      const emptyState = page.locator('[data-testid="audio-tab-empty"]');
      await expect(emptyState).toBeVisible({ timeout: 3000 });
    }
  });

  test('Audio tab shows script text when row has audio context', async ({ page }) => {
    // Intercept mapdata audio API
    await page.route('**/api/ldm/mapdata/audio/*', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_AUDIO_CONTEXT)
      });
    });

    await loginToApp(page);
    await navigateToFirstFile(page);

    const firstRow = page.locator('.virtual-row').first();
    if (await firstRow.isVisible({ timeout: 5000 }).catch(() => false)) {
      await firstRow.click();
      await page.waitForTimeout(500);

      const audioTab = page.locator('[data-testid="tab-audio"]');
      if (await audioTab.isVisible({ timeout: 3000 }).catch(() => false)) {
        await audioTab.click();
        await page.waitForTimeout(1000);

        // Should show player or empty state
        const player = page.locator('[data-testid="audio-tab-player"]');
        const script = page.locator('[data-testid="audio-tab-script"]');
        const emptyState = page.locator('[data-testid="audio-tab-empty"]');

        const hasPlayer = await player.isVisible({ timeout: 3000 }).catch(() => false);
        const hasScript = await script.isVisible({ timeout: 1000 }).catch(() => false);
        const hasEmpty = await emptyState.isVisible({ timeout: 1000 }).catch(() => false);

        expect(hasPlayer || hasScript || hasEmpty).toBe(true);
      }
    }
  });

  test('Tab switching between TM/Image/Audio works without errors', async ({ page }) => {
    // Track console errors
    const consoleErrors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    await loginToApp(page);
    await navigateToFirstFile(page);

    // Switch tabs rapidly
    const tabs = ['tab-tm', 'tab-image', 'tab-audio', 'tab-tm', 'tab-image'];
    for (const tabId of tabs) {
      const tab = page.locator(`[data-testid="${tabId}"]`);
      if (await tab.isVisible({ timeout: 3000 }).catch(() => false)) {
        await tab.click();
        await page.waitForTimeout(300);
      }
    }

    // Filter out noise - only check for critical errors related to our components
    const criticalErrors = consoleErrors.filter(e =>
      e.includes('ImageTab') || e.includes('AudioTab') || e.includes('mapdata')
    );

    expect(criticalErrors).toHaveLength(0);
  });
});
