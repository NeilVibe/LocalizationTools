/**
 * File Explorer CRUD Test - Platform, Project, Folder, File operations
 *
 * Tests create/upload operations in Online mode
 */
import { test, expect } from '@playwright/test';
import * as path from 'path';

const DEV_URL = 'http://localhost:5173';

test.describe('File Explorer CRUD Operations', () => {
  test.beforeEach(async ({ page }) => {
    // Go to app and login
    await page.goto(DEV_URL);
    await page.waitForTimeout(2000);

    // Login
    const loginButton = page.locator('button:has-text("Login")').first();
    if (await loginButton.isVisible()) {
      await loginButton.click();
      await page.waitForTimeout(1000);
    }
    await page.locator('input[placeholder="Enter username"]').fill('admin');
    await page.locator('input[placeholder="Enter password"]').fill('admin123');
    await page.locator('button:has-text("Login")').last().click();
    await page.waitForTimeout(2500);

    // Navigate to Files page
    await page.locator('text=Files').first().click();
    await page.waitForTimeout(1500);
  });

  test('Create Platform', async ({ page }) => {
    // Screenshot before
    await page.screenshot({ path: '/tmp/crud_01_before_platform.png' });

    // Right-click on empty area to get context menu
    await page.locator('.explorer-grid').click({ button: 'right', position: { x: 100, y: 300 } });
    await page.waitForTimeout(500);

    // Screenshot of context menu
    await page.screenshot({ path: '/tmp/crud_02_platform_context.png' });

    // Click "New Platform" if available
    const newPlatformOption = page.locator('.context-menu-item:has-text("New Platform"), .context-item:has-text("New Platform")');
    if (await newPlatformOption.isVisible()) {
      await newPlatformOption.click();
      await page.waitForTimeout(500);

      // Fill platform name
      await page.locator('input[placeholder*="platform"], input[placeholder*="name"]').fill('TestPlatform_' + Date.now());
      await page.locator('button:has-text("Create"), button:has-text("Submit")').click();
      await page.waitForTimeout(1000);
    }

    // Screenshot after
    await page.screenshot({ path: '/tmp/crud_03_after_platform.png' });
    console.log('Platform creation test complete');
  });

  test('Create Project in Platform', async ({ page }) => {
    // Find and enter a platform
    const platformRow = page.locator('.grid-row:has-text("Platform"), .grid-row.platform').first();
    if (await platformRow.isVisible()) {
      await platformRow.dblclick();
      await page.waitForTimeout(1000);

      // Screenshot inside platform
      await page.screenshot({ path: '/tmp/crud_04_inside_platform.png' });

      // Right-click to create project
      await page.locator('.explorer-grid, .grid-body').click({ button: 'right', position: { x: 100, y: 200 } });
      await page.waitForTimeout(500);

      await page.screenshot({ path: '/tmp/crud_05_project_context.png' });

      const newProjectOption = page.locator('.context-menu-item:has-text("New Project"), .context-item:has-text("New Project")');
      if (await newProjectOption.isVisible()) {
        await newProjectOption.click();
        await page.waitForTimeout(500);

        await page.locator('input[placeholder*="project"], input[placeholder*="name"]').fill('TestProject_' + Date.now());
        await page.locator('button:has-text("Create"), button:has-text("Submit")').click();
        await page.waitForTimeout(1000);
      }

      await page.screenshot({ path: '/tmp/crud_06_after_project.png' });
    }
    console.log('Project creation test complete');
  });

  test('Create Folder in Project', async ({ page }) => {
    // Navigate to a project first
    const platformRow = page.locator('.grid-row.platform, .grid-row:has(.item-icon)').first();
    if (await platformRow.isVisible()) {
      await platformRow.dblclick();
      await page.waitForTimeout(1000);
    }

    const projectRow = page.locator('.grid-row.project, .grid-row:has-text("Project")').first();
    if (await projectRow.isVisible()) {
      await projectRow.dblclick();
      await page.waitForTimeout(1000);

      // Screenshot inside project
      await page.screenshot({ path: '/tmp/crud_07_inside_project.png' });

      // Right-click to create folder
      await page.locator('.explorer-grid, .grid-body').click({ button: 'right', position: { x: 100, y: 200 } });
      await page.waitForTimeout(500);

      await page.screenshot({ path: '/tmp/crud_08_folder_context.png' });

      const newFolderOption = page.locator('.context-menu-item:has-text("New Folder"), .context-item:has-text("New Folder")');
      if (await newFolderOption.isVisible()) {
        await newFolderOption.click();
        await page.waitForTimeout(500);

        // Fill folder name
        const folderInput = page.locator('input[placeholder*="folder"], input[placeholder*="name"]');
        if (await folderInput.isVisible()) {
          await folderInput.fill('TestFolder_' + Date.now());
          await page.locator('button:has-text("Create"), button:has-text("Submit")').click();
          await page.waitForTimeout(1000);
        }
      }

      await page.screenshot({ path: '/tmp/crud_09_after_folder.png' });
    }
    console.log('Folder creation test complete');
  });

  test('Upload File to Project', async ({ page }) => {
    // Navigate to a project
    const platformRow = page.locator('.grid-row.platform').first();
    if (await platformRow.isVisible()) {
      await platformRow.dblclick();
      await page.waitForTimeout(1000);
    }

    const projectRow = page.locator('.grid-row.project').first();
    if (await projectRow.isVisible()) {
      await projectRow.dblclick();
      await page.waitForTimeout(1000);

      // Screenshot before upload
      await page.screenshot({ path: '/tmp/crud_10_before_upload.png' });

      // Create a test file to upload
      const testFilePath = '/tmp/test_upload.txt';
      const fs = require('fs');
      fs.writeFileSync(testFilePath, 'EN\tKO\nHello\t안녕하세요\nWorld\t세계');

      // Find upload button or use file input
      const fileInput = page.locator('input[type="file"]').first();
      if (await fileInput.count() > 0) {
        await fileInput.setInputFiles(testFilePath);
        await page.waitForTimeout(2000);
      }

      await page.screenshot({ path: '/tmp/crud_11_after_upload.png' });
    }
    console.log('File upload test complete');
  });
});
