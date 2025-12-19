/**
 * Check all settings - navigate properly and examine each panel
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

    console.log('=== SETTINGS INVESTIGATION ===\n');

    // First, close any modals by pressing Escape multiple times
    for (let i = 0; i < 3; i++) {
        await evaluate(`document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', code: 'Escape', bubbles: true }))`);
        await sleep(200);
    }

    // Navigate to main Settings page (top navigation)
    console.log('[1] Clicking Settings in top nav...');
    await evaluate(`
        const settingsLink = Array.from(document.querySelectorAll('a, button'))
            .find(el => el.textContent.trim() === 'Settings' && !el.closest('.sidebar'));
        if (settingsLink) settingsLink.click();
        'clicked'
    `);
    await sleep(1000);

    // Check current page content
    const pageContent = await evaluate(`document.body.innerText.substring(0, 1500)`);
    console.log('\n--- Current Page Content ---');
    console.log(pageContent);

    // Check for settings-related elements
    console.log('\n[2] Looking for settings controls...');
    const settingsElements = await evaluate(`
        const result = [];

        // Find all labels
        document.querySelectorAll('label').forEach(l => {
            result.push('LABEL: ' + l.textContent.trim().substring(0, 50));
        });

        // Find all inputs with their types
        document.querySelectorAll('input, select').forEach(el => {
            const label = el.closest('label')?.textContent || el.name || el.id || 'unknown';
            result.push('INPUT[' + (el.type || el.tagName) + ']: ' + label.trim().substring(0, 50));
        });

        // Find all buttons in main area
        document.querySelectorAll('.content button, main button, [role="main"] button').forEach(b => {
            result.push('BUTTON: ' + b.textContent.trim().substring(0, 50));
        });

        result.slice(0, 30).join('\\n');
    `);
    console.log(settingsElements);

    // Now specifically click Display Settings if visible
    console.log('\n[3] Trying Display Settings tab...');
    await evaluate(`
        const displayBtn = Array.from(document.querySelectorAll('button'))
            .find(b => b.textContent.includes('Display Settings'));
        if (displayBtn) { displayBtn.click(); 'clicked Display Settings'; }
        else { 'Display Settings button not found'; }
    `);
    await sleep(500);

    // Get Display Settings panel content
    const displayContent = await evaluate(`
        // Try to find a panel that appeared after clicking
        const panels = document.querySelectorAll('[class*="panel"], [class*="settings"], [class*="content"]');
        let text = '';
        panels.forEach(p => {
            if (p.innerText.includes('Font') || p.innerText.includes('Bold') || p.innerText.includes('Size')) {
                text = p.innerText;
            }
        });
        text || 'No font/bold settings found in any panel';
    `);
    console.log('\n--- Display Settings Panel ---');
    console.log(displayContent.substring(0, 1000));

    ws.close();
}

main().catch(e => { console.error(e); process.exit(1); });
