import { test, expect } from '@playwright/test';

test('capture TM page settings panel', async ({ page }) => {
  // Login
  await page.goto('/');
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(2000);
  await page.click('text=Login');
  await page.waitForTimeout(2000);
  await page.fill('input[placeholder*="username" i], input[placeholder*="Username" i], input[type="text"]', 'admin');
  await page.fill('input[placeholder*="password" i], input[placeholder*="Password" i], input[type="password"]', 'admin123');
  await page.click('button:has-text("Login"), button:has-text("Sign"), button[type="submit"]');
  await page.waitForTimeout(3000);
  
  // Go to TM page
  await page.click('text=TM');
  await page.waitForTimeout(2000);
  await page.screenshot({ path: 'tm-page-initial.png', fullPage: true });
  
  // Click the Settings gear icon in the TM header (top right area)
  // The Settings button should be in the Translation Memories header
  const settingsIcon = page.locator('button[title="Settings"], .icon-button:has(svg)').last();
  if (await settingsIcon.isVisible({ timeout: 3000 }).catch(() => false)) {
    await settingsIcon.click();
    await page.waitForTimeout(1500);
    await page.screenshot({ path: 'tm-settings-panel.png', fullPage: true });
  }
  
  console.log('Screenshots saved');
});
