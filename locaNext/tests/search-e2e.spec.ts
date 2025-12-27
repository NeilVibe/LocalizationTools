import { test, expect } from '@playwright/test';

test.describe('Search End-to-End Test', () => {
  test('search filters rows correctly', async ({ page }) => {
    test.setTimeout(90000);

    // Console log capture
    const consoleLogs: string[] = [];
    page.on('console', msg => {
      const text = msg.text();
      consoleLogs.push(text);
      if (text.includes('searchTerm') || text.includes('handleSearch') || text.includes('loadRows')) {
        console.log(`[BROWSER] ${text}`);
      }
    });

    // Step 1: Login
    console.log('\n=== STEP 1: Login ===');
    await page.goto('http://localhost:5173');
    await page.waitForSelector('input[placeholder*="username"]', { timeout: 10000 });
    await page.fill('input[placeholder*="username"]', 'admin');
    await page.fill('input[placeholder*="password"]', 'admin123');
    await page.click('button[type="submit"]');
    await page.waitForTimeout(2000);
    await page.screenshot({ path: '/tmp/e2e_01_logged_in.png' });
    console.log('Login complete');

    // Step 2: Navigate to LDM
    console.log('\n=== STEP 2: Navigate to LDM ===');
    await page.goto('http://localhost:5173/ldm');
    await page.waitForTimeout(2000);
    await page.screenshot({ path: '/tmp/e2e_02_ldm_page.png' });

    // Step 3: Select first project
    console.log('\n=== STEP 3: Select project ===');
    const projectItems = await page.$$('.project-item');
    console.log(`Found ${projectItems.length} projects`);

    if (projectItems.length === 0) {
      console.log('No projects found!');
      await page.screenshot({ path: '/tmp/e2e_03_no_projects.png' });
      return;
    }

    await page.click('.project-item >> nth=0');
    await page.waitForTimeout(1000);
    await page.screenshot({ path: '/tmp/e2e_03_project_selected.png' });

    // Step 4: Select first file
    console.log('\n=== STEP 4: Select file ===');
    const treeNodes = await page.$$('.tree-node');
    console.log(`Found ${treeNodes.length} tree nodes`);

    if (treeNodes.length === 0) {
      console.log('No tree nodes found!');
      await page.screenshot({ path: '/tmp/e2e_04_no_files.png' });
      return;
    }

    await page.click('.tree-node >> nth=0');
    await page.waitForTimeout(5000); // Wait for file to load
    await page.screenshot({ path: '/tmp/e2e_04_file_selected.png' });

    // Step 5: Count initial rows
    console.log('\n=== STEP 5: Count initial rows ===');

    // Look for grid rows in different ways
    const gridRows = await page.$$('.virtual-row');
    const tableRows = await page.$$('tr[data-row-id]');
    const anyRows = await page.$$('[class*="row"]');

    console.log(`Grid rows (.virtual-row): ${gridRows.length}`);
    console.log(`Table rows (tr[data-row-id]): ${tableRows.length}`);
    console.log(`Any rows ([class*="row"]): ${anyRows.length}`);

    // Get total from displayed count if available
    const totalText = await page.textContent('.row-count, .total-rows, [class*="count"]') || 'N/A';
    console.log(`Total text: ${totalText}`);

    await page.screenshot({ path: '/tmp/e2e_05_initial_rows.png' });

    // Step 6: Find and focus search input
    console.log('\n=== STEP 6: Find search input ===');
    const searchInput = page.locator('#ldm-search-input, input[placeholder*="Search"]');
    const searchExists = await searchInput.count();
    console.log(`Search inputs found: ${searchExists}`);

    if (searchExists === 0) {
      console.log('No search input found!');
      // Check what inputs exist
      const allInputs = await page.$$eval('input', inputs =>
        inputs.map(i => ({ placeholder: i.placeholder, id: i.id, type: i.type }))
      );
      console.log('All inputs:', JSON.stringify(allInputs, null, 2));
      await page.screenshot({ path: '/tmp/e2e_06_no_search.png' });
      return;
    }

    // Step 7: Type search term using keyboard
    console.log('\n=== STEP 7: Type search term ===');
    await searchInput.first().focus();
    await page.waitForTimeout(200);

    // Type character by character to ensure events fire
    const searchTerm = 'Item';
    for (const char of searchTerm) {
      await page.keyboard.type(char, { delay: 50 });
    }

    await page.waitForTimeout(500); // Wait for debounce (300ms) + buffer

    const inputValue = await searchInput.first().inputValue();
    console.log(`Input value after typing: "${inputValue}"`);
    await page.screenshot({ path: '/tmp/e2e_07_search_typed.png' });

    // Step 8: Wait for search to filter
    console.log('\n=== STEP 8: Wait for filter ===');
    await page.waitForTimeout(2000); // Wait for API response
    await page.screenshot({ path: '/tmp/e2e_08_after_search.png' });

    // Step 9: Count filtered rows
    console.log('\n=== STEP 9: Count filtered rows ===');
    const filteredGridRows = await page.$$('.virtual-row');
    const filteredTableRows = await page.$$('tr[data-row-id]');

    console.log(`Filtered grid rows: ${filteredGridRows.length}`);
    console.log(`Filtered table rows: ${filteredTableRows.length}`);

    const filteredTotalText = await page.textContent('.row-count, .total-rows, [class*="count"]') || 'N/A';
    console.log(`Filtered total text: ${filteredTotalText}`);

    // Step 10: Summary
    console.log('\n=== SUMMARY ===');
    console.log(`Initial rows: ${gridRows.length || tableRows.length}`);
    console.log(`Filtered rows: ${filteredGridRows.length || filteredTableRows.length}`);
    console.log(`Search term typed: "${inputValue}"`);
    console.log(`Search working: ${(filteredGridRows.length || filteredTableRows.length) !== (gridRows.length || tableRows.length) ? 'YES' : 'UNKNOWN'}`);

    // Print relevant console logs
    console.log('\n=== SEARCH-RELATED LOGS ===');
    consoleLogs
      .filter(l => l.includes('search') || l.includes('Search') || l.includes('handleSearch'))
      .slice(-20)
      .forEach(l => console.log(l));
  });
});
