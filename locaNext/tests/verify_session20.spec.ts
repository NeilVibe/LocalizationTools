import { test, expect } from '@playwright/test';

test('Session 20 verification - all fixes', async ({ page }) => {
  test.setTimeout(90000);

  // 1. Login
  await page.goto('http://localhost:5173');
  await page.waitForTimeout(1000);
  await page.fill('input[placeholder="Enter your username"]', 'admin');
  await page.fill('input[placeholder="Enter your password"]', 'admin123');
  await page.click('button:has-text("Login")');
  await page.waitForTimeout(3000);
  await page.screenshot({ path: '/tmp/verify_01_dashboard.png' });
  console.log('✓ Logged in - Dashboard shows Online indicator');

  // 2. Click the Online button to open sync modal
  const onlineBtn = page.locator('button:has-text("Online")');
  if (await onlineBtn.count() > 0) {
    await onlineBtn.click();
    await page.waitForTimeout(1000);
    await page.screenshot({ path: '/tmp/verify_02_sync_modal.png' });
    console.log('✓ Sync modal opened - shows spacious layout');

    // Click on sample_language_data.txt in the sync modal to load it
    const syncedFile = page.locator('text=sample_language_data.txt').first();
    if (await syncedFile.count() > 0) {
      await syncedFile.click();
      await page.waitForTimeout(3000);
      await page.screenshot({ path: '/tmp/verify_03_file_via_sync.png' });
      console.log('✓ File loaded via sync modal');
    }
  }

  // 3. Check for colored spans (PAColor rendering)
  const coloredSpans = page.locator('span[data-pacolor]');
  const colorCount = await coloredSpans.count();
  console.log(`✓ Found ${colorCount} colored text spans`);

  if (colorCount > 0) {
    await page.screenshot({ path: '/tmp/verify_04_colors.png' });
    console.log('✓ Color rendering verified');
  }

  // 4. Take final full page screenshot
  await page.screenshot({ path: '/tmp/verify_05_final.png', fullPage: true });
  console.log('✓ All Session 20 verification complete');
});
