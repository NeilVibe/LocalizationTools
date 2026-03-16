---
phase: "35"
plan: "01"
title: "Cross-Page Consistency Enforcement"
subsystem: frontend-ui
tags: [consistency, pageheader, dark-mode, error-handling, sidebar]
dependency-graph:
  requires: [Phase 32 design tokens, Phase 34 page polish]
  provides: [unified page headers, consistent error recovery, clean dark mode]
  affects: [CodexPage, WorldMapPage, TMPage, +layout.svelte]
tech-stack:
  added: []
  patterns: [shared PageHeader adoption, ErrorState with retry, design token enforcement]
key-files:
  created: []
  modified:
    - locaNext/src/lib/components/pages/CodexPage.svelte
    - locaNext/src/lib/components/pages/WorldMapPage.svelte
    - locaNext/src/lib/components/pages/TMPage.svelte
    - locaNext/src/routes/+layout.svelte
decisions:
  - "GameDevPage and GridPage retain specialized toolbars -- split-panel and contextual toolbar patterns are intentionally different from simple page headers"
  - "CodexPage fallback hex (#0f62fe) in CSS var() kept as standard CSS fallback pattern"
  - "Removed box-shadow from CodexPage entity card hover to match matte theme decision"
metrics:
  duration: "3min"
  completed: "2026-03-17"
---

# Phase 35 Plan 01: Cross-Page Consistency Enforcement Summary

**Unified PageHeader adoption across 3 pages, ErrorState with retry on Codex, zero hardcoded colors in all page components**

## What Was Done

### Task 1: Shared PageHeader Adoption (XPG-01, XPG-04)

Replaced custom header markup and CSS in 3 pages with the shared PageHeader component:

1. **CodexPage** -- Replaced `.codex-header` div with `<PageHeader icon={Book} title="Game World Codex" />`. Also replaced the custom `.codex-error` div with `<ErrorState message={apiError} onretry={fetchTypes} />` for proper retry capability.

2. **WorldMapPage** -- Replaced `.worldmap-header` div with `<PageHeader icon={Earth} title="Interactive World Map">` using the children slot for the node/route count display. WorldMap already used ErrorState.

3. **TMPage** -- Replaced `.tm-page-header` div with `<PageHeader icon={DataBase} title="Translation Memories">` using the children slot for Upload and Settings action buttons.

**Intentionally NOT changed:**
- **GameDevPage** -- Split-panel layout with file explorer; the left panel has a panel-level header, not a full-width page header
- **GridPage** -- Contextual toolbar showing file info + back button; this is a file-editing toolbar, not a page header

Removed ~70 lines of duplicate header CSS across the 3 updated pages.

### Task 2: Dark Mode Audit + Sidebar Consistency (XPG-02, XPG-03)

**Dark mode audit findings:**
- All 5 page components use CSS custom properties exclusively (zero hardcoded hex colors)
- One CSS fallback value (`var(--cds-interactive-01, #0f62fe)`) in CodexPage is standard CSS practice -- kept as-is
- Removed `box-shadow: 0 2px 6px rgba(0,0,0,0.15)` from CodexPage entity card hover to match matte theme decision from Phase 34
- Replaced hardcoded `rgba(218, 30, 40, 0.1)` logout button hover in layout with `var(--cds-layer-hover-01)`

**Sidebar navigation audit:**
- All 5 nav tabs use consistent token-based styles: `--cds-text-02` default, `--cds-layer-hover-01` hover, `--cds-interactive` + `--cds-text-on-color` active, `--cds-focus` focus outline
- Tab spacing and sizing uniform across all tabs
- No changes needed -- sidebar was already consistent

**Error handling audit:**
- CodexPage: NOW uses ErrorState with retry (was custom div)
- WorldMapPage: Already uses ErrorState with retry
- TMPage: TM loading errors handled inline (graceful degradation, tmList = [])
- GameDevPage: Uses EmptyState for empty states; error handling via fetch .catch
- GridPage: Error handling via RightPanel and VirtualGrid internal states

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed matte-breaking box-shadow from CodexPage**
- **Found during:** Task 2 dark mode audit
- **Issue:** CodexPage entity card hover had `box-shadow: 0 2px 6px rgba(0,0,0,0.15)` which contradicts the Phase 34 matte theme decision
- **Fix:** Removed box-shadow from hover state and transition property
- **Files modified:** CodexPage.svelte
- **Commit:** cbe9c11a

**2. [Rule 2 - Missing] Replaced hardcoded rgba in layout logout hover**
- **Found during:** Task 2 dark mode audit
- **Issue:** Layout logout button used hardcoded `rgba(218, 30, 40, 0.1)` instead of design token
- **Fix:** Replaced with `var(--cds-layer-hover-01)`
- **Files modified:** +layout.svelte
- **Commit:** cbe9c11a

## Decisions Made

1. GameDevPage and GridPage intentionally retain specialized toolbars -- they serve different UX patterns than simple page headers
2. CSS `var()` fallback values (e.g., `var(--cds-interactive-01, #0f62fe)`) are standard practice, not hardcoded colors
3. Box-shadow removed from CodexPage card hover to match matte theme (Phase 34 decision)
