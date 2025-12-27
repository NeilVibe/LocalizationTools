import { test, expect } from '@playwright/test';

test('verify grid hover and selection states', async ({ page }) => {
  // Login
  await page.goto('/');
  await page.waitForTimeout(1000);
  
  // Use placeholder text to find inputs
  await page.fill('input[placeholder*="username"]', 'admin');
  await page.fill('input[placeholder*="password"]', 'admin123');
  await page.click('button:has-text("Login")');
  
  // Wait for LDM page
  await page.waitForSelector('text=LanguageData Manager', { timeout: 15000 });
  await page.screenshot({ path: 'test-results/01-ldm-page.png' });
  
  // Expand project
  await page.click('text=Playwright Test Project');
  await page.waitForTimeout(1000);
  await page.screenshot({ path: 'test-results/02-project-expanded.png' });
  
  // Click on a file
  const file = page.locator('text=test_10k.txt').first();
  if (await file.isVisible()) {
    await file.click();
    await page.waitForTimeout(3000);
    await page.screenshot({ path: 'test-results/03-file-opened.png' });
    
    // Check for cells
    const cells = page.locator('.cell');
    const cellCount = await cells.count();
    console.log(`Found ${cellCount} cells`);
    
    if (cellCount > 0) {
      // Test hover on source cell
      const sourceCell = page.locator('.cell.source').first();
      await sourceCell.hover();
      await page.waitForTimeout(300);
      await page.screenshot({ path: 'test-results/04-source-hover.png' });
      
      // Test hover on target cell
      const targetCell = page.locator('.cell.target').first();
      await targetCell.hover();
      await page.waitForTimeout(300);
      await page.screenshot({ path: 'test-results/05-target-hover.png' });
      
      // Test click selection
      await targetCell.click();
      await page.waitForTimeout(300);
      await page.screenshot({ path: 'test-results/06-target-clicked.png' });
      
      // Move mouse away and check if selection persists
      await page.mouse.move(100, 100);
      await page.waitForTimeout(300);
      await page.screenshot({ path: 'test-results/07-after-mouse-away.png' });
      
      console.log('All screenshots captured');
    }
  }
});
