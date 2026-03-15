# Architecture Patterns

**Domain:** Localization management platform (CAT Tool + Game Dev) -- v2.0 integration
**Researched:** 2026-03-15
**Confidence:** HIGH (based on existing codebase inspection + battle-tested NewScripts patterns)

## Current Architecture (v1.0 Baseline)

```
Electron Shell
  |
  +-- Svelte 5 Frontend (Carbon Components)
  |     +-- VirtualGrid (translation editor, 4048 lines)
  |     +-- TMExplorerTree / TMManager
  |     +-- ImageTab / AudioTab / ContextTab
  |     +-- QAFooter (persistent panel)
  |
  +-- FastAPI Backend (embedded Python)
        +-- Repository Layer (9 interfaces, PG + SQLite)
        +-- Services Layer (singleton pattern)
        |     +-- MapDataService (scaffolded -- empty indexes)
        |     +-- GlossaryService (scaffolded -- AC automaton ready)
        |     +-- ContextService (orchestrates glossary + mapdata)
        |     +-- TMService, IndexingService, CategoryMapper
        +-- Routes Layer (tools/ldm/routes/)
        +-- FAISS + Model2Vec (semantic search)
        +-- WebSocket (real-time sync, online mode)
```

**Key insight:** v1.0 built the scaffolding correctly. Services exist as singletons with `get_*_service()` factories. Routes are clean, using dependency injection. The v2.0 work is about **filling the scaffolds with real data pipelines**, not restructuring.

## Recommended Architecture (v2.0 Additions)

### High-Level Integration Map

```
                     EXISTING (keep)                    NEW (v2.0)
                  +-------------------+            +-------------------+
  Frontend        | VirtualGrid       |            | Column configs    |
                  | (4048 lines)      |----+------>| per file type     |
                  +-------------------+    |       | (Translator vs    |
                                           |       |  Game Dev mode)   |
                                           |       +-------------------+
                                           |
                  +-------------------+    |       +-------------------+
  File Detection  | FilesPage.svelte  |----+------>| FileTypeDetector  |
                  | ExplorerGrid      |            | (LocStr scan)     |
                  +-------------------+            +-------------------+

                  +-------------------+            +-------------------+
  Services        | MapDataService    |<-----------| XMLParsingEngine  |
  (fill scaffolds)| (empty indexes)   |  populate  | (lxml + sanitizer)|
                  +-------------------+            +-------------------+
                  | GlossaryService   |<-----------| StaticInfoParser  |
                  | (AC automaton)    |  populate  | (KnowledgeInfo,   |
                  +-------------------+            |  CharacterInfo)   |
                  | ContextService    |            +-------------------+
                  | (orchestrator)    |
                  +-------------------+
                                                   +-------------------+
  New Services                                     | MergeEngine       |
                                                   |  +TranslatorMerge |
                                                   |  +GameDevMerge    |
                                                   +-------------------+
                                                   | ExportService     |
                                                   |  (XML/Excel/Text) |
                                                   +-------------------+
                                                   | MediaConverter    |
                                                   |  (DDS->PNG,       |
                                                   |   WEM->WAV)       |
                                                   +-------------------+
                                                   | AISummaryService  |
                                                   |  (Ollama/Qwen3)   |
                                                   +-------------------+
```

### Component Boundaries

| Component | Responsibility | Communicates With | New/Modified |
|-----------|---------------|-------------------|--------------|
| **FileTypeDetector** | Scan XML for LocStr nodes, classify as Translator vs Game Dev | FilesPage, VirtualGrid, Routes | NEW service |
| **XMLParsingEngine** | Sanitize + parse XML using QuickTranslate patterns (lxml + recovery) | MapDataService, GlossaryService, MergeEngine | NEW service |
| **TranslatorMergeEngine** | StringID match, StrOrigin match, fuzzy match + postprocess | ExportService, VirtualGrid | NEW service |
| **GameDevMergeEngine** | Position-based node-level merge (add/remove/modify at any depth) | ExportService, VirtualGrid | NEW service |
| **ExportService** | Write XML (br-tag safe), Excel (xlsxwriter), plain text | TranslatorMerge, GameDevMerge, Routes | NEW service |
| **MediaConverter** | DDS to PNG (Pillow+pillow-dds), WEM to WAV (vgmstream-cli) | MapDataService, ImageTab, AudioTab | NEW service |
| **AISummaryService** | Qwen3-4B via Ollama, structured JSON, per-StringID cache | ContextService, ContextTab | NEW service |
| **MapDataService** | StrKey-to-image/audio O(1) lookups | ContextService, Routes | MODIFIED (fill indexes) |
| **GlossaryService** | AC automaton entity detection | ContextService, Routes | MODIFIED (fill indexes) |
| **VirtualGrid** | Translation editor with virtual scrolling | Routes, all services via API | MODIFIED (column configs) |
| **Repository Layer** | DB abstraction (9 interfaces, PG + SQLite) | All routes | UNCHANGED |

## New Components: Detailed Design

### 1. FileTypeDetector (server/tools/ldm/services/filetype_detector.py)

**Pattern:** Stateless utility -- no singleton needed.

```python
from lxml import etree
from enum import Enum

class FileType(Enum):
    TRANSLATOR = "translator"    # Has LocStr nodes
    GAMEDEV = "gamedev"          # XML without LocStr (staticinfo, etc.)
    UNKNOWN = "unknown"          # Non-XML or empty

def detect_file_type(xml_content: str) -> FileType:
    """Scan first 50 LocStr-tagged elements. If found -> TRANSLATOR, else -> GAMEDEV."""
    # Use raw bytes regex for speed (same pattern as QuickTranslate's _quick_scan_stringids)
    if re.search(rb'<(?:LocStr|locstr|LOCSTR)', xml_content.encode('utf-8', errors='replace')):
        return FileType.TRANSLATOR
    # Check if valid XML at all
    try:
        etree.fromstring(xml_content.encode())
        return FileType.GAMEDEV
    except Exception:
        return FileType.UNKNOWN
```

**Integration point:** Called when file is opened. Result stored in file metadata and sent to frontend via API response. Frontend uses it to switch column configs.

### 2. XMLParsingEngine (server/tools/ldm/services/xml_parsing.py)

**Pattern:** Singleton service, wraps QuickTranslate's battle-tested parsing.

This is NOT a new invention -- it is a **direct port** of these existing modules:
- `QuickTranslate/core/xml_parser.py` -- sanitizer, entity fix, tag repair
- `QuickTranslate/core/xml_io.py` -- LocStr element iteration, attribute extraction
- `MapDataGenerator/core/xml_parser.py` -- generic XML iteration
- `MapDataGenerator/core/linkage.py` -- KnowledgeInfo chain resolution

```python
class XMLParsingEngine:
    """Centralized XML parsing with sanitization and recovery."""

    def parse_locstr_file(self, path: Path) -> List[LocStrRow]:
        """Parse translator file: extract LocStr elements with all attributes."""
        # Port from QuickTranslate/core/xml_io.py::parse_corrections_from_xml
        # + xml_parser.py sanitization pipeline

    def parse_staticinfo_file(self, path: Path) -> List[StaticInfoNode]:
        """Parse game dev file: extract node tree with attributes."""
        # Port from MapDataGenerator/core/xml_parser.py

    def build_knowledge_chain(self, knowledge_folder: Path) -> Dict[str, KnowledgeLookup]:
        """Build StrKey -> KnowledgeLookup from KnowledgeInfo XMLs."""
        # Port from MapDataGenerator/core/linkage.py::KnowledgeLookup

    def sanitize(self, raw_xml: str) -> str:
        """Fix bad entities, repair tags, preprocess newlines."""
        # Port from QuickTranslate/core/xml_parser.py
```

**Critical:** Use lxml with `recover=True` parser. Never stdlib ElementTree for game data (too fragile).

### 3. MergeEngine Architecture

Two distinct engines, sharing a common result type.

```python
class MergeResult:
    """Unified merge result."""
    matched: int
    unmatched: int
    changes: List[MergeChange]  # (string_id, field, old_value, new_value)

class TranslatorMergeEngine:
    """Port of QuickTranslate's _fast_folder_merge logic."""

    def merge_by_string_id(self, source, target) -> MergeResult:
        """Exact StringID match -- O(n) via dict lookup."""

    def merge_by_str_origin(self, source, target) -> MergeResult:
        """Source text match when StringIDs differ."""

    def merge_fuzzy(self, source, target, threshold=0.7) -> MergeResult:
        """Model2Vec similarity above threshold."""

    def postprocess(self, rows) -> PostprocessResult:
        """8-step CJK-safe cleanup pipeline."""
        # Direct port from QuickTranslate/core/postprocess.py

class GameDevMergeEngine:
    """Position-aware XML node merge (NOT string-match based)."""

    def merge_at_node_level(self, source_tree, target_tree) -> MergeResult:
        """Add/remove/modify nodes by XPath position."""

    def merge_at_attribute_level(self, source_node, target_node) -> MergeResult:
        """Diff attributes within matching nodes."""

    def merge_children(self, source_parent, target_parent, depth=0) -> MergeResult:
        """Recursive children merge preserving document order."""
```

### 4. ExportService (server/tools/ldm/services/export_service.py)

```python
class ExportService:
    """Handles all export formats."""

    def export_xml(self, rows, output_path: Path) -> Path:
        """Write XML with <br/> preservation. Uses lxml raw_attribs pattern."""
        # Port from QuickTranslate's xml_transfer.py::_write_target_xml

    def export_excel(self, rows, output_path: Path, columns: List[str]) -> Path:
        """Write Excel via xlsxwriter (NEVER openpyxl for writing)."""

    def export_text(self, rows, output_path: Path) -> Path:
        """Write tab-delimited text (StringID + source + translation)."""
```

### 5. MediaConverter (server/tools/ldm/services/media_converter.py)

```python
class MediaConverter:
    """DDS/WEM conversion for browser display."""

    def dds_to_png(self, dds_path: Path, output_path: Path,
                   max_size: tuple = (256, 256)) -> Optional[Path]:
        """Convert DDS texture to PNG thumbnail."""
        # Port from MapDataGenerator/core/dds_handler.py::DDSHandler
        # Uses Pillow + pillow-dds plugin
        # LRU cache for repeated lookups

    def wem_to_wav(self, wem_path: Path, output_path: Path) -> Optional[Path]:
        """Convert WEM audio to WAV via vgmstream-cli."""
        # subprocess call to vgmstream-cli
        # Fallback: return None (UI shows "Audio unavailable" badge)
```

**Integration:** MapDataService calls MediaConverter when populating indexes. Converted files cached in temp directory. API serves them as static files.

### 6. AISummaryService (server/tools/ldm/services/ai_summary.py)

```python
class AISummaryService:
    """Qwen3 via Ollama for contextual summaries."""

    def __init__(self):
        self._cache: Dict[str, str] = {}  # string_id -> summary
        self._ollama_url = "http://localhost:11434"
        self._model = "qwen3:4b"  # or 8b

    async def get_summary(self, string_id, context) -> Optional[str]:
        """Generate 2-line contextual summary. Cached per string_id."""
        if string_id in self._cache:
            return self._cache[string_id]
        prompt = self._build_prompt(context)
        response = await self._call_ollama(prompt)
        self._cache[string_id] = response
        return response

    def is_available(self) -> bool:
        """Check if Ollama is running and model is loaded."""
```

**Integration:** ContextService calls AISummaryService. ContextTab shows summary or "AI unavailable" badge.

## Data Flow: End-to-End

### File Open Flow (Modified)

```
User clicks file in ExplorerGrid
  |
  v
[1] API: GET /api/ldm/files/{id}/content
  |
  v
[2] FileTypeDetector.detect(content)  --> FileType.TRANSLATOR or .GAMEDEV
  |
  v
[3] Response includes file_type field
  |
  v
[4] Frontend: VirtualGrid receives file_type
  |
  v
[5] VirtualGrid.getVisibleColumns() switches column config:
     TRANSLATOR: [#, StringID, Source(KR), Target, Reference]
     GAMEDEV:    [#, NodeName, Attributes, Values, Children]
```

### XML Parsing + Index Population Flow (New)

```
MapDataService.initialize(branch, drive)
  |
  v
XMLParsingEngine.build_knowledge_chain(knowledge_folder)
  --> Dict[strkey, KnowledgeLookup]
  |
  v
For each KnowledgeLookup:
  MediaConverter.dds_to_png(lookup.ui_texture_name)
  --> MapDataService._strkey_to_image[strkey] = ImageContext(...)
  |
  v
GlossaryService.build_from_entity_names(extracted_entities)
  --> AC automaton populated
  |
  v
ContextService now has real data for:
  - Entity detection (GlossaryService)
  - Image/audio lookups (MapDataService)
  - AI summaries (AISummaryService)
```

### Merge Flow (New)

```
User initiates merge (Translator mode)
  |
  v
[1] API: POST /api/ldm/merge/translator
     body: { source_file_id, target_file_id, match_types: [...] }
  |
  v
[2] XMLParsingEngine.parse_locstr_file(source) --> source_rows
    XMLParsingEngine.parse_locstr_file(target) --> target_rows
  |
  v
[3] TranslatorMergeEngine.merge_by_string_id(source, target)
    Then: .merge_by_str_origin(unmatched)
    Then: .merge_fuzzy(still_unmatched, threshold=0.7)
  |
  v
[4] TranslatorMergeEngine.postprocess(merged_rows)
  |
  v
[5] ExportService.export_xml(merged_rows, output_path)
    or: ExportService.export_excel(merged_rows, output_path)
  |
  v
[6] Response: MergeResult { matched, unmatched, changes[] }
```

### AI Summary Flow (New)

```
User selects row in VirtualGrid
  |
  v
[1] RightPanel/ContextTab: GET /api/ldm/context/{string_id}?source_text=...
  |
  v
[2] ContextService.resolve_context_for_row(string_id, source_text)
     --> entities, image, audio (existing flow)
  |
  v
[3] AISummaryService.get_summary(string_id, context)
     --> Ollama call (or cache hit)
  |
  v
[4] Response includes ai_summary field
  |
  v
[5] ContextTab renders summary or "AI unavailable" badge
```

## Patterns to Follow

### Pattern 1: Singleton Service with Lazy Init (Existing Pattern)

All v1.0 services use this pattern. v2.0 services MUST follow it.

```python
_service_instance: Optional[MyService] = None

def get_my_service() -> MyService:
    global _service_instance
    if _service_instance is None:
        _service_instance = MyService()
    return _service_instance
```

**When:** Every new service (XMLParsingEngine, MergeEngine, ExportService, AISummaryService).
**Why:** Consistent with MapDataService, GlossaryService, ContextService. DI via `Depends()` in routes.

### Pattern 2: Port NewScripts Logic, Don't Reinvent

The NewScripts codebase has battle-tested XML handling. Port directly.

| v2.0 Feature | Source Code to Port | Key Module |
|---|---|---|
| XML sanitization | `QuickTranslate/core/xml_parser.py` | `_fix_bad_entities`, `_repair_tag_stack` |
| LocStr parsing | `QuickTranslate/core/xml_io.py` | `parse_corrections_from_xml` |
| Transfer/merge | `QuickTranslate/core/xml_transfer.py` | `_fast_folder_merge` |
| Postprocess | `QuickTranslate/core/postprocess.py` | `run_all_postprocess` (8 steps) |
| Knowledge chains | `MapDataGenerator/core/linkage.py` | `KnowledgeLookup`, `DataEntry` |
| DDS conversion | `MapDataGenerator/core/dds_handler.py` | `DDSHandler.load_dds` |
| Attribute constants | `QuickTranslate/core/xml_parser.py` | `STRINGID_ATTRS`, `LOCSTR_TAGS`, etc. |

**When:** Any XML, merge, or media feature.
**Why:** These patterns handle edge cases (malformed XML, CJK encoding, formula injection, br-tag variants) that would take weeks to rediscover.

### Pattern 3: Column Config Objects for Dual UI

Extend `allColumns` in VirtualGrid with mode-specific configs rather than creating separate grids.

```javascript
// VirtualGrid.svelte
const translatorColumns = {
  row_num: { key: "row_num", label: "#", width: 60 },
  string_id: { key: "string_id", label: "StringID", width: 150 },
  source: { key: "source", label: "Source (KR)", width: 350, always: true },
  target: { key: "target", label: "Target", width: 350, always: true },
  reference: { key: "reference", label: "Reference", width: 300 },
};

const gameDevColumns = {
  row_num: { key: "row_num", label: "#", width: 60 },
  node_name: { key: "node_name", label: "Node", width: 200, always: true },
  attributes: { key: "attributes", label: "Attributes", width: 300, always: true },
  values: { key: "values", label: "Values", width: 300, always: true },
  children_count: { key: "children_count", label: "Children", width: 100 },
};

let activeColumns = $derived(
  fileType === 'gamedev' ? gameDevColumns : translatorColumns
);
```

**When:** Dual UI switching.
**Why:** Reuses 4000+ lines of VirtualGrid infrastructure (virtual scrolling, resize, editing, search). Building a second grid would be architectural debt.

### Pattern 4: Async Ollama with Timeout + Fallback

```python
async def _call_ollama(self, prompt: str, timeout: float = 10.0) -> Optional[str]:
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{self._ollama_url}/api/generate",
                json={"model": self._model, "prompt": prompt, "stream": False}
            )
            return response.json().get("response", "")
    except (httpx.TimeoutException, httpx.ConnectError):
        logger.warning("[AI] Ollama unavailable")
        return None
```

**When:** AI summary integration.
**Why:** Ollama may not be running. Never block UI. Show badge instead.

## Anti-Patterns to Avoid

### Anti-Pattern 1: Separate Grid Components for Each Mode

**What:** Creating `TranslatorGrid.svelte` and `GameDevGrid.svelte` as separate components.
**Why bad:** VirtualGrid is 4048 lines of complex virtual scrolling, resize handling, editing, search, WebSocket sync, TM integration, QA integration. Duplicating even 20% would create maintenance hell.
**Instead:** Single VirtualGrid with column config objects selected by file type. The grid renders whatever columns it receives.

### Anti-Pattern 2: Parsing XML in Routes

**What:** Putting XML parsing logic directly in FastAPI route handlers.
**Why bad:** Routes should be thin (5-10 lines). XML parsing has error handling, sanitization, recovery -- it belongs in services.
**Instead:** Route calls service, service calls XMLParsingEngine.

### Anti-Pattern 3: Using stdlib ElementTree for Game Data

**What:** Using `xml.etree.ElementTree` instead of lxml.
**Why bad:** Game XML files are frequently malformed (bad entities, unclosed tags, encoding issues). stdlib ET throws on first error. lxml's `recover=True` handles gracefully.
**Instead:** Always lxml with recovery parser. QuickTranslate already has the fallback pattern if lxml unavailable.

### Anti-Pattern 4: Building Merge Logic from Scratch

**What:** Writing new string matching, postprocessing, or transfer logic.
**Why bad:** QuickTranslate's merge pipeline handles dozens of edge cases: formula injection, Korean detection, br-tag normalization, invisible chars, CJK ellipsis, double-escaped entities. Missing any one of them means data corruption.
**Instead:** Port `xml_transfer.py` and `postprocess.py` functions directly. Adapt interfaces, keep logic.

### Anti-Pattern 5: Synchronous Ollama Calls

**What:** Blocking the FastAPI event loop waiting for Qwen3 response.
**Why bad:** Even at 117 tok/s, a summary takes 1-3 seconds. Blocking kills concurrent requests.
**Instead:** Use `httpx.AsyncClient` with timeout. Cache results per StringID.

## Component File Layout (New Files)

```
server/tools/ldm/
  services/
    # EXISTING (modify)
    mapdata_service.py        # Fill indexes with real XML data
    glossary_service.py       # Build AC from real staticinfo
    context_service.py        # Add AI summary orchestration

    # NEW
    filetype_detector.py      # FileType enum + detect_file_type()
    xml_parsing.py            # XMLParsingEngine (ports QuickTranslate patterns)
    merge_translator.py       # TranslatorMergeEngine
    merge_gamedev.py          # GameDevMergeEngine
    export_service.py         # ExportService (XML/Excel/Text)
    media_converter.py        # DDS->PNG, WEM->WAV
    ai_summary.py             # AISummaryService (Ollama/Qwen3)

  routes/
    # EXISTING (modify)
    files.py                  # Add file_type to response
    context.py                # Add ai_summary field
    mapdata.py                # Wire real initialization

    # NEW
    merge.py                  # POST /merge/translator, /merge/gamedev
    export.py                 # POST /export/{format}

locaNext/src/lib/
  components/ldm/
    # EXISTING (modify)
    VirtualGrid.svelte        # Add column config switching
    ContextTab.svelte         # Add AI summary display
    ImageTab.svelte           # Wire real DDS->PNG URLs
    AudioTab.svelte           # Wire real WEM->WAV playback

  stores/
    # EXISTING (modify)
    ldm.js                    # Add fileType state

  utils/
    # NEW (if needed)
    columnConfigs.js          # Translator vs GameDev column definitions
```

## Scalability Considerations

| Concern | Current (v2.0) | At 10K files | At 100K strings |
|---------|----------------|--------------|-----------------|
| XML parsing speed | lxml, ~1000 files/sec | Fine (lxml is C-based) | Fine |
| Knowledge index | In-memory dict | ~50MB RAM for 100K entries | Fine |
| DDS conversion | On-demand + LRU cache | Pre-convert on init | Background job queue |
| AI summaries | Per-request + cache | Cache in SQLite | Background pre-generation |
| Merge operations | In-memory | Streaming for large files | Chunked processing |
| AC automaton | ~100K terms fine | ~500K terms fine | Fine (ahocorasick is C) |

## Build Order (Dependency-Driven)

The integration dependencies dictate this build order:

```
Phase 1: XML Parsing Foundation
  XMLParsingEngine + FileTypeDetector
  (everything else depends on being able to parse XML)

Phase 2: Dual UI + Media Pipeline
  VirtualGrid column switching + MediaConverter
  (visible progress, parallelize with Phase 3)

Phase 3: Wire Existing Services
  MapDataService (fill indexes) + GlossaryService (fill AC)
  (depends on XMLParsingEngine from Phase 1)

Phase 4: Merge Engines
  TranslatorMergeEngine + GameDevMergeEngine
  (depends on XMLParsingEngine, complex logic, needs testing)

Phase 5: Export
  ExportService (XML/Excel/Text)
  (depends on merge engines producing data)

Phase 6: AI Summaries
  AISummaryService + ContextTab integration
  (independent of merge, but lowest priority)

Phase 7: Bug Fixes + CLI + E2E
  FIX-01/02/03, CLI commands, round-trip tests
  (can start earlier for bug fixes)
```

**Rationale:** XML parsing is the foundation -- merge, export, index population all need it. Dual UI is high-visibility (demo value). AI summaries are independent and lowest risk, so they go last. Bug fixes can be sprinkled throughout.

## Sources

- Inspected: `server/tools/ldm/services/mapdata_service.py` (singleton pattern, scaffolded indexes)
- Inspected: `server/tools/ldm/services/glossary_service.py` (AC automaton, entity detection)
- Inspected: `server/tools/ldm/services/context_service.py` (orchestrator pattern)
- Inspected: `server/tools/ldm/routes/mapdata.py`, `context.py` (clean route pattern)
- Inspected: `locaNext/src/lib/components/ldm/VirtualGrid.svelte` (column config, 4048 lines)
- Inspected: `QuickTranslate/core/xml_parser.py` (sanitizer, attribute constants)
- Inspected: `QuickTranslate/core/xml_io.py` (LocStr parsing)
- Inspected: `QuickTranslate/core/xml_transfer.py` (merge logic, postprocess integration)
- Inspected: `QuickTranslate/core/postprocess.py` (8-step cleanup pipeline)
- Inspected: `MapDataGenerator/core/linkage.py` (KnowledgeLookup, DataEntry)
- Inspected: `MapDataGenerator/core/dds_handler.py` (DDS conversion via Pillow)
- Inspected: `docs/architecture/ARCHITECTURE_SUMMARY.md` (repository pattern, 3-mode detection)
- Inspected: `.planning/PROJECT.md` + `.planning/REQUIREMENTS.md` (40 requirements)
