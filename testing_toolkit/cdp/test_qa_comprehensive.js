/**
 * Comprehensive QA Test Script
 *
 * This script:
 * 1. Logs in using env credentials
 * 2. Lists all projects
 * 3. Attempts to trigger QA functionality
 * 4. Monitors console for errors (especially "Cannot read properties of undefined (reading 'id')")
 *
 * Usage (from Windows PowerShell):
 *   Push-Location '\\wsl.localhost\Ubuntu2\home\neil1988\LocalizationTools\testing_toolkit\cdp'
 *   $env:CDP_TEST_USER="neil"; $env:CDP_TEST_PASS="neil"; node test_qa_comprehensive.js
 */
const WebSocket = require('ws');
const http = require('http');

const sleep = ms => new Promise(r => setTimeout(r, ms));

// Get credentials from environment
const TEST_USER = process.env.CDP_TEST_USER;
const TEST_PASS = process.env.CDP_TEST_PASS;

if (!TEST_USER || !TEST_PASS) {
    console.error('ERROR: CDP_TEST_USER and CDP_TEST_PASS environment variables are required');
    console.error('For local: $env:CDP_TEST_USER="neil"; $env:CDP_TEST_PASS="neil"; node test_qa_comprehensive.js');
    process.exit(1);
}

async function main() {
    console.log('=== COMPREHENSIVE QA TEST ===\n');

    // Get CDP targets
    const targets = await new Promise((resolve, reject) => {
        http.get('http://127.0.0.1:9222/json', (res) => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => resolve(JSON.parse(data)));
        }).on('error', reject);
    });

    const page = targets.find(t => t.type === 'page');
    if (!page) {
        console.log('ERROR: No page found. Make sure LocaNext is running with --remote-debugging-port=9222');
        process.exit(1);
    }

    console.log('Connected to:', page.title);
    console.log('URL:', page.url);
    console.log('');

    const ws = new WebSocket(page.webSocketDebuggerUrl);
    let id = 1;
    const consoleMessages = [];
    const consoleErrors = [];

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
        const r = await send('Runtime.evaluate', {
            expression: expr,
            returnByValue: true,
            awaitPromise: true
        });
        if (r.result?.exceptionDetails) {
            console.error('ERROR evaluating expression:', r.result.exceptionDetails.text);
            console.error('Expression:', expr.substring(0, 200));
        }
        return r.result?.result?.value;
    };

    await new Promise(resolve => ws.on('open', resolve));

    // Enable console logging
    await send('Console.enable');
    await send('Runtime.enable');
    await send('Log.enable');

    // Listen for console messages
    ws.on('message', (data) => {
        const msg = JSON.parse(data.toString());

        // Console.messageAdded
        if (msg.method === 'Console.messageAdded') {
            const entry = msg.params.message;
            consoleMessages.push({
                level: entry.level,
                text: entry.text,
                timestamp: new Date().toISOString()
            });
            if (entry.level === 'error') {
                consoleErrors.push(entry.text);
            }
        }

        // Runtime.consoleAPICalled
        if (msg.method === 'Runtime.consoleAPICalled') {
            const args = msg.params.args.map(a => a.value || a.description || '').join(' ');
            consoleMessages.push({
                level: msg.params.type,
                text: args,
                timestamp: new Date().toISOString()
            });
            if (msg.params.type === 'error') {
                consoleErrors.push(args);
            }
        }

        // Runtime.exceptionThrown
        if (msg.method === 'Runtime.exceptionThrown') {
            const exception = msg.params.exceptionDetails;
            const text = exception.exception?.description || exception.text || 'Unknown exception';
            consoleErrors.push(`EXCEPTION: ${text}`);
            consoleMessages.push({
                level: 'error',
                text: `EXCEPTION: ${text}`,
                timestamp: new Date().toISOString()
            });
        }
    });

    // STEP 1: Check if logged in, if not, login
    console.log('[STEP 1] Checking login status...');
    const bodyText = await evaluate('document.body.innerText.substring(0, 300)');

    if (bodyText.includes('Login') || bodyText.includes('Password')) {
        console.log('Not logged in. Logging in as:', TEST_USER);

        // Fill username
        await evaluate(`
            const inputs = document.querySelectorAll('input');
            const usernameInput = inputs[0];
            if (usernameInput) {
                usernameInput.value = '${TEST_USER}';
                usernameInput.dispatchEvent(new Event('input', {bubbles: true}));
            }
        `);

        // Fill password
        await evaluate(`
            const passwordInput = document.querySelector('input[type="password"]');
            if (passwordInput) {
                passwordInput.value = '${TEST_PASS}';
                passwordInput.dispatchEvent(new Event('input', {bubbles: true}));
            }
        `);

        await sleep(500);

        // Click login
        await evaluate(`
            const loginBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Login'));
            if (loginBtn) loginBtn.click();
        `);

        console.log('Login clicked. Waiting for navigation...');
        await sleep(3000);
    } else {
        console.log('Already logged in!');
    }

    // STEP 2: Get current page state
    console.log('\n[STEP 2] Getting page state...');
    const pageState = await evaluate(`JSON.stringify({
        url: window.location.href,
        hash: window.location.hash,
        hasLdmTest: typeof window.ldmTest !== 'undefined',
        bodyPreview: document.body.innerText.substring(0, 500)
    })`);
    const state = JSON.parse(pageState || '{}');
    console.log('URL:', state.url);
    console.log('Hash:', state.hash || '(none)');
    console.log('Has ldmTest interface:', state.hasLdmTest);

    // STEP 3: Navigate to Files tab if not there
    console.log('\n[STEP 3] Navigating to Files tab...');
    await evaluate(`
        const filesBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.trim() === 'Files');
        if (filesBtn) {
            filesBtn.click();
            console.log('Clicked Files button');
        } else {
            console.log('Files button not found');
        }
    `);
    await sleep(1000);

    // STEP 4: List all projects
    console.log('\n[STEP 4] Listing all projects...');
    const projects = await evaluate(`
        (function() {
            const projectItems = document.querySelectorAll('.project-item, [class*="project"]');
            const projects = [];
            projectItems.forEach((item, idx) => {
                projects.push({
                    index: idx,
                    text: item.textContent.trim().substring(0, 100),
                    className: item.className
                });
            });
            return JSON.stringify(projects);
        })()
    `);

    const projectList = JSON.parse(projects || '[]');
    console.log(`Found ${projectList.length} projects:`);
    projectList.forEach(p => {
        console.log(`  [${p.index}] ${p.text}`);
    });

    // STEP 5: Try to select first project and list files
    if (projectList.length > 0) {
        console.log('\n[STEP 5] Selecting first project...');
        await evaluate(`
            const projectItems = document.querySelectorAll('.project-item, [class*="project"]');
            if (projectItems.length > 0) {
                projectItems[0].click();
            }
        `);
        await sleep(2000);

        // List files in project
        const files = await evaluate(`
            (function() {
                const fileItems = document.querySelectorAll('.tree-node, .file-item, [class*="file"]');
                const files = [];
                fileItems.forEach((item, idx) => {
                    if (item.textContent.trim().length > 0) {
                        files.push({
                            index: idx,
                            text: item.textContent.trim().substring(0, 100),
                            className: item.className
                        });
                    }
                });
                return JSON.stringify(files);
            })()
        `);

        const fileList = JSON.parse(files || '[]');
        console.log(`Found ${fileList.length} files/folders in project:`);
        fileList.slice(0, 10).forEach(f => {
            console.log(`  [${f.index}] ${f.text}`);
        });
        if (fileList.length > 10) {
            console.log(`  ... and ${fileList.length - 10} more`);
        }
    } else {
        console.log('\n[STEP 5] SKIPPED - No projects found');
    }

    // STEP 6: Try to trigger QA functionality
    console.log('\n[STEP 6] Attempting to trigger QA functionality...');

    // Check if we can access the QA API
    const qaApiCheck = await evaluate(`
        (async () => {
            try {
                const token = localStorage.getItem('auth_token');
                if (!token) {
                    return 'No auth token found in localStorage';
                }

                // Try to get projects first
                const projectsResp = await fetch('http://localhost:8888/api/ldm/projects', {
                    headers: { 'Authorization': 'Bearer ' + token }
                });

                if (!projectsResp.ok) {
                    return 'Failed to fetch projects: ' + projectsResp.status;
                }

                const projectsData = await projectsResp.json();
                return 'Projects API working. Found ' + projectsData.length + ' projects';
            } catch (err) {
                return 'Error: ' + err.message;
            }
        })()
    `);
    console.log('QA API check:', qaApiCheck);

    // Try to click QA button if available
    const qaButtonCheck = await evaluate(`
        (function() {
            const qaButtons = Array.from(document.querySelectorAll('button')).filter(b =>
                b.textContent.includes('QA') ||
                b.textContent.includes('Quality') ||
                b.textContent.includes('Check')
            );
            if (qaButtons.length > 0) {
                return 'Found QA buttons: ' + qaButtons.map(b => b.textContent.trim()).join(', ');
            }
            return 'No QA buttons found';
        })()
    `);
    console.log('QA button check:', qaButtonCheck);

    // STEP 7: Check for console errors
    console.log('\n[STEP 7] Checking for console errors...');
    await sleep(1000); // Wait a bit more to collect any late errors

    // Check for specific error pattern
    const hasIdError = consoleErrors.some(err =>
        err.includes('Cannot read properties of undefined') && err.includes("'id'")
    );

    if (hasIdError) {
        console.log('FOUND ERROR: "Cannot read properties of undefined (reading \'id\')"');
    } else {
        console.log('No "Cannot read properties of undefined (reading \'id\')" error found');
    }

    // Print all console errors
    if (consoleErrors.length > 0) {
        console.log(`\nTotal console errors: ${consoleErrors.length}`);
        console.log('\n=== CONSOLE ERRORS ===');
        consoleErrors.forEach((err, idx) => {
            console.log(`[${idx + 1}] ${err}`);
        });
    } else {
        console.log('No console errors detected');
    }

    // Print all console messages (optional - can be verbose)
    if (consoleMessages.length > 0 && consoleMessages.length < 50) {
        console.log('\n=== ALL CONSOLE MESSAGES ===');
        consoleMessages.forEach(msg => {
            console.log(`[${msg.level}] ${msg.text}`);
        });
    } else if (consoleMessages.length >= 50) {
        console.log(`\n(${consoleMessages.length} console messages captured - too many to display)`);
    }

    // STEP 8: Summary
    console.log('\n=== TEST SUMMARY ===');
    console.log('Projects found:', projectList.length);
    console.log('Console errors:', consoleErrors.length);
    console.log('ID error present:', hasIdError ? 'YES' : 'NO');

    ws.close();
    console.log('\n=== TEST COMPLETE ===');
}

main().catch(e => {
    console.error('\nFATAL ERROR:', e.message);
    console.error(e);
    process.exit(1);
});
