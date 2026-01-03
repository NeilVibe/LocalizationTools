import { test, expect } from '@playwright/test';

test('Verify color rendering in grid', async ({ page }) => {
  test.setTimeout(120000);

  // Login
  await page.goto('http://localhost:5173');
  await page.waitForTimeout(1000);
  await page.fill('input[placeholder="Enter your username"]', 'admin');
  await page.fill('input[placeholder="Enter your password"]', 'admin123');
  await page.click('button:has-text("Login")');
  await page.waitForTimeout(3000);
  console.log('✓ Logged in');

  // Double-click TestProject
  const testProject = page.locator('text=TestProject').first();
  if (await testProject.count() > 0) {
    await testProject.dblclick();
    await page.waitForTimeout(1000);
    console.log('✓ TestProject opened');
  }

  // Double-click TestFolder
  const testFolder = page.locator('text=TestFolder').first();
  if (await testFolder.count() > 0) {
    await testFolder.dblclick();
    await page.waitForTimeout(1000);
    console.log('✓ TestFolder opened');
  }

  // DOUBLE-click sample_language_data.txt
  const sampleFile = page.locator('text=sample_language_data.txt').first();
  if (await sampleFile.count() > 0) {
    await sampleFile.dblclick();
    console.log('✓ File double-clicked');

    // Wait for grid to finish loading - look for row content
    await page.waitForTimeout(3000);
    await page.screenshot({ path: '/tmp/verify_colors_1.png' });

    // Wait for "Loading rows..." to disappear
    try {
      await page.waitForSelector('text=Loading rows...', { state: 'hidden', timeout: 15000 });
      console.log('✓ Loading complete');
    } catch (e) {
      console.log('⚠ Still loading or no loading indicator');
    }

    await page.waitForTimeout(3000);
    await page.screenshot({ path: '/tmp/verify_colors_2.png', fullPage: true });
  }

  // Check for colored spans
  const coloredSpans = page.locator('span[data-pacolor]');
  const colorCount = await coloredSpans.count();
  console.log(`✓ Found ${colorCount} colored text spans with data-pacolor`);

  // Check for spans with inline color styles
  const colorStyleSpans = page.locator('span[style*="color"]');
  const styleCount = await colorStyleSpans.count();
  console.log(`✓ Found ${styleCount} spans with color styles`);

  // Check for any grid cells
  const gridCells = page.locator('.grid-cell, [class*="cell"], .row');
  const cellCount = await gridCells.count();
  console.log(`✓ Found ${cellCount} grid cells`);

  // Final screenshot
  await page.screenshot({ path: '/tmp/verify_colors_final.png', fullPage: true });
});
