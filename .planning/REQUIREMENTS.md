# Requirements: LocaNext

**Defined:** 2026-03-24
**Core Value:** Real, working localization workflows with zero cloud dependency

## v9.0 Requirements

Requirements for Build Validation + Real-World Testing milestone. Each maps to roadmap phases.

### Build Pipeline

- [ ] **BUILD-01**: PyInstaller bundle includes internalized merge module (14 QT files)
- [ ] **BUILD-02**: Bundled app runs merge workflow end-to-end without QT source tree
- [ ] **BUILD-03**: Light Build triggered on GitHub produces downloadable installer
- [ ] **BUILD-04**: Downloaded installer installs and launches successfully on offline Windows PC

### Mock Data

- [x] **MOCK-09**: Mock gamedata structure mirrors real Perforce paths exactly (F:\perforce\cd\mainline\...)
- [x] **MOCK-10**: Mock DDS textures resolvable via PerforcePathService with correct drive/branch substitution
- [x] **MOCK-11**: Mock WEM audio files present at expected audio folder paths per language
- [x] **MOCK-12**: Mock language data XML files (.loc.xml) with realistic content at loc folder paths

### Language Data E2E

- [ ] **LDE2E-01**: User can upload language data (.loc.xml) in built app and see it in grid
- [ ] **LDE2E-02**: User can edit language data cells and save — round-trip integrity verified
- [ ] **LDE2E-03**: Language data entries resolve to associated images/audio via Perforce paths
- [ ] **LDE2E-04**: All language data operations work in offline mode (SQLite)

### Visual Audit

- [ ] **UIUX-01**: Qwen3-VL visual review of all 5 pages with mock data loaded (score 7+/10)
- [ ] **UIUX-02**: Critical UIUX issues from visual audit fixed
- [ ] **UIUX-03**: Screenshot evidence of all 5 pages with real-looking data

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
| Full QA pipeline testing in build | QA already verified in DEV mode (v3.0) |
| Performance benchmarking | Focus is correctness, not speed |
| Multi-user online testing | Offline PC testing only |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| BUILD-01 | Phase 75 | Pending |
| BUILD-02 | Phase 75 | Pending |
| BUILD-03 | Phase 75 | Pending |
| BUILD-04 | Phase 75 | Pending |
| MOCK-09 | Phase 74 | Complete |
| MOCK-10 | Phase 74 | Complete |
| MOCK-11 | Phase 74 | Complete |
| MOCK-12 | Phase 74 | Complete |
| LDE2E-01 | Phase 76 | Pending |
| LDE2E-02 | Phase 76 | Pending |
| LDE2E-03 | Phase 76 | Pending |
| LDE2E-04 | Phase 76 | Pending |
| UIUX-01 | Phase 77 | Pending |
| UIUX-02 | Phase 77 | Pending |
| UIUX-03 | Phase 77 | Pending |

**Coverage:**
- v9.0 requirements: 15 total
- Mapped to phases: 15
- Unmapped: 0

---
*Requirements defined: 2026-03-24*
*Last updated: 2026-03-24 after roadmap creation*
