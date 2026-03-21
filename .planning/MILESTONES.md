# Milestones

## v5.0 Offline Production Bundle + Full Codex (Shipped: 2026-03-21)

**Phases completed:** 7 phases, 15 plans, 30 tasks

**Key accomplishments:**

- Centralized Perforce path resolution service (11 templates, drive/branch config, WSL conversion) extracted from MapDataService, plus 10 frozen dataclass schemas for all MegaIndex entity types
- Runtime AI engine detection service with 5-engine probes, FastAPI endpoint, and Svelte 5 reactive capability badges in Settings UI
- Unified game data index with 35 dicts, 66 methods, 1310 lines -- O(1) lookups by StrKey/StringId/EventName/UITextureName with graceful empty-build degradation
- CodexService and MapDataService wired to MegaIndex -- single XML parse replaces 3 independent scans
- 3 REST endpoints for Item Codex consuming MegaIndex O(1) lookups with paginated list, group tree hierarchy, and 3-pass knowledge resolution detail
- Svelte 5 Item Codex page with card grid, ItemGroupInfo hierarchy tabs, debounced search, infinite scroll, and knowledge resolution detail panel with 4-tab layout
- 3 FastAPI endpoints for character browsing with race/gender parsing, filename categories, and 3-pass knowledge resolution
- Character Codex frontend with card grid, category tabs, debounced search, infinite scroll, and detail panel with Race/Gender/Age/Job badges and 4-tab knowledge resolution
- 4 FastAPI endpoints for audio browsing, searching, streaming, and categorizing via MegaIndex D10/D11/D20/D21/C4/C5 lookups with WEM-to-WAV conversion
- Svelte 5 Audio Codex page with category tree sidebar, audio entry list with inline playback, debounced search, and detail panel with full script text overlay
- Region Codex API with faction hierarchy tree, paginated list with faction_group filtering, and region detail with WorldPosition and knowledge 3-pass resolution
- Region Codex Svelte 5 page with d3-zoom interactive map, FactionGroup tab filtering, collapsible faction tree, and knowledge detail panel
- C7-bridged image lookup wiring StringID to entity portraits via MegaIndex, plus AudioTab src= reactivity fix with {#key} cache-bust
- Model2Vec + vgmstream bundling scripts, electron-builder extraResources config, and SQLite WAL hardening for offline-only reliability
- 31 pytest tests auditing all 9 factory/repository paths for SQLite correctness in OFFLINE and SERVER-LOCAL modes, plus smoke tests confirming no PostgreSQL hard-dependencies in the service layer

---

## v5.0 Offline Production Bundle + Full Codex (IN PROGRESS)

**Phases:** 45-51 (7 phases)
**Requirements:** 0/26 complete (7 categories: INFRA, AUDIO, ITEM, CHAR, REGION, STRID, OFFLINE)
**Goal:** Ship a self-sufficient offline bundle that works on disconnected machines (SQLite only, no server). Expand Codex with Audio/Item/Character/Region UIs powered by QACompiler + MapDataGenerator logic. All core features work without AI engines.

**Phase structure:**

1. Phase 45: Foundation Infrastructure (PerforcePathService, AICapabilityService, graceful degradation)
2. Phase 46: Item Codex (card grid, DDS images, ItemGroupInfo hierarchy, knowledge tabs)
3. Phase 47: Character Codex (portraits, filename-based grouping, Race/Gender/Age/Job detail)
4. Phase 48: Audio Codex (WEM playback, AudioIndex chain, category tree)
5. Phase 49: Region Codex + Interactive Map (FactionNode tree, WorldPosition d3-zoom map)
6. Phase 50: StringID-to-Audio Integration (reverse lookup, inline LDM grid player)
7. Phase 51: Offline Production Bundle (SQLite-only, Model2Vec light build, fresh-machine smoke test)

---

## v4.0 Mockdata Excellence + Next Level (SHIPPED 2026-03-18)

**Phases:** 43-44 (2 phases, 5 plans)
**Requirements:** 8/8 complete (MOCK-AUDIT-01..04, WOW-WIRE-01..04)
**Goal:** Audit and elevate all mock data for maximum WOW effect, then wire backend code to leverage it.

**Key accomplishments:**

1. **Mockdata Audit** -- 3 new XML entity types (Skill/Region/Quest), KnowledgeInfo 10->59, map 10->14 nodes, TM 35->50
2. **WOW Wiring** -- 28 typed relationship graph links, GlossaryService 33 entities, MapData 31 images, TM 500->200

---

## v3.5 WOW Showcase + LanguageData (SHIPPED 2026-03-18)

**Phases:** 37-42 (6 phases, 16 plans)
**Requirements:** 12/12 complete (WOW-01..17, TTS-01..05, LDM-FIX/MOCK/WOW)
**Goal:** Transform LocaNext from functional to STUNNING with maximum demo WOW effect.

**Key accomplishments:**

1. **XML Viewer WOW** -- Smart semantic attribute colors, hover preview tooltips, panel animations
2. **Fantasy World Map** -- Parchment aesthetic, region polygons, terrain icons, route animations, mini-map
3. **Codex Cards + Graph** -- Glassmorphism entity cards, D3 force-directed relationship graph, parallax hover
4. **Cross-cutting Polish** -- Page transitions, shimmer loading choreography, Ctrl+K command palette
5. **Qwen3-TTS** -- Korean voice generation backend, 5 character voice profiles
6. **LanguageData Fix** -- Grid regression fix, 3-format showcase data, TM cascade wiring

**Post-review:** 28+ Hive fixes (D3 leaks, AbortControllers, race conditions, a11y)

---

## v3.3 UI/UX Polish + Performance (SHIPPED 2026-03-17)

**Phases:** 32-36 (5 phases, 8 plans)
**Requirements:** 32/32 complete (8 categories: FND, CDX, GDT, LDG, WMP, TMP, XPG, VER)
**Goal:** Audit, critique, and polish ALL 5 pages for visual consistency, performance, and production-readiness. Codex gets a full revamp with lazy loading. Cross-page consistency enforced so the app feels like ONE product.

**Phase structure:**

1. Phase 32: Design Token Foundation (CSS tokens + 5 shared micro-components)
2. Phase 33: Codex Revamp (paginated loading, IntersectionObserver, skeleton states, search-first UX)
3. Phase 34: Page-by-Page Polish (GameData Tree, Language Data Grid, World Map, TM Panel -- parallelizable)
4. Phase 35: Cross-Page Consistency (unified headers, dark mode, sidebar, error handling)
5. Phase 36: Visual Verification (Playwright screenshots, perf benchmarks, memory leaks, regression tests)

---

## v3.2 GameData Tree UI + Context Intelligence + Image Gen (SHIPPED 2026-03-16)

**Phases:** 26-31 (6 phases, 12 plans)
**Requirements:** 25/25 complete (5 categories: TREE, IDX, CTX, IMG, NAV)
**Goal:** Rework Game Data page from flat grid to hierarchical XML tree navigator, add right-side context panel with TM/images/audio/AI context via 5-tier cascade search, generate AI images for Codex, and achieve sub-second lookup via multi-tier indexing.

**Archive:** [v3.2-ROADMAP.md](milestones/v3.2-ROADMAP.md) | [v3.2-REQUIREMENTS.md](milestones/v3.2-REQUIREMENTS.md)

---

## v3.1 Debug + Polish + Svelte 5 Migration (SHIPPED 2026-03-16)

**Phases:** 22-25 (4 phases, 19 plans)
**Requirements:** 48/48 complete (4 categories: SV5, FIX, UX, TEST-E2E)

**Key accomplishments:**

1. **Svelte 5 Migration** -- 36 components purged of createEventDispatcher and on: directives, pure $props callbacks
2. **Bug Fixes** -- 12 runtime bugs fixed
3. **UIUX Polish** -- 60 audit issues resolved
4. **API E2E Testing** -- 834 test functions, 40 files, 275 endpoints

**Archive:** [v3.1-ROADMAP.md](milestones/v3.1-ROADMAP.md) | [v3.1-REQUIREMENTS.md](milestones/v3.1-REQUIREMENTS.md)

---

## v3.0 Game Dev Platform + AI Intelligence (SHIPPED 2026-03-15)

**Phases:** 15-21 (7 phases, 14 plans)
**Requirements:** 45/45 complete (9 categories)

**Archive:** [v3.0-ROADMAP.md](milestones/v3.0-ROADMAP.md) | [v3.0-REQUIREMENTS.md](milestones/v3.0-REQUIREMENTS.md)

---

## v2.0 Real Data + Dual Platform (SHIPPED 2026-03-15)

**Phases:** 07-14 (8 phases, 17 plans)
**Requirements:** 40/40 complete

**Archive:** [v2.0-ROADMAP.md](milestones/v2.0-ROADMAP.md) | [v2.0-REQUIREMENTS.md](milestones/v2.0-REQUIREMENTS.md)

---

## v1.0 Demo-Ready CAT Tool (SHIPPED 2026-03-15)

**Phases:** 01-06 (7 phases, 20 plans)
**Requirements:** 42/42 complete

**Archive:** [v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md) | [v1.0-REQUIREMENTS.md](milestones/v1.0-REQUIREMENTS.md)

---
