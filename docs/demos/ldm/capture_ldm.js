const { chromium } = require('playwright');

async function captureLDM() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 }
  });
  const page = await context.newPage();

  const baseDir = '/home/neil1988/LocalizationTools/docs/demos';

  try {
    // 1. Go to main page
    console.log('1. Navigating to main page...');
    await page.goto('http://localhost:5173/', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);
    await page.screenshot({ path: `${baseDir}/ldm_01_homepage.png` });
    console.log('   Saved: ldm_01_homepage.png');

    // 2. Click on Apps dropdown
    console.log('2. Opening Apps menu...');
    await page.click('text=Apps');
    await page.waitForTimeout(1000);
    await page.screenshot({ path: `${baseDir}/ldm_02_apps_menu.png` });
    console.log('   Saved: ldm_02_apps_menu.png');

    // 3. Click on LDM
    console.log('3. Selecting LDM...');
    await page.click('text=LDM');
    await page.waitForTimeout(3000);
    await page.screenshot({ path: `${baseDir}/ldm_03_ldm_main.png` });
    console.log('   Saved: ldm_03_ldm_main.png');

    // 4. Try to click "New Project" if visible
    console.log('4. Looking for New Project button...');
    const newProjectBtn = page.locator('text=New Project').first();
    if (await newProjectBtn.isVisible()) {
      await newProjectBtn.click();
      await page.waitForTimeout(2000);
      await page.screenshot({ path: `${baseDir}/ldm_04_new_project.png` });
      console.log('   Saved: ldm_04_new_project.png');
    }

    console.log('\nDone! Screenshots saved to:', baseDir);

  } catch (error) {
    console.error('Error:', error.message);
    await page.screenshot({ path: `${baseDir}/ldm_error.png` });
  } finally {
    await browser.close();
  }
}

captureLDM();
