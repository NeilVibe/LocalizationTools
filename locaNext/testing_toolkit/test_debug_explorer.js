// Debug test for Windows Explorer
import { chromium } from 'playwright';

async function debugExplorer() {
  console.log('🔍 Debug: Windows Explorer Data Loading...\n');

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  // Capture all console logs
  const logs = [];
  page.on('console', msg => {
    const text = msg.text();
    logs.push(`[${msg.type()}] ${text}`);
    if (text.includes('API') || text.includes('Projects') || text.includes('error') || text.includes('ERROR')) {
      console.log(`  📋 ${text}`);
    }
  });

  try {
    console.log('1. Loading app...');
    await page.goto('http://localhost:5173');
    await page.waitForLoadState('networkidle');

    console.log('2. Logging in...');
    await page.waitForSelector('.bx--text-input', { timeout: 10000 });
    await page.locator('.bx--text-input').first().fill('admin');
    await page.locator('input[type="password"]').fill('admin123');
    await page.click('button[type="submit"]');
    await page.waitForSelector('.ldm-app', { timeout: 10000 });

    console.log('3. Waiting for FilesPage to load...');
    await page.waitForTimeout(2000);

    // Check if ExplorerGrid shows items or empty state
    const gridBody = await page.locator('.grid-body').innerHTML().catch(() => 'not found');
    const emptyState = await page.locator('.empty-state').isVisible().catch(() => false);

    console.log(`\n4. Grid state:`);
    console.log(`   - Empty state visible: ${emptyState}`);
    console.log(`   - Grid body content length: ${gridBody.length}`);

    // Check for grid-row elements
    const rows = await page.locator('.grid-row').count();
    console.log(`   - Grid rows found: ${rows}`);

    // Log recent relevant console messages
    console.log('\n5. Relevant console logs:');
    logs.filter(l => l.includes('project') || l.includes('Project') || l.includes('API') || l.includes('load'))
      .slice(-15)
      .forEach(l => console.log(`   ${l}`));

    console.log('\n6. Taking screenshot...');
    await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/debug-explorer.png', fullPage: true });

  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    await browser.close();
  }
}

debugExplorer();
