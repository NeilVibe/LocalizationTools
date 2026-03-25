# Milestones

## v9.0 Build Validation + Real-World Testing (Shipped: 2026-03-25)

**Phases completed:** 6 phases, 14 plans, 22 tasks

**Key accomplishments:**

- Pillow-valid 64x64 DDS textures and WAV-content WEM audio stubs across 3 language folders (English, Korean, Chinese)
- Japanese XML with 100 StringIds + 13 tests validating DDS/WEM/XML at correct Perforce-mapped paths
- Added lxml to embedded Python pip install and merge module import verification step to GitHub Actions build workflow
- Triggered GitHub Actions Light Build to validate lxml + merge module CI pipeline end-to-end; installer verification pending human testing on offline PC
- 7 E2E tests verifying language data upload, row listing with Korean text, edit persistence, and full SQLite round-trip using showcase_dialogue.loc.xml fixture
- 9 E2E tests verifying DDS thumbnail, WEM audio stream, image/audio context endpoints against Phase 74 mock gamedata
- 11 E2E tests verifying TM lifecycle: populate 10 game localization entries, CRUD operations, FAISS index build, and 5-tier cascade search
- E2E tests for merge (5 tests, 4 xfail due to route shadow) and QA pipeline (6 tests passing, pattern mismatch detected in DLG_003)
- Aho-Corasick detection endpoint and context panel verified with 12 E2E tests (10 pass, 2 xfail for gamedata dependency)
- Qwen3-VL scored all 5 LocaNext pages (avg 6.6/10): Files 6, GameDev 7, Codex 7, Map 7, TM 6 -- 2 pages need fixes
- Fixed Files type labels and TM status column, re-verified all 5 pages with Qwen3-VL -- avg score improved from 6.6 to 8.6/10, all pass 7+
- FIX-01 (Critical): Merge route conflict resolved.
- Corrected BUILD-04 to pending, checked off 7 completed Active items in PROJECT.md, populated STATE.md metrics, fixed ROADMAP phase count

---

## v8.0 Tag Visualizer + Service Layer Extraction (Shipped: 2026-03-24)

**Phases:** 73, 69-72 (5 phases)
**Requirements:** 7/7 complete (TAG-01..03, SVC-01..04)

**Key accomplishments:**

- MemoQ-style tag pills: tagDetector.js (5-pattern priority detection) + TagText.svelte pill renderer in VirtualGrid source/target/reference cells
- 136 tests pass (43 unit + 93 E2E mock) proving tag pills are display-only render transform
- 8 service classes extracted from thick API routes: StatsService, RankingsService, AuthService, TelemetryService, RemoteLoggingService, DbStatsService, HealthService, ProgressService
- Route file reductions: 33-81% (stats 78%, rankings 78%, db_stats 81%, health 74%, telemetry 68%)
- Tribunal architecture decision: class-based services matching SyncService pattern (unanimous 3/3)
- Net -2,173 lines of code across service extraction (7,731 deleted, 5,558 added)

**Archive:** [v8.0-ROADMAP.md](milestones/v8.0-ROADMAP.md) | [v8.0-REQUIREMENTS.md](milestones/v8.0-REQUIREMENTS.md)

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

**Phases:** 61-64 (4 phases, 9 plans)
**Requirements:** 18/18 complete (MARCH, PERF, TMAU, UIUX)

**Key accomplishments:**

- Merge internalized: 14 QT modules copied into server/services/merge/, zero sys.path hacks, PyInstaller-safe
- TM auto-update inline: embedding + HNSW on every add/edit/delete (~6ms), immediate search consistency
- PerfTimer ring buffer on all hot paths with /api/performance/summary endpoint
- MergeModal hardened: preview retry, zero-match guard, AbortController cancel, error recovery

**Archive:** [v7.0-ROADMAP.md](milestones/v7.0-ROADMAP.md) | [v7.0-REQUIREMENTS.md](milestones/v7.0-REQUIREMENTS.md)

---

## v5.1 Testing + Polish (Shipped: 2026-03-21)

**Phases:** 52-55 (4 phases)
**Requirements:** 15/15 complete

**Key accomplishments:**

- MegaIndex auto-builds on DEV start via PerforcePathService mock path override
- All 4 Codex UIs verified rendering with MegaIndex mock data
- RightPanel Image/Audio tabs wired via MegaIndex C7->C1 and C3 chains
- LanguageData grid status colors (teal-50), TM auto-register + suggest fallback
- Playwright smoke test: all 11 pages render correctly

---

## v5.0 Offline Production Bundle + Full Codex (Shipped: 2026-03-21)

**Phases:** 45-51 (7 phases, 15 plans)
**Requirements:** 30/30 complete

**Key accomplishments:**

- MegaIndex: unified game data index with 35 dicts, 66 methods, O(1) lookups
- 4 Codex UIs: Item, Character, Audio, Region with semantic search and media preview
- Model2Vec + vgmstream bundling for offline production bundle
- 31 pytest tests for SQLite correctness in offline/server-local modes

**Archive:** [v5.0-ROADMAP.md](milestones/v5.0-ROADMAP.md) | [v5.0-REQUIREMENTS.md](milestones/v5.0-REQUIREMENTS.md)

---

## v4.0 Mockdata Excellence + Next Level (Shipped: 2026-03-18)

**Phases:** 43-44 (2 phases, 5 plans)
**Requirements:** 8/8 complete

**Key accomplishments:**

- 3 new XML entity types (Skill/Region/Quest), KnowledgeInfo 10->59, map 14 nodes
- 28 typed relationship graph links, GlossaryService 33 entities, MapData 31 images

---

## v3.5 WOW Showcase + LanguageData (Shipped: 2026-03-18)

**Phases:** 37-42 (6 phases, 16 plans)
**Requirements:** 12/12 complete

**Key accomplishments:**

- XML Viewer WOW, Fantasy World Map, Codex Cards + D3 Graph, Cross-cutting Polish
- Qwen3-TTS Korean voice generation, LanguageData grid fix + showcase data

---

## v3.3 UI/UX Polish + Performance (Shipped: 2026-03-17)

**Phases:** 32-36 (5 phases, 8 plans)
**Requirements:** 32/32 complete

---

## v3.2 GameData Tree UI + Context Intelligence + Image Gen (Shipped: 2026-03-16)

**Phases:** 26-31 (6 phases, 12 plans)
**Requirements:** 25/25 complete

**Archive:** [v3.2-ROADMAP.md](milestones/v3.2-ROADMAP.md) | [v3.2-REQUIREMENTS.md](milestones/v3.2-REQUIREMENTS.md)

---

## v3.1 Debug + Polish + Svelte 5 Migration (Shipped: 2026-03-16)

**Phases:** 22-25 (4 phases, 19 plans)
**Requirements:** 48/48 complete

**Archive:** [v3.1-ROADMAP.md](milestones/v3.1-ROADMAP.md) | [v3.1-REQUIREMENTS.md](milestones/v3.1-REQUIREMENTS.md)

---

## v3.0 Game Dev Platform + AI Intelligence (Shipped: 2026-03-15)

**Phases:** 15-21 (7 phases, 14 plans)
**Requirements:** 45/45 complete

**Archive:** [v3.0-ROADMAP.md](milestones/v3.0-ROADMAP.md) | [v3.0-REQUIREMENTS.md](milestones/v3.0-REQUIREMENTS.md)

---

## v2.0 Real Data + Dual Platform (Shipped: 2026-03-15)

**Phases:** 07-14 (8 phases, 17 plans)
**Requirements:** 40/40 complete

**Archive:** [v2.0-ROADMAP.md](milestones/v2.0-ROADMAP.md) | [v2.0-REQUIREMENTS.md](milestones/v2.0-REQUIREMENTS.md)

---

## v1.0 Demo-Ready CAT Tool (Shipped: 2026-03-15)

**Phases:** 01-06 (7 phases, 20 plans)
**Requirements:** 42/42 complete

**Archive:** [v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md) | [v1.0-REQUIREMENTS.md](milestones/v1.0-REQUIREMENTS.md)

---
