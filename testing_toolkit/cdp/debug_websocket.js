/**
 * Debug WebSocket connection - BUG-030
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
        const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
        return r.result?.result?.value;
    };

    await new Promise(resolve => ws.on('open', resolve));

    console.log('=== BUG-030: WebSocket Debug ===\n');

    // Check websocket service state
    const wsState = await evaluate(`
        if (typeof window !== 'undefined') {
            // Try to access the websocket module
            const result = {
                hasWebsocket: false,
                socketExists: false,
                socketConnected: false,
                socketId: null,
                socketTransport: null
            };

            // Check if socket.io client is loaded
            if (window.io) {
                result.hasIO = true;
            }

            // Try to find the websocket instance (it's in a module, might need different approach)
            // Check console for WebSocket errors

            JSON.stringify(result, null, 2);
        } else {
            'window not defined';
        }
    `);
    console.log('WebSocket module state:', wsState);

    // Check localStorage for auth token
    const authToken = await evaluate(`localStorage.getItem('auth_token') ? 'exists' : 'missing'`);
    console.log('Auth token:', authToken);

    // Check isConnected store value
    const storeState = await evaluate(`
        // The stores are Svelte stores, hard to access directly
        // But we can check the DOM for indicators
        const serverStatus = document.body.innerText;
        const wsLine = serverStatus.includes('WebSocket') ?
            serverStatus.split('\\n').find(l => l.includes('WebSocket')) : 'not found';
        wsLine;
    `);
    console.log('WebSocket status in UI:', storeState);

    // Check for console errors related to WebSocket
    console.log('\n--- Checking console for WS errors ---');

    // Enable console message capture
    await send('Runtime.enable');
    await send('Console.enable');

    // Try to manually trigger websocket connect
    console.log('\n--- Attempting to get websocket state from window ---');
    const wsDebug = await evaluate(`
        // Check if there are any socket connections
        const sockets = [];
        if (window.WebSocket) {
            // Can't directly enumerate WebSocket instances
            // But we can check performance entries
        }

        // Try to access Svelte context (won't work from here)
        // Instead, let's check network activity

        'WebSocket API exists: ' + (typeof WebSocket !== 'undefined');
    `);
    console.log(wsDebug);

    // Check backend WebSocket endpoint
    console.log('\n--- Testing backend WS endpoint ---');
    const backendCheck = await evaluate(`
        fetch('http://localhost:8888/ws/socket.io/')
            .then(r => 'WS endpoint status: ' + r.status)
            .catch(e => 'WS endpoint error: ' + e.message);
    `);
    console.log('Backend WS check:', backendCheck);

    ws.close();
}

main().catch(e => { console.error(e); process.exit(1); });
