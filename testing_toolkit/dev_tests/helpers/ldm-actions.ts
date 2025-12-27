/**
 * LDM Actions Helper for Playwright Tests
 *
 * Common LDM UI actions: select project, select file, search, etc.
 */

import { Page, Locator } from '@playwright/test';

/**
 * Select first project in project list
 */
export async function selectFirstProject(page: Page): Promise<void> {
  const projects = await page.$$('.project-item');
  if (projects.length === 0) {
    throw new Error('No projects found');
  }
  await page.click('.project-item >> nth=0');
  await page.waitForTimeout(1000);
}

/**
 * Select first file in file tree
 */
export async function selectFirstFile(page: Page): Promise<void> {
  const treeNodes = await page.$$('.tree-node');
  if (treeNodes.length === 0) {
    throw new Error('No files found in tree');
  }
  await page.click('.tree-node >> nth=0');
  await page.waitForTimeout(5000); // Wait for file to load
}

/**
 * Type in search box (keyboard method - Svelte 5 compatible)
 */
export async function typeSearch(page: Page, searchTerm: string): Promise<void> {
  const searchInput = page.locator('#ldm-search-input, input[placeholder*="Search"]');
  await searchInput.first().focus();
  await page.waitForTimeout(200);

  // Type character by character to ensure events fire
  for (const char of searchTerm) {
    await page.keyboard.type(char, { delay: 50 });
  }

  await page.waitForTimeout(500); // Wait for debounce
}

/**
 * Clear search box
 */
export async function clearSearch(page: Page): Promise<void> {
  const clearButton = page.locator('.bx--search-close');
  if (await clearButton.count() > 0) {
    await clearButton.click();
    await page.waitForTimeout(500);
  }
}

/**
 * Get current row count from UI
 */
export async function getRowCount(page: Page): Promise<number> {
  const countText = await page.textContent('.row-count') || '';
  const match = countText.match(/([\d,]+)/);
  return match ? parseInt(match[1].replace(',', '')) : 0;
}

/**
 * Get visible rows count
 */
export async function getVisibleRowsCount(page: Page): Promise<number> {
  const rows = await page.$$('.virtual-row');
  return rows.length;
}

/**
 * Double-click on target cell to open edit modal
 */
export async function openEditModal(page: Page, rowIndex: number = 0): Promise<void> {
  const targetCells = await page.$$('.cell.target');
  if (targetCells.length <= rowIndex) {
    throw new Error(`Row ${rowIndex} not found`);
  }
  await targetCells[rowIndex].dblclick();
  await page.waitForTimeout(1000);
}

/**
 * Close edit modal
 */
export async function closeEditModal(page: Page): Promise<void> {
  const closeButton = page.locator('.edit-modal .close-button, .modal-close');
  if (await closeButton.count() > 0) {
    await closeButton.click();
    await page.waitForTimeout(500);
  }
}

/**
 * Wait for grid to load
 */
export async function waitForGridLoad(page: Page, timeout: number = 10000): Promise<void> {
  await page.waitForSelector('.virtual-row', { timeout });
}

/**
 * Take labeled screenshot
 */
export async function screenshot(page: Page, label: string): Promise<void> {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  await page.screenshot({ path: `/tmp/test_${label}_${timestamp}.png` });
}
