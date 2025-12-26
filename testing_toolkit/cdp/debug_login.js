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

    console.log('=== DEBUG LOGIN ===\n');

    // Check page URL and title
    const pageInfo = await eval_(`({
        url: location.href,
        title: document.title,
        bodyText: document.body.innerText.substring(0, 500)
    })`);
    console.log('URL:', pageInfo.url);
    console.log('Title:', pageInfo.title);
    console.log('Body:', pageInfo.bodyText.substring(0, 200));

    // Check all inputs
    const allInputs = await eval_(`Array.from(document.querySelectorAll('input')).map(i => ({
        type: i.type, name: i.name, id: i.id, placeholder: i.placeholder
    }))`);
    console.log('\nAll inputs:', JSON.stringify(allInputs, null, 2));

    // Check if login form exists
    const loginForm = await eval_(`({
        usernameInput: !!document.querySelector('input[type="text"], input[name="username"]'),
        passwordInput: !!document.querySelector('input[type="password"]'),
        loginButton: !!document.querySelector('button[type="submit"], button'),
        buttons: Array.from(document.querySelectorAll('button')).map(b => b.innerText.trim()).slice(0, 5)
    })`);
    console.log('\nLogin form:', loginForm);

    // Try to fill and submit
    const user = process.env.CDP_TEST_USER || 'neil';
    const pass = process.env.CDP_TEST_PASS || 'test123';
    console.log('\nLogging in as:', user);

    const fillResult = await eval_(`
        (async () => {
            // Find inputs - get all inputs and use first non-password as username
            const allInputs = document.querySelectorAll('input');
            let userInput = null;
            let passInput = null;
            for (const inp of allInputs) {
                if (inp.type === 'password') passInput = inp;
                else if (!userInput && (inp.type === 'text' || inp.type === '' || !inp.type)) userInput = inp;
            }

            if (!userInput) return { error: 'Username input not found' };
            if (!passInput) return { error: 'Password input not found' };

            // Clear and fill
            userInput.value = '';
            userInput.focus();
            userInput.value = '${user}';
            userInput.dispatchEvent(new Event('input', { bubbles: true }));

            passInput.value = '';
            passInput.focus();
            passInput.value = '${pass}';
            passInput.dispatchEvent(new Event('input', { bubbles: true }));

            // Find and click login button
            const loginBtn = document.querySelector('button[type="submit"]') ||
                            Array.from(document.querySelectorAll('button')).find(b =>
                                b.innerText.toLowerCase().includes('login') ||
                                b.innerText.toLowerCase().includes('sign in')
                            );

            if (!loginBtn) return { error: 'Login button not found' };

            loginBtn.click();
            await new Promise(r => setTimeout(r, 3000));

            return {
                success: true,
                pageAfter: document.body.innerText.substring(0, 300)
            };
        })()
    `);
    console.log('\nFill result:', JSON.stringify(fillResult, null, 2));

    ws.close();
}
test().catch(e => { console.error(e); process.exit(1); });
