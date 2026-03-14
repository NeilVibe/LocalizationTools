# Roadmap: LocaNext Demo-Ready CAT Tool

## Overview

LocaNext has a mature architecture but incomplete implementation. The path to demo-ready follows natural dependency order: stabilize the server foundation, build the performant editor grid, complete the TM workflow, layer in search and AI differentiators, polish the UI with settings and MapDataGenerator integration, then validate the entire experience works flawlessly offline. Each phase delivers a coherent, testable capability that builds on the previous one.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Stability Foundation** - Server starts reliably, DB layer works correctly across SQLite and PostgreSQL, no zombie processes
- [ ] **Phase 2: Editor Core** - Production-quality translation grid with virtual scrolling, editing, search/filter, export, and segment status
- [ ] **Phase 3: TM Workflow** - TM tree auto-mirrors file structure, TM assignment and lookup with match percentages, semantic matching
- [ ] **Phase 4: Search and AI Differentiators** - Semantic search UI, local AI pretranslation with Qwen, near-instant search performance
- [ ] **Phase 5: Visual Polish and Integration** - Settings UI, MapDataGenerator in the grid, overall visual quality matching landing page
- [ ] **Phase 5.1: Contextual Intelligence** - INSERTED - Auto-detect characters, locations, items within strings; show rich context (images, audio, metadata, map positions); category clustering; AI Translated status
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
**Plans**: TBD

Plans:
- [ ] 01-01: TBD
- [ ] 01-02: TBD

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
**Plans**: TBD

Plans:
- [ ] 02-01: TBD
- [ ] 02-02: TBD
- [ ] 02-03: TBD

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
**Plans**: TBD

Plans:
- [ ] 03-01: TBD
- [ ] 03-02: TBD
- [ ] 03-03: TBD

### Phase 4: Search and AI Differentiators
**Goal**: Users can find translations by meaning (not just exact text) and get AI-generated pretranslations from a local model with zero cloud dependency
**Depends on**: Phase 3
**Requirements**: SRCH-01, SRCH-02, SRCH-03, AI-01, AI-02
**Success Criteria** (what must be TRUE):
  1. User can search for a concept and find relevant translations even when the wording differs from the query
  2. Semantic search UI prominently showcases the "find similar" capability with similarity scores and relevance ranking
  3. Search results return in under one second for typical TM sizes
  4. User can trigger AI pretranslation on untranslated segments and see results marked with a clear "AI-suggested" indicator
  5. AI pretranslation works entirely offline with the local Qwen model (no network request made)
**Plans**: TBD

Plans:
- [ ] 04-01: TBD
- [ ] 04-02: TBD

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

### Phase 5.1: Contextual Intelligence (INSERTED)
**Goal**: The editor becomes context-aware — auto-detecting characters, locations, and items within strings and surfacing rich game context (images, audio, metadata, map positions) that makes translators smarter and executives say "wow"
**Depends on**: Phase 5
**Requirements**: CTX-01, CTX-02, CTX-03, CTX-04, CTX-05, CTX-06, CTX-07, CTX-08
**Success Criteria** (what must be TRUE):
  1. When a string contains a character name, the context panel shows character metadata (gender, age, job, race) and quest/interaction information
  2. When a string contains a location name (castle, city, etc.), the context panel shows location images and map position
  3. Audio samples appear for detected characters — including samples not directly linked to the current StringID
  4. Vectorial n-gram analysis detects multiple entities within a single sentence (e.g., "The warrior enters the castle" → character info + location info)
  5. Category clustering auto-assigns string types using QACompiler/LanguageDataExporter technology
  6. "AI Translated" status is visible in the grid, distinguishing human from AI translations
  7. Context panel updates dynamically as user navigates between segments
**Plans**: TBD

Plans:
- [ ] 05.1-01: TBD
- [ ] 05.1-02: TBD
- [ ] 05.1-03: TBD

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
| 1. Stability Foundation | 0/2 | Not started | - |
| 2. Editor Core | 0/3 | Not started | - |
| 3. TM Workflow | 0/3 | Not started | - |
| 4. Search and AI Differentiators | 0/2 | Not started | - |
| 5. Visual Polish and Integration | 0/2 | Not started | - |
| 5.1. Contextual Intelligence | 0/3 | Not started | - |
| 6. Offline Demo Validation | 0/1 | Not started | - |
