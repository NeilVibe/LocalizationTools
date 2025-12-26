const http = require('http');
const WebSocket = require('ws');

async function test() {
    const targets = await new Promise(r => http.get('http://127.0.0.1:9222/json', res => {
        let d=''; res.on('data',c=>d+=c); res.on('end',()=>r(JSON.parse(d)));
    }));
    const ws = new WebSocket(targets.find(t=>t.type==='page').webSocketDebuggerUrl);
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

    console.log('=== DEBUG GRID ===\n');

    // Get all class names containing 'row' or 'grid'
    const classes = await eval_(`
        Array.from(new Set(
            Array.from(document.querySelectorAll('*'))
                .map(el => el.className)
                .filter(c => typeof c === 'string' && (c.includes('row') || c.includes('grid') || c.includes('virtual')))
        )).slice(0, 20)
    `);
    console.log('Classes with row/grid/virtual:', JSON.stringify(classes, null, 2));

    // Count elements
    const counts = await eval_(`({
        total: document.querySelectorAll('*').length,
        divs: document.querySelectorAll('div').length,
        rowClasses: document.querySelectorAll('[class*="row"]').length,
        gridClasses: document.querySelectorAll('[class*="grid"]').length,
        virtualClasses: document.querySelectorAll('[class*="virtual"]').length,
        scrollContainer: document.querySelector('.scroll-container') ? 'found' : 'not found',
        virtualGrid: document.querySelector('.virtual-grid') ? 'found' : 'not found'
    })`);
    console.log('\nElement counts:', JSON.stringify(counts, null, 2));

    // Sample of grid content
    const sample = await eval_(`
        document.body.innerText.substring(0, 800)
    `);
    console.log('\nPage content sample:', sample);

    ws.close();
}
test().catch(e => { console.error(e); process.exit(1); });
