#!/usr/bin/env node
/**
 * Verify bug fixes - BUG-037, PERF-003
 * Run from Windows PowerShell
 */

const http = require('http');
const WebSocket = require('ws');

const sleep = ms => new Promise(r => setTimeout(r, ms));

async function getTarget() {
    return new Promise((resolve, reject) => {
        http.get('http://127.0.0.1:9222/json', (res) => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => {
                const targets = JSON.parse(data);
                resolve(targets.find(t => t.type === 'page' && t.url.includes('index.html')));
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
                const msg = JSON.parse(data.toString());
                if (msg.id === id) {
                    ws.off('message', handler);
                    resolve(msg.result);
                }
            };
            ws.on('message', handler);
            ws.send(JSON.stringify({ id, method, params }));
        });
    };

    const evaluate = async (expression) => {
        const result = await send('Runtime.evaluate', {
            expression,
            returnByValue: true,
            awaitPromise: true
        });
        return result.result?.value;
    };

    await new Promise(r => ws.on('open', r));
    await send('Runtime.enable');

    // Step 1: Navigate to LDM and click on a project
    console.log('STEP 1: Navigate to project...');
    const nav1 = await evaluate(`
        (async () => {
            // Click on first project in sidebar
            const items = document.querySelectorAll('.file-explorer-item, .project-item, [data-testid="project-item"]');
            if (items.length === 0) {
                // Try clicking on any expandable item in the tree
                const treeItems = document.querySelectorAll('[role="treeitem"], .tree-item');
                if (treeItems.length > 0) {
                    treeItems[0].click();
                    await new Promise(r => setTimeout(r, 500));
                    return 'Clicked tree item: ' + treeItems[0].innerText.substring(0, 30);
                }
            } else {
                items[0].click();
                await new Promise(r => setTimeout(r, 500));
                return 'Clicked project: ' + items[0].innerText.substring(0, 30);
            }
            return 'No project items found';
        })()
    `);
    console.log('  Result:', nav1);

    await sleep(1000);

    // Step 2: Look for files and click one
    console.log('\nSTEP 2: Click on a file...');
    const nav2 = await evaluate(`
        (async () => {
            // Look for file items (usually have .txt, .xml, .xliff extension in text)
            const allItems = document.querySelectorAll('.tree-item, .file-item, [role="treeitem"]');
            for (const item of allItems) {
                const text = item.innerText || '';
                if (text.includes('.txt') || text.includes('.xml') || text.includes('10k') || text.includes('10K')) {
                    item.click();
                    await new Promise(r => setTimeout(r, 1500));
                    return 'Clicked file: ' + text.substring(0, 40);
                }
            }
            // If no file found, just click second tree item
            if (allItems.length > 1) {
                allItems[1].click();
                await new Promise(r => setTimeout(r, 1500));
                return 'Clicked item 2: ' + allItems[1].innerText.substring(0, 40);
            }
            return 'No files found';
        })()
    `);
    console.log('  Result:', nav2);

    await sleep(2000);

    // Step 3: Check if VirtualGrid loaded (PERF-003)
    console.log('\n=== TEST: PERF-003 (Lazy Loading) ===');
    const lazyLoadCheck = await evaluate(`
        (function() {
            const grid = document.querySelector('.virtual-scroll-container, .virtual-grid, [class*="virtual"]');
            const rows = document.querySelectorAll('.virtual-row, .grid-row, [class*="row"]');
            const container = document.querySelector('.virtual-container');

            // Check if we have rows loaded
            const rowCount = rows.length;
            const containerHeight = container?.style?.height || 'N/A';

            // Check body text for row content
            const hasGridContent = document.body.innerText.includes('Source') ||
                                   document.body.innerText.includes('Target') ||
                                   document.body.innerText.includes('StringId');

            return {
                hasGrid: !!grid,
                rowCount: rowCount,
                containerHeight: containerHeight,
                hasGridContent: hasGridContent,
                lazyLoadOK: rowCount > 0 && rowCount < 500 // Not loading ALL rows
            };
        })()
    `);
    console.log('  Grid found:', lazyLoadCheck?.hasGrid);
    console.log('  Rows loaded:', lazyLoadCheck?.rowCount);
    console.log('  Has grid content:', lazyLoadCheck?.hasGridContent);
    console.log('  Lazy load OK:', lazyLoadCheck?.lazyLoadOK ? 'YES (< 500 rows)' : 'Need more data');

    // Step 4: Test QA Panel (BUG-037)
    console.log('\n=== TEST: BUG-037 (QA Panel X Button) ===');

    // First, find and click QA button
    const openQA = await evaluate(`
        (async () => {
            // Find QA button - could be in toolbar or sidebar
            const buttons = document.querySelectorAll('button');
            let qaBtn = null;
            for (const btn of buttons) {
                const text = btn.innerText || btn.getAttribute('aria-label') || '';
                if (text.includes('QA') && !text.includes('Off')) {
                    qaBtn = btn;
                    break;
                }
            }
            if (!qaBtn) {
                // Try finding by looking for QA in toolbar area
                const toolbar = document.querySelector('.toolbar, .actions, [class*="tool"]');
                if (toolbar) {
                    const btns = toolbar.querySelectorAll('button');
                    for (const btn of btns) {
                        if (btn.innerText.includes('QA')) {
                            qaBtn = btn;
                            break;
                        }
                    }
                }
            }
            if (qaBtn) {
                qaBtn.click();
                await new Promise(r => setTimeout(r, 800));
                return 'Clicked QA button';
            }
            return 'QA button not found';
        })()
    `);
    console.log('  Open QA:', openQA);

    await sleep(1000);

    // Check if panel opened
    const panelCheck = await evaluate(`
        (function() {
            const panel = document.querySelector('.qa-menu-panel, .qa-panel, .slide-panel, [class*="qa-menu"]');
            if (panel) {
                const isVisible = panel.offsetParent !== null &&
                                  getComputedStyle(panel).display !== 'none' &&
                                  getComputedStyle(panel).visibility !== 'hidden';
                return { found: true, visible: isVisible, classes: panel.className };
            }
            return { found: false, visible: false };
        })()
    `);
    console.log('  Panel found:', panelCheck?.found);
    console.log('  Panel visible:', panelCheck?.visible);

    // Now click the X button to close
    const closeResult = await evaluate(`
        (async () => {
            const panel = document.querySelector('.qa-menu-panel, .qa-panel, .slide-panel, [class*="qa-menu"]');
            if (!panel) return { error: 'Panel not found' };

            // Look for close button (usually has X or close icon)
            const closeBtn = panel.querySelector('button[aria-label*="lose"]') ||
                            panel.querySelector('button[aria-label*="Close"]') ||
                            panel.querySelector('.close-btn, .close-button') ||
                            panel.querySelector('button:has(svg[data-icon="close"])');

            // Fallback: find first button in header area
            if (!closeBtn) {
                const header = panel.querySelector('.panel-header, header, [class*="header"]');
                if (header) {
                    const headerBtns = header.querySelectorAll('button');
                    if (headerBtns.length > 0) {
                        headerBtns[0].click();
                        await new Promise(r => setTimeout(r, 500));

                        // Check if closed
                        const panelAfter = document.querySelector('.qa-menu-panel, .qa-panel, .slide-panel, [class*="qa-menu"]');
                        const stillVisible = panelAfter && panelAfter.offsetParent !== null;
                        return { clicked: 'header button', closed: !stillVisible };
                    }
                }
            }

            if (closeBtn) {
                closeBtn.click();
                await new Promise(r => setTimeout(r, 500));

                // Check if closed
                const panelAfter = document.querySelector('.qa-menu-panel, .qa-panel, .slide-panel, [class*="qa-menu"]');
                const stillVisible = panelAfter && panelAfter.offsetParent !== null;
                return { clicked: 'close button', closed: !stillVisible };
            }

            return { error: 'Close button not found' };
        })()
    `);
    console.log('  Close action:', closeResult?.clicked || closeResult?.error);
    console.log('  Panel closed:', closeResult?.closed);

    // Summary
    console.log('\n=== SUMMARY ===');
    const perf003Pass = lazyLoadCheck?.rowCount > 0 && lazyLoadCheck?.rowCount < 500;
    const bug037Pass = closeResult?.closed === true;

    console.log('PERF-003 (Lazy loading):', perf003Pass ? '✅ PASS' : '⚠️ NEEDS FILE OPEN');
    console.log('BUG-037 (QA X button):', bug037Pass ? '✅ PASS' : (panelCheck?.found ? '❌ FAIL' : '⚠️ PANEL NOT FOUND'));

    ws.close();
    process.exit(bug037Pass && perf003Pass ? 0 : 1);
}

runTest().catch(err => {
    console.error('Test error:', err);
    process.exit(1);
});
