---
gsd_state_version: 1.0
milestone: v5.0
milestone_name: Offline Production Bundle + Full Codex
status: defining_requirements
stopped_at: Milestone started, research phase next
last_updated: "2026-03-21T00:00:00.000Z"
last_activity: 2026-03-21 -- Milestone v5.0 started
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-21)

**Core value:** Self-sufficient offline bundle with full Codex (Audio/Item/Character/Region) powered by proven NewScripts logic.
**Current focus:** v5.0 — defining requirements

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-03-21 — Milestone v5.0 started

## Accumulated Context

- v1.0-v4.0 shipped (44 phases, all complete)
- Factory/Abstraction/Repo pattern used for offline/online parity
- QACompiler has Item/Character/Region/Skill generators with full XML parsing
- MapDataGenerator has audio/image path resolution, branch/drive mapping
- Model2Vec bundled in light build, Qwen3 only in full build
- WEM decoder exists in MapDataGenerator source
- Landing page stable at 9290e310, deployed to Netlify
