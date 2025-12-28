import { test } from '@playwright/test';

test('search 연금 and check all rows including row 0', async ({ page }) => {
  test.setTimeout(120000);

  await page.goto('http://localhost:5173');
  await page.fill('input[placeholder*="username"]', 'admin');
  await page.fill('input[placeholder*="password"]', 'admin123');
  await page.click('button[type="submit"]');
  await page.waitForTimeout(3000);

  await page.goto('http://localhost:5173/ldm');
  await page.waitForTimeout(3000);

  await page.click('.project-item >> nth=0');
  await page.waitForTimeout(2000);
  await page.click('.tree-node >> nth=0');
  await page.waitForTimeout(5000);

  console.log('\n=== SEARCH: "연금" ===');
  const searchInput = page.locator('#ldm-search-input');
  await searchInput.focus();
  await page.keyboard.type('연금');
  await page.waitForTimeout(3000);

  const count = await page.textContent('.row-count');
  console.log(`Results: ${count}`);

  const rows = await page.evaluate(() => {
    const results: any[] = [];
    document.querySelectorAll('.virtual-row').forEach((row, idx) => {
      const src = row.querySelector('.cell.source')?.textContent?.trim()?.substring(0, 60);
      const tgt = row.querySelector('.cell.target')?.textContent?.trim()?.substring(0, 60);
      const isEmpty = !src && !tgt;
      results.push({ idx, src, tgt, isEmpty });
    });
    return results;
  });

  console.log('\nAll visible rows:');
  rows.forEach(r => {
    const status = r.isEmpty ? '❌ EMPTY' : '✓';
    console.log(`Row ${r.idx} ${status}: "${r.src}"`);
    console.log(`           "${r.tgt}"`);
  });

  await page.screenshot({ path: '/tmp/search_yeon.png' });

  // Check for empty rows
  const emptyRows = rows.filter(r => r.isEmpty);
  if (emptyRows.length > 0) {
    console.log(`\n✗ FOUND ${emptyRows.length} EMPTY ROWS: ${emptyRows.map(r => r.idx).join(', ')}`);
  } else if (rows.length > 0) {
    console.log(`\n✓ ALL ${rows.length} ROWS HAVE CONTENT (including row 0)`);
  } else {
    console.log('\n? NO ROWS FOUND');
  }
});
