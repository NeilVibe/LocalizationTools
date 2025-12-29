import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';

/**
 * Check 5 MEDIUM issues with actual file loaded in grid
 *
 * Issues:
 * - UI-063: CSS Text Overflow (missing ellipsis)
 * - UI-066: Placeholder rows wrong column count
 * - UI-067: Filter dropdown height mismatch
 * - UI-068: Resize handle not visible until hover
 * - UI-069: QA + Edit icon overlap
 */

const API_URL = 'http://localhost:8888';
const TEST_USER = 'admin';
const TEST_PASS = 'admin123';

// Test fixture file
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const FIXTURE_FILE = path.join(__dirname, 'fixtures', 'sample_language_data.txt');

async function getAuthToken(request: any): Promise<string> {
    const response = await request.post(`${API_URL}/api/v2/auth/login`, {
        data: { username: TEST_USER, password: TEST_PASS }
    });
    if (!response.ok()) {
        throw new Error(`Login failed: ${response.status()}`);
    }
    const { access_token } = await response.json();
    return access_token;
}

test('check 5 MEDIUM issues with loaded grid', async ({ page, request }) => {
    // Step 1: Ensure file exists via API
    const token = await getAuthToken(request);
    console.log('✓ Got auth token');

    // Get or create project
    let projectId: number;
    const projectsResp = await request.get(`${API_URL}/api/ldm/projects`, {
        headers: { Authorization: `Bearer ${token}` }
    });
    const projects = await projectsResp.json();

    if (projects.length > 0) {
        projectId = projects[0].id;
        console.log(`✓ Using existing project: ${projects[0].name} (ID: ${projectId})`);
    } else {
        const createResp = await request.post(`${API_URL}/api/ldm/projects`, {
            headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
            data: { name: 'MEDIUM Issues Test', source_lang: 'ko', target_lang: 'fr' }
        });
        const newProject = await createResp.json();
        projectId = newProject.id;
        console.log(`✓ Created project: ${newProject.name} (ID: ${projectId})`);
    }

    // Upload test file - create synthetic data with long text for overflow testing
    let fileId: number | null = null;

    // Create test data with long strings to test overflow/ellipsis
    // Format: col0\tcol1\tcol2\tcol3\tcol4\tSource\tTarget (7+ columns required)
    const lines: string[] = [];
    for (let i = 0; i < 100; i++) {
        const col0 = 'GAME';
        const col1 = 'UI';
        const col2 = 'MENU';
        const col3 = String(i).padStart(4, '0');
        const col4 = 'TEXT';
        const longSource = `Source text line ${i} with extra long content that should trigger text overflow behavior and ellipsis display when rendered in narrow cells ${i}`;
        const longTarget = `Target translation ${i} with similarly long text content to verify ellipsis styling works correctly on both source and target columns ${i}`;
        lines.push(`${col0}\t${col1}\t${col2}\t${col3}\t${col4}\t${longSource}\t${longTarget}`);
    }
    const syntheticData = lines.join('\n');

    const uploadResp = await request.post(`${API_URL}/api/ldm/files/upload`, {
        headers: { Authorization: `Bearer ${token}` },
        multipart: {
            file: { name: 'medium_overflow_test.txt', mimeType: 'text/plain', buffer: Buffer.from(syntheticData) },
            project_id: projectId.toString()
        }
    });
    console.log(`Upload response status: ${uploadResp.status()}`);
    if (uploadResp.ok()) {
        const result = await uploadResp.json();
        fileId = result.id;
        console.log(`✓ Uploaded file: medium_overflow_test.txt (ID: ${fileId})`);
    } else if (uploadResp.status() === 409) {
        console.log('✓ File already exists (409), finding in tree...');
    } else {
        const errText = await uploadResp.text();
        console.log(`✗ Upload failed: ${uploadResp.status()} - ${errText}`);
    }

    // Get file ID from project tree if not from upload
    if (!fileId) {
        const treeResp = await request.get(`${API_URL}/api/ldm/projects/${projectId}/tree`, {
            headers: { Authorization: `Bearer ${token}` }
        });
        const tree = await treeResp.json();
        console.log('Tree structure:', JSON.stringify(tree, null, 2).substring(0, 500));

        function findFile(nodes: any[]): any {
            if (!Array.isArray(nodes)) return null;
            for (const node of nodes) {
                if (node.type === 'file') return node;
                if (node.children) {
                    const found = findFile(node.children);
                    if (found) return found;
                }
            }
            return null;
        }
        // The tree response might be the project node itself with children
        const searchNodes = tree.children || (Array.isArray(tree) ? tree : [tree]);
        const file = findFile(searchNodes);
        if (file) {
            fileId = file.id;
            console.log(`✓ Found file in tree: ${file.name} (ID: ${fileId})`);
        } else {
            // Try to find file by direct query
            const filesResp = await request.get(`${API_URL}/api/ldm/files?project_id=${projectId}`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            if (filesResp.ok()) {
                const files = await filesResp.json();
                if (files.length > 0) {
                    fileId = files[0].id;
                    console.log(`✓ Found file via direct query: ${files[0].name} (ID: ${fileId})`);
                }
            }
        }
    }

    if (!fileId) {
        console.log('⚠ No file available to test with');
        return;
    }

    // Step 2: Login via UI
    await page.goto('/');
    await page.getByPlaceholder('Enter your username').fill(TEST_USER);
    await page.getByPlaceholder('Enter your password').fill(TEST_PASS);
    await page.getByRole('button', { name: /login/i }).click();
    await page.waitForTimeout(2000);
    console.log('✓ Logged in');

    // Step 3: Navigate to LDM using navTest helper
    await page.evaluate(() => {
        if ((window as any).navTest?.goToApp) {
            (window as any).navTest.goToApp('ldm');
        }
    });
    await page.waitForTimeout(1000);
    console.log('✓ Navigated to LDM');

    // Step 4: Load the file via API call in page context
    await page.evaluate(async (params: { fileId: number; token: string; apiUrl: string }) => {
        const resp = await fetch(`${params.apiUrl}/api/ldm/files/${params.fileId}/rows?offset=0&limit=50`, {
            headers: { Authorization: `Bearer ${params.token}` }
        });
        const data = await resp.json();
        console.log('File rows loaded:', data?.rows?.length || 0);

        // Trigger file selection in app
        if ((window as any).__loadFileForTest) {
            (window as any).__loadFileForTest(params.fileId);
        }
    }, { fileId, token, apiUrl: API_URL });

    // Wait for sidebar to render
    await page.waitForTimeout(2000);

    // First, expand the project to show files
    const projectItem = page.locator('text=Playwright Test Project');
    if (await projectItem.isVisible({ timeout: 3000 }).catch(() => false)) {
        await projectItem.click();
        await page.waitForTimeout(1000); // Wait for expansion
        console.log('✓ Expanded project');
    }

    // Now click on the file
    const fileItem = page.locator('text=medium_overflow_test.txt');
    if (await fileItem.isVisible({ timeout: 3000 }).catch(() => false)) {
        await fileItem.click();
        await page.waitForTimeout(3000); // Wait for grid to load
        console.log('✓ Clicked file: medium_overflow_test.txt');
    } else {
        // Try clicking any visible .txt file
        const anyFile = page.locator('text=/sample.*\\.txt|test.*\\.txt|medium.*\\.txt/').first();
        if (await anyFile.isVisible({ timeout: 2000 }).catch(() => false)) {
            const fileName = await anyFile.textContent();
            await anyFile.click();
            await page.waitForTimeout(3000);
            console.log(`✓ Clicked file: ${fileName}`);
        } else {
            console.log('⚠ Could not find file to click');
        }
    }

    // Step 5: Take screenshot
    await page.screenshot({ path: '/tmp/medium_01_grid.png', fullPage: true });
    console.log('\n=== CHECKING 5 MEDIUM ISSUES ===\n');

    // Step 6: Analyze DOM for issues
    const domInfo = await page.evaluate(() => {
        const virtualRows = document.querySelectorAll('.virtual-row');
        const cells = document.querySelectorAll('.cell');
        const sourceCells = document.querySelectorAll('.cell.source');
        const targetCells = document.querySelectorAll('.cell.target');
        const searchInput = document.querySelector('#ldm-search-input');
        // Measure the actual visible dropdown button, not the wrapper
        const filterDropdown = document.querySelector('.filter-wrapper .bx--list-box__field') ||
                              document.querySelector('.filter-wrapper button') ||
                              document.querySelector('.filter-wrapper');
        const resizeHandles = document.querySelectorAll('[class*="resize"], .resize-handle');
        const qaFlagged = document.querySelectorAll('.qa-flagged, [class*="qa-flag"]');
        const editIcons = document.querySelectorAll('.edit-icon, [class*="edit-icon"]');
        const headerCells = document.querySelectorAll('.header-cell');

        // UI-063: Check text overflow styling
        let cellsWithOverflow = 0;
        let cellsWithEllipsis = 0;
        cells.forEach(cell => {
            const style = getComputedStyle(cell);
            if (style.overflow === 'hidden') {
                cellsWithOverflow++;
                if (style.textOverflow === 'ellipsis') cellsWithEllipsis++;
            }
        });

        // UI-067: Measure heights
        const inputHeight = searchInput ? (searchInput as HTMLElement).offsetHeight : 0;
        const dropdownRect = filterDropdown ? (filterDropdown as HTMLElement).getBoundingClientRect() : null;

        // Get body HTML length for debugging
        const bodyLen = document.body.innerHTML.length;

        return {
            rows: virtualRows.length,
            cells: cells.length,
            sourceCells: sourceCells.length,
            targetCells: targetCells.length,
            headerCells: headerCells.length,
            searchInputHeight: inputHeight,
            dropdownHeight: dropdownRect?.height || 0,
            resizeHandles: resizeHandles.length,
            qaFlagged: qaFlagged.length,
            editIcons: editIcons.length,
            cellsWithOverflow,
            cellsWithEllipsis,
            bodyLen
        };
    });

    console.log('Grid State:');
    console.log(`  Rows: ${domInfo.rows}`);
    console.log(`  Cells: ${domInfo.cells} (${domInfo.sourceCells} source, ${domInfo.targetCells} target)`);
    console.log(`  Header cells: ${domInfo.headerCells}`);
    console.log(`  Body HTML length: ${domInfo.bodyLen}`);

    console.log('\n--- UI-063: Text Overflow ---');
    console.log(`  Cells with overflow:hidden: ${domInfo.cellsWithOverflow}`);
    console.log(`  Cells with text-overflow:ellipsis: ${domInfo.cellsWithEllipsis}`);
    if (domInfo.cellsWithOverflow > domInfo.cellsWithEllipsis) {
        console.log(`  ⚠ ${domInfo.cellsWithOverflow - domInfo.cellsWithEllipsis} cells MISSING ellipsis`);
    } else if (domInfo.cellsWithOverflow > 0) {
        console.log('  ✓ All overflow cells have ellipsis');
    } else {
        console.log('  ℹ No cells with overflow:hidden found');
    }

    console.log('\n--- UI-066: Placeholder Rows ---');
    console.log('  (Placeholder rows appear during loading - check manually)');

    console.log('\n--- UI-067: Filter Dropdown Height ---');
    console.log(`  Search input height: ${domInfo.searchInputHeight}px`);
    console.log(`  Dropdown height: ${domInfo.dropdownHeight}px`);
    if (domInfo.searchInputHeight > 0 && domInfo.dropdownHeight > 0) {
        const diff = Math.abs(domInfo.searchInputHeight - domInfo.dropdownHeight);
        console.log(`  Height difference: ${diff}px ${diff <= 2 ? '✓ Match' : '⚠ Mismatch'}`);
    } else {
        console.log('  ℹ Could not measure both elements');
    }

    console.log('\n--- UI-068: Resize Handles ---');
    console.log(`  Resize handles found: ${domInfo.resizeHandles}`);
    if (domInfo.resizeHandles > 0) {
        console.log('  ✓ Resize handles exist in DOM');
    } else {
        console.log('  ⚠ No resize handles found (may be hidden until hover)');
    }

    console.log('\n--- UI-069: QA + Edit Icon Overlap ---');
    console.log(`  QA flagged cells: ${domInfo.qaFlagged}`);
    console.log(`  Edit icons: ${domInfo.editIcons}`);
    console.log('  (Check screenshot for visual overlap)');

    // Hover tests for resize handle visibility
    if (domInfo.headerCells > 0) {
        await page.locator('.header-cell').first().hover();
        await page.waitForTimeout(300);
        await page.screenshot({ path: '/tmp/medium_02_header_hover.png' });
        console.log('\n  Screenshot: /tmp/medium_02_header_hover.png (check resize handle on hover)');
    }

    // Hover test for edit icon
    if (domInfo.targetCells > 0) {
        await page.locator('.cell.target').first().hover();
        await page.waitForTimeout(300);
        await page.screenshot({ path: '/tmp/medium_03_cell_hover.png' });
        console.log('  Screenshot: /tmp/medium_03_cell_hover.png (check edit icon on hover)');
    }

    console.log('\n=== SUMMARY ===');
    console.log(`Grid loaded: ${domInfo.rows > 0 ? 'YES' : 'NO'} (${domInfo.rows} rows, ${domInfo.cells} cells)`);
    console.log('See screenshots in /tmp/medium_*.png for visual verification');
    console.log('=== DONE ===');
});
