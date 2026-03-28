---
phase: 98-mega-graft-mdg-lde-battle-tested-techniques
plan: 02
subsystem: frontend-ui
tags: [bugfix, gamedev, audio, grid, column-toggle]
dependency_graph:
  requires: []
  provides: [gamedev-stringid-toggle, entity-audio-streaming]
  affects: [CellRenderer, EntityCard, gridState]
tech_stack:
  added: []
  patterns: [streaming-audio-endpoint, media-cache-bust]
key_files:
  created: []
  modified:
    - locaNext/src/lib/components/ldm/grid/CellRenderer.svelte
    - locaNext/src/lib/components/ldm/grid/gridState.svelte.ts
    - locaNext/src/lib/components/ldm/EntityCard.svelte
decisions:
  - "Resize delta NOT changed -- analysis proved current formula correct for right-side panel"
  - "Used entity.strkey as streaming endpoint key (matches server lookup pattern)"
metrics:
  duration: "3m 9s"
  completed: "2026-03-28T21:11:07Z"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 3
---

# Phase 98 Plan 02: Frontend Bug Fixes (Column Toggles, Audio Streaming) Summary

**One-liner:** Unblocked StringID column toggle for gamedev grid, wired EntityCard audio to streaming endpoint, fixed loadedPages crash in gridState reset.

## Completed Tasks

| Task | Name | Commit | Key Changes |
|------|------|--------|-------------|
| 1 | Column toggle + resize analysis | 222b9cfa | Removed `fileType !== 'gamedev'` guard on StringID, fixed loadedPages.clear() crash |
| 2 | EntityCard audio streaming | 1fd3e4dd | Replaced raw wem_path with /api/ldm/mapdata/audio/stream/{strkey} endpoint |

## Deviations from Plan

### Intentional Deviation: Resize Delta NOT Changed

**Found during:** Task 1 analysis
**Plan said:** Change `resizeStartX - e.clientX` to `e.clientX - resizeStartX`
**Analysis:** The GameDataContextPanel is a RIGHT-side panel with a resize handle on its LEFT edge (CSS: `position: absolute; left: 0`). For this layout:
- Dragging LEFT (clientX decreases) should make panel WIDER
- Current formula: `resizeStartX - e.clientX` = positive when dragging left = width increases
- This is CORRECT behavior for a right-side panel

The plan's proposed fix would INVERT the drag direction (making drag-right widen the panel, which is wrong). The plan itself noted uncertainty: "If this turns out wrong after testing, it can be reverted with a sign flip." Analysis confirms the current code is correct.

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed loadedPages.clear() crash in gridState.svelte.ts**
- **Found during:** Task 1
- **Issue:** `resetGridState()` called `loadedPages.clear()` but `loadedPages` was removed during bulk load architecture migration (only a comment remained)
- **Fix:** Removed the dead `loadedPages.clear()` call
- **Files modified:** gridState.svelte.ts
- **Commit:** 222b9cfa

## Verification Results

1. `fileType !== 'gamedev'` in CellRenderer.svelte: Only on Category and Reference columns (correct), NOT on StringID or Index
2. `audio/stream` in EntityCard.svelte: Present, using streaming endpoint
3. Raw `<source src={wem_path}>` in EntityCard: 0 matches (removed)
4. `crossorigin="anonymous"` on audio element: Present
5. `{#key}` wrapper for cache-bust: Present

## Known Stubs

None -- all changes are complete functional fixes.

## Self-Check: PASSED

All 3 modified files exist. Both commits (222b9cfa, 1fd3e4dd) verified in git log.
