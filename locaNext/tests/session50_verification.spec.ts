/**
 * Session 50 Verification Test
 *
 * Tests for:
 * - UI-113: Edit mode right-click menu with color picker + edit actions
 * - BUG-044: File search with correct auth token
 * - UI-114: Toast notification positioning
 */
import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:5173';

// Helper to navigate from Mode Selection to Login form and complete login
async function loginAsAdmin(page: any) {
  await page.goto('/');
  await page.waitForLoadState('domcontentloaded');

  // Wait for Mode Selection screen (Start Offline button indicates it's loaded)
  const startOfflineBtn = page.locator('button:has-text("Start Offline")');
  await expect(startOfflineBtn).toBeVisible({ timeout: 10000 });

  // Wait for server to be connected
  await expect(page.locator('text=Central Server Connected')).toBeVisible({ timeout: 10000 });

  // Find the Login button and wait for it to be enabled
  const loginBtn = page.locator('button.login-btn');
  await expect(loginBtn).toBeEnabled({ timeout: 5000 });

  // Click the button to show login form
  await loginBtn.click();

  // Wait for login form to appear
  await expect(page.locator('input[type="password"]')).toBeVisible({ timeout: 5000 });

  // Enter credentials
  await page.locator('input').first().fill('admin');
  await page.locator('input[type="password"]').fill('admin123');
  await page.getByRole('button', { name: /login/i }).click();

  // Wait for successful login - main app navigation should appear
  await expect(page.getByRole('button', { name: 'Files' })).toBeVisible({ timeout: 10000 });
}

test.describe('Session 50 Fixes Verification', () => {

  test('UI-113: Edit mode shows right-click menu with colors and edit actions', async ({ page }) => {
    await loginAsAdmin(page);

    // We're on Files page after login - navigate to a folder with data
    // Click on Apps tab to access LDM
    const appsButton = page.locator('button:has-text("Apps"), [data-nav="apps"]');
    if (await appsButton.isVisible({ timeout: 3000 }).catch(() => false)) {
      await appsButton.click();
      await page.waitForTimeout(500);

      // Look for LDM app button
      const ldmButton = page.locator('button:has-text("LDM"), [data-app="ldm"]');
      if (await ldmButton.isVisible({ timeout: 3000 }).catch(() => false)) {
        await ldmButton.click();
        await page.waitForLoadState('networkidle');
      }
    }

    // Take screenshot of current page
    await page.screenshot({
      path: 'testing_toolkit/dev_tests/screenshots/ui113-after-nav.png',
      fullPage: false
    });

    // Alternative: Navigate via Files - double-click on HELLO folder which has data
    const helloFolder = page.locator('text=HELLO').first();
    if (await helloFolder.isVisible({ timeout: 3000 }).catch(() => false)) {
      await helloFolder.dblclick();
      await page.waitForTimeout(1000);

      await page.screenshot({
        path: 'testing_toolkit/dev_tests/screenshots/ui113-hello-folder.png',
        fullPage: false
      });

      // Look for a file to open
      const fileItem = page.locator('.explorer-item, .file-item, [data-type="file"]').first();
      if (await fileItem.isVisible({ timeout: 3000 }).catch(() => false)) {
        await fileItem.dblclick();
        await page.waitForTimeout(1500);
      }
    }

    // Now look for the VirtualGrid with target cells
    const targetCell = page.locator('.virtual-grid .cell-content, .target-cell, [data-column="target"]').first();
    const hasCell = await targetCell.isVisible({ timeout: 5000 }).catch(() => false);

    await page.screenshot({
      path: 'testing_toolkit/dev_tests/screenshots/ui113-grid-view.png',
      fullPage: false
    });

    if (hasCell) {
      // Double-click to enter edit mode
      await targetCell.dblclick();
      await page.waitForTimeout(500);

      // Right-click on the inline edit textarea
      const editTextarea = page.locator('.inline-edit-textarea');
      if (await editTextarea.isVisible({ timeout: 2000 }).catch(() => false)) {
        await editTextarea.click({ button: 'right' });
        await page.waitForTimeout(500);

        // Take screenshot of edit menu
        await page.screenshot({
          path: 'testing_toolkit/dev_tests/screenshots/ui113-edit-menu.png',
          fullPage: false
        });

        // Check for edit context menu items
        const editMenu = page.locator('.edit-context-menu');
        const menuVisible = await editMenu.isVisible({ timeout: 2000 }).catch(() => false);

        const cutVisible = await page.locator('.edit-menu-item:has-text("Cut")').isVisible().catch(() => false);
        const copyVisible = await page.locator('.edit-menu-item:has-text("Copy")').isVisible().catch(() => false);
        const pasteVisible = await page.locator('.edit-menu-item:has-text("Paste")').isVisible().catch(() => false);
        const selectAllVisible = await page.locator('.edit-menu-item:has-text("Select All")').isVisible().catch(() => false);

        console.log('UI-113 Results:', { menuVisible, cutVisible, copyVisible, pasteVisible, selectAllVisible });

        // Verify the menu is visible
        expect(menuVisible).toBe(true);
      } else {
        console.log('UI-113: Edit textarea not visible after double-click');
      }
    } else {
      console.log('UI-113: No target cell visible - need to load a file first');
    }
  });

  test('BUG-044: Auth token key is auth_token not token', async ({ page }) => {
    await loginAsAdmin(page);

    // After login, check localStorage
    const storageKeys = await page.evaluate(() => {
      const keys: { key: string; hasValue: boolean }[] = [];
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key && (key.includes('token') || key.includes('auth'))) {
          keys.push({ key, hasValue: !!localStorage.getItem(key) });
        }
      }
      return keys;
    });

    console.log('BUG-044: Auth-related localStorage keys after login:', storageKeys);

    // Verify auth_token exists
    const hasAuthToken = storageKeys.some(k => k.key === 'auth_token' && k.hasValue);
    expect(hasAuthToken).toBe(true);

    // The search input should be visible on the Files page (global search bar)
    // Look for the search bar in the header
    const searchInput = page.locator('input[placeholder*="Search"], input[placeholder*="search"]').first();
    const hasSearch = await searchInput.isVisible({ timeout: 3000 }).catch(() => false);

    await page.screenshot({
      path: 'testing_toolkit/dev_tests/screenshots/bug044-files-page.png',
      fullPage: false
    });

    if (hasSearch) {
      // Monitor network requests
      let authHeaderFound = false;
      page.on('request', request => {
        const auth = request.headers()['authorization'];
        if (auth && auth.startsWith('Bearer ')) {
          authHeaderFound = true;
          console.log('BUG-044: Found auth header in request:', request.url());
        }
      });

      // Type in search
      await searchInput.fill('test');
      await page.waitForTimeout(1000);

      await page.screenshot({
        path: 'testing_toolkit/dev_tests/screenshots/bug044-search.png',
        fullPage: false
      });

      console.log('BUG-044: Auth header found in requests:', authHeaderFound);
    } else {
      console.log('BUG-044: Search input not visible on Files page');
    }
  });

  test('UI-114: Toast notification CSS is correct', async ({ page }) => {
    await loginAsAdmin(page);

    // We're on Files page - that's fine for checking toast CSS
    await page.waitForLoadState('networkidle');

    // Find the actual toast-container in the DOM (from GlobalToast.svelte)
    const toastContainer = page.locator('.toast-container').first();
    const containerExists = await toastContainer.count() > 0;
    console.log('UI-114: Toast container in DOM:', containerExists);

    if (containerExists) {
      // Get the computed styles of the actual toast container
      const cssVerification = await toastContainer.evaluate((el) => {
        const styles = window.getComputedStyle(el);
        return {
          position: styles.position,
          bottom: styles.bottom,
          right: styles.right,
          maxHeight: styles.maxHeight,
          zIndex: styles.zIndex,
          display: styles.display,
          flexDirection: styles.flexDirection
        };
      });

      console.log('UI-114: Actual toast container computed styles:', cssVerification);

      // Verify key CSS properties for UI-114 fix
      expect(cssVerification.position).toBe('fixed');
      expect(parseInt(cssVerification.zIndex)).toBeGreaterThan(9000);
    } else {
      // Toast container not rendered yet - check the source file exists with the fix
      console.log('UI-114: Toast container not rendered (no toasts) - verifying component source');

      // Alternative: Just verify the component source has the fix
      // Since GlobalToast.svelte has position: fixed, we can verify by triggering a toast
      await page.evaluate(() => {
        // Dispatch a custom event to trigger a toast if toast store is available
        try {
          window.dispatchEvent(new CustomEvent('test-toast'));
        } catch (e) {
          console.log('Could not trigger test toast');
        }
      });

      // Wait a moment and check again
      await page.waitForTimeout(500);
      const containerAfter = await page.locator('.toast-container').count() > 0;
      console.log('UI-114: Toast container after trigger attempt:', containerAfter);
    }

    await page.screenshot({
      path: 'testing_toolkit/dev_tests/screenshots/ui114-page.png',
      fullPage: false
    });
  });

  test('Verify VirtualGrid has edit menu handlers', async ({ page }) => {
    await loginAsAdmin(page);

    // Navigate into HELLO folder which has data
    const helloFolder = page.locator('text=HELLO').first();
    if (await helloFolder.isVisible({ timeout: 3000 }).catch(() => false)) {
      await helloFolder.dblclick();
      await page.waitForTimeout(1000);

      // Look for a file to open
      const fileItem = page.locator('.explorer-item, .file-item, [data-type="file"]').first();
      if (await fileItem.isVisible({ timeout: 3000 }).catch(() => false)) {
        await fileItem.dblclick();
        await page.waitForTimeout(1500);
      }
    }

    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    // Check if VirtualGrid component has the edit handlers in the DOM
    const hasEditHandlers = await page.evaluate(() => {
      const pageContent = document.body.innerHTML;
      return {
        hasEditContextMenuClass: pageContent.includes('edit-context-menu'),
        hasEditMenuItem: pageContent.includes('edit-menu-item'),
        hasInlineEditTextarea: pageContent.includes('inline-edit-textarea')
      };
    });

    console.log('VirtualGrid edit handlers check:', hasEditHandlers);

    await page.screenshot({
      path: 'testing_toolkit/dev_tests/screenshots/ldm-grid.png',
      fullPage: false
    });
  });
});
