# Perforce Path Templates Research

**Researched:** 2026-03-21
**Domain:** Perforce folder paths for all 4 Codex data modes
**Confidence:** HIGH (all data from existing source code)

---

## 1. Base Path Pattern

All paths follow the pattern:

```
{drive}:\perforce\cd\{branch}\resource\GameData\...
```

Exception: `texture_folder` uses a **different depot root**:

```
{drive}:\perforce\common\{branch}\commonresource\ui\texture\image
```

Note the `common` vs `cd` depot and `commonresource` vs `resource` subtree.

---

## 2. Complete Path Templates (All 4 Modes)

### Source of Truth: MapDataGenerator/config.py `_PATH_TEMPLATES`

These are the 11 canonical path templates (F: drive, mainline branch as placeholders):

| Key | Template | Used By |
|-----|----------|---------|
| `faction_folder` | `F:\perforce\cd\mainline\resource\GameData\StaticInfo\factioninfo` | MAP |
| `loc_folder` | `F:\perforce\cd\mainline\resource\GameData\stringtable\loc` | ALL modes |
| `knowledge_folder` | `F:\perforce\cd\mainline\resource\GameData\StaticInfo\knowledgeinfo` | MAP, ITEM, CHARACTER |
| `waypoint_folder` | `F:\perforce\cd\mainline\resource\GameData\StaticInfo\factioninfo\NodeWaypointInfo` | MAP |
| `texture_folder` | `F:\perforce\common\mainline\commonresource\ui\texture\image` | MAP, ITEM, CHARACTER |
| `character_folder` | `F:\perforce\cd\mainline\resource\GameData\StaticInfo\characterinfo` | CHARACTER |
| `audio_folder` | `F:\perforce\cd\mainline\resource\sound\windows\English(US)` | AUDIO |
| `audio_folder_kr` | `F:\perforce\cd\mainline\resource\sound\windows\Korean` | AUDIO |
| `audio_folder_zh` | `F:\perforce\cd\mainline\resource\sound\windows\Chinese(PRC)` | AUDIO |
| `export_folder` | `F:\perforce\cd\mainline\resource\GameData\stringtable\export__` | AUDIO |
| `vrs_folder` | `F:\perforce\cd\mainline\resource\editordata\VoiceRecordingSheet__` | AUDIO |

### Paths Per Mode

#### MAP Mode
| Folder | Purpose | Notes |
|--------|---------|-------|
| `knowledge_folder` | Build KnowledgeLookup table (StrKey -> Name, UITextureName, Desc) | Loaded FIRST |
| `texture_folder` | DDS texture index (UITextureName -> DDS file) | Scanned for *.dds recursively |
| `faction_folder` | FactionNode XMLs (WorldPosition, StrKey, KnowledgeKey) | Merged with Knowledge entries for position data |
| `waypoint_folder` | NodeWaypointInfo (subfolder of factioninfo) | Available but not used in main loading flow |
| `loc_folder` | Language XML tables (languagedata_{code}.xml) | For translation display |

#### CHARACTER Mode
| Folder | Purpose | Notes |
|--------|---------|-------|
| `knowledge_folder` | Build KnowledgeLookup table (Name, UITextureName) | Loaded FIRST (same as MAP) |
| `texture_folder` | DDS texture index | Scanned for *.dds recursively |
| `character_folder` | CharacterInfo XMLs (StrKey, CharacterName, UseMacro, Age, Job) | Primary data source |
| `loc_folder` | Language XML tables | For translation display |

CharacterInfo elements may have nested `<Knowledge>` child elements with UITextureName, or fall back to `UIIconPath` attribute.

#### ITEM Mode
| Folder | Purpose | Notes |
|--------|---------|-------|
| `knowledge_folder` | Both lookup table AND primary data (KnowledgeInfo + KnowledgeGroupInfo) | Re-parsed for group info |
| `texture_folder` | DDS texture index | Scanned for *.dds recursively |
| `loc_folder` | Language XML tables | For translation display |

Items do NOT use a separate `iteminfo` folder. Data comes entirely from `knowledgeinfo` XMLs. (QACompiler uses `RESOURCE_FOLDER / "iteminfo"` separately -- see differences section below.)

#### AUDIO Mode
| Folder | Purpose | Notes |
|--------|---------|-------|
| `audio_folder` | WEM audio files (one per language: English(US), Korean, Chinese(PRC)) | Scanned for *.wem |
| `export_folder` | Event XMLs with SoundEventName -> StringId/StrOrigin mappings | Parsed for event-to-string links |
| `loc_folder` | Language XMLs for script lines (KOR + ENG) | StringId -> StrOrigin/Str lookup |
| `vrs_folder` | VoiceRecordingSheet XMLs for chronological ordering | Optional, reorders entries |

Audio mode does NOT use `texture_folder` or `knowledge_folder`.

---

## 3. What MapDataService (server/) Already Has

The `server/tools/ldm/services/mapdata_service.py` has **all 11 templates** copied exactly from MapDataGenerator:

```python
PATH_TEMPLATES = {
    'faction_folder':    r"F:\perforce\cd\mainline\resource\GameData\StaticInfo\factioninfo",
    'loc_folder':        r"F:\perforce\cd\mainline\resource\GameData\stringtable\loc",
    'knowledge_folder':  r"F:\perforce\cd\mainline\resource\GameData\StaticInfo\knowledgeinfo",
    'waypoint_folder':   r"F:\perforce\cd\mainline\resource\GameData\StaticInfo\factioninfo\NodeWaypointInfo",
    'texture_folder':    r"F:\perforce\common\mainline\commonresource\ui\texture\image",
    'character_folder':  r"F:\perforce\cd\mainline\resource\GameData\StaticInfo\characterinfo",
    'audio_folder':      r"F:\perforce\cd\mainline\resource\sound\windows\English(US)",
    'audio_folder_kr':   r"F:\perforce\cd\mainline\resource\sound\windows\Korean",
    'audio_folder_zh':   r"F:\perforce\cd\mainline\resource\sound\windows\Chinese(PRC)",
    'export_folder':     r"F:\perforce\cd\mainline\resource\GameData\stringtable\export__",
    'vrs_folder':        r"F:\perforce\cd\mainline\resource\editordata\VoiceRecordingSheet__",
}
```

**Status:** All 11 paths already exist and match MapDataGenerator exactly. No templates are missing.

However, MapDataService currently only USES `knowledge_folder` and `texture_folder` in its `initialize()` method. The audio, character, faction, loc, export, vrs, and waypoint paths are defined but unused at the service level.

---

## 4. Drive Letter + Branch Substitution

### How It Works

Both MapDataGenerator and QACompiler use the same two-step substitution:

1. **Drive substitution:** Replace `F:` prefix with configured drive letter
2. **Branch substitution:** Replace literal string `mainline` with configured branch name

```python
def _apply_drive_letter(path_str, drive_letter):
    if path_str.startswith("F:") or path_str.startswith("f:"):
        return f"{drive_letter}:{path_str[2:]}"
    return path_str

def _apply_branch(path_str, branch):
    return path_str.replace("mainline", branch)
```

**Warning:** Branch substitution uses naive string replace -- if "mainline" appears elsewhere in the path it would be replaced. In practice this is safe because the folder structure doesn't contain "mainline" except as the branch name.

### Known Drives and Branches

| Source | Known Drives | Default Drive | Known Branches | Default Branch |
|--------|-------------|---------------|----------------|----------------|
| MapDataGenerator | Any single alpha char | `F` | mainline, cd_beta, cd_alpha, cd_lambda | `mainline` |
| QACompiler | C, D, E, F, G | `D` | cd_beta, mainline, cd_alpha, cd_delta, cd_lambda | `cd_beta` |
| MapDataService (server) | Any single alpha char | `F` | mainline, cd_beta, cd_alpha, cd_lambda | `mainline` |

**Key difference:** QACompiler defaults to drive `D` and branch `cd_beta`. MapDataGenerator defaults to drive `F` and branch `mainline`. QACompiler also has `cd_delta` in its known branches list (MapDataGenerator does not).

### Configuration Source

Both apps load from `settings.json` next to the executable:

```json
{
  "drive_letter": "D",
  "branch": "cd_beta"
}
```

MapDataService takes drive/branch as arguments to `initialize(branch, drive)`.

### WSL Path Conversion

MapDataService includes a `convert_to_wsl_path()` that converts Windows paths to WSL mount paths:

```
F:\perforce\cd\mainline\... -> /mnt/f/perforce/cd/mainline/...
```

---

## 5. Missing Folder Handling (Graceful vs Crash)

### MapDataGenerator Behavior

| Function | Missing Folder | Behavior |
|----------|---------------|----------|
| `DDSIndex.scan_folder()` | texture_folder doesn't exist | `log.warning()`, returns 0 files. App continues with no images. |
| `LinkageResolver.build_knowledge_lookup()` | knowledge_folder doesn't exist | `log.error()`, returns 0 entries. App continues with empty knowledge. |
| `load_map_data()` | faction_folder doesn't exist | `log.warning()`, skips FactionNode loading. Knowledge entries still available. |
| `load_character_data()` | character_folder doesn't exist | `log.error()`, returns 0. |
| `load_item_data()` | knowledge_folder doesn't exist | Skips file iteration, returns 0. |
| `load_audio_data()` | audio_folder doesn't exist | `log.error()`, returns 0. |
| `iter_xml_files()` | root doesn't exist | `if not root.exists(): return`. Silent empty iterator. |

**Summary:** MapDataGenerator is fully graceful. No crashes on missing folders. Everything degrades to empty data with warnings. The GUI shows "0 entries" and the user sees a status message.

### QACompiler Behavior

```python
def validate_paths() -> tuple:
    critical = {
        "RESOURCE_FOLDER": RESOURCE_FOLDER,
        "LANGUAGE_FOLDER": LANGUAGE_FOLDER,
        "EXPORT_FOLDER": EXPORT_FOLDER,
    }
    missing = [name for name, path in critical.items() if not path.exists()]
    return (len(missing) == 0, missing)
```

QACompiler validates paths upfront and reports missing ones. Individual generators check `RESOURCE_FOLDER.exists()` before proceeding and add errors to result dict. Also graceful -- no crashes.

---

## 6. Differences Between QACompiler and MapDataGenerator Path Conventions

### Structural Differences

| Aspect | MapDataGenerator | QACompiler |
|--------|-----------------|------------|
| Base path concept | Individual path templates per folder | Single `RESOURCE_FOLDER` base + subfolders |
| RESOURCE_FOLDER | Not used (individual paths) | `F:\perforce\cd\mainline\resource\GameData\StaticInfo` |
| Item data source | `knowledgeinfo` folder (via KnowledgeInfo XML) | `RESOURCE_FOLDER / "iteminfo"` (separate folder) |
| Character data source | `characterinfo` folder (path template) | `RESOURCE_FOLDER` (scans for `characterinfo_*.staticinfo.xml`) |
| Region/Map data | `factioninfo` + `knowledgeinfo` | `RESOURCE_FOLDER` (scans `factioninfo` subfolder) |
| Texture path | Explicit `texture_folder` template | Not used by QACompiler |
| Audio paths | 3 language-specific audio folders + export + vrs | Not used by QACompiler (no audio mode) |

### QACompiler Has Additional Paths Not in MapDataGenerator

| Path | Template |
|------|----------|
| `QUESTGROUPINFO_FILE` | `F:\perforce\cd\mainline\resource\GameData\staticinfo_quest\questgroupinfo.staticinfo.xml` |
| `SCENARIO_FOLDER` | `F:\perforce\cd\mainline\resource\GameData\staticinfo_quest\main` |
| `FACTION_QUEST_FOLDER` | `F:\perforce\cd\mainline\resource\GameData\staticinfo_quest\faction` |
| `CHALLENGE_FOLDER` | `F:\perforce\cd\mainline\resource\GameData\staticinfo_quest\Challenge` |
| `MINIGAME_FILE` | `F:\perforce\cd\mainline\resource\GameData\staticinfo_quest\contents\contents_minigame.staticinfo.xml` |
| `STRINGKEYTABLE_FILE` | `F:\perforce\cd\mainline\resource\editordata\StaticInfo__\StaticInfo_StringKeyTable.xml` |
| `SEQUENCER_FOLDER` | `F:\perforce\cd\mainline\resource\sequencer\stageseq` |
| `FACTIONINFO_FOLDER` | `F:\perforce\cd\mainline\resource\GameData\StaticInfo\factioninfo` |
| `VOICE_RECORDING_SHEET_FOLDER` | `F:\perforce\cd\mainline\resource\editordata\VoiceRecordingSheet__` |

### Key Insight: Item Mode Path Discrepancy

**MapDataGenerator ITEM mode** uses `knowledgeinfo` folder -- items are KnowledgeInfo entries with group info from KnowledgeGroupInfo.

**QACompiler Item generator** uses `RESOURCE_FOLDER / "iteminfo"` as the primary source, plus `RESOURCE_FOLDER / "knowledgeinfo"` for knowledge resolution. These are different data sources that produce different item sets.

For a Codex implementation, the MapDataGenerator approach (knowledgeinfo) is the reference pattern since it's what the existing GUI tool uses.

---

## 7. Audio Folder Language Mapping

MapDataGenerator supports 3 audio languages with separate folders:

| Language Code | Audio Folder Name | Path |
|---------------|-------------------|------|
| `eng` | `English(US)` | `{drive}:\perforce\cd\{branch}\resource\sound\windows\English(US)` |
| `kor` | `Korean` | `{drive}:\perforce\cd\{branch}\resource\sound\windows\Korean` |
| `zho-cn` | `Chinese(PRC)` | `{drive}:\perforce\cd\{branch}\resource\sound\windows\Chinese(PRC)` |

Configured via `LANG_TO_AUDIO_FOLDER` mapping:
```python
LANG_TO_AUDIO_FOLDER = {
    'eng': 'audio_folder',
    'kor': 'audio_folder_kr',
    'zho-cn': 'audio_folder_zh',
}
```

---

## 8. Data Loading Order (Critical)

All non-AUDIO modes follow the same initialization sequence:

1. **Scan DDS textures** (`texture_folder`) -- build stem-to-path index
2. **Build Knowledge lookup** (`knowledge_folder`) -- StrKey to Name/UITextureName/Desc
3. **Load mode-specific data** (uses folders specific to each mode)
4. **Load language tables** (`loc_folder`) -- for translation display

AUDIO mode skips steps 1-2 and instead:
1. Scan WEM files (`audio_folder`)
2. Load event mappings (`export_folder`)
3. Apply VRS ordering (`vrs_folder`, optional)
4. Load script lines (`loc_folder`)

---

## 9. File Patterns Within Folders

| Folder | File Pattern | Recursive |
|--------|-------------|-----------|
| `knowledge_folder` | `*.xml` | Yes (rglob) |
| `faction_folder` | `*.xml` | Yes |
| `character_folder` | `*.xml` (specifically `characterinfo_*.staticinfo.xml` in QACompiler) | Yes |
| `texture_folder` | `*.dds` | Yes (rglob) |
| `audio_folder` | `*.wem` | Yes (glob) |
| `export_folder` | `*.xml` | Yes |
| `vrs_folder` | `*.xml` | Yes |
| `loc_folder` | `languagedata_{code}.xml` | No (direct children) |

---

## Summary for Implementation

For a Codex API that serves all 4 modes, the complete set of paths needed is exactly what MapDataGenerator's `_PATH_TEMPLATES` defines (11 paths). These are already copied into `mapdata_service.py`'s `PATH_TEMPLATES`. No paths are missing from the server-side templates.

The implementation task is to wire up the unused paths (audio_folder, character_folder, faction_folder, etc.) to actual service methods, following MapDataGenerator's loading patterns per mode.
