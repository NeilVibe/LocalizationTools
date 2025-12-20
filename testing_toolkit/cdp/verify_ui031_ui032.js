/**
 * Clean verification for UI-031/032 font settings
 * Build 304 verification
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

    console.log('=== UI-031/032: BUILD 304 VERIFICATION ===\n');

    // Load file first
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

    // Reset to Small + Normal
    console.log('[RESET] Setting to Small + Normal...');
    await evaluate(`
        (function() {
            const selects = document.querySelectorAll('select');
            for (const s of selects) {
                if (s.value === 'large' || s.value === 'medium' || s.value === 'small') {
                    s.value = 'small';
                    s.dispatchEvent(new Event('change', { bubbles: true }));
                }
            }
        })()
    `);
    await sleep(300);

    // Reset bold if on
    await evaluate(`
        (function() {
            const grid = document.querySelector('.virtual-grid');
            if (grid && grid.style.getPropertyValue('--grid-font-weight') === '600') {
                const toggles = document.querySelectorAll('.bx--toggle-input');
                for (const t of toggles) {
                    const parent = t.closest('.bx--toggle, .bx--form-item');
                    if (parent && parent.textContent.includes('Bold')) {
                        t.click();
                    }
                }
            }
        })()
    `);
    await sleep(300);

    // Get baseline
    const baseline = await evaluate(`
        (function() {
            const cell = document.querySelector('.cell');
            const s = window.getComputedStyle(cell);
            return { fontSize: s.fontSize, fontWeight: s.fontWeight };
        })()
    `);
    console.log('[BASELINE] Small + Normal:', JSON.stringify(baseline));

    // Test 1: Change to Large
    console.log('\n[TEST 1] Changing font size to Large...');
    await evaluate(`
        (function() {
            const selects = document.querySelectorAll('select');
            for (const s of selects) {
                if (s.value === 'small') {
                    s.value = 'large';
                    s.dispatchEvent(new Event('change', { bubbles: true }));
                }
            }
        })()
    `);
    await sleep(300);

    const afterLarge = await evaluate(`
        (function() {
            const cell = document.querySelector('.cell');
            return window.getComputedStyle(cell).fontSize;
        })()
    `);
    console.log('After Large:', afterLarge);

    // Test 2: Click Bold toggle
    console.log('\n[TEST 2] Clicking Bold toggle...');
    await evaluate(`
        (function() {
            const toggles = document.querySelectorAll('.bx--toggle-input');
            for (const t of toggles) {
                const parent = t.closest('.bx--toggle, .bx--form-item');
                if (parent && parent.textContent.includes('Bold')) {
                    t.click();
                }
            }
        })()
    `);
    await sleep(300);

    const afterBold = await evaluate(`
        (function() {
            const cell = document.querySelector('.cell');
            return window.getComputedStyle(cell).fontWeight;
        })()
    `);
    console.log('After Bold:', afterBold);

    // Final verdict
    console.log('\n========================================');
    console.log('        FINAL VERDICT - BUILD 304');
    console.log('========================================\n');

    const sizeWorks = baseline.fontSize !== afterLarge;
    const boldWorks = baseline.fontWeight !== afterBold;

    console.log('UI-031 (Font Size):', sizeWorks ? '✅ VERIFIED FIXED' : '❌ STILL BROKEN');
    console.log('  Small:', baseline.fontSize, '→ Large:', afterLarge);

    console.log('\nUI-032 (Bold):', boldWorks ? '✅ VERIFIED FIXED' : '❌ STILL BROKEN');
    console.log('  Normal:', baseline.fontWeight, '→ Bold:', afterBold);

    if (sizeWorks && boldWorks) {
        console.log('\n🎉 BUILD 304: BOTH UI-031 AND UI-032 VERIFIED WORKING!');
        console.log('   Font settings now correctly apply to the grid.');
    } else {
        console.log('\n⚠️  Some issues remain.');
    }

    ws.close();
}

main().catch(console.error);
