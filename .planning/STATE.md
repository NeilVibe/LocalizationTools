---
gsd_state_version: 1.0
milestone: v5.0
milestone_name: Offline Production Bundle + Full Codex
status: unknown
stopped_at: Completed 46-01-PLAN.md (Item Codex Backend)
last_updated: "2026-03-21T12:09:25.636Z"
progress:
  total_phases: 7
  completed_phases: 1
  total_plans: 6
  completed_plans: 5
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-21)

**Core value:** Self-sufficient offline bundle with full Codex (Audio/Item/Character/Region) powered by proven NewScripts logic.
**Current focus:** Phase 46 — Item Codex UI

## Current Position

Phase: 46 (Item Codex UI) — EXECUTING
Plan: 2 of 2

## Performance Metrics

**Velocity:**

- Total plans completed: 0 (v5.0)
- Average duration: --
- Total execution time: --

## Accumulated Context

### Decisions

- v1.0-v4.0 shipped (44 phases, all complete)
- GameData is file-based, bypasses Repository/DB layer -- new Codex services follow same pattern
- PerforcePathService extracted from MapDataService before any new Codex service
- AICapabilityService built in Phase 45 to prevent AI hard-crashes in offline bundle
- Item/Character/Audio/Region Codex types are independent (phases 46-49 could parallelize)
- StringID-to-Audio depends on Audio Codex (Phase 48) being complete
- Offline bundle must be last phase -- packaging after all features built
- [Phase 45]: Merged KNOWN_BRANCHES from QACompiler and MapDataGenerator into unified 5-branch list
- [Phase 45]: Added SCHEMA_REGISTRY dict for dynamic type access in MegaIndex schemas
- [Phase 45]: Named AI capabilities route ai_capabilities.py to avoid conflict with existing admin capabilities.py
- [Phase 45]: Used Svelte 5 module-level $state in .ts for aiCapabilityStore (new pattern vs existing Svelte 4 writable stores)
- [Phase 45]: StaticInfo folder derived from knowledge_folder.parent instead of new PATH_TEMPLATE key
- [Phase 45]: C2 strkey_to_audio_path uses direct matching; full chain deferred to Audio Codex phase
- [Phase 45]: CodexService and MapDataService now delegate all XML parsing to MegaIndex singleton -- single parse replaces 3 independent scans
- [Phase 46]: Knowledge 3-pass resolution: Pass 0 (shared key siblings), Pass 1 (direct key), Pass 2 (name match)
- [Phase 46]: Item Codex routes at /codex/items sub-prefix, coexisting with generic /codex routes

### Pending Todos

None yet.

### Blockers/Concerns

- Research flag: SQLite WAL mode compatibility with existing aiosqlite usage (verify in Phase 45 planning)
- Research flag: StringID-to-Audio reverse lookup chain not explicitly implemented in MapDataGenerator (validate in Phase 50 planning)
- Research flag: WorldPosition coordinate normalization to SVG viewport (validate in Phase 49 planning)
- Research flag: Electron + Python packaging mechanism clarification (validate in Phase 51 planning)

## Session Continuity

Last session: 2026-03-21T12:09:25.633Z
Stopped at: Completed 46-01-PLAN.md (Item Codex Backend)
Resume file: None
