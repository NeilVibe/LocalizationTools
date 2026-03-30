# Phase 102: Codex Overhaul — QACompiler Graft + Bulk Load + Dropdown Navigation

## Goal

Replace the current broken/incomplete Codex with a fully functional system that:
1. Uses QACompiler's battle-tested category clustering logic
2. Bulk-loads all entities client-side (no pagination bugs)
3. Has a single "Codex" nav button with a dropdown menu for entity types
4. Properly categorizes Items, Quests, Characters, Gimmicks (defer Regions/Map)

## Architecture

### Navigation: Codex Dropdown Menu
```
[Codex ▾]
  ├── Items        (QAC ItemType clustering)
  ├── Quests       (QAC QuestType clustering) ← NEW, currently missing
  ├── Characters   (QAC CharacterType + Job/Race/Gender)
  ├── Gimmicks     (existing, needs category)
  └── Knowledge    (existing, works)
```
Region/Map → DEFERRED (interactive map needs proper design)

### Data Pipeline: QACompiler → MegaIndex → Codex
```
Game XML files (StaticInfo/)
  ↓ MegaIndex entity parsers (graft QAC extraction)
  ↓ Entity schemas (add type/category fields)
  ↓ Codex routes (bulk-load, no pagination)
  ↓ Frontend (client-side search/filter/scroll)
```

## Plans

### Plan 102-01: Schema + Parser Graft (Wave 1)
**Files:** `mega_index_schemas.py`, `mega_index_entity_parsers.py`

- **ItemEntry**: Add `item_type` field (Weapon, Armor, Consumable, Quest, Material, Equipment, etc.)
  - Parser: extract `ItemType` attribute from `<ItemInfo>` XML elements
  - Graft from: `QACompilerNEW/generators/item.py`

- **CharacterEntry**: Add `character_type`, `race`, `gender` fields
  - Parser: extract `CharacterType`, `Race`, `Gender` from `<CharacterInfo>` XML
  - Graft from: `QACompilerNEW/generators/region.py` (character extraction)

- **NEW QuestEntry**: Create schema + parser for `<QuestInfo>` elements
  - Fields: `strkey`, `name`, `desc`, `quest_type` (Main/Sub/Daily/Challenge/Minigame), `source_file`
  - Parser: extract from `questinfo*.xml` files
  - Graft from: `QACompilerNEW/generators/quest.py`
  - Register as D7 entity type in MegaIndex (currently placeholder)

- **GimmickEntry**: Add `gimmick_type` if available in XML

### Plan 102-02: Codex Routes — Bulk Load (Wave 1)
**Files:** `codex_items.py`, `codex_characters.py`, `codex_audio.py`, `codex_regions.py`, NEW `codex_quests.py`

- Remove pagination (offset/limit/has_more) from all Codex list endpoints
- Return ALL entities in one response (they're already in MegaIndex memory)
- Add category/type filter query params
- Add quest list endpoint
- Expose region `node_type` for filtering

### Plan 102-03: Frontend — Codex Dropdown + Bulk Client-Side (Wave 2)
**Files:** `+layout.svelte`, `CodexPage.svelte`, all Codex pages

- Replace individual Codex nav tabs with single "Codex" dropdown button
- Dropdown shows: Items, Quests, Characters, Gimmicks, Knowledge
- Each page: bulk-load all entities on mount, client-side search/filter
- Category sidebar filter (like QACompiler's folder tree)
- Remove infinite scroll / pagination logic
- Virtual scroll for large lists (Items: 6k, Characters: 8k)

### Plan 102-04: QACompiler Clustering Logic (Wave 2)
**Files:** NEW `server/tools/ldm/services/codex_clustering.py`

- Graft QACompiler's clustering thresholds:
  - `MERGE_UP_THRESHOLD = 50` (groups <50 items merge into parent)
  - `FOLDER_MIN_THRESHOLD = 100` (folders <100 items merge into "Others")
- Item depth-based color coding
- Quest source-folder classification
- Character job/race grouping

## Deferred

- **Region/Map**: Interactive map needs proper design (current implementation unclear)
- **Audio Codex**: Works but could use WEM preview player
- **Skill Codex**: Not yet built (1,722 skills in MegaIndex)

## Dependencies

- MegaIndex must be built (already auto-builds on first request)
- QACompiler source at `RFC/NewScripts/QACompilerNEW/` (reference only, not runtime)
- Game XML fixtures at `tests/fixtures/mock_gamedata/` for testing

## Success Criteria

1. Single Codex dropdown in nav → 5 entity types accessible
2. Items show ItemType category (Weapon, Armor, etc.) with sidebar filter
3. Quests fully functional (Main/Sub/Daily/Challenge)
4. Characters show CharacterType + Job + Race/Gender
5. All pages bulk-load (no pagination, no infinite scroll bugs)
6. Client-side search across all entity fields
7. QACompiler clustering thresholds applied
