/**
 * Check Server Status Panel - for BUG-030 investigation
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

    console.log('=== BUG-030: WebSocket Status Investigation ===\n');

    // Click Server Status tab
    await evaluate(`
        const btn = Array.from(document.querySelectorAll('button'))
            .find(b => b.textContent.includes('Server Status'));
        if (btn) btn.click();
    `);
    await sleep(1000);

    // Get full server status content
    const content = await evaluate(`
        // Find the server status panel content
        const panel = document.querySelector('[class*="server-status"]') ||
                      document.querySelector('[class*="ServerStatus"]') ||
                      document.body;
        panel.innerText;
    `);

    console.log('Full Panel Content:');
    console.log(content);
    console.log('\n--- Filtered Status Lines ---');

    const lines = content.split('\n').filter(l =>
        l.includes('API') || l.includes('Database') || l.includes('WebSocket') ||
        l.includes('connected') || l.includes('disconnected') || l.includes('Online') ||
        l.includes('Offline') || l.includes('Status') || l.includes('Server')
    );
    lines.forEach(l => console.log('  ', l.trim()));

    // Check for specific status indicators
    const hasWebSocketDisconnected = content.includes('WebSocket') && content.includes('disconnected');
    const hasDbConnected = content.includes('Database') && content.includes('connected');

    console.log('\n--- Analysis ---');
    console.log('Database connected:', hasDbConnected ? 'YES' : 'NO');
    console.log('WebSocket disconnected:', hasWebSocketDisconnected ? 'YES (BUG-030)' : 'NO');

    ws.close();
}

main().catch(e => { console.error(e); process.exit(1); });
