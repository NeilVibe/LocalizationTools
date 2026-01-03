import { test, expect } from '@playwright/test';

test.describe('Search for "proue" debug', () => {
  test.skip('investigate proue search behavior', async ({ page }) => {
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

    // Select project
    console.log('\n=== STEP 3: SELECT PROJECT ===');
    await page.click('.project-item >> nth=0');
    await page.waitForTimeout(2000);

    // Select file
    console.log('\n=== STEP 4: SELECT FILE ===');
    await page.click('.tree-node >> nth=0');
    await page.waitForTimeout(5000);
    await page.screenshot({ path: '/tmp/proue_01_file_loaded.png' });

    // Get initial state
    const initialCount = await page.textContent('.row-count');
    console.log(`\n=== INITIAL STATE ===`);
    console.log(`Initial row count: "${initialCount}"`);

    // Get some sample rows to see what data looks like
    const sampleRows = await page.evaluate(() => {
      const cells = document.querySelectorAll('.cell.target');
      return Array.from(cells).slice(0, 5).map(c => c.textContent?.substring(0, 50));
    });
    console.log('Sample target cells:', sampleRows);

    // Check if "proue" exists in the data
    const proueExists = await page.evaluate(() => {
      const allText = document.body.innerText;
      return allText.toLowerCase().includes('proue');
    });
    console.log(`Does "proue" exist in visible data? ${proueExists}`);

    // Focus search input
    console.log('\n=== STEP 5: SEARCH FOR "proue" ===');
    const searchInput = page.locator('#ldm-search-input');
    await searchInput.focus();
    await page.waitForTimeout(500);

    // Type character by character to see behavior
    const searchTerm = 'proue';
    for (let i = 0; i < searchTerm.length; i++) {
      const char = searchTerm[i];
      await page.keyboard.type(char);
      await page.waitForTimeout(200);

      const currentValue = await searchInput.inputValue();
      const currentCount = await page.textContent('.row-count');
      console.log(`After typing '${char}': value="${currentValue}", count="${currentCount}"`);
    }

    await page.screenshot({ path: '/tmp/proue_02_after_typing.png' });

    // Wait for debounce and API
    console.log('\n=== STEP 6: WAIT FOR SEARCH RESULTS ===');
    await page.waitForTimeout(3000);

    const afterCount = await page.textContent('.row-count');
    const finalValue = await searchInput.inputValue();
    console.log(`Final input value: "${finalValue}"`);
    console.log(`Final row count: "${afterCount}"`);

    await page.screenshot({ path: '/tmp/proue_03_after_wait.png' });

    // Check what rows are visible now
    const visibleRows = await page.evaluate(() => {
      const rows: string[] = [];
      const cells = document.querySelectorAll('.cell.target');
      cells.forEach((cell, i) => {
        if (i < 10) {
          rows.push(cell.textContent?.substring(0, 100) || '');
        }
      });
      return rows;
    });
    console.log('\n=== VISIBLE ROWS AFTER SEARCH ===');
    visibleRows.forEach((row, i) => console.log(`Row ${i}: ${row}`));

    // Check for any rows containing "proue"
    const matchingRows = await page.evaluate(() => {
      const matches: string[] = [];
      const cells = document.querySelectorAll('.cell');
      cells.forEach(cell => {
        const text = cell.textContent || '';
        if (text.toLowerCase().includes('proue')) {
          matches.push(text.substring(0, 100));
        }
      });
      return matches;
    });
    console.log(`\n=== ROWS CONTAINING "proue" ===`);
    console.log(`Found ${matchingRows.length} matches`);
    matchingRows.forEach((m, i) => console.log(`Match ${i}: ${m}`));

    // Check search-related logs
    console.log('\n=== SEARCH LOGS ===');
    const searchLogs = allLogs.filter(l =>
      l.toLowerCase().includes('search') ||
      l.includes('handleSearch') ||
      l.includes('loadRows') ||
      l.includes('oninput')
    );
    searchLogs.slice(-20).forEach(l => console.log(`  ${l}`));

    // Summary
    console.log('\n=== SUMMARY ===');
    console.log(`Initial count: ${initialCount}`);
    console.log(`After "proue" search: ${afterCount}`);
    console.log(`Input value: "${finalValue}"`);
    console.log(`Matching rows found: ${matchingRows.length}`);

    const initialNum = parseInt((initialCount || '0').replace(/[^0-9]/g, ''));
    const afterNum = parseInt((afterCount || '0').replace(/[^0-9]/g, ''));

    if (afterNum < initialNum && afterNum > 0) {
      console.log('\n✓ SEARCH FILTERED ROWS');
    } else if (afterNum === 0) {
      console.log('\n? SEARCH RETURNED 0 ROWS - may be no matches or bug');
    } else if (afterNum === initialNum) {
      console.log('\n✗ SEARCH DID NOT FILTER - count unchanged');
    }
  });
});
