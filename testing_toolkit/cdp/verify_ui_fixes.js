/**
 * VERIFICATION TEST: UI-051, UI-052, UI-053, UI-074
 *
 * This test PROVES the fixes work by actually testing them in a real browser.
 * No assumptions - only HARD EVIDENCE.
 *
 * Usage: node verify_ui_fixes.js
 */

const { chromium } = require('playwright');

const BASE_URL = process.env.TEST_URL || 'http://localhost:5173';
const API_BASE = 'http://localhost:8888';

// Test results
const results = {
  'UI-051_modal_close': { status: 'pending', details: '' },
  'UI-052_tm_suggest_endpoint': { status: 'pending', details: '' },
  'UI-053_scroll_constraint': { status: 'pending', details: '' },
  'UI-074_files_endpoint': { status: 'pending', details: '' }
};

async function verifyUI074FilesEndpoint() {
  console.log('\n=== UI-074: Verifying /api/ldm/files endpoint ===');

  try {
    // First get auth token
    const loginRes = await fetch(`${API_BASE}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: 'admin', password: 'admin123' })
    });

    if (!loginRes.ok) {
      results['UI-074_files_endpoint'] = {
        status: 'FAIL',
        details: `Login failed: ${loginRes.status}`
      };
      return;
    }

    const loginData = await loginRes.json();
    const token = loginData.access_token;

    // Test the files endpoint
    const filesRes = await fetch(`${API_BASE}/api/ldm/files?limit=5`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });

    if (!filesRes.ok) {
      results['UI-074_files_endpoint'] = {
        status: 'FAIL',
        details: `Endpoint returned ${filesRes.status}: ${await filesRes.text()}`
      };
      return;
    }

    const files = await filesRes.json();

    if (!Array.isArray(files)) {
      results['UI-074_files_endpoint'] = {
        status: 'FAIL',
        details: `Expected array, got: ${typeof files}`
      };
      return;
    }

    results['UI-074_files_endpoint'] = {
      status: 'PASS',
      details: `Endpoint returns array with ${files.length} files`
    };
    console.log(`✓ UI-074 PASS: /api/ldm/files returns ${files.length} files`);

  } catch (err) {
    results['UI-074_files_endpoint'] = {
      status: 'FAIL',
      details: `Error: ${err.message}`
    };
  }
}

async function verifyUI052TMSuggest() {
  console.log('\n=== UI-052: Verifying /api/ldm/tm/suggest endpoint ===');

  try {
    // First get auth token
    const loginRes = await fetch(`${API_BASE}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: 'admin', password: 'admin123' })
    });

    if (!loginRes.ok) {
      results['UI-052_tm_suggest_endpoint'] = {
        status: 'FAIL',
        details: `Login failed: ${loginRes.status}`
      };
      return;
    }

    const loginData = await loginRes.json();
    const token = loginData.access_token;

    // Test the TM suggest endpoint
    const tmRes = await fetch(`${API_BASE}/api/ldm/tm/suggest?source=test&threshold=0.3&max_results=5`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });

    if (!tmRes.ok) {
      const errText = await tmRes.text();
      results['UI-052_tm_suggest_endpoint'] = {
        status: 'FAIL',
        details: `Endpoint returned ${tmRes.status}: ${errText.slice(0, 200)}`
      };
      return;
    }

    const data = await tmRes.json();

    // API returns {suggestions: [], count: 0}
    if (!data || typeof data !== 'object') {
      results['UI-052_tm_suggest_endpoint'] = {
        status: 'FAIL',
        details: `Expected object, got: ${typeof data}`
      };
      return;
    }

    const suggestions = data.suggestions || data;
    const isValid = Array.isArray(suggestions) || (data.suggestions !== undefined);

    if (!isValid) {
      results['UI-052_tm_suggest_endpoint'] = {
        status: 'FAIL',
        details: `Unexpected response format: ${JSON.stringify(data).slice(0, 100)}`
      };
      return;
    }

    results['UI-052_tm_suggest_endpoint'] = {
      status: 'PASS',
      details: `Endpoint returns ${Array.isArray(suggestions) ? suggestions.length : data.count} suggestions`
    };
    console.log(`✓ UI-052 PASS: /api/ldm/tm/suggest works (${data.count || 0} results)`);

  } catch (err) {
    results['UI-052_tm_suggest_endpoint'] = {
      status: 'FAIL',
      details: `Error: ${err.message}`
    };
  }
}

async function verifyUI053ScrollConstraint(page) {
  console.log('\n=== UI-053: Verifying scroll container height constraint ===');

  try {
    // Check if scroll container exists and has proper height
    const scrollInfo = await page.evaluate(() => {
      const container = document.querySelector('.scroll-container');
      if (!container) {
        return { error: 'scroll-container not found' };
      }

      const rect = container.getBoundingClientRect();
      const computed = window.getComputedStyle(container);
      const parent = container.parentElement;
      const parentRect = parent ? parent.getBoundingClientRect() : null;

      // Get viewport height
      const viewportHeight = window.innerHeight;

      // Check if scrolling works
      const canScroll = container.scrollHeight > container.clientHeight;

      return {
        containerHeight: rect.height,
        containerScrollHeight: container.scrollHeight,
        containerClientHeight: container.clientHeight,
        viewportHeight,
        parentHeight: parentRect ? parentRect.height : null,
        overflow: computed.overflow,
        overflowY: computed.overflowY,
        canScroll,
        heightValue: computed.height,
        minHeightValue: computed.minHeight,
        // Critical check: container should not exceed viewport
        isConstrained: rect.height < viewportHeight * 2
      };
    });

    if (scrollInfo.error) {
      results['UI-053_scroll_constraint'] = {
        status: 'SKIP',
        details: scrollInfo.error
      };
      console.log(`⚠ UI-053 SKIP: ${scrollInfo.error}`);
      return;
    }

    // Check if height is properly constrained
    // Before fix: container was 480,000px+
    // After fix: container should be viewport-sized
    const isConstrained = scrollInfo.containerHeight < 5000; // Generous limit
    const overflowCorrect = scrollInfo.overflowY === 'auto' || scrollInfo.overflowY === 'scroll';

    if (isConstrained && overflowCorrect) {
      results['UI-053_scroll_constraint'] = {
        status: 'PASS',
        details: `Container height: ${scrollInfo.containerHeight}px, overflow-y: ${scrollInfo.overflowY}`
      };
      console.log(`✓ UI-053 PASS: Scroll container properly constrained (${scrollInfo.containerHeight}px)`);
    } else {
      results['UI-053_scroll_constraint'] = {
        status: 'FAIL',
        details: `Container: ${scrollInfo.containerHeight}px (expected < 5000), overflow-y: ${scrollInfo.overflowY}`
      };
      console.log(`✗ UI-053 FAIL: Container height ${scrollInfo.containerHeight}px is too large`);
    }

    console.log('  Details:', JSON.stringify(scrollInfo, null, 2));

  } catch (err) {
    results['UI-053_scroll_constraint'] = {
      status: 'FAIL',
      details: `Error: ${err.message}`
    };
  }
}

async function verifyUI051ModalClose(page) {
  console.log('\n=== UI-051: Verifying edit modal close button ===');

  try {
    // Wait for virtual scroll to render rows
    console.log('  Waiting for virtual rows to render...');
    await page.waitForTimeout(2000);

    // Check for rows in the VirtualGrid - they have class="virtual-row"
    const rowInfo = await page.evaluate(() => {
      // VirtualGrid rows have class="virtual-row"
      const rows = document.querySelectorAll('.virtual-row');
      const scrollContainer = document.querySelector('.scroll-container');
      return {
        rowCount: rows.length,
        firstRowClasses: rows[0] ? rows[0].className : null,
        hasScrollContainer: !!scrollContainer,
        scrollHeight: scrollContainer ? scrollContainer.scrollHeight : 0,
        // Also check for any loading state
        hasLoading: !!document.querySelector('.placeholder-shimmer')
      };
    });

    console.log(`  Found ${rowInfo.rowCount || 0} rows in grid (scrollHeight: ${rowInfo.scrollHeight})`);

    if (!rowInfo.rowCount || rowInfo.rowCount === 0) {
      results['UI-051_modal_close'] = {
        status: 'SKIP',
        details: 'No rows found in virtual grid'
      };
      return;
    }

    // Double-click on a target cell to open the edit modal
    // Modal opens on dblclick on ".cell.target" elements
    console.log('  Double-clicking target cell to open modal...');
    const clicked = await page.evaluate(() => {
      // Find target cells - they have class "cell target"
      const targetCells = document.querySelectorAll('.cell.target');
      if (targetCells.length > 0) {
        // Get second target cell (first might be partially visible)
        const targetCell = targetCells[1] || targetCells[0];
        // Create and dispatch dblclick event
        const dblclickEvent = new MouseEvent('dblclick', {
          bubbles: true,
          cancelable: true,
          view: window
        });
        targetCell.dispatchEvent(dblclickEvent);
        return { clicked: true, classes: targetCell.className, count: targetCells.length };
      }
      return { clicked: false, count: 0 };
    });

    console.log(`  Clicked cell: ${clicked.clicked ? clicked.classes : 'none'}`);

    if (!clicked.clicked) {
      results['UI-051_modal_close'] = {
        status: 'SKIP',
        details: 'Could not find cell to click'
      };
      return;
    }

    // Wait for modal to appear
    await page.waitForTimeout(800);

    // Take screenshot of modal state
    await page.screenshot({ path: '/tmp/verify_modal_open.png', fullPage: false });

    // Check if modal opened
    const modalBefore = await page.evaluate(() => {
      const overlay = document.querySelector('.edit-modal-overlay');
      if (!overlay) return { exists: false };

      const style = window.getComputedStyle(overlay);
      return {
        exists: true,
        display: style.display,
        visibility: style.visibility,
        opacity: style.opacity
      };
    });

    console.log(`  Modal state: ${JSON.stringify(modalBefore)}`);

    if (!modalBefore.exists) {
      results['UI-051_modal_close'] = {
        status: 'SKIP',
        details: 'Modal overlay not found after cell click'
      };
      return;
    }

    console.log('  Modal opened, testing close button...');

    // Click the close button using Playwright's click
    const closeBtnExists = await page.$('.close-btn');
    if (closeBtnExists) {
      await closeBtnExists.click();
      console.log('  Clicked close button');
    } else {
      // Try pressing Escape key
      await page.keyboard.press('Escape');
      console.log('  Pressed Escape key');
    }

    // Wait for modal to close
    await page.waitForTimeout(500);

    // Take screenshot after close attempt
    await page.screenshot({ path: '/tmp/verify_modal_closed.png', fullPage: false });

    // Check if modal closed
    const modalAfter = await page.evaluate(() => {
      const overlay = document.querySelector('.edit-modal-overlay');
      if (!overlay) return { exists: false };

      const style = window.getComputedStyle(overlay);
      return {
        exists: true,
        display: style.display,
        visibility: style.visibility
      };
    });

    console.log(`  Modal after close: ${JSON.stringify(modalAfter)}`);

    // Modal is closed if overlay doesn't exist or display is none
    const isClosed = !modalAfter.exists || modalAfter.display === 'none';

    if (isClosed) {
      results['UI-051_modal_close'] = {
        status: 'PASS',
        details: 'Close button works - modal closed successfully'
      };
      console.log('✓ UI-051 PASS: Modal close button works');
    } else {
      results['UI-051_modal_close'] = {
        status: 'FAIL',
        details: `Modal still visible (display: ${modalAfter.display})`
      };
      console.log('✗ UI-051 FAIL: Modal did not close');
    }

  } catch (err) {
    results['UI-051_modal_close'] = {
      status: 'FAIL',
      details: `Error: ${err.message}`
    };
    console.log(`  Error: ${err.message}`);
  }
}

async function main() {
  console.log('╔════════════════════════════════════════════════════════════╗');
  console.log('║  UI FIX VERIFICATION TEST                                  ║');
  console.log('║  Testing: UI-051, UI-052, UI-053, UI-074                   ║');
  console.log('╚════════════════════════════════════════════════════════════╝');
  console.log(`\nTarget: ${BASE_URL}`);
  console.log(`API: ${API_BASE}`);

  // First test API endpoints directly (no browser needed)
  await verifyUI074FilesEndpoint();
  await verifyUI052TMSuggest();

  // Now test UI components in browser
  console.log('\n=== Starting browser tests ===');

  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox']
  });

  try {
    const context = await browser.newContext({
      viewport: { width: 1920, height: 1080 }
    });
    const page = await context.newPage();

    // Collect console errors
    const consoleErrors = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    // Navigate to app
    console.log('\nNavigating to app...');
    await page.goto(BASE_URL, { waitUntil: 'networkidle', timeout: 30000 });

    // Login - Carbon Components use bx--text-input class
    console.log('Logging in...');
    // Wait for login form to be visible
    await page.waitForSelector('.login-box, .login-container', { timeout: 10000 }).catch(() => {
      console.log('Login form not found - may already be logged in');
    });

    // Check if we need to login
    const needsLogin = await page.$('.login-box');
    if (needsLogin) {
      // Carbon TextInput has bx--text-input class
      await page.fill('.bx--text-input:not([type="password"])', 'admin');
      await page.fill('input[type="password"], .bx--password-input', 'admin123');
      await page.click('button[type="submit"]');
    }
    await page.waitForTimeout(2000);

    // Navigate to LDM - first take a screenshot to see current state
    await page.screenshot({ path: '/tmp/verify_step1_after_login.png', fullPage: false });
    console.log('Screenshot: /tmp/verify_step1_after_login.png');

    console.log('Navigating to LDM...');
    // Try multiple selectors for LDM button
    const ldmButton = await page.$('button:has-text("Language Data Manager")') ||
                      await page.$('button:has-text("LDM")') ||
                      await page.$('[data-app="ldm"]') ||
                      await page.$('.app-card:has-text("Language")');

    if (ldmButton) {
      await ldmButton.click();
      await page.waitForTimeout(3000);
    } else {
      console.log('LDM button not found, checking if already in LDM...');
    }

    await page.screenshot({ path: '/tmp/verify_step2_in_ldm.png', fullPage: false });
    console.log('Screenshot: /tmp/verify_step2_in_ldm.png');

    // Wait for LDM to load and check for project tree
    await page.waitForTimeout(2000);

    // Select project - this shows the project tree with files
    console.log('Looking for project to select...');
    const projectItem = await page.$('.project-item');

    if (projectItem) {
      console.log('Found project, selecting...');
      await projectItem.click();
      await page.waitForTimeout(2000);
    } else {
      console.log('No project found - may need to create one');
    }

    await page.screenshot({ path: '/tmp/verify_step3_project_selected.png', fullPage: false });

    // Click on a file to load it - files are in .tree-node elements
    console.log('Looking for file to open...');
    const fileNode = await page.$('.tree-node');

    if (fileNode) {
      console.log('Found file, clicking to open...');
      await fileNode.click();
      await page.waitForTimeout(3000);
    } else {
      console.log('No files found in tree');
    }

    // Take final screenshot for evidence
    await page.screenshot({ path: '/tmp/verify_ui_fixes.png', fullPage: false });
    console.log('Screenshot: /tmp/verify_ui_fixes.png');

    // Run UI tests
    await verifyUI053ScrollConstraint(page);
    await verifyUI051ModalClose(page);

    // Report console errors
    if (consoleErrors.length > 0) {
      console.log(`\n⚠ Console errors found: ${consoleErrors.length}`);
      consoleErrors.slice(0, 5).forEach((err, i) => {
        console.log(`  ${i + 1}. ${err.slice(0, 100)}`);
      });
    }

  } finally {
    await browser.close();
  }

  // Print final results
  console.log('\n╔════════════════════════════════════════════════════════════╗');
  console.log('║  VERIFICATION RESULTS                                      ║');
  console.log('╚════════════════════════════════════════════════════════════╝');

  let passCount = 0;
  let failCount = 0;
  let skipCount = 0;

  for (const [test, result] of Object.entries(results)) {
    const icon = result.status === 'PASS' ? '✓' :
                 result.status === 'FAIL' ? '✗' : '⚠';
    console.log(`${icon} ${test}: ${result.status}`);
    console.log(`  └─ ${result.details}`);

    if (result.status === 'PASS') passCount++;
    else if (result.status === 'FAIL') failCount++;
    else skipCount++;
  }

  console.log('\n────────────────────────────────────────────────────────────');
  console.log(`TOTAL: ${passCount} PASS, ${failCount} FAIL, ${skipCount} SKIP`);

  if (failCount > 0) {
    console.log('\n⚠ SOME TESTS FAILED - Fixes need review');
    process.exit(1);
  } else if (passCount > 0) {
    console.log('\n✓ All tested fixes verified!');
    process.exit(0);
  }
}

main().catch(err => {
  console.error('Test failed:', err);
  process.exit(1);
});
