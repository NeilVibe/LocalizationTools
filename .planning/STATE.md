---
gsd_state_version: 1.0
milestone: v14.0
milestone_name: — Active)
status: executing
stopped_at: Completed 93-01-PLAN.md
last_updated: "2026-03-27T05:39:42Z"
progress:
  total_phases: 57
  completed_phases: 44
  total_plans: 101
  completed_plans: 98
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-27)

**Core value:** Real, working localization workflows with zero cloud dependency
**Current focus:** Phase 97 — TM Structural Fix + Full Verification

**Plan:** `.planning/milestones/v14.0-phases/97-tm-structural-fix/97-PLAN.md`

### Task Status (6/10 PASS, 4 need frontend test)
- Task 1: getCurrentScope wiring — needs frontend test (navigate to folder, click Upload, check modal heading)
- Task 2: Upload + folder assignment — **PASS** (API verified: tm_id=796, folder=97)
- Task 3: TM auto-activation — **PASS** (is_active=True fix applied in code + DB)
- Task 4: FileUploader spinner — needs frontend test (select file, should show checkmark not spinner)
- Task 5: Upload progress — needs frontend test (should reach 100%, not stuck at 90%)
- Task 6: Projects endpoint — **PASS** (200 OK, owner_id Optional)
- Task 7: Breadcrumb — needs frontend test (Offline Storage > folder, not doubled)
- Task 8: Image chain — **PASS** (has_image=true)
- Task 9: Audio chain — **PASS** (stream 200, 4454 bytes WAV)
- Task 10: Merge modal — needs frontend test (Apps > Merge, check normalization toggles)

### Code Changes NOT YET COMMITTED
- TMExplorerGrid.svelte: dedup, getCurrentScope, removed Unassigned, breadcrumb fix
- TMUploadModal.svelte: status="complete" on FileUploader
- TMPage.svelte: header button passes getCurrentScope()
- CellRenderer.svelte: yellow→grey
- +layout.svelte: Merge to Apps dropdown
- tm_crud.py: background indexing, _background_index_tm
- tm_repo.py: is_active=True on assign
- tm_assignment.py: folder dedup in merge
- media_converter.py: RIFF header detection
- merge.py + xml_transfer.py + text_utils.py: ignore_spaces/ignore_punctuation
- project.py schema: owner_id Optional
- FilesPage.svelte: Offline Storage skip nested project

### DB State
- PostgreSQL: 1 TM (id=796, Korean_TM_Test), assigned to folder 97 (Korean), is_active=true
- SQLite offline: clean (0 TMs), stale PC platform removed

### Next Session
1. Use sequential thinking MCP (will activate on /clear)
2. Frontend test remaining 4 tasks
3. Commit all changes
4. Build on Gitea (test) → GitHub Build Light (production)

## Current Position

Phase: 93 COMPLETE, 94 COMPLETE, 95 COMPLETE
Next: Phase 96 (GameData categories → tabs, CrimsonDesert.gg style)

## v14.0 Plan Summary (11 original + 2 new from testing)

### Phase 93 — Debug/Fix (Plan 01 DONE)

1. ~~Codex list infinite loop~~ ✅ FIXED (commit ecca01bf)
2. ~~Remote logger feedback loop~~ ✅ FIXED (commit e14fe56e)
3. v13.0 E2E verification — grid ✅, images ✅, audio ✅ (stream fix), TM ✅ (dedup fix)

### Grid & TM + Demo Blockers (Phase 94)

4. ~~TM page crash~~ ✅ FIXED — dedup filter in TMExplorerGrid.svelte (deduplicateItems helper)
5. ~~Audio stream broken~~ ✅ FIXED — RIFF header detection bypass in media_converter.py (mock WEMs are WAVs)
6. ~~TM upload~~ ✅ VERIFIED WORKING — endpoint + modal both functional, test upload succeeded (1 entry)
7. TM assignment — drag-drop already built in TMExplorerGrid, Unassigned section shows uploaded TMs
8. ~~Yellow cell default color~~ ✅ FIXED — translated status now neutral grey (#8d8d8d) instead of amber (#c6a300)
9. (Optional) Qwen3-TTS voice generation — installed, voice profiles defined in Phase 41 CONTEXT.md

### Navigation (Phase 95) — COMPLETE

7. ~~Merge button~~ ✅ REMOVED from top-level nav (still accessible via FilesPage context menu)

### GameData Polish (Phase 96)

8. GameData categories → auto-parsed TABS
9. CrimsonDesert.gg visual reference style

### Protocols (Apply immediately, not phases)

10. Debug protocol upgrades — sequential thinking, Viking+Ruflo
11. Playwright → Qwen+CDP for vision reviews

## Accumulated Context

### Decisions

- v13.0 complete: Branch+Drive, media fallback, MegaIndex split
- v12.0 complete: Dual threshold 92%/62%, AC Context Engine
- Build fix: `$derived(getVisibleRows())` → infinite loop, use `$derived.by()`
- Portproxy on 8888 needs admin elevation to remove
- Plain Map for tabCache (same pattern as rowHeightCache fix) -- eliminates reactivity cascade
- 3-layer logger protection: re-entrancy + rate limit (10/5s) + URL filter

### Key Patterns (from v13.0 debugging)

- `$effect` → `$state` loops cause infinite API calls (BranchDriveSelector: 161k calls)
- `$state(new Map())` in render loops = O(n²) freeze
- `$state.snapshot` required for >10k iterations
- CDP deep monitor catches what code review + Tribunal miss

## Session Continuity

Last session: 2026-03-27
Stopped at: Completed 93-01-PLAN.md
Next action: Execute 93-02 — E2E verification of v13.0 features
