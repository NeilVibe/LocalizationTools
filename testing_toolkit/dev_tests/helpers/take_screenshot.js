#!/usr/bin/env node
/**
 * Screenshot Helper for DEV Mode UI Debugging
 *
 * Usage:
 *   node take_screenshot.js <url> [output_file] [selector]
 *
 * Examples:
 *   node take_screenshot.js "http://localhost:5173"
 *   node take_screenshot.js "http://localhost:5173" "homepage.png"
 *   node take_screenshot.js "http://localhost:5173/ldm" "tm-modal.png" ".tm-manager-modal"
 *
 * After taking screenshot, use Claude's Read tool to view it visually.
 */

const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

async function takeScreenshot(url, outputFile, selector) {
    const browser = await chromium.launch({ headless: true });
    const context = await browser.newContext({
        viewport: { width: 1920, height: 1080 }
    });
    const page = await context.newPage();

    console.log(`Navigating to: ${url}`);
    await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 });

    // Wait a bit for any animations
    await page.waitForTimeout(1000);

    let screenshotPath;

    if (selector) {
        // Screenshot specific element
        console.log(`Taking screenshot of element: ${selector}`);
        const element = await page.$(selector);
        if (element) {
            screenshotPath = outputFile || `element_${Date.now()}.png`;
            await element.screenshot({ path: screenshotPath });
        } else {
            console.error(`Element not found: ${selector}`);
            // Take full page screenshot instead
            screenshotPath = outputFile || `fullpage_${Date.now()}.png`;
            await page.screenshot({ path: screenshotPath, fullPage: true });
        }
    } else {
        // Full page screenshot
        screenshotPath = outputFile || `screenshot_${Date.now()}.png`;
        await page.screenshot({ path: screenshotPath, fullPage: false });
    }

    console.log(`Screenshot saved: ${path.resolve(screenshotPath)}`);
    console.log(`\nTo view this screenshot visually, use Claude's Read tool:`);
    console.log(`  Read file_path="${path.resolve(screenshotPath)}"`);

    await browser.close();
    return screenshotPath;
}

// Login helper for authenticated pages
async function takeAuthenticatedScreenshot(url, outputFile, selector, credentials = { username: 'admin', password: 'admin123' }) {
    const browser = await chromium.launch({ headless: true });
    const context = await browser.newContext({
        viewport: { width: 1920, height: 1080 }
    });
    const page = await context.newPage();

    // First login
    console.log('Logging in...');
    await page.goto('http://localhost:5173', { waitUntil: 'networkidle' });

    // Fill login form
    await page.fill('input[type="text"], input[name="username"]', credentials.username);
    await page.fill('input[type="password"]', credentials.password);
    await page.click('button[type="submit"]');

    // Wait for navigation
    await page.waitForURL('**/dashboard**', { timeout: 10000 }).catch(() => {
        console.log('Note: Dashboard URL not detected, continuing anyway');
    });
    await page.waitForTimeout(2000);

    // Now navigate to target URL
    console.log(`Navigating to: ${url}`);
    await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(1000);

    let screenshotPath;

    if (selector) {
        console.log(`Taking screenshot of element: ${selector}`);
        const element = await page.$(selector);
        if (element) {
            screenshotPath = outputFile || `element_${Date.now()}.png`;
            await element.screenshot({ path: screenshotPath });
        } else {
            console.error(`Element not found: ${selector}`);
            screenshotPath = outputFile || `fullpage_${Date.now()}.png`;
            await page.screenshot({ path: screenshotPath, fullPage: true });
        }
    } else {
        screenshotPath = outputFile || `screenshot_${Date.now()}.png`;
        await page.screenshot({ path: screenshotPath, fullPage: false });
    }

    console.log(`Screenshot saved: ${path.resolve(screenshotPath)}`);
    console.log(`\nTo view this screenshot visually, use Claude's Read tool:`);
    console.log(`  Read file_path="${path.resolve(screenshotPath)}"`);

    await browser.close();
    return screenshotPath;
}

// CLI handling
const args = process.argv.slice(2);

if (args.length === 0) {
    console.log(`
Screenshot Helper for DEV Mode UI Debugging

Usage:
  node take_screenshot.js <url> [output_file] [selector]
  node take_screenshot.js --auth <url> [output_file] [selector]

Examples:
  node take_screenshot.js "http://localhost:5173"
  node take_screenshot.js "http://localhost:5173" "homepage.png"
  node take_screenshot.js "http://localhost:5173/ldm" "tm.png" ".tm-manager"
  node take_screenshot.js --auth "http://localhost:5173/ldm" "ldm.png"

Options:
  --auth    Login first with admin/admin123 before taking screenshot
`);
    process.exit(0);
}

// Check for --auth flag
const useAuth = args[0] === '--auth';
const startIndex = useAuth ? 1 : 0;

const url = args[startIndex] || 'http://localhost:5173';
const outputFile = args[startIndex + 1];
const selector = args[startIndex + 2];

(async () => {
    try {
        if (useAuth) {
            await takeAuthenticatedScreenshot(url, outputFile, selector);
        } else {
            await takeScreenshot(url, outputFile, selector);
        }
    } catch (error) {
        console.error('Error taking screenshot:', error.message);
        process.exit(1);
    }
})();

module.exports = { takeScreenshot, takeAuthenticatedScreenshot };
