/**
 * CDP Test: Check LDM internal state
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
            console.log('=== LDM STATE DEBUG ===\n');

            // Try calling the checkHealth manually
            const manualCheck = await send(ws, id++, 'Runtime.evaluate', {
                expression: `
                    (async function() {
                        const API_BASE = 'http://localhost:8888';
                        const token = localStorage.getItem('auth_token');

                        console.log('Manual health check starting...');

                        try {
                            const resp1 = await fetch(API_BASE + '/api/ldm/health', {
                                headers: { 'Authorization': 'Bearer ' + token }
                            });
                            const health = await resp1.json();
                            console.log('Health:', health);

                            const resp2 = await fetch(API_BASE + '/api/status', {
                                headers: { 'Authorization': 'Bearer ' + token }
                            });
                            const status = await resp2.json();
                            console.log('Status:', status);

                            return JSON.stringify({
                                health: health,
                                status: status,
                                allGood: true
                            });
                        } catch (err) {
                            return JSON.stringify({ error: err.message });
                        }
                    })()
                `,
                returnByValue: true,
                awaitPromise: true
            });
            console.log('Manual check:', manualCheck.result?.result?.value);

            // Check if there's a Svelte component state we can access
            const svelteState = await send(ws, id++, 'Runtime.evaluate', {
                expression: `
                    JSON.stringify({
                        // Check visible elements
                        hasLoadingElement: !!document.querySelector('.loading-state'),
                        hasErrorBanner: !!document.querySelector('.error-banner'),
                        loadingText: document.querySelector('.loading-state')?.textContent?.trim(),
                        errorText: document.querySelector('.error-banner')?.textContent?.trim(),

                        // Check LDM layout
                        hasLdmLayout: !!document.querySelector('.ldm-layout'),
                        hasFileExplorer: !!document.querySelector('.file-explorer'),
                        hasVirtualGrid: !!document.querySelector('.virtual-grid'),

                        // Body classes
                        bodyClass: document.body?.className
                    })
                `,
                returnByValue: true
            });
            console.log('UI state:', svelteState.result?.result?.value);

            // Check console log messages
            const consoleLogs = await send(ws, id++, 'Runtime.evaluate', {
                expression: `
                    // Capture the last console logs
                    JSON.stringify({
                        allElements: Array.from(document.querySelectorAll('*')).length,
                        ldmAppExists: !!document.querySelector('.ldm-app'),
                        ldmAppContent: document.querySelector('.ldm-app')?.innerHTML?.substring(0, 500)
                    })
                `,
                returnByValue: true
            });
            console.log('LDM app content:', consoleLogs.result?.result?.value);

            console.log('\n=== DONE ===');
            ws.close();
            process.exit(0);
        });

        function send(ws, id, method, params) {
            return new Promise(resolve => {
                const timeout = setTimeout(() => resolve({ error: 'timeout' }), 15000);
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
