const WebSocket = require('ws');
async function main() {
    const pages = await fetch('http://localhost:9222/json').then(r => r.json());
    const ws = new WebSocket(pages[0].webSocketDebuggerUrl);
    let msgId = 1;
    function send(method, params = {}) {
        return new Promise((resolve) => {
            const id = msgId++;
            ws.on('message', function handler(data) {
                const msg = JSON.parse(data.toString());
                if (msg.id === id) { ws.off('message', handler); resolve(msg.result); }
            });
            ws.send(JSON.stringify({ id, method, params }));
        });
    }
    ws.on('open', async () => {
        const check = await send('Runtime.evaluate', {
            expression: `JSON.stringify({
                xlsTransferTest: typeof window.xlsTransferTest !== 'undefined',
                quickSearchTest: typeof window.quickSearchTest !== 'undefined',
                krSimilarTest: typeof window.krSimilarTest !== 'undefined',
                ldmTest: typeof window.ldmTest !== 'undefined'
            })`,
            returnByValue: true
        });
        console.log('Available test interfaces:', check.result.value);
        ws.close();
        process.exit(0);
    });
}
main();
