# Roadmap: LocaNext Demo-Ready CAT Tool

## Overview

LocaNext has a mature architecture but incomplete implementation. The path to demo-ready follows natural dependency order: stabilize the server foundation, build the performant editor grid, complete the TM workflow, layer in search and AI differentiators, polish the UI with settings and MapDataGenerator integration, then validate the entire experience works flawlessly offline. Each phase delivers a coherent, testable capability that builds on the previous one.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Stability Foundation** - Server starts reliably, DB layer works correctly across SQLite and PostgreSQL, no zombie processes (completed 2026-03-14)
- [x] **Phase 2: Editor Core** - Production-quality translation grid with virtual scrolling, editing, search/filter, export, and segment status (completed 2026-03-14)
- [x] **Phase 3: TM Workflow** - TM tree auto-mirrors file structure, TM assignment and lookup with match percentages, semantic matching (completed 2026-03-14)
- [ ] **Phase 4: Search and AI Differentiators** - Semantic search UI powered by Model2Vec, near-instant search performance, AI-matched translation indicators
- [ ] **Phase 5: Visual Polish and Integration** - Settings UI, MapDataGenerator in the grid, overall visual quality matching landing page
- [ ] **Phase 5.1: Contextual Intelligence & QA Engine** - INSERTED - Aho-Corasick entity detection (reuse QuickSearch/QuickCheck logic), auto glossary extraction, context panel, QA capabilities (Line Check, Term Check), category clustering, AI Translated status
- [ ] **Phase 6: Offline Demo Validation** - Offline mode works flawlessly for the full demo narrative, mode switching is transparent

## Phase Details

### Phase 1: Stability Foundation
**Goal**: The server and data layer are rock-solid -- every startup succeeds, both database backends work identically, and no processes leak
**Depends on**: Nothing (first phase)
**Requirements**: STAB-01, STAB-02, STAB-03, STAB-04, STAB-05
**Success Criteria** (what must be TRUE):
  1. Server starts successfully on first attempt, every time, with no error output
  2. All repository interfaces return identical results when tested against SQLite and PostgreSQL with the same input data
  3. Shutting down the app (normal close, force quit, crash) leaves zero orphaned Python processes
  4. SQLite and PostgreSQL schemas produce identical behavior for all CRUD operations used by the app
**Plans:** 3/3 plans complete

Plans:
- [ ] 01-01-PLAN.md -- Test infrastructure, schema drift guard, and terminology rename
- [ ] 01-02-PLAN.md -- Repository parity tests for all 9 interfaces (3 modes x ~95 methods)
- [ ] 01-03-PLAN.md -- Startup reliability tests, zombie process tests, and stop script

### Phase 2: Editor Core
**Goal**: Users can open a file and work in a fast, professional translation grid -- editing, saving, searching, filtering, and exporting segments
**Depends on**: Phase 1
**Requirements**: EDIT-01, EDIT-02, EDIT-03, EDIT-04, EDIT-05, EDIT-06, UI-01
**Success Criteria** (what must be TRUE):
  1. User can open a 10K+ segment file and scroll through it without any visible lag or jank
  2. User can edit a segment, press Ctrl+S, and the save completes without overflowing content into the next row
  3. User can filter segments by status (confirmed/draft/empty) and search by text, seeing results update in the grid
  4. User can export translated segments and the output file is structurally identical to the input (preserving XML structure, attributes, and br-tags)
  5. Each segment row displays a clear color-coded status indicator (green=confirmed, yellow=draft, gray=empty)
**Plans:** 3 plans

Plans:
- [ ] 02-01-PLAN.md -- Fix Ctrl+S save overflow bug, 3-state status colors, editing reliability
- [ ] 02-02-PLAN.md -- Search/filter verification, export round-trip validation with br-tags
- [ ] 02-03-PLAN.md -- Performance validation for 10K+ segments, UI visual polish to demo-ready

### Phase 3: TM Workflow
**Goal**: Users can manage Translation Memories through a mirrored tree structure, assign TMs to files, and see match results with quality indicators
**Depends on**: Phase 2
**Requirements**: TM-01, TM-02, TM-03, TM-04, TM-05, UI-02, UI-03
**Success Criteria** (what must be TRUE):
  1. When user uploads files into a folder structure, the TM tree automatically mirrors that same structure
  2. User can assign a TM to a folder or file through the TM tree, and the assignment is visible and persistent
  3. When user selects a segment, TM matches appear with color-coded percentages (green=100%, yellow=fuzzy, red=no match) and word-level diff highlighting
  4. User can see per-file TM leverage statistics showing exact, fuzzy, and new match percentages
  5. File explorer and TM explorer tree views look polished and professional (not raw component defaults)
**Plans:** 3/3 plans complete

Plans:
- [ ] 03-01-PLAN.md -- Backend TM auto-mirror hook, leverage stats API, TM search cascade verification
- [ ] 03-02-PLAN.md -- Tabbed right panel, color-coded TM matches with word-level diff, explorer CSS polish
- [ ] 03-03-PLAN.md -- End-to-end integration wiring, leverage display, assignment E2E, visual checkpoint

### Phase 4: Search and AI Differentiators
**Goal**: Users can find translations by meaning (not just exact text) using Model2Vec, with near-instant performance and clear AI-matched indicators
**Depends on**: Phase 3
**Requirements**: SRCH-01, SRCH-02, SRCH-03, AI-01, AI-02
**Success Criteria** (what must be TRUE):
  1. User can search for a concept and find relevant translations even when the wording differs from the query
  2. Semantic search UI prominently showcases the "find similar" capability with similarity scores and relevance ranking
  3. Search results return in under one second for typical TM sizes (Model2Vec is 79x faster than alternatives)
  4. Model2Vec powers the entire semantic pipeline — TM matching, search, entity detection
  5. AI-matched translations are clearly indicated in the editor
**Plans:** 2 plans

Plans:
- [ ] 04-01-PLAN.md -- Backend semantic search endpoint with TMSearcher wiring, unit tests, performance validation
- [ ] 04-02-PLAN.md -- Frontend semantic search UI with similarity scores overlay, AI-suggested badges, E2E tests

### Phase 5: Visual Polish and Integration
**Goal**: The app looks executive-demo-ready with settings management, MapDataGenerator context in the grid, and overall visual quality matching the cinematic landing page
**Depends on**: Phase 4
**Requirements**: UI-04, UI-05, MAP-01, MAP-02, MAP-03
**Success Criteria** (what must be TRUE):
  1. Settings UI allows configuring branches, drives, and metadata reading preferences
  2. Image references from MapDataGenerator are visible directly in translation grid rows alongside their segments
  3. Audio references from MapDataGenerator are visible directly in translation grid rows alongside their segments
  4. MapDataGenerator data feels organically integrated into the grid, not like a bolted-on separate tool
  5. Overall visual quality (typography, spacing, colors, transitions) is consistent and polished across all views
**Plans**: TBD

Plans:
- [ ] 05-01: TBD
- [ ] 05-02: TBD

### Phase 5.1: Contextual Intelligence & QA Engine (INSERTED)
**Goal**: The editor becomes context-aware — auto-detecting entities via Aho-Corasick (reusing proven QuickSearch/QuickCheck logic), surfacing rich game context, AND providing integrated QA capabilities (Line Check, Term Check) so translators catch inconsistencies without leaving LocaNext
**Depends on**: Phase 5
**Requirements**: CTX-01, CTX-02, CTX-03, CTX-04, CTX-05, CTX-06, CTX-07, CTX-08, CTX-09, CTX-10, QA-01, QA-02, QA-03

**Reuse Strategy** (CRITICAL — research before implementing):
  - **QuickSearch** (`RFC/NewScripts/QuickSearch/`): Aho-Corasick automaton (`core/term_check.py:build_automaton()`), glossary extraction with AC validation (`core/glossary.py:extract_glossary_with_validation()`), word boundary detection (`is_isolated_match()`), filter pipeline (`utils/filters.py:glossary_filter()`)
  - **QuickCheck** (`RFC/NewScripts/QuickCheck/`): LINE CHECK (`core/line_check.py`), TERM CHECK with dual AC automaton (`core/term_check.py`), multi-language folder scanning (`core/scanner.py`), Excel output writers (`utils/excel_writer.py`)
  - **Both projects share**: XML parser (`core/xml_parser.py`), preprocessing with KR/ENG BASE modes (`core/preprocessing.py`), language utilities (`utils/language_utils.py`)

**Glossary Extraction Parameters** (defaults from QuickSearch/QuickCheck):
  - `min_occurrence`: 2 (term must appear at least twice)
  - `max_term_length`: 25 chars (user override — QuickSearch default is 15, QuickCheck is 20)
  - `filter_sentences`: True (skip entries ending with `.?!`)
  - `match_mode`: ISOLATED only (word boundary check, no substring — prevents Korean compound false matches)
  - `max_issues_per_term`: 6 (noise filter for Term Check)

**Success Criteria** (what must be TRUE):
  1. Glossary automatically extracted from game data (QACompiler/LDE generators) — all character, location, item, skill names — using QuickSearch's `extract_glossary_with_validation()` pattern with min_occurrence=2, max_length=25, no sentences
  2. Aho-Corasick automaton built from glossary scans strings in real-time — "The warrior enters Stormhold Castle" instantly detects both entities — reusing QuickSearch's `build_automaton()` + `is_isolated_match()`
  3. Detected character names → context panel shows metadata (gender, age, job, race), quest info, audio samples (including indirect matches)
  4. Detected location names → context panel shows location images and map position from staticinfo
  5. Glossary terms mapped to staticinfo datapoints where images, DESC, and audio files can be found
  6. Category clustering auto-assigns string types using QACompiler/LanguageDataExporter technology
  7. "AI Translated" status visible in grid, distinguishing human from AI translations
  8. Context panel updates dynamically as user navigates between segments
  9. **LINE CHECK** integrated — same source translated differently flagged as inconsistency (reuse QuickCheck's `run_line_check()` logic)
  10. **TERM CHECK** integrated — glossary term in source but missing translation flagged (reuse QuickCheck's dual Aho-Corasick + noise filter logic)
  11. QA results displayed in a dedicated panel/tab within the editor, not as a separate tool
**Plans**: TBD

Plans:
- [ ] 05.1-01: TBD
- [ ] 05.1-02: TBD
- [ ] 05.1-03: TBD
- [ ] 05.1-04: TBD

### Phase 6: Offline Demo Validation
**Goal**: The complete demo narrative works flawlessly offline -- user can disconnect network and continue working through the entire upload-translate-search-export flow without interruption
**Depends on**: Phase 5
**Requirements**: OFFL-01, OFFL-02, OFFL-03
**Success Criteria** (what must be TRUE):
  1. User can disconnect from the network and continue uploading, editing, searching, and exporting without any error or degraded behavior
  2. All features delivered in Phases 2-5 function identically in offline mode (SQLite) as they do in online mode (PostgreSQL)
  3. Mode switching happens transparently -- user never needs to manually configure or toggle between online and offline
**Plans**: TBD

Plans:
- [ ] 06-01: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 5.1 -> 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Stability Foundation | 3/3 | Complete    | 2026-03-14 |
| 2. Editor Core | 3/3 | Complete | 2026-03-14 |
| 3. TM Workflow | 3/3 | Complete   | 2026-03-14 |
| 4. Search and AI Differentiators | 0/2 | Planned | - |
| 5. Visual Polish and Integration | 0/2 | Not started | - |
| 5.1. Contextual Intelligence & QA Engine | 0/4 | Not started | - |
| 6. Offline Demo Validation | 0/1 | Not started | - |
