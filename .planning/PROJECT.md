# LocaNext — Real Data CAT Tool + Game Dev Platform

## What This Is

LocaNext is a desktop localization management platform (Electron + FastAPI + Svelte 5) for game localization teams AND game developers. It handles real XML parsing from game data files, dual UI modes (Translator vs Game Dev), translation memory management with 4-mode merge engine, semantic search, entity-aware context panels with AI summaries, integrated QA, DDS image / WEM audio preview, and XML-based language data editing. v2.0 ships with production-ready data pipelines ported from 5 proven NewScripts projects, local AI via Qwen3, and full offline/online parity.

## Core Value

The platform delivers real, working localization workflows — real XML parsing, real merge logic matching QuickTranslate patterns, real image/audio from game data, and AI-powered context summaries — all running locally with zero cloud dependency, dual-mode for both translators and game developers, polished enough to demo to executives.

## Current State (v3.0 shipped 2026-03-16)

- v1.0: 7 phases, 20 plans, 42 requirements — architecture scaffolds + tests
- v2.0: 8 phases, 17 plans, 40 requirements — real data pipelines + merge + AI
- v3.0: 7 phases, 14 plans, 45 requirements — game dev platform + AI intelligence
- ~200+ LDM tests, 89 commits, 25K+ lines added in v3.0
- 7 new services (Category, AISuggestion, GameDataBrowse, GameDataEdit, Codex, WorldMap, NamingCoherence)
- 3 new pages (GameDevPage, CodexPage, WorldMapPage), 12 new Svelte components
- Post-milestone review: 9 issues found and fixed (1 build-breaking, 2 critical, 6 important)
- Full offline/online parity maintained across all three milestones

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

### Active

(No active milestone — v3.0 complete. Run `/gsd:new-milestone` for v4.0.)

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
| CodexService + FAISS for entity search | Reuse existing embedding infrastructure | ✓ Good — semantic search across all entity types |
| Route-handler category filtering | Keep repo layer clean, filter in Python | ✓ Good — simpler than DB-side filtering |

---
*Last updated: 2026-03-16 after v3.0 milestone completed*
