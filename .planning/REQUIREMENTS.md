# Requirements: LocaNext v5.1

**Defined:** 2026-03-22
**Core Value:** Every v5.0 feature verified working end-to-end with mock data. Polish rough edges. Production-ready demo.

## v5.1 Requirements

### INIT -- MegaIndex DEV Initialization

- [x] **INIT-01**: MegaIndex.build() runs automatically on DEV server start, populating all 35 dicts from mock_gamedata fixtures
- [x] **INIT-02**: PerforcePathService auto-configures to mock_gamedata path in DEV mode (no manual settings needed)

### VERIFY -- Codex UI Verification

- [x] **VERIFY-01**: Item Codex page renders card grid with DDS images, group hierarchy tabs, and search — verified with Playwright screenshot
- [x] **VERIFY-02**: Character Codex page renders card grid with portraits, category tabs, and Race/Gender/Age/Job detail — verified with screenshot
- [x] **VERIFY-03**: Audio Codex page renders list with category tree sidebar, inline play buttons, and script text — verified with screenshot
- [x] **VERIFY-04**: Region Codex page renders split layout with faction tree and d3-zoom map with WorldPosition nodes — verified with screenshot

### RPANEL -- Right Panel Verification

- [x] **RPANEL-01**: Image tab shows entity DDS portrait when selecting a LanguageData row with a StringID linked to an entity (via MegaIndex C7→C1)
- [x] **RPANEL-02**: Audio tab plays WEM audio with script text when selecting a row with available audio (via MegaIndex C3)

### TM -- Translation Memory Flow

- [ ] **TM-01**: Editing a row and setting status to "reviewed" auto-registers source+target pair to linked TM
- [ ] **TM-02**: FAISS index auto-builds after TM entries are added or modified (no manual trigger needed)
- [ ] **TM-03**: TM 5-tier cascade search returns results in right panel TM tab when selecting a row

### COLOR -- LanguageData Grid Colors

- [ ] **COLOR-01**: Default row color is grey (neutral) — not yellow
- [ ] **COLOR-02**: Yellow color only appears when user explicitly sets "needs confirmation" via hotkey or button
- [ ] **COLOR-03**: Blue-green color for confirmed/approved rows

### SMOKE -- End-to-End Smoke Test

- [ ] **SMOKE-01**: Playwright smoke test visits all pages (Files, LanguageData, GameData, Codex, Item Codex, Character Codex, Audio Codex, Region Codex, Map, TM, Settings) and takes screenshots

## Out of Scope

| Feature | Reason |
|---------|--------|
| New features or Codex types | v5.1 is testing + polish only |
| Production build/packaging | Tested in v5.0 Phase 51, not re-tested |
| Performance optimization | Polish pass, not perf pass |
| Full E2E test suite | Smoke test only -- comprehensive testing later |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| INIT-01 | Phase 52 | Complete |
| INIT-02 | Phase 52 | Complete |
| VERIFY-01 | Phase 53 | Complete |
| VERIFY-02 | Phase 53 | Complete |
| VERIFY-03 | Phase 53 | Complete |
| VERIFY-04 | Phase 53 | Complete |
| RPANEL-01 | Phase 53 | Complete |
| RPANEL-02 | Phase 53 | Complete |
| TM-01 | Phase 54 | Pending |
| TM-02 | Phase 54 | Pending |
| TM-03 | Phase 54 | Pending |
| COLOR-01 | Phase 54 | Pending |
| COLOR-02 | Phase 54 | Pending |
| COLOR-03 | Phase 54 | Pending |
| SMOKE-01 | Phase 55 | Pending |

**Coverage:**
- v5.1 requirements: 15 total
- Mapped to phases: 15
- Unmapped: 0

---
*Requirements defined: 2026-03-22*
*Traceability updated: 2026-03-22*
