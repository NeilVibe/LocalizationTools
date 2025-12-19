/**
 * Close any open modals
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
        const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true });
        return r.result?.result?.value;
    };

    await new Promise(resolve => ws.on('open', resolve));

    // Close any open modals by clicking Cancel or X button
    const closed = await evaluate(`
        const cancelBtn = Array.from(document.querySelectorAll('button'))
            .find(b => b.textContent.includes('Cancel'));
        if (cancelBtn) { cancelBtn.click(); 'closed modal'; }
        else { 'no modal found'; }
    `);
    console.log('Result:', closed);

    await sleep(500);

    // Also try pressing Escape
    await evaluate(`
        document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', code: 'Escape' }));
    `);

    console.log('Done');
    ws.close();
}

main().catch(e => { console.error(e); process.exit(1); });
