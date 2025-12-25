/**
 * Check TM Status - Find a TM that's ready for testing
 */
const WebSocket = require('ws');
const http = require('http');
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function main() {
    console.log('=== CHECK TM STATUS ===\n');

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

    // Go to TM tab and open TM Manager
    await evaluate(`
        const tmTab = Array.from(document.querySelectorAll('button')).find(b =>
            b.textContent.trim() === 'TM' && b.className.includes('tab-button')
        );
        if (tmTab) tmTab.click();
    `);
    await sleep(800);

    await evaluate(`
        const tmItem = document.querySelector('.tm-item');
        if (tmItem) tmItem.click();
    `);
    await sleep(500);

    await evaluate(`
        const btn = Array.from(document.querySelectorAll('button')).find(b =>
            b.textContent.includes('Open TM Manager')
        );
        if (btn) btn.click();
    `);
    await sleep(1500);

    // Get all TMs and their statuses
    const tmList = await evaluate(`
        (function() {
            const rows = document.querySelectorAll('table tbody tr');
            const tms = [];

            rows.forEach(row => {
                const cells = row.querySelectorAll('td');
                if (cells.length >= 4) {
                    const name = cells[0]?.textContent.trim();
                    const entries = cells[1]?.textContent.trim();
                    const languages = cells[2]?.textContent.trim();
                    const status = cells[3]?.textContent.trim();

                    // Check for View Entries button
                    const viewBtn = row.querySelector('button');
                    const hasViewEntries = viewBtn?.textContent.includes('View Entries');

                    tms.push({
                        name: name?.substring(0, 30),
                        entries,
                        languages,
                        status,
                        hasViewEntries
                    });
                }
            });

            return JSON.stringify(tms);
        })()
    `);

    console.log('TM List:');
    const tms = JSON.parse(tmList || '[]');
    tms.forEach((tm, i) => {
        const statusIcon = tm.status === 'ready' || tm.status === 'active' ? '✅' :
                          tm.status === 'indexing' ? '⏳' :
                          tm.status === 'error' ? '❌' : '❓';
        console.log(`  [${i}] ${statusIcon} ${tm.name} | ${tm.entries} | ${tm.status}`);
    });

    // Find a TM that's ready
    const readyTM = tms.find(tm =>
        tm.status?.toLowerCase() === 'ready' ||
        tm.status?.toLowerCase() === 'active' ||
        tm.status?.toLowerCase() === 'completed'
    );

    if (readyTM) {
        console.log(`\n✅ Found ready TM: ${readyTM.name}`);
    } else {
        console.log('\n⚠️ No ready TMs found. Available statuses:');
        const statuses = [...new Set(tms.map(t => t.status))];
        console.log('  ', statuses.join(', '));
    }

    // Try clicking View Entries on first TM anyway to see what happens
    console.log('\n[Attempting to view first TM entries...]');
    await evaluate(`
        const viewBtn = Array.from(document.querySelectorAll('button')).find(b =>
            b.textContent.includes('View Entries')
        );
        if (viewBtn) viewBtn.click();
    `);
    await sleep(3000);

    // Check what appeared
    const afterView = await evaluate(`
        (function() {
            const body = document.body.innerText;
            const hasSource = body.includes('Source');
            const hasTarget = body.includes('Target');
            const hasError = body.includes('error') || body.includes('Error');
            const hasLoading = body.includes('Loading') || body.includes('loading');

            // Check for entries table
            const tables = document.querySelectorAll('table');
            let entriesTable = null;
            for (const t of tables) {
                const headers = Array.from(t.querySelectorAll('th')).map(h => h.textContent);
                if (headers.some(h => h.includes('Source') || h.includes('Target'))) {
                    entriesTable = {
                        headers,
                        rows: t.querySelectorAll('tbody tr').length
                    };
                    break;
                }
            }

            return JSON.stringify({
                hasSource,
                hasTarget,
                hasError,
                hasLoading,
                entriesTable,
                bodySnippet: body.substring(0, 500)
            });
        })()
    `);

    console.log('\nAfter clicking View Entries:');
    const result = JSON.parse(afterView || '{}');
    console.log('  Has Source column:', result.hasSource);
    console.log('  Has Target column:', result.hasTarget);
    console.log('  Has Error:', result.hasError);
    console.log('  Entries table:', result.entriesTable ? `${result.entriesTable.rows} rows` : 'not found');
    console.log('\nBody snippet:', result.bodySnippet?.substring(0, 300));

    ws.close();
    console.log('\n=== CHECK COMPLETE ===');
}

main().catch(err => console.error('Error:', err));
