/**
 * CDP Test: Folder Creation in Offline Storage (Windows)
 */
const CDP = require('chrome-remote-interface');
const fs = require('fs');

const sleep = ms => new Promise(r => setTimeout(r, ms));

async function test() {
  let client;
  try {
    console.log('Connecting to CDP...');
    const targets = await CDP.List({ port: 9222 });
    const mainTarget = targets.find(t => t.type === 'page');
    if (!mainTarget) { console.log('No target'); return; }

    client = await CDP({ target: mainTarget });
    const { Page, Runtime, Input, DOM } = client;
    await Page.enable();
    await Runtime.enable();
    await DOM.enable();

    const screenshot = async (name) => {
      const { data } = await Page.captureScreenshot({ format: 'png' });
      fs.writeFileSync(`C:/Users/MYCOM/Pictures/${name}.png`, Buffer.from(data, 'base64'));
      console.log(`Screenshot: ${name}`);
    };

    const run = async (js) => {
      const r = await Runtime.evaluate({ expression: js, returnByValue: true });
      return r.result?.value;
    };

    const click = async (x, y, dbl = false) => {
      await Input.dispatchMouseEvent({ type: 'mousePressed', x, y, button: 'left', clickCount: dbl ? 2 : 1 });
      await Input.dispatchMouseEvent({ type: 'mouseReleased', x, y, button: 'left' });
    };

    const rightClick = async (x, y) => {
      await Input.dispatchMouseEvent({ type: 'mousePressed', x, y, button: 'right', clickCount: 1 });
      await Input.dispatchMouseEvent({ type: 'mouseReleased', x, y, button: 'right' });
    };

    await screenshot('bug043_01_start');
    console.log('Viewport:', await run(`JSON.stringify({ w: window.innerWidth, h: window.innerHeight })`));

    // Step 1: Click Login card
    console.log('Step 1: Click Login card...');
    await click(795, 540);
    await sleep(2000);
    await screenshot('bug043_02_login_form');

    // Step 2: Focus username and type using insertText
    console.log('Step 2: Fill username...');
    await run(`document.querySelector('input[placeholder="Enter username"]').focus()`);
    await sleep(100);
    await Input.insertText({ text: 'admin' });
    await sleep(300);

    // Step 3: Focus password and type
    console.log('Step 3: Fill password...');
    await run(`document.querySelector('input[placeholder="Enter password"]').focus()`);
    await sleep(100);
    await Input.insertText({ text: 'admin123' });
    await sleep(300);
    await screenshot('bug043_03_filled');

    // Check what's in the inputs
    const inputValues = await run(`JSON.stringify({
      user: document.querySelector('input[placeholder="Enter username"]').value,
      pass: document.querySelector('input[placeholder="Enter password"]').value
    })`);
    console.log('Input values:', inputValues);

    // Step 4: Click Login button (approximately at 770, 685 based on layout)
    console.log('Step 4: Submit login...');
    await click(770, 685);
    await sleep(4000);
    await screenshot('bug043_04_dashboard');

    // Check if logged in
    const pageText = await run(`document.body.innerText.substring(0, 300)`);
    console.log('After login:', pageText.substring(0, 150));

    if (pageText.includes('Files') && (pageText.includes('TM') || pageText.includes('Apps'))) {
      console.log('LOGIN SUCCESSFUL!');
    } else {
      console.log('LOGIN FAILED - checking what buttons exist');
      const buttons = await run(`Array.from(document.querySelectorAll('button')).map(b => b.textContent.trim()).join(', ')`);
      console.log('Buttons:', buttons);
      return;
    }

    // Step 5: Click Files nav
    console.log('Step 5: Navigate to Files...');
    await click(173, 24);  // Files nav position based on typical layout
    await sleep(2000);
    await screenshot('bug043_05_files');

    // Step 6: Double-click Offline Storage
    console.log('Step 6: Open Offline Storage...');
    const offlinePos = await run(`
      const items = Array.from(document.querySelectorAll('*'));
      const el = items.find(e => e.innerText === 'Offline Storage' && e.offsetParent);
      el ? JSON.stringify({ x: el.getBoundingClientRect().x + 50, y: el.getBoundingClientRect().y + 10 }) : null;
    `);
    console.log('Offline Storage:', offlinePos);
    if (offlinePos) {
      const pos = JSON.parse(offlinePos);
      await click(pos.x, pos.y, true);
    }
    await sleep(2000);
    await screenshot('bug043_06_offline');

    // Count items
    const beforeCount = await run(`document.querySelectorAll('.explorer-grid .row').length`);
    console.log('Items before:', beforeCount);

    // Step 7: Right-click for context menu
    console.log('Step 7: Context menu...');
    await rightClick(500, 350);
    await sleep(500);
    await screenshot('bug043_07_context');

    // Step 8: Click New Folder
    console.log('Step 8: Click New Folder...');
    const nfPos = await run(`
      const items = Array.from(document.querySelectorAll('*'));
      const el = items.find(e => e.innerText === 'New Folder' && e.offsetParent);
      el ? JSON.stringify({ x: el.getBoundingClientRect().x + 40, y: el.getBoundingClientRect().y + 10 }) : null;
    `);
    console.log('New Folder:', nfPos);
    if (nfPos) {
      const pos = JSON.parse(nfPos);
      await click(pos.x, pos.y);
    }
    await sleep(1000);
    await screenshot('bug043_08_dialog');

    // Step 9: Focus input and type folder name
    const folderName = `WinTest_${Date.now()}`;
    console.log('Step 9: Create folder:', folderName);
    const hasInput = await run(`!!document.querySelector('input[placeholder="Enter folder name"]')`);
    if (hasInput) {
      await run(`document.querySelector('input[placeholder="Enter folder name"]').focus()`);
      await sleep(100);
      await Input.insertText({ text: folderName });
    }
    await sleep(300);

    // Step 10: Click Create button
    console.log('Step 10: Click Create...');
    const createPos = await run(`
      const btns = Array.from(document.querySelectorAll('button'));
      const btn = btns.find(b => b.textContent.trim() === 'Create' && b.offsetParent);
      btn ? JSON.stringify({ x: btn.getBoundingClientRect().x + 40, y: btn.getBoundingClientRect().y + 15 }) : null;
    `);
    console.log('Create:', createPos);
    if (createPos) {
      const pos = JSON.parse(createPos);
      await click(pos.x, pos.y);
    }
    await sleep(2000);
    await screenshot('bug043_09_result');

    // Verify
    const afterCount = await run(`document.querySelectorAll('.explorer-grid .row').length`);
    const visible = await run(`document.body.innerText.includes('${folderName}')`);

    console.log('\n========== RESULT ==========');
    console.log('Items before:', beforeCount);
    console.log('Items after:', afterCount);
    console.log('Folder visible:', visible);
    console.log('============================');

  } catch (err) {
    console.error('Error:', err.message);
  } finally {
    if (client) await client.close();
  }
}

test();
