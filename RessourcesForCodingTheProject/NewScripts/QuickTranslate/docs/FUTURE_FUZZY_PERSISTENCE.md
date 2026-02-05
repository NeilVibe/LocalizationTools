# Future Update: Fuzzy Matching Persistence & Auto-Update

**Status:** PLANNED
**Priority:** Medium
**Reference:** LocaNext embedding update logic

---

## Current State (v3.4.0)

| Feature | Status |
|---------|--------|
| Embeddings storage | In-memory only |
| Persistence | None (lost on restart) |
| Auto-update | None |
| First-run time | ~30-60 seconds per folder |

**Problem:** Every app restart requires rebuilding the FAISS index from scratch.

---

## Planned Changes

### 1. Persistent Embedding Storage

Store pre-computed embeddings in NPY/PKL files:

```
QuickTranslate/
├── embeddings_cache/
│   ├── languagedata_ENG.npy      # 768-dim float32 embeddings
│   ├── languagedata_ENG.pkl      # Entry metadata (StringID, StrOrigin, file_path)
│   ├── languagedata_ENG.meta     # Version hash, timestamp, count
│   ├── languagedata_FRE.npy
│   ├── languagedata_FRE.pkl
│   ├── languagedata_FRE.meta
│   └── ...
```

**File formats:**
- `.npy` - NumPy array of embeddings (N x 768, float32)
- `.pkl` - Pickle of entry list with StringID, StrOrigin, source_file
- `.meta` - JSON with version hash, file mtime, entry count

### 2. Auto-Update Logic

**Reference:** LocaNext's `server/ml/embedding_manager.py`

```python
def check_embeddings_need_update(target_file: Path, cache_dir: Path) -> bool:
    """
    Check if cached embeddings are stale.

    Update needed if:
    1. Cache files don't exist
    2. Target file mtime > cache file mtime
    3. Target file hash != cached hash
    4. Entry count changed
    """
    meta_file = cache_dir / f"{target_file.stem}.meta"

    if not meta_file.exists():
        return True  # No cache

    meta = json.loads(meta_file.read_text())

    # Check mtime
    target_mtime = target_file.stat().st_mtime
    if target_mtime > meta["cached_at"]:
        return True  # Target newer than cache

    # Check hash (first 1000 chars of file for speed)
    current_hash = compute_quick_hash(target_file)
    if current_hash != meta["content_hash"]:
        return True  # Content changed

    return False  # Cache is valid
```

### 3. Startup Flow

```
APP STARTUP
    ↓
CHECK embeddings_cache/ EXISTS?
    ↓
FOR EACH languagedata_*.xml in LOC folder:
    ├── Cache exists AND up-to-date? → LOAD from NPY/PKL
    └── Cache missing OR stale? → REBUILD and SAVE
    ↓
LOAD ALL into FAISS index
    ↓
READY (fast queries)
```

### 4. Background Update

When target folder changes or on periodic check:

```python
async def update_embeddings_if_needed(loc_folder: Path):
    """Background task to update stale embeddings."""
    for xml_file in loc_folder.glob("languagedata_*.xml"):
        if check_embeddings_need_update(xml_file, CACHE_DIR):
            logger.info(f"Updating embeddings for {xml_file.name}")
            await rebuild_embeddings_async(xml_file)
```

### 5. Incremental Updates (Future)

For large files, support incremental embedding updates:

1. Track StringIDs in cache
2. On update, find new/modified/deleted entries
3. Only re-encode changed entries
4. Merge into existing index

---

## Implementation Tasks

| Task | Effort | Priority |
|------|--------|----------|
| Create `embeddings_cache/` directory structure | Small | High |
| Implement `save_embeddings_to_cache()` | Medium | High |
| Implement `load_embeddings_from_cache()` | Medium | High |
| Implement `check_embeddings_need_update()` | Small | High |
| Add startup cache loading | Medium | High |
| Add background update thread | Medium | Medium |
| Incremental updates | Large | Low |

---

## Files to Modify

| File | Changes |
|------|---------|
| `config.py` | Add `EMBEDDINGS_CACHE_DIR` constant |
| `core/fuzzy_matching.py` | Add cache save/load/check functions |
| `gui/app.py` | Add startup cache loading, status display |

---

## Benefits

| Metric | Before | After |
|--------|--------|-------|
| First startup | 30-60 sec | 2-5 sec (load from cache) |
| Restart time | 30-60 sec | 2-5 sec |
| Memory usage | Same | Same (still in-memory for queries) |
| Disk usage | 0 | ~50-100 MB per language |

---

## LocaNext Reference

Check these files for embedding persistence patterns:

```
locaNext/server/ml/
├── embedding_manager.py    # Cache management
├── faiss_index.py          # Index persistence
└── semantic_search.py      # Search with cached embeddings
```

Key patterns to copy:
- Hash-based staleness check
- Async background updates
- Graceful fallback on cache corruption

---

*Document created: 2026-02-05*
*Last updated: 2026-02-05*
