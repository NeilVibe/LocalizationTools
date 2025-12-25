/**
 * Full QA Test with Complete Console Capture
 *
 * This test:
 * 1. Opens a file in the grid
 * 2. Clicks QA button to open panel
 * 3. Runs Full QA check
 * 4. Captures ALL console messages (errors, warnings, logs)
 * 5. Reports everything found
 */
const WebSocket = require('ws');
const http = require('http');

const sleep = ms => new Promise(r => setTimeout(r, ms));

const TEST_USER = process.env.CDP_TEST_USER;
const TEST_PASS = process.env.CDP_TEST_PASS;

if (!TEST_USER || !TEST_PASS) {
    console.error('ERROR: CDP_TEST_USER and CDP_TEST_PASS required');
    process.exit(1);
}

async function main() {
    console.log('╔══════════════════════════════════════════════════════════════╗');
    console.log('║  FULL QA TEST WITH CONSOLE CAPTURE                           ║');
    console.log('╚══════════════════════════════════════════════════════════════╝\n');

    // Connect to CDP
    const targets = await new Promise((resolve, reject) => {
        http.get('http://127.0.0.1:9222/json', (res) => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => resolve(JSON.parse(data)));
        }).on('error', reject);
    });

    const page = targets.find(t => t.type === 'page');
    if (!page) {
        console.log('ERROR: No page found');
        process.exit(1);
    }

    const ws = new WebSocket(page.webSocketDebuggerUrl);
    let id = 1;

    // Collect ALL console messages
    const consoleMessages = [];
    const consoleErrors = [];
    const consoleWarnings = [];
    const exceptions = [];

    const send = (method, params = {}) => new Promise(resolve => {
        const msgId = id++;
        const handler = (msg) => {
            const r = JSON.parse(msg.toString());
            if (r.id === msgId) { ws.off('message', handler); resolve(r); }
        };
        ws.on('message', handler);
        ws.send(JSON.stringify({ id: msgId, method, params }));
    });

    const evaluate = async (expr) => {
        const r = await send('Runtime.evaluate', {
            expression: expr,
            returnByValue: true,
            awaitPromise: true
        });
        return r.result?.result?.value;
    };

    await new Promise(resolve => ws.on('open', resolve));

    // Enable ALL logging domains
    await send('Console.enable');
    await send('Runtime.enable');
    await send('Log.enable');

    // Listen for ALL console events
    ws.on('message', (data) => {
        const msg = JSON.parse(data.toString());

        // Console.messageAdded (older API)
        if (msg.method === 'Console.messageAdded') {
            const entry = msg.params.message;
            const record = {
                level: entry.level,
                text: entry.text,
                source: entry.source,
                url: entry.url,
                line: entry.line
            };
            consoleMessages.push(record);
            if (entry.level === 'error') consoleErrors.push(record);
            if (entry.level === 'warning') consoleWarnings.push(record);
        }

        // Runtime.consoleAPICalled (newer API)
        if (msg.method === 'Runtime.consoleAPICalled') {
            const args = msg.params.args.map(a => a.value || a.description || JSON.stringify(a)).join(' ');
            const record = {
                level: msg.params.type,
                text: args,
                stackTrace: msg.params.stackTrace
            };
            consoleMessages.push(record);
            if (msg.params.type === 'error') consoleErrors.push(record);
            if (msg.params.type === 'warning') consoleWarnings.push(record);
        }

        // Runtime.exceptionThrown (JS exceptions)
        if (msg.method === 'Runtime.exceptionThrown') {
            const ex = msg.params.exceptionDetails;
            const record = {
                text: ex.exception?.description || ex.text,
                url: ex.url,
                line: ex.lineNumber,
                column: ex.columnNumber,
                stackTrace: ex.stackTrace
            };
            exceptions.push(record);
            consoleErrors.push({ level: 'exception', ...record });
        }

        // Log.entryAdded (browser logs)
        if (msg.method === 'Log.entryAdded') {
            const entry = msg.params.entry;
            if (entry.level === 'error' || entry.level === 'warning') {
                consoleMessages.push({
                    level: entry.level,
                    text: entry.text,
                    source: 'browser'
                });
                if (entry.level === 'error') consoleErrors.push({ level: 'browser-error', text: entry.text });
            }
        }
    });

    // STEP 1: Check current state
    console.log('[STEP 1] Checking current state...');
    const bodyText = await evaluate('document.body.innerText.substring(0, 500)');

    if (bodyText.includes('Login')) {
        console.log('  → Not logged in, logging in...');
        await evaluate(`document.querySelectorAll('input')[0].value = '${TEST_USER}'; document.querySelectorAll('input')[0].dispatchEvent(new Event('input', {bubbles:true}))`);
        await evaluate(`document.querySelector('input[type="password"]').value = '${TEST_PASS}'; document.querySelector('input[type="password"]').dispatchEvent(new Event('input', {bubbles:true}))`);
        await sleep(300);
        await evaluate(`Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Login'))?.click()`);
        await sleep(3000);
        console.log('  → Logged in');
    } else {
        console.log('  → Already logged in');
    }

    // STEP 2: Navigate to Files and select project
    console.log('\n[STEP 2] Navigating to Files tab...');
    await evaluate(`Array.from(document.querySelectorAll('button')).find(b => b.textContent.trim() === 'Files')?.click()`);
    await sleep(1000);

    // STEP 3: Click on first project
    console.log('\n[STEP 3] Selecting project...');
    const projectClicked = await evaluate(`
        const projects = document.querySelectorAll('.project-item, [class*="project-name"], .tree-item');
        if (projects.length > 0) {
            projects[0].click();
            'clicked: ' + projects[0].textContent.trim().substring(0, 50);
        } else {
            'no projects found';
        }
    `);
    console.log('  →', projectClicked);
    await sleep(1500);

    // STEP 4: Click on first file to load it
    console.log('\n[STEP 4] Selecting file to load...');
    const fileClicked = await evaluate(`
        const files = document.querySelectorAll('.tree-node, .file-item, [class*="file-name"]');
        for (const f of files) {
            if (f.textContent.includes('.txt') || f.textContent.includes('.xliff') || f.textContent.includes('10k')) {
                f.click();
                return 'clicked: ' + f.textContent.trim().substring(0, 50);
            }
        }
        if (files.length > 0) {
            files[0].click();
            return 'clicked first: ' + files[0].textContent.trim().substring(0, 50);
        }
        return 'no files found';
    `);
    console.log('  →', fileClicked);
    await sleep(3000); // Wait for file to load

    // STEP 5: Check if grid loaded
    console.log('\n[STEP 5] Checking if grid loaded...');
    const gridState = await evaluate(`
        const grid = document.querySelector('.virtual-grid, [class*="grid"], [class*="VirtualGrid"]');
        const rows = document.querySelectorAll('.grid-row, [class*="row"]');
        JSON.stringify({
            hasGrid: !!grid,
            rowCount: rows.length,
            bodyPreview: document.body.innerText.substring(0, 300)
        })
    `);
    const grid = JSON.parse(gridState || '{}');
    console.log('  → Grid present:', grid.hasGrid);
    console.log('  → Rows visible:', grid.rowCount);

    // STEP 6: Click QA button to open panel
    console.log('\n[STEP 6] Opening QA panel...');
    const qaButtonClicked = await evaluate(`
        // Try different QA button selectors
        const qaBtn = Array.from(document.querySelectorAll('button')).find(b =>
            b.textContent.includes('QA Off') ||
            b.textContent.includes('QA On') ||
            b.textContent === 'QA'
        );
        if (qaBtn) {
            qaBtn.click();
            'clicked: ' + qaBtn.textContent.trim();
        } else {
            'QA button not found';
        }
    `);
    console.log('  →', qaButtonClicked);
    await sleep(2000);

    // STEP 7: Look for QA panel and Run Full QA button
    console.log('\n[STEP 7] Looking for Run Full QA button...');
    const runQAResult = await evaluate(`
        // Find the QA panel
        const panel = document.querySelector('[class*="QAMenuPanel"], [class*="qa-panel"], [class*="slide-panel"]');

        // Find Run Full QA button
        const runBtn = Array.from(document.querySelectorAll('button')).find(b =>
            b.textContent.includes('Run Full QA') ||
            b.textContent.includes('Run QA') ||
            b.textContent.includes('Check All')
        );

        if (runBtn) {
            runBtn.click();
            'clicked: ' + runBtn.textContent.trim();
        } else {
            // List all buttons for debugging
            const allBtns = Array.from(document.querySelectorAll('button')).map(b => b.textContent.trim()).filter(t => t.length > 0 && t.length < 30);
            'Run QA button not found. Available buttons: ' + allBtns.join(', ');
        }
    `);
    console.log('  →', runQAResult);

    // Wait for QA to complete
    console.log('\n[STEP 8] Waiting for QA to complete (10 seconds)...');
    await sleep(10000);

    // STEP 9: Check QA results
    console.log('\n[STEP 9] Checking QA results...');
    const qaResults = await evaluate(`
        // Look for QA issue count or results
        const issueElements = document.querySelectorAll('[class*="issue"], [class*="qa-result"], [class*="error-count"]');
        const bodyText = document.body.innerText;

        // Extract any numbers that might be issue counts
        const issueMatch = bodyText.match(/(\\d+)\\s*(issues?|errors?|warnings?)/i);

        JSON.stringify({
            issueElements: issueElements.length,
            issueMatch: issueMatch ? issueMatch[0] : null,
            hasQAPanel: !!document.querySelector('[class*="QA"]'),
            relevantText: bodyText.match(/QA[^]*?(\\d+[^]*?(issue|error|warning|pattern|line|term))/i)?.[0]?.substring(0, 200)
        })
    `);
    const results = JSON.parse(qaResults || '{}');
    console.log('  → Issue elements found:', results.issueElements);
    console.log('  → Issue match:', results.issueMatch);
    console.log('  → QA panel present:', results.hasQAPanel);
    if (results.relevantText) {
        console.log('  → QA text:', results.relevantText);
    }

    // Wait a bit more for any delayed errors
    await sleep(2000);

    // FINAL REPORT
    console.log('\n╔══════════════════════════════════════════════════════════════╗');
    console.log('║  CONSOLE CAPTURE REPORT                                       ║');
    console.log('╚══════════════════════════════════════════════════════════════╝\n');

    console.log(`Total messages captured: ${consoleMessages.length}`);
    console.log(`  - Errors: ${consoleErrors.length}`);
    console.log(`  - Warnings: ${consoleWarnings.length}`);
    console.log(`  - Exceptions: ${exceptions.length}`);

    if (consoleErrors.length > 0) {
        console.log('\n=== ERRORS ===');
        consoleErrors.forEach((err, i) => {
            console.log(`\n[ERROR ${i + 1}] ${err.level || 'error'}`);
            console.log(`  Text: ${err.text?.substring(0, 200)}`);
            if (err.url) console.log(`  URL: ${err.url}`);
            if (err.line) console.log(`  Line: ${err.line}`);
        });
    } else {
        console.log('\n✅ NO ERRORS DETECTED');
    }

    if (consoleWarnings.length > 0) {
        console.log('\n=== WARNINGS ===');
        consoleWarnings.slice(0, 10).forEach((warn, i) => {
            console.log(`[WARN ${i + 1}] ${warn.text?.substring(0, 100)}`);
        });
        if (consoleWarnings.length > 10) {
            console.log(`  ... and ${consoleWarnings.length - 10} more warnings`);
        }
    }

    if (exceptions.length > 0) {
        console.log('\n=== EXCEPTIONS ===');
        exceptions.forEach((ex, i) => {
            console.log(`\n[EXCEPTION ${i + 1}]`);
            console.log(`  ${ex.text}`);
            if (ex.stackTrace?.callFrames) {
                ex.stackTrace.callFrames.slice(0, 3).forEach(frame => {
                    console.log(`    at ${frame.functionName || '(anonymous)'} (${frame.url}:${frame.lineNumber})`);
                });
            }
        });
    }

    // Check for specific BUG-035 error
    const hasBug035 = consoleErrors.some(e =>
        e.text?.includes("Cannot read properties of undefined") &&
        e.text?.includes("'id'")
    );

    console.log('\n╔══════════════════════════════════════════════════════════════╗');
    console.log('║  BUG-035 CHECK                                                ║');
    console.log('╚══════════════════════════════════════════════════════════════╝');
    if (hasBug035) {
        console.log('\n❌ BUG-035 DETECTED: "Cannot read properties of undefined (reading \'id\')"');
    } else {
        console.log('\n✅ BUG-035 NOT DETECTED');
    }

    ws.close();
    console.log('\n=== TEST COMPLETE ===');

    // Exit with error code if errors found
    process.exit(consoleErrors.length > 0 ? 1 : 0);
}

main().catch(e => {
    console.error('FATAL:', e.message);
    process.exit(1);
});
