---
gsd_state_version: 1.0
milestone: v12.0
milestone_name: TM Intelligence
status: active
stopped_at: Milestone initialized, requirements defined
last_updated: "2026-03-26T07:00:00.000Z"
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-26)

**Core value:** Real, working localization workflows with zero cloud dependency
**Current focus:** Defining requirements for v12.0 TM Intelligence

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-03-26 — Milestone v12.0 started

## Performance Metrics

- Phases: 0/TBD complete
- Plans: 0/TBD complete
- Requirements mapped: 0/TBD

## Accumulated Context

### Decisions

- v10.0 Tribunal: v11.0 = ARCH-04 (unit tests first) + ARCH-01 (split VirtualGrid)
- v10.0 Tribunal: v12.0 = TM Intelligence (contextual ranking + batch pre-translate)
- Grill-me session: Existing 5-tier cascade sufficient, v12.0 adds AC context layer
- Korean NLP research: char n-gram {2,3,4,5} optimal, no word n-grams for Korean
- Dual threshold: 92% pretranslation (batch apply), 62% context panel (more fuzzy matches)
- AC automaton from TM whole_lookup + line_lookup — data already in memory
- Space-strip Korean before n-gram extraction (inconsistent spacing in game text)
- Performance fallback: n={2,4} if n={2,3,4,5} too slow

### Phase Structure

TBD — roadmap creation pending

### Deferred

- ARCH-02: Split mega_index.py (1310 lines)
- LDE2E-03: Language data with images/audio resolves from Perforce-like paths
- LAN-01 through LAN-07: LAN Server Mode (future milestone)

### Blockers/Concerns

None.

## Session Continuity

Last session: 2026-03-26
Stopped at: Milestone v12.0 initialized, grill session complete
Next action: Define requirements → create roadmap
