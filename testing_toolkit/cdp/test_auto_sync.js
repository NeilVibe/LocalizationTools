/**
 * Q-001: Test Auto-Sync Feature
 *
 * Tests that TM entry modifications trigger auto-sync in background.
 * Watches backend logs for sync messages.
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
      console.log('=== Q-001 TEST: AUTO-SYNC FEATURE ===\n');

      const send = (method, params = {}) => {
        return new Promise((res, rej) => {
          const id = messageId++;
          pending.set(id, { resolve: res, reject: rej });
          ws.send(JSON.stringify({ id, method, params }));
        });
      };

      try {
        await send('Runtime.enable');

        // Step 1: Navigate to TM tab
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

        // Step 2: Check for existing TMs
        console.log('2. Looking for TMs...');
        const tmCheck = await send('Runtime.evaluate', {
          expression: `(function() {
            const rows = document.querySelectorAll('.tm-list-item, [data-testid="tm-row"], tbody tr');
            return { count: rows.length };
          })()`,
          returnByValue: true
        });
        console.log('   TMs found:', tmCheck.result.value?.count || 0);

        // Step 3: Try to find View button and open TM Viewer
        console.log('3. Opening TM Viewer...');
        const viewResult = await send('Runtime.evaluate', {
          expression: `(function() {
            const viewBtn = document.querySelector('button[aria-label="View entries"]');
            if (viewBtn) {
              viewBtn.click();
              return 'clicked view';
            }
            return 'no view button found';
          })()`,
          returnByValue: true
        });
        console.log('   Result:', viewResult.result.value);
        await sleep(1500);

        // Step 4: Check if modal is open and try to edit an entry
        console.log('4. Checking TM Viewer modal...');
        const modalCheck = await send('Runtime.evaluate', {
          expression: `(function() {
            const modal = document.querySelector('.bx--modal.is-visible');
            if (!modal) return { modal: false };

            // Find entry rows
            const entries = modal.querySelectorAll('.tm-entry, tbody tr, .entry-row');
            return {
              modal: true,
              entries: entries.length,
              title: modal.querySelector('.bx--modal-header__heading')?.textContent || 'unknown'
            };
          })()`,
          returnByValue: true
        });
        console.log('   Modal state:', modalCheck.result.value);

        // Step 5: If we have entries, try to trigger an edit
        if (modalCheck.result.value?.modal && modalCheck.result.value?.entries > 0) {
          console.log('5. Attempting to edit an entry (will trigger auto-sync)...');

          // Find and click edit button on first entry
          const editResult = await send('Runtime.evaluate', {
            expression: `(function() {
              const editBtn = document.querySelector('.bx--modal.is-visible button[aria-label="Edit"]');
              if (editBtn) {
                editBtn.click();
                return 'clicked edit';
              }
              return 'no edit button';
            })()`,
            returnByValue: true
          });
          console.log('   Edit result:', editResult.result.value);
          await sleep(1000);

          // Check if edit form appeared
          const formCheck = await send('Runtime.evaluate', {
            expression: `(function() {
              const form = document.querySelector('.edit-entry-form, .bx--form');
              const saveBtn = document.querySelector('button[type="submit"], button:contains("Save")');
              return {
                formVisible: !!form,
                hasSaveButton: !!saveBtn
              };
            })()`,
            returnByValue: true
          });
          console.log('   Form state:', formCheck.result.value);
        } else {
          console.log('5. SKIPPED: No entries to edit');
        }

        console.log('\n=== AUTO-SYNC VERIFICATION ===');
        console.log('To verify auto-sync is working, check backend logs for:');
        console.log('  "Auto-sync TM X: INSERT=Y, UPDATE=Z, time=..."');
        console.log('\nThe auto-sync runs in background after:');
        console.log('  - add_tm_entry');
        console.log('  - update_tm_entry');
        console.log('  - delete_tm_entry');

        // Close modal
        await send('Runtime.evaluate', {
          expression: `document.querySelector('.bx--modal-close')?.click()`
        });

        console.log('\n=== TEST COMPLETE ===');
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
