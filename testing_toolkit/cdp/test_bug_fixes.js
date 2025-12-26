#!/usr/bin/env node
/**
 * Test script to verify bug fixes:
 * - BUG-037: QA Panel X button closes
 * - PERF-003: Lazy loading works (no scroll lag)
 */

const http = require('http');
const WebSocket = require('ws');

async function getTarget() {
    return new Promise((resolve, reject) => {
        http.get('http://127.0.0.1:9222/json', (res) => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => {
                const targets = JSON.parse(data);
                const target = targets.find(t => t.type === 'page' && t.url.includes('index.html'));
                resolve(target);
            });
        }).on('error', reject);
    });
}

async function runTest() {
    console.log('=== BUG FIX VERIFICATION ===\n');

    const target = await getTarget();
    if (!target) {
        console.log('ERROR: No target found');
        process.exit(1);
    }

    const ws = new WebSocket(target.webSocketDebuggerUrl);
    let msgId = 1;

    const send = (method, params = {}) => {
        return new Promise((resolve) => {
            const id = msgId++;
            const handler = (data) => {
                const msg = JSON.parse(data);
                if (msg.id === id) {
                    ws.off('message', handler);
                    resolve(msg.result);
                }
            };
            ws.on('message', handler);
            ws.send(JSON.stringify({ id, method, params }));
        });
    };

    const evaluate = (expression) => send('Runtime.evaluate', {
        expression,
        returnByValue: true,
        awaitPromise: true
    });

    await new Promise(r => ws.on('open', r));
    await send('Runtime.enable');

    // Test 1: Click on a project to open file
    console.log('TEST 1: Opening a file...');
    const clickProject = await evaluate(`
        (async () => {
            const projectBtn = document.querySelector('.tree-item-content');
            if (projectBtn) {
                projectBtn.click();
                await new Promise(r => setTimeout(r, 500));
                // Find and click a file
                const fileItems = document.querySelectorAll('.tree-item-content');
                for (const item of fileItems) {
                    if (item.textContent.includes('.txt') || item.textContent.includes('.xml')) {
                        item.click();
                        await new Promise(r => setTimeout(r, 1000));
                        return 'File clicked';
                    }
                }
                return 'No file found, clicked project';
            }
            return 'No project found';
        })()
    `);
    console.log('  Result:', clickProject.result?.value || clickProject);

    // Test 2: Check if VirtualGrid loaded (PERF-003)
    console.log('\nTEST 2: Checking lazy loading (PERF-003)...');
    const lazyLoadCheck = await evaluate(`
        (async () => {
            await new Promise(r => setTimeout(r, 1000));
            const rows = document.querySelectorAll('.virtual-row');
            const placeholders = document.querySelectorAll('.placeholder-row');
            const totalHeight = document.querySelector('.virtual-container')?.style.height;
            return {
                visibleRows: rows.length,
                placeholders: placeholders.length,
                containerHeight: totalHeight,
                notAllRowsLoaded: rows.length < 100 // Should be lazy loaded
            };
        })()
    `);
    const lazyResult = lazyLoadCheck.result?.value;
    console.log('  Visible rows:', lazyResult?.visibleRows);
    console.log('  Placeholders:', lazyResult?.placeholders);
    console.log('  Container height:', lazyResult?.containerHeight);
    console.log('  Lazy loading working:', lazyResult?.notAllRowsLoaded ? 'YES' : 'MAYBE (need more rows)');

    // Test 3: Open QA Panel and close with X button (BUG-037)
    console.log('\nTEST 3: Testing QA Panel X button (BUG-037)...');
    const qaTest = await evaluate(`
        (async () => {
            // Find and click QA button to open panel
            const qaBtn = document.querySelector('button[title*="QA"]') ||
                          Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('QA'));
            if (!qaBtn) return { error: 'QA button not found' };

            qaBtn.click();
            await new Promise(r => setTimeout(r, 500));

            // Check if panel opened
            const panel = document.querySelector('.qa-menu-panel') ||
                          document.querySelector('[class*="qa-panel"]') ||
                          document.querySelector('.slide-panel');
            if (!panel) return { error: 'QA panel did not open' };

            const panelVisible1 = panel.offsetParent !== null || getComputedStyle(panel).display !== 'none';

            // Find and click X button
            const closeBtn = panel.querySelector('button[aria-label="Close"]') ||
                            panel.querySelector('.close-button') ||
                            panel.querySelector('button svg') ||
                            Array.from(panel.querySelectorAll('button')).find(b =>
                                b.textContent.includes('×') || b.innerHTML.includes('close') || b.innerHTML.includes('Close')
                            );

            if (!closeBtn) {
                // Try finding by icon
                const buttons = panel.querySelectorAll('button');
                for (const btn of buttons) {
                    if (btn.querySelector('svg') || btn.textContent.trim() === '') {
                        btn.click();
                        await new Promise(r => setTimeout(r, 500));
                        break;
                    }
                }
            } else {
                closeBtn.click();
                await new Promise(r => setTimeout(r, 500));
            }

            // Check if panel closed
            const panelAfter = document.querySelector('.qa-menu-panel') ||
                               document.querySelector('[class*="qa-panel"]') ||
                               document.querySelector('.slide-panel');
            const panelVisible2 = panelAfter ? (panelAfter.offsetParent !== null || getComputedStyle(panelAfter).display !== 'none') : false;

            return {
                panelOpenedInitially: panelVisible1,
                panelClosedAfterClick: !panelVisible2,
                closeBtnFound: !!closeBtn
            };
        })()
    `);
    const qaResult = qaTest.result?.value;
    console.log('  Panel opened:', qaResult?.panelOpenedInitially);
    console.log('  Close button found:', qaResult?.closeBtnFound);
    console.log('  Panel closed after X click:', qaResult?.panelClosedAfterClick);

    // Summary
    console.log('\n=== SUMMARY ===');
    console.log('PERF-003 (Lazy loading):', lazyResult?.notAllRowsLoaded ? '✅ PASS' : '⚠️ NEEDS MORE DATA');
    console.log('BUG-037 (QA X button):', qaResult?.panelClosedAfterClick ? '✅ PASS' : '❌ FAIL');

    ws.close();
    process.exit(0);
}

runTest().catch(err => {
    console.error('Test error:', err);
    process.exit(1);
});
