const WebSocket = require('ws');
async function main() {
    const pages = await fetch('http://localhost:9222/json').then(r => r.json());
    const ws = new WebSocket(pages[0].webSocketDebuggerUrl);
    let msgId = 1;
    function send(method, params = {}) {
        return new Promise((resolve) => {
            const id = msgId++;
            const timeout = setTimeout(() => resolve({ error: 'timeout' }), 30000);
            ws.on('message', function handler(data) {
                const msg = JSON.parse(data.toString());
                if (msg.id === id) { 
                    clearTimeout(timeout);
                    ws.off('message', handler); 
                    resolve(msg.result); 
                }
            });
            ws.send(JSON.stringify({ id, method, params }));
        });
    }
    ws.on('open', async () => {
        console.log('Connected to CDP');
        
        // Navigate to LDM by clicking the menu
        console.log('Navigating to LDM...');
        const navResult = await send('Runtime.evaluate', {
            expression: `
                // Find and click the LDM option in the app menu
                const ldmLink = document.querySelector('a[href*="ldm"]') || 
                               Array.from(document.querySelectorAll('a, button')).find(el => 
                                   el.textContent.toLowerCase().includes('ldm') || 
                                   el.textContent.toLowerCase().includes('language data')
                               );
                if (ldmLink) {
                    ldmLink.click();
                    'clicked LDM link';
                } else {
                    // Try setting app directly via store if available
                    if (window.navigateToApp) {
                        window.navigateToApp('ldm');
                        'called navigateToApp';
                    } else {
                        'LDM link not found';
                    }
                }
            `,
            returnByValue: true
        });
        console.log('Navigation result:', navResult.result?.value);
        
        // Wait for LDM to mount
        console.log('Waiting 3 seconds for LDM to mount...');
        await new Promise(r => setTimeout(r, 3000));
        
        // Check if ldmTest is now available
        const check = await send('Runtime.evaluate', {
            expression: `JSON.stringify({
                ldmTest: typeof window.ldmTest !== 'undefined',
                ldmTestMethods: window.ldmTest ? Object.keys(window.ldmTest) : []
            })`,
            returnByValue: true
        });
        console.log('LDM Test Interface:', check.result?.value);
        
        ws.close();
        process.exit(0);
    });
}
main();
