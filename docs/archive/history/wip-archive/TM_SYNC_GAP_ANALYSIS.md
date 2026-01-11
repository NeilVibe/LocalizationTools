# TM Sync Protocol - Gap Analysis

**Created:** 2025-12-18 | **Status:** ALL GAPS FIXED

---

## Summary

**P25 Design:** DB updates instant, FAISS syncs on-demand via [Synchronize TM] button
**Status:** FULLY IMPLEMENTED (Build 298)

---

## Architecture (Implemented)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  DB = CENTRAL SOURCE OF TRUTH (always up-to-date)                       │
│  FAISS = LOCAL INDEX (synced on demand)                                 │
│                                                                          │
│  DB updates happen AUTOMATICALLY:                                       │
│  - Edit TM entry → DB updates instantly (438ms)                        │
│  - Add TM entry → DB updates instantly                                  │
│  - Delete TM entry → DB updates instantly                               │
│  - Ctrl+S confirm string → DB updates instantly (if TM active)          │
│                                                                          │
│  FAISS sync happens ON DEMAND:                                          │
│  - User clicks [Sync Indexes] button in TMDataGrid                      │
│  - Pulls changes from DB → INSERT/UPDATE/DELETE locally                 │
│  - Re-embeds new/changed entries only (smart diff)                      │
│  - Rebuilds FAISS index at the end                                      │
│  - ~31s first time (model load), ~2s subsequent                        │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Status

### Backend Components - COMPLETE

| Component | Status | Implementation |
|-----------|--------|----------------|
| TMIndexer | ✅ | `tm_indexer.py` - Full rebuild |
| TMSyncManager | ✅ | `tm_indexer.py` - Smart diff sync |
| `/tm/{id}/sync` | ✅ | `api.py:1900-1974` |
| `/tm/{id}/sync-status` | ✅ | `api.py:1833-1899` |

### Frontend Components - COMPLETE

| Component | Status | Implementation |
|-----------|--------|----------------|
| TMDataGrid | ✅ | `TMDataGrid.svelte` |
| Sync Button | ✅ | "Sync Indexes" in header |
| Stale Badge | ✅ | Yellow "X pending" tag |
| Synced Badge | ✅ | Green "Synced" tag |

---

## Gap Resolution

### GAP 1: No `/tm/{id}/sync` API Endpoint - FIXED
**Implementation:** `api.py:1900-1974`
```python
@router.post("/tm/{tm_id}/sync")
async def sync_tm_indexes(tm_id: int, ...):
    sync_manager = TMSyncManager(db, tm_id)
    result = sync_manager.sync(progress_callback)
    return result
```

### GAP 2: No Stale Tracking - FIXED
**Implementation:** `api.py:1833-1899`
```python
@router.get("/tm/{tm_id}/sync-status")
async def get_tm_sync_status(tm_id: int, ...):
    # Compares tm.updated_at vs metadata.synced_at
    # Returns: is_stale, pending_changes, last_synced
```

### GAP 3: No [Synchronize TM] Button in UI - FIXED
**Implementation:** `TMDataGrid.svelte` header
- Yellow badge: "X pending" when stale
- Green badge: "Synced" when up-to-date
- "Sync Indexes" button (disabled during sync)

### GAP 4: No Stale Indicator After Edit - FIXED
**Implementation:** After saveEdit() succeeds:
- Badge immediately updates to "1 pending"
- loadSyncStatus() called to refresh count

---

## Test Results (CDP - 2025-12-18)

| Test | Result |
|------|--------|
| Edit entry → DB update | ✅ 438ms (instant) |
| Edit → Pending badge appears | ✅ "1 pending" shows |
| Click Sync Indexes | ✅ Button shows "Syncing..." |
| Sync completes | ✅ Badge changes to "Synced" |
| First sync timing | 31s (model load) |
| Subsequent sync | ~2s |

---

## API Endpoints (Complete)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/tm/{id}/entries` | GET | List entries (paginated) |
| `/tm/{id}/entries/{eid}` | PUT | Update entry (DB) |
| `/tm/{id}/entries/{eid}` | DELETE | Delete entry |
| `/tm/{id}/entries/{eid}/confirm` | POST | Toggle confirm |
| `/tm/{id}/sync-status` | GET | Check stale state |
| `/tm/{id}/sync` | POST | Smart sync to FAISS |
| `/tm/{id}/indexes/build` | POST | Full rebuild |
| `/tm/{id}/indexes/status` | GET | Index info |

---

## Architecture Note

**Why Manual Sync?**

FAISS HNSW indexes cannot be incrementally updated - they require full rebuild. The Qwen embedding model is 2.3GB and takes ~30s to load on first use. For rapid editing workflows, manual sync is optimal:

1. Edit entries → DB updates instantly (user sees changes)
2. Continue editing → No waiting for embeddings
3. When ready → Click "Sync Indexes" once
4. Pretranslation → Uses updated FAISS indexes

**Future Alternative:** Consider Typesense/Meilisearch for instant search (see FAST_SEARCH_ALTERNATIVES.md)

---

*Status: ALL GAPS FIXED | Build 298 | 2025-12-18*
