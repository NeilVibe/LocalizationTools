import { test, expect } from '@playwright/test';

test.describe('Search Verification Test', () => {
  test('search filters rows - VERIFIED', async ({ page }) => {
    test.setTimeout(90000);

    // Login
    await page.goto('http://localhost:5173');
    await page.fill('input[placeholder*="username"]', 'admin');
    await page.fill('input[placeholder*="password"]', 'admin123');
    await page.click('button[type="submit"]');
    await page.waitForTimeout(2000);

    // Navigate to LDM
    await page.goto('http://localhost:5173/ldm');
    await page.waitForTimeout(2000);

    // Select project and file
    await page.click('.project-item >> nth=0');
    await page.waitForTimeout(1000);
    await page.click('.tree-node >> nth=0');
    await page.waitForTimeout(5000);

    // Get initial count
    const initialCountText = await page.textContent('.row-count') || '';
    const initialMatch = initialCountText.match(/([\d,]+)/);
    const initialCount = initialMatch ? parseInt(initialMatch[1].replace(',', '')) : 0;
    console.log(`Initial row count: ${initialCount}`);
    await page.screenshot({ path: '/tmp/search_verified_01_initial.png' });

    // Type search term
    const searchInput = page.locator('#ldm-search-input');
    await searchInput.focus();
    await page.keyboard.type('Valencia', { delay: 50 }); // Search in real Korean/French data
    await page.waitForTimeout(2000); // Wait for debounce + API

    // Get filtered count
    const filteredCountText = await page.textContent('.row-count') || '';
    const filteredMatch = filteredCountText.match(/([\d,]+)/);
    const filteredCount = filteredMatch ? parseInt(filteredMatch[1].replace(',', '')) : 0;
    console.log(`Filtered row count: ${filteredCount}`);
    await page.screenshot({ path: '/tmp/search_verified_02_filtered.png' });

    // Verify
    console.log('\n=== VERIFICATION ===');
    console.log(`Initial count: ${initialCount}`);
    console.log(`Filtered count: ${filteredCount}`);
    console.log(`Filtering worked: ${filteredCount < initialCount}`);
    console.log(`Rows filtered out: ${initialCount - filteredCount}`);

    // Assert search is working
    expect(filteredCount).toBeLessThan(initialCount);
    console.log('\n*** SEARCH TEST PASSED ***');
  });
});
