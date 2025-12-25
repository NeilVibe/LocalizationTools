/**
 * Test UI-031 and UI-032: Font Size and Bold settings
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

    console.log('=== UI-031/032: Font Size & Bold Test ===\n');

    // Close any modals
    for (let i = 0; i < 3; i++) {
        await evaluate(`document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))`);
        await sleep(200);
    }

    // First, click on a file to load the grid
    console.log('[1] Clicking on a file to load grid...');
    await evaluate(`
        const file = document.querySelector('.tree-node');
        if (file) file.click();
    `);
    await sleep(1000);

    // Get current font size of grid cells
    const beforeFontSize = await evaluate(`
        const cell = document.querySelector('[class*="grid"] td, [class*="grid"] [role="cell"], .virtual-row, [class*="VirtualGrid"]');
        if (cell) {
            const style = window.getComputedStyle(cell);
            style.fontSize + ' / ' + style.fontWeight;
        } else {
            'No grid cell found';
        }
    `);
    console.log('BEFORE - Grid cell style:', beforeFontSize);

    // Click Display Settings
    console.log('\n[2] Opening Display Settings...');
    await evaluate(`
        const btn = Array.from(document.querySelectorAll('button'))
            .find(b => b.textContent.includes('Display Settings'));
        if (btn) btn.click();
    `);
    await sleep(500);

    // Get current selection
    const currentSettings = await evaluate(`
        const fontSelect = document.querySelector('select[name*="font"], select[id*="font"]') ||
                           Array.from(document.querySelectorAll('select')).find(s =>
                               s.closest('label')?.textContent.includes('Font'));
        const boldInputs = document.querySelectorAll('input[type="radio"][name*="bold"], input[name*="bold"]');

        let fontVal = fontSelect ? fontSelect.value : 'not found';
        let boldVal = 'not found';
        boldInputs.forEach(i => { if (i.checked) boldVal = i.value; });

        'Font: ' + fontVal + ', Bold: ' + boldVal;
    `);
    console.log('Current settings:', currentSettings);

    // Change font size to Large
    console.log('\n[3] Changing font size to Large (16px)...');
    await evaluate(`
        const fontSelect = document.querySelector('select') ||
                           Array.from(document.querySelectorAll('select')).find(s =>
                               s.closest('label')?.textContent.includes('Font'));
        if (fontSelect) {
            // Find the Large option
            const options = Array.from(fontSelect.options);
            const largeOpt = options.find(o => o.text.includes('Large') || o.value.includes('16'));
            if (largeOpt) {
                fontSelect.value = largeOpt.value;
                fontSelect.dispatchEvent(new Event('change', { bubbles: true }));
                'Changed to: ' + largeOpt.text;
            } else {
                'Large option not found. Options: ' + options.map(o => o.text).join(', ');
            }
        } else {
            'Select not found';
        }
    `);
    await sleep(500);

    // Also try Bold
    console.log('\n[4] Changing Bold to Bold...');
    await evaluate(`
        const boldRadio = document.querySelector('input[value="bold"], input[type="radio"]:not(:checked)');
        if (boldRadio) {
            boldRadio.click();
            'Clicked bold radio';
        } else {
            'Bold radio not found';
        }
    `);
    await sleep(500);

    // Check grid cell style AFTER changes
    const afterFontSize = await evaluate(`
        const cell = document.querySelector('[class*="grid"] td, [class*="grid"] [role="cell"], .virtual-row, [class*="VirtualGrid"]');
        if (cell) {
            const style = window.getComputedStyle(cell);
            style.fontSize + ' / ' + style.fontWeight;
        } else {
            'No grid cell found';
        }
    `);
    console.log('\nAFTER - Grid cell style:', afterFontSize);

    // Final verdict
    console.log('\n=== VERDICT ===');
    if (beforeFontSize === afterFontSize) {
        console.log('❌ UI-031/032 CONFIRMED BROKEN: Settings do NOT affect grid!');
        console.log('   Before:', beforeFontSize);
        console.log('   After:', afterFontSize);
    } else {
        console.log('✅ Settings ARE working!');
        console.log('   Before:', beforeFontSize);
        console.log('   After:', afterFontSize);
    }

    ws.close();
}

main().catch(e => { console.error(e); process.exit(1); });
