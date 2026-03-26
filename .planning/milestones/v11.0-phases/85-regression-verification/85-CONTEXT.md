# Phase 85: Regression Verification - Context

**Gathered:** 2026-03-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Confirm all existing E2E/Playwright tests pass after the VirtualGrid decomposition with zero behavior changes. Verify grid editing, selection, scroll, and status display work identically to pre-decomposition. This is a verification-only phase — no new code, no new features.

</domain>

<decisions>
## Implementation Decisions

### Verification approach
- **D-01:** Run all 169 Vitest unit tests — must pass unchanged (already confirmed during Phase 84)
- **D-02:** Run Playwright E2E test suite against DEV server (localhost:5173)
- **D-03:** If any E2E tests fail, fix the decomposed modules (not the tests) — tests define correct behavior
- **D-04:** Manual visual verification in DEV browser for grid operations: editing, selection, scroll, status colors, QA badges, TM badges, context menus, keyboard shortcuts
- **D-05:** No test modifications allowed — if a test fails, the decomposition broke something

### What to verify
- **D-06:** Grid renders rows correctly with tag pills (TagText integration)
- **D-07:** Virtual scroll works smoothly (ScrollEngine)
- **D-08:** Cell selection and keyboard navigation (SelectionManager)
- **D-09:** Inline editing with save/cancel (InlineEditor)
- **D-10:** Status colors and QA badges display correctly (StatusColors)
- **D-11:** Search and filter functionality (SearchEngine)
- **D-12:** Context menu actions (confirm, translate, QA)
- **D-13:** Column resize works
- **D-14:** WebSocket real-time sync (if online mode available)

### Claude's Discretion
- Whether to add new regression tests for decomposition-specific concerns
- How to verify WebSocket sync without a running PostgreSQL

</decisions>

<canonical_refs>
## Canonical References

### Phase 84 artifacts (what was decomposed)
- `locaNext/src/lib/components/ldm/grid/` — All 7 extracted modules
- `locaNext/src/lib/components/ldm/VirtualGrid.svelte` — 383-line orchestrator

### Test files
- `locaNext/tests/` — All Vitest unit tests (169 tests)
- `locaNext/tests/` — Playwright E2E tests (68 spec files)

### Requirements
- `.planning/REQUIREMENTS.md` §GRID-08 — Zero regressions after decomposition

</canonical_refs>

<deferred>
## Deferred Ideas

None — this is the final verification phase of v11.0.

</deferred>

---

*Phase: 85-regression-verification*
*Context gathered: 2026-03-26*
