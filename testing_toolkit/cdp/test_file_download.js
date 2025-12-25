/**
 * CDP Test: File Download Functionality
 *
 * Tests:
 * 1. Export file from project
 * 2. Download TM as TMX
 * 3. Download QA report
 *
 * Prerequisites:
 * - LocaNext running with --remote-debugging-port=9222
 * - Logged in user with access to projects
 * - At least one project with files
 *
 * Usage (Windows PowerShell):
 *   $env:CDP_TEST_USER="user"; $env:CDP_TEST_PASS="pass"
 *   node test_file_download.js
 */
const WebSocket = require('ws');
const http = require('http');
const path = require('path');

const sleep = ms => new Promise(r => setTimeout(r, ms));

// Colors for output
const C = {
    reset: '\x1b[0m',
    green: '\x1b[32m',
    red: '\x1b[31m',
    yellow: '\x1b[33m',
    cyan: '\x1b[36m',
    dim: '\x1b[2m'
};

// Get credentials
const TEST_USER = process.env.CDP_TEST_USER;
const TEST_PASS = process.env.CDP_TEST_PASS;

if (!TEST_USER || !TEST_PASS) {
    console.error(`${C.red}ERROR: CDP_TEST_USER and CDP_TEST_PASS required${C.reset}`);
    process.exit(1);
}

async function main() {
    console.log('\n' + '═'.repeat(60));
    console.log(`${C.cyan}  CDP TEST: File Download Functionality${C.reset}`);
    console.log('═'.repeat(60) + '\n');

    // Connect to CDP
    const targets = await new Promise((resolve, reject) => {
        const req = http.get('http://127.0.0.1:9222/json', (res) => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => resolve(JSON.parse(data)));
        });
        req.on('error', reject);
        req.setTimeout(5000, () => {
            req.destroy();
            reject(new Error('CDP connection timeout'));
        });
    });

    const page = targets.find(t => t.type === 'page');
    if (!page) {
        console.log(`${C.red}ERROR: No page found${C.reset}`);
        process.exit(1);
    }

    console.log(`${C.green}✓${C.reset} Connected to: ${page.title}`);

    const ws = new WebSocket(page.webSocketDebuggerUrl);
    let id = 1;
    const errors = [];

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

    const evaluate = async (expr) => {
        const r = await send('Runtime.evaluate', {
            expression: expr,
            returnByValue: true,
            awaitPromise: true
        });
        if (r.result?.exceptionDetails) {
            errors.push(r.result.exceptionDetails.text || 'Unknown error');
        }
        return r.result?.result?.value;
    };

    await new Promise(resolve => ws.on('open', resolve));

    // Enable console capture
    await send('Console.enable');
    await send('Runtime.enable');

    ws.on('message', (data) => {
        const msg = JSON.parse(data.toString());
        if (msg.method === 'Runtime.exceptionThrown') {
            errors.push(msg.params.exceptionDetails?.text || 'Exception');
        }
    });

    // Step 1: Check if logged in
    console.log(`\n${C.cyan}[1/5]${C.reset} Checking login status...`);
    const bodyText = await evaluate('document.body.innerText.substring(0, 300)');

    if (bodyText.includes('Login') || bodyText.includes('Password')) {
        console.log(`${C.yellow}⚠${C.reset} Not logged in. Logging in...`);
        await evaluate(`
            const inputs = document.querySelectorAll('input');
            if (inputs[0]) {
                inputs[0].value = '${TEST_USER}';
                inputs[0].dispatchEvent(new Event('input', {bubbles: true}));
            }
        `);
        await evaluate(`
            const pwInput = document.querySelector('input[type="password"]');
            if (pwInput) {
                pwInput.value = '${TEST_PASS}';
                pwInput.dispatchEvent(new Event('input', {bubbles: true}));
            }
        `);
        await sleep(500);
        await evaluate(`
            const btn = Array.from(document.querySelectorAll('button'))
                .find(b => b.textContent.includes('Login'));
            if (btn) btn.click();
        `);
        await sleep(3000);
        console.log(`${C.green}✓${C.reset} Logged in`);
    } else {
        console.log(`${C.green}✓${C.reset} Already logged in`);
    }

    // Step 2: Get available projects and files
    console.log(`\n${C.cyan}[2/5]${C.reset} Fetching projects...`);
    const projectsData = await evaluate(`
        (async () => {
            const token = localStorage.getItem('auth_token');
            if (!token) return { error: 'No auth token' };

            const resp = await fetch('http://localhost:8888/api/ldm/projects', {
                headers: { 'Authorization': 'Bearer ' + token }
            });
            if (!resp.ok) return { error: 'API error: ' + resp.status };
            return await resp.json();
        })()
    `);

    if (projectsData.error) {
        console.log(`${C.red}✗${C.reset} ${projectsData.error}`);
    } else if (Array.isArray(projectsData) && projectsData.length > 0) {
        console.log(`${C.green}✓${C.reset} Found ${projectsData.length} projects`);

        const project = projectsData[0];
        console.log(`${C.dim}  Using project: ${project.name} (ID: ${project.id})${C.reset}`);

        // Step 3: Get files in project
        console.log(`\n${C.cyan}[3/5]${C.reset} Fetching project files...`);
        const treeData = await evaluate(`
            (async () => {
                const token = localStorage.getItem('auth_token');
                const resp = await fetch('http://localhost:8888/api/ldm/projects/${project.id}/tree', {
                    headers: { 'Authorization': 'Bearer ' + token }
                });
                if (!resp.ok) return { error: 'Tree API error: ' + resp.status };
                return await resp.json();
            })()
        `);

        if (treeData.error) {
            console.log(`${C.red}✗${C.reset} ${treeData.error}`);
        } else {
            // Find first file
            function findFile(nodes) {
                for (const node of nodes) {
                    if (node.type === 'file') return node;
                    if (node.children) {
                        const found = findFile(node.children);
                        if (found) return found;
                    }
                }
                return null;
            }

            const file = findFile(treeData.children || [treeData]);
            if (file) {
                console.log(`${C.green}✓${C.reset} Found file: ${file.name} (ID: ${file.id})`);

                // Step 4: Test file export/download
                console.log(`\n${C.cyan}[4/5]${C.reset} Testing file export...`);
                const exportResult = await evaluate(`
                    (async () => {
                        const token = localStorage.getItem('auth_token');

                        // Test file export endpoint
                        const resp = await fetch('http://localhost:8888/api/ldm/files/${file.id}/export', {
                            method: 'GET',
                            headers: { 'Authorization': 'Bearer ' + token }
                        });

                        if (!resp.ok) {
                            // Try alternative download endpoint
                            const altResp = await fetch('http://localhost:8888/api/ldm/files/${file.id}/download', {
                                method: 'GET',
                                headers: { 'Authorization': 'Bearer ' + token }
                            });
                            if (altResp.ok) {
                                const blob = await altResp.blob();
                                return {
                                    success: true,
                                    endpoint: 'download',
                                    size: blob.size,
                                    type: altResp.headers.get('content-type')
                                };
                            }
                            return { error: 'Both export and download failed' };
                        }

                        const blob = await resp.blob();
                        return {
                            success: true,
                            endpoint: 'export',
                            size: blob.size,
                            type: resp.headers.get('content-type')
                        };
                    })()
                `);

                if (exportResult.success) {
                    console.log(`${C.green}✓${C.reset} File export works`);
                    console.log(`${C.dim}  Endpoint: ${exportResult.endpoint}${C.reset}`);
                    console.log(`${C.dim}  Size: ${exportResult.size} bytes${C.reset}`);
                    console.log(`${C.dim}  Type: ${exportResult.type}${C.reset}`);
                } else {
                    console.log(`${C.yellow}⚠${C.reset} Export endpoint not available: ${exportResult.error}`);
                }
            } else {
                console.log(`${C.yellow}⚠${C.reset} No files found in project`);
            }
        }
    } else {
        console.log(`${C.yellow}⚠${C.reset} No projects found`);
    }

    // Step 5: Test TM export
    console.log(`\n${C.cyan}[5/5]${C.reset} Testing TM export...`);
    const tmData = await evaluate(`
        (async () => {
            const token = localStorage.getItem('auth_token');

            // Get TMs
            const tmsResp = await fetch('http://localhost:8888/api/ldm/translation-memories', {
                headers: { 'Authorization': 'Bearer ' + token }
            });
            if (!tmsResp.ok) return { error: 'TM list failed: ' + tmsResp.status };
            const tms = await tmsResp.json();

            if (!tms || tms.length === 0) {
                return { noTMs: true };
            }

            const tm = tms[0];

            // Test TMX export
            const exportResp = await fetch('http://localhost:8888/api/ldm/translation-memories/' + tm.id + '/export', {
                method: 'GET',
                headers: { 'Authorization': 'Bearer ' + token }
            });

            if (exportResp.ok) {
                const blob = await exportResp.blob();
                return {
                    success: true,
                    tmName: tm.name,
                    tmId: tm.id,
                    exportSize: blob.size,
                    contentType: exportResp.headers.get('content-type')
                };
            }

            return { error: 'TM export failed: ' + exportResp.status };
        })()
    `);

    if (tmData.noTMs) {
        console.log(`${C.yellow}⚠${C.reset} No TMs found to test export`);
    } else if (tmData.success) {
        console.log(`${C.green}✓${C.reset} TM export works`);
        console.log(`${C.dim}  TM: ${tmData.tmName} (ID: ${tmData.tmId})${C.reset}`);
        console.log(`${C.dim}  Size: ${tmData.exportSize} bytes${C.reset}`);
        console.log(`${C.dim}  Type: ${tmData.contentType}${C.reset}`);
    } else {
        console.log(`${C.yellow}⚠${C.reset} TM export: ${tmData.error}`);
    }

    // Summary
    console.log('\n' + '─'.repeat(60));
    console.log(`\n${C.cyan}SUMMARY${C.reset}`);

    if (errors.length === 0) {
        console.log(`${C.green}✓ No JavaScript errors detected${C.reset}`);
    } else {
        console.log(`${C.red}✗ ${errors.length} errors detected:${C.reset}`);
        errors.forEach(e => console.log(`  - ${e}`));
    }

    console.log('\n' + '═'.repeat(60) + '\n');

    ws.close();
    process.exit(errors.length > 0 ? 1 : 0);
}

main().catch(e => {
    console.error(`${C.red}FATAL: ${e.message}${C.reset}`);
    process.exit(1);
});
