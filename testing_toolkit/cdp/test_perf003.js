#!/usr/bin/env node
/**
 * Test PERF-003: Lazy loading works (no scroll lag)
 */

const http = require('http');
const WebSocket = require('ws');

async function main() {
    console.log('=== PERF-003: Lazy Loading Test ===\n');

    const targets = await new Promise((resolve, reject) => {
        http.get('http://127.0.0.1:9222/json', (res) => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => resolve(JSON.parse(data)));
        }).on('error', reject);
    });

    const page = targets.find(t => t.type === 'page');
    if (!page) { console.log('ERROR: No page found'); process.exit(1); }

    const ws = new WebSocket(page.webSocketDebuggerUrl);
    let msgId = 1;

    const send = (method, params = {}) => new Promise((resolve) => {
        const id = msgId++;
        const handler = (data) => {
            const msg = JSON.parse(data.toString());
            if (msg.id === id) { ws.off('message', handler); resolve(msg.result); }
        };
        ws.on('message', handler);
        ws.send(JSON.stringify({ id, method, params }));
    });

    const evaluate = async (expr) => {
        const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
        return r.result?.value;
    };

    await new Promise(r => ws.on('open', r));
    await send('Runtime.enable');

    // Check if file is loaded
    const fileInfo = await evaluate(`
        (function() {
            const text = document.body.innerText;
            const match = text.match(/(\\d+[,\\s]?\\d*)\\s*rows/i);
            return {
                hasFile: text.includes('test_10k') || text.includes('SOURCE'),
                totalRows: match ? parseInt(match[1].replace(/[,\\s]/g, '')) : 0
            };
        })()
    `);
    console.log('File loaded:', fileInfo?.hasFile);
    console.log('Total rows:', fileInfo?.totalRows);

    // Check virtual grid rendering
    const gridStats = await evaluate(`
        (function() {
            // Count rendered rows - use the Svelte class name pattern
            const virtualRows = document.querySelectorAll('.virtual-row');
            const allVirtualEls = document.querySelectorAll('[class*="virtual"]');

            // Get container info
            const scrollContainer = document.querySelector('.scroll-container');
            const virtualContainer = document.querySelector('.virtual-container');
            const virtualGrid = document.querySelector('.virtual-grid');

            return {
                virtualRowCount: virtualRows.length,
                virtualElements: allVirtualEls.length,
                hasVirtualGrid: !!virtualGrid,
                containerHeight: virtualContainer ? virtualContainer.style.height : 'N/A',
                scrollable: scrollContainer ? scrollContainer.scrollHeight > scrollContainer.clientHeight : false
            };
        })()
    `);

    console.log('\nGrid stats:');
    console.log('  Virtual rows rendered:', gridStats?.virtualRowCount);
    console.log('  Virtual elements total:', gridStats?.virtualElements);
    console.log('  Has virtual grid:', gridStats?.hasVirtualGrid);
    console.log('  Container height:', gridStats?.containerHeight);
    console.log('  Scrollable:', gridStats?.scrollable);

    // Determine if lazy loading is working
    // Lazy loading = rendering fewer rows than total
    const renderedRows = gridStats?.virtualRowCount || 0;
    const totalRows = fileInfo?.totalRows || 0;

    console.log('\n=== RESULT ===');

    if (totalRows === 0) {
        console.log('PERF-003 (Lazy loading): ⚠️ CANNOT VERIFY (no file loaded)');
        ws.close();
        process.exit(1);
    }

    // Pass if rendered rows is significantly less than total
    // (typical virtualization renders ~20-100 rows max for visible area + buffer)
    const lazyLoadOK = renderedRows > 0 && renderedRows < 500 && renderedRows < totalRows;

    if (lazyLoadOK) {
        console.log('PERF-003 (Lazy loading): ✅ PASS');
        console.log(`  Rendered ${renderedRows} rows instead of ${totalRows} (${((renderedRows/totalRows)*100).toFixed(1)}%)`);
    } else {
        console.log('PERF-003 (Lazy loading): ❌ FAIL');
        console.log(`  Rendered ${renderedRows} rows out of ${totalRows}`);
        console.log('  Expected < 500 rendered rows for lazy loading');
    }

    ws.close();
    process.exit(lazyLoadOK ? 0 : 1);
}

main().catch(err => {
    console.error('Error:', err);
    process.exit(1);
});
