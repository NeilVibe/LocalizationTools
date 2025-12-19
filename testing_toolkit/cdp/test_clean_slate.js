/**
 * Clean Slate Test - Clear all TMs and Files
 */
const WebSocket = require('ws');
const http = require('http');
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function main() {
    console.log('=== CLEAN SLATE: Clear TMs and Files ===\n');

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
        const timeout = setTimeout(() => resolve({ timeout: true }), 30000);
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

    // Step 1: Go to TM tab and list TMs
    console.log('[1] Checking existing TMs...');
    await evaluate(`
        const tmTab = Array.from(document.querySelectorAll('button')).find(b => b.textContent.trim() === 'TM');
        if (tmTab) tmTab.click();
    `);
    await sleep(1000);

    const tmList = await evaluate(`
        (function() {
            const tmItems = document.querySelectorAll('.tm-item');
            return Array.from(tmItems).map(el => el.innerText.split('\\n')[0]).join(', ');
        })()
    `);
    console.log('   Existing TMs:', tmList || '(none)');

    // Step 2: Delete each TM
    console.log('[2] Deleting TMs...');
    const deleteResult = await evaluate(`
        (async function() {
            const tmItems = document.querySelectorAll('.tm-item');
            let deleted = 0;

            for (const tm of tmItems) {
                // Right-click to get context menu
                const event = new MouseEvent('contextmenu', { bubbles: true, clientX: 100, clientY: 100 });
                tm.dispatchEvent(event);
                await new Promise(r => setTimeout(r, 500));

                // Find Delete option
                const deleteBtn = Array.from(document.querySelectorAll('button, [role="menuitem"]')).find(b =>
                    b.textContent.toLowerCase().includes('delete')
                );
                if (deleteBtn) {
                    deleteBtn.click();
                    await new Promise(r => setTimeout(r, 500));

                    // Confirm delete
                    const confirmBtn = Array.from(document.querySelectorAll('button')).find(b =>
                        b.textContent.toLowerCase() === 'delete' || b.textContent.toLowerCase() === 'confirm'
                    );
                    if (confirmBtn) {
                        confirmBtn.click();
                        deleted++;
                        await new Promise(r => setTimeout(r, 1000));
                    }
                }
            }
            return deleted;
        })()
    `);
    console.log('   Deleted TMs:', deleteResult);
    await sleep(1000);

    // Step 3: Go to Files tab
    console.log('[3] Checking Files tab...');
    await evaluate(`
        const filesTab = Array.from(document.querySelectorAll('button')).find(b => b.textContent.trim() === 'Files');
        if (filesTab) filesTab.click();
    `);
    await sleep(1000);

    // Step 4: List projects
    const projects = await evaluate(`
        (function() {
            const projectItems = document.querySelectorAll('[class*="project"], .tree-item, .folder-item');
            return Array.from(projectItems).map(el => el.innerText.split('\\n')[0]).slice(0, 10).join(', ');
        })()
    `);
    console.log('   Projects:', projects || '(none)');

    // Step 5: Get current state summary
    console.log('\n[4] Getting current state...');
    const state = await evaluate(`
        (function() {
            const body = document.body.innerText;
            return {
                hasTMs: body.includes('entries'),
                hasProjects: body.includes('Project'),
                hasFiles: body.includes('.xlsx') || body.includes('.txt') || body.includes('.xml')
            };
        })()
    `);

    console.log('\n=== CURRENT STATE ===');
    console.log('TMs present:', tmList ? 'Yes' : 'No');
    console.log('Projects present:', projects ? 'Yes' : 'No');

    ws.close();
    console.log('\n=== CLEAN SLATE CHECK COMPLETE ===');
}

main().catch(err => console.error('Error:', err));
