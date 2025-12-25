/**
 * CDP Login Script - Login to LocaNext and verify test interfaces
 */
const WebSocket = require('ws');
const http = require('http');

const CDP_URL = 'http://127.0.0.1:9222/json';
const USERNAME = 'neil';
const PASSWORD = 'neil';

async function main() {
    console.log('=== CDP LOGIN TEST ===\n');

    // Get CDP target
    const targets = await new Promise((resolve, reject) => {
        http.get(CDP_URL, (res) => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => resolve(JSON.parse(data)));
        }).on('error', reject);
    });

    const page = targets.find(t => t.type === 'page');
    if (!page) {
        console.log('ERROR: No page target found');
        process.exit(1);
    }

    const ws = new WebSocket(page.webSocketDebuggerUrl);
    let id = 1;

    function send(method, params = {}) {
        return new Promise((resolve, reject) => {
            const msgId = id++;
            const timeout = setTimeout(() => reject(new Error('Timeout')), 15000);
            const handler = (data) => {
                const msg = JSON.parse(data.toString());
                if (msg.id === msgId) {
                    clearTimeout(timeout);
                    ws.off('message', handler);
                    resolve(msg);
                }
            };
            ws.on('message', handler);
            ws.send(JSON.stringify({ id: msgId, method, params }));
        });
    }

    async function evaluate(expression) {
        const result = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
        if (result.result?.exceptionDetails) {
            console.log('JS Error:', result.result.exceptionDetails.exception?.description || 'Unknown');
            return null;
        }
        return result.result?.result?.value;
    }

    await new Promise((resolve, reject) => {
        ws.on('open', resolve);
        ws.on('error', reject);
    });

    console.log('[1] Connected to CDP');

    // Check current page state
    const bodyText = await evaluate('document.body.innerText.substring(0, 200)');
    console.log('[2] Current page:', bodyText && bodyText.includes('Login') ? 'LOGIN PAGE' : 'OTHER');

    if (bodyText && bodyText.includes('Login')) {
        console.log('[3] Filling login form...');

        // Find and fill inputs
        await evaluate(`
            (function() {
                const inputs = document.querySelectorAll('input');
                inputs.forEach(input => {
                    if (input.type === 'text' || input.placeholder?.toLowerCase().includes('user')) {
                        input.value = '${USERNAME}';
                        input.dispatchEvent(new Event('input', { bubbles: true }));
                    }
                    if (input.type === 'password') {
                        input.value = '${PASSWORD}';
                        input.dispatchEvent(new Event('input', { bubbles: true }));
                    }
                });
            })()
        `);

        // Find and click login button
        console.log('[4] Clicking login button...');
        await evaluate(`
            (function() {
                const buttons = document.querySelectorAll('button');
                for (const btn of buttons) {
                    if (btn.textContent.toLowerCase().includes('login') || btn.type === 'submit') {
                        btn.click();
                        return 'clicked';
                    }
                }
                // Also try form submit
                const form = document.querySelector('form');
                if (form) {
                    form.submit();
                    return 'form submitted';
                }
                return 'no button found';
            })()
        `);

        // Wait for navigation
        console.log('[5] Waiting for login...');
        await new Promise(r => setTimeout(r, 4000));
    }

    // Check page state after login
    console.log('\n[6] Checking page state after login...');
    const state = await evaluate(`JSON.stringify({
        url: window.location.href,
        hash: window.location.hash,
        bodyPreview: document.body.innerText.substring(0, 400),
        pageDebug: typeof window.pageDebug !== 'undefined',
        navTest: typeof window.navTest !== 'undefined',
        ldmTest: typeof window.ldmTest !== 'undefined',
        xlsTransferTest: typeof window.xlsTransferTest !== 'undefined',
        quickSearchTest: typeof window.quickSearchTest !== 'undefined',
        krSimilarTest: typeof window.krSimilarTest !== 'undefined'
    })`);

    if (state) {
        const parsed = JSON.parse(state);
        console.log('\n=== RESULT ===');
        console.log('Hash:', parsed.hash || '(none)');
        console.log('\nTest Interfaces:');
        console.log('  navTest:', parsed.navTest);
        console.log('  ldmTest:', parsed.ldmTest);
        console.log('  xlsTransferTest:', parsed.xlsTransferTest);
        console.log('  quickSearchTest:', parsed.quickSearchTest);
        console.log('  krSimilarTest:', parsed.krSimilarTest);
        console.log('\nBody Preview:');
        console.log(parsed.bodyPreview.substring(0, 200));
    }

    ws.close();
    process.exit(0);
}

main().catch(err => {
    console.error('Error:', err.message);
    process.exit(1);
});
