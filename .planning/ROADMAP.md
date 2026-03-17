# Roadmap: LocaNext

## Milestones

- v1.0 Demo-Ready CAT Tool (Phases 01-06) -- SHIPPED 2026-03-15
- v2.0 Real Data + Dual Platform (Phases 07-14) -- SHIPPED 2026-03-15
- v3.0 Game Dev Platform + AI Intelligence (Phases 15-21) -- SHIPPED 2026-03-15
- v3.1 Debug + Polish + Svelte 5 Migration (Phases 22-25) -- SHIPPED 2026-03-16
- v3.2 GameData Tree UI + Context Intelligence + Image Gen (Phases 26-31) -- SHIPPED 2026-03-16
- v3.3 UI/UX Polish + Performance (Phases 32-36) -- SHIPPED 2026-03-17

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

### v3.3 UI/UX Polish + Performance (SHIPPED 2026-03-17)

**Milestone Goal:** Audit, critique, and polish ALL 5 pages (GameData Tree, Language Data Grid, Codex, World Map, TM) for visual consistency, performance, and production-readiness. Codex gets a full revamp with lazy loading. Cross-page consistency enforced so the app feels like ONE product.

- [x] **Phase 32: Design Token Foundation** - CSS tokens, shared micro-components (PageHeader, SkeletonCard, EmptyState, ErrorState, InfiniteScroll) (completed 2026-03-16)
- [x] **Phase 33: Codex Revamp** - Paginated loading, IntersectionObserver infinite scroll, skeleton states, search-first UX, tab caching (completed 2026-03-16)
- [x] **Phase 34: Page-by-Page Polish** - Parallel UI/UX audit and polish for GameData Tree, Language Data Grid, World Map, and TM Panel (completed 2026-03-16)
- [x] **Phase 35: Cross-Page Consistency** - Unified PageHeader adoption, dark mode enforcement, sidebar consistency, error handling standardization (completed 2026-03-17)
- [x] **Phase 36: Visual Verification** - Playwright screenshots, performance benchmarks, memory leak testing, regression testing (completed 2026-03-17)

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
**Plans**: 3 plans

Plans:
- [ ] 34-01-PLAN.md -- GameData Tree polish (GameDevPage, GameDataTree, NodeDetailPanel, GameDataContextPanel)
- [ ] 34-02-PLAN.md -- Language Data Grid + TM Panel polish (GridPage, TMPage, TMExplorerGrid)
- [ ] 34-03-PLAN.md -- World Map polish (WorldMapPage, MapCanvas, MapTooltip, MapDetailPanel)

### Phase 35: Cross-Page Consistency
**Goal**: All five pages feel like one unified application -- same header pattern, same dark mode behavior, same sidebar interactions, same error recovery pattern
**Depends on**: Phase 33, Phase 34 (all pages must be individually polished before unifying)
**Requirements**: XPG-01, XPG-02, XPG-03, XPG-04
**Success Criteria** (what must be TRUE):
  1. All 5 pages use the shared PageHeader component and look consistent when navigating between them
  2. Dark mode works on every page with zero hardcoded colors -- toggling dark mode shows no broken elements on any page
  3. Sidebar navigation has consistent active states, hover effects, and spacing across all pages
  4. Every page uses the shared ErrorState component with a retry button for error recovery -- no page silently fails
**Plans**: 3 plans

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
**Plans**: 3 plans

Plans:
- [ ] 36-01: Playwright screenshots + performance benchmarks + regression test suite

### v3.5 WOW Showcase (Phases 37-42)

**Milestone Goal:** Transform LocaNext from functional to STUNNING with maximum demo WOW effect. Smart attribute highlighting in XML viewer, fantasy world map, codex relationship graph, cross-cutting micro-interactions, TTS voice generation, and a showcase-ready LanguageData editor.

- [x] **Phase 37: XML Viewer WOW Polish** - Smart attribute semantic colors, hover preview tooltips, smooth panel/tab animations, micro-interactions (completed 2026-03-17)
- [x] **Phase 38: Fantasy World Map** - Parchment aesthetic, region polygons, terrain icons, custom SVG markers, route animations, mini-map (completed 2026-03-17)
- [x] **Phase 39: Codex Cards + Relationship Graph** - Glassmorphism entity cards, D3 force-directed relationship graph, parallax hover (completed 2026-03-17)
- [x] **Phase 40: Cross-cutting WOW Polish** - Page transitions, shimmer loading choreography, Ctrl+K command palette, micro-interactions (completed 2026-03-17)
- [ ] **Phase 41: Qwen3-TTS Korean Voice** - TTS backend service, 5 character voice profiles, frontend audio playback
- [ ] **Phase 42: LanguageData Fix + WOW Showcase** - Fix grid regression, 3-format mock data, right panel TM/Image/Audio/AI showcase

### Phase 37: XML Viewer WOW Polish
**Goal**: Every attribute in the XML viewer is semantically colored, hovering cross-refs shows entity previews, and all panel interactions have smooth animations
**Depends on**: v3.3 complete
**Requirements**: WOW-01, WOW-02, WOW-03, WOW-04
**Success Criteria** (what must be TRUE):
  1. Cross-ref attributes (KnowledgeKey, FactionKey, etc.) render blue with underline; identity attrs gold; editable attrs green; media attrs purple; stat attrs cyan
  2. Hovering a cross-ref attribute value for 300ms shows a mini-preview card with entity name, type badge, and thumbnail image
  3. Panel entrance has slide-in animation, tab switching has crossfade, image loading has shimmer-to-reveal
  4. Clicking an attribute value copies it to clipboard with a ripple effect
**Plans**: 3 plans

Plans:
- [ ] 37-01-PLAN.md -- Smart attribute semantic highlighting (classifyAttr + 6 color categories)
- [ ] 37-02-PLAN.md -- Hover preview tooltips + copy ripple + search highlight pulse
- [ ] 37-03-PLAN.md -- Panel slide-in + tab crossfade + image shimmer + dict stagger animations

### Phase 38: Fantasy World Map
**Goal**: The map page looks like a real fantasy game world map with parchment background, region polygons, terrain indicators, and smooth navigation
**Depends on**: Phase 37 (establishes animation patterns)
**Requirements**: WOW-05, WOW-06, WOW-07, WOW-08, WOW-09
**Success Criteria** (what must be TRUE):
  1. Map has parchment/aged paper background with CSS gradients (no external images) and ornamental border frame
  2. 10 regions render as semi-transparent polygons with glow-on-hover and Korean fantasy names
  3. Each node type has a distinct SVG icon (castle=Town, skull=Dungeon, shield=Fortress, tent=Wilderness, compass=Main, tree=Sub)
  4. Routes between regions animate on hover with a travel-path effect and danger-level coloring
  5. Click region -> smooth zoom-to-fit with d3 transition + detail panel
**Plans**: 3 plans

Plans:
- [ ] 38-01-PLAN.md -- Mock map data (10 regions, 13 routes) + parchment aesthetic
- [ ] 38-02-PLAN.md -- Region polygons + terrain icons + node markers
- [ ] 38-03-PLAN.md -- Route animations + zoom interactions + mini-map

### Phase 39: Codex Cards + Relationship Graph
**Goal**: Codex entity grid uses glassmorphism cards with parallax hover, and a D3 force-directed graph shows entity relationships
**Depends on**: Phase 37 (animation patterns), Phase 38 (mock data enrichment)
**Requirements**: WOW-10, WOW-11, WOW-12, WOW-13
**Success Criteria** (what must be TRUE):
  1. Entity cards have glassmorphism effect (backdrop-filter blur, semi-transparent background) with AI portrait as card image
  2. Hovering a card produces parallax shift on the background image
  3. D3 force-directed graph shows character->item, character->skill, character->faction relationships with typed link styles
  4. Hovering a graph node highlights all connected nodes and dims unconnected ones
**Plans**: 2 plans

Plans:
- [ ] 39-01: Glassmorphism entity cards with parallax hover
- [ ] 39-02: D3 force-directed relationship graph

### Phase 40: Cross-cutting WOW Polish
**Goal**: Every page transition, loading state, and interaction across the entire app feels polished and delightful
**Depends on**: Phases 37-39 (all visual work complete)
**Requirements**: WOW-14, WOW-15, WOW-16, WOW-17
**Success Criteria** (what must be TRUE):
  1. Navigating between pages has crossfade transition (not instant swap)
  2. All loading states use shimmer skeletons matching the content dimensions (no spinners anywhere)
  3. Ctrl+K opens a command palette for global search across all entities
  4. Toast notifications slide in from top-right with auto-dismiss after 3 seconds
**Plans**: 2 plans

Plans:
- [ ] 40-01: Page transitions + shimmer loading choreography
- [ ] 40-02: Ctrl+K command palette + toast system

### Phase 41: Qwen3-TTS Korean Voice Generation
**Goal**: Install Qwen3-TTS and integrate Korean voice generation into the Codex, with unique voice profiles for each of the 5 game characters and frontend audio playback
**Depends on**: Phase 40
**Requirements**: TTS-01, TTS-02, TTS-03, TTS-04, TTS-05
**Success Criteria** (what must be TRUE):
  1. TTSService loads Qwen3-TTS lazily on first voice generation request
  2. Each of the 5 characters has a distinct voice profile with unique instructions
  3. POST /api/ldm/codex/generate-voice/{strkey} generates .wav and returns audio URL
  4. Generated audio is cached on disk -- repeat calls skip regeneration
  5. Codex entity detail shows Generate Voice button, loading state, audio player with auto-play
**Plans**: 2 plans

Plans:
- [ ] 41-01-PLAN.md -- TTS backend service + API endpoints (TTSService, voice profiles, generate/serve routes)
- [ ] 41-02-PLAN.md -- Frontend voice generation UI (CodexEntityDetail integration)

### Phase 42: LanguageData Fix + WOW Showcase
**Goal**: Fix the broken LDM grid editor regression, create 3-format mock localization data (Excel, TXT, XML) for format-agnostic showcase, and wire the right panel with TM 6-tier cascade, entity images, character voice audio, and AI context for a professional CAT tool demo
**Depends on**: Phase 41
**Requirements**: LDM-FIX-01, LDM-FIX-02, LDM-FIX-03, LDM-MOCK-01, LDM-MOCK-02, LDM-MOCK-03, LDM-MOCK-04, LDM-WOW-01, LDM-WOW-02, LDM-WOW-03, LDM-WOW-04
**Success Criteria** (what must be TRUE):
  1. All LDM API endpoints return 200 (no 422 validation errors in file navigation chain)
  2. Double-clicking a file opens GridPage with rows visible
  3. 3 mock files (xlsx, txt, xml) uploaded to a Showcase Demo project with 75+ game-themed strings
  4. TM tab shows 6-tier cascade results when a row is selected
  5. Image/Audio/AI Context tabs light up with entity content when editing cross-referenced strings
**Plans**: 3 plans

Plans:
- [ ] 42-01-PLAN.md -- Debug and fix LDM grid regression (API 422 errors + frontend flow)
- [ ] 42-02-PLAN.md -- Create 3-format mock localization data + TM entries
- [ ] 42-03-PLAN.md -- Wire right panel tabs (TM cascade, Image, Audio, AI Context)

## Progress

**Execution Order:**
Phases execute in numeric order: 32 -> 33 -> 34 -> 35 -> 36 -> 37 -> 38 -> 39 -> 40 -> 41 -> 42
Note: Phase 38 and 39 can be partially parallelized after Phase 37.
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
| 32. Design Token Foundation | v3.3 | 1/1 | Complete | 2026-03-16 |
| 33. Codex Revamp | v3.3 | 2/2 | Complete | 2026-03-16 |
| 34. Page-by-Page Polish | 3/3 | Complete   | 2026-03-16 | - |
| 35. Cross-Page Consistency | v3.3 | 1/1 | Complete | 2026-03-17 |
| 36. Visual Verification | v3.3 | 1/1 | Complete | 2026-03-17 |
| 37. XML Viewer WOW Polish | 3/3 | Complete    | 2026-03-17 | - |
| 38. Fantasy World Map | 2/3 | In Progress|  | - |
| 39. Codex Cards + Relationship Graph | 2/2 | Complete   | 2026-03-17 | - |
| 40. Cross-cutting WOW Polish | 1/2 | In Progress|  | - |
| 41. Qwen3-TTS Korean Voice | 0/2 | Planned |  | - |
| 42. LanguageData Fix + WOW Showcase | v3.5 | 0/3 | Planned | - |

---
*Roadmap created: 2026-03-14*
*v3.3 milestone added: 2026-03-17*
*v3.5 WOW Showcase milestone added: 2026-03-17*
*Phase 41 planned: 2026-03-18*
*Phase 42 planned: 2026-03-18*
