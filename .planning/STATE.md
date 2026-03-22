# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-22)

**Core value:** Real, working localization workflows with zero cloud dependency, dual-mode for translators and game developers.
**Current focus:** v6.0 Showcase Offline Transfer — Defining requirements

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-03-22 — Milestone v6.0 Showcase Offline Transfer started

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Tribunal 2026-03-22]: Port QuickTranslate via adapter import (sys.path), never copy — Sacred Scripts rule
- [Tribunal 2026-03-22]: Single-page merge modal with phase-driven state (configure → preview → execute → done)
- [Tribunal 2026-03-22]: 3 match types: StringID Only, StringID+StrOrigin, StrOrigin+FileName 2PASS
- [Tribunal 2026-03-22]: SSE streaming for merge progress, sync endpoint for dry-run preview
- [Tribunal 2026-03-22]: No backup needed — trust QuickTranslate's battle-tested logic
- [Tribunal 2026-03-22]: Merge button in main toolbar near Export
- [Tribunal 2026-03-22]: Mock DB via CLI script (scripts/setup_mock_data.py --confirm-wipe)
- [Tribunal 2026-03-22]: Language auto-detected from project name (project_FRE → French)
- [Tribunal 2026-03-22]: LOC PATH + EXPORT PATH in Settings page, not merge modal
- [Tribunal 2026-03-22]: Test data at C:\Users\MYCOM\Desktop\oldoldVold\test123

### Pending Todos

(None — fresh milestone)

### Deferred from v6.0 Architecture

- Split VirtualGrid.svelte (4299 lines → 5 focused components)
- Split mega_index.py (1310 lines → 3 modules)
- Extract business logic from thick route handlers
- Add unit test infrastructure
- Fix right-click context menu on file explorer panel
