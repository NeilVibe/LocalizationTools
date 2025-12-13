/**
 * BUG-005: Edit Modal Keyboard Shortcuts Test (REAL KEY SIMULATION)
 *
 * Uses CDP Input.dispatchKeyEvent to simulate REAL keyboard input
 * (not JavaScript KeyboardEvent which may bypass Electron interception)
 *
 * Usage:
 *   1. Start LocaNext with CDP: ./LocaNext.exe --remote-debugging-port=9222
 *   2. Run via PowerShell: node test_edit_keyboard_real.js
 */

const WebSocket = require('ws');
const http = require('http');

const CDP_URL = 'http://localhost:9222/json';

function log(...args) {
  console.log(...args);
}

http.get(CDP_URL, (res) => {
  let data = '';
  res.on('data', chunk => data += chunk);
  res.on('end', () => {
    const targets = JSON.parse(data);
    const page = targets.find(t => t.type === 'page' && !t.url.includes('devtools'));

    if (!page) {
      console.error('ERROR: No page found');
      process.exit(1);
    }

    const ws = new WebSocket(page.webSocketDebuggerUrl);
    let id = 1;

    ws.on('open', async () => {
      log('');
      log('='.repeat(60));
      log('  BUG-005: REAL KEY SIMULATION TEST');
      log('  Using CDP Input.dispatchKeyEvent');
      log('='.repeat(60));
      log('');

      await send(ws, id++, 'Page.enable', {});
      await send(ws, id++, 'Runtime.enable', {});
      await send(ws, id++, 'Input.enable', {});

      // Check state and load file if needed
      log('Step 1: Checking state...');
      const state = await send(ws, id++, 'Runtime.evaluate', {
        expression: `JSON.stringify({
          targetCells: document.querySelectorAll('.cell.target').length,
          modalOpen: document.querySelector('.edit-modal') !== null
        })`,
        returnByValue: true
      });
      const s = JSON.parse(state.result?.result?.value || '{}');
      log('  Target cells:', s.targetCells);

      if (s.targetCells === 0) {
        log('Step 2: Loading file...');
        await send(ws, id++, 'Runtime.evaluate', {
          expression: `document.querySelectorAll('.project-item')[0]?.click()`,
          returnByValue: true
        });
        await sleep(1500);
        await send(ws, id++, 'Runtime.evaluate', {
          expression: `
            (function() {
              const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
              let node;
              while (node = walker.nextNode()) {
                if (node.textContent.trim().match(/\\.(txt|xml)$/)) {
                  node.parentElement.click();
                  return 'clicked';
                }
              }
            })()
          `,
          returnByValue: true
        });
        await sleep(2500);
      }

      // Add instrumentation
      log('Step 3: Adding keyboard instrumentation...');
      await send(ws, id++, 'Runtime.evaluate', {
        expression: `
          window.__realKeyLog = [];
          document.addEventListener('keydown', function(e) {
            window.__realKeyLog.push({
              key: e.key,
              code: e.code,
              ctrlKey: e.ctrlKey,
              target: e.target.tagName + '.' + e.target.className,
              defaultPrevented: e.defaultPrevented,
              time: Date.now()
            });
          }, true);
          'instrumented'
        `,
        returnByValue: true
      });

      // Open modal
      log('Step 4: Opening edit modal...');
      await send(ws, id++, 'Runtime.evaluate', {
        expression: `
          const cell = document.querySelectorAll('.cell.target')[0];
          if (cell) cell.dispatchEvent(new MouseEvent('dblclick', { bubbles: true, cancelable: true, view: window }));
        `,
        returnByValue: true
      });
      await sleep(3500);

      // Check modal opened
      const modalState = await send(ws, id++, 'Runtime.evaluate', {
        expression: `JSON.stringify({
          modalOpen: document.querySelector('.edit-modal') !== null,
          textareaFound: document.querySelector('.target-textarea') !== null
        })`,
        returnByValue: true
      });
      const m = JSON.parse(modalState.result?.result?.value || '{}');
      log('  Modal open:', m.modalOpen);
      log('  Textarea found:', m.textareaFound);

      if (!m.modalOpen) {
        log('ERROR: Modal did not open');
        ws.close();
        process.exit(1);
      }

      // Focus textarea
      log('Step 5: Focusing textarea...');
      await send(ws, id++, 'Runtime.evaluate', {
        expression: `document.querySelector('.target-textarea')?.focus()`,
        returnByValue: true
      });
      await sleep(200);

      // Simulate Ctrl+S using CDP Input.dispatchKeyEvent (REAL key simulation)
      log('');
      log('Step 6: Sending REAL Ctrl+S via Input.dispatchKeyEvent...');

      // Key down for Ctrl
      await send(ws, id++, 'Input.dispatchKeyEvent', {
        type: 'keyDown',
        key: 'Control',
        code: 'ControlLeft',
        windowsVirtualKeyCode: 17,
        nativeVirtualKeyCode: 17,
        modifiers: 2  // Ctrl modifier
      });

      // Key down for S (with Ctrl held)
      await send(ws, id++, 'Input.dispatchKeyEvent', {
        type: 'keyDown',
        key: 's',
        code: 'KeyS',
        windowsVirtualKeyCode: 83,
        nativeVirtualKeyCode: 83,
        modifiers: 2,  // Ctrl modifier
        text: 's'
      });

      // Key up for S
      await send(ws, id++, 'Input.dispatchKeyEvent', {
        type: 'keyUp',
        key: 's',
        code: 'KeyS',
        windowsVirtualKeyCode: 83,
        nativeVirtualKeyCode: 83,
        modifiers: 2
      });

      // Key up for Ctrl
      await send(ws, id++, 'Input.dispatchKeyEvent', {
        type: 'keyUp',
        key: 'Control',
        code: 'ControlLeft',
        windowsVirtualKeyCode: 17,
        nativeVirtualKeyCode: 17,
        modifiers: 0
      });

      await sleep(500);

      // Check what happened
      log('');
      log('Step 7: Checking results...');

      const afterState = await send(ws, id++, 'Runtime.evaluate', {
        expression: `JSON.stringify({
          modalStillOpen: document.querySelector('.edit-modal') !== null,
          keyLog: window.__realKeyLog || []
        })`,
        returnByValue: true
      });
      const after = JSON.parse(afterState.result?.result?.value || '{}');

      log('  Modal still open:', after.modalStillOpen);
      log('  Key events captured:', after.keyLog.length);

      if (after.keyLog.length > 0) {
        log('  Key log:');
        after.keyLog.forEach((k, i) => {
          log(`    ${i + 1}. ${k.key} (ctrl=${k.ctrlKey}) → ${k.target}`);
        });
      }

      // VERDICT
      log('');
      log('='.repeat(60));
      log('  VERDICT');
      log('='.repeat(60));
      log('');

      const ctrlSFound = after.keyLog.some(k => k.key === 's' && k.ctrlKey);

      if (!after.modalStillOpen) {
        log('✓ SUCCESS: Modal closed! Ctrl+S worked!');
      } else if (ctrlSFound) {
        log('⚠ PARTIAL: Ctrl+S event was captured but modal stayed open');
        log('  → Handler received event but save may have failed');
      } else if (after.keyLog.length === 0) {
        log('❌ FAIL: No key events reached the page');
        log('  → Electron may be intercepting Ctrl+S before renderer');
      } else {
        log('❌ FAIL: Key events captured but no Ctrl+S');
        log('  → Check key log above');
      }

      log('');

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

    function sleep(ms) {
      return new Promise(r => setTimeout(r, ms));
    }
  });
}).on('error', err => {
  console.error('Cannot connect:', err.message);
  process.exit(1);
});
