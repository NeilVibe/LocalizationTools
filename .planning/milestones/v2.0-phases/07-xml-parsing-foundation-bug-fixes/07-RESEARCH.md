# Phase 07: XML Parsing Foundation + Bug Fixes - Research

**Researched:** 2026-03-15
**Domain:** XML parsing with lxml, sanitization/recovery, language table extraction, cross-reference chains, Aho-Corasick glossary building, plus v1.0 bug fixes
**Confidence:** HIGH

## Summary

Phase 07 is the foundation for all v2.0 work. Every downstream feature (merge, export, media, AI summaries) depends on reliable XML parsing. The current `xml_handler.py` uses stdlib `xml.etree.ElementTree` which crashes on malformed game data -- it must be replaced with lxml + sanitization, porting battle-tested patterns from QuickTranslate and MapDataGenerator. The existing service scaffolds (MapDataService, GlossaryService, ContextService) are well-designed singletons with empty indexes that need to be filled with real XML data pipelines.

The critical insight is that **every XML parsing pattern needed already exists in NewScripts**. QuickTranslate has `sanitize_xml_content()`, `parse_xml_file()`, `iter_locstr_elements()`, and attribute constants. MapDataGenerator has `KnowledgeLookup`, `DataEntry`, and the cross-reference chain builder. QACompiler has `StringIdConsumer` for deduplication. LanguageDataExporter has language file discovery and parsing. This is a porting effort -- the algorithms are proven, the edge cases are handled, the test patterns are known.

The three bug fixes (FIX-01 through FIX-03) are independent of XML parsing and involve the TM/folder subsystem. They can be tackled in parallel with XML work.

**Primary recommendation:** Port QuickTranslate's XML sanitizer and parser as the new `XMLParsingEngine` service, then wire MapDataService and GlossaryService to consume real parsed data. Fix TM bugs independently.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| XML-01 | MapDataService parses real KnowledgeInfo XMLs and builds StrKey-to-UITextureName-to-DDS chains | Port MapDataGenerator `linkage.py` KnowledgeLookup/DataEntry + DDS index builder into MapDataService.initialize() |
| XML-02 | GlossaryService wires to real game data and builds Aho-Corasick automaton from staticinfo | GlossaryService already has extract_*_glossary() methods + _parse_xml() with lxml recovery; wire initialize() to real WSL paths via convert_to_wsl_path() |
| XML-03 | ContextService resolves multi-pass KnowledgeKey chains with full metadata | Port MapDataGenerator's multi-step chain resolution: StrKey -> KnowledgeInfo -> UITextureName -> DDS path, with partial result tracking |
| XML-04 | XML sanitizer + recovery pattern handles malformed game data files gracefully | Port QuickTranslate `sanitize_xml_content()` (5 steps: control chars, bad entities, seg newlines, attribute escaping, tag stack repair) + lxml `recover=True` fallback |
| XML-05 | Cross-reference chain resolution works across multiple XML files (join keys) | Port MapDataGenerator linkage pattern: build knowledge lookup table first, then resolve DataEntry references across characterinfo/iteminfo/factioninfo XMLs |
| XML-06 | Language table parsing extracts all language columns from loc.xml files correctly | Port QuickTranslate `language_loader.py` discover_language_files() + build_translation_lookup() pattern; 14 language codes supported |
| XML-07 | StringIdConsumer pattern provides fresh consumer per language for deduplication | Port QACompiler `StringIdConsumer` class from generators/base.py; critical: one fresh instance per language, never shared |
| FIX-01 | Offline TMs appear in online TM tree (SQLite-to-PostgreSQL visibility) | TMExplorerTree fetches from `/api/ldm/tm-tree` -- need to ensure endpoint returns both online and offline TMs merged into single tree structure |
| FIX-02 | TM Paste UI flow works correctly end-to-end | Clipboard store exists; trace paste flow from VirtualGrid/TMExplorerGrid through API to repository |
| FIX-03 | Folder fetch returns 200 (not 404) after creation | SQLite folder_repo.py creates folders with negative IDs; verify get_folder_contents() handles negative IDs correctly after create() |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| lxml | >=4.9.0 (installed) | XML parsing with sanitization + recovery | Already in requirements.txt, used by ALL NewScripts projects. `recover=True` handles malformed game files where stdlib ET crashes |
| ahocorasick | (installed) | O(n) multi-pattern entity matching | Already used by GlossaryService for entity detection |
| loguru | (installed) | Structured logging | Project standard -- never use `print()` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| re | stdlib | XML sanitization regex, Korean detection | Bad entity fixing, tag repair, control char removal |
| pathlib | stdlib | File path operations | All file I/O with WSL path translation |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| lxml | xml.etree.ElementTree (stdlib) | Stdlib crashes on malformed XML, no recovery mode, no attribute order preservation. lxml is the ONLY correct choice. |
| Custom XML sanitizer | defusedxml | defusedxml prevents XXE but doesn't fix malformed content. QuickTranslate's sanitizer handles game-specific corruption patterns. |

**Installation:**
```bash
# Nothing to install -- all dependencies already in requirements.txt
```

## Architecture Patterns

### Recommended Project Structure
```
server/tools/ldm/
  services/
    xml_parsing.py            # NEW: XMLParsingEngine (ports QuickTranslate patterns)
    filetype_detector.py      # NEW: FileType enum + detect_file_type()
    mapdata_service.py        # MODIFY: Fill indexes with real XML data via XMLParsingEngine
    glossary_service.py       # MODIFY: Wire initialize() to real WSL paths
    context_service.py        # MODIFY: Add chain resolution logging
  file_handlers/
    xml_handler.py            # MODIFY: Replace stdlib ET with lxml + sanitizer
```

### Pattern 1: XMLParsingEngine -- Centralized Parsing Service
**What:** A singleton service that wraps all XML parsing operations with sanitization, encoding detection, and recovery. All other services call XMLParsingEngine instead of parsing XML directly.
**When to use:** Every XML file operation in the system.
**Example:**
```python
# Source: QuickTranslate/core/xml_parser.py (direct port)
from __future__ import annotations

from lxml import etree
from pathlib import Path
from typing import Dict, List, Optional
from loguru import logger
import re

# Centralized attribute name variants (from QuickTranslate)
STRINGID_ATTRS = ['StringId', 'StringID', 'stringid', 'STRINGID', 'Stringid', 'stringId']
STRORIGIN_ATTRS = ['StrOrigin', 'Strorigin', 'strorigin', 'STRORIGIN']
STR_ATTRS = ('Str', 'str', 'STR')
DESC_ATTRS = ['Desc', 'desc', 'DESC']
DESCORIGIN_ATTRS = ['DescOrigin', 'Descorigin', 'descorigin', 'DESCORIGIN']
LOCSTR_TAGS = ['LocStr', 'locstr', 'LOCSTR', 'LOCStr', 'Locstr']

_bad_entity_re = re.compile(r'&(?!lt;|gt;|amp;|apos;|quot;|#)')

class XMLParsingEngine:
    """Centralized XML parsing with sanitization and recovery."""

    def sanitize(self, raw: str) -> str:
        """Port of QuickTranslate sanitize_xml_content -- 5-step pipeline."""
        # 1. Remove control characters
        raw = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', raw)
        # 2. Fix bad entities
        raw = _bad_entity_re.sub("&amp;", raw)
        # 3. Handle newlines in seg elements
        raw = self._preprocess_newlines(raw)
        # 4. Fix unescaped < in attribute values
        raw = re.sub(r'="([^"]*<[^"]*)"',
                     lambda m: '="' + m.group(1).replace("<", "&lt;") + '"', raw)
        # 5. Repair malformed tag structure
        raw = self._repair_tag_stack(raw)
        return raw

    def parse_file(self, path: Path) -> Optional[etree._Element]:
        """Parse with strict-first, recovery-fallback (QuickTranslate pattern)."""
        content = path.read_text(encoding='utf-8')
        content = self.sanitize(content)
        try:
            return etree.fromstring(
                content.encode('utf-8'),
                parser=etree.XMLParser(huge_tree=True)
            )
        except etree.XMLSyntaxError:
            logger.warning(f"[XML] Strict parse failed for {path.name}, using recovery mode")
            return etree.fromstring(
                content.encode('utf-8'),
                parser=etree.XMLParser(recover=True, huge_tree=True)
            )
```

### Pattern 2: Knowledge Chain Builder (MapDataGenerator Port)
**What:** Build StrKey-to-image lookup tables from KnowledgeInfo XMLs, then resolve cross-reference chains.
**When to use:** MapDataService.initialize() -- populating the _strkey_to_image index.
**Example:**
```python
# Source: MapDataGenerator/core/linkage.py (port KnowledgeLookup + build_knowledge_table)
@dataclass
class KnowledgeLookup:
    strkey: str
    name: str
    desc: str
    ui_texture_name: str
    group_key: str = ""
    source_file: str = ""

def build_knowledge_table(knowledge_folder: Path, parser: XMLParsingEngine) -> Dict[str, KnowledgeLookup]:
    """Build StrKey -> KnowledgeLookup from KnowledgeInfo XMLs."""
    table = {}
    for xml_path in knowledge_folder.rglob("*.xml"):
        root = parser.parse_file(xml_path)
        if root is None:
            continue
        for elem in root.iter("KnowledgeData"):
            strkey = elem.get("StrKey") or ""
            if strkey:
                table[strkey] = KnowledgeLookup(
                    strkey=strkey,
                    name=elem.get("Name") or "",
                    desc=elem.get("Desc") or "",
                    ui_texture_name=elem.get("UITextureName") or "",
                    source_file=xml_path.name,
                )
    return table
```

### Pattern 3: Singleton Service with Lazy Init (Existing Pattern)
**What:** All services use `get_*_service()` factory functions returning module-level singletons.
**When to use:** Every new and modified service.
**Example:**
```python
# Existing pattern in mapdata_service.py, glossary_service.py, context_service.py
_service_instance: Optional[XMLParsingEngine] = None

def get_xml_parsing_engine() -> XMLParsingEngine:
    global _service_instance
    if _service_instance is None:
        _service_instance = XMLParsingEngine()
    return _service_instance
```

### Pattern 4: WSL Path Translation (Existing in MapDataService)
**What:** Convert Windows paths to WSL paths at the API boundary.
**When to use:** Every file operation involving game data paths.
**Example:**
```python
# Already exists in mapdata_service.py -- reuse directly
def convert_to_wsl_path(windows_path: str) -> str:
    if windows_path.startswith("/"):
        return windows_path
    if len(windows_path) >= 2 and windows_path[1] == ":":
        drive = windows_path[0].lower()
        rest = windows_path[2:].replace("\\", "/")
        return f"/mnt/{drive}{rest}"
    return windows_path
```

### Anti-Patterns to Avoid
- **Using stdlib ElementTree for game data:** stdlib ET crashes on malformed XML. Always use lxml with `recover=True` fallback.
- **Parsing XML in route handlers:** Routes should be thin (5-10 lines). XML parsing belongs in services.
- **Hardcoding attribute names:** Use the centralized `STRINGID_ATTRS`, `STRORIGIN_ATTRS` constants from QuickTranslate.
- **Global module-level state for file metadata:** The current `xml_handler.py` uses `_file_metadata: Dict = {}` as module-level state. This is not thread-safe and breaks with concurrent requests. Store metadata per-file in the return value.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| XML sanitization | Custom regex pipeline | Port `sanitize_xml_content()` from QuickTranslate | Handles 5 classes of XML corruption (control chars, bad entities, seg newlines, unescaped < in attrs, malformed tags). Missing any one causes parse failures. |
| LocStr element iteration | Simple `root.findall('LocStr')` | Port `iter_locstr_elements()` with `LOCSTR_TAGS` | Case-insensitive tag matching handles `LocStr`, `locstr`, `LOCSTR` variants across different game data files. |
| Attribute extraction | Direct `elem.get('StringId')` | Port `get_attr(elem, STRINGID_ATTRS)` | Handles 6 case variants of StringId attribute across different data sources. |
| Knowledge chain resolution | Custom XML tree traversal | Port MapDataGenerator `build_knowledge_table()` + `build_dds_index()` | Chain resolution across 3+ XML file types with fallback lookups is deceptively complex. |
| StringID deduplication | Simple `set()` tracking | Port QACompiler `StringIdConsumer` | Ordered consumption preserving document order with per-file, per-text pointers. Simple set tracking loses order and breaks cross-reference resolution. |
| Korean text detection | `re.search(r'[\uac00-\ud7af]', text)` | Full regex `[\uac00-\ud7af\u1100-\u11ff\u3130-\u318f]` | Missing Jamo and Compatibility Jamo ranges causes false negatives on decomposed Korean. |

**Key insight:** The NewScripts codebase has spent months handling edge cases in XML parsing. Porting saves weeks and prevents data corruption.

## Common Pitfalls

### Pitfall 1: stdlib ET vs lxml Divergence (CRITICAL)
**What goes wrong:** Current `xml_handler.py` uses `import xml.etree.ElementTree as ET`. Real game XML files have malformed content (bare `&`, control chars, unclosed tags). Stdlib ET throws `ParseError` and stops. lxml's `recover=True` handles gracefully.
**Why it happens:** v1.0 was built with clean test fixtures. Real game data is messy.
**How to avoid:** Replace stdlib ET with lxml in `xml_handler.py` FIRST, before any other work. Port the 3-stage validation from QuickTranslate: (1) sanitize, (2) strict parse, (3) recovery fallback.
**Warning signs:** Any `ET.ParseError` in server logs when opening real XML files.

### Pitfall 2: Encoding Detection Cascade
**What goes wrong:** Current handler tries `['utf-8', 'utf-16', 'cp1252', 'iso-8859-1']` in sequence. CP1252 and ISO-8859-1 overlap for bytes 0x80-0x9F, causing mojibake on European special characters. Korean text in non-UTF-8 files is silently destroyed.
**Why it happens:** Many encodings are ASCII supersets -- the cascade picks whichever doesn't throw an error, not the correct one.
**How to avoid:** Parse XML declaration `<?xml encoding="..."?>` first. For LocStr files: Korean content = always UTF-8 (project standard). Keep cascade as last-resort fallback only.
**Warning signs:** Characters like curly quotes appearing as garbage after round-trip.

### Pitfall 3: Cross-Reference Chain Missing Intermediate Files
**What goes wrong:** StrKey -> KnowledgeInfo -> UITextureName -> DDS path spans multiple XML files. If any file in the chain is missing, the code returns None silently. User sees "No Image" placeholder with no explanation.
**Why it happens:** Game data directories may have incomplete data, different branch structures, or missing files.
**How to avoid:** Track chain resolution steps explicitly. Return partial results: "Found KnowledgeKey but UITextureName missing" is more useful than None. Log each step's success/failure.
**Warning signs:** Image tab shows all placeholders despite DDS files existing on disk.

### Pitfall 4: File Path Windows vs WSL2
**What goes wrong:** PATH_TEMPLATES in `mapdata_service.py` use Windows backslash paths (`F:\perforce\...`). The server runs in WSL2 where paths are `/mnt/f/perforce/...`. `Path()` objects with Windows paths don't resolve in Linux.
**Why it happens:** MapDataGenerator was a Windows-only tool. LocaNext server runs in WSL2.
**How to avoid:** `convert_to_wsl_path()` already exists in mapdata_service.py. Apply it to ALL path templates before any file operations. Handle drive letter case insensitivity.
**Warning signs:** `FileNotFoundError` for paths that exist when accessed from Windows Explorer.

### Pitfall 5: Module-Level State in xml_handler.py
**What goes wrong:** Current `xml_handler.py` stores file metadata in `_file_metadata: Dict = {}` at module level. With concurrent requests, one file's metadata overwrites another's.
**Why it happens:** Quick scaffolding pattern that works in single-request testing but fails under load.
**How to avoid:** Return metadata as part of the parse result (tuple or dataclass), not as module-level state.
**Warning signs:** Metadata from wrong file appearing in API responses.

### Pitfall 6: GlossaryService _parse_xml Uses lxml But xml_handler Uses stdlib ET
**What goes wrong:** GlossaryService already uses lxml with `recover=True` in its `_parse_xml()` method. The file handler `xml_handler.py` uses stdlib ET. These parse differently -- attribute ordering, entity handling, and recovery behavior diverge. Files that parse fine through one path may fail or produce different results through the other.
**Why it happens:** Services were built at different times by different phases.
**How to avoid:** Migrate ALL XML parsing to go through XMLParsingEngine, which uses lxml exclusively. GlossaryService._parse_xml() should delegate to XMLParsingEngine.parse_file().

## Code Examples

Verified patterns from existing NewScripts source code:

### XML Sanitization (QuickTranslate/core/xml_parser.py)
```python
# Source: QuickTranslate/core/xml_parser.py lines 100-127
def sanitize_xml_content(raw: str) -> str:
    # 1. Remove control characters
    raw = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', raw)
    # 2. Fix bad entities (& not part of valid XML entity ref)
    raw = _bad_entity_re.sub("&amp;", raw)
    # 3. Handle newlines in seg elements -> <br/>
    raw = _preprocess_newlines(raw)
    # 4. Fix unescaped < in attribute values
    raw = re.sub(r'="([^"]*<[^"]*)"',
                 lambda m: '="' + m.group(1).replace("<", "&lt;") + '"', raw)
    # 5. Repair malformed tag structure
    raw = _repair_tag_stack(raw)
    return raw
```

### LocStr Parsing with Skip Guards (QuickTranslate/core/xml_io.py)
```python
# Source: QuickTranslate/core/xml_io.py lines 48-66
# Three critical skip guards when parsing corrections:
# 1. Skip Korean-only Str values (untranslated = not a correction)
if is_korean_text(str_value):
    continue
# 2. Skip "no translation" entries
_norm = ' '.join(str_value.split()).lower()
if _norm == 'no translation':
    continue
# 3. Skip formula/garbage text
bad_str = is_formula_text(str_value)
if bad_str:
    continue
```

### Knowledge Chain Resolution (MapDataGenerator/core/linkage.py)
```python
# Source: MapDataGenerator/core/linkage.py
# Step 1: Build knowledge table
knowledge_table: Dict[str, KnowledgeLookup] = {}
for xml_path in knowledge_folder.rglob("*.xml"):
    root = parse_xml(xml_path)
    for elem in root.iter("KnowledgeData"):
        strkey = elem.get("StrKey") or ""
        if strkey:
            knowledge_table[strkey] = KnowledgeLookup(
                strkey=strkey,
                name=elem.get("Name") or "",
                ui_texture_name=elem.get("UITextureName") or "",
            )

# Step 2: Build DDS index (UITextureName -> DDS path)
dds_index: Dict[str, Path] = {}
for dds_file in texture_folder.rglob("*.dds"):
    dds_index[dds_file.stem.lower()] = dds_file

# Step 3: Resolve chain: StrKey -> knowledge -> UITextureName -> DDS
def resolve_image(strkey: str) -> Optional[Path]:
    lookup = knowledge_table.get(strkey)
    if not lookup or not lookup.ui_texture_name:
        return None
    return dds_index.get(lookup.ui_texture_name.lower())
```

### Language File Discovery (QuickTranslate/core/language_loader.py)
```python
# Source: QuickTranslate/core/language_loader.py lines 14-34
def discover_language_files(loc_folder: Path) -> Dict[str, Path]:
    lang_files = {}
    for xml_file in loc_folder.glob("languagedata_*.xml"):
        match = re.match(r'languagedata_(.+)\.xml', xml_file.name, re.IGNORECASE)
        if match:
            lang_code = match.group(1).lower()
            lang_files[lang_code] = xml_file
    return lang_files
# Supported: eng, fre, ger, spa-es, spa-mx, por-br, ita, rus, tur, pol, zho-cn, zho-tw, jpn, kor
```

### StringIdConsumer (QACompiler/generators/base.py)
```python
# Source: QACompilerNEW/generators/base.py lines 221-251
class StringIdConsumer:
    """Consume StringIDs in document order. Fresh instance per language."""
    def __init__(self, ordered_index: Dict[str, Dict[str, List[str]]]):
        self._index = ordered_index
        self._consumed: Dict[Tuple[str, str], int] = defaultdict(int)

    def consume(self, normalized_kor: str, export_key: str) -> Optional[str]:
        file_map = self._index.get(export_key)
        if not file_map:
            return None
        sid_list = file_map.get(normalized_kor)
        if not sid_list:
            return None
        key = (export_key, normalized_kor)
        idx = self._consumed[key]
        if idx >= len(sid_list):
            return None
        self._consumed[key] = idx + 1
        return sid_list[idx]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| stdlib ElementTree | lxml with recover=True | v2.0 (now) | Malformed game files no longer crash parser |
| Module-level metadata dict | Per-file metadata in return value | v2.0 (now) | Thread-safe concurrent file parsing |
| Hardcoded attribute names | Centralized STRINGID_ATTRS constants | Already in QuickTranslate | Case-insensitive across all game data variants |
| Simple encoding cascade | XML declaration parsing first | v2.0 (now) | Correct encoding detection for multi-language files |

**Deprecated/outdated:**
- `xml.etree.ElementTree` for game data parsing: crashes on malformed XML, no recovery
- Module-level `_file_metadata` pattern: not thread-safe

## Open Questions

1. **Offline TM visibility (FIX-01) -- exact bug location**
   - What we know: TMExplorerTree fetches from `/api/ldm/tm-tree`. Both online and offline TMs exist in their respective repositories.
   - What's unclear: Whether the tm-tree endpoint merges SQLite TMs into the tree response, or if it only queries the primary (PostgreSQL) repository.
   - Recommendation: Trace the `/api/ldm/tm-tree` endpoint to its handler and verify it queries both repositories via the factory pattern. The fix is likely in the route or the repository factory.

2. **TM Paste flow (FIX-02) -- what exactly breaks**
   - What we know: Clipboard store exists (`clipboard.js`), paste references exist in VirtualGrid and TMExplorerGrid.
   - What's unclear: Whether the bug is in the frontend paste handler, the API endpoint, or the repository layer. Need to reproduce.
   - Recommendation: Trace the full paste flow during planning. This may be a Svelte reactivity issue (stale state after paste) or an API contract mismatch.

3. **Folder 404 after creation (FIX-03) -- negative ID handling**
   - What we know: SQLite folder_repo creates folders with negative IDs (`-int(time.time() * 1000) % 1000000000`). The create method returns `await self.get(folder_id)` which should work.
   - What's unclear: Whether the 404 happens on the subsequent GET request from the frontend (race condition?) or if the negative ID causes issues in the folder content endpoint.
   - Recommendation: Check if `get_folder_contents()` or the frontend's fetch-after-create has a timing issue with the negative ID.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest with pytest-asyncio |
| Config file | `pytest.ini` (root) |
| Quick run command | `python -m pytest tests/unit/ldm/ -x --no-header -q` |
| Full suite command | `python -m pytest tests/unit/ldm/ tests/stability/ -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| XML-01 | MapDataService parses KnowledgeInfo, builds StrKey chains | unit | `python -m pytest tests/unit/ldm/test_xml_parsing.py::test_knowledge_chain -x` | Wave 0 |
| XML-02 | GlossaryService builds AC automaton from real staticinfo | unit | `python -m pytest tests/unit/ldm/test_glossary_service.py::test_build_from_real_data -x` | Wave 0 (test file exists, new tests needed) |
| XML-03 | ContextService resolves multi-pass KnowledgeKey chains | unit | `python -m pytest tests/unit/ldm/test_context_service.py::test_chain_resolution -x` | Wave 0 (test file exists, new tests needed) |
| XML-04 | XML sanitizer handles malformed game data | unit | `python -m pytest tests/unit/ldm/test_xml_parsing.py::test_sanitizer -x` | Wave 0 |
| XML-05 | Cross-reference chains work across multiple XML files | unit | `python -m pytest tests/unit/ldm/test_xml_parsing.py::test_cross_reference -x` | Wave 0 |
| XML-06 | Language table parsing extracts all language columns | unit | `python -m pytest tests/unit/ldm/test_xml_parsing.py::test_language_table -x` | Wave 0 |
| XML-07 | StringIdConsumer deduplication per language | unit | `python -m pytest tests/unit/ldm/test_xml_parsing.py::test_stringid_consumer -x` | Wave 0 |
| FIX-01 | Offline TMs appear in online TM tree | integration | `python -m pytest tests/unit/ldm/test_routes_tm_crud.py -x -k offline` | Wave 0 (test file exists, new test needed) |
| FIX-02 | TM paste works end-to-end | integration | `python -m pytest tests/unit/ldm/test_tm_paste.py -x` | Wave 0 |
| FIX-03 | Folder fetch returns 200 after creation | integration | `python -m pytest tests/unit/ldm/test_routes_folders.py -x -k create_then_get` | Wave 0 (test file exists, new test needed) |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/unit/ldm/ -x --no-header -q`
- **Per wave merge:** `python -m pytest tests/unit/ldm/ tests/stability/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/unit/ldm/test_xml_parsing.py` -- covers XML-01, XML-04, XML-05, XML-06, XML-07 (new file)
- [ ] `tests/unit/ldm/test_glossary_service.py` -- needs new tests for XML-02 with real fixture data
- [ ] `tests/unit/ldm/test_context_service.py` -- needs new tests for XML-03 chain resolution
- [ ] `tests/unit/ldm/test_routes_tm_crud.py` -- needs test for FIX-01 offline TM visibility
- [ ] `tests/unit/ldm/test_tm_paste.py` -- covers FIX-02 (new file)
- [ ] `tests/unit/ldm/test_routes_folders.py` -- needs test for FIX-03 create-then-get
- [ ] `tests/fixtures/xml/` -- XML fixture files (malformed, KnowledgeInfo, LocStr, language tables)

## Sources

### Primary (HIGH confidence)
- QuickTranslate `core/xml_parser.py` -- sanitizer, attribute constants, parse_xml_file, validate_xml_load
- QuickTranslate `core/xml_io.py` -- parse_corrections_from_xml, skip guards (Korean, no-translation, formula)
- QuickTranslate `core/language_loader.py` -- discover_language_files, build_translation_lookup
- MapDataGenerator `core/linkage.py` -- KnowledgeLookup, DataEntry, build_knowledge_table, build_dds_index
- QACompilerNEW `generators/base.py` -- StringIdConsumer class
- LanguageDataExporter `exporter/xml_parser.py` -- sanitize_xml_content (independent port, validates QuickTranslate patterns)
- LocaNext `server/tools/ldm/file_handlers/xml_handler.py` -- current stdlib ET implementation to replace
- LocaNext `server/tools/ldm/services/mapdata_service.py` -- scaffolded service with empty indexes + convert_to_wsl_path
- LocaNext `server/tools/ldm/services/glossary_service.py` -- already uses lxml, has extract methods, needs wiring
- LocaNext `server/tools/ldm/services/context_service.py` -- orchestrator combining glossary + mapdata lookups

### Secondary (MEDIUM confidence)
- LocaNext `server/repositories/sqlite/folder_repo.py` -- negative ID creation pattern for FIX-03
- LocaNext `locaNext/src/lib/components/ldm/TMExplorerTree.svelte` -- TM tree fetching for FIX-01

### Tertiary (LOW confidence)
- FIX-01, FIX-02 exact root causes -- need reproduction during planning/execution

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already installed, patterns verified in source code
- Architecture: HIGH -- existing scaffolds are well-designed, integration points are clear
- Pitfalls: HIGH -- all sourced from production NewScripts code and existing LocaNext codebase
- Bug fixes: MEDIUM -- root causes identified from code inspection but not yet reproduced

**Research date:** 2026-03-15
**Valid until:** 2026-04-15 (stable domain, no fast-moving dependencies)
