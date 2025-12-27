import { test, expect } from '@playwright/test';

test.describe('Search Debug Tests', () => {
  test('debug search input', async ({ page }) => {
    test.setTimeout(60000);

    // Login
    await page.goto('http://localhost:5173');
    await page.fill('input[placeholder*="username"]', 'admin');
    await page.fill('input[placeholder*="password"]', 'admin123');
    await page.click('button[type="submit"]');
    await page.waitForTimeout(2000);

    // Navigate to LDM
    await page.goto('http://localhost:5173/ldm');
    await page.waitForTimeout(2000);

    // Select project and file
    await page.click('.project-item >> nth=0');
    await page.waitForTimeout(1000);
    await page.click('.tree-node >> nth=0');
    await page.waitForTimeout(5000);

    // Debug: Get info about all inputs
    console.log('=== ALL INPUTS ON PAGE ===');
    const allInputs = await page.$$eval('input', inputs => inputs.map(i => ({
      type: i.type,
      placeholder: i.placeholder,
      className: i.className,
      id: i.id,
      readonly: i.readOnly,
      disabled: i.disabled,
      value: i.value,
      tagName: i.tagName,
      isConnected: i.isConnected
    })));
    allInputs.forEach((inp, idx) => {
      console.log(`Input ${idx}:`, JSON.stringify(inp));
    });

    // Find search input specifically
    console.log('\n=== SEARCH INPUT DETAILS ===');
    const searchDetails = await page.$$eval('input[placeholder*="Search"]', inputs => inputs.map(i => ({
      outerHTML: i.outerHTML.substring(0, 200),
      computedStyle: {
        display: window.getComputedStyle(i).display,
        visibility: window.getComputedStyle(i).visibility,
        pointerEvents: window.getComputedStyle(i).pointerEvents,
        opacity: window.getComputedStyle(i).opacity,
        position: window.getComputedStyle(i).position,
        zIndex: window.getComputedStyle(i).zIndex
      },
      boundingRect: i.getBoundingClientRect()
    })));
    searchDetails.forEach((inp, idx) => {
      console.log(`Search ${idx}:`, JSON.stringify(inp, null, 2));
    });

    // Try to interact with the input
    console.log('\n=== INTERACTION TEST ===');
    const searchInput = page.locator('input[placeholder*="Search"]').first();

    // Check visibility
    const isVisible = await searchInput.isVisible();
    const isEnabled = await searchInput.isEnabled();
    const isEditable = await searchInput.isEditable();
    console.log(`Visible: ${isVisible}, Enabled: ${isEnabled}, Editable: ${isEditable}`);

    // Try to fill
    console.log('Attempting fill...');
    try {
      await searchInput.fill('Test123');
      console.log('Fill succeeded');
    } catch (e) {
      console.log('Fill failed:', e.message);
    }

    const valueAfterFill = await searchInput.inputValue();
    console.log(`Value after fill: "${valueAfterFill}"`);

    await page.screenshot({ path: '/tmp/debug_search.png' });
  });
});
