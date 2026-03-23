# Phase 62: TM Auto-Update Pipeline - Context

**Gathered:** 2026-03-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Make TM add/edit/delete operations automatically update embeddings and HNSW index inline (synchronous, ~6ms per entry), so search always returns current results with zero manual intervention. Batch imports use bulk encode + batch add. No full rebuilds needed.

</domain>

<decisions>
## Implementation Decisions

### Update Architecture (Tribunal: 4/4 for direct inline, 3/4 unanimous)
- Single add/edit: encode() + HNSW add inline in same request (~6ms on GPU)
- Batch import: asyncio.to_thread() with batch model.encode() + batch add_with_ids()
- Edit: remove old vector + add new vector (needs ID-based removal support)
- Delete: remove vector from index
- Synchronous = always consistent, no version tracking needed

### FAISS Index Strategy
- Current FAISSManager uses IndexHNSWFlat — no native remove support
- Need to either: (a) add IDMap2 wrapper for remove, or (b) mark-and-rebuild approach
- IndexIDMap2(IndexHNSWFlat(dim, M)) enables remove_ids() + add_with_ids()
- Full rebuild when deletions > 20% of index size (quality degradation guard)
- Persist with faiss.write_index() periodically, not per-operation

### Integration Points
- Hook into TMSyncManager or create a new lightweight service
- `_auto_sync_tm_indexes()` in tm_entries.py currently runs full diff as BackgroundTask — replace with inline per-entry updates
- Keep full sync as fallback (server restart, consistency recovery)

### Claude's Discretion
- Whether to modify existing TMSyncManager or create new InlineTMUpdater class
- How to handle the hash lookups (PKL files) — inline update vs keep background
- Whether to deprecate the full background sync or keep both paths
- Threading/locking strategy for concurrent access to FAISS index

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- server/tools/shared/faiss_manager.py — FAISSManager with create_index, incremental_add, search
- server/tools/ldm/indexing/indexer.py — TMIndexer with build_indexes()
- server/tools/ldm/indexing/sync_manager.py — TMSyncManager with _incremental_sync() (INSERT-only)
- server/tools/ldm/indexing/utils.py — normalize_for_hash, normalize_for_embedding
- server/tools/shared/ — get_embedding_engine(), EmbeddingEngine with encode()

### Established Patterns
- BackgroundTasks for async work after CRUD operations
- TMSyncManager.sync() does full diff (DB vs PKL via pandas merge) — heavy
- FAISSManager.incremental_add() adds vectors to existing index
- Model2Vec via EmbeddingEngine.encode() — batch-friendly, ~29k sentences/sec
- Repository pattern for TM CRUD (TMRepository interface, PG + SQLite impls)

### Integration Points
- server/tools/ldm/routes/tm_entries.py — _auto_sync_tm_indexes() called as BackgroundTask
- server/tools/ldm/routes/tm_crud.py — upload endpoint triggers trigger_auto_indexing()
- server/tools/ldm/routes/tm_search.py — semantic search uses TMSearcher
- server/tools/ldm/indexing/searcher.py — TMSearcher loads FAISS index from disk

</code_context>

<specifics>
## Specific Ideas

- The key gap: current sync is a heavy pandas-based full diff as BackgroundTask. Phase 62 adds inline per-entry updates that complete before the HTTP response returns (~6ms overhead).
- Keep full sync as a fallback for recovery/restart scenarios
- Hash lookup PKL files also need inline updates (insert/remove entries)
- Consider thread-safe wrapper around FAISS index since asyncio.to_thread() may cause concurrent access

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>
