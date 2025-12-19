/**
 * BUG-023 TM Status Check
 * Verifies TM status shows "ready" instead of "pending"
 */
const WebSocket = require('ws');
const http = require('http');
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function main() {
    console.log('=== BUG-023 TM STATUS CHECK ===\n');

    const targets = await new Promise((resolve, reject) => {
        http.get('http://127.0.0.1:9222/json', (res) => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => resolve(JSON.parse(data)));
        }).on('error', reject);
    });

    const page = targets.find(t => t.type === 'page');
    console.log('Page:', page.title);

    const ws = new WebSocket(page.webSocketDebuggerUrl);
    let id = 1;

    const send = (method, params = {}) => new Promise((resolve) => {
        const msgId = id++;
        const timeout = setTimeout(() => resolve({ timeout: true }), 15000);
        ws.on('message', function handler(data) {
            const msg = JSON.parse(data.toString());
            if (msg.id === msgId) {
                clearTimeout(timeout);
                ws.off('message', handler);
                resolve(msg);
            }
        });
        ws.send(JSON.stringify({ id: msgId, method, params }));
    });

    const evaluate = async (expression) => {
        const result = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
        return result.result?.result?.value;
    };

    await new Promise(resolve => ws.on('open', resolve));

    // Click on TM tab in the sidebar
    console.log('[1] Clicking TM tab...');
    const clickResult = await evaluate(`
        (function() {
            const tmTab = Array.from(document.querySelectorAll('button, .nav-item')).find(el =>
                el.textContent.trim() === 'TM'
            );
            if (tmTab) { tmTab.click(); return 'clicked TM tab'; }
            return 'TM tab not found';
        })()
    `);
    console.log('    Result:', clickResult);
    await sleep(1500);

    // Look for TM status indicators
    console.log('[2] Checking TM status...');
    const tmInfo = await evaluate(`
        (function() {
            const bodyText = document.body.innerText;

            // Check for status keywords
            const hasPending = bodyText.toLowerCase().includes('pending');
            const hasReady = bodyText.toLowerCase().includes('ready');
            const hasIndexing = bodyText.toLowerCase().includes('indexing');
            const hasActive = bodyText.toLowerCase().includes('active');

            // Find all text that might be status
            const statusMatches = bodyText.match(/(ready|pending|indexing|active|error|building)/gi) || [];

            // Look for TM-related sections
            const sections = [];
            document.querySelectorAll('.tm-item, [class*="status"], .badge').forEach(el => {
                const text = el.textContent.trim();
                if (text && text.length < 50) {
                    sections.push(text);
                }
            });

            return JSON.stringify({
                hasPending,
                hasReady,
                hasIndexing,
                hasActive,
                statusMatches: [...new Set(statusMatches)],
                statusSections: sections.slice(0, 20)
            });
        })()
    `);

    const info = JSON.parse(tmInfo || '{}');

    console.log('\n=== STATUS CHECK RESULTS ===');
    console.log('Found "pending":', info.hasPending);
    console.log('Found "ready":', info.hasReady);
    console.log('Found "indexing":', info.hasIndexing);
    console.log('Found "active":', info.hasActive);
    console.log('Status keywords found:', info.statusMatches?.join(', ') || '(none)');

    if (info.statusSections?.length) {
        console.log('\nStatus sections:');
        info.statusSections.forEach(s => console.log('  -', s));
    }

    // Get full page context
    console.log('\n[3] Getting page context...');
    const pageText = await evaluate(`document.body.innerText.substring(0, 1500)`);
    console.log('Page text preview:');
    console.log(pageText);

    // BUG-023 Verdict
    console.log('\n=============================');
    console.log('=== BUG-023 VERDICT ===');
    console.log('=============================');

    if (info.hasPending && !info.hasReady) {
        console.log('❌ FAIL: Found "pending" but no "ready"');
        console.log('   BUG-023 may not be fixed');
    } else if (info.hasReady || info.hasActive) {
        console.log('✅ PASS: Found "ready" or "active" status');
        console.log('   BUG-023 is FIXED!');
    } else if (!info.hasPending && !info.hasReady) {
        console.log('⚠️ INCONCLUSIVE: No TM status text visible');
        console.log('   Need to open TM Manager to verify');
    }

    ws.close();
}

main().catch(err => console.error('Error:', err));
