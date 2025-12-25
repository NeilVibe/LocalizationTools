/**
 * CDP Script: Create project and upload test file
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
    if (!page) {
        console.log('No page found');
        process.exit(1);
    }

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

    console.log('=== CREATE PROJECT & UPLOAD ===\n');

    // Step 1: Create project via test interface
    console.log('[1] Creating project...');
    const createResult = await evaluate(`
        (async () => {
            const token = localStorage.getItem('auth_token');
            const response = await fetch('http://localhost:8888/api/ldm/projects', {
                method: 'POST',
                headers: {
                    'Authorization': 'Bearer ' + token,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    name: 'QA Test Project 10K',
                    source_lang: 'ko',
                    target_lang: 'en'
                })
            });
            const data = await response.json();
            return JSON.stringify(data);
        })()
    `);
    console.log('Project created:', createResult);
    const project = JSON.parse(createResult);

    await sleep(1000);

    // Step 2: Click on the project in the sidebar to select it
    console.log('[2] Selecting project...');
    await evaluate(`
        // Click on the newly created project
        const projectItems = document.querySelectorAll('.project-item, .tree-item');
        for (const item of projectItems) {
            if (item.textContent.includes('QA Test Project')) {
                item.click();
                break;
            }
        }
    `);
    await sleep(500);

    // Step 3: Upload file via API
    console.log('[3] Uploading 10K row file...');
    const uploadResult = await evaluate(`
        (async () => {
            const token = localStorage.getItem('auth_token');
            const projectId = ${project.id};

            // Read file content (simulate)
            const fileContent = await fetch('file:///C:/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/test_10k.txt')
                .then(r => r.text())
                .catch(() => null);

            if (!fileContent) {
                // Try direct upload approach
                const formData = new FormData();
                const blob = new Blob(['test'], { type: 'text/plain' });
                formData.append('file', blob, 'test.txt');
                formData.append('project_id', projectId);

                return 'File content not accessible - need manual upload';
            }

            return 'File found: ' + fileContent.substring(0, 100);
        })()
    `);
    console.log('Upload result:', uploadResult);

    // Step 4: Check project list
    console.log('\n[4] Checking projects...');
    const projects = await evaluate(`
        (async () => {
            const token = localStorage.getItem('auth_token');
            const response = await fetch('http://localhost:8888/api/ldm/projects', {
                headers: { 'Authorization': 'Bearer ' + token }
            });
            return await response.text();
        })()
    `);
    console.log('Projects:', projects);

    ws.close();
    console.log('\n=== DONE ===');
    console.log('Project created. Upload file manually via UI:');
    console.log('File: C:\\NEIL_PROJECTS_WINDOWSBUILD\\LocaNextProject\\test_10k.txt');
}

main().catch(e => { console.error(e); process.exit(1); });
