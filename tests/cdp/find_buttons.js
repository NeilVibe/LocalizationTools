const WebSocket = require('ws');
const http = require('http');

http.get('http://localhost:9222/json', (res) => {
    let data = '';
    res.on('data', chunk => data += chunk);
    res.on('end', () => {
        const targets = JSON.parse(data);
        const page = targets.find(t => t.type === 'page');
        const ws = new WebSocket(page.webSocketDebuggerUrl);
        let id = 1;

        ws.on('open', async () => {
            console.log('Finding all buttons and clickable elements...\n');

            const result = await send(ws, id++, 'Runtime.evaluate', {
                expression: `
                    (function() {
                        // Get all buttons
                        const buttons = document.querySelectorAll('button');
                        const buttonInfo = [];
                        buttons.forEach((btn, i) => {
                            const title = btn.getAttribute('title') || '';
                            const label = btn.getAttribute('aria-label') || '';
                            const text = btn.innerText.trim().substring(0, 30);
                            const className = btn.className.substring(0, 50);
                            const hasIcon = btn.querySelector('svg') !== null;
                            buttonInfo.push({
                                index: i,
                                title,
                                label,
                                text,
                                className,
                                hasIcon
                            });
                        });

                        // Check SVG elements
                        const svgs = document.querySelectorAll('svg');
                        const svgParents = [];
                        svgs.forEach((svg, i) => {
                            const parent = svg.parentElement;
                            if (parent) {
                                const pTitle = parent.getAttribute('title') || '';
                                const pLabel = parent.getAttribute('aria-label') || '';
                                if (pTitle || pLabel) {
                                    svgParents.push({ index: i, parentTag: parent.tagName, title: pTitle, label: pLabel });
                                }
                            }
                        });

                        // Check grid for clickable areas
                        const gridCells = document.querySelectorAll('.virtual-grid [class*="cell"]');
                        const cellInfo = [];
                        gridCells.forEach((cell, i) => {
                            if (i < 5) { // First 5 cells
                                cellInfo.push({
                                    index: i,
                                    className: cell.className,
                                    hasButton: cell.querySelector('button') !== null,
                                    text: cell.innerText.substring(0, 50)
                                });
                            }
                        });

                        return JSON.stringify({
                            buttonCount: buttons.length,
                            buttons: buttonInfo,
                            svgParentsWithLabels: svgParents,
                            gridCells: cellInfo
                        }, null, 2);
                    })()
                `,
                returnByValue: true
            });
            console.log(result.result?.result?.value);

            ws.close();
            process.exit(0);
        });

        function send(ws, id, method, params) {
            return new Promise(resolve => {
                const handler = (data) => {
                    const msg = JSON.parse(data);
                    if (msg.id === id) {
                        ws.removeListener('message', handler);
                        resolve(msg);
                    }
                };
                ws.on('message', handler);
                ws.send(JSON.stringify({ id, method, params }));
            });
        }
    });
}).on('error', err => {
    console.log('HTTP Error:', err.message);
    process.exit(1);
});
