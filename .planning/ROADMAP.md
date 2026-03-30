# Roadmap: LocaNext

## Milestones

- v1.0 through v9.0 --- Phases 01-79.1 (shipped)
- v10.0 UI Polish + Tag Pill Redesign --- Phases 80-82 (shipped 2026-03-25)
- v11.0 Architecture & Test Infrastructure --- Phases 83-85 (shipped 2026-03-26)
- v12.0 TM Intelligence --- Phases 86-88 (shipped 2026-03-26)
- v13.0 Production Path Resolution --- Phases 89-92 (shipped 2026-03-26)
- **v14.0 Debug & UX Overhaul** --- Phases 93-96 (planning)
- **v15.0 MEGA Graft** --- Phase 98 (shipped 2026-03-29)
- **v16.0 Windows App Polish** --- Phase 99 (planning)

### Phase 99: Svelte 4-to-5 Event Migration
**Goal**: All Svelte 4 on:event patterns migrated to Svelte 5 syntax via AppModal wrapper pattern, isolating Carbon 0.95 compat boundary to one file
**Depends on**: Phase 98
**Requirements**: EVT-01, EVT-02, EVT-03, EVT-04, EVT-05, EVT-06, EVT-07
**Success Criteria** (what must be TRUE):
  1. Zero Svelte 4 `on:event` patterns remain in locaNext/src/ except AppModal.svelte (grep returns 0 matches)
  2. AppModal.svelte wrapper exists, exposing onprimary/onsecondary/onclose callback props
  3. All Carbon Modal buttons (primary/secondary) fire their handlers via AppModal
  4. Carbon Dropdown on:select replaced with bind:selectedId in SearchEngine
  5. Carbon Button on:click replaced with onclick in ProjectSettingsModal
  6. Build succeeds with zero errors, svelte-check passes with zero warnings
**Plans:** 3 plans
Plans:
- [x] 99-01-PLAN.md --- Create AppModal wrapper + migrate Button on:click and Dropdown on:select
- [ ] 99-02-PLAN.md --- Migrate 10 small/medium modal files to AppModal
- [x] 99-03-PLAN.md --- Migrate 4 large app/page files + 10 additional files to AppModal + full codebase verification

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

### Phase 93: Critical Debug Fixes
**Goal**: Zero infinite loops, zero feedback cascades, all v13.0 features verified working in DEV browser
**Depends on**: Nothing (first phase of v14.0)
**Requirements**: DBG-01, DBG-02, DBG-03
**Success Criteria** (what must be TRUE):
  1. `/api/ldm/codex/list/` is called <=5 times on page load (CDP deep monitor verified)
  2. Remote logger does not cascade — 404 errors logged once, not 825x
  3. Grid loads LanguageData file without freezing
  4. Branch+Drive selector shows dropdowns and green/red validation
  5. Image/Audio tabs display specific fallback reasons
  6. TM context search returns AC results on row select
**Plans:** 2 plans
Plans:
- [x] 93-01-PLAN.md --- Fix Codex tabCache $state(Map) infinite loop + remote logger feedback cascade (completed 2026-03-27)
- [ ] 93-02-PLAN.md --- CDP deep monitor verification + human E2E verification of all v13.0 features

### Phase 94: Grid & TM UX Fixes + Demo Blockers
**Goal**: TM page works without crashing, audio chain resolves WEM files, TM upload works, grid default color is neutral
**Depends on**: Phase 93
**Requirements**: TM-04, AUDIO-01, TMUX-01, TMUX-02, TMUX-03
**Success Criteria** (what must be TRUE):
  1. TM page loads without `each_key_duplicate` crash — no duplicate folder entries in tree
  2. Selecting a LanguageData row with a voice event shows WEM audio in Audio tab
  3. D11 (event_to_stringid) is populated from export XMLs with SoundEventName
  4. TM upload completes without infinite spinner — TM appears in list
  5. TM assignment is accessible through a visible UI action
  6. Grid cells default to neutral grey, yellow only on explicit user action
**Plans:** TBD

### Phase 95: Navigation & Merge Redesign
**Goal**: Merge is accessible but not cluttering top navigation
**Depends on**: Phase 94
**Requirements**: NAV-01
**Plans:** TBD

### Phase 96: GameData Category Tabs + Visual Polish
**Goal**: GameData categories display as auto-detected tabs, visual quality moves toward CrimsonDesert.gg
**Depends on**: Phase 95
**Requirements**: GD-01, GD-02
**Plans:** TBD

### Phase 98: MEGA Graft -- MDG/LDE Battle-Tested Techniques
**Goal**: LocaNext GameData uses MapDataGenerator's exact XML sanitizer+virtual root wrapper+dual-pass parsing, LDE's two-tier category mapper+FileName+Korean detection, with all broken features fixed (resize, column toggles, MegaIndex, audio streaming, loading screen, Model2Vec)
**Depends on**: Nothing (independent, new milestone)
**Requirements**: GRAFT-01, GRAFT-02, GRAFT-03, GRAFT-04, GRAFT-05, GRAFT-06, GRAFT-07, GRAFT-08, GRAFT-09
**Success Criteria** (what must be TRUE):
  1. GameData XML parsing uses 5-stage sanitizer + virtual root wrapper identical to MDG core/xml_parser.py
  2. GameData loads files with fake roots (include above root) without error
  3. LDE two-tier category mapper assigns categories to all StringIDs with priority keyword override
  4. FileName column shows .loc.xml stem for each row; Korean detection marks untranslated rows
  5. GameData left panel resize drags correctly in both directions
  6. StringID and Index column toggles actually show/hide columns in Game Dev grid
  7. MegaIndex auto-builds on gamedata load with success/error toast visible
  8. Audio plays via streaming endpoint in EntityCard (no raw wem_path 404)
  9. Professional loading screen with centered progress bar and percentage replaces shimmer skeletons
**Plans:** 5/5 plans complete
Plans:
- [x] 98-01-PLAN.md --- XML sanitizer graft (MDG 5-stage) + virtual root + dual-pass + path validation fix
- [x] 98-02-PLAN.md --- Frontend bug fixes: resize delta, column toggles, audio streaming endpoint
- [x] 98-03-PLAN.md --- Professional loading screen with progress bar replacing shimmer skeletons
- [ ] 98-04-PLAN.md --- LDE category mapper graft + FileName/Korean columns in gamedev grid
- [x] 98-05-PLAN.md --- MegaIndex auto-build on gamedata load with toast notifications

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
**Plans:** 1/1 plans complete
Plans:
- [x] 90-01-PLAN.md --- Path validation endpoint + BranchDriveSelector inline component + GridPage toolbar wiring

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
**Plans:** 2/2 plans complete
Plans:
- [x] 91-01-PLAN.md --- Add fallback_reason to image/audio resolution chains + update frontend tabs to show specific reasons
- [x] 91-02-PLAN.md --- Unit tests for fallback reasons + E2E tests for full LanguageData-to-media chains

### Phase 92: MegaIndex Decomposition
**Goal**: mega_index.py is split into focused domain modules that are independently readable and testable, with zero behavior change
**Depends on**: Phase 91 (chain work may reveal natural module boundaries; splitting after feature work preserves stability during development)
**Requirements**: ARCH-02
**Success Criteria** (what must be TRUE):
  1. mega_index.py is replaced by 5 focused modules (entity parsing, media indexing, cross-reference chains, search/lookup, build orchestrator) with no single module exceeding 400 lines
  2. All existing tests that exercise MegaIndex (E2E mapdata tests, mock gamedata tests, new Phase 91 tests) pass without modification
  3. The public API of MegaIndex (build(), all 35 dict accessors, all lookup methods) remains unchanged -- callers do not need to change imports
**Plans:** 1/1 plans complete
Plans:
- [x] 92-01-PLAN.md --- Mixin decomposition: extract 4 mixin modules (data parsers, entity parsers, builders, API) + helpers, slim mega_index.py to orchestrator

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 93. Critical Debug Fixes | 1/2 | Plan 01 done, Plan 02 E2E pending | -- |
| 94. Grid & TM UX Fixes + Demo Blockers | 0/? | Pending (TM-04, AUDIO-01 added) | -- |
| 95. Navigation & Merge Redesign | 0/? | Pending | -- |
| 96. GameData Category Tabs | 0/? | Pending | -- |
| 98. MEGA Graft | 4/5 | Complete    | 2026-03-28 |
| 99. Svelte 5 Event Migration | 2/3 | Complete    | 2026-03-29 |
| 89. Code Cleanup | 1/1 | Complete | 2026-03-26 |
| 90. Branch+Drive Configuration | 1/1 | Complete | 2026-03-26 |
| 91. Media Path Resolution + E2E Testing | 2/2 | Complete | 2026-03-26 |
| 92. MegaIndex Decomposition | 1/1 | Complete | 2026-03-26 |

### Phase 100: Windows App Bugfix Sprint

**Goal:** Fix 12 issues from PEARL PC Windows app testing. FIX-1 to FIX-4 committed. Case-insensitive MegaIndex done. 8 remaining: multi-language audio, image Korean fallback, StatusPage nav, merge direction, category column, dead Project Settings, About version, About cleanup.
**Requirements**: FIX-1, FIX-2, FIX-3, FIX-4, CASE-INSENSITIVE, BUG-5, BUG-6, BUG-7, BUG-8, BUG-9, BUG-10, BUG-11, BUG-12
**Depends on:** Phase 99
**Plans:** 2/2 plans complete

Plans:
- [x] 100-01-PLAN.md --- Backend: case-insensitive MegaIndex (DONE) + multi-language audio (3 folders EN/KR/ZH) + image Korean text fallback (R1)
- [x] 100-02-PLAN.md --- Frontend: StatusPage enhancement + merge direction fix + category column width+resize + dead Project Settings + About version+cleanup+credits

### Phase 101: QuickTranslate Merge Deep Graft

**Goal:** Merge system works EXACTLY like QuickTranslate — skip identical rows, only transfer corrections, progress feedback, per-row logging, dry run, make_file_writable, transfer scope/category filtering. Fix broken merge (target file not modified). Fix TM spam during editing.
**Requirements**: BUG-13, BUG-14, BUG-15, BUG-16, BUG-19, BUG-21, BUG-22, BUG-23
**Depends on:** Phase 100
**Success Criteria** (what must be TRUE):
  1. Merge ONLY updates rows where target text DIFFERS from correction (identical rows skipped)
  2. Target file is visibly modified after merge — user can see changed translations
  3. Merge modal shows live progress (row count, percentage, match type breakdown)
  4. merge logging uses f-strings with actual values, per-row old→new logged
  5. MergeRequest accepts and enforces transfer_scope, category filter, non_script_only options
  6. make_file_writable() called before any file write operation
  7. Dry run mode available — preview changes before committing
  8. TM suggest does NOT fire during active inline editing
  9. All merge logic matches QuickTranslate core/transfer.py exactly
**Plans:** TBD — needs /gsd:plan-phase 101
