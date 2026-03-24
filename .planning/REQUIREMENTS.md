# Requirements: LocaNext

**Defined:** 2026-03-24
**Core Value:** Real, working localization workflows with zero cloud dependency

## v9.0 Requirements

Requirements for Build Validation + Real-World Testing milestone. Each maps to roadmap phases.

### Build Pipeline

- [x] **BUILD-01**: PyInstaller bundle includes internalized merge module (14 QT files)
- [x] **BUILD-02**: Bundled app runs merge workflow end-to-end without QT source tree
- [x] **BUILD-03**: Light Build triggered on GitHub produces downloadable installer
- [ ] **BUILD-04**: Downloaded installer installs and launches successfully on offline Windows PC

### Mock Data

- [x] **MOCK-09**: Mock gamedata structure mirrors real Perforce paths exactly (F:\perforce\cd\mainline\...)
- [x] **MOCK-10**: Mock DDS textures resolvable via PerforcePathService with correct drive/branch substitution
- [x] **MOCK-11**: Mock WEM audio files present at expected audio folder paths per language
- [x] **MOCK-12**: Mock language data XML files (.loc.xml) with realistic content at loc folder paths

### Language Data E2E

- [x] **LDE2E-01**: User can upload language data (.loc.xml) in built app and see it in grid
- [x] **LDE2E-02**: User can edit language data cells and save — round-trip integrity verified
- [ ] **LDE2E-03**: Language data entries resolve to associated images/audio via Perforce paths
- [x] **LDE2E-04**: All language data operations work in offline mode (SQLite)

### Feature Pipeline Verification (DEV mode)

- [x] **FEAT-01**: TM auto-update fires on add/edit/delete — Model2Vec embedding + FAISS index update in ~6ms
- [x] **FEAT-02**: 5-tier TM cascade returns matches (hash → FAISS → n-gram → text → fallback) with correct confidence scores
- [x] **FEAT-03**: QuickTranslate merge executes all match modes (strict, stringid, strorigin, fuzzy, cascade) with postprocess pipeline
- [x] **FEAT-04**: QuickCheck QA runs line check + term check on uploaded language data, badges appear in grid
- [ ] **FEAT-05**: Aho-Corasick entity detection identifies characters/items/locations in source text
- [ ] **FEAT-06**: Context panel shows entity info + DDS image + WEM audio when clicking a string with entity references
- [x] **FEAT-07**: Mock TM data populated so cascade search returns real matches for uploaded language data

### Visual Audit

- [x] **UIUX-01**: Qwen3-VL visual review of all 5 pages with mock data loaded (score 7+/10)
- [x] **UIUX-02**: Critical UIUX issues from visual audit fixed
- [ ] **UIUX-03**: Screenshot evidence of all 5 pages with real-looking data

### Review Fixes (Phase 79.1 — INSERTED)

- [x] **FIX-01**: Merge route conflict resolved — TranslatorMergeService not shadowed by files.py
- [x] **FIX-02**: test_langdata_media.py uses shared conftest fixtures, no duplicate TestClient
- [x] **FIX-03**: CI merge verification runs for ALL build modes (remove Light Mode gate)
- [x] **FIX-04**: category_mapper.py included in CI merge module verification imports
- [x] **FIX-05**: TMExplorerGrid.svelte formatStatus handles null/undefined, uses correct field for platform
- [x] **FIX-06**: GSD artifacts consistent (BUILD-03/04 status corrected, STATE.md current, ROADMAP overview fixed)
- [x] **FIX-07**: Full E2E test suite passes — all tests green or justified xfail

## Future Requirements

### Architecture (Deferred)

- **ARCH-01**: Split VirtualGrid.svelte (4299 lines) into composable modules
- **ARCH-02**: Split mega_index.py (1310 lines) into domain services
- **ARCH-04**: Unit test infrastructure (unblocked by service extraction)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Full production Perforce integration | Mock paths only — real P4 requires P4 client |
| macOS build testing | Windows-only for this milestone |
| Performance benchmarking | Focus is correctness, not speed |
| Multi-user online testing | Offline PC testing only |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| BUILD-01 | Phase 75 | Complete |
| BUILD-02 | Phase 75 | Complete |
| BUILD-03 | Phase 75 | Complete |
| BUILD-04 | Phase 75 | Pending |
| MOCK-09 | Phase 74 | Complete |
| MOCK-10 | Phase 74 | Complete |
| MOCK-11 | Phase 74 | Complete |
| MOCK-12 | Phase 74 | Complete |
| LDE2E-01 | Phase 76 | Complete |
| LDE2E-02 | Phase 76 | Complete |
| LDE2E-03 | Phase 76 | Pending |
| LDE2E-04 | Phase 76 | Complete |
| FEAT-01 | Phase 78 | Complete |
| FEAT-02 | Phase 78 | Complete |
| FEAT-03 | Phase 78 | Complete |
| FEAT-04 | Phase 78 | Complete |
| FEAT-05 | Phase 78 | Pending |
| FEAT-06 | Phase 78 | Pending |
| FEAT-07 | Phase 78 | Complete |
| UIUX-01 | Phase 79 | Complete |
| UIUX-02 | Phase 79 | Complete |
| UIUX-03 | Phase 79 | Pending |
| FIX-01 | Phase 79.1 | Complete |
| FIX-02 | Phase 79.1 | Complete |
| FIX-03 | Phase 79.1 | Complete |
| FIX-04 | Phase 79.1 | Complete |
| FIX-05 | Phase 79.1 | Complete |
| FIX-06 | Phase 79.1 | Complete |
| FIX-07 | Phase 79.1 | Complete |

**Coverage:**
- v9.0 requirements: 29 total (22 original + 7 FIX)
- Mapped to phases: 22
- Unmapped: 0

---
*Requirements defined: 2026-03-24*
*Last updated: 2026-03-24 after Phase 79.1 completion + GSD health check*
