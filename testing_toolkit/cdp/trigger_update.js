/**
 * Trigger Auto-Update via CDP
 *
 * Purpose: Update the running LocaNext app to the latest version without full reinstall.
 *
 * Usage (from Windows PowerShell):
 *   Push-Location '\\wsl.localhost\Ubuntu2\home\neil1988\LocalizationTools\testing_toolkit\cdp'
 *   node trigger_update.js
 *
 * Or from WSL (if interop works):
 *   /mnt/c/Program\ Files/nodejs/node.exe testing_toolkit/cdp/trigger_update.js
 */

const WebSocket = require('ws');
const http = require('http');

const sleep = ms => new Promise(r => setTimeout(r, ms));

async function main() {
    console.log('=== TRIGGER AUTO-UPDATE ===\n');

    // 1. Check if app is running
    console.log('1. Checking if app is running...');
    let targets;
    try {
        targets = await new Promise((resolve, reject) => {
            const req = http.get('http://127.0.0.1:9222/json', (res) => {
                let data = '';
                res.on('data', chunk => data += chunk);
                res.on('end', () => resolve(JSON.parse(data)));
            });
            req.on('error', reject);
            req.setTimeout(5000, () => {
                req.destroy();
                reject(new Error('Connection timeout'));
            });
        });
    } catch (e) {
        console.log('   App not running on CDP port 9222');
        console.log('   Please launch the app first:');
        console.log('   C:\\...\\Playground\\LocaNext\\LocaNext.exe --remote-debugging-port=9222');
        process.exit(1);
    }

    const page = targets.find(t => t.type === 'page');
    if (!page) {
        console.log('   No page found in CDP targets');
        process.exit(1);
    }
    console.log('   App running: ' + page.title);

    // 2. Connect via WebSocket
    console.log('\n2. Connecting via WebSocket...');
    const ws = new WebSocket(page.webSocketDebuggerUrl);

    let id = 1;
    const send = (method, params = {}) => new Promise((resolve, reject) => {
        const msgId = id++;
        const timeout = setTimeout(() => reject(new Error('CDP timeout')), 10000);

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

    const evaluate = async (expr) => {
        const r = await send('Runtime.evaluate', {
            expression: expr,
            returnByValue: true,
            awaitPromise: true
        });
        return r.result?.result?.value;
    };

    await new Promise(resolve => ws.on('open', resolve));
    console.log('   Connected');

    // 3. Get current version
    console.log('\n3. Getting current version...');
    const currentVersion = await evaluate(`
        fetch('http://localhost:8888/health')
            .then(r => r.json())
            .then(d => d.version)
            .catch(() => 'unknown')
    `);
    console.log('   Current: v' + currentVersion);

    // 4. Check if electronUpdate API is available (CORRECT API name)
    console.log('\n4. Checking electronUpdate API...');
    const hasElectronUpdate = await evaluate(`typeof window.electronUpdate !== 'undefined'`);
    if (!hasElectronUpdate) {
        console.log('   electronUpdate not available (might be dev server)');
        console.log('   Auto-update only works in production builds');
        ws.close();
        process.exit(1);
    }
    console.log('   electronUpdate available');

    // 5. Trigger update check
    console.log('\n5. Triggering update check...');
    const updateResult = await evaluate(`
        new Promise((resolve) => {
            if (window.electronUpdate && window.electronUpdate.checkForUpdates) {
                window.electronUpdate.checkForUpdates()
                    .then(result => resolve(JSON.stringify(result)))
                    .catch(err => resolve(JSON.stringify({ error: err.message })));
            } else {
                resolve(JSON.stringify({ error: 'checkForUpdates not available' }));
            }
        })
    `);

    console.log('   Result:', updateResult);

    const result = JSON.parse(updateResult || '{}');

    if (result.error) {
        console.log('\n   Update check failed:', result.error);
    } else if (result.updateInfo) {
        console.log('\n   Update found: v' + result.updateInfo.version);
        console.log('   Download will start automatically...');
        console.log('   App will restart when ready');
    } else {
        console.log('\n   No update available or already up to date');
    }

    // 6. Cleanup
    ws.close();
    console.log('\n=== DONE ===');
}

main().catch(e => {
    console.error('Error:', e.message);
    process.exit(1);
});
