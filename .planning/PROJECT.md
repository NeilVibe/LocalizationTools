# LocaNext — Demo-Ready CAT Tool

## What This Is

LocaNext is a desktop localization management platform (Electron + FastAPI + Svelte 5) that provides a Language Data Manager (CAT tool) for game localization teams. It handles file uploads, translation memory management, semantic search, entity-aware context panels, integrated QA (Line Check, Term Check), and XML-based language data editing. v1.0 shipped with full offline/online parity, executive-demo-ready polish, and Aho-Corasick entity detection.

## Core Value

The CAT tool delivers a flawless end-to-end localization workflow — upload files, automatically organize TMs mirroring the folder structure, search/edit translations with rich game context, and export — working seamlessly in both offline and online modes, polished enough to demo to executives.

## Current State (v1.0 shipped 2026-03-15)

- 7 phases, 20 plans, 42 requirements — all complete
- 115+ commits in milestone sprint
- 451+ repository parity tests, E2E Playwright tests, XML round-trip tests
- Full offline/online mode parity validated
- Aho-Corasick entity detection, MapDataGenerator integration, semantic search

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

### Active

(To be defined in v2.0 milestone — `/gsd:new-milestone`)

### Out of Scope

- Full MT engine integration (Google/DeepL API) — LocaNext differentiates with LOCAL AI (Qwen), not API wrappers
- WYSIWYG in-context preview — MapDataGenerator provides context without the nightmare
- Plugin/extension marketplace — Core must work first
- Automated workflow orchestration — Enterprise TMS feature
- Mobile app — Desktop-first
- Multi-language UI — Not planned

## Context

- **Shipped v1.0** with 7 phases covering stability, editor, TM workflow, semantic search, visual polish, contextual intelligence, and offline validation
- v1.0 is scaffold/test-focused — wires real patterns but uses mock data and test fixtures
- **v2.0 goals** (from memory): Wire real XML parsing, merge logic, dual UI (Translator vs Game Dev), AI summaries via Qwen3
- Landing page live on Netlify with cinematic design
- Tech stack: Electron + Svelte 5 (Runes) + FastAPI + SQLite/PostgreSQL + FAISS + Model2Vec

## Constraints

- **Svelte 5 Runes only**: `$state`, `$derived`, `$effect` — no Svelte 4 patterns
- **Optimistic UI mandatory**: UI updates instantly, server syncs in background
- **No backend modifications**: Only wrapper layers (API, GUI) around core logic
- **Logger only**: Never `print()`, always `logger`
- **XML newlines**: `<br/>` tags only, never `&#10;`
- **Sacred Scripts**: XLSTransfer, KR Similar, QuickSearch core logic — never modify
- **Excel libs**: xlsxwriter for writing, openpyxl only for reading
- **Build pipeline**: Gitea CI for LocaNext, GitHub Actions for NewScripts

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Offline mode priority over online | Demo to executives without server dependency | ✓ Good — offline validated E2E |
| MapDataGenerator as first NewScripts integration | Most visual and impressive for demos | ✓ Good — image/audio tabs integrated |
| Full UI rework in this milestone | Can't demo with rough UI | ✓ Good — CSS polish, custom scrollbars, transitions |
| Model2Vec over Qwen for TM search | 79x faster, 12x smaller build | ✓ Good — sub-second semantic search |
| Aho-Corasick for entity detection | O(n) scan, proven in QuickSearch/QuickCheck | ✓ Good — real-time entity detection |
| Custom LCS diff over diff-match-patch | Zero deps, CJK syllable-level tokenization | ✓ Good — accurate word diffs |
| QA footer as persistent panel | Always visible regardless of active tab | ✓ Good — natural QA workflow |
| Auto-mirror at folder-level scope | Simplest TM-per-folder approach | ✓ Good — clean UX |
| v1.0 as scaffold with tests | Validate architecture before wiring real data | — Pending v2.0 validation |

---
*Last updated: 2026-03-15 after v1.0 milestone*
