/**
 * CDP Test: Find API URL and connection issues
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

        ws.on('open', async () => {
            console.log('=== API URL & CONNECTION CHECK ===\n');

            // Check localStorage for API settings
            const storage = await send(ws, id++, 'Runtime.evaluate', {
                expression: `JSON.stringify(Object.fromEntries(Object.keys(localStorage).map(k => [k, localStorage.getItem(k)])))`,
                returnByValue: true
            });
            console.log('localStorage:', storage.result?.result?.value);

            // Check for API base URL in various places
            const apiCheck = await send(ws, id++, 'Runtime.evaluate', {
                expression: `JSON.stringify({
                    VITE_API_URL: typeof import !== 'undefined' ? 'check import.meta' : 'no import',
                    windowLocation: window.location.href,
                    documentDomain: document.domain
                })`,
                returnByValue: true
            });
            console.log('API check:', apiCheck.result?.result?.value);

            // Look for any hardcoded URLs in scripts
            const scriptUrls = await send(ws, id++, 'Runtime.evaluate', {
                expression: `JSON.stringify({
                    scripts: Array.from(document.scripts).map(s => s.src).filter(s => s).slice(0, 5)
                })`,
                returnByValue: true
            });
            console.log('Scripts:', scriptUrls.result?.result?.value);

            // Check the actual fetch/network that's happening
            // Install network interceptor
            await send(ws, id++, 'Runtime.evaluate', {
                expression: `
                    window.__networkLog = [];
                    const originalFetch = window.fetch;
                    window.fetch = function(...args) {
                        window.__networkLog.push({type: 'fetch', url: args[0], time: Date.now()});
                        return originalFetch.apply(this, args).catch(err => {
                            window.__networkLog.push({type: 'fetchError', url: args[0], error: err.message});
                            throw err;
                        });
                    };
                    'interceptor installed'
                `,
                returnByValue: true
            });

            // Wait a bit for network activity
            await new Promise(r => setTimeout(r, 3000));

            // Get network log
            const networkLog = await send(ws, id++, 'Runtime.evaluate', {
                expression: `JSON.stringify(window.__networkLog || [])`,
                returnByValue: true
            });
            console.log('\nNetwork log:', networkLog.result?.result?.value);

            // Check console for errors by evaluating history
            const consoleCheck = await send(ws, id++, 'Runtime.evaluate', {
                expression: `JSON.stringify({
                    hasErrors: typeof console.error !== 'undefined',
                    bodyContent: document.body?.innerText?.substring(0, 500)
                })`,
                returnByValue: true
            });
            console.log('\nBody content:', consoleCheck.result?.result?.value);

            // Check if there's an embedded backend config
            const backendConfig = await send(ws, id++, 'Runtime.evaluate', {
                expression: `JSON.stringify({
                    electronAPI: typeof window.electronAPI,
                    nodeIntegration: typeof require !== 'undefined',
                    processEnv: typeof process !== 'undefined' ? 'exists' : 'no'
                })`,
                returnByValue: true
            });
            console.log('\nBackend config:', backendConfig.result?.result?.value);

            console.log('\n=== DONE ===');
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
