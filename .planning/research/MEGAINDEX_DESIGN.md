# MegaIndex Design Document

**Designed:** 2026-03-21
**Domain:** Unified game data lookup index spanning MapDataGenerator + QACompiler + LocaNext server
**Confidence:** HIGH (all findings from direct source code analysis of 10 files across 3 codebases)

---

## Executive Summary

The MegaIndex is a single Python service that parses all game data XML files once and builds a complete graph of interconnected dictionaries. Every entity (item, character, region, knowledge, audio) becomes reachable from every key type (StrKey, StringId, KnowledgeKey, EventName, UITextureName) in O(1) time.

Today, three independent codebases redundantly parse the same XML files with incompatible key conventions:
- **MapDataGenerator** (`core/linkage.py`): `LinkageResolver` + `AudioIndex` + `DDSIndex` + `KnowledgeLookup`
- **QACompiler** (`generators/base.py`): `load_knowledge_data()` + `load_language_tables()` + `build_export_indexes()`
- **LocaNext server** (`codex_service.py` + `mapdata_service.py`): `CodexService._registry` + `MapDataService._knowledge_table`

The MegaIndex replaces all three with one unified build, one shared memory footprint, and O(1) lookups in every direction.

---

## 1. Every Dict Needed

### 1A. Direct Dicts (built from parsing XML/files)

| # | Name | Key Type + Example | Value Type + Example | Source | Build Method | Est. Size |
|---|------|--------------------|----------------------|--------|-------------|-----------|
| D1 | `knowledge_by_strkey` | `str "Knowledge_Region_Calpheon"` | `KnowledgeEntry(name, desc, ui_texture_name, group_key, source_file)` | `knowledgeinfo/*.xml` `<KnowledgeInfo>` elements | Direct parse: StrKey attr | ~15,000 |
| D2 | `character_by_strkey` | `str "CharInfo_Varon"` | `CharacterEntry(name, desc, knowledge_key, use_macro, age, job, ui_icon_path, source_file)` | `characterinfo/*.staticinfo.xml` `<CharacterInfo>` elements | Direct parse: StrKey attr | ~8,000 |
| D3 | `item_by_strkey` | `str "ItemInfo_BlackStar_Sword"` | `ItemEntry(name, desc, knowledge_key, group_key, source_file, inspect_entries)` | `iteminfo/*.staticinfo.xml` `<ItemInfo>` elements + `knowledgeinfo/` for items in Knowledge mode | Direct parse: StrKey attr | ~20,000 |
| D4 | `region_by_strkey` | `str "FactionNode_Calpheon_City"` | `RegionEntry(name, desc, knowledge_key, world_position, node_type, parent_strkey, source_file)` | `factioninfo/*.xml` `<FactionNode>` elements | Direct parse: StrKey attr | ~5,000 |
| D5 | `faction_by_strkey` | `str "Faction_Calpheon"` | `FactionEntry(name, knowledge_key, group_strkey, source_file, node_strkeys: List[str])` | `factioninfo/*.xml` `<Faction>` elements | Direct parse: StrKey attr | ~200 |
| D6 | `faction_group_by_strkey` | `str "FactionGroup_World"` | `FactionGroupEntry(group_name, knowledge_key, source_file, faction_strkeys: List[str])` | `factioninfo/*.xml` `<FactionGroup>` elements | Direct parse: StrKey attr | ~30 |
| D7 | `skill_by_strkey` | `str "SkillInfo_MeteorShower"` | `SkillEntry(name, desc, learn_knowledge_key, source_file)` | `skillinfo/*.staticinfo.xml` `<SkillInfo>` elements | Direct parse: StrKey attr | ~3,000 |
| D8 | `gimmick_by_strkey` | `str "GimmickGroup_Seal01"` | `GimmickEntry(name, desc, seal_desc, source_file)` | `gimmickinfo/*.staticinfo.xml` `<GimmickGroupInfo>` elements | Direct parse: StrKey attr | ~2,000 |
| D9 | `dds_by_stem` | `str "cd_knowledgeimage_node_calpheon"` | `Path("/mnt/f/perforce/.../image/cd_knowledgeimage_node_calpheon.dds")` | `texture/image/**/*.dds` files | Filesystem scan: `rglob("*.dds")`, key = `stem.lower()` | ~50,000 |
| D10 | `wem_by_event` | `str "play_npc_greeting_01"` | `Path("/mnt/f/perforce/.../English(US)/play_npc_greeting_01.wem")` | `sound/windows/{lang}/**/*.wem` files | Filesystem scan: `rglob("*.wem")`, key = `stem.lower()` | ~80,000 per lang |
| D11 | `event_to_stringid` | `str "play_npc_greeting_01"` (lowercase) | `str "NPC_GREETING_01_NAME"` (exact case) | `export__/**/*.xml` elements with SoundEventName + StringId attrs | Direct parse: case-insensitive attr extraction | ~60,000 |
| D12 | `stringid_to_strorigin` | `str "NPC_GREETING_01_NAME"` | `str "인사말 01"` (Korean source text) | `loc/languagedata_KOR.xml` `<LocStr>` elements | Direct parse: StringId -> StrOrigin | ~200,000 |
| D13 | `stringid_to_translations` | `str "NPC_GREETING_01_NAME"` | `Dict[str, str] {"eng": "Greeting 01", "fre": "Salutation 01", ...}` | `loc/languagedata_{code}.xml` `<LocStr>` elements (14 languages) | Direct parse: StringId -> {lang: Str} | ~200,000 |
| D14 | `item_group_hierarchy` | `str "ItemGroup_Weapon_Sword"` | `ItemGroupNode(group_name, parent_strkey, child_strkeys, item_strkeys)` | `iteminfo/*.staticinfo.xml` `<ItemGroupInfo>` elements | Direct parse: StrKey + parent traversal | ~2,000 |
| D15 | `knowledge_group_hierarchy` | `str "KnowledgeGroup_Region"` | `KnowledgeGroupNode(group_name, child_strkeys)` | `knowledgeinfo/*.xml` `<KnowledgeGroupInfo>` elements | Direct parse: StrKey + GroupName | ~500 |
| D16 | `region_display_names` | `str "Knowledge_Region_Calpheon"` (KnowledgeKey) | `str "칼페온 수도"` (DisplayName) | `factioninfo/*.xml` `<RegionInfo>` elements | Direct parse: KnowledgeKey -> DisplayName | ~3,000 |
| D17 | `export_file_stringids` | `str "characterinfo_npc.staticinfo"` (normalized filename) | `Set[str] {"CHAR_NPC_01_NAME", "CHAR_NPC_02_NAME", ...}` | `export__/**/*.loc.xml` `<LocStr>` elements | Direct parse: filename stem -> {StringId, ...} | ~500 files |
| D18 | `ordered_export_index` | `str "characterinfo_npc.staticinfo"` | `Dict[str, List[str]] {normalized_kor: [sid1, sid2, ...]}` | `export__/**/*.loc.xml` `<LocStr>` elements | Direct parse: preserves XML document order | ~500 files |
| D19 | `strkey_to_devmemo` | `str "fishing"` (StrKey.lower()) | `str "낚시"` (DevMemo/DevComment Korean text) | `StaticInfo/**/*.xml` ALL elements with StrKey | Broad scan: StrKey -> DevMemo or DevComment | ~50,000 |
| D20 | `event_to_export_path` | `str "play_npc_greeting_01"` | `str "Dialog/QuestDialog"` (relative dir from export root) | `export__/**/*.xml` (directory structure) | Computed during D11 build: `xml_path.relative_to(export_folder).parent` | ~60,000 |
| D21 | `event_to_xml_order` | `str "play_npc_greeting_01"` | `int 42` (global element position) | `export__/**/*.xml` element iteration order | Counter during D11 build, optionally overridden by VRS | ~60,000 |

### 1B. Reverse Dicts (inverted from direct dicts)

| # | Name | Key -> Value | Built From | Est. Size |
|---|------|-------------|-----------|-----------|
| R1 | `name_kr_to_strkeys` | `str "바론" -> List[str] ["CharInfo_Varon", ...]` | Invert D2.name, D3.name, D4.name, D1.name | ~40,000 |
| R2 | `knowledge_key_to_entities` | `str "Knowledge_Region_Calpheon" -> List[Tuple[str, str]] [("region", "FactionNode_Calpheon"), ("character", "CharInfo_Guard")]` | Scan D2.knowledge_key, D3.knowledge_key, D4.knowledge_key, D7.learn_knowledge_key | ~15,000 |
| R3 | `stringid_to_event` | `str "NPC_GREETING_01_NAME" -> str "play_npc_greeting_01"` | Invert D11 | ~60,000 |
| R4 | `ui_texture_to_strkeys` | `str "cd_knowledgeimage_node_calpheon" -> List[str] ["Knowledge_Region_Calpheon"]` | Invert D1.ui_texture_name (lowercased) | ~10,000 |
| R5 | `source_file_to_strkeys` | `str "characterinfo_npc.staticinfo.xml" -> List[Tuple[str, str]] [("character", "CharInfo_Varon"), ...]` | Scan all direct dicts source_file field | ~500 files |
| R6 | `strorigin_to_stringids` | `str "인사말 01" (normalized) -> List[str] ["NPC_GREETING_01_NAME", ...]` | Invert D12 with normalize_placeholders() | ~180,000 |
| R7 | `group_key_to_items` | `str "ItemGroup_Weapon_Sword" -> List[str] ["ItemInfo_BlackStar_Sword", ...]` | From D3 scanning: accumulate items per group | ~2,000 |

### 1C. Composed Dicts (transitive lookups, A->B + B->C = A->C)

| # | Name | Chain | Key -> Value | Built From | Est. Size |
|---|------|-------|-------------|-----------|-----------|
| C1 | `strkey_to_image_path` | StrKey -> KnowledgeInfo.UITextureName -> DDS path | `str "Knowledge_Region_Calpheon" -> Path("...calpheon.dds")` | D1.ui_texture_name + D9 | ~10,000 |
| C2 | `strkey_to_audio_path` | StrKey -> (entity has event) -> WEM path | Complex -- see Section 6 | D11 + D10 | ~5,000 |
| C3 | `stringid_to_audio_path` | StringId -> event_name -> WEM path | `str "NPC_GREETING_01_NAME" -> Path("...play_npc_greeting_01.wem")` | R3 + D10 | ~60,000 |
| C4 | `event_to_script_kr` | event -> StringId -> StrOrigin (Korean script line) | `str "play_npc_greeting_01" -> str "인사말 01"` | D11 + D12 | ~60,000 |
| C5 | `event_to_script_eng` | event -> StringId -> ENG translation | `str "play_npc_greeting_01" -> str "Greeting 01"` | D11 + D13["eng"] | ~60,000 |
| C6 | `entity_strkey_to_stringids` | Entity StrKey -> source_file -> export file StringIds | `str "CharInfo_Varon" -> Set[str] {"CHAR_VARON_NAME", "CHAR_VARON_DESC"}` | entity.source_file + D17 | ~40,000 |
| C7 | `stringid_to_entity` | StringId -> (which entity does this text belong to?) | `str "CHAR_VARON_NAME" -> Tuple[str, str] ("character", "CharInfo_Varon")` | D17 inverted + heuristic matching | ~200,000 |

---

## 2. Parse Sources

### 2A. XML File Types

| # | File Pattern | Folder | Elements to Extract | Existing Code | Est. Files | Est. Parse Time |
|---|-------------|--------|---------------------|--------------|-----------|----------------|
| P1 | `*.xml` in `knowledgeinfo/` | `knowledge_folder` | `<KnowledgeInfo>`: StrKey, Name, Desc, UITextureName, KnowledgeGroupKey. `<KnowledgeGroupInfo>`: StrKey, GroupName | `LinkageResolver.build_knowledge_lookup()` (linkage.py:265), `load_knowledge_data()` (base.py:916), `build_knowledge_table()` (mapdata_service.py:86) | ~50 | ~2s |
| P2 | `characterinfo_*.staticinfo.xml` in `characterinfo/` | `character_folder` | `<CharacterInfo>`: StrKey, CharacterName, CharacterDesc, KnowledgeKey, RewardKnowledgeKey, UseMacro, Age, Job, UIIconPath. Nested `<Knowledge>`: UITextureName, Name, Desc | `LinkageResolver.load_character_data()` (linkage.py:544), `scan_characters_with_knowledge()` (character.py:128) | ~20 | ~1s |
| P3 | `*.staticinfo.xml` in `iteminfo/` | `RESOURCE_FOLDER/iteminfo` | `<ItemGroupInfo>`: StrKey, GroupName, parent hierarchy. `<ItemInfo>`: StrKey, ItemName, ItemDesc, KnowledgeKey. `<InspectData>`: Desc, RewardKnowledgeKey. `<PageData>`: book pattern | `scan_items_with_knowledge()` (item.py:304), `LinkageResolver.load_item_data()` (linkage.py:638) | ~30 | ~2s |
| P4 | `*.xml` in `factioninfo/` | `faction_folder` | `<FactionGroup>`: StrKey, GroupName, KnowledgeKey. `<Faction>`: StrKey, Name, KnowledgeKey. `<FactionNode>`: StrKey, Name, KnowledgeKey, WorldPosition, Type. `<RegionInfo>`: KnowledgeKey, DisplayName | `LinkageResolver.load_map_data()` (linkage.py:364), `parse_all_faction_groups()` (region.py:395), `build_region_display_lookup()` (region.py:813) | ~15 | ~1s |
| P5 | `skillinfo_*.staticinfo.xml` in `StaticInfo/` | `RESOURCE_FOLDER` | `<SkillInfo>`: StrKey, SkillName, LearnKnowledgeKey | `CodexService._extract_entity()` (codex_service.py:138) | ~10 | ~1s |
| P6 | `gimmickinfo_*.staticinfo.xml` in `StaticInfo/` | `RESOURCE_FOLDER` | `<GimmickGroupInfo>`: StrKey, GimmickName. `<GimmickInfo>`: StrKey. `<SealData>`: Desc | `CodexService._extract_entity()` (codex_service.py:138) | ~5 | ~0.5s |
| P7 | `languagedata_{code}.xml` in `loc/` | `loc_folder` | `<LocStr>`: StringId/StringID, StrOrigin, Str | `AudioIndex.load_script_lines()` (linkage.py:1139), `load_language_tables()` (base.py:585) | 14 files (one per lang) | ~5s total |
| P8 | `*.xml` in `export__/` | `export_folder` | Elements with SoundEventName/EventName + StringId attrs. `<LocStr>`: StringId, StrOrigin (for ordered export index) | `AudioIndex.load_event_mappings()` (linkage.py:955), `build_export_indexes()` (base.py:199) | ~100+ | ~3s |
| P9 | `*.wem` in `sound/windows/{lang}/` | `audio_folder` | Filename stems (= event names) | `AudioIndex.scan_folder()` (linkage.py:919) | ~80,000 | ~2s (filesystem scan) |
| P10 | `*.dds` in `texture/image/` | `texture_folder` | Filename stems (= texture names) | `DDSIndex.scan_folder()` (linkage.py:111) | ~50,000 | ~2s (filesystem scan) |
| P11 | `*.xlsx` in `VoiceRecordingSheet__/` | `vrs_folder` | EventName column (for chronological ordering) | `AudioIndex.load_vrs_order()` (linkage.py:1037) | 1 file | ~1s |
| P12 | `StaticInfo/**/*.xml` (broad scan) | `RESOURCE_FOLDER` | Any element with StrKey + DevMemo/DevComment | `_build_strkey_lookup()` (base.py:87) | ~200+ | ~5s |

### 2B. Total Estimated Build Time

| Phase | Time |
|-------|------|
| Filesystem scans (DDS + WEM) | ~4s |
| Knowledge XML parse | ~2s |
| Entity XML parse (character, item, region, skill, gimmick) | ~5s |
| Language table parse (14 files) | ~5s |
| Export XML parse | ~3s |
| Broad StrKey scan (DevMemo) | ~5s |
| Reverse/composed dict construction | ~1s |
| **Total** | **~25s** |

---

## 3. Build Order

Dependencies dictate strict ordering. Some phases can parallelize.

```
PHASE 1: Foundation (parallel)
  ├── D9:  Scan DDS textures (filesystem, no deps)
  ├── D10: Scan WEM audio files (filesystem, no deps)
  └── D1:  Parse KnowledgeInfo XMLs -> knowledge_by_strkey
           D15: Parse KnowledgeGroupInfo -> knowledge_group_hierarchy
           (both from same files, single pass)

PHASE 2: Entity Parse (parallel, all depend on D1 for knowledge resolution)
  ├── D2:  Parse CharacterInfo -> character_by_strkey
  │         (uses D1 for KnowledgeKey -> Name/Desc/UITexture)
  ├── D3:  Parse ItemInfo -> item_by_strkey
  │   D14: Parse ItemGroupInfo -> item_group_hierarchy
  │         (uses D1 for KnowledgeKey resolution)
  ├── D4:  Parse FactionNode -> region_by_strkey
  │   D5:  Parse Faction -> faction_by_strkey
  │   D6:  Parse FactionGroup -> faction_group_by_strkey
  │   D16: Parse RegionInfo -> region_display_names
  │         (uses D1 for KnowledgeKey -> Name/Desc)
  ├── D7:  Parse SkillInfo -> skill_by_strkey
  └── D8:  Parse GimmickGroupInfo -> gimmick_by_strkey

PHASE 3: Localization (parallel with Phase 2 if no entity deps)
  ├── D12: Parse KOR loc -> stringid_to_strorigin
  ├── D13: Parse ALL loc files -> stringid_to_translations
  ├── D11: Parse export__ XMLs -> event_to_stringid
  │   D20: event_to_export_path (built alongside D11)
  │   D21: event_to_xml_order (built alongside D11)
  ├── D17: Parse export__ .loc.xml -> export_file_stringids
  └── D18: Parse export__ .loc.xml -> ordered_export_index
           (D17 and D18 can share a single parse pass)

PHASE 4: VRS Ordering (depends on D11 + D21)
  └── Apply VRS xlsx data to D21 (override xml_order values)

PHASE 5: Broad Scan (can run parallel with Phase 2-3)
  └── D19: Broad StaticInfo scan -> strkey_to_devmemo

PHASE 6: Reverse Dicts (depends on Phase 1-3 completion)
  ├── R1: name_kr_to_strkeys (invert D1, D2, D3, D4 name fields)
  ├── R2: knowledge_key_to_entities (scan D2, D3, D4, D7 knowledge_key fields)
  ├── R3: stringid_to_event (invert D11)
  ├── R4: ui_texture_to_strkeys (invert D1.ui_texture_name)
  ├── R5: source_file_to_strkeys (scan all entity dicts)
  ├── R6: strorigin_to_stringids (invert D12 with normalization)
  └── R7: group_key_to_items (from D3 group scanning)

PHASE 7: Composed Dicts (depends on Phase 1-6)
  ├── C1: strkey_to_image_path (D1 + D9)
  ├── C2: strkey_to_audio_path (entity knowledge_key -> ... -> WEM)
  ├── C3: stringid_to_audio_path (R3 + D10)
  ├── C4: event_to_script_kr (D11 + D12)
  ├── C5: event_to_script_eng (D11 + D13)
  ├── C6: entity_strkey_to_stringids (entity.source_file + D17)
  └── C7: stringid_to_entity (complex -- see below)
```

**Critical dependency:** D1 (knowledge) MUST complete before Phase 2, because CharacterInfo, ItemInfo, and FactionNode all resolve KnowledgeKey through the knowledge table.

---

## 4. Data Volume Estimates

### Per-Entity Type (typical game project)

| Entity Type | Estimated Count | Fields per Entry | Memory per Entry | Total Memory |
|------------|----------------|------------------|-----------------|-------------|
| KnowledgeInfo (D1) | 15,000 | 6 strings | ~300 bytes | ~4.5 MB |
| CharacterInfo (D2) | 8,000 | 8 strings | ~400 bytes | ~3.2 MB |
| ItemInfo (D3) | 20,000 | 8 strings + inspect list | ~500 bytes | ~10 MB |
| FactionNode (D4) | 5,000 | 8 strings + position tuple | ~400 bytes | ~2 MB |
| Faction (D5) | 200 | 5 strings + list | ~200 bytes | ~0.04 MB |
| FactionGroup (D6) | 30 | 4 strings + list | ~200 bytes | ~0.006 MB |
| SkillInfo (D7) | 3,000 | 4 strings | ~200 bytes | ~0.6 MB |
| GimmickInfo (D8) | 2,000 | 4 strings | ~200 bytes | ~0.4 MB |

### Per-Lookup Dict

| Dict | Key Count | Memory Estimate |
|------|-----------|----------------|
| D9: DDS index | 50,000 | ~8 MB (Path objects) |
| D10: WEM index | 80,000 per lang | ~12 MB per lang |
| D11: event_to_stringid | 60,000 | ~5 MB |
| D12: stringid_to_strorigin | 200,000 | ~20 MB |
| D13: stringid_to_translations | 200,000 x 14 langs | ~280 MB (largest!) |
| D17: export_file_stringids | 500 files x ~400 SIDs each | ~2 MB |
| D19: strkey_to_devmemo | 50,000 | ~5 MB |
| R3: stringid_to_event | 60,000 | ~5 MB |
| R6: strorigin_to_stringids | 180,000 | ~18 MB |

### Total Memory Footprint

| Category | Estimate |
|----------|---------|
| Entity data (D1-D8) | ~21 MB |
| Filesystem indexes (D9-D10) | ~32 MB (3 audio langs) |
| Localization data (D11-D13, D17-D18) | ~310 MB |
| Reverse dicts (R1-R7) | ~50 MB |
| Composed dicts (C1-C7) | ~20 MB |
| **Total** | **~430 MB** |

### Optimization: Lazy Language Loading

D13 (all 14 language translations) is the memory hog at ~280 MB. Following MapDataGenerator's pattern (`PRELOAD_LANGUAGES = ['eng', 'kor']`), only preload ENG + KOR translations. Other languages loaded on-demand:

| Strategy | Memory |
|----------|--------|
| All 14 languages preloaded | ~430 MB |
| ENG + KOR only (lazy others) | ~190 MB |
| Core dicts only (no translations) | ~150 MB |

**Recommendation:** Preload ENG + KOR, lazy-load others. This matches MapDataGenerator's existing pattern and keeps memory under 200 MB.

---

## 5. Integration Points

### 5A. CodexService._registry -- REPLACE

**Current:** `CodexService` in `codex_service.py` builds its own `_registry: Dict[str, Dict[str, CodexEntity]]` by scanning all XML files independently. It has 6 entity types, FAISS index, and relationship graph.

**MegaIndex replacement:**
- `_registry["character"]` -> `MegaIndex.character_by_strkey` (D2)
- `_registry["item"]` -> `MegaIndex.item_by_strkey` (D3)
- `_registry["region"]` -> `MegaIndex.region_by_strkey` (D4)
- `_registry["knowledge"]` -> `MegaIndex.knowledge_by_strkey` (D1)
- `_registry["skill"]` -> `MegaIndex.skill_by_strkey` (D7)
- `_registry["gimmick"]` -> `MegaIndex.gimmick_by_strkey` (D8)

**Cross-ref resolution:** Currently `_resolve_cross_refs()` manually walks knowledge_map. MegaIndex builds C1 (image path) and R2 (knowledge->entities) at build time, eliminating runtime resolution.

**FAISS index:** Remains unchanged -- build from MegaIndex entity names+descriptions instead of CodexService._registry.

**Relationship graph:** Currently `_find_related_entities()` + `get_relationships()`. MegaIndex provides R2 (knowledge links), R5 (same-file grouping), and entity cross-ref attributes directly.

### 5B. MapDataService -- REPLACE

**Current:** `MapDataService` in `mapdata_service.py` builds `_knowledge_table`, `_dds_index`, `_strkey_to_image`, `_strkey_to_audio` independently.

**MegaIndex replacement:**
- `_knowledge_table` -> `MegaIndex.knowledge_by_strkey` (D1)
- `_dds_index` -> `MegaIndex.dds_by_stem` (D9)
- `_strkey_to_image` -> `MegaIndex.strkey_to_image_path` (C1)
- `_strkey_to_audio` -> `MegaIndex.strkey_to_audio_path` (C2) + `MegaIndex.stringid_to_audio_path` (C3)
- `get_image_context(string_id)` -> Try D1 lookup, then R4, then fuzzy. With MegaIndex, C7 (stringid_to_entity) provides the bridge.

### 5C. API Endpoints and Dict Consumption

| API Endpoint | Current Service | MegaIndex Dicts Used |
|-------------|----------------|---------------------|
| `GET /api/ldm/codex/search` | CodexService.search() | FAISS index built from D1-D8 entities |
| `GET /api/ldm/codex/entity/{type}/{strkey}` | CodexService.get_entity() | D1-D8 direct lookup by type + strkey |
| `GET /api/ldm/codex/types` | CodexService.get_entity_types() | len() of D1-D8 |
| `GET /api/ldm/codex/relationships` | CodexService.get_relationships() | R2, R5, entity attributes |
| `GET /api/ldm/mapdata/image/{strkey}` | MapDataService.get_image_context() | C1 (strkey_to_image_path) |
| `GET /api/ldm/mapdata/audio/{strkey}` | MapDataService.get_audio_context() | C2, C3, C4, C5 |
| `GET /api/ldm/mapdata/thumbnail/{name}` | MapDataService (DDS conversion) | D9 (dds_by_stem) |
| Translation grid context | ContextService.resolve_chain() | C1, C3, C7, D12, D13 |

### 5D. Svelte Component Consumption

| Component | API Endpoint(s) | What It Needs |
|-----------|----------------|---------------|
| CodexBrowser | `/codex/search`, `/codex/entity` | Entity name, desc, image URL, type |
| CodexGraph | `/codex/relationships` | Nodes + links with entity types |
| TranslationGrid | `/rows`, `/mapdata/image`, `/mapdata/audio` | Row string_id -> image + audio context |
| MapView | `/codex/entity/region/*` | WorldPosition, name, image |
| AudioPlayer | `/mapdata/audio/*` | WEM path, script lines (KR + ENG) |

---

## 6. The StringId <-> StrKey Bridge

This is the **most critical and most complex** part of the design. StringId and StrKey are fundamentally different identifiers used in different XML schemas.

### 6A. What Each Identifier Is

| Identifier | Schema | Attribute Name | Example | Lives In |
|-----------|--------|----------------|---------|----------|
| **StrKey** | StaticInfo (game data) | `StrKey` | `Knowledge_Region_Calpheon` | `knowledgeinfo/*.xml`, `characterinfo/*.xml`, `iteminfo/*.xml`, `factioninfo/*.xml` |
| **StringId** | Localization (translation data) | `StringId` or `StringID` | `REGION_CALPHEON_NAME` | `loc/languagedata_*.xml`, `export__/*.xml`, `export__/*.loc.xml` |

### 6B. How They Connect

**There is NO single element that has both StrKey AND StringId.** They live in completely separate XML schemas. The bridge goes through **Korean text matching**:

```
StaticInfo XML:                           Localization XML:
  <KnowledgeInfo                            <LocStr
    StrKey="Knowledge_Region_Calpheon"        StringId="REGION_CALPHEON_NAME"
    Name="칼페온 수도"                          StrOrigin="칼페온 수도"
    .../>                                     Str="Calpheon City"
                                              .../>

Bridge: KnowledgeInfo.Name == LocStr.StrOrigin (after normalization)
```

### 6C. The Three Bridge Mechanisms

**Bridge 1: Korean Text Matching (primary, already implemented)**

Used by QACompiler's `resolve_translation()`:
1. Take entity's Korean text (e.g., `KnowledgeInfo.Name = "칼페온 수도"`)
2. Normalize with `normalize_placeholders()` (strip `#` suffixes, `<br/>` -> space, collapse whitespace)
3. Look up in language table: `lang_table[normalized_kor]` -> `[(translation, stringid, str_origin), ...]`
4. Disambiguate using export file + source_file: `export_file_stringids[source_file_stem]` filters candidates

**Bridge 2: Export File Scoping (disambiguation)**

When the same Korean text appears with multiple StringIds (common for short names like "검" = "Sword"):
1. The entity's `source_file` (e.g., `"iteminfo_weapon.staticinfo.xml"`) identifies which export file to check
2. `export_file_stringids["iteminfo_weapon.staticinfo"]` = Set of StringIds valid for that file
3. Pick the candidate whose StringId is in that set

**Bridge 3: Order-Based Consumption (precise disambiguation)**

When Bridge 2 still has multiple candidates (same Korean text, same file, different entities):
1. `StringIdConsumer` tracks the Nth occurrence of each Korean text per export file
2. The Nth call for the same text returns the Nth StringId from `ordered_export_index`
3. Requires processing entities in XML document order

### 6D. MegaIndex Bridge Dicts

For the MegaIndex, the bridge is built as follows:

```python
# C6: entity_strkey_to_stringids
# For each entity, find which StringIds belong to it via source_file + Korean text matching
for entity_type in ["character", "item", "knowledge", "region", "skill", "gimmick"]:
    for strkey, entity in mega_index.get_entities(entity_type).items():
        source_stem = get_export_key(entity.source_file)
        korean_texts = entity.get_korean_texts()  # name, desc, etc.

        matched_sids = set()
        for kor_text in korean_texts:
            normalized = normalize_placeholders(kor_text)
            candidates = strorigin_to_stringids.get(normalized, [])
            valid_sids = export_file_stringids.get(source_stem, set())
            for sid in candidates:
                if sid in valid_sids:
                    matched_sids.add(sid)

        entity_strkey_to_stringids[strkey] = matched_sids

# C7: stringid_to_entity (reverse of C6)
for strkey, sids in entity_strkey_to_stringids.items():
    for sid in sids:
        stringid_to_entity[sid] = (entity_type, strkey)
```

### 6E. Special Cases

**ItemData.StringID vs KnowledgeInfo.StrKey:**
- In MapDataGenerator ITEM mode, items come from `knowledgeinfo/` (KnowledgeInfo elements). The StrKey IS the knowledge key.
- In QACompiler, items come from `iteminfo/` (ItemInfo elements). ItemInfo has its own StrKey, plus a `KnowledgeKey` that links to KnowledgeInfo.
- For QACompiler items: `ItemInfo.StrKey` (entity key) != `ItemInfo.KnowledgeKey` (knowledge link) != `StringId` (loc identifier)
- The bridge: `ItemInfo.ItemName` (Korean) -> normalize -> match in lang_table -> `StringId`

**Audio chain (different bridge):**
- Audio does NOT go through Korean text matching.
- Audio bridge: `EventName` (from WEM filename) -> `StringId` (from export XML `SoundEventName + StringId` pair)
- This is D11 (`event_to_stringid`) -- a direct mapping, not text-based.

**LocStr format vs LanguageData format:**
- Upload files (`locstr_upload_*.xml`): use `StrKey` attribute on `<LocStr>` -- this is DIFFERENT from StaticInfo StrKey! It's actually a StringId-equivalent with a different attribute name.
- Language data files (`languagedata_*.xml`): use `StringId` or `StringID` attribute on `<LocStr>`
- The XML parsing engine in `server/tools/ldm/services/xml_parsing.py` handles both via `STRINGID_ATTRS = ['StringId', 'StringID', 'stringid', 'STRINGID', 'Stringid', 'stringId']`

### 6F. The Complete Entity Resolution Chain

For any LDM translation grid row with `string_id = "CHAR_VARON_NAME"`:

```
1. C7: stringid_to_entity["CHAR_VARON_NAME"]
   -> ("character", "CharInfo_Varon")

2. D2: character_by_strkey["CharInfo_Varon"]
   -> CharacterEntry(name="바론", knowledge_key="Knowledge_Character_Varon", ...)

3. C1: strkey_to_image_path["Knowledge_Character_Varon"]
   -> Path("...cd_knowledgeimage_character_varon.dds")

4. C3: stringid_to_audio_path["CHAR_VARON_NAME"]
   -> Path("...play_varon_greeting_01.wem")  (if voice line exists)

Result: Row "CHAR_VARON_NAME" gets image + audio + entity metadata in 4 dict lookups.
```

---

## 7. MegaIndex Public API Design

```python
class MegaIndex:
    """Unified game data index with O(1) lookups in every direction."""

    # === Initialization ===
    def build(self, paths: Dict[str, Path], preload_langs: List[str] = ["eng", "kor"]) -> None:
        """Build all indexes from game data folders. ~25s for typical project."""

    # === Direct Entity Lookups (by StrKey) ===
    def get_knowledge(self, strkey: str) -> Optional[KnowledgeEntry]: ...
    def get_character(self, strkey: str) -> Optional[CharacterEntry]: ...
    def get_item(self, strkey: str) -> Optional[ItemEntry]: ...
    def get_region(self, strkey: str) -> Optional[RegionEntry]: ...
    def get_skill(self, strkey: str) -> Optional[SkillEntry]: ...
    def get_gimmick(self, strkey: str) -> Optional[GimmickEntry]: ...
    def get_entity(self, entity_type: str, strkey: str) -> Optional[Any]: ...

    # === Media Lookups ===
    def get_image_path(self, strkey: str) -> Optional[Path]: ...           # C1
    def get_audio_path_by_event(self, event_name: str) -> Optional[Path]:  # D10
    def get_audio_path_by_stringid(self, string_id: str) -> Optional[Path]:# C3
    def get_dds_path(self, texture_name: str) -> Optional[Path]: ...       # D9

    # === Localization Lookups ===
    def get_strorigin(self, string_id: str) -> Optional[str]: ...          # D12
    def get_translation(self, string_id: str, lang: str) -> Optional[str]: # D13
    def get_script_kr(self, event_name: str) -> Optional[str]: ...         # C4
    def get_script_eng(self, event_name: str) -> Optional[str]: ...        # C5

    # === Bridge Lookups (StringId <-> StrKey) ===
    def stringid_to_entity(self, string_id: str) -> Optional[Tuple[str, str]]:  # C7
    def entity_stringids(self, entity_type: str, strkey: str) -> Set[str]: ...   # C6
    def event_to_stringid(self, event_name: str) -> Optional[str]: ...           # D11
    def stringid_to_event(self, string_id: str) -> Optional[str]: ...            # R3

    # === Reverse Lookups ===
    def find_by_korean_name(self, name_kr: str) -> List[Tuple[str, str]]: ...    # R1
    def find_by_knowledge_key(self, key: str) -> List[Tuple[str, str]]: ...      # R2
    def find_by_source_file(self, filename: str) -> List[Tuple[str, str]]: ...   # R5
    def find_stringids_by_korean(self, text: str) -> List[str]: ...              # R6

    # === Hierarchy ===
    def get_item_group_tree(self) -> Dict[str, ItemGroupNode]: ...               # D14
    def get_knowledge_group_tree(self) -> Dict[str, KnowledgeGroupNode]: ...     # D15
    def get_faction_tree(self) -> List[FactionGroupEntry]: ...                   # D6 -> D5 -> D4

    # === Translation Resolution (QACompiler-compatible) ===
    def resolve_translation(
        self, korean_text: str, lang: str, source_file: str = ""
    ) -> Tuple[str, str, str]:
        """(translation, stringid, str_origin) with export-based disambiguation."""

    # === Bulk ===
    def all_entities(self, entity_type: str) -> Dict[str, Any]: ...
    def entity_counts(self) -> Dict[str, int]: ...
    def stats(self) -> Dict[str, Any]: ...
```

---

## 8. Data Entry Schemas

```python
@dataclass(frozen=True, slots=True)
class KnowledgeEntry:
    strkey: str
    name: str                    # Korean display name
    desc: str                    # Korean description
    ui_texture_name: str         # UITextureName (for DDS lookup)
    group_key: str               # KnowledgeGroupKey
    source_file: str             # XML filename

@dataclass(frozen=True, slots=True)
class CharacterEntry:
    strkey: str
    name: str                    # CharacterName (Korean)
    desc: str                    # CharacterDesc
    knowledge_key: str           # KnowledgeKey or RewardKnowledgeKey
    use_macro: str               # Race/Gender (e.g., "Macro_NPC_Human_Male")
    age: str                     # Age (e.g., "Adult")
    job: str                     # Job (e.g., "Job_Scholar")
    ui_icon_path: str            # UIIconPath fallback
    source_file: str

@dataclass(frozen=True, slots=True)
class ItemEntry:
    strkey: str
    name: str                    # ItemName (Korean)
    desc: str                    # ItemDesc
    knowledge_key: str           # KnowledgeKey
    group_key: str               # Parent ItemGroupInfo StrKey
    source_file: str
    inspect_entries: Tuple[Tuple[str, str, str, str], ...]  # (desc, k_name, k_desc, k_src)

@dataclass(frozen=True, slots=True)
class RegionEntry:
    strkey: str
    name: str                    # Display name (from KnowledgeInfo or Name attr)
    desc: str                    # Description
    knowledge_key: str
    world_position: Optional[Tuple[float, float, float]]  # (x, y, z)
    node_type: str               # Main, Sub, etc.
    parent_strkey: str           # Parent FactionNode StrKey
    source_file: str
    display_name: str            # RegionInfo.DisplayName (if different from name)

@dataclass(frozen=True, slots=True)
class FactionEntry:
    strkey: str
    name: str
    knowledge_key: str
    group_strkey: str            # Parent FactionGroup
    source_file: str
    node_strkeys: Tuple[str, ...]

@dataclass(frozen=True, slots=True)
class FactionGroupEntry:
    strkey: str
    group_name: str
    knowledge_key: str
    source_file: str
    faction_strkeys: Tuple[str, ...]

@dataclass(frozen=True, slots=True)
class SkillEntry:
    strkey: str
    name: str
    desc: str
    learn_knowledge_key: str
    source_file: str

@dataclass(frozen=True, slots=True)
class GimmickEntry:
    strkey: str
    name: str
    desc: str
    seal_desc: str
    source_file: str

@dataclass(frozen=True, slots=True)
class ItemGroupNode:
    strkey: str
    group_name: str              # Korean group name
    parent_strkey: str           # "" if root
    child_strkeys: Tuple[str, ...]  # Child groups
    item_strkeys: Tuple[str, ...]   # Direct items in this group

@dataclass(frozen=True, slots=True)
class KnowledgeGroupNode:
    strkey: str
    group_name: str
    child_strkeys: Tuple[str, ...]  # Knowledge entries in this group
```

**Design choice:** `frozen=True, slots=True` for all entry dataclasses because MegaIndex data is immutable after build. This saves memory (no `__dict__`) and prevents accidental mutation.

---

## 9. Open Questions

### Q1: Should MegaIndex live server-side only, or also in standalone tools?

MapDataGenerator and QACompiler run as standalone PyInstaller EXEs on Windows. The MegaIndex design is pure Python with no server dependencies. It could be extracted as a shared library used by:
- LocaNext server (primary consumer)
- MapDataGenerator (replace LinkageResolver)
- QACompiler (replace load_knowledge_data + load_language_tables)

**Recommendation:** Start server-side. Extract to shared library later if standalone tools need it.

### Q2: Incremental rebuild or full rebuild?

When a single XML file changes in Perforce, does MegaIndex need to rebuild everything?

**Current reality:** All three existing tools do full rebuilds. Parse times are under 30s total. For the MVP, full rebuild is fine.

**Future optimization:** Track file modification timestamps. Only re-parse changed files and rebuild affected dicts. This would need dependency tracking (which dicts depend on which files).

### Q3: How to handle the D13 memory problem at scale?

280 MB for 14 languages is acceptable on a dev workstation server but might be an issue for future scaling.

**Options:**
1. Lazy language loading (recommended -- already proven in MapDataGenerator)
2. SQLite-backed storage for rarely-accessed languages
3. Memory-mapped files for large dicts

---

## 10. Migration Path

### Phase 1: Build MegaIndex alongside existing services
- Create `server/tools/ldm/services/mega_index.py`
- Initialize at server startup alongside CodexService and MapDataService
- Add `/api/ldm/mega/status` endpoint to verify data

### Phase 2: Wire CodexService to MegaIndex
- Replace `CodexService._scan_entities()` with MegaIndex entity iteration
- Replace `_resolve_cross_refs()` with MegaIndex composed dicts
- Keep FAISS index building (just read from MegaIndex instead of _registry)

### Phase 3: Wire MapDataService to MegaIndex
- Replace `_knowledge_table` with MegaIndex.knowledge_by_strkey
- Replace `_dds_index` with MegaIndex.dds_by_stem
- Replace `_resolve_image_chains()` with MegaIndex.strkey_to_image_path
- Implement real audio context using MegaIndex.stringid_to_audio_path

### Phase 4: Remove redundant parsing
- Delete `build_knowledge_table()` from mapdata_service.py
- Delete `_scan_entities()` / `_parse_xml_file()` from codex_service.py
- Single initialization path: `MegaIndex.build()` -> all services read from it

---

*Design document only. No implementation code.*
