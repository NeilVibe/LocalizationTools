---
phase: 23-bug-fixes
plan: 02
subsystem: ui
tags: [svelte5, worldmap, codex, tooltip, navigation, sorting]

requires:
  - phase: 22-svelte-5-migration
    provides: Svelte 5 runes and callback props across all components
  - phase: 20-world-map
    provides: WorldMapPage, MapCanvas, MapDetailPanel, MapTooltip
  - phase: 19-codex
    provides: CodexPage, CodexSearchBar, CodexEntityDetail

provides:
  - Tooltip suppression when detail panel is open
  - Deduplicated route keys preventing {#each} crashes
  - NPC navigation from MapDetailPanel to CodexPage with auto-search
  - Unknown entity types sorted last in CodexPage tab list
  - codexSearchQuery store for cross-page search communication

affects: [worldmap, codex, navigation]

tech-stack:
  added: []
  patterns: [cross-page-search-via-store, sort-unknown-last-999-pattern]

key-files:
  created: []
  modified:
    - locaNext/src/lib/components/pages/WorldMapPage.svelte
    - locaNext/src/lib/components/ldm/MapCanvas.svelte
    - locaNext/src/lib/components/ldm/MapDetailPanel.svelte
    - locaNext/src/lib/components/pages/CodexPage.svelte
    - locaNext/src/lib/stores/navigation.js

key-decisions:
  - "codexSearchQuery writable store for cross-page NPC search (consumed and cleared on CodexPage mount)"
  - "FIX-10 satisfied: WorldMapPage uses inline fetch, no duplicate service instantiation exists"

patterns-established:
  - "Cross-page search: writable store set before navigation, consumed and cleared on target page mount"
  - "Unknown sort: map indexOf -1 to 999 so unknown items sort last instead of first"

requirements-completed: [FIX-03, FIX-04, FIX-07, FIX-09, FIX-10]

duration: 2min
completed: 2026-03-16
---

# Phase 23 Plan 02: WorldMap/Codex Bug Fixes Summary

**Tooltip suppression when panel open, route key deduplication, NPC-to-Codex navigation with auto-search, and unknown entity type sort fix**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-15T22:06:16Z
- **Completed:** 2026-03-15T22:08:33Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Tooltip no longer appears when detail panel is open (selectedNode guard + clear on click)
- Route keys include index for uniqueness, preventing {#each} duplicate key crashes with bidirectional routes
- Clicking NPC name in MapDetailPanel navigates to Codex with that NPC pre-searched via codexSearchQuery store
- Unknown entity types sort last (999 sentinel) instead of first (-1 from indexOf)
- Confirmed no duplicate CodexService instantiation in WorldMap components (FIX-10 already satisfied)

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix WorldMap tooltip suppression, route key dedup, and service singleton** - `13fc0175` (fix)
2. **Task 2: Fix NPC navigation to Codex with search and entity type sorting** - `66b2b0d3` (fix)

## Files Created/Modified
- `locaNext/src/lib/components/pages/WorldMapPage.svelte` - Tooltip suppression guard + clear on click
- `locaNext/src/lib/components/ldm/MapCanvas.svelte` - Route key dedup with index
- `locaNext/src/lib/components/ldm/MapDetailPanel.svelte` - NPC name passed to goToCodex
- `locaNext/src/lib/components/pages/CodexPage.svelte` - Consume codexSearchQuery + unknown type sort fix
- `locaNext/src/lib/stores/navigation.js` - codexSearchQuery store + goToCodex searchQuery param

## Decisions Made
- Used writable store (codexSearchQuery) for cross-page search communication, consumed and cleared on mount to avoid stale queries
- FIX-10 confirmed already satisfied: WorldMapPage uses inline fetch(), no service class duplication exists

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- WorldMap and Codex bugs fixed, ready for remaining Phase 23 plans
- codexSearchQuery store available for any future cross-page search needs

---
*Phase: 23-bug-fixes*
*Completed: 2026-03-16*
