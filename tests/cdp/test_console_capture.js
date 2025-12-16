/**
 * CDP Test: Capture console output and errors
 */
const http = require('http');
const WebSocket = require('ws');

http.get('http://127.0.0.1:9222/json', (res) => {
    let data = '';
    res.on('data', chunk => data += chunk);
    res.on('end', () => {
        const targets = JSON.parse(data);
        const page = targets.find(t => t.type === 'page');
        const ws = new WebSocket(page.webSocketDebuggerUrl);
        let id = 1;
        let consoleLogs = [];

        ws.on('open', async () => {
            console.log('=== CONSOLE CAPTURE ===\n');

            // Enable Console and Runtime
            await send(ws, id++, 'Console.enable', {});
            await send(ws, id++, 'Runtime.enable', {});

            // Listen for console messages
            ws.on('message', (data) => {
                const msg = JSON.parse(data);
                if (msg.method === 'Console.messageAdded') {
                    const log = msg.params.message;
                    consoleLogs.push(`[${log.level}] ${log.text}`);
                    console.log(`[${log.level}] ${log.text}`);
                } else if (msg.method === 'Runtime.consoleAPICalled') {
                    const args = msg.params.args.map(a => a.value || a.description || '?').join(' ');
                    consoleLogs.push(`[${msg.params.type}] ${args}`);
                    console.log(`[${msg.params.type}] ${args}`);
                } else if (msg.method === 'Runtime.exceptionThrown') {
                    const exc = msg.params.exceptionDetails;
                    consoleLogs.push(`[EXCEPTION] ${exc.text}`);
                    console.log(`[EXCEPTION] ${JSON.stringify(exc)}`);
                }
            });

            // Wait a bit for any logs
            console.log('Waiting for console output...\n');
            await new Promise(r => setTimeout(r, 3000));

            // Try to reload the LDM component
            console.log('\n--- Triggering navigation to check logs ---');
            await send(ws, id++, 'Runtime.evaluate', {
                expression: `
                    console.log('[TEST] Manual log test');
                    console.log('[TEST] Auth token exists:', !!localStorage.getItem('auth_token'));
                `,
                returnByValue: true
            });

            await new Promise(r => setTimeout(r, 2000));

            // Check for errors in the DOM
            const domErrors = await send(ws, id++, 'Runtime.evaluate', {
                expression: `
                    JSON.stringify({
                        errors: Array.from(document.querySelectorAll('[class*="error"]')).map(e => ({
                            class: e.className,
                            text: e.textContent?.substring(0, 100)
                        })),
                        scripts: Array.from(document.scripts).length,
                        bodyHTML: document.body?.innerHTML?.substring(0, 200)
                    })
                `,
                returnByValue: true
            });
            console.log('\nDOM state:', domErrors.result?.result?.value);

            console.log('\n=== Captured', consoleLogs.length, 'log entries ===');
            ws.close();
            process.exit(0);
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
}).on('error', e => {
    console.log('CDP Error:', e.message);
    process.exit(1);
});
