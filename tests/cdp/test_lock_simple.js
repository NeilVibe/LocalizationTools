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
            console.log('=== BUG-002 Lock Test ===');
            console.log('');

            // Step 1: Expand first project
            console.log('Step 1: Click first project to expand...');
            const clickProj = await send(ws, id++, 'Runtime.evaluate', {
                expression: `
                    (function() {
                        // Projects are direct children with project-item class
                        const projects = document.querySelectorAll('.project-item');
                        if (projects.length === 0) return 'No projects found';

                        // Click first real project (skip if it's just New Project button)
                        for (const p of projects) {
                            const text = p.textContent.trim();
                            if (text && !text.includes('New Project')) {
                                // Find the clickable header
                                const header = p.querySelector('.project-header, [class*="header"], button');
                                if (header) {
                                    header.click();
                                    return 'Clicked project header: ' + text.substring(0, 30);
                                }
                                // Otherwise click the project item itself
                                p.click();
                                return 'Clicked project: ' + text.substring(0, 30);
                            }
                        }
                        return 'No clickable project found';
                    })()
                `,
                returnByValue: true
            });
            console.log('  Result:', clickProj.result?.result?.value);

            await new Promise(r => setTimeout(r, 2000));

            // Step 2: Check what happened - are files visible?
            console.log('Step 2: Check for files...');
            const filesCheck = await send(ws, id++, 'Runtime.evaluate', {
                expression: `
                    (function() {
                        const text = document.body.innerText;
                        // Look for file names (usually have extensions)
                        const hasFiles = text.includes('.txt') || text.includes('.xml') ||
                                        text.includes('.xlsx') || text.includes('.json');
                        const fileItems = document.querySelectorAll('.file-item, [class*="file"]');
                        return JSON.stringify({
                            hasFileExtensions: hasFiles,
                            fileItemCount: fileItems.length,
                            pageTextPreview: text.substring(0, 600)
                        });
                    })()
                `,
                returnByValue: true
            });
            const files = JSON.parse(filesCheck.result?.result?.value || '{}');
            console.log('  Has files:', files.hasFileExtensions);
            console.log('  File items:', files.fileItemCount);
            console.log('');

            // Step 3: Try to click on a file if any
            console.log('Step 3: Click file to load content...');
            const clickFile = await send(ws, id++, 'Runtime.evaluate', {
                expression: `
                    (function() {
                        // Look for text nodes containing file names
                        const walker = document.createTreeWalker(
                            document.body,
                            NodeFilter.SHOW_TEXT,
                            null,
                            false
                        );
                        let node;
                        while (node = walker.nextNode()) {
                            const text = node.textContent.trim();
                            if (text.endsWith('.txt') || text.endsWith('.xml') || text.endsWith('.xlsx')) {
                                // Click the parent element
                                let target = node.parentElement;
                                // Go up to find clickable container
                                while (target && target.tagName !== 'BODY') {
                                    if (target.onclick || target.tagName === 'BUTTON' ||
                                        target.getAttribute('role') === 'button' ||
                                        target.classList.contains('file-item')) {
                                        target.click();
                                        return 'Clicked parent of: ' + text;
                                    }
                                    target = target.parentElement;
                                }
                                // Just click the text's direct parent
                                node.parentElement.click();
                                return 'Clicked text parent: ' + text;
                            }
                        }

                        // Fallback: Try clicking .file-item class
                        const fileItems = document.querySelectorAll('.file-item');
                        if (fileItems.length > 0) {
                            fileItems[0].click();
                            return 'Clicked .file-item';
                        }

                        return 'No file to click';
                    })()
                `,
                returnByValue: true
            });
            console.log('  Result:', clickFile.result?.result?.value);

            await new Promise(r => setTimeout(r, 2000));

            // Step 4: Check grid content
            console.log('Step 4: Check grid content...');
            const gridCheck = await send(ws, id++, 'Runtime.evaluate', {
                expression: `
                    (function() {
                        const grid = document.querySelector('.virtual-grid');
                        if (!grid) return JSON.stringify({found: false});

                        const rows = grid.querySelectorAll('[class*="row"]');
                        const cells = grid.querySelectorAll('[class*="cell"]');
                        const hasKorean = grid.innerText.match(/[가-힣]/);

                        return JSON.stringify({
                            found: true,
                            rows: rows.length,
                            cells: cells.length,
                            hasKoreanText: !!hasKorean
                        });
                    })()
                `,
                returnByValue: true
            });
            const grid = JSON.parse(gridCheck.result?.result?.value || '{}');
            console.log('  Grid found:', grid.found);
            console.log('  Rows:', grid.rows, '| Cells:', grid.cells);
            console.log('  Has Korean:', grid.hasKoreanText);
            console.log('');

            // Step 5: Check for LOCK indicators
            console.log('Step 5: Check for lock indicators...');
            const lockCheck = await send(ws, id++, 'Runtime.evaluate', {
                expression: `
                    (function() {
                        const text = document.body.innerText.toLowerCase();
                        const hasLock = text.includes('lock');
                        const hasLocked = text.includes('locked');

                        // Check for lock badges/elements
                        const lockBadges = document.querySelectorAll('[class*="lock"]');
                        const lockBadgeTexts = [];
                        lockBadges.forEach(b => {
                            if (b.offsetParent !== null) { // visible
                                lockBadgeTexts.push(b.className + ': ' + b.textContent.trim().substring(0, 50));
                            }
                        });

                        return JSON.stringify({
                            textHasLock: hasLock,
                            textHasLocked: hasLocked,
                            visibleLockBadges: lockBadgeTexts.length,
                            lockBadgeDetails: lockBadgeTexts
                        });
                    })()
                `,
                returnByValue: true
            });
            const locks = JSON.parse(lockCheck.result?.result?.value || '{}');
            console.log('  Text has "lock":', locks.textHasLock);
            console.log('  Text has "locked":', locks.textHasLocked);
            console.log('  Lock badges:', locks.visibleLockBadges);
            if (locks.lockBadgeDetails.length > 0) {
                console.log('  Badge details:', locks.lockBadgeDetails);
            }
            console.log('');

            // Step 6: Try clicking edit if grid has content
            if (grid.cells > 0) {
                console.log('Step 6: Try to click edit button...');
                const editClick = await send(ws, id++, 'Runtime.evaluate', {
                    expression: `
                        (function() {
                            // Find any button with Edit in title or aria-label
                            const btns = document.querySelectorAll('button');
                            for (const btn of btns) {
                                const title = (btn.getAttribute('title') || '').toLowerCase();
                                const label = (btn.getAttribute('aria-label') || '').toLowerCase();
                                if (title.includes('edit') || label.includes('edit')) {
                                    btn.click();
                                    return 'Clicked edit button';
                                }
                            }
                            return 'No edit button found';
                        })()
                    `,
                    returnByValue: true
                });
                console.log('  Result:', editClick.result?.result?.value);

                await new Promise(r => setTimeout(r, 1500));

                // Check if edit modal opened
                const modalCheck = await send(ws, id++, 'Runtime.evaluate', {
                    expression: `
                        (function() {
                            const modal = document.querySelector('.bx--modal--open');
                            const textarea = document.querySelector('textarea');
                            const lockMsg = document.body.innerText.toLowerCase().includes('locked');

                            return JSON.stringify({
                                modalOpen: modal !== null,
                                textareaOpen: textarea !== null,
                                hasLockedMessage: lockMsg
                            });
                        })()
                    `,
                    returnByValue: true
                });
                const modal = JSON.parse(modalCheck.result?.result?.value || '{}');
                console.log('  Modal open:', modal.modalOpen);
                console.log('  Textarea open:', modal.textareaOpen);
                console.log('  Locked message:', modal.hasLockedMessage);

                console.log('');
                console.log('=== VERDICT ===');
                if (modal.hasLockedMessage && !modal.modalOpen && !modal.textareaOpen) {
                    console.log('BUG-002 NOT FIXED: Locked message shown, edit blocked');
                } else if (modal.modalOpen || modal.textareaOpen) {
                    console.log('BUG-002 FIXED! Edit works!');
                } else {
                    console.log('INCONCLUSIVE - needs manual check');
                }
            } else {
                console.log('SKIPPED: No grid content to test edit');
                console.log('');
                console.log('Page text:');
                console.log(files.pageTextPreview);
            }

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
