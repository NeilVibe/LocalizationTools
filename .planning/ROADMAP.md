# Roadmap: LocaNext v6.0 Architecture & Code Quality

## Overview

Refactor the LocaNext codebase for long-term maintainability. Split God components (VirtualGrid 4299 lines, FilesPage 3080 lines) and backend services (mega_index 1310 lines), thin route handlers, add unit test infrastructure, and fix known UI issues. Backend decomposition first (unblocks route thinning and tests), then frontend decomposition, then verification.

## Phases

- [ ] **Phase 56: Backend Service Decomposition** - Split mega_index, codex_service, and gamedata_context_service into focused modules
- [ ] **Phase 57: Route Thinning** - Extract business logic from files.py and sync.py into dedicated services
- [ ] **Phase 58: VirtualGrid Decomposition** - Split 4299-line God component into 5 focused modules
- [ ] **Phase 59: FilesPage Decomposition + UI Fixes** - Split FilesPage into 3 modules, fix right-click and audit issues
- [ ] **Phase 60: Test Infrastructure + Regression Verification** - Unit tests for new backend modules, component test structure, full regression check

## Phase Details

### Phase 56: Backend Service Decomposition
**Goal**: Backend services are cleanly separated into single-responsibility modules that maintain identical API behavior
**Depends on**: Nothing (first phase)
**Requirements**: SVC-01, SVC-02, SVC-03
**Success Criteria** (what must be TRUE):
  1. mega_index.py is replaced by three files (builder.py, indexes.py, lookup.py) each under 500 lines, and all existing imports resolve without error
  2. codex_service.py is split into entity_registry and search modules, and Codex API endpoints return identical responses
  3. gamedata_context_service.py is split into reverse_index and crossref_resolver modules, and Game Dev context panel still renders cross-references
  4. DEV server starts without errors and all 4 Codex pages load correctly
**Plans**: TBD

Plans:
- [ ] 56-01: TBD
- [ ] 56-02: TBD
- [ ] 56-03: TBD

### Phase 57: Route Thinning
**Goal**: Route handlers contain only HTTP concerns (parse request, call service, return response) with business logic in dedicated service modules
**Depends on**: Phase 56
**Requirements**: ROUTE-01, ROUTE-02
**Success Criteria** (what must be TRUE):
  1. files.py route file is under 400 lines with file validation, TM registration, and merge coordination extracted to service modules
  2. sync.py route file is under 400 lines with sync logic extracted to a service module
  3. All file upload, merge, and sync API endpoints return identical responses as before extraction
**Plans**: TBD

Plans:
- [ ] 57-01: TBD
- [ ] 57-02: TBD

### Phase 58: VirtualGrid Decomposition
**Goal**: VirtualGrid is split into focused, independently maintainable components without any change in grid behavior
**Depends on**: Nothing (independent of backend phases)
**Requirements**: COMP-01
**Success Criteria** (what must be TRUE):
  1. VirtualGrid.svelte is replaced by 5 modules (virtual scroll, search/filter, cell editing, TM leverage, QA layer) each under 800 lines
  2. Language Data grid renders, scrolls, searches, filters, and edits identically to the monolithic version
  3. TM suggestions appear in cells and QA badges display inline -- both verified with Playwright screenshots
  4. No new Svelte warnings or runtime errors in browser console
**Plans**: TBD

Plans:
- [ ] 58-01: TBD
- [ ] 58-02: TBD

### Phase 59: FilesPage Decomposition + UI Fixes
**Goal**: FilesPage is split into focused modules and known UI bugs are resolved
**Depends on**: Nothing (independent of other phases)
**Requirements**: COMP-02, UIFIX-01, UIFIX-02
**Success Criteria** (what must be TRUE):
  1. FilesPage.svelte is split into explorer navigation, context menu operations, and upload manager -- each a separate component
  2. Right-click on file explorer panel opens a working context menu with correct actions
  3. AudioContext residue warning is eliminated and AI capabilities 404 is handled gracefully (no console errors)
  4. File upload, folder navigation, and context menu operations all work identically to before the split
**Plans**: TBD

Plans:
- [ ] 59-01: TBD
- [ ] 59-02: TBD

### Phase 60: Test Infrastructure + Regression Verification
**Goal**: New backend modules have unit test coverage and all split components are verified to maintain identical behavior
**Depends on**: Phase 56, Phase 57, Phase 58, Phase 59
**Requirements**: TEST-01, TEST-02, TEST-03, COMP-03
**Success Criteria** (what must be TRUE):
  1. conftest.py exists with mock DB fixtures and test helper utilities for backend service tests
  2. At least 30 unit test cases pass covering mega_index (builder + lookup), codex_service, and gamedata_context_service modules
  3. Component test structure exists for split Svelte components with at least one test file per split component
  4. Playwright smoke test visits all 11 pages and confirms no regressions from the decomposition work
  5. All 834 existing API E2E tests still pass
**Plans**: TBD

Plans:
- [ ] 60-01: TBD
- [ ] 60-02: TBD
- [ ] 60-03: TBD

## Progress

**Execution Order:**
Phases 56 → 57 (depends on 56). Phases 58, 59 can run in parallel with 56-57. Phase 60 runs last.

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 56. Backend Service Decomposition | v6.0 | 0/3 | Not started | - |
| 57. Route Thinning | v6.0 | 0/2 | Not started | - |
| 58. VirtualGrid Decomposition | v6.0 | 0/2 | Not started | - |
| 59. FilesPage Decomposition + UI Fixes | v6.0 | 0/2 | Not started | - |
| 60. Test Infrastructure + Regression Verification | v6.0 | 0/3 | Not started | - |
