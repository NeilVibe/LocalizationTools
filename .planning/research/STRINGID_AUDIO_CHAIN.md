# StringID to Audio/Image Chain Research

**Researched:** 2026-03-21
**Confidence:** HIGH (all findings from direct source code analysis)

---

## 1. What is "StringId" in the AudioIndex chain?

**Answer: StringId is a unique identifier from the EXPORT XML files, NOT the same as StrKey or StrOrigin.**

The chain is documented in `MapDataGenerator/core/linkage.py` line 891-897:

```
1. WEM files:   event_name.wem -> Path              (audio_folder)
2. Export XMLs:  EventName -> StringId               (export_folder)
3. LOC XMLs:     StringId -> StrOrigin + Str         (loc_folder)
4. Lookup:       event -> StringId -> StrOrigin/Str  (one chain, no fallback)
```

### StringId vs StrKey vs StrOrigin

| Field | What It Is | Where It Lives | Example |
|-------|-----------|----------------|---------|
| **StringId / StringID** | Unique string identifier in the localization system | XML attribute on `<LocStr>` elements in both export__ and loc XML files | `ITEM_BLACKSTAR_SWORD_NAME`, `CHAR_VARON_NAME` |
| **StrKey** | Entity key in StaticInfo XMLs (KnowledgeInfo, CharacterInfo, etc.) | XML attribute on entity elements in StaticInfo | `STR_QUEST_0001` |
| **StrOrigin** | Korean original text (source language) | XML attribute on `<LocStr>` elements | "흑성검" |

**CRITICAL DISTINCTION:**
- In the **LocStr format** (uploaded translation files like `locstr_upload_questinfo.xml`), `StrKey` is used as the identifier: `<LocStr StrKey="STR_QUEST_0001" StrOrigin="..." Str="...">`
- In the **LanguageData format** (loc XML files like `showcase_items.loc.xml`), `StringID` is used as the identifier: `<LocStr StringID="ITEM_BLACKSTAR_SWORD_NAME" StrOrigin="..." Str="...">`
- These are the SAME concept (unique row identifier) with different attribute names depending on XML schema variant.

The AudioIndex specifically reads from **export__ XMLs** which use `StringId` attribute.

---

## 2. How does an LDM row expose its StringID?

**Field name: `string_id` (lowercase, snake_case)**

### Database model (server/database/models.py line 700):
```python
string_id = Column(String(255), nullable=True, index=True)  # StringId attribute (may be null for TXT)
```

### Row repository interface (server/repositories/interfaces/row_repository.py line 32):
```python
# Returns: Row dict with: id, file_id, row_num, string_id, source, target,
#          status, extra_data, created_at, updated_at.
```

### API schema (server/tools/ldm/schemas/row.py):
```python
class RowResponse(BaseModel):
    id: int
    file_id: int
    row_num: int
    string_id: Optional[str]  # <-- This is it
    source: Optional[str]
    target: Optional[str]
    ...
```

### Availability by format:

| Format | `string_id` populated? | Source attribute |
|--------|----------------------|-----------------|
| **XML (LocStr)** | YES | `StringId` / `StringID` / `StrKey` (case-variant lookup via STRINGID_ATTRS) |
| **Excel** | YES (if column exists) | Typically a column header like "StringID" |
| **TXT** | May be NULL | Not all TXT formats have StringID columns |

The XML parsing engine (`server/tools/ldm/services/xml_parsing.py` line 28) handles multiple case variants:
```python
STRINGID_ATTRS = ['StringId', 'StringID', 'stringid', 'STRINGID', 'Stringid', 'stringId']
```

---

## 3. REVERSE lookup: StringID -> EventName -> WEM

### In MapDataGenerator (existing forward chain):
```python
# Forward: event_name -> StringId (from export XMLs)
self._event_to_stringid: Dict[str, str] = {}  # key=event_lower, value=StringId
```

### Building the reverse dict:

The key in `_event_to_stringid` is **lowercase event_name**. The value is the **exact StringId string** from the export XML (NOT lowercased).

```python
# To build reverse: StringId -> event_name
stringid_to_event = {}
for event_lower, string_id in audio_index._event_to_stringid.items():
    stringid_to_event[string_id] = event_lower
```

### Case sensitivity:

| Dictionary | Key Case | Value Case |
|-----------|----------|------------|
| `_event_to_stringid` | **lowercase** event_name | **exact case** StringId from XML |
| `_stringid_to_kor` | **exact case** StringId | exact text |
| `_stringid_to_eng` | **exact case** StringId | exact text |
| `_stringid_to_strorigin` | **exact case** StringId | exact text |

**StringId is stored in EXACT CASE as found in the XML.** The event_name keys are lowercased. For the reverse lookup (`string_id -> event`), the key should be the exact-case StringId. When matching against LDM row `string_id`, you may need case-insensitive comparison since the row's `string_id` comes from a different XML source that might use different casing.

### How event_name maps to WEM:
```python
self._wem_files: Dict[str, Path] = {}  # key=event_name.lower(), value=wem_path
```
WEM filenames ARE the event names (stem, lowercased). So: `StringId -> event_lower -> _wem_files[event_lower] -> Path`.

---

## 4. Image chain: StringID -> KnowledgeInfo -> UITextureName -> DDS

This chain works differently from audio. It goes through **KnowledgeInfo** XML entities:

### Chain (from mapdata_service.py):
```
StrKey -> KnowledgeLookup (from KnowledgeInfo XML)
       -> UITextureName attribute
       -> DDS index (lowercase stem lookup)
       -> ImageContext
```

### Key data structures:

1. **KnowledgeLookup** (built from `KnowledgeInfo/*.xml`):
   - Keyed by `StrKey` attribute on `<KnowledgeInfo>` elements
   - Contains: `strkey`, `name`, `desc`, `ui_texture_name`, `group_key`

2. **DDS Index** (built from texture folder scan):
   - Keyed by `lowercase stem` of `.dds` files
   - Value: `Path` to DDS file

3. **Image chain resolution** (`_resolve_image_chains`):
   ```python
   for strkey, knowledge in self._knowledge_table.items():
       texture_name = knowledge.ui_texture_name
       texture_lower = texture_name.lower()
       dds_path = self._dds_index.get(texture_lower)
       # -> ImageContext
   ```

### The gap for LDM rows:

The image chain is indexed by **StrKey** (from KnowledgeInfo). An LDM row has `string_id` (from LocStr/LanguageData). These are **different identifiers**:
- `StrKey` on KnowledgeInfo: e.g., `Knowledge_Region_BlackstarVillage`
- `StringID` on LocStr: e.g., `REGION_BLACKSTAR_NAME`

The current `MapDataService.get_image_context()` does fuzzy matching (partial string containment) to bridge this gap. The `ContextService.resolve_context_for_row()` passes the row's `string_id` directly into `resolve_chain()` which calls `get_knowledge_lookup(strkey)` -- this works IF the StringID happens to match a StrKey, but often they won't match.

**For reliable image lookup from StringID, you would need one of:**
1. A StringID -> StrKey mapping table (not currently built)
2. The fuzzy match in `get_image_context()` which does partial string containment
3. Going through the Codex entity registry which stores both `strkey` and `audio_key=strkey`

---

## 5. Perforce paths for audio resolution

From `MapDataGenerator/config.py` line 136-148:

```python
_PATH_TEMPLATES = {
    'audio_folder':      r"F:\perforce\cd\mainline\resource\sound\windows\English(US)",
    'audio_folder_kr':   r"F:\perforce\cd\mainline\resource\sound\windows\Korean",
    'audio_folder_zh':   r"F:\perforce\cd\mainline\resource\sound\windows\Chinese(PRC)",
    'export_folder':     r"F:\perforce\cd\mainline\resource\GameData\stringtable\export__",
    'loc_folder':        r"F:\perforce\cd\mainline\resource\GameData\stringtable\loc",
    'vrs_folder':        r"F:\perforce\cd\mainline\resource\editordata\VoiceRecordingSheet__",
}
```

### What each folder contains:

| Folder | Contents | Used For |
|--------|----------|----------|
| `audio_folder` | `*.wem` files named by event_name | WEM file path lookup |
| `export_folder` | `*.xml` files with `EventName + StringId` attributes | EventName -> StringId mapping |
| `loc_folder` | `languagedata_KOR.xml`, `languagedata_ENG.xml` etc. | StringId -> StrOrigin/Str text |
| `vrs_folder` | `*.xlsx` VoiceRecordingSheet files | Optional ordering override |

### Audio languages:
```python
AUDIO_LANGUAGES = [
    ('eng', 'English(US)'),
    ('kor', 'Korean'),
    ('zho-cn', 'Chinese(PRC)'),
]
```

### WSL path conversion:
`mapdata_service.py` includes `convert_to_wsl_path()` which converts `F:\perforce\...` to `/mnt/f/perforce/...`.

---

## 6. What does MapDataService.get_audio_context() actually do?

**Currently: It does NOT use the AudioIndex chain at all.** It's a stub that lazy-loads WAV files from a local `audio/` directory.

From `mapdata_service.py` line 364-406:

```python
def get_audio_context(self, string_id: str) -> Optional[AudioContext]:
    """Look up audio context by StrKey, StringID, or KnowledgeKey."""
    if not self._loaded:
        return None
    # Lazy-populate audio index from TTS WAV files
    if not self._strkey_to_audio:
        self._lazy_load_audio()
    result = self._strkey_to_audio.get(string_id)
    if result:
        return result
    # Fuzzy match (partial string containment)
    ...

def _lazy_load_audio(self) -> None:
    """Lazily scan audio/ directory for WAV files."""
    # Scans project root audio/ dir for TTS-generated WAV files
    # Keys by WAV filename stem
```

### What's missing:
1. **No WEM file scanning** -- only looks for local WAV files, not Perforce WEM files
2. **No export XML parsing** -- no EventName -> StringId chain
3. **No loc XML parsing** -- no StringId -> script text chain
4. **No real audio content** -- only TTS-generated placeholder WAVs

### What would need to be built for real audio:
To build a proper `StringID -> AudioContext` reverse lookup:

```python
# 1. Scan WEM files from audio_folder
#    event_name.wem -> Path  (keyed by lowercase stem)

# 2. Parse export__ XMLs for EventName -> StringId
#    (SoundEventName or EventName attr) -> (StringId attr)

# 3. Build reverse: StringId -> event_name -> wem_path
#    stringid_to_event[string_id] = event_name_lower
#    Then: wem_path = wem_files[event_name_lower]

# 4. Parse loc XMLs for StringId -> script text (optional, for display)
#    stringid_to_kor[string_id] = Str text
```

---

## Summary Table

| Question | Answer |
|----------|--------|
| StringId == StrKey? | **NO.** StringId is the LocStr identifier. StrKey is the StaticInfo entity identifier. Different naming, different schemas. |
| StringId == StrOrigin? | **NO.** StrOrigin is the Korean source text. StringId is the unique identifier string. |
| Row field name? | `string_id` (snake_case, nullable, String(255)) |
| All formats have it? | XML: yes. Excel: usually. TXT: may be null. |
| Case sensitive? | StringId in AudioIndex is stored exact-case. Event names are lowercased. Match carefully. |
| Image chain from StringID? | StringID -> (fuzzy match) -> KnowledgeInfo.StrKey -> UITextureName -> DDS. No reliable direct mapping exists. |
| get_audio_context() status? | **STUB.** Only scans local WAV files. Does NOT implement the real WEM chain from MapDataGenerator. |
| What needs building? | Reverse dict `stringid_to_event` from AudioIndex data, or port AudioIndex chain into MapDataService. |
