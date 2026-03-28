---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: unknown
last_updated: "2026-03-28T21:08:38.929Z"
progress:
  total_phases: 9
  completed_phases: 0
  total_plans: 5
  completed_plans: 2
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-28)

**Core value:** Real, working localization workflows with zero cloud dependency
**Current focus:** Phase 98 — MEGA Graft -- MDG/LDE Battle-Tested Techniques

## v14.0 Completion Status

### Phase 93 — Debug/Fix — COMPLETE

### Phase 94 — Grid & TM + Demo Blockers — COMPLETE

### Phase 95 — Navigation — COMPLETE

### Phase 96 — GameData Polish — DEFERRED

### Phase 97 — TM Structural Fix — COMPLETE (10/10 PASS)

**Builds:**

- GitHub Build Light v14.0 — SUCCESS (2026-03-28, with Model2Vec bundled)
- GitHub Build QA v14.0 — SUCCESS (2026-03-28, full test suite 1599 passed)

## What Was Done This Session (2026-03-28)

1. **Phase 97 frontend verification** — 4 remaining tasks tested via Playwright, all PASS
2. **Committed Phase 97** — 16 files, 543 insertions (commit 5ce120cc)
3. **Fixed merge test failure** — `transfer_adapter.py` missing `ignore_spaces`/`ignore_punctuation` passthrough (commit 1b48ebc3)
4. **CI trigger format fix** — `BUILD_TRIGGER.txt` requires EXACT match (`Build Light`, not `Build Light v14.0`)
5. **Build Light workflow change** — removed Model2Vec download from CI (commit 30f4c623). User places model files manually at `<install>\resources\models\Model2Vec\`
6. **Memory audit** — deleted 7 stale/duplicate files, merged 2 CI rules, updated 4 files. 93→86 files.

## Uncommitted Changes

- `test_multi_language_merge` still fails locally (same `ignore_spaces` passthrough issue in a different code path)
- `.planning/STATE.md` (this file)

## Next Session

1. Fix `test_multi_language_merge` (same pattern as transfer_adapter fix)
2. Phase 96 (GameData tabs) or new work
3. Test Build Light installer on offline PC (place Model2Vec at `resources\models\Model2Vec\`)

## DB State

- PostgreSQL: 1 TM (id=796, Korean_TM_Test), folder 97 (Korean), is_active=true
- SQLite offline: clean

## Key Lessons This Session

- **BUILD_TRIGGER.txt** = EXACT match only (`Build`, `Build QA`, `Build Light`, `TROUBLESHOOT`). No extra text.
- **Default = Build Light** (offline). Never use `Build` unless user explicitly says QA mode.
- **Model2Vec NOT bundled in Build Light** — user has files, places manually after install at `resources\models\Model2Vec\`
- **Grill yourself immediately** — after doing A, verify A worked before moving to B
- **Check individual job statuses** — a "successful" run can have all jobs skipped

## Session Continuity

Last session: 2026-03-28
Build Light RUNNING: run ID 23686307001 (includes xml_handler fix + transfer_adapter fix)
Next actions:

1. Confirm sequential-thinking MCP works (`/clear` or restart Claude Code)
2. Check build result: `gh run view 23686307001`
3. Test installer on offline PC — place Model2Vec at `resources\models\Model2Vec\`
4. Fix test_multi_language_merge (pre-existing, not in CI)
5. Phase 96 or new work
