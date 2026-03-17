---
phase: 38-fantasy-world-map
plan: 03
subsystem: frontend-map
tags: [route-animation, zoom, mini-map, fantasy-ui, danger-coloring]
dependency_graph:
  requires: [38-01]
  provides: [route-animations, zoom-to-fit, mini-map, fantasy-detail-panel, fantasy-tooltip]
  affects: [MapCanvas.svelte, MapDetailPanel.svelte, MapTooltip.svelte]
tech_stack:
  added: []
  patterns: [stroke-dashoffset-animation, d3-programmatic-zoom, mini-map-viewport-tracking, danger-level-coloring]
key_files:
  created: []
  modified:
    - locaNext/src/lib/components/ldm/MapCanvas.svelte
    - locaNext/src/lib/components/ldm/MapDetailPanel.svelte
    - locaNext/src/lib/components/ldm/MapTooltip.svelte
decisions:
  - Used $derived.by() for viewportRect since it needs getBoundingClientRect() call
  - Stored zoomBehavior and svgSelection as $state refs for cross-function access
  - Mini-map renders node dots only (polygon rendering deferred to Plan 02 merge)
  - Wrapped SVG + mini-map in position:relative container div
metrics:
  duration: 286s
  completed: 2026-03-17T10:11:20Z
  tasks_completed: 2
  tasks_total: 2
  files_modified: 3
---

# Phase 38 Plan 03: Route Animations + Zoom + Mini-map + Fantasy Panel Summary

Route danger coloring with stroke-dashoffset hover animation, d3 programmatic zoom-to-fit on click, 150x150 mini-map with viewport rectangle, and warm copper/sepia fantasy styling for detail panel and tooltip.

## Tasks Completed

### Task 1: Route danger coloring + hover animation + zoom-to-fit + mini-map
**Commit:** 282cd811

- Added DANGER_COLORS mapping (green/#24a148, amber/#f1c21b, red/#da1e28)
- Replaced polyline routes with path elements supporting stroke-dashoffset animation
- Route hover shows animated dash flow (1.5s linear infinite) + travel time label
- SVG marker arrow for route direction indication
- zoomToRegion() function with 500ms ease-out-quart (1 - Math.pow(1-t, 4))
- Mini-map overlay at bottom-right with node dots and viewport rectangle
- prefers-reduced-motion disables all animations

### Task 2: Enhanced MapDetailPanel + MapTooltip with fantasy styling
**Commit:** e993b365

- Detail panel: warm copper gradient background, Korean name as primary title
- Danger level badges (Safe/Moderate/Dangerous) with semantic color coding
- Slide-in transition with cubic-bezier(0.25, 1, 0.5, 1) ease-out-quart
- Tooltip: dark sepia background with backdrop-filter blur, danger zone dot indicator
- All var(--cds-*) colors replaced with warm copper/sepia palette

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Used $derived.by() instead of $derived() for viewportRect**
- **Found during:** Task 1
- **Issue:** viewportRect needs to call getBoundingClientRect() which is an imperative call, not a pure derivation
- **Fix:** Used $derived.by(() => { ... }) pattern for computed values with side effects
- **Files modified:** MapCanvas.svelte

**2. [Rule 3 - Blocking] Mini-map polygon rendering skipped (Plan 02 parallel)**
- **Found during:** Task 1
- **Issue:** polygonData derived value is created by Plan 02 which executes in parallel
- **Fix:** Mini-map renders node dots only; polygon rendering will appear after Plan 02 merge
- **Files modified:** MapCanvas.svelte

## Self-Check: PASSED

- [x] MapCanvas.svelte exists and contains DANGER_COLORS, route-animated, mini-map, zoomToRegion, stroke-dashoffset, viewportRect, route-arrow, prefers-reduced-motion
- [x] MapDetailPanel.svelte exists and contains danger-badge, name_kr, name_en, copper palette, ease-out-quart
- [x] MapTooltip.svelte exists and contains danger-dot, backdrop-filter, dark sepia background
- [x] Commit 282cd811: route animations + zoom-to-fit + mini-map
- [x] Commit e993b365: fantasy-styled detail panel + tooltip
- [x] Commit 2b9912f7: polygon shapes in mini-map
