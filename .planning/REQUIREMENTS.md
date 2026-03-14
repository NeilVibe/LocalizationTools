# Requirements: LocaNext Demo-Ready CAT Tool

**Defined:** 2026-03-14
**Core Value:** Flawless end-to-end localization workflow — upload, TM auto-mirror, search/edit, export — working seamlessly offline and online, polished enough for executive demos.

## v1 Requirements

### Stability

- [x] **STAB-01**: Server starts reliably every time without errors or zombie processes
- [x] **STAB-02**: Offline mode (SQLite) delivers full feature parity with online mode
- [x] **STAB-03**: DB Factory and Repository pattern implementations work correctly across all repository interfaces
- [x] **STAB-04**: No Python zombie processes on startup, shutdown, or crash recovery
- [x] **STAB-05**: SQLite schema matches PostgreSQL schema for all operations (no divergence bugs)

### TM Management

- [x] **TM-01**: TM tree auto-mirrors file explorer folder structure when files are uploaded
- [x] **TM-02**: User can assign TMs to folders/files through the mirrored tree
- [x] **TM-03**: TM lookup shows match percentages with color coding (100%=green, fuzzy=yellow, no-match=red)
- [x] **TM-04**: TM leverage statistics displayed per file ("45% exact, 30% fuzzy, 25% new")
- [x] **TM-05**: Model2Vec-based semantic matching (light build, fast performance over Qwen for TM matching)

### Editor

- [x] **EDIT-01**: Virtual scrolling grid handles 10K+ segments without jank or lag
- [x] **EDIT-02**: Segment status indicators with color coding (confirmed/draft/empty)
- [x] **EDIT-03**: Search and filter segments by text and by status
- [x] **EDIT-04**: Ctrl+S saves current segment without overflowing to the row below (bug fix)
- [x] **EDIT-05**: Editing and saving translations works reliably in the grid
- [x] **EDIT-06**: Export workflow produces correct output files in original format

### Search

- [x] **SRCH-01**: Semantic search using Model2Vec (FAISS vectors) finds similar-meaning translations
- [x] **SRCH-02**: Semantic search UI prominently showcases the "find similar" capability
- [x] **SRCH-03**: Search performance is near-instant (sub-second for typical TM sizes)

### AI Features

- [x] **AI-01**: Model2Vec powers the entire semantic pipeline (TM matching, search, entity detection) as the default/standard model
- [x] **AI-02**: "AI-suggested" indicator visible in editor for Model2Vec-matched translations

### Offline Demo

- [ ] **OFFL-01**: Offline mode demo flow works flawlessly (disconnect network, keep working)
- [ ] **OFFL-02**: All core operations (upload, edit, search, export) function identically offline
- [ ] **OFFL-03**: Mode switching is transparent — user doesn't need to know or configure anything

### UI Rework

- [x] **UI-01**: Main translation grid reworked to production-quality, executive-demo-ready
- [x] **UI-02**: File explorer tree view polished with professional appearance
- [x] **UI-03**: TM explorer tree view polished with assignment UI
- [x] **UI-04**: Settings UI for branches, drives, metadata reading
- [x] **UI-05**: Overall visual polish matches the cinematic quality of the landing page

### MapDataGenerator Integration

- [x] **MAP-01**: Image mapping visible directly in the translation grid
- [x] **MAP-02**: Audio mapping visible directly in the translation grid
- [x] **MAP-03**: MapDataGenerator data integrated organically (not a separate tool feel)

### Contextual Intelligence

- [x] **CTX-01**: Auto-detect character names within strings and display character metadata (gender, age, job, race, quest appearances, character interactions)
- [x] **CTX-02**: Auto-detect location names within strings and display location images and map positions
- [x] **CTX-03**: Audio samples shown for detected characters — both directly linked audio AND other samples from the same character
- [x] **CTX-04**: Image context shown for detected entities (characters, locations, items) even when not directly linked to the StringID
- [x] **CTX-05**: Aho-Corasick automaton built from extracted glossary — scans strings in real-time O(n) to detect all entities (characters, locations, items, skills) simultaneously in one pass
- [x] **CTX-06**: Category clustering using QACompiler/LanguageDataExporter technology to auto-assign string types
- [x] **CTX-09**: Automatic glossary extraction from game data (QACompiler/LDE generators) → character names, location names, item names, skill names
- [x] **CTX-10**: Glossary-to-datapoint mapping — each glossary term maps to staticinfo paths where images, DESC, and audio can be found
- [x] **CTX-07**: "AI Translated" status type visible in the grid to distinguish human vs AI translations
- [x] **CTX-08**: Context panel in the editor that dynamically shows all detected entity information for the current segment

## v2 Requirements

### Online Collaboration

- **COLLAB-01**: Online mode (PostgreSQL) works for multi-user collaboration
- **COLLAB-02**: Real-time multi-user editing via WebSocket
- **COLLAB-03**: Conflict resolution for concurrent edits

### Editor Enhancements

- **EDIT-07**: Keyboard navigation (Tab between segments, Enter to confirm)
- **EDIT-08**: Undo/redo in editor cells
- **EDIT-09**: Concordance search panel (right-click or Ctrl+F)
- **EDIT-10**: Glossary/terminology panel with auto-detected terms
- **EDIT-11**: Batch operations (bulk confirm, bulk pretranslate)

### Navigation/Menus

- **NAV-01**: App switching UI rework
- **NAV-02**: Sidebar navigation rework

### Game-Specific

- **GAME-01**: Character limit display per field with warnings
- **GAME-02**: Variable placeholder highlighting and protection

### Legacy Parity

- **LEG-01**: XLSTransfer in LocaNext matches legacy script output
- **LEG-02**: KRSimilar in LocaNext matches legacy script output
- **LEG-03**: Apps menu functions verified against legacy scripts

### Additional NewScripts

- **NS-01**: QuickSearch integration into LocaNext
- **NS-02**: QuickTranslate integration into LocaNext
- **NS-03**: ExtractAnything integration into LocaNext

### Qwen AI Pretranslation

- **QWEN-01**: Local AI pretranslation using Qwen model (zero cloud dependency)
- **QWEN-02**: Qwen-powered pretranslation results with quality scoring

### Visual Polish

- **VIS-01**: Dark mode / theme switching
- **VIS-02**: Activity/audit log for enterprise compliance

## Out of Scope

| Feature | Reason |
|---------|--------|
| Full MT engine integration (Google/DeepL API) | LocaNext differentiates with LOCAL AI (Qwen), not API wrappers. Breaks offline story |
| WYSIWYG in-context preview | Massive effort rendering game UI. MapDataGenerator provides context without the nightmare |
| Plugin/extension marketplace | Premature. Core must work first |
| Automated workflow orchestration | Enterprise TMS feature, not demo-ready CAT tool |
| Cost estimation / billing | Irrelevant for internal enterprise tool |
| 100+ file format support | XML primary, Excel for import/export. Three formats done well |
| Mobile app | Desktop-first. Translators don't work on phones |
| Multi-language UI | Not planned |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| STAB-01 | Phase 1 | Complete |
| STAB-02 | Phase 1 | Complete |
| STAB-03 | Phase 1 | Complete |
| STAB-04 | Phase 1 | Complete |
| STAB-05 | Phase 1 | Complete |
| EDIT-01 | Phase 2 | Complete |
| EDIT-02 | Phase 2 | Complete |
| EDIT-03 | Phase 2 | Complete |
| EDIT-04 | Phase 2 | Complete |
| EDIT-05 | Phase 2 | Complete |
| EDIT-06 | Phase 2 | Complete |
| UI-01 | Phase 2 | Complete |
| TM-01 | Phase 3 | Complete |
| TM-02 | Phase 3 | Complete |
| TM-03 | Phase 3 | Complete |
| TM-04 | Phase 3 | Complete |
| TM-05 | Phase 3 | Complete |
| UI-02 | Phase 3 | Complete |
| UI-03 | Phase 3 | Complete |
| SRCH-01 | Phase 4 | Complete |
| SRCH-02 | Phase 4 | Complete |
| SRCH-03 | Phase 4 | Complete |
| AI-01 | Phase 4 | Complete |
| AI-02 | Phase 4 | Complete |
| UI-04 | Phase 5 | Complete |
| UI-05 | Phase 5 | Complete |
| MAP-01 | Phase 5 | Complete |
| MAP-02 | Phase 5 | Complete |
| MAP-03 | Phase 5 | Complete |
| CTX-01 | Phase 5.1 | Complete |
| CTX-02 | Phase 5.1 | Complete |
| CTX-03 | Phase 5.1 | Complete |
| CTX-04 | Phase 5.1 | Complete |
| CTX-05 | Phase 5.1 | Complete |
| CTX-06 | Phase 5.1 | Complete |
| CTX-07 | Phase 5.1 | Complete |
| CTX-08 | Phase 5.1 | Complete |
| CTX-09 | Phase 5.1 | Complete |
| CTX-10 | Phase 5.1 | Complete |
| OFFL-01 | Phase 6 | Pending |
| OFFL-02 | Phase 6 | Pending |
| OFFL-03 | Phase 6 | Pending |

**Coverage:**
- v1 requirements: 42 total
- Mapped to phases: 42
- Unmapped: 0

---
*Requirements defined: 2026-03-14*
*Last updated: 2026-03-14 after roadmap creation*
