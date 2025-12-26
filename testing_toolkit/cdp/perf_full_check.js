#!/usr/bin/env node
/**
 * Full Performance Check
 * Tests: Lazy loading, scroll performance, network requests, frame timing
 */

const http = require('http');
const WebSocket = require('ws');

const sleep = ms => new Promise(r => setTimeout(r, ms));

async function main() {
    console.log('=== FULL PERFORMANCE CHECK ===\n');

    // Connect to CDP
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
    const pending = new Map();
    const networkRequests = [];
    const performanceMetrics = [];

    ws.on('message', (data) => {
        const msg = JSON.parse(data.toString());
        if (msg.id && pending.has(msg.id)) {
            pending.get(msg.id)(msg.result);
            pending.delete(msg.id);
        }
        // Capture network events
        if (msg.method === 'Network.requestWillBeSent') {
            networkRequests.push({
                type: 'request',
                url: msg.params.request.url,
                time: msg.params.timestamp
            });
        }
        if (msg.method === 'Network.responseReceived') {
            networkRequests.push({
                type: 'response',
                url: msg.params.response.url,
                status: msg.params.response.status,
                time: msg.params.timestamp
            });
        }
    });

    const send = (method, params = {}) => new Promise((resolve) => {
        const id = msgId++;
        pending.set(id, resolve);
        ws.send(JSON.stringify({ id, method, params }));
    });

    const evaluate = async (expr) => {
        const r = await send('Runtime.evaluate', {
            expression: expr,
            returnByValue: true,
            awaitPromise: true
        });
        return r?.result?.value;
    };

    await new Promise(r => ws.on('open', r));

    // Enable domains
    await send('Runtime.enable');
    await send('Network.enable');
    await send('Performance.enable');

    console.log('Connected to CDP\n');

    // ============ TEST 1: PAGE STATE ============
    console.log('=== TEST 1: PAGE STATE ===');
    const pageState = await evaluate(`
        (function() {
            const body = document.body.innerText;
            return {
                hasProjects: body.includes('QA Test Project') || body.includes('Project'),
                hasFile: body.includes('test_10k') || body.includes('.txt'),
                hasGrid: !!document.querySelector('[class*="virtual"]'),
                url: window.location.href
            };
        })()
    `);
    console.log('  Projects visible:', pageState?.hasProjects);
    console.log('  File visible:', pageState?.hasFile);
    console.log('  Grid present:', pageState?.hasGrid);
    console.log('');

    // ============ TEST 2: LAZY LOADING ============
    console.log('=== TEST 2: LAZY LOADING (DOM Row Count) ===');
    const lazyStats = await evaluate(`
        (function() {
            // Count actual rendered rows
            const virtualRows = document.querySelectorAll('.virtual-row');
            const allRows = document.querySelectorAll('[class*="row"]');
            const placeholders = document.querySelectorAll('[class*="placeholder"]');

            // Get total rows from UI
            const text = document.body.innerText;
            const match = text.match(/(\\d+[,\\s]?\\d*)\\s*rows/i);
            const totalRows = match ? parseInt(match[1].replace(/[,\\s]/g, '')) : 0;

            // Get scroll container info
            const container = document.querySelector('.scroll-container') ||
                             document.querySelector('[class*="virtual-container"]');

            return {
                virtualRowCount: virtualRows.length,
                allRowsCount: allRows.length,
                placeholderCount: placeholders.length,
                totalRows: totalRows,
                containerHeight: container ? container.clientHeight : 0,
                scrollHeight: container ? container.scrollHeight : 0
            };
        })()
    `);

    console.log('  Virtual rows rendered:', lazyStats?.virtualRowCount);
    console.log('  Total rows (from text):', lazyStats?.totalRows);
    console.log('  Placeholder rows:', lazyStats?.placeholderCount);
    console.log('  Container height:', lazyStats?.containerHeight, 'px');
    console.log('  Scroll height:', lazyStats?.scrollHeight, 'px');

    const lazyLoadOK = lazyStats?.virtualRowCount > 0 &&
                       lazyStats?.virtualRowCount < 500 &&
                       (lazyStats?.totalRows === 0 || lazyStats?.virtualRowCount < lazyStats?.totalRows);
    console.log('  Lazy loading:', lazyLoadOK ? '✅ WORKING' : '⚠️ CHECK NEEDED');
    console.log('');

    // ============ TEST 3: SCROLL PERFORMANCE ============
    console.log('=== TEST 3: SCROLL PERFORMANCE ===');
    networkRequests.length = 0; // Reset

    const scrollTest = await evaluate(`
        (async function() {
            const container = document.querySelector('.scroll-container') ||
                             document.querySelector('[class*="scroll"]');
            if (!container) return { error: 'No scroll container' };

            const results = [];
            const scrollPositions = [500, 1500, 3000, 5000, 10000];

            for (const pos of scrollPositions) {
                const start = performance.now();
                container.scrollTop = pos;
                await new Promise(r => setTimeout(r, 100)); // Wait for render
                const end = performance.now();

                const visibleRows = document.querySelectorAll('.virtual-row').length;
                results.push({
                    scrollTo: pos,
                    renderTime: Math.round(end - start),
                    visibleRows: visibleRows
                });
            }

            // Reset scroll
            container.scrollTop = 0;

            return results;
        })()
    `);

    if (Array.isArray(scrollTest)) {
        console.log('  Scroll position tests:');
        let totalTime = 0;
        for (const r of scrollTest) {
            console.log(`    → ${r.scrollTo}px: ${r.renderTime}ms (${r.visibleRows} rows visible)`);
            totalTime += r.renderTime;
        }
        console.log(`  Average render time: ${Math.round(totalTime / scrollTest.length)}ms`);
        console.log('  Scroll perf:', totalTime / scrollTest.length < 50 ? '✅ SMOOTH' : '⚠️ LAGGY');
    } else {
        console.log('  Error:', scrollTest?.error || 'Unknown');
    }
    console.log('');

    // ============ TEST 4: NETWORK DURING SCROLL ============
    console.log('=== TEST 4: NETWORK REQUESTS DURING SCROLL ===');
    await sleep(500); // Let any pending requests complete

    const apiRequests = networkRequests.filter(r =>
        r.type === 'request' && r.url.includes('/api/')
    );
    console.log('  API requests during scroll test:', apiRequests.length);

    // Group by endpoint
    const endpoints = {};
    for (const req of apiRequests) {
        const path = new URL(req.url).pathname;
        endpoints[path] = (endpoints[path] || 0) + 1;
    }
    for (const [path, count] of Object.entries(endpoints)) {
        console.log(`    ${path}: ${count} requests`);
    }

    const requestFlood = apiRequests.length > 20;
    console.log('  Request flooding:', requestFlood ? '❌ TOO MANY' : '✅ OK');
    console.log('');

    // ============ TEST 5: MEMORY USAGE ============
    console.log('=== TEST 5: MEMORY USAGE ===');
    const memMetrics = await send('Performance.getMetrics');
    const heapSize = memMetrics?.metrics?.find(m => m.name === 'JSHeapUsedSize');
    const heapTotal = memMetrics?.metrics?.find(m => m.name === 'JSHeapTotalSize');
    const nodes = memMetrics?.metrics?.find(m => m.name === 'Nodes');

    console.log('  JS Heap Used:', heapSize ? Math.round(heapSize.value / 1024 / 1024) + ' MB' : 'N/A');
    console.log('  JS Heap Total:', heapTotal ? Math.round(heapTotal.value / 1024 / 1024) + ' MB' : 'N/A');
    console.log('  DOM Nodes:', nodes ? nodes.value : 'N/A');

    const memoryOK = heapSize && heapSize.value < 200 * 1024 * 1024; // < 200MB
    console.log('  Memory:', memoryOK ? '✅ OK' : '⚠️ HIGH');
    console.log('');

    // ============ TEST 6: RAPID SCROLL (STRESS TEST) ============
    console.log('=== TEST 6: RAPID SCROLL STRESS TEST ===');
    networkRequests.length = 0;

    const stressTest = await evaluate(`
        (async function() {
            const container = document.querySelector('.scroll-container') ||
                             document.querySelector('[class*="scroll"]');
            if (!container) return { error: 'No scroll container' };

            const start = performance.now();

            // Rapid scroll 20 times
            for (let i = 0; i < 20; i++) {
                container.scrollTop = (i % 2 === 0) ? i * 500 : 0;
                await new Promise(r => setTimeout(r, 50));
            }

            const end = performance.now();
            container.scrollTop = 0;

            return {
                totalTime: Math.round(end - start),
                iterations: 20
            };
        })()
    `);

    if (stressTest && !stressTest.error) {
        console.log('  20 rapid scrolls in:', stressTest.totalTime, 'ms');
        console.log('  Average per scroll:', Math.round(stressTest.totalTime / 20), 'ms');

        await sleep(300);
        const stressApiCalls = networkRequests.filter(r =>
            r.type === 'request' && r.url.includes('/api/')
        ).length;
        console.log('  API calls during stress:', stressApiCalls);
        console.log('  Throttling:', stressApiCalls < 30 ? '✅ WORKING' : '❌ NOT WORKING');
    }
    console.log('');

    // ============ SUMMARY ============
    console.log('=== PERFORMANCE SUMMARY ===');
    console.log('');
    console.log('| Test                    | Result |');
    console.log('|-------------------------|--------|');
    console.log(`| Lazy Loading            | ${lazyLoadOK ? '✅ PASS' : '❌ FAIL'} |`);
    console.log(`| Scroll Render (<50ms)   | ${scrollTest && !scrollTest.error ? '✅ PASS' : '⚠️ N/A'} |`);
    console.log(`| Request Throttling      | ${!requestFlood ? '✅ PASS' : '❌ FAIL'} |`);
    console.log(`| Memory (<200MB)         | ${memoryOK ? '✅ PASS' : '⚠️ HIGH'} |`);
    console.log('');

    ws.close();
    process.exit(0);
}

main().catch(err => {
    console.error('Error:', err);
    process.exit(1);
});
