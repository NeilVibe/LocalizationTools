# Phase 19: Game World Codex - Research

**Researched:** 2026-03-15
**Domain:** Interactive encyclopedia UI + entity indexing + semantic search + media pipelines
**Confidence:** HIGH

## Summary

Phase 19 builds an interactive encyclopedia ("Codex") that lets both translators and game developers browse characters, items, and other entities with rich metadata, images, audio, and cross-references. The Codex is a read-only reference tool -- no entity creation or editing.

The project already has all the foundational infrastructure: GameDataBrowseService scans XML folder trees (Phase 18), MediaConverter handles DDS-to-PNG and WEM-to-WAV conversion with LRU caching (Phase 11), EmbeddingEngine provides Model2Vec 256-dim embeddings (Phase 4), FAISSManager handles HNSW index creation/search (Phase 4), and ContextService resolves cross-reference chains (Phase 5.1). The mock gamedata universe (Phase 15) provides 352 entities across 6 types with 102 DDS stubs and 23 WEM audio stubs.

The main new work is: (1) a backend CodexService that parses all entity XML files into a unified entity registry with cross-reference resolution, builds a FAISS index over entity names/descriptions for semantic search, and exposes REST endpoints for entity detail/search/listing; (2) a frontend CodexPage with entity type listing, detail cards with inline media, and a semantic search bar accessible from both Translator and Game Dev modes.

**Primary recommendation:** Build a CodexService that pre-indexes all entities from StaticInfo XML files on initialization, constructs a FAISS index from Model2Vec embeddings of entity names+descriptions, and serves entity detail pages with resolved cross-references and media URLs. Frontend adds a new "Codex" page/tab accessible from the navigation sidebar with entity type browsing and semantic search.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CODEX-01 | Character encyclopedia page shows name, image, description, race, job, quest appearances, related entities | CodexService parses CharacterInfo XML (StrKey, KnowledgeKey, Gender, Age, Job, Race), resolves KnowledgeKey to KnowledgeInfo for description/image, cross-references to find quest appearances |
| CODEX-02 | Item encyclopedia page shows name, image, description, category, stats, similar items via Model2Vec | CodexService parses ItemInfo XML (Key, StrKey, ItemType, Grade, KnowledgeKey), uses FAISS search over item embeddings to find similar items |
| CODEX-03 | Codex is searchable via semantic search (Model2Vec + FAISS) across all entity types | CodexService builds FAISS index from all entity names+descriptions using EmbeddingEngine, FAISSManager.search() returns ranked results |
| CODEX-04 | Both translators and game devs can access Codex pages | Add "Codex" page to navigation store (currentPage = 'codex'), add nav tab in LDM.svelte sidebar for both modes |
| CODEX-05 | Codex pages show inline images (DDS->PNG) and audio playback (WEM->WAV) | Reuse existing /mapdata/thumbnail/{texture_name} and /mapdata/audio/stream/{string_id} endpoints from Phase 5 |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | existing | REST endpoints for codex | Already used for all API routes |
| Pydantic | existing | Request/response schemas | Already used everywhere |
| lxml | existing | XML parsing of StaticInfo files | Already used in gamedata_browse_service |
| Model2Vec | existing (256-dim) | Embedding entity text for semantic search | Already in EmbeddingEngine |
| FAISS | existing (HNSW) | Vector index for similar entity search | Already in FAISSManager |
| Svelte 5 | existing | Codex page UI | Runes-only, Carbon Components |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Pillow (PIL) | existing | DDS-to-PNG conversion | MediaConverter already handles this |
| Carbon Components Svelte | existing | UI components (Tag, Search, Tabs) | All Codex page UI |
| carbon-icons-svelte | existing | Icons (Book, Search, Person) | Codex navigation icons |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom FAISS index per entity type | Single unified index | Single index is simpler, entity_type stored in metadata for filtering |
| Separate Codex backend service | Extend existing routes/gamedata.py | New routes file keeps concerns separated, better maintainability |
| Full-text search (SQLite FTS) | Model2Vec + FAISS | FAISS already exists, provides semantic (meaning-based) not just keyword search |

**Installation:**
```bash
# No new dependencies -- all libraries already in project
```

## Architecture Patterns

### Recommended Project Structure
```
server/tools/ldm/
  services/
    codex_service.py           # CodexService: entity registry + FAISS index + search
  routes/
    codex.py                   # REST endpoints: /codex/search, /codex/entity/{type}/{key}
  schemas/
    codex.py                   # Pydantic models for codex requests/responses

locaNext/src/lib/
  components/
    pages/
      CodexPage.svelte         # Main codex page with search + entity list
    ldm/
      CodexEntityDetail.svelte # Entity detail card (character/item/skill/etc.)
      CodexSearchBar.svelte    # Semantic search input with results dropdown
      CodexEntityList.svelte   # Entity type browsing grid
```

### Pattern 1: Entity Registry (Backend)
**What:** CodexService scans all StaticInfo XML files on init, builds an in-memory entity registry (dict keyed by entity_type + StrKey), resolves KnowledgeKey cross-references to attach descriptions/images.
**When to use:** On server startup or first codex request (lazy init).
**Example:**
```python
# Pattern from gamedata_browse_service.py -- scan + parse
from lxml import etree

class CodexService:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self._entities: dict[str, dict[str, CodexEntity]] = {}
        self._faiss_index = None
        self._entity_keys: list[tuple[str, str]] = []  # (type, strkey) aligned with FAISS

    def _scan_entities(self):
        """Parse all StaticInfo XML files into entity registry."""
        for xml_file in self.base_dir.rglob("*.staticinfo.xml"):
            tree = etree.parse(str(xml_file))
            for elem in tree.getroot():
                entity = self._parse_entity(elem, xml_file)
                if entity:
                    self._entities.setdefault(entity.entity_type, {})[entity.strkey] = entity
```

### Pattern 2: Cross-Reference Resolution
**What:** After scanning all entities, resolve KnowledgeKey references to attach descriptions, images (UITextureName), and find related entities by shared KnowledgeKey references.
**When to use:** During entity registry build, after all XML files are parsed.
**Example:**
```python
# Cross-ref chain: CharacterInfo.KnowledgeKey -> KnowledgeInfo.StrKey -> UITextureName
# Already proven in context_service.py resolve_chain()
def _resolve_cross_refs(self):
    knowledge_map = {e.strkey: e for e in self._entities.get("knowledge", {}).values()}
    for entity_type, entities in self._entities.items():
        for entity in entities.values():
            if entity.knowledge_key and entity.knowledge_key in knowledge_map:
                knowledge = knowledge_map[entity.knowledge_key]
                entity.description = knowledge.description
                entity.image_texture = knowledge.ui_texture_name
```

### Pattern 3: FAISS Index for Codex Search
**What:** Build a FAISS index from Model2Vec embeddings of all entity names+descriptions for semantic search across all entity types.
**When to use:** After entity registry is built.
**Example:**
```python
# Reuse existing infrastructure
from server.tools.shared import get_embedding_engine, FAISSManager

def _build_search_index(self):
    engine = get_embedding_engine()  # Model2Vec 256-dim
    texts = [f"{e.name} {e.description or ''}" for e in all_entities]
    embeddings = engine.encode(texts)
    self._faiss_index = FAISSManager.build_index(embeddings)
```

### Pattern 4: Frontend Codex Page
**What:** New page in navigation store, accessible via sidebar tab. Shows entity type grid, detail cards, and semantic search.
**When to use:** New page component following GameDevPage pattern.
**Example:**
```svelte
<!-- Pattern: navigation store + page component from Phase 18 -->
<!-- navigation.js: add 'codex' page type + goToCodex() -->
<!-- LDM.svelte: add Codex tab in sidebar -->
{#if $currentPage === 'codex'}
  <CodexPage />
{/if}
```

### Anti-Patterns to Avoid
- **Re-parsing XML on every request:** Parse once on init, cache in memory. Entity data is read-only.
- **Separate FAISS index per entity type:** One unified index with entity_type metadata. Simpler, allows cross-type search.
- **Building new media conversion pipeline:** Reuse existing MediaConverter + /mapdata/thumbnail and /mapdata/audio/stream endpoints.
- **Making Codex editable:** CODEX is read-only reference. Editing happens in Game Dev Grid (Phase 18).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Semantic search | Custom embedding + search | EmbeddingEngine + FAISSManager | Already battle-tested, Model2Vec 256-dim, HNSW config tuned |
| DDS-to-PNG conversion | Image parsing logic | MediaConverter.convert_dds_to_png() | LRU cache, error handling, Pillow-based |
| WEM-to-WAV conversion | Audio conversion | MediaConverter.convert_wem_to_wav() | vgmstream-cli wrapper with disk cache |
| Cross-reference resolution | Manual XML traversal | Adapt ContextService.resolve_chain() pattern | Proven chain: StrKey -> KnowledgeKey -> UITextureName |
| XML entity parsing | Custom XML parser | lxml etree (same as GameDataBrowseService) | Already used everywhere, handles br-tag encoding |
| Entity display cards | New card component | Extend EntityCard.svelte | Already renders name/type/image/audio/metadata |

**Key insight:** Nearly all the building blocks exist. The Codex is primarily a composition/orchestration layer that connects existing services into a new UI experience.

## Common Pitfalls

### Pitfall 1: Slow Initialization from Full XML Scan
**What goes wrong:** Scanning 20+ XML files and building FAISS index on every server restart takes too long.
**Why it happens:** StaticInfo folder has many XML files, each needs parsing.
**How to avoid:** Lazy initialization (build on first codex request), cache the FAISS index to disk. Mock gamedata has ~20 XML files with ~352 entities -- fast enough for eager init, but production gamedata could be larger.
**Warning signs:** Server startup time increases by more than 2 seconds.

### Pitfall 2: Missing KnowledgeKey Cross-References
**What goes wrong:** Some entities have KnowledgeKey values that don't match any KnowledgeInfo entry.
**Why it happens:** Cross-ref generation in Phase 15 reuses keys cyclically (e.g., KNOW_CHAR_0037 references KNOW_CHAR_0001). Some entities might not have KnowledgeKey at all.
**How to avoid:** Graceful fallback: if KnowledgeKey not found, show entity without description/image. Never crash on missing cross-ref.
**Warning signs:** Entity detail page shows "No description" for entities that should have one.

### Pitfall 3: Image/Audio URL Construction
**What goes wrong:** Codex tries to construct image/audio URLs that don't match existing endpoints.
**Why it happens:** Existing endpoints use different key patterns (texture_name vs string_id).
**How to avoid:** Use /mapdata/thumbnail/{texture_name} for images (from KnowledgeInfo.UITextureName), /mapdata/audio/stream/{string_id} for audio (from entity StrKey). Follow the exact same URL patterns as ImageTab and AudioTab components.
**Warning signs:** 404 errors on image/audio requests.

### Pitfall 4: FAISS Index Dimension Mismatch
**What goes wrong:** FAISS index built with wrong dimension or without normalization.
**Why it happens:** Model2Vec outputs 256-dim, must match FAISSManager.create_index(dim=256).
**How to avoid:** Always get dimension from engine.dimension property. Always use FAISSManager.build_index() which handles normalization.
**Warning signs:** "dimension mismatch" errors from FAISS.

### Pitfall 5: Navigation Integration Breaks Existing Pages
**What goes wrong:** Adding "codex" page type to navigation store causes regressions in existing page routing.
**Why it happens:** LDM.svelte has conditional rendering based on $currentPage.
**How to avoid:** Add 'codex' as a new case in the {#if} chain. Follow exact pattern of 'gamedev' page addition. Don't modify existing page conditions.
**Warning signs:** Switching to Files/TM/Grid pages shows blank or wrong content.

## Code Examples

### Codex Entity Schema (Pydantic)
```python
# Source: Pattern from server/tools/ldm/schemas/gamedata.py
from pydantic import BaseModel
from typing import List, Optional

class CodexEntity(BaseModel):
    entity_type: str          # "character", "item", "skill", "region", "gimmick"
    strkey: str               # STR_CHAR_0001
    name: str                 # Korean name from KnowledgeInfo
    description: Optional[str] = None  # From KnowledgeInfo.Desc
    knowledge_key: Optional[str] = None
    image_texture: Optional[str] = None  # UITextureName for thumbnail URL
    audio_key: Optional[str] = None     # StrKey for audio stream URL
    source_file: str          # Relative path to XML file
    attributes: dict = {}     # Entity-specific attrs (Grade, Job, Race, etc.)
    related_entities: List[str] = []  # StrKeys of related entities

class CodexSearchResult(BaseModel):
    entity: CodexEntity
    similarity: float
    match_type: str  # "semantic" or "exact"

class CodexSearchResponse(BaseModel):
    results: List[CodexSearchResult]
    count: int
    search_time_ms: float
```

### Codex Route Registration
```python
# Source: Pattern from server/tools/ldm/router.py
# Add to router.py:
from .routes.codex import router as codex_router  # Phase 19: Game World Codex
router.include_router(codex_router)  # Phase 19: Game World Codex
```

### Navigation Store Extension
```javascript
// Source: Pattern from locaNext/src/lib/stores/navigation.js
// Add 'codex' page type:
export function goToCodex() {
  currentPage.set('codex');
  openFile.set(null);
}
```

### Entity XML Parsing Patterns (from mock_gamedata)
```xml
<!-- CharacterInfo: StrKey, CharacterName, KnowledgeKey, Gender, Age, Job, Race -->
<CharacterInfo StrKey="STR_CHAR_0023" CharacterName="Character_0023"
  KnowledgeKey="KNOW_CHAR_0023" Gender="Female" Age="231" Job="Paladin" Race="Dwarf"/>

<!-- ItemInfo: Key, StrKey, ItemName, ItemDesc, ItemType, Grade, KnowledgeKey -->
<ItemInfo Key="10001" StrKey="STR_ITEM_0001" ItemName="철 검"
  ItemDesc="전투에서 유용한 검.&lt;br/&gt;장인이 정성껏 제작했다."
  ItemType="Weapon" Grade="Common" KnowledgeKey="KNOW_ITEM_0001"/>

<!-- KnowledgeInfo: StrKey, Name, Desc, UITextureName (image ref) -->
<KnowledgeInfo StrKey="KNOW_CHAR_VARON" Name="장로 바론"
  Desc="검은별 마을의 장로.&lt;br/&gt;300년간 마을을 지켜온 현자."
  UITextureName="character_varon"/>
```

### Media URL Construction (Frontend)
```javascript
// Image: use UITextureName from KnowledgeInfo
const thumbnailUrl = `${API_BASE}/api/ldm/mapdata/thumbnail/${entity.image_texture}`;

// Audio: use StrKey
const audioUrl = `${API_BASE}/api/ldm/mapdata/audio/stream/${entity.strkey}`;
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| ContextService resolves per-row | CodexService pre-indexes all entities | Phase 19 (new) | Batch index enables search across all entities |
| EntityCard shows single entity in RightPanel | CodexEntityDetail shows full encyclopedia page | Phase 19 (new) | Richer display with cross-refs and similar items |
| Semantic search only in TM | Semantic search across gamedata entities | Phase 19 (new) | Codex search uses same Model2Vec + FAISS stack |

**Nothing deprecated:** All existing services remain intact. Codex adds a new consumption layer.

## Open Questions

1. **How should "quest appearances" be determined for characters?**
   - What we know: Characters have KnowledgeKey, but quest data isn't explicitly in the mock XML. GimmickInfo references characters indirectly.
   - What's unclear: Whether the mock data has enough cross-reference data to derive quest appearances.
   - Recommendation: For Phase 19, show "related entities" by finding other entities that share the same KnowledgeKey prefix or appear in the same source files. Mark as "Related" rather than "Quest Appearances" if actual quest data isn't available.

2. **Should the FAISS index persist to disk or rebuild on startup?**
   - What we know: Mock data has ~352 entities. Model2Vec encoding + FAISS build takes <1 second for this size.
   - What's unclear: Production gamedata size.
   - Recommendation: For now, rebuild on first request (lazy init). If performance becomes an issue, add disk persistence later (FAISSManager.save_index already supports this).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | tests/conftest.py |
| Quick run command | `python -m pytest tests/unit/ldm/test_codex_service.py -x -q` |
| Full suite command | `python -m pytest tests/unit/ldm/ -x -q` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CODEX-01 | Character entity detail with name, image, desc, race, job, related | unit | `python -m pytest tests/unit/ldm/test_codex_service.py::test_character_detail -x` | Wave 0 |
| CODEX-02 | Item entity detail with similar items via FAISS | unit | `python -m pytest tests/unit/ldm/test_codex_service.py::test_item_similar_search -x` | Wave 0 |
| CODEX-03 | Semantic search across all entity types | unit | `python -m pytest tests/unit/ldm/test_codex_service.py::test_semantic_search -x` | Wave 0 |
| CODEX-04 | Codex accessible from both modes | integration | `python -m pytest tests/unit/ldm/test_codex_route.py::test_codex_endpoints -x` | Wave 0 |
| CODEX-05 | Images and audio resolve correctly | unit | `python -m pytest tests/unit/ldm/test_codex_service.py::test_media_resolution -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/unit/ldm/test_codex_service.py -x -q`
- **Per wave merge:** `python -m pytest tests/unit/ldm/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/unit/ldm/test_codex_service.py` -- covers CODEX-01, CODEX-02, CODEX-03, CODEX-05
- [ ] `tests/unit/ldm/test_codex_route.py` -- covers CODEX-04 (endpoint access)

## Sources

### Primary (HIGH confidence)
- Codebase analysis: `server/tools/ldm/services/gamedata_browse_service.py` -- entity scanning pattern
- Codebase analysis: `server/tools/ldm/services/media_converter.py` -- DDS/WEM conversion
- Codebase analysis: `server/tools/shared/embedding_engine.py` -- Model2Vec engine
- Codebase analysis: `server/tools/shared/faiss_manager.py` -- FAISS HNSW index
- Codebase analysis: `server/tools/ldm/services/context_service.py` -- cross-ref resolution
- Codebase analysis: `server/tools/ldm/routes/mapdata.py` -- thumbnail/audio endpoints
- Codebase analysis: `tests/fixtures/mock_gamedata/` -- entity XML structure
- Codebase analysis: `locaNext/src/lib/stores/navigation.js` -- page navigation pattern
- Codebase analysis: `locaNext/src/lib/components/pages/GameDevPage.svelte` -- page layout pattern
- Codebase analysis: `locaNext/src/lib/components/ldm/EntityCard.svelte` -- entity display pattern

### Secondary (MEDIUM confidence)
- None needed -- all patterns derive from existing codebase

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already in project, no new dependencies
- Architecture: HIGH -- follows established patterns from Phases 5, 11, 15, 18
- Pitfalls: HIGH -- identified from actual codebase analysis of cross-ref chains and media pipelines

**Research date:** 2026-03-15
**Valid until:** 2026-04-15 (stable -- internal project, no external dependency changes)
