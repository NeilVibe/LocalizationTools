/**
 * Check for network failures and other issues
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

    const page = targets.find(t => t.type === 'page' && t.url.includes('index.html'));
    if (!page) {
        console.error('App page not found');
        process.exit(1);
    }

    const ws = new WebSocket(page.webSocketDebuggerUrl);
    let id = 1;
    const failedRequests = [];
    const slowRequests = [];

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

    await send('Network.enable');

    // Track failed requests
    ws.on('message', (data) => {
        const msg = JSON.parse(data.toString());

        if (msg.method === 'Network.loadingFailed') {
            failedRequests.push({
                requestId: msg.params.requestId,
                errorText: msg.params.errorText,
                type: msg.params.type
            });
        }
    });

    console.log('Refreshing page to capture network activity...\n');
    await send('Page.enable');
    await send('Page.reload');
    await sleep(10000);

    // Get performance entries
    const perfData = await send('Runtime.evaluate', {
        expression: `
            const entries = performance.getEntriesByType('resource');
            const data = entries.map(e => ({
                name: e.name.split('/').pop().substring(0, 50),
                type: e.initiatorType,
                duration: e.duration.toFixed(0),
                size: e.transferSize || 0,
                status: e.responseStatus || 200
            }));

            // Get slow requests (> 1 second)
            const slow = data.filter(d => parseInt(d.duration) > 1000);

            // Get failed (0 size might indicate failure)
            const failed = data.filter(d => d.size === 0 && d.type !== 'fetch');

            JSON.stringify({ total: entries.length, slow, failed, sample: data.slice(0, 20) });
        `,
        returnByValue: true
    });

    // Get DOM stats
    const domStats = await send('Runtime.evaluate', {
        expression: `
            const allElements = document.querySelectorAll('*');
            const eventListeners = [];

            // Count by element type
            const tagCounts = {};
            allElements.forEach(el => {
                const tag = el.tagName.toLowerCase();
                tagCounts[tag] = (tagCounts[tag] || 0) + 1;
            });

            // Top elements
            const topTags = Object.entries(tagCounts)
                .sort((a, b) => b[1] - a[1])
                .slice(0, 15);

            // Check for duplicate IDs
            const ids = Array.from(document.querySelectorAll('[id]')).map(el => el.id);
            const dupeIds = ids.filter((id, i) => ids.indexOf(id) !== i);

            // Check for empty elements that shouldn't be empty
            const emptyDivs = document.querySelectorAll('div:empty').length;

            // Hidden elements taking up DOM
            const hiddenElements = document.querySelectorAll('[style*="display: none"], [hidden], .hidden').length;

            JSON.stringify({
                totalElements: allElements.length,
                topTags,
                duplicateIds: [...new Set(dupeIds)],
                emptyDivs,
                hiddenElements
            });
        `,
        returnByValue: true
    });

    // Check for memory issues
    const memoryInfo = await send('Runtime.evaluate', {
        expression: `
            if (performance.memory) {
                JSON.stringify({
                    usedJSHeap: (performance.memory.usedJSHeapSize / 1024 / 1024).toFixed(1) + ' MB',
                    totalJSHeap: (performance.memory.totalJSHeapSize / 1024 / 1024).toFixed(1) + ' MB',
                    limit: (performance.memory.jsHeapSizeLimit / 1024 / 1024).toFixed(1) + ' MB'
                });
            } else {
                JSON.stringify({ available: false });
            }
        `,
        returnByValue: true
    });

    console.log('='.repeat(60));
    console.log('NETWORK & DOM HEALTH REPORT');
    console.log('='.repeat(60));

    console.log('\n--- NETWORK STATS ---');
    if (perfData.result?.result?.value) {
        const data = JSON.parse(perfData.result.result.value);
        console.log(`Total requests: ${data.total}`);
        console.log(`Slow requests (>1s): ${data.slow.length}`);
        if (data.slow.length > 0) {
            data.slow.forEach(r => console.log(`  - ${r.name}: ${r.duration}ms`));
        }
        console.log(`Potentially failed: ${data.failed.length}`);
        if (data.failed.length > 0) {
            data.failed.slice(0, 10).forEach(r => console.log(`  - ${r.name}`));
        }
    }

    console.log('\n--- FAILED REQUESTS (CDP) ---');
    console.log(`Failed: ${failedRequests.length}`);
    failedRequests.forEach(r => console.log(`  - ${r.errorText}`));

    console.log('\n--- DOM STATS ---');
    if (domStats.result?.result?.value) {
        const data = JSON.parse(domStats.result.result.value);
        console.log(`Total DOM elements: ${data.totalElements}`);
        console.log(`Empty divs: ${data.emptyDivs}`);
        console.log(`Hidden elements: ${data.hiddenElements}`);
        console.log(`Duplicate IDs: ${data.duplicateIds.length}`);
        if (data.duplicateIds.length > 0) {
            console.log(`  ${data.duplicateIds.slice(0, 10).join(', ')}`);
        }
        console.log('\nTop element types:');
        data.topTags.forEach(([tag, count]) => {
            console.log(`  ${tag}: ${count}`);
        });
    }

    console.log('\n--- MEMORY ---');
    if (memoryInfo.result?.result?.value) {
        const data = JSON.parse(memoryInfo.result.result.value);
        if (data.available === false) {
            console.log('Memory API not available');
        } else {
            console.log(`Used JS Heap: ${data.usedJSHeap}`);
            console.log(`Total JS Heap: ${data.totalJSHeap}`);
            console.log(`Heap Limit: ${data.limit}`);
        }
    }

    ws.close();
}

main().catch(e => { console.error(e); process.exit(1); });
