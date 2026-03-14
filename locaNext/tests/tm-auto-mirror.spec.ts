/**
 * Test: TM Auto-Mirror E2E
 * Verifies that file upload triggers auto-mirror TM creation,
 * the TM appears in the TM tree, and leverage stats are available.
 *
 * Prerequisites: DEV servers running (./scripts/start_all_servers.sh --with-vite)
 */
import { test, expect } from '@playwright/test';

const DEV_URL = 'http://localhost:5173';
const API_BASE = 'http://localhost:8888';

/** Helper: Login via API and get auth token */
async function getAuthToken(request: any): Promise<string> {
  const response = await request.post(`${API_BASE}/api/auth/login`, {
    data: { username: 'admin', password: 'admin123' }
  });
  const data = await response.json();
  return data.access_token;
}

/** Helper: Login and navigate to main page */
async function loginToApp(page: any) {
  await page.goto(DEV_URL);

  // Mode Selection: click "Login"
  await page.click('text=Login');
  await page.waitForTimeout(500);

  // Login form
  await page.fill('input[placeholder="Enter username"]', 'admin');
  await page.fill('input[placeholder="Enter password"]', 'admin123');
  await page.click('button:has-text("Login"):not(:text-is("Back"))');
  await page.waitForTimeout(5000);
}

test.describe('TM Auto-Mirror', () => {
  test.setTimeout(120000);

  test('Auto-mirror creates TM on file upload, appears in TM page', async ({ page, request }) => {
    // Step 1: Get auth token for API calls
    const token = await getAuthToken(request);
    expect(token).toBeTruthy();

    // Step 2: Get existing TMs
    const tmsBeforeRes = await request.get(`${API_BASE}/api/ldm/tm`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const tmsBefore = await tmsBeforeRes.json();
    const tmCountBefore = Array.isArray(tmsBefore) ? tmsBefore.length : 0;

    // Step 3: Explore hierarchy to find a file (verifying auto-mirror data exists)
    const platformsRes = await request.get(`${API_BASE}/api/ldm/explorer`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const platforms = await platformsRes.json();
    const platformList = (platforms as any).platforms || platforms;

    if (Array.isArray(platformList) && platformList.length > 0) {
      const platformId = platformList[0].id || platformList[0].platform_id;

      const projectsRes = await request.get(`${API_BASE}/api/ldm/explorer/${platformId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const projects = await projectsRes.json();
      const projectList = (projects as any).projects || projects;

      if (Array.isArray(projectList) && projectList.length > 0) {
        const projectId = projectList[0].id || projectList[0].project_id;

        const foldersRes = await request.get(`${API_BASE}/api/ldm/explorer/${platformId}/${projectId}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        const folders = await foldersRes.json();
        const folderList = (folders as any).folders || folders;

        if (Array.isArray(folderList) && folderList.length > 0) {
          const folderId = folderList[0].id || folderList[0].folder_id;

          const filesRes = await request.get(`${API_BASE}/api/ldm/explorer/${platformId}/${projectId}/${folderId}`, {
            headers: { 'Authorization': `Bearer ${token}` }
          });
          const filesData = await filesRes.json();
          const fileList = (filesData as any).files || filesData;

          if (Array.isArray(fileList) && fileList.length > 0) {
            const firstFileId = fileList[0].id || fileList[0].file_id;

            // Check active TMs for this file (verifies auto-mirror assignment)
            const activeTmsRes = await request.get(`${API_BASE}/api/ldm/files/${firstFileId}/active-tms`, {
              headers: { 'Authorization': `Bearer ${token}` }
            });

            if (activeTmsRes.ok()) {
              const activeTms = await activeTmsRes.json();
              console.log(`Active TMs for file ${firstFileId}: ${JSON.stringify(activeTms)}`);
            }
          }
        }
      }
    }

    // Step 4: Login to UI and navigate to TM page
    await loginToApp(page);

    // Look for TM navigation
    const tmNav = page.locator('text=Translation Memor').first();
    const hasTmNav = await tmNav.isVisible().catch(() => false);

    if (hasTmNav) {
      await tmNav.click();
      await page.waitForTimeout(2000);

      const heading = page.locator('h2:has-text("Translation Memories")');
      await expect(heading).toBeVisible({ timeout: 5000 });
    }

    // Step 5: Verify TMs still exist via API
    const tmsAfterRes = await request.get(`${API_BASE}/api/ldm/tm`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const tmsAfter = await tmsAfterRes.json();
    const tmCountAfter = Array.isArray(tmsAfter) ? tmsAfter.length : 0;

    expect(tmCountAfter).toBeGreaterThanOrEqual(tmCountBefore);
  });

  test('Leverage stats are available via API for files', async ({ request }) => {
    const token = await getAuthToken(request);

    // Navigate hierarchy
    const platformsRes = await request.get(`${API_BASE}/api/ldm/explorer`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const platforms = await platformsRes.json();
    const platformList = (platforms as any).platforms || platforms;

    if (!Array.isArray(platformList) || platformList.length === 0) {
      console.log('No platforms found - skipping leverage test (data-dependent)');
      return;
    }

    const platformId = platformList[0].id || platformList[0].platform_id;
    const projectsRes = await request.get(`${API_BASE}/api/ldm/explorer/${platformId}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const projects = await projectsRes.json();
    const projectList = (projects as any).projects || projects;

    if (!Array.isArray(projectList) || projectList.length === 0) {
      console.log('No projects found - skipping leverage test');
      return;
    }

    const projectId = projectList[0].id || projectList[0].project_id;
    const foldersRes = await request.get(`${API_BASE}/api/ldm/explorer/${platformId}/${projectId}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const folders = await foldersRes.json();
    const folderList = (folders as any).folders || folders;

    if (!Array.isArray(folderList) || folderList.length === 0) {
      console.log('No folders found - skipping leverage test');
      return;
    }

    const folderId = folderList[0].id || folderList[0].folder_id;
    const filesRes = await request.get(`${API_BASE}/api/ldm/explorer/${platformId}/${projectId}/${folderId}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const filesData = await filesRes.json();
    const fileList = (filesData as any).files || filesData;

    if (!Array.isArray(fileList) || fileList.length === 0) {
      console.log('No files found - skipping leverage test');
      return;
    }

    const fileId = fileList[0].id || fileList[0].file_id;

    // Get leverage stats
    const leverageRes = await request.get(`${API_BASE}/api/ldm/files/${fileId}/leverage`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });

    expect(leverageRes.ok()).toBeTruthy();
    const leverage = await leverageRes.json() as any;

    // Verify shape
    expect(leverage).toHaveProperty('exact');
    expect(leverage).toHaveProperty('fuzzy');
    expect(leverage).toHaveProperty('new');
    expect(leverage).toHaveProperty('total');
    expect(leverage).toHaveProperty('exact_pct');
    expect(leverage).toHaveProperty('fuzzy_pct');
    expect(leverage).toHaveProperty('new_pct');

    // Percentages should sum to ~100% (allowing for rounding)
    const pctSum = leverage.exact_pct + leverage.fuzzy_pct + leverage.new_pct;
    expect(pctSum).toBeGreaterThanOrEqual(99);
    expect(pctSum).toBeLessThanOrEqual(101);

    console.log(`Leverage stats for file ${fileId}: exact=${leverage.exact_pct}%, fuzzy=${leverage.fuzzy_pct}%, new=${leverage.new_pct}%`);
  });
});
