# Requirements: LocaNext Demo-Ready CAT Tool

**Defined:** 2026-03-14
**Core Value:** Flawless end-to-end localization workflow — upload, TM auto-mirror, search/edit, export — working seamlessly offline and online, polished enough for executive demos.

## v1 Requirements

### Stability

- [ ] **STAB-01**: Server starts reliably every time without errors or zombie processes
- [ ] **STAB-02**: Offline mode (SQLite) delivers full feature parity with online mode
- [ ] **STAB-03**: DB Factory and Repository pattern implementations work correctly across all repository interfaces
- [ ] **STAB-04**: No Python zombie processes on startup, shutdown, or crash recovery
- [ ] **STAB-05**: SQLite schema matches PostgreSQL schema for all operations (no divergence bugs)

### TM Management

- [ ] **TM-01**: TM tree auto-mirrors file explorer folder structure when files are uploaded
- [ ] **TM-02**: User can assign TMs to folders/files through the mirrored tree
- [ ] **TM-03**: TM lookup shows match percentages with color coding (100%=green, fuzzy=yellow, no-match=red)
- [ ] **TM-04**: TM leverage statistics displayed per file ("45% exact, 30% fuzzy, 25% new")
- [ ] **TM-05**: Model2Vec-based semantic matching (light build, fast performance over Qwen for TM matching)

### Editor

- [ ] **EDIT-01**: Virtual scrolling grid handles 10K+ segments without jank or lag
- [ ] **EDIT-02**: Segment status indicators with color coding (confirmed/draft/empty)
- [ ] **EDIT-03**: Search and filter segments by text and by status
- [ ] **EDIT-04**: Ctrl+S saves current segment without overflowing to the row below (bug fix)
- [ ] **EDIT-05**: Editing and saving translations works reliably in the grid
- [ ] **EDIT-06**: Export workflow produces correct output files in original format

### Search

- [ ] **SRCH-01**: Semantic search using Model2Vec (FAISS vectors) finds similar-meaning translations
- [ ] **SRCH-02**: Semantic search UI prominently showcases the "find similar" capability
- [ ] **SRCH-03**: Search performance is near-instant (sub-second for typical TM sizes)

### AI Features

- [ ] **AI-01**: Local AI pretranslation using Qwen model works end-to-end (zero cloud dependency)
- [ ] **AI-02**: Pretranslation results displayed in editor with clear "AI-suggested" indicator

### Offline Demo

- [ ] **OFFL-01**: Offline mode demo flow works flawlessly (disconnect network, keep working)
- [ ] **OFFL-02**: All core operations (upload, edit, search, export) function identically offline
- [ ] **OFFL-03**: Mode switching is transparent — user doesn't need to know or configure anything

### UI Rework

- [ ] **UI-01**: Main translation grid reworked to production-quality, executive-demo-ready
- [ ] **UI-02**: File explorer tree view polished with professional appearance
- [ ] **UI-03**: TM explorer tree view polished with assignment UI
- [ ] **UI-04**: Settings UI for branches, drives, metadata reading
- [ ] **UI-05**: Overall visual polish matches the cinematic quality of the landing page

### MapDataGenerator Integration

- [ ] **MAP-01**: Image mapping visible directly in the translation grid
- [ ] **MAP-02**: Audio mapping visible directly in the translation grid
- [ ] **MAP-03**: MapDataGenerator data integrated organically (not a separate tool feel)

### Contextual Intelligence

- [ ] **CTX-01**: Auto-detect character names within strings and display character metadata (gender, age, job, race, quest appearances, character interactions)
- [ ] **CTX-02**: Auto-detect location names within strings and display location images and map positions
- [ ] **CTX-03**: Audio samples shown for detected characters — both directly linked audio AND other samples from the same character
- [ ] **CTX-04**: Image context shown for detected entities (characters, locations, items) even when not directly linked to the StringID
- [ ] **CTX-05**: Vectorial n-gram entity detection within sentences — detect multiple entities (character + location + item) in a single string
- [ ] **CTX-06**: Category clustering using QACompiler/LanguageDataExporter technology to auto-assign string types
- [ ] **CTX-07**: "AI Translated" status type visible in the grid to distinguish human vs AI translations
- [ ] **CTX-08**: Context panel in the editor that dynamically shows all detected entity information for the current segment

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
| STAB-01 | Phase 1 | Pending |
| STAB-02 | Phase 1 | Pending |
| STAB-03 | Phase 1 | Pending |
| STAB-04 | Phase 1 | Pending |
| STAB-05 | Phase 1 | Pending |
| EDIT-01 | Phase 2 | Pending |
| EDIT-02 | Phase 2 | Pending |
| EDIT-03 | Phase 2 | Pending |
| EDIT-04 | Phase 2 | Pending |
| EDIT-05 | Phase 2 | Pending |
| EDIT-06 | Phase 2 | Pending |
| UI-01 | Phase 2 | Pending |
| TM-01 | Phase 3 | Pending |
| TM-02 | Phase 3 | Pending |
| TM-03 | Phase 3 | Pending |
| TM-04 | Phase 3 | Pending |
| TM-05 | Phase 3 | Pending |
| UI-02 | Phase 3 | Pending |
| UI-03 | Phase 3 | Pending |
| SRCH-01 | Phase 4 | Pending |
| SRCH-02 | Phase 4 | Pending |
| SRCH-03 | Phase 4 | Pending |
| AI-01 | Phase 4 | Pending |
| AI-02 | Phase 4 | Pending |
| UI-04 | Phase 5 | Pending |
| UI-05 | Phase 5 | Pending |
| MAP-01 | Phase 5 | Pending |
| MAP-02 | Phase 5 | Pending |
| MAP-03 | Phase 5 | Pending |
| CTX-01 | Phase 5.1 | Pending |
| CTX-02 | Phase 5.1 | Pending |
| CTX-03 | Phase 5.1 | Pending |
| CTX-04 | Phase 5.1 | Pending |
| CTX-05 | Phase 5.1 | Pending |
| CTX-06 | Phase 5.1 | Pending |
| CTX-07 | Phase 5.1 | Pending |
| CTX-08 | Phase 5.1 | Pending |
| OFFL-01 | Phase 6 | Pending |
| OFFL-02 | Phase 6 | Pending |
| OFFL-03 | Phase 6 | Pending |

**Coverage:**
- v1 requirements: 40 total
- Mapped to phases: 40
- Unmapped: 0

---
*Requirements defined: 2026-03-14*
*Last updated: 2026-03-14 after roadmap creation*
