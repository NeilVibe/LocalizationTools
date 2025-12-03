# Playwright Guide - Frontend E2E Testing

## Overview

Playwright tests browser interactions **via DOM**, not screenshots.

```typescript
// Finds by label, clicks by role - no screenshots needed!
await page.getByLabel('Username').fill('admin');
await page.getByRole('button', { name: /login/i }).click();
await expect(page.locator('.content')).toBeVisible();
```

---

## Test Locations

```
locaNext/tests/
├── login.spec.ts                    # 10 tests
├── navigation.spec.ts               # 10 tests
├── tools.spec.ts                    # 11 tests
├── api-integration.spec.ts          # 8 tests
├── frontend-backend-integration.spec.ts  # 16 tests
└── screenshot.spec.ts               # 1 utility

adminDashboard/tests/
├── dashboard.spec.ts                # 15 tests
└── telemetry-integration.spec.ts    # 15 tests
```

---

## Running Tests

```bash
# LocaNext (56 tests)
cd locaNext && npm test

# Admin Dashboard (30 tests)
cd adminDashboard && npm test

# With visible browser (debugging)
npm run test:headed

# Interactive UI mode
npm run test:ui

# Single file
npx playwright test login.spec.ts

# Show report
npm run test:report
```

---

## Writing Tests

### Basic Test
```typescript
import { test, expect } from '@playwright/test';

test('should login successfully', async ({ page }) => {
  await page.goto('/');
  await page.getByLabel('Username').fill('admin');
  await page.getByLabel('Password').fill('admin123');
  await page.getByRole('button', { name: /login/i }).click();

  // Verify login worked
  await expect(page.locator('.login-container')).not.toBeVisible({ timeout: 10000 });
});
```

### API Test with Playwright
```typescript
test('should fetch stats from API', async ({ request }) => {
  const response = await request.post('http://localhost:8888/api/v2/auth/login', {
    data: { username: 'admin', password: 'admin123' }
  });
  expect(response.ok()).toBeTruthy();
  const { access_token } = await response.json();
  expect(access_token).toBeTruthy();
});
```

---

## Configuration

`playwright.config.ts`:
```typescript
export default defineConfig({
  testDir: './tests',
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  webServer: [
    { command: 'python3 ../server/main.py', url: 'http://localhost:8888/health' },
    { command: 'npm run dev', url: 'http://localhost:5173' },
  ],
});
```

---

## Screenshots (Optional)

Only for debugging or demos:
```bash
# Capture screenshot
npx playwright test screenshot.spec.ts

# Screenshot saved to locaNext/login-screenshot.png
```
