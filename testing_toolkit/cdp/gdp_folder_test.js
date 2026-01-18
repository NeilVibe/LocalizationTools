/**
 * GDP (Granular Debug Protocol) Test: Folder Creation in Offline Storage
 * Microscopic step-by-step debugging
 */
const CDP = require('chrome-remote-interface');
const fs = require('fs');

const sleep = ms => new Promise(r => setTimeout(r, ms));

async function gdpTest() {
  console.log('='.repeat(60));
  console.log('GDP TEST: Folder Creation in Offline Storage');
  console.log('='.repeat(60));

  let client;
  try {
    // Connect
    console.log('\n[GDP] Connecting to CDP port 9222...');
    const targets = await CDP.List({ port: 9222 });
    console.log('[GDP] Found', targets.length, 'targets');

    const mainTarget = targets.find(t => t.type === 'page');
    if (!mainTarget) {
      console.log('[GDP] ERROR: No page target found');
      return;
    }
    console.log('[GDP] Connecting to:', mainTarget.url);

    client = await CDP({ target: mainTarget });
    const { Page, Runtime, Input, Console } = client;

    await Page.enable();
    await Runtime.enable();
    await Console.enable();

    // Capture ALL console messages
    Console.messageAdded(({ message }) => {
      console.log(`[BROWSER ${message.level.toUpperCase()}]`, message.text);
    });

    const screenshot = async (name) => {
      const { data } = await Page.captureScreenshot({ format: 'png' });
      const path = `C:/Users/MYCOM/Pictures/gdp_${name}.png`;
      fs.writeFileSync(path, Buffer.from(data, 'base64'));
      console.log('[GDP] Screenshot:', name);
    };

    const run = async (js) => {
      const r = await Runtime.evaluate({ expression: js, returnByValue: true });
      if (r.exceptionDetails) {
        console.log('[GDP] JS ERROR:', r.exceptionDetails.text);
      }
      return r.result?.value;
    };

    const click = async (x, y, desc) => {
      console.log(`[GDP] Click at (${x}, ${y}) - ${desc}`);
      await Input.dispatchMouseEvent({ type: 'mousePressed', x, y, button: 'left', clickCount: 1 });
      await Input.dispatchMouseEvent({ type: 'mouseReleased', x, y, button: 'left' });
    };

    const rightClick = async (x, y, desc) => {
      console.log(`[GDP] Right-click at (${x}, ${y}) - ${desc}`);
      await Input.dispatchMouseEvent({ type: 'mousePressed', x, y, button: 'right', clickCount: 1 });
      await Input.dispatchMouseEvent({ type: 'mouseReleased', x, y, button: 'right' });
    };

    // ==================== STEP 1: Initial State ====================
    console.log('\n' + '='.repeat(60));
    console.log('STEP 1: Check Initial State');
    console.log('='.repeat(60));

    await screenshot('01_initial');

    const pageText = await run(`document.body.innerText.substring(0, 500)`);
    console.log('[GDP] Page text:', pageText.substring(0, 200));

    const breadcrumb = await run(`document.querySelector('.breadcrumb')?.innerText || 'NO BREADCRUMB'`);
    console.log('[GDP] Breadcrumb:', breadcrumb);

    const isInOfflineStorage = breadcrumb.includes('Offline Storage');
    console.log('[GDP] In Offline Storage:', isInOfflineStorage);

    // ==================== STEP 2: Navigate to Offline Storage ====================
    if (!isInOfflineStorage) {
      console.log('\n' + '='.repeat(60));
      console.log('STEP 2: Navigate to Offline Storage');
      console.log('='.repeat(60));

      const offlineEl = await run(`
        const el = Array.from(document.querySelectorAll('.explorer-grid .row')).find(row => row.innerText.includes('Offline Storage'));
        if (el) {
          const rect = el.getBoundingClientRect();
          JSON.stringify({ x: rect.x + 100, y: rect.y + 20, found: true });
        } else {
          JSON.stringify({ found: false, rows: document.querySelectorAll('.explorer-grid .row').length });
        }
      `);
      console.log('[GDP] Offline Storage element:', offlineEl);

      if (offlineEl) {
        const data = JSON.parse(offlineEl);
        if (data.found) {
          // Double-click to enter
          await click(data.x, data.y, 'First click on Offline Storage');
          await sleep(100);
          await click(data.x, data.y, 'Second click (double-click)');
          await sleep(2000);
          await screenshot('02_entered_offline');
        } else {
          console.log('[GDP] ERROR: Offline Storage row not found! Rows:', data.rows);
          return;
        }
      }
    }

    // ==================== STEP 3: Verify Inside Offline Storage ====================
    console.log('\n' + '='.repeat(60));
    console.log('STEP 3: Verify Inside Offline Storage');
    console.log('='.repeat(60));

    const breadcrumb2 = await run(`document.querySelector('.breadcrumb')?.innerText || 'NO BREADCRUMB'`);
    console.log('[GDP] Current breadcrumb:', breadcrumb2);

    const rowCount = await run(`document.querySelectorAll('.explorer-grid .row').length`);
    console.log('[GDP] Row count:', rowCount);

    const emptyState = await run(`document.body.innerText.includes('This folder is empty')`);
    console.log('[GDP] Shows empty state:', emptyState);

    await screenshot('03_inside_offline');

    // ==================== STEP 4: Right-Click for Context Menu ====================
    console.log('\n' + '='.repeat(60));
    console.log('STEP 4: Open Context Menu');
    console.log('='.repeat(60));

    // Get grid position
    const gridRect = await run(`
      const grid = document.querySelector('.explorer-grid');
      grid ? JSON.stringify(grid.getBoundingClientRect()) : null
    `);
    console.log('[GDP] Grid rect:', gridRect);

    if (gridRect) {
      const rect = JSON.parse(gridRect);
      await rightClick(rect.x + 400, rect.y + 200, 'Right-click on grid');
      await sleep(500);
      await screenshot('04_context_menu');
    }

    // ==================== STEP 5: Check Context Menu ====================
    console.log('\n' + '='.repeat(60));
    console.log('STEP 5: Check Context Menu');
    console.log('='.repeat(60));

    const menuItems = await run(`
      const items = Array.from(document.querySelectorAll('.context-menu-item, [class*="context-menu"] button, [class*="context-menu"] div'));
      items.filter(el => el.offsetParent).map(el => el.innerText.trim()).filter(t => t).join(', ')
    `);
    console.log('[GDP] Context menu items:', menuItems);

    const newFolderEl = await run(`
      const items = Array.from(document.querySelectorAll('*'));
      const nf = items.find(el => el.innerText === 'New Folder' && el.offsetParent !== null && el.offsetWidth > 0);
      if (nf) {
        const rect = nf.getBoundingClientRect();
        JSON.stringify({ x: rect.x + rect.width/2, y: rect.y + rect.height/2, found: true, tag: nf.tagName });
      } else {
        JSON.stringify({ found: false });
      }
    `);
    console.log('[GDP] New Folder element:', newFolderEl);

    // ==================== STEP 6: Click New Folder ====================
    console.log('\n' + '='.repeat(60));
    console.log('STEP 6: Click New Folder');
    console.log('='.repeat(60));

    if (newFolderEl) {
      const data = JSON.parse(newFolderEl);
      if (data.found) {
        await click(data.x, data.y, 'Click New Folder');
        await sleep(1000);
        await screenshot('05_after_new_folder_click');
      } else {
        console.log('[GDP] ERROR: New Folder not found in menu!');
        return;
      }
    }

    // ==================== STEP 7: Check Modal ====================
    console.log('\n' + '='.repeat(60));
    console.log('STEP 7: Check Modal');
    console.log('='.repeat(60));

    const hasModal = await run(`!!document.querySelector('.bx--modal--open, [role="dialog"]')`);
    console.log('[GDP] Modal open:', hasModal);

    const hasInput = await run(`!!document.querySelector('input[placeholder="Enter folder name"]')`);
    console.log('[GDP] Folder name input exists:', hasInput);

    if (!hasInput) {
      console.log('[GDP] ERROR: Folder creation modal did not open!');
      await screenshot('05b_no_modal');
      return;
    }

    // ==================== STEP 8: Enter Folder Name ====================
    console.log('\n' + '='.repeat(60));
    console.log('STEP 8: Enter Folder Name');
    console.log('='.repeat(60));

    const folderName = `GDPTest_${Date.now()}`;
    console.log('[GDP] Folder name:', folderName);

    await run(`document.querySelector('input[placeholder="Enter folder name"]').focus()`);
    await sleep(100);
    await Input.insertText({ text: folderName });
    await sleep(300);

    const inputValue = await run(`document.querySelector('input[placeholder="Enter folder name"]').value`);
    console.log('[GDP] Input value after typing:', inputValue);

    await screenshot('06_name_entered');

    // ==================== STEP 9: Click Create ====================
    console.log('\n' + '='.repeat(60));
    console.log('STEP 9: Click Create Button');
    console.log('='.repeat(60));

    const createBtn = await run(`
      const btns = Array.from(document.querySelectorAll('button'));
      const btn = btns.find(b => b.textContent.trim() === 'Create' && b.offsetParent !== null);
      if (btn) {
        const rect = btn.getBoundingClientRect();
        JSON.stringify({ x: rect.x + rect.width/2, y: rect.y + rect.height/2, disabled: btn.disabled });
      } else {
        null
      }
    `);
    console.log('[GDP] Create button:', createBtn);

    if (createBtn) {
      const data = JSON.parse(createBtn);
      console.log('[GDP] Create button disabled:', data.disabled);
      await click(data.x, data.y, 'Click Create');
      await sleep(2000);
      await screenshot('07_after_create');
    } else {
      console.log('[GDP] ERROR: Create button not found!');
      return;
    }

    // ==================== STEP 10: Verify Result ====================
    console.log('\n' + '='.repeat(60));
    console.log('STEP 10: Verify Result');
    console.log('='.repeat(60));

    const finalRowCount = await run(`document.querySelectorAll('.explorer-grid .row').length`);
    console.log('[GDP] Final row count:', finalRowCount);

    const folderVisible = await run(`document.body.innerText.includes('${folderName}')`);
    console.log('[GDP] Folder visible in UI:', folderVisible);

    const allRows = await run(`
      Array.from(document.querySelectorAll('.explorer-grid .row')).map(r => r.innerText.split('\\n')[0]).join(', ')
    `);
    console.log('[GDP] All rows:', allRows);

    await screenshot('08_final');

    // ==================== RESULT ====================
    console.log('\n' + '='.repeat(60));
    console.log('RESULT');
    console.log('='.repeat(60));
    console.log('Folder name:', folderName);
    console.log('Initial rows:', rowCount);
    console.log('Final rows:', finalRowCount);
    console.log('Folder visible:', folderVisible);
    console.log('SUCCESS:', folderVisible === true);
    console.log('='.repeat(60));

  } catch (err) {
    console.error('[GDP] FATAL ERROR:', err.message);
    console.error(err.stack);
  } finally {
    if (client) await client.close();
  }
}

gdpTest();
