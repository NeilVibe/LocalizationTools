const WebSocket = require('ws');
const http = require('http');

http.get('http://localhost:9222/json', (res) => {
    let data = '';
    res.on('data', chunk => data += chunk);
    res.on('end', () => {
        const targets = JSON.parse(data);
        const page = targets.find(t => t.type === 'page');
        const ws = new WebSocket(page.webSocketDebuggerUrl);
        let id = 1;
        let alertMessages = [];

        // Track JavaScript dialogs (alerts)
        ws.on('message', (data) => {
            const msg = JSON.parse(data);
            if (msg.method === 'Page.javascriptDialogOpening') {
                console.log('>>> ALERT DETECTED:', msg.params.message);
                alertMessages.push(msg.params.message);
                // Auto-dismiss the alert
                ws.send(JSON.stringify({
                    id: id++,
                    method: 'Page.handleJavaScriptDialog',
                    params: { accept: true }
                }));
            }
        });

        ws.on('open', async () => {
            console.log('=== BUG-002 FINAL TEST ===');
            console.log('');

            // Enable Page events to catch alerts
            await send(ws, id++, 'Page.enable', {});
            await send(ws, id++, 'Runtime.enable', {});

            // Intercept alert() calls
            await send(ws, id++, 'Runtime.evaluate', {
                expression: `
                    window.__originalAlert = window.alert;
                    window.__alertMessages = [];
                    window.alert = function(msg) {
                        console.log('[ALERT INTERCEPTED]', msg);
                        window.__alertMessages.push(msg);
                        // Don't show the actual alert
                    };
                `,
                returnByValue: true
            });

            // Step 1: Click project
            console.log('Step 1: Expanding project...');
            await send(ws, id++, 'Runtime.evaluate', {
                expression: `document.querySelectorAll('.project-item')[0]?.click()`,
                returnByValue: true
            });
            await new Promise(r => setTimeout(r, 1500));

            // Step 2: Click file
            console.log('Step 2: Loading file...');
            await send(ws, id++, 'Runtime.evaluate', {
                expression: `
                    (function() {
                        const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
                        let node;
                        while (node = walker.nextNode()) {
                            const text = node.textContent.trim();
                            if (text.endsWith('.txt') || text.endsWith('.xml')) {
                                node.parentElement.click();
                                return 'Clicked: ' + text;
                            }
                        }
                        return 'No file found';
                    })()
                `,
                returnByValue: true
            });
            await new Promise(r => setTimeout(r, 2500));

            // Step 3: Check grid and join file status
            console.log('Step 3: Checking grid and WebSocket status...');
            const statusCheck = await send(ws, id++, 'Runtime.evaluate', {
                expression: `
                    (function() {
                        const targetCells = document.querySelectorAll('.cell.target');
                        // Check console for any LDM messages
                        return JSON.stringify({
                            targetCellCount: targetCells.length,
                            pageText: document.body.innerText.substring(0, 500)
                        });
                    })()
                `,
                returnByValue: true
            });
            const status = JSON.parse(statusCheck.result?.result?.value || '{}');
            console.log('  Target cells:', status.targetCellCount);
            console.log('');

            if (status.targetCellCount === 0) {
                console.log('ERROR: No target cells - grid not loaded');
                ws.close();
                process.exit(1);
            }

            // Step 4: Double-click target cell
            console.log('Step 4: Double-clicking target cell...');
            const dblClick = await send(ws, id++, 'Runtime.evaluate', {
                expression: `
                    (function() {
                        const targetCells = document.querySelectorAll('.cell.target');
                        if (targetCells.length === 0) return 'No target cells';

                        const cell = targetCells[0];
                        const dblClickEvent = new MouseEvent('dblclick', {
                            bubbles: true,
                            cancelable: true,
                            view: window
                        });
                        cell.dispatchEvent(dblClickEvent);
                        return 'Double-clicked';
                    })()
                `,
                returnByValue: true
            });
            console.log('  Result:', dblClick.result?.result?.value);

            // Wait for response
            await new Promise(r => setTimeout(r, 3000));

            // Step 5: Check intercepted alerts
            console.log('Step 5: Checking for intercepted alerts...');
            const alertCheck = await send(ws, id++, 'Runtime.evaluate', {
                expression: `JSON.stringify(window.__alertMessages || [])`,
                returnByValue: true
            });
            const alerts = JSON.parse(alertCheck.result?.result?.value || '[]');
            console.log('  Intercepted alerts:', alerts);
            console.log('');

            // Step 6: Check modal state
            console.log('Step 6: Checking final state...');
            const finalState = await send(ws, id++, 'Runtime.evaluate', {
                expression: `
                    (function() {
                        const modal = document.querySelector('.bx--modal--open');
                        const textarea = document.querySelector('textarea');
                        return JSON.stringify({
                            modalOpen: modal !== null,
                            textareaVisible: textarea !== null,
                            modalTitle: modal?.querySelector('.bx--modal-header__heading')?.innerText || ''
                        });
                    })()
                `,
                returnByValue: true
            });
            const final = JSON.parse(finalState.result?.result?.value || '{}');
            console.log('  Modal open:', final.modalOpen);
            console.log('  Textarea visible:', final.textareaVisible);
            console.log('  Modal title:', final.modalTitle);
            console.log('');

            // VERDICT
            console.log('========================================');
            console.log('               VERDICT');
            console.log('========================================');

            if (final.modalOpen || final.textareaVisible) {
                console.log('');
                console.log('  ✓ SUCCESS! BUG-002 IS FIXED!');
                console.log('  Edit modal opened successfully!');
                console.log('');
            } else if (alerts.length > 0) {
                const lockAlert = alerts.find(a =>
                    a.includes('locked') || a.includes('Lock') || a.includes('acquire')
                );
                if (lockAlert) {
                    console.log('');
                    console.log('  ✗ FAILED! BUG-002 NOT FIXED');
                    console.log('  Lock alert shown:', lockAlert);
                    console.log('');
                } else {
                    console.log('');
                    console.log('  ? PARTIAL - Alert shown but not lock-related:');
                    console.log('  Alerts:', alerts);
                    console.log('');
                }
            } else {
                console.log('');
                console.log('  ? INCONCLUSIVE');
                console.log('  No modal and no alert intercepted.');
                console.log('  Double-click event may not have triggered.');
                console.log('');
            }

            ws.close();
            process.exit(0);
        });

        function send(ws, id, method, params) {
            return new Promise(resolve => {
                const timeout = setTimeout(() => {
                    resolve({ error: 'timeout' });
                }, 10000);
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
    console.log('HTTP Error:', err.message);
    process.exit(1);
});
