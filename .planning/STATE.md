---
gsd_state_version: 1.0
milestone: v14.0
milestone_name: LocaNext v14.0
status: Phase 110 IN PROGRESS. Auth architecture fix + dashboard + audio.
last_updated: "2026-04-03T02:00:00.000Z"
progress:
  total_phases: 13
  completed_phases: 7
  total_plans: 22
  completed_plans: 22
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-30)

**Core value:** Real, working localization workflows with zero cloud dependency
**Current focus:** Phase 102 COMPLETE — awaiting build result

## v14.0 Completion Status

| Phase | Name | Status |
|-------|------|--------|
| 93 | Debug/Fix | COMPLETE |
| 94 | Grid & TM + Demo Blockers | COMPLETE |
| 95 | Navigation | COMPLETE |
| 96 | GameData Polish | DEFERRED |
| 97 | TM Structural Fix | COMPLETE |
| 98 | MEGA Graft MDG+LDE | COMPLETE |
| 99 | Svelte 4→5 Event Migration | COMPLETE |
| 100 | Windows App Bugfix (9 issues) | COMPLETE |
| 101 | Merge Deep Graft + Editing Perf | COMPLETE |
| 102 | Codex Overhaul | **COMPLETE** |

## Phase 102 — Codex Overhaul (COMPLETE 2026-03-30)

### Delivered
- Codex mega dropdown (8 entries) replaces 5 separate nav buttons
- Bulk load all codex pages (no pagination)
- 3 new routes: quests, skills, gimmicks + schemas
- QuestEntry schema + parser (QACompiler graft)
- 3 new frontend pages: Quest (tabs+subtabs), Skills, Gimmicks
- Greedy DDS 4-phase image resolution (A=knowledge, B=greedy attrs, C=knowledge_key chain, D=Korean name+desc R1)
- image_urls: List[str] in all schemas (stacked in UI)
- BUG-16 fixed: merge options in to-file + to-folder
- BUG-14 fixed: SSE streaming progress in FileMergeModal

### CRITICAL Fixes
- **Audio NEVER linked** in previous builds — SoundEventName from LocStr now extracted into D11
- **Categories WRONG** — D17 key now uses relative path, Sequencer/Dialog correctly detected
- **CategoryService race** — _mega_checked only set after confirmed build
- **CategoryService .lower()** — C7 lookup was case-sensitive, mixed-case StringIDs always missed

### Review (2 rounds, 8 agents each)
Round 1: node_elem typo, merge_to_folder pre-filters, quest dedup, SSE error handling
Round 2: category .lower(), _mega_checked race, SSE chunking, search crash, gimmick texture, merge_to_folder match_mode, dropdown overlap

### Build
- Build Light running: run 23748476606 (commit 0f56d162)
- 668 tests passed locally, 0 failed
- Previous builds: 23746963791 SUCCESS (partial), 23747794491 FAILED (test mock)

## What WORKS Now

| Feature | Status |
|---------|--------|
| Codex (8 entity types) | ✅ Dropdown nav, bulk load, client-side filter |
| Audio linking | ✅ SoundEventName → D11 → WEM (3 languages) |
| Categories | ✅ LDE 2-tier algorithm, relative path D17 key |
| DDS Images | ✅ 4-phase greedy (knowledge + attrs + knowledge_key + Korean R1) |
| Merge (single file) | ✅ 6 match modes, 10 options, stringid_only branching |
| Merge (folder batch) | ✅ Suffix recognition, pre-filters, match_mode branching |
| Merge (browser SSE) | ✅ Live progress streaming, cross-chunk handling |
| MegaIndex | ✅ 11 schemas, 35+ dicts, 7-phase build, quest parser |
| R1 reverse lookup | ✅ 7 entity types, name + desc indexed |
| Grid bulk load | ✅ Client-side search/filter/scroll |
| Svelte 5 | ✅ All runes, AppModal wrapper |
| Offline/Online | ✅ SQLite/PostgreSQL, auto-fallback |

## What Needs Testing (Next Session)

1. Check build result (run 23748476606)
2. If GREEN → Playground install + test:
   - Codex dropdown navigation (all 8 entries)
   - Audio playback in Audio Codex
   - Category correctness (Sequencer files should show "Sequencer" not "Quest")
   - Images in Codex cards (greedy DDS should find more than before)
   - Quest/Skill/Gimmick pages populated
   - Merge single file + folder batch

## Deferred / Future

- Phase 96: GameData tabs
- Region/Map interactive visualization
- LAN Server Mode
- QuickTranslate standalone app
- Knowledge codex page (currently uses legacy CodexPage)
- Fine-grained Sequencer subcategories (9 patterns defined but unused)
- VirtualList component (add if scroll perf needs it)
