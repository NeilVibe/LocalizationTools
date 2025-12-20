/**
 * UI-027: Verify Confirm button is removed from TM Viewer
 */

const http = require('http');
const WebSocket = require('ws');

async function getCDPTarget() {
  return new Promise((resolve, reject) => {
    http.get('http://127.0.0.1:9222/json', (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          const targets = JSON.parse(data);
          const page = targets.find(t => t.type === 'page');
          if (page) resolve(page.webSocketDebuggerUrl);
          else reject(new Error('No page target'));
        } catch (e) { reject(e); }
      });
    }).on('error', reject);
  });
}

async function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function runTest() {
  const wsUrl = await getCDPTarget();
  const ws = new WebSocket(wsUrl);

  return new Promise((resolve, reject) => {
    let messageId = 1;
    const pending = new Map();

    ws.on('open', async () => {
      console.log('=== UI-027 VERIFY: CONFIRM BUTTON REMOVED ===\n');

      const send = (method, params = {}) => {
        return new Promise((res, rej) => {
          const id = messageId++;
          pending.set(id, { resolve: res, reject: rej });
          ws.send(JSON.stringify({ id, method, params }));
        });
      };

      try {
        await send('Runtime.enable');

        // Step 1: Click TM tab to open TM Manager
        console.log('1. Opening TM Manager...');
        await send('Runtime.evaluate', {
          expression: `(function() {
            const tmTab = Array.from(document.querySelectorAll('.bx--tabs__nav-link'))
              .find(el => el.textContent.includes('TM'));
            if (tmTab) { tmTab.click(); return 'clicked'; }
            return 'not found';
          })()`
        });
        await sleep(1000);

        // Step 2: Find a TM with entries and click View
        console.log('2. Looking for TM to view...');
        const viewResult = await send('Runtime.evaluate', {
          expression: `(function() {
            // Find View button in TM list
            const viewBtn = document.querySelector('button[aria-label="View entries"]');
            if (viewBtn) {
              viewBtn.click();
              return 'clicked view';
            }
            // Alternative: look for any view icon button
            const btns = document.querySelectorAll('.bx--btn--icon-only');
            for (const btn of btns) {
              const desc = btn.getAttribute('aria-label') || '';
              if (desc.toLowerCase().includes('view')) {
                btn.click();
                return 'clicked view (alt)';
              }
            }
            return 'no view button found';
          })()`,
          returnByValue: true
        });
        console.log('   Result:', viewResult.result.value);
        await sleep(1500);

        // Step 3: Check if TM Viewer modal is open and look for Confirm button
        console.log('3. Checking for Confirm button in TM Viewer...');
        const checkResult = await send('Runtime.evaluate', {
          expression: `(function() {
            // Check if modal is open
            const modal = document.querySelector('.bx--modal.is-visible');
            if (!modal) return { modal: false, message: 'Modal not open' };

            // Look for Confirm/Unconfirm button
            const buttons = modal.querySelectorAll('.bx--btn--icon-only');
            const buttonDescs = [];
            let confirmFound = false;

            buttons.forEach(btn => {
              const desc = btn.getAttribute('aria-label') ||
                          btn.querySelector('.bx--assistive-text')?.textContent || '';
              buttonDescs.push(desc);
              if (desc.toLowerCase().includes('confirm') || desc.toLowerCase().includes('unconfirm')) {
                confirmFound = true;
              }
            });

            return {
              modal: true,
              confirmFound: confirmFound,
              buttons: buttonDescs.filter(d => d.length > 0)
            };
          })()`,
          returnByValue: true
        });

        const result = checkResult.result.value;
        console.log('\n=== RESULT ===');

        if (!result.modal) {
          console.log('SKIPPED: TM Viewer modal not open (no TMs with entries?)');
        } else if (result.confirmFound) {
          console.log('FAILED: Confirm button still exists!');
          console.log('Buttons found:', result.buttons);
        } else {
          console.log('PASSED: Confirm button successfully removed');
          console.log('Buttons found:', result.buttons);
        }

        // Close modal
        await send('Runtime.evaluate', {
          expression: `document.querySelector('.bx--modal-close')?.click()`
        });

        ws.close();
        resolve();

      } catch (err) {
        console.error('Test error:', err.message);
        ws.close();
        reject(err);
      }
    });

    ws.on('message', (data) => {
      const msg = JSON.parse(data);
      if (msg.id && pending.has(msg.id)) {
        const { resolve, reject } = pending.get(msg.id);
        pending.delete(msg.id);
        if (msg.error) reject(new Error(msg.error.message));
        else resolve(msg.result);
      }
    });

    ws.on('error', reject);
  });
}

runTest().catch(console.error);
