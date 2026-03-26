# Path Resolution Current State — LocaNext v13.0 Research

**Researched:** 2026-03-26
**Scope:** Complete audit of path resolution chain from LanguageData row to media file
**Confidence:** HIGH (all findings from direct source code reading)

---

## 1. PerforcePathService — Centralized Path Templates

**File:** `server/tools/ldm/services/perforce_path_service.py` (238 lines)
**Status:** FULLY WORKING

### What It Does

Resolves 11 Perforce path templates with drive+branch substitution and WSL conversion.

### Templates (11 total)

| Key | Template Pattern | Purpose |
|-----|-----------------|---------|
| `faction_folder` | `{D}:\perforce\cd\{branch}\resource\GameData\StaticInfo\factioninfo` | Region/faction XMLs |
| `loc_folder` | `{D}:\perforce\cd\{branch}\resource\GameData\stringtable\loc` | LanguageData XMLs |
| `knowledge_folder` | `{D}:\perforce\cd\{branch}\resource\GameData\StaticInfo\knowledgeinfo` | Knowledge entity XMLs |
| `waypoint_folder` | `{D}:\perforce\cd\{branch}\resource\GameData\StaticInfo\factioninfo\NodeWaypointInfo` | Map waypoints |
| `texture_folder` | `{D}:\perforce\common\{branch}\commonresource\ui\texture\image` | DDS textures |
| `character_folder` | `{D}:\perforce\cd\{branch}\resource\GameData\StaticInfo\characterinfo` | Character XMLs |
| `audio_folder` | `{D}:\perforce\cd\{branch}\resource\sound\windows\English(US)` | English WEM files |
| `audio_folder_kr` | `{D}:\perforce\cd\{branch}\resource\sound\windows\Korean` | Korean WEM files |
| `audio_folder_zh` | `{D}:\perforce\cd\{branch}\resource\sound\windows\Chinese(PRC)` | Chinese WEM files |
| `export_folder` | `{D}:\perforce\cd\{branch}\resource\GameData\stringtable\export__` | Export XMLs with events |
| `vrs_folder` | `{D}:\perforce\cd\{branch}\resource\editordata\VoiceRecordingSheet__` | VRS data |

### Configuration Methods

1. **`configure(drive, branch)`** — Standard: substitutes drive letter and branch name in templates, converts to WSL paths
2. **`configure_for_mock_gamedata(mock_dir)`** — DEV mode: overrides all resolved paths to point at `tests/fixtures/mock_gamedata/`
3. **`resolve(key)`** — Returns WSL Path for a given template key
4. **`resolve_audio_folder(language)`** — Language-specific audio folder (eng/kor/zho-cn)

### Known Branches

`mainline`, `cd_beta`, `cd_alpha`, `cd_lambda`, `cd_delta`

### Known Drives

`C`, `D`, `E`, `F`, `G`

### WSL Conversion

`F:\perforce\...` becomes `/mnt/f/perforce/...` — already handles Unix passthrough.

---

## 2. MegaIndex — Unified Game Data Cross-Reference

**File:** `server/tools/ldm/services/mega_index.py` (1311 lines)
**Status:** FULLY WORKING (but 1311 lines = ARCH-02 split target)

### Architecture: 35 Dictionaries in 7-Phase Build Pipeline

#### Direct Dicts (D1-D21)

| Dict | Key | Value | Purpose |
|------|-----|-------|---------|
| D1 | StrKey | KnowledgeEntry | Knowledge entities (name, desc, UITextureName) |
| D2 | StrKey | CharacterEntry | Characters (name, desc, knowledge_key) |
| D3 | StrKey | ItemEntry | Items (name, desc, knowledge_key, group_key) |
| D4 | StrKey | RegionEntry | Regions (name, world_position, node_type) |
| D5 | StrKey | FactionEntry | Factions |
| D6 | StrKey | FactionGroupEntry | Faction groups |
| D7 | StrKey | SkillEntry | Skills |
| D8 | StrKey | GimmickEntry | Gimmicks |
| D9 | stem.lower() | Path | DDS texture file paths |
| D10 | stem.lower() | Path | WEM audio file paths |
| D11 | event_name.lower() | StringId | Event -> StringId mapping |
| D12 | StringId | StrOrigin | Korean source text |
| D13 | StringId | Dict[lang, text] | Translations per language |
| D14 | StrKey | ItemGroupNode | Item group hierarchy |
| D15 | StrKey | KnowledgeGroupNode | Knowledge group hierarchy |
| D16 | StrKey | display_name | Region display names |
| D17 | filename_key | Set[StringId] | Export file StringId sets |
| D18 | filename_key | Dict[norm_text, List[StringId]] | Ordered export index |
| D19 | strkey.lower() | DevMemo text | Developer notes |
| D20 | event_name.lower() | rel_dir | Event -> export path |
| D21 | event_name.lower() | int | Event XML ordering |

#### Reverse Dicts (R1-R7)

| Dict | Key | Value | Purpose |
|------|-----|-------|---------|
| R1 | name_kr | List[(entity_type, strkey)] | Korean name -> entities |
| R2 | knowledge_key | List[(entity_type, strkey)] | Knowledge key -> referencing entities |
| R3 | StringId | event_name | StringId -> event (invert D11) |
| R4 | texture_name.lower() | List[strkey] | Texture -> knowledge entries |
| R5 | source_file | List[(entity_type, strkey)] | File -> entities |
| R6 | normalized_strorigin | List[StringId] | Korean text -> StringIds |
| R7 | group_key | List[strkey] | Item group -> items |

#### Composed Dicts (C1-C7) — THE CROSS-REFERENCE CHAINS

| Dict | Chain | Purpose |
|------|-------|---------|
| **C1** | StrKey -> D1.UITextureName -> D9.dds_path | **Image path from entity StrKey** |
| **C2** | Entity StrKey -> wem_by_event[strkey.lower()] | **Audio path from entity StrKey** (weak chain) |
| **C3** | StringId -> R3.event -> D10.wem_path | **Audio path from StringId** |
| C4 | event -> D11.StringId -> D12.StrOrigin | Korean script from event |
| C5 | event -> D11.StringId -> D13.translations["eng"] | English script from event |
| **C6** | Entity StrKey -> source_file -> export StringIds + Korean text match | **Entity -> StringIds** |
| **C7** | Invert C6: StringId -> (entity_type, strkey) | **StringId -> Entity** |

---

## 3. The Full Resolution Chain: LanguageData Row -> Media File

### Chain A: StringId -> Image (WORKING)

```
LanguageData row
  |-- string_id
  |
  v
MapDataService.get_image_context(string_id)
  |
  |-- Step 1: Direct lookup in _strkey_to_image (pre-indexed from C1)
  |     C1: StrKey -> KnowledgeInfo.UITextureName -> DDS path
  |
  |-- Step 2: C7 bridge: StringId -> entity (type, strkey)
  |     Then: entity strkey -> C1 image path
  |     Fallback: partial match against knowledge entries
  |
  |-- Step 3: Fuzzy: partial string match against all indexed StrKeys
  |
  v
ImageContext { texture_name, dds_path, thumbnail_url, has_image }
  |
  v
GET /api/ldm/mapdata/thumbnail/{texture_name}
  |-- Lookup in DDS index (case-insensitive)
  |-- Fallback: mock_gamedata/textures/ (PNG/DDS/JPG)
  |-- DDS -> PNG via MediaConverter (Pillow)
  |-- Cache headers, ETag
  v
PNG bytes to browser
```

**CRITICAL ISSUE:** Step 2 (C7 bridge) depends on C6 which uses Korean text matching (StrOrigin normalization + exact match) to link entities to StringIds. This is fragile -- it only works when entity name/desc text EXACTLY matches the StrOrigin text in languagedata files after normalization.

### Chain B: StringId -> Audio (WORKING)

```
LanguageData row
  |-- string_id
  |
  v
MapDataService.get_audio_context(string_id)
  |
  |-- Step 1: Check cache (_strkey_to_audio)
  |
  |-- Step 2: C3: StringId -> event (R3) -> WEM path (D10)
  |     Gets event_name, script_kr (C4), script_eng (C5)
  |
  |-- Step 3: C2: StrKey-based audio path fallback
  |
  |-- Step 4: Lazy-load from audio/ directory (TTS WAV files)
  |
  |-- Step 5: Fuzzy partial match
  |
  v
AudioContext { event_name, wem_path, script_kr, script_eng, duration_seconds }
  |
  v
GET /api/ldm/mapdata/audio/stream/{string_id}
  |-- WAV files served directly
  |-- WEM -> WAV via vgmstream (MediaConverter)
  v
WAV bytes to browser
```

**CRITICAL ISSUE:** C2 (strkey_to_audio_path) is weak. It only checks `wem_by_event.get(strkey.lower())` -- i.e., it assumes the WEM filename matches the entity StrKey, which is rarely true. The real chain should be: entity -> export -> event_name -> WEM file.

### Chain C: Configure Branch+Drive (WORKING at API level, NO UI)

```
POST /api/ldm/mapdata/paths/configure { drive: "F", branch: "mainline" }
  |
  v
PerforcePathService.configure(drive, branch)
  |-- Validates drive (single alpha char)
  |-- Validates branch (must be in KNOWN_BRANCHES)
  |-- Regenerates all 11 path templates
  |
  v
MapDataService.initialize(branch, drive)
  |-- Triggers MegaIndex.build()
  |-- Populates knowledge table, DDS index, image chains from MegaIndex
  |
  v
PathStatusResponse { drive, branch, paths_resolved, known_branches, known_drives }
```

**MISSING:** No frontend UI exists for Branch+Drive selection. The `/api/ldm/mapdata/paths/configure` endpoint exists but is never called from the frontend.

---

## 4. Frontend Components

### ImageTab.svelte (WORKING)

- Receives `selectedRow` prop
- Fetches `GET /api/ldm/mapdata/image/{stringId}` on row change
- Uses AbortController for request cancellation on rapid row changes
- Shows thumbnail via `{API_BASE}{imageContext.thumbnail_url}?v={Date.now()}` (cache-busted)
- States: loading, no-row, has-image, error, no-image
- **NO issues found**

### AudioTab.svelte (WORKING)

- Receives `selectedRow` prop
- Fetches `GET /api/ldm/mapdata/audio/{stringId}` on row change
- Audio player via `<audio controls>` with `{#key}` for reactivity
- Shows event name, duration, Korean/English script text, WEM path
- **NO issues found**

### RightPanel.svelte (WORKING)

- Tab system: TM, Image, Audio, Context, AI Suggestions
- Passes `selectedRow` to ImageTab and AudioTab
- **NO issues found**

---

## 5. Mock GameData Structure (DEV Mode)

**Directory:** `tests/fixtures/mock_gamedata/` (119 files, 34 directories)

```
mock_gamedata/
  StaticInfo/
    knowledgeinfo/        # Knowledge XMLs (D1 parsing)
    characterinfo/        # Character XMLs (D2)
    iteminfo/             # Item XMLs (D3)
    factioninfo/          # Faction/Region XMLs (D4, D5, D6)
      NodeWaypointInfo/   # Waypoints
    skillinfo/            # Skill XMLs (D7)
    gimmickinfo/          # Gimmick XMLs (D8)
      Background/
      Item/
      Puzzle/
    regioninfo/           # Region XMLs
    questinfo/            # Quest XMLs
  texture/
    image/                # DDS files (D9) - ~20 .dds files
  textures/               # PNG fallbacks for thumbnail serving (separate from DDS)
  sound/
    windows/
      English(US)/        # WEM files (D10) - 10 .wem files
      Korean/             # Korean WEM - 10 .wem files
      Chinese(PRC)/       # Chinese WEM - 10 .wem files
  loc/                    # Language data XMLs (D12, D13)
    languagedata_KOR.xml
    languagedata_ENG.xml
    languagedata_JPN.xml
    showcase_dialogue.loc.xml
  export__/               # Export XMLs with events (D11, D17, D18)
    Character/
    Dialog/QuestDialog/
    Item/
    Skill/
    Gimmick/
  localization/           # Showcase data generation scripts
  server/data/            # QuickSearch dictionaries
```

**DEV Mode Wiring** (`server/main.py` line 158-178):
1. If `config.DEV_MODE` is True, auto-builds MegaIndex from mock_gamedata
2. `path_svc.configure_for_mock_gamedata(mock_gamedata_dir)` overrides all 11 paths
3. `mega.build()` runs full 7-phase pipeline against mock data

**Mock paths are COMPLETE** -- all 11 PerforcePathService keys are mapped to mock directories.

---

## 6. What Works vs What's Missing

### WORKING (Green)

| Component | Status | Notes |
|-----------|--------|-------|
| PerforcePathService | COMPLETE | 11 templates, drive/branch substitution, WSL conversion |
| PerforcePathService.configure_for_mock_gamedata | COMPLETE | DEV mode overrides |
| MegaIndex 35-dict build | COMPLETE | 7-phase pipeline, all parsers |
| C1: StrKey -> image path | COMPLETE | Knowledge.UITextureName -> DDS |
| C3: StringId -> audio path | COMPLETE | StringId -> event (R3) -> WEM (D10) |
| C7: StringId -> entity | COMPLETE | Via C6 Korean text matching |
| MapDataService image lookup | COMPLETE | 3-tier: direct, C7 bridge, fuzzy |
| MapDataService audio lookup | COMPLETE | 5-tier: cache, C3, C2, lazy WAV, fuzzy |
| MediaConverter DDS->PNG | COMPLETE | Pillow, LRU cache |
| MediaConverter WEM->WAV | COMPLETE | vgmstream, disk cache |
| ImageTab frontend | COMPLETE | AbortController, cache-bust, error states |
| AudioTab frontend | COMPLETE | Keyed audio player, script display |
| RightPanel tab integration | COMPLETE | Image/Audio tabs wired |
| Mock gamedata fixtures | COMPLETE | 119 files, all entity types |
| API: GET /mapdata/image/{sid} | COMPLETE | Returns ImageContextResponse |
| API: GET /mapdata/audio/{sid} | COMPLETE | Returns AudioContextResponse |
| API: GET /mapdata/audio/stream/{sid} | COMPLETE | WEM->WAV streaming |
| API: GET /mapdata/thumbnail/{name} | COMPLETE | DDS->PNG with fallback |
| API: POST /mapdata/configure | COMPLETE | Branch+drive config |
| API: POST /mapdata/paths/configure | COMPLETE | PerforcePathService config |
| API: GET /mapdata/status | COMPLETE | Service status |
| API: GET /mapdata/paths/status | COMPLETE | Path service status |
| DEV auto-init | COMPLETE | main.py auto-builds from mock_gamedata |

### MISSING (Red)

| Component | Status | Impact |
|-----------|--------|--------|
| **Branch+Drive selector UI** | NOT BUILT | User has no way to configure paths from frontend |
| **Path validation UI** | NOT BUILT | No visual feedback on whether paths resolve to real files |
| **LanguageData -> GameData entity chain visibility** | HIDDEN | Chain works but user doesn't see *which* entity was matched |
| **C2 audio chain accuracy** | WEAK | Only matches when WEM filename = entity StrKey (rare) |
| **mega_index.py splitting** | NOT DONE | 1311 lines, single file -- ARCH-02 target |

### PARTIALLY WORKING (Yellow)

| Component | Status | Notes |
|-----------|--------|-------|
| C6: Entity -> StringIds | FRAGILE | Korean text normalization + exact match; misses when entity name differs from StrOrigin |
| C7: StringId -> Entity | FRAGILE | Depends on C6 quality |
| Image lookup for LanguageData rows | DEPENDENT | Works ONLY when StringId matches a StrKey that's in knowledge_by_strkey, OR when C7 bridge finds entity, OR fuzzy match succeeds |
| Audio lookup for LanguageData rows | DEPENDENT | Works ONLY when C3 chain exists (StringId has event mapping in export XMLs) |

---

## 7. The 4 v11.0 Code Review Issues (FIX-01)

### Issue 1: onScrollToRow Delegate Race Condition

**File:** `locaNext/src/lib/components/ldm/grid/SearchEngine.svelte` (line 177-178)
**File:** `locaNext/src/lib/components/ldm/VirtualGrid.svelte` (line 160-163)

**Problem:** `SearchEngine` stores `onScrollToRow` as `$state(null)` and exposes `setScrollToRowDelegate(fn)`. The parent `VirtualGrid` sets this delegate in an `$effect`:

```javascript
$effect(() => {
  if (searchEngine) {
    searchEngine.setScrollToRowDelegate((rowId) => scrollToRowById(rowId));
  }
});
```

**Race:** If `SearchEngine` tries to call `onScrollToRow` before the `$effect` fires (e.g., during mount or rapid interaction), it calls `null?.()` which silently does nothing. The semantic search result click would fail silently.

**Fix:** Use a prop or callback pattern instead of a delegate setter, or ensure the delegate is set synchronously during initialization.

### Issue 2: visibleColumns Dead Code

**File:** `locaNext/src/lib/components/ldm/grid/CellRenderer.svelte` (line 102)

**Problem:**
```javascript
let visibleColumns = $derived(getVisibleColumns($preferences, allColumns));
```

This `$derived` is computed every time preferences change but is NEVER read anywhere in the component or exported. The `getVisibleColumns()` function (line 104+) is also dead code. Together they cause unnecessary re-computation on every preference change.

**Fix:** Remove `visibleColumns`, `getVisibleColumns()`, and any associated code.

### Issue 3: onSaveComplete Never Called

**File:** `locaNext/src/lib/components/ldm/grid/InlineEditor.svelte` (line 40)

**Problem:** `onSaveComplete` is declared as a prop:
```javascript
let { ..., onSaveComplete = undefined } = $props();
```

But `VirtualGrid.svelte` (the parent) NEVER passes this prop. Searching the entire codebase shows no caller ever provides `onSaveComplete`. The callback exists in the interface but is dead.

**Fix:** Either wire it from VirtualGrid (if save-complete notification is needed) or remove the prop entirely.

### Issue 4: tmSuggestions Inaccessible from Outside

**File:** `locaNext/src/lib/components/ldm/grid/StatusColors.svelte` (line 42)

**Problem:** `tmSuggestions` is declared as module-local `$state([])` but is never exported or exposed via any getter function. The parent `VirtualGrid` has no way to read TM suggestions for display in the TM tab or context panel. The `fetchTMSuggestions()` method IS exported, but the resulting data stays trapped inside `StatusColors`.

**Fix:** Export a getter or make `tmSuggestions` accessible, OR confirm that TM suggestions are consumed entirely within StatusColors (which appears to be the case based on current code -- the suggestions are used internally for status coloring, not for display).

**NOTE:** After v12.0 TM Intelligence shipped, the TM context search may have superseded this. Verify whether tmSuggestions is still needed for anything beyond internal status coloring.

---

## 8. GameDev Mode vs Translator Mode

### Translator Mode (fileType = "translator")

- LanguageData files (LocStr XML)
- StringId is the primary key
- Full chain: StringId -> C7 -> entity -> C1 image / C3 audio
- **Image/Audio tabs work** when the chain resolves

### GameDev Mode (fileType = "gamedev")

- Non-LocStr XML files (StaticInfo, etc.)
- StrKey is the primary key (not StringId)
- Direct knowledge lookup: StrKey -> KnowledgeEntry -> UITextureName -> DDS
- **Image/Audio tabs work** via direct MapDataService lookup by StrKey
- GameDev mode has BETTER resolution because StrKey maps directly to knowledge entries

### Summary

Both modes are wired to the same MapDataService/MegaIndex backend. Translator mode requires the C7 bridge (StringId -> entity) which is more fragile. GameDev mode uses direct StrKey lookup which is reliable.

---

## 9. Diagram: Complete Chain Architecture

```
                    FRONTEND                           BACKEND
                    ========                           =======

  LanguageData Grid                     PerforcePathService
  (VirtualGrid)                         (11 templates, drive+branch)
       |                                        |
       | selectedRow.string_id                  |
       v                                        v
  RightPanel                            MegaIndex (35 dicts)
  [Image Tab] [Audio Tab]              [7-phase build pipeline]
       |            |                    |
       | GET /mapdata/image/{sid}       | D1: knowledge_by_strkey
       | GET /mapdata/audio/{sid}       | D9: dds_by_stem
       v            v                   | D10: wem_by_event
  MapDataService                        | C1: strkey -> image path
  .get_image_context(sid)               | C3: stringid -> audio path
    1. Direct _strkey_to_image          | C7: stringid -> entity
    2. C7 bridge: sid->entity->C1       |
    3. Fuzzy partial match              v
       |                            MediaConverter
       v                            DDS->PNG (Pillow)
  ImageContextResponse              WEM->WAV (vgmstream)
  { texture_name, dds_path,            |
    thumbnail_url, has_image }          v
       |                            GET /mapdata/thumbnail/{name}
       v                            GET /mapdata/audio/stream/{sid}
  ImageTab.svelte                       |
  <img src=thumbnail_url>               v
                                    FileResponse (PNG/WAV bytes)
```

---

## 10. Recommendations for v13.0

### Phase Ordering

1. **FIX-01: Code review issues** (low risk, unblocks clean codebase)
2. **PATH-01: Branch+Drive selector UI** (needed before path validation)
3. **PATH-02: Path validation** (verify data before wiring chains)
4. **PATH-03 + PATH-04: Image + Audio chain wiring** (the main work)
5. **MOCK-01 + MOCK-02: Mock path testing** (validate chain end-to-end)
6. **ARCH-02: mega_index.py split** (cleanup, independent of features)

### Key Technical Risks

1. **C6/C7 bridge fragility** -- Korean text matching is the weakest link. Entity names don't always match StrOrigin text. Consider adding StrKey-based matching as primary, text matching as fallback.
2. **C2 audio chain** -- Nearly useless. WEM filenames are event names (e.g., `play_varon_greeting_01`), not entity StrKeys. C3 (StringId -> event -> WEM) is the real audio chain.
3. **Path validation on real Perforce** -- Mock data always works. Real Perforce paths may be missing folders, have different branch layouts, or lack DDS/WEM files. Need explicit validation.
4. **Mock paths are NOT drive-agnostic** -- `configure_for_mock_gamedata` uses absolute Path objects. MOCK-01 should make this relative.

---

*Source files audited: perforce_path_service.py, mega_index.py (1311 lines), mega_index_schemas.py, mapdata_service.py, mapdata.py (routes), media_converter.py, ImageTab.svelte, AudioTab.svelte, RightPanel.svelte, VirtualGrid.svelte, SearchEngine.svelte, CellRenderer.svelte, InlineEditor.svelte, StatusColors.svelte, main.py (DEV init), tests/fixtures/mock_gamedata/ (119 files)*
