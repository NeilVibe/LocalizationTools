/**
 * Captures ALL console errors by refreshing the page and collecting from start
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

    // Enable domains BEFORE reload
    await send('Console.enable');
    await send('Runtime.enable');
    await send('Log.enable');
    await send('Page.enable');
    await send('Network.enable');

    // Set up listeners
    ws.on('message', (data) => {
        const msg = JSON.parse(data.toString());

        if (msg.method === 'Console.messageAdded') {
            const entry = msg.params.message;
            allMessages.push({ source: 'Console', level: entry.level, text: entry.text, url: entry.url, line: entry.line });
            if (entry.level === 'error') allErrors.push(entry);
            if (entry.level === 'warning') allWarnings.push(entry);
        }

        if (msg.method === 'Runtime.consoleAPICalled') {
            const args = msg.params.args.map(a => {
                if (a.type === 'string') return a.value;
                if (a.description) return a.description;
                return JSON.stringify(a);
            }).join(' ');
            allMessages.push({ source: 'Runtime', level: msg.params.type, text: args });
            if (msg.params.type === 'error') allErrors.push({ text: args });
            if (msg.params.type === 'warning') allWarnings.push({ text: args });
        }

        if (msg.method === 'Runtime.exceptionThrown') {
            const ex = msg.params.exceptionDetails;
            const text = ex.exception?.description || ex.text || 'Exception';
            allErrors.push({ level: 'exception', text, url: ex.url, line: ex.lineNumber });
            allMessages.push({ source: 'Exception', level: 'exception', text, url: ex.url, line: ex.lineNumber });
        }

        if (msg.method === 'Log.entryAdded') {
            const entry = msg.params.entry;
            allMessages.push({ source: 'Log', level: entry.level, text: entry.text, url: entry.url });
            if (entry.level === 'error') allErrors.push(entry);
            if (entry.level === 'warning') allWarnings.push(entry);
        }
    });

    console.log('Reloading page to capture all console messages...\n');
    await send('Page.reload');

    // Wait for page load
    await new Promise((resolve) => {
        const checkLoad = (data) => {
            const msg = JSON.parse(data.toString());
            if (msg.method === 'Page.loadEventFired') {
                ws.off('message', checkLoad);
                resolve();
            }
        };
        ws.on('message', checkLoad);
    });

    console.log('Page loaded. Collecting messages for 15 seconds...\n');
    await sleep(15000);

    // Also check for any visible errors in the UI
    const uiErrors = await send('Runtime.evaluate', {
        expression: `
            const errors = [];

            // Check for error toasts/notifications
            document.querySelectorAll('[class*="error"], [class*="Error"], .bx--toast-notification--error').forEach(el => {
                if (el.textContent.trim()) errors.push({ type: 'error-element', text: el.textContent.substring(0, 200) });
            });

            // Check for failed network indicators
            document.querySelectorAll('[class*="fail"], [class*="Fail"]').forEach(el => {
                if (el.textContent.trim()) errors.push({ type: 'fail-element', text: el.textContent.substring(0, 200) });
            });

            // Count visible loading spinners (should be 0 when loaded)
            const loadingCount = document.querySelectorAll('.bx--loading:not([style*="display: none"]), [class*="loading"]:not([style*="display: none"])').length;
            errors.push({ type: 'loading-spinners', count: loadingCount });

            // Count total modals in DOM
            const modalCount = document.querySelectorAll('.bx--modal, [class*="modal"]').length;
            errors.push({ type: 'total-modals', count: modalCount });

            JSON.stringify(errors);
        `,
        returnByValue: true
    });

    console.log('='.repeat(60));
    console.log('CONSOLE ERROR/WARNING REPORT');
    console.log('='.repeat(60));

    console.log(`\nTotal messages: ${allMessages.length}`);
    console.log(`Total ERRORS: ${allErrors.length}`);
    console.log(`Total WARNINGS: ${allWarnings.length}`);

    // Group and count unique errors
    const errorCounts = {};
    allErrors.forEach(e => {
        const key = (e.text || '').substring(0, 150);
        if (!errorCounts[key]) errorCounts[key] = { count: 0, sample: e };
        errorCounts[key].count++;
    });

    console.log('\n--- UNIQUE ERRORS (sorted by count) ---\n');
    Object.entries(errorCounts)
        .sort((a, b) => b[1].count - a[1].count)
        .forEach(([key, data], i) => {
            console.log(`[${i + 1}] (${data.count}x) ${key}`);
            if (data.sample.url) console.log(`    @ ${data.sample.url}:${data.sample.line || '?'}`);
        });

    // Group and count unique warnings
    const warningCounts = {};
    allWarnings.forEach(w => {
        const key = (w.text || '').substring(0, 150);
        if (!warningCounts[key]) warningCounts[key] = { count: 0, sample: w };
        warningCounts[key].count++;
    });

    console.log('\n--- UNIQUE WARNINGS (sorted by count) ---\n');
    Object.entries(warningCounts)
        .sort((a, b) => b[1].count - a[1].count)
        .slice(0, 50) // Top 50 warnings
        .forEach(([key, data], i) => {
            console.log(`[${i + 1}] (${data.count}x) ${key}`);
        });

    console.log('\n--- UI STATE ISSUES ---\n');
    if (uiErrors.result?.result?.value) {
        JSON.parse(uiErrors.result.result.value).forEach(e => {
            console.log(`${e.type}: ${e.count !== undefined ? e.count : e.text}`);
        });
    }

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
        errors: Object.entries(errorCounts).map(([k, v]) => ({ text: k, count: v.count, url: v.sample.url })),
        warnings: Object.entries(warningCounts).map(([k, v]) => ({ text: k, count: v.count })),
        allMessages
    };

    fs.writeFileSync('console_errors_report.json', JSON.stringify(report, null, 2));
    console.log('\nFull report saved to: console_errors_report.json');

    ws.close();
}

main().catch(e => { console.error(e); process.exit(1); });
