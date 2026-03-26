# Requirements: LocaNext

**Defined:** 2026-03-26
**Core Value:** Real, working localization workflows with zero cloud dependency

## v13.0 Requirements

Requirements for Production Path Resolution milestone.

### Code Cleanup

- [ ] **FIX-01**: onScrollToRow delegate race in SearchEngine resolved — scroll-to-row works reliably after search
- [ ] **FIX-02**: visibleColumns dead $derived removed from CellRenderer
- [ ] **FIX-03**: onSaveComplete callback wired in InlineEditor — parent notified on save
- [ ] **FIX-04**: tmSuggestions accessible from StatusColors to parent components

### Path Configuration

- [ ] **PATH-01**: User can select Branch (cd_beta, mainline, cd_alpha, cd_delta, cd_lambda) via dropdown — always visible in UI like QACompiler top bar
- [ ] **PATH-02**: User can select Drive letter (A-Z) via dropdown — combined with branch to form base Perforce path
- [ ] **PATH-03**: Path validation shows green "PATHS OK" or red "PATHS NOT FOUND" with specific missing folders — validates on startup, on change, and before operations
- [ ] **PATH-04**: Branch+Drive selection persisted across sessions (settings.json or DB preferences)

### Media Path Resolution

- [ ] **MEDIA-01**: LanguageData grid row-select resolves DDS image via StringID → GameData entity → TextureName → Perforce DDS path — shown in ImageTab
- [ ] **MEDIA-02**: LanguageData grid row-select resolves WEM audio via StringID → GameData entity → SoundEventName → Perforce WEM path — shown in AudioTab
- [ ] **MEDIA-03**: Path resolution uses configured Branch+Drive (not hardcoded paths)
- [ ] **MEDIA-04**: Graceful fallback when image/audio not found — shows "No media" with reason (entity not found / texture attribute missing / file not on disk)

### Mock Testing

- [ ] **MOCK-01**: Mock Perforce directory structure with DDS/WEM fixtures at correct relative paths
- [ ] **MOCK-02**: E2E tests verify full chain: LanguageData row → StringID → entity → DDS thumbnail in ImageTab
- [ ] **MOCK-03**: E2E tests verify full chain: LanguageData row → StringID → entity → WEM playback in AudioTab
- [ ] **MOCK-04**: Mock paths are drive-agnostic (relative structure, any drive letter works)

### Architecture

- [ ] **ARCH-02**: mega_index.py split from 1310 lines into 5 focused modules (entity, media, cross-ref, search, build)

## Future Requirements

Deferred to future milestones.

### Interactive Codex (v14.0+)

- **CODEX-01**: Per-generator Codex pages (Quest, Item, Character, Region) with QACompiler tab structure
- **CODEX-02**: Interactive world map with Region boundaries from MapPlot data
- **CODEX-03**: Entity pins on map from WorldPosition, color-coded by type
- **CODEX-04**: crimsondesert.gg-style visual quality for map and entity cards

### Infrastructure

- **LAN-01 through LAN-07**: LAN Server Mode — installer sets up machine as PostgreSQL LAN server

## Out of Scope

| Feature | Reason |
|---------|--------|
| Perforce client integration | Branch list is hardcoded (matches all 3 NewScripts apps) |
| Auto-detect drive letter | User selects manually (matches QACompiler/MapDataGenerator pattern) |
| Real Perforce sync/checkout | Read-only access to local files, no P4 commands |
| Multi-user branch/drive | v13.0 is single-user; multi-user deferred to LAN milestone |
| Codex enhancements | Deferred to v14.0+ (needs path resolution working first) |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| FIX-01 | TBD | Pending |
| FIX-02 | TBD | Pending |
| FIX-03 | TBD | Pending |
| FIX-04 | TBD | Pending |
| PATH-01 | TBD | Pending |
| PATH-02 | TBD | Pending |
| PATH-03 | TBD | Pending |
| PATH-04 | TBD | Pending |
| MEDIA-01 | TBD | Pending |
| MEDIA-02 | TBD | Pending |
| MEDIA-03 | TBD | Pending |
| MEDIA-04 | TBD | Pending |
| MOCK-01 | TBD | Pending |
| MOCK-02 | TBD | Pending |
| MOCK-03 | TBD | Pending |
| MOCK-04 | TBD | Pending |
| ARCH-02 | TBD | Pending |

**Coverage:**
- v13.0 requirements: 17 total
- Mapped to phases: 0
- Unmapped: 17 (pending roadmap)

---
*Requirements defined: 2026-03-26*
*Last updated: 2026-03-26 after v13.0 milestone initialization*
