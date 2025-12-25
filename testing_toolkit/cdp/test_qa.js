/**
 * CDP Script: Test QA functionality
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

    const page = targets.find(t => t.type === 'page');
    const ws = new WebSocket(page.webSocketDebuggerUrl);
    let id = 1;

    const send = (method, params = {}) => new Promise(resolve => {
        const msgId = id++;
        const handler = (msg) => {
            const r = JSON.parse(msg.toString());
            if (r.id === msgId) { ws.off('message', handler); resolve(r); }
        };
        ws.on('message', handler);
        ws.send(JSON.stringify({ id: msgId, method, params }));
    });

    const evaluate = async (expr) => {
        const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
        return r.result?.result?.value;
    };

    await new Promise(resolve => ws.on('open', resolve));

    console.log('=== QA TEST ===\n');

    // Step 1: Select the project
    console.log('[1] Selecting project...');
    await evaluate(`
        const projectItems = document.querySelectorAll('.project-item, [class*="project"]');
        for (const item of projectItems) {
            if (item.textContent.includes('QA Test Project')) {
                item.click();
                break;
            }
        }
    `);
    await sleep(1000);

    // Step 2: Click on the file
    console.log('[2] Selecting file...');
    await evaluate(`
        const fileItems = document.querySelectorAll('.tree-node, .file-item, [class*="file"]');
        for (const item of fileItems) {
            if (item.textContent.includes('test_10k')) {
                item.click();
                break;
            }
        }
    `);
    await sleep(2000);

    // Step 3: Check if file loaded
    console.log('[3] Checking file load...');
    const pageState = await evaluate(`
        document.body.innerText.substring(0, 1000)
    `);
    console.log('Page state:', pageState.substring(0, 500));

    // Step 4: Run QA check via API
    console.log('\n[4] Running QA check via API...');
    const qaResult = await evaluate(`
        (async () => {
            const token = localStorage.getItem('auth_token');
            const response = await fetch('http://localhost:8888/api/ldm/files/109/check-qa', {
                method: 'POST',
                headers: {
                    'Authorization': 'Bearer ' + token,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    checks: ["line", "pattern", "term"],
                    force: true
                })
            });

            if (!response.ok) {
                return 'QA check failed: ' + response.status;
            }

            return await response.text();
        })()
    `);
    console.log('QA result:', qaResult);

    // Step 5: Get QA summary
    console.log('\n[5] Getting QA summary...');
    const summary = await evaluate(`
        (async () => {
            const token = localStorage.getItem('auth_token');
            const response = await fetch('http://localhost:8888/api/ldm/files/109/qa-summary', {
                headers: { 'Authorization': 'Bearer ' + token }
            });
            return await response.text();
        })()
    `);
    console.log('QA summary:', summary);

    // Step 6: Check for errors
    console.log('\n[6] Checking for errors...');
    const hasErrors = await evaluate(`
        document.body.innerText.includes('Error') ||
        document.body.innerText.includes('undefined')
    `);
    console.log('Has errors:', hasErrors);

    ws.close();
    console.log('\n=== QA TEST COMPLETE ===');
}

main().catch(e => { console.error(e); process.exit(1); });
