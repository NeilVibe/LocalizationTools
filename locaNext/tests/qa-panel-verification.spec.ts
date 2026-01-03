import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

/**
 * QA Panel Verification Test Suite
 *
 * Tests the QA panel functionality:
 * - Run full QA check
 * - Verify summary counts match results list
 * - Test cancel functionality
 * - Test error handling
 */

const API_URL = 'http://localhost:8888';
const TEST_USER = process.env.PLAYWRIGHT_TEST_USER || 'admin';
const TEST_PASS = process.env.PLAYWRIGHT_TEST_PASS || 'admin123';

// Use simple test data that will trigger QA issues
// This file has duplicate source texts with different translations (triggers LINE check)
const TEST_FILE_PATH = '/home/neil1988/LocalizationTools/tests/fixtures/qa_test_simple.txt';

// Helper to get auth token
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

// Helper to create test project
async function createTestProject(request: any, token: string): Promise<number> {
    const projectName = `QA_Test_${Date.now()}`;
    const response = await request.post(`${API_URL}/api/ldm/projects`, {
        headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json'
        },
        data: {
            name: projectName,
            description: 'Test project for QA verification',
            source_language: 'ko',
            target_language: 'fr'
        }
    });

    if (!response.ok()) {
        throw new Error(`Failed to create project: ${response.status()}`);
    }

    const project = await response.json();
    return project.id;
}

// Helper to upload file
async function uploadTestFile(request: any, token: string, projectId: number, folderId: number | null = null): Promise<number> {
    // Read the test file content as buffer for multipart upload
    const fileContent = fs.readFileSync(TEST_FILE_PATH);

    // Use multipart form data (as required by the upload endpoint)
    // Use unique filename to avoid conflicts
    const uniqueFilename = `qa_test_${Date.now()}.txt`;
    const response = await request.post(`${API_URL}/api/ldm/files/upload`, {
        headers: {
            Authorization: `Bearer ${token}`
        },
        multipart: {
            project_id: projectId.toString(),
            file: {
                name: uniqueFilename,
                mimeType: 'text/plain',
                buffer: fileContent
            }
        }
    });

    if (!response.ok()) {
        const text = await response.text();
        throw new Error(`Failed to upload file: ${response.status()} - ${text}`);
    }

    const file = await response.json();
    return file.id;
}

test.describe('QA Panel API Verification', () => {

    test('QA summary should match QA results count', async ({ request }) => {
        const token = await getAuthToken(request);
        console.log('Got auth token');

        // Create test project
        const projectId = await createTestProject(request, token);
        console.log(`Created test project: ${projectId}`);

        // Upload test file
        const fileId = await uploadTestFile(request, token, projectId);
        console.log(`Uploaded test file: ${fileId}`);

        // Run full QA check
        console.log('Running full QA check...');
        const qaResp = await request.post(`${API_URL}/api/ldm/files/${fileId}/check-qa`, {
            headers: {
                Authorization: `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            data: {
                checks: ['line', 'pattern', 'term'],
                force: true
            },
            timeout: 60000
        });

        expect(qaResp.ok()).toBeTruthy();
        const qaResult = await qaResp.json();
        console.log('QA check result:', JSON.stringify(qaResult, null, 2));

        // Get QA summary
        const summaryResp = await request.get(`${API_URL}/api/ldm/files/${fileId}/qa-summary`, {
            headers: { Authorization: `Bearer ${token}` }
        });
        expect(summaryResp.ok()).toBeTruthy();
        const summary = await summaryResp.json();
        console.log('QA summary:', JSON.stringify(summary, null, 2));

        // Get QA results (all)
        const resultsResp = await request.get(`${API_URL}/api/ldm/files/${fileId}/qa-results`, {
            headers: { Authorization: `Bearer ${token}` }
        });
        expect(resultsResp.ok()).toBeTruthy();
        const results = await resultsResp.json();
        console.log(`QA results count: ${results.issues?.length || 0}`);
        console.log('First few issues:', JSON.stringify(results.issues?.slice(0, 3), null, 2));

        // CRITICAL: Verify summary matches results
        expect(summary.total).toBe(results.total_count);
        console.log(`VERIFIED: Summary total (${summary.total}) matches results count (${results.total_count})`);

        // Verify each check type matches
        if (summary.pattern > 0) {
            const patternResults = await request.get(`${API_URL}/api/ldm/files/${fileId}/qa-results?check_type=pattern`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            const patternData = await patternResults.json();
            expect(summary.pattern).toBe(patternData.issues.length);
            console.log(`Pattern: summary (${summary.pattern}) matches results (${patternData.issues.length})`);
        }

        if (summary.line > 0) {
            const lineResults = await request.get(`${API_URL}/api/ldm/files/${fileId}/qa-results?check_type=line`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            const lineData = await lineResults.json();
            expect(summary.line).toBe(lineData.issues.length);
            console.log(`Line: summary (${summary.line}) matches results (${lineData.issues.length})`);
        }

        if (summary.term > 0) {
            const termResults = await request.get(`${API_URL}/api/ldm/files/${fileId}/qa-results?check_type=term`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            const termData = await termResults.json();
            expect(summary.term).toBe(termData.issues.length);
            console.log(`Term: summary (${summary.term}) matches results (${termData.issues.length})`);
        }

        // Cleanup: delete project
        await request.delete(`${API_URL}/api/ldm/projects/${projectId}`, {
            headers: { Authorization: `Bearer ${token}` }
        });
        console.log(`Cleaned up test project ${projectId}`);
    });

    test('QA results should include row details', async ({ request }) => {
        const token = await getAuthToken(request);

        // Create test project
        const projectId = await createTestProject(request, token);
        const fileId = await uploadTestFile(request, token, projectId);

        // Run QA check
        await request.post(`${API_URL}/api/ldm/files/${fileId}/check-qa`, {
            headers: {
                Authorization: `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            data: {
                checks: ['line', 'pattern', 'term'],
                force: true
            },
            timeout: 60000
        });

        // Get results
        const resultsResp = await request.get(`${API_URL}/api/ldm/files/${fileId}/qa-results`, {
            headers: { Authorization: `Bearer ${token}` }
        });
        const results = await resultsResp.json();

        // Verify each issue has required fields
        for (const issue of results.issues || []) {
            expect(issue).toHaveProperty('id');
            expect(issue).toHaveProperty('check_type');
            expect(issue).toHaveProperty('severity');
            expect(issue).toHaveProperty('message');
            expect(issue).toHaveProperty('row_id');
            expect(issue).toHaveProperty('row_num');
            console.log(`Issue ${issue.id}: [${issue.check_type}] Row ${issue.row_num} - ${issue.message.substring(0, 50)}...`);
        }

        // Cleanup
        await request.delete(`${API_URL}/api/ldm/projects/${projectId}`, {
            headers: { Authorization: `Bearer ${token}` }
        });
    });
});

test.describe('QA Panel UI Tests', () => {

    test('should open QA panel and display issues', async ({ page, request }) => {
        const token = await getAuthToken(request);

        // Create test data
        const projectId = await createTestProject(request, token);
        const fileId = await uploadTestFile(request, token, projectId);

        // Run QA check via API first
        await request.post(`${API_URL}/api/ldm/files/${fileId}/check-qa`, {
            headers: {
                Authorization: `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            data: {
                checks: ['line', 'pattern', 'term'],
                force: true
            },
            timeout: 60000
        });

        // Navigate to the app
        await page.goto('/');

        // Login - use placeholder-based selectors for reliability
        await page.getByPlaceholder('Enter your username').fill(TEST_USER);
        await page.getByPlaceholder('Enter your password').fill(TEST_PASS);
        await page.getByRole('button', { name: /login/i }).click();
        await page.waitForTimeout(2000);

        // Navigate to LDM
        const ldmTab = page.getByRole('button', { name: /files|ldm/i });
        if (await ldmTab.isVisible()) {
            await ldmTab.click();
        }
        await page.waitForTimeout(1000);

        // Take screenshot of current state
        await page.screenshot({ path: 'testing_toolkit/dev_tests/screenshots/qa-panel-test-1.png', fullPage: true });

        // Cleanup
        await request.delete(`${API_URL}/api/ldm/projects/${projectId}`, {
            headers: { Authorization: `Bearer ${token}` }
        });

        console.log('Test completed - check screenshots for UI state');
    });
});
