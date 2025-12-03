import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright configuration for Admin Dashboard E2E tests
 */
export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:5175',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: [
    {
      command: 'cd .. && python3 server/main.py',
      url: 'http://localhost:8888/health',
      reuseExistingServer: true,
      timeout: 120 * 1000,
    },
    {
      command: 'npm run dev -- --port 5175',
      url: 'http://localhost:5175',
      reuseExistingServer: true,
      timeout: 120 * 1000,
    },
  ],
});
