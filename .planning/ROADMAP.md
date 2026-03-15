# Roadmap: LocaNext

## Milestones

- v1.0 Demo-Ready CAT Tool (Phases 01-06) -- SHIPPED 2026-03-15
- v2.0 Real Data + Dual Platform (Phases 07-14) -- SHIPPED 2026-03-15
- v3.0 Game Dev Platform + AI Intelligence (Phases 15-21) -- SHIPPED 2026-03-15
- v3.1 Debug + Polish + Svelte 5 Migration (Phases 22-24) -- IN PROGRESS

## Phases

<details>
<summary>v1.0 Demo-Ready CAT Tool (Phases 01-06) -- SHIPPED 2026-03-15</summary>

- [x] Phase 01: Stability Foundation (3/3 plans) -- completed 2026-03-14
- [x] Phase 02: Editor Core (3/3 plans) -- completed 2026-03-14
- [x] Phase 03: TM Workflow (3/3 plans) -- completed 2026-03-14
- [x] Phase 04: Search and AI Differentiators (2/2 plans) -- completed 2026-03-14
- [x] Phase 05: Visual Polish and Integration (2/2 plans) -- completed 2026-03-14
- [x] Phase 05.1: Contextual Intelligence & QA Engine (5/5 plans) -- completed 2026-03-14
- [x] Phase 06: Offline Demo Validation (2/2 plans) -- completed 2026-03-14

</details>

<details>
<summary>v2.0 Real Data + Dual Platform (Phases 07-14) -- SHIPPED 2026-03-15</summary>

- [x] Phase 07: XML Parsing Foundation + Bug Fixes (3/3 plans) -- completed 2026-03-15
- [x] Phase 08: Dual UI Mode (2/2 plans) -- completed 2026-03-15
- [x] Phase 09: Translator Merge (2/2 plans) -- completed 2026-03-15
- [x] Phase 10: Export Pipeline (1/1 plan) -- completed 2026-03-15
- [x] Phase 11: Image & Audio Pipeline (2/2 plans) -- completed 2026-03-15
- [x] Phase 12: Game Dev Merge (2/2 plans) -- completed 2026-03-15
- [x] Phase 13: AI Summaries (2/2 plans) -- completed 2026-03-15
- [x] Phase 14: E2E Validation + CLI (2/2 plans) -- completed 2026-03-15

</details>

<details>
<summary>v3.0 Game Dev Platform + AI Intelligence (Phases 15-21) -- SHIPPED 2026-03-15</summary>

- [x] Phase 15: Mock Gamedata Universe (2/2 plans) -- completed 2026-03-15
- [x] Phase 16: Category Clustering + QA Pipeline (2/2 plans) -- completed 2026-03-15
- [x] Phase 17: AI Translation Suggestions (2/2 plans) -- completed 2026-03-15
- [x] Phase 18: Game Dev Grid + File Explorer (2/2 plans) -- completed 2026-03-15
- [x] Phase 19: Game World Codex (2/2 plans) -- completed 2026-03-15
- [x] Phase 20: Interactive World Map (2/2 plans) -- completed 2026-03-15
- [x] Phase 21: AI Naming Coherence + Placeholders (2/2 plans) -- completed 2026-03-15

</details>

### v3.1 Debug + Polish + Svelte 5 Migration (In Progress)

**Milestone Goal:** Fix all runtime bugs from v3.0 code review, migrate entire frontend from Svelte 4 event patterns to pure Svelte 5 Runes, and polish UI/UX across all v3.0 features.

- [x] **Phase 22: Svelte 5 Migration** - Purge all createEventDispatcher and on: directives, converting VirtualGrid, LDM.svelte, and all v3.0 components to $props callback pattern (completed 2026-03-15)
- [x] **Phase 23: Bug Fixes** - Fix 10 runtime bugs from 3-agent swarm audit plus stale test fixture (completed 2026-03-15)
- [x] **Phase 24: UIUX Polish** - Accessibility attributes, visual consistency, and error state handling across v3.0 features (completed 2026-03-15)

## Phase Details

### Phase 22: Svelte 5 Migration
**Goal**: The entire frontend uses pure Svelte 5 Runes patterns with zero legacy Svelte 4 event dispatching -- making the codebase maintainable and consistent
**Depends on**: Nothing (v3.1 foundation -- clean event model required before fixing bugs that touch the same components)
**Requirements**: SV5-01, SV5-02, SV5-03, SV5-04, SV5-05, SV5-06
**Success Criteria** (what must be TRUE):
  1. VirtualGrid emits row selection, edit, and scroll events via callback props passed through $props, not createEventDispatcher
  2. LDM.svelte receives all child component events (grid, panels, filters) via callback props bound with $props destructuring
  3. All v3.0 components (AISuggestionsTab, QAInlineBadge, CategoryFilter, NamingPanel, CodexSearchBar, MapCanvas) use $props callbacks for parent communication
  4. Searching the codebase for "createEventDispatcher" returns zero results
  5. Searching the codebase for " on:" event directives returns zero results (excluding Carbon component interop where the library requires it)
**Plans:** 3/3 plans complete
Plans:
- [ ] 22-01-PLAN.md — Core grid pipeline: VirtualGrid (20 dispatchers) + LDM.svelte + page consumers
- [ ] 22-02-PLAN.md — TM subsystem + modals: TMDataGrid, TMManager, TMViewer, TMPage + FilePickerDialog, PretranslateModal, AccessControl
- [ ] 22-03-PLAN.md — Remaining on: directives, e.detail cleanup, and codebase-wide zero-count verification

### Phase 23: Bug Fixes
**Goal**: All runtime bugs identified in the v3.0 3-agent swarm audit are fixed -- no crashes, no broken navigation, no infinite loading states
**Depends on**: Phase 22 (event wiring must be stable before fixing component-level bugs that depend on event flow)
**Requirements**: FIX-01, FIX-02, FIX-03, FIX-04, FIX-05, FIX-06, FIX-07, FIX-08, FIX-09, FIX-10, FIX-11, TEST-01
**Success Criteria** (what must be TRUE):
  1. GameDevPage loads files without creating fallback IDs -- error states show meaningful messages instead of silent Date.now() workarounds
  2. Audio playback in CodexEntityDetail falls back to PlaceholderAudio on decode error instead of showing a broken player
  3. Clicking "Navigate to NPC" in MapDetailPanel opens the correct Codex entity page for that NPC
  4. Loading indicators in AISuggestionsTab and NamingPanel clear when debounce timers are cancelled (no infinite spinners)
  5. WorldMapPage tooltip does not appear over the detail panel, and route keys are deduplicated to prevent {#each} crashes
  6. GameDevPage file selection works end-to-end using gamedata/browse and gamedata/columns APIs (no non-existent upload-path endpoint)
**Plans:** 4/4 plans complete
Plans:
- [ ] 23-01-PLAN.md — GameDevPage: remove upload-path call, eliminate Date.now() fallback, fix tree refresh flicker
- [ ] 23-02-PLAN.md — WorldMap + Codex: tooltip suppression, route key dedup, NPC navigation, entity type sorting
- [ ] 23-03-PLAN.md — AI/QA components: audio error fallback, loading state cleanup, QA badge click-outside fix
- [ ] 23-04-PLAN.md — Test fixture update + API testing shell wrapper script

### Phase 24: UIUX Polish
**Goal**: All v3.0 features meet accessibility standards and visual consistency -- no broken layouts, missing fallbacks, or inaccessible controls
**Depends on**: Phase 23 (bugs fixed before polishing the same components)
**Requirements**: UX-01, UX-02, UX-03, UX-04, UX-05
**Success Criteria** (what must be TRUE):
  1. FileExplorerTree folder buttons announce their expand/collapse state to screen readers via aria-expanded
  2. Navigation tab dividers render consistently across all 5 tabs (not just the first tab)
  3. CodexPage card images display PlaceholderImage SVG when the actual image returns 404
  4. PlaceholderImage renders correctly in Chromium-based Electron using div layout instead of foreignObject
  5. MapDetailPanel long text content wraps properly without overflow at all viewport widths
**Plans:** 2/2 plans complete
Plans:
- [ ] 24-01-PLAN.md — Fix all 5 UX requirements: aria-expanded, tab dividers, image fallbacks, PlaceholderImage div layout, text wrapping
- [ ] 24-02-PLAN.md — Skill-driven UIUX review: audit + harden + clarify pass across all v3.0 components

### Phase 25: Comprehensive API E2E Testing
**Goal**: Every API endpoint tested E2E with mock data -- complete CRUD workflows for all 12 subsystems, expanded mock fixtures covering all StaticInfo entity types, br-tag and Korean text round-trip verification
**Depends on:** Phase 24
**Requirements**: TEST-E2E-01 through TEST-E2E-25
**Success Criteria** (what must be TRUE):
  1. All 10 StaticInfo entity types have mock XML files with 10+ entities each
  2. Upload fixtures exist for XML, Excel (EU 14-col), and TXT/TSV formats
  3. Every API endpoint (275 total) has at least one pytest test
  4. br-tag `<br/>` content survives upload -> edit -> export round-trip
  5. Korean Unicode text survives upload -> edit -> export round-trip
  6. TM 5-tier cascade search returns results at appropriate tiers
  7. GameData column detection works for all entity types
  8. Test suite runs headless for overnight autonomous execution
**Plans:** 8/10 plans executed
Plans:
- [ ] 25-01-PLAN.md — Expand mock StaticInfo: questinfo, sceneobjectdata, sealdatainfo, regioninfo + loc.xml files
- [ ] 25-02-PLAN.md — Create upload fixtures: EU 14-col Excel, TXT/TSV, LocStr XML + multilingual language data
- [ ] 25-03-PLAN.md — API test infrastructure: conftest, typed APIClient, assertions, constants
- [ ] 25-04-PLAN.md — Test runner script + pytest configuration for overnight execution
- [ ] 25-05-PLAN.md — Test suite: Health + Auth + Projects + Folders + Files (54 endpoints)
- [ ] 25-06-PLAN.md — Test suite: Rows + TM CRUD + TM Search + TM Entries (42 endpoints)
- [ ] 25-07-PLAN.md — Test suite: GameData + Codex + WorldMap (8 endpoints, all entity types)
- [ ] 25-08-PLAN.md — Test suite: AI Intelligence + Search + QA/Grammar (33 endpoints)
- [ ] 25-09-PLAN.md — Test suite: Merge + Export + Offline + Admin + Tools (93 endpoints)
- [ ] 25-10-PLAN.md — Integration workflows + br-tag/Korean tests + endpoint coverage validation

## Progress

**Execution Order:**
Phases execute in numeric order: 22 -> 23 -> 24 -> 25

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 01. Stability Foundation | v1.0 | 3/3 | Complete | 2026-03-14 |
| 02. Editor Core | v1.0 | 3/3 | Complete | 2026-03-14 |
| 03. TM Workflow | v1.0 | 3/3 | Complete | 2026-03-14 |
| 04. Search and AI Differentiators | v1.0 | 2/2 | Complete | 2026-03-14 |
| 05. Visual Polish and Integration | v1.0 | 2/2 | Complete | 2026-03-14 |
| 05.1. Contextual Intelligence & QA | v1.0 | 5/5 | Complete | 2026-03-14 |
| 06. Offline Demo Validation | v1.0 | 2/2 | Complete | 2026-03-14 |
| 07. XML Parsing Foundation + Bug Fixes | v2.0 | 3/3 | Complete | 2026-03-15 |
| 08. Dual UI Mode | v2.0 | 2/2 | Complete | 2026-03-15 |
| 09. Translator Merge | v2.0 | 2/2 | Complete | 2026-03-15 |
| 10. Export Pipeline | v2.0 | 1/1 | Complete | 2026-03-15 |
| 11. Image & Audio Pipeline | v2.0 | 2/2 | Complete | 2026-03-15 |
| 12. Game Dev Merge | v2.0 | 2/2 | Complete | 2026-03-15 |
| 13. AI Summaries | v2.0 | 2/2 | Complete | 2026-03-15 |
| 14. E2E Validation + CLI | v2.0 | 2/2 | Complete | 2026-03-15 |
| 15. Mock Gamedata Universe | v3.0 | 2/2 | Complete | 2026-03-15 |
| 16. Category Clustering + QA Pipeline | v3.0 | 2/2 | Complete | 2026-03-15 |
| 17. AI Translation Suggestions | v3.0 | 2/2 | Complete | 2026-03-15 |
| 18. Game Dev Grid + File Explorer | v3.0 | 2/2 | Complete | 2026-03-15 |
| 19. Game World Codex | v3.0 | 2/2 | Complete | 2026-03-15 |
| 20. Interactive World Map | v3.0 | 2/2 | Complete | 2026-03-15 |
| 21. AI Naming Coherence + Placeholders | v3.0 | 2/2 | Complete | 2026-03-15 |
| 22. Svelte 5 Migration | 3/3 | Complete    | 2026-03-15 | - |
| 23. Bug Fixes | 4/4 | Complete    | 2026-03-15 | - |
| 24. UIUX Polish | 2/2 | Complete    | 2026-03-15 | - |
| 25. Comprehensive API E2E Testing | 8/10 | In Progress|  | - |
