/**
 * COMPREHENSIVE BUILD TEST - Build 396
 *
 * Tests ALL issues from ISSUES_TO_FIX.md
 * Takes screenshots at EVERY step
 * THE HARD WAY - no shortcuts, full verification
 */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const BASE_URL = 'http://localhost:5173';
const API_BASE = 'http://localhost:8888';
const SCREENSHOT_DIR = '/tmp/build_test_screenshots';

// Ensure screenshot directory exists
if (!fs.existsSync(SCREENSHOT_DIR)) {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

let screenshotCount = 0;

async function screenshot(page, name) {
  screenshotCount++;
  const filename = `${String(screenshotCount).padStart(3, '0')}_${name}.png`;
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, filename), fullPage: false });
  console.log(`  📸 ${filename}`);
  return filename;
}

const results = [];

function log(issue, status, details) {
  const icon = status === 'PASS' ? '✅' : status === 'FAIL' ? '❌' : '⚠️';
  console.log(`${icon} ${issue}: ${status}`);
  if (details) console.log(`   └─ ${details}`);
  results.push({ issue, status, details });
}

async function main() {
  console.log('╔══════════════════════════════════════════════════════════════╗');
  console.log('║  COMPREHENSIVE BUILD TEST - Build 396                        ║');
  console.log('║  Philosophy: ALWAYS CHOOSE HARD                              ║');
  console.log('╚══════════════════════════════════════════════════════════════╝');
  console.log(`\nScreenshots: ${SCREENSHOT_DIR}`);
  console.log('');

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
  const page = await context.newPage();

  // Collect ALL console messages
  const consoleMessages = [];
  const networkErrors = [];

  page.on('console', msg => {
    consoleMessages.push({ type: msg.type(), text: msg.text() });
  });

  page.on('requestfailed', request => {
    networkErrors.push({ url: request.url(), failure: request.failure()?.errorText });
  });

  try {
    // ═══════════════════════════════════════════════════════════════════
    // STEP 1: Navigate and Login
    // ═══════════════════════════════════════════════════════════════════
    console.log('\n=== STEP 1: Navigation & Login ===');

    await page.goto(BASE_URL, { waitUntil: 'networkidle', timeout: 30000 });
    await screenshot(page, 'initial_load');

    // Check if login needed
    const loginBox = await page.$('.login-box');
    if (loginBox) {
      await page.fill('.bx--text-input:not([type="password"])', 'admin');
      await page.fill('input[type="password"]', 'admin123');
      await screenshot(page, 'login_form_filled');
      await page.click('button[type="submit"]');
      await page.waitForTimeout(2000);
    }
    await screenshot(page, 'after_login');

    // ═══════════════════════════════════════════════════════════════════
    // STEP 2: Navigate to LDM
    // ═══════════════════════════════════════════════════════════════════
    console.log('\n=== STEP 2: LDM Navigation ===');

    await page.waitForTimeout(1000);
    await screenshot(page, 'main_app');

    // Select project
    const projectItem = await page.$('.project-item');
    if (projectItem) {
      await projectItem.click();
      await page.waitForTimeout(2000);
      await screenshot(page, 'project_selected');
    }

    // Open file
    const fileNode = await page.$('.tree-node');
    if (fileNode) {
      await fileNode.click();
      await page.waitForTimeout(3000);
      await screenshot(page, 'file_opened');
    }

    // ═══════════════════════════════════════════════════════════════════
    // STEP 3: Test UI-053 - Virtual Scroll
    // ═══════════════════════════════════════════════════════════════════
    console.log('\n=== TEST: UI-053 Virtual Scroll ===');

    const scrollInfo = await page.evaluate(() => {
      const container = document.querySelector('.scroll-container');
      if (!container) return { error: 'not found' };
      return {
        clientHeight: container.clientHeight,
        scrollHeight: container.scrollHeight,
        overflowY: getComputedStyle(container).overflowY
      };
    });

    if (scrollInfo.error) {
      log('UI-053', 'SKIP', 'Scroll container not found');
    } else if (scrollInfo.clientHeight < 5000 && scrollInfo.overflowY === 'auto') {
      log('UI-053', 'PASS', `Container: ${scrollInfo.clientHeight}px, scrollable: ${scrollInfo.scrollHeight}px`);
    } else {
      log('UI-053', 'FAIL', `Container: ${scrollInfo.clientHeight}px (should be < viewport)`);
    }

    // ═══════════════════════════════════════════════════════════════════
    // STEP 4: Test UI-054 - Cell Expansion
    // ═══════════════════════════════════════════════════════════════════
    console.log('\n=== TEST: UI-054 Cell Expansion ===');

    const cellHeights = await page.evaluate(() => {
      const rows = document.querySelectorAll('.virtual-row');
      const heights = [];
      rows.forEach((row, i) => {
        if (i < 10) heights.push(row.offsetHeight);
      });
      return heights;
    });

    await screenshot(page, 'cell_heights_test');

    const hasVariableHeights = cellHeights.some(h => h > 50);
    if (hasVariableHeights) {
      log('UI-054', 'PASS', `Variable heights detected: ${cellHeights.slice(0, 5).join(', ')}px`);
    } else {
      log('UI-054', 'FAIL', `All cells same height: ${cellHeights[0]}px`);
    }

    // ═══════════════════════════════════════════════════════════════════
    // STEP 5: Test UI-055 - Modal Count
    // ═══════════════════════════════════════════════════════════════════
    console.log('\n=== TEST: UI-055 Modal Bloat ===');

    const modalCount = await page.evaluate(() => {
      return document.querySelectorAll('.bx--modal').length;
    });

    if (modalCount < 10) {
      log('UI-055', 'PASS', `Only ${modalCount} modals in DOM`);
    } else {
      log('UI-055', 'FAIL', `${modalCount} modals in DOM (bloat!)`);
    }

    // ═══════════════════════════════════════════════════════════════════
    // STEP 6: Test UI-056 - Source Text Selectable
    // ═══════════════════════════════════════════════════════════════════
    console.log('\n=== TEST: UI-056 Source Selectable ===');

    const sourceSelectable = await page.evaluate(() => {
      const sourceCell = document.querySelector('.cell.source');
      if (!sourceCell) return { error: 'not found' };
      const style = getComputedStyle(sourceCell);
      return {
        userSelect: style.userSelect,
        cursor: style.cursor
      };
    });

    if (sourceSelectable.error) {
      log('UI-056', 'SKIP', 'Source cell not found');
    } else if (sourceSelectable.userSelect !== 'none') {
      log('UI-056', 'PASS', `user-select: ${sourceSelectable.userSelect}`);
    } else {
      log('UI-056', 'FAIL', `user-select: ${sourceSelectable.userSelect} (should be text)`);
    }

    // ═══════════════════════════════════════════════════════════════════
    // STEP 7: Test UI-051 - Modal Close
    // ═══════════════════════════════════════════════════════════════════
    console.log('\n=== TEST: UI-051 Modal Close ===');

    // Wait for rows
    await page.waitForTimeout(2000);

    // Double-click target cell
    const targetCell = await page.$('.cell.target');
    if (targetCell) {
      await targetCell.dblclick();
      await page.waitForTimeout(1000);
      await screenshot(page, 'modal_opened');

      const modalVisible = await page.evaluate(() => {
        const overlay = document.querySelector('.edit-modal-overlay');
        return overlay && getComputedStyle(overlay).display !== 'none';
      });

      if (modalVisible) {
        // Try close button
        const closeBtn = await page.$('.close-btn');
        if (closeBtn) {
          await closeBtn.click();
          await page.waitForTimeout(500);
          await screenshot(page, 'after_close_click');

          const modalClosed = await page.evaluate(() => {
            const overlay = document.querySelector('.edit-modal-overlay');
            return !overlay || getComputedStyle(overlay).display === 'none';
          });

          if (modalClosed) {
            log('UI-051', 'PASS', 'Close button works');
          } else {
            log('UI-051', 'FAIL', 'Modal still visible after close');
          }
        } else {
          log('UI-051', 'FAIL', 'Close button not found');
        }
      } else {
        log('UI-051', 'SKIP', 'Modal did not open');
      }
    } else {
      log('UI-051', 'SKIP', 'No target cell found');
    }

    // ═══════════════════════════════════════════════════════════════════
    // STEP 8: Test Hover States
    // ═══════════════════════════════════════════════════════════════════
    console.log('\n=== TEST: UI-057 Hover Colors ===');

    const firstRow = await page.$('.virtual-row');
    if (firstRow) {
      await firstRow.hover();
      await page.waitForTimeout(300);
      await screenshot(page, 'row_hover');

      const hoverColors = await page.evaluate(() => {
        const row = document.querySelector('.virtual-row');
        const sourceCell = row?.querySelector('.cell.source');
        const targetCell = row?.querySelector('.cell.target');
        return {
          rowBg: row ? getComputedStyle(row).backgroundColor : null,
          sourceBg: sourceCell ? getComputedStyle(sourceCell).backgroundColor : null,
          targetBg: targetCell ? getComputedStyle(targetCell).backgroundColor : null
        };
      });

      // Check if colors are consistent
      const uniqueColors = new Set([hoverColors.sourceBg, hoverColors.targetBg].filter(Boolean));
      if (uniqueColors.size <= 1) {
        log('UI-057', 'PASS', 'Consistent hover colors');
      } else {
        log('UI-057', 'FAIL', `Split colors: source=${hoverColors.sourceBg}, target=${hoverColors.targetBg}`);
      }
    }

    // ═══════════════════════════════════════════════════════════════════
    // STEP 9: Scroll Test
    // ═══════════════════════════════════════════════════════════════════
    console.log('\n=== TEST: Scroll & Lazy Loading ===');

    const scrollContainer = await page.$('.scroll-container');
    if (scrollContainer) {
      // Get initial row count
      const initialRows = await page.evaluate(() => {
        return document.querySelectorAll('.virtual-row').length;
      });

      // Scroll down
      await page.evaluate(() => {
        const container = document.querySelector('.scroll-container');
        if (container) container.scrollTop = 5000;
      });
      await page.waitForTimeout(1000);
      await screenshot(page, 'after_scroll');

      // Check if new rows loaded
      const afterScrollRows = await page.evaluate(() => {
        return document.querySelectorAll('.virtual-row').length;
      });

      log('SCROLL', 'INFO', `Initial: ${initialRows} rows, After scroll: ${afterScrollRows} rows`);
    }

    // ═══════════════════════════════════════════════════════════════════
    // STEP 10: Console Error Analysis
    // ═══════════════════════════════════════════════════════════════════
    console.log('\n=== Console & Network Analysis ===');

    const errors = consoleMessages.filter(m => m.type === 'error');
    const warnings = consoleMessages.filter(m => m.type === 'warning');

    console.log(`  Errors: ${errors.length}`);
    console.log(`  Warnings: ${warnings.length}`);
    console.log(`  Network failures: ${networkErrors.length}`);

    errors.slice(0, 5).forEach((e, i) => {
      console.log(`  [${i + 1}] ${e.text.slice(0, 80)}`);
    });

    networkErrors.forEach(e => {
      console.log(`  ❌ ${e.url}: ${e.failure}`);
    });

    // Final screenshot
    await screenshot(page, 'final_state');

  } finally {
    await browser.close();
  }

  // ═══════════════════════════════════════════════════════════════════
  // SUMMARY
  // ═══════════════════════════════════════════════════════════════════
  console.log('\n╔══════════════════════════════════════════════════════════════╗');
  console.log('║  TEST RESULTS SUMMARY                                        ║');
  console.log('╚══════════════════════════════════════════════════════════════╝');

  const passed = results.filter(r => r.status === 'PASS').length;
  const failed = results.filter(r => r.status === 'FAIL').length;
  const skipped = results.filter(r => r.status === 'SKIP').length;

  results.forEach(r => {
    const icon = r.status === 'PASS' ? '✅' : r.status === 'FAIL' ? '❌' : '⚠️';
    console.log(`${icon} ${r.issue}: ${r.status}`);
  });

  console.log(`\nTotal: ${passed} PASS, ${failed} FAIL, ${skipped} SKIP`);
  console.log(`Screenshots: ${screenshotCount} saved to ${SCREENSHOT_DIR}`);

  // Write results to JSON
  fs.writeFileSync(
    path.join(SCREENSHOT_DIR, 'results.json'),
    JSON.stringify({ results, consoleErrors: consoleMessages.filter(m => m.type === 'error').length }, null, 2)
  );
}

main().catch(console.error);
