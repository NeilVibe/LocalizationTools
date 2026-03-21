# Architecture Patterns

**Domain:** Offline Production Bundle + Full Codex Expansion for LocaNext v5.0
**Researched:** 2026-03-21
**Confidence:** HIGH (based on deep codebase analysis of all relevant server modules)

## Current Architecture (As-Is)

```
Frontend (Svelte 5 Runes)
  CodexPage.svelte ─── CodexCard / CodexEntityDetail / CodexSearchBar / CodexRelationshipGraph
  WorldMapPage.svelte ── MapCanvas / MapTooltip / MapDetailPanel / MapIcons
  GameDevGrid.svelte ── (tree + rows endpoints)
  FilesPage.svelte ── VirtualGrid (translator mode)

API Routes (FastAPI)
  routes/codex.py ─── /codex/search, /codex/entity, /codex/list, /codex/types, /codex/relationships
  routes/gamedata.py ── /gamedata/browse, /gamedata/rows, /gamedata/tree, /gamedata/context
  routes/mapdata.py ── /mapdata/thumbnail, /mapdata/audio/stream, /mapdata/configure
  routes/worldmap.py ── /worldmap/nodes, /worldmap/routes

Services (Stateful Singletons)
  CodexService ──── XML scan + registry + FAISS index + cross-ref resolution
  MapDataService ── Perforce path templates + knowledge table + DDS index + image chains
  WorldMapService ── FactionNode positions + waypoint routes + Codex enrichment
  MediaConverter ── DDS->PNG (Pillow) + WEM->WAV (vgmstream-cli)
  GameDataTreeService ── lxml tree walking (XML-nested + reference-based hierarchies)
  GameDataContextService ── cross-refs + related entities + TM suggestions + media + AI summary

Shared Infrastructure
  EmbeddingEngine ── Model2Vec (default, 256-dim) | Qwen (opt-in, 1024-dim)
  FAISSManager ── HNSW index build/search
  XMLParsingEngine ── 5-step sanitizer + strict/recover parsing + language tables

Repository Layer (Factory Pattern - ARCH-001)
  Factory ── 3-mode detection: Offline (header) | Server-local SQLite | PostgreSQL
  Interfaces ── 9 abstract repos: TM, File, Row, Project, Folder, Platform, QA, Trash, Capability
  SQLite repos ── SchemaMode.OFFLINE (offline_* tables) | SchemaMode.SERVER (ldm_* tables)
  PostgreSQL repos ── Full implementations with permissions
  RoutingRowRepo ── Negative ID routing for local Electron data
```

## Critical Architectural Observations

### 1. GameData is File-Based, NOT DB-Synced

**This is the most important finding.** GameData (StaticInfo XML, Codex entities, world map nodes) operates entirely through file-system scanning. None of it touches the Repository layer.

Evidence:
- `CodexService.__init__` takes a `base_dir: Path` and scans XML files with `rglob("*.xml")`
- `GameDataTreeService` parses XML directly from filesystem paths
- `gamedata/rows` endpoint reads XML with `etree.parse(str(resolved))` -- no DB
- `MapDataService` builds indexes from Perforce path templates + filesystem scanning
- `WorldMapService` parses FactionNode XML from filesystem

**Implication for offline bundle:** GameData works offline automatically because it reads files, not databases. The Factory/Abstraction/Repo pattern is irrelevant for Codex/GameData. The only concern is ensuring the XML files are present in the bundle.

**Implication for online collaboration:** Multiple game devs CANNOT collaborate on gamedata online through the current architecture. GameData edits (`gamedata/save`) write directly to XML files on the server's filesystem. There is no DB-backed gamedata, no change tracking, no conflict resolution. This is fine for v5.0 (offline-first), but important to document.

### 2. The Repo Layer Only Covers LDM (Translation Data)

The Factory/Abstraction/Repo pattern covers:
- Platforms, Projects, Folders, Files, Rows (translation content)
- Translation Memories, QA Results, Trash

It does NOT cover:
- Codex entities (in-memory registry from XML scan)
- GameData tree/browse/edit (direct filesystem)
- World map nodes (in-memory from XML scan)
- MapData indexes (in-memory from filesystem scan)
- AI services (Ollama, FAISS, embeddings)

### 3. Service Initialization Pattern = Singleton + Lazy Init

All major services follow this pattern:
```python
_service_instance: Optional[ServiceClass] = None

def get_service() -> ServiceClass:
    global _service_instance
    if _service_instance is None:
        _service_instance = ServiceClass()
    return _service_instance
```

Services self-initialize on first request via `if not self._initialized: self.initialize()`.

### 4. Codex Entity Registry is Flat

Current `CodexService._registry` is a flat dict: `{entity_type: {strkey: CodexEntity}}`. Six types: character, item, skill, gimmick, knowledge, region. There is NO type-specific behavior -- all entity types share the same `CodexEntity` Pydantic model with generic `attributes: Dict[str, str]`.

### 5. Perforce Path Resolution is Hardcoded Templates

`MapDataService` uses `PATH_TEMPLATES` dict with Windows paths like `F:\perforce\cd\mainline\resource\...`. The `generate_paths(drive, branch)` function substitutes drive letter and branch name. `convert_to_wsl_path()` converts Windows paths to WSL.

---

## Recommended Architecture (To-Be)

### Component Boundaries

| Component | Responsibility | Communicates With | New/Modified |
|-----------|---------------|-------------------|-------------|
| `CodexService` | Entity registry + FAISS search | XMLParsingEngine, EmbeddingEngine | **MODIFIED** -- enrichment hooks |
| `AudioCodexService` | Audio file discovery + StrKey mapping | PerforcePathService, MediaConverter | **NEW** |
| `ItemCodexService` | Item enrichment + image linkage | CodexService, MapDataService | **NEW** |
| `CharacterCodexService` | Character enrichment + portraits | CodexService, MapDataService | **NEW** |
| `RegionCodexService` | Region enrichment + WorldPosition | CodexService, WorldMapService | **NEW** |
| `PerforcePathService` | Unified path resolution (all types) | Extracted from MapDataService | **NEW** |
| `AICapabilityService` | Runtime AI engine detection | EmbeddingEngine, Ollama, TTS | **NEW** |

### Data Flow: Offline Bundle

```
Offline Bundle (Electron app, no server)
  SQLite DB ── translation data (files, rows, TM) via Repo layer
  XML Files ── gamedata/codex/worldmap via Service singletons
  Model2Vec ── embeddings for search (bundled, ~128MB)
  vgmstream-cli ── WEM->WAV conversion (bundled binary)
  NO Qwen/Ollama ── AI features gracefully degraded
  NO PostgreSQL ── offline_* tables via SchemaMode.OFFLINE
  NO TTS ── voice generation unavailable
```

### Data Flow: Type-Specific Codex UIs

```
User clicks "Audio Codex" tab
  Frontend: AudioCodexPage.svelte
    GET /api/ldm/codex/audio/list?branch=mainline&drive=F&language=Korean
  Backend: AudioCodexService
    PerforcePathService.resolve("audio_folder", branch, drive, language)
    Scan resolved path for .wem files
    Cross-ref with CodexService registry for entity metadata
    Return AudioCodexEntry[] with stream URLs
  Playback: GET /api/ldm/mapdata/audio/stream/{string_id}
    MediaConverter.convert_wem_to_wav() (existing)
```

### File Organization

```
server/tools/ldm/services/
  codex_service.py          ── (existing) core registry + FAISS
  codex_audio_service.py    ── NEW: audio discovery + StrKey mapping
  codex_item_service.py     ── NEW: item enrichment + image linkage
  codex_character_service.py ── NEW: character enrichment + portraits
  codex_region_service.py   ── NEW: region enrichment + WorldPosition
  perforce_path_service.py  ── NEW: extracted from MapDataService
  ai_capability_service.py  ── NEW: runtime AI detection
  mapdata_service.py        ── (existing, MODIFIED) delegate path resolution
  media_converter.py        ── (existing, unchanged)
```

---

## Patterns to Follow

### Pattern 1: Type-Specific Codex Service (Composition)

Each Codex type gets its own service that COMPOSES the core CodexService rather than extending it.

```python
class AudioCodexService:
    """Audio-specific Codex -- discovery, playback, StrKey mapping."""

    def __init__(self):
        self._audio_entries: Dict[str, AudioCodexEntry] = {}
        self._initialized = False

    def initialize(self, branch: str, drive: str, language: str) -> None:
        path_service = get_perforce_path_service()
        audio_path = path_service.resolve("audio_folder", branch, drive, language=language)
        codex = _get_codex_service()
        # Scan .wem files, match StrKey patterns, cross-ref with CodexService

    def list_entries(self, offset: int = 0, limit: int = 50) -> AudioCodexListResponse:
        ...
```

### Pattern 2: Perforce Path Service (Extracted)

Extract `PATH_TEMPLATES`, `generate_paths()`, `convert_to_wsl_path()` into dedicated service.

```python
class PerforcePathService:
    PATH_TEMPLATES = {
        'audio_folder_en': r"F:\perforce\cd\{branch}\resource\sound\windows\English(US)",
        'texture_folder': r"F:\perforce\common\{branch}\commonresource\ui\texture\image",
        'character_folder': r"F:\perforce\cd\{branch}\resource\GameData\StaticInfo\characterinfo",
        # ... all from MapDataGenerator config
    }

    def resolve(self, key: str, branch: str, drive: str, **kwargs) -> Path:
        template = self.PATH_TEMPLATES[key]
        path = template.replace("{branch}", branch)
        path = f"{drive}:{path[2:]}"
        return Path(convert_to_wsl_path(path))
```

### Pattern 3: AI Graceful Degradation

```python
class AICapabilityService:
    def get_capabilities(self) -> Dict[str, bool]:
        return {
            "embeddings": self._check_model2vec(),
            "semantic_search": self._check_faiss(),
            "ai_summary": self._check_ollama(),
            "tts": self._check_tts(),
            "image_gen": self._check_gemini(),
        }
```

Frontend checks capabilities on load, hides/badges unavailable features.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Adding GameData to the Repository Layer

**What:** Creating `CodexRepository` with SQLite/PostgreSQL to store Codex entities in DB.
**Why bad:** GameData is file-sourced. DB creates sync problem (files change, DB stale). Every service reads XML, not DB.
**Instead:** Keep Codex services as filesystem scanners with in-memory registries.

### Anti-Pattern 2: One Giant CodexService for All Types

**What:** Adding Audio/Item/Character/Region methods to existing `CodexService` (already 565 lines).
**Why bad:** Each type has different data sources, media, cross-refs. God-class.
**Instead:** Composition -- separate service per type using core `CodexService` registry.

### Anti-Pattern 3: Duplicating Path Resolution

**What:** Each Codex service independently implementing Perforce path templates.
**Why bad:** Paths diverge when templates change.
**Instead:** Extract into `PerforcePathService`.

### Anti-Pattern 4: Making AI Features Mandatory

**What:** Codex UIs that crash when Ollama/Qwen is unavailable.
**Why bad:** Offline bundle runs without Qwen. Core value is browsing, not AI.
**Instead:** Check `AICapabilityService`, gracefully degrade.

### Anti-Pattern 5: Putting QACompiler Logic in Routes

**What:** Generator logic (join keys, cross-file refs, StringIdConsumer) in route handlers.
**Why bad:** Routes should be thin. Generator logic is complex.
**Instead:** Port to dedicated service classes.

---

## Integration Points Summary

### New Components (10)

| Component | Type | Dependencies |
|-----------|------|-------------|
| `PerforcePathService` | Service | None (pure logic, extracted from MapDataService) |
| `AICapabilityService` | Service | EmbeddingEngine, httpx |
| `AudioCodexService` | Service | PerforcePathService, CodexService, MediaConverter |
| `ItemCodexService` | Service | CodexService, MapDataService |
| `CharacterCodexService` | Service | CodexService, MapDataService |
| `RegionCodexService` | Service | CodexService, WorldMapService |
| `AudioCodexPage.svelte` | Page | AudioCodexService API |
| `ItemCodexPage.svelte` | Page | ItemCodexService API |
| `CharacterCodexPage.svelte` | Page | CharacterCodexService API |
| `RegionCodexPage.svelte` | Page | RegionCodexService API |

### Modified Components (4)

| Component | Change | Reason |
|-----------|--------|--------|
| `MapDataService` | Extract path templates | Reuse in all Codex services |
| `CodexEntity` schema | Add optional type-specific fields | audio_url, world_position |
| `config.py` | Add `LIGHT_BUILD` env var | Explicit mode toggle |
| `codex.py` route | Add sub-routes per type | `/codex/audio/list` etc. |

### Unchanged Components (8)

Repository layer (all 9 repos), SyncService, XMLParsingEngine, MediaConverter, FAISSManager, GameDataTreeService -- none need changes for v5.0.

---

## Build Order (Dependency-Driven)

```
Phase 1: Foundation (no new UI)
  1a. Extract PerforcePathService from MapDataService
  1b. Create AICapabilityService + /api/ldm/capabilities endpoint
  1c. Add LIGHT_BUILD config + bundle manifest

Phase 2: Audio Codex (highest demo value, existing MediaConverter)
  2a. AudioCodexService (PerforcePathService + WEM scanning)
  2b. AudioCodexPage.svelte (browse, search, play)
  2c. StringID -> Audio mapping

Phase 3: Item + Character Codex (QACompiler logic)
  3a. Port QACompiler Item generator -> ItemCodexService
  3b. ItemCodexPage.svelte
  3c. Port QACompiler Character generator -> CharacterCodexService
  3d. CharacterCodexPage.svelte

Phase 4: Region Codex + Map Enhancement
  4a. Port QACompiler Region generator -> RegionCodexService
  4b. RegionCodexPage.svelte with mini-map
  4c. WorldMapPage integration

Phase 5: AI Degradation + Bundle Polish
  5a. Wrap all AI calls with capability checks
  5b. UI degradation (hide/badge unavailable features)
  5c. Test full offline flow

Phase 6: Offline Bundle Packaging
  6a. PyInstaller/Electron packaging (Model2Vec + vgmstream-cli)
  6b. Exclude torch/sentence-transformers/qwen-tts
  6c. E2E validation on disconnected machine
```

## Sources

- Direct codebase analysis (HIGH confidence)
- `server/repositories/factory.py` -- ARCH-001 3-mode detection
- `server/tools/ldm/services/codex_service.py` -- entity registry
- `server/tools/ldm/services/mapdata_service.py` -- Perforce paths
- `server/tools/ldm/services/xml_parsing.py` -- XMLParsingEngine
- `server/tools/shared/embedding_engine.py` -- light mode detection
- `server/tools/ldm/services/media_converter.py` -- DDS/WEM conversion
- `server/tools/ldm/routes/gamedata.py` -- filesystem-based gamedata
- `.planning/PROJECT.md` -- v5.0 scope and constraints
