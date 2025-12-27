/**
 * Stress test - Trigger ALL possible errors by performing extensive interactions
 * This should reproduce the 1500+ errors the user saw
 */
const WebSocket = require('ws');
const http = require('http');
const fs = require('fs');

const sleep = ms => new Promise(r => setTimeout(r, ms));

async function main() {
    const targets = await new Promise((resolve, reject) => {
        http.get('http://127.0.0.1:9222/json', (res) => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => resolve(JSON.parse(data)));
        }).on('error', reject);
    });

    const page = targets.find(t => t.type === 'page' && t.url.includes('index.html'));
    if (!page) {
        console.error('App page not found');
        process.exit(1);
    }

    const ws = new WebSocket(page.webSocketDebuggerUrl);
    let id = 1;
    const allErrors = [];
    const allWarnings = [];
    const allMessages = [];

    const send = (method, params = {}) => new Promise((resolve, reject) => {
        const msgId = id++;
        const timeout = setTimeout(() => reject(new Error(`Timeout: ${method}`)), 30000);
        const handler = (msg) => {
            const r = JSON.parse(msg.toString());
            if (r.id === msgId) {
                clearTimeout(timeout);
                ws.off('message', handler);
                resolve(r);
            }
        };
        ws.on('message', handler);
        ws.send(JSON.stringify({ id: msgId, method, params }));
    });

    await new Promise(resolve => ws.on('open', resolve));

    // Enable ALL console/logging domains BEFORE reload
    await send('Console.enable');
    await send('Runtime.enable');
    await send('Log.enable');
    await send('Page.enable');
    await send('Network.enable');

    // Collect ALL messages
    ws.on('message', (data) => {
        const msg = JSON.parse(data.toString());

        if (msg.method === 'Console.messageAdded') {
            const entry = msg.params.message;
            allMessages.push({ source: 'Console', level: entry.level, text: entry.text?.substring(0, 200) });
            if (entry.level === 'error') allErrors.push(entry);
            if (entry.level === 'warning') allWarnings.push(entry);
        }

        if (msg.method === 'Runtime.consoleAPICalled') {
            const args = msg.params.args.map(a => a.value || a.description || '').join(' ');
            allMessages.push({ source: 'Runtime', level: msg.params.type, text: args.substring(0, 200) });
            if (msg.params.type === 'error') allErrors.push({ text: args });
            if (msg.params.type === 'warning') allWarnings.push({ text: args });
        }

        if (msg.method === 'Runtime.exceptionThrown') {
            const ex = msg.params.exceptionDetails;
            const text = ex.exception?.description || ex.text || 'Exception';
            allErrors.push({ level: 'exception', text: text.substring(0, 500) });
            allMessages.push({ source: 'Exception', level: 'exception', text: text.substring(0, 200) });
        }

        if (msg.method === 'Log.entryAdded') {
            const entry = msg.params.entry;
            allMessages.push({ source: 'Log', level: entry.level, text: entry.text?.substring(0, 200) });
            if (entry.level === 'error') allErrors.push(entry);
            if (entry.level === 'warning') allWarnings.push(entry);
        }
    });

    console.log('='.repeat(60));
    console.log('STRESS TEST - TRIGGERING ALL POSSIBLE ERRORS');
    console.log('='.repeat(60));

    // Reload page fresh
    console.log('\n1. Reloading page...');
    await send('Page.reload');
    await sleep(3000);

    // Helper to click at position
    async function click(x, y) {
        await send('Input.dispatchMouseEvent', { type: 'mousePressed', x, y, button: 'left', clickCount: 1 });
        await send('Input.dispatchMouseEvent', { type: 'mouseReleased', x, y, button: 'left', clickCount: 1 });
    }

    async function doubleClick(x, y) {
        await send('Input.dispatchMouseEvent', { type: 'mousePressed', x, y, button: 'left', clickCount: 2 });
        await send('Input.dispatchMouseEvent', { type: 'mouseReleased', x, y, button: 'left', clickCount: 2 });
    }

    async function hover(x, y) {
        await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x, y });
    }

    async function scroll(deltaY) {
        await send('Input.dispatchMouseEvent', {
            type: 'mouseWheel',
            x: 400, y: 400,
            deltaX: 0, deltaY
        });
    }

    async function evaluate(expr) {
        const result = await send('Runtime.evaluate', { expression: expr, returnByValue: true });
        return result.result?.result?.value;
    }

    // 2. Get grid dimensions
    console.log('\n2. Finding grid elements...');
    const gridInfo = await evaluate(`
        const grid = document.querySelector('.virtual-grid');
        const rows = document.querySelectorAll('.virtual-row');
        const cells = document.querySelectorAll('.cell');
        JSON.stringify({
            hasGrid: !!grid,
            rowCount: rows.length,
            cellCount: cells.length,
            firstRowRect: rows[0]?.getBoundingClientRect()
        });
    `);
    console.log('Grid info:', gridInfo);

    // 3. Hover over many cells rapidly
    console.log('\n3. Rapid hover over 50 positions...');
    for (let i = 0; i < 50; i++) {
        const x = 300 + (i % 10) * 50;
        const y = 200 + Math.floor(i / 10) * 60;
        await hover(x, y);
        await sleep(50);
    }
    console.log(`   After hover: ${allErrors.length} errors, ${allWarnings.length} warnings`);

    // 4. Click on many cells
    console.log('\n4. Clicking on 20 cells...');
    for (let i = 0; i < 20; i++) {
        const x = 350 + (i % 2) * 200;
        const y = 250 + Math.floor(i / 2) * 50;
        await click(x, y);
        await sleep(100);
    }
    console.log(`   After clicks: ${allErrors.length} errors, ${allWarnings.length} warnings`);

    // 5. Double-click to open edit modals
    console.log('\n5. Opening edit modals (double-click)...');
    for (let i = 0; i < 5; i++) {
        const y = 280 + i * 60;
        await doubleClick(550, y);
        await sleep(500);

        // Try to close by clicking X button area
        await click(740, 90);
        await sleep(300);

        // Try ESC key
        await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Escape', code: 'Escape' });
        await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Escape', code: 'Escape' });
        await sleep(300);

        // Click overlay to close
        await click(50, 400);
        await sleep(300);
    }
    console.log(`   After modals: ${allErrors.length} errors, ${allWarnings.length} warnings`);

    // 6. Scroll extensively
    console.log('\n6. Scrolling extensively...');
    for (let i = 0; i < 30; i++) {
        await scroll(500);
        await sleep(100);
    }
    console.log(`   After scroll down: ${allErrors.length} errors, ${allWarnings.length} warnings`);

    for (let i = 0; i < 30; i++) {
        await scroll(-500);
        await sleep(100);
    }
    console.log(`   After scroll up: ${allErrors.length} errors, ${allWarnings.length} warnings`);

    // 7. Rapid scroll (simulate fast scrolling)
    console.log('\n7. Rapid scrolling...');
    for (let i = 0; i < 50; i++) {
        await scroll(i % 2 === 0 ? 1000 : -1000);
        await sleep(30);
    }
    console.log(`   After rapid scroll: ${allErrors.length} errors, ${allWarnings.length} warnings`);

    // 8. Click everywhere
    console.log('\n8. Clicking random positions...');
    for (let i = 0; i < 30; i++) {
        const x = 100 + Math.random() * 600;
        const y = 100 + Math.random() * 600;
        await click(x, y);
        await sleep(50);
    }
    console.log(`   After random clicks: ${allErrors.length} errors, ${allWarnings.length} warnings`);

    // 9. Try to trigger network errors
    console.log('\n9. Triggering API calls...');
    await evaluate(`
        // Try to trigger TM suggestions for many rows
        for (let i = 0; i < 10; i++) {
            fetch('/api/ldm/tm/suggest?source=test' + i + '&threshold=0.3&max_results=5')
                .catch(e => console.error('TM fetch error:', e));
        }
    `);
    await sleep(2000);
    console.log(`   After API calls: ${allErrors.length} errors, ${allWarnings.length} warnings`);

    // 10. Force garbage collection and check memory
    console.log('\n10. Final check...');
    await sleep(2000);

    // Final report
    console.log('\n' + '='.repeat(60));
    console.log('STRESS TEST COMPLETE');
    console.log('='.repeat(60));

    console.log(`\nTotal messages collected: ${allMessages.length}`);
    console.log(`Total ERRORS: ${allErrors.length}`);
    console.log(`Total WARNINGS: ${allWarnings.length}`);

    // Group errors
    const errorCounts = {};
    allErrors.forEach(e => {
        const key = (e.text || '').substring(0, 100);
        if (!errorCounts[key]) errorCounts[key] = 0;
        errorCounts[key]++;
    });

    console.log('\n--- UNIQUE ERRORS (sorted by count) ---\n');
    Object.entries(errorCounts)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 50)
        .forEach(([key, count], i) => {
            console.log(`[${i + 1}] (${count}x) ${key}`);
        });

    // Group warnings
    const warningCounts = {};
    allWarnings.forEach(w => {
        const key = (w.text || '').substring(0, 100);
        if (!warningCounts[key]) warningCounts[key] = 0;
        warningCounts[key]++;
    });

    console.log('\n--- UNIQUE WARNINGS (sorted by count) ---\n');
    Object.entries(warningCounts)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 50)
        .forEach(([key, count], i) => {
            console.log(`[${i + 1}] (${count}x) ${key}`);
        });

    // Save full report
    const report = {
        timestamp: new Date().toISOString(),
        summary: {
            totalMessages: allMessages.length,
            totalErrors: allErrors.length,
            totalWarnings: allWarnings.length,
            uniqueErrors: Object.keys(errorCounts).length,
            uniqueWarnings: Object.keys(warningCounts).length
        },
        errorCounts,
        warningCounts,
        allErrors: allErrors.slice(0, 500),
        allWarnings: allWarnings.slice(0, 500)
    };

    fs.writeFileSync('stress_test_report.json', JSON.stringify(report, null, 2));
    console.log('\nFull report saved to: stress_test_report.json');

    ws.close();
}

main().catch(e => { console.error(e); process.exit(1); });
