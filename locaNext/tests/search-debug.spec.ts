import { test, expect } from '@playwright/test';

test.describe('Search Debug Tests', () => {
  test('test search via debug hook', async ({ page }) => {
    test.setTimeout(60000);

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
    await page.screenshot({ path: '/tmp/debug_01_file_loaded.png' });

    // Check initial state via debug hook
    const initialTotal = await page.evaluate(() => {
      return (window as any).__ldmDebug?.getTotal() || 0;
    });
    console.log(`Initial total rows: ${initialTotal}`);

    // Use debug hook to set search term
    console.log('Setting search term via debug hook...');
    await page.evaluate(() => {
      (window as any).__ldmDebug?.setSearch('Item');
    });

    // Check if searchTerm was set
    const searchTermAfter = await page.evaluate(() => {
      return (window as any).__ldmDebug?.getSearch() || '';
    });
    console.log(`Search term after set: "${searchTermAfter}"`);

    // Wait for effect to trigger and API to respond
    await page.waitForTimeout(2000);
    await page.screenshot({ path: '/tmp/debug_02_after_search.png' });

    // Check total after search
    const totalAfterSearch = await page.evaluate(() => {
      return (window as any).__ldmDebug?.getTotal() || 0;
    });
    console.log(`Total rows after search: ${totalAfterSearch}`);

    // Check the input value
    const inputValue = await page.inputValue('input[placeholder*="Search"]');
    console.log(`Input value: "${inputValue}"`);

    // Summary
    console.log('\n=== SEARCH TEST RESULTS ===');
    console.log(`Initial rows: ${initialTotal}`);
    console.log(`After "Item" search: ${totalAfterSearch}`);
    console.log(`Search term set correctly: ${searchTermAfter === 'Item'}`);
    console.log(`Rows filtered: ${totalAfterSearch < initialTotal}`);

    if (totalAfterSearch < initialTotal) {
      console.log('✓ SEARCH IS WORKING!');
    } else if (totalAfterSearch === initialTotal) {
      console.log('✗ SEARCH NOT FILTERING - rows unchanged');
    }
  });
});
