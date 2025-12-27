/**
 * Comprehensive UI Audit - Captures ALL console errors, takes screenshots,
 * tests interactions, and documents every issue found.
 */
const WebSocket = require('ws');
const http = require('http');
const fs = require('fs');
const path = require('path');

const SCREENSHOT_DIR = 'C:\\NEIL_PROJECTS_WINDOWSBUILD\\LocaNextProject\\screenshots\\audit_' + Date.now();
const sleep = ms => new Promise(r => setTimeout(r, ms));

let screenshotCount = 0;

async function main() {
    // Create screenshot directory
    fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
    console.log(`Screenshots will be saved to: ${SCREENSHOT_DIR}\n`);

    const targets = await new Promise((resolve, reject) => {
        http.get('http://127.0.0.1:9222/json', (res) => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => resolve(JSON.parse(data)));
        }).on('error', reject);
    });

    // Find the actual app page (not DevTools)
    const page = targets.find(t => t.type === 'page' && t.url.includes('index.html')) ||
                 targets.find(t => t.type === 'page' && !t.url.includes('devtools'));
    if (!page) {
        console.error('No page found. Is the app running?');
        console.log('Available targets:', targets.map(t => ({ type: t.type, title: t.title, url: t.url })));
        process.exit(1);
    }

    console.log(`Connected to: ${page.url}\n`);

    const ws = new WebSocket(page.webSocketDebuggerUrl);
    let id = 1;
    const allConsoleMessages = [];
    const allErrors = [];
    const allWarnings = [];

    const send = (method, params = {}) => new Promise((resolve, reject) => {
        const msgId = id++;
        const timeout = setTimeout(() => reject(new Error(`Timeout: ${method}`)), 30000);
        const handler = (msg) => {
            const r = JSON.parse(msg.toString());
            if (r.id === msgId) {
                clearTimeout(timeout);
                ws.off('message', handler);
                resolve(r);
            }
        };
        ws.on('message', handler);
        ws.send(JSON.stringify({ id: msgId, method, params }));
    });

    await new Promise(resolve => ws.on('open', resolve));

    // Enable all domains we need
    await send('Console.enable');
    await send('Runtime.enable');
    await send('Log.enable');
    await send('Page.enable');
    await send('DOM.enable');
    await send('CSS.enable');
    await send('Network.enable');

    // Collect ALL console messages
    ws.on('message', (data) => {
        const msg = JSON.parse(data.toString());

        if (msg.method === 'Console.messageAdded') {
            const entry = msg.params.message;
            allConsoleMessages.push({
                level: entry.level,
                text: entry.text,
                source: entry.source,
                url: entry.url,
                line: entry.line
            });
            if (entry.level === 'error') allErrors.push(entry);
            if (entry.level === 'warning') allWarnings.push(entry);
        }

        if (msg.method === 'Runtime.consoleAPICalled') {
            const args = msg.params.args.map(a => a.value || a.description || JSON.stringify(a)).join(' ');
            const entry = {
                level: msg.params.type,
                text: args,
                stackTrace: msg.params.stackTrace
            };
            allConsoleMessages.push(entry);
            if (msg.params.type === 'error') allErrors.push(entry);
            if (msg.params.type === 'warning') allWarnings.push(entry);
        }

        if (msg.method === 'Runtime.exceptionThrown') {
            const ex = msg.params.exceptionDetails;
            allErrors.push({
                level: 'exception',
                text: ex.text || ex.exception?.description || 'Unknown exception',
                url: ex.url,
                line: ex.lineNumber,
                column: ex.columnNumber,
                stackTrace: ex.stackTrace
            });
        }

        if (msg.method === 'Log.entryAdded') {
            const entry = msg.params.entry;
            allConsoleMessages.push({
                level: entry.level,
                text: entry.text,
                source: entry.source,
                url: entry.url
            });
            if (entry.level === 'error') allErrors.push(entry);
            if (entry.level === 'warning') allWarnings.push(entry);
        }
    });

    async function takeScreenshot(name) {
        screenshotCount++;
        const filename = `${String(screenshotCount).padStart(3, '0')}_${name}.png`;
        const result = await send('Page.captureScreenshot', { format: 'png' });
        const buffer = Buffer.from(result.result.data, 'base64');
        fs.writeFileSync(path.join(SCREENSHOT_DIR, filename), buffer);
        console.log(`📸 Screenshot: ${filename}`);
        return filename;
    }

    async function evaluate(expression) {
        const result = await send('Runtime.evaluate', {
            expression,
            returnByValue: true,
            awaitPromise: true
        });
        return result.result?.result?.value;
    }

    async function getElementAt(x, y) {
        const doc = await send('DOM.getDocument');
        const node = await send('DOM.getNodeForLocation', { x, y });
        if (node.result?.nodeId) {
            const attrs = await send('DOM.getAttributes', { nodeId: node.result.nodeId });
            return attrs.result?.attributes || [];
        }
        return null;
    }

    async function clickAt(x, y) {
        await send('Input.dispatchMouseEvent', { type: 'mousePressed', x, y, button: 'left', clickCount: 1 });
        await send('Input.dispatchMouseEvent', { type: 'mouseReleased', x, y, button: 'left', clickCount: 1 });
    }

    async function hoverAt(x, y) {
        await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x, y });
    }

    console.log('='.repeat(60));
    console.log('COMPREHENSIVE UI AUDIT - LOCANEXT');
    console.log('='.repeat(60));

    // Initial screenshot
    await takeScreenshot('01_initial_state');
    await sleep(500);

    // Get current page info
    const currentUrl = await evaluate('window.location.href');
    const pageTitle = await evaluate('document.title');
    console.log(`\nPage: ${pageTitle}`);
    console.log(`URL: ${currentUrl}\n`);

    // Check if we're on file viewer
    const isFileViewer = await evaluate(`
        const grid = document.querySelector('.virtual-grid');
        const fileViewer = document.querySelector('[class*="file-viewer"]');
        const rows = document.querySelectorAll('.virtual-row');
        JSON.stringify({
            hasGrid: !!grid,
            hasFileViewer: !!fileViewer,
            rowCount: rows.length,
            gridClass: grid?.className || 'none',
            containerHeight: grid?.parentElement?.clientHeight || 0
        });
    `);
    console.log('File Viewer State:', isFileViewer);

    // Get viewport dimensions
    const viewport = await evaluate(`JSON.stringify({ width: window.innerWidth, height: window.innerHeight })`);
    console.log('Viewport:', viewport);

    // ========== TEST 1: Grid/Cell Analysis ==========
    console.log('\n--- TEST 1: Grid & Cell Analysis ---');

    const gridAnalysis = await evaluate(`
        const rows = document.querySelectorAll('.virtual-row');
        const cells = document.querySelectorAll('.cell');
        const sourceCells = document.querySelectorAll('.cell.source, [class*="source"]');
        const targetCells = document.querySelectorAll('.cell.target, [class*="target"]');

        const cellHeights = [];
        cells.forEach(c => cellHeights.push(c.offsetHeight));

        const rowHeights = [];
        rows.forEach(r => rowHeights.push(r.offsetHeight));

        JSON.stringify({
            totalRows: rows.length,
            totalCells: cells.length,
            sourceCells: sourceCells.length,
            targetCells: targetCells.length,
            cellHeights: cellHeights.slice(0, 10),
            rowHeights: rowHeights.slice(0, 10),
            maxCellHeight: Math.max(...cellHeights),
            minCellHeight: Math.min(...cellHeights),
            avgCellHeight: (cellHeights.reduce((a,b) => a+b, 0) / cellHeights.length).toFixed(1)
        });
    `);
    console.log('Grid Analysis:', gridAnalysis);
    await takeScreenshot('02_grid_analysis');

    // ========== TEST 2: Hover Behavior ==========
    console.log('\n--- TEST 2: Hover Behavior Analysis ---');

    // Find first row position
    const firstRowPos = await evaluate(`
        const row = document.querySelector('.virtual-row');
        if (row) {
            const rect = row.getBoundingClientRect();
            JSON.stringify({ x: rect.x + 50, y: rect.y + 10, width: rect.width, height: rect.height });
        } else {
            null;
        }
    `);

    if (firstRowPos) {
        const pos = JSON.parse(firstRowPos);
        console.log('First row position:', firstRowPos);

        // Screenshot before hover
        await takeScreenshot('03_before_hover');

        // Hover over first row
        await hoverAt(pos.x, pos.y);
        await sleep(300);
        await takeScreenshot('04_hover_row1');

        // Check hover styles
        const hoverStyles = await evaluate(`
            const row = document.querySelector('.virtual-row');
            if (row) {
                const styles = window.getComputedStyle(row);
                JSON.stringify({
                    background: styles.backgroundColor,
                    boxShadow: styles.boxShadow,
                    border: styles.border,
                    outline: styles.outline
                });
            }
        `);
        console.log('Hover styles:', hoverStyles);

        // Hover over different positions in the row
        for (let i = 1; i <= 5; i++) {
            const xPos = pos.x + (i * 100);
            await hoverAt(xPos, pos.y);
            await sleep(200);
            await takeScreenshot(`05_hover_position_${i}`);
        }

        // Hover over second row
        await hoverAt(pos.x, pos.y + pos.height + 5);
        await sleep(300);
        await takeScreenshot('06_hover_row2');

        // Hover over third row
        await hoverAt(pos.x, pos.y + (pos.height * 2) + 10);
        await sleep(300);
        await takeScreenshot('07_hover_row3');
    }

    // ========== TEST 3: Cell Selection/Click Behavior ==========
    console.log('\n--- TEST 3: Cell Selection & Click Behavior ---');

    const cellPositions = await evaluate(`
        const cells = document.querySelectorAll('.cell');
        const positions = [];
        cells.forEach((c, i) => {
            if (i < 6) {
                const rect = c.getBoundingClientRect();
                const classes = c.className;
                positions.push({
                    index: i,
                    x: rect.x + 20,
                    y: rect.y + 10,
                    width: rect.width,
                    height: rect.height,
                    classes: classes,
                    isSource: classes.includes('source') || c.closest('[class*="source"]'),
                    isTarget: classes.includes('target') || c.closest('[class*="target"]')
                });
            }
        });
        JSON.stringify(positions);
    `);
    console.log('Cell positions:', cellPositions);

    if (cellPositions) {
        const cells = JSON.parse(cellPositions);

        // Try clicking on source cell
        const sourceCell = cells.find(c => c.classes.includes('source') || c.index % 3 === 1);
        if (sourceCell) {
            console.log(`Clicking source cell at (${sourceCell.x}, ${sourceCell.y})`);
            await takeScreenshot('08_before_source_click');
            await clickAt(sourceCell.x, sourceCell.y);
            await sleep(500);
            await takeScreenshot('09_after_source_click');

            // Check if text is selectable
            const sourceSelectable = await evaluate(`
                const selection = window.getSelection();
                const cells = document.querySelectorAll('.cell');
                let isEditable = false;
                cells.forEach(c => {
                    if (c.contentEditable === 'true' || c.querySelector('input, textarea')) {
                        isEditable = true;
                    }
                });
                JSON.stringify({
                    hasSelection: selection.toString().length > 0,
                    selectionText: selection.toString().substring(0, 50),
                    isEditable: isEditable
                });
            `);
            console.log('Source cell selectability:', sourceSelectable);
        }

        // Try clicking on target cell
        const targetCell = cells.find(c => c.classes.includes('target') || c.index % 3 === 2);
        if (targetCell) {
            console.log(`Clicking target cell at (${targetCell.x}, ${targetCell.y})`);
            await takeScreenshot('10_before_target_click');
            await clickAt(targetCell.x, targetCell.y);
            await sleep(1000);
            await takeScreenshot('11_after_target_click');

            // Check for modal/edit panel
            const editPanelState = await evaluate(`
                const modal = document.querySelector('.bx--modal, [class*="modal"], [class*="Modal"]');
                const editPanel = document.querySelector('[class*="edit"], [class*="Edit"]');
                const overlay = document.querySelector('[class*="overlay"], [class*="Overlay"]');
                const loading = document.querySelector('[class*="loading"], [class*="Loading"], .bx--loading');

                JSON.stringify({
                    hasModal: !!modal,
                    modalVisible: modal?.classList.contains('is-visible') || modal?.style.display !== 'none',
                    hasEditPanel: !!editPanel,
                    hasOverlay: !!overlay,
                    hasLoading: !!loading,
                    loadingVisible: loading?.style.display !== 'none'
                });
            `);
            console.log('Edit panel state:', editPanelState);
        }
    }

    // ========== TEST 4: Cell Edit Modal (if open) ==========
    console.log('\n--- TEST 4: Cell Edit Modal Analysis ---');

    await sleep(2000); // Wait for any modal to fully load

    const modalAnalysis = await evaluate(`
        const modals = document.querySelectorAll('.bx--modal, [class*="modal"], [class*="Modal"], [class*="dialog"], [class*="Dialog"]');
        const closeButtons = document.querySelectorAll('[class*="close"], button[aria-label*="close"], .bx--modal-close');
        const xButtons = document.querySelectorAll('button svg, [class*="close"] svg');
        const loadingElements = document.querySelectorAll('.bx--loading, [class*="loading"], [class*="spinner"]');

        const modalInfo = [];
        modals.forEach(m => {
            const rect = m.getBoundingClientRect();
            const styles = window.getComputedStyle(m);
            modalInfo.push({
                className: m.className,
                visible: styles.display !== 'none' && styles.visibility !== 'hidden',
                position: { x: rect.x, y: rect.y, w: rect.width, h: rect.height },
                zIndex: styles.zIndex
            });
        });

        JSON.stringify({
            totalModals: modals.length,
            modals: modalInfo,
            closeButtonCount: closeButtons.length,
            xButtonCount: xButtons.length,
            loadingCount: loadingElements.length,
            loadingVisible: Array.from(loadingElements).some(l => {
                const s = window.getComputedStyle(l);
                return s.display !== 'none' && s.visibility !== 'hidden';
            })
        });
    `);
    console.log('Modal analysis:', modalAnalysis);
    await takeScreenshot('12_modal_state');

    // Try to find and click close button
    const closeButtonPos = await evaluate(`
        const closeBtn = document.querySelector('.bx--modal-close, [class*="close-button"], button[aria-label*="close"]');
        if (closeBtn) {
            const rect = closeBtn.getBoundingClientRect();
            JSON.stringify({ x: rect.x + rect.width/2, y: rect.y + rect.height/2, found: true });
        } else {
            const allButtons = document.querySelectorAll('button');
            let xBtn = null;
            allButtons.forEach(b => {
                if (b.textContent.includes('×') || b.textContent.includes('X') || b.innerHTML.includes('svg')) {
                    const rect = b.getBoundingClientRect();
                    if (rect.width > 0 && rect.width < 100) xBtn = b;
                }
            });
            if (xBtn) {
                const rect = xBtn.getBoundingClientRect();
                JSON.stringify({ x: rect.x + rect.width/2, y: rect.y + rect.height/2, found: true, type: 'x-button' });
            } else {
                JSON.stringify({ found: false });
            }
        }
    `);
    console.log('Close button:', closeButtonPos);

    if (closeButtonPos) {
        const btn = JSON.parse(closeButtonPos);
        if (btn.found) {
            console.log(`Clicking close button at (${btn.x}, ${btn.y})`);
            await takeScreenshot('13_before_close_click');
            await clickAt(btn.x, btn.y);
            await sleep(1000);
            await takeScreenshot('14_after_close_click');
        }
    }

    // ========== TEST 5: Scroll Behavior (Lazy Loading) ==========
    console.log('\n--- TEST 5: Scroll & Lazy Loading ---');

    const scrollContainer = await evaluate(`
        const container = document.querySelector('.scroll-container, [class*="scroll"], .virtual-grid');
        if (container) {
            const rect = container.getBoundingClientRect();
            JSON.stringify({
                scrollHeight: container.scrollHeight,
                clientHeight: container.clientHeight,
                scrollTop: container.scrollTop,
                canScroll: container.scrollHeight > container.clientHeight,
                rect: { x: rect.x, y: rect.y, w: rect.width, h: rect.height }
            });
        } else {
            null;
        }
    `);
    console.log('Scroll container:', scrollContainer);

    if (scrollContainer) {
        const sc = JSON.parse(scrollContainer);

        // Screenshot before scroll
        await takeScreenshot('15_before_scroll');

        // Scroll down
        await evaluate(`
            const container = document.querySelector('.scroll-container, [class*="scroll"], .virtual-grid');
            if (container) container.scrollTop += 500;
        `);
        await sleep(500);
        await takeScreenshot('16_after_scroll_500');

        const afterScroll1 = await evaluate(`
            const container = document.querySelector('.scroll-container, [class*="scroll"], .virtual-grid');
            const rows = document.querySelectorAll('.virtual-row');
            JSON.stringify({
                scrollTop: container?.scrollTop,
                rowCount: rows.length
            });
        `);
        console.log('After scroll 500px:', afterScroll1);

        // Scroll more
        await evaluate(`
            const container = document.querySelector('.scroll-container, [class*="scroll"], .virtual-grid');
            if (container) container.scrollTop += 1000;
        `);
        await sleep(500);
        await takeScreenshot('17_after_scroll_1500');

        const afterScroll2 = await evaluate(`
            const container = document.querySelector('.scroll-container, [class*="scroll"], .virtual-grid');
            const rows = document.querySelectorAll('.virtual-row');
            JSON.stringify({
                scrollTop: container?.scrollTop,
                rowCount: rows.length
            });
        `);
        console.log('After scroll 1500px:', afterScroll2);

        // Scroll to end
        await evaluate(`
            const container = document.querySelector('.scroll-container, [class*="scroll"], .virtual-grid');
            if (container) container.scrollTop = container.scrollHeight;
        `);
        await sleep(500);
        await takeScreenshot('18_scroll_to_end');
    }

    // ========== TEST 6: TM Status Check ==========
    console.log('\n--- TEST 6: TM Status & Loading ---');

    const tmStatus = await evaluate(`
        const tmElements = document.querySelectorAll('[class*="tm"], [class*="TM"], [class*="translation"]');
        const loadingSpinners = document.querySelectorAll('.bx--loading, [class*="spinner"], [class*="loading"]');
        const statusBadges = document.querySelectorAll('[class*="status"], [class*="badge"]');

        JSON.stringify({
            tmElementCount: tmElements.length,
            loadingCount: loadingSpinners.length,
            statusBadges: Array.from(statusBadges).map(s => s.textContent.substring(0, 50))
        });
    `);
    console.log('TM Status:', tmStatus);

    // ========== TEST 7: CSS Issues Detection ==========
    console.log('\n--- TEST 7: CSS Issues Detection ---');

    const cssIssues = await evaluate(`
        const issues = [];

        // Check for overflow issues
        document.querySelectorAll('*').forEach(el => {
            const styles = window.getComputedStyle(el);
            const rect = el.getBoundingClientRect();

            // Text overflow without ellipsis
            if (el.scrollWidth > el.clientWidth && styles.overflow === 'visible') {
                issues.push({ type: 'text-overflow', element: el.className });
            }

            // Elements outside viewport
            if (rect.right < 0 || rect.bottom < 0 || rect.left > window.innerWidth) {
                issues.push({ type: 'off-screen', element: el.className });
            }

            // Z-index issues
            if (parseInt(styles.zIndex) > 10000) {
                issues.push({ type: 'high-zindex', element: el.className, zIndex: styles.zIndex });
            }
        });

        // Limit to first 50 issues
        JSON.stringify(issues.slice(0, 50));
    `);
    console.log('CSS Issues:', cssIssues);

    // ========== FINAL: Collect All Errors ==========
    console.log('\n' + '='.repeat(60));
    console.log('CONSOLE ERRORS & WARNINGS SUMMARY');
    console.log('='.repeat(60));

    // Wait a bit more to collect any remaining messages
    await sleep(2000);

    // Take final screenshot
    await takeScreenshot('19_final_state');

    console.log(`\nTotal console messages collected: ${allConsoleMessages.length}`);
    console.log(`Total ERRORS: ${allErrors.length}`);
    console.log(`Total WARNINGS: ${allWarnings.length}`);

    // Group errors by type
    const errorGroups = {};
    allErrors.forEach(e => {
        const key = (e.text || '').substring(0, 100);
        if (!errorGroups[key]) errorGroups[key] = [];
        errorGroups[key].push(e);
    });

    console.log('\n--- UNIQUE ERRORS ---');
    Object.entries(errorGroups).forEach(([key, errors], i) => {
        console.log(`\n[ERROR ${i + 1}] (${errors.length}x): ${key}`);
        if (errors[0].url) console.log(`  URL: ${errors[0].url}:${errors[0].line}`);
    });

    // Group warnings by type
    const warningGroups = {};
    allWarnings.forEach(w => {
        const key = (w.text || '').substring(0, 100);
        if (!warningGroups[key]) warningGroups[key] = [];
        warningGroups[key].push(w);
    });

    console.log('\n--- UNIQUE WARNINGS ---');
    Object.entries(warningGroups).slice(0, 30).forEach(([key, warnings], i) => {
        console.log(`\n[WARNING ${i + 1}] (${warnings.length}x): ${key}`);
    });

    // Save full report
    const reportPath = path.join(SCREENSHOT_DIR, 'AUDIT_REPORT.json');
    const report = {
        timestamp: new Date().toISOString(),
        page: { url: currentUrl, title: pageTitle },
        screenshotCount,
        totalMessages: allConsoleMessages.length,
        totalErrors: allErrors.length,
        totalWarnings: allWarnings.length,
        uniqueErrors: Object.keys(errorGroups).length,
        uniqueWarnings: Object.keys(warningGroups).length,
        errors: allErrors,
        warnings: allWarnings,
        allMessages: allConsoleMessages
    };
    fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
    console.log(`\nFull report saved to: ${reportPath}`);

    console.log(`\n📸 Total screenshots taken: ${screenshotCount}`);
    console.log(`📁 Screenshots saved to: ${SCREENSHOT_DIR}`);

    ws.close();
}

main().catch(e => { console.error(e); process.exit(1); });
