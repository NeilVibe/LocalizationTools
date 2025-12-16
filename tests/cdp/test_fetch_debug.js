/**
 * CDP Test: Debug fetch call to backend
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
            console.log('=== FETCH DEBUG TEST ===\n');

            // Try to make a direct fetch call
            const fetchResult = await send(ws, id++, 'Runtime.evaluate', {
                expression: `
                    (async function() {
                        try {
                            const token = localStorage.getItem('auth_token');
                            console.log('Token exists:', !!token);

                            const controller = new AbortController();
                            const timeoutId = setTimeout(() => controller.abort(), 5000);

                            console.log('Fetching http://localhost:8888/health...');
                            const response = await fetch('http://localhost:8888/health', {
                                signal: controller.signal,
                                headers: {
                                    'Authorization': 'Bearer ' + token
                                }
                            });
                            clearTimeout(timeoutId);

                            console.log('Response status:', response.status);
                            const data = await response.json();
                            return JSON.stringify({success: true, status: response.status, data: data});
                        } catch (err) {
                            console.log('Fetch error:', err.message);
                            return JSON.stringify({success: false, error: err.message, name: err.name});
                        }
                    })()
                `,
                returnByValue: true,
                awaitPromise: true
            });
            console.log('Fetch result:', fetchResult.result?.result?.value);

            // Check if there are CORS errors
            const corsCheck = await send(ws, id++, 'Runtime.evaluate', {
                expression: `
                    (async function() {
                        try {
                            // Try without auth first
                            const controller = new AbortController();
                            const timeoutId = setTimeout(() => controller.abort(), 5000);

                            const response = await fetch('http://localhost:8888/health', {
                                signal: controller.signal
                            });
                            clearTimeout(timeoutId);

                            return JSON.stringify({success: true, status: response.status});
                        } catch (err) {
                            return JSON.stringify({success: false, error: err.message});
                        }
                    })()
                `,
                returnByValue: true,
                awaitPromise: true
            });
            console.log('CORS check (no auth):', corsCheck.result?.result?.value);

            // Check the specific LDM health endpoint
            const ldmHealth = await send(ws, id++, 'Runtime.evaluate', {
                expression: `
                    (async function() {
                        try {
                            const token = localStorage.getItem('auth_token');
                            const controller = new AbortController();
                            const timeoutId = setTimeout(() => controller.abort(), 5000);

                            const response = await fetch('http://localhost:8888/api/ldm/health', {
                                signal: controller.signal,
                                headers: {
                                    'Authorization': 'Bearer ' + token,
                                    'Content-Type': 'application/json'
                                }
                            });
                            clearTimeout(timeoutId);

                            const data = await response.json();
                            return JSON.stringify({success: true, status: response.status, data: data});
                        } catch (err) {
                            return JSON.stringify({success: false, error: err.message});
                        }
                    })()
                `,
                returnByValue: true,
                awaitPromise: true
            });
            console.log('LDM health:', ldmHealth.result?.result?.value);

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
