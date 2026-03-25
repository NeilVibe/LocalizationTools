# LocaNext — Real Data CAT Tool + Game Dev Platform

## What This Is

LocaNext is a desktop localization management platform (Electron + FastAPI + Svelte 5) for game localization teams AND game developers. It handles real XML parsing from game data files, dual UI modes (Translator vs Game Dev), translation memory management with 4-mode merge engine, semantic search, entity-aware context panels with AI summaries, integrated QA, DDS image / WEM audio preview, and XML-based language data editing. v2.0 ships with production-ready data pipelines ported from 5 proven NewScripts projects, local AI via Qwen3, and full offline/online parity.

## Core Value

The platform delivers real, working localization workflows — real XML parsing, real merge logic matching QuickTranslate patterns, real image/audio from game data, and AI-powered context summaries — all running locally with zero cloud dependency, dual-mode for both translators and game developers, polished enough to demo to executives.

## Current Milestone: v10.0 UI Polish + Tag Pill Redesign

**Goal:** Fix 4 UI issues found during v9.0 Windows testing. Qwen3-VL visual review mandatory after each change.

**Target features:**
- [ ] UI-101: Hide br-tag linebreaks from grid (merge auto-handles them, only show color/format tags)
- [ ] UI-102: Combine color+format codes into single tag pill with color applied
- [ ] UI-103: Grid default background → neutral/white (not yellow)
- [ ] UI-104: Tag pill redesign — color-coded combined formatter tags

**Stack:** `/xml-localization` + `/svelte-code-writer` + `/svelte-core-bestpractices` + `/vision-review` (Qwen3-VL)
**Mode:** DEV (localhost:5173) + Playwright for instant feedback

**Critical env note:** Remove WSL2 portproxy on 8888 before Playground testing (`netsh interface portproxy delete v4tov4 listenport=8888 listenaddress=0.0.0.0`)

## Shipped: v9.0 Build Validation + Real-World Testing (2026-03-25)

<details>
<summary>v9.0 details (click to expand)</summary>

- 6 phases, 14 plans, 212 commits
- GitHub Actions build GREEN — Light Build v26.324.2024
- Gitea build GREEN — Build 555, all 7 QA stages
- Security audit: 6 CVEs fixed
- Windows Playground: installed, backend running, file upload verified
- Qwen3-VL visual audit: avg 8.6/10, all pages 7+
- 12+ build fixes: CORS, deps, Model2Vec, PYTHONPATH, DATABASE_MODE

</details>

## Current State (v8.0 shipped — 12 milestones complete)

- 12 milestones shipped (v1.0 through v8.0), 73 phases, ~150 plans
- v8.0: MemoQ-style tag pills (136 tests) + 8 service classes extracted (route files 33-81% thinner)
- v7.0: Merge internalized (14 modules, PyInstaller-safe), TM auto-update inline (~6ms), PerfTimer instrumentation
- v7.1: Security hardening (17 endpoints secured, 3 path traversal fixes, XSS/IDOR patches)
- v9.0: Security audit (6 CVEs fixed), build pipeline hardened (12+ fixes), Ruflo intelligence initialized
- 10 service classes in server/services/ (Stats, Rankings, Auth, Telemetry, RemoteLogging, DbStats, Health, Progress, Sync, Transfer)
- 834 API test functions across 40 test files covering 275 endpoints
- All 5 main pages verified working (Files, Game Dev, Codex, Map, TM)
- Full offline/online parity maintained across all milestones

## Requirements

### Validated

- ✓ STAB-01 through STAB-05 — Server stability, DB parity, zombie process prevention — v1.0
- ✓ EDIT-01 through EDIT-06 — Virtual grid, status colors, save fix, search/filter, export — v1.0
- ✓ TM-01 through TM-05 — Auto-mirror, assignment, match percentages, leverage, Model2Vec — v1.0
- ✓ SRCH-01 through SRCH-03 — Semantic search, UI, sub-second performance — v1.0
- ✓ AI-01, AI-02 — Model2Vec pipeline, AI-suggested indicators — v1.0
- ✓ OFFL-01 through OFFL-03 — Offline demo, feature parity, transparent switching — v1.0
- ✓ UI-01 through UI-05 — Grid rework, explorer polish, settings, visual quality — v1.0
- ✓ MAP-01 through MAP-03 — Image/audio mapping, organic integration — v1.0
- ✓ CTX-01 through CTX-10 — Entity detection, context panel, glossary, category clustering, AI status — v1.0
- ✓ DUAL-01 through DUAL-05 — File type detection, dual columns, mode badge, shared grid — v2.0
- ✓ XML-01 through XML-07 — XMLParsingEngine, sanitizer, language tables, cross-ref chains, StringIdConsumer — v2.0
- ✓ TMERGE-01 through TMERGE-07 — 4-mode merge, postprocess, XML/Excel/text export — v2.0
- ✓ GMERGE-01 through GMERGE-05 — Position-based tree diff, node/attribute/children merge — v2.0
- ✓ MEDIA-01 through MEDIA-04 — DDS→PNG, WEM→WAV, API streaming, placeholders — v2.0
- ✓ AISUM-01 through AISUM-05 — Qwen3 endpoint, summaries, cache, fallback — v2.0
- ✓ CLI-01 through CLI-04 — CLI merge/export/detect, E2E round-trip — v2.0
- ✓ FIX-01 through FIX-03 — Offline TM visibility, TM paste, folder 404 — v2.0

- ✓ MOCK-01 through MOCK-08 — Mock gamedata universe, StaticInfo XMLs, language data, cross-refs — v3.0
- ✓ CAT-01 through CAT-03 — Category classification, grid column, multi-select filter — v3.0
- ✓ QA-01 through QA-06 — Term Check, Line Check, inline QA badges, dismiss — v3.0
- ✓ AISUG-01 through AISUG-05 — AI translation suggestions, blended confidence, graceful fallback — v3.0
- ✓ GDEV-01 through GDEV-07 — File explorer, hierarchical grid, inline edit, dynamic columns — v3.0
- ✓ CODEX-01 through CODEX-05 — Entity encyclopedia, semantic search, DDS/WEM media — v3.0
- ✓ MAP-04, MAP-05 — World map nodes, route connections, pan/zoom, Codex links — v3.0
- ✓ AINAME-01 through AINAME-03 — Naming coherence, FAISS similarity, Qwen3 suggestions — v3.0
- ✓ PLACEHOLDER-01 through PLACEHOLDER-03 — Styled SVG placeholders for missing media — v3.0
- ✓ SV5-01 through SV5-06 — VirtualGrid/LDM/TM callback props, zero createEventDispatcher, zero legacy on: — v3.1
- ✓ FIX-01 through FIX-11, TEST-01 — GameDev upload-path, audio fallback, NPC nav, tooltip, loading, QA badge, tree refresh — v3.1
- ✓ UX-01 through UX-05 — aria-expanded, tab dividers, PlaceholderImage div layout, image fallback, text wrap — v3.1
- ✓ TEST-E2E-01 through TEST-E2E-25 — 834 API test functions, 40 files, 275 endpoints, mock expansion — v3.1

- ✓ MARCH-01 through MARCH-04 — Merge internalization, no sys.path/importlib, PyInstaller-safe, all 3 match types — v7.0
- ✓ TMAU-01 through TMAU-05 — TM auto-update: inline embedding + HNSW on add/edit/delete, batch import, immediate search — v7.0
- ✓ PERF-01 through PERF-06 — Performance instrumentation: PerfTimer on all hot paths, /api/performance/summary — v7.0
- ✓ UIUX-03 — Merge modal edge case hardening (retry, cancel, zero-match, error recovery) — v7.0
- ✓ TAG-01 through TAG-03 — Tag pills: 5-pattern detector, colored inline pills, display-only in VirtualGrid — v8.0
- ✓ SVC-01 through SVC-04 — Service extraction: 8 service classes from 8 thick route files — v8.0

- ✓ BUILD-01 through BUILD-04 — PyInstaller merge bundle, Light Build CI, Windows installer verified — v9.0
- ✓ MOCK-09 through MOCK-12 — Perforce-path mock gamedata (DDS/WEM/XML), all paths resolve — v9.0
- ✓ LDE2E-01, LDE2E-02, LDE2E-04 — Language data upload/edit/save round-trip, SQLite offline — v9.0
- ✓ FEAT-01 through FEAT-04, FEAT-07 — TM cascade, merge modes, QA checks, mock TM data — v9.0
- ✓ UIUX-01, UIUX-02 — Qwen3-VL visual audit all 5 pages (avg 8.6/10), critical fixes applied — v9.0
- ✓ FIX-01 through FIX-07 — Merge route conflict, test fixtures, CI gates, GSD artifacts — v9.0

### Active

- [ ] UI-101 — Hide br-tag linebreaks from grid display (merge auto-handles them)
- [ ] UI-102 — Combine color+format codes into single tag pill with color applied
- [ ] UI-103 — Grid default background → neutral/white (not yellow)
- [ ] UI-104 — Tag pill redesign — color-coded combined formatter tags
- [ ] LDE2E-03 — Language data with images/audio resolves from Perforce-like paths

### Out of Scope

- Full MT engine integration (Google/DeepL API) — LOCAL AI only, no cloud dependency
- WYSIWYG in-context preview — MapDataGenerator provides context
- Plugin/extension marketplace — Core must work first
- Automated workflow orchestration — Enterprise TMS feature
- Mobile app — Desktop-first
- Multi-language UI — Not planned

## Context

- **Shipped v1.0 + v2.0** in single-day sprints using GSD workflow with full power stack
- **NewScripts patterns fully ported** — XMLParsingEngine, merge engine, postprocess, export all based on battle-tested code
- **Dual platform** — Translator mode (LocStr files) + Game Dev mode (non-LocStr XML) with automatic detection
- **AI pipeline operational** — Qwen3-4B via Ollama at 117 tok/s (RTX 4070 Ti, CUDA in WSL2)
- **v3.0 shipped** — Game Dev Platform, Codex, World Map, AI Suggestions, QA Pipeline, Category Clustering, Naming Coherence, Mock GameData
- **v3.1 shipped** — Pure Svelte 5 Runes, 12 bug fixes, 60 UIUX audit fixes, 834 API E2E tests, 7 post-review fixes
- **v7.0 shipped** — Merge internalized (14 modules, PyInstaller-safe), TM auto-update inline (~6ms), PerfTimer on all hot paths, merge modal hardened
- **v8.0 shipped** — MemoQ-style tag pills (136 tests), 8 service classes extracted (net -2,173 LOC), Tribunal-driven architecture decisions
- **v9.0 shipped** — Build validated on Windows, 6 CVEs fixed, 12+ build fixes, Qwen3-VL visual audit (8.6/10 avg), 4 UI issues found for v10.0
- Landing page live on Netlify
- Tech stack: Electron + Svelte 5 (Runes) + FastAPI + SQLite/PostgreSQL + FAISS + Model2Vec + Qwen3/Ollama

## Constraints

- **Svelte 5 Runes only**: `$state`, `$derived`, `$effect` — no Svelte 4 patterns
- **Optimistic UI mandatory**: UI updates instantly, server syncs in background
- **No backend modifications**: Only wrapper layers (API, GUI) around core logic
- **Logger only**: Never `print()`, always `loguru`
- **XML newlines**: `<br/>` tags only, never `&#10;`
- **Sacred Scripts**: XLSTransfer, KR Similar, QuickSearch core logic — never modify
- **Excel libs**: xlsxwriter for writing, openpyxl only for reading
- **Build pipeline**: Gitea CI for LocaNext, GitHub Actions for NewScripts
- **Model2Vec ONLY** for embeddings — Qwen3 for AI summaries only
- **Research before implementing** — always read NewScripts source before writing new code

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Offline mode priority over online | Demo to executives without server dependency | ✓ Good — offline validated E2E |
| MapDataGenerator as first NewScripts integration | Most visual and impressive for demos | ✓ Good — image/audio tabs integrated |
| Model2Vec over Qwen for TM search | 79x faster, 12x smaller build | ✓ Good — sub-second semantic search |
| Aho-Corasick for entity detection | O(n) scan, proven in QuickSearch/QuickCheck | ✓ Good — real-time entity detection |
| v1.0 as scaffold with tests | Validate architecture before wiring real data | ✓ Good — v2.0 validated the approach |
| Dual UI via file type detection | LocStr nodes = Translator, other = Game Dev | ✓ Good — automatic, no user config needed |
| QuickTranslate logic for Translator merge | Proven match types, postprocess, CJK-safe | ✓ Good — 4 modes + 8-step pipeline ported exactly |
| Qwen3-4B for AI summaries | 117 tok/s local, zero cloud dependency | ✓ Good — graceful fallback when unavailable |
| Novel tree diff for Game Dev merge | No existing implementation, position-based needed | ✓ Good — parallel tree walk works correctly |
| httpx direct for Ollama (not ollama package) | Zero new dependencies, httpx already installed | ✓ Good — simple, reliable |
| Separate text_matching.py for merge | LocaNext's normalize_text differs from QuickTranslate's | ✓ Good — prevents matching bugs |
| Post-milestone code review | Catch issues before archiving | ✓ Good — found 11 real issues including 2 crashes |
| v3.0 post-milestone review | Same pattern as v2.0 | ✓ Good — found 9 issues (1 build-breaking, 2 critical) |
| d3-zoom for World Map | SVG pan/zoom for 14 nodes, no Leaflet needed | ✓ Good — lightweight, correct paradigm |
| Internalize QT modules (copy, not pip package) | Same repo, one consumer, avoids version ceremony | ✓ Good — tribunal 4/4 unanimous, 14 files clean |
| Direct inline FAISS updates (not event/queue) | ~6ms on GPU, single-user desktop app, immediacy required | ✓ Good — tribunal 3/4 for inline, search always fresh |
| IDMap2 wrapper for FAISS remove support | Plain HNSW can't remove vectors, edits need remove+add | ✓ Good — IndexIDMap2(IndexFlatIP) enables full CRUD |
| PerfTimer ring buffer (not external monitoring) | Zero deps, sufficient for desktop diagnostic use | ✓ Good — in-memory deque, numpy p50/p95/max |
| CodexService + FAISS for entity search | Reuse existing embedding infrastructure | ✓ Good — semantic search across all entity types |
| Route-handler category filtering | Keep repo layer clean, filter in Python | ✓ Good — simpler than DB-side filtering |
| gamedata/rows endpoint for direct XML loading | Game Dev entities come from XML files, not DB — no file_id exists | ✓ Good — POST with path, no DB dependency |
| Class-based services (Option A) | Tribunal unanimous: match SyncService pattern, testable, consistent | ✓ Good — 8 services extracted, route files 33-81% thinner |
| Tag pills = display-only render transform | Tribunal: raw text in DB, pills are frontend-only, no backend changes | ✓ Good — 136 tests verify round-trip integrity |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-03-25 after v9.0 milestone completion — archived, v10.0 planned*
