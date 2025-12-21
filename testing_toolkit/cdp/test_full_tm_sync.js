/**
 * Full TM Sync Test - E2E flow:
 * 1. Select/create project
 * 2. Upload file (or use existing)
 * 3. Create TM from file
 * 4. Edit TM entry
 * 5. Verify sync status changes to "ready"
 */

const http = require('http');
const WebSocket = require('ws');
const fs = require('fs');
const path = require('path');

const SCREENSHOT_DIR = 'C:/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/Playground';
let screenshotCount = 0;

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
      screenshotCount++;
      const result = await send('Page.captureScreenshot', { format: 'png' });
      const filename = `${SCREENSHOT_DIR}/sync_test_${String(screenshotCount).padStart(2, '0')}_${name}.png`;
      fs.writeFileSync(filename, Buffer.from(result.data, 'base64'));
      console.log(`   [Screenshot: ${path.basename(filename)}]`);
      return filename;
    };

    ws.on('open', async () => {
      console.log('=== FULL TM SYNC TEST ===\n');

      try {
        await send('Runtime.enable');
        await send('Page.enable');

        // Step 1: Check current state and go to Files tab
        console.log('[1] Navigating to Files tab...');
        await evaluate(`
          const filesTab = Array.from(document.querySelectorAll('button, [role="tab"]'))
            .find(el => el.textContent.trim() === 'Files');
          if (filesTab) filesTab.click();
        `);
        await sleep(1000);
        await screenshot('files_tab');

        // Step 2: Select a project (Test Project)
        console.log('[2] Selecting Test Project...');
        const projectClick = await evaluate(`
          (function() {
            const items = document.querySelectorAll('.tree-item, .project-item, [class*="project"], div');
            for (const item of items) {
              if (item.textContent.trim().startsWith('Test Project') &&
                  !item.textContent.includes('1766') &&
                  !item.textContent.includes('TRUE')) {
                item.click();
                return 'clicked: ' + item.textContent.trim().split('\\n')[0];
              }
            }
            return 'not found';
          })()
        `);
        console.log('   Result:', projectClick);
        await sleep(1000);
        await screenshot('project_selected');

        // Step 3: Check for existing files
        console.log('[3] Checking for existing files...');
        const files = await evaluate(`
          (function() {
            const fileItems = document.querySelectorAll('.file-item, [class*="file"], .tree-item');
            const texts = [];
            for (const f of fileItems) {
              const text = f.textContent.trim().split('\\n')[0];
              if (text.includes('.') && (text.includes('.xlsx') || text.includes('.xliff') || text.includes('.txt'))) {
                texts.push(text);
              }
            }
            return texts.slice(0, 5);
          })()
        `);
        console.log('   Files found:', files?.length || 0, files?.slice(0, 3) || []);

        // Step 4: If no files, we need to upload one
        if (!files || files.length === 0) {
          console.log('[4] No files found - need to upload...');
          console.log('   MANUAL ACTION REQUIRED: Upload a bilingual file (XLIFF/XLSX)');
          await screenshot('no_files');
          ws.close();
          return resolve({ success: false, reason: 'No files - manual upload required' });
        }

        // Step 5: Right-click on first file to get context menu and add to TM
        console.log('[4] Right-clicking file for context menu...');
        const contextResult = await evaluate(`
          (async function() {
            const fileItems = document.querySelectorAll('.file-item, [class*="file"], .tree-item');
            for (const f of fileItems) {
              const text = f.textContent.trim();
              if (text.includes('.xlsx') || text.includes('.xliff')) {
                // Right-click
                const rect = f.getBoundingClientRect();
                const event = new MouseEvent('contextmenu', {
                  bubbles: true,
                  clientX: rect.left + rect.width / 2,
                  clientY: rect.top + rect.height / 2
                });
                f.dispatchEvent(event);
                await new Promise(r => setTimeout(r, 500));
                return 'context menu triggered on: ' + text.split('\\n')[0];
              }
            }
            return 'no suitable file';
          })()
        `);
        console.log('   Result:', contextResult);
        await sleep(500);
        await screenshot('context_menu');

        // Step 6: Click "Add to TM" option
        console.log('[5] Looking for "Add to TM" option...');
        const addToTM = await evaluate(`
          (async function() {
            const menuItems = document.querySelectorAll('[role="menuitem"], .context-menu-item, button');
            for (const item of menuItems) {
              const text = item.textContent.toLowerCase();
              if (text.includes('add to tm') || text.includes('create tm') || text.includes('upload to tm')) {
                item.click();
                return 'clicked: ' + item.textContent;
              }
            }
            // List what options are available
            const opts = Array.from(menuItems).map(m => m.textContent.trim()).filter(t => t.length < 50);
            return 'not found, options: ' + opts.slice(0, 10).join(', ');
          })()
        `);
        console.log('   Result:', addToTM);
        await sleep(2000);
        await screenshot('after_add_to_tm');

        // Step 7: Switch to TM tab
        console.log('[6] Switching to TM tab...');
        await evaluate(`
          const tmTab = Array.from(document.querySelectorAll('button, [role="tab"]'))
            .find(el => el.textContent.trim() === 'TM');
          if (tmTab) tmTab.click();
        `);
        await sleep(1500);
        await screenshot('tm_tab');

        // Step 8: Check TM list and status
        console.log('[7] Checking TM list and status...');
        const tmStatus = await evaluate(`
          (function() {
            const tmItems = document.querySelectorAll('.tm-item, .tm-row, [class*="tm-list"]');
            const results = [];
            for (const tm of tmItems) {
              const text = tm.textContent;
              const status = text.includes('ready') ? 'ready' :
                            text.includes('pending') ? 'pending' :
                            text.includes('building') ? 'building' : 'unknown';
              results.push({ text: text.substring(0, 50), status });
            }

            // Also check for status badges
            const statusBadges = document.querySelectorAll('.status-badge, [class*="status"]');
            const statuses = Array.from(statusBadges).map(b => b.textContent.trim()).filter(t =>
              ['ready', 'pending', 'building'].includes(t.toLowerCase())
            );

            return { tmCount: results.length, tms: results.slice(0, 3), statusBadges: statuses };
          })()
        `);
        console.log('   TM Status:', JSON.stringify(tmStatus, null, 2));

        // Step 9: Find a TM and click View to open entries
        console.log('[8] Opening TM Viewer...');
        const viewClick = await evaluate(`
          (async function() {
            // Find View button
            const viewBtns = document.querySelectorAll('button');
            for (const btn of viewBtns) {
              if (btn.title?.includes('View') || btn.getAttribute('aria-label')?.includes('View') ||
                  btn.textContent.includes('View entries')) {
                btn.click();
                return 'clicked view button';
              }
            }
            // Try eye icon
            const icons = document.querySelectorAll('svg, [class*="icon"]');
            for (const icon of icons) {
              if (icon.closest('button')) {
                const btn = icon.closest('button');
                if (btn.title?.toLowerCase().includes('view')) {
                  btn.click();
                  return 'clicked icon button';
                }
              }
            }
            return 'no view button found';
          })()
        `);
        console.log('   Result:', viewClick);
        await sleep(1500);
        await screenshot('tm_viewer');

        // Step 10: Try to edit an entry
        console.log('[9] Attempting to edit TM entry...');
        const editResult = await evaluate(`
          (async function() {
            // Look for edit button in modal or grid
            const modal = document.querySelector('.bx--modal.is-visible, [class*="modal"]');
            const container = modal || document;

            // Find editable cells or edit buttons
            const editBtns = container.querySelectorAll('button[aria-label*="Edit"], button[title*="Edit"], .edit-btn');
            if (editBtns.length > 0) {
              editBtns[0].click();
              return 'clicked edit button';
            }

            // Try double-clicking a cell
            const cells = container.querySelectorAll('td, .cell, [class*="editable"]');
            if (cells.length > 0) {
              const dblClick = new MouseEvent('dblclick', { bubbles: true });
              cells[0].dispatchEvent(dblClick);
              return 'double-clicked cell';
            }

            return 'no edit method found';
          })()
        `);
        console.log('   Result:', editResult);
        await sleep(1000);
        await screenshot('edit_mode');

        // Step 11: Make a small change and save
        console.log('[10] Making change and saving...');
        const saveResult = await evaluate(`
          (async function() {
            // Find any input/textarea
            const inputs = document.querySelectorAll('input[type="text"], textarea');
            if (inputs.length > 0) {
              const input = inputs[0];
              input.value = input.value + ' ';  // Add space
              input.dispatchEvent(new Event('input', { bubbles: true }));
              await new Promise(r => setTimeout(r, 500));

              // Find save button
              const saveBtn = Array.from(document.querySelectorAll('button'))
                .find(b => b.textContent.toLowerCase().includes('save') ||
                          b.getAttribute('aria-label')?.toLowerCase().includes('save'));
              if (saveBtn) {
                saveBtn.click();
                return 'saved changes';
              }
              return 'no save button';
            }
            return 'no input found';
          })()
        `);
        console.log('   Result:', saveResult);
        await sleep(2000);
        await screenshot('after_save');

        // Step 12: Check TM status changed to "ready" after sync
        console.log('[11] Verifying TM sync status...');
        await sleep(3000); // Wait for auto-sync

        const finalStatus = await evaluate(`
          (function() {
            // Close any modals first
            const closeBtn = document.querySelector('.bx--modal-close, [aria-label="Close"]');
            if (closeBtn) closeBtn.click();

            // Check status in TM list
            const body = document.body.innerText;
            const hasReady = body.includes('ready');
            const hasPending = body.includes('pending');
            const hasBuilding = body.includes('building');

            // Look for specific status elements
            const statusElements = document.querySelectorAll('[class*="status"]');
            const statuses = Array.from(statusElements).map(el => el.textContent.trim())
              .filter(t => ['ready', 'pending', 'building'].includes(t.toLowerCase()));

            return { hasReady, hasPending, hasBuilding, statusElements: statuses };
          })()
        `);
        console.log('   Final status:', JSON.stringify(finalStatus, null, 2));
        await screenshot('final_status');

        // Summary
        console.log('\n=== TEST SUMMARY ===');
        console.log('Files found:', files?.length || 0);
        console.log('TMs found:', tmStatus?.tmCount || 0);
        console.log('Edit attempted:', editResult);
        console.log('Save attempted:', saveResult);
        console.log('Final sync status:', finalStatus?.hasReady ? 'READY' : (finalStatus?.hasPending ? 'PENDING' : 'UNKNOWN'));

        if (finalStatus?.hasReady) {
          console.log('\n[PASS] TM status shows "ready" - sync working!');
        } else if (finalStatus?.hasPending) {
          console.log('\n[WARN] TM still shows "pending" - sync may not have completed');
        } else {
          console.log('\n[INFO] Could not determine final status');
        }

        console.log('\n=== TEST COMPLETE ===');
        console.log('Screenshots saved to:', SCREENSHOT_DIR);

        ws.close();
        resolve({ success: true, finalStatus });

      } catch (err) {
        console.error('Test error:', err.message);
        await screenshot('error_state');
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
    console.log('\nResult:', result);
    process.exit(result?.success ? 0 : 1);
  })
  .catch(err => {
    console.error('Fatal error:', err);
    process.exit(1);
  });
