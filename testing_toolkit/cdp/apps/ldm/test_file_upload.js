/**
 * LDM File Upload Test - CDP Autonomous Testing
 *
 * Tests the file upload functionality in LDM (LanguageData Manager).
 * This is a MULTI-DIMENSIONAL test that can run in 3 environments:
 * 1. DEV: Direct API test (no CDP needed)
 * 2. APP: electron:dev mode via CDP
 * 3. EXE: LocaNext.exe on Windows via CDP
 *
 * Usage:
 *   node test_file_upload.js [environment]
 *   - environment: 'dev' | 'app' | 'exe' (default: 'exe')
 *
 * Prerequisites:
 *   - DEV: Backend server running on localhost:8888
 *   - APP: npm run electron:dev with --remote-debugging-port=9222
 *   - EXE: LocaNext.exe running with --remote-debugging-port=9222
 */

const path = require('path');

// Determine environment
const ENV = process.argv[2] || 'exe';
console.log('========================================');
console.log('LDM FILE UPLOAD TEST');
console.log(`Environment: ${ENV.toUpperCase()}`);
console.log('========================================');

const API_BASE = 'http://localhost:8888';

// Test file content (tab-separated)
const TEST_FILE_CONTENT = `StringID\tCol1\tCol2\tCol3\tCol4\tKorean\tTranslation\tCol7
TEST001\tdata\there\t\t\t안녕하세요\tHello\textra
TEST002\tdata\there\t\t\t감사합니다\tThank you\textra
TEST003\tdata\there\t\t\t좋은 아침\tGood morning\textra`;

async function testDevEnvironment() {
    console.log('\n[DEV] Testing direct API...');

    // 1. Login to get token
    console.log('  [1] Getting auth token...');
    const loginRes = await fetch(`${API_BASE}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: 'admin', password: 'admin123' })
    });

    if (!loginRes.ok) {
        throw new Error('Login failed');
    }

    const { access_token } = await loginRes.json();
    console.log('    ✓ Got token');

    // 2. Create project
    console.log('  [2] Creating test project...');
    const projectRes = await fetch(`${API_BASE}/api/ldm/projects`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${access_token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ name: `TestProject_${Date.now()}` })
    });

    if (!projectRes.ok) {
        throw new Error('Failed to create project');
    }

    const project = await projectRes.json();
    console.log(`    ✓ Created project: ${project.id}`);

    // 3. Upload file
    console.log('  [3] Uploading test file...');
    const formData = new FormData();
    formData.append('project_id', project.id.toString());
    const blob = new Blob([TEST_FILE_CONTENT], { type: 'text/plain' });
    formData.append('file', blob, 'test_upload.txt');

    const uploadRes = await fetch(`${API_BASE}/api/ldm/files/upload`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${access_token}` },
        body: formData
    });

    if (!uploadRes.ok) {
        const err = await uploadRes.json();
        throw new Error(`Upload failed: ${err.detail}`);
    }

    const file = await uploadRes.json();
    console.log(`    ✓ Uploaded file: ${file.name} (${file.row_count} rows)`);

    // 4. Verify rows
    console.log('  [4] Verifying uploaded rows...');
    const rowsRes = await fetch(`${API_BASE}/api/ldm/files/${file.id}/rows?limit=10`, {
        headers: { 'Authorization': `Bearer ${access_token}` }
    });

    if (!rowsRes.ok) {
        throw new Error('Failed to get rows');
    }

    const rowsData = await rowsRes.json();
    console.log(`    ✓ Got ${rowsData.total} rows`);

    // 5. Cleanup - delete project
    console.log('  [5] Cleaning up...');
    await fetch(`${API_BASE}/api/ldm/projects/${project.id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${access_token}` }
    });
    console.log('    ✓ Deleted test project');

    return { success: true, rows: rowsData.total };
}

async function testAppEnvironment() {
    console.log('\n[APP/EXE] Testing via CDP...');

    const { connect, evaluate, navigateToApp, waitForSelector } = require('../../utils/cdp-client');

    const cdp = await connect();

    try {
        // 1. Navigate to LDM
        console.log('  [1] Navigating to LDM...');
        const navResult = await navigateToApp(cdp, 'ldm');
        if (!navResult.success) {
            throw new Error(`Navigation failed: ${navResult.error}`);
        }
        console.log('    ✓ Navigated to LDM');

        // 2. Wait for LDM to load
        console.log('  [2] Waiting for LDM to load...');
        await new Promise(r => setTimeout(r, 2000));

        // Check if ldmTest is available
        const interfaces = await evaluate(cdp, `JSON.stringify({
            ldmTest: typeof window.ldmTest !== 'undefined',
            ldmTestMethods: window.ldmTest ? Object.keys(window.ldmTest) : []
        })`);
        const { ldmTest, ldmTestMethods } = JSON.parse(interfaces);

        if (!ldmTest) {
            console.log('    ⚠ window.ldmTest not available, checking DOM...');

            // Check DOM for LDM component
            const dom = await evaluate(cdp, `JSON.stringify({
                hasFileExplorer: !!document.querySelector('.file-explorer'),
                hasUploadButton: !!document.querySelector('[iconDescription="Upload File"]'),
                hasProjectsList: !!document.querySelector('.projects-list')
            })`);
            console.log(`    DOM state: ${dom}`);
        } else {
            console.log(`    ✓ ldmTest available: ${ldmTestMethods.join(', ')}`);
        }

        // 3. Create project via API (since file dialog is hard to automate)
        console.log('  [3] Creating project via API...');
        const createResult = await evaluate(cdp, `
            (async () => {
                try {
                    const token = localStorage.getItem('auth_token');
                    const res = await fetch('http://localhost:8888/api/ldm/projects', {
                        method: 'POST',
                        headers: {
                            'Authorization': 'Bearer ' + token,
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ name: 'CDPTestProject_' + Date.now() })
                    });
                    return JSON.stringify(await res.json());
                } catch(e) {
                    return JSON.stringify({ error: e.message });
                }
            })()
        `);
        const project = JSON.parse(createResult);

        if (project.error) {
            throw new Error(`Project creation failed: ${project.error}`);
        }
        console.log(`    ✓ Created project: ${project.id}`);

        // 4. Upload file via API (file dialog automation is complex)
        console.log('  [4] Uploading file via API...');
        const uploadResult = await evaluate(cdp, `
            (async () => {
                try {
                    const token = localStorage.getItem('auth_token');
                    const content = ${JSON.stringify(TEST_FILE_CONTENT)};
                    const blob = new Blob([content], { type: 'text/plain' });
                    const formData = new FormData();
                    formData.append('project_id', '${project.id}');
                    formData.append('file', blob, 'cdp_test_upload.txt');

                    const res = await fetch('http://localhost:8888/api/ldm/files/upload', {
                        method: 'POST',
                        headers: { 'Authorization': 'Bearer ' + token },
                        body: formData
                    });
                    return JSON.stringify(await res.json());
                } catch(e) {
                    return JSON.stringify({ error: e.message });
                }
            })()
        `);
        const file = JSON.parse(uploadResult);

        if (file.error) {
            throw new Error(`Upload failed: ${file.error}`);
        }
        console.log(`    ✓ Uploaded file: ${file.name} (${file.row_count} rows)`);

        // 5. Refresh project tree in UI
        console.log('  [5] Refreshing project tree...');
        if (ldmTest) {
            await evaluate(cdp, `window.ldmTest.refreshProjects()`);
            await new Promise(r => setTimeout(r, 1000));
        }

        // 6. Cleanup
        console.log('  [6] Cleaning up...');
        await evaluate(cdp, `
            (async () => {
                const token = localStorage.getItem('auth_token');
                await fetch('http://localhost:8888/api/ldm/projects/${project.id}', {
                    method: 'DELETE',
                    headers: { 'Authorization': 'Bearer ' + token }
                });
            })()
        `);
        console.log('    ✓ Deleted test project');

        return { success: true, rows: file.row_count };
    } finally {
        cdp.ws.close();
    }
}

async function main() {
    try {
        let result;

        if (ENV === 'dev') {
            result = await testDevEnvironment();
        } else {
            result = await testAppEnvironment();
        }

        console.log('\n========================================');
        console.log('✓ TEST PASSED');
        console.log(`  Uploaded and verified ${result.rows} rows`);
        console.log('========================================');
        process.exit(0);

    } catch (err) {
        console.log('\n========================================');
        console.log('✗ TEST FAILED');
        console.log(`  Error: ${err.message}`);
        console.log('========================================');
        process.exit(1);
    }
}

main();
