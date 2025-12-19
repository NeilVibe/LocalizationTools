/**
 * Check network requests for WebSocket
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
    const networkEvents = [];

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

    console.log('=== Network Debug for WebSocket ===\n');

    // Enable Network domain
    await send('Network.enable');

    // Listen for network events
    ws.on('message', (data) => {
        const msg = JSON.parse(data.toString());
        if (msg.method?.startsWith('Network.')) {
            if (msg.params?.request?.url?.includes('socket') ||
                msg.params?.response?.url?.includes('socket') ||
                msg.params?.documentURL?.includes('socket')) {
                networkEvents.push(msg);
            }
        }
    });

    // Trigger a page reload to capture fresh WebSocket connection attempt
    console.log('Capturing network activity...');
    await sleep(2000);

    // Now manually test the socket.io endpoint
    console.log('\n--- Testing socket.io endpoint directly ---');
    const testResult = await send('Runtime.evaluate', {
        expression: `
            (async () => {
                try {
                    // Test the socket.io polling endpoint
                    const response = await fetch('http://localhost:8888/ws/socket.io/?EIO=4&transport=polling');
                    const text = await response.text();
                    return {
                        status: response.status,
                        statusText: response.statusText,
                        headers: Object.fromEntries(response.headers.entries()),
                        body: text.substring(0, 500)
                    };
                } catch (e) {
                    return { error: e.message };
                }
            })()
        `,
        returnByValue: true,
        awaitPromise: true
    });

    console.log('Socket.IO endpoint response:');
    console.log(JSON.stringify(testResult.result?.result?.value, null, 2));

    // Check if socket.io actually tried to connect
    console.log('\n--- Checking for WebSocket upgrade requests ---');
    const wsUpgrade = await send('Runtime.evaluate', {
        expression: `
            performance.getEntriesByType('resource')
                .filter(e => e.initiatorType === 'fetch' || e.initiatorType === 'xmlhttprequest')
                .filter(e => e.name.includes('socket'))
                .map(e => ({
                    url: e.name,
                    duration: e.duration.toFixed(0) + 'ms',
                    type: e.initiatorType
                }))
        `,
        returnByValue: true
    });
    console.log(JSON.stringify(wsUpgrade.result?.result?.value, null, 2));

    ws.close();
}

main().catch(e => { console.error(e); process.exit(1); });
