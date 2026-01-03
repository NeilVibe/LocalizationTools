// @ts-check
import { test, expect } from '@playwright/test';

test.skip('FULL sync flow test', async ({ page }) => {
  // Login
  await page.goto('http://localhost:5173');
  await page.waitForTimeout(2000);
  await page.fill('input[placeholder="Enter your username"]', 'admin');
  await page.fill('input[placeholder="Enter your password"]', 'admin123');
  await page.click('button:has-text("Login")');
  await page.waitForTimeout(3000);
  
  console.log('\n=== STEP 1: Check Online indicator ===');
  const onlineIndicator = page.locator('.sync-status-button, [class*="sync"], [class*="online"]');
  const indicatorCount = await onlineIndicator.count();
  console.log('Found sync indicators:', indicatorCount);
  
  // Take screenshot of main page
  await page.screenshot({ path: '/tmp/sync_test_1_main.png' });
  console.log('Screenshot 1: Main page saved');
  
  console.log('\n=== STEP 2: Navigate to Files ===');
  // Click on Files or navigate
  const filesTab = page.locator('a:has-text("Files"), button:has-text("Files"), [href*="files"]');
  if (await filesTab.count() > 0) {
    await filesTab.first().click();
    await page.waitForTimeout(2000);
    console.log('Clicked Files tab');
  }
  
  await page.screenshot({ path: '/tmp/sync_test_2_files.png' });
  console.log('Screenshot 2: Files page saved');
  
  console.log('\n=== STEP 3: Look for file items ===');
  // Look for any clickable file items
  const fileItems = page.locator('[data-type="file"], .file-item, .explorer-item, [class*="file"]');
  const fileCount = await fileItems.count();
  console.log('File items found:', fileCount);
  
  // Check if TestPlatform or TestProject is visible
  const platformItem = page.locator('text=TestPlatform');
  const projectItem = page.locator('text=TestProject');
  console.log('TestPlatform visible:', await platformItem.count());
  console.log('TestProject visible:', await projectItem.count());
  
  // Try to navigate into TestPlatform
  if (await platformItem.count() > 0) {
    console.log('Double-clicking TestPlatform...');
    await platformItem.dblclick();
    await page.waitForTimeout(1000);
    await page.screenshot({ path: '/tmp/sync_test_3_platform.png' });
  }
  
  // Try to navigate into TestProject
  const projectItem2 = page.locator('text=TestProject');
  if (await projectItem2.count() > 0) {
    console.log('Double-clicking TestProject...');
    await projectItem2.dblclick();
    await page.waitForTimeout(1000);
    await page.screenshot({ path: '/tmp/sync_test_4_project.png' });
  }
  
  console.log('\n=== STEP 4: Right-click to get context menu ===');
  // Find any item to right-click
  const anyItem = page.locator('.explorer-item, .grid-item, [class*="item"]').first();
  if (await anyItem.count() > 0) {
    console.log('Right-clicking item...');
    await anyItem.click({ button: 'right' });
    await page.waitForTimeout(500);
    await page.screenshot({ path: '/tmp/sync_test_5_contextmenu.png' });
    
    // Check for context menu
    const contextMenu = page.locator('.context-menu, [class*="context-menu"], [role="menu"]');
    console.log('Context menu visible:', await contextMenu.count());
    
    // Look for offline sync option
    const offlineOption = page.locator('text=Offline Sync, text=Enable Offline, text=Sync');
    console.log('Offline sync option count:', await offlineOption.count());
  } else {
    console.log('No items found to right-click');
  }
  
  console.log('\n=== STEP 5: Open Sync Dashboard Modal ===');
  const syncButton = page.locator('.sync-status-button');
  if (await syncButton.count() > 0) {
    await syncButton.click();
    await page.waitForTimeout(1000);
    await page.screenshot({ path: '/tmp/sync_test_6_dashboard.png' });
    
    // Check what's in the modal
    const subscriptionItems = page.locator('.subscription-item, .sync-item');
    console.log('Subscription items in modal:', await subscriptionItems.count());
    
    const emptyText = page.locator('text=No items synced');
    console.log('Empty text visible:', await emptyText.count());
  }
  
  console.log('\n=== Test Complete ===');
});
