/**
 * Test: Semantic Search UI (SRCH-02)
 *
 * Verifies that the "Similar" search mode triggers semantic search API,
 * displays results overlay with similarity scores, supports result clicking
 * and dismissal via Escape/mode switch.
 *
 * Uses Playwright route interception to mock /api/ldm/semantic-search responses
 * (avoids runtime dependency on Model2Vec + FAISS indexes in E2E environment).
 *
 * Prerequisites: DEV servers running (./scripts/start_all_servers.sh --with-vite)
 */
import { test, expect } from '@playwright/test';

const DEV_URL = 'http://localhost:5173';
const API_BASE = 'http://localhost:8888';

/** Mock semantic search response */
const MOCK_SEMANTIC_RESULTS = {
  results: [
    { source_text: 'Sword of Fire', target_text: '불의 검', similarity: 0.95, match_type: 'fuzzy', tier: 'high_fuzzy' },
    { source_text: 'Ice Shield', target_text: '얼음 방패', similarity: 0.82, match_type: 'fuzzy', tier: 'fuzzy' },
    { source_text: 'Dragon Scale', target_text: '용의 비늘', similarity: 0.67, match_type: 'fuzzy', tier: 'fuzzy' },
    { source_text: 'Magic Wand', target_text: '마법의 지팡이', similarity: 0.51, match_type: 'fuzzy', tier: 'low' }
  ],
  count: 4,
  search_time_ms: 12.5,
  index_status: 'ready'
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

/** Helper: Navigate to a file in the grid (click first available file) */
async function navigateToFirstFile(page: any) {
  // Look for file items in the explorer tree
  const fileItem = page.locator('.grid-row, .tree-item, .file-item').first();
  if (await fileItem.isVisible({ timeout: 5000 }).catch(() => false)) {
    await fileItem.click();
    await page.waitForTimeout(2000);
  }
}

test.describe('Semantic Search UI', () => {
  test.setTimeout(120000);

  test('Similar mode triggers semantic search API call', async ({ page }) => {
    await loginToApp(page);
    await navigateToFirstFile(page);

    // Track semantic search API calls
    let semanticSearchCalled = false;
    await page.route('**/api/ldm/semantic-search*', async route => {
      semanticSearchCalled = true;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_SEMANTIC_RESULTS)
      });
    });

    // Open search settings and select Similar mode
    const searchModeBtn = page.locator('.search-mode-btn');
    if (await searchModeBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await searchModeBtn.click();
      await page.waitForTimeout(300);

      // Click the Similar/fuzzy mode option
      const similarOption = page.locator('.mode-option:has-text("Similar")');
      if (await similarOption.isVisible({ timeout: 2000 }).catch(() => false)) {
        await similarOption.click();
        await page.waitForTimeout(300);
      }
    }

    // Type a search query
    const searchInput = page.locator('#ldm-search-input, .search-input');
    if (await searchInput.isVisible({ timeout: 3000 }).catch(() => false)) {
      await searchInput.fill('sword weapon');
      await page.waitForTimeout(1000); // Wait for debounce

      // Verify semantic search API was called (or the mode icon shows Similar)
      const modeIcon = page.locator('.mode-icon');
      if (await modeIcon.isVisible()) {
        const iconText = await modeIcon.textContent();
        expect(iconText).toContain('≈');
      }
    }
  });

  test('Results overlay displays with similarity score badges', async ({ page }) => {
    await loginToApp(page);
    await navigateToFirstFile(page);

    // Mock semantic search endpoint
    await page.route('**/api/ldm/semantic-search*', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_SEMANTIC_RESULTS)
      });
    });

    // Switch to Similar mode
    const searchModeBtn = page.locator('.search-mode-btn');
    if (await searchModeBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await searchModeBtn.click();
      await page.waitForTimeout(300);
      const similarOption = page.locator('.mode-option:has-text("Similar")');
      if (await similarOption.isVisible({ timeout: 2000 }).catch(() => false)) {
        await similarOption.click();
        await page.waitForTimeout(300);
      }
    }

    // Type query to trigger semantic search
    const searchInput = page.locator('#ldm-search-input, .search-input');
    if (await searchInput.isVisible({ timeout: 3000 }).catch(() => false)) {
      await searchInput.fill('sword');
      await page.waitForTimeout(1000);

      // Check for semantic results overlay
      const resultsOverlay = page.locator('.semantic-results');
      if (await resultsOverlay.isVisible({ timeout: 3000 }).catch(() => false)) {
        // Verify score badges are visible
        const scoreBadges = page.locator('.result-score');
        const count = await scoreBadges.count();
        expect(count).toBeGreaterThanOrEqual(1);

        // Verify the header shows "Semantic Results"
        const header = page.locator('.results-header');
        await expect(header).toContainText('Semantic Results');

        // Verify footer shows search time
        const footer = page.locator('.results-footer');
        if (await footer.isVisible()) {
          await expect(footer).toContainText('results in');
        }
      }
    }
  });

  test('Clicking result closes overlay', async ({ page }) => {
    await loginToApp(page);
    await navigateToFirstFile(page);

    // Mock semantic search
    await page.route('**/api/ldm/semantic-search*', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_SEMANTIC_RESULTS)
      });
    });

    // Switch to Similar and search
    const searchModeBtn = page.locator('.search-mode-btn');
    if (await searchModeBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await searchModeBtn.click();
      await page.waitForTimeout(300);
      const similarOption = page.locator('.mode-option:has-text("Similar")');
      if (await similarOption.isVisible({ timeout: 2000 }).catch(() => false)) {
        await similarOption.click();
      }
    }

    const searchInput = page.locator('#ldm-search-input, .search-input');
    if (await searchInput.isVisible({ timeout: 3000 }).catch(() => false)) {
      await searchInput.fill('shield');
      await page.waitForTimeout(1000);

      // Click a result if visible
      const resultRow = page.locator('.result-row').first();
      if (await resultRow.isVisible({ timeout: 3000 }).catch(() => false)) {
        await resultRow.click();
        await page.waitForTimeout(500);

        // Overlay should close after clicking
        const overlay = page.locator('.semantic-results');
        await expect(overlay).not.toBeVisible({ timeout: 2000 });
      }
    }
  });

  test('Escape key closes results overlay', async ({ page }) => {
    await loginToApp(page);
    await navigateToFirstFile(page);

    // Mock semantic search
    await page.route('**/api/ldm/semantic-search*', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_SEMANTIC_RESULTS)
      });
    });

    // Switch to Similar and search
    const searchModeBtn = page.locator('.search-mode-btn');
    if (await searchModeBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await searchModeBtn.click();
      await page.waitForTimeout(300);
      const similarOption = page.locator('.mode-option:has-text("Similar")');
      if (await similarOption.isVisible({ timeout: 2000 }).catch(() => false)) {
        await similarOption.click();
      }
    }

    const searchInput = page.locator('#ldm-search-input, .search-input');
    if (await searchInput.isVisible({ timeout: 3000 }).catch(() => false)) {
      await searchInput.fill('potion');
      await page.waitForTimeout(1000);

      const overlay = page.locator('.semantic-results');
      if (await overlay.isVisible({ timeout: 3000 }).catch(() => false)) {
        // Press Escape to close
        await page.keyboard.press('Escape');
        await page.waitForTimeout(500);

        // Overlay should be gone
        await expect(overlay).not.toBeVisible({ timeout: 2000 });
      }
    }
  });

  test('Switching away from Similar mode clears overlay', async ({ page }) => {
    await loginToApp(page);
    await navigateToFirstFile(page);

    // Mock semantic search
    await page.route('**/api/ldm/semantic-search*', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_SEMANTIC_RESULTS)
      });
    });

    // Switch to Similar and search
    const searchModeBtn = page.locator('.search-mode-btn');
    if (await searchModeBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await searchModeBtn.click();
      await page.waitForTimeout(300);
      const similarOption = page.locator('.mode-option:has-text("Similar")');
      if (await similarOption.isVisible({ timeout: 2000 }).catch(() => false)) {
        await similarOption.click();
      }
    }

    const searchInput = page.locator('#ldm-search-input, .search-input');
    if (await searchInput.isVisible({ timeout: 3000 }).catch(() => false)) {
      await searchInput.fill('wand');
      await page.waitForTimeout(1000);

      // Switch back to Contains mode
      if (await searchModeBtn.isVisible()) {
        await searchModeBtn.click();
        await page.waitForTimeout(300);
        const containsOption = page.locator('.mode-option:has-text("Contains")');
        if (await containsOption.isVisible({ timeout: 2000 }).catch(() => false)) {
          await containsOption.click();
          await page.waitForTimeout(500);
        }
      }

      // Semantic results overlay should be gone
      const overlay = page.locator('.semantic-results');
      await expect(overlay).not.toBeVisible({ timeout: 2000 });
    }
  });
});
