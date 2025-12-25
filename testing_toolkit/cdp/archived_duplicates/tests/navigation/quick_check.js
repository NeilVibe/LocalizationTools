/**
 * Quick CDP page state check
 */
const WebSocket = require('ws');
const http = require('http');

http.get('http://127.0.0.1:9222/json', (res) => {
    let data = '';
    res.on('data', chunk => data += chunk);
    res.on('end', () => {
        const targets = JSON.parse(data);
        const page = targets.find(t => t.type === 'page');
        if (!page) {
            console.log('No page found');
            process.exit(1);
        }

        console.log('=== CDP TARGET ===');
        console.log('Title:', page.title);
        console.log('URL:', page.url);

        const ws = new WebSocket(page.webSocketDebuggerUrl);
        ws.on('open', () => {
            ws.send(JSON.stringify({
                id: 1,
                method: 'Runtime.evaluate',
                params: {
                    expression: `JSON.stringify({
                        url: window.location.href,
                        title: document.title,
                        hash: window.location.hash,
                        pageDebug: typeof window.pageDebug !== 'undefined',
                        navTest: typeof window.navTest !== 'undefined',
                        ldmTest: typeof window.ldmTest !== 'undefined',
                        xlsTransferTest: typeof window.xlsTransferTest !== 'undefined',
                        quickSearchTest: typeof window.quickSearchTest !== 'undefined',
                        krSimilarTest: typeof window.krSimilarTest !== 'undefined',
                        bodyPreview: document.body ? document.body.innerText.substring(0, 800) : 'no body'
                    })`,
                    returnByValue: true
                }
            }));
        });
        ws.on('message', (msg) => {
            const result = JSON.parse(msg);
            if (result.id === 1) {
                console.log('\n=== PAGE STATE ===');
                const val = result.result?.result?.value;
                if (val) {
                    const state = JSON.parse(val);
                    console.log('URL:', state.url);
                    console.log('Title:', state.title);
                    console.log('Hash:', state.hash || '(none)');
                    console.log('\n=== TEST INTERFACES ===');
                    console.log('pageDebug:', state.pageDebug);
                    console.log('navTest:', state.navTest);
                    console.log('ldmTest:', state.ldmTest);
                    console.log('xlsTransferTest:', state.xlsTransferTest);
                    console.log('quickSearchTest:', state.quickSearchTest);
                    console.log('krSimilarTest:', state.krSimilarTest);
                    console.log('\n=== BODY PREVIEW ===');
                    console.log(state.bodyPreview);
                } else {
                    console.log('Error:', result.result?.exceptionDetails?.text || 'Unknown');
                }
                ws.close();
                process.exit(0);
            }
        });
        ws.on('error', (err) => {
            console.log('WebSocket error:', err.message);
            process.exit(1);
        });
    });
}).on('error', err => {
    console.log('HTTP Error:', err.message);
    process.exit(1);
});
