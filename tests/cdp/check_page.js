const CDP = require('chrome-remote-interface');

(async () => {
    const client = await CDP({ port: 9222 });
    const { Runtime } = client;
    await Runtime.enable();

    // Check what's on screen
    const check = await Runtime.evaluate({
        expression: `
            JSON.stringify({
                url: window.location.href,
                title: document.title,
                bodyLength: document.body.innerHTML.length,
                hasLDM: document.querySelector('.ldm-container') !== null,
                hasHeader: document.querySelector('header, .bx--header') !== null,
                hasError: document.body.innerText.includes('error') || document.body.innerText.includes('Error'),
                visibleText: document.body.innerText.substring(0, 500)
            });
        `
    });
    console.log('Page state:', check.result.value);

    const parsed = JSON.parse(check.result.value);
    console.log('');
    console.log('URL:', parsed.url);
    console.log('Title:', parsed.title);
    console.log('Has LDM:', parsed.hasLDM);
    console.log('Has Header:', parsed.hasHeader);
    console.log('Has Error:', parsed.hasError);
    console.log('');
    console.log('Visible text preview:');
    console.log(parsed.visibleText);

    await client.close();
})().catch(console.error);
