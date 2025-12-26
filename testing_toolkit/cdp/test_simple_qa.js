const http = require('http');
const WebSocket = require('ws');

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

    console.log('=== QA PANEL TEST ===\n');

    // First, let's see all buttons
    console.log('1. Finding QA-related buttons...');
    const buttons = await eval_(`
        Array.from(document.querySelectorAll('button')).map(b => ({
            text: b.innerText.trim().substring(0, 30),
            ariaLabel: b.getAttribute('aria-label') || '',
            classes: b.className.substring(0, 50)
        })).filter(b => b.text.includes('QA') || b.ariaLabel.includes('QA'))
    `);
    console.log('   Found:', JSON.stringify(buttons, null, 2));

    // Click the QA menu button (the one that opens the side panel, not the toggle)
    console.log('\n2. Clicking QA menu button (sidebar)...');
    const clickResult = await eval_(`
        (async () => {
            // Look for menu items or sidebar buttons
            const items = document.querySelectorAll('.menu-item, .sidebar-item, [role="menuitem"], button');
            for (const item of items) {
                const text = item.innerText.trim();
                // Click the "QA" menu item that's just "QA" (not "QA Off")
                if (text === 'QA' && !item.innerText.includes('Off') && !item.innerText.includes('On')) {
                    item.click();
                    await new Promise(r => setTimeout(r, 1000));
                    return 'Clicked QA menu: ' + item.tagName;
                }
            }
            // Also look for sidebar navigation
            const sidebarLinks = document.querySelectorAll('nav a, .nav-link, .sidebar a');
            for (const link of sidebarLinks) {
                if (link.innerText.trim() === 'QA') {
                    link.click();
                    await new Promise(r => setTimeout(r, 1000));
                    return 'Clicked QA nav link';
                }
            }
            return 'No QA menu found';
        })()
    `);
    console.log('   Result:', clickResult);

    // Check if anything changed
    await new Promise(r => setTimeout(r, 500));
    const pageContent = await eval_('document.body.innerText.substring(0, 500)');
    console.log('\n3. Page content preview:\n', pageContent.substring(0, 300));

    // Check if panel opened
    const hasQAPanel = await eval_(`
        document.body.innerText.includes('Run Full QA') ||
        document.body.innerText.includes('QA Summary') ||
        document.body.innerText.includes('QA Issues') ||
        document.querySelector('.qa-menu-panel, .qa-panel, [class*="qa-menu"]') !== null
    `);
    console.log('\n4. QA Panel visible:', hasQAPanel);

    if (!hasQAPanel) {
        console.log('\n⚠️ QA Panel not visible - may need a file open first');
        console.log('   The QA panel only shows when viewing a file.');
    }

    ws.close();
    process.exit(hasQAPanel ? 0 : 1);
}
test().catch(e => { console.error(e); process.exit(1); });
