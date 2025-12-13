/**
 * BUG-005: Edit Modal Keyboard Shortcuts Test
 *
 * Tests Ctrl+S (Confirm/Reviewed) and Ctrl+T (Translate Only) keyboard shortcuts
 * in the LDM Cell Edit Modal.
 *
 * Usage:
 *   1. Start LocaNext with CDP: ./LocaNext.exe --remote-debugging-port=9222
 *   2. Run: node tests/cdp/test_edit_keyboard.js
 *
 * Test Flow:
 *   1. Expand project and load a file
 *   2. Double-click a target cell to open edit modal
 *   3. Add instrumentation to track keyboard events
 *   4. Dispatch Ctrl+S and Ctrl+T events
 *   5. Report whether handlers were triggered
 */

const WebSocket = require('ws');
const http = require('http');

const CDP_URL = 'http://localhost:9222/json';
const VERBOSE = process.argv.includes('--verbose') || process.argv.includes('-v');

function log(...args) {
  console.log(...args);
}

function debug(...args) {
  if (VERBOSE) console.log('[DEBUG]', ...args);
}

http.get(CDP_URL, (res) => {
  let data = '';
  res.on('data', chunk => data += chunk);
  res.on('end', () => {
    const targets = JSON.parse(data);
    const page = targets.find(t => t.type === 'page' && !t.url.includes('devtools'));

    if (!page) {
      console.error('ERROR: No page found. Is LocaNext running with --remote-debugging-port=9222?');
      process.exit(1);
    }

    log('Found page:', page.url);
    const ws = new WebSocket(page.webSocketDebuggerUrl);
    let id = 1;

    ws.on('open', async () => {
      log('');
      log('='.repeat(60));
      log('  BUG-005: EDIT MODAL KEYBOARD SHORTCUTS TEST');
      log('='.repeat(60));
      log('');

      // Enable necessary domains
      await send(ws, id++, 'Page.enable', {});
      await send(ws, id++, 'Runtime.enable', {});
      await send(ws, id++, 'DOM.enable', {});

      // Step 1: Check current state
      log('Step 1: Checking current page state...');
      const stateCheck = await send(ws, id++, 'Runtime.evaluate', {
        expression: `
          (function() {
            const projects = document.querySelectorAll('.project-item');
            const cells = document.querySelectorAll('.cell.target');
            const modal = document.querySelector('.edit-modal');
            return JSON.stringify({
              projectCount: projects.length,
              targetCellCount: cells.length,
              modalOpen: modal !== null
            });
          })()
        `,
        returnByValue: true
      });
      const state = JSON.parse(stateCheck.result?.result?.value || '{}');
      log('  Projects:', state.projectCount);
      log('  Target cells:', state.targetCellCount);
      log('  Modal open:', state.modalOpen);
      log('');

      // Step 2: If no cells, load a file first
      if (state.targetCellCount === 0) {
        log('Step 2: Loading file (no cells visible)...');

        // Click first project
        await send(ws, id++, 'Runtime.evaluate', {
          expression: `document.querySelectorAll('.project-item')[0]?.click()`,
          returnByValue: true
        });
        await sleep(1500);

        // Click first file
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
        await sleep(2500);

        // Verify cells loaded
        const cellCheck = await send(ws, id++, 'Runtime.evaluate', {
          expression: `document.querySelectorAll('.cell.target').length`,
          returnByValue: true
        });
        const cellCount = cellCheck.result?.result?.value || 0;
        log('  Cells after load:', cellCount);

        if (cellCount === 0) {
          log('ERROR: Could not load file with target cells');
          ws.close();
          process.exit(1);
        }
      } else {
        log('Step 2: File already loaded, skipping...');
      }
      log('');

      // Step 3: Instrument the keyboard handler
      log('Step 3: Adding keyboard event instrumentation...');
      await send(ws, id++, 'Runtime.evaluate', {
        expression: `
          window.__keyboardTestLog = [];
          window.__originalAlert = window.alert;
          window.alert = function(msg) {
            console.log('[ALERT]', msg);
            window.__keyboardTestLog.push({ type: 'alert', message: msg });
          };

          // Add global keydown listener to see all events
          document.addEventListener('keydown', function(e) {
            if (e.ctrlKey && (e.key === 's' || e.key === 'S' || e.key === 't' || e.key === 'T')) {
              window.__keyboardTestLog.push({
                type: 'keydown',
                key: e.key,
                ctrlKey: e.ctrlKey,
                target: e.target.tagName,
                targetClass: e.target.className,
                defaultPrevented: e.defaultPrevented,
                timestamp: Date.now()
              });
              console.log('[KEYDOWN CAPTURED]', e.key, 'ctrl:', e.ctrlKey, 'target:', e.target.tagName);
            }
          }, true); // Use capture phase

          'Instrumentation added';
        `,
        returnByValue: true
      });
      log('  Instrumentation installed');
      log('');

      // Step 4: Open edit modal
      log('Step 4: Opening edit modal (double-click target cell)...');
      await send(ws, id++, 'Runtime.evaluate', {
        expression: `
          (function() {
            window.__keyboardTestLog.push({ type: 'action', message: 'Opening modal' });
            const targetCells = document.querySelectorAll('.cell.target');
            if (targetCells.length === 0) return 'No target cells';

            const cell = targetCells[0];
            const dblClickEvent = new MouseEvent('dblclick', {
              bubbles: true,
              cancelable: true,
              view: window
            });
            cell.dispatchEvent(dblClickEvent);
            return 'Double-clicked first target cell';
          })()
        `,
        returnByValue: true
      });
      await sleep(3500); // Wait for lock acquisition

      // Check if modal opened
      const modalCheck = await send(ws, id++, 'Runtime.evaluate', {
        expression: `
          (function() {
            const modal = document.querySelector('.edit-modal');
            const textarea = document.querySelector('.target-textarea');
            return JSON.stringify({
              modalFound: modal !== null,
              textareaFound: textarea !== null,
              activeElement: document.activeElement?.tagName,
              activeClass: document.activeElement?.className
            });
          })()
        `,
        returnByValue: true
      });
      const modalState = JSON.parse(modalCheck.result?.result?.value || '{}');
      log('  Modal found:', modalState.modalFound);
      log('  Textarea found:', modalState.textareaFound);
      log('  Active element:', modalState.activeElement, modalState.activeClass);
      log('');

      if (!modalState.modalFound) {
        log('ERROR: Edit modal did not open');
        log('Check __keyboardTestLog for alerts:');
        const logResult = await send(ws, id++, 'Runtime.evaluate', {
          expression: `JSON.stringify(window.__keyboardTestLog || [])`,
          returnByValue: true
        });
        log(JSON.parse(logResult.result?.result?.value || '[]'));
        ws.close();
        process.exit(1);
      }

      // Step 5: Focus textarea and test Ctrl+S
      log('Step 5: Testing Ctrl+S (Confirm/Save as Reviewed)...');

      // First focus the textarea
      await send(ws, id++, 'Runtime.evaluate', {
        expression: `
          const textarea = document.querySelector('.target-textarea');
          if (textarea) {
            textarea.focus();
            window.__keyboardTestLog.push({ type: 'action', message: 'Focused textarea' });
          }
        `,
        returnByValue: true
      });
      await sleep(200);

      // Get textarea node and dispatch key events
      const ctrlSResult = await send(ws, id++, 'Runtime.evaluate', {
        expression: `
          (function() {
            window.__keyboardTestLog.push({ type: 'action', message: 'Dispatching Ctrl+S' });

            const textarea = document.querySelector('.target-textarea');
            const modal = document.querySelector('.edit-modal');
            const target = textarea || modal || document.body;

            // Create and dispatch keydown event
            const keydownEvent = new KeyboardEvent('keydown', {
              key: 's',
              code: 'KeyS',
              ctrlKey: true,
              bubbles: true,
              cancelable: true,
              view: window
            });

            const result = target.dispatchEvent(keydownEvent);

            return JSON.stringify({
              dispatchedTo: target.tagName + '.' + target.className,
              eventResult: result,
              defaultPrevented: keydownEvent.defaultPrevented
            });
          })()
        `,
        returnByValue: true
      });
      const ctrlS = JSON.parse(ctrlSResult.result?.result?.value || '{}');
      log('  Dispatched to:', ctrlS.dispatchedTo);
      log('  Event result:', ctrlS.eventResult);
      log('  Default prevented:', ctrlS.defaultPrevented);
      await sleep(500);

      // Step 6: Check if modal closed (indicates save worked)
      log('');
      log('Step 6: Checking if save triggered...');
      const afterCtrlS = await send(ws, id++, 'Runtime.evaluate', {
        expression: `
          (function() {
            const modal = document.querySelector('.edit-modal');
            return JSON.stringify({
              modalStillOpen: modal !== null,
              log: window.__keyboardTestLog
            });
          })()
        `,
        returnByValue: true
      });
      const afterS = JSON.parse(afterCtrlS.result?.result?.value || '{}');
      log('  Modal still open:', afterS.modalStillOpen);
      log('');

      // Step 7: Re-open modal if closed, test Ctrl+T
      if (!afterS.modalStillOpen) {
        log('Step 7: Re-opening modal for Ctrl+T test...');
        await send(ws, id++, 'Runtime.evaluate', {
          expression: `
            const targetCells = document.querySelectorAll('.cell.target');
            if (targetCells.length > 0) {
              targetCells[0].dispatchEvent(new MouseEvent('dblclick', { bubbles: true, cancelable: true, view: window }));
            }
          `,
          returnByValue: true
        });
        await sleep(3500);
      } else {
        log('Step 7: Modal still open, testing Ctrl+T...');
      }

      // Test Ctrl+T
      const ctrlTResult = await send(ws, id++, 'Runtime.evaluate', {
        expression: `
          (function() {
            window.__keyboardTestLog.push({ type: 'action', message: 'Dispatching Ctrl+T' });

            const textarea = document.querySelector('.target-textarea');
            const modal = document.querySelector('.edit-modal');
            const target = textarea || modal || document.body;

            if (textarea) textarea.focus();

            const keydownEvent = new KeyboardEvent('keydown', {
              key: 't',
              code: 'KeyT',
              ctrlKey: true,
              bubbles: true,
              cancelable: true,
              view: window
            });

            const result = target.dispatchEvent(keydownEvent);

            return JSON.stringify({
              dispatchedTo: target.tagName + '.' + target.className,
              eventResult: result,
              defaultPrevented: keydownEvent.defaultPrevented
            });
          })()
        `,
        returnByValue: true
      });
      const ctrlT = JSON.parse(ctrlTResult.result?.result?.value || '{}');
      log('  Ctrl+T dispatched to:', ctrlT.dispatchedTo);
      log('  Event result:', ctrlT.eventResult);
      log('  Default prevented:', ctrlT.defaultPrevented);
      await sleep(500);

      // Step 8: Final analysis
      log('');
      log('='.repeat(60));
      log('  FINAL ANALYSIS');
      log('='.repeat(60));
      log('');

      const finalLog = await send(ws, id++, 'Runtime.evaluate', {
        expression: `JSON.stringify(window.__keyboardTestLog || [])`,
        returnByValue: true
      });
      const testLog = JSON.parse(finalLog.result?.result?.value || '[]');

      log('Event Log:');
      testLog.forEach((entry, i) => {
        log(`  ${i + 1}. [${entry.type}] ${entry.message || entry.key || ''}`);
        if (entry.type === 'keydown') {
          log(`      Target: ${entry.target}.${entry.targetClass}`);
          log(`      Ctrl: ${entry.ctrlKey}, Prevented: ${entry.defaultPrevented}`);
        }
      });
      log('');

      // Determine result
      const keydownEvents = testLog.filter(e => e.type === 'keydown');
      const ctrlSEvents = keydownEvents.filter(e => e.key === 's' || e.key === 'S');
      const ctrlTEvents = keydownEvents.filter(e => e.key === 't' || e.key === 'T');

      log('RESULTS:');
      log('  Ctrl+S events captured:', ctrlSEvents.length);
      log('  Ctrl+T events captured:', ctrlTEvents.length);
      log('');

      if (ctrlSEvents.length === 0 && ctrlTEvents.length === 0) {
        log('❌ FAIL: No keyboard events were captured');
        log('');
        log('Likely causes:');
        log('  1. Events not bubbling to the handler');
        log('  2. Browser intercepting before JS receives them');
        log('  3. Svelte handler not attached correctly');
      } else {
        const prevented = keydownEvents.some(e => e.defaultPrevented);
        if (prevented) {
          log('✓ PARTIAL: Events captured and preventDefault called');
          log('  Handler is receiving events but save may not be working');
        } else {
          log('⚠ WARNING: Events captured but defaultPrevented=false');
          log('  Handler may not be processing the events');
        }
      }

      log('');
      log('='.repeat(60));

      ws.close();
      process.exit(0);
    });

    ws.on('error', (err) => {
      console.error('WebSocket error:', err.message);
      process.exit(1);
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

    function sleep(ms) {
      return new Promise(resolve => setTimeout(resolve, ms));
    }
  });
}).on('error', err => {
  console.error('Cannot connect to CDP endpoint:', err.message);
  console.error('');
  console.error('Make sure LocaNext is running with:');
  console.error('  ./LocaNext.exe --remote-debugging-port=9222');
  process.exit(1);
});
