# Requirements: LocaNext v3.1

**Defined:** 2026-03-16
**Core Value:** Fix runtime issues, migrate to pure Svelte 5, polish UI/UX

## v3.1 Requirements

### Svelte 5 Migration

- [x] **SV5-01**: VirtualGrid.svelte uses callback props ($props) instead of createEventDispatcher for all events
- [x] **SV5-02**: LDM.svelte uses callback props instead of on: event listeners for all child component events
- [x] **SV5-03**: All v3.0 components (AISuggestionsTab, QAInlineBadge, CategoryFilter, NamingPanel) use $props callbacks, not dispatchers
- [x] **SV5-04**: GameDevPage, GridPage, CodexPage use $props callbacks to receive child events
- [x] **SV5-05**: No createEventDispatcher import exists anywhere in the codebase
- [x] **SV5-06**: No on: event directive exists anywhere in codebase (except Carbon component interop where required)

### Bug Fixes

- [x] **FIX-01**: GameDevPage Date.now() fallback file ID replaced with proper error handling
- [x] **FIX-02**: CodexEntityDetail audio element has onerror fallback to PlaceholderAudio
- [x] **FIX-03**: MapDetailPanel navigateToNPC passes NPC name to Codex search
- [x] **FIX-04**: WorldMapPage tooltip suppressed while detail panel is open
- [x] **FIX-05**: AISuggestionsTab and NamingPanel loading state cleared on debounce cancel
- [x] **FIX-06**: QAInlineBadge handleClickOutside properly attached, backdrop has tabindex
- [x] **FIX-07**: MapCanvas route key deduplication to prevent {#each} crash
- [x] **FIX-08**: GameDevPage tree refresh uses reload method instead of remount flicker
- [x] **FIX-09**: CodexPage entity type sort handles unknown types (sorts last, not first)
- [x] **FIX-10**: WorldMapService reuses CodexService singleton instead of creating duplicate

### UIUX Polish

- [x] **UX-01**: FileExplorerTree folder buttons have aria-expanded reflecting expand state
- [x] **UX-02**: Navigation tab dividers CSS covers all 5 tabs, not just first
- [x] **UX-03**: CodexPage card images fallback to PlaceholderImage on 404
- [x] **UX-04**: PlaceholderImage uses div layout instead of foreignObject for Chromium compatibility
- [x] **UX-05**: MapDetailPanel long text wraps properly at all viewport sizes

### Test Fixes

- [x] **FIX-11**: GameDevPage handleFileSelect removes non-existent upload-path call and loads XML directly via gamedata/browse + columns endpoints
- [x] **TEST-01**: test_mock_gamedata_pipeline.py texture test updated for generated universe filenames

## Out of Scope

| Feature | Reason |
|---------|--------|
| Carbon Components Svelte 5 upgrade | External dependency — wait for upstream release |
| Full E2E Playwright test suite | v4.0 scope |
| Performance optimization | Premature — fix bugs first |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SV5-01 | Phase 22 | Complete |
| SV5-02 | Phase 22 | Complete |
| SV5-03 | Phase 22 | Complete |
| SV5-04 | Phase 22 | Complete |
| SV5-05 | Phase 22 | Complete |
| SV5-06 | Phase 22 | Complete |
| FIX-01 | Phase 23 | Complete |
| FIX-02 | Phase 23 | Complete |
| FIX-03 | Phase 23 | Complete |
| FIX-04 | Phase 23 | Complete |
| FIX-05 | Phase 23 | Complete |
| FIX-06 | Phase 23 | Complete |
| FIX-07 | Phase 23 | Complete |
| FIX-08 | Phase 23 | Complete |
| FIX-09 | Phase 23 | Complete |
| FIX-10 | Phase 23 | Complete |
| FIX-11 | Phase 23 | Complete |
| TEST-01 | Phase 23 | Complete |
| UX-01 | Phase 24 | Complete |
| UX-02 | Phase 24 | Complete |
| UX-03 | Phase 24 | Complete |
| UX-04 | Phase 24 | Complete |
| UX-05 | Phase 24 | Complete |

**Coverage:**
- v3.1 requirements: 23 total
- Mapped to phases: 23
- Unmapped: 0

---
*Requirements defined: 2026-03-16*
