#!/usr/bin/env node
/**
 * Test BUG-037: QA Panel X button closes properly
 */

const http = require('http');
const WebSocket = require('ws');

const sleep = ms => new Promise(r => setTimeout(r, ms));

async function main() {
    console.log('=== TEST: BUG-037 (QA Panel X Button) ===\n');

    const targets = await new Promise((resolve, reject) => {
        http.get('http://127.0.0.1:9222/json', (res) => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => resolve(JSON.parse(data)));
        }).on('error', reject);
    });
    const page = targets.find(t => t.type === 'page');
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

    // Step 1: Expand project and click on a file
    console.log('STEP 1: Click on project to expand...');
    const expandProject = await evaluate(`
        (async () => {
            // Find QA Test Project
            const items = document.querySelectorAll('[class*="tree"], [role="treeitem"], .project-item, button, span');
            for (const item of items) {
                const text = item.innerText?.trim() || '';
                if (text.includes('QA Test Project')) {
                    item.click();
                    await new Promise(r => setTimeout(r, 1000));
                    return 'Clicked: ' + text.substring(0, 30);
                }
            }
            return 'Project not found';
        })()
    `);
    console.log('  Result:', expandProject);
    await sleep(1500);

    // Step 2: Click on a file - find the tree-item-content element
    console.log('\nSTEP 2: Click on test file...');
    const clickFile = await evaluate(`
        (async () => {
            // Look for tree-item-content that contains test_10k.txt
            const treeContents = document.querySelectorAll('.tree-item-content, [class*="tree-item"]');
            for (const item of treeContents) {
                const text = item.textContent?.trim();
                if (text && text.includes('test_10k.txt') && !text.includes('Project')) {
                    // Click on the item
                    item.click();
                    await new Promise(r => setTimeout(r, 2000));
                    return 'Clicked tree item: ' + text.substring(0, 30);
                }
            }

            // Try finding span with just the filename
            const spans = document.querySelectorAll('span');
            for (const span of spans) {
                if (span.textContent.trim() === 'test_10k.txt') {
                    span.click();
                    await new Promise(r => setTimeout(r, 2000));
                    return 'Clicked span: test_10k.txt';
                }
            }

            // Last resort: look for any clickable element with the filename
            const allEls = document.querySelectorAll('button, div[role="button"], li, [tabindex]');
            for (const el of allEls) {
                const text = el.textContent?.trim();
                if (text === 'test_10k.txt') {
                    el.click();
                    await new Promise(r => setTimeout(r, 2000));
                    return 'Clicked element: ' + el.tagName;
                }
            }

            return 'File not found';
        })()
    `);
    console.log('  Result:', clickFile);
    await sleep(3000);

    // Verify file loaded (check for grid rows)
    const fileLoaded = await evaluate(`
        document.querySelectorAll('[class*="row"]').length > 10 ||
        document.body.innerText.includes('Source') ||
        document.body.innerText.includes('Target')
    `);
    console.log('  File loaded:', fileLoaded);

    if (!fileLoaded) {
        console.log('\n⚠️ File not loaded, cannot test QA panel');
        ws.close();
        process.exit(1);
    }

    // Step 3: Click QA MENU button (just "QA", NOT "QA Off" or "QA On")
    console.log('\nSTEP 3: Click QA menu button to open panel...');
    const openQA = await evaluate(`
        (async () => {
            const buttons = document.querySelectorAll('button');
            // Find the button that says exactly "QA" (not "QA Off" or "QA On")
            for (const btn of buttons) {
                const text = btn.innerText?.trim();
                if (text === 'QA') {
                    // Make sure it's not the toggle (which says "QA Off" or "QA On")
                    if (!btn.closest('[class*="tree"]') && !btn.closest('[class*="explorer"]')) {
                        btn.click();
                        await new Promise(r => setTimeout(r, 1500));
                        return 'Clicked QA menu button';
                    }
                }
            }
            // Try by aria-label "QA Report"
            const qaBtn = document.querySelector('button[aria-label="QA Report"]');
            if (qaBtn) {
                qaBtn.click();
                await new Promise(r => setTimeout(r, 1500));
                return 'Clicked QA Report button';
            }
            return 'QA menu button not found';
        })()
    `);
    console.log('  Result:', openQA);
    await sleep(1500);

    // Step 4: Verify panel opened
    console.log('\nSTEP 4: Verify QA panel opened...');
    const panelOpen = await evaluate(`
        (function() {
            const body = document.body.innerText;
            const hasRunFullQA = body.includes('Run Full QA');
            const hasQAReport = body.includes('QA Report');

            // Look for panel element
            const panel = document.querySelector('.qa-panel, [class*="qa-panel"], [class*="slide-panel"]');
            const panelVisible = panel && panel.offsetParent !== null;

            return {
                hasRunFullQA,
                hasQAReport,
                panelVisible,
                isOpen: hasRunFullQA || hasQAReport || panelVisible
            };
        })()
    `);
    console.log('  Has "Run Full QA":', panelOpen?.hasRunFullQA);
    console.log('  Has "QA Report":', panelOpen?.hasQAReport);
    console.log('  Panel visible:', panelOpen?.panelVisible);
    console.log('  Is open:', panelOpen?.isOpen);

    if (!panelOpen?.isOpen) {
        console.log('\n⚠️ QA Panel did not open');
        console.log('  Page content:', await evaluate('document.body.innerText.substring(0, 500)'));
        ws.close();
        process.exit(1);
    }

    // Step 5: Click close button (X) - must be in the QA panel header
    console.log('\nSTEP 5: Click X button to close panel...');
    const closePanel = await evaluate(`
        (async () => {
            // The QA panel has class "qa-panel" and a header with class "qa-panel-header"
            const panel = document.querySelector('.qa-panel');
            if (!panel) {
                return { clicked: false, error: 'QA panel not found' };
            }

            // Find the header
            const header = panel.querySelector('.qa-panel-header');
            if (!header) {
                return { clicked: false, error: 'QA panel header not found' };
            }

            // Find the close button in header - should be a ghost button with Close icon
            const closeBtn = header.querySelector('button.bx--btn--ghost') ||
                            header.querySelector('button[aria-label="Close"]') ||
                            header.querySelector('button');

            if (closeBtn) {
                console.log('Found close button:', closeBtn.className);
                closeBtn.click();
                await new Promise(r => setTimeout(r, 1000));
                return { clicked: true, method: closeBtn.className || 'button', text: closeBtn.innerText };
            }

            // Fallback: look for any button with SVG icon in header
            const headerBtns = header.querySelectorAll('button');
            for (const btn of headerBtns) {
                if (btn.querySelector('svg')) {
                    btn.click();
                    await new Promise(r => setTimeout(r, 1000));
                    return { clicked: true, method: 'svg button', class: btn.className };
                }
            }

            return { clicked: false, error: 'Close button not found in header' };
        })()
    `);
    console.log('  Clicked:', closePanel?.clicked);
    console.log('  Method:', closePanel?.method || closePanel?.error);
    await sleep(1000);

    // Step 6: Verify panel closed
    console.log('\nSTEP 6: Verify panel closed...');
    const panelClosed = await evaluate(`
        (function() {
            const body = document.body.innerText;
            const stillHasQA = body.includes('Run Full QA') || body.includes('QA Report');
            return { closed: !stillHasQA };
        })()
    `);
    console.log('  Panel closed:', panelClosed?.closed);

    // Summary
    console.log('\n=== RESULT ===');
    const passed = panelOpen?.isOpen && closePanel?.clicked && panelClosed?.closed;
    console.log('BUG-037 (QA X button):', passed ? '✅ PASS' : '❌ FAIL');

    if (!passed) {
        console.log('\nDebug info:');
        console.log('  Panel opened:', panelOpen?.isOpen);
        console.log('  Close clicked:', closePanel?.clicked);
        console.log('  Panel closed:', panelClosed?.closed);
    }

    ws.close();
    process.exit(passed ? 0 : 1);
}

main().catch(err => {
    console.error('Error:', err);
    process.exit(1);
});
