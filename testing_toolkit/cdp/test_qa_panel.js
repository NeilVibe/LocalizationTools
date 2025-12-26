#!/usr/bin/env node
/**
 * Test BUG-037: QA Panel X button closes properly
 */

const http = require('http');
const WebSocket = require('ws');

const sleep = ms => new Promise(r => setTimeout(r, ms));

async function main() {
    console.log('=== TEST: BUG-037 (QA Panel X Button) ===\n');

    // Get target
    const targets = await new Promise((resolve, reject) => {
        http.get('http://127.0.0.1:9222/json', (res) => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => resolve(JSON.parse(data)));
        }).on('error', reject);
    });
    const page = targets.find(t => t.type === 'page' && t.url.includes('index.html'));
    if (!page) { console.log('ERROR: No page found'); process.exit(1); }

    const ws = new WebSocket(page.webSocketDebuggerUrl);
    let msgId = 1;

    const send = (method, params = {}) => new Promise((resolve) => {
        const id = msgId++;
        const handler = (data) => {
            const msg = JSON.parse(data.toString());
            if (msg.id === id) { ws.off('message', handler); resolve(msg.result); }
        };
        ws.on('message', handler);
        ws.send(JSON.stringify({ id, method, params }));
    });

    const evaluate = async (expr) => {
        const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
        return r.result?.value;
    };

    await new Promise(r => ws.on('open', r));
    await send('Runtime.enable');

    // Step 1: Click on test_10k.txt file using ldmTest
    console.log('STEP 1: Open file using ldmTest...');
    const clickFile = await evaluate(`
        (async () => {
            // Use the test interface if available
            if (window.ldmTest && typeof window.ldmTest.selectFile === 'function') {
                await window.ldmTest.selectFile('test_10k.txt');
                return 'Used ldmTest.selectFile';
            }

            // Fallback: click on file in tree
            const fileItems = document.querySelectorAll('[role="treeitem"], .tree-item, .file-item');
            for (const item of fileItems) {
                const text = item.innerText;
                if (text.includes('test_10k.txt') && !text.includes('Project')) {
                    item.click();
                    await new Promise(r => setTimeout(r, 1500));
                    return 'Clicked file item';
                }
            }

            // Click any item that has .txt
            const allElements = document.querySelectorAll('div, span, li');
            for (const el of allElements) {
                const text = el.innerText.trim();
                if (text === 'test_10k.txt') {
                    el.click();
                    await new Promise(r => setTimeout(r, 1500));
                    return 'Clicked text element';
                }
            }

            return 'File click failed';
        })()
    `);
    console.log('  Result:', clickFile);
    await sleep(2000);

    // Step 2: Verify file is loaded
    console.log('\nSTEP 2: Verify file loaded...');
    const fileLoaded = await evaluate(`
        (function() {
            const rows = document.querySelectorAll('.virtual-row, .grid-row, [class*="row"]');
            const rowCount = Array.from(rows).filter(r => r.className.includes('row')).length;
            return { rowCount: rowCount, loaded: rowCount > 10 };
        })()
    `);
    console.log('  Rows:', fileLoaded?.rowCount);
    console.log('  Loaded:', fileLoaded?.loaded);

    if (!fileLoaded?.loaded) {
        console.log('\n⚠️ File not loaded, cannot test QA panel');
        ws.close();
        process.exit(1);
    }

    // Step 3: Click QA button in TOOLBAR (not sidebar)
    console.log('\nSTEP 3: Open QA Panel (toolbar button)...');
    const openQA = await evaluate(`
        (async () => {
            // The QA button should be in the toolbar area on the right side
            // It usually says "QA" or "QA Off"
            // Avoid clicking on project names that contain "QA"

            // Look for buttons in the main content area (not sidebar)
            const mainContent = document.querySelector('.main-content, main, [class*="content"]') || document.body;
            const buttons = mainContent.querySelectorAll('button');

            for (const btn of buttons) {
                const text = btn.innerText.trim();
                // Match exactly "QA" or "QA Off" or "QA On"
                if (text === 'QA' || text === 'QA Off' || text === 'QA On') {
                    // Make sure it's not in a tree/project list
                    const parent = btn.closest('.tree, .file-explorer, .sidebar, .project-list');
                    if (!parent) {
                        btn.click();
                        await new Promise(r => setTimeout(r, 1000));
                        return 'Clicked toolbar QA button: ' + text;
                    }
                }
            }

            // Fallback: look for QA in toolbar/actions area
            const toolbar = document.querySelector('.toolbar, .actions, [class*="toolbar"], [class*="action"]');
            if (toolbar) {
                const toolbarBtns = toolbar.querySelectorAll('button');
                for (const btn of toolbarBtns) {
                    if (btn.innerText.includes('QA')) {
                        btn.click();
                        await new Promise(r => setTimeout(r, 1000));
                        return 'Clicked QA in toolbar';
                    }
                }
            }

            return 'QA button not found in toolbar';
        })()
    `);
    console.log('  Result:', openQA);
    await sleep(1000);

    // Step 4: Check panel opened
    console.log('\nSTEP 4: Verify panel opened...');
    const panelOpen = await evaluate(`
        (function() {
            // Check for QA-specific content
            const body = document.body.innerText;
            const hasRunFullQA = body.includes('Run Full QA');
            const hasQAIssues = body.includes('QA Issues') || body.includes('Pattern') && body.includes('Character');

            // Look for visible panel
            const panels = document.querySelectorAll('.qa-menu-panel, .slide-panel, [class*="qa-panel"], [class*="menu-panel"], .panel');
            let visiblePanel = null;
            for (const p of panels) {
                if (p.offsetParent !== null && p.offsetWidth > 50) {
                    visiblePanel = p;
                    break;
                }
            }

            return {
                panelVisible: !!visiblePanel,
                hasRunFullQA: hasRunFullQA,
                hasQAIssues: hasQAIssues,
                isOpen: hasRunFullQA || hasQAIssues || !!visiblePanel
            };
        })()
    `);
    console.log('  Panel visible:', panelOpen?.panelVisible);
    console.log('  Has "Run Full QA":', panelOpen?.hasRunFullQA);
    console.log('  Is open:', panelOpen?.isOpen);

    if (!panelOpen?.isOpen) {
        console.log('\n⚠️ QA Panel did not open');
        ws.close();
        process.exit(1);
    }

    // Step 5: Click X to close
    console.log('\nSTEP 5: Click X button to close...');
    const closePanel = await evaluate(`
        (async () => {
            // Find close button - usually has × or close aria-label
            const closeButtons = document.querySelectorAll(
                'button[aria-label*="lose"], button[aria-label*="Close"], ' +
                '.close-button, .close-btn, button:has(svg[data-icon="close"])'
            );

            if (closeButtons.length > 0) {
                closeButtons[0].click();
                await new Promise(r => setTimeout(r, 500));
                return { clicked: true, method: 'aria-label/class' };
            }

            // Look in panel for first button (usually close)
            const panel = document.querySelector('.qa-menu-panel, .slide-panel, [class*="qa-panel"]');
            if (panel) {
                const header = panel.querySelector('.panel-header, [class*="header"]');
                if (header) {
                    const btn = header.querySelector('button');
                    if (btn) {
                        btn.click();
                        await new Promise(r => setTimeout(r, 500));
                        return { clicked: true, method: 'panel header button' };
                    }
                }
            }

            return { clicked: false, error: 'No close button found' };
        })()
    `);
    console.log('  Clicked:', closePanel?.clicked);
    console.log('  Method:', closePanel?.method);
    await sleep(500);

    // Step 6: Verify panel closed
    console.log('\nSTEP 6: Verify panel closed...');
    const panelClosed = await evaluate(`
        (function() {
            const body = document.body.innerText;
            const hasRunFullQA = body.includes('Run Full QA');
            return { closed: !hasRunFullQA };
        })()
    `);
    console.log('  Panel closed:', panelClosed?.closed);

    // Summary
    console.log('\n=== RESULT ===');
    const passed = panelOpen?.isOpen && closePanel?.clicked && panelClosed?.closed;
    console.log('BUG-037 (QA X button):', passed ? '✅ PASS' : '❌ FAIL');

    ws.close();
    process.exit(passed ? 0 : 1);
}

main().catch(err => {
    console.error('Error:', err);
    process.exit(1);
});
