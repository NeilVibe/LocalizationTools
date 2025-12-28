import { test, expect } from '@playwright/test';

test.describe('Row 0 Display Check', () => {
  test('verify row 0 is displayed correctly', async ({ page }) => {
    test.setTimeout(120000);

    // Login
    console.log('\n=== LOGIN ===');
    await page.goto('http://localhost:5173');
    await page.fill('input[placeholder*="username"]', 'admin');
    await page.fill('input[placeholder*="password"]', 'admin123');
    await page.click('button[type="submit"]');
    await page.waitForTimeout(3000);

    // Navigate to LDM
    console.log('\n=== NAVIGATE TO LDM ===');
    await page.goto('http://localhost:5173/ldm');
    await page.waitForTimeout(3000);

    // Select project and file
    await page.click('.project-item >> nth=0');
    await page.waitForTimeout(2000);
    await page.click('.tree-node >> nth=0');
    await page.waitForTimeout(5000);

    // Check row count
    const rowCount = await page.textContent('.row-count');
    console.log(`\nTotal rows: ${rowCount}`);

    // Get first few rows displayed
    console.log('\n=== CHECKING ROW INDICES ===');

    // Check if there's a row number column
    const rowNumbers = await page.evaluate(() => {
      const cells = document.querySelectorAll('.cell.row-num, .row-number, [class*="row-num"]');
      return Array.from(cells).slice(0, 5).map(c => c.textContent?.trim());
    });
    console.log('Row number cells found:', rowNumbers);

    // Check the actual row indices in data
    const rowData = await page.evaluate(() => {
      const rows = document.querySelectorAll('.virtual-row, [class*="row"]');
      const data: any[] = [];
      rows.forEach((row, i) => {
        if (i < 5 && row.classList.contains('virtual-row')) {
          const cells = row.querySelectorAll('.cell');
          const rowNum = row.querySelector('.cell.row-num')?.textContent?.trim();
          const source = row.querySelector('.cell.source')?.textContent?.trim()?.substring(0, 30);
          data.push({ index: i, rowNum, source });
        }
      });
      return data;
    });
    console.log('\nRow data (first 5):');
    rowData.forEach(r => console.log(`  Index ${r.index}: row_num=${r.rowNum}, source="${r.source}"`));

    // Get ALL visible cell content to see what's displayed
    const allCells = await page.evaluate(() => {
      const result: any[] = [];
      const virtualRows = document.querySelectorAll('.virtual-row');
      virtualRows.forEach((row, rowIdx) => {
        if (rowIdx < 5) {
          const cells = row.querySelectorAll('.cell');
          const rowData: any = { rowIndex: rowIdx, cells: [] };
          cells.forEach((cell, cellIdx) => {
            const content = cell.textContent?.trim()?.substring(0, 40);
            const classes = cell.className;
            rowData.cells.push({ cellIdx, content, classes });
          });
          result.push(rowData);
        }
      });
      return result;
    });

    console.log('\n=== ALL VISIBLE CELLS (first 5 rows) ===');
    allCells.forEach(row => {
      console.log(`\nRow ${row.rowIndex}:`);
      row.cells.forEach((cell: any) => {
        console.log(`  Cell ${cell.cellIdx} (${cell.classes}): "${cell.content}"`);
      });
    });

    await page.screenshot({ path: '/tmp/row_zero_check.png' });

    // Query database for actual first row
    console.log('\n=== DATABASE FIRST ROW ===');
    // We'll check this separately

    // Check if row numbers start at 0 or 1
    const firstRowNum = await page.evaluate(() => {
      const firstRow = document.querySelector('.virtual-row');
      const rowNumCell = firstRow?.querySelector('.cell.row-num');
      return rowNumCell?.textContent?.trim();
    });
    console.log(`\nFirst visible row number: ${firstRowNum}`);

    // Check data attribute or index
    const dataIndices = await page.evaluate(() => {
      const rows = document.querySelectorAll('.virtual-row');
      return Array.from(rows).slice(0, 5).map(row => {
        return {
          style: row.getAttribute('style'),
          dataIndex: row.getAttribute('data-index'),
          firstCellContent: row.querySelector('.cell')?.textContent?.trim()?.substring(0, 20)
        };
      });
    });
    console.log('\nRow data attributes:');
    dataIndices.forEach((r, i) => console.log(`  Row ${i}:`, r));
  });
});
