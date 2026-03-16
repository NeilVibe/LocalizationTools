import { test, expect } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';

/**
 * Phase 36: Visual Verification - Screenshot capture for all 5 pages
 * in both light and dark mode (10 screenshots minimum).
 *
 * Pages: Localization Data (files), TM, Game Data, Codex, World Map
 */

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SCREENSHOT_DIR = path.resolve(__dirname, '../../.planning/phases/36-verification/screenshots');

const PAGES = [
  { name: 'localization-data', tabText: 'Localization Data' },
  { name: 'tm', tabText: 'TM' },
  { name: 'game-data', tabText: 'Game Data' },
  { name: 'codex', tabText: 'Codex' },
  { name: 'world-map', tabText: 'Map' },
];

async function login(page: any) {
  await page.goto('/');
  await page.waitForTimeout(1500);

  // Step 1: Handle Launcher screen - click "Login" card
  const loginCard = page.locator('text=Login').first();
  const isLauncherVisible = await loginCard.isVisible().catch(() => false);
  if (isLauncherVisible) {
    await loginCard.click();
    await page.waitForTimeout(1000);
  }

  // Step 2: Fill login form (Carbon TextInput uses <input> inside wrapper)
  // Placeholder may be "Enter username" or "Enter your username"
  const usernameInput = page.locator('input[placeholder*="username"], input[placeholder*="Username"]').first();
  const isLoginFormVisible = await usernameInput.isVisible({ timeout: 5000 }).catch(() => false);

  if (isLoginFormVisible) {
    await usernameInput.fill('admin');
    const passwordInput = page.locator('input[placeholder*="password"], input[placeholder*="Password"]').first();
    await passwordInput.fill('admin123');

    // Click the Login button (not the Back button)
    const submitButton = page.locator('button:has-text("Login")').last();
    await submitButton.click();
    await page.waitForTimeout(3000);
  }

  // Step 3: Verify we're past login - nav tabs should be visible
  await expect(page.locator('.ldm-nav-tab').first()).toBeVisible({ timeout: 10000 });
}

test.describe('Phase 36: Visual Verification Screenshots', () => {
  // Run sequentially to avoid auth race conditions
  test.describe.configure({ mode: 'serial' });

  for (const mode of ['dark', 'light'] as const) {
    for (const pageInfo of PAGES) {
      test(`${pageInfo.name} - ${mode} mode`, async ({ page }) => {
        // Login first
        await login(page);

        // Set theme via CSS class swap (Carbon uses data-carbon-theme or class-based)
        if (mode === 'light') {
          await page.evaluate(() => {
            // Swap Carbon theme stylesheet effect by changing body class
            document.documentElement.setAttribute('data-carbon-theme', 'white');
            // Replace g100 with white theme
            const allStyles = document.querySelectorAll('style, link[rel="stylesheet"]');
            document.body.style.backgroundColor = '#f4f4f4';
            document.body.style.color = '#161616';
            // Force light mode on all elements
            document.querySelectorAll('*').forEach(el => {
              const htmlEl = el as HTMLElement;
              const computed = getComputedStyle(htmlEl);
              if (computed.backgroundColor === 'rgb(22, 22, 22)' || computed.backgroundColor === 'rgb(38, 38, 38)') {
                htmlEl.style.backgroundColor = '#f4f4f4';
              }
              if (computed.color === 'rgb(244, 244, 244)' || computed.color === 'rgb(198, 198, 198)') {
                htmlEl.style.color = '#161616';
              }
            });
          });
          await page.waitForTimeout(500);
        }

        // Navigate to the page by clicking the nav tab
        const navTab = page.locator(`.ldm-nav-tab:has-text("${pageInfo.tabText}")`);
        await expect(navTab).toBeVisible({ timeout: 5000 });
        await navTab.click();

        // Wait for page content to settle
        await page.waitForTimeout(2000);

        // Take viewport screenshot
        const filename = `${pageInfo.name}-${mode}.png`;
        await page.screenshot({
          path: path.join(SCREENSHOT_DIR, filename),
          fullPage: false,
        });
      });
    }
  }
});
