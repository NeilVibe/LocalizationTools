/**
 * CDP Script: Upload file to project
 */
const WebSocket = require('ws');
const http = require('http');
const fs = require('fs');
const path = require('path');

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

    console.log('=== UPLOAD FILE ===\n');

    // Read file from Windows path
    const filePath = 'C:\\NEIL_PROJECTS_WINDOWSBUILD\\LocaNextProject\\test_10k.txt';

    // Upload via frontend API
    const result = await evaluate(`
        (async () => {
            const token = localStorage.getItem('auth_token');
            const projectId = 7;  // From previous step

            // Fetch file content from file:// URL
            let fileContent;
            try {
                const response = await fetch('file:///C:/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/test_10k.txt');
                fileContent = await response.text();
            } catch (e) {
                return 'Error fetching file: ' + e.message;
            }

            console.log('File size:', fileContent.length, 'chars');

            // Create FormData with file blob
            const blob = new Blob([fileContent], { type: 'text/plain' });
            const formData = new FormData();
            formData.append('file', blob, 'test_10k.txt');
            formData.append('project_id', projectId.toString());

            // Upload to API
            try {
                const uploadResponse = await fetch('http://localhost:8888/api/ldm/files/upload', {
                    method: 'POST',
                    headers: {
                        'Authorization': 'Bearer ' + token
                    },
                    body: formData
                });

                if (!uploadResponse.ok) {
                    const errText = await uploadResponse.text();
                    return 'Upload failed: ' + uploadResponse.status + ' - ' + errText;
                }

                const data = await uploadResponse.json();
                return JSON.stringify(data);
            } catch (e) {
                return 'Upload error: ' + e.message;
            }
        })()
    `);

    console.log('Upload result:', result);

    await sleep(2000);

    // Check files in project
    const files = await evaluate(`
        (async () => {
            const token = localStorage.getItem('auth_token');
            const response = await fetch('http://localhost:8888/api/ldm/projects/7/tree', {
                headers: { 'Authorization': 'Bearer ' + token }
            });
            return await response.text();
        })()
    `);
    console.log('Project files:', files);

    ws.close();
}

main().catch(e => { console.error(e); process.exit(1); });
