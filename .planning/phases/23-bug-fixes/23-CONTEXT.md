# Phase 23: Bug Fixes - Context

**Gathered:** 2026-03-16
**Status:** Ready for planning
**Source:** Brainstorming session + API audit + v3.0 swarm review

<domain>
## Phase Boundary

Fix ALL runtime bugs from v3.0 code review, the missing GameDev upload-path API endpoint, and perform a comprehensive API call audit. Every frontend API call must have a matching backend route. Every button that triggers an API call must work end-to-end.

**Scope: 11 bug fixes + 1 test fix + full API endpoint audit**

</domain>

<decisions>
## Implementation Decisions

### Bug Fixes (from v3.0 3-agent swarm audit)
- **FIX-01**: GameDevPage Date.now() fallback file ID → proper error handling with user-visible error state
- **FIX-02**: CodexEntityDetail audio element → onerror fallback to PlaceholderAudio component
- **FIX-03**: MapDetailPanel navigateToNPC → pass NPC name to Codex search correctly
- **FIX-04**: WorldMapPage tooltip → suppress when detail panel is open
- **FIX-05**: AISuggestionsTab + NamingPanel → clear loading state on debounce cancel
- **FIX-06**: QAInlineBadge handleClickOutside → proper attachment, backdrop tabindex
- **FIX-07**: MapCanvas route key deduplication → prevent {#each} crash
- **FIX-08**: GameDevPage tree refresh → use reload method instead of remount flicker
- **FIX-09**: CodexPage entity type sort → unknown types sort last, not first
- **FIX-10**: WorldMapService → reuse CodexService singleton, not duplicate

### Missing API Endpoint (CRITICAL - user-reported bug)
- **FIX-11**: GameDevPage calls `POST /api/ldm/files/upload-path` which DOES NOT EXIST
  - Backend has: browse, columns, save — NO upload-path
  - Fix: Remove upload-path call from handleFileSelect, load XML directly via gamedata/browse response
  - The browse response already returns file metadata (name, path, entity_count)
  - No new backend endpoint needed — just fix the frontend to use existing data

### Full API Call Audit
- Cross-reference ALL 100+ frontend API calls against backend routes
- Verify every button/action that triggers an API call
- Create a shell wrapper script for testing API endpoints
- Log analysis: check server logs for 404s on API calls

### Test Fix
- **TEST-01**: Update test_mock_gamedata_pipeline.py texture test for generated universe filenames

### Claude's Discretion
- Order of bug fixes (group by component for efficiency)
- Shell wrapper design for API testing
- Whether to add API health-check integration tests

</decisions>

<specifics>
## Specific Ideas

### GameDev Upload Fix (FIX-11) — The Primary User-Reported Bug
Current broken flow:
```
handleFileSelect → POST /api/ldm/files/upload-path (404!) → fallback fake object → Date.now() ID (FIX-01)
```

Fixed flow:
```
handleFileSelect → use file object from FileExplorerTree directly → POST /api/ldm/gamedata/columns → openFile.set(gridFile)
```

The FileExplorerTree already calls `/api/ldm/gamedata/browse` and returns `{name, path, entity_count}`. No upload needed.

### API Audit Results (from exploration)
- 100+ endpoints total across frontend
- 99% have matching backend routes
- 1 confirmed missing: `/api/ldm/files/upload-path`
- Backend-only endpoints (no frontend caller): pretranslate, trash, maintenance, offline sync

</specifics>

<deferred>
## Deferred Ideas

- Full E2E Playwright test suite for all API endpoints (v4.0)
- API rate limiting implementation
- Backend-only endpoint cleanup

</deferred>

---

*Phase: 23-bug-fixes*
*Context gathered: 2026-03-16 via brainstorming + API audit*
