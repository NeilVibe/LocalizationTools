/**
 * UI-047 Verification Test - TM Status Display
 * Verifies that synced TMs show "Ready" instead of "Pending"
 */

const http = require('http');
const WebSocket = require('ws');
const fs = require('fs');
const path = require('path');

const SCREENSHOT_DIR = 'C:/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/Playground';

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

const sleep = ms => new Promise(r => setTimeout(r, ms));

async function runTest() {
  const wsUrl = await getCDPTarget();
  const ws = new WebSocket(wsUrl);

  return new Promise((resolve, reject) => {
    let messageId = 1;
    const pending = new Map();

    const send = (method, params = {}) => {
      return new Promise((res, rej) => {
        const id = messageId++;
        const timeout = setTimeout(() => {
          pending.delete(id);
          rej(new Error(`Timeout: ${method}`));
        }, 30000);
        pending.set(id, { resolve: res, reject: rej, timeout });
        ws.send(JSON.stringify({ id, method, params }));
      });
    };

    const evaluate = async (expression) => {
      const result = await send('Runtime.evaluate', {
        expression,
        returnByValue: true,
        awaitPromise: true
      });
      return result.result?.value;
    };

    const screenshot = async (name) => {
      const result = await send('Page.captureScreenshot', { format: 'png' });
      const filename = `${SCREENSHOT_DIR}/ui047_${name}.png`;
      fs.writeFileSync(filename, Buffer.from(result.data, 'base64'));
      console.log(`   [Screenshot: ${path.basename(filename)}]`);
      return filename;
    };

    ws.on('open', async () => {
      console.log('=== UI-047 VERIFICATION TEST ===\n');
      console.log('Testing: TM status shows "Ready" instead of "Pending"\n');

      try {
        await send('Runtime.enable');
        await send('Page.enable');

        // Step 1: Navigate to TM tab
        console.log('[1] Navigating to TM tab...');
        await evaluate(`
          const tmTab = Array.from(document.querySelectorAll('button, [role="tab"]'))
            .find(el => el.textContent.trim() === 'TM');
          if (tmTab) tmTab.click();
        `);
        await sleep(1500);
        await screenshot('01_tm_tab');

        // Step 2: Get all TM items and their status tags
        console.log('[2] Checking TM status tags...');
        const tmItems = await evaluate(`
          (function() {
            const items = [];
            // Find TM items in the list
            const tmElements = document.querySelectorAll('.tm-item, [class*="tm-list"] button, button');
            for (const el of tmElements) {
              // Check if it has a tag element
              const tag = el.querySelector('.bx--tag, [class*="Tag"]');
              if (tag) {
                const name = el.querySelector('.tm-name')?.textContent || el.textContent.split('\\n')[0].trim();
                const tagText = tag.textContent.trim();
                const tagClass = tag.className;
                items.push({ name: name.substring(0, 30), status: tagText, tagClass });
              }
            }
            return items;
          })()
        `);

        console.log('\n   TM Status Tags Found:');
        if (tmItems && tmItems.length > 0) {
          for (const tm of tmItems) {
            const icon = tm.status.toLowerCase() === 'ready' ? '✓' :
                        tm.status.toLowerCase() === 'pending' ? '⏳' : '?';
            console.log(`   ${icon} "${tm.name}" → ${tm.status}`);
          }
        } else {
          console.log('   No TM items with status tags found');
        }

        // Step 3: Check specifically for Ready vs Pending
        console.log('\n[3] Analyzing results...');
        const readyCount = tmItems?.filter(t => t.status.toLowerCase() === 'ready').length || 0;
        const pendingCount = tmItems?.filter(t => t.status.toLowerCase() === 'pending').length || 0;
        const indexedCount = tmItems?.filter(t => t.status.toLowerCase() === 'indexed').length || 0;

        console.log(`   Ready: ${readyCount}`);
        console.log(`   Pending: ${pendingCount}`);
        console.log(`   Indexed (old): ${indexedCount}`);

        // Step 4: Take final screenshot
        await screenshot('02_tm_status_tags');

        // Summary
        console.log('\n=== TEST RESULT ===');

        if (readyCount > 0 && pendingCount === 0) {
          console.log('[PASS] ✓ All TMs show "Ready" status');
          console.log('UI-047 FIX VERIFIED');
        } else if (pendingCount > 0) {
          console.log('[FAIL] ✗ Some TMs still show "Pending"');
          console.log('UI-047 FIX NOT WORKING');
        } else if (indexedCount > 0) {
          console.log('[PARTIAL] TMs show "Indexed" (old text) - fix applied but text not updated');
        } else {
          console.log('[INFO] No TMs with status tags found');
          console.log('Check if TMs exist and have been synced');
        }

        console.log('\nScreenshots saved to:', SCREENSHOT_DIR);

        ws.close();
        resolve({ readyCount, pendingCount, indexedCount, items: tmItems });

      } catch (err) {
        console.error('Test error:', err.message);
        await screenshot('error');
        ws.close();
        reject(err);
      }
    });

    ws.on('message', (data) => {
      const msg = JSON.parse(data.toString());
      if (msg.id && pending.has(msg.id)) {
        const { resolve, reject, timeout } = pending.get(msg.id);
        clearTimeout(timeout);
        pending.delete(msg.id);
        if (msg.error) reject(new Error(msg.error.message));
        else resolve(msg.result);
      }
    });

    ws.on('error', reject);
  });
}

runTest()
  .then(result => {
    console.log('\nDone.');
    process.exit(result.pendingCount === 0 && result.readyCount > 0 ? 0 : 1);
  })
  .catch(err => {
    console.error('Fatal:', err);
    process.exit(1);
  });
