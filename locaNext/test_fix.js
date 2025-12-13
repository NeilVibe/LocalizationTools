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
            console.log('=== BUG-005 FIX VERIFICATION ===');
            console.log('');
            await send(ws, id++, 'Runtime.enable', {});
            await send(ws, id++, 'Input.enable', {});

            // Load file
            await send(ws, id++, 'Runtime.evaluate', {
                expression: "document.querySelectorAll('.project-item')[0]?.click()",
                returnByValue: true
            });
            await sleep(1500);
            await send(ws, id++, 'Runtime.evaluate', {
                expression: "(function(){const w=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT,null,false);let n;while(n=w.nextNode()){if(n.textContent.trim().match(/\\.(txt|xml)$/)){n.parentElement.click();return'clicked';}}})()"
            });
            await sleep(2500);

            // Open modal via double-click (NO explicit focus - let the fix handle it)
            console.log('Step 1: Opening modal (fix should auto-focus textarea)...');
            await send(ws, id++, 'Runtime.evaluate', {
                expression: "document.querySelectorAll('.cell.target')[0]?.dispatchEvent(new MouseEvent('dblclick', {bubbles:true,cancelable:true,view:window}))",
                returnByValue: true
            });
            await sleep(3500);

            // Check where focus landed
            const focusCheck = await send(ws, id++, 'Runtime.evaluate', {
                expression: "document.activeElement.tagName + '.' + document.activeElement.className",
                returnByValue: true
            });
            console.log('  Focus on:', focusCheck.result?.result?.value);

            const isFocusCorrect = focusCheck.result?.result?.value?.includes('TEXTAREA');
            console.log('  Auto-focus worked:', isFocusCorrect ? 'YES' : 'NO');

            // Now send Ctrl+S without any manual focus
            console.log('');
            console.log('Step 2: Sending Ctrl+S (no manual focus)...');
            await send(ws, id++, 'Input.dispatchKeyEvent', { type: 'keyDown', key: 'Control', code: 'ControlLeft', modifiers: 2 });
            await send(ws, id++, 'Input.dispatchKeyEvent', { type: 'keyDown', key: 's', code: 'KeyS', modifiers: 2, text: 's' });
            await send(ws, id++, 'Input.dispatchKeyEvent', { type: 'keyUp', key: 's', code: 'KeyS', modifiers: 2 });
            await send(ws, id++, 'Input.dispatchKeyEvent', { type: 'keyUp', key: 'Control', code: 'ControlLeft', modifiers: 0 });
            await sleep(500);

            const modalOpen = await send(ws, id++, 'Runtime.evaluate', {
                expression: "document.querySelector('.edit-modal') \!== null",
                returnByValue: true
            });

            console.log('  Modal still open:', modalOpen.result?.result?.value);
            console.log('');
            console.log('=================================');
            if (\!modalOpen.result?.result?.value) {
                console.log('SUCCESS: BUG-005 FIXED\!');
                console.log('Ctrl+S works without manual focus\!');
            } else if (isFocusCorrect) {
                console.log('PARTIAL: Focus correct but Ctrl+S failed');
            } else {
                console.log('FAIL: Auto-focus did not work');
            }
            console.log('=================================');

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
