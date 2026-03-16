# Phase 26: Navigation + DEV Parity - Context

**Gathered:** 2026-03-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Correct menu naming, browser folder picker parity, auto-load mock data in DEV, and strict file type separation between Localization Data and Game Data pages.

</domain>

<decisions>
## Implementation Decisions

### Menu Naming (NAV-01, NAV-02) — ALREADY DONE
- "Files" → "Localization Data" in sidebar tabs (applied via HMR)
- "Game Dev" → "Game Data" in sidebar tabs (applied via HMR)
- Location: `locaNext/src/routes/+layout.svelte` lines 319, 335

### Browser Folder Picker (NAV-03) — PARTIALLY DONE
- `showDirectoryPicker()` added to GameDevPage.svelte `browseFolder()`
- Fallback chain: Electron native → File System Access API → text input
- `register-browser-folder` endpoint returns mock_gamedata base path
- Needs: verify the full flow works end-to-end, handle permission denied gracefully

### Auto-Load Mock Data (NAV-04) — PARTIALLY DONE
- `$effect` on GameDevPage mount calls browse API with empty path
- Backend `_get_base_dir()` auto-detects mock_gamedata directory
- `BrowseRequest.path` defaults to empty string
- Needs: verify tree populates automatically, handle case where no mock data exists

### File Type Separation (NAV-05) — NEW
- Localization Data page: only accepts `.loc.xml` files (LocStr format) and languagedata XML
- Game Data page: only accepts StaticInfo XML files (non-LocStr)
- Backend already detects file_type on upload (`translator` vs `gamedev`)
- Frontend should filter/reject wrong types with clear error message
- Upload endpoint should validate: reject gamedev files uploaded to translator context, and vice versa

### Claude's Discretion
- Exact error message wording for file type rejection
- Whether to show a toast or inline error for wrong file type
- Loading skeleton design during auto-load

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Navigation
- `locaNext/src/routes/+layout.svelte` — Sidebar tab labels and navigation functions
- `locaNext/src/lib/components/pages/GameDevPage.svelte` — Browse folder, auto-load, showDirectoryPicker

### File Type Detection
- `server/tools/ldm/routes/gamedata.py` — GameData API endpoints, `_get_base_dir()`, register-browser-folder
- `server/tools/ldm/schemas/gamedata.py` — BrowseRequest with default empty path
- `server/tools/ldm/services/gamedata_browse_service.py` — Folder scanning, path validation

### Reference Example
- `RessourcesForCodingTheProject/NewScripts/QACompilerNEW/exampleofskillgamedata.txt` — Real XML hierarchy examples

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `GameDevPage.svelte:browseFolder()` — already has showDirectoryPicker + Electron + fallback chain
- `GameDevPage.svelte:$effect` — auto-load on mount already wired
- Backend `file_type` detection on upload — already classifies as `translator` or `gamedev`

### Established Patterns
- File type detection: `<LocStr>` nodes = translator, other XML = gamedev (DUAL-01 from v2.0)
- Optimistic UI with error revert (project constraint)
- Carbon Components for toasts/notifications

### Integration Points
- Upload endpoint needs file_type validation per context
- GameDevPage auto-load connects to existing browse API
- Layout.svelte tab labels (already changed)

</code_context>

<specifics>
## Specific Ideas

- NAV-01/02 are already live — just need to verify and commit
- The user explicitly wants STRICT separation: languagedata files ONLY in Localization Data, gamedata ONLY in Game Data
- Auto-load should be seamless — user opens Game Data page and sees the tree immediately

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 26-navigation-dev-parity*
*Context gathered: 2026-03-16*
