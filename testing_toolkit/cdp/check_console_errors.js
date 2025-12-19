/**
 * Check browser console for WebSocket errors
 */
const WebSocket = require('ws');
const http = require('http');

const sleep = ms => new Promise(r => setTimeout(r, ms));

async function main() {
    const targets = await new Promise((resolve, reject) => {
        http.get('http://127.0.0.1:9222/json', (res) => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => resolve(JSON.parse(data)));
        }).on('error', reject);
    });

    const page = targets.find(t => t.type === 'page');
    const ws = new WebSocket(page.webSocketDebuggerUrl);
    let id = 1;
    const consoleMessages = [];

    const send = (method, params = {}) => new Promise(resolve => {
        const msgId = id++;
        const handler = (msg) => {
            const r = JSON.parse(msg.toString());
            if (r.id === msgId) { ws.off('message', handler); resolve(r); }
        };
        ws.on('message', handler);
        ws.send(JSON.stringify({ id: msgId, method, params }));
    });

    await new Promise(resolve => ws.on('open', resolve));

    console.log('=== Console Messages & WebSocket Debug ===\n');

    // Enable console and collect messages
    await send('Console.enable');
    await send('Runtime.enable');

    // Listen for console messages
    ws.on('message', (data) => {
        const msg = JSON.parse(data.toString());
        if (msg.method === 'Console.messageAdded') {
            const entry = msg.params.message;
            consoleMessages.push({
                level: entry.level,
                text: entry.text
            });
        }
        if (msg.method === 'Runtime.consoleAPICalled') {
            const args = msg.params.args.map(a => a.value || a.description || '').join(' ');
            consoleMessages.push({
                level: msg.params.type,
                text: args
            });
        }
    });

    // Wait a bit to collect any existing messages
    await sleep(1000);

    // Now get existing console logs by evaluating
    const existingLogs = await send('Runtime.evaluate', {
        expression: `
            // This won't get past logs, but we can check current state
            const checks = [];

            // Check if socket.io was even loaded
            checks.push('socket.io-client loaded: ' + (typeof io !== 'undefined'));

            // Check for any error elements in the DOM
            const errors = document.querySelectorAll('[class*="error"], [class*="Error"]');
            checks.push('Error elements in DOM: ' + errors.length);

            // Check the actual websocket connection attempt
            // Look for any failed network requests
            checks.push('Performance entries with WebSocket: ' +
                performance.getEntriesByType('resource')
                    .filter(e => e.name.includes('socket') || e.name.includes('ws'))
                    .map(e => e.name + ' [' + e.duration.toFixed(0) + 'ms]')
                    .join(', ')
            );

            checks.join('\\n');
        `,
        returnByValue: true
    });

    console.log('--- Current State ---');
    console.log(existingLogs.result?.result?.value || 'No result');

    // Filter WebSocket related messages
    console.log('\n--- WebSocket Related Console Messages ---');
    const wsMessages = consoleMessages.filter(m =>
        m.text.toLowerCase().includes('websocket') ||
        m.text.toLowerCase().includes('socket') ||
        m.text.toLowerCase().includes('ws') ||
        m.text.toLowerCase().includes('connect')
    );
    if (wsMessages.length > 0) {
        wsMessages.forEach(m => console.log(`[${m.level}] ${m.text}`));
    } else {
        console.log('No WebSocket messages captured (might have happened before we started listening)');
    }

    // All error messages
    console.log('\n--- Error Messages ---');
    const errors = consoleMessages.filter(m => m.level === 'error');
    if (errors.length > 0) {
        errors.forEach(m => console.log(`[ERROR] ${m.text}`));
    } else {
        console.log('No error messages');
    }

    ws.close();
}

main().catch(e => { console.error(e); process.exit(1); });
