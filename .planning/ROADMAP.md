# Roadmap: LocaNext

## Milestones

- v1.0 through v9.0 --- Phases 01-79.1 (shipped)
- v10.0 UI Polish + Tag Pill Redesign --- Phases 80-82 (shipped 2026-03-25)
- v11.0 Architecture & Test Infrastructure --- Phases 83-85 (shipped 2026-03-26)
- v12.0 TM Intelligence --- Phases 86-88 (shipped 2026-03-26)
- **v13.0 Production Path Resolution** --- Phases 89-92 (in progress)

## Archived Milestones

Full details in `.planning/milestones/`:
- `v9.0-ROADMAP.md` / `v9.0-REQUIREMENTS.md`
- `v10.0-ROADMAP.md` / `v10.0-REQUIREMENTS.md`

<details>
<summary>v11.0 Architecture & Test Infrastructure (shipped 2026-03-26)</summary>

### Phase 83: Test Infrastructure
**Goal**: Developers can run unit tests for frontend components with a single command
**Depends on**: Nothing (first phase of v11.0)
**Requirements**: TEST-01, TEST-02, TEST-03, TEST-04, TEST-05, TEST-06
**Success Criteria** (what must be TRUE):
  1. `npm run test:unit` runs and exits with code 0, reporting coverage
  2. tagDetector.js all 6 patterns each have passing tests that fail when the pattern logic is removed
  3. TagText.svelte pill rendering, combined pills, and inline hex-tinted styles each have passing tests
  4. Status color logic for all 3 states (empty, translated, confirmed) has passing tests
  5. Svelte 5 rune patterns ($state, $derived, $effect) work correctly in the test environment
**Plans:** 2/2 plans complete
Plans:
- [x] 83-01-PLAN.md --- Vitest setup, config, existing tagDetector test migration with mutation-killing assertions
- [x] 83-02-PLAN.md --- StatusColors extraction + tests, TagText component tests, full coverage verification

### Phase 84: VirtualGrid Decomposition
**Goal**: VirtualGrid.svelte is decomposed into 6 focused modules + thin orchestrator, each testable in isolation
**Depends on**: Phase 83
**Requirements**: GRID-02, GRID-03, GRID-04, GRID-05, GRID-06, GRID-07
**Success Criteria** (what must be TRUE):
  1. No single module exceeds 800 lines
  2. ScrollEngine module handles virtual scroll, row height calculation, and viewport management independently
  3. CellRenderer module handles source/target/reference cell rendering with TagText integration
  4. SelectionManager module handles cell selection, keyboard navigation, and multi-select
  5. InlineEditor module handles textarea editing, save/cancel, and keyboard shortcuts
  6. StatusColors module encapsulates the 3-state status scheme, hover states, and QA badge styling
**Plans:** 3/3 plans complete
Plans:
- [x] 84-01-PLAN.md --- Batch 1: gridState.svelte.ts + ScrollEngine + StatusColors extraction
- [x] 84-02-PLAN.md --- Batch 2: CellRenderer + SelectionManager extraction
- [x] 84-03-PLAN.md --- Batch 3: InlineEditor + SearchEngine extraction, parent slim-down, final verification

### Phase 85: Regression Verification
**Goal**: The decomposed grid behaves identically to the original VirtualGrid with zero user-visible changes
**Depends on**: Phase 84
**Requirements**: GRID-08
**Success Criteria** (what must be TRUE):
  1. All existing E2E/Playwright tests pass without modification to test code
  2. Grid editing, selection, scroll, and status display work identically to pre-decomposition behavior in the DEV browser (localhost:5173)
  3. Unit tests added in Phase 83 continue to pass against the decomposed modules
**Plans**: 1/1 plans complete

</details>

<details>
<summary>v12.0 TM Intelligence (shipped 2026-03-26)</summary>

### Phase 86: Dual Threshold + TM Tab UI
**Goal**: Translators see quality-filtered TM results with clear match percentage indicators at two threshold levels
**Depends on**: Nothing (first phase of v12.0; builds on existing TMTab.svelte and searcher.py)
**Requirements**: TMUI-01, TMUI-02
**Success Criteria** (what must be TRUE):
  1. Right panel TM suggestions only show matches at or above 62% when browsing rows (context threshold)
  2. Pretranslation (batch apply) only uses matches at or above 92% (quality threshold)
  3. Every TM result in the right panel displays a color-coded match percentage badge (green for 92%+, yellow for 75-91%, orange for 62-74%)
  4. Match percentage badge is prominent and immediately visible without hovering or expanding
**Plans:** 1/1 plans complete
Plans:
- [x] 86-01-PLAN.md --- Hardcode 0.62 context threshold in StatusColors, update TMTab color bands and prominent badge

### Phase 87: AC Context Engine
**Goal**: The backend can scan Korean source text against TM entries using a 3-tier cascade (whole AC, line AC, char n-gram Jaccard) in under 100ms
**Depends on**: Phase 86 (threshold constants shared between UI and engine)
**Requirements**: ACCTX-01, ACCTX-03, PERF-01
**Success Criteria** (what must be TRUE):
  1. Aho-Corasick automatons are built from whole_lookup and line_lookup dictionaries when the TM index loads (no separate build step needed)
  2. Character n-gram Jaccard scorer produces correct similarity scores for Korean text using n={2,3,4,5} with space-stripped input
  3. The 3-tier cascade returns results: tier-1 whole-match, tier-2 line-match, tier-3 fuzzy (Jaccard >= 62%)
  4. End-to-end context search completes in under 100ms for a single source text against a TM with 1000+ entries
  5. Unit tests verify each tier independently and the cascade ordering
**Plans:** 2/2 plans complete
Plans:
- [x] 87-01-PLAN.md --- AC automaton build in load_indexes(), ContextSearcher 3-tier cascade, unit tests
- [x] 87-02-PLAN.md --- POST /tm/context endpoint, performance benchmark (<100ms for 1000+ entries)

### Phase 88: AC Context Integration
**Goal**: When a translator selects a row, the right panel shows where the source text appears elsewhere in the TM with match tier and score
**Depends on**: Phase 87
**Requirements**: ACCTX-02, ACCTX-04
**Success Criteria** (what must be TRUE):
  1. Selecting a row in the grid triggers an AC context search on the Korean source text of that row
  2. Context search results appear in the right panel alongside (not replacing) existing TM suggestions
  3. Each result shows a tier indicator (Exact / Line / Fuzzy) and the match score percentage
  4. Results are ordered by tier (exact first) then by score descending within each tier
  5. The right panel updates without perceptible delay when clicking between rows
**Plans:** 1/1 plans complete
Plans:
- [x] 88-01-PLAN.md --- Wire context fetch to row-select with AbortController, display tiered results in TM tab

</details>

## Phases

- [x] **Phase 89: Code Cleanup** - Fix 4 v11.0 code review issues (onScrollToRow race, dead code, missing callbacks, inaccessible state) (completed 2026-03-26)
- [ ] **Phase 90: Branch+Drive Configuration** - Branch/Drive selector UI with path validation and session persistence
- [ ] **Phase 91: Media Path Resolution + E2E Testing** - Wire StringID-to-entity-to-media chains in LanguageData grid with mock Perforce E2E tests
- [ ] **Phase 92: MegaIndex Decomposition** - Split mega_index.py (1310 lines) into 5 focused domain modules

## Phase Details

### Phase 89: Code Cleanup
**Goal**: The 4 deferred v11.0 code review issues are resolved -- no dead code, no race conditions, no inaccessible state in the decomposed grid modules
**Depends on**: Nothing (independent cleanup, first phase of v13.0)
**Requirements**: FIX-01, FIX-02, FIX-03, FIX-04
**Success Criteria** (what must be TRUE):
  1. Clicking a search result in SearchEngine scrolls to the correct row immediately on first click (no silent failures from null delegate)
  2. CellRenderer has no unused $derived computations or dead helper functions (visibleColumns removed)
  3. InlineEditor notifies the parent when a cell save completes (onSaveComplete wired or removed with documented rationale)
  4. TM suggestions from StatusColors are either consumed by parent components or confirmed as internal-only with dead export path removed
**Plans:** 1/1 plans complete
Plans:
- [x] 89-01-PLAN.md --- Fix onScrollToRow race (prop instead of delegate), remove dead code in CellRenderer/InlineEditor/StatusColors

### Phase 90: Branch+Drive Configuration
**Goal**: Users can configure which Perforce branch and drive letter to use for game data lookups, with immediate visual feedback on path availability
**Depends on**: Phase 89 (clean codebase before adding new UI)
**Requirements**: PATH-01, PATH-02, PATH-03, PATH-04
**Success Criteria** (what must be TRUE):
  1. User can select a branch (cd_beta, mainline, cd_alpha, cd_delta, cd_lambda) from a dropdown that is always visible in the UI (not buried in settings)
  2. User can select a drive letter (A-Z) from a dropdown adjacent to the branch selector
  3. After changing branch or drive, a status indicator shows green "PATHS OK" when the configured folders exist on disk, or red "PATHS NOT FOUND" listing which specific folders are missing
  4. Branch and drive selection persists across application restarts without re-configuration
  5. Path validation runs automatically on startup and on every branch/drive change
**Plans**: TBD

### Phase 91: Media Path Resolution + E2E Testing
**Goal**: When a translator selects a LanguageData row, the Image and Audio tabs show the correct game asset by resolving the full chain from StringID through GameData entity to DDS/WEM file, verified by E2E tests against mock Perforce structure
**Depends on**: Phase 90 (branch+drive must be configurable before chains can use configured paths)
**Requirements**: MEDIA-01, MEDIA-02, MEDIA-03, MEDIA-04, MOCK-01, MOCK-02, MOCK-03, MOCK-04
**Success Criteria** (what must be TRUE):
  1. Selecting a LanguageData row with a known entity shows the correct DDS texture thumbnail in the Image tab (chain: StringID -> C7 entity -> C1 UITextureName -> DDS path using configured branch+drive)
  2. Selecting a LanguageData row with a known voice event shows the correct WEM audio in the Audio tab with playback controls (chain: StringID -> C3 event -> WEM path using configured branch+drive)
  3. When image or audio cannot be resolved, the tab shows a specific reason: "Entity not found", "No texture attribute", or "File not on disk" (not a generic error)
  4. E2E tests pass verifying the full image chain (LanguageData row -> StringID -> entity -> DDS thumbnail in ImageTab) against mock Perforce fixtures
  5. E2E tests pass verifying the full audio chain (LanguageData row -> StringID -> entity -> WEM playback in AudioTab) against mock Perforce fixtures with drive-agnostic relative paths
**Plans**: TBD

### Phase 92: MegaIndex Decomposition
**Goal**: mega_index.py is split into focused domain modules that are independently readable and testable, with zero behavior change
**Depends on**: Phase 91 (chain work may reveal natural module boundaries; splitting after feature work preserves stability during development)
**Requirements**: ARCH-02
**Success Criteria** (what must be TRUE):
  1. mega_index.py is replaced by 5 focused modules (entity parsing, media indexing, cross-reference chains, search/lookup, build orchestrator) with no single module exceeding 400 lines
  2. All existing tests that exercise MegaIndex (E2E mapdata tests, mock gamedata tests, new Phase 91 tests) pass without modification
  3. The public API of MegaIndex (build(), all 35 dict accessors, all lookup methods) remains unchanged -- callers do not need to change imports
**Plans**: TBD

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 89. Code Cleanup | 1/1 | Complete    | 2026-03-26 |
| 90. Branch+Drive Configuration | 0/? | Not started | - |
| 91. Media Path Resolution + E2E Testing | 0/? | Not started | - |
| 92. MegaIndex Decomposition | 0/? | Not started | - |
