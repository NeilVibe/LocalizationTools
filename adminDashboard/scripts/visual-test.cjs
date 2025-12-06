#!/usr/bin/env node
/**
 * Admin Dashboard Visual Testing Script - ENHANCED
 *
 * Uses Playwright's FULL POWER:
 * 1. Screenshots for visual verification
 * 2. FULL Console monitoring (ALL types: log, info, warn, error, debug)
 * 3. Network request/response tracking with status codes
 * 4. DOM element verification
 * 5. "undefined" text detection
 * 6. API response validation
 * 7. Page error (crash) detection
 * 8. DevTools-like output format
 *
 * Usage: node scripts/visual-test.cjs [--verbose] [--page=/database]
 *
 * Prerequisites:
 * - Server running on port 8888
 * - Dashboard running on port 5175
 * - Playwright installed
 *
 * Output matches browser DevTools console format for easy comparison.
 */

const { chromium } = require('playwright');
const path = require('path');

const DASHBOARD_URL = 'http://localhost:5175';
const SCREENSHOT_DIR = '/tmp';

// Parse command line arguments
const args = process.argv.slice(2);
const verbose = args.includes('--verbose');
const pageFilter = args.find(a => a.startsWith('--page='))?.split('=')[1];

const PAGES = [
  {
    path: '/',
    name: 'Overview',
    checks: [
      { selector: '.compact-stat-value', description: 'Stats values visible' },
      { selector: '.page-title', description: 'Page title visible' }
    ],
    apiEndpoints: ['/api/v2/admin/stats/overview', '/api/v2/admin/stats/app-rankings']
  },
  {
    path: '/users',
    name: 'Users',
    checks: [
      { selector: '.page-title', description: 'Page title visible' }
    ],
    apiEndpoints: ['/api/v2/admin/users']
  },
  {
    path: '/stats',
    name: 'Stats',
    checks: [
      { selector: '.page-title', description: 'Page title visible' },
      { selector: '.period-selector', description: 'Period selector visible' }
    ],
    apiEndpoints: ['/api/v2/admin/stats/app-rankings']
  },
  {
    path: '/telemetry',
    name: 'Telemetry',
    checks: [
      { selector: '.page-title', description: 'Page title visible' }
    ],
    apiEndpoints: []
  },
  {
    path: '/logs',
    name: 'Logs',
    checks: [
      { selector: '.page-title', description: 'Page title visible' }
    ],
    apiEndpoints: ['/api/v2/admin/logs']
  },
  {
    path: '/database',
    name: 'Database',
    checks: [
      { selector: '.page-title', description: 'Page title visible' },
      { selector: '.stat-card', description: 'Database stats visible' }
    ],
    apiEndpoints: ['/api/v2/admin/stats/database']
  },
  {
    path: '/server',
    name: 'Server',
    checks: [
      { selector: '.page-title', description: 'Page title visible' },
      { selector: '.stat-card', description: 'Server stats visible' }
    ],
    apiEndpoints: ['/api/v2/admin/stats/server']
  }
];

async function runVisualTests() {
  console.log('=== Admin Dashboard Visual Test (ENHANCED) ===');
  console.log(`Dashboard URL: ${DASHBOARD_URL}`);
  console.log(`Screenshot directory: ${SCREENSHOT_DIR}`);
  console.log(`Verbose mode: ${verbose ? 'ON (all console types)' : 'OFF (errors only)'}`);
  if (pageFilter) {
    console.log(`Page filter: ${pageFilter}`);
  }
  console.log('');

  // PREREQUISITE CHECK: Is backend server running?
  console.log('=== PREREQUISITE CHECK ===');
  try {
    const http = require('http');
    await new Promise((resolve, reject) => {
      const req = http.get('http://localhost:8888/health', { timeout: 3000 }, (res) => {
        if (res.statusCode === 200) {
          console.log('Backend (8888): RUNNING');
          resolve();
        } else {
          reject(new Error(`Backend returned ${res.statusCode}`));
        }
      });
      req.on('error', (err) => reject(err));
      req.on('timeout', () => { req.destroy(); reject(new Error('Timeout')); });
    });
  } catch (err) {
    console.log('');
    console.log('ERROR: Backend server is NOT running on port 8888');
    console.log('');
    console.log('This is why you see "ERR_CONNECTION_REFUSED" or "Failed to fetch" errors.');
    console.log('');
    console.log('FIX: Start the backend server first:');
    console.log('  cd /home/neil1988/LocalizationTools');
    console.log('  python3 server/main.py');
    console.log('');
    console.log('Then run this test again.');
    process.exit(1);
  }

  // Check dashboard is running
  try {
    const http = require('http');
    await new Promise((resolve, reject) => {
      const req = http.get(DASHBOARD_URL, { timeout: 3000 }, (res) => {
        if (res.statusCode === 200) {
          console.log('Dashboard (5175): RUNNING');
          resolve();
        } else {
          reject(new Error(`Dashboard returned ${res.statusCode}`));
        }
      });
      req.on('error', (err) => reject(err));
      req.on('timeout', () => { req.destroy(); reject(new Error('Timeout')); });
    });
  } catch (err) {
    console.log('');
    console.log('ERROR: Dashboard is NOT running on port 5175');
    console.log('');
    console.log('FIX: Start the dashboard first:');
    console.log('  cd /home/neil1988/LocalizationTools/adminDashboard');
    console.log('  npm run dev -- --port 5175');
    console.log('');
    process.exit(1);
  }

  console.log('Prerequisites: OK');
  console.log('');

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1400, height: 900 } });
  const page = await context.newPage();

  // Track ALL console output and network
  const consoleMessages = [];  // ALL console types
  const consoleErrors = [];    // Just errors (for backwards compatibility)
  const pageErrors = [];
  const failedRequests = [];
  const apiResponses = {};

  // Console monitoring - Capture ALL types (log, info, warn, error, debug)
  page.on('console', msg => {
    const type = msg.type();
    const text = msg.text();
    const entry = {
      page: page.url(),
      type: type.toUpperCase(),
      text: text,
      timestamp: new Date().toISOString()
    };

    // Store ALL messages
    consoleMessages.push(entry);

    // Also track errors separately for backwards compatibility
    if (type === 'error') {
      consoleErrors.push({ page: page.url(), text: text });
    }

    // In verbose mode, print DevTools-style output
    if (verbose) {
      const typeColors = {
        'log': '\x1b[0m',      // default
        'info': '\x1b[36m',    // cyan
        'warn': '\x1b[33m',    // yellow
        'error': '\x1b[31m',   // red
        'debug': '\x1b[35m'    // magenta
      };
      const color = typeColors[type] || '\x1b[0m';
      const reset = '\x1b[0m';
      console.log(`  ${color}[${type.toUpperCase()}]${reset} ${text.substring(0, 150)}`);
    }
  });

  // Page error (crash) monitoring
  page.on('pageerror', error => {
    pageErrors.push({ page: page.url(), error: error.message });
  });

  // Network monitoring
  page.on('requestfailed', request => {
    failedRequests.push({ url: request.url(), failure: request.failure()?.errorText });
  });

  page.on('response', response => {
    const url = response.url();
    if (url.includes('/api/')) {
      apiResponses[url] = {
        status: response.status(),
        ok: response.ok()
      };
    }
  });

  const results = [];

  // Filter pages if --page argument provided
  const pagesToTest = pageFilter
    ? PAGES.filter(p => p.path === pageFilter || p.name.toLowerCase() === pageFilter.toLowerCase())
    : PAGES;

  if (pageFilter && pagesToTest.length === 0) {
    console.log(`ERROR: No page found matching "${pageFilter}"`);
    console.log('Available pages:');
    PAGES.forEach(p => console.log(`  ${p.path} (${p.name})`));
    process.exit(1);
  }

  for (const p of pagesToTest) {
    console.log(`Testing ${p.name} (${p.path})...`);
    const result = { name: p.name, path: p.path, passed: true, errors: [], warnings: [] };

    try {
      // Navigate to page
      const response = await page.goto(`${DASHBOARD_URL}${p.path}`, {
        timeout: 15000,
        waitUntil: 'networkidle'
      });

      // Check HTTP status
      if (!response.ok()) {
        result.passed = false;
        result.errors.push(`Page returned HTTP ${response.status()}`);
      }

      await page.waitForTimeout(1000);

      // Take screenshot
      const screenshotPath = path.join(SCREENSHOT_DIR, `dashboard_${p.name.toLowerCase()}.png`);
      await page.screenshot({ path: screenshotPath, fullPage: true });
      console.log(`  -> Screenshot: ${screenshotPath}`);

      // Check for error container
      const errorEl = await page.$('.error-container');
      if (errorEl) {
        const errorText = await errorEl.textContent();
        result.passed = false;
        result.errors.push(`Error displayed: ${errorText.substring(0, 100)}`);
        console.log(`  -> ERROR: ${errorText.substring(0, 100)}`);
      }

      // Check for "undefined" text (data binding issues)
      const bodyText = await page.textContent('body');
      const undefinedPatterns = ['undefined ops', 'undefined rows', 'undefined calls', 'undefined users'];
      for (const pattern of undefinedPatterns) {
        if (bodyText.includes(pattern)) {
          result.passed = false;
          result.errors.push(`Found "${pattern}" in content - data binding issue`);
          console.log(`  -> ERROR: Found "${pattern}"`);
        }
      }

      // Check for N/A with suspicious context (might indicate missing data)
      if (bodyText.includes('N/A') && bodyText.includes('undefined')) {
        result.warnings.push('Page has N/A values - may need data');
      }

      // Run specific element checks
      for (const check of p.checks) {
        const el = await page.$(check.selector);
        if (!el) {
          result.warnings.push(`${check.description} (${check.selector})`);
          console.log(`  -> WARNING: ${check.description} not found`);
        }
      }

      // Check API responses for this page
      for (const endpoint of p.apiEndpoints) {
        const matchingResponses = Object.entries(apiResponses).filter(([url]) => url.includes(endpoint));
        if (matchingResponses.length === 0) {
          result.warnings.push(`API ${endpoint} not called`);
        } else {
          for (const [url, resp] of matchingResponses) {
            if (!resp.ok) {
              result.passed = false;
              result.errors.push(`API ${endpoint} returned ${resp.status}`);
              console.log(`  -> ERROR: API ${endpoint} returned ${resp.status}`);
            }
          }
        }
      }

      if (result.errors.length === 0) {
        console.log(`  -> PASSED${result.warnings.length > 0 ? ` (${result.warnings.length} warnings)` : ''}`);
      }

    } catch (error) {
      result.passed = false;
      result.errors.push(`Page error: ${error.message}`);
      console.log(`  -> FAILED: ${error.message}`);
    }

    results.push(result);
  }

  await browser.close();

  // Summary
  console.log('');
  console.log('=== Test Summary ===');
  const passed = results.filter(r => r.passed).length;
  const failed = results.filter(r => !r.passed).length;
  const warnings = results.reduce((sum, r) => sum + r.warnings.length, 0);

  console.log(`Pages tested: ${results.length}`);
  console.log(`Passed: ${passed}`);
  console.log(`Failed: ${failed}`);
  console.log(`Warnings: ${warnings}`);

  // Full console log dump (always show if there are messages)
  if (consoleMessages.length > 0) {
    console.log('');
    console.log('=== Console Output Summary ===');
    const byType = {};
    consoleMessages.forEach(m => {
      byType[m.type] = (byType[m.type] || 0) + 1;
    });
    Object.entries(byType).forEach(([type, count]) => {
      console.log(`  ${type}: ${count}`);
    });

    // Show errors prominently
    if (consoleErrors.length > 0) {
      console.log('');
      console.log(`Console ERRORS: ${consoleErrors.length}`);
      consoleErrors.slice(0, 10).forEach((e, i) => {
        console.log(`  ${i + 1}. ${e.text.substring(0, 150)}`);
      });
    }

    // In verbose mode, dump all messages
    if (verbose) {
      console.log('');
      console.log('=== Full Console Dump ===');
      consoleMessages.forEach((m, i) => {
        console.log(`[${m.type}] ${m.text.substring(0, 200)}`);
      });
    }
  }

  if (pageErrors.length > 0) {
    console.log('');
    console.log(`Page crashes: ${pageErrors.length}`);
    pageErrors.forEach((e, i) => {
      console.log(`  ${i + 1}. ${e.error.substring(0, 100)}`);
    });
  }

  if (failedRequests.length > 0) {
    console.log('');
    console.log(`Failed requests: ${failedRequests.length}`);
    failedRequests.slice(0, 5).forEach((r, i) => {
      console.log(`  ${i + 1}. ${r.url} - ${r.failure}`);
    });
  }

  // Return exit code
  if (failed > 0 || consoleErrors.length > 0 || pageErrors.length > 0) {
    console.log('');
    console.log('RESULT: FAILED');
    process.exit(1);
  } else {
    console.log('');
    console.log('RESULT: ALL TESTS PASSED');
    process.exit(0);
  }
}

runVisualTests().catch(err => {
  console.error('Test script error:', err);
  process.exit(1);
});
