import { test, expect } from '@playwright/test';

test.describe('Search Results Row 0 Check', () => {
  test('verify row 0 displays in search results', async ({ page }) => {
    test.setTimeout(120000);

    // Login
    await page.goto('http://localhost:5173');
    await page.fill('input[placeholder*="username"]', 'admin');
    await page.fill('input[placeholder*="password"]', 'admin123');
    await page.click('button[type="submit"]');
    await page.waitForTimeout(3000);

    // Navigate to LDM
    await page.goto('http://localhost:5173/ldm');
    await page.waitForTimeout(3000);

    // Select project and file
    await page.click('.project-item >> nth=0');
    await page.waitForTimeout(2000);
    await page.click('.tree-node >> nth=0');
    await page.waitForTimeout(5000);

    // Search for something with multiple results
    console.log('\n=== SEARCH TEST: "어선" (fishing boat) ===');
    const searchInput = page.locator('#ldm-search-input');
    await searchInput.focus();
    await page.keyboard.type('어선');
    await page.waitForTimeout(3000);

    const count1 = await page.textContent('.row-count');
    console.log(`Search "어선" results: ${count1}`);

    // Get all visible rows in search results
    const searchRows1 = await page.evaluate(() => {
      const rows = document.querySelectorAll('.virtual-row');
      return Array.from(rows).map((row, idx) => {
        const source = row.querySelector('.cell.source')?.textContent?.trim()?.substring(0, 50);
        const target = row.querySelector('.cell.target')?.textContent?.trim()?.substring(0, 50);
        return { index: idx, source, target };
      });
    });

    console.log('\nSearch results for "어선":');
    searchRows1.forEach(r => {
      console.log(`  Row ${r.index}: source="${r.source}"`);
      console.log(`           target="${r.target}"`);
    });

    await page.screenshot({ path: '/tmp/search_row0_test1.png' });

    // Clear and try another search
    console.log('\n=== SEARCH TEST: "de" (French "of") ===');
    await searchInput.fill('');
    await page.waitForTimeout(500);
    await page.keyboard.type('de');
    await page.waitForTimeout(3000);

    const count2 = await page.textContent('.row-count');
    console.log(`Search "de" results: ${count2}`);

    const searchRows2 = await page.evaluate(() => {
      const rows = document.querySelectorAll('.virtual-row');
      return Array.from(rows).slice(0, 5).map((row, idx) => {
        const source = row.querySelector('.cell.source')?.textContent?.trim()?.substring(0, 40);
        const target = row.querySelector('.cell.target')?.textContent?.trim()?.substring(0, 40);
        return { index: idx, source, target };
      });
    });

    console.log('\nFirst 5 search results for "de":');
    searchRows2.forEach(r => {
      console.log(`  Row ${r.index}: source="${r.source}"`);
      console.log(`           target="${r.target}"`);
    });

    // Check if row 0 exists and has content
    const row0Content = await page.evaluate(() => {
      const firstRow = document.querySelector('.virtual-row');
      if (!firstRow) return { exists: false };
      const source = firstRow.querySelector('.cell.source')?.textContent?.trim();
      const target = firstRow.querySelector('.cell.target')?.textContent?.trim();
      const isEmpty = !source && !target;
      return { exists: true, isEmpty, source: source?.substring(0, 50), target: target?.substring(0, 50) };
    });

    console.log('\n=== ROW 0 CHECK ===');
    console.log(`Row 0 exists: ${row0Content.exists}`);
    console.log(`Row 0 is empty: ${row0Content.isEmpty}`);
    console.log(`Row 0 source: "${row0Content.source}"`);
    console.log(`Row 0 target: "${row0Content.target}"`);

    await page.screenshot({ path: '/tmp/search_row0_test2.png' });

    // Verify row 0 has content
    if (row0Content.exists && !row0Content.isEmpty) {
      console.log('\n✓ ROW 0 DISPLAYS CORRECTLY IN SEARCH RESULTS');
    } else {
      console.log('\n✗ ROW 0 IS MISSING OR EMPTY');
    }
  });
});
