# Phase 83: Test Infrastructure - Context

**Gathered:** 2026-03-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Stand up Vitest + @testing-library/svelte for Svelte 5 component testing. Write unit tests for tagDetector.js (6 patterns), TagText.svelte (pill rendering), and status color logic (3-state scheme). Deliver a single `npm run test:unit` command with coverage. No new features, no refactoring beyond minimal extraction needed for testability.

</domain>

<decisions>
## Implementation Decisions

### Test runner strategy
- **D-01:** Use Vitest as the single test runner for all unit tests (pure JS and Svelte components)
- **D-02:** Existing tagDetector.test.mjs and tagDetector.e2e.test.mjs (636 lines total, using node:assert) run through Vitest first with zero syntax changes — Vitest supports node:assert natively
- **D-03:** After confirming they pass under Vitest, migrate assertions to Vitest expect() syntax for consistency
- **D-04:** Single command `npm run test:unit` runs everything with coverage via Vitest's built-in c8/istanbul

### Vitest + Svelte 5 configuration
- **D-05:** Install vitest, @testing-library/svelte, jsdom (environment for component tests)
- **D-06:** vitest.config.ts at locaNext/ root, extending vite.config if needed for Svelte preprocessing
- **D-07:** Test files: `**/*.test.{ts,js,mjs}` glob — pick up existing .mjs tests AND new .test.ts files
- **D-08:** Svelte 5 runes ($state, $derived, $effect) must work in test environment — verify with a smoke test

### tagDetector.js test scope
- **D-09:** Existing 375-line test file already covers all 6 patterns — migration to Vitest syntax is sufficient
- **D-10:** Add mutation-killing assertions: each pattern test must FAIL when the corresponding regex is removed from tagDetector.js (per success criteria #2)

### TagText.svelte test scope
- **D-11:** 6 test cases: (1) plain text renders unchanged, (2) each pill type renders correct class/color, (3) combined color pills render TWO sibling spans, (4) inline hex-tinted styles present, (5) mixed text+tag+text produces correct DOM order, (6) empty/null input renders without crash
- **D-12:** DO NOT test tagDetector logic from TagText tests — mock detectTags if needed
- **D-13:** DO NOT test CSS visual appearance or Svelte reactivity internals

### Status color logic
- **D-14:** Extract the pure status→tag-type function from VirtualGrid.svelte (~line 2169) to `src/lib/utils/statusColors.ts` as a seed file (~20 lines)
- **D-15:** VirtualGrid.svelte imports from the new utility (no logic duplication)
- **D-16:** Phase 84 will wrap this seed into the full StatusColors module — keep the extraction minimal
- **D-17:** Test all 3 states: 'reviewed'→teal, 'translated'→warm-gray, default→gray, plus edge cases (undefined, null, unknown string)

### Claude's Discretion
- Vitest config details (reporters, thresholds, exclude patterns)
- Exact file organization for test files (colocated vs tests/ directory)
- Whether to use @testing-library/svelte's render() or mount() for TagText
- Coverage threshold numbers (reasonable starting point)

</decisions>

<specifics>
## Specific Ideas

- Existing tagDetector tests are well-structured (375 lines, grouped by pattern type) — preserve this organization during migration
- The e2e test file (tagDetector.e2e.test.mjs) tests full pipeline scenarios — include in Vitest run
- Status color function is currently: `case 'reviewed': return 'teal'; case 'translated': return 'warm-gray'; default: return 'gray'`

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Target files to test
- `locaNext/src/lib/utils/tagDetector.js` — 160 lines, 6 regex patterns (combinedcolor, braced, color, memoq, placeholder, br-exclusion)
- `locaNext/src/lib/components/ldm/TagText.svelte` — 90 lines, renders tag pills from detectTags() output
- `locaNext/src/lib/components/ldm/VirtualGrid.svelte` §2169-2176 — Status color switch/case to extract

### Existing tests (to migrate)
- `locaNext/tests/tagDetector.test.mjs` — 375 lines, node:test runner, all 6 patterns covered
- `locaNext/tests/tagDetector.e2e.test.mjs` — 261 lines, full pipeline scenarios

### Project config
- `locaNext/package.json` — Current deps: svelte ^5.0.0, @sveltejs/kit ^2.0.0, @playwright/test ^1.57.0 (no Vitest yet)

### Architecture docs
- `.planning/REQUIREMENTS.md` §TEST-01 through TEST-06 — Requirement definitions for this phase

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- tagDetector.test.mjs: 375 lines of well-structured tests — migrate, don't rewrite from scratch
- tagDetector.e2e.test.mjs: 261 lines of integration-style tests — include in Vitest run

### Established Patterns
- Tests currently at `locaNext/tests/` directory (not colocated)
- Node.js native test runner with node:assert — Vitest can run these as-is initially
- Playwright tests already exist at locaNext level — Vitest should NOT conflict with @playwright/test

### Integration Points
- statusColors.ts will be imported by VirtualGrid.svelte (replacing inline logic)
- Vitest config must coexist with existing vite.config (SvelteKit project)
- `npm run test:unit` must not interfere with existing `npm run test` (if Playwright uses that)

</code_context>

<deferred>
## Deferred Ideas

- Full VirtualGrid decomposition testing — Phase 84-85 scope
- Visual regression testing (screenshot comparison) — not in v11.0 scope
- Backend Python test infrastructure — v11.0 is frontend-only

</deferred>

---

*Phase: 83-test-infrastructure*
*Context gathered: 2026-03-26*
