# Roadmap: LocaNext v10.0 UI Polish + Tag Pill Redesign

## Overview

Fix 4 UI issues found during v9.0 Windows testing: hide br-tags from grid, combine color+format tag pills, redesign tag pill styling, and normalize grid background color. All changes are Svelte 5 frontend-only (tagDetector.js, TagText.svelte, VirtualGrid.svelte). Qwen3-VL visual review validates all changes at the end.

## Milestones

- [x] **v1.0 through v9.0** - Phases 01-79.1 (shipped)
- [ ] **v10.0 UI Polish + Tag Pill Redesign** - Phases 80-82 (in progress)

## Phases

- [x] **Phase 80: Tag Pill Overhaul** - Hide br-tags, combine color+format codes, redesign pill styling (completed 2026-03-25)
- [ ] **Phase 81: Grid Polish** - Default background from yellow to neutral/white
- [ ] **Phase 82: Visual Verification** - Qwen3-VL review all 5 pages, confirm 7+/10

## Phase Details

### Phase 80: Tag Pill Overhaul
**Goal**: Users see clean, color-coded combined tag pills in the grid -- no br-tag noise, format+color merged into single styled elements
**Depends on**: Nothing (first phase of v10.0)
**Requirements**: TAG-04, TAG-05, TAG-06
**Success Criteria** (what must be TRUE):
  1. br-tag linebreaks do not appear as pills or visible markers in the grid -- text flows naturally across lines
  2. A cell containing both a color code and a format code shows ONE combined tag pill (not two separate pills)
  3. Combined tag pills display the actual color from the color code (e.g., red text color code produces a red-tinted pill)
  4. Tag pills render as tight inline elements that sit naturally within the text flow, not as block-level or oversized badges
**Plans:** 1/1 plans complete
Plans:
- [x] 80-01-PLAN.md -- br-tag exclusion + combined color+code pills + CSS redesign

### Phase 81: Grid Polish
**Goal**: Grid cells use a neutral/white default background instead of yellow
**Depends on**: Nothing (independent of Phase 80)
**Requirements**: GRID-01
**Success Criteria** (what must be TRUE):
  1. Grid cells with no special status display a white or neutral background (not yellow)
  2. Status-colored cells (teal for translated, etc.) still display their correct status colors unchanged
**Plans**: TBD

### Phase 82: Visual Verification
**Goal**: Qwen3-VL confirms all UI changes look correct across all 5 LocaNext pages
**Depends on**: Phase 80, Phase 81
**Requirements**: VIS-01
**Success Criteria** (what must be TRUE):
  1. Qwen3-VL scores each of the 5 pages (Files, GameDev, Codex, Map, TM) at 7+/10
  2. Tag pills are visible and correctly styled in pages that display language data (Files, GameDev)
  3. No visual regressions detected compared to v9.0 baseline (8.6/10 avg)
**Plans**: TBD

## Progress

**Execution Order:** 80 -> 81 -> 82 (81 can run parallel with 80)

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 80. Tag Pill Overhaul | 1/1 | Complete   | 2026-03-25 |
| 81. Grid Polish | 0/TBD | Not started | - |
| 82. Visual Verification | 0/TBD | Not started | - |
