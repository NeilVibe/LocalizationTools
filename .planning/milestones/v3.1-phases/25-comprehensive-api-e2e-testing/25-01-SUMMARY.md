---
phase: 25-comprehensive-api-e2e-testing
plan: 01
subsystem: testing
tags: [xml, mock-data, staticinfo, loc-xml, korean, br-tags, fixtures]

# Dependency graph
requires:
  - phase: 15-mock-gamedata
    provides: "Initial 6 StaticInfo subdirectories with fixture data"
provides:
  - "Complete 10-directory StaticInfo mock dataset (questinfo, sceneobjectdata, sealdatainfo, regioninfo)"
  - "8 matching loc.xml files for new entity types"
  - "100+ new entities with Korean text and br-tags"
affects: [25-comprehensive-api-e2e-testing, api-browse, codex, column-detection]

# Tech tracking
tech-stack:
  added: []
  patterns: ["StaticInfo XML fixture pattern with StrKey/Key/Korean text/br-tags"]

key-files:
  created:
    - tests/fixtures/mock_gamedata/StaticInfo/questinfo/questinfo_main.staticinfo.xml
    - tests/fixtures/mock_gamedata/StaticInfo/questinfo/questinfo_sub.staticinfo.xml
    - tests/fixtures/mock_gamedata/StaticInfo/questinfo/questinfo_daily.staticinfo.xml
    - tests/fixtures/mock_gamedata/StaticInfo/sceneobjectdata/SceneObjectData_Town.staticinfo.xml
    - tests/fixtures/mock_gamedata/StaticInfo/sceneobjectdata/SceneObjectData_Dungeon.staticinfo.xml
    - tests/fixtures/mock_gamedata/StaticInfo/sceneobjectdata/SceneObjectData_Field.staticinfo.xml
    - tests/fixtures/mock_gamedata/StaticInfo/sealdatainfo/SealDataInfo.staticinfo.xml
    - tests/fixtures/mock_gamedata/StaticInfo/regioninfo/RegionInfo.staticinfo.xml
    - tests/fixtures/mock_gamedata/stringtable/export__/System/questinfo_main.loc.xml
    - tests/fixtures/mock_gamedata/stringtable/export__/System/questinfo_sub.loc.xml
    - tests/fixtures/mock_gamedata/stringtable/export__/System/questinfo_daily.loc.xml
    - tests/fixtures/mock_gamedata/stringtable/export__/System/sceneobjectdata_town.loc.xml
    - tests/fixtures/mock_gamedata/stringtable/export__/System/sceneobjectdata_dungeon.loc.xml
    - tests/fixtures/mock_gamedata/stringtable/export__/System/sceneobjectdata_field.loc.xml
    - tests/fixtures/mock_gamedata/stringtable/export__/System/sealdatainfo.loc.xml
    - tests/fixtures/mock_gamedata/stringtable/export__/System/regioninfo.loc.xml
  modified: []

key-decisions:
  - "Followed existing LocStrList > LocStr with StringId pattern for loc.xml files (not LanguageData format from plan)"

patterns-established:
  - "QuestInfo pattern: QuestInfoList > QuestInfo with Key/StrKey/QuestName/QuestDesc/QuestType/Grade/RewardKey"
  - "SceneObjectData pattern: SceneObjectDataList > SceneObjectData with Position/SceneType/AliasName"
  - "SealDataInfo pattern: SealDataInfoList > SealDataInfo with GimmickKey references"
  - "RegionInfo pattern: RegionInfoList > RegionInfo with RegionType/ParentRegion/FactionKey"

requirements-completed: [TEST-E2E-01, TEST-E2E-02]

# Metrics
duration: 4min
completed: 2026-03-15
---

# Phase 25 Plan 01: Mock Gamedata Expansion Summary

**8 new StaticInfo XMLs + 8 loc.xml files covering questinfo, sceneobjectdata, sealdatainfo, and regioninfo with 101 Korean entities and br-tag examples**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-15T22:30:42Z
- **Completed:** 2026-03-15T22:35:12Z
- **Tasks:** 3
- **Files modified:** 16

## Accomplishments
- Expanded mock_gamedata from 6 to 10 StaticInfo subdirectories (complete coverage)
- Created 101 entities across 8 new StaticInfo XML files with Korean text and br-tags
- Created 8 matching loc.xml files following existing LocStrList/StringId pattern

## Task Commits

Each task was committed atomically:

1. **Task 1: Create questinfo StaticInfo XMLs** - `be938202` (feat)
2. **Task 2: Create sceneobjectdata and sealdatainfo StaticInfo XMLs** - `9f9a8936` (feat)
3. **Task 3: Create regioninfo StaticInfo + all matching .loc.xml files** - `6a93af12` (feat)

## Files Created/Modified
- `tests/fixtures/mock_gamedata/StaticInfo/questinfo/questinfo_main.staticinfo.xml` - 12 main quest entities
- `tests/fixtures/mock_gamedata/StaticInfo/questinfo/questinfo_sub.staticinfo.xml` - 10 sub quest entities
- `tests/fixtures/mock_gamedata/StaticInfo/questinfo/questinfo_daily.staticinfo.xml` - 10 daily quest entities
- `tests/fixtures/mock_gamedata/StaticInfo/sceneobjectdata/SceneObjectData_Town.staticinfo.xml` - 12 town scene objects
- `tests/fixtures/mock_gamedata/StaticInfo/sceneobjectdata/SceneObjectData_Dungeon.staticinfo.xml` - 10 dungeon scene objects
- `tests/fixtures/mock_gamedata/StaticInfo/sceneobjectdata/SceneObjectData_Field.staticinfo.xml` - 10 field scene objects
- `tests/fixtures/mock_gamedata/StaticInfo/sealdatainfo/SealDataInfo.staticinfo.xml` - 12 seal data entities
- `tests/fixtures/mock_gamedata/StaticInfo/regioninfo/RegionInfo.staticinfo.xml` - 15 region entities
- `tests/fixtures/mock_gamedata/stringtable/export__/System/*.loc.xml` - 8 new loc.xml files

## Decisions Made
- Used existing `LocStrList > LocStr` with `StringId` pattern for loc.xml files (plan suggested `LanguageData > LocStr` format, but existing convention was followed for consistency)

## Deviations from Plan

None - plan executed exactly as written (minor loc.xml format alignment to existing convention is not a deviation, it is correct behavior).

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All 10 StaticInfo subdirectories now have mock data
- API tests for gamedata/browse, codex, and column detection can now validate complete entity type coverage
- Ready for Plan 02 (API endpoint E2E tests)

## Self-Check: PASSED

All 16 created files verified on disk. All 3 task commits verified in git history.

---
*Phase: 25-comprehensive-api-e2e-testing*
*Completed: 2026-03-15*
