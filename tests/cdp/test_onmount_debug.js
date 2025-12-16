/**
 * CDP Test: Check if LDM onMount is running at all
 * Listen for ALL console output including the logger
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
        let allLogs = [];

        ws.on('open', async () => {
            console.log('=== ONMOUNT DEBUG TEST ===\n');

            // Enable Console and Runtime
            await send(ws, id++, 'Console.enable', {});
            await send(ws, id++, 'Runtime.enable', {});

            // Capture ALL console output
            ws.on('message', (data) => {
                const msg = JSON.parse(data);
                if (msg.method === 'Runtime.consoleAPICalled') {
                    const args = msg.params.args.map(a => {
                        if (a.type === 'object' && a.preview) {
                            return JSON.stringify(a.preview.properties?.reduce((o, p) => (o[p.name] = p.value, o), {}) || a.preview);
                        }
                        return a.value || a.description || '?';
                    }).join(' ');
                    allLogs.push(`[${msg.params.type}] ${args}`);
                    console.log(`  [${msg.params.type}] ${args}`);
                } else if (msg.method === 'Runtime.exceptionThrown') {
                    const exc = msg.params.exceptionDetails;
                    allLogs.push(`[EXCEPTION] ${JSON.stringify(exc)}`);
                    console.log(`  [EXCEPTION] ${JSON.stringify(exc)}`);
                }
            });

            // Step 1: Check what console logs exist
            console.log('--- Step 1: Existing console logs in last 5 seconds ---');
            console.log('Listening for 5 seconds...\n');

            await new Promise(r => setTimeout(r, 5000));

            console.log('\n--- Step 2: Navigate to LDM to trigger fresh onMount ---');

            // Try clicking on LDM nav item to remount
            const clickResult = await send(ws, id++, 'Runtime.evaluate', {
                expression: `
                    (function() {
                        // Find and click on a different app first, then back to LDM
                        const navItems = document.querySelectorAll('.nav-item, .app-nav-item, [data-app]');
                        console.log('[TEST] Found nav items:', navItems.length);

                        // Look for any navigation element
                        const allButtons = document.querySelectorAll('button');
                        console.log('[TEST] Found buttons:', allButtons.length);

                        // Check current URL/route
                        console.log('[TEST] Current URL:', window.location.href);
                        console.log('[TEST] Current hash:', window.location.hash);

                        return JSON.stringify({
                            navItems: navItems.length,
                            buttons: allButtons.length,
                            url: window.location.href
                        });
                    })()
                `,
                returnByValue: true
            });
            console.log('Click result:', clickResult.result?.result?.value);

            // Step 3: Force reload the page and watch onMount
            console.log('\n--- Step 3: Reload page to watch fresh onMount ---');
            await send(ws, id++, 'Page.reload', {});

            // Wait for page to load
            await new Promise(r => setTimeout(r, 3000));

            // Step 4: Check state after reload
            console.log('\n--- Step 4: State after reload ---');
            const postReloadState = await send(ws, id++, 'Runtime.evaluate', {
                expression: `
                    JSON.stringify({
                        hasLoadingElement: !!document.querySelector('.loading-state'),
                        hasLdmLayout: !!document.querySelector('.ldm-layout'),
                        hasErrorBanner: !!document.querySelector('.error-banner'),
                        loadingText: document.querySelector('.loading-state')?.textContent?.trim(),
                        bodyHTML: document.body?.innerHTML?.substring(0, 200)
                    })
                `,
                returnByValue: true
            });
            console.log('Post-reload state:', postReloadState.result?.result?.value);

            // Wait a bit more for any async operations
            await new Promise(r => setTimeout(r, 3000));

            console.log('\n--- Step 5: Final state after waiting ---');
            const finalState = await send(ws, id++, 'Runtime.evaluate', {
                expression: `
                    JSON.stringify({
                        hasLoadingElement: !!document.querySelector('.loading-state'),
                        hasLdmLayout: !!document.querySelector('.ldm-layout'),
                        hasErrorBanner: !!document.querySelector('.error-banner')
                    })
                `,
                returnByValue: true
            });
            console.log('Final state:', finalState.result?.result?.value);

            console.log('\n--- All captured logs ---');
            allLogs.forEach(log => console.log('  ' + log));

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
