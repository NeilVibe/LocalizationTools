# Roadmap: LocaNext

## Milestones

- v1.0 Demo-Ready CAT Tool (Phases 01-06) -- SHIPPED 2026-03-15
- v2.0 Real Data + Dual Platform (Phases 07-14) -- IN PROGRESS

## Phases

<details>
<summary>v1.0 Demo-Ready CAT Tool (Phases 01-06) -- SHIPPED 2026-03-15</summary>

- [x] Phase 01: Stability Foundation (3/3 plans) -- completed 2026-03-14
- [x] Phase 02: Editor Core (3/3 plans) -- completed 2026-03-14
- [x] Phase 03: TM Workflow (3/3 plans) -- completed 2026-03-14
- [x] Phase 04: Search and AI Differentiators (2/2 plans) -- completed 2026-03-14
- [x] Phase 05: Visual Polish and Integration (2/2 plans) -- completed 2026-03-14
- [x] Phase 05.1: Contextual Intelligence & QA Engine (5/5 plans) -- completed 2026-03-14
- [x] Phase 06: Offline Demo Validation (2/2 plans) -- completed 2026-03-14

</details>

### v2.0 Real Data + Dual Platform

**Milestone Goal:** Wire real XML parsing, merge/export logic, dual UI modes, and AI summaries -- replacing v1.0 scaffolds with production-ready data pipelines sourced from proven NewScripts patterns.

- [x] **Phase 07: XML Parsing Foundation + Bug Fixes** - Replace stdlib ET with lxml, wire real XML parsing services, fix 3 v1.0 bugs (completed 2026-03-15)
- [x] **Phase 08: Dual UI Mode** - Auto-detect file type and switch between Translator and Game Dev column layouts (completed 2026-03-15)
- [x] **Phase 09: Translator Merge** - Port QuickTranslate merge logic (exact/source/fuzzy match + postprocess pipeline) (completed 2026-03-15)
- [x] **Phase 10: Export Pipeline** - XML, Excel, and plain text export with br-tag preservation (completed 2026-03-15)
- [x] **Phase 11: Image & Audio Pipeline** - DDS-to-PNG conversion, WEM audio playback, real data flowing to context tabs (completed 2026-03-15)
- [x] **Phase 12: Game Dev Merge** - Position-aware XML merge at node/attribute/children depth (completed 2026-03-15)
- [x] **Phase 13: AI Summaries** - Qwen3 via Ollama for contextual summaries with caching and graceful fallback (completed 2026-03-15)
- [x] **Phase 14: E2E Validation + CLI** - Round-trip integration tests and CLI coverage for merge/export operations (completed 2026-03-15)

## Phase Details

### Phase 07: XML Parsing Foundation + Bug Fixes
**Goal**: All XML game data files parse correctly through lxml with sanitization and recovery, and v1.0 bugs are eliminated
**Depends on**: v1.0 complete
**Requirements**: XML-01, XML-02, XML-03, XML-04, XML-05, XML-06, XML-07, FIX-01, FIX-02, FIX-03
**Success Criteria** (what must be TRUE):
  1. User opens a real KnowledgeInfo XML file and sees parsed StrKey-to-image chains in the context panel
  2. User opens a malformed XML file and the system recovers gracefully instead of crashing
  3. User opens a loc.xml file and all language columns (KR, EN, JP, etc.) are correctly extracted
  4. Offline TMs appear in the online TM tree, TM paste works end-to-end, and folder fetch returns 200 after creation
  5. GlossaryService builds an Aho-Corasick automaton from real staticinfo XML data
**Plans**: 3 plans

Plans:
- [ ] 07-01-PLAN.md -- XMLParsingEngine + xml_handler migration (XML-04, XML-06, XML-07)
- [ ] 07-02-PLAN.md -- Service wiring: MapData, Glossary, Context (XML-01, XML-02, XML-03, XML-05)
- [ ] 07-03-PLAN.md -- Bug fixes: offline TM, TM paste, folder 404 (FIX-01, FIX-02, FIX-03)

### Phase 08: Dual UI Mode
**Goal**: Users see the correct editor layout automatically based on the type of XML file they open
**Depends on**: Phase 07
**Requirements**: DUAL-01, DUAL-02, DUAL-03, DUAL-04, DUAL-05
**Success Criteria** (what must be TRUE):
  1. User opens a file with LocStr nodes and sees Translator columns (Source, Target, Status, Match%, TM Source)
  2. User opens a non-LocStr XML file and sees Game Dev columns (NodeName, Attributes, Values, Children count)
  3. Mode indicator in the editor header shows "Translator" or "Game Dev" matching the loaded file
  4. Switching between files of different types changes the column layout without leftover state from the previous mode
**Plans**: 2 plans

Plans:
- [ ] 08-01-PLAN.md -- Backend file type detection + Game Dev node parsing (DUAL-01, DUAL-03)
- [ ] 08-02-PLAN.md -- Frontend dual column configs + mode badge (DUAL-02, DUAL-04, DUAL-05)

### Phase 09: Translator Merge
**Goal**: Translators can merge translations between files using exact, source-text, and fuzzy matching with automatic post-processing
**Depends on**: Phase 07, Phase 08
**Requirements**: TMERGE-01, TMERGE-02, TMERGE-03, TMERGE-04
**Success Criteria** (what must be TRUE):
  1. User merges two loc.xml files and translations transfer correctly via exact StringID match
  2. User merges files where StringIDs differ but source text matches, and translations still transfer
  3. User triggers fuzzy merge and sees Model2Vec-based similar string matches above the configured threshold
  4. Merged translations pass through the 8-step CJK-safe postprocess pipeline (whitespace, br-tags, punctuation normalization)
**Plans**: 2 plans

Plans:
- [ ] 09-01-PLAN.md -- Text matching utilities + Korean detection + 8-step postprocess pipeline (TMERGE-04)
- [ ] 09-02-PLAN.md -- TranslatorMergeService with 4 match modes + skip guards + API endpoint (TMERGE-01, TMERGE-02, TMERGE-03)

### Phase 10: Export Pipeline
**Goal**: Users can export their translation work in XML, Excel, and plain text formats with full data integrity
**Depends on**: Phase 09
**Requirements**: TMERGE-05, TMERGE-06, TMERGE-07
**Success Criteria** (what must be TRUE):
  1. User exports to XML and br-tags round-trip correctly (no corruption, no entity encoding)
  2. User exports to Excel and sees the correct column structure (StrOrigin, ENG, Str, Correction, etc.)
  3. User exports to plain text and gets a clean StringID + source + translation tabulated format
**Plans**: 1 plan

Plans:
- [ ] 10-01-PLAN.md -- ExportService (XML/Excel/text) + route wiring (TMERGE-05, TMERGE-06, TMERGE-07)

### Phase 11: Image & Audio Pipeline
**Goal**: Users see real game images and hear game audio inline in the context panel
**Depends on**: Phase 07
**Requirements**: MEDIA-01, MEDIA-02, MEDIA-03, MEDIA-04
**Success Criteria** (what must be TRUE):
  1. User selects a string with a linked DDS texture and sees the converted PNG image in the Image tab
  2. User selects a string with a linked WEM audio file and can play it back in the Audio tab
  3. Real data flows from MapDataService through the API to the frontend Image/Audio tabs without mock fixtures
  4. Missing image or audio shows a styled placeholder with explanatory text instead of a broken icon
**Plans**: 2 plans

Plans:
- [ ] 11-01-PLAN.md -- MediaConverter service (DDS-to-PNG, WEM-to-WAV conversion + caching)
- [ ] 11-02-PLAN.md -- Thumbnail/audio stream endpoints + AudioTab wiring

### Phase 12: Game Dev Merge
**Goal**: Game developers can merge XML changes at the structural level (nodes, attributes, children) preserving document order
**Depends on**: Phase 07, Phase 08
**Requirements**: GMERGE-01, GMERGE-02, GMERGE-03, GMERGE-04, GMERGE-05
**Success Criteria** (what must be TRUE):
  1. User runs global export and sees all changed nodes identified across the entire file
  2. User merges at node level and nodes are correctly added, removed, or modified
  3. User merges at attribute level and individual attribute values update without affecting sibling attributes
  4. User merges a file with nested parent-children-sub-children and depth is preserved correctly
  5. Merged output preserves original XML document order (position-based, not match-type-based)
**Plans**: 2 plans

Plans:
- [ ] 12-01-PLAN.md -- GameDevMergeService: parallel tree walk diff + in-place apply (GMERGE-01, GMERGE-02, GMERGE-03, GMERGE-04, GMERGE-05)
- [ ] 12-02-PLAN.md -- bulk_update extra_data + gamedev-merge API endpoint (GMERGE-01, GMERGE-02, GMERGE-03, GMERGE-04, GMERGE-05)

### Phase 13: AI Summaries
**Goal**: Users see AI-generated contextual summaries for game entities powered by local Qwen3 with zero cloud dependency
**Depends on**: Phase 07
**Requirements**: AISUM-01, AISUM-02, AISUM-03, AISUM-04, AISUM-05
**Success Criteria** (what must be TRUE):
  1. User selects a character/item/region string and sees a 2-line contextual summary in the ContextTab
  2. Summaries are cached per StringID so re-selecting the same string loads instantly without re-generation
  3. When Ollama is not running, the ContextTab shows an "AI unavailable" badge instead of errors or spinners
  4. Qwen3 endpoint returns structured JSON that the frontend parses reliably
**Plans**: 2 plans

Plans:
- [ ] 13-01-PLAN.md -- AISummaryService + context endpoint wiring (AISUM-01, AISUM-02, AISUM-04, AISUM-05)
- [ ] 13-02-PLAN.md -- ContextTab AI summary section + unavailable badge (AISUM-03)

### Phase 14: E2E Validation + CLI
**Goal**: Full pipeline validated end-to-end with real data round-trips, and CLI provides scriptable access to all merge/export operations
**Depends on**: Phase 09, Phase 10, Phase 12
**Requirements**: CLI-01, CLI-02, CLI-03, CLI-04
**Success Criteria** (what must be TRUE):
  1. CLI merge commands work for both Translator and Game Dev modes with correct output
  2. CLI export commands produce XML, Excel, and plain text in all formats
  3. CLI file-type detection command correctly identifies Translator vs Game Dev files
  4. E2E round-trip test (parse real XML, merge, export, re-parse, compare) passes with zero data loss
**Plans**: 2 plans

Plans:
- [ ] 14-01-PLAN.md -- CLI merge/export/detect commands + unit tests (CLI-01, CLI-02, CLI-03)
- [ ] 14-02-PLAN.md -- E2E round-trip tests for Translator and Game Dev pipelines (CLI-04)

## Progress

**Execution Order:**
Phases execute in numeric order: 07 > 08 > 09 > 10 > 11 > 12 > 13 > 14
Note: Phase 11 and 13 depend only on Phase 07 and could execute in parallel with 08-10.

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 01. Stability Foundation | v1.0 | 3/3 | Complete | 2026-03-14 |
| 02. Editor Core | v1.0 | 3/3 | Complete | 2026-03-14 |
| 03. TM Workflow | v1.0 | 3/3 | Complete | 2026-03-14 |
| 04. Search and AI Differentiators | v1.0 | 2/2 | Complete | 2026-03-14 |
| 05. Visual Polish and Integration | v1.0 | 2/2 | Complete | 2026-03-14 |
| 05.1. Contextual Intelligence & QA | v1.0 | 5/5 | Complete | 2026-03-14 |
| 06. Offline Demo Validation | v1.0 | 2/2 | Complete | 2026-03-14 |
| 07. XML Parsing Foundation + Bug Fixes | 3/3 | Complete    | 2026-03-15 | - |
| 08. Dual UI Mode | 2/2 | Complete    | 2026-03-15 | - |
| 09. Translator Merge | 2/2 | Complete    | 2026-03-15 | - |
| 10. Export Pipeline | 1/1 | Complete    | 2026-03-15 | - |
| 11. Image & Audio Pipeline | 2/2 | Complete    | 2026-03-15 | - |
| 12. Game Dev Merge | 2/2 | Complete    | 2026-03-15 | - |
| 13. AI Summaries | 2/2 | Complete    | 2026-03-15 | - |
| 14. E2E Validation + CLI | 2/2 | Complete   | 2026-03-15 | - |
