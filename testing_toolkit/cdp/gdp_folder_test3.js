/**
 * GDP Test v3: CORRECT selectors - .grid-row not .row
 */
const CDP = require('chrome-remote-interface');
const fs = require('fs');

const sleep = ms => new Promise(r => setTimeout(r, ms));

async function test() {
  console.log('='.repeat(60));
  console.log('GDP TEST v3: Folder Creation (Correct Selectors)');
  console.log('='.repeat(60));

  const client = await CDP({ port: 9222 });
  const { Page, Runtime, Input } = client;
  await Page.enable();
  await Runtime.enable();

  const screenshot = async (name) => {
    const { data } = await Page.captureScreenshot({ format: 'png' });
    fs.writeFileSync(`C:/Users/MYCOM/Pictures/gdp3_${name}.png`, Buffer.from(data, 'base64'));
    console.log('[SS]', name);
  };

  const run = async (js) => (await Runtime.evaluate({ expression: js, returnByValue: true })).result?.value;

  try {
    await screenshot('01_start');

    // STEP 1: Check current state
    console.log('\n[STEP 1] Check current state');
    const breadcrumb = await run(`document.querySelector('.breadcrumb')?.innerText || 'NO BREADCRUMB'`);
    console.log('Breadcrumb:', breadcrumb);

    // DEBUG: Check both selectors
    const oldSelector = await run(`document.querySelectorAll('.explorer-grid .row').length`);
    const newSelector = await run(`document.querySelectorAll('.explorer-grid .grid-row').length`);
    console.log('.row count:', oldSelector);
    console.log('.grid-row count:', newSelector);

    // Get all row names
    const rowNames = await run(`
      Array.from(document.querySelectorAll('.explorer-grid .grid-row .item-name'))
        .map(el => el.textContent.trim())
        .join(', ')
    `);
    console.log('Rows:', rowNames);

    // STEP 2: Find and double-click Offline Storage
    console.log('\n[STEP 2] Find Offline Storage');
    const offlineRect = await run(`
      const rows = document.querySelectorAll('.explorer-grid .grid-row');
      for (const row of rows) {
        const name = row.querySelector('.item-name')?.textContent;
        if (name && name.includes('Offline Storage')) {
          const rect = row.getBoundingClientRect();
          return JSON.stringify({ x: rect.x + 100, y: rect.y + rect.height/2 });
        }
      }
      return null;
    `);
    console.log('Offline Storage rect:', offlineRect);

    if (!offlineRect) {
      console.log('ERROR: Offline Storage not found!');
      console.log('Available rows:', rowNames);
      return;
    }

    const pos = JSON.parse(offlineRect);
    console.log('Double-clicking at', pos.x, pos.y);

    // Double-click
    await Input.dispatchMouseEvent({ type: 'mousePressed', x: pos.x, y: pos.y, button: 'left', clickCount: 2 });
    await Input.dispatchMouseEvent({ type: 'mouseReleased', x: pos.x, y: pos.y, button: 'left' });

    await sleep(2000);
    await screenshot('02_inside_offline');

    // STEP 3: Verify inside Offline Storage
    console.log('\n[STEP 3] Verify inside Offline Storage');
    const bc2 = await run(`document.querySelector('.breadcrumb')?.innerText || 'NO BREADCRUMB'`);
    console.log('Breadcrumb now:', bc2);

    if (!bc2.includes('Offline Storage')) {
      console.log('ERROR: Did not enter Offline Storage!');
      console.log('Page text:', await run(`document.body.innerText.substring(0, 300)`));
      return;
    }
    console.log('SUCCESS: Inside Offline Storage');

    // STEP 4: Count items before
    const beforeCount = await run(`document.querySelectorAll('.explorer-grid .grid-row').length`);
    const isEmpty = await run(`document.body.innerText.includes('This folder is empty')`);
    console.log('\n[STEP 4] State inside:');
    console.log('Items before:', beforeCount);
    console.log('Shows empty:', isEmpty);

    // STEP 5: Right-click for context menu
    console.log('\n[STEP 5] Right-click for context menu');

    // Get grid position for right-click
    const gridRect = await run(`
      const grid = document.querySelector('.explorer-grid');
      if (grid) {
        const rect = grid.getBoundingClientRect();
        return JSON.stringify({ x: rect.x + 200, y: rect.y + 150 });
      }
      return null;
    `);
    console.log('Grid rect:', gridRect);

    if (gridRect) {
      const gpos = JSON.parse(gridRect);
      await Input.dispatchMouseEvent({ type: 'mousePressed', x: gpos.x, y: gpos.y, button: 'right', clickCount: 1 });
      await Input.dispatchMouseEvent({ type: 'mouseReleased', x: gpos.x, y: gpos.y, button: 'right' });
    }

    await sleep(500);
    await screenshot('03_context_menu');

    // STEP 6: Check context menu
    console.log('\n[STEP 6] Context menu items');
    const menuItems = await run(`
      const items = Array.from(document.querySelectorAll('.context-menu-item'));
      return items.map(i => i.innerText.trim()).filter(t => t).join(' | ');
    `);
    console.log('Menu:', menuItems);

    // STEP 7: Click New Folder
    console.log('\n[STEP 7] Click New Folder');
    const nfRect = await run(`
      const items = document.querySelectorAll('.context-menu-item');
      for (const item of items) {
        if (item.innerText.includes('New Folder')) {
          const rect = item.getBoundingClientRect();
          return JSON.stringify({ x: rect.x + 40, y: rect.y + 12 });
        }
      }
      return null;
    `);
    console.log('New Folder rect:', nfRect);

    if (!nfRect) {
      console.log('ERROR: New Folder not in menu!');
      return;
    }

    const nfpos = JSON.parse(nfRect);
    await Input.dispatchMouseEvent({ type: 'mousePressed', x: nfpos.x, y: nfpos.y, button: 'left', clickCount: 1 });
    await Input.dispatchMouseEvent({ type: 'mouseReleased', x: nfpos.x, y: nfpos.y, button: 'left' });

    await sleep(1000);
    await screenshot('04_modal');

    // STEP 8: Check modal
    console.log('\n[STEP 8] Check modal');
    const hasInput = await run(`!!document.querySelector('input[placeholder="Enter folder name"]')`);
    console.log('Folder input visible:', hasInput);

    if (!hasInput) {
      console.log('ERROR: Modal not open!');
      // Debug what's visible
      const visible = await run(`Array.from(document.querySelectorAll('input')).map(i => i.placeholder).join(', ')`);
      console.log('Visible inputs:', visible);
      return;
    }

    // STEP 9: Type folder name
    const folderName = 'GDP3_' + Date.now();
    console.log('\n[STEP 9] Type folder name:', folderName);
    await run(`document.querySelector('input[placeholder="Enter folder name"]').focus()`);
    await sleep(100);
    await Input.insertText({ text: folderName });
    await sleep(300);

    const typed = await run(`document.querySelector('input[placeholder="Enter folder name"]').value`);
    console.log('Typed value:', typed);
    await screenshot('05_name_typed');

    // STEP 10: Click Create
    console.log('\n[STEP 10] Click Create');
    const createRect = await run(`
      const btns = document.querySelectorAll('button');
      for (const btn of btns) {
        if (btn.innerText.trim() === 'Create' && btn.offsetParent) {
          const rect = btn.getBoundingClientRect();
          return JSON.stringify({ x: rect.x + 40, y: rect.y + 15 });
        }
      }
      return null;
    `);
    console.log('Create button rect:', createRect);

    if (createRect) {
      const cpos = JSON.parse(createRect);
      await Input.dispatchMouseEvent({ type: 'mousePressed', x: cpos.x, y: cpos.y, button: 'left', clickCount: 1 });
      await Input.dispatchMouseEvent({ type: 'mouseReleased', x: cpos.x, y: cpos.y, button: 'left' });
    }

    await sleep(2000);
    await screenshot('06_result');

    // STEP 11: Verify
    console.log('\n[STEP 11] RESULT');
    const afterCount = await run(`document.querySelectorAll('.explorer-grid .grid-row').length`);
    const visible = await run(`document.body.innerText.includes('${folderName}')`);

    console.log('Items before:', beforeCount);
    console.log('Items after:', afterCount);
    console.log('Folder visible:', visible);
    console.log('='.repeat(60));
    console.log(visible ? 'SUCCESS!' : 'FAILED!');
    console.log('='.repeat(60));

  } finally {
    await client.close();
  }
}

test().catch(e => console.error('Error:', e));
