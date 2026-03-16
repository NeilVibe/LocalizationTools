# Roadmap: LocaNext

## Milestones

- v1.0 Demo-Ready CAT Tool (Phases 01-06) -- SHIPPED 2026-03-15
- v2.0 Real Data + Dual Platform (Phases 07-14) -- SHIPPED 2026-03-15
- v3.0 Game Dev Platform + AI Intelligence (Phases 15-21) -- SHIPPED 2026-03-15
- v3.1 Debug + Polish + Svelte 5 Migration (Phases 22-25) -- SHIPPED 2026-03-16
- v3.2 GameData Tree UI + Context Intelligence + Image Gen (Phases 26-31) -- SHIPPED 2026-03-16
- v3.3 UI/UX Polish + Performance (Phases 32-36) -- IN PROGRESS

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

<details>
<summary>v3.1 Debug + Polish + Svelte 5 Migration (Phases 22-25) -- SHIPPED 2026-03-16</summary>

- [x] Phase 22: Svelte 5 Migration (3/3 plans) -- completed 2026-03-15
- [x] Phase 23: Bug Fixes (4/4 plans) -- completed 2026-03-15
- [x] Phase 24: UIUX Polish (2/2 plans) -- completed 2026-03-15
- [x] Phase 25: Comprehensive API E2E Testing (10/10 plans) -- completed 2026-03-16

</details>

<details>
<summary>v3.2 GameData Tree UI + Context Intelligence + Image Gen (Phases 26-31) -- SHIPPED 2026-03-16</summary>

- [x] Phase 26: Navigation + DEV Parity (1/1 plan) -- completed 2026-03-16
- [x] Phase 27: Tree Backend + Mock Data (2/2 plans) -- completed 2026-03-16
- [x] Phase 28: Hierarchical Tree UI (3/3 plans) -- completed 2026-03-16
- [x] Phase 29: Multi-Tier Indexing (3/3 plans) -- completed 2026-03-16
- [x] Phase 30: Context Intelligence Panel (2/2 plans) -- completed 2026-03-16
- [x] Phase 31: Codex AI Image Generation (2/2 plans) -- completed 2026-03-16

</details>

### v3.3 UI/UX Polish + Performance (IN PROGRESS)

**Milestone Goal:** Audit, critique, and polish ALL 5 pages (GameData Tree, Language Data Grid, Codex, World Map, TM) for visual consistency, performance, and production-readiness. Codex gets a full revamp with lazy loading. Cross-page consistency enforced so the app feels like ONE product.

- [x] **Phase 32: Design Token Foundation** - CSS tokens, shared micro-components (PageHeader, SkeletonCard, EmptyState, ErrorState, InfiniteScroll) (completed 2026-03-16)
- [ ] **Phase 33: Codex Revamp** - Paginated loading, IntersectionObserver infinite scroll, skeleton states, search-first UX, tab caching
- [ ] **Phase 34: Page-by-Page Polish** - Parallel UI/UX audit and polish for GameData Tree, Language Data Grid, World Map, and TM Panel
- [ ] **Phase 35: Cross-Page Consistency** - Unified PageHeader adoption, dark mode enforcement, sidebar consistency, error handling standardization
- [ ] **Phase 36: Visual Verification** - Playwright screenshots, performance benchmarks, memory leak testing, regression testing

## Phase Details

### Phase 32: Design Token Foundation
**Goal**: All pages have access to a shared design language -- CSS tokens for spacing/color/shadow/radius, plus reusable micro-components for common UI patterns (headers, loading, empty, error, infinite scroll)
**Depends on**: Nothing (first phase of v3.3)
**Requirements**: FND-01, FND-02, FND-03, FND-04, FND-05, FND-06
**Success Criteria** (what must be TRUE):
  1. CSS custom properties for spacing scale, color tokens, shadow tokens, and border-radius exist in app.css and can be referenced by any component
  2. A shared PageHeader component renders consistently when dropped into any page with title, icon, and action slot
  3. SkeletonCard, EmptyState, ErrorState, and InfiniteScroll components exist in lib/components/common/ and render correctly in isolation
  4. InfiniteScroll fires a callback when its sentinel enters the viewport and cleans up the IntersectionObserver via $effect
**Plans**: 1 plan

Plans:
- [ ] 32-01: CSS design tokens and shared micro-components

### Phase 33: Codex Revamp
**Goal**: Codex transforms from a slow all-at-once entity dump into a polished, fast encyclopedia with paginated loading, skeleton states, and search-first UX
**Depends on**: Phase 32 (uses InfiniteScroll, SkeletonCard, design tokens)
**Requirements**: CDX-01, CDX-02, CDX-03, CDX-04, CDX-05, CDX-06, CDX-07
**Success Criteria** (what must be TRUE):
  1. Codex loads first 50 entities immediately and loads more as the user scrolls -- never fetches all entities at once
  2. Skeleton cards matching real card dimensions show during loading -- no spinner, no layout shift when content appears
  3. Entity images only load when scrolled into view (loading="lazy"), not all at once on page open
  4. Search bar is prominent at the top, results update as the user types with visible debounce feedback
  5. Switching between category tabs is instant (cached results) with correct entity counts shown per tab
**Plans**: 2 plans

Plans:
- [ ] 33-01-PLAN.md -- Backend pagination + frontend InfiniteScroll + SkeletonCard + lazy images
- [ ] 33-02-PLAN.md -- Search-first UX + category tab caching + visual polish

### Phase 34: Page-by-Page Polish
**Goal**: GameData Tree, Language Data Grid, World Map, and TM Panel all pass UI/UX audits with consistent loading/empty/error states, proper dark mode, and polished spacing/typography
**Depends on**: Phase 32 (uses design tokens, EmptyState, ErrorState, SkeletonCard, PageHeader)
**Requirements**: GDT-01, GDT-02, GDT-03, GDT-04, LDG-01, LDG-02, LDG-03, WMP-01, WMP-02, TMP-01, TMP-02
**Success Criteria** (what must be TRUE):
  1. GameData Tree page has polished node detail panel with consistent spacing, loading states for the tree panel, and smooth expand/collapse at 1000+ nodes
  2. Language Data Grid uses skeleton rows for loading (not a spinner), has proper column alignment in dark mode, and shows clear feedback on empty search results
  3. World Map has consistent node styling, route lines, and tooltips in dark mode, plus a helpful empty state when no map data is loaded
  4. TM Panel has polished match percentage display, diff highlighting that works in dark mode, and proper loading/empty states for suggestions
**Plans**: TBD

Plans:
- [ ] 34-01: GameData Tree polish (GDT-01 through GDT-04)
- [ ] 34-02: Language Data Grid polish (LDG-01 through LDG-03)
- [ ] 34-03: World Map + TM Panel polish (WMP-01, WMP-02, TMP-01, TMP-02)

### Phase 35: Cross-Page Consistency
**Goal**: All five pages feel like one unified application -- same header pattern, same dark mode behavior, same sidebar interactions, same error recovery pattern
**Depends on**: Phase 33, Phase 34 (all pages must be individually polished before unifying)
**Requirements**: XPG-01, XPG-02, XPG-03, XPG-04
**Success Criteria** (what must be TRUE):
  1. All 5 pages use the shared PageHeader component and look consistent when navigating between them
  2. Dark mode works on every page with zero hardcoded colors -- toggling dark mode shows no broken elements on any page
  3. Sidebar navigation has consistent active states, hover effects, and spacing across all pages
  4. Every page uses the shared ErrorState component with a retry button for error recovery -- no page silently fails
**Plans**: TBD

Plans:
- [ ] 35-01: Cross-page consistency enforcement (PageHeader, dark mode, sidebar, error handling)

### Phase 36: Visual Verification
**Goal**: The entire v3.3 milestone is validated with hard evidence -- screenshots, benchmarks, memory stability, and zero test regressions
**Depends on**: Phase 35 (all visual work must be complete before verification)
**Requirements**: VER-01, VER-02, VER-03, VER-04
**Success Criteria** (what must be TRUE):
  1. Playwright screenshots exist for all 5 pages in both light and dark mode (minimum 10 screenshots) showing consistent, polished UI
  2. Codex loads 500 entities without visible lag, with initial render completing under 1 second
  3. Opening and closing pages 10 times shows stable memory usage with no growth trend (heap snapshot comparison)
  4. All 834+ existing API tests pass with zero regressions after all polish changes
**Plans**: TBD

Plans:
- [ ] 36-01: Playwright screenshots + performance benchmarks + regression test suite

## Progress

**Execution Order:**
Phases execute in numeric order: 32 -> 33 -> 34 -> 35 -> 36
Note: Phase 34 plans (34-01, 34-02, 34-03) are fully parallelizable.

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
| 22. Svelte 5 Migration | v3.1 | 3/3 | Complete | 2026-03-15 |
| 23. Bug Fixes | v3.1 | 4/4 | Complete | 2026-03-15 |
| 24. UIUX Polish | v3.1 | 2/2 | Complete | 2026-03-15 |
| 25. Comprehensive API E2E Testing | v3.1 | 10/10 | Complete | 2026-03-16 |
| 26. Navigation + DEV Parity | v3.2 | 1/1 | Complete | 2026-03-16 |
| 27. Tree Backend + Mock Data | v3.2 | 2/2 | Complete | 2026-03-16 |
| 28. Hierarchical Tree UI | v3.2 | 3/3 | Complete | 2026-03-16 |
| 29. Multi-Tier Indexing | v3.2 | 3/3 | Complete | 2026-03-16 |
| 30. Context Intelligence Panel | v3.2 | 2/2 | Complete | 2026-03-16 |
| 31. Codex AI Image Generation | v3.2 | 2/2 | Complete | 2026-03-16 |
| 32. Design Token Foundation | 1/1 | Complete   | 2026-03-16 | - |
| 33. Codex Revamp | 1/2 | In Progress|  | - |
| 34. Page-by-Page Polish | v3.3 | 0/3 | Not started | - |
| 35. Cross-Page Consistency | v3.3 | 0/1 | Not started | - |
| 36. Visual Verification | v3.3 | 0/1 | Not started | - |

---
*Roadmap created: 2026-03-14*
*v3.3 milestone added: 2026-03-17*
