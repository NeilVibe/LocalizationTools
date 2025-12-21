/**
 * Build 312 - UI-045 Tooltip Verification
 * Verifies that the "X viewing" tooltip shows username instead of "?"
 */
const WebSocket = require('ws');
const http = require('http');
const fs = require('fs');

const sleep = ms => new Promise(r => setTimeout(r, ms));

async function main() {
    console.log('=== BUILD 312 TOOLTIP VERIFICATION ===\n');

    // Get CDP targets
    const targets = await new Promise((resolve, reject) => {
        http.get('http://127.0.0.1:9222/json', (res) => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => resolve(JSON.parse(data)));
        }).on('error', reject);
    });

    const page = targets.find(t => t.type === 'page');
    if (!page) {
        console.log('No page found');
        return;
    }

    const ws = new WebSocket(page.webSocketDebuggerUrl);
    let id = 1;

    const send = (method, params = {}) => new Promise((resolve) => {
        const msgId = id++;
        ws.on('message', function handler(data) {
            const msg = JSON.parse(data.toString());
            if (msg.id === msgId) {
                ws.off('message', handler);
                resolve(msg);
            }
        });
        ws.send(JSON.stringify({ id: msgId, method, params }));
    });

    const evaluate = async (expression) => {
        const result = await send('Runtime.evaluate', {
            expression,
            returnByValue: true,
            awaitPromise: true
        });
        return result.result?.result?.value;
    };

    const screenshot = async (filename) => {
        const result = await send('Page.captureScreenshot', { format: 'png' });
        const buffer = Buffer.from(result.result.data, 'base64');
        fs.writeFileSync(filename, buffer);
        console.log('Screenshot saved:', filename);
    };

    await new Promise(resolve => ws.on('open', resolve));

    // Screenshot 1: Initial state
    console.log('1. Taking initial screenshot...');
    await screenshot('C:\\Users\\MYCOM\\AppData\\Local\\Temp\\build312_step1.png');

    // Check current page state
    const pageContent = await evaluate('document.body.innerText.substring(0, 300)');
    console.log('Current page:', pageContent.substring(0, 100) + '...\n');

    // Step 2: Click on a project to expand it
    console.log('2. Clicking on a project...');
    const projectClicked = await evaluate(`
        const projectItems = document.querySelectorAll('.project-item, [class*="project"]');
        let clicked = false;
        for (const item of projectItems) {
            if (item.textContent.includes('Excel Test Project')) {
                item.click();
                clicked = true;
                break;
            }
        }
        clicked;
    `);
    console.log('Project clicked:', projectClicked);
    await sleep(1500);

    // Screenshot 2: After project expansion
    await screenshot('C:\\Users\\MYCOM\\AppData\\Local\\Temp\\build312_step2.png');

    // Step 3: Click on a file to open it
    console.log('\n3. Clicking on a file...');
    const fileClicked = await evaluate(`
        const treeNodes = document.querySelectorAll('.tree-node, [class*="file"], [data-type="file"]');
        let clicked = false;
        for (const node of treeNodes) {
            const text = node.textContent || node.innerText;
            if (text && (text.includes('.xlsx') || text.includes('.txt') || text.includes('.xlsm'))) {
                node.click();
                clicked = true;
                break;
            }
        }
        clicked;
    `);
    console.log('File clicked:', fileClicked);
    await sleep(2000);

    // Screenshot 3: File viewer should be visible
    await screenshot('C:\\Users\\MYCOM\\AppData\\Local\\Temp\\build312_step3.png');

    // Step 4: Check for PresenceBar and tooltip
    console.log('\n4. Checking PresenceBar...');
    const presenceInfo = await evaluate(`
        const presenceBar = document.querySelector('.presence-bar, .presence-indicator, [class*="presence"]');
        if (!presenceBar) return JSON.stringify({ found: false });

        const title = presenceBar.getAttribute('title') || presenceBar.querySelector('[title]')?.getAttribute('title') || 'no title';
        const text = presenceBar.textContent || presenceBar.innerText;

        return JSON.stringify({
            found: true,
            title: title,
            text: text,
            outerHTML: presenceBar.outerHTML.substring(0, 500)
        });
    `);

    const presence = JSON.parse(presenceInfo);
    console.log('PresenceBar found:', presence.found);
    if (presence.found) {
        console.log('Title (tooltip):', presence.title);
        console.log('Text:', presence.text);
        console.log('\n=== VERIFICATION ===');

        // Check if tooltip shows username
        const tooltipValue = presence.title;
        if (tooltipValue && !tooltipValue.includes('?') && !tooltipValue.includes('undefined') && !tooltipValue.includes('Unknown')) {
            if (tooltipValue.includes('neil') || tooltipValue === 'You') {
                console.log('PASS: Tooltip shows valid username:', tooltipValue);
            } else {
                console.log('CHECK: Tooltip value:', tooltipValue);
            }
        } else {
            console.log('FAIL: Tooltip still shows invalid value:', tooltipValue);
        }
    } else {
        console.log('PresenceBar not found - may need to open a file first');
    }

    // Screenshot 4: Final state
    console.log('\n5. Taking final verification screenshot...');
    await screenshot('C:\\Users\\MYCOM\\AppData\\Local\\Temp\\build312_step4.png');

    // Get DOM info about viewing status
    const viewingInfo = await evaluate(`
        const elements = document.querySelectorAll('[title]');
        const results = [];
        for (const el of elements) {
            const title = el.getAttribute('title');
            if (title && (title.includes('viewing') || title.includes('neil') || title.includes('?'))) {
                results.push({ title, class: el.className, text: el.textContent.trim().substring(0, 50) });
            }
        }
        JSON.stringify(results);
    `);
    console.log('\nElements with viewing-related titles:', viewingInfo);

    ws.close();
    console.log('\n=== VERIFICATION COMPLETE ===');
    console.log('Screenshots saved in C:\\Users\\MYCOM\\AppData\\Local\\Temp\\');
}

main().catch(console.error);
