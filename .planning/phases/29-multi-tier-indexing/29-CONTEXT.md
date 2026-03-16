# Phase 29: Multi-Tier Indexing - Context

**Gathered:** 2026-03-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Build three indexing tiers that activate automatically when a gamedata folder loads: (1) hashtable for O(1) key/name lookup, (2) FAISS vector index for semantic search via Model2Vec, (3) Aho-Corasick automaton for real-time glossary detection. All three must complete in under 3 seconds for 5000+ entities.

Requirements: IDX-01, IDX-02, IDX-03, IDX-04, IDX-05

</domain>

<decisions>
## Implementation Decisions

### Indexing Architecture — Backend Service
- New `GameDataIndexService` in `server/tools/ldm/services/` — owns all three index tiers
- Triggered automatically when `POST /gamedata/tree/folder` returns data — backend builds indexes as a side effect
- New endpoint `POST /api/ldm/gamedata/index/search` for querying across all tiers
- Indexes are in-memory only (rebuilt on each folder load, no disk persistence for gamedata — it's fast enough)

### Tier 1: Hashtable Index (IDX-01)
- Python dict mapping: `{Key: entity, StrKey: entity, entity_name_lower: entity}` for O(1) lookup
- Populated by walking all TreeNode objects from folder tree response
- Entity name extracted from first EDITABLE_ATTRS entry (e.g., ItemName, CharacterName)
- Case-insensitive name lookup (lowercase key)

### Tier 2: FAISS Vector Index (IDX-02)
- REUSE existing `server/tools/shared/faiss_manager.py` (IndexHNSWFlat, M=32, ef=400/500)
- REUSE existing `server/tools/shared/embedding_engine.py` (Model2Vec, 256-dim)
- Encode all entity names + descriptions via Model2Vec
- Build FAISS index from the embeddings
- Search returns top-K similar entities with cosine similarity scores

### Tier 3: Aho-Corasick Automaton (IDX-03, IDX-04)
- REUSE existing `server/tools/ldm/services/glossary_service.py` pattern
- Build automaton from all entity names extracted during folder load
- Use isolated match mode (word boundary check) — Korean-aware via `is_isolated()`
- Frozenset pattern from QuickCheck for duplicate name handling
- Auto-glossary: collect all entity names + descriptions into glossary entries

### Performance Target (IDX-05)
- 5000+ entities must index in under 3 seconds
- Hashtable: O(n) build, instant — trivial
- FAISS: Model2Vec batch encoding (batch_size=100) + HNSW build — ~1-2s for 5000 entities
- Aho-Corasick: `ahocorasick.Automaton()` build — <100ms for 5000 terms
- Total budget: ~2-3 seconds including XML parsing overhead

### API Design
- `POST /api/ldm/gamedata/index/build` — explicitly trigger index build (called after folder load)
- `POST /api/ldm/gamedata/index/search` — unified search across all tiers, returns `{hashtable_results, semantic_results, glossary_matches}`
- `GET /api/ldm/gamedata/index/status` — check if indexes are built, entity count, build time

### Frontend Integration
- GameDataTree receives index status via API poll after folder load
- Search bar in tree header — queries all three tiers
- Glossary highlights in NodeDetailPanel (Aho-Corasick results shown inline)

### Claude's Discretion
- Exact batch size for Model2Vec encoding (100 is proven default)
- Whether to add pyahocorasick to server requirements.txt or keep fallback pattern
- In-memory cache eviction strategy (if user loads a different folder)
- Whether to show index build progress in the UI

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing FAISS Infrastructure (REUSE)
- `server/tools/shared/faiss_manager.py` — FAISSManager with HNSW config, create/add/search/load methods
- `server/tools/shared/embedding_engine.py` — EmbeddingEngine with Model2Vec (256-dim) and Qwen backends

### Existing Aho-Corasick Infrastructure (REUSE)
- `server/tools/ldm/services/glossary_service.py` — GlossaryService with build_from_entity_names, detect_entities, is_isolated
- `RessourcesForCodingTheProject/NewScripts/QuickCheck/core/term_check.py` lines 61-113 — Dual automaton + frozenset dedup pattern (reference implementation)

### Existing TM Indexing (ADAPT pattern)
- `server/tools/ldm/indexing/indexer.py` — TMIndexer showing hash + FAISS index build pattern
- `server/tools/ldm/indexing/searcher.py` — TMSearcher with 5-tier cascade (adapt for entity search)

### Tree Data Source (INPUT)
- `server/tools/ldm/services/gamedata_tree_service.py` — GameDataTreeService returns TreeNode hierarchies
- `server/tools/ldm/schemas/gamedata.py` — TreeNode, FolderTreeDataResponse schemas
- `server/tools/ldm/services/gamedata_browse_service.py` lines 24-38 — EDITABLE_ATTRS mapping

### Frontend Integration Points
- `locaNext/src/lib/components/ldm/GameDataTree.svelte` — Tree component, needs search bar + index status
- `locaNext/src/lib/components/ldm/NodeDetailPanel.svelte` — Detail panel, needs glossary highlights
- `locaNext/src/lib/components/pages/GameDevPage.svelte` — Page layout, needs search integration

### Mock Data for Testing
- `tests/fixtures/mock_gamedata/StaticInfo/` — 10 directories, 5676 mock entities for benchmarking

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `FAISSManager`: complete HNSW index lifecycle (create, add, search, save, load)
- `EmbeddingEngine`: Model2Vec encode() with batch support and L2 normalization
- `GlossaryService`: Aho-Corasick automaton with Korean-aware word boundary detection
- `TMIndexer`: hash + embedding index build pattern (adapt for entities)
- `TMSearcher`: 5-tier cascade search (adapt for entity tiers)
- `gamedata_tree_service.parse_folder()`: returns all entities as TreeNode hierarchies

### Established Patterns
- FAISS: IndexHNSWFlat with METRIC_INNER_PRODUCT after L2 normalization
- Model2Vec: batch_size=100, normalize_L2 at FAISS boundary only
- Aho-Corasick: frozenset for duplicate keys, is_isolated() for word boundaries
- FastAPI services: stateless classes, loguru logger, Pydantic schemas

### Integration Points
- `POST /gamedata/tree/folder` already returns all entities — hook index build here
- `glossary_service.py` already has entity detection — wire to gamedata entities
- `embedding_engine.py` already cached — reuse same engine instance

</code_context>

<specifics>
## Specific Ideas

- All three index tiers share the same input: entity list extracted from TreeNode walk
- Entity extraction: walk TreeNode tree, for each node collect {tag, Key, StrKey, editable_attrs values}
- Performance is the key differentiator — 3-second budget for 5000+ entities is tight
- Model2Vec encoding is the bottleneck (~1-2s) — everything else is <100ms
- pyahocorasick is already partially integrated (glossary_service.py) but missing from requirements.txt

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 29-multi-tier-indexing*
*Context gathered: 2026-03-16*
