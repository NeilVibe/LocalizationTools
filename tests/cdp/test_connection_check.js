/**
 * CDP Test: Connection Check
 * Check app state, connection status, and any errors
 */

const http = require('http');
const WebSocket = require('ws');

const CDP_PORT = 9222;

console.log('=== CONNECTION CHECK TEST ===\n');

http.get(`http://127.0.0.1:${CDP_PORT}/json`, (res) => {
    let data = '';
    res.on('data', chunk => data += chunk);
    res.on('end', async () => {
        const targets = JSON.parse(data);
        console.log('CDP Targets found:', targets.length);

        const page = targets.find(t => t.type === 'page');
        if (!page) {
            console.log('ERROR: No page target found');
            process.exit(1);
        }

        console.log('Page URL:', page.url);
        console.log('Page Title:', page.title);
        console.log('');

        const ws = new WebSocket(page.webSocketDebuggerUrl);
        let id = 1;

        ws.on('open', async () => {
            try {
                // Enable console logging
                await send(ws, id++, 'Console.enable', {});
                await send(ws, id++, 'Runtime.enable', {});

                // Intercept alerts
                await send(ws, id++, 'Runtime.evaluate', {
                    expression: `
                        window.__alertMessages = [];
                        window.__originalAlert = window.alert;
                        window.alert = function(msg) {
                            window.__alertMessages.push(msg);
                            console.log('[ALERT]', msg);
                        };
                    `,
                    returnByValue: true
                });

                console.log('--- CURRENT PAGE STATE ---');

                // Check current URL and title
                const pageInfo = await send(ws, id++, 'Runtime.evaluate', {
                    expression: `JSON.stringify({
                        url: window.location.href,
                        title: document.title,
                        body: document.body?.className || 'no-body'
                    })`,
                    returnByValue: true
                });
                console.log('Page:', JSON.parse(pageInfo.result?.result?.value || '{}'));

                // Check for login page
                const loginCheck = await send(ws, id++, 'Runtime.evaluate', {
                    expression: `JSON.stringify({
                        hasLoginForm: document.querySelector('form') !== null,
                        hasLoginButton: document.querySelector('button[type="submit"]') !== null,
                        loginInputs: Array.from(document.querySelectorAll('input')).map(i => i.type + ':' + (i.placeholder || i.name || 'unnamed'))
                    })`,
                    returnByValue: true
                });
                console.log('Login check:', JSON.parse(loginCheck.result?.result?.value || '{}'));

                // Check for error messages
                const errorCheck = await send(ws, id++, 'Runtime.evaluate', {
                    expression: `JSON.stringify({
                        errors: Array.from(document.querySelectorAll('.error, .alert-error, [class*="error"], [class*="Error"]')).map(e => e.textContent?.trim().substring(0, 100)),
                        notifications: Array.from(document.querySelectorAll('.notification, .toast, .alert')).map(e => e.textContent?.trim().substring(0, 100))
                    })`,
                    returnByValue: true
                });
                console.log('Errors/Notifications:', JSON.parse(errorCheck.result?.result?.value || '{}'));

                // Check connection status indicators
                const statusCheck = await send(ws, id++, 'Runtime.evaluate', {
                    expression: `JSON.stringify({
                        hasOfflineIndicator: document.querySelector('[class*="offline"], [class*="Offline"]') !== null,
                        hasOnlineIndicator: document.querySelector('[class*="online"], [class*="Online"]') !== null,
                        hasConnectionStatus: document.querySelector('[class*="connection"], [class*="Connection"]') !== null,
                        statusText: document.querySelector('[class*="status"]')?.textContent?.trim()
                    })`,
                    returnByValue: true
                });
                console.log('Status indicators:', JSON.parse(statusCheck.result?.result?.value || '{}'));

                // Check for loading spinners
                const loadingCheck = await send(ws, id++, 'Runtime.evaluate', {
                    expression: `JSON.stringify({
                        hasLoading: document.querySelector('.loading, .spinner, [class*="loading"], [class*="Loading"]') !== null,
                        loadingText: document.querySelector('.loading-text, [class*="loading"]')?.textContent?.trim()
                    })`,
                    returnByValue: true
                });
                console.log('Loading state:', JSON.parse(loadingCheck.result?.result?.value || '{}'));

                // Get all visible text on screen (first 500 chars)
                const visibleText = await send(ws, id++, 'Runtime.evaluate', {
                    expression: `document.body?.innerText?.substring(0, 1000) || 'no text'`,
                    returnByValue: true
                });
                console.log('\n--- VISIBLE TEXT (first 1000 chars) ---');
                console.log(visibleText.result?.result?.value || 'none');

                // Check console errors
                console.log('\n--- CHECKING CONSOLE ERRORS ---');
                const consoleErrors = await send(ws, id++, 'Runtime.evaluate', {
                    expression: `JSON.stringify(window.__consoleErrors || [])`,
                    returnByValue: true
                });
                console.log('Console errors:', JSON.parse(consoleErrors.result?.result?.value || '[]'));

                // Check alerts
                const alerts = await send(ws, id++, 'Runtime.evaluate', {
                    expression: `JSON.stringify(window.__alertMessages || [])`,
                    returnByValue: true
                });
                const alertList = JSON.parse(alerts.result?.result?.value || '[]');
                if (alertList.length > 0) {
                    console.log('\n--- ALERTS ---');
                    alertList.forEach(a => console.log('ALERT:', a));
                }

                // Check if LDM is loaded
                console.log('\n--- LDM STATE ---');
                const ldmCheck = await send(ws, id++, 'Runtime.evaluate', {
                    expression: `JSON.stringify({
                        hasLDM: document.querySelector('[class*="ldm"], [class*="LDM"], [class*="language-data"]') !== null,
                        hasGrid: document.querySelector('.virtual-grid, [class*="grid"], table') !== null,
                        hasFileExplorer: document.querySelector('[class*="file-explorer"], [class*="FileExplorer"], .tree-view') !== null,
                        projectCount: document.querySelectorAll('[class*="project"]').length,
                        fileCount: document.querySelectorAll('[class*="file-item"]').length
                    })`,
                    returnByValue: true
                });
                console.log('LDM:', JSON.parse(ldmCheck.result?.result?.value || '{}'));

                console.log('\n=== TEST COMPLETE ===');
                ws.close();
                process.exit(0);

            } catch (err) {
                console.error('Test error:', err);
                ws.close();
                process.exit(1);
            }
        });

        ws.on('error', (err) => {
            console.error('WebSocket error:', err.message);
            process.exit(1);
        });

        function send(ws, id, method, params) {
            return new Promise(resolve => {
                const timeout = setTimeout(() => resolve({ error: 'timeout' }), 10000);
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
    });
}).on('error', err => {
    console.log('Cannot connect to CDP:', err.message);
    console.log('Make sure LocaNext is running with --remote-debugging-port=9222');
    process.exit(1);
});
