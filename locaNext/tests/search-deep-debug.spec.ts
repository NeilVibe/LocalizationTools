import { test, expect } from '@playwright/test';

test.describe('Search Deep Debug', () => {
  test('investigate search behavior step by step', async ({ page }) => {
    test.setTimeout(120000);

    // Capture ALL console logs
    const allLogs: string[] = [];
    page.on('console', msg => {
      const text = msg.text();
      allLogs.push(`[${msg.type()}] ${text}`);
    });

    // Login
    console.log('\n=== STEP 1: LOGIN ===');
    await page.goto('http://localhost:5173');
    await page.fill('input[placeholder*="username"]', 'admin');
    await page.fill('input[placeholder*="password"]', 'admin123');
    await page.click('button[type="submit"]');
    await page.waitForTimeout(3000);

    // Navigate to LDM
    console.log('\n=== STEP 2: NAVIGATE TO LDM ===');
    await page.goto('http://localhost:5173/ldm');
    await page.waitForTimeout(3000);
    await page.screenshot({ path: '/tmp/debug_01_ldm.png' });

    // Select project
    console.log('\n=== STEP 3: SELECT PROJECT ===');
    const projects = await page.$$('.project-item');
    console.log(`Found ${projects.length} projects`);
    if (projects.length === 0) {
      console.log('ERROR: No projects found!');
      return;
    }
    await page.click('.project-item >> nth=0');
    await page.waitForTimeout(2000);

    // Select file
    console.log('\n=== STEP 4: SELECT FILE ===');
    const files = await page.$$('.tree-node');
    console.log(`Found ${files.length} files`);
    if (files.length === 0) {
      console.log('ERROR: No files found!');
      return;
    }
    await page.click('.tree-node >> nth=0');
    await page.waitForTimeout(5000);
    await page.screenshot({ path: '/tmp/debug_02_file_loaded.png' });

    // Get initial state
    console.log('\n=== STEP 5: INITIAL STATE ===');
    const initialCount = await page.textContent('.row-count');
    console.log(`Initial row count text: "${initialCount}"`);

    // Find search input
    console.log('\n=== STEP 6: FIND SEARCH INPUT ===');
    const searchInputs = await page.$$('#ldm-search-input');
    console.log(`Search inputs with ID: ${searchInputs.length}`);

    const allInputs = await page.$$('input');
    console.log(`All inputs on page: ${allInputs.length}`);

    // Get search input details
    const searchInput = page.locator('#ldm-search-input');
    const exists = await searchInput.count();
    console.log(`Search input exists: ${exists > 0}`);

    if (exists === 0) {
      // Try alternative selectors
      const altSearch = page.locator('input[placeholder*="Search"]');
      const altExists = await altSearch.count();
      console.log(`Alternative search input: ${altExists > 0}`);
    }

    // Focus and check
    console.log('\n=== STEP 7: FOCUS SEARCH ===');
    await searchInput.focus();
    await page.waitForTimeout(500);

    const isFocused = await page.evaluate(() => {
      const el = document.getElementById('ldm-search-input');
      return el === document.activeElement;
    });
    console.log(`Search input focused: ${isFocused}`);

    // Type ONE character and check
    console.log('\n=== STEP 8: TYPE ONE CHARACTER ===');
    await page.keyboard.type('V');
    await page.waitForTimeout(1000);

    const valueAfterV = await searchInput.inputValue();
    console.log(`Value after typing 'V': "${valueAfterV}"`);

    // Check state via evaluate
    const stateAfterV = await page.evaluate(() => {
      const input = document.getElementById('ldm-search-input') as HTMLInputElement;
      return {
        value: input?.value,
        id: input?.id,
        placeholder: input?.placeholder
      };
    });
    console.log(`DOM state after V:`, JSON.stringify(stateAfterV));

    await page.screenshot({ path: '/tmp/debug_03_after_v.png' });

    // Type more characters
    console.log('\n=== STEP 9: TYPE REST OF WORD ===');
    await page.keyboard.type('alencia');
    await page.waitForTimeout(1000);

    const valueAfterFull = await searchInput.inputValue();
    console.log(`Value after full word: "${valueAfterFull}"`);

    await page.screenshot({ path: '/tmp/debug_04_after_valencia.png' });

    // Wait for debounce and API
    console.log('\n=== STEP 10: WAIT FOR SEARCH ===');
    await page.waitForTimeout(3000);

    const countAfterSearch = await page.textContent('.row-count');
    console.log(`Row count after search: "${countAfterSearch}"`);

    await page.screenshot({ path: '/tmp/debug_05_after_wait.png' });

    // Check network requests
    console.log('\n=== STEP 11: CHECK LOGS ===');
    const searchLogs = allLogs.filter(l =>
      l.includes('search') || l.includes('Search') ||
      l.includes('handleSearch') || l.includes('loadRows') ||
      l.includes('oninput') || l.includes('effect')
    );
    console.log(`Search-related logs (${searchLogs.length}):`);
    searchLogs.slice(-30).forEach(l => console.log(`  ${l}`));

    // Summary
    console.log('\n=== SUMMARY ===');
    console.log(`Initial count: ${initialCount}`);
    console.log(`After search: ${countAfterSearch}`);
    console.log(`Input value: "${valueAfterFull}"`);
    console.log(`Search triggered: ${searchLogs.length > 0}`);

    const initialNum = parseInt((initialCount || '0').replace(/[^0-9]/g, ''));
    const afterNum = parseInt((countAfterSearch || '0').replace(/[^0-9]/g, ''));

    if (afterNum < initialNum) {
      console.log('\n✓ SEARCH IS WORKING!');
    } else if (afterNum === initialNum) {
      console.log('\n✗ SEARCH NOT WORKING - count unchanged');
    } else {
      console.log('\n? UNKNOWN STATE');
    }
  });
});
