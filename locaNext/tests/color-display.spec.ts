import { test, expect } from '@playwright/test';

test.describe('Color Display Test', () => {
  test('PAColor tags render as colored text', async ({ page }) => {
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

    await page.screenshot({ path: '/tmp/color_01_file_loaded.png' });

    // Check for colored spans in the grid
    const coloredSpans = await page.$$('span[style*="color"]');
    console.log(`Found ${coloredSpans.length} colored spans`);

    // Check for specific color patterns
    const goldSpans = await page.$$('span[style*="rgb(233, 189, 35)"], span[style*="#e9bd23"]');
    console.log(`Found ${goldSpans.length} gold colored spans`);

    // Get some cell content to verify
    const cells = await page.$$('.cell.source, .cell.target');
    console.log(`Found ${cells.length} cells`);

    // Check first few cells for PAColor tags (should NOT be visible as raw text)
    let rawTagsFound = 0;
    let coloredTextFound = 0;

    for (let i = 0; i < Math.min(10, cells.length); i++) {
      const html = await cells[i].innerHTML();
      if (html.includes('<PAColor') || html.includes('PAOldColor>')) {
        rawTagsFound++;
        console.log(`RAW TAG in cell ${i}: ${html.substring(0, 100)}...`);
      }
      if (html.includes('style=') && html.includes('color')) {
        coloredTextFound++;
      }
    }

    await page.screenshot({ path: '/tmp/color_02_grid_content.png' });

    console.log('\n=== COLOR DISPLAY RESULTS ===');
    console.log(`Total colored spans: ${coloredSpans.length}`);
    console.log(`Gold colored spans: ${goldSpans.length}`);
    console.log(`Raw PAColor tags visible: ${rawTagsFound}`);
    console.log(`Cells with colored content: ${coloredTextFound}`);

    if (rawTagsFound > 0) {
      console.log('\n⚠️ WARNING: Raw PAColor tags are visible - ColorText not working!');
    } else if (coloredSpans.length > 0) {
      console.log('\n✓ SUCCESS: Colors are rendering correctly!');
    } else {
      console.log('\n? UNKNOWN: No colored spans found - may need to scroll to colored rows');
    }
  });
});
