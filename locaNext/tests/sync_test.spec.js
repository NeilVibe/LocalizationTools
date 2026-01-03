// @ts-check
import { test, expect } from '@playwright/test';

test('sync dashboard shows subscriptions', async ({ page }) => {
  // Login
  await page.goto('http://localhost:5173');
  await page.waitForTimeout(2000);
  await page.fill('input[placeholder="Enter your username"]', 'admin');
  await page.fill('input[placeholder="Enter your password"]', 'admin123');
  await page.click('button:has-text("Login")');
  await page.waitForTimeout(2000);
  
  // Find sync status button
  const syncButton = page.locator('.sync-status-button');
  await expect(syncButton).toBeVisible({ timeout: 5000 });
  
  const buttonText = await syncButton.textContent();
  console.log('Sync button text:', buttonText);
  
  // Click to open dashboard
  await syncButton.click();
  await page.waitForTimeout(1000);
  
  // Check modal opened (Carbon modal uses .bx--modal.is-visible)
  const modal = page.locator('.bx--modal.is-visible, .bx--modal--open');
  await expect(modal).toBeVisible({ timeout: 5000 });
  
  // Take screenshot
  await page.screenshot({ path: '/tmp/sync_dashboard.png' });
  
  // Check subscription items
  const subscriptionList = page.locator('.subscriptions-list');
  const items = page.locator('.subscription-item');
  const count = await items.count();
  console.log('Subscription items:', count);
});
