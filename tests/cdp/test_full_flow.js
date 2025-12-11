/**
 * Full Flow Test: Project → File → Double-click Row → Modal Opens
 *
 * This test:
 * 1. Opens the app (assumes app is running with CDP)
 * 2. Navigates to LDM (should be default)
 * 3. Creates a project if needed OR selects existing
 * 4. Uploads a test file OR selects existing
 * 5. Double-clicks a row in the grid
 * 6. Verifies the edit modal opens
 */

const http = require('http');
const WebSocket = require('ws');

// Test configuration
const CDP_PORT = 9222;
const TIMEOUT = 30000;

// Helper: Send CDP command
function send(ws, id, method, params) {
    return new Promise((resolve, reject) => {
        const timeout = setTimeout(() => {
            resolve({ error: 'timeout', method });
        }, 10000);

        const handler = (data) => {
            const msg = JSON.parse(data);
            if (msg.id === id) {
                clearTimeout(timeout);
                ws.removeListener('message', handler);
                resolve(msg);
            }
        };
        ws.on('message', handler);
        ws.send(JSON.stringify({ id, method, params }));
    });
}

// Helper: Wait ms
function wait(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// Helper: Evaluate JS and return result
async function evaluate(ws, id, expression) {
    const result = await send(ws, id, 'Runtime.evaluate', {
        expression,
        returnByValue: true,
        awaitPromise: true
    });
    return result.result?.result?.value;
}

// Main test
async function runTest() {
    console.log('═══════════════════════════════════════════════════════════');
    console.log('  FULL FLOW TEST: Project → File → Row → Edit Modal');
    console.log('═══════════════════════════════════════════════════════════');
    console.log('');

    // Connect to CDP
    console.log('[1/8] Connecting to CDP...');

    const targets = await new Promise((resolve, reject) => {
        http.get(`http://localhost:${CDP_PORT}/json`, (res) => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => resolve(JSON.parse(data)));
        }).on('error', reject);
    });

    const page = targets.find(t => t.type === 'page');
    if (!page) {
        console.log('❌ No page target found. Is the app running?');
        process.exit(1);
    }

    const ws = new WebSocket(page.webSocketDebuggerUrl);
    let id = 1;

    await new Promise(resolve => ws.on('open', resolve));
    console.log('   ✓ Connected to CDP');

    // Enable domains
    await send(ws, id++, 'Page.enable', {});
    await send(ws, id++, 'Runtime.enable', {});

    // Intercept alerts
    await evaluate(ws, id++, `
        window.__alertMessages = [];
        window.__originalAlert = window.alert;
        window.alert = function(msg) {
            console.log('[ALERT INTERCEPTED]', msg);
            window.__alertMessages.push(msg);
        };
    `);
    console.log('   ✓ Alert interceptor installed');

    // Step 2: Check current state
    console.log('');
    console.log('[2/8] Checking app state...');

    const appState = await evaluate(ws, id++, `JSON.stringify({
        url: window.location.href,
        hasNavTest: typeof window.navTest !== 'undefined',
        hasLdmTest: typeof window.ldmTest !== 'undefined',
        currentApp: window.navTest?.getState?.()?.app || 'unknown',
        isAuthenticated: window.navTest?.getState?.()?.authenticated || false
    })`);

    const state = JSON.parse(appState || '{}');
    console.log('   URL:', state.url);
    console.log('   Current App:', state.currentApp);
    console.log('   Authenticated:', state.isAuthenticated);
    console.log('   Test APIs available:', state.hasNavTest && state.hasLdmTest ? '✓' : '✗');

    if (!state.isAuthenticated) {
        console.log('');
        console.log('❌ Not authenticated. Please login first.');
        ws.close();
        process.exit(1);
    }

    // Step 3: Navigate to LDM
    console.log('');
    console.log('[3/8] Navigating to LDM...');

    await evaluate(ws, id++, `window.navTest.goToApp('ldm')`);
    await wait(1000);
    console.log('   ✓ Navigated to LDM');

    // Step 4: Check for existing projects
    console.log('');
    console.log('[4/8] Checking for projects...');

    const projectsInfo = await evaluate(ws, id++, `JSON.stringify({
        projectCount: document.querySelectorAll('.project-item').length,
        projectNames: Array.from(document.querySelectorAll('.project-item span')).map(el => el.textContent)
    })`);

    const projects = JSON.parse(projectsInfo || '{"projectCount":0}');
    console.log('   Found', projects.projectCount, 'project(s)');

    if (projects.projectCount === 0) {
        // Create a test project
        console.log('   Creating test project...');
        await evaluate(ws, id++, `window.ldmTest.createProject()`);
        await wait(2000);

        const status = await evaluate(ws, id++, `JSON.stringify(window.ldmTest.getStatus())`);
        console.log('   Status:', JSON.parse(status || '{}').statusMessage);
    } else {
        // Click first project
        console.log('   Selecting first project:', projects.projectNames[0]);
        await evaluate(ws, id++, `document.querySelector('.project-item')?.click()`);
        await wait(500);
    }

    // Step 5: Check for files in project
    console.log('');
    console.log('[5/8] Checking for files...');
    await wait(1000);

    const filesInfo = await evaluate(ws, id++, `JSON.stringify({
        fileCount: document.querySelectorAll('.bx--tree-node').length,
        hasFiles: document.querySelectorAll('.bx--tree-node[data-value^="file-"]').length > 0 ||
                  document.querySelectorAll('.bx--tree-node').length > 0
    })`);

    const files = JSON.parse(filesInfo || '{"fileCount":0}');
    console.log('   Tree nodes found:', files.fileCount);

    if (files.fileCount === 0) {
        // Upload a test file
        console.log('   No files found. Uploading test file...');
        await evaluate(ws, id++, `window.ldmTest.uploadFile('uploadSmall')`);
        await wait(3000);

        const status = await evaluate(ws, id++, `JSON.stringify(window.ldmTest.getStatus())`);
        const statusObj = JSON.parse(status || '{}');
        console.log('   Status:', statusObj.statusMessage);

        // Select the uploaded file
        await evaluate(ws, id++, `window.ldmTest.selectFile()`);
        await wait(1000);
    } else {
        // Click first file in tree
        console.log('   Clicking first file...');
        await evaluate(ws, id++, `
            const nodes = document.querySelectorAll('.bx--tree-node');
            for (const node of nodes) {
                const text = node.textContent;
                if (text && !text.includes('folder')) {
                    node.click();
                    break;
                }
            }
        `);
        await wait(1000);
    }

    // Step 6: Wait for grid to load
    console.log('');
    console.log('[6/8] Waiting for grid to load...');
    await wait(2000);

    const gridInfo = await evaluate(ws, id++, `JSON.stringify({
        hasGrid: document.querySelector('.virtual-grid') !== null,
        hasRows: document.querySelectorAll('.virtual-row').length,
        hasTargetCells: document.querySelectorAll('.cell.target').length,
        rowCount: document.querySelector('.row-count')?.textContent || 'N/A'
    })`);

    const grid = JSON.parse(gridInfo || '{}');
    console.log('   Grid present:', grid.hasGrid ? '✓' : '✗');
    console.log('   Visible rows:', grid.hasRows);
    console.log('   Target cells:', grid.hasTargetCells);
    console.log('   Total rows:', grid.rowCount);

    if (grid.hasTargetCells === 0) {
        console.log('');
        console.log('❌ No target cells found. Cannot test double-click.');

        // Debug: show what's in the grid
        const debug = await evaluate(ws, id++, `JSON.stringify({
            gridHTML: document.querySelector('.virtual-grid')?.innerHTML?.substring(0, 500) || 'N/A',
            emptyState: document.querySelector('.empty-state')?.textContent || null
        })`);
        console.log('   Debug:', JSON.parse(debug || '{}'));

        ws.close();
        process.exit(1);
    }

    // Step 7: Double-click a target cell
    console.log('');
    console.log('[7/8] Double-clicking target cell...');

    // First check for any existing modal
    const beforeModal = await evaluate(ws, id++, `JSON.stringify({
        modalExists: document.querySelector('.bx--modal') !== null,
        modalVisible: document.querySelector('.bx--modal.is-visible') !== null
    })`);
    console.log('   Modal before click:', JSON.parse(beforeModal || '{}'));

    // Double-click the first target cell
    await evaluate(ws, id++, `
        const targetCell = document.querySelector('.cell.target');
        if (targetCell) {
            console.log('Double-clicking target cell');
            const rect = targetCell.getBoundingClientRect();
            const event = new MouseEvent('dblclick', {
                bubbles: true,
                cancelable: true,
                view: window,
                clientX: rect.left + rect.width / 2,
                clientY: rect.top + rect.height / 2
            });
            targetCell.dispatchEvent(event);
        }
    `);

    console.log('   ✓ Double-click dispatched');
    await wait(1500);

    // Step 8: Check if modal opened
    console.log('');
    console.log('[8/8] Checking for edit modal...');

    const afterModal = await evaluate(ws, id++, `JSON.stringify({
        modalExists: document.querySelector('.bx--modal') !== null,
        modalVisible: document.querySelector('.bx--modal.is-visible') !== null,
        modalHeading: document.querySelector('.bx--modal-header__heading')?.textContent || null,
        hasTextArea: document.querySelector('.bx--modal .bx--text-area') !== null,
        hasSourcePreview: document.querySelector('.source-preview') !== null
    })`);

    const modal = JSON.parse(afterModal || '{}');
    console.log('   Modal exists:', modal.modalExists ? '✓' : '✗');
    console.log('   Modal visible:', modal.modalVisible ? '✓' : '✗');
    console.log('   Modal heading:', modal.modalHeading || 'N/A');
    console.log('   Has textarea:', modal.hasTextArea ? '✓' : '✗');
    console.log('   Has source preview:', modal.hasSourcePreview ? '✓' : '✗');

    // Check for any alerts (lock errors, etc)
    const alerts = await evaluate(ws, id++, `JSON.stringify(window.__alertMessages || [])`);
    const alertList = JSON.parse(alerts || '[]');
    if (alertList.length > 0) {
        console.log('');
        console.log('⚠️  Alerts captured:', alertList);
    }

    // Final result
    console.log('');
    console.log('═══════════════════════════════════════════════════════════');
    if (modal.modalVisible && modal.hasTextArea) {
        console.log('  ✅ TEST PASSED: Edit modal opened successfully!');
    } else if (modal.modalExists) {
        console.log('  ⚠️  TEST PARTIAL: Modal exists but may not be fully visible');
    } else {
        console.log('  ❌ TEST FAILED: Edit modal did not open');
    }
    console.log('═══════════════════════════════════════════════════════════');

    ws.close();
    process.exit(modal.modalVisible ? 0 : 1);
}

// Run
runTest().catch(err => {
    console.error('Test error:', err);
    process.exit(1);
});
