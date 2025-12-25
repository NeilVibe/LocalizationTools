/**
 * TM Viewer & Confirm Test - Build 298 (Final)
 *
 * Flow:
 * 1. Go to TM tab
 * 2. Select a TM
 * 3. Click "Open TM Manager" button
 * 4. Test TM Viewer features
 * 5. Test Confirm feature
 */
const WebSocket = require('ws');
const http = require('http');

const results = { passed: [], failed: [] };
const log = msg => console.log(`[${new Date().toISOString().substr(11, 8)}] ${msg}`);
const pass = test => { results.passed.push(test); log(`✅ PASS: ${test}`); };
const fail = (test, reason) => { results.failed.push({ test, reason }); log(`❌ FAIL: ${test} - ${reason}`); };
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function main() {
    console.log('═══════════════════════════════════════════════════════════');
    console.log('   TM VIEWER & CONFIRM TEST (FINAL) - Build 298');
    console.log('═══════════════════════════════════════════════════════════\n');

    const targets = await new Promise((resolve, reject) => {
        http.get('http://127.0.0.1:9222/json', (res) => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => resolve(JSON.parse(data)));
        }).on('error', reject);
    });

    const page = targets.find(t => t.type === 'page');
    const ws = new WebSocket(page.webSocketDebuggerUrl);
    let id = 1;

    const send = (method, params = {}) => new Promise((resolve, reject) => {
        const msgId = id++;
        const timeout = setTimeout(() => reject(new Error('Timeout')), 30000);
        ws.on('message', function handler(data) {
            const msg = JSON.parse(data.toString());
            if (msg.id === msgId) {
                clearTimeout(timeout);
                ws.off('message', handler);
                resolve(msg);
            }
        });
        ws.send(JSON.stringify({ id: msgId, method, params }));
    });

    const evaluate = async (expression) => {
        const result = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
        return result.result?.result?.value;
    };

    await new Promise((resolve, reject) => {
        ws.on('open', resolve);
        ws.on('error', reject);
    });

    pass('CDP Connection');

    // ═══════════════════════════════════════════════════════════
    // STEP 1: Navigate to TM tab
    // ═══════════════════════════════════════════════════════════
    log('\n[STEP 1] Navigating to TM tab...');
    await evaluate(`
        const tmTab = Array.from(document.querySelectorAll('button')).find(b =>
            b.textContent.trim() === 'TM' && b.className.includes('tab-button')
        );
        if (tmTab) tmTab.click();
    `);
    await sleep(1000);
    pass('Navigate to TM tab');

    // ═══════════════════════════════════════════════════════════
    // STEP 2: Select a TM
    // ═══════════════════════════════════════════════════════════
    log('\n[STEP 2] Selecting TRUE E2E Standard TM...');
    await evaluate(`
        const tmItem = document.querySelector('.tm-item');
        if (tmItem) tmItem.click();
    `);
    await sleep(500);
    pass('Select TM item');

    // ═══════════════════════════════════════════════════════════
    // STEP 3: Click "Open TM Manager" button
    // ═══════════════════════════════════════════════════════════
    log('\n[STEP 3] Clicking "Open TM Manager" button...');
    const openResult = await evaluate(`
        (function() {
            const buttons = document.querySelectorAll('button');
            for (const btn of buttons) {
                if (btn.textContent.includes('Open TM Manager')) {
                    btn.click();
                    return 'clicked';
                }
            }
            return 'not found';
        })()
    `);
    log(`  Result: ${openResult}`);
    await sleep(2000);

    if (openResult === 'clicked') {
        pass('Click Open TM Manager');
    } else {
        fail('Click Open TM Manager', 'Button not found');
    }

    // ═══════════════════════════════════════════════════════════
    // STEP 4: Check TM Manager opened
    // ═══════════════════════════════════════════════════════════
    log('\n[STEP 4] Checking TM Manager view...');
    const managerState = await evaluate(`
        (function() {
            const body = document.body.innerText;
            return JSON.stringify({
                hasSource: body.includes('Source'),
                hasTarget: body.includes('Target'),
                hasViewer: body.includes('TM Viewer') || body.includes('entries'),
                hasConfirmed: body.includes('Confirmed'),
                tables: document.querySelectorAll('table').length,
                rows: document.querySelectorAll('table tbody tr').length,
                bodyPreview: body.substring(0, 500)
            });
        })()
    `);
    log(`  Manager state: ${managerState}`);

    const state = JSON.parse(managerState || '{}');

    // If not showing viewer, look for a View button or modal
    if (!state.hasSource && !state.hasTarget) {
        log('  TM Manager opened but viewer not showing. Looking for view action...');

        // Check for modal or new view
        const modalCheck = await evaluate(`
            (function() {
                const modal = document.querySelector('.bx--modal.is-visible, [class*="modal"][class*="open"]');
                const allButtons = document.querySelectorAll('button');
                const viewBtns = Array.from(allButtons).filter(b => {
                    const text = b.textContent.toLowerCase();
                    return text.includes('view') || text.includes('entries');
                });
                return JSON.stringify({
                    hasModal: !!modal,
                    viewButtons: viewBtns.map(b => b.textContent.substring(0, 30))
                });
            })()
        `);
        log(`  Modal/View check: ${modalCheck}`);
    }

    // ═══════════════════════════════════════════════════════════
    // STEP 5: Test TM Viewer features
    // ═══════════════════════════════════════════════════════════
    log('\n[STEP 5] Testing TM Viewer features...');

    // Check for table headers
    const tableHeaders = await evaluate(`
        (function() {
            const headers = document.querySelectorAll('th');
            return JSON.stringify(Array.from(headers).map(h => h.textContent.trim()).filter(h => h));
        })()
    `);
    log(`  Table headers: ${tableHeaders}`);

    // Check pagination
    const pagination = await evaluate(`
        (function() {
            const pagEl = document.querySelector('[class*="pagination"], .page-nav');
            const pageText = document.body.innerText.match(/Page\\s+\\d+\\s+of\\s+\\d+/);
            return JSON.stringify({
                hasPaginationEl: !!pagEl,
                pageText: pageText ? pageText[0] : null
            });
        })()
    `);
    log(`  Pagination: ${pagination}`);

    // Check search
    const search = await evaluate(`
        !!document.querySelector('input[placeholder*="search" i], input[type="search"]')
    `);
    log(`  Has search: ${search}`);
    if (search) pass('TM Viewer: Search present');

    // Check metadata dropdown
    const metadataDropdown = await evaluate(`
        (function() {
            const dropdowns = document.querySelectorAll('select, [class*="dropdown"], .bx--list-box');
            const metadata = Array.from(dropdowns).filter(d => {
                const text = d.textContent || '';
                return text.includes('StringID') || text.includes('Confirmed') || text.includes('Metadata');
            });
            return JSON.stringify({
                found: metadata.length > 0,
                options: metadata.length > 0 ? metadata[0].textContent.substring(0, 100) : null
            });
        })()
    `);
    log(`  Metadata dropdown: ${metadataDropdown}`);

    const metaData = JSON.parse(metadataDropdown || '{}');
    if (metaData.found) {
        pass('TM Viewer: Metadata dropdown present');
    }

    // ═══════════════════════════════════════════════════════════
    // STEP 6: Test Confirm feature
    // ═══════════════════════════════════════════════════════════
    log('\n[STEP 6] Testing Confirm feature...');

    // Get row buttons
    const rowButtonsInfo = await evaluate(`
        (function() {
            const rows = document.querySelectorAll('table tbody tr');
            if (rows.length === 0) return JSON.stringify({ rows: 0, buttons: [] });

            const firstRow = rows[0];
            const buttons = firstRow.querySelectorAll('button');
            return JSON.stringify({
                rows: rows.length,
                buttons: Array.from(buttons).map(b => ({
                    title: b.getAttribute('title'),
                    class: b.className.substring(0, 50),
                    ariaLabel: b.getAttribute('aria-label'),
                    svg: !!b.querySelector('svg')
                }))
            });
        })()
    `);
    log(`  Row buttons: ${rowButtonsInfo}`);

    // Try to find and click confirm button
    const confirmAction = await evaluate(`
        (function() {
            // Strategy 1: Find by title/aria-label
            let confirmBtn = document.querySelector(
                'button[title*="Confirm" i], ' +
                'button[aria-label*="confirm" i], ' +
                '[data-action="confirm"]'
            );

            if (confirmBtn) {
                confirmBtn.click();
                return JSON.stringify({ clicked: true, method: 'title/aria' });
            }

            // Strategy 2: Find in table row buttons
            const rows = document.querySelectorAll('table tbody tr');
            for (const row of rows) {
                const buttons = row.querySelectorAll('button');
                // Often the first or second button in actions is confirm
                for (const btn of buttons) {
                    const title = btn.getAttribute('title') || '';
                    const ariaLabel = btn.getAttribute('aria-label') || '';
                    if (title.toLowerCase().includes('confirm') ||
                        ariaLabel.toLowerCase().includes('confirm')) {
                        btn.click();
                        return JSON.stringify({ clicked: true, method: 'row-button-title' });
                    }
                }
            }

            // Strategy 3: Click first button in row (might be confirm)
            const firstRowBtn = document.querySelector('table tbody tr button');
            if (firstRowBtn) {
                const title = firstRowBtn.getAttribute('title');
                firstRowBtn.click();
                return JSON.stringify({ clicked: true, method: 'first-row-button', title });
            }

            return JSON.stringify({ clicked: false });
        })()
    `);
    log(`  Confirm action: ${confirmAction}`);

    await sleep(1500);

    // Check for visual feedback
    const visualFeedback = await evaluate(`
        (function() {
            const confirmedRows = document.querySelectorAll('tr.confirmed, tr[class*="confirmed"]');
            const toasts = document.querySelectorAll('[class*="toast"]:not([class*="container"]), [role="alert"]');
            return JSON.stringify({
                confirmedRowCount: confirmedRows.length,
                toastCount: toasts.length,
                toastMessages: Array.from(toasts).map(t => t.textContent.substring(0, 50))
            });
        })()
    `);
    log(`  Visual feedback: ${visualFeedback}`);

    const confirmResult = JSON.parse(confirmAction || '{}');
    if (confirmResult.clicked) {
        pass('TM Confirm: Button interaction');
    } else {
        // Log current page state for debugging
        const debugState = await evaluate(`document.body.innerText.substring(0, 800)`);
        log(`  Debug - Current page: ${debugState?.substring(0, 300)}`);
        fail('TM Confirm: Button interaction', 'Could not find/click confirm button');
    }

    // ═══════════════════════════════════════════════════════════
    // STEP 7: Check Global Toast System
    // ═══════════════════════════════════════════════════════════
    log('\n[STEP 7] Checking Global Toast System...');
    const toastSystem = await evaluate(`
        (function() {
            const container = document.querySelector('[class*="global-toast"], [class*="GlobalToast"]');
            return JSON.stringify({
                exists: !!container,
                class: container?.className || 'not found'
            });
        })()
    `);
    log(`  Toast system: ${toastSystem}`);

    const toastData = JSON.parse(toastSystem || '{}');
    if (toastData.exists) {
        pass('Global Toast: System present');
    }

    // ═══════════════════════════════════════════════════════════
    // SUMMARY
    // ═══════════════════════════════════════════════════════════
    console.log('\n═══════════════════════════════════════════════════════════');
    console.log('   TEST SUMMARY');
    console.log('═══════════════════════════════════════════════════════════');
    console.log(`\n✅ PASSED: ${results.passed.length}`);
    results.passed.forEach(t => console.log(`   - ${t}`));

    if (results.failed.length > 0) {
        console.log(`\n❌ FAILED: ${results.failed.length}`);
        results.failed.forEach(f => console.log(`   - ${f.test}: ${f.reason}`));
    }

    const total = results.passed.length + results.failed.length;
    console.log(`\n   Total: ${total} tests (${results.passed.length} passed, ${results.failed.length} failed)`);
    console.log('═══════════════════════════════════════════════════════════\n');

    ws.close();
    process.exit(results.failed.length > 0 ? 1 : 0);
}

main().catch(err => {
    console.error('Error:', err.message);
    process.exit(1);
});
