/**
 * CDP Login Script - Login to LocaNext via CDP
 *
 * Usage (from Windows PowerShell):
 *   Push-Location '\\wsl.localhost\Ubuntu2\home\neil1988\LocalizationTools\testing_toolkit\cdp'
 *   node login.js
 *
 * Credentials: Uses CDP_TEST_USER/CDP_TEST_PASS env vars, or defaults to neil/neil
 */
const WebSocket = require('ws');
const http = require('http');

const sleep = ms => new Promise(r => setTimeout(r, ms));

// Get credentials from environment (REQUIRED - no fallback for security)
const TEST_USER = process.env.CDP_TEST_USER;
const TEST_PASS = process.env.CDP_TEST_PASS;

if (!TEST_USER || !TEST_PASS) {
    console.error('ERROR: CDP_TEST_USER and CDP_TEST_PASS environment variables are required');
    console.error('For CI: Configure Gitea secrets (CI_TEST_USER, CI_TEST_PASS)');
    console.error('For local: export CDP_TEST_USER=username CDP_TEST_PASS=password');
    process.exit(1);
}

async function main() {
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

    console.log('=== CDP LOGIN ===');

    // Check if already logged in
    const bodyText = await evaluate('document.body.innerText.substring(0, 200)');
    if (!bodyText.includes('Login') && !bodyText.includes('Password')) {
        console.log('Already logged in!');
        console.log('Body:', bodyText);
        ws.close();
        return;
    }

    console.log(`Logging in as: ${TEST_USER}`);

    // Fill username
    await evaluate(`
        const inputs = document.querySelectorAll('input');
        const usernameInput = inputs[0];
        if (usernameInput) {
            usernameInput.value = '${TEST_USER}';
            usernameInput.dispatchEvent(new Event('input', {bubbles: true}));
        }
    `);
    console.log('Username filled');

    // Fill password
    await evaluate(`
        const passwordInput = document.querySelector('input[type="password"]');
        if (passwordInput) {
            passwordInput.value = '${TEST_PASS}';
            passwordInput.dispatchEvent(new Event('input', {bubbles: true}));
        }
    `);
    console.log('Password filled');

    await sleep(500);

    // Click login
    await evaluate(`
        const loginBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Login'));
        if (loginBtn) loginBtn.click();
    `);
    console.log('Login clicked');

    // Wait for navigation
    await sleep(3000);

    const result = await evaluate('document.body.innerText.substring(0, 500)');
    console.log('\n=== RESULT ===');
    console.log(result);

    ws.close();
}

main().catch(e => { console.error(e); process.exit(1); });
