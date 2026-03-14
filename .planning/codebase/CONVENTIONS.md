# Coding Conventions

**Analysis Date:** 2026-03-14

## Naming Patterns

**Files:**
- Svelte components: PascalCase, `.svelte` extension. Example: `InputModal.svelte`, `TMPage.svelte`
- JavaScript utilities: camelCase, `.js` extension. Example: `logger.js`, `api.js`, `formatters.js`
- Stores: camelCase, `.js` extension. Example: `toastStore.js`, `preferences.js`
- Test files: descriptive names with `.spec.ts` extension. Example: `navigation.spec.ts`, `api-integration.spec.ts`

**Functions:**
- camelCase for all functions. Example: `formatDate()`, `getAuthHeaders()`, `loadTMs()`
- Function names are action-oriented: `load`, `fetch`, `handle`, `create`, `delete`, `activate`
- Async functions: same camelCase convention. Example: `async function loadTMs()`, `async function setEmbeddingEngine()`

**Variables:**
- camelCase for all variables. Example: `selectedTMId`, `tmLoading`, `currentEngine`
- State variables in Svelte 5 use `$state()`. Example: `let tmList = $state([]);`
- Derived values use `$derived()`. Example: `let doubled = $derived(count * 2);`
- Booleans prefixed with `is` or use action names. Example: `isElectron`, `tmLoading`, `showSettings`

**Types:**
- No TypeScript strict typing throughout codebase — uses loose `.js` files with JSDoc comments
- JSDoc used for function documentation, not TypeScript. See `logger.js` for pattern

## Code Style

**Formatting:**
- No formatter configured (no .prettierrc found)
- Manual indentation: 2 spaces per level
- Trailing commas in objects/arrays recommended but not enforced
- Line length varies (no strict limit enforced)

**Linting:**
- No ESLint configuration found
- No formal linting rules enforced
- Code style relies on developer discipline and JSDoc conventions

## Import Organization

**Order:**
1. Framework imports (`svelte`, `svelte/store`)
2. External library imports (`carbon-components-svelte`, `carbon-icons-svelte`)
3. Internal utility/store imports (`$lib/...`)
4. Relative imports (if any)

**Example order from `TMPage.svelte`:**
```javascript
import { createEventDispatcher, onMount } from 'svelte';
import { Slider } from 'carbon-components-svelte';
import { CheckmarkFilled, TrashCan } from 'carbon-icons-svelte';
import { preferences } from '$lib/stores/preferences.js';
import { logger } from '$lib/utils/logger.js';
```

**Path Aliases:**
- `$lib` maps to `/src/lib/`
- Used consistently throughout codebase for imports
- Never use relative `../` paths for cross-module imports

## Error Handling

**Patterns:**
- Try-catch blocks used in async operations. Example in `api.js`:
```javascript
try {
  const response = await fetch(url, { ...options, headers });
  if (response.status === 401) {
    this.clearAuth();
    throw new Error('Unauthorized - please login');
  }
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }
  return await response.json();
} catch (error) {
  console.error('API request failed:', error);
  throw error;
}
```

- Error objects include context: `{ detail: '...', status: ... }`
- HTTP errors check both status code and response body
- No error silencing — errors thrown and logged (via logger or console)
- Component-level try-catch wraps API calls, logs via `logger.error()`

**Response validation:**
- Check `response.ok` for HTTP errors
- Parse JSON error responses: `.json().catch(() => ({ detail: ... }))`
- Handle network failures in offline mode (stores check `typeof window !== 'undefined'`)

## Logging

**Framework:** Custom `logger.js` module (not console directly)

**Patterns:**
- All logging goes through `logger` object with methods: `debug()`, `info()`, `success()`, `warning()`, `error()`, `critical()`
- Specialized methods for domains: `logger.apiCall()`, `logger.apiResponse()`, `logger.file()`, `logger.userAction()`, `logger.performance()`
- Logs include timestamp, level, message, and optional structured data
- Example usage in `TMPage.svelte`:
```javascript
logger.apiCall('/api/ldm/tm', 'GET');
logger.success('TMs loaded', { count: tmList.length });
logger.error('Failed to load TMs', { error: err.message });
```

- Console styling applies color codes (blue for INFO, green for SUCCESS, red for ERROR)
- File output in Electron mode only, separate files for general and error logs

## Comments

**When to Comment:**
- Comment purpose, not mechanism. Example: "UX-001: Load current embedding engine" (from `TMPage.svelte`)
- Use section separators for logical grouping: `// ========================================`
- Reference bug/feature codes: "BUG-016 Task Manager Toast Notifications" (from `toastStore.js`)
- Explain non-obvious business logic or workarounds

**JSDoc/TSDoc:**
- JSDoc comments on functions and exports (not strict TypeScript, but document intent)
- Document parameters: `@param {type} name - description`
- Document return values: `@returns {type} description`
- Example from `api.js`:
```javascript
/**
 * Make an authenticated fetch request
 * @param {string} endpoint - API endpoint (e.g., '/api/ldm/files')
 * @param {Object} options - Fetch options
 * @returns {Promise<Response>}
 */
export async function apiFetch(endpoint, options = {}) {
```

## Function Design

**Size:** Aim for focused functions (50-100 lines for async operations, 20-30 for utilities)

**Parameters:**
- Positional for required params (max 2-3)
- Options object for optional/multiple params: `function apiRequest(endpoint, options = {})`
- Destructuring for clear parameter names

**Return Values:**
- Async functions return Promises
- Sync functions return data directly or objects for multiple values
- Null/undefined for "not found" cases (no throwing expected errors for missing data)
- Error conditions throw exceptions (caller handles with try-catch)

## Module Design

**Exports:**
- Named exports for utilities: `export function formatDate()`, `export const logger = { ... }`
- Default export for singletons: `export default toast;` (from `toastStore.js`)
- Mixed when useful: named + default (logger has both)

**Barrel Files:**
- Not used in current structure
- Each util/store is imported directly by path: `import { logger } from '$lib/utils/logger.js'`

## Svelte 5 Runes (CRITICAL!)

**State declaration:**
- `let count = $state(0);` for reactive state
- `let items = $state([]);` for arrays (mutations auto-tracked)

**Derived values:**
- `let doubled = $derived(count * 2);` for computed properties
- NOT `let doubled = $state(count * 2)` — use derived

**Effects:**
- `$effect(() => { ... })` for side effects
- Do NOT use Svelte 4 syntax: `$:` is invalid in Svelte 5

**Props with bindables:**
- `let { open = $bindable(false), value = $bindable('') } = $props();`
- Props with defaults use destructuring in script block
- `$bindable()` enables two-way binding

**Loops with keys:**
- `{#each items as item (item.id)}` — ALWAYS include key
- Keys must be unique and stable

**Example from `InputModal.svelte`:**
```svelte
<script>
  let { open = $bindable(false), value = $bindable('') } = $props();
  let inputValue = $state('');
  $effect(() => {
    if (open) inputValue = value || '';
  });
</script>
```

---

*Convention analysis: 2026-03-14*
