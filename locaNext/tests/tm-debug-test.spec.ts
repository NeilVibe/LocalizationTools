import { test, expect } from '@playwright/test';

test('Debug login and navigation flow', async ({ page }) => {
  // Step 1: Go to app
  await page.goto('http://localhost:5173');
  await page.waitForTimeout(1000);
  await page.screenshot({ path: '/tmp/debug_01_landing.png' });
  console.log('Step 1: Landing page');

  // Step 2: Click Login button
  await page.getByRole('button', { name: /login/i }).click();
  await page.waitForTimeout(1000);
  await page.screenshot({ path: '/tmp/debug_02_login_form.png' });
  console.log('Step 2: Login form');

  // Step 3: Fill credentials
  await page.getByPlaceholder('Enter username').fill('admin');
  await page.getByPlaceholder('Enter password').fill('admin123');
  await page.screenshot({ path: '/tmp/debug_03_filled_form.png' });
  console.log('Step 3: Filled form');

  // Step 4: Click Login button in form
  // Need to find the specific login button in the form
  const loginButtons = page.getByRole('button', { name: /login/i });
  const buttonCount = await loginButtons.count();
  console.log('Found', buttonCount, 'login buttons');

  // Click the last one (should be the submit button)
  await loginButtons.last().click();
  await page.waitForTimeout(3000);
  await page.screenshot({ path: '/tmp/debug_04_after_login.png' });
  console.log('Step 4: After login click, URL:', page.url());

  // Step 5: Try to navigate to LDM
  await page.goto('http://localhost:5173/ldm');
  await page.waitForTimeout(2000);
  await page.screenshot({ path: '/tmp/debug_05_ldm_page.png' });
  console.log('Step 5: LDM page, URL:', page.url());

  // Check what's visible
  const tmExplorer = page.locator('text=TM Explorer');
  const visible = await tmExplorer.isVisible().catch(() => false);
  console.log('TM Explorer visible:', visible);

  // Check for any navigation elements
  const navItems = await page.locator('nav a, nav button').count();
  console.log('Navigation items found:', navItems);
});
