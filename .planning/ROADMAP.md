# Roadmap: LocaNext

## Milestones

- ✅ **v1.0 through v9.0** — Phases 01-79.1 (shipped)
- ✅ **v10.0 UI Polish + Tag Pill Redesign** — Phases 80-82 (shipped 2026-03-25)
- 🔄 **v11.0 Architecture & Test Infrastructure** — Phases 83-85 (in progress)

## Archived Milestones

Full details in `.planning/milestones/`:
- `v9.0-ROADMAP.md` / `v9.0-REQUIREMENTS.md`
- `v10.0-ROADMAP.md` / `v10.0-REQUIREMENTS.md`

## Phases

- [ ] **Phase 83: Test Infrastructure** - Stand up Vitest + @testing-library/svelte, write unit tests for tagDetector.js, TagText.svelte, and status color logic
- [ ] **Phase 84: VirtualGrid Decomposition** - Extract 5 composable modules from VirtualGrid.svelte (ScrollEngine, CellRenderer, SelectionManager, InlineEditor, StatusColors)
- [ ] **Phase 85: Regression Verification** - Confirm all existing E2E/Playwright tests pass after decomposition with zero behavior changes

## Phase Details

### Phase 83: Test Infrastructure
**Goal**: Developers can run unit tests for frontend components with a single command
**Depends on**: Nothing (first phase of v11.0)
**Requirements**: TEST-01, TEST-02, TEST-03, TEST-04, TEST-05, TEST-06
**Success Criteria** (what must be TRUE):
  1. `npm run test:unit` runs and exits with code 0, reporting coverage
  2. tagDetector.js all 6 patterns (combinedcolor, braced, color, memoq, placeholder, br-exclusion) each have passing tests that fail when the pattern logic is removed
  3. TagText.svelte pill rendering, combined pills, and inline hex-tinted styles each have passing tests
  4. Status color logic for all 3 states (empty, translated, confirmed) has passing tests
  5. Svelte 5 rune patterns ($state, $derived, $effect) work correctly in the test environment
**Plans:** 2 plans
Plans:
- [ ] 83-01-PLAN.md — Vitest setup, config, existing tagDetector test migration with mutation-killing assertions
- [ ] 83-02-PLAN.md — StatusColors extraction + tests, TagText component tests, full coverage verification

### Phase 84: VirtualGrid Decomposition
**Goal**: VirtualGrid.svelte is decomposed into 5 focused modules, each testable in isolation
**Depends on**: Phase 83
**Requirements**: GRID-02, GRID-03, GRID-04, GRID-05, GRID-06, GRID-07
**Success Criteria** (what must be TRUE):
  1. No single module exceeds 800 lines
  2. ScrollEngine module handles virtual scroll, row height calculation, and viewport management independently
  3. CellRenderer module handles source/target/reference cell rendering with TagText integration
  4. SelectionManager module handles cell selection, keyboard navigation, and multi-select
  5. InlineEditor module handles textarea editing, save/cancel, and keyboard shortcuts
  6. StatusColors module encapsulates the 3-state status scheme, hover states, and QA badge styling
**Plans**: TBD

### Phase 85: Regression Verification
**Goal**: The decomposed grid behaves identically to the original VirtualGrid with zero user-visible changes
**Depends on**: Phase 84
**Requirements**: GRID-08
**Success Criteria** (what must be TRUE):
  1. All existing E2E/Playwright tests pass without modification to test code
  2. Grid editing, selection, scroll, and status display work identically to pre-decomposition behavior in the DEV browser (localhost:5173)
  3. Unit tests added in Phase 83 continue to pass against the decomposed modules
**Plans**: TBD

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 83. Test Infrastructure | 0/2 | Planned | - |
| 84. VirtualGrid Decomposition | 0/? | Not started | - |
| 85. Regression Verification | 0/? | Not started | - |
