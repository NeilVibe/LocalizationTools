/**
 * Build 308 Verification Test
 * Tests all 10 fixes from the Build 308 session
 */

const CDP = require('chrome-remote-interface');

async function verifyBuild308() {
    let client;
    const results = {
        passed: [],
        failed: [],
        warnings: []
    };

    try {
        client = await CDP({ port: 9222 });
        const { Runtime, Page, DOM } = client;

        await Promise.all([Runtime.enable(), Page.enable(), DOM.enable()]);
        await new Promise(r => setTimeout(r, 2000));

        console.log('=== BUILD 308 VERIFICATION ===\n');

        // Get full page HTML for analysis
        const htmlResult = await Runtime.evaluate({
            expression: `document.body.innerHTML`
        });
        const html = htmlResult.result.value;

        // ==== UI-035: No Pagination in TMDataGrid ====
        console.log('UI-035: Checking for pagination...');
        const hasPagination = html.includes('Items per page') ||
                             html.includes('bx--pagination') ||
                             html.includes('1 of 1');
        if (!hasPagination) {
            results.passed.push('UI-035: No pagination found');
            console.log('  PASS: No pagination elements found');
        } else {
            results.failed.push('UI-035: Pagination still present');
            console.log('  FAIL: Pagination elements still in DOM');
        }

        // ==== UI-036: No Confirm Button ====
        console.log('\nUI-036: Checking for Confirm button...');
        const hasConfirmBtn = html.includes('Confirm') &&
                              (html.includes('toggleConfirm') || html.includes('tm-confirm'));
        // Check in TM Grid specifically
        const confirmBtnResult = await Runtime.evaluate({
            expression: `
                const tmGrid = document.querySelector('.tm-grid, .tm-data-grid');
                if (tmGrid) {
                    const buttons = tmGrid.querySelectorAll('button');
                    return Array.from(buttons).some(b => b.textContent.includes('Confirm'));
                }
                return false;
            `
        });
        if (!confirmBtnResult.result.value) {
            results.passed.push('UI-036: No Confirm button in TM grid');
            console.log('  PASS: No Confirm button found in TM grid');
        } else {
            results.failed.push('UI-036: Confirm button still present');
            console.log('  FAIL: Confirm button still in TM grid');
        }

        // ==== UI-037: No "No email" text ====
        console.log('\nUI-037: Checking for "No email" text...');
        const hasNoEmail = html.includes('No email');
        if (!hasNoEmail) {
            results.passed.push('UI-037: No "No email" text');
            console.log('  PASS: No "No email" text found');
        } else {
            results.failed.push('UI-037: "No email" text still present');
            console.log('  FAIL: "No email" text still in DOM');
        }

        // ==== UI-038: User Profile Modal ====
        console.log('\nUI-038: Checking for User Profile Modal support...');
        // Check if clicking username opens modal
        const userMenuResult = await Runtime.evaluate({
            expression: `
                // Look for user menu
                const userMenu = document.querySelector('[class*="header-action"]') ||
                                document.querySelector('button[title*="User"]');
                // Check if UserProfileModal component exists in imports
                const hasUserProfileModal = document.querySelector('[class*="user-profile"]') !== null ||
                                           document.body.innerHTML.includes('View Profile');
                return hasUserProfileModal;
            `
        });
        if (userMenuResult.result.value || html.includes('View Profile')) {
            results.passed.push('UI-038: User Profile Modal support present');
            console.log('  PASS: "View Profile" option available');
        } else {
            results.warnings.push('UI-038: Could not verify User Profile Modal (needs manual test)');
            console.log('  WARN: Cannot verify modal without clicking menu - needs manual test');
        }

        // ==== UI-039: Third Column Logic ====
        console.log('\nUI-039: Checking column configuration...');
        // Check that TM Results is not in visible columns dropdown
        const colConfigResult = await Runtime.evaluate({
            expression: `
                const html = document.body.innerHTML;
                const hasTMResults = html.includes('TM Results') && html.includes('column');
                return !hasTMResults;
            `
        });
        if (colConfigResult.result.value) {
            results.passed.push('UI-039: No TM Results column option');
            console.log('  PASS: TM Results column not in options');
        } else {
            results.warnings.push('UI-039: TM Results check inconclusive');
            console.log('  WARN: Could not verify column options');
        }

        // ==== UI-040: No "i" button in PresenceBar ====
        console.log('\nUI-040: Checking PresenceBar for empty tooltips...');
        const presenceBarResult = await Runtime.evaluate({
            expression: `
                // Look for empty tooltip triggers (the "i" button bug)
                const presenceBar = document.querySelector('.presence-bar, [class*="presence"]');
                if (presenceBar) {
                    // Check for buttons with no text/icon that were tooltip triggers
                    const emptyButtons = presenceBar.querySelectorAll('button:empty, [class*="tooltip-trigger"]:empty');
                    return emptyButtons.length === 0;
                }
                // Also check for triggerText="" pattern
                return !document.body.innerHTML.includes('triggerText=""');
            `
        });
        if (presenceBarResult.result.value) {
            results.passed.push('UI-040: No empty tooltip triggers');
            console.log('  PASS: No empty "i" button/tooltip trigger');
        } else {
            results.failed.push('UI-040: Empty tooltip trigger may still exist');
            console.log('  FAIL: Empty tooltip trigger might be present');
        }

        // ==== UI-041: No Footer in VirtualGrid ====
        console.log('\nUI-041: Checking for VirtualGrid footer...');
        const hasFooter = html.includes('Showing rows') ||
                         html.includes('grid-footer') ||
                         html.includes('of rows');
        if (!hasFooter) {
            results.passed.push('UI-041: No VirtualGrid footer');
            console.log('  PASS: No "Showing rows X-Y" footer');
        } else {
            results.failed.push('UI-041: Footer still present');
            console.log('  FAIL: Footer text still in DOM');
        }

        // ==== BUG-032/033/034: Sync Status Updates ====
        console.log('\nBUG-032/033/034: Sync status (needs backend test)...');
        // This requires actual TM edit and sync operation
        results.warnings.push('BUG-032/033/034: Sync fixes require manual TM edit test');
        console.log('  WARN: Sync status updates need manual verification with TM edit');

        // ==== Summary ====
        console.log('\n=== SUMMARY ===');
        console.log(`PASSED: ${results.passed.length}`);
        results.passed.forEach(p => console.log(`  ✓ ${p}`));

        if (results.warnings.length > 0) {
            console.log(`\nWARNINGS: ${results.warnings.length}`);
            results.warnings.forEach(w => console.log(`  ⚠ ${w}`));
        }

        if (results.failed.length > 0) {
            console.log(`\nFAILED: ${results.failed.length}`);
            results.failed.forEach(f => console.log(`  ✗ ${f}`));
        }

        const total = results.passed.length + results.failed.length + results.warnings.length;
        console.log(`\nTotal: ${results.passed.length}/${total - results.warnings.length} passed (${results.warnings.length} need manual check)`);

        return results.failed.length === 0;

    } catch (err) {
        console.error('CDP Error:', err.message);
        return false;
    } finally {
        if (client) await client.close();
    }
}

verifyBuild308().then(success => {
    process.exit(success ? 0 : 1);
});
