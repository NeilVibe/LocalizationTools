/**
 * DETAILED Full Flow Test: Project → File → Double-click Row → Modal Opens
 *
 * This is the VERBOSE version that logs EVERYTHING:
 * - Every DOM query with selector and result
 * - Every click with coordinates
 * - Every wait with duration
 * - Console messages from the app
 * - All alerts intercepted
 * - Timing for each step
 *
 * Use this for debugging complex issues.
 * For quick checks, use test_full_flow.js instead.
 */

const http = require('http');
const WebSocket = require('ws');

// Test configuration
const CDP_PORT = 9222;
const LOG_LEVEL = 'DETAILED'; // 'NORMAL' or 'DETAILED'

// Timing tracker
const timings = [];
let testStartTime;

// Colors for console
const colors = {
    reset: '\x1b[0m',
    bright: '\x1b[1m',
    green: '\x1b[32m',
    yellow: '\x1b[33m',
    red: '\x1b[31m',
    cyan: '\x1b[36m',
    gray: '\x1b[90m'
};

// Detailed logger
function log(level, message, data = null) {
    const timestamp = Date.now() - testStartTime;
    const prefix = `[${timestamp.toString().padStart(6)}ms]`;

    if (level === 'STEP') {
        console.log(`\n${colors.bright}${colors.cyan}${prefix} ═══ ${message} ═══${colors.reset}`);
    } else if (level === 'OK') {
        console.log(`${colors.gray}${prefix}${colors.reset} ${colors.green}✓${colors.reset} ${message}`);
    } else if (level === 'FAIL') {
        console.log(`${colors.gray}${prefix}${colors.reset} ${colors.red}✗${colors.reset} ${message}`);
    } else if (level === 'WARN') {
        console.log(`${colors.gray}${prefix}${colors.reset} ${colors.yellow}⚠${colors.reset} ${message}`);
    } else if (level === 'DEBUG') {
        if (LOG_LEVEL === 'DETAILED') {
            console.log(`${colors.gray}${prefix}   → ${message}${colors.reset}`);
        }
    } else if (level === 'DATA') {
        if (LOG_LEVEL === 'DETAILED' && data) {
            console.log(`${colors.gray}${prefix}     ${JSON.stringify(data, null, 2).split('\n').join('\n' + ' '.repeat(14))}${colors.reset}`);
        }
    } else {
        console.log(`${colors.gray}${prefix}${colors.reset}   ${message}`);
    }

    timings.push({ timestamp, level, message });
}

// Helper: Send CDP command with detailed logging
function send(ws, id, method, params) {
    return new Promise((resolve, reject) => {
        log('DEBUG', `CDP Command: ${method}`);
        if (Object.keys(params).length > 0) {
            log('DATA', null, params);
        }

        const startTime = Date.now();
        const timeout = setTimeout(() => {
            log('WARN', `Timeout after 10s on ${method}`);
            resolve({ error: 'timeout', method });
        }, 10000);

        const handler = (data) => {
            const msg = JSON.parse(data);
            if (msg.id === id) {
                clearTimeout(timeout);
                ws.removeListener('message', handler);
                const elapsed = Date.now() - startTime;
                log('DEBUG', `CDP Response in ${elapsed}ms`);
                resolve(msg);
            }
        };
        ws.on('message', handler);
        ws.send(JSON.stringify({ id, method, params }));
    });
}

// Helper: Wait with logging
function wait(ms) {
    log('DEBUG', `Waiting ${ms}ms...`);
    return new Promise(resolve => setTimeout(resolve, ms));
}

// Helper: Evaluate JS with detailed logging
async function evaluate(ws, id, expression, description = '') {
    if (description) {
        log('DEBUG', `Evaluating: ${description}`);
    }
    log('DEBUG', `Expression: ${expression.substring(0, 100)}${expression.length > 100 ? '...' : ''}`);

    const result = await send(ws, id, 'Runtime.evaluate', {
        expression,
        returnByValue: true,
        awaitPromise: true
    });

    const value = result.result?.result?.value;
    if (value !== undefined) {
        log('DEBUG', `Result: ${typeof value === 'string' ? value.substring(0, 200) : value}`);
    }

    return value;
}

// Helper: Query DOM with detailed logging
async function queryDOM(ws, id, selector, description) {
    log('DEBUG', `DOM Query: "${selector}" (${description})`);

    const result = await evaluate(ws, id, `JSON.stringify({
        found: document.querySelectorAll('${selector}').length,
        first: document.querySelector('${selector}')?.tagName || null,
        text: document.querySelector('${selector}')?.textContent?.substring(0, 50) || null
    })`, description);

    const parsed = JSON.parse(result || '{}');
    log('DEBUG', `Found ${parsed.found} element(s)${parsed.first ? `, first: <${parsed.first}>` : ''}`);

    return parsed;
}

// Helper: Click element with detailed logging
async function clickElement(ws, id, selector, description) {
    log('DEBUG', `Click: "${selector}" (${description})`);

    const result = await evaluate(ws, id, `
        (function() {
            const el = document.querySelector('${selector}');
            if (!el) return JSON.stringify({ success: false, error: 'Element not found' });

            const rect = el.getBoundingClientRect();
            const info = {
                success: true,
                tag: el.tagName,
                class: el.className,
                text: el.textContent?.substring(0, 30),
                x: Math.round(rect.left + rect.width/2),
                y: Math.round(rect.top + rect.height/2),
                visible: rect.width > 0 && rect.height > 0
            };

            el.click();
            return JSON.stringify(info);
        })()
    `, description);

    const parsed = JSON.parse(result || '{}');
    if (parsed.success) {
        log('OK', `Clicked <${parsed.tag}> at (${parsed.x}, ${parsed.y}) - "${parsed.text}"`);
    } else {
        log('FAIL', `Click failed: ${parsed.error}`);
    }

    return parsed;
}

// Helper: Double-click element with detailed logging
async function doubleClickElement(ws, id, selector, description) {
    log('DEBUG', `Double-click: "${selector}" (${description})`);

    const result = await evaluate(ws, id, `
        (function() {
            const el = document.querySelector('${selector}');
            if (!el) return JSON.stringify({ success: false, error: 'Element not found' });

            const rect = el.getBoundingClientRect();
            const info = {
                success: true,
                tag: el.tagName,
                class: el.className,
                text: el.textContent?.substring(0, 30),
                x: Math.round(rect.left + rect.width/2),
                y: Math.round(rect.top + rect.height/2)
            };

            const event = new MouseEvent('dblclick', {
                bubbles: true,
                cancelable: true,
                view: window,
                clientX: info.x,
                clientY: info.y
            });
            el.dispatchEvent(event);

            return JSON.stringify(info);
        })()
    `, description);

    const parsed = JSON.parse(result || '{}');
    if (parsed.success) {
        log('OK', `Double-clicked <${parsed.tag}> at (${parsed.x}, ${parsed.y})`);
    } else {
        log('FAIL', `Double-click failed: ${parsed.error}`);
    }

    return parsed;
}

// Main test
async function runTest() {
    testStartTime = Date.now();

    console.log('');
    console.log('╔══════════════════════════════════════════════════════════════════╗');
    console.log('║     DETAILED FULL FLOW TEST - CDP Autonomous Testing             ║');
    console.log('║     Project → File → Double-click Row → Edit Modal               ║');
    console.log('╠══════════════════════════════════════════════════════════════════╣');
    console.log(`║     Log Level: ${LOG_LEVEL.padEnd(50)}║`);
    console.log(`║     Started: ${new Date().toISOString().padEnd(52)}║`);
    console.log('╚══════════════════════════════════════════════════════════════════╝');

    // ═══════════════════════════════════════════════════════════════════
    log('STEP', 'STEP 1: Connect to CDP');
    // ═══════════════════════════════════════════════════════════════════

    log('DEBUG', `Fetching targets from http://localhost:${CDP_PORT}/json`);

    const targets = await new Promise((resolve, reject) => {
        http.get(`http://localhost:${CDP_PORT}/json`, (res) => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => {
                log('DEBUG', `Received ${data.length} bytes`);
                resolve(JSON.parse(data));
            });
        }).on('error', (err) => {
            log('FAIL', `HTTP Error: ${err.message}`);
            reject(err);
        });
    });

    log('DEBUG', `Found ${targets.length} target(s)`);
    targets.forEach((t, i) => log('DEBUG', `  [${i}] ${t.type}: ${t.title || t.url}`));

    const page = targets.find(t => t.type === 'page');
    if (!page) {
        log('FAIL', 'No page target found. Is the app running with --remote-debugging-port=9222?');
        process.exit(1);
    }

    log('DEBUG', `Connecting to WebSocket: ${page.webSocketDebuggerUrl}`);
    const ws = new WebSocket(page.webSocketDebuggerUrl);
    let id = 1;

    await new Promise(resolve => ws.on('open', resolve));
    log('OK', 'Connected to CDP WebSocket');

    // Enable domains
    await send(ws, id++, 'Page.enable', {});
    await send(ws, id++, 'Runtime.enable', {});
    await send(ws, id++, 'Console.enable', {});
    log('OK', 'CDP domains enabled (Page, Runtime, Console)');

    // Listen for console messages
    ws.on('message', (data) => {
        const msg = JSON.parse(data);
        if (msg.method === 'Console.messageAdded') {
            log('DEBUG', `[Console] ${msg.params.message.level}: ${msg.params.message.text}`);
        }
    });

    // Intercept alerts
    await evaluate(ws, id++, `
        window.__alertMessages = [];
        window.__originalAlert = window.alert;
        window.alert = function(msg) {
            console.log('[ALERT INTERCEPTED]', msg);
            window.__alertMessages.push({ time: Date.now(), message: msg });
        };
    `, 'Install alert interceptor');
    log('OK', 'Alert interceptor installed');

    // ═══════════════════════════════════════════════════════════════════
    log('STEP', 'STEP 2: Check App State');
    // ═══════════════════════════════════════════════════════════════════

    const appState = await evaluate(ws, id++, `JSON.stringify({
        url: window.location.href,
        title: document.title,
        hasNavTest: typeof window.navTest !== 'undefined',
        hasLdmTest: typeof window.ldmTest !== 'undefined',
        navState: window.navTest?.getState?.() || null,
        bodyClasses: document.body.className,
        theme: document.documentElement.getAttribute('data-theme')
    })`, 'Get app state');

    const state = JSON.parse(appState || '{}');
    log('INFO', `URL: ${state.url}`);
    log('INFO', `Title: ${state.title}`);
    log('INFO', `Theme: ${state.theme || 'default'}`);
    log('INFO', `Nav State: ${JSON.stringify(state.navState)}`);
    log('INFO', `Test APIs: navTest=${state.hasNavTest}, ldmTest=${state.hasLdmTest}`);

    if (!state.navState?.authenticated) {
        log('FAIL', 'Not authenticated. Please login first.');
        ws.close();
        process.exit(1);
    }
    log('OK', 'User is authenticated');

    // ═══════════════════════════════════════════════════════════════════
    log('STEP', 'STEP 3: Navigate to LDM');
    // ═══════════════════════════════════════════════════════════════════

    await evaluate(ws, id++, `window.navTest.goToApp('ldm')`, 'Navigate to LDM');
    await wait(1000);

    const ldmCheck = await queryDOM(ws, id++, '.ldm-app', 'LDM app container');
    if (ldmCheck.found > 0) {
        log('OK', 'LDM app loaded');
    } else {
        log('FAIL', 'LDM app not found');
    }

    // ═══════════════════════════════════════════════════════════════════
    log('STEP', 'STEP 4: Select Project');
    // ═══════════════════════════════════════════════════════════════════

    const projects = await queryDOM(ws, id++, '.project-item', 'Project items');

    if (projects.found === 0) {
        log('WARN', 'No projects found, creating one...');
        await evaluate(ws, id++, `window.ldmTest.createProject()`, 'Create project');
        await wait(2000);
    } else {
        log('INFO', `Found ${projects.found} project(s)`);
        await clickElement(ws, id++, '.project-item', 'First project');
        await wait(500);
    }

    // ═══════════════════════════════════════════════════════════════════
    log('STEP', 'STEP 5: Select File');
    // ═══════════════════════════════════════════════════════════════════

    await wait(1000);
    const files = await queryDOM(ws, id++, '.bx--tree-node', 'Tree nodes');

    if (files.found === 0) {
        log('WARN', 'No files found, uploading one...');
        await evaluate(ws, id++, `window.ldmTest.uploadFile('uploadSmall')`, 'Upload file');
        await wait(3000);
        await evaluate(ws, id++, `window.ldmTest.selectFile()`, 'Select uploaded file');
        await wait(1000);
    } else {
        log('INFO', `Found ${files.found} tree node(s)`);
        await clickElement(ws, id++, '.bx--tree-node', 'First tree node');
        await wait(1000);
    }

    // ═══════════════════════════════════════════════════════════════════
    log('STEP', 'STEP 6: Verify Grid Loaded');
    // ═══════════════════════════════════════════════════════════════════

    await wait(2000);

    const gridState = await evaluate(ws, id++, `JSON.stringify({
        hasGrid: document.querySelector('.virtual-grid') !== null,
        hasScrollContainer: document.querySelector('.scroll-container') !== null,
        rowCount: document.querySelectorAll('.virtual-row').length,
        targetCells: document.querySelectorAll('.cell.target').length,
        sourceCells: document.querySelectorAll('.cell.source').length,
        totalRowsText: document.querySelector('.row-count')?.textContent,
        gridHeight: document.querySelector('.scroll-container')?.clientHeight,
        emptyState: document.querySelector('.empty-state')?.textContent
    })`, 'Get grid state');

    const grid = JSON.parse(gridState || '{}');
    log('INFO', `Grid present: ${grid.hasGrid}`);
    log('INFO', `Scroll container: ${grid.hasScrollContainer} (height: ${grid.gridHeight}px)`);
    log('INFO', `Visible rows: ${grid.rowCount}`);
    log('INFO', `Target cells: ${grid.targetCells}`);
    log('INFO', `Source cells: ${grid.sourceCells}`);
    log('INFO', `Total rows: ${grid.totalRowsText || 'N/A'}`);

    if (grid.emptyState) {
        log('WARN', `Empty state message: ${grid.emptyState}`);
    }

    if (grid.targetCells === 0) {
        log('FAIL', 'No target cells found in grid');
        ws.close();
        process.exit(1);
    }
    log('OK', `Grid loaded with ${grid.targetCells} editable cells`);

    // ═══════════════════════════════════════════════════════════════════
    log('STEP', 'STEP 7: Double-click Target Cell');
    // ═══════════════════════════════════════════════════════════════════

    // Check modal state before
    const modalBefore = await evaluate(ws, id++, `JSON.stringify({
        exists: document.querySelector('.bx--modal') !== null,
        visible: document.querySelector('.bx--modal.is-visible') !== null,
        count: document.querySelectorAll('.bx--modal').length
    })`, 'Check modal state before click');

    const before = JSON.parse(modalBefore || '{}');
    log('INFO', `Modals before: ${before.count} (visible: ${before.visible})`);

    // Double-click
    const clickResult = await doubleClickElement(ws, id++, '.cell.target', 'First target cell');

    if (!clickResult.success) {
        log('FAIL', 'Failed to double-click target cell');
        ws.close();
        process.exit(1);
    }

    await wait(1500);

    // ═══════════════════════════════════════════════════════════════════
    log('STEP', 'STEP 8: Verify Edit Modal Opened');
    // ═══════════════════════════════════════════════════════════════════

    const modalAfter = await evaluate(ws, id++, `JSON.stringify({
        exists: document.querySelector('.bx--modal') !== null,
        visible: document.querySelector('.bx--modal.is-visible') !== null,
        heading: document.querySelector('.bx--modal.is-visible .bx--modal-header__heading')?.textContent,
        hasTextArea: document.querySelector('.bx--modal.is-visible .bx--text-area') !== null,
        hasSourcePreview: document.querySelector('.bx--modal.is-visible .source-preview') !== null,
        hasSaveButton: document.querySelector('.bx--modal.is-visible .bx--btn--primary') !== null,
        modalClasses: document.querySelector('.bx--modal.is-visible')?.className
    })`, 'Check modal state after click');

    const after = JSON.parse(modalAfter || '{}');
    log('INFO', `Modal exists: ${after.exists}`);
    log('INFO', `Modal visible: ${after.visible}`);
    log('INFO', `Modal heading: ${after.heading || 'N/A'}`);
    log('INFO', `Has textarea: ${after.hasTextArea}`);
    log('INFO', `Has source preview: ${after.hasSourcePreview}`);
    log('INFO', `Has save button: ${after.hasSaveButton}`);

    // Check for any alerts
    const alerts = await evaluate(ws, id++, `JSON.stringify(window.__alertMessages || [])`, 'Get intercepted alerts');
    const alertList = JSON.parse(alerts || '[]');
    if (alertList.length > 0) {
        log('WARN', `Alerts captured: ${alertList.length}`);
        alertList.forEach(a => log('WARN', `  Alert: ${a.message}`));
    } else {
        log('OK', 'No alerts/errors captured');
    }

    // ═══════════════════════════════════════════════════════════════════
    // FINAL RESULT
    // ═══════════════════════════════════════════════════════════════════

    const totalTime = Date.now() - testStartTime;

    console.log('');
    console.log('╔══════════════════════════════════════════════════════════════════╗');

    if (after.visible && after.hasTextArea) {
        console.log('║                    ✅ TEST PASSED                                ║');
        console.log('║                                                                  ║');
        console.log('║     Edit modal opened successfully with all expected elements   ║');
    } else if (after.exists) {
        console.log('║                    ⚠️  TEST PARTIAL                              ║');
        console.log('║                                                                  ║');
        console.log('║     Modal exists but may not be fully functional                ║');
    } else {
        console.log('║                    ❌ TEST FAILED                                ║');
        console.log('║                                                                  ║');
        console.log('║     Edit modal did not open                                     ║');
    }

    console.log('╠══════════════════════════════════════════════════════════════════╣');
    console.log(`║     Total time: ${(totalTime/1000).toFixed(2)}s                                            ║`);
    console.log(`║     Steps completed: 8/8                                         ║`);
    console.log(`║     Alerts: ${alertList.length}                                                      ║`);
    console.log('╚══════════════════════════════════════════════════════════════════╝');
    console.log('');

    ws.close();
    process.exit(after.visible ? 0 : 1);
}

// Run
runTest().catch(err => {
    console.error('Test error:', err);
    process.exit(1);
});
