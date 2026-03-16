# Phase 29: Multi-Tier Indexing - Context

**Gathered:** 2026-03-16
**Status:** Ready for planning
**Source:** Deep research swarm (5 agents on TMIndexer, TMSearcher, update logic, split-line/whole, delta analysis)

<domain>
## Phase Boundary

Adapt the existing 5-tier TMIndexer/TMSearcher cascade for gamedata entities, add Aho-Corasick as Tier 0, and wire it to the tree UI. 80% code reuse — input adaptation, not greenfield.

Requirements: IDX-01, IDX-02, IDX-03, IDX-04, IDX-05

</domain>

<decisions>
## Implementation Decisions

### Architecture: Adapt TMIndexer/TMSearcher Pattern
- Create `GameDataIndexer` modeled on `server/tools/ldm/indexing/indexer.py` — same build pipeline
- Create `GameDataSearcher` modeled on `server/tools/ldm/indexing/searcher.py` — 6-tier cascade (add AC)
- REUSE directly: `FAISSManager`, `EmbeddingEngine`, `normalize_for_hash`, `normalize_for_embedding`, HNSW params
- NO database tracking (no LDMTMIndex table) — use metadata.json only
- In-memory indexes (rebuilt on folder load, no disk persistence for gamedata)

### 6-Tier Cascade (adapted from 5-tier TM search)
- **Tier 0 (NEW): Aho-Corasick** — O(n) single-pass entity name detection in query text. From `glossary_service.py` pattern + QuickCheck frozenset dedup.
- **Tier 1: Whole hash** — O(1) exact match on entity name. Adapted from `_build_whole_lookup()`.
- **Tier 2: Whole embedding** — FAISS HNSW semantic search on (entity_name + entity_desc). Model2Vec 256-dim.
- **Tier 3: Line hash** — O(1) exact match on description lines split by `<br/>`. Adapted from `_build_line_lookup()`.
- **Tier 4: Line embedding** — FAISS HNSW per description line. Same threshold 0.92.
- **Tier 5: N-gram fallback** — Jaccard trigram on entity names. Same `_ngram_search()` logic.

### Input Adaptation (TM → Gamedata)
- **TM input:** `LDMTMEntry.source_text` (single field)
- **Gamedata input:** Two fields from TreeNode:
  - `entity_name` = `attributes[EDITABLE_ATTRS[tag][0]]` (e.g., ItemName, CharacterName)
  - `entity_desc` = `attributes[EDITABLE_ATTRS[tag][1]]` if exists (e.g., ItemDesc, SkillDesc)
- **Whole embedding:** Encode `entity_name + " " + entity_desc` concatenated
- **Line splitting:** Split `entity_desc` by `<br/>` (NOT `\n` — XML format)
- **Hashtable keys:** Normalized entity name for Tier 1, normalized desc lines for Tier 3

### Storage: In-Memory, Global
- No per-tm_id scoping — one global index for all loaded gamedata
- Rebuild on each folder load (gamedata is immutable XML, no incremental updates needed)
- Aho-Corasick automaton is immutable after `make_automaton()` — rebuild on folder change

### Performance Budget (IDX-05)
- Target: <3 seconds for 5000+ entities
- Hashtable build: ~10ms (trivial)
- Model2Vec encoding 5000 texts: ~170ms (29K/sec)
- FAISS HNSW build: ~200ms
- Aho-Corasick build: ~50ms
- Total: ~430ms (well under 3s budget)

### API Endpoints
- `POST /api/ldm/gamedata/index/build` — trigger index build from folder path
- `POST /api/ldm/gamedata/index/search` — 6-tier cascade search, returns `{tier, tier_name, results, perfect_match}`
- `GET /api/ldm/gamedata/index/status` — index readiness, entity count, build time

### Frontend Integration
- Search bar in GameDataTree header
- Glossary highlights in NodeDetailPanel (Aho-Corasick detection on attribute values)
- Search results navigate to matching nodes in tree

### Claude's Discretion
- Whether to add pyahocorasick to requirements.txt or keep graceful fallback
- Exact entity extraction logic from TreeNode walk
- Whether to persist indexes to disk (recommendation: don't, rebuild is <500ms)
- Loading indicator design during index build

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing Index/Search System (ADAPT these)
- `server/tools/ldm/indexing/indexer.py` — TMIndexer: full build pipeline (hash + embedding + FAISS). Adapt for gamedata.
- `server/tools/ldm/indexing/searcher.py` — TMSearcher: 5-tier cascade. Extend to 6 tiers with AC.
- `server/tools/ldm/indexing/utils.py` — normalize_for_hash, normalize_for_embedding, normalize_newlines_universal

### Shared Infrastructure (REUSE directly)
- `server/tools/shared/faiss_manager.py` — FAISSManager: HNSW build/search/incremental_add
- `server/tools/shared/embedding_engine.py` — EmbeddingEngine: Model2Vec 256-dim encode()

### Aho-Corasick Pattern (REUSE for Tier 0)
- `server/tools/ldm/services/glossary_service.py` — GlossaryService: build_from_entity_names, detect_entities, is_isolated
- `RessourcesForCodingTheProject/NewScripts/QuickCheck/core/term_check.py` lines 61-113 — Dual automaton + frozenset dedup

### Gamedata Tree Source (INPUT)
- `server/tools/ldm/services/gamedata_tree_service.py` — TreeNode hierarchy from XML
- `server/tools/ldm/services/gamedata_browse_service.py` lines 24-38 — EDITABLE_ATTRS mapping

### Frontend Integration Points
- `locaNext/src/lib/components/ldm/GameDataTree.svelte` — Add search bar, handle search results
- `locaNext/src/lib/components/ldm/NodeDetailPanel.svelte` — Add glossary highlights

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets (80% of implementation)
- `TMIndexer._build_whole_lookup()` → adapt for entity names
- `TMIndexer._build_line_lookup()` → adapt for desc lines (br-tag split)
- `TMIndexer._build_whole_embeddings()` → adapt for name+desc concat
- `TMIndexer._build_line_embeddings()` → adapt for desc lines
- `TMSearcher.search()` → extend cascade, add Tier 0
- `TMSearcher._ngram_search()` → reuse as-is
- `FAISSManager` — all methods reusable
- `EmbeddingEngine` — encode() reusable
- `GlossaryService` — AC pattern reusable

### Critical Adaptation Points (20% new code)
- `<br/>` splitting instead of `\n` for line tiers
- Two-field extraction (name + desc) from TreeNode.attributes
- Global storage path (not per-tm_id)
- No DB tracking (metadata.json only)
- New Tier 0 AC automaton integration
- Result schema: node_id/tag/folder_path instead of entry_id

### Integration Points
- `POST /gamedata/tree/folder` returns all entities → feed to indexer
- `glossary_service.py` AC pattern → adapt for Tier 0
- GameDataTree search bar → query index/search endpoint
- NodeDetailPanel → show AC glossary highlights inline

</code_context>

<specifics>
## Specific Ideas

- The 5-tier cascade is PROVEN with millions of TM entries — adapting for 5000 gamedata entities will be trivially fast
- Build time will be under 500ms total, well within 3s budget
- AC automaton from QuickCheck's frozenset pattern handles duplicate entity names correctly
- No NPC check needed (gamedata has no "user target" concept)
- Can run index build as a side-effect of folder loading (non-blocking, ~500ms)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 29-multi-tier-indexing*
*Context gathered: 2026-03-16 via deep research swarm*
