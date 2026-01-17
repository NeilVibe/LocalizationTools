/**
 * Test script for patch update download with debug logging
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

    // First check patch update
    console.log('Checking for patch update...');
    const checkResult = await evaluate(`
        window.electronUpdate.checkPatchUpdate()
            .then(r => JSON.stringify(r))
            .catch(e => JSON.stringify({ error: e.message }))
    `);

    const check = JSON.parse(checkResult);
    console.log('Patch available:', check.available);
    console.log('New version:', check.version);

    if (!check.available) {
        console.log('No update available');
        ws.close();
        return;
    }

    console.log('Components to update:', check.updates?.map(u => u.name).join(', '));
    console.log('Total size:', ((check.totalSize || 0) / 1024 / 1024).toFixed(1), 'MB');

    // Now trigger the download
    console.log('');
    console.log('Triggering download (this will take a while)...');
    console.log('The debug logging is in the Electron main process console.');
    console.log('');

    const updateCode = `
        new Promise((resolve) => {
            const timeout = setTimeout(() => resolve({ timeout: true }), 120000);
            window.electronUpdate.applyPatchUpdate(${JSON.stringify(check.updates)})
                .then(r => { clearTimeout(timeout); resolve(r); })
                .catch(e => { clearTimeout(timeout); resolve({ error: e.message }); });
        }).then(r => JSON.stringify(r, null, 2))
    `;

    const applyResult = await evaluate(updateCode);

    console.log('Apply result:');
    console.log(applyResult);

    ws.close();
}

main().catch(e => console.error('Error:', e.message));
