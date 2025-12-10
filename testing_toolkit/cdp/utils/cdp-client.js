/**
 * CDP Client Utility - Shared Chrome DevTools Protocol Connection
 *
 * Used by all CDP-based tests to connect to LocaNext app.
 *
 * Usage:
 *   const { connect, evaluate, navigateToApp } = require('./utils/cdp-client');
 *   const cdp = await connect();
 *   const result = await evaluate(cdp, 'window.location.href');
 */

const WebSocket = require('ws');

const CDP_PORT = process.env.CDP_PORT || 9222;
const CDP_HOST = process.env.CDP_HOST || 'localhost';

/**
 * Connect to CDP and return WebSocket + send function
 */
async function connect() {
    console.log(`[CDP] Connecting to http://${CDP_HOST}:${CDP_PORT}...`);

    // Get CDP pages
    const response = await fetch(`http://${CDP_HOST}:${CDP_PORT}/json`);
    const pages = await response.json();

    console.log(`[CDP] Found ${pages.length} page(s)`);

    const targetPage = pages.find(p => p.type === 'page') || pages[0];
    if (!targetPage || !targetPage.webSocketDebuggerUrl) {
        throw new Error('No debuggable page found');
    }

    console.log(`[CDP] Connecting to: ${targetPage.title || 'page'}`);

    const ws = new WebSocket(targetPage.webSocketDebuggerUrl);
    let msgId = 1;

    // Send CDP command and wait for response
    function send(method, params = {}) {
        return new Promise((resolve, reject) => {
            const id = msgId++;
            const timeout = setTimeout(() => {
                ws.off('message', handler);
                reject(new Error(`Timeout waiting for ${method}`));
            }, 30000);

            function handler(data) {
                const msg = JSON.parse(data.toString());
                if (msg.id === id) {
                    clearTimeout(timeout);
                    ws.off('message', handler);
                    if (msg.error) {
                        reject(new Error(msg.error.message));
                    } else {
                        resolve(msg.result || {});
                    }
                }
            }
            ws.on('message', handler);
            ws.send(JSON.stringify({ id, method, params }));
        });
    }

    // Wait for connection
    await new Promise((resolve, reject) => {
        ws.on('open', resolve);
        ws.on('error', reject);
    });

    console.log('[CDP] Connected');

    return { ws, send };
}

/**
 * Evaluate JavaScript in the page context
 */
async function evaluate(cdp, expression) {
    const result = await cdp.send('Runtime.evaluate', {
        expression,
        returnByValue: true,
        awaitPromise: true
    });
    return result.result?.value;
}

/**
 * Navigate to an app using the navTest interface
 */
async function navigateToApp(cdp, appName) {
    console.log(`[CDP] Navigating to ${appName}...`);
    const result = await evaluate(cdp, `
        (function() {
            if (typeof window.pageDebug !== 'undefined') {
                return JSON.stringify(window.pageDebug.setApp('${appName}'));
            }
            if (typeof window.navTest !== 'undefined') {
                return JSON.stringify(window.navTest.goToApp('${appName}'));
            }
            return JSON.stringify({ success: false, error: 'No navigation interface' });
        })()
    `);
    return JSON.parse(result);
}

/**
 * Wait for a DOM element to appear
 */
async function waitForSelector(cdp, selector, timeout = 10000) {
    const start = Date.now();
    while (Date.now() - start < timeout) {
        const exists = await evaluate(cdp, `!!document.querySelector('${selector}')`);
        if (exists) return true;
        await new Promise(r => setTimeout(r, 100));
    }
    throw new Error(`Timeout waiting for selector: ${selector}`);
}

/**
 * Get all test interfaces available in the page
 */
async function getTestInterfaces(cdp) {
    return await evaluate(cdp, `JSON.stringify({
        pageDebug: typeof window.pageDebug !== 'undefined',
        navTest: typeof window.navTest !== 'undefined',
        ldmTest: typeof window.ldmTest !== 'undefined',
        xlsTransferTest: typeof window.xlsTransferTest !== 'undefined',
        quickSearchTest: typeof window.quickSearchTest !== 'undefined',
        krSimilarTest: typeof window.krSimilarTest !== 'undefined'
    })`);
}

module.exports = {
    CDP_HOST,
    CDP_PORT,
    connect,
    evaluate,
    navigateToApp,
    waitForSelector,
    getTestInterfaces
};
