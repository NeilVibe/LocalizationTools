/**
 * LDM Full Test Script - CDP Autonomous Testing
 * Navigates to LDM and runs all available tests
 */
const WebSocket = require('ws');

const CDP_PORT = process.env.CDP_PORT || 9222;
const CDP_HOST = process.env.CDP_HOST || 'localhost';

async function main() {
    console.log('========================================');
    console.log('LDM FULL TEST - CDP Autonomous Testing');
    console.log('========================================');
    console.log(`CDP: http://${CDP_HOST}:${CDP_PORT}`);
    console.log('');

    // Get CDP pages
    let pages;
    try {
        const response = await fetch(`http://${CDP_HOST}:${CDP_PORT}/json`);
        pages = await response.json();
        console.log(`Found ${pages.length} CDP page(s)`);
    } catch (err) {
        console.error('ERROR: Cannot connect to CDP');
        console.error('Make sure LocaNext is running with --remote-debugging-port=9222');
        process.exit(1);
    }

    const targetPage = pages.find(p => p.type === 'page') || pages[0];
    if (!targetPage || !targetPage.webSocketDebuggerUrl) {
        console.error('ERROR: No debuggable page found');
        process.exit(1);
    }

    console.log(`Connecting to: ${targetPage.title || 'page'}`);

    const ws = new WebSocket(targetPage.webSocketDebuggerUrl);
    let msgId = 1;

    function send(method, params = {}) {
        return new Promise((resolve, reject) => {
            const id = msgId++;
            const timeout = setTimeout(() => {
                ws.off('message', handler);
                resolve({ error: 'timeout' });
            }, 30000);

            function handler(data) {
                const msg = JSON.parse(data.toString());
                if (msg.id === id) {
                    clearTimeout(timeout);
                    ws.off('message', handler);
                    resolve(msg.result || { error: msg.error });
                }
            }
            ws.on('message', handler);
            ws.send(JSON.stringify({ id, method, params }));
        });
    }

    ws.on('error', (err) => {
        console.error('WebSocket error:', err.message);
        process.exit(1);
    });

    ws.on('open', async () => {
        console.log('Connected to CDP');
        console.log('');

        // Step 1: Check current state
        console.log('[STEP 1] Checking current app state...');
        const stateCheck = await send('Runtime.evaluate', {
            expression: `JSON.stringify({
                url: window.location.href,
                ldmTest: typeof window.ldmTest !== 'undefined',
                xlsTransferTest: typeof window.xlsTransferTest !== 'undefined',
                navTest: typeof window.navTest !== 'undefined',
                pageDebug: typeof window.pageDebug !== 'undefined',
                authenticated: document.querySelector('.bx--header__action') !== null
            })`,
            returnByValue: true
        });
        const state = JSON.parse(stateCheck.result?.value || '{}');
        console.log('  Current state:', state);

        // Check initial store state
        const initialStores = await send('Runtime.evaluate', {
            expression: `
                window.navTest ? JSON.stringify(window.navTest.getState()) : 'navTest not ready'
            `,
            returnByValue: true
        });
        console.log('  Initial store state:', initialStores.result?.value);

        // Check what component is currently showing
        const currentComponent = await send('Runtime.evaluate', {
            expression: `JSON.stringify({
                hasXLSTransfer: !!document.querySelector('.transfer-container'),
                hasWelcome: !!document.querySelector('.welcome-container'),
                hasLDM: !!document.querySelector('.ldm-file-explorer'),
                mainContainerChild: document.querySelector('.main-container')?.firstElementChild?.className || 'none'
            })`,
            returnByValue: true
        });
        console.log('  Initial component:', currentComponent.result?.value);
        console.log('');

        // Step 2: Navigate to LDM using the test navigation helper
        console.log('[STEP 2] Navigating to LDM...');

        // Try using pageDebug (from +page.svelte) which has direct access to the store
        const navResult = await send('Runtime.evaluate', {
            expression: `
                (function() {
                    // Prefer pageDebug (sets from page's context) over navTest (layout's context)
                    if (typeof window.pageDebug !== 'undefined') {
                        const result = window.pageDebug.setApp('ldm');
                        return JSON.stringify({ ...result, source: 'pageDebug' });
                    }
                    // Fallback to navTest
                    if (typeof window.navTest !== 'undefined') {
                        const result = window.navTest.goToApp('ldm');
                        return JSON.stringify({ ...result, source: 'navTest' });
                    }
                    return JSON.stringify({
                        success: false,
                        error: 'Neither pageDebug nor navTest available'
                    });
                })()
            `,
            returnByValue: true
        });
        const navState = JSON.parse(navResult.result?.value || '{}');
        console.log('  Navigation result:', navState);

        if (!navState.success) {
            console.log('');
            console.log('ERROR: Navigation failed');
            console.log('The app needs to be rebuilt with the updated +layout.svelte');
            console.log('Run: cd locaNext && npm run build');
            ws.close();
            process.exit(1);
        }

        // Enable console capture to see any errors
        await send('Runtime.enable', {});
        const consoleErrors = [];
        ws.on('message', (data) => {
            const msg = JSON.parse(data.toString());
            if (msg.method === 'Runtime.consoleAPICalled' && msg.params.type === 'error') {
                consoleErrors.push(msg.params.args.map(a => a.value || a.description).join(' '));
            }
            if (msg.method === 'Runtime.exceptionThrown') {
                consoleErrors.push(msg.params.exceptionDetails.text);
            }
        });

        // Small delay to capture any immediate errors
        await new Promise(r => setTimeout(r, 500));

        // Verify store state after navigation - compare BOTH layout and page views
        await new Promise(r => setTimeout(r, 1000));
        const verifyNav = await send('Runtime.evaluate', {
            expression: `JSON.stringify({
                layoutView: window.navTest ? window.navTest.getState() : 'not available',
                pageView: window.pageDebug ? window.pageDebug.getStoreValues() : 'not available'
            })`,
            returnByValue: true
        });
        console.log('  Store state comparison:', verifyNav.result?.value);

        // Try forcing a DOM update by toggling something
        const forceUpdate = await send('Runtime.evaluate', {
            expression: `
                (function() {
                    // Check if we can trigger a rerender
                    const state = window.navTest.getState();
                    // Force view to app if not already
                    if (state.view !== 'app') {
                        window.navTest.goToApp('ldm');
                        return 'Forced re-navigation';
                    }
                    return 'State looks correct: ' + JSON.stringify(state);
                })()
            `,
            returnByValue: true
        });
        console.log('  Force update:', forceUpdate.result?.value);
        console.log('');

        // Wait for LDM to mount
        console.log('[STEP 3] Waiting for LDM to mount (5 seconds)...');
        await new Promise(r => setTimeout(r, 5000));

        // Check browser console for any errors or debug output
        const consoleCheck = await send('Runtime.evaluate', {
            expression: `
                // Check what view/app the page thinks it has
                (function() {
                    // Look for debug info in the DOM or check for errors
                    const content = document.querySelector('.bx--content');
                    if (!content) return 'No .bx--content found';

                    // Get all child classes to understand what's rendered
                    const children = content.innerHTML.substring(0, 1000);
                    const mainContainer = document.querySelector('.main-container');
                    const childClasses = mainContainer ?
                        Array.from(mainContainer.children).map(c => c.className).join(', ') :
                        'no main-container';

                    return JSON.stringify({
                        childClasses,
                        hasLDM: !!document.querySelector('.ldm-file-explorer, .ldm-container, [class*="ldm"]'),
                        hasWelcome: !!document.querySelector('.welcome-container'),
                        hasXLSTransfer: !!document.querySelector('.transfer-container')
                    });
                })()
            `,
            returnByValue: true
        });
        console.log('  DOM inspection:', consoleCheck.result?.value);

        // Step 4: Verify LDM loaded
        console.log('[STEP 4] Checking LDM test interface...');
        const ldmCheck = await send('Runtime.evaluate', {
            expression: `JSON.stringify({
                ldmTest: typeof window.ldmTest !== 'undefined',
                ldmTestMethods: window.ldmTest ? Object.keys(window.ldmTest) : [],
                pageTitle: document.title,
                hasLdmComponent: document.querySelector('.ldm-container, .ldm-wrapper, [class*="ldm"]') !== null
            })`,
            returnByValue: true
        });
        const ldmState = JSON.parse(ldmCheck.result?.value || '{}');
        console.log('  LDM state:', ldmState);
        console.log('');

        if (!ldmState.ldmTest) {
            console.log('WARNING: window.ldmTest not available');
            console.log('Debugging DOM...');

            // Debug: what's on the page
            const debugDom = await send('Runtime.evaluate', {
                expression: `JSON.stringify({
                    bodyClasses: document.body.className,
                    mainContent: document.querySelector('.bx--content')?.innerHTML?.substring(0, 500) || 'none',
                    headerActions: Array.from(document.querySelectorAll('.bx--header__action')).map(a => a.textContent.trim())
                })`,
                returnByValue: true
            });
            console.log('  DOM debug:', debugDom.result?.value);

            ws.close();
            process.exit(1);
        }

        // Step 5: Run LDM tests
        console.log('[STEP 5] Running LDM tests...');
        console.log('');

        // Test: Get status
        console.log('  Test: getStatus');
        const statusResult = await send('Runtime.evaluate', {
            expression: `JSON.stringify(window.ldmTest.getStatus())`,
            returnByValue: true
        });
        console.log('    Result:', statusResult.result?.value);

        // Test: Create project
        console.log('  Test: createProject');
        const createResult = await send('Runtime.evaluate', {
            expression: `(async () => {
                try {
                    const result = await window.ldmTest.createProject();
                    return JSON.stringify(result);
                } catch(e) {
                    return JSON.stringify({error: e.message});
                }
            })()`,
            returnByValue: true,
            awaitPromise: true
        });
        console.log('    Result:', createResult.result?.value);

        // Summary
        console.log('');
        console.log('========================================');
        if (consoleErrors.length > 0) {
            console.log('CONSOLE ERRORS DETECTED:');
            consoleErrors.forEach(e => console.log('  -', e));
        }
        console.log('LDM TEST COMPLETE');
        console.log('========================================');

        ws.close();
        process.exit(0);
    });
}

main().catch(err => {
    console.error('Fatal error:', err);
    process.exit(1);
});
