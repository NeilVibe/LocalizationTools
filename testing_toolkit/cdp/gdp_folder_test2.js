/**
 * GDP Test v2: PROPER folder creation - must ENTER Offline Storage first
 */
const CDP = require('chrome-remote-interface');
const fs = require('fs');

const sleep = ms => new Promise(r => setTimeout(r, ms));

async function test() {
  console.log('='.repeat(60));
  console.log('GDP TEST v2: Folder Creation (Enter Offline Storage First)');
  console.log('='.repeat(60));

  const client = await CDP({ port: 9222 });
  const { Page, Runtime, Input } = client;
  await Page.enable();
  await Runtime.enable();

  const screenshot = async (name) => {
    const { data } = await Page.captureScreenshot({ format: 'png' });
    fs.writeFileSync(`C:/Users/MYCOM/Pictures/gdp2_${name}.png`, Buffer.from(data, 'base64'));
    console.log('[SS]', name);
  };

  const run = async (js) => (await Runtime.evaluate({ expression: js, returnByValue: true })).result?.value;

  try {
    await screenshot('01_start');

    // STEP 1: Find and double-click Offline Storage row
    console.log('\n[STEP 1] Double-click Offline Storage to ENTER it');

    const offlineRect = await run(`
      const rows = document.querySelectorAll('.explorer-grid .row');
      for (const row of rows) {
        if (row.innerText.includes('Offline Storage')) {
          const rect = row.getBoundingClientRect();
          return JSON.stringify({ x: rect.x + 100, y: rect.y + 20 });
        }
      }
      return null;
    `);

    console.log('Offline Storage rect:', offlineRect);

    if (offlineRect) {
      const pos = JSON.parse(offlineRect);
      // Double-click
      await Input.dispatchMouseEvent({ type: 'mousePressed', x: pos.x, y: pos.y, button: 'left', clickCount: 2 });
      await Input.dispatchMouseEvent({ type: 'mouseReleased', x: pos.x, y: pos.y, button: 'left' });
      console.log('Double-clicked at', pos.x, pos.y);
    } else {
      console.log('ERROR: Offline Storage row not found!');
      return;
    }

    await sleep(2000);
    await screenshot('02_inside_offline');

    // STEP 2: Verify we're inside
    console.log('\n[STEP 2] Verify inside Offline Storage');
    const breadcrumb = await run(`
      const bc = document.querySelector('.breadcrumb');
      return bc ? bc.innerText : 'NO BREADCRUMB';
    `);
    console.log('Breadcrumb:', breadcrumb);

    if (!breadcrumb.includes('Offline Storage')) {
      console.log('ERROR: Not inside Offline Storage!');
      console.log('Page text:', await run(`document.body.innerText.substring(0, 300)`));
      return;
    }
    console.log('SUCCESS: Inside Offline Storage');

    // STEP 3: Count items
    const beforeCount = await run(`document.querySelectorAll('.explorer-grid .row').length`);
    console.log('\n[STEP 3] Items before:', beforeCount);

    // STEP 4: Right-click
    console.log('\n[STEP 4] Right-click for context menu');
    await Input.dispatchMouseEvent({ type: 'mousePressed', x: 600, y: 400, button: 'right', clickCount: 1 });
    await Input.dispatchMouseEvent({ type: 'mouseReleased', x: 600, y: 400, button: 'right' });
    await sleep(500);
    await screenshot('03_context_menu');

    // STEP 5: Check menu items
    console.log('\n[STEP 5] Context menu items:');
    const menuText = await run(`
      const items = Array.from(document.querySelectorAll('.context-menu-item'));
      return items.map(i => i.innerText.trim()).filter(t => t).join(' | ');
    `);
    console.log('Menu:', menuText);

    // STEP 6: Click New Folder
    console.log('\n[STEP 6] Click New Folder');
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

    if (nfRect) {
      const pos = JSON.parse(nfRect);
      await Input.dispatchMouseEvent({ type: 'mousePressed', x: pos.x, y: pos.y, button: 'left', clickCount: 1 });
      await Input.dispatchMouseEvent({ type: 'mouseReleased', x: pos.x, y: pos.y, button: 'left' });
    } else {
      console.log('ERROR: New Folder not in menu!');
      return;
    }

    await sleep(1000);
    await screenshot('04_modal');

    // STEP 7: Check modal
    console.log('\n[STEP 7] Check modal');
    const hasInput = await run(`!!document.querySelector('input[placeholder="Enter folder name"]')`);
    console.log('Folder input visible:', hasInput);

    if (!hasInput) {
      console.log('ERROR: Modal not open!');
      return;
    }

    // STEP 8: Type folder name
    const folderName = 'GDP2_' + Date.now();
    console.log('\n[STEP 8] Typing folder name:', folderName);
    await run(`document.querySelector('input[placeholder="Enter folder name"]').focus()`);
    await sleep(100);
    await Input.insertText({ text: folderName });
    await sleep(300);

    const typed = await run(`document.querySelector('input[placeholder="Enter folder name"]').value`);
    console.log('Typed value:', typed);
    await screenshot('05_name_typed');

    // STEP 9: Click Create
    console.log('\n[STEP 9] Click Create');
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
      const pos = JSON.parse(createRect);
      await Input.dispatchMouseEvent({ type: 'mousePressed', x: pos.x, y: pos.y, button: 'left', clickCount: 1 });
      await Input.dispatchMouseEvent({ type: 'mouseReleased', x: pos.x, y: pos.y, button: 'left' });
    }

    await sleep(2000);
    await screenshot('06_result');

    // STEP 10: Verify
    console.log('\n[STEP 10] RESULT');
    const afterCount = await run(`document.querySelectorAll('.explorer-grid .row').length`);
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
