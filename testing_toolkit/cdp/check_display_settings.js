/**
 * Check Display Settings - UI-031, UI-032, UI-033 investigation
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

    console.log('=== UI-031/032/033: Display Settings Investigation ===\n');

    // Click Display Settings tab
    await evaluate(`
        const btn = Array.from(document.querySelectorAll('button'))
            .find(b => b.textContent.includes('Display Settings'));
        if (btn) btn.click();
    `);
    await sleep(1000);

    // Get display settings content
    const content = await evaluate('document.body.innerText');

    console.log('--- Display Settings Panel ---');
    const lines = content.split('\n').filter(l =>
        l.includes('Font') || l.includes('Bold') || l.includes('Size') ||
        l.includes('Display') || l.includes('Setting') || l.includes('Theme') ||
        l.includes('px') || l.includes('pt')
    );
    lines.forEach(l => console.log('  ', l.trim()));

    // Check what controls exist
    const controls = await evaluate(`
        const inputs = document.querySelectorAll('input, select, button');
        const found = [];
        inputs.forEach(el => {
            const label = el.closest('label')?.textContent ||
                          el.previousElementSibling?.textContent ||
                          el.placeholder || el.name || el.id || '';
            if (label.toLowerCase().includes('font') ||
                label.toLowerCase().includes('bold') ||
                label.toLowerCase().includes('size')) {
                found.push({
                    type: el.tagName + (el.type ? ':' + el.type : ''),
                    label: label.trim().substring(0, 50),
                    value: el.value || el.checked
                });
            }
        });
        JSON.stringify(found, null, 2);
    `);

    console.log('\n--- Font/Bold Controls Found ---');
    console.log(controls || 'None found');

    // Now check App Settings (UI-033)
    console.log('\n=== UI-033: App Settings Investigation ===\n');

    // Click Settings in top nav
    await evaluate(`
        const btn = Array.from(document.querySelectorAll('button, a'))
            .find(b => b.textContent.trim() === 'Settings');
        if (btn) btn.click();
    `);
    await sleep(1000);

    const settingsContent = await evaluate('document.body.innerText.substring(0, 2000)');
    console.log('--- Settings Page Content ---');
    console.log(settingsContent);

    ws.close();
}

main().catch(e => { console.error(e); process.exit(1); });
