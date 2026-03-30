# Phase 102: Codex Overhaul — QACompiler Graft + Bulk Load + Dropdown Navigation

## Goal

Replace the current fragmented Codex (5 separate nav buttons, broken pagination) with a unified system that:
1. Uses QACompiler's battle-tested category clustering logic
2. Bulk-loads all entities client-side (no pagination bugs)
3. Has a single "Codex" dropdown menu for ALL entity types
4. Properly categorizes Items, Quests, Characters, Skills, Gimmicks, Knowledge

## Architecture

### Navigation: Codex Dropdown Menu
```
[Codex ▾]
  ├── Items        (group hierarchy from ItemGroupNode)
  ├── Characters   (filename type + race/gender from use_macro)
  ├── Audio        (export path category tree)
  ├── Regions      (faction group hierarchy)
  ├── Quests       ← NEW (QAC quest_type: main/faction/challenge/minigame)
  ├── Skills       ← NEW (schema exists, needs route + UI)
  ├── Gimmicks     ← NEW (schema exists, needs route + UI)
  └── Knowledge    ← NEW (repurpose legacy CodexPage)
```
Game Data, Map, Status → remain as separate top-level buttons.

### Data Pipeline
```
Game XML files (StaticInfo/)
  ↓ MegaIndex entity parsers (graft QAC extraction patterns)
  ↓ Entity schemas (frozen dataclasses)
  ↓ Codex routes (bulk-load, no pagination)
  ↓ Frontend (client-side $derived search/filter + card grid)
```

## Plans (6 plans, 3 waves)

### Wave 1 (parallel): Backend Bulk Load + Dropdown Nav

**Plan 102-01: Remove Pagination from 4 Existing Routes**
- codex_items.py, codex_characters.py, codex_audio.py, codex_regions.py
- Remove offset/limit/has_more from routes + schemas
- Return ALL entities in one response

**Plan 102-02: Codex Dropdown Navigation**
- +layout.svelte: replace 5 buttons with 1 dropdown (8 entries)
- navigation.js: add goToQuestCodex, goToSkillCodex, goToGimmickCodex, goToKnowledgeCodex

### Wave 2 (parallel): Quest + Skills + Gimmicks Backend

**Plan 102-03: QuestEntry Schema + Parser (QACompiler Graft)**
- mega_index_schemas.py: add QuestEntry (strkey, name, desc, quest_type, quest_subtype, faction_key, source_file)
- mega_index_entity_parsers.py: add _parse_quest_info() — classify by subfolder + StrKey pattern
- mega_index.py: wire quest_by_strkey into build pipeline

**Plan 102-04: New Codex Routes (Quest + Skills + Gimmicks)**
- NEW codex_quests.py (3 endpoints: types, detail, list)
- NEW codex_skills.py (2 endpoints: detail, list)
- NEW codex_gimmicks.py (2 endpoints: detail, list)
- NEW schemas for all 3
- router.py: mount all 3

### Wave 3 (sequential): Frontend Bulk Load + New Pages

**Plan 102-05: Convert 4 Existing Pages to Bulk Load**
- Remove infinite scroll from ItemCodexPage, CharacterCodexPage, AudioCodexPage, RegionCodexPage
- Single fetch on mount, $derived for client-side filtering
- Keep category sidebars (client-side matching)

**Plan 102-06: 4 New Codex Pages**
- NEW QuestCodexPage.svelte (tabs by quest type, sub-tabs for faction subtypes)
- NEW SkillCodexPage.svelte (search + card grid)
- NEW GimmickCodexPage.svelte (search + card grid)
- Repurpose CodexPage.svelte as Knowledge browser (knowledge group tree nav)
- LDM.svelte: add routing for all 4 new pages

## Dependencies

- MegaIndex must be built (auto-builds on first request)
- QACompiler source at `RFC/NewScripts/QACompilerNEW/` (reference only, not runtime)
- Quest XML at `staticinfo_quest/` subfolder (main/, faction/, Challenge/, contents/)

## Success Criteria

1. Single Codex dropdown in nav → 8 entity types accessible
2. ALL pages bulk-load (no pagination, no infinite scroll bugs)
3. Client-side search across all entity fields (instant, no API calls)
4. Quests fully functional with type/subtype classification
5. Skills + Gimmicks browsable
6. Knowledge browsable with group hierarchy
7. QACompiler category patterns matched (filename types, quest subtypes, group hierarchy)

## Deferred
- Region/Map interactive visualization (needs design)
- Quest prerequisite chain visualization
- Audio WEM preview improvements
- VirtualList (add if perf needs it — CSS grid may suffice for <10k items)
