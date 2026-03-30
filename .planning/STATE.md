---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: Phase 101 COMPLETE — needs commit + build
last_updated: "2026-03-30T20:00:00.000Z"
progress:
  total_phases: 12
  completed_phases: 4
  total_plans: 12
  completed_plans: 10
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-30)

**Core value:** Real, working localization workflows with zero cloud dependency
**Current focus:** Phase 101 — merge-deep-graft

## v14.0 Completion Status

### Phase 93 — Debug/Fix — COMPLETE

### Phase 94 — Grid & TM + Demo Blockers — COMPLETE

### Phase 95 — Navigation — COMPLETE

### Phase 96 — GameData Polish — DEFERRED

### Phase 97 — TM Structural Fix — COMPLETE (10/10 PASS)

### Phase 98 — MEGA Graft MDG+LDE — COMPLETE (9/9 verified)

### Phase 99 — Svelte 4→5 Event Migration — COMPLETE (3/3 plans)

**Builds:**

- GitHub Build Light v14.0 — SUCCESS (2026-03-30, run 23727131467, 5/5 jobs green)
- Gitea CI — Run 571 triggered (2026-03-30)

## Session 2026-03-30 — MEGA Session

### Phase 99 Execution (COMPLETE)

- 3 plans, 2 waves, parallel agent execution
- AppModal wrapper isolates Carbon Modal Svelte 4 compatibility to ONE file
- 50+ deprecated on:event patterns migrated across 16+ files
- 5 duplicate AppModal imports from parallel agents fixed (build was failing)
- 1 pre-existing test fixed (SkillTreeInfo → SkillTreeInfoList root wrapper)

### QT Merge Graft (COMPLETE)

- 2 missing match modes implemented: strorigin_descorigin, strorigin_filename
- Both wired into cascade, single-mode dispatch, route validation
- parse_corrections now passes desc_origin/filepath fields
- 6-agent parallel code review caught 4 critical + 2 important issues, all fixed

### MDG Graft Audit (VERIFIED)

- FULL MATCH on all MDG patterns (virtual WRAP, XML sanitization, DDS fuzzy, data extraction)
- MegaIndex adds 8 new entity types + 7 reverse lookups + 7 composed dicts beyond MDG

### MegaIndex Logging (UPGRADED)

- 95%+ coverage, logger.exception for tracebacks
- Per-file extraction counts for faction/skill/gimmick
- Export loc and singleton init logging added

### Windows App Testing (PEARL PC) — 9 Issues Found

**Plan:** `docs/superpowers/plans/2026-03-30-windows-app-bugfix-plan.md`

**COMMITTED (c2b2e3d7):**

1. FIX-1: AI capabilities fetch URL (relative → getApiBase) — fixes "Model2Vec UNAVAILABLE" display
2. FIX-2: Factory.py deadlock — eager SQLite imports prevent _ModuleLock crash
3. FIX-3: Event parser case-sensitivity — grafted MDG lowercase attr pattern
4. FIX-4: MegaIndex logging improvements

**DONE (in working tree, not committed):**

- CASE-INSENSITIVE EVERYTHING: All 5 MegaIndex files — XML attr names, attr values, dict keys, lookups, strorigin, filenames. Zero case sensitivity anywhere. Matches MDG pattern.

**NEEDS IMPLEMENTATION (8 issues):**

5. BUG-5: Multi-language audio (3 folders: English/Korean/Chinese like MDG)
6. BUG-6: Image Korean fallback (StringID miss → try Korean text via R1 → badge)
7. BUG-7: LocaNext Status menu (NOT in Preferences — dedicated view with AI/MegaIndex/DB/WebSocket)
8. BUG-8: Merge direction (right-click = SOURCE, file dialog = TARGET)
9. BUG-9: Category column (too narrow + resize handle broken)
10. BUG-10: Dead "Project Settings" menu item — wire or remove
11. BUG-11: About LocaNext version hardcoded — auto-detect from build
12. BUG-12: About LocaNext cleanup — remove internal tool listing, add "Created by Neil Schmitt"

## What WORKS (confirmed by PEARL PC log)

- Model2Vec loaded: dim=256 ✓
- MegaIndex 7-phase build: 15.06s ✓
- Knowledge: 5,288 + 513 groups, Characters: 7,998, Items: 6,158
- Regions: 1,158, Factions: 135, Skills: 1,722, Gimmicks: 13,540
- DDS: 21,142, WEM: 57,535, StrOrigins: 173,675
- Images (C1): 3,005, Entity↔StringID (C6/C7): 26,251/55,552
- SQLite offline mode, WebSocket, GameData browse

## Session Continuity

Last session: 2026-03-30
Phase 100: COMPLETE — Build 23734591694 GREEN.
Phase 100b: EDITING PERF FIXES (session 2026-03-30 evening):
- FIXED: Enter linebreak — was inserting literal `<br/>` text, now inserts HTML `<br>` element
- FIXED: TM spam during editing (BUG-19) — `isEditing` flag skips TM fetch
- FIXED: Save freeze — optimistic UI (instant local update, async API, revert on fail)
- FIXED: Blur+keyboard double-save race — `isSaving` mutex guard
- FIXED: Hotkey bar labels updated (Enter=Linebreak, Ctrl+Enter=Save & Next)
- NOT YET BUILT — needs commit + build trigger

Phase 101: PLANNED — Merge Deep Graft (2 plans, 2 waves)

### Phase 101 Scope (from research)

**Root cause of BUG-21 + BUG-13:** Merge has NO identical-skip check. All 169,650 matched rows get "updated" in DB with the SAME value. Nothing visibly changed.

**BUG-15 (format string):** FALSE ALARM — Python % formatting is correct.
**BUG-22 (make file writable):** N/A — LocaNext writes to PostgreSQL, not disk files.

| Plan | Bugs | Wave | Scope | Status |
|------|------|------|-------|--------|
| 101-01 | BUG-21, BUG-13, BUG-23 | 1 | Identical-skip + detailed results | DONE |
| 101-02 | BUG-16, BUG-14 | 2 | Options wiring + progress + SSE | DONE |
| 101-03 | Merge architecture | 3 | QT-style disk write + folder merge | DONE |
| 101-04 | File explorer | 4 | Refresh button + delete artifact fix | DONE |

Phase 101-03 DETAILS (QT-style merge-to-disk):
- NEW endpoint: POST /api/ldm/merge/to-file — source DB rows → target file on disk
- NEW endpoint: POST /api/ldm/merge/to-folder — source folder → target folder (suffix matching)
- Uses QT's xml_transfer.py engine (merge_corrections_to_xml) for actual XML manipulation
- Electron: native file/folder dialog → gets PATH → backend reads, merges, writes back
- Browser fallback: old upload-based flow (for DEV mode)
- No more ghost files / upload artifacts
- Folder merge: right-click folder → pick target folder → matches by language suffix

Phase 101-04 DETAILS (File explorer fixes):
- Refresh button in right-click context menu (both item + background)
- Delete failure → refreshCurrentView() (no more stale optimistic state)
- Uploaded merge artifacts auto-cleaned after merge

Code review findings (tmx_tools.py — PRE-EXISTING, not from this session):
- `lang == 'ko'` should be `lang.startswith('ko')` for BCP-47
- Missing `is_desc` detection pipeline
- StringID column missing `num_format: '@'`
- These are tmx_tools sync issues, NOT blocking Phase 101

Next actions:
1. Commit all changes (13 files + 1 new)
2. Trigger build (needs user approval)
3. Test on PEARL PC
