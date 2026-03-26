# Phase 83: Test Infrastructure - Research

**Researched:** 2026-03-26
**Domain:** Vitest + @testing-library/svelte for Svelte 5 component testing
**Confidence:** HIGH

## Summary

Vitest 4.1.1 is fully compatible with the project's Vite 7.x and Svelte 5.46.0 stack. The `@testing-library/svelte` 5.3.1 provides a `/vite` plugin (`svelteTesting`) that auto-configures browser resolve conditions and cleanup, making SvelteKit integration straightforward. The existing 636 lines of `node:assert` + `node:test` tests in `tagDetector.test.mjs` and `tagDetector.e2e.test.mjs` will run under Vitest without modification -- Vitest natively supports `node:assert` and `describe`/`it` from `node:test`.

The critical discovery for Svelte 5 rune testing: test files that need to use runes (`$state`, `$derived`, `$effect`) must use the `*.svelte.test.ts` naming convention. Standard `*.test.ts` files cannot access runes. For this phase, only TagText.svelte component tests need rune-aware processing; tagDetector.js and statusColors are pure functions that need no rune support.

**Primary recommendation:** Install vitest + @testing-library/svelte + jsdom + @vitest/coverage-v8. Create `vitest.config.ts` extending the SvelteKit vite config with the `svelteTesting()` plugin. Use `.test.mjs` glob to capture existing tests and `.test.ts` / `.svelte.test.ts` for new tests. Exclude `*.spec.*` from Vitest (those are Playwright).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Use Vitest as the single test runner for all unit tests (pure JS and Svelte components)
- **D-02:** Existing tagDetector.test.mjs and tagDetector.e2e.test.mjs (636 lines total, using node:assert) run through Vitest first with zero syntax changes -- Vitest supports node:assert natively
- **D-03:** After confirming they pass under Vitest, migrate assertions to Vitest expect() syntax for consistency
- **D-04:** Single command `npm run test:unit` runs everything with coverage via Vitest's built-in c8/istanbul
- **D-05:** Install vitest, @testing-library/svelte, jsdom (environment for component tests)
- **D-06:** vitest.config.ts at locaNext/ root, extending vite.config if needed for Svelte preprocessing
- **D-07:** Test files: `**/*.test.{ts,js,mjs}` glob -- pick up existing .mjs tests AND new .test.ts files
- **D-08:** Svelte 5 runes ($state, $derived, $effect) must work in test environment -- verify with a smoke test
- **D-09:** Existing 375-line test file already covers all 6 patterns -- migration to Vitest syntax is sufficient
- **D-10:** Add mutation-killing assertions: each pattern test must FAIL when the corresponding regex is removed from tagDetector.js (per success criteria #2)
- **D-11:** 6 test cases for TagText.svelte: (1) plain text, (2) pill type class/color, (3) combined color pills, (4) inline hex-tinted styles, (5) mixed text+tag+text DOM order, (6) empty/null input
- **D-12:** DO NOT test tagDetector logic from TagText tests -- mock detectTags if needed
- **D-13:** DO NOT test CSS visual appearance or Svelte reactivity internals
- **D-14:** Extract status->tag-type function from VirtualGrid.svelte (~line 2169) to `src/lib/utils/statusColors.ts`
- **D-15:** VirtualGrid.svelte imports from the new utility (no logic duplication)
- **D-16:** Phase 84 will wrap this seed into the full StatusColors module -- keep the extraction minimal
- **D-17:** Test all 3 states: 'reviewed'->teal, 'translated'->warm-gray, default->gray, plus edge cases

### Claude's Discretion
- Vitest config details (reporters, thresholds, exclude patterns)
- Exact file organization for test files (colocated vs tests/ directory)
- Whether to use @testing-library/svelte's render() or mount() for TagText
- Coverage threshold numbers (reasonable starting point)

### Deferred Ideas (OUT OF SCOPE)
- Full VirtualGrid decomposition testing -- Phase 84-85 scope
- Visual regression testing (screenshot comparison) -- not in v11.0 scope
- Backend Python test infrastructure -- v11.0 is frontend-only
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TEST-01 | Vitest configured for Svelte 5 component testing with jsdom environment | vitest.config.ts pattern verified with official Svelte docs + @testing-library/svelte/vite plugin |
| TEST-02 | @testing-library/svelte installed and working with Svelte 5 runes ($state, $derived, $effect) | Confirmed: `*.svelte.test.ts` naming enables runes; svelteTesting() plugin auto-configures browser conditions |
| TEST-03 | Unit tests for tagDetector.js -- all 6 patterns | Existing 375+261 line tests migrate to Vitest; add mutation-killing assertions per D-10 |
| TEST-04 | Unit tests for TagText.svelte -- pill rendering, combined pills, inline styles | @testing-library/svelte render() + screen queries; mock detectTags for isolation per D-12 |
| TEST-05 | Unit tests for status color logic -- 3-state scheme | Extract getStatusKind() from VirtualGrid.svelte:2170-2177 to statusColors.ts; pure function tests |
| TEST-06 | npm run test:unit script runs all component tests with coverage report | Vitest CLI with @vitest/coverage-v8; exclude `*.spec.*` (Playwright) |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| vitest | 4.1.1 | Test runner | Official Svelte recommendation; shares Vite pipeline; peer dep supports vite ^7.0.0 |
| @testing-library/svelte | 5.3.1 | Component test utilities | Official testing-library; provides `/vite` plugin for SvelteKit |
| jsdom | 29.0.1 | DOM environment | Required for component rendering in Node.js; Vitest jsdom environment |
| @vitest/coverage-v8 | 4.1.1 | Coverage reporting | Built-in V8 coverage; matches vitest version; faster than istanbul |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| @testing-library/jest-dom | 6.9.1 | Extended DOM matchers | `toBeInTheDocument()`, `toHaveClass()`, `toHaveStyle()` -- import in vitest-setup.js |
| @testing-library/user-event | 14.6.1 | User interaction simulation | NOT needed for Phase 83 (no interaction tests); install if Phase 84 needs it |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| @testing-library/svelte | svelte `mount()` directly | mount() is lower-level, no screen queries; testing-library is better for DOM assertions |
| jsdom | happy-dom | happy-dom is faster but less complete; jsdom is safer for first-time setup |
| @vitest/coverage-v8 | @vitest/coverage-istanbul | istanbul is slower; v8 is default recommendation |
| vitest-browser-svelte | @testing-library/svelte | Browser mode is newer, runs real browser; overkill for unit tests, better for Phase 84+ |

**Installation:**
```bash
cd locaNext
npm install -D vitest@^4.1.0 @testing-library/svelte@^5.3.0 @testing-library/jest-dom@^6.9.0 jsdom@^29.0.0 @vitest/coverage-v8@^4.1.0
```

## Architecture Patterns

### Recommended Project Structure
```
locaNext/
  vitest.config.ts              # NEW: Vitest config (separate from vite.config.js)
  vitest-setup.js               # NEW: Setup file (jest-dom matchers)
  src/
    lib/
      utils/
        tagDetector.js           # EXISTING: 160 lines, 6 regex patterns
        colorParser.js           # EXISTING: dependency of tagDetector
        statusColors.ts          # NEW: extracted from VirtualGrid.svelte:2170-2177
      components/
        ldm/
          TagText.svelte         # EXISTING: 90 lines, renders tag pills
          VirtualGrid.svelte     # EXISTING: modify to import statusColors.ts
  tests/
    tagDetector.test.mjs         # EXISTING: 375 lines, migrate to expect() syntax
    tagDetector.e2e.test.mjs     # EXISTING: 261 lines, migrate to expect() syntax
    statusColors.test.ts         # NEW: pure function tests
    TagText.svelte.test.ts       # NEW: component rendering tests (*.svelte.test.ts for rune support)
    *.spec.ts                    # EXISTING: Playwright tests (EXCLUDED from Vitest)
```

### Pattern 1: vitest.config.ts for SvelteKit
**What:** Separate Vitest config that extends the SvelteKit Vite config
**When to use:** Always -- keeps Vitest config isolated from production build
**Example:**
```typescript
// Source: https://svelte.dev/docs/svelte/testing + https://testing-library.com/docs/svelte-testing-library/setup/
import { defineConfig } from 'vitest/config';
import { sveltekit } from '@sveltejs/kit/vite';
import { svelteTesting } from '@testing-library/svelte/vite';

export default defineConfig({
  plugins: [sveltekit(), svelteTesting()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./vitest-setup.js'],
    include: ['tests/**/*.test.{js,mjs,ts}', 'tests/**/*.svelte.test.ts'],
    exclude: ['tests/**/*.spec.*', 'node_modules/**'],
    coverage: {
      provider: 'v8',
      include: ['src/lib/utils/tagDetector.js', 'src/lib/utils/statusColors.ts', 'src/lib/components/ldm/TagText.svelte'],
      reporter: ['text', 'html'],
      thresholds: {
        // Starting point -- increase after baseline established
        statements: 80,
        branches: 70,
        functions: 80,
        lines: 80,
      },
    },
  },
});
```

### Pattern 2: vitest-setup.js
**What:** Setup file for extended DOM matchers
**When to use:** Always -- loaded before every test file
**Example:**
```javascript
// Source: https://testing-library.com/docs/svelte-testing-library/setup/
import '@testing-library/jest-dom/vitest';
```

### Pattern 3: Component Test with @testing-library/svelte
**What:** Render Svelte 5 component and assert DOM output
**When to use:** TagText.svelte tests
**Example:**
```typescript
// TagText.svelte.test.ts
// NOTE: *.svelte.test.ts naming enables rune processing
import { render, screen } from '@testing-library/svelte';
import { expect, test, vi } from 'vitest';
import TagText from '$lib/components/ldm/TagText.svelte';

// Mock detectTags to isolate component rendering from regex logic (D-12)
vi.mock('$lib/utils/tagDetector.js', () => ({
  detectTags: vi.fn(),
  hasTags: vi.fn(),
}));

test('renders plain text when no tags detected', () => {
  const { hasTags } = await import('$lib/utils/tagDetector.js');
  hasTags.mockReturnValue(false);

  render(TagText, { props: { text: 'Hello world' } });
  // ColorText receives the text -- verify it appears in DOM
  expect(screen.getByText('Hello world')).toBeInTheDocument();
});
```

### Pattern 4: Pure Function Test (statusColors)
**What:** Test extracted utility function with standard assertions
**When to use:** statusColors.ts, tagDetector.js
**Example:**
```typescript
// statusColors.test.ts
import { expect, describe, it } from 'vitest';
import { getStatusKind } from '$lib/utils/statusColors';

describe('getStatusKind', () => {
  it('returns teal for reviewed', () => {
    expect(getStatusKind('reviewed')).toBe('teal');
  });
  it('returns teal for approved', () => {
    expect(getStatusKind('approved')).toBe('teal');
  });
  it('returns warm-gray for translated', () => {
    expect(getStatusKind('translated')).toBe('warm-gray');
  });
  it('returns gray for default', () => {
    expect(getStatusKind('unknown')).toBe('gray');
  });
  it('returns gray for undefined', () => {
    expect(getStatusKind(undefined)).toBe('gray');
  });
  it('returns gray for null', () => {
    expect(getStatusKind(null)).toBe('gray');
  });
});
```

### Pattern 5: Mutation-Killing Assertion
**What:** Test that FAILS when the corresponding regex is removed
**When to use:** tagDetector pattern tests (D-10, success criteria #2)
**Example:**
```typescript
// After migrating to expect() syntax, add for each pattern:
describe('braced pattern is essential', () => {
  it('detects {PlayerName} only because braced regex exists', () => {
    const result = detectTags('{PlayerName}');
    // This assertion fails if braced regex is removed:
    // detectTags returns [{text: '{PlayerName}'}] instead of a tag
    expect(result).toHaveLength(1);
    expect(result[0].tag).toBeDefined();
    expect(result[0].tag.type).toBe('braced');
  });
});
```

### Anti-Patterns to Avoid
- **Using `*.svelte.test.ts` for non-rune tests:** Regular `.test.ts` files are fine for pure functions; `*.svelte.test.ts` adds unnecessary Svelte compilation overhead
- **Testing TagText by checking tagDetector output:** Per D-12, mock `detectTags` to isolate component behavior from regex logic
- **Running `vitest` globally from project root:** Always run from `locaNext/` directory; the vitest.config.ts is there
- **Including `*.spec.*` in Vitest:** Those are Playwright tests that need a running browser+server; Vitest would fail on them
- **Testing CSS colors/pixel values:** Per D-13, test class names and style attributes, not computed styles

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| DOM environment | Custom DOM mocking | jsdom via Vitest environment | jsdom handles all DOM APIs needed for Svelte rendering |
| Component mounting | Manual `mount()` + cleanup | @testing-library/svelte `render()` | Auto-cleanup, screen queries, accessibility-first API |
| DOM matchers | Custom `assert.ok(el.classList.contains(...))` | @testing-library/jest-dom | `toBeInTheDocument()`, `toHaveClass()`, `toHaveStyle()` |
| Coverage | Manual line counting | @vitest/coverage-v8 | V8 native coverage, zero instrumentation overhead |
| Svelte preprocessing in tests | Manual svelte.compile() calls | sveltekit() + svelteTesting() plugins | Handled automatically by the Vite plugin pipeline |

**Key insight:** The Vitest + SvelteKit + @testing-library/svelte stack is specifically designed to work together. The `svelteTesting()` plugin automatically adds browser resolve conditions and cleanup -- do not configure these manually.

## Common Pitfalls

### Pitfall 1: Vitest Picks Up Playwright Tests
**What goes wrong:** `npm run test:unit` tries to run `.spec.ts` files, which import from `@playwright/test` and fail
**Why it happens:** Default Vitest include pattern is `**/*.{test,spec}.{js,ts}` -- matches both
**How to avoid:** Explicitly set `include` to only `*.test.*` patterns and `exclude` to `*.spec.*` in vitest.config.ts
**Warning signs:** Import errors mentioning `@playwright/test` in Vitest output

### Pitfall 2: Runes Don't Work in Test Files
**What goes wrong:** `$state is not defined` or similar error in test files
**Why it happens:** Runes only work in files that go through Svelte compilation. Standard `.test.ts` files are not compiled as Svelte
**How to avoid:** Name files that need rune access as `*.svelte.test.ts` (the `.svelte` in the filename triggers Svelte compilation)
**Warning signs:** ReferenceError for `$state`, `$derived`, or `$effect` in test output

### Pitfall 3: $lib Path Alias Not Resolved
**What goes wrong:** `Cannot find module '$lib/utils/tagDetector.js'` in test files
**Why it happens:** `$lib` is a SvelteKit alias -- needs Vite to resolve it
**How to avoid:** Use `sveltekit()` plugin in vitest.config.ts (NOT just `svelte()`). The sveltekit plugin registers the `$lib` alias automatically.
**Warning signs:** Module resolution errors for `$lib/*` imports

### Pitfall 4: Component Tests Fail Without DOM Environment
**What goes wrong:** `document is not defined` when rendering Svelte components
**Why it happens:** Vitest defaults to Node.js environment (no DOM)
**How to avoid:** Set `test.environment: 'jsdom'` in vitest.config.ts
**Warning signs:** ReferenceError for `document`, `window`, or `HTMLElement`

### Pitfall 5: Existing node:assert Tests Fail Under Vitest
**What goes wrong:** Import errors or assertion failures when running existing `.test.mjs` files
**Why it happens:** Vitest supports `node:assert` natively, BUT the import paths in existing tests use relative paths (`../src/lib/utils/tagDetector.js`) which may conflict with Vite's module resolution
**How to avoid:** Existing tests use relative imports (not `$lib`), which Vite resolves normally. Verify by running `npx vitest run tests/tagDetector.test.mjs` before any migration work.
**Warning signs:** Module resolution errors for relative `../src/` paths

### Pitfall 6: Coverage Reports Wrong Files
**What goes wrong:** Coverage includes node_modules, Playwright test files, or irrelevant source files
**Why it happens:** Default coverage scans all files touched during test execution
**How to avoid:** Set `coverage.include` explicitly to only the files being tested: `tagDetector.js`, `statusColors.ts`, `TagText.svelte`
**Warning signs:** Coverage report showing hundreds of files instead of the 3 target files

### Pitfall 7: TagText Tests Depend on ColorText
**What goes wrong:** TagText tests break when ColorText implementation changes
**Why it happens:** TagText delegates plain text segments to ColorText.svelte; if ColorText is not mocked, tests depend on its internals
**How to avoid:** Either: (a) accept this coupling since ColorText is a thin wrapper, OR (b) mock ColorText. Recommendation: accept the coupling -- ColorText is stable and its output is just text rendering. Only mock `detectTags`/`hasTags` per D-12.
**Warning signs:** TagText test failures that trace to ColorText code

## Code Examples

### Extract: statusColors.ts (from VirtualGrid.svelte:2170-2177)
```typescript
// src/lib/utils/statusColors.ts
// Source: VirtualGrid.svelte lines 2169-2177 (verified via Read tool)

/**
 * Map translation status to display tag type.
 * 3-state scheme: teal=confirmed, warm-gray=draft, gray=empty.
 *
 * NOTE: Phase 84 GRID-07 will expand this into a full StatusColors module
 * with hover states and QA badge styling. Keep this minimal.
 */
export function getStatusKind(status: string | undefined | null): string {
  switch (status) {
    case 'approved': return 'teal';
    case 'reviewed': return 'teal';
    case 'translated': return 'warm-gray';
    default: return 'gray';
  }
}
```

### Migration Example: node:assert to Vitest expect()
```typescript
// BEFORE (node:assert):
assert.strictEqual(result.length, 1);
assert.deepStrictEqual(result[0].tag, {
  label: '0', type: 'braced', color: 'blue', raw: '{0}'
});

// AFTER (vitest expect):
expect(result).toHaveLength(1);
expect(result[0].tag).toEqual({
  label: '0', type: 'braced', color: 'blue', raw: '{0}'
});
```

### npm Script
```json
{
  "scripts": {
    "test": "playwright test",
    "test:unit": "vitest run --coverage",
    "test:unit:watch": "vitest"
  }
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| node:test runner | Vitest | Svelte 5 official docs (2024) | Vitest is the official recommendation for Svelte testing |
| @testing-library/svelte alone | + svelteTesting() vite plugin | @testing-library/svelte 5.x | Auto-configures browser conditions + cleanup |
| *.test.ts for all tests | *.svelte.test.ts for rune tests | Svelte 5 (2024) | Required for rune compilation in test files |
| jest-dom with Jest | @testing-library/jest-dom/vitest | jest-dom 6.x | Direct Vitest integration, no adapter needed |

**Deprecated/outdated:**
- `jest` + `svelte-jester`: Replaced by Vitest for Svelte projects
- `@testing-library/svelte` without the `/vite` plugin: Missing auto-cleanup and browser conditions
- Testing runes with standard `.test.ts` files: Must use `.svelte.test.ts` naming

## Open Questions

1. **ColorText mock strategy for TagText tests**
   - What we know: TagText delegates plain text to ColorText.svelte; mocking ColorText adds complexity
   - What's unclear: Whether jsdom renders nested Svelte components correctly in all cases
   - Recommendation: Start WITHOUT mocking ColorText; if tests are flaky, add a mock later

2. **Coverage thresholds baseline**
   - What we know: tagDetector.js has comprehensive existing tests (should be near 100%); TagText and statusColors are new
   - What's unclear: What coverage the 6 TagText test cases will achieve
   - Recommendation: Start with statements: 80%, branches: 70%, functions: 80%, lines: 80%. Adjust after first run.

## Sources

### Primary (HIGH confidence)
- [Svelte Official Testing Docs](https://svelte.dev/docs/svelte/testing) -- vitest.config.ts pattern, *.svelte.test.ts naming, rune support
- [Testing Library Svelte Setup](https://testing-library.com/docs/svelte-testing-library/setup/) -- svelteTesting() plugin, SvelteKit config
- npm registry (verified via `npm view`) -- vitest 4.1.1, @testing-library/svelte 5.3.1, jsdom 29.0.1, @vitest/coverage-v8 4.1.1
- Vitest peer dependencies (verified) -- `vite: ^6.0.0 || ^7.0.0 || ^8.0.0` (compatible with project's vite 7.2.7)
- Existing project files (verified via Read tool) -- vite.config.js, svelte.config.js, package.json, all test files, tagDetector.js, TagText.svelte, VirtualGrid.svelte:2169-2177

### Secondary (MEDIUM confidence)
- [Testing Library Svelte GitHub](https://github.com/testing-library/svelte-testing-library) -- Svelte 5 support status
- [Scott Spence: From JSDOM to Real Browsers](https://scottspence.com/posts/testing-with-vitest-browser-svelte-guide) -- alternative browser-mode approach (not needed for Phase 83)

### Tertiary (LOW confidence)
- None -- all critical claims verified against official sources

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all versions verified against npm registry; peer deps confirmed compatible
- Architecture: HIGH -- vitest.config.ts pattern from official Svelte docs; file patterns verified against existing codebase
- Pitfalls: HIGH -- Playwright/Vitest conflict verified (68 .spec.* files vs 2 .test.* files in tests/); rune naming convention from official docs

**Research date:** 2026-03-26
**Valid until:** 2026-04-26 (stable ecosystem, unlikely to change)
