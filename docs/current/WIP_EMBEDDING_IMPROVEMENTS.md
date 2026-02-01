# WIP: Embedding/Indexing Improvements Plan

> **Status:** Planning
> **Created:** 2026-02-01
> **Last Updated:** 2026-02-01
> **Owner:** TBD

---

## Overview

This document outlines planned improvements to the LocaNext TM embedding and indexing system. The goal is to improve the user experience by automating index management and reducing manual intervention.

**IMPORTANT TERMINOLOGY:**
- **Embedding** = Converting text → dense vectors (256/1024 dims) via EmbeddingEngine
- **FAISS Index** = Building searchable HNSW structure from embeddings via FAISSManager
- **Build Indexes** = The combined operation: Embedding + FAISS Index + Hash Lookups
- These are **SEPARATE steps** in code but **COUPLED in practice** (build_indexes does both)

---

## 1. Current State (What Works Now)

### 1.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  REPOSITORY PATTERN (Database Abstraction)                                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│   TMRepository (Interface)          ←── Routes ONLY use this                    │
│         │                                                                        │
│         ├── PostgreSQLTMRepository  ←── Online: ldm_* tables                    │
│         └── SQLiteTMRepository      ←── Offline: offline_* OR ldm_* tables      │
│                   │                                                              │
│                   └── SchemaMode: OFFLINE | SERVER                              │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│  INDEXING LAYER (Local Files - Always On User's Machine)                        │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│   TMIndexer                         ←── Orchestrates embedding + indexing       │
│         │                                                                        │
│         ├── EmbeddingEngine         ←── Text → vectors (Model2Vec or Qwen)      │
│         ├── FAISSManager            ←── Vectors → HNSW index                    │
│         └── Hash Lookups            ←── Exact match dictionaries                │
│                                                                                  │
│   Storage: server/data/ldm_tm/{tm_id}/                                          │
│   ├── embeddings/whole.npy, line.npy                                            │
│   ├── faiss/whole.index, line.index                                             │
│   └── hash/whole_lookup.pkl, line_lookup.pkl                                    │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Repository Pattern (ARCH-001)

**Location:** `server/repositories/`

The repository pattern provides complete database abstraction. Routes NEVER access the database directly - they use repository interfaces.

```python
# Interface definition (server/repositories/interfaces/tm_repository.py)
class TMRepository(ABC):
    """Contract that both PostgreSQL and SQLite must implement."""
    
    @abstractmethod
    async def get(self, tm_id: int) -> Optional[Dict[str, Any]]: ...
    
    @abstractmethod
    async def get_all_entries(self, tm_id: int) -> List[Dict[str, Any]]: ...
    
    @abstractmethod
    async def add_entries_bulk(self, tm_id: int, entries: List) -> int: ...
    # ... 30+ methods for TM operations

# PostgreSQL implementation (server/repositories/postgresql/tm_repo.py)
class PostgreSQLTMRepository(TMRepository):
    def __init__(self, db: AsyncSession, current_user: dict):
        self.db = db
        self.user_id = current_user.get("id")
    
    async def get_all_entries(self, tm_id: int) -> List[Dict]:
        # Uses SQLAlchemy ORM with ldm_tm_entries table
        ...

# SQLite implementation (server/repositories/sqlite/tm_repo.py)
class SQLiteTMRepository(SQLiteBaseRepository, TMRepository):
    def __init__(self, schema_mode: SchemaMode = SchemaMode.OFFLINE):
        super().__init__(schema_mode)
    
    async def get_all_entries(self, tm_id: int) -> List[Dict]:
        # Uses aiosqlite with offline_tm_entries OR ldm_tm_entries
        table = self._table("tm_entries")  # Schema-aware table name
        ...
```

**Benefits:**
- Routes are database-agnostic
- Offline parity: same API works online and offline
- Testing: can mock repositories easily
- Permissions: baked INTO PostgreSQL repository, not in routes

### 1.3 Factory Pattern - 3-Mode Detection

**Location:** `server/repositories/factory.py`

The factory automatically selects the correct repository based on the current mode.

```python
def get_tm_repository(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
) -> TMRepository:
    """
    3-Mode Detection:
    1. Offline mode (header)   → SQLiteRepo(OFFLINE) → offline_* tables
    2. SQLite fallback         → SQLiteRepo(SERVER)  → ldm_* tables  
    3. PostgreSQL available    → PostgreSQLRepo      → ldm_* tables
    """
    if _is_offline_mode(request):
        # Header: "Bearer OFFLINE_MODE_..."
        return SQLiteTMRepository(schema_mode=SchemaMode.OFFLINE)
    elif _is_sqlite_fallback():
        # config.ACTIVE_DATABASE_TYPE == "sqlite"
        return SQLiteTMRepository(schema_mode=SchemaMode.SERVER)
    else:
        return PostgreSQLTMRepository(db, current_user)
```

**3 Modes Explained:**

| Mode | Trigger | Repository | Tables | Use Case |
|------|---------|------------|--------|----------|
| **Offline** | Auth header starts with `OFFLINE_MODE_` | SQLiteTMRepository(OFFLINE) | offline_* | Electron app offline |
| **SQLite Fallback** | `config.ACTIVE_DATABASE_TYPE == "sqlite"` | SQLiteTMRepository(SERVER) | ldm_* | Server with no PostgreSQL |
| **PostgreSQL** | Default when PostgreSQL available | PostgreSQLTMRepository | ldm_* | Normal online operation |

**Schema Mode (SQLite only):**
- `SchemaMode.OFFLINE` → Uses `offline_platforms`, `offline_tm_entries`, etc.
- `SchemaMode.SERVER` → Uses `ldm_platforms`, `ldm_tm_entries`, etc.

### 1.4 How Embedding/Indexing Works with Repositories

The indexing layer uses the **synchronous SQLAlchemy session** (not async repositories) because:
1. Embedding is CPU-intensive and runs in background threads
2. FAISS operations are synchronous (C++ library)
3. Index files are LOCAL (not synced to server)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  INDEXING FLOW                                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. Route calls:  POST /ldm/tm/{tm_id}/indexes/build                        │
│           │                                                                  │
│           ▼                                                                  │
│  2. Route uses:   TMRepository.get(tm_id)  ←── Async, mode-aware            │
│           │       TMRepository.get_all_entries(tm_id)                        │
│           │                                                                  │
│           ▼                                                                  │
│  3. Background:   TMIndexer.build_indexes(tm_id)  ←── Sync, local files     │
│           │                                                                  │
│           ├── Loads entries from DB (sync session)                          │
│           ├── EmbeddingEngine.encode(texts) → .npy files                    │
│           ├── FAISSManager.build_index() → .index files                     │
│           └── Hash lookups → .pkl files                                     │
│                                                                              │
│  4. Storage:      server/data/ldm_tm/{tm_id}/ (LOCAL, not in DB)            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Key Insight:** TM *entries* are in the database (synced online/offline). TM *indexes* are local files (never synced - rebuilt when needed).

### 1.5 Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `TMRepository` | `server/repositories/interfaces/tm_repository.py` | Interface for TM operations |
| `PostgreSQLTMRepository` | `server/repositories/postgresql/tm_repo.py` | PostgreSQL implementation |
| `SQLiteTMRepository` | `server/repositories/sqlite/tm_repo.py` | SQLite implementation (dual schema) |
| `EmbeddingEngine` | `server/tools/shared/embedding_engine.py` | **EMBEDDING**: Text → vectors |
| `FAISSManager` | `server/tools/shared/faiss_manager.py` | **INDEXING**: Vectors → HNSW index |
| `TMIndexer` | `server/tools/ldm/indexing/indexer.py` | **ORCHESTRATOR**: Calls both |
| `TMSyncManager` | `server/tools/ldm/indexing/sync_manager.py` | **SMART SYNC**: Incremental updates |

### 1.6 Embedding Engines

**Two independent embedding engines:**

| Engine | Model | Dimension | Speed | Memory | Status |
|--------|-------|-----------|-------|--------|--------|
| **Model2Vec** | `minishlab/potion-multilingual-128M` | 256 | 79x faster | 128 MB | DEFAULT |
| **Qwen** | `Qwen/Qwen3-Embedding-0.6B` | 1024 | Slower | 2.3 GB | Opt-in |

**Engine Abstraction:**
```python
# server/tools/shared/embedding_engine.py

class EmbeddingEngine(ABC):
    @abstractmethod
    def encode(texts) -> np.ndarray: ...  # Returns (N, dim) float32
    @property
    def dimension(self) -> int: ...       # 256 or 1024

class Model2VecEngine(EmbeddingEngine):   # Fast, lightweight
    dimension = 256

class QwenEngine(EmbeddingEngine):        # Deep semantic
    dimension = 1024
```

**Switching Engines:**
```
POST /settings/embedding-engine {"engine": "qwen"}
    ↓
Global _current_engine_name = "qwen"
    ↓
Next TM sync: dimension mismatch detected (256 ≠ 1024)
    ↓
Force RE-EMBED ALL entries with new engine
    ↓
Rebuild FAISS index with new dimension
    ↓
Update metadata.json: embedding_dim=1024, model="Qwen"
```

### 1.7 WHOLE vs LINE Embeddings (Dual Indexing)

**Two parallel embedding systems per TM:**

| Type | What It Embeds | Use Case |
|------|----------------|----------|
| **WHOLE** | Full source_text as single vector | Paragraph/sentence matching |
| **LINE** | Each line split by `\n` separately | Structured data, lists, dialogs |

**5-Tier Cascade Search:**
```
Query → Tier 1: Perfect WHOLE match (hash, 100%)
     ↓ (no match)
     → Tier 2: WHOLE embedding (FAISS, ≥92%)
     ↓ (no match)
     → Tier 3: Perfect LINE match (hash, 100%)
     ↓ (no match)
     → Tier 4: LINE embedding (FAISS, ≥92%)
     ↓ (no match)
     → Tier 5: N-gram fallback (≥92%)
```

**Storage per TM:**
```
server/data/ldm_tm/{tm_id}/
├── embeddings/
│   ├── whole.npy           ← Full text vectors
│   ├── whole_mapping.pkl   ← entry_id, source, target
│   ├── line.npy            ← Per-line vectors
│   └── line_mapping.pkl    ← entry_id, line_num, source_line, target_line
├── faiss/
│   ├── whole.index         ← HNSW for Tier 2
│   └── line.index          ← HNSW for Tier 4
└── hash/
    ├── whole_lookup.pkl    ← Tier 1 exact match
    └── line_lookup.pkl     ← Tier 3 exact match
```

### 1.8 Current Triggers

| Trigger | Action | Notes |
|---------|--------|-------|
| Manual "Build Indexes" button | Full embed+index via `TMIndexer.build_indexes()` | User-initiated, creates all files |
| Manual "Sync" button | Smart sync via `TMSyncManager.sync()` | User-initiated, diff-based |
| Entry ADD | Background auto-sync via `_auto_sync_tm_indexes()` | Incremental: only new entries embedded |
| Entry UPDATE | Background auto-sync via `_auto_sync_tm_indexes()` | Full rebuild (can't update vectors in-place) |
| Entry DELETE | Background auto-sync via `_auto_sync_tm_indexes()` | Full rebuild (FAISS can't remove vectors) |

**Note:** Auto-sync only works if indexes already exist. First-time build is still manual.

### 1.9 Sync Modes

1. **Full Rebuild** - Used when:
   - No existing indexes
   - UPDATE or DELETE detected
   - Embedding dimension mismatch

2. **Incremental Add (PERF-001)** - Used when:
   - Only INSERTs detected
   - Existing FAISS index available
   - Uses `FAISSManager.incremental_add()` to append vectors

---

## 2. Gaps Identified

### 2.1 First-Time Auto-Build Missing

**Problem:** When a TM is created (via file upload), embeddings and FAISS indexes are NOT built automatically. Users must manually click "Build Indexes" before semantic TM search works.

**Current flow:**
```
1. User uploads TXT/TMX file
2. Entries stored in database (via TMRepository.add_entries_bulk) ✓
3. TM status = "ready", indexed_at = NULL
4. USER MUST CLICK "Build Indexes" ← Manual step required
   └─ This triggers: EmbeddingEngine.encode() + FAISSManager.build_index()
5. Only then can 5-Tier Cascade semantic search work
```

**User impact:**
- New users don't know they need to build indexes
- Semantic TM search returns empty results until indexed
- Confusing UX: "I imported my TM, why doesn't fuzzy search work?"

### 2.2 Delete Handling Requires Full Rebuild

**Problem:** When entries are deleted, `TMSyncManager` cannot do incremental updates because FAISS HNSW doesn't support vector removal. A full rebuild is triggered instead.

**Performance impact:**
- Delete 1 entry from 100k TM → Full rebuild of 100k embeddings
- Takes minutes instead of seconds
- Blocking operation during sync

### 2.3 Login/Startup Maintenance Missing

**Problem:** No automatic check for stale indexes on user login or app startup. If the database was modified externally (multi-user scenario), local indexes become stale.

**Multi-user scenario:**
```
User A: Adds 1000 entries to TM via web interface
User B: Opens desktop app → Local indexes are stale → Search misses new entries
```

---

## 3. Proposed Improvements

### 3.1 Auto-Build on TM Creation (Background)

**Goal:** Automatically trigger `build_indexes()` when a TM is created or imported.

**Implementation:**

```python
# In TM upload route:
@router.post("/tm/upload")
async def upload_tm(..., background_tasks: BackgroundTasks):
    tm = await tm_repo.create(...)
    await tm_repo.add_entries_bulk(tm.id, entries)
    
    # NEW: Trigger background build
    if entry_count > 0:
        background_tasks.add_task(_auto_build_indexes, tm.id, user_id)
    
    return tm

async def _auto_build_indexes(tm_id: int, user_id: int):
    """Background: builds embeddings + FAISS indexes."""
    indexer = TMIndexer(db)
    indexer.build_indexes(tm_id)
```

**Status indicators:**
- `ready` (indexed_at=NULL) → TM uploaded, build not started
- `indexing` → Background build in progress
- `ready` (indexed_at set) → Build complete, semantic search available

### 3.2 Optimized Delete Handling

**Goal:** Avoid full rebuilds for single-entry deletes using soft delete approach.

**Option A: Soft Delete with Periodic Compaction**
```python
class TMSyncManager:
    COMPACTION_THRESHOLD = 0.1  # 10% deleted triggers rebuild
    
    def mark_deleted(self, entry_ids: List[int]):
        """Mark entries as deleted without rebuilding."""
        # Update mapping.pkl with deleted=True flag
        # Search filters out deleted entries
        
    def needs_compaction(self) -> bool:
        """Check if deleted ratio exceeds threshold."""
        deleted = sum(1 for e in mapping if e.get("deleted"))
        return deleted / len(mapping) > self.COMPACTION_THRESHOLD
```

### 3.3 Periodic Maintenance Triggers

**Trigger Points:**

| Trigger | Action | Priority |
|---------|--------|----------|
| User login | Check stale TMs, queue sync | P1 |
| App startup | Validate index integrity | P1 |
| Every N minutes (idle) | Check for pending syncs | P2 |
| Before TM search | Quick staleness check | P3 |

---

## 4. Action Items

### Priority 1 (Critical)

| ID | Task | Estimate | Notes |
|----|------|----------|-------|
| EMB-001 | Auto-build on TM upload | 4h | Add background task calling `build_indexes()` |
| EMB-002 | TM status indicator in UI | 2h | Show "building..." spinner, check `indexed_at` |
| EMB-003 | Login-time stale check | 3h | Compare `indexed_at` vs `updated_at`, trigger sync |

### Priority 2 (Important)

| ID | Task | Estimate | Notes |
|----|------|----------|-------|
| EMB-004 | Soft delete for mapping | 4h | Avoid full rebuild on delete |
| EMB-005 | Compaction threshold | 2h | Auto-rebuild when 10% deleted |
| EMB-006 | Startup index validation | 2h | Check integrity on boot |

### Priority 3 (Nice to Have)

| ID | Task | Estimate | Notes |
|----|------|----------|-------|
| EMB-007 | Periodic idle sync | 3h | Background task scheduler |
| EMB-008 | Pre-search staleness check | 1h | Quick check before 5-Tier |
| EMB-009 | Index health dashboard | 4h | Admin view of all TM indexes |

---

## 5. Implementation Notes

### 5.1 Files to Modify

```
server/repositories/
├── interfaces/tm_repository.py   # Already has get_all_entries, get_indexes
├── postgresql/tm_repo.py         # Implements interface
└── sqlite/tm_repo.py             # Implements interface

server/tools/ldm/
├── indexing/
│   ├── indexer.py         # Add auto-index trigger
│   ├── sync_manager.py    # Add soft delete support
│   └── maintenance.py     # NEW: Maintenance manager
├── routes/
│   ├── projects.py        # Trigger auto-index on import
│   └── tm_indexes.py      # Add maintenance endpoints
└── tm.py                  # Update TM status handling

server/api.py              # Add login hook for stale check
```

### 5.2 Database Changes

None required - using existing fields:
- `LDMTranslationMemory.status` - Already supports "pending", "indexing", "ready", "error"
- `LDMTranslationMemory.indexed_at` - Timestamp of last index build
- `LDMTranslationMemory.updated_at` - Timestamp of last DB change

### 5.3 Testing Strategy

1. **Unit tests:**
   - `test_auto_index_on_create.py` - Verify background task triggered
   - `test_soft_delete.py` - Verify mapping updates without rebuild
   - `test_staleness_check.py` - Verify stale detection logic

2. **Integration tests:**
   - Full TM create → auto-index → search flow
   - Delete entry → verify search excludes → compaction

3. **E2E tests:**
   - User imports TM → waits for indexing → search works
   - Multi-user scenario with sync verification

---

## 6. Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Background indexing slows down import | High | Use worker thread, show progress |
| Soft delete increases search time | Medium | Periodic compaction, lazy filtering |
| Login sync storms (many stale TMs) | Medium | Limit concurrent syncs, prioritize recent |
| Index corruption after crash | Low | Integrity check on startup |

---

## 7. Success Metrics

- **Time to first search** after TM import: Target < 30s for 10k entries
- **Delete handling overhead**: Target < 100ms per delete (no full rebuild)
- **Stale index rate**: Target < 5% of TMs stale at any time

---

## References

- [Architecture Summary](../architecture/ARCHITECTURE_SUMMARY.md)
- [Repository Factory](../../server/repositories/factory.py)
- [TM Repository Interface](../../server/repositories/interfaces/tm_repository.py)
- [TM Indexer Source](../../server/tools/ldm/indexing/indexer.py)
- [FAISS Manager Source](../../server/tools/shared/faiss_manager.py)
- [Embedding Engine Source](../../server/tools/shared/embedding_engine.py)

---

*This is a WIP document. Update as implementation progresses.*
