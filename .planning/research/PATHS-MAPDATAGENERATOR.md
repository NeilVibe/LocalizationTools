# Path Patterns Research: MapDataGenerator + LocaNext PerforcePathService

**Project:** LocaNext v13.0 Production Path Resolution
**Researched:** 2026-03-26
**Overall confidence:** HIGH (all findings from direct source code analysis)
**Source files analyzed:**
- `RFC/NewScripts/MapDataGenerator/config.py` (667 lines)
- `RFC/NewScripts/MapDataGenerator/core/linkage.py` (~1300 lines)
- `RFC/NewScripts/MapDataGenerator/core/dds_handler.py` (315 lines)
- `RFC/NewScripts/MapDataGenerator/core/audio_handler.py` (337 lines)
- `RFC/NewScripts/MapDataGenerator/core/language.py` (434 lines)
- `RFC/NewScripts/MapDataGenerator/gui/app.py` (settings dialog)
- `RFC/NewScripts/MapDataGenerator/docs/DRIVE_SELECTOR_REPORT.md`
- `RFC/NewScripts/QACompilerNEW/config.py` (path templates)
- `server/tools/ldm/services/perforce_path_service.py` (already in LocaNext)

---

## 1. Complete Path Templates (The Canonical Set)

All 11 path templates are **identical** across MapDataGenerator, QACompiler, and the existing LocaNext `perforce_path_service.py`. This is the single source of truth:

```python
PATH_TEMPLATES = {
    # GameData / StaticInfo (XML game entities)
    "faction_folder":    r"F:\perforce\cd\mainline\resource\GameData\StaticInfo\factioninfo",
    "knowledge_folder":  r"F:\perforce\cd\mainline\resource\GameData\StaticInfo\knowledgeinfo",
    "character_folder":  r"F:\perforce\cd\mainline\resource\GameData\StaticInfo\characterinfo",
    "waypoint_folder":   r"F:\perforce\cd\mainline\resource\GameData\StaticInfo\factioninfo\NodeWaypointInfo",

    # Language Data (LanguageData XMLs)
    "loc_folder":        r"F:\perforce\cd\mainline\resource\GameData\stringtable\loc",
    "export_folder":     r"F:\perforce\cd\mainline\resource\GameData\stringtable\export__",

    # Textures (DDS images)
    "texture_folder":    r"F:\perforce\common\mainline\commonresource\ui\texture\image",

    # Audio (WEM files, per-language folders)
    "audio_folder":      r"F:\perforce\cd\mainline\resource\sound\windows\English(US)",
    "audio_folder_kr":   r"F:\perforce\cd\mainline\resource\sound\windows\Korean",
    "audio_folder_zh":   r"F:\perforce\cd\mainline\resource\sound\windows\Chinese(PRC)",

    # VoiceRecordingSheet (Excel ordering)
    "vrs_folder":        r"F:\perforce\cd\mainline\resource\editordata\VoiceRecordingSheet__",
}
```

### Additional QACompiler-Only Templates (NOT in MapDataGenerator)

QACompiler has 12 templates total. The extras are quest/scenario-specific:

```python
# QACompiler-only templates (not needed for v13.0)
"RESOURCE_FOLDER":              r"F:\perforce\cd\mainline\resource\GameData\StaticInfo",
"QUESTGROUPINFO_FILE":          r"F:\perforce\cd\mainline\resource\GameData\staticinfo_quest\questgroupinfo.staticinfo.xml",
"SCENARIO_FOLDER":              r"F:\perforce\cd\mainline\resource\GameData\staticinfo_quest\main",
"FACTION_QUEST_FOLDER":         r"F:\perforce\cd\mainline\resource\GameData\staticinfo_quest\faction",
"CHALLENGE_FOLDER":             r"F:\perforce\cd\mainline\resource\GameData\staticinfo_quest\Challenge",
"MINIGAME_FILE":                r"F:\perforce\cd\mainline\resource\GameData\staticinfo_quest\contents\contents_minigame.staticinfo.xml",
"STRINGKEYTABLE_FILE":          r"F:\perforce\cd\mainline\resource\editordata\StaticInfo__\StaticInfo_StringKeyTable.xml",
"SEQUENCER_FOLDER":             r"F:\perforce\cd\mainline\resource\sequencer\stageseq",
"FACTIONINFO_FOLDER":           r"F:\perforce\cd\mainline\resource\GameData\StaticInfo\factioninfo",
"VOICE_RECORDING_SHEET_FOLDER": r"F:\perforce\cd\mainline\resource\editordata\VoiceRecordingSheet__",
```

---

## 2. Path Anatomy: Two Distinct Perforce Depots

**CRITICAL DISCOVERY:** Textures use a DIFFERENT depot than everything else.

| Path Segment | Game Data | Textures |
|-------------|-----------|----------|
| Drive | `F:` | `F:` |
| Root | `\perforce\` | `\perforce\` |
| **Depot** | **`cd`** | **`common`** |
| Branch | `\mainline\` | `\mainline\` |
| Base | `resource\GameData\...` | `commonresource\ui\texture\image` |

This means branch substitution affects both depots but the depot name differs:
- **`cd` depot**: All game data, language, audio, VRS
- **`common` depot**: UI textures only

Template structure:
```
{DRIVE}:\perforce\{DEPOT}\{BRANCH}\{REST_OF_PATH}
```

Where `{DEPOT}` is either `cd` or `common`.

---

## 3. DDS Image Path Resolution

### How MapDataGenerator Finds DDS Files for a Given Entity

**Resolution chain:** Entity XML -> `UITextureName` attribute -> DDSIndex scan -> file match

#### Step 1: DDSIndex Scans Texture Folder
```python
# linkage.py DDSIndex.scan_folder()
# Recursively scans: F:\perforce\common\mainline\commonresource\ui\texture\image\**\*.dds
# Indexes TWICE per file: once by stem (no ext), once by full filename
for dds_path in sorted(texture_folder.rglob("*.dds")):
    name_lower = dds_path.stem.lower()        # e.g., "cd_knowledgeimage_node_hexe_sanctuary"
    self._dds_files[name_lower] = dds_path     # Index by stem
    self._dds_files[dds_path.name.lower()] = dds_path  # Index by filename with .dds
```

#### Step 2: Entity Has UITextureName Attribute
```xml
<!-- KnowledgeInfo example -->
<KnowledgeInfo StrKey="Knowledge_Node_Hexe_Sanctuary"
               Name="헥세 성역"
               UITextureName="CD_KnowledgeImage_Node_Hexe_Sanctuary"
               Desc="..."/>
```

#### Step 3: DDSIndex.find() Resolves Path
```python
def find(self, ui_texture_name: str) -> Optional[Path]:
    name = ui_texture_name.lower().strip()

    # 1. Remove path components (if UITextureName has / or \)
    if '/' in name or '\\' in name:
        name = name.replace('\\', '/').split('/')[-1]

    # 2. Remove .dds extension for lookup
    lookup_name = name[:-4] if name.endswith('.dds') else name

    # 3. Try exact stem match
    if lookup_name in self._dds_files: return it

    # 4. Try with .dds
    if name in self._dds_files: return it

    # 5. Try adding .dds
    if (lookup_name + '.dds') in self._dds_files: return it

    # 6. FALLBACK: Partial/fuzzy substring match
    for key in self._dds_files:
        if lookup_name in key or key in lookup_name: return it
```

#### DDS Path Pattern:
```
{DRIVE}:\perforce\common\{BRANCH}\commonresource\ui\texture\image\{SUBFOLDERS}\{UITextureName}.dds
```

Actual file example:
```
F:\perforce\common\mainline\commonresource\ui\texture\image\knowledge\CD_KnowledgeImage_Node_Hexe_Sanctuary.dds
```

### For LocaNext (WSL Context)
The existing `perforce_path_service.py` converts to WSL:
```python
# F:\perforce\common\mainline\... -> /mnt/f/perforce/common/mainline/...
def convert_to_wsl_path(windows_path: str) -> str:
    drive = windows_path[0].lower()
    rest = windows_path[2:].replace("\\", "/")
    return f"/mnt/{drive}{rest}"
```

---

## 4. WEM Audio Path Resolution

### How MapDataGenerator Finds WEM Audio for a Given Entity

**Resolution chain:** Entity/Event -> event_name -> AudioIndex WEM scan -> file match

#### Step 1: AudioIndex Scans Audio Folder
```python
# Audio folder per language:
#   English: F:\perforce\cd\mainline\resource\sound\windows\English(US)\**\*.wem
#   Korean:  F:\perforce\cd\mainline\resource\sound\windows\Korean\**\*.wem
#   Chinese: F:\perforce\cd\mainline\resource\sound\windows\Chinese(PRC)\**\*.wem

for wem_path in sorted(audio_folder.rglob("*.wem")):
    event_name = wem_path.stem.lower()  # filename without extension
    self._wem_files[event_name] = wem_path
```

#### Step 2: Event Mappings from Export XMLs
```python
# Export folder: F:\perforce\cd\mainline\resource\GameData\stringtable\export__\**\*.xml
# Maps: SoundEventName/EventName -> StringId
for elem in root.iter():
    attrs = {k.lower(): v for k, v in elem.attrib.items()}
    event_name = attrs.get("soundeventname") or attrs.get("eventname")
    string_id = attrs.get("stringid")
    # Store: event_name -> string_id
```

#### Step 3: Script Lines from Loc XMLs
```python
# Loc folder: F:\perforce\cd\mainline\resource\GameData\stringtable\loc\
# Files: languagedata_KOR.xml, languagedata_ENG.xml
# Maps: StringId -> Str (text), StringId -> StrOrigin
for elem in root.iter():
    string_id = attrs.get("stringid")
    str_origin = attrs.get("strorigin")
    text = attrs.get("str")
    # Store: string_id -> kor_text, string_id -> eng_text
```

#### Complete Audio Lookup Chain:
```
event_name.wem -> event_name -> StringId (from export XML) -> StrOrigin + Str (from loc XML)
```

#### Audio Folder Selection (Language-Specific):
```python
LANG_TO_AUDIO_FOLDER = {
    'eng': 'audio_folder',      # -> .../sound/windows/English(US)/
    'kor': 'audio_folder_kr',   # -> .../sound/windows/Korean/
    'zho-cn': 'audio_folder_zh', # -> .../sound/windows/Chinese(PRC)/
}
```

WEM path pattern:
```
{DRIVE}:\perforce\cd\{BRANCH}\resource\sound\windows\{AUDIO_LANG}\{SUBFOLDERS}\{event_name}.wem
```

---

## 5. LanguageData XML Path Resolution

### File Location Pattern
```
{DRIVE}:\perforce\cd\{BRANCH}\resource\GameData\stringtable\loc\languagedata_{LANG_CODE}.xml
```

### Language Codes (14 total)
```python
LANGUAGES = [
    ('eng', 'English'), ('fre', 'French'), ('ger', 'German'),
    ('spa-es', 'Spanish (Spain)'), ('spa-mx', 'Spanish (Mexico)'),
    ('por-br', 'Portuguese (Brazil)'), ('ita', 'Italian'),
    ('rus', 'Russian'), ('tur', 'Turkish'), ('pol', 'Polish'),
    ('zho-cn', 'Chinese (Simplified)'), ('zho-tw', 'Chinese (Traditional)'),
    ('jpn', 'Japanese'), ('kor', 'Korean'),
]
```

### File Finding Logic (Case-Insensitive)
```python
def _find_lang_file(self, loc_folder: Path, lang_code: str) -> Optional[Path]:
    # Try UPPERCASE: languagedata_KOR.xml
    # Try lowercase: languagedata_kor.xml
    # Try glob match: languagedata_*.xml where suffix == lang_code
```

### XML Structure (LocStr elements)
```xml
<LocStr StringId="12345678901234567890"
        StrOrigin="한국어 원문"
        Str="English translation"/>
```

Key attributes: `StringId`, `StrOrigin` (Korean source), `Str` (translated text)

---

## 6. VoiceRecordingSheet Path Resolution

### Folder Pattern
```
{DRIVE}:\perforce\cd\{BRANCH}\resource\editordata\VoiceRecordingSheet__\
```

### File Discovery
```python
# Finds most recent .xlsx file by modification time
xlsx_files = sorted(vrs_folder.glob("*.xlsx"), key=lambda f: f.stat().st_mtime, reverse=True)
vrs_file = xlsx_files[0]  # Most recent
```

### Reading Logic
- Uses `openpyxl` in `read_only=True` mode
- Finds `EventName` column by header name (not hardcoded index)
- Maps event_name -> row position for chronological ordering
- Events found in VRS get VRS row position as `xml_order`
- Events NOT in VRS get offset (`vrs_max + original_order`) to sort after

---

## 7. Export Folder Path Resolution

### Folder Pattern
```
{DRIVE}:\perforce\cd\{BRANCH}\resource\GameData\stringtable\export__\**\*.xml
```

### Category Tree Construction
- Export XMLs are organized in subdirectories (e.g., `Dialog/QuestDialog/`, `System/LookAt/`)
- Each XML's relative path from `export__/` becomes its category
- `xml_path.relative_to(export_folder).parent` gives the category
- Backslashes normalized to forward slashes for cross-platform

### Export XML Structure
```xml
<SomeElement SoundEventName="event_name_here"
             StringId="12345678901234567890"/>
```

Case-insensitive attribute matching: `soundeventname`, `eventname`, `stringid`

---

## 8. Branch Handling

### Known Branches
```python
# MapDataGenerator
KNOWN_BRANCHES = ["mainline", "cd_beta", "cd_alpha", "cd_lambda"]

# QACompiler (slightly different order)
KNOWN_BRANCHES = ["cd_beta", "mainline", "cd_alpha", "cd_delta", "cd_lambda"]

# LocaNext perforce_path_service.py (union of both)
KNOWN_BRANCHES = ["mainline", "cd_beta", "cd_alpha", "cd_lambda", "cd_delta"]
```

**Note:** QACompiler includes `cd_delta` which MapDataGenerator does not. LocaNext already has the union.

### Branch Substitution (Simple String Replace)
```python
def _apply_branch(path_str: str, branch: str) -> str:
    """Replace 'mainline' with the configured branch name."""
    return path_str.replace("mainline", branch)
```

**WARNING:** This is a naive `str.replace()`. It works because "mainline" only appears once in each path template (in the branch segment). But if a path ever contained "mainline" elsewhere, it would break.

### Branch Affects Both Depots
```
cd depot:     F:\perforce\cd\{BRANCH}\resource\...
common depot: F:\perforce\common\{BRANCH}\commonresource\...
```

Both use the same branch name. Changing branch from `mainline` to `cd_beta` changes both:
```
F:\perforce\cd\cd_beta\resource\GameData\...
F:\perforce\common\cd_beta\commonresource\ui\texture\image\...
```

---

## 9. Drive Letter Handling

### Default Drive
- MapDataGenerator: `F` (default)
- QACompiler: `D` (default)
- LocaNext: `F` (default)

### Drive Substitution
```python
def _apply_drive_letter(path_str: str, drive_letter: str) -> str:
    """Replace default F: drive with configured drive letter."""
    if path_str.startswith("F:") or path_str.startswith("f:"):
        return f"{drive_letter}:{path_str[2:]}"
    return path_str
```

### Drive Validation
```python
# MapDataGenerator
raw_drive = data.get('drive_letter', 'F')
if isinstance(raw_drive, str) and len(raw_drive) == 1 and raw_drive.isalpha():
    drive = raw_drive.upper()
```

### GUI: Combobox with A-Z
```python
drive_combo = ttk.Combobox(
    drive_row, textvariable=drive_var,
    values=[chr(c) for c in range(ord('A'), ord('Z') + 1)],
    width=5, state="readonly"
)
```

### Settings Persistence
```json
// settings.json
{
    "drive_letter": "D",
    "branch": "cd_beta"
}
```

### WSL Path Conversion (LocaNext-specific)
```python
# F:\perforce\... -> /mnt/f/perforce/...
drive = windows_path[0].lower()
return f"/mnt/{drive}{rest.replace('\\', '/')}"
```

---

## 10. Path Validation Patterns

### MapDataGenerator Validates At Load Time
```python
# DDSIndex
if not texture_folder or not texture_folder.exists():
    log.warning("Texture folder not found: %s", texture_folder)
    return 0

# AudioIndex
if not audio_folder or not audio_folder.exists():
    log.warning("Audio folder not found: %s", audio_folder)
    return 0

# Knowledge folder
if not knowledge_folder or not knowledge_folder.exists():
    log.error("Knowledge folder not found: %s", knowledge_folder)
    return 0
```

### DDS File Validation
```python
# DDSHandler.load_dds()
if not path.exists():
    log.warning("DDS file not found: %s", path)
    return None
```

### WEM File Validation
```python
# AudioHandler.convert_wem_to_wav()
if not wem_path.exists():
    log.error("WEM file not found: %s", wem_path)
    return None
```

### Diagnostic Report (DDS)
MapDataGenerator logs a full diagnostic at load time:
```python
log.info("DDS DIAGNOSTIC REPORT")
log.info("DDS Index: %d files indexed from %s", ...)
# Shows 5 HIT examples (DDS found)
# Shows 5 MISS examples (DDS not found)
# Distinguishes: MISS with UITextureName (real problem) vs MISS without UITextureName (expected)
```

---

## 11. Settings GUI Pattern (For LocaNext to Copy)

### MapDataGenerator Settings Dialog
```python
# Perforce Configuration section in dialog
p4_frame = ttk.LabelFrame(dialog, text="Perforce Configuration")

# Drive: Readonly combobox A-Z
drive_combo = ttk.Combobox(drive_row, textvariable=drive_var,
    values=[chr(c) for c in range(ord('A'), ord('Z') + 1)],
    width=5, state="readonly")

# Branch: Editable combobox with known branches
branch_combo = ttk.Combobox(branch_row, textvariable=branch_var,
    values=KNOWN_BRANCHES, width=25)

# Live preview (updates as user types)
preview_var.set(f"{d}:\\perforce\\cd\\{b}\\resource\\GameData\\...")
drive_var.trace_add("write", update_preview)
branch_var.trace_add("write", update_preview)
```

### On Save: Recalculate + Auto-Reload
```python
def on_save():
    if drive_changed:
        update_drive_letter(new_drive)  # Recalculates ALL path globals
    if branch_changed:
        update_branch(new_branch)       # Recalculates ALL path globals

    # Auto-reload data if drive or branch changed
    if drive_changed or branch_changed:
        self._auto_load_data()
```

---

## 12. Existing LocaNext Infrastructure (Already Built)

`server/tools/ldm/services/perforce_path_service.py` already has:

- All 11 PATH_TEMPLATES (identical to MapDataGenerator)
- `KNOWN_BRANCHES` and `KNOWN_DRIVES`
- `generate_paths(drive, branch)` function
- `convert_to_wsl_path()` for WSL conversion
- `PerforcePathService` singleton with `.configure()`, `.resolve()`, `.resolve_audio_folder()`
- `configure_for_mock_gamedata()` for DEV mode
- `get_all_resolved()` and `get_status()` methods

### What's Missing for v13.0

1. **No frontend UI** for drive/branch selection
2. **No API endpoint** to configure drive/branch at runtime
3. **No path validation endpoint** (check if folders exist, report OK/NOT OK)
4. **No wiring** from LanguageData StringID -> GameData entity -> DDS/WEM resolution in the grid context
5. **No settings persistence** (drive/branch saved to disk for next session)

---

## 13. Mock Gamedata Structure (Already in LocaNext)

The existing mock at `tests/fixtures/mock_gamedata/` maps to:
```python
{
    "knowledge_folder": mock_dir / "StaticInfo" / "knowledgeinfo",
    "character_folder": mock_dir / "StaticInfo" / "characterinfo",
    "faction_folder":   mock_dir / "StaticInfo" / "factioninfo",
    "texture_folder":   mock_dir / "texture" / "image",
    "audio_folder":     mock_dir / "sound" / "windows" / "English(US)",
    "audio_folder_kr":  mock_dir / "sound" / "windows" / "Korean",
    "audio_folder_zh":  mock_dir / "sound" / "windows" / "Chinese(PRC)",
    "export_folder":    mock_dir / "export__",
    "loc_folder":       mock_dir / "loc",
    "waypoint_folder":  mock_dir / "StaticInfo" / "factioninfo" / "NodeWaypointInfo",
    "vrs_folder":       mock_dir / "localization",
}
```

---

## 14. Key Architecture Insight: The Resolution Chain

For LocaNext v13.0, the path resolution goes:

### DDS Image for a LanguageData Row:
```
LanguageData row (StringId)
  -> MegaIndex lookup: StringId -> entity StrKey
  -> entity has UITextureName attribute
  -> DDSIndex: UITextureName -> DDS file path
  -> DDS file -> PNG conversion -> display in right panel
```

### WEM Audio for a LanguageData Row:
```
LanguageData row (StringId)
  -> Export XML lookup: StringId -> SoundEventName
  -> AudioIndex: event_name -> WEM file path
  -> WEM file -> WAV conversion (vgmstream-cli) -> playback
```

### The MegaIndex is the bridge:
LanguageData lives in `loc_folder`. Game entities live in `knowledge_folder`, `faction_folder`, `character_folder`. The MegaIndex already links them via StringId/StrKey cross-references. The v13.0 task is wiring this existing linkage to the right panel's Image/Audio tabs.

---

## 15. Recommendations for v13.0

### PATH-01: Branch + Drive Selector UI
- Copy MapDataGenerator's pattern: LabelFrame with drive combobox (A-Z, readonly) + branch combobox (editable, KNOWN_BRANCHES)
- Add live path preview showing resolved example path
- On change: call `PerforcePathService.configure(drive, branch)` + validate + reload
- Save to LocaNext settings (already has settings infrastructure)

### PATH-02: Path Validation
- Check each of the 11 resolved paths: `folder.exists()` and `any(folder.rglob("*.ext"))`
- Return structured status: `{ key: "knowledge_folder", status: "OK", file_count: 42 }` or `{ status: "NOT_OK", reason: "Folder does not exist" }`
- UI shows green/red indicators per path

### PATH-03 + PATH-04: Wire Image/Audio Resolution
- When user selects a LanguageData row, get StringId
- Query MegaIndex for the entity with that StringId
- For DDS: get UITextureName from entity, resolve via DDSIndex
- For WEM: get SoundEventName from export XMLs via StringId, resolve via AudioIndex
- Display in existing right panel Image/Audio tabs

### MOCK-01 + MOCK-02: Mock Testing
- Existing mock_gamedata structure is already correct
- Add mock DDS files (tiny 4x4 DDS) and mock WEM files to fixtures
- E2E test: configure mock -> select LanguageData row -> verify image/audio tabs populate

---

*Research complete. All path templates extracted from source code with exact patterns, validated against 3 independent codebases (MapDataGenerator, QACompiler, LocaNext perforce_path_service.py).*
