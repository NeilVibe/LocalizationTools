---
phase: 34-page-polish
plan: "02"
subsystem: ldm-ui
tags: [dark-mode, loading-states, empty-states, polish, carbon-tokens]
dependency_graph:
  requires: [32-01]
  provides: [polished-grid-page, polished-tm-page, polished-tm-explorer]
  affects: [GridPage, TMPage, TMExplorerGrid]
tech_stack:
  added: []
  patterns: [carbon-skeleton-loading, empty-state-component, left-border-accent]
key_files:
  created: []
  modified:
    - locaNext/src/lib/components/pages/GridPage.svelte
    - locaNext/src/lib/components/pages/TMPage.svelte
    - locaNext/src/lib/components/ldm/TMExplorerGrid.svelte
decisions:
  - Left-border accent for TM indicator (simpler, guaranteed dark mode safe)
  - Skeleton rows match grid column dimensions (name/entries/status/type)
  - Removed dead context menu CSS from TMPage (handled entirely by TMExplorerGrid)
  - Icon colors mapped to Carbon semantic tokens (link-01, support-success, support-warning)
metrics:
  duration: 4min
  completed: "2026-03-16T17:34:17Z"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 3
---

# Phase 34 Plan 02: Language Data Grid + TM Panel Polish Summary

Carbon-token dark mode fix for GridPage TM indicator, InlineLoading for TM status, SkeletonText loading rows and EmptyState component for TMExplorerGrid, header icon + font polish for TMPage.

## What Was Done

### Task 1: GridPage dark mode + loading polish
- Replaced hardcoded `rgba(36, 161, 72, 0.15)` TM indicator background with `var(--cds-layer-02)` + left-border accent `var(--cds-support-success)`
- Replaced plain "Loading TM..." text with Carbon `InlineLoading` component
- All styles confirmed using `--cds-*` tokens -- zero hardcoded rgba remaining

### Task 2: TMPage + TMExplorerGrid loading/empty/dark mode polish
- TMPage header: added `DataBase` icon, increased font-size from 1rem to 1.125rem for visual consistency
- Removed 30 lines of dead context menu CSS from TMPage (context menu fully handled by TMExplorerGrid)
- TMExplorerGrid loading: replaced plain "Loading..." text with 5 `SkeletonText` skeleton rows matching grid column layout
- TMExplorerGrid empty: replaced inline empty state with shared `EmptyState` component with Upload TM CTA button
- Fixed `.status-badge.active` from hardcoded `rgba(36, 161, 72, 0.2)` to Carbon tokens
- Fixed `.tm-icon.active/inactive` from hardcoded hex to `--cds-support-success` / `--cds-text-03`
- Fixed item icon colors (platform/project/folder) from hardcoded hex to Carbon semantic tokens
- Fixed context-item danger hover from hardcoded rgba to `--cds-layer-hover-01`

## Requirements Satisfied

- [x] LDG-01: Full UI/UX audit -- column alignment preserved (VirtualGrid untouched), status colors use Carbon tokens, empty states use shared component
- [x] LDG-02: Loading state uses InlineLoading for TM status (grid loading handled by VirtualGrid internally)
- [x] LDG-03: Search/filter handled by VirtualGrid (DO NOT MODIFY) -- GridPage contributes polished toolbar
- [x] TMP-01: TM Panel audit -- header with icon, settings panel dark mode confirmed safe, status badge uses tokens
- [x] TMP-02: TMExplorerGrid has SkeletonText loading rows and EmptyState for empty list with Upload CTA

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing] Dead CSS removal in TMPage**
- **Found during:** Task 2
- **Issue:** 30 lines of `.context-menu` CSS in TMPage were dead code (context menu is rendered by TMExplorerGrid with different class names)
- **Fix:** Removed dead CSS, replaced with comment
- **Files modified:** TMPage.svelte
- **Commit:** 0d9eae61

**2. [Rule 1 - Bug] Additional hardcoded colors in TMExplorerGrid**
- **Found during:** Task 2
- **Issue:** Item icon colors (#a8b0b8, #4589ff, #5a9a6e, #d4a574), TM icon colors (#24a148, #6f6f6f), status badge (rgba), and context menu danger hover (rgba) all used hardcoded colors
- **Fix:** Mapped all to Carbon semantic tokens (--cds-icon-secondary, --cds-link-01, --cds-support-success, --cds-support-warning, --cds-text-03, --cds-layer-hover-01)
- **Files modified:** TMExplorerGrid.svelte
- **Commit:** 0d9eae61

## Verification Results

1. svelte-check: zero new errors (2 pre-existing warnings: a11y role on contextmenu div, button nesting in grid row)
2. grep rgba/rgb: zero matches in GridPage and TMPage
3. EmptyState/SkeletonText count: 7 references in TMExplorerGrid
4. VirtualGrid: confirmed unmodified (empty diff)

## Commits

| Task | Commit | Message |
|------|--------|---------|
| 1 | 86370bd1 | feat(34-02): GridPage dark mode + loading polish |
| 2 | 0d9eae61 | feat(34-02): TMPage header + TMExplorerGrid skeleton loading + dark mode fixes |
