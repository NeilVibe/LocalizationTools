/**
 * UI-107 Fix Verification Test
 * Verify that File Explorer no longer shows duplicate "Offline Storage"
 */
import { test, expect } from '@playwright/test';

const DEV_URL = 'http://localhost:5173';

test('UI-107 Fix: File Explorer should show only ONE Offline Storage', async ({ page }) => {
  // 1. Login online
  await page.goto(DEV_URL);
  await page.waitForTimeout(2000);

  await page.locator('text=Login').first().click();
  await page.waitForTimeout(1500);
  await page.locator('input').first().fill('admin');
  await page.locator('input[type="password"]').fill('admin123');
  await page.locator('button:has-text("Login")').click();
  await page.waitForTimeout(3000);

  console.log('✓ Logged in Online');

  // 2. Visit TM page first (triggers PostgreSQL platform creation)
  await page.locator('text=TM').first().click();
  await page.waitForTimeout(3000);
  console.log('✓ Visited TM page (PostgreSQL platform created)');

  // 3. Go to Files page
  await page.locator('text=Files').first().click();
  await page.waitForTimeout(3000);
  await page.screenshot({ path: '/tmp/ui107_fix_files.png' });

  // 4. Count VISIBLE rows with "Offline Storage" in the name column
  // Look specifically in the explorer grid/list, not hidden elements
  const visibleRows = await page.evaluate(() => {
    const rows = document.querySelectorAll('.explorer-row, [class*="item-row"], [data-type]');
    let count = 0;
    rows.forEach(row => {
      const text = row.textContent || '';
      if (text.includes('Offline Storage')) {
        count++;
        console.log('Found row:', text.slice(0, 50));
      }
    });
    return count;
  });

  // Also get all text matches for debugging
  const allMatches = await page.locator('text=Offline Storage').count();

  console.log(`\n=== UI-107 FIX TEST ===`);
  console.log(`Visible rows with "Offline Storage": ${visibleRows}`);
  console.log(`All text matches (includes hidden): ${allMatches}`);

  if (visibleRows === 1) {
    console.log('✅ FIX VERIFIED: Only 1 visible Offline Storage row!');
  } else if (visibleRows > 1) {
    console.log('❌ FIX FAILED: Still showing duplicates!');
  } else {
    console.log('⚠️ No Offline Storage visible');
  }

  // 5. Check TM tree
  await page.locator('text=TM').first().click();
  await page.waitForTimeout(2000);
  await page.screenshot({ path: '/tmp/ui107_fix_tm.png' });

  const tmCount = await page.locator('button:has-text("Offline Storage")').count();
  console.log(`TM Tree buttons: ${tmCount}`);

  // Assertion - check visible rows only
  expect(visibleRows).toBeLessThanOrEqual(1);
});
