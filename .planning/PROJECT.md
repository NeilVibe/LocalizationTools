# LocaNext — Real Data CAT Tool + Game Dev Platform

## What This Is

LocaNext is a desktop localization management platform (Electron + FastAPI + Svelte 5) for game localization teams AND game developers. v1.0 delivered the architecture scaffold with tests. v2.0 wires real XML parsing from NewScripts, adds dual UI modes (Translator vs Game Dev), implements actual merge/export logic, and enables AI context summaries via local Qwen3 — transforming the scaffolded demo into a production-capable tool with real game data flowing end-to-end.

## Core Value

The platform delivers real, working localization workflows — not scaffolds: real XML parsing, real merge logic matching QuickTranslate patterns, real image/audio from game data, and AI-powered context summaries — all running locally with zero cloud dependency, dual-mode for both translators and game developers.

## Current Milestone: v2.0 Real Data + Dual Platform

**Goal:** Wire real XML parsing, merge/export logic, dual UI modes, and AI summaries — replacing v1.0 scaffolds with production-ready data pipelines sourced from proven NewScripts patterns.

**Target features:**
- Dual UI detection (Translator vs Game Dev based on file type)
- Real XML parsing using all 10 patterns from NewScripts
- DDS→PNG image conversion + WEM audio playback
- Translator merge with QuickTranslate exact logic
- Game Dev position-aware XML merge
- AI context summaries via Qwen3-4B/8B (Ollama)
- CLI toolkit expansion for full API coverage
- Bug fixes (offline TMs, TM paste, 404 on folder fetch)

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

(Defined in REQUIREMENTS.md for v2.0)

### Out of Scope

- Full MT engine integration (Google/DeepL API) — LocaNext differentiates with LOCAL AI (Qwen), not API wrappers
- WYSIWYG in-context preview — MapDataGenerator provides context without the nightmare
- Plugin/extension marketplace — Core must work first
- Automated workflow orchestration — Enterprise TMS feature
- Mobile app — Desktop-first
- Multi-language UI — Not planned
- Game World Codex (Interactive Encyclopedia) — v3.0 milestone (needs all XML parsing wired first)
- Game Dev Grid full CRUD — v2.0 focuses on read + edit, full create/nest in v3.0
- AI Translation Suggestions — v3.0 (needs LLM endpoint + embedding index mature)
- AI Naming Suggestions — v3.0 (depends on AI Translation foundation)
- Auto-generate missing images/audio — v3.0 (Nano Banana + voice synthesis)

## Context

- **Shipped v1.0** with 7 phases — scaffolds + tests covering stability, editor, TM workflow, semantic search, visual polish, contextual intelligence, offline validation
- **v2.0 is the "make it real" milestone** — wire actual XML parsing, real merge logic, real image/audio pipeline, AI summaries
- **NewScripts are the source of truth** — MapDataGenerator, QACompiler, LanguageDataExporter, QuickCheck, QuickTranslate all have battle-tested patterns to reuse
- 10 XML parsing patterns documented in memory (reference_xml_parsing_patterns.md)
- Qwen3-4B/8B available via Ollama at 117 tok/s (RTX 4070 Ti, 12GB VRAM, CUDA in WSL2)
- Landing page live on Netlify
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
- **Model2Vec ONLY** for embeddings (not Qwen) — Qwen3 for AI summaries only
- **Research before implementing** — always read NewScripts source before writing new code
- **YOLO mode** — auto-approve all checkpoints

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
| v1.0 as scaffold with tests | Validate architecture before wiring real data | ✓ Good — v2.0 now wires real data |
| Dual UI via file type detection | LocStr nodes = Translator, other = Game Dev | — Pending v2.0 |
| QuickTranslate logic for Translator merge | Proven match types, postprocess, CJK-safe | — Pending v2.0 |
| Qwen3-4B for AI summaries | 117 tok/s local, zero cloud dependency | — Pending v2.0 |

---
*Last updated: 2026-03-15 after v2.0 milestone start*
