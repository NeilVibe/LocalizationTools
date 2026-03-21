# Feature Landscape

**Domain:** Game Localization CAT Tool -- Codex UIs (Audio/Item/Character/Region) + Offline Bundle
**Researched:** 2026-03-21
**Confidence:** HIGH (all features derived from existing, analyzed source code)

## Table Stakes

Features users expect. Missing = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Entity card grid with search | Codex already has this for 5 types; Audio/Item/Character/Region are just new entity types | Low | Reuse existing `CodexPage.svelte` + `CodexCard.svelte` pattern |
| DDS image preview per entity | MapDataGenerator already has DDS->PNG; LocaNext already has DDS preview API | Low | Already built: `/api/ldm/media/dds` endpoint exists |
| Entity detail panel with attributes | Existing `CodexEntityDetail.svelte` shows attributes; extend for mode-specific fields | Low | Add Character fields (Race/Gender/Age/Job), Item fields (Knowledge passes), Region fields (WorldPosition) |
| Text search (contains/exact) | MapDataGenerator SearchEngine pattern: Korean name, translated name, StrKey, description | Low | Port SearchEngine multi-field search; existing Codex FAISS already covers semantic |
| Category/group filtering | Item has ItemGroupInfo hierarchy, Character has filename-based groups (NPC/MONSTER), Region has FactionGroup tabs | Med | Item clustering is complex (depth-based + monster extraction + small folder consolidation) -- port the grouping but simplify for UI |
| Korean + translated name display | MapDataGenerator shows both; QACompiler resolves translations via language tables | Low | Reuse existing language table loading from codex_service |
| Offline-capable (works without server AI) | v5.0 goal: light bundle without Qwen; core browsing must work with SQLite only | Med | FAISS semantic search needs Model2Vec (kept in light bundle); Qwen summaries gracefully degrade |
| Perforce path configuration | MapDataGenerator has drive_letter + branch config (settings.json); 14 languages, 4 modes | Med | Port the `generate_default_paths()` pattern to LocaNext settings; expose drive/branch in UI |

## Differentiators

Features that set product apart. Not expected but valued.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Audio Codex with inline WEM playback | No CAT tool offers WEM-to-WAV streaming with script line display; MapDataGenerator's AudioIndex provides EventName->StringId->StrOrigin chain | Med | Port AudioHandler (vgmstream-cli), AudioIndex (WEM scan + event mapping + VRS ordering + KOR/ENG script lines). Category tree from export_path hierarchy. |
| StringID->Audio mapping in translation grid | Click a StringID in the LDM grid, hear the voice line. Translators get tone/delivery context without leaving the editor | Med | Requires mapping StrOrigin->EventName->WEM path; reverse lookup of AudioIndex chain. Inline `<audio>` player on row select. |
| Interactive Region map from WorldPosition data | QACompiler Region generator has FactionNode.WorldPosition + 3-hop KnowledgeInfo->UIMapTextureInfo->LevelGimmickSceneObjectInfo position chain | Med | Existing WorldMap page uses d3-zoom with 14 mock nodes; Region Codex adds REAL nodes from parsed XML data with actual coordinates |
| Knowledge cross-reference chains | QACompiler generators resolve multi-pass knowledge: Pass 0 (inline children), Pass 1 (KnowledgeKey direct), Pass 2 (identical name match). Shows full entity context | Low | Data structures exist: ItemEntry has 7 knowledge fields, CharacterEntry has 5. Display all resolved knowledge in entity detail |
| Export category tree for audio | MapDataGenerator AudioIndex.build_category_tree() provides hierarchical navigation (Dialog/QuestDialog, etc.) | Low | Already implemented in MapDataGenerator GUI; port tree structure to Svelte 5 TreeView component |
| Shop + SceneObjectData position for regions | Region generator resolves shop AliasName -> SceneObjectData.Position for teleport commands | Low | Already in region.py; adds shop locations to map overlay |
| Graceful AI degradation with capability badges | Show which AI features are available (Model2Vec: YES, Qwen: NO, FAISS: YES, TTS: NO) and adjust UI accordingly | Med | Feature detection at startup; hide AI-dependent UI sections; show status badges on settings page |
| VRS chronological ordering | Audio entries sorted by VoiceRecordingSheet row position, giving quest-chronological playback order | Low | AudioIndex.load_vrs_order() already implemented; just need to honor xml_order in UI sort |

## Anti-Features

Features to explicitly NOT build.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Full audio editing/waveform UI | Scope creep; LocaNext is a CAT tool, not an audio editor. MapDataGenerator only does playback | Simple play/stop/duration display with script text overlay |
| CRUD operations on Codex entities | v5.0 is read-only encyclopedia; editing XML entities is Game Dev Grid territory (already built in v3.0) | Browse, search, view details. Link to Game Dev Grid for editing |
| Real-time audio recording | Not in scope; TTS auto-gen for missing audio is already partially done in v3.5 | Use existing TTS endpoint as fallback for missing audio |
| Perforce integration (sync/checkout) | Too coupled to specific VCS; LocaNext works with local files | Just parse Perforce path patterns for file resolution |
| Full Qwen AI in offline bundle | Qwen 0.6B is 2.3GB; defeats "light bundle" purpose | Model2Vec only (12x smaller); semantic search works, AI summaries gracefully missing |
| MapDataGenerator's tkinter GUI porting | MapDataGenerator is a standalone tkinter app; porting its GUI is meaningless | Port the DATA LOGIC (linkage, search, audio), build NEW Svelte 5 UI |
| Multi-language audio folder switching in UI | MapDataGenerator supports 3 audio languages (EN/KR/ZH) with folder switching; adds complexity | Default to project language (1 project = 1 language); audio folder auto-detected from Perforce path |

## Feature Dependencies

```
Perforce Path Config -> Audio Codex (needs audio_folder path)
Perforce Path Config -> Item/Character/Region Codex (needs resource paths)
Perforce Path Config -> StringID->Audio mapping (needs export_folder + loc_folder)

Existing CodexService -> Item Codex (extends entity registry)
Existing CodexService -> Character Codex (extends entity registry)
Existing CodexService -> Region Codex (extends entity registry)

AudioIndex (from MapDataGenerator) -> Audio Codex
AudioIndex -> StringID->Audio mapping
DDS preview API (existing) -> Item/Character/Region image cards

Model2Vec + FAISS (existing) -> Semantic search across new Codex types
Graceful AI degradation -> All Codex UIs (must work without AI)

Region WorldPosition data -> Region Codex interactive map
Existing WorldMap page -> Region Codex map integration (or extension)
```

## MVP Recommendation

Prioritize for maximum demo impact with minimum risk:

1. **Graceful AI degradation** -- Must be Phase 1 (baked into architecture, not bolted on after). Feature detection for Model2Vec/Qwen/FAISS/TTS. All subsequent Codex UIs depend on this.

2. **Perforce path configuration** -- Foundation for all data loading. Port MapDataGenerator's `generate_default_paths()` with drive/branch settings. Without this, nothing loads real data.

3. **Item Codex UI** -- Highest visual impact (items have images). Port ItemGroupInfo hierarchy for category navigation, ItemEntry data structure for detail view. Reuse existing CodexPage pattern.

4. **Character Codex UI** -- Second highest visual impact. Simpler than Items (filename-based grouping, no depth clustering). Add Race/Gender/Age/Job fields to detail panel.

5. **Audio Codex UI** -- Unique differentiator no competitor has. Port AudioIndex chain (WEM scan -> event mapping -> script lines), AudioHandler for playback, category tree for navigation.

6. **Region Codex UI + map** -- Extend existing WorldMap with real WorldPosition data from FactionNode XML. Add FactionGroup hierarchy for navigation.

7. **StringID->Audio inline player** -- Wire the reverse lookup from LDM grid to AudioIndex. High wow-factor for translators.

Defer:
- **VRS ordering**: Nice-to-have; chronological order improves audio browsing but not critical for MVP
- **Shop positions on map**: Enhances Region Codex but adds complexity to the map overlay
- **3-hop Knowledge_Contents position chain**: Complex (KnowledgeInfo -> UIMapTextureInfo -> LevelGimmickSceneObjectInfo); defer to polish pass

## Data Available from Source Code Analysis

### Item Generator (item.py)
- **Data structure:** `ItemEntry` with 12 fields including 3 knowledge passes + InspectData
- **Hierarchy:** ItemGroupInfo with depth-based clustering, monster item extraction, small folder consolidation
- **Key paths:** `RESOURCE_FOLDER/iteminfo/`, `RESOURCE_FOLDER/knowledgeinfo/`
- **Output format:** Row-per-text with DataType column (ItemData, KnowledgeData, KnowledgeData2, ChildKnowledgeData, InspectData, InspectKnowledgeData)
- **Complexity:** HIGHEST of all generators (7 knowledge resolution passes, depth clustering, dedup logic)
- **For LocaNext:** Simplify to card view with knowledge tabs, not row-per-text Excel format

### Character Generator (character.py)
- **Data structure:** `CharacterEntry` with knowledge passes + inline children
- **Grouping:** By filename pattern (characterinfo_npc -> "npc", characterinfo_monster_unique -> "monster")
- **Key paths:** `RESOURCE_FOLDER/characterinfo/` (files named `characterinfo_*.staticinfo.xml`)
- **Output format:** 9 columns including COMMAND (/create character {strkey})
- **Complexity:** MEDIUM -- simpler than Item (no depth clustering, no InspectData)
- **For LocaNext:** Group tabs by category (NPC, MONSTER, etc.), character card with Knowledge panel

### Region Generator (region.py)
- **Data structure:** `FactionGroupData` -> `FactionData` -> `FactionNodeData` (recursive tree)
- **WorldPosition:** On FactionNode elements, parsed as (x, y, z) floats
- **DisplayName:** Separate lookup via `RegionInfo.KnowledgeKey -> RegionInfo.DisplayName`
- **Shop data:** Parsed from `shop_world.staticinfo.xml` with AliasName -> SceneObjectData.Position
- **Knowledge_Contents:** 3-hop position chain for teleport coordinates
- **Complexity:** HIGH (hierarchical tree, multiple lookups, shop cross-reference, 3-hop chain)
- **For LocaNext:** Tree navigation + map overlay from WorldPosition data

### MapDataGenerator Audio (linkage.py + audio_handler.py)
- **Data structure:** `AudioIndex` with 5 lookup chains (WEM files, event->StringId, StringId->StrOrigin/KOR/ENG)
- **Category tree:** Built from export folder relative paths (Dialog/QuestDialog, etc.)
- **Playback:** `AudioHandler` with vgmstream-cli WEM->WAV, winsound playback, thread-safe generation counters
- **VRS ordering:** VoiceRecordingSheet Excel files provide chronological sort
- **Languages:** 3 audio folders (English(US), Korean, Chinese(PRC))
- **Complexity:** MEDIUM -- well-structured chain lookups, no complex hierarchy
- **For LocaNext:** Port AudioIndex for data loading, use existing WEM->WAV streaming API for playback

### MapDataGenerator Linkage (linkage.py)
- **Data structure:** `LinkageResolver` with unified `DataEntry` for all 4 modes
- **DDS lookup:** `DDSIndex` scans texture folder, handles stem/extension/fuzzy matching
- **Knowledge-first pattern:** Build knowledge lookup table FIRST, then layer mode-specific data
- **Character loading:** From CharacterInfo with Knowledge children for UITextureName
- **Item loading:** From KnowledgeInfo with KnowledgeGroupInfo tracking
- **Map loading:** Knowledge entries + FactionNode position overlay
- **For LocaNext:** Adapt LinkageResolver pattern into CodexService extensions

### Perforce Path Configuration (config.py)
- **14 languages** with code/name pairs
- **3 audio languages** with separate folder paths
- **4 data modes:** map, character, item, audio
- **Path templates:** Drive letter (default F:) + branch (default mainline) substitution
- **Known branches:** mainline, cd_beta, cd_alpha, cd_lambda
- **Settings persistence:** JSON file with drive/branch/paths/UI prefs
- **For LocaNext:** Add drive_letter and branch to LocaNext settings; generate paths from templates

## Sources

- `RessourcesForCodingTheProject/NewScripts/QACompilerNEW/generators/item.py` -- Item generator (1080 lines)
- `RessourcesForCodingTheProject/NewScripts/QACompilerNEW/generators/character.py` -- Character generator (594 lines)
- `RessourcesForCodingTheProject/NewScripts/QACompilerNEW/generators/region.py` -- Region generator (1307 lines)
- `RessourcesForCodingTheProject/NewScripts/QACompilerNEW/generators/base.py` -- Shared generator base (958 lines)
- `RessourcesForCodingTheProject/NewScripts/MapDataGenerator/core/linkage.py` -- LinkageResolver + AudioIndex (1326 lines)
- `RessourcesForCodingTheProject/NewScripts/MapDataGenerator/core/audio_handler.py` -- AudioHandler (337 lines)
- `RessourcesForCodingTheProject/NewScripts/MapDataGenerator/core/search.py` -- SearchEngine (356 lines)
- `RessourcesForCodingTheProject/NewScripts/MapDataGenerator/config.py` -- Perforce config + settings (667 lines)
- `server/tools/ldm/services/codex_service.py` -- Existing Codex service
- `locaNext/src/lib/components/pages/CodexPage.svelte` -- Existing Codex UI
- `.planning/DEFERRED_IDEAS.md` -- Feature backlog
