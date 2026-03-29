# Requirements: LocaNext

**Defined:** 2026-03-26
**Core Value:** Real, working localization workflows with zero cloud dependency

## v13.0 Requirements

Requirements for Production Path Resolution milestone.

### Code Cleanup

- [x] **FIX-01**: onScrollToRow delegate race in SearchEngine resolved -- scroll-to-row works reliably after search
- [x] **FIX-02**: visibleColumns dead $derived removed from CellRenderer
- [x] **FIX-03**: onSaveComplete callback wired in InlineEditor -- parent notified on save
- [x] **FIX-04**: tmSuggestions accessible from StatusColors to parent components

### Path Configuration

- [x] **PATH-01**: User can select Branch (cd_beta, mainline, cd_alpha, cd_delta, cd_lambda) via dropdown -- always visible in UI like QACompiler top bar
- [x] **PATH-02**: User can select Drive letter (A-Z) via dropdown -- combined with branch to form base Perforce path
- [x] **PATH-03**: Path validation shows green "PATHS OK" or red "PATHS NOT FOUND" with specific missing folders -- validates on startup, on change, and before operations
- [x] **PATH-04**: Branch+Drive selection persisted across sessions (settings.json or DB preferences)

### Media Path Resolution

- [x] **MEDIA-01**: LanguageData grid row-select resolves DDS image via StringID -> GameData entity -> TextureName -> Perforce DDS path -- shown in ImageTab
- [x] **MEDIA-02**: LanguageData grid row-select resolves WEM audio via StringID -> GameData entity -> SoundEventName -> Perforce WEM path -- shown in AudioTab
- [x] **MEDIA-03**: Path resolution uses configured Branch+Drive (not hardcoded paths)
- [x] **MEDIA-04**: Graceful fallback when image/audio not found -- shows "No media" with reason (entity not found / texture attribute missing / file not on disk)

### Mock Testing

- [x] **MOCK-01**: Mock Perforce directory structure with DDS/WEM fixtures at correct relative paths
- [x] **MOCK-02**: E2E tests verify full chain: LanguageData row -> StringID -> entity -> DDS thumbnail in ImageTab
- [x] **MOCK-03**: E2E tests verify full chain: LanguageData row -> StringID -> entity -> WEM playback in AudioTab
- [x] **MOCK-04**: Mock paths are drive-agnostic (relative structure, any drive letter works)

### Architecture

- [x] **ARCH-02**: mega_index.py split from 1310 lines into 5 focused modules (entity, media, cross-ref, search, build)

## v15.0 Requirements

Requirements for MEGA Graft milestone.

### XML Parsing Graft
- **GRAFT-01**: GameData XML parsing MUST use MDG's exact 5-stage sanitizer (bad entities, newlines in seg, attr <, attr &, tag stack repair) + virtual root wrapper + dual-pass parsing (strict then recovery)
- **GRAFT-02**: GameData path validation MUST allow Perforce paths outside CWD base directory (fix is_relative_to strictness)

### Category & Detection Graft
- **GRAFT-03**: LDE two-tier category mapper (STORY: 4 Dialog + 8 Sequencer types; GAME_DATA: 9 categories + System_Misc fallback) with priority keyword override MUST be grafted as a new service
- **GRAFT-04**: FileName column (StringID -> .loc.xml stem) and Korean untranslated detection (3-range regex) MUST appear as toggleable grid columns

### Bug Fixes
- **GRAFT-05**: GameData left panel resize delta MUST be corrected (e.clientX - resizeStartX, not inverted)
- **GRAFT-06**: StringID and Index column toggles MUST actually show/hide columns in Game Dev grid
- **GRAFT-07**: MegaIndex MUST auto-build on gamedata load and show toast notifications (building/success/error)
- **GRAFT-08**: EntityCard audio MUST use streaming endpoint /api/ldm/mapdata/audio/stream/{id} not raw wem_path

### UX Polish
- **GRAFT-09**: Professional loading screen with centered progress bar, percentage, and industry-grade animation MUST replace shimmer skeleton loading

### Traceability

| REQ | Phase |
|-----|-------|
| GRAFT-01 | 98 |
| GRAFT-02 | 98 |
| GRAFT-03 | 98 |
| GRAFT-04 | 98 |
| GRAFT-05 | 98 |
| GRAFT-06 | 98 |
| GRAFT-07 | 98 |
| GRAFT-08 | 98 |
| GRAFT-09 | 98 |
- Unmapped: 0

## v16.0 Requirements

Requirements for Windows App Polish milestone.

### Svelte 5 Event Migration

- **EVT-01**: AppModal.svelte wrapper MUST exist that wraps Carbon Modal 0.95 and exposes onprimary/onsecondary/onclose callback props (Svelte 5 pattern), isolating the Svelte 4 compat boundary to ONE file
- **EVT-02**: Carbon Button on:click events MUST be migrated to onclick (Svelte 5 DOM event syntax) in all application files
- **EVT-03**: Carbon Dropdown on:select events MUST be migrated to bind:selectedId with $effect for change detection
- **EVT-04**: All common/shared modal files (ConfirmModal, InputModal, ChangePassword, UpdateModal, AccessControl) MUST use AppModal instead of Carbon Modal directly, with onprimary/onsecondary callback props
- **EVT-05**: All LDM modal files (TMUploadModal, FilePickerDialog, PretranslateModal, FileMergeModal, TMManager) MUST use AppModal instead of Carbon Modal directly
- **EVT-06**: All app files (KRSimilar, QuickSearch, XLSTransfer) MUST use AppModal instead of Carbon Modal directly
- **EVT-07**: FilesPage MUST use AppModal instead of Carbon Modal directly. After migration, grep for on:click/on:select/on:submit in locaNext/src/ (excluding AppModal.svelte) MUST return 0 results

### Traceability

| REQ | Phase |
|-----|-------|
| EVT-01 | 99 |
| EVT-02 | 99 |
| EVT-03 | 99 |
| EVT-04 | 99 |
| EVT-05 | 99 |
| EVT-06 | 99 |
| EVT-07 | 99 |
- Unmapped: 0

## Future Requirements

Deferred to future milestones.

### Interactive Codex (v14.0+)

- **CODEX-01**: Per-generator Codex pages (Quest, Item, Character, Region) with QACompiler tab structure
- **CODEX-02**: Interactive world map with Region boundaries from MapPlot data
- **CODEX-03**: Entity pins on map from WorldPosition, color-coded by type
- **CODEX-04**: crimsondesert.gg-style visual quality for map and entity cards

### Infrastructure

- **LAN-01 through LAN-07**: LAN Server Mode -- installer sets up machine as PostgreSQL LAN server

## Out of Scope

| Feature | Reason |
|---------|--------|
| Perforce client integration | Branch list is hardcoded (matches all 3 NewScripts apps) |
| Auto-detect drive letter | User selects manually (matches QACompiler/MapDataGenerator pattern) |
| Real Perforce sync/checkout | Read-only access to local files, no P4 commands |
| Multi-user branch/drive | v13.0 is single-user; multi-user deferred to LAN milestone |
| Codex enhancements | Deferred to v14.0+ (needs path resolution working first) |
| Carbon Components upgrade | v0.95 is Svelte 4; upgrade to v1.0 deferred until stable release |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| FIX-01 | Phase 89 | Complete |
| FIX-02 | Phase 89 | Complete |
| FIX-03 | Phase 89 | Complete |
| FIX-04 | Phase 89 | Complete |
| PATH-01 | Phase 90 | Complete |
| PATH-02 | Phase 90 | Complete |
| PATH-03 | Phase 90 | Complete |
| PATH-04 | Phase 90 | Complete |
| MEDIA-01 | Phase 91 | Complete |
| MEDIA-02 | Phase 91 | Complete |
| MEDIA-03 | Phase 91 | Complete |
| MEDIA-04 | Phase 91 | Complete |
| MOCK-01 | Phase 91 | Complete |
| MOCK-02 | Phase 91 | Complete |
| MOCK-03 | Phase 91 | Complete |
| MOCK-04 | Phase 91 | Complete |
| ARCH-02 | Phase 92 | Complete |

**Coverage:**
- v13.0 requirements: 17 total
- Mapped to phases: 17
- Unmapped: 0

---
*Requirements defined: 2026-03-26*
*Last updated: 2026-03-29 after v16.0 Phase 99 planning*
