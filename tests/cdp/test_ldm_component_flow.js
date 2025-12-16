/**
 * CDP Test: Mirror EXACTLY what LDM.svelte onMount does
 * To find why loading stays true
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
            console.log('=== LDM COMPONENT FLOW TEST ===\n');

            // Enable Console and Runtime to catch ALL logs
            await send(ws, id++, 'Console.enable', {});
            await send(ws, id++, 'Runtime.enable', {});

            // Listen for console messages
            ws.on('message', (data) => {
                const msg = JSON.parse(data);
                if (msg.method === 'Runtime.consoleAPICalled') {
                    const args = msg.params.args.map(a => a.value || a.description || '?').join(' ');
                    console.log(`  [console.${msg.params.type}] ${args}`);
                } else if (msg.method === 'Runtime.exceptionThrown') {
                    const exc = msg.params.exceptionDetails;
                    console.log(`  [EXCEPTION] ${exc.text}`);
                }
            });

            // Step 1: Check initial state
            console.log('--- Step 1: Check initial state ---');
            const initialState = await send(ws, id++, 'Runtime.evaluate', {
                expression: `
                    JSON.stringify({
                        hasLoadingElement: !!document.querySelector('.loading-state'),
                        hasLdmLayout: !!document.querySelector('.ldm-layout'),
                        hasErrorBanner: !!document.querySelector('.error-banner'),
                        loadingText: document.querySelector('.loading-state')?.textContent?.trim(),
                        errorText: document.querySelector('.error-banner')?.textContent?.trim(),
                        authToken: !!localStorage.getItem('auth_token'),
                        tokenPreview: localStorage.getItem('auth_token')?.substring(0, 20) + '...'
                    })
                `,
                returnByValue: true
            });
            console.log('Initial state:', initialState.result?.result?.value);

            // Step 2: Try the EXACT same calls the component makes
            console.log('\n--- Step 2: Mimic checkHealth() ---');
            const healthCheck = await send(ws, id++, 'Runtime.evaluate', {
                expression: `
                    (async function() {
                        const API_BASE = 'http://localhost:8888';
                        const token = localStorage.getItem('auth_token');
                        const headers = token ? { 'Authorization': 'Bearer ' + token } : {};

                        console.log('[TEST] checkHealth starting, token exists:', !!token);

                        try {
                            const response = await fetch(API_BASE + '/api/ldm/health', { headers });
                            console.log('[TEST] checkHealth response status:', response.status);

                            if (!response.ok) {
                                throw new Error('HTTP ' + response.status);
                            }

                            const data = await response.json();
                            console.log('[TEST] checkHealth data:', JSON.stringify(data));
                            return JSON.stringify({ success: true, data });
                        } catch (err) {
                            console.log('[TEST] checkHealth ERROR:', err.message);
                            return JSON.stringify({ success: false, error: err.message });
                        }
                    })()
                `,
                returnByValue: true,
                awaitPromise: true
            });
            console.log('Health check result:', healthCheck.result?.result?.value);

            // Step 3: fetchConnectionStatus
            console.log('\n--- Step 3: Mimic fetchConnectionStatus() ---');
            const statusCheck = await send(ws, id++, 'Runtime.evaluate', {
                expression: `
                    (async function() {
                        const API_BASE = 'http://localhost:8888';
                        const token = localStorage.getItem('auth_token');
                        const headers = token ? { 'Authorization': 'Bearer ' + token } : {};

                        console.log('[TEST] fetchConnectionStatus starting');

                        try {
                            const response = await fetch(API_BASE + '/api/status', { headers });
                            console.log('[TEST] fetchConnectionStatus response status:', response.status);

                            if (response.ok) {
                                const data = await response.json();
                                console.log('[TEST] fetchConnectionStatus data:', JSON.stringify(data));
                                return JSON.stringify({ success: true, data });
                            } else {
                                return JSON.stringify({ success: false, status: response.status });
                            }
                        } catch (err) {
                            console.log('[TEST] fetchConnectionStatus ERROR:', err.message);
                            return JSON.stringify({ success: false, error: err.message });
                        }
                    })()
                `,
                returnByValue: true,
                awaitPromise: true
            });
            console.log('Status check result:', statusCheck.result?.result?.value);

            // Step 4: Check if there are any pending promises or errors
            console.log('\n--- Step 4: Check for JavaScript errors ---');
            const jsErrors = await send(ws, id++, 'Runtime.evaluate', {
                expression: `
                    JSON.stringify({
                        // Check if window.onerror caught anything
                        lastError: window.__lastError || null,
                        // Check for unhandled rejections
                        unhandledRejection: window.__unhandledRejection || null
                    })
                `,
                returnByValue: true
            });
            console.log('JS errors:', jsErrors.result?.result?.value);

            // Step 5: Final state check
            console.log('\n--- Step 5: Final state check ---');
            const finalState = await send(ws, id++, 'Runtime.evaluate', {
                expression: `
                    JSON.stringify({
                        hasLoadingElement: !!document.querySelector('.loading-state'),
                        hasLdmLayout: !!document.querySelector('.ldm-layout'),
                        hasErrorBanner: !!document.querySelector('.error-banner'),
                        ldmAppHTML: document.querySelector('.ldm-app')?.innerHTML?.substring(0, 300)
                    })
                `,
                returnByValue: true
            });
            console.log('Final state:', finalState.result?.result?.value);

            // Step 6: Try to find the Svelte component's internal state
            console.log('\n--- Step 6: Look for Svelte component state ---');
            const svelteState = await send(ws, id++, 'Runtime.evaluate', {
                expression: `
                    // Look for Svelte 5 runes state on the component
                    const ldmApp = document.querySelector('.ldm-app');
                    const allElements = document.querySelectorAll('*');
                    let svelteComponents = [];

                    allElements.forEach(el => {
                        // Svelte 5 uses $$ for internal state
                        if (el.$$) {
                            svelteComponents.push({
                                tag: el.tagName,
                                class: el.className,
                                hasContext: !!el.$$.ctx
                            });
                        }
                    });

                    JSON.stringify({
                        svelteComponentsFound: svelteComponents.length,
                        components: svelteComponents.slice(0, 5)
                    })
                `,
                returnByValue: true
            });
            console.log('Svelte state:', svelteState.result?.result?.value);

            console.log('\n=== TEST COMPLETE ===');
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
