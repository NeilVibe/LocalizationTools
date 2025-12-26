const http = require('http');
const WebSocket = require('ws');

const sleep = ms => new Promise(r => setTimeout(r, ms));

async function test() {
    const targets = await new Promise(r => http.get('http://127.0.0.1:9222/json', res => {
        let d=''; res.on('data',c=>d+=c); res.on('end',()=>r(JSON.parse(d)));
    }));
    const ws = new WebSocket(targets.find(t=>t.url.includes('index.html')).webSocketDebuggerUrl);
    let id=1;
    const send = (m,p={}) => new Promise(r=>{
        const i=id++; ws.on('message',function h(d){const msg=JSON.parse(d);if(msg.id===i){ws.off('message',h);r(msg.result);}});
        ws.send(JSON.stringify({id:i,method:m,params:p}));
    });
    const eval_ = async (expr) => {
        const r = await send('Runtime.evaluate', {expression:expr, returnByValue:true, awaitPromise:true});
        return r.result?.value;
    };
    await new Promise(r=>ws.on('open',r));
    await send('Runtime.enable');

    console.log('=== FULL QA PANEL TEST ===\n');

    // Step 1: Click on file
    console.log('STEP 1: Click on test_10k.txt file...');
    const clickFile = await eval_(`
        (async () => {
            // Find and click on file item
            const items = document.querySelectorAll('button, div, span, li');
            for (const item of items) {
                const text = item.innerText?.trim();
                if (text === 'test_10k.txt') {
                    item.click();
                    await new Promise(r => setTimeout(r, 2000));
                    return 'Clicked: ' + item.tagName;
                }
            }
            return 'File not found';
        })()
    `);
    console.log('   Result:', clickFile);
    await sleep(2000);

    // Check if file loaded (grid visible)
    const fileLoaded = await eval_(`
        document.body.innerText.includes('Source') ||
        document.querySelectorAll('[class*="row"]').length > 10
    `);
    console.log('   File loaded:', fileLoaded);

    if (!fileLoaded) {
        console.log('\n⚠️ File not loaded, trying again...');
        // Try using ldmTest interface
        await eval_(`
            if (window.ldmTest) {
                window.ldmTest.selectFile && window.ldmTest.selectFile('test_10k.txt');
            }
        `);
        await sleep(2000);
    }

    // Step 2: Click QA menu button
    console.log('\nSTEP 2: Open QA Panel...');
    const openQA = await eval_(`
        (async () => {
            // Find the QA button (not toggle, not project)
            const buttons = document.querySelectorAll('button');
            for (const btn of buttons) {
                const text = btn.innerText.trim();
                if (text === 'QA' && btn.className.includes('ghost')) {
                    btn.click();
                    await new Promise(r => setTimeout(r, 1000));
                    return 'Clicked QA menu button';
                }
            }
            return 'QA button not found';
        })()
    `);
    console.log('   Result:', openQA);
    await sleep(1000);

    // Check if panel opened
    const panelOpen = await eval_(`
        document.body.innerText.includes('Run Full QA') ||
        document.body.innerText.includes('QA Summary')
    `);
    console.log('   Panel opened:', panelOpen);

    if (!panelOpen) {
        console.log('\n⚠️ QA Panel did not open. Checking page state...');
        const pageText = await eval_('document.body.innerText.substring(0, 400)');
        console.log('   Page:', pageText.substring(0, 200));
        ws.close();
        process.exit(1);
    }

    // Step 3: Click X to close
    console.log('\nSTEP 3: Click X button to close panel...');
    const closeResult = await eval_(`
        (async () => {
            // Find close button
            const closeBtn = document.querySelector('button[aria-label*="Close"]') ||
                            document.querySelector('button[aria-label*="close"]') ||
                            document.querySelector('.close-button');
            if (closeBtn) {
                closeBtn.click();
                await new Promise(r => setTimeout(r, 500));
                return 'Clicked close button';
            }
            return 'Close button not found';
        })()
    `);
    console.log('   Result:', closeResult);
    await sleep(500);

    // Step 4: Verify panel closed
    const panelClosed = await eval_('!document.body.innerText.includes("Run Full QA")');
    console.log('   Panel closed:', panelClosed);

    // Results
    console.log('\n=== RESULTS ===');
    console.log('PERF-003 (Lazy loading):', fileLoaded ? '✅ PASS (file loaded)' : '⚠️ NEEDS VERIFY');
    console.log('BUG-037 (QA X button):', panelClosed ? '✅ PASS' : '❌ FAIL');

    ws.close();
    process.exit(panelClosed ? 0 : 1);
}
test().catch(e => { console.error(e); process.exit(1); });
