# Phase 4: Search and AI Differentiators - Research

**Researched:** 2026-03-14
**Domain:** Semantic search UI, Model2Vec integration, FAISS indexing, AI-matched indicators
**Confidence:** HIGH

## Summary

Phase 4 builds on a mature backend infrastructure. The 5-Tier Cascade TM Search (`TMSearcher`) already performs semantic search using Model2Vec + FAISS for TM matching (Tiers 2 and 4). The `EmbeddingEngine` abstraction with Model2Vec as default is fully operational. The KR Similar API provides a standalone similarity search tool. What is **missing** is: (1) a dedicated semantic search UI in the grid toolbar that queries TM/project rows by meaning, (2) the "fuzzy" search mode in VirtualGrid currently falls through to SQL LIKE instead of actual semantic search, (3) no "AI-suggested" visual indicator exists in the editor grid, and (4) performance benchmarking/validation of sub-second search.

**Primary recommendation:** Wire the existing TMSearcher's FAISS semantic search into the grid's "fuzzy/similar" search mode via a new API endpoint, add a prominent "Find Similar" UI element, and introduce an "AI-matched" badge in the grid row for translations sourced from Model2Vec matching.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SRCH-01 | Semantic search using Model2Vec (FAISS vectors) finds similar-meaning translations | TMSearcher Tier 2/4 already does this for TM. Need new endpoint for cross-file/project semantic search. Grid "fuzzy" mode must call it. |
| SRCH-02 | Semantic search UI prominently showcases the "find similar" capability | VirtualGrid has a "Similar" (fuzzy) mode button but it does SQL LIKE. Need to rewire to semantic backend + add similarity scores to results. |
| SRCH-03 | Search performance is near-instant (sub-second for typical TM sizes) | Model2Vec encodes in ~0.5ms per text. FAISS HNSW search is O(log n). Need perf test to validate. |
| AI-01 | Model2Vec powers the entire semantic pipeline (TM matching, search, entity detection) as the default/standard model | EmbeddingEngine defaults to Model2Vec. TMSearcher uses it. Need to ensure new search endpoints also use it exclusively. |
| AI-02 | "AI-suggested" indicator visible in editor for Model2Vec-matched translations | No indicator exists. Need badge/icon in VirtualGrid rows when translation came from AI/TM auto-fill. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Model2Vec (potion-multilingual-128M) | latest | 256-dim multilingual embeddings | Already integrated via EmbeddingEngine. 79x faster than Qwen, 128MB model |
| FAISS | cpu | HNSW vector index for similarity search | Already used in TMSearcher and KR Similar. O(log n) search |
| NumPy | installed | Embedding arithmetic, normalization | Already used throughout |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Carbon Components Svelte | installed | UI components (Tag, InlineLoading, icons) | All UI work in this phase |
| Svelte 5 (Runes) | installed | Frontend framework | $state, $derived, $effect patterns |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| FAISS HNSW | FAISS Flat (brute force) | HNSW is faster for large indexes but Flat is simpler. HNSW already used -- keep it. |
| Model2Vec | Qwen embeddings | Qwen is higher quality (1024-dim) but 79x slower. Decision: Model2Vec ONLY (locked). |

**Installation:** No new dependencies needed. All libraries already installed.

## Architecture Patterns

### Existing Architecture (What We Build On)

```
server/tools/shared/embedding_engine.py     # EmbeddingEngine abstraction (Model2Vec default)
server/tools/ldm/indexing/searcher.py       # TMSearcher - 5-Tier Cascade
server/tools/ldm/routes/tm_search.py        # /tm/suggest, /tm/{id}/search/exact, /tm/{id}/search
server/tools/ldm/routes/tm_indexes.py       # /tm/{id}/build-indexes, /tm/{id}/sync
server/tools/ldm/services/indexing_service.py  # Auto-indexing after TM upload
server/api/kr_similar_async.py              # KR Similar standalone search API
locaNext/src/lib/components/ldm/VirtualGrid.svelte   # Grid with searchMode (fuzzy = SQL LIKE)
locaNext/src/lib/components/ldm/TMTab.svelte         # TM matches in right panel
locaNext/src/lib/components/ldm/RightPanel.svelte    # Tabbed side panel
locaNext/src/lib/components/pages/GridPage.svelte    # Main grid page, wires TM suggest
```

### Pattern 1: Semantic Search Endpoint (New)
**What:** A new API endpoint that accepts a query text and returns semantically similar rows from the current file/TM using FAISS.
**When to use:** When VirtualGrid's search mode is "fuzzy/similar"
**Key Design:**
```python
# New endpoint: GET /api/ldm/files/{file_id}/semantic-search
# Params: query, threshold (0.5), max_results (20), tm_id (optional)
# Returns: list of {row_id, line_number, source, target, similarity, match_type}
#
# Implementation:
# 1. Encode query with EmbeddingEngine (Model2Vec)
# 2. Search FAISS index for the file's TM (or build on-the-fly from file rows)
# 3. Return ranked results with similarity scores
```

### Pattern 2: AI-Suggested Indicator
**What:** A visual badge in the grid marking rows where the translation was auto-filled from TM/AI matching.
**When to use:** When a translation is applied from TM suggest or auto-translate.
**Key Design:**
- Add `match_source` field to row data (values: null, "tm_exact", "tm_fuzzy", "ai_semantic")
- Store this when user clicks "Apply TM" from TMTab or when auto-pretranslate fills rows
- VirtualGrid renders a small AI/TM icon badge next to the target text
- Color coding: same as TM match colors (green=exact, yellow=fuzzy, blue=AI semantic)

### Pattern 3: Search Results with Scores
**What:** When semantic search is active, results show similarity scores alongside the regular grid rows.
**When to use:** Only in "Similar" search mode
**Key Design:**
- Semantic search returns row IDs + similarity scores
- VirtualGrid renders a small score badge next to matching rows
- Results sorted by similarity (descending), not by row number
- Clear visual distinction from regular text search results

### Anti-Patterns to Avoid
- **Building a separate search page:** Search must live IN the grid toolbar, not as a separate view. Users expect filter-in-place.
- **Re-encoding on every search keystroke:** Model2Vec is fast but encoding + FAISS search on every keypress is wasteful. Use debounce (300ms) like existing search.
- **Mixing Model2Vec and Qwen results:** Decision is Model2Vec ONLY. Never fall back to Qwen for search.
- **Blocking UI during search:** Always use async fetch. TMSearcher loads model lazily; first search may have a ~1s cold start.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Text embeddings | Custom embedding code | `EmbeddingEngine.encode()` | Already abstracted with caching, normalization, lazy loading |
| Vector similarity | Manual cosine similarity loops | FAISS `IndexFlatIP` or HNSW | FAISS handles batching, memory mapping, efficient search |
| TM cascade search | Custom multi-tier logic | `TMSearcher.search()` | Already implements 5-tier cascade with hash + FAISS + n-gram |
| Debounced search | Custom setTimeout logic | Existing `searchDebounceTimer` pattern in VirtualGrid | Already working pattern |
| Color-coded badges | Custom color logic | `getMatchColor()` in TMTab.svelte | Already implements the exact/fuzzy/low color system |

**Key insight:** 90% of the backend infrastructure exists. This phase is primarily about WIRING existing capabilities into the grid search UI and adding visual indicators.

## Common Pitfalls

### Pitfall 1: FAISS Index Not Built Yet
**What goes wrong:** Semantic search returns empty because the file's TM has no FAISS index built.
**Why it happens:** FAISS indexes are built on-demand via `/tm/{id}/build-indexes`. New TMs or TMs with only hash lookups won't have embedding indexes.
**How to avoid:** Check index status before attempting semantic search. If no FAISS index exists, show a helpful message ("Build TM index to enable semantic search") with a one-click build button. Auto-indexing service (`trigger_auto_indexing`) should handle this for new TMs.
**Warning signs:** Empty results on semantic search when TM has entries.

### Pitfall 2: Dimension Mismatch Between Indexes
**What goes wrong:** FAISS index was built with Qwen (1024-dim) but current engine is Model2Vec (256-dim). Search crashes.
**Why it happens:** User or system switched embedding engine after building indexes.
**How to avoid:** TMSearcher already handles this via the `test_tm_dimension_mismatch.py` test suite. The index metadata stores the engine name and dimension. On mismatch, rebuild is triggered. Ensure new search endpoint also checks dimensions.
**Warning signs:** `RuntimeError` from FAISS about dimension mismatch.

### Pitfall 3: Cold Start Latency
**What goes wrong:** First semantic search takes 2-3 seconds because Model2Vec model needs loading.
**Why it happens:** Model is lazy-loaded on first `encode()` call.
**How to avoid:** Preload engine during server startup or on first file open. `preload_engine("model2vec")` exists for this purpose.
**Warning signs:** First search is slow, subsequent searches are fast.

### Pitfall 4: Fuzzy Mode Falls Through to LIKE
**What goes wrong:** The "Similar" search mode in VirtualGrid sends `search_mode=fuzzy` but the backend SQLite repo treats it as "contain" (LIKE).
**Why it happens:** Current `row_repo.py` line 392 has `else: # contain (default)` which catches fuzzy too.
**How to avoid:** This is the core implementation gap. Need to either: (a) intercept fuzzy mode in the frontend and call a different endpoint, or (b) add semantic search handling in the backend rows endpoint.
**Warning signs:** "Similar" mode returning exact text matches, not semantic matches.

### Pitfall 5: No File-Level FAISS Index
**What goes wrong:** TMSearcher indexes TM entries, but semantic search in the grid needs to search file rows (which are different from TM entries).
**Why it happens:** TM entries are a curated subset; file rows are the full working set.
**How to avoid:** Two approaches: (1) Search the linked TM's FAISS index (already built) -- this gives TM suggestions. (2) Build a transient FAISS index from file rows on demand -- this gives within-file semantic search. Approach (1) is simpler and sufficient for SRCH-01. Approach (2) can be deferred.
**Warning signs:** Semantic search only finding TM entries, not rows within the current file.

## Code Examples

### Loading and Using TMSearcher for Semantic Search
```python
# Source: server/tools/ldm/indexing/searcher.py (existing code)
from server.tools.ldm.indexing.searcher import TMSearcher
from server.tools.ldm.tm_indexer import TMIndexer

# Load indexes for a TM
indexer = TMIndexer(db_session)
indexes = indexer.load_indexes(tm_id)
searcher = TMSearcher(indexes)

# Semantic search (uses Tier 2: FAISS whole embedding)
result = searcher.search("save the game", top_k=10, threshold=0.5)
# Returns: {"tier": 2, "tier_name": "whole_embedding", "results": [...], "perfect_match": False}
```

### Direct FAISS Search with Model2Vec (for custom endpoint)
```python
# Source: server/tools/shared/embedding_engine.py
from server.tools.shared import get_embedding_engine
import faiss
import numpy as np

engine = get_embedding_engine("model2vec")
engine.load()

# Encode query
query_embedding = engine.encode(["find similar translations"], normalize=True)

# Search existing FAISS index
scores, indices = faiss_index.search(query_embedding, top_k)
# scores[0] contains cosine similarities, indices[0] contains row positions
```

### VirtualGrid Search Mode (Current Svelte 5 Pattern)
```svelte
<!-- Source: locaNext/src/lib/components/ldm/VirtualGrid.svelte -->
let searchMode = $state("contain"); // 'contain' | 'exact' | 'not_contain' | 'fuzzy'
const searchModeOptions = [
  { id: "contain", text: "Contains", icon: "\u2283" },
  { id: "exact", text: "Exact", icon: "=" },
  { id: "not_contain", text: "Excludes", icon: "\u2260" },
  { id: "fuzzy", text: "Similar", icon: "\u2248" }
];

// Currently sends: params.append('search_mode', searchMode);
// Backend falls through to LIKE for fuzzy -- THIS IS THE GAP
```

### AI-Suggested Badge Pattern (New)
```svelte
<!-- Pattern for rendering AI indicator in grid rows -->
{#if row.match_source}
  <span class="ai-badge" class:exact={row.match_source === 'tm_exact'}
        class:fuzzy={row.match_source === 'tm_fuzzy'}
        class:semantic={row.match_source === 'ai_semantic'}>
    <MachineLearningModel size={12} />
  </span>
{/if}
```

### RightPanel Tab Integration (Existing Pattern)
```svelte
<!-- Source: locaNext/src/lib/components/ldm/RightPanel.svelte -->
<!-- Tabs already defined: TM | Image | Audio | AI Context -->
<!-- AI Context tab is placeholder -- can be used for search results display -->
const tabs = [
  { id: 'tm', label: 'TM', icon: DataBase },
  { id: 'image', label: 'Image', icon: Image },
  { id: 'audio', label: 'Audio', icon: Music },
  { id: 'context', label: 'AI Context', icon: MachineLearningModel }
];
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Qwen 1024-dim embeddings | Model2Vec 256-dim embeddings | Phase 3 (EmbeddingEngine) | 79x faster, 12x smaller build |
| SQL LIKE for all text search | 5-Tier Cascade (hash + FAISS + n-gram) | TMSearcher refactor | Real semantic matching for TM |
| No TM matching | TMSearcher + TMTab with color-coded % | Phase 3 | TM matches displayed in right panel |
| Manual TM assignment | Auto-mirror + hierarchy cascade | Phase 3 | TMs automatically linked to files |

**What remains:** Grid search toolbar still uses SQL LIKE even in "Similar" mode. No AI-suggested indicators. No dedicated semantic search UI showcase.

## Open Questions

1. **File-Level vs TM-Level Semantic Search**
   - What we know: TMSearcher indexes TM entries. File rows are separate.
   - What's unclear: Should "Similar" search in the grid search within TM entries, within file rows, or both?
   - Recommendation: Search TM entries first (already indexed). Searching file rows requires building a per-file FAISS index on demand, which adds complexity. Start with TM-level search for SRCH-01, note per-file as enhancement.

2. **Persistence of AI-Suggested Status**
   - What we know: We need a visual indicator for AI-matched translations (AI-02).
   - What's unclear: Should this be persisted in the database (new column on rows table) or just tracked in-memory?
   - Recommendation: Track in-memory for now (Svelte store or row metadata). Database schema change can come later when we need to persist across sessions. For the demo, in-session tracking is sufficient.

3. **Search Results Presentation in "Similar" Mode**
   - What we know: Regular search filters the grid in-place. Semantic search returns ranked results that may span the entire file.
   - What's unclear: Should semantic results replace the grid, overlay it, or show in a separate panel?
   - Recommendation: Show results in a dropdown/overlay below the search bar (like autocomplete), not replacing the grid. Each result shows similarity score and clicking scrolls to that row. This preserves the grid context while showcasing similarity scores.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.4.2 + Playwright |
| Config file | `pytest.ini` (root) + `locaNext/playwright.config.ts` |
| Quick run command | `python3 -m pytest tests/unit/test_tm_search.py -x -v` |
| Full suite command | `python3 -m pytest tests/unit/ tests/stability/ -x -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SRCH-01 | Semantic search finds similar-meaning translations | unit | `python3 -m pytest tests/unit/test_semantic_search.py -x` | No -- Wave 0 |
| SRCH-02 | Semantic search UI showcases "find similar" | e2e | `npx playwright test tests/semantic-search.spec.ts` | No -- Wave 0 |
| SRCH-03 | Search performance is sub-second | unit | `python3 -m pytest tests/unit/test_semantic_search.py::test_performance -x` | No -- Wave 0 |
| AI-01 | Model2Vec powers entire semantic pipeline | unit | `python3 -m pytest tests/unit/test_tm_search.py -x -v` | Yes (existing) |
| AI-02 | AI-suggested indicator in editor | e2e | `npx playwright test tests/ai-indicator.spec.ts` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `python3 -m pytest tests/unit/test_tm_search.py tests/unit/test_semantic_search.py -x -v`
- **Per wave merge:** `python3 -m pytest tests/unit/ -x -v && cd locaNext && npx playwright test`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/unit/test_semantic_search.py` -- covers SRCH-01, SRCH-03 (new endpoint unit tests)
- [ ] `locaNext/tests/semantic-search.spec.ts` -- covers SRCH-02 (E2E: UI renders search results with scores)
- [ ] `locaNext/tests/ai-indicator.spec.ts` -- covers AI-02 (E2E: AI badge appears when TM applied)

*(Existing `tests/unit/test_tm_search.py` covers TMSearcher 5-tier cascade including embedding tiers -- AI-01 is already covered)*

## Sources

### Primary (HIGH confidence)
- `server/tools/shared/embedding_engine.py` -- EmbeddingEngine with Model2Vec default, 256-dim
- `server/tools/ldm/indexing/searcher.py` -- TMSearcher 5-Tier Cascade (hash + FAISS + n-gram)
- `server/tools/ldm/routes/tm_search.py` -- Existing TM suggest/search endpoints
- `server/tools/ldm/routes/tm_indexes.py` -- Index build/sync endpoints
- `server/repositories/sqlite/row_repo.py` -- Shows fuzzy mode falls through to LIKE
- `locaNext/src/lib/components/ldm/VirtualGrid.svelte` -- Grid search with searchMode options
- `locaNext/src/lib/components/ldm/TMTab.svelte` -- TM match display with color-coded badges
- `locaNext/src/lib/components/ldm/RightPanel.svelte` -- Tabbed panel with AI Context placeholder
- `locaNext/src/lib/components/pages/GridPage.svelte` -- TM suggest wiring, row selection

### Secondary (MEDIUM confidence)
- `server/api/kr_similar_async.py` -- KR Similar standalone search (reference for search patterns)
- `server/tools/kr_similar/searcher.py` -- FAISS search patterns (find_similar, extract_similar)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all libraries already installed and integrated
- Architecture: HIGH - existing codebase thoroughly examined, patterns clear
- Pitfalls: HIGH - identified from actual code gaps (fuzzy->LIKE fallthrough, dimension mismatch tests exist)

**Research date:** 2026-03-14
**Valid until:** 2026-04-14 (stable -- no external dependencies changing)
