# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-22)

**Core value:** Real, working localization workflows with zero cloud dependency, dual-mode for translators and game developers.
**Current focus:** v6.0 Showcase Offline Transfer — Phase 56 (Mock Data + Settings)

## Current Position

Phase: 56 (1 of 5) — Mock Data + Settings
Plan: —
Status: Ready to plan
Last activity: 2026-03-22 — Roadmap created for v6.0 Showcase Offline Transfer

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: —
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Tribunal 2026-03-22]: Port QuickTranslate via adapter import (sys.path), never copy — Sacred Scripts rule
- [Tribunal 2026-03-22]: Single-page merge modal with phase-driven state (configure/preview/execute/done)
- [Tribunal 2026-03-22]: 3 match types: StringID Only, StringID+StrOrigin, StrOrigin+FileName 2PASS
- [Tribunal 2026-03-22]: SSE streaming for merge progress, sync endpoint for dry-run preview
- [Tribunal 2026-03-22]: No backup needed — trust QuickTranslate's battle-tested logic
- [Tribunal 2026-03-22]: Mock DB via CLI script (scripts/setup_mock_data.py --confirm-wipe)
- [Tribunal 2026-03-22]: LOC PATH + EXPORT PATH in Settings page, not merge modal
- [Tribunal 2026-03-22]: Two entry points: toolbar button (single) + right-click folder (multi-language)

### Pending Todos

(None — fresh milestone)

### Deferred from v6.0

- Split VirtualGrid.svelte (4299 lines) — ARCH-01
- Split mega_index.py (1310 lines) — ARCH-02
- Extract business logic from thick route handlers — ARCH-03
- Add unit test infrastructure — ARCH-04
- Fix right-click context menu on file explorer panel

## Session Continuity

Last session: 2026-03-22
Stopped at: Roadmap created, ready to plan Phase 56
Resume file: None
