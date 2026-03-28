---
phase: 98-mega-graft-mdg-lde-battle-tested-techniques
plan: 04
subsystem: ldm-gamedata
tags: [category-mapper, korean-detection, lde-graft, gamedev-grid]
dependency_graph:
  requires: [98-01]
  provides: [category_mapper_service, korean_text_state, filename_index, gamedev_grid_columns]
  affects: [server/tools/ldm/routes/gamedata.py, locaNext/src/lib/components/ldm/grid/CellRenderer.svelte]
tech_stack:
  added: []
  patterns: [two-tier-classification, priority-keyword-override, korean-3range-regex]
key_files:
  created:
    - server/tools/ldm/services/category_mapper.py
  modified:
    - server/tools/ldm/routes/gamedata.py
    - locaNext/src/lib/components/ldm/grid/CellRenderer.svelte
    - locaNext/src/lib/components/ldm/grid/gridState.svelte.ts
decisions:
  - Replaced old Phase 5.1 category_mapper.py entirely (was simple path-string matcher, now full LDE algorithm)
  - Reused existing korean_detection.py pattern but inlined in category_mapper for single-import convenience
  - Added category/file_name/text_state to extra_data dict rather than new schema fields (non-breaking)
  - Korean detection checks Str/StrOrigin/Name/Desc/DescOrigin attributes in priority order
metrics:
  duration: 223s
  completed: "2026-03-28T21:18:21Z"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 4
---

# Phase 98 Plan 04: LDE Category Mapper + Korean Detection + GameDev Grid Columns Summary

Grafted LDE's full two-tier category mapper into LocaNext with Korean untranslated detection and FileName column for gamedev grid.

## One-liner

LDE two-tier category mapper with priority keyword override, 3-range Korean detection, and FileName/TextState columns in gamedev grid.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Create category_mapper.py with LDE algorithm | e0e1ba05 | server/tools/ldm/services/category_mapper.py |
| 2 | Enrich gamedata rows + frontend columns | 5246705a | gamedata.py, CellRenderer.svelte, gridState.svelte.ts |

## What Was Built

### Task 1: TwoTierCategoryMapper Service
- **Full LDE algorithm** grafted from `LanguageDataExporter/exporter/category_mapper.py`
- **Tier 1 (STORY)**: Dialog subfolder detection (AIDialog, QuestDialog, NarrationDialog) + Sequencer
- **Tier 2 (GAME_DATA)**: Two-phase matching:
  - Phase 1: Priority keywords (gimmick > item > quest > skill > character > region > faction)
  - Phase 2: Standard folder/keyword patterns (17 patterns)
- **Korean detection**: 3-range regex (AC00-D7AF + 1100-11FF + 3130-318F)
- **Text state**: `get_text_state()` returns KOREAN or TRANSLATED
- **FileName index**: `build_filename_index()` scans XML for StrKey attributes
- **Legacy API**: `categorize_string()` preserved for backward compatibility

### Task 2: GameData Route + Frontend Columns
- **Backend enrichment**: Each GameDataRow gets category, file_name, text_state in extra_data
- **Frontend columns**: Category (tag), FileName (monospace), TextState (badge) in gamedev grid
- **Visual indicators**: KOREAN = amber badge, TRANSLATED = green badge
- **Category colors**: Synced with existing CATEGORY_COLORS map
- **Grid width**: getFixedWidthAfter updated from 350px to 660px for new columns

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Existing category_mapper.py had incompatible API**
- **Found during:** Task 1
- **Issue:** Old Phase 5.1 category_mapper.py used `categorize(file_path_str, text)` API instead of `get_category(Path)`. Also had extra keywords (npc, monster, buff, etc.) not in LDE.
- **Fix:** Complete rewrite preserving `categorize_string()` for backward compatibility
- **Files modified:** server/tools/ldm/services/category_mapper.py

**2. [Rule 2 - Missing functionality] GameDataRow schema doesn't have category/file_name/text_state fields**
- **Found during:** Task 2
- **Issue:** Adding new fields to Pydantic model would break API contract
- **Fix:** Added to extra_data dict instead (non-breaking, frontend reads from extra_data)
- **Files modified:** server/tools/ldm/routes/gamedata.py

## Known Stubs

None -- all data is live from XML parsing and LDE algorithm.

## Verification Results

- Python import test: PASSED (TwoTierCategoryMapper, contains_korean, get_text_state, build_filename_index)
- Korean 3-range test: PASSED (syllables, jamo, compat jamo)
- Priority keyword override: PASSED (KnowledgeInfo_Item.xml -> Item, not Knowledge)
- Category mapping: PASSED (Dialog, Sequencer, Quest, Gimmick)
- Legacy API: PASSED (categorize_string backward compat)
- Frontend grep: PASSED (category_mapper: 3, gameDevDynamicColumns: 1, text_state/fileName: 5)
