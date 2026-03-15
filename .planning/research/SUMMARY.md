# Project Research Summary

**Project:** LocaNext v3.0 -- Game Dev Platform + AI Intelligence
**Domain:** Game localization CAT tool with game dev authoring + AI intelligence
**Researched:** 2026-03-15
**Confidence:** HIGH

## Executive Summary

LocaNext v3.0 extends a production-ready localization platform (Electron + FastAPI + Svelte 5) with game dev authoring, AI-powered suggestions, an interactive game world encyclopedia (Codex), and integrated QA pipelines. The research confirms that nearly all v3.0 features can be built by extending existing infrastructure and porting proven NewScripts code -- the new dependency footprint is remarkably small (d3-zoom for map pan/zoom, Faker for mock data generation, and optionally piper-tts for placeholder audio). No new frameworks, no new databases, no architectural pivots. This is an assembly milestone, not an invention milestone.

The recommended approach is foundation-first: build the mock gamedata universe before any UI work, because every Game Dev feature depends on having realistic XML data to parse, display, and search. Three features (QA Term Check, QA Line Check, AI Translation Suggestions) are independent of game dev data and can be built in parallel with early phases. The Codex (interactive world map + character/item encyclopedia) is the crown jewel differentiator -- no competitor offers anything like it -- but it depends on entity data, media pipelines, and semantic search all being wired up first, making it a natural late-phase deliverable.

The key risks are concentrated in two areas: mock data XML format incompatibility with the existing XMLParsingEngine (mitigated by mandatory round-trip testing before any UI work), and AI suggestion rate limiting against slow LLM inference (mitigated by debouncing, request cancellation, and caching). The d3-zoom + Svelte integration for the world map requires discipline -- d3 must handle only transform math while Svelte owns the DOM -- but the pattern is well-documented. Everything else is porting proven code from QuickCheck, LanguageDataExporter, and QACompiler with minimal adaptation.

## Key Findings

### Recommended Stack

v3.0 requires almost no new dependencies. The existing stack (Electron, Svelte 5, FastAPI, SQLite/PostgreSQL, FAISS, Model2Vec, Qwen3/Ollama, lxml, Aho-Corasick, Pillow, vgmstream-cli) handles the vast majority of new features. The philosophy is "new prompts and endpoints, not new libraries."

**New technologies (only 3):**
- **d3-zoom + d3-selection** (~45KB): SVG pan/zoom transform math for the interactive world map -- Svelte renders DOM, d3 provides gesture handling and transform calculations only
- **Faker** (~1.5MB): Realistic mock data generation with Korean locale support for the mock gamedata universe -- contextually appropriate names and descriptions for executive demos
- **piper-tts** (OPTIONAL, ~55MB with voice model): Local neural TTS for placeholder audio -- make entirely optional with silence WAV fallback, defer if PyInstaller integration is problematic

**Explicitly not needed:** No new UI framework (Carbon covers everything), no new grid library (extend VirtualGrid), no tree-view library (Carbon TreeView), no geographic map library (fantasy XY positions, not lat/lng), no new AI library (httpx + Ollama already proven), no ML clustering (keyword heuristics work fine).

See `.planning/research/STACK.md` for full rationale and alternatives considered.

### Expected Features

**Must have (table stakes):**
- **T1: Mock gamedata universe** -- Foundation for all Game Dev features; Items, Characters, Regions, Skills with cross-references
- **T2: Category clustering** -- Auto-detect content type (Item/Quest/UI/Skill) from file path + XML structure
- **T3: QA term consistency** -- Port QuickCheck dual Aho-Corasick; flag glossary terms missing in translations
- **T4: QA line consistency** -- Port QuickCheck same-source-different-translation detection
- **T5: AI translation suggestions** -- Extend Qwen3 endpoint with ranked suggestions + confidence scores
- **T6: Game Dev Grid + file explorer** -- VS Code-like tree view for staticinfo XML with hierarchical editing

**Should have (differentiators -- no competitor offers these):**
- **D1: Game World Codex (encyclopedia)** -- Browsable character/item pages with images, audio, cross-references, semantic search
- **D2: Interactive world map** -- D3.js + SVG regions with clickable nodes linked to Codex entries
- **D3: AI naming coherence** -- Vector similarity + LLM analysis of naming patterns across entities
- **D4: Auto-generated placeholder images** -- Pillow colored placeholders with category icons for missing assets

**Defer to v4+:**
- Full CRUD in Game Dev Grid (create new XML nodes) -- schema validation too complex
- Cloud MT integration -- breaks offline-first competitive moat
- Real-time collaborative editing -- requires OT/CRDT
- Voice synthesis -- CJK quality too low in open-source models
- Spell/grammar check -- Qwen3-4B not reliable enough
- WYSIWYG in-context preview -- requires game engine integration
- Plugin marketplace -- premature
- XLIFF/TMX interchange -- orthogonal to v3.0 scope

See `.planning/research/FEATURES.md` for competitive positioning matrix and full anti-feature rationale.

### Architecture Approach

v3.0 adds 12 new backend files (6 services, 4 routes, 2 schema modules) and 11 new frontend files (5 components, 1 page, 2 stores, 2 API modules, 1 Codex sub-component set), while modifying 14 existing files. All new services follow the established singleton-with-lazy-init pattern. All new routes register through the existing router aggregation. The Codex is a new page within LDM (not a separate app), accessible via the existing navigation store.

**Major components:**
1. **gamedata_universe.py** -- Generates mock XML mimicking real staticinfo; reverse-engineers QACompiler generator patterns
2. **ai_suggestion_service.py** -- Single service for all AI suggestion modes (translate, naming, quality); shared Ollama client, shared cache
3. **qa_pipeline_service.py** -- Ports QuickCheck Term Check + Line Check; real-time single-row checks (<50ms) plus batch full-file scans
4. **codex_service.py** -- Aggregates entity data across all parsed files for encyclopedia views; uses Model2Vec + FAISS for semantic search
5. **GameDevGrid.svelte** -- Wraps/extends VirtualGrid's virtual scrolling; adds tree hierarchy rendering for XML nodes
6. **MapView.svelte** -- SVG world map with d3-zoom for pan/zoom; Svelte owns all DOM elements
7. **placeholder_generator.py** -- Pillow-based colored rectangles with text overlay; optional piper-tts for audio

See `.planning/research/ARCHITECTURE.md` for complete data flow diagrams, component boundaries, and anti-patterns.

### Critical Pitfalls

1. **Mock data XML incompatible with XMLParsingEngine** -- Subtle format differences (attribute order, encoding, `<br/>` handling) cause silent parsing failures. **Prevention:** Write round-trip integration test FIRST: generate -> parse -> assert all fields. Run before any UI work.
2. **d3-zoom fighting Svelte reactivity** -- Most d3 tutorials show d3 managing DOM, which breaks Svelte's reactive model. **Prevention:** Strict rule -- d3 provides transform object via callback, Svelte applies it. d3 never calls `.append()` or `.attr()`.
3. **AI suggestions without rate limiting** -- Rapid row navigation queues dozens of Ollama calls (2-5s each), freezing UI. **Prevention:** 500ms debounce, cancel in-flight requests, cache per source text, max 1 concurrent Ollama request.
4. **WorldPosition coordinate scale mismatch** -- Game engine units vary wildly; naive SVG mapping clusters all nodes. **Prevention:** Normalize to viewport using min/max scaling with padding.
5. **Piper-TTS in PyInstaller build** -- ONNX Runtime native dependencies may fail packaging. **Prevention:** Make entirely optional; silence WAV via Python `wave` module as MVP fallback.

See `.planning/research/PITFALLS.md` for full list including moderate and minor pitfalls with phase-specific warnings.

## Implications for Roadmap

Based on combined research, the recommended structure is 7 phases. The ordering is driven by a single critical dependency: mock gamedata (Phase 1) must exist before any Game Dev UI feature can be built or tested. Three features are independent of game dev data and should run early or in parallel.

### Phase 1: Mock Gamedata Universe
**Rationale:** Every Game Dev feature (T6, D1, D2, D3, D4) depends on having realistic XML data. Without it, nothing can be tested end-to-end. This is the critical path.
**Delivers:** Folder structure with Items, Characters, Regions, Skills as XML; matching LocStr translation files; mock texture/audio references; entity index in GlossaryService.
**Addresses:** T1 (Mock gamedata universe)
**Avoids:** Pitfall #1 (XML incompatibility) via mandatory round-trip test; Pitfall #10 (cross-reference inconsistency) via dependency-order generation.
**Stack:** lxml (existing), Faker (new), QACompiler generator patterns (reference).

### Phase 2: Category Clustering + QA Pipeline
**Rationale:** Low-risk, high-value features that enhance the EXISTING translator grid immediately. Category clustering needs Phase 1 data for game dev mode but works on translator data right away. QA pipeline is fully independent. Grouping these provides quick demo value before tackling complex UI work.
**Delivers:** Category column in grid with filterable tags; QA term consistency checks inline; QA line consistency checks in QAFooter.
**Addresses:** T2 (Category clustering), T3 (QA Term Check), T4 (QA Line Check)
**Avoids:** Pitfall #5 (clustering false positives) via full fallback chain port; Pitfall #6 (automaton build perf) via glossary-version caching.
**Stack:** Aho-Corasick (existing), LanguageDataExporter logic (port), QuickCheck logic (port).

### Phase 3: AI Translation Suggestions
**Rationale:** Independent of game dev data but benefits from Phase 1 entity embeddings for richer context. Table stakes in 2025-2026 -- every competitor now offers AI suggestions. Extends the proven Qwen3 pipeline with new prompts and a new UI tab.
**Delivers:** Ranked translation suggestions with confidence scores in RightPanel; user-click-to-accept (never auto-replace).
**Addresses:** T5 (AI Translation Suggestions)
**Avoids:** Pitfall #3 (rate limiting) via debounce + cancel + cache + max 1 concurrent.
**Stack:** Qwen3/Ollama (existing), Model2Vec + FAISS (existing), httpx (existing). Zero new dependencies.

### Phase 4: Game Dev Grid + File Explorer
**Rationale:** The core of the v3.0 promise. Highest UI complexity -- building after QA and AI means it integrates them from day one rather than retrofitting. Needs Phase 1 mock data to test against.
**Delivers:** VS Code-like file explorer for staticinfo folders; hierarchical XML node editing grid; integrated AI suggestions + QA checks on edit.
**Addresses:** T6 (Game Dev Grid + file explorer)
**Avoids:** Pitfall #8 (XML write-back corruption) by starting read + edit-in-memory only.
**Stack:** Carbon TreeView (existing), VirtualGrid extension (existing), XMLParsingEngine new `parse_full_tree()` method.

### Phase 5: Game World Codex (Encyclopedia)
**Rationale:** The highest "wow factor" feature and the primary differentiator. Depends on entity data indexed (Phase 1), media pipelines (v2.0), and semantic search (Phase 3 embeddings). No competitor offers an integrated interactive encyclopedia.
**Delivers:** Character browser with images, metadata, quest appearances; Item browser with similarity; Codex as new LDM page.
**Addresses:** D1 (Game World Codex -- Character/Item encyclopedia)
**Avoids:** Pitfall #9 (image loading waterfall) via intersection observer + placeholder colors.
**Stack:** Model2Vec + FAISS (existing), Pillow DDS->PNG (existing), codex_service.py (new).

### Phase 6: Interactive World Map
**Rationale:** The crown jewel visual demo. Depends on Codex entity pages (Phase 5) for click-through navigation and Phase 1 region position data. Very high complexity but limited scope (SVG rendering + d3-zoom math).
**Delivers:** Pan/zoom SVG map with positioned region nodes; hover tooltips; click-to-Codex navigation; connection lines between regions.
**Addresses:** D2 (Interactive world map)
**Avoids:** Pitfall #2 (d3 DOM fighting Svelte) via strict d3-math-only rule; Pitfall #4 (coordinate mismatch) via min/max viewport normalization; Pitfall #11 (SVG perf) acceptable at <200 nodes.
**Stack:** d3-zoom + d3-selection (new, ~45KB), raw SVG + Svelte 5 rendering.

### Phase 7: AI Naming Coherence + Placeholder Generation
**Rationale:** Polish and enhancement phase. AI naming coherence needs the full entity index from Phase 1 and embeddings from Phase 3. Placeholder generation is pure polish that makes the demo complete. Lowest priority but high visual impact.
**Delivers:** AI naming pattern analysis with similar-entity suggestions; Pillow-generated placeholder images for missing assets; placeholder audio (silence WAV or optional piper-tts).
**Addresses:** D3 (AI naming coherence), D4 (Auto-generated placeholder images)
**Avoids:** Pitfall #7 (piper-tts PyInstaller) by making TTS entirely optional with silence WAV fallback.
**Stack:** Model2Vec + FAISS (existing), Qwen3 (existing), Pillow (existing), optionally piper-tts (new).

### Phase Ordering Rationale

- **Phase 1 is non-negotiable as first** -- the dependency analysis shows T2, T6, D1, D2, D3, D4 all require mock data to function. Building any UI before data exists means testing against nothing.
- **Phases 2-3 enhance the existing grid** before building the new one, providing immediate demo value to both translator and game dev modes without waiting for the full Game Dev Grid.
- **Phase 4 (Game Dev Grid) comes after QA + AI** so it integrates those capabilities from day one rather than retrofitting them later.
- **Phases 5-6 (Codex + Map) are the visual showcase** -- they come last because they depend on everything else and represent the highest "wow" but require the most supporting infrastructure.
- **Phase 7 is polish** -- entirely safe to defer if timeline is tight.
- **Parallelization opportunity:** Phases 2 and 3 are fully independent and can execute in parallel. Within Phase 2, QA pipeline and category clustering are also independent of each other.

### Research Flags

**Phases likely needing deeper research during planning:**
- **Phase 1 (Mock Gamedata):** Needs careful study of QACompiler generator source code to reverse-engineer XML schemas. The mock data must be format-identical to real game output. Run `/gsd:research-phase` to inspect actual XML samples.
- **Phase 6 (World Map):** d3-zoom + Svelte 5 integration is documented but novel for this project. May benefit from a prototype spike before full planning.

**Phases with standard patterns (skip research-phase):**
- **Phase 2 (Category + QA):** Direct port of proven QuickCheck and LanguageDataExporter code. Patterns fully documented in NewScripts source.
- **Phase 3 (AI Suggestions):** Extends existing AISummaryService pattern. New prompts + new endpoint, not new architecture.
- **Phase 4 (Game Dev Grid):** Extends existing VirtualGrid and XMLParsingEngine. Well-understood component extension.
- **Phase 5 (Codex Encyclopedia):** Standard CRUD + search page. Carbon components cover all UI primitives.
- **Phase 7 (Naming + Placeholders):** Simple Pillow image generation + prompt engineering. No unknowns.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Minimal additions, all verified with current docs and npm/PyPI. Nearly everything reuses existing tech. |
| Features | MEDIUM-HIGH | Table stakes well-validated against 6 competitors. Codex/map are novel (no direct competitor reference) but validated by Eidos-Montreal internal Codex success. |
| Architecture | HIGH | All integration points verified against actual v2.0 source code (17 services, 22 routes, 25 components inspected). Patterns are extensions of proven v2.0 patterns. |
| Pitfalls | HIGH | Critical pitfalls identified from v2.0 post-milestone review lessons and library-specific documentation. Prevention strategies are concrete and testable. |

**Overall confidence:** HIGH

### Gaps to Address

- **WorldPosition data format:** Actual coordinate values from game XML have not been sampled. The normalization approach is sound but the specific scale/range is unknown until mock data or real samples are inspected. Address during Phase 1 by examining QACompiler Region generator output.
- **piper-tts PyInstaller compatibility:** No verified report of piper-tts working cleanly in a PyInstaller bundle. Decision: make it entirely optional and defer to post-v3.0 if packaging fails. Silence WAV is the MVP.
- **GameDevGrid complexity estimate:** The architecture flags this as "highest complexity" but the exact scope of VirtualGrid extension vs rewrite is uncertain. Address during Phase 4 planning by auditing VirtualGrid's internal architecture (4048+ lines).
- **Qwen3 prompt quality for naming coherence:** The naming pattern analysis (D3) depends on prompt engineering quality. No ground truth exists for "good naming suggestions." Address during Phase 7 with iterative prompt testing against mock data.

## Sources

### Primary (HIGH confidence)
- Codebase inspection: 17 services, 22 routes, 25 components in v2.0 source
- QACompiler generators (Item, Character, Region, Skill) at `RFC/NewScripts/QACompilerNEW/generators/`
- QuickCheck core (Term Check, Line Check) at `RFC/NewScripts/QuickCheck/core/`
- LanguageDataExporter clustering at `RFC/NewScripts/LanguageDataExporter/clustering/`
- [d3-zoom npm](https://www.npmjs.com/package/d3-zoom), [Faker PyPI](https://pypi.org/project/Faker/)
- [Owlcat LocalizationTool (GitHub)](https://github.com/OwlcatGames/LocalizationTool) -- open source competitor
- [Eidos-Montreal Codex GDC 2022](https://www.gamedeveloper.com/marketing/behind-codex-the-tool-powering-the-dialogue-of-i-marvel-s-guardians-of-the-galaxy-i-) -- validates Codex concept

### Secondary (MEDIUM confidence)
- [memoQ Game Localization](https://www.memoq.com/solutions/game-localization/), [Gridly Platform](https://www.gridly.com/), [Xbench](https://www.xbench.net/) -- vendor feature claims for competitive analysis
- [DMM Game Translate GDC 2025](https://dmm-game-translate.medium.com/) -- AI agents for game localization
- [piper-tts GitHub](https://github.com/rhasspy/piper) -- TTS capabilities and model sizes
- [Svelte D3 integration patterns](https://datavisualizationwithsvelte.com/) -- reference for Phase 6

### Tertiary (LOW confidence)
- piper-tts PyInstaller compatibility -- inferred from GitHub issues, not verified firsthand

---
*Research completed: 2026-03-15*
*Ready for roadmap: yes*
