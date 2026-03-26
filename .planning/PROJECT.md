# LocaNext — Real Data CAT Tool + Game Dev Platform

## What This Is

LocaNext is a desktop localization management platform (Electron + FastAPI + Svelte 5) for game localization teams AND game developers. It handles real XML parsing from game data files, dual UI modes (Translator vs Game Dev), translation memory management with 4-mode merge engine, semantic search, entity-aware context panels with AI summaries, integrated QA, DDS image / WEM audio preview, and XML-based language data editing. v2.0 ships with production-ready data pipelines ported from 5 proven NewScripts projects, local AI via Qwen3, and full offline/online parity.

## Core Value

The platform delivers real, working localization workflows — real XML parsing, real merge logic matching QuickTranslate patterns, real image/audio from game data, and AI-powered context summaries — all running locally with zero cloud dependency, dual-mode for both translators and game developers, polished enough to demo to executives.

## Current Milestone: v13.0 Production Path Resolution

**Goal:** Wire real Perforce path resolution for image/audio in LanguageData grid, with Branch+Drive selection, path validation, mock testing, and fix deferred code issues.

**Target features:**
- [ ] FIX-01: Fix 4 v11.0 code review issues (onScrollToRow race, visibleColumns dead code, onSaveComplete, tmSuggestions)
- [ ] PATH-01: Branch + Drive selector UI (like QACompiler/MapDataGenerator)
- [ ] PATH-02: Path validation — verify data availability (OK/NOT OK with details)
- [ ] PATH-03: Wire LanguageData StringID → GameData entity → DDS image path resolution
- [ ] PATH-04: Wire LanguageData StringID → GameData entity → WEM audio path resolution
- [ ] MOCK-01: Mock Perforce paths on local machine (relative, drive-agnostic)
- [ ] MOCK-02: E2E tests with mocked Perforce structure
- [ ] ARCH-02: Split mega_index.py (1310 lines) into domain services

**Research needed:** MapDataGenerator path patterns, QACompiler branch/drive selection, LanguageDataExporter path conventions, path validation logic.

## Shipped: v12.0 TM Intelligence (2026-03-26)

<details>
<summary>v12.0 details (click to expand)</summary>

- 3 phases, 4 plans, 25 tests
- Dual threshold: 62% context panel, 92% pretranslation (hardcoded)
- AC Context Engine: 3-tier cascade (whole AC, line AC, char n-gram Jaccard n={2,3,4,5})
- Bigram inverted index pre-filter for <100ms at 1000+ entries
- POST /api/ldm/tm/context endpoint, TMTab context section with tier badges
- 6 code review issues fixed

</details>

## Shipped: v11.0 Architecture & Test Infrastructure (2026-03-26)

<details>
<summary>v11.0 details (click to expand)</summary>

- 3 phases, 6 plans, 169 tests
- Vitest + @testing-library/svelte infrastructure for Svelte 5 components
- VirtualGrid.svelte decomposed: 4293→383 lines (91% reduction, 6 modules)
- Modules: ScrollEngine, CellRenderer, SelectionManager, InlineEditor, StatusColors, SearchEngine
- gridState.svelte.ts shared reactive state with Svelte 5 runes

</details>

## Shipped: v10.0 UI Polish + Tag Pill Redesign (2026-03-25)

<details>
<summary>v10.0 details (click to expand)</summary>

- 3 phases, 3 plans, 10 commits
- Tag pill overhaul: combinedcolor pattern, br-tag exclusion, dynamic hex-tinted pills
- Grid polish: neutral #222222 background, amber status contrast increased
- Qwen3-VL visual verification: avg 7.4/10, all 5 pages pass 7+
- Pure Svelte 5 frontend changes only (tagDetector.js, TagText.svelte, VirtualGrid.svelte)

</details>

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

## Current State (v11.0 shipped — 14 milestones complete)

- 14 milestones shipped (v1.0 through v11.0), 85 phases, ~159 plans
- v10.0: Tag pill overhaul (combinedcolor, br-tag exclusion), grid polish (#222222 neutral), Qwen3-VL 7.4/10
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

- ✓ TAG-04 through TAG-06 — Combined color+format tag pills, br-tag exclusion, pill CSS redesign — v10.0
- ✓ GRID-01 — Grid default background neutralized (#222222), amber status contrast increased — v10.0
- ✓ VIS-01 — Qwen3-VL visual verification all 5 pages (avg 7.4/10, all 7+) — v10.0

- ✓ TEST-01 through TEST-06 — Vitest + @testing-library/svelte infrastructure, tagDetector.js + TagText.svelte + StatusColors tests — v11.0
- ✓ GRID-02 through GRID-08 — VirtualGrid decomposed into 6 modules (ScrollEngine, CellRenderer, SelectionManager, InlineEditor, StatusColors, SearchEngine), regression verified — v11.0
- ✓ ARCH-01 — VirtualGrid.svelte decomposed (4293→383 lines, 91% reduction) — v11.0
- ✓ ARCH-04 — Unit test infrastructure for Svelte 5 components (Vitest, 169 tests) — v11.0

- ✓ TMUI-01 — Dual threshold system (62% context panel, 92% pretranslation, hardcoded) — v12.0
- ✓ TMUI-02 — TM Tab UI polish with prominent match percentage badges (4-tier color bands) — v12.0
- ✓ ACCTX-01 — AC Context Search 3-tier cascade with AC automatons built on TM load — v12.0
- ✓ ACCTX-02 — Row-select triggers AC context search, results in right panel with tier badges — v12.0
- ✓ ACCTX-03 — Character n-gram {2,3,4,5} space-stripped Korean, Jaccard ≥62%, bigram pre-filter — v12.0
- ✓ ACCTX-04 — Context results with tier indicators (Exact/Line/Fuzzy) and score percentages — v12.0
- ✓ PERF-01 — AC context search <100ms for 1000+ TM entries (bigram inverted index optimization) — v12.0

### Active

- [ ] FIX-01 — Fix 4 v11.0 code review issues (onScrollToRow race, dead code, missing callbacks)
- [ ] PATH-01 — Branch + Drive selector UI (like QACompiler/MapDataGenerator)
- [ ] PATH-02 — Path validation with OK/NOT OK status and missing data details
- [ ] PATH-03 — LanguageData StringID → GameData → DDS image path resolution
- [ ] PATH-04 — LanguageData StringID → GameData → WEM audio path resolution
- [ ] MOCK-01 — Mock Perforce paths on local machine (relative, drive-agnostic)
- [ ] MOCK-02 — E2E tests with mocked Perforce path structure
- [ ] ARCH-02 — Split mega_index.py (1310 lines) into domain services

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
- **v10.0 shipped** — Tag pill overhaul (combinedcolor + br-tag exclusion), grid neutral background, Qwen3-VL 7.4/10
- **v11.0 shipped** — Vitest infrastructure (169 tests), VirtualGrid decomposed 4293→383 lines (6 modules), regression verified
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
| Combined color+format pills (priority-0 pattern) | Prevents braced pattern from claiming inner {code} | ✓ Good — dynamic hex-tinted inline pills |
| Grid neutral background #222222 | Yellow/amber status-translated was dominant visual | ✓ Good — clear neutral baseline, amber stands out |
| v11.0 = ARCH-04 + ARCH-01 (Tribunal decision) | Split without tests = blind surgery; tests first, split second | ✓ Good — 169 tests, 91% VG reduction |
| Char n-gram {2,3,4,5} for Korean (NLP research) | Korean syllable blocks = high info density; bigrams capture compound nouns; n=4,5 for longer terms | — Pending |
| AC automaton from TM whole_lookup + line_lookup | Data already in memory; build once on TM load, O(n) scan per row | — Pending |

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
*Last updated: 2026-03-26 after v13.0 milestone initialization*
