/**
 * Debug - find modal content after clicking Server Status
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

    console.log('=== BUG-030: WebSocket Status Test ===\n');

    // Click the Server Status button (icon button with tooltip)
    await evaluate(`
        const btn = Array.from(document.querySelectorAll('button'))
            .find(b => b.querySelector('.bx--assistive-text')?.textContent.includes('Server Status'));
        if (btn) btn.click();
    `);
    console.log('Clicked Server Status button');

    await sleep(2000);

    // Check for modal content
    const modalContent = await evaluate(`
        const modal = document.querySelector('.bx--modal--open') ||
                      document.querySelector('[class*="modal"][class*="open"]') ||
                      document.querySelector('[role="dialog"]');
        modal ? modal.innerText : 'No modal found';
    `);
    console.log('\n=== Modal Content ===');
    console.log(modalContent);

    // Specific check for WebSocket status
    const wsStatus = await evaluate(`
        const text = document.body.innerText;
        const wsMatch = text.match(/WebSocket[:\\s]*(connected|disconnected)/i);
        wsMatch ? wsMatch[0] : 'WebSocket status not found in page';
    `);
    console.log('\n=== WebSocket Status ===');
    console.log(wsStatus);

    // Full body for reference
    const body = await evaluate('document.body.innerText');
    console.log('\n=== Full Page Text ===');
    console.log(body);

    ws.close();
}

main().catch(e => { console.error(e); process.exit(1); });
