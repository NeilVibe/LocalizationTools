/**
 * Verify UI-031/032 font settings fix
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

    console.log('=== UI-031/032: FONT SETTINGS TEST ===\n');

    // First click the file to load it
    console.log('[SETUP] Loading file...');
    await evaluate(`
        (function() {
            const spans = document.querySelectorAll('.node-text');
            for (const s of spans) {
                if (s.textContent.includes('xlsx')) {
                    s.click();
                    return 'clicked';
                }
            }
        })()
    `);
    await sleep(1500);

    // Check cells exist
    const cellCount = await evaluate(`document.querySelectorAll('.cell').length`);
    console.log('Cells found:', cellCount);

    if (cellCount === 0) {
        console.log('ERROR: No cells found. File may not have loaded.');
        ws.close();
        return;
    }

    // Get BEFORE style
    const beforeStyle = await evaluate(`
        (function() {
            const cell = document.querySelector('.cell');
            if (!cell) return null;
            const s = window.getComputedStyle(cell);
            return { fontSize: s.fontSize, fontWeight: s.fontWeight };
        })()
    `);
    console.log('[BEFORE] Cell style:', JSON.stringify(beforeStyle));

    // Change font size via select element
    console.log('\n[ACTION] Changing font size to large via select...');
    await evaluate(`
        (function() {
            const selects = document.querySelectorAll('select');
            for (const s of selects) {
                const opts = Array.from(s.options).map(o => o.value);
                if (opts.includes('small') && opts.includes('large')) {
                    s.value = 'large';
                    s.dispatchEvent(new Event('change', { bubbles: true }));
                    return 'Changed to large';
                }
            }
            return 'Select not found';
        })()
    `);
    await sleep(500);

    // Change bold via toggle
    console.log('[ACTION] Clicking Bold toggle...');
    await evaluate(`
        (function() {
            const toggles = document.querySelectorAll('.bx--toggle-input');
            for (const t of toggles) {
                const parent = t.closest('.bx--toggle, .bx--form-item');
                if (parent && parent.textContent.includes('Bold')) {
                    t.click();
                    return 'Clicked';
                }
            }
            return 'Not found';
        })()
    `);
    await sleep(500);

    // Check CSS custom properties on grid
    const cssVars = await evaluate(`
        (function() {
            const grid = document.querySelector('.virtual-grid');
            if (!grid) return { error: 'no grid' };
            return {
                styleAttr: grid.getAttribute('style'),
                fontSize: window.getComputedStyle(grid).getPropertyValue('--grid-font-size'),
                fontWeight: window.getComputedStyle(grid).getPropertyValue('--grid-font-weight')
            };
        })()
    `);
    console.log('[DEBUG] CSS vars:', JSON.stringify(cssVars));

    // Get AFTER style
    const afterStyle = await evaluate(`
        (function() {
            const cell = document.querySelector('.cell');
            if (!cell) return null;
            const s = window.getComputedStyle(cell);
            return { fontSize: s.fontSize, fontWeight: s.fontWeight };
        })()
    `);
    console.log('[AFTER] Cell style:', JSON.stringify(afterStyle));

    // Verdict
    console.log('\n========== VERDICT ==========');

    const fontChanged = beforeStyle.fontSize !== afterStyle.fontSize;
    const boldChanged = beforeStyle.fontWeight !== afterStyle.fontWeight;

    console.log('UI-031 (Font Size):', fontChanged ? '✅ WORKING' : '❌ BROKEN');
    console.log('  Before:', beforeStyle.fontSize);
    console.log('  After:', afterStyle.fontSize);

    console.log('\nUI-032 (Bold):', boldChanged ? '✅ WORKING' : '❌ BROKEN');
    console.log('  Before:', beforeStyle.fontWeight);
    console.log('  After:', afterStyle.fontWeight);

    if (fontChanged && boldChanged) {
        console.log('\n🎉 BOTH UI-031 AND UI-032 VERIFIED FIXED!');
    } else if (fontChanged || boldChanged) {
        console.log('\n⚠️ PARTIAL FIX - one setting works, one does not');
    } else {
        console.log('\n❌ BOTH STILL BROKEN - CSS vars may not be applied to cells');
        console.log('   Check VirtualGrid.svelte for CSS variable usage');
    }

    ws.close();
}

main().catch(console.error);
