import { test, expect } from '@playwright/test';

test('full login and LDM flow', async ({ page }) => {
  page.on('console', (msg) => {
    const text = msg.text();
    // Show important messages
    if (text.includes('ERROR') || text.includes('error') || text.includes('Failed') || text.includes('Loading') || text.includes('LDM')) {
      console.log('BROWSER:', text);
    }
  });
  
  page.on('response', (response) => {
    if (response.status() >= 400) {
      console.log('HTTP ERROR:', response.status(), response.url());
    }
  });
  
  // Go to app
  await page.goto('http://localhost:5173/');
  
  // Click login
  await page.click('text=Login');
  await page.fill('input[placeholder*="username"]', 'admin');
  await page.fill('input[placeholder*="password"]', 'admin123');
  await page.click('button:has-text("Login"):not(:text-is("Back"))');
  
  // Wait for navigation to dashboard
  await page.waitForURL('**/dashboard', { timeout: 15000 });
  console.log('Reached dashboard');
  
  // Wait for LDM to load
  await page.waitForTimeout(3000);
  
  // Check for loading state
  const loading = await page.locator('text=Connecting to LDM').isVisible();
  console.log('Loading visible:', loading);
  
  // Check for error
  const errorBanner = await page.locator('.error-banner').isVisible();
  console.log('Error banner visible:', errorBanner);
  
  // Take screenshot
  await page.screenshot({ path: 'test-results/ldm-flow.png', fullPage: true });
  console.log('Screenshot saved');
  
  // Should not be stuck on loading
  expect(loading).toBe(false);
});
