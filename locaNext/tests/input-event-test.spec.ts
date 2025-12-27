import { test, expect } from '@playwright/test';

test.describe('Input Event Test', () => {
  test('verify input events fire', async ({ page }) => {
    test.setTimeout(60000);

    // Setup console log capture
    const consoleLogs: string[] = [];
    page.on('console', msg => {
      const text = msg.text();
      consoleLogs.push(text);
      if (text.includes('searchTerm') || text.includes('input') || text.includes('Native')) {
        console.log(`[BROWSER] ${text}`);
      }
    });

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

    console.log('\n=== TESTING INPUT EVENTS ===');

    // Add event listener to track what events fire
    await page.evaluate(() => {
      const input = document.querySelector('input[placeholder*="Search"]');
      if (input) {
        ['input', 'change', 'keydown', 'keyup', 'keypress'].forEach(eventType => {
          input.addEventListener(eventType, (e: any) => {
            console.log(`EVENT: ${eventType}, value: "${e.target?.value}"`);
          });
        });
        console.log('Event listeners attached to search input');
      } else {
        console.log('Search input not found!');
      }
    });

    // Get the search input
    const searchInput = page.locator('input[placeholder*="Search"]');

    // Method 1: Try focus + keyboard
    console.log('\n--- Method 1: focus + keyboard ---');
    await searchInput.focus();
    await page.waitForTimeout(200);
    await page.keyboard.press('T');
    await page.waitForTimeout(100);
    await page.keyboard.press('e');
    await page.waitForTimeout(100);
    await page.keyboard.press('s');
    await page.waitForTimeout(100);
    await page.keyboard.press('t');
    await page.waitForTimeout(500);

    let val1 = await searchInput.inputValue();
    console.log(`After keyboard: "${val1}"`);
    await page.screenshot({ path: '/tmp/input_test_1.png' });

    // Method 2: Clear and use type()
    console.log('\n--- Method 2: type() ---');
    await searchInput.clear();
    await page.waitForTimeout(200);
    await searchInput.type('Hello', { delay: 50 });
    await page.waitForTimeout(500);

    let val2 = await searchInput.inputValue();
    console.log(`After type(): "${val2}"`);
    await page.screenshot({ path: '/tmp/input_test_2.png' });

    // Method 3: pressSequentially via locator
    console.log('\n--- Method 3: pressSequentially ---');
    await searchInput.clear();
    await page.waitForTimeout(200);
    await searchInput.pressSequentially('World');
    await page.waitForTimeout(500);

    let val3 = await searchInput.inputValue();
    console.log(`After pressSequentially(): "${val3}"`);
    await page.screenshot({ path: '/tmp/input_test_3.png' });

    console.log('\n=== CONSOLE LOGS WITH "searchTerm" ===');
    consoleLogs.filter(l => l.includes('searchTerm')).forEach(l => console.log(l));

    console.log('\n=== SUMMARY ===');
    console.log(`keyboard result: "${val1}"`);
    console.log(`type() result: "${val2}"`);
    console.log(`pressSequentially result: "${val3}"`);
  });
});
