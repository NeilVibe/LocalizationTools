# Testing Patterns

**Analysis Date:** 2026-03-14

## Test Framework

**Runner:**
- Playwright (`@playwright/test` v1.57.0)
- Config: `playwright.config.ts`

**Assertion Library:**
- Playwright's built-in expect API

**Run Commands:**
```bash
npm test                    # Run all tests headless
npm run test:headed         # Run with browser UI visible
npm run test:ui             # Interactive test runner
npm run test:report         # Show HTML report of last run
```

## Test File Organization

**Location:**
- All tests in `/locaNext/tests/` directory (parallel to `/src/`)
- NOT co-located with source code

**Naming:**
- Descriptive names with `.spec.ts` extension
- Examples: `navigation.spec.ts`, `api-integration.spec.ts`, `tm-debug-test.spec.ts`

**Structure:**
```
locaNext/
├── src/
│   ├── lib/
│   ├── routes/
│   └── ...
└── tests/
    ├── navigation.spec.ts
    ├── api-integration.spec.ts
    ├── tm-debug-test.spec.ts
    └── ... (40+ test files)
```

## Test Structure

**Suite Organization:**
```typescript
import { test, expect, Page } from '@playwright/test';

test.describe('Feature Name', () => {
  test.beforeEach(async ({ page }) => {
    // Setup: login, navigate, etc.
    await login(page);
  });

  test('should do X', async ({ page }) => {
    // Arrange
    // Act
    // Assert
  });
});
```

**Patterns:**

**Setup/Teardown:**
- `test.beforeEach()` for per-test setup (login, navigation)
- `test.beforeAll()` for one-time setup (get token)
- No explicit teardown needed (Playwright cleans up pages)

**Assertion pattern:**
```typescript
await expect(page.locator('.login-container')).not.toBeVisible({ timeout: 10000 });
expect(response.ok()).toBeTruthy();
expect(body.status).toBe('healthy');
```

**Example from `navigation.spec.ts`:**
```typescript
test.describe('Main Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('should show Welcome page after login', async ({ page }) => {
    await expect(page.locator('.main-container')).toBeVisible();
  });
});
```

## Mocking

**Framework:**
- No explicit mocking library (interceptResponse for API mocking)

**Patterns:**
```typescript
// Intercept and wait for API response
const loginPromise = page.waitForResponse(response =>
  response.url().includes('/auth/login') && response.status() === 200
);

await page.getByLabel('Username').fill('admin');
await page.getByLabel('Password').fill('admin123');
await page.getByRole('button', { name: /login/i }).click();

const response = await loginPromise;
const body = await response.json();
expect(body.access_token).toBeDefined();
```

**What to Mock:**
- HTTP responses (via `waitForResponse`)
- LocalStorage via `page.evaluate()`

**What NOT to Mock:**
- Database — tests run against real backend
- File system — tests use real temp directories
- Real API calls — backend servers run during tests (see `webServer` in config)

## Fixtures and Factories

**Test Data:**
```typescript
// Helper function pattern - not formal fixtures
async function login(page: Page) {
  await page.goto('/');
  await page.evaluate(() => localStorage.clear());
  await page.reload();

  await page.getByLabel('Username').fill('admin');
  await page.getByLabel('Password').fill('admin123');
  await page.getByRole('button', { name: /login/i }).click();

  await expect(page.locator('.login-container')).not.toBeVisible({ timeout: 10000 });
}
```

**Location:**
- Inline in test files as helper functions
- Repeated across multiple test files (duplication visible in `navigation.spec.ts`, `api-integration.spec.ts`, etc.)
- Could be refactored to `tests/fixtures.ts` (currently not done)

## Coverage

**Requirements:** None enforced

**View Coverage:**
- Not configured in `playwright.config.ts`
- Tests focus on E2E scenarios, not code coverage metrics

## Test Types

**Unit Tests:**
- NOT present in codebase (no Jest or Vitest setup)
- Only E2E tests via Playwright

**Integration Tests:**
- Primary test type
- Test frontend communicates with live backend API
- Examples: `api-integration.spec.ts` tests login, tool health checks, token storage

**E2E Tests:**
- Framework: Playwright
- Scope: Full user workflows from login through tool interaction
- Browser: Chromium (Desktop Chrome device preset)
- Examples: `navigation.spec.ts` tests navigation across pages, `tm-debug-test.spec.ts` tests TM workflow

## Common Patterns

**Async Testing:**
```typescript
// Wait for async operation to complete
await page.waitForTimeout(1000);  // Fixed wait (not ideal but common)
await expect(element).toBeVisible({ timeout: 10000 });  // Smart wait
await page.waitForResponse(r => r.url().includes('/api/'));  // Wait for specific API
```

**Error Testing:**
```typescript
test('should reject invalid credentials', async ({ request }) => {
  const response = await request.post('http://localhost:8888/api/v2/auth/login', {
    data: {
      username: 'wronguser',
      password: 'wrongpass'
    }
  });

  expect(response.ok()).toBeFalsy();
});
```

**Conditional execution:**
```typescript
// Check if element exists before interacting (graceful failure)
if (await xlsLink.isVisible({ timeout: 2000 }).catch(() => false)) {
  await xlsLink.click();
}
```

**Screenshot debugging:**
```typescript
await page.screenshot({ path: '/tmp/debug_01_landing.png' });
console.log('Step 1: Landing page');
```

## Playwright Configuration Details

**Config file:** `playwright.config.ts`

**Key settings:**
```typescript
testDir: './tests'                    // All tests in tests/ directory
fullyParallel: true                   // Run tests in parallel
forbidOnly: !!process.env.CI          // Fail if test.only left in code
retries: process.env.CI ? 2 : 0       // Retry failed tests on CI only
workers: process.env.CI ? 1 : undefined // Single worker on CI
reporter: 'html'                      // HTML test report

// Shared browser settings
use: {
  baseURL: 'http://localhost:5173',   // Default navigation URL
  trace: 'on-first-retry',            // Trace failed tests
  screenshot: 'only-on-failure'       // Screenshot failures
}

// Browsers
projects: [
  { name: 'chromium', use: { ...devices['Desktop Chrome'] } }
]

// Start servers before tests
webServer: [
  {
    command: 'cd .. && python3 server/main.py',  // Backend server
    url: 'http://localhost:8888/health',
    timeout: 120 * 1000
  },
  {
    command: 'npm run dev -- --port 5173',       // Frontend dev server
    url: 'http://localhost:5173',
    timeout: 120 * 1000
  }
]
```

## Test Inventory

Major test files (40+ total):

**Authentication & Core:**
- `navigation.spec.ts` — Main nav, page switching, responsive layout
- `api-integration.spec.ts` — Health check, login, token management, API health endpoints

**Feature-Specific:**
- `tm-debug-test.spec.ts`, `tm-manager-screenshot.spec.ts`, `tm-offline-test.spec.ts` — Translation Memory
- `file_explorer_crud.spec.ts`, `file-operations.spec.ts` — File management
- `search-*.spec.ts` — Search functionality
- `websocket-realtime.spec.ts` — Real-time sync
- `sync_*.spec.ts` — Synchronization
- `tm_grid_*.spec.ts`, `tm_clipboard.spec.ts` — Grid and clipboard ops

**UI/UX:**
- `column-resize.spec.ts`, `cell_context_menu.spec.ts` — Grid interactions
- `screenshot.spec.ts`, `verify_colors.spec.ts` — Visual tests
- `background_menu_test.spec.ts` — Context menus

**Workflows:**
- `full-workflow-simulation.spec.ts` — End-to-end scenario
- `frontend-backend-integration.spec.ts` — Full stack integration

---

*Testing analysis: 2026-03-14*
