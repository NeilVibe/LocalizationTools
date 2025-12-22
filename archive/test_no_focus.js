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

        ws.on('open', async () => {
            console.log('=== TEST: Ctrl+S WITHOUT explicit focus ===');
            await send(ws, id++, 'Runtime.enable', {});
            await send(ws, id++, 'Input.enable', {});

            // Open modal
            await send(ws, id++, 'Runtime.evaluate', {
                expression: "document.querySelectorAll('.cell.target')[1]?.dispatchEvent(new MouseEvent('dblclick', {bubbles:true,cancelable:true,view:window}))",
                returnByValue: true
            });
            await sleep(3500);

            // Check active element (DO NOT focus textarea)
            const active = await send(ws, id++, 'Runtime.evaluate', {
                expression: "document.activeElement.tagName + '.' + document.activeElement.className",
                returnByValue: true
            });
            console.log('Active element BEFORE:', active.result?.result?.value);

            // Send Ctrl+S without focusing
            await send(ws, id++, 'Input.dispatchKeyEvent', { type: 'keyDown', key: 'Control', code: 'ControlLeft', modifiers: 2 });
            await send(ws, id++, 'Input.dispatchKeyEvent', { type: 'keyDown', key: 's', code: 'KeyS', modifiers: 2, text: 's' });
            await send(ws, id++, 'Input.dispatchKeyEvent', { type: 'keyUp', key: 's', code: 'KeyS', modifiers: 2 });
            await send(ws, id++, 'Input.dispatchKeyEvent', { type: 'keyUp', key: 'Control', code: 'ControlLeft', modifiers: 0 });

            await sleep(500);

            const modalOpen = await send(ws, id++, 'Runtime.evaluate', {
                expression: "document.querySelector('.edit-modal') \!== null",
                returnByValue: true
            });
            console.log('Modal still open:', modalOpen.result?.result?.value);
            console.log(modalOpen.result?.result?.value ? 'FAIL: Modal stayed open' : 'SUCCESS: Modal closed');

            ws.close();
            process.exit(0);
        });

        function send(ws, id, method, params) {
            return new Promise(resolve => {
                const timeout = setTimeout(() => resolve({}), 10000);
                ws.on('message', function h(data) {
                    const msg = JSON.parse(data);
                    if (msg.id === id) { clearTimeout(timeout); ws.removeListener('message', h); resolve(msg); }
                });
                ws.send(JSON.stringify({ id, method, params }));
            });
        }
        function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }
    });
});
