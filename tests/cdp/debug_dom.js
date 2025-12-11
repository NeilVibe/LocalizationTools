const CDP = require('chrome-remote-interface');

(async () => {
    const client = await CDP({ port: 9222 });
    const { Runtime } = client;
    await Runtime.enable();

    // Get DOM structure
    const dom = await Runtime.evaluate({
        expression: `
            // Find tree/project structure
            const treeNodes = document.querySelectorAll('[class*="tree"]');
            const projectNodes = document.querySelectorAll('[id^="folder-"], [id^="project-"]');
            const fileNodes = document.querySelectorAll('[id^="file-"]');
            const allButtons = document.querySelectorAll('button');

            // Get class names of important elements
            const classes = new Set();
            document.querySelectorAll('*').forEach(el => {
                if (el.className && typeof el.className === 'string') {
                    el.className.split(' ').forEach(c => {
                        if (c.includes('tree') || c.includes('node') || c.includes('grid') ||
                            c.includes('project') || c.includes('file') || c.includes('explorer')) {
                            classes.add(c);
                        }
                    });
                }
            });

            JSON.stringify({
                treeNodesCount: treeNodes.length,
                projectNodesCount: projectNodes.length,
                projectNodeIds: Array.from(projectNodes).slice(0, 5).map(n => n.id),
                fileNodesCount: fileNodes.length,
                fileNodeIds: Array.from(fileNodes).slice(0, 5).map(n => n.id),
                buttonCount: allButtons.length,
                relevantClasses: Array.from(classes).slice(0, 30)
            }, null, 2);
        `
    });
    console.log('DOM Analysis:');
    console.log(dom.result.value);

    await client.close();
})().catch(console.error);
