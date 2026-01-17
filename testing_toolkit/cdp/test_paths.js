/**
 * Test script to query app paths
 */

const WebSocket = require('ws');
const http = require('http');

async function main() {
    const targets = await new Promise((resolve, reject) => {
        http.get('http://127.0.0.1:9222/json', res => {
            let d = '';
            res.on('data', c => d += c);
            res.on('end', () => resolve(JSON.parse(d)));
        }).on('error', reject);
    });

    const page = targets.find(t => t.type === 'page');
    const ws = new WebSocket(page.webSocketDebuggerUrl);

    let id = 1;
    const send = (method, params = {}) => new Promise(resolve => {
        const msgId = id++;
        ws.on('message', function handler(data) {
            const msg = JSON.parse(data.toString());
            if (msg.id === msgId) {
                ws.off('message', handler);
                resolve(msg);
            }
        });
        ws.send(JSON.stringify({ id: msgId, method, params }));
    });

    const evaluate = async expr => {
        const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
        return r.result?.result?.value;
    };

    await new Promise(r => ws.on('open', r));
    console.log('Connected to app');

    // Try to get update info
    const updateCheck = await evaluate(`
        window.electronUpdate.checkPatchUpdate()
            .then(r => JSON.stringify(r, null, 2))
            .catch(e => JSON.stringify({ error: e.message }))
    `);
    console.log('Patch update check result:');
    console.log(updateCheck);

    ws.close();
}

main().catch(e => console.error('Error:', e.message));
