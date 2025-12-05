/**
 * Master Test Script - Full App Verification via CDP
 *
 * Tests: Auth, UI Components, Navigation, API, WebSocket
 *
 * Usage:
 *   1. Launch app: LocaNext.exe --remote-debugging-port=9222
 *   2. Wait 30 seconds for startup
 *   3. Run: node master_test.js
 */

const WebSocket = require('ws');

// Test results
const results = { passed: 0, failed: 0, tests: [] };

function log(msg) { console.log(`[${new Date().toISOString().slice(11,19)}] ${msg}`); }
function pass(name) { results.passed++; results.tests.push({ name, status: 'PASS' }); log(`  ✓ ${name}`); }
function fail(name, reason) { results.failed++; results.tests.push({ name, status: 'FAIL', reason }); log(`  ✗ ${name}: ${reason}`); }

async function wait(ms) { return new Promise(r => setTimeout(r, ms)); }

// Find the app page (not DevTools)
async function findAppPage() {
    const response = await fetch('http://localhost:9222/json');
    const pages = await response.json();
    return pages.find(p => p.type === 'page' && p.url.includes('file:') && !p.url.includes('devtools'));
}

async function cdpSend(ws, method, params = {}) {
    return new Promise((resolve, reject) => {
        const id = Math.floor(Math.random() * 10000);
        const timeout = setTimeout(() => reject(new Error('CDP timeout')), 10000);
        const handler = (data) => {
            const msg = JSON.parse(data.toString());
            if (msg.id === id) {
                clearTimeout(timeout);
                ws.off('message', handler);
                resolve(msg.result);
            }
        };
        ws.on('message', handler);
        ws.send(JSON.stringify({ id, method, params }));
    });
}

async function main() {
    log('='.repeat(60));
    log('MASTER TEST - Full App Verification');
    log('='.repeat(60));

    // 1. Find and connect to app page
    log('\n[1] Connecting to App via CDP...');
    let appPage;
    try {
        appPage = await findAppPage();
        if (appPage) {
            pass('Find app page');
            log(`    URL: ${appPage.url}`);
        } else {
            fail('Find app page', 'No app page found');
            return printResults();
        }
    } catch (e) {
        fail('CDP connection', e.message);
        return printResults();
    }

    const ws = new WebSocket(appPage.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => {
        ws.on('open', resolve);
        ws.on('error', reject);
        setTimeout(() => reject(new Error('WebSocket timeout')), 5000);
    });
    pass('WebSocket connected');

    // 2. Check Authentication
    log('\n[2] Checking Authentication...');
    try {
        const authResult = await cdpSend(ws, 'Runtime.evaluate', {
            expression: `JSON.stringify({
                hasAuthToken: !!localStorage.getItem('auth_token'),
                tokenLength: (localStorage.getItem('auth_token') || '').length
            })`,
            returnByValue: true
        });
        const auth = JSON.parse(authResult.result.value);
        if (auth.hasAuthToken && auth.tokenLength > 50) {
            pass(`Auth token present (${auth.tokenLength} chars)`);
        } else {
            fail('Auth token', `Token missing or too short (${auth.tokenLength})`);
        }
    } catch (e) {
        fail('Auth check', e.message);
    }

    // 3. Check Backend API
    log('\n[3] Testing Backend API...');
    try {
        const healthResponse = await fetch('http://127.0.0.1:8888/health');
        if (healthResponse.ok) pass('Backend /health');
        else fail('Backend /health', `Status ${healthResponse.status}`);
    } catch (e) {
        fail('Backend /health', e.message);
    }

    // 4. Check XLSTransfer UI
    log('\n[4] Checking XLSTransfer UI...');
    try {
        const uiResult = await cdpSend(ws, 'Runtime.evaluate', {
            expression: `JSON.stringify({
                hasContainer: !!document.querySelector('.xlstransfer-container'),
                hasButtonFrame: !!document.querySelector('.button-frame'),
                buttonCount: document.querySelectorAll('button').length,
                buttons: {
                    createDict: !!Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Create dictionary')),
                    loadDict: !!Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Load dictionary')),
                    transferClose: !!Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Transfer to Close')),
                    transferExcel: !!Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Transfer to Excel')),
                    checkNewlines: !!Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Check Newlines'))
                }
            })`,
            returnByValue: true
        });
        const ui = JSON.parse(uiResult.result.value);

        if (ui.hasContainer) pass('XLSTransfer container');
        else fail('XLSTransfer container', 'Not found');

        if (ui.hasButtonFrame) pass('Button frame');
        else fail('Button frame', 'Not found');

        if (ui.buttons.createDict) pass('Button: Create dictionary');
        else fail('Button: Create dictionary', 'Not found');

        if (ui.buttons.loadDict) pass('Button: Load dictionary');
        else fail('Button: Load dictionary', 'Not found');

        if (ui.buttons.transferClose) pass('Button: Transfer to Close');
        else fail('Button: Transfer to Close', 'Not found');

        log(`    Total buttons: ${ui.buttonCount}`);
    } catch (e) {
        fail('XLSTransfer UI', e.message);
    }

    // 5. Check Navigation
    log('\n[5] Checking Navigation...');
    try {
        const navResult = await cdpSend(ws, 'Runtime.evaluate', {
            expression: `JSON.stringify({
                hasHeader: !!document.querySelector('.bx--header'),
                hasAppsMenu: !!Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Apps')),
                hasSettings: !!Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Settings')),
                hasUser: !!Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('User'))
            })`,
            returnByValue: true
        });
        const nav = JSON.parse(navResult.result.value);

        if (nav.hasHeader) pass('Header present');
        else fail('Header', 'Not found');

        if (nav.hasAppsMenu) pass('Apps menu');
        else fail('Apps menu', 'Not found');

        if (nav.hasSettings) pass('Settings button');
        else fail('Settings button', 'Not found');
    } catch (e) {
        fail('Navigation', e.message);
    }

    // 6. Test Navigation to QuickSearch
    log('\n[6] Testing App Navigation...');
    try {
        // Click Apps menu
        await cdpSend(ws, 'Runtime.evaluate', {
            expression: `
                const appsBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Apps'));
                if (appsBtn) appsBtn.click();
            `
        });
        await wait(500);

        // Click QuickSearch
        await cdpSend(ws, 'Runtime.evaluate', {
            expression: `
                const qsLink = Array.from(document.querySelectorAll('a')).find(a => a.textContent.includes('QuickSearch'));
                if (qsLink) qsLink.click();
            `
        });
        await wait(1000);

        // Check if QuickSearch loaded
        const qsResult = await cdpSend(ws, 'Runtime.evaluate', {
            expression: `!!document.querySelector('.quicksearch-container')`,
            returnByValue: true
        });

        if (qsResult.result.value) pass('Navigate to QuickSearch');
        else fail('Navigate to QuickSearch', 'Container not found');

        // Navigate back to XLSTransfer
        await cdpSend(ws, 'Runtime.evaluate', {
            expression: `
                const appsBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Apps'));
                if (appsBtn) appsBtn.click();
            `
        });
        await wait(500);
        await cdpSend(ws, 'Runtime.evaluate', {
            expression: `
                const xlsLink = Array.from(document.querySelectorAll('a')).find(a => a.textContent.includes('XLSTransfer'));
                if (xlsLink) xlsLink.click();
            `
        });
        await wait(1000);

        const backResult = await cdpSend(ws, 'Runtime.evaluate', {
            expression: `!!document.querySelector('.xlstransfer-container')`,
            returnByValue: true
        });

        if (backResult.result.value) pass('Navigate back to XLSTransfer');
        else fail('Navigate back to XLSTransfer', 'Container not found');

    } catch (e) {
        fail('App navigation', e.message);
    }

    // 7. Test Button Click
    log('\n[7] Testing Button Click...');
    try {
        const clickResult = await cdpSend(ws, 'Runtime.evaluate', {
            expression: `
                const btn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Load dictionary'));
                if (btn) {
                    btn.click();
                    'CLICKED';
                } else {
                    'NOT_FOUND';
                }
            `,
            returnByValue: true
        });

        if (clickResult.result.value === 'CLICKED') {
            pass('Click "Load dictionary" button');
        } else {
            fail('Click button', 'Button not found');
        }
    } catch (e) {
        fail('Button click', e.message);
    }

    ws.close();
    printResults();
}

function printResults() {
    log('\n' + '='.repeat(60));
    log(`RESULTS: ${results.passed} passed, ${results.failed} failed`);
    log('='.repeat(60) + '\n');

    results.tests.forEach(t => {
        const icon = t.status === 'PASS' ? '✓' : '✗';
        const reason = t.reason ? ` (${t.reason})` : '';
        console.log(`  ${icon} ${t.name}${reason}`);
    });

    console.log('\n' + (results.failed === 0 ? '🎉 ALL TESTS PASSED!' : `⚠️  ${results.failed} TESTS FAILED`));
    process.exit(results.failed > 0 ? 1 : 0);
}

main().catch(e => {
    console.error('Fatal error:', e);
    process.exit(1);
});
