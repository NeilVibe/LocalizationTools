# Phase 24 Plan 02: UIUX Audit Findings

Comprehensive audit/harden/clarify pass across all 13 v3.0 components.

## Accessibility Findings

| # | Component | Issue | Fix Applied |
|---|-----------|-------|-------------|
| A1 | GameDevPage | Icon-only refresh button missing `aria-label` | Added `aria-label="Refresh file tree"` |
| A2 | GameDevPage | Icon-only browse button missing `aria-label` | Added `aria-label="Apply path"` |
| A3 | GameDevPage | Loading state not announced to screen readers | Added `role="status" aria-live="polite"` |
| A4 | GameDevPage | Icon buttons missing visible `:focus` styles | Added `:focus` with `outline: 2px solid var(--cds-focus)` |
| A5 | AISuggestionsTab | Loading state not announced to screen readers | Added `role="status" aria-live="polite"` |
| A6 | AISuggestionsTab | Error state not announced to screen readers | Added `role="alert" aria-live="assertive"` |
| A7 | AISuggestionsTab | Suggestion cards missing `aria-label` | Added `aria-label` with truncated suggestion text |
| A8 | AISuggestionsTab | Suggestion cards missing visible `:focus` styles | Added `:focus` outline |
| A9 | NamingPanel | Loading state not announced to screen readers | Wrapped InlineLoading in `role="status" aria-live="polite"` span |
| A10 | NamingPanel | Error state not announced to screen readers | Added `role="alert" aria-live="assertive"` to error empty state |
| A11 | NamingPanel | Name tags and suggestion items missing `:focus` styles | Added `:focus` outlines to both `.name-tag` and `.suggestion-item` |
| A12 | QAInlineBadge | Badge missing `aria-label` for screen readers | Added descriptive `aria-label` with issue count |
| A13 | QAInlineBadge | Badge missing visible `:focus` styles | Added `:focus` outline with `border-radius: 4px` |
| A14 | QAInlineBadge | Popover close button missing `:focus` styles | Added `:focus` outline |
| A15 | QAInlineBadge | Dismiss button missing `:focus` styles | Added `:focus` outline |
| A16 | QAInlineBadge | Loading text not announced to screen readers | Added `role="status" aria-live="polite"` |
| A17 | CodexSearchBar | Dropdown missing `role="listbox"` | Added `role="listbox" aria-label="Search results"` |
| A18 | CodexSearchBar | Search results missing `role="option"` and `aria-label` | Added `role="option"` and descriptive `aria-label` |
| A19 | CodexSearchBar | Search results missing `:focus` styles | Added `:focus` outline |
| A20 | CodexSearchBar | Loading/no-results states missing `aria-live` | Added `role="status" aria-live="polite"` |
| A21 | CodexPage | Tab container missing `role="tablist"` | Added `role="tablist" aria-label="Entity type tabs"` |
| A22 | CodexPage | Tab buttons missing `role="tab"` and `aria-selected` | Added `role="tab"` and `aria-selected={activeTab === type}` |
| A23 | CodexPage | Tabs missing `:focus` styles | Added `:focus` outline |
| A24 | CodexPage | Back button missing `aria-label` | Added `aria-label="Back to entity list"` |
| A25 | CodexPage | Entity cards missing `aria-label` | Added `aria-label` with entity name and type |
| A26 | CodexPage | Entity cards missing `:focus` styles | Added `:focus` outline |
| A27 | CodexPage | Loading types state missing `aria-live` | Added `role="status" aria-live="polite"` |
| A28 | CodexEntityDetail | Similar item badges missing `aria-label` | Added `aria-label="View similar item: {name}"` |
| A29 | CodexEntityDetail | Related entity badges missing `aria-label` | Added `aria-label="View related entity: {key}"` |
| A30 | CodexEntityDetail | Related badges missing `:focus` styles | Added `:focus` outline |
| A31 | MapDetailPanel | Entity count buttons missing `aria-label` | Added `aria-label` with count and type |
| A32 | MapDetailPanel | Close button missing `:focus` styles | Added `:focus` outline |
| A33 | MapDetailPanel | NPC link buttons missing `:focus` styles | Added `:focus` outline |
| A34 | MapDetailPanel | Entity count buttons missing `:focus` styles | Added `:focus` outline |
| A35 | MapTooltip | Missing `role="tooltip"` | Added `role="tooltip"` |
| A36 | WorldMapPage | Loading state missing `aria-live` | Added `role="status" aria-live="polite"` |
| A37 | WorldMapPage | Error state missing `aria-live` | Added `role="alert" aria-live="assertive"` |
| A38 | FileExplorerTree | Retry button missing `aria-label` | Added `aria-label="Retry loading folder tree"` |
| A39 | FileExplorerTree | Retry button missing `:focus` styles | Added `:focus` outline |
| A40 | FileExplorerTree | Tree nodes missing `:focus` styles | Added `:focus` outline to `.tree-node` |

## Error Hardening Findings

| # | Component | Issue | Fix Applied |
|---|-----------|-------|-------------|
| E1 | AISuggestionsTab | Error state showed raw `err.message` (e.g., "HTTP 500") | Replaced with human-readable "Could not retrieve AI suggestions -- check your network connection or try again later." |
| E2 | AISuggestionsTab | Suggestion text could overflow without wrapping | Added `overflow-wrap: break-word` |
| E3 | NamingPanel | Error state not shown separately from empty state | Added explicit `status === 'error'` branch with human-readable message |
| E4 | NamingPanel | Suggestion name and reasoning could overflow | Added `overflow-wrap: break-word` to `.suggestion-name` and `.suggestion-reasoning` |
| E5 | MapTooltip | Tooltip could render off-screen near viewport edges | Added viewport clamping using `$derived` with `window.innerWidth/innerHeight` bounds |
| E6 | MapTooltip | Tooltip description could overflow | Added `overflow-wrap: break-word` to `.tooltip-desc` |
| E7 | CodexEntityDetail | Entity description could overflow | Added `overflow-wrap: break-word` to `.entity-description` |

## UX Copy Findings

| # | Component | Issue | Fix Applied |
|---|-----------|-------|-------------|
| C1 | GameDevPage | Loading text "Loading file..." was generic | Changed to "Loading game data file..." |
| C2 | AISuggestionsTab | Loading text was "Generating suggestions..." | Changed to "Generating AI translation suggestions..." (more specific) |
| C3 | AISuggestionsTab | Error title was generic "Error" | Changed to "Failed to load suggestions" |
| C4 | NamingPanel | Loading text "Searching..." was generic | Changed to "Searching for similar names..." |
| C5 | NamingPanel | Empty state "Select a Name field to see suggestions" | Changed to "Select a Name field to see naming suggestions" |
| C6 | NamingPanel | Short input message "Type at least 2 characters" | Changed to "Type at least 2 characters to search for similar names" |
| C7 | NamingPanel | No results message "No similar names found" | Changed to "No similar names found -- this name appears to be unique" |
| C8 | QAInlineBadge | Loading text "Loading..." was generic | Changed to "Loading QA issues..." |
| C9 | CodexSearchBar | Loading text "Searching..." was generic | Changed to "Searching entities..." |
| C10 | CodexSearchBar | No results "No matching entities found" | Changed to "No matching entities found -- try a different search term" |
| C11 | CodexPage | Loading text "Loading Codex..." | Changed to "Loading Codex entity types..." |
| C12 | CodexPage | Empty entities "No entities found for this type." | Changed to "No entities found for this type -- ensure gamedata files are loaded and indexed." |
| C13 | WorldMapPage | Loading text "Loading world map..." | Changed to "Loading world map regions and routes..." |

## Intentionally Skipped

| Component | Reason |
|-----------|--------|
| CategoryFilter | Carbon MultiSelect component handles its own a11y internally |
| MapCanvas `role="img"` | Already present from v3.0 implementation |
| MapCanvas node `role="button"` + keyboard | Already present from v3.0 implementation |
| FileExplorerTree `role="tree"` + `aria-expanded` | Already present from v3.0 implementation |
| MapDetailPanel close button `aria-label` | Already present: `aria-label="Close panel"` |
| QAInlineBadge popover `role="dialog"` + `aria-label` | Already present from v3.0 implementation |
| PlaceholderImage | Fixed in Plan 01 (24-01), not modified here |

## Summary

- **40 accessibility fixes** across 13 components
- **7 error hardening fixes** (overflow, viewport clamping, human-readable errors)
- **13 UX copy improvements** (action-oriented, specific, guiding)
- **7 items intentionally skipped** (already correct or handled by Plan 01)
- Total: **60 issues found and fixed**
