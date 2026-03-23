# Milestones

## v8.0 Tag Visualizer + Service Layer Extraction (IN PROGRESS)

**Phases:** 73, 69-72 (5 phases)
**Requirements:** 0/16 complete (5 categories: TAG, SVC-STATS, SVC-AUTH, SVC-TELEM, SVC-INFRA)
**Goal:** (1) MemoQ-style tag pills for translators — {0}, %1#, \n rendered as colored inline badges. (2) Extract business logic from 6 thick API modules into service classes.

---

## v7.1 Security Hardening (Shipped: 2026-03-23)

**Phases:** 65-68 (4 phases, 4 commits)
**Requirements:** 15/18 complete (3 MEDIUM/LOW deferred)
**Goal:** Fix all CRITICAL/HIGH security issues from full-stack audit — auth gaps, path traversal, XSS, IDOR, frontend consolidation.

**Key accomplishments:**
- 17 API endpoints secured with proper authentication (8 had zero auth, 6 were commented out)
- 3 path traversal vulnerabilities fixed (file upload, download, merge)
- XSS fix in ExplorerSearch (HTML-escape before {@html})
- 4 local getAuthHeaders duplicates consolidated to canonical api.js
- IDOR fix in remote logging (installation scoped to own data)
- Log injection endpoint now requires API key auth
- stderr suppression removed from background task execution

---

## v7.0 Production-Ready Merge + Performance + UIUX (Shipped: 2026-03-23)

**Phases completed:** 4 phases, 9 plans, 12 tasks

**Key accomplishments:**

- 1. [Rule 1 - Bug] Fixed importlib detection test false positive
- FAISSManager extended with IndexIDMap2(FlatIP) for ID-based add/remove, plus InlineTMUpdater service for synchronous per-entry FAISS + hash PKL updates
- All TM CRUD endpoints (add/edit/delete/upload) now update FAISS index and hash lookups inline before HTTP response, giving users immediate search consistency
- InlineTMUpdater now tracks and persists line-level FAISS data (line.index, line.npy, line_mapping.pkl) so Tier 4 line-embedding search returns current results immediately after inline add/edit/delete
- PerfTimer context manager with ring buffer metrics + 6 modules instrumented for duration_ms logging across embedding, FAISS, TM CRUD, merge, and upload
- GET /api/performance/summary endpoint exposing ring buffer metrics as JSON with p50/p95/max/count/avg per instrumented operation
- MergeModal hardened with preview retry, zero-match guard, AbortController cancel, execute error recovery, and adaptive done-phase messaging

---

## v5.1 Testing + Polish (Shipped: 2026-03-21)

**Phases completed:** 11 phases, 21 plans, 41 tasks

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
- MegaIndex auto-builds all 35 dicts from mock_gamedata on DEV server start via PerforcePathService mock path override
- All 4 Codex UIs verified rendering with MegaIndex mock data; fixed app-blocking rune error and Region map missing coordinates
- RightPanel Image tab shows DDS portrait via MegaIndex C7->C1 chain; Audio tab shows WEM player with Korean/English script text via C3 chain -- both verified end-to-end with Playwright screenshots
- LanguageData grid status colors updated from green to blue-green/teal for reviewed/approved rows using Carbon Design teal-50
- Verified TM auto-register chain (reviewed -> add_entry -> FAISS auto-sync) and added project-row fallback for TM suggest when no linked TM exists
- Playwright automated smoke test verified all 11 LocaNext pages render correctly in DEV mode with mock data -- no blank screens, no blocking errors

---

## v5.1 Testing + Polish (IN PROGRESS)

**Phases:** 52-55 (4 phases)
**Requirements:** 0/15 complete (6 categories: INIT, VERIFY, RPANEL, TM, COLOR, SMOKE)
**Goal:** Verify all v5.0 features work end-to-end in DEV mode with mock data. Fix MegaIndex DEV init, TM flow, FAISS auto-build, LanguageData grid colors, and right panel wiring. Every page tested with Playwright screenshots.

**Phase structure:**

1. Phase 52: DEV Init + MegaIndex Wiring (auto-build on DEV start, PerforcePathService auto-config)
2. Phase 53: Codex + Right Panel Verification (4 Codex UIs + Image/Audio tabs with Playwright screenshots)
3. Phase 54: TM Flow + FAISS Auto-Build + Grid Colors (auto-register, auto-rebuild, grey/yellow/blue-green)
4. Phase 55: End-to-End Smoke Test (Playwright visits all 11 pages, screenshots)

---

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
