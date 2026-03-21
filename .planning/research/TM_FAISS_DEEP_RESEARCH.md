# TM Auto-Registration and FAISS/HNSW Index Updates - Deep Research

**Researched:** 2026-03-21
**Domain:** Translation Memory (TM) auto-registration, FAISS HNSW indexing, Model2Vec embeddings
**Confidence:** HIGH (all findings verified from source code)

---

## Summary

LocaNext's Translation Memory system is a sophisticated 5-tier cascade search architecture built on top of FAISS HNSW indexes and Model2Vec 256-dim embeddings. TM auto-registration happens **only when a row's status is set to "reviewed"** (FEAT-001), not on every save. The FAISS indexes support both incremental adds (INSERT-only) and full rebuilds (UPDATE/DELETE), with a smart sync manager that diffs DB vs PKL state. Offline/SQLite mode has full TM search parity via cached FAISS indexes loaded on-demand.

**Key architecture insight:** DB is always the source of truth. FAISS/PKL indexes are local caches that sync on demand (auto-sync after entry modifications, manual sync via UI).

---

## Question 1: When does a row AUTO-REGISTER to TM?

**Answer: ONLY when status is set to "reviewed"** (FEAT-001)

**File:** `server/tools/ldm/routes/rows.py` lines 225-260

```python
# FEAT-001: Auto-add to linked TM if status is 'reviewed'
new_status = updated_row.get("status")
source = updated_row.get("source")
target = updated_row.get("target")
if new_status == "reviewed" and source and target:
    # Get project's linked TM
    linked_tm_id = await _get_project_linked_tm(tm_repo, project_id, current_user["user_id"])
    if linked_tm_id:
        # Add entry to TM in background thread
        result = await asyncio.to_thread(_add_to_tm)
        if result:
            # Trigger index rebuild in background
            background_tasks.add_task(_auto_sync_tm_indexes, linked_tm_id, current_user["user_id"])
```

**Conditions for auto-registration:**
1. Row status must be set to **"reviewed"** (not "approved", "pending", or "translated")
2. Row must have both **source AND target** text
3. Project must have a **linked TM** (via FEAT-001 TM Linking API)
4. The linked TM must exist and be accessible

**After auto-add:** Background task `_auto_sync_tm_indexes` runs to update FAISS indexes.

**For negative row IDs (offline/local):** No TM auto-add happens (early return at line 169-177).

**Confidence:** HIGH -- verified directly from source code.

---

## Question 2: Does file upload auto-populate TM?

**Answer: NO.** File upload does NOT auto-populate TM entries.

**TM population happens via:**
1. **Manual TM upload** -- `TMManager.upload_tm()` in `tm_manager.py` (TXT, XML, Excel files parsed and bulk-inserted)
2. **Auto-add on row confirm** -- FEAT-001 (when status = "reviewed")
3. **Manual entry add** -- `POST /api/ldm/tm/{tm_id}/entries`

The `file_service.py` does not exist (returned file not found), and row upload goes through `rows.py` which only adds to TM on status="reviewed".

**Confidence:** HIGH

---

## Question 3: TM Search Cascade (5-Tier, not 6)

**Answer: 5-Tier Cascade** (not 6)

**File:** `server/tools/ldm/indexing/searcher.py`

| Tier | Name | Method | Speed | What It Returns |
|------|------|--------|-------|-----------------|
| **1** | Perfect Whole Match | Hash lookup (`whole_lookup.pkl`) | O(1) | Exact match with score=1.0 |
| **2** | Whole Embedding Match | FAISS HNSW (`whole.index`) | ~1ms | Top-K similar whole texts >= threshold |
| **3** | Perfect Line Match | Hash lookup (`line_lookup.pkl`) | O(1) per line | Exact line-by-line matches score=1.0 |
| **4** | Line Embedding Match | FAISS HNSW (`line.index`) | ~1ms per line | Top-K similar lines >= threshold |
| **5** | N-gram Fallback | Character trigram Jaccard | O(N) | Top-K n-gram similar >= threshold |

**Cascade logic:** Stops at the first tier that returns results. If Tier 1 returns a perfect match, Tiers 2-5 are never executed.

**Default threshold:** 0.92 (92%) for matching, configurable per-user via preferences.
**NPC threshold:** 0.65 (65%) for Neil's Probabilistic Check (translation consistency verification).

**Normalization pipeline:**
- `normalize_for_hash()`: Universal newlines (br tags, escaped, Windows) -> lowercase -> whitespace normalize
- `normalize_for_embedding()`: Universal newlines -> basic whitespace cleanup (less aggressive)

**Confidence:** HIGH

---

## Question 4: FAISS Index Update on ADD

**Answer: Supports both incremental add AND full rebuild.**

**File:** `server/tools/ldm/indexing/sync_manager.py`

### Incremental Add (PERF-001)
Used when: INSERT-only changes (no UPDATE, no DELETE), and existing index exists.

```python
can_incremental = (
    stats['update'] == 0 and stats['delete'] == 0 and stats['insert'] > 0 and
    faiss_index_path.exists() and pkl_state is not None and
    pkl_state.get("embeddings") is not None
)
```

Process:
1. Embed only new entries using Model2Vec
2. `np.vstack()` existing + new embeddings
3. `FAISSManager.incremental_add()` -- loads existing index, adds new vectors, saves
4. Update hash lookups (append to existing PKL dicts)
5. Save updated metadata

**This is effectively instant for small adds** -- Model2Vec encodes at ~29k sentences/sec.

### Full Rebuild
Used when: UPDATE or DELETE detected.

Process:
1. Compute diff (DB vs PKL using pandas merge on source_normalized)
2. Reuse cached embeddings for UNCHANGED entries (dimension check first)
3. Re-embed only INSERT + UPDATE entries
4. `FAISSManager.build_index()` -- creates brand new HNSW index from all vectors
5. Rebuild all hash lookups from scratch

**Confidence:** HIGH

---

## Question 5: FAISS Handle DELETED TM Entries

**Answer: HNSW does NOT support vector removal. Full rebuild required.**

FAISS `IndexHNSWFlat` has no `remove_ids()` method. When a DELETE is detected in the diff:

```python
if stats['update'] > 0 or stats['delete'] > 0:
    logger.info("Full rebuild required (UPDATE/DELETE detected)")
```

The full rebuild path:
1. Takes all UNCHANGED + INSERT + UPDATE entries
2. Reuses cached embeddings for UNCHANGED (avoids re-encoding)
3. Generates new embeddings for INSERT/UPDATE
4. Builds completely new FAISS index from combined vectors
5. Rebuilds all hash lookups

**Key insight:** Even during full rebuild, existing embeddings for unchanged entries are **reused** (not re-generated), so the expensive step is only the FAISS index construction, not the embedding generation.

**Confidence:** HIGH

---

## Question 6: FAISS Index Configuration

**File:** `server/tools/shared/faiss_manager.py`

| Parameter | Value | Purpose |
|-----------|-------|---------|
| **Index type** | `IndexHNSWFlat` | HNSW graph index on flat vectors |
| **Metric** | `METRIC_INNER_PRODUCT` | Cosine similarity (vectors are normalized) |
| **Dimension** | 256 (Model2Vec) or 1024 (Qwen) | Depends on active engine |
| **HNSW_M** | 32 | Connections per layer |
| **HNSW_EF_CONSTRUCTION** | 400 | Build-time accuracy |
| **HNSW_EF_SEARCH** | 500 | Search-time accuracy |

**Storage structure per TM:**
```
server/data/ldm_tm/{tm_id}/
├── metadata.json           # TM metadata, sync timestamps, entry counts
├── hash/
│   ├── whole_lookup.pkl    # Tier 1: source_normalized -> entry_data
│   └── line_lookup.pkl     # Tier 3: line_normalized -> line_data
├── embeddings/
│   ├── whole.npy           # Whole-text embedding matrix (N x dim)
│   ├── whole_mapping.pkl   # Index -> entry_id/source/target mapping
│   ├── line.npy            # Line-by-line embedding matrix
│   └── line_mapping.pkl    # Index -> line mapping
└── faiss/
    ├── whole.index         # Tier 2: FAISS HNSW for whole texts
    └── line.index          # Tier 4: FAISS HNSW for individual lines
```

**Normalization:** All vectors are L2-normalized before storage and search (cosine similarity via inner product).

**Confidence:** HIGH

---

## Question 7: Model2Vec for TM Embeddings

**Answer: YES, Model2Vec is the default TM embedding engine.**

**File:** `server/tools/shared/embedding_engine.py`

| Engine | Model | Dimension | Speed | Memory | Default |
|--------|-------|-----------|-------|--------|---------|
| **Model2Vec** | `minishlab/potion-multilingual-128M` | 256 | 79x faster | ~128MB | YES |
| **Qwen** | `Qwen/Qwen3-Embedding-0.6B` | 1024 | Baseline | ~2.3GB | No (opt-in) |

**Key details:**
- Engine selection is stored per-user in settings
- `get_current_engine_name()` returns the active engine ("model2vec" or "qwen")
- In **Light Mode** (no torch/sentence-transformers): ONLY Model2Vec available
- Engines are lazy-loaded (first use triggers model load)
- `Model2VecModelAdapter` provides SentenceTransformer-compatible interface for legacy code
- Embedding dimension mismatch detection: if cached embeddings have different dim than current model, full re-embedding occurs

**Confidence:** HIGH

---

## Question 8: Offline/SQLite Mode TM Support

**Answer: YES, full TM search works offline via FAISS.**

**File:** `server/repositories/sqlite/tm_repo.py` (LIMIT-001)

**How it works:**
1. TM indexes must be **pre-built** before going offline (built while online, stored in `server/data/ldm_tm/`)
2. `search_similar()` uses `TMSearcher` with FAISS indexes (same 5-tier cascade)
3. Indexes are loaded on-demand and cached in-memory (thread-safe, max 10 TMs)
4. LRU-style eviction when cache is full
5. Results are transformed to PostgreSQL-compatible format for consistent API responses

**Limitations in offline mode:**
- `search_similar()` in PostgreSQL uses `pg_trgm` extension -- SQLite falls back to FAISS instead
- Auto-sync of indexes after entry modifications: `TODO: Add index sync for SQLite mode` (line 201-202 in `tm_entries.py`)
- TM entries can be added/edited offline, but index sync may need manual trigger

**Confidence:** HIGH

---

## Question 9: Right Panel Tabs

**File:** `locaNext/src/lib/components/ldm/RightPanel.svelte`

| # | Tab ID | Label | Icon | Component |
|---|--------|-------|------|-----------|
| 1 | `tm` | TM | DataBase | `TMTab.svelte` |
| 2 | `image` | Image | Image | `ImageTab.svelte` |
| 3 | `audio` | Audio | Music | `AudioTab.svelte` |
| 4 | `context` | AI Context | MachineLearningModel | `ContextTab.svelte` |
| 5 | `ai-suggest` | AI Suggest | AiRecommend | `AISuggestionsTab.svelte` |

**Plus persistent footer:** `QAFooter.svelte` (QA issues, always visible regardless of active tab)

Default active tab: `tm`

**Confidence:** HIGH

---

## Question 10: When Does FAISS Index Get Built?

**Answer: Explicitly triggered, not automatic.**

### Build Methods:

1. **Manual build via API:** `POST /api/ldm/tm/{tm_id}/build-indexes`
   - Triggered from UI when user clicks "Build Indexes"
   - Runs in threadpool, tracked via `TrackedOperation` (progress bar in Task Manager)
   - Creates all 4 index types (whole_hash, line_hash, whole_faiss, line_faiss)

2. **Auto-sync after entry modifications:** `_auto_sync_tm_indexes()` background task
   - Triggered after: add entry, update entry, delete entry, row auto-add (FEAT-001)
   - Uses `TMSyncManager.sync()` -- smart diff (incremental if INSERT-only, full rebuild if UPDATE/DELETE)
   - Silent operation (no toast notification)
   - `TASK-002` tracked but `silent=True`

3. **Manual sync via API:** `POST /api/ldm/tm/{tm_id}/sync`
   - User-triggered from UI
   - Shows toast notification
   - Same `TMSyncManager.sync()` logic

### NOT built:
- **Not at server startup** -- FAISS is lazy-imported (`_faiss = None`)
- **Not on first search** -- if indexes don't exist, search returns empty results
- **Not on TM upload** -- `TMManager.upload_tm()` sets status to "ready" but does NOT build indexes

### Index Lifecycle:
```
TM Upload → status="ready" (NO indexes yet)
User clicks "Build Indexes" → TMIndexer.build_indexes() → status="ready" (indexes exist)
User edits entry → _auto_sync_tm_indexes → TMSyncManager.sync() → indexes updated
User confirms row (reviewed) → auto-add to TM → _auto_sync_tm_indexes → indexes updated
```

**Confidence:** HIGH

---

## TM Search Flow (End-to-End)

```
User selects row in grid
  → LDM.svelte handleRowSelect()
    → loadTMMatchesForRow(row)
      → GET /api/ldm/tm/suggest?source=...&threshold=0.50&max_results=5
        → tm_search.py get_tm_suggestions()
          → If tm_id provided:
              → tm_repo.search_similar(tm_id, source, threshold, max_results)
                → [PostgreSQL] pg_trgm similarity search
                → [SQLite] FAISS TMSearcher 5-tier cascade
          → Else:
              → row_repo.suggest_similar() (search within project rows)
        → Return suggestions to UI
      → sidePanelTMMatches = data.suggestions
    → TMTab.svelte renders matches with color-coded badges
```

**Key: TM search is triggered on every row selection in the grid.** Uses the `/api/ldm/tm/suggest` endpoint. The threshold is configurable per-user via preferences (default 0.50 for suggest, 0.92 for cascade matching).

---

## Auto-Sync Architecture Diagram

```
Entry Modified (add/update/delete/FEAT-001)
  │
  ├── BackgroundTask: _auto_sync_tm_indexes(tm_id, user_id)
  │     │
  │     └── TMSyncManager(db, tm_id).sync()
  │           │
  │           ├── 1. Load DB entries (source of truth)
  │           ├── 2. Load PKL state (local cache)
  │           ├── 3. Compute diff (pandas merge on source_normalized)
  │           │     ├── INSERT: in DB, not in PKL
  │           │     ├── UPDATE: in both, target changed
  │           │     ├── DELETE: in PKL, not in DB
  │           │     └── UNCHANGED: same source and target
  │           │
  │           ├── 4a. INSERT-only? → Incremental FAISS add (fast)
  │           │     ├── Embed only new entries
  │           │     ├── FAISSManager.incremental_add()
  │           │     └── Append to hash lookups
  │           │
  │           ├── 4b. UPDATE/DELETE? → Full rebuild
  │           │     ├── Reuse cached embeddings for UNCHANGED
  │           │     ├── Re-embed INSERT + UPDATE entries
  │           │     ├── FAISSManager.build_index() (new HNSW)
  │           │     └── Rebuild all hash lookups
  │           │
  │           └── 5. Save metadata (synced_at timestamp)
  │
  └── TM status updated to "ready"
```

---

## Sources

All findings verified from source code:
- `server/tools/ldm/routes/rows.py` -- FEAT-001 auto-add logic
- `server/tools/ldm/routes/tm_entries.py` -- `_auto_sync_tm_indexes`
- `server/tools/ldm/routes/tm_indexes.py` -- Build/sync endpoints
- `server/tools/ldm/routes/tm_search.py` -- Suggest endpoint
- `server/tools/ldm/indexing/indexer.py` -- TMIndexer (build all indexes)
- `server/tools/ldm/indexing/searcher.py` -- TMSearcher (5-tier cascade)
- `server/tools/ldm/indexing/sync_manager.py` -- TMSyncManager (diff + incremental/full sync)
- `server/tools/ldm/indexing/utils.py` -- Normalization functions
- `server/tools/ldm/tm_manager.py` -- TM upload and parsing
- `server/tools/shared/faiss_manager.py` -- FAISSManager (HNSW config)
- `server/tools/shared/embedding_engine.py` -- Model2Vec/Qwen engines
- `server/repositories/interfaces/tm_repository.py` -- TM repo interface
- `server/repositories/sqlite/tm_repo.py` -- SQLite TM with FAISS search
- `locaNext/src/lib/components/ldm/RightPanel.svelte` -- 5 tabs
- `locaNext/src/lib/components/ldm/TMTab.svelte` -- TM matches display
- `locaNext/src/lib/components/apps/LDM.svelte` -- Row selection -> TM search trigger
