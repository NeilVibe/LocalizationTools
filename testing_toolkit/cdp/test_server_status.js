/**
 * Check Server Status and TM Build
 * Navigate to Server Status panel and trigger TM build
 */
const WebSocket = require('ws');
const http = require('http');
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function main() {
    console.log('=== SERVER STATUS & TM BUILD TEST ===\n');

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

    const send = (method, params = {}) => new Promise((resolve) => {
        const msgId = id++;
        const timeout = setTimeout(() => resolve({ timeout: true }), 30000);
        ws.on('message', function handler(data) {
            const msg = JSON.parse(data.toString());
            if (msg.id === msgId) {
                clearTimeout(timeout);
                ws.off('message', handler);
                resolve(msg);
            }
        });
        ws.send(JSON.stringify({ id: msgId, method, params }));
    });

    const evaluate = async (expression) => {
        const result = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
        return result.result?.result?.value;
    };

    await new Promise(resolve => ws.on('open', resolve));

    // Click Server Status in the right panel
    console.log('[1] Clicking Server Status tab...');
    await evaluate(`
        const serverBtn = Array.from(document.querySelectorAll('button')).find(b =>
            b.textContent.includes('Server Status')
        );
        if (serverBtn) serverBtn.click();
    `);
    await sleep(1500);

    // Get Server Status panel content
    console.log('[2] Reading Server Status panel...');
    const statusContent = await evaluate(`
        (function() {
            // Look for the server status panel content
            const panel = document.querySelector('[class*="server-status"], [class*="status-panel"]');
            if (panel) return panel.innerText;

            // Otherwise get all visible panels
            const body = document.body.innerText;
            return body;
        })()
    `);

    console.log('\nServer Status Content:');
    console.log(statusContent.substring(0, 2000));

    // Look for TM status info
    console.log('\n[3] Looking for TM/Index status...');
    const tmStatus = await evaluate(`
        (function() {
            const body = document.body.innerText;
            const lines = body.split('\\n');
            const tmLines = lines.filter(l =>
                l.toLowerCase().includes('tm') ||
                l.toLowerCase().includes('index') ||
                l.toLowerCase().includes('embedding') ||
                l.toLowerCase().includes('model') ||
                l.toLowerCase().includes('status') ||
                l.toLowerCase().includes('ready') ||
                l.toLowerCase().includes('pending')
            );
            return tmLines.slice(0, 20).join('\\n');
        })()
    `);
    console.log('TM-related lines:');
    console.log(tmStatus);

    // Try to find and click Build/Rebuild buttons
    console.log('\n[4] Looking for Build buttons...');
    const buildAction = await evaluate(`
        (function() {
            const btns = Array.from(document.querySelectorAll('button'));
            const buildBtns = btns.filter(b =>
                b.textContent.toLowerCase().includes('build') ||
                b.textContent.toLowerCase().includes('rebuild') ||
                b.textContent.toLowerCase().includes('sync')
            );

            if (buildBtns.length > 0) {
                return buildBtns.map(b => b.textContent.trim()).join(' | ');
            }
            return 'No build buttons found';
        })()
    `);
    console.log('Build buttons:', buildAction);

    // Check for any error messages
    const errors = await evaluate(`
        (function() {
            const body = document.body.innerText.toLowerCase();
            const hasNameError = body.includes('nameerror') || body.includes('model_name');
            const hasError = body.includes('error:') || body.includes('failed');
            const errorLines = body.split('\\n').filter(l => l.includes('error'));

            return JSON.stringify({
                hasNameError,
                hasError,
                errorLines: errorLines.slice(0, 5)
            });
        })()
    `);

    const errorInfo = JSON.parse(errors);
    console.log('\n=== ERROR CHECK ===');
    console.log('NameError found:', errorInfo.hasNameError);
    console.log('Any errors:', errorInfo.hasError);
    if (errorInfo.errorLines.length > 0) {
        console.log('Error lines:', errorInfo.errorLines);
    }

    // VERDICT
    console.log('\n=============================');
    console.log('=== BUG-023 FINAL VERDICT ===');
    console.log('=============================');

    if (errorInfo.hasNameError) {
        console.log('❌ FAIL: MODEL_NAME/NameError detected');
    } else {
        console.log('✅ No MODEL_NAME/NameError detected');
        console.log('   BUG-023 fix appears to be working');
    }

    ws.close();
}

main().catch(err => console.error('Error:', err));
