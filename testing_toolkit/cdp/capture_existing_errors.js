/**
 * Capture existing errors from the console by checking what's already there
 * and monitoring for 30 seconds of normal interaction
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

    const send = (method, params = {}) => new Promise((resolve, reject) => {
        const msgId = id++;
        const timeout = setTimeout(() => resolve({ error: 'timeout' }), 10000);
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

    // Enable console
    await send('Console.enable');
    await send('Runtime.enable');
    await send('Log.enable');

    // Collect messages
    ws.on('message', (data) => {
        const msg = JSON.parse(data.toString());

        if (msg.method === 'Console.messageAdded') {
            const entry = msg.params.message;
            if (entry.level === 'error') allErrors.push({ text: entry.text, url: entry.url, line: entry.line });
            if (entry.level === 'warning') allWarnings.push({ text: entry.text });
        }

        if (msg.method === 'Runtime.consoleAPICalled') {
            const args = msg.params.args.map(a => a.value || a.description || '').join(' ');
            if (msg.params.type === 'error') allErrors.push({ text: args });
            if (msg.params.type === 'warning') allWarnings.push({ text: args });
        }

        if (msg.method === 'Runtime.exceptionThrown') {
            const ex = msg.params.exceptionDetails;
            allErrors.push({
                level: 'exception',
                text: ex.exception?.description || ex.text,
                url: ex.url,
                line: ex.lineNumber
            });
        }
    });

    console.log('='.repeat(60));
    console.log('CAPTURING ERRORS - 60 second interaction test');
    console.log('='.repeat(60));

    async function evaluate(expr) {
        const result = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
        return result.result?.result?.value;
    }

    // Don't reload - work with current state to capture accumulated errors

    // 1. Check current state
    console.log('\n1. Current app state...');
    const appState = await evaluate(`
        JSON.stringify({
            url: window.location.href,
            rowCount: document.querySelectorAll('.virtual-row').length,
            cellCount: document.querySelectorAll('.cell').length,
            modalCount: document.querySelectorAll('.bx--modal, [class*="modal"]').length,
            loadingCount: document.querySelectorAll('.bx--loading, [class*="loading"]').length,
            hasEditModal: !!document.querySelector('.edit-modal-overlay')
        });
    `);
    console.log('State:', appState);

    // 2. Close any open modals first
    console.log('\n2. Trying to close any open modals...');
    await evaluate(`
        // Try clicking all close buttons
        document.querySelectorAll('.close-btn, .bx--modal-close, [class*="close"]').forEach(btn => {
            try { btn.click(); } catch(e) {}
        });
        // Press ESC
        document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
    `);
    await sleep(500);

    // 3. Scroll using JavaScript
    console.log('\n3. Scrolling via JavaScript...');
    for (let i = 0; i < 20; i++) {
        await evaluate(`
            const container = document.querySelector('.scroll-container');
            if (container) container.scrollTop += 200;
        `);
        await sleep(100);
    }
    console.log(`   Errors so far: ${allErrors.length}, Warnings: ${allWarnings.length}`);

    // Scroll back up
    for (let i = 0; i < 20; i++) {
        await evaluate(`
            const container = document.querySelector('.scroll-container');
            if (container) container.scrollTop -= 200;
        `);
        await sleep(100);
    }
    console.log(`   After scroll back: Errors: ${allErrors.length}, Warnings: ${allWarnings.length}`);

    // 4. Click on cells
    console.log('\n4. Clicking cells via JavaScript...');
    await evaluate(`
        const cells = document.querySelectorAll('.cell.target');
        cells.forEach((cell, i) => {
            if (i < 10) {
                setTimeout(() => {
                    cell.click();
                    cell.dispatchEvent(new MouseEvent('dblclick', { bubbles: true }));
                }, i * 200);
            }
        });
    `);
    await sleep(3000);
    console.log(`   Errors so far: ${allErrors.length}, Warnings: ${allWarnings.length}`);

    // 5. Hover simulation
    console.log('\n5. Hover simulation...');
    await evaluate(`
        const rows = document.querySelectorAll('.virtual-row');
        rows.forEach((row, i) => {
            if (i < 30) {
                setTimeout(() => {
                    row.dispatchEvent(new MouseEvent('mouseenter', { bubbles: true }));
                    row.dispatchEvent(new MouseEvent('mouseover', { bubbles: true }));
                }, i * 50);
            }
        });
    `);
    await sleep(2000);
    console.log(`   Errors so far: ${allErrors.length}, Warnings: ${allWarnings.length}`);

    // 6. Trigger various events
    console.log('\n6. Triggering various events...');
    await evaluate(`
        // Trigger resize
        window.dispatchEvent(new Event('resize'));

        // Trigger scroll events
        const container = document.querySelector('.scroll-container');
        if (container) {
            for (let i = 0; i < 50; i++) {
                container.dispatchEvent(new Event('scroll'));
            }
        }

        // Try to access non-existent APIs
        try { fetch('/api/nonexistent'); } catch(e) {}
        try { fetch('/api/ldm/tm/suggest?source=test'); } catch(e) {}
    `);
    await sleep(2000);
    console.log(`   Errors so far: ${allErrors.length}, Warnings: ${allWarnings.length}`);

    // 7. Try to force errors
    console.log('\n7. Attempting to force errors...');
    await evaluate(`
        // Try operations that might fail
        try {
            const rows = [];
            rows[999999].click(); // Should throw
        } catch(e) { console.error('Test error 1:', e.message); }

        try {
            document.querySelector('.nonexistent-element').click();
        } catch(e) { console.error('Test error 2:', e.message); }
    `);
    await sleep(1000);

    // 8. Monitor for 10 more seconds
    console.log('\n8. Monitoring for 10 more seconds...');
    for (let i = 0; i < 10; i++) {
        await sleep(1000);
        process.stdout.write(`   ${10-i}s remaining - Errors: ${allErrors.length}, Warnings: ${allWarnings.length}\r`);
    }
    console.log('');

    // Final report
    console.log('\n' + '='.repeat(60));
    console.log('CAPTURE COMPLETE');
    console.log('='.repeat(60));

    console.log(`\nTotal ERRORS: ${allErrors.length}`);
    console.log(`Total WARNINGS: ${allWarnings.length}`);

    // Group and display errors
    const errorCounts = {};
    allErrors.forEach(e => {
        const key = (e.text || '').substring(0, 120);
        if (!errorCounts[key]) errorCounts[key] = { count: 0, sample: e };
        errorCounts[key].count++;
    });

    console.log('\n--- ALL UNIQUE ERRORS ---\n');
    Object.entries(errorCounts)
        .sort((a, b) => b[1].count - a[1].count)
        .forEach(([key, data], i) => {
            console.log(`[${i + 1}] (${data.count}x) ${key}`);
            if (data.sample.url) console.log(`    @ ${data.sample.url}:${data.sample.line || '?'}`);
        });

    // Group and display warnings
    const warningCounts = {};
    allWarnings.forEach(w => {
        const key = (w.text || '').substring(0, 120);
        if (!warningCounts[key]) warningCounts[key] = 0;
        warningCounts[key]++;
    });

    if (Object.keys(warningCounts).length > 0) {
        console.log('\n--- ALL UNIQUE WARNINGS ---\n');
        Object.entries(warningCounts)
            .sort((a, b) => b[1] - a[1])
            .forEach(([key, count], i) => {
                console.log(`[${i + 1}] (${count}x) ${key}`);
            });
    }

    // Check if there might be more errors we're not seeing
    const consoleCheck = await evaluate(`
        // Check if there's a way to see console history
        const checks = [];

        // Check for React/Svelte error boundaries
        const errorBoundaries = document.querySelectorAll('[class*="error"], [class*="Error"]');
        checks.push('Error elements in DOM: ' + errorBoundaries.length);

        // Check for any error toasts
        const toasts = document.querySelectorAll('.bx--toast-notification--error');
        checks.push('Error toasts: ' + toasts.length);

        // Check performance
        const perfEntries = performance.getEntriesByType('resource').filter(e => e.transferSize === 0 && e.duration > 0);
        checks.push('Failed resource loads: ' + perfEntries.length);

        checks.join('\\n');
    `);
    console.log('\n--- ADDITIONAL CHECKS ---\n');
    console.log(consoleCheck);

    // Save report
    fs.writeFileSync('error_capture_report.json', JSON.stringify({
        timestamp: new Date().toISOString(),
        totalErrors: allErrors.length,
        totalWarnings: allWarnings.length,
        errors: allErrors,
        warnings: allWarnings
    }, null, 2));
    console.log('\nReport saved to: error_capture_report.json');

    ws.close();
}

main().catch(e => { console.error(e); process.exit(1); });
