# Requirements: LocaNext v3.1

**Defined:** 2026-03-16
**Core Value:** Fix runtime issues, migrate to pure Svelte 5, polish UI/UX

## v3.1 Requirements

### Svelte 5 Migration

- [x] **SV5-01**: VirtualGrid.svelte uses callback props ($props) instead of createEventDispatcher for all events
- [x] **SV5-02**: LDM.svelte uses callback props instead of on: event listeners for all child component events
- [x] **SV5-03**: All v3.0 components (AISuggestionsTab, QAInlineBadge, CategoryFilter, NamingPanel) use $props callbacks, not dispatchers
- [x] **SV5-04**: GameDevPage, GridPage, CodexPage use $props callbacks to receive child events
- [ ] **SV5-05**: No createEventDispatcher import exists anywhere in the codebase
- [ ] **SV5-06**: No on: event directive exists anywhere in codebase (except Carbon component interop where required)

### Bug Fixes

- [ ] **FIX-01**: GameDevPage Date.now() fallback file ID replaced with proper error handling
- [ ] **FIX-02**: CodexEntityDetail audio element has onerror fallback to PlaceholderAudio
- [ ] **FIX-03**: MapDetailPanel navigateToNPC passes NPC name to Codex search
- [ ] **FIX-04**: WorldMapPage tooltip suppressed while detail panel is open
- [ ] **FIX-05**: AISuggestionsTab and NamingPanel loading state cleared on debounce cancel
- [ ] **FIX-06**: QAInlineBadge handleClickOutside properly attached, backdrop has tabindex
- [ ] **FIX-07**: MapCanvas route key deduplication to prevent {#each} crash
- [ ] **FIX-08**: GameDevPage tree refresh uses reload method instead of remount flicker
- [ ] **FIX-09**: CodexPage entity type sort handles unknown types (sorts last, not first)
- [ ] **FIX-10**: WorldMapService reuses CodexService singleton instead of creating duplicate

### UIUX Polish

- [ ] **UX-01**: FileExplorerTree folder buttons have aria-expanded reflecting expand state
- [ ] **UX-02**: Navigation tab dividers CSS covers all 5 tabs, not just first
- [ ] **UX-03**: CodexPage card images fallback to PlaceholderImage on 404
- [ ] **UX-04**: PlaceholderImage uses div layout instead of foreignObject for Chromium compatibility
- [ ] **UX-05**: MapDetailPanel long text wraps properly at all viewport sizes

### Test Fixes

- [ ] **FIX-11**: GameDevPage handleFileSelect removes non-existent upload-path call and loads XML directly via gamedata/browse + columns endpoints
- [ ] **TEST-01**: test_mock_gamedata_pipeline.py texture test updated for generated universe filenames

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
| SV5-05 | Phase 22 | Pending |
| SV5-06 | Phase 22 | Pending |
| FIX-01 | Phase 23 | Pending |
| FIX-02 | Phase 23 | Pending |
| FIX-03 | Phase 23 | Pending |
| FIX-04 | Phase 23 | Pending |
| FIX-05 | Phase 23 | Pending |
| FIX-06 | Phase 23 | Pending |
| FIX-07 | Phase 23 | Pending |
| FIX-08 | Phase 23 | Pending |
| FIX-09 | Phase 23 | Pending |
| FIX-10 | Phase 23 | Pending |
| FIX-11 | Phase 23 | Pending |
| TEST-01 | Phase 23 | Pending |
| UX-01 | Phase 24 | Pending |
| UX-02 | Phase 24 | Pending |
| UX-03 | Phase 24 | Pending |
| UX-04 | Phase 24 | Pending |
| UX-05 | Phase 24 | Pending |

**Coverage:**
- v3.1 requirements: 23 total
- Mapped to phases: 23
- Unmapped: 0

---
*Requirements defined: 2026-03-16*
