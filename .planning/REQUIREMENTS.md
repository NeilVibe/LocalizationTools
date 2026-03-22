# Requirements: LocaNext v6.0 Showcase Offline Transfer

**Defined:** 2026-03-22
**Core Value:** Real, working localization workflows with zero cloud dependency

## v1 Requirements

### Mock Data

- [x] **MOCK-01**: CLI script wipes DB and creates mock platform with project_FRE, project_ENG, and project_MULTI
- [x] **MOCK-02**: Mock projects auto-detect language from project name (project_FRE → French, project_ENG → English)
- [x] **MOCK-03**: project_MULTI contains subfolders with language-suffixed files (e.g., corrections_FRE/, corrections_ENG/) for multi-language merge testing
- [x] **MOCK-04**: Test languagedata files from C:\Users\MYCOM\Desktop\oldoldVold\test123 are loadable as mock LOC data

### Settings

- [x] **SET-01**: User can configure LOC PATH in Settings page (persistent, per-project)
- [x] **SET-02**: User can configure EXPORT PATH in Settings page (persistent, per-project)
- [x] **SET-03**: Settings validate paths exist and contain expected files (languagedata_*.xml)

### Transfer Service

- [x] **XFER-01**: Adapter imports QuickTranslate core modules via sys.path (xml_transfer, postprocess, source_scanner, language_loader)
- [x] **XFER-02**: StringID Only match type works (case-insensitive, SCRIPT/ALL category filter)
- [x] **XFER-03**: StringID+StrOrigin match type works (strict 2-key with nospace fallback)
- [x] **XFER-04**: StrOrigin+FileName 2PASS match type works (3-tuple then 2-tuple fallback)
- [x] **XFER-05**: 8-step postprocess pipeline runs after merge (newlines, apostrophes, entities, etc.)
- [x] **XFER-06**: Transfer scope works: "Transfer All" vs "Only Untranslated"
- [x] **XFER-07**: Multi-language folder merge: scans source folder, auto-detects language suffixes per file/subfolder, merges each language into correct languagedata target

### Merge API

- [x] **API-01**: POST /api/merge/preview returns dry-run summary (files, entries, matches, overwrites)
- [x] **API-02**: POST /api/merge/execute streams progress via SSE (file-by-file + postprocess steps)
- [x] **API-03**: Merge summary report returned on completion (matched, skipped, overwritten counts)
- [x] **API-04**: POST /api/merge/preview supports multi-language mode (scans folder, returns per-language breakdown)

### Merge UI

- [ ] **UI-01**: "Merge to LOCDEV" button in main toolbar near Export actions (single-file/project merge)
- [ ] **UI-02**: Right-click folder context menu "Merge Folder to LOCDEV" (multi-language folder merge)
- [ ] **UI-03**: Single-page merge modal with target LOCDEV folder picker, match type radios, scope toggle
- [ ] **UI-04**: Category filter toggle visible only for StringID mode
- [ ] **UI-05**: Dry-run preview panel shows file/entry counts and overwrite warnings (per-language for multi)
- [ ] **UI-06**: Progress display during merge execution (file-by-file updates)
- [ ] **UI-07**: Summary report shown on completion with matched/skipped/overwritten counts
- [ ] **UI-08**: Language auto-detected from project and shown as badge in modal header
- [ ] **UI-09**: Multi-language mode shows detected languages with file counts before merge

## v2 Requirements

### Deferred Architecture

- **ARCH-01**: Split VirtualGrid.svelte (4299 lines → 5 focused components)
- **ARCH-02**: Split mega_index.py (1310 lines → 3 modules)
- **ARCH-03**: Extract business logic from thick route handlers into services
- **ARCH-04**: Add unit test infrastructure with mocks

## Out of Scope

| Feature | Reason |
|---------|--------|
| Backup/rollback on merge | User decided not needed — trust QuickTranslate logic |
| StrOrigin-Only match type | Rarely used, not in top 3 |
| StrOrigin+DescOrigin match type | Voice direction specific, defer |
| Fuzzy matching | Not in QuickTranslate core transfer |
| Game Dev Grid (CRUD) | Separate milestone, tribunal decisions captured |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| MOCK-01 | Phase 56 | Complete |
| MOCK-02 | Phase 56 | Complete |
| MOCK-03 | Phase 56 | Complete |
| MOCK-04 | Phase 56 | Complete |
| SET-01 | Phase 56 | Complete |
| SET-02 | Phase 56 | Complete |
| SET-03 | Phase 56 | Complete |
| XFER-01 | Phase 57 | Complete |
| XFER-02 | Phase 57 | Complete |
| XFER-03 | Phase 57 | Complete |
| XFER-04 | Phase 57 | Complete |
| XFER-05 | Phase 57 | Complete |
| XFER-06 | Phase 57 | Complete |
| XFER-07 | Phase 57 | Complete |
| API-01 | Phase 58 | Complete |
| API-02 | Phase 58 | Complete |
| API-03 | Phase 58 | Complete |
| API-04 | Phase 58 | Complete |
| UI-01 | Phase 59 | Pending |
| UI-02 | Phase 59 | Pending |
| UI-03 | Phase 59 | Pending |
| UI-04 | Phase 59 | Pending |
| UI-05 | Phase 59 | Pending |
| UI-06 | Phase 59 | Pending |
| UI-07 | Phase 59 | Pending |
| UI-08 | Phase 59 | Pending |
| UI-09 | Phase 59 | Pending |

**Coverage:**
- v1 requirements: 26 total
- Mapped to phases: 26
- Unmapped: 0

---
*Requirements defined: 2026-03-22*
