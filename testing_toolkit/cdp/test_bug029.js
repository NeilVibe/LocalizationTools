/**
 * CDP Test: BUG-029 - Right-click "Upload as TM" not working
 *
 * Tests:
 * 1. Login and navigate to Files tab
 * 2. Select a project with files
 * 3. Right-click on a file to open context menu
 * 4. Click "Upload as TM" option
 * 5. Verify modal opens
 * 6. Check for console errors
 */

const WebSocket = require('ws');
const http = require('http');

const CDP_URL = 'http://127.0.0.1:9222';

// Console messages captured
let consoleMessages = [];
let consoleErrors = [];

async function getTargets() {
    return new Promise((resolve, reject) => {
        http.get(`${CDP_URL}/json`, (res) => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => {
                try {
                    resolve(JSON.parse(data));
                } catch (e) {
                    reject(e);
                }
            });
        }).on('error', reject);
    });
}

async function connect() {
    const targets = await getTargets();
    const page = targets.find(t => t.type === 'page' && !t.url.includes('devtools'));

    if (!page) {
        throw new Error('No page target found. Is the app running with CDP enabled?');
    }

    console.log(`[INFO] Connecting to: ${page.url}`);

    const ws = new WebSocket(page.webSocketDebuggerUrl);

    return new Promise((resolve, reject) => {
        ws.on('open', () => resolve(ws));
        ws.on('error', reject);
    });
}

async function send(ws, method, params = {}) {
    const id = Math.floor(Math.random() * 100000);

    return new Promise((resolve, reject) => {
        const timeout = setTimeout(() => {
            reject(new Error(`Timeout waiting for ${method}`));
        }, 30000);

        const handler = (data) => {
            const msg = JSON.parse(data);
            if (msg.id === id) {
                clearTimeout(timeout);
                ws.off('message', handler);
                if (msg.error) {
                    reject(new Error(msg.error.message));
                } else {
                    resolve(msg);
                }
            }
        };

        ws.on('message', handler);
        ws.send(JSON.stringify({ id, method, params }));
    });
}

async function evaluate(ws, expression) {
    const result = await send(ws, 'Runtime.evaluate', {
        expression,
        returnByValue: true,
        awaitPromise: true
    });
    return result.result?.result?.value;
}

async function sleep(ms) {
    return new Promise(r => setTimeout(r, ms));
}

async function waitFor(ws, selector, timeout = 10000) {
    const start = Date.now();
    while (Date.now() - start < timeout) {
        const exists = await evaluate(ws, `!!document.querySelector('${selector}')`);
        if (exists) return true;
        await sleep(200);
    }
    return false;
}

async function enableConsoleCapture(ws) {
    await send(ws, 'Runtime.enable');

    ws.on('message', (data) => {
        const msg = JSON.parse(data);
        if (msg.method === 'Runtime.consoleAPICalled') {
            const args = msg.params.args || [];
            const text = args.map(a => a.value || a.description || '').join(' ');

            if (msg.params.type === 'error') {
                consoleErrors.push(text);
            } else {
                consoleMessages.push(`[${msg.params.type}] ${text}`);
            }
        } else if (msg.method === 'Runtime.exceptionThrown') {
            consoleErrors.push(msg.params.exceptionDetails?.text || 'Unknown exception');
        }
    });
}

async function runTest() {
    console.log('\n=== BUG-029 Test: Right-click Upload as TM ===\n');

    let ws;
    try {
        ws = await connect();
        console.log('[OK] Connected to CDP\n');

        // Enable console capture
        await enableConsoleCapture(ws);

        // Check current page state
        const pageText = await evaluate(ws, 'document.body.innerText.substring(0, 500)');
        console.log('[INFO] Page content preview:');
        console.log(pageText.substring(0, 200) + '...\n');

        // Check if logged in (look for Files or TM tabs)
        const hasFilesTab = await evaluate(ws, `
            !!document.querySelector('button.tab-button')
        `);

        if (!hasFilesTab) {
            console.log('[ERROR] Not logged in or app not ready. Please login first.');
            console.log('[INFO] Run cdp_login.js first if needed.\n');
            return;
        }

        console.log('[OK] App is ready (tabs visible)\n');

        // Step 1: Make sure we're on Files tab
        console.log('[STEP 1] Switching to Files tab...');
        await evaluate(ws, `
            const filesTab = Array.from(document.querySelectorAll('button.tab-button'))
                .find(b => b.textContent.includes('Files'));
            if (filesTab) filesTab.click();
        `);
        await sleep(500);
        console.log('[OK] Files tab clicked\n');

        // Step 2: Check if there are any projects
        console.log('[STEP 2] Looking for projects...');
        const projectCount = await evaluate(ws, `
            document.querySelectorAll('.project-item').length
        `);
        console.log(`[INFO] Found ${projectCount} projects\n`);

        if (projectCount === 0) {
            console.log('[ERROR] No projects found. Create a project and upload a file first.\n');
            return;
        }

        // Step 3: Select first project
        console.log('[STEP 3] Selecting first project...');
        await evaluate(ws, `
            const firstProject = document.querySelector('.project-item');
            if (firstProject) firstProject.click();
        `);
        await sleep(1000);
        console.log('[OK] Project selected\n');

        // Step 4: Check for files in the tree
        console.log('[STEP 4] Looking for files in project...');
        const fileNodes = await evaluate(ws, `
            JSON.stringify(
                Array.from(document.querySelectorAll('.tree-node'))
                    .map(n => n.textContent.trim())
            )
        `);
        console.log(`[INFO] Tree nodes: ${fileNodes}\n`);

        const nodeCount = await evaluate(ws, `document.querySelectorAll('.tree-node').length`);

        if (nodeCount === 0) {
            console.log('[ERROR] No files found in project. Upload a file first.\n');
            return;
        }

        // Step 5: Simulate right-click on first file
        console.log('[STEP 5] Right-clicking on first file...');
        await evaluate(ws, `
            const firstFile = document.querySelector('.tree-node');
            if (firstFile) {
                const rect = firstFile.getBoundingClientRect();
                const event = new MouseEvent('contextmenu', {
                    bubbles: true,
                    cancelable: true,
                    clientX: rect.left + rect.width / 2,
                    clientY: rect.top + rect.height / 2,
                    button: 2
                });
                firstFile.dispatchEvent(event);
            }
        `);
        await sleep(500);

        // Step 6: Check if context menu appeared
        console.log('[STEP 6] Checking for context menu...');
        const hasContextMenu = await evaluate(ws, `!!document.querySelector('.context-menu')`);

        if (!hasContextMenu) {
            console.log('[ERROR] Context menu did not appear!\n');
            console.log('[DEBUG] This could be because:');
            console.log('  1. The right-click was on a folder, not a file');
            console.log('  2. The context menu handler is not working');
            console.log('  3. The file was not properly recognized\n');
            return;
        }

        console.log('[OK] Context menu appeared!\n');

        // Step 7: Look for "Upload as TM" option
        console.log('[STEP 7] Looking for "Upload as TM" option...');
        const menuOptions = await evaluate(ws, `
            JSON.stringify(
                Array.from(document.querySelectorAll('.context-menu-item'))
                    .map(item => item.textContent.trim())
            )
        `);
        console.log(`[INFO] Menu options: ${menuOptions}\n`);

        const hasUploadAsTM = await evaluate(ws, `
            !!Array.from(document.querySelectorAll('.context-menu-item'))
                .find(item => item.textContent.includes('Upload as TM'))
        `);

        if (!hasUploadAsTM) {
            console.log('[ERROR] "Upload as TM" option not found in context menu!\n');
            return;
        }

        // Step 8: Click "Upload as TM"
        console.log('[STEP 8] Clicking "Upload as TM"...');
        await evaluate(ws, `
            const uploadAsTM = Array.from(document.querySelectorAll('.context-menu-item'))
                .find(item => item.textContent.includes('Upload as TM'));
            if (uploadAsTM) uploadAsTM.click();
        `);
        await sleep(500);

        // Step 9: Check if TM modal opened
        console.log('[STEP 9] Checking for TM Registration modal...');
        const hasModal = await waitFor(ws, '.bx--modal.is-visible', 3000);

        if (!hasModal) {
            console.log('[ERROR] TM Registration modal did not open!\n');
            console.log('[DEBUG] Possible causes:');
            console.log('  1. showTMModal state not being set');
            console.log('  2. Modal component issue');
            console.log('  3. JavaScript error occurred\n');
        } else {
            console.log('[OK] TM Registration modal opened!\n');

            // Get modal details
            const modalHeading = await evaluate(ws, `
                document.querySelector('.bx--modal.is-visible .bx--modal-header__heading')?.textContent || 'N/A'
            `);
            console.log(`[INFO] Modal heading: ${modalHeading}\n`);
        }

        // Step 10: Report console errors
        console.log('[STEP 10] Checking console errors...');
        if (consoleErrors.length > 0) {
            console.log('[WARNING] Console errors detected:');
            consoleErrors.forEach(err => console.log(`  - ${err}`));
            console.log('');
        } else {
            console.log('[OK] No console errors detected\n');
        }

        // Summary
        console.log('=== Test Summary ===');
        console.log(`Context Menu: ${hasContextMenu ? 'OK' : 'FAILED'}`);
        console.log(`Upload as TM Option: ${hasUploadAsTM ? 'OK' : 'FAILED'}`);
        console.log(`Modal Opens: ${hasModal ? 'OK' : 'FAILED'}`);
        console.log(`Console Errors: ${consoleErrors.length}`);
        console.log('');

        if (hasContextMenu && hasUploadAsTM && hasModal && consoleErrors.length === 0) {
            console.log('[PASS] BUG-029 test passed - Upload as TM is working!\n');
        } else {
            console.log('[FAIL] BUG-029 test failed - see details above\n');
        }

    } catch (err) {
        console.error('[ERROR]', err.message);
    } finally {
        if (ws) {
            ws.close();
        }
    }
}

runTest();
