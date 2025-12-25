/**
 * Explore Entries Table - Look inside the TM viewer
 */
const WebSocket = require('ws');
const http = require('http');
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function main() {
    console.log('=== EXPLORE ENTRIES TABLE ===\n');

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

    // Open TM Manager
    console.log('[1] Opening TM Manager...');
    await evaluate(`document.querySelector('button.tab-button:not(.active)')?.click()`);
    await sleep(500);
    await evaluate(`
        const tmTab = Array.from(document.querySelectorAll('button')).find(b =>
            b.textContent.trim() === 'TM' && b.className.includes('tab-button')
        );
        if (tmTab) tmTab.click();
    `);
    await sleep(800);
    await evaluate(`document.querySelector('.tm-item')?.click()`);
    await sleep(500);
    await evaluate(`
        Array.from(document.querySelectorAll('button')).find(b =>
            b.textContent.includes('Open TM Manager')
        )?.click()
    `);
    await sleep(1500);

    // Click View Entries on ready TM
    console.log('[2] Clicking View Entries...');
    await evaluate(`
        (function() {
            const rows = document.querySelectorAll('table tbody tr');
            for (const row of rows) {
                const status = row.querySelectorAll('td')[3]?.textContent.trim().toLowerCase();
                if (status === 'ready') {
                    Array.from(row.querySelectorAll('button')).find(b =>
                        b.textContent.includes('View Entries')
                    )?.click();
                    return;
                }
            }
        })()
    `);
    await sleep(3000);

    // Explore the tm-viewer element
    console.log('\n[3] Exploring tm-viewer element:');
    const viewerInfo = await evaluate(`
        (function() {
            const viewer = document.querySelector('.tm-viewer');
            if (!viewer) return JSON.stringify({ found: false });

            return JSON.stringify({
                found: true,
                class: viewer.className,
                innerHTML: viewer.innerHTML.substring(0, 1500),
                childCount: viewer.children.length,
                children: Array.from(viewer.children).map(c => ({
                    class: c.className,
                    tag: c.tagName,
                    text: c.textContent.substring(0, 100)
                }))
            });
        })()
    `);
    console.log(viewerInfo);

    // Explore entries-table specifically
    console.log('\n[4] Exploring entries-table:');
    const tableInfo = await evaluate(`
        (function() {
            const entriesTable = document.querySelector('.entries-table');
            if (!entriesTable) return JSON.stringify({ found: false });

            const table = entriesTable.querySelector('table');
            if (table) {
                const headers = Array.from(table.querySelectorAll('th')).map(h => h.textContent.trim());
                const rows = table.querySelectorAll('tbody tr');
                const rowData = Array.from(rows).slice(0, 3).map(row => {
                    const cells = row.querySelectorAll('td');
                    const buttons = row.querySelectorAll('button');
                    return {
                        cells: Array.from(cells).map(c => c.textContent.substring(0, 30)),
                        buttonTitles: Array.from(buttons).map(b => b.getAttribute('title'))
                    };
                });

                return JSON.stringify({
                    found: true,
                    hasTable: true,
                    headers,
                    rowCount: rows.length,
                    sampleRows: rowData
                });
            }

            return JSON.stringify({
                found: true,
                hasTable: false,
                innerHTML: entriesTable.innerHTML.substring(0, 500),
                text: entriesTable.textContent.substring(0, 200)
            });
        })()
    `);
    console.log(tableInfo);

    // Check viewer-toolbar
    console.log('\n[5] Exploring viewer-toolbar:');
    const toolbarInfo = await evaluate(`
        (function() {
            const toolbar = document.querySelector('.viewer-toolbar');
            if (!toolbar) return JSON.stringify({ found: false });

            const buttons = toolbar.querySelectorAll('button');
            const inputs = toolbar.querySelectorAll('input');
            const selects = toolbar.querySelectorAll('select, .bx--dropdown, .bx--list-box');

            return JSON.stringify({
                found: true,
                buttons: Array.from(buttons).map(b => ({
                    text: b.textContent.trim().substring(0, 30),
                    title: b.getAttribute('title')
                })),
                inputs: Array.from(inputs).map(i => ({
                    type: i.type,
                    placeholder: i.placeholder
                })),
                selects: Array.from(selects).map(s => ({
                    class: s.className.substring(0, 40),
                    text: s.textContent.substring(0, 50)
                })),
                text: toolbar.textContent.substring(0, 200)
            });
        })()
    `);
    console.log(toolbarInfo);

    // Check for TMViewer (capital V)
    console.log('\n[6] Looking for TMViewer component:');
    const TMViewerInfo = await evaluate(`
        (function() {
            const tmViewer = document.querySelector('[class*="TMViewer"]');
            if (!tmViewer) return JSON.stringify({ found: false, note: 'No TMViewer class found' });

            return JSON.stringify({
                found: true,
                class: tmViewer.className,
                text: tmViewer.textContent.substring(0, 200)
            });
        })()
    `);
    console.log(TMViewerInfo);

    // Get the second visible modal (the viewer modal)
    console.log('\n[7] Checking second visible modal:');
    const secondModal = await evaluate(`
        (function() {
            const modals = document.querySelectorAll('.bx--modal.is-visible');
            if (modals.length < 2) return JSON.stringify({ found: false, count: modals.length });

            const modal = modals[1];
            const tables = modal.querySelectorAll('table');
            const tableInfo = [];

            tables.forEach((t, i) => {
                const headers = Array.from(t.querySelectorAll('th')).map(h => h.textContent.trim());
                const rows = t.querySelectorAll('tbody tr').length;
                tableInfo.push({ index: i, headers, rows });
            });

            return JSON.stringify({
                found: true,
                class: modal.className,
                tables: tableInfo,
                text: modal.textContent.substring(0, 300)
            });
        })()
    `);
    console.log(secondModal);

    ws.close();
    console.log('\n=== EXPLORE COMPLETE ===');
}

main().catch(err => console.error('Error:', err));
