/**
 * UI-034: Verify tooltip alignment fix
 *
 * Tests that right-side toolbar buttons have tooltipAlignment="end"
 * to prevent tooltips from being cut off at window edge.
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
          if (page) {
            resolve(page.webSocketDebuggerUrl);
          } else {
            reject(new Error('No page target found'));
          }
        } catch (e) {
          reject(e);
        }
      });
    }).on('error', reject);
  });
}

async function runTest() {
  const wsUrl = await getCDPTarget();
  const ws = new WebSocket(wsUrl);

  return new Promise((resolve, reject) => {
    let messageId = 1;
    const pending = new Map();

    ws.on('open', async () => {
      console.log('=== UI-034 TOOLTIP ALIGNMENT TEST ===\n');

      const send = (method, params = {}) => {
        return new Promise((res, rej) => {
          const id = messageId++;
          pending.set(id, { resolve: res, reject: rej });
          ws.send(JSON.stringify({ id, method, params }));
        });
      };

      try {
        await send('Runtime.enable');

        // Check if we're on the LDM page
        const urlResult = await send('Runtime.evaluate', {
          expression: 'window.location.href'
        });
        console.log('Current URL:', urlResult.result.value);

        // Check for tooltip alignment classes on right-side buttons
        const checkResult = await send('Runtime.evaluate', {
          expression: `(function() {
            const results = [];

            // Find all icon-only buttons with tooltips
            const buttons = document.querySelectorAll('.bx--btn--icon-only.bx--tooltip__trigger');

            // Check for align-end class (Carbon adds this when tooltipAlignment="end")
            buttons.forEach((btn, i) => {
              const hasAlignEnd = btn.classList.contains('bx--tooltip--align-end');
              const hasAlignCenter = btn.classList.contains('bx--tooltip--align-center');
              const hasAlignStart = btn.classList.contains('bx--tooltip--align-start');

              // Get button description if available
              const desc = btn.getAttribute('aria-label') ||
                          btn.querySelector('.bx--assistive-text')?.textContent ||
                          btn.title ||
                          'Button ' + i;

              // Check if button is in right side of toolbar
              const rect = btn.getBoundingClientRect();
              const viewportWidth = window.innerWidth;
              const isRightSide = rect.right > viewportWidth / 2;

              if (isRightSide) {
                results.push({
                  desc: desc.trim(),
                  alignEnd: hasAlignEnd,
                  alignCenter: hasAlignCenter,
                  alignStart: hasAlignStart,
                  x: Math.round(rect.left),
                  right: Math.round(rect.right),
                  viewportWidth: viewportWidth
                });
              }
            });

            return results;
          })()`
        });

        if (checkResult.result.value) {
          const buttons = JSON.parse(JSON.stringify(checkResult.result.value));

          if (buttons.length === 0) {
            console.log('No right-side buttons found. Make sure LDM is open.\n');
          } else {
            console.log('Right-side toolbar buttons:\n');
            let allPass = true;

            buttons.forEach(btn => {
              const status = btn.alignEnd ? 'PASS' : 'FAIL';
              if (!btn.alignEnd) allPass = false;
              console.log(`  [${status}] ${btn.desc}`);
              console.log(`         alignEnd: ${btn.alignEnd}, position: ${btn.x}px - ${btn.right}px`);
            });

            console.log('\n=== RESULT ===');
            if (allPass) {
              console.log('UI-034 VERIFIED: All right-side buttons have tooltipAlignment="end"');
            } else {
              console.log('UI-034 FAILED: Some buttons missing tooltipAlignment="end"');
            }
          }
        } else {
          // Result came as object, parse differently
          const evalResult = await send('Runtime.evaluate', {
            expression: `(function() {
              const buttons = document.querySelectorAll('.bx--btn--icon-only');
              const rightButtons = [];

              buttons.forEach(btn => {
                const rect = btn.getBoundingClientRect();
                if (rect.right > window.innerWidth / 2) {
                  const desc = btn.getAttribute('aria-label') ||
                              btn.querySelector('.bx--assistive-text')?.textContent?.trim() ||
                              'Unknown';
                  const hasAlignEnd = btn.classList.contains('bx--tooltip--align-end');
                  rightButtons.push(desc + ': ' + (hasAlignEnd ? 'OK' : 'MISSING'));
                }
              });

              return rightButtons.join('\\n');
            })()`,
            returnByValue: true
          });

          console.log('Right-side buttons:\n');
          console.log(evalResult.result.value || 'No buttons found');
        }

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
        if (msg.error) {
          reject(new Error(msg.error.message));
        } else {
          resolve(msg.result);
        }
      }
    });

    ws.on('error', reject);
  });
}

runTest().catch(console.error);
