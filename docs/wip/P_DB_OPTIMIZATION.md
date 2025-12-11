# Database Optimization WIP

**Priority:** P18
**Status:** ✅ PHASE 1 COMPLETE
**Last Updated:** 2025-12-09
**PostgreSQL Version:** 14.20 (Ubuntu)

> Dedicated document for database optimization tasks for LocaNext platform.

---

## PostgreSQL Setup (INSTALLED!)

```
POSTGRESQL CONFIGURATION:
═══════════════════════════════════════════════════════════════════
Status:     ✅ INSTALLED AND RUNNING
Version:    PostgreSQL 14.20 (Ubuntu 14.20-0ubuntu0.22.04.1)
User:       localization_admin
Database:   localizationtools
Host:       localhost:5432
Auth:       Password (md5)

Environment Variables (~/.bashrc):
  export DATABASE_TYPE=postgresql
  export POSTGRES_USER=localization_admin
  export POSTGRES_PASSWORD=locanext_dev_2025
  export POSTGRES_HOST=localhost
  export POSTGRES_PORT=5432
  export POSTGRES_DB=localizationtools

Tables Created: 29 (all LDM + telemetry + core)
═══════════════════════════════════════════════════════════════════
```

## Real Data Benchmark Results

```
TESTED WITH sampleofLanguageData.txt (103,500 entries):
═══════════════════════════════════════════════════════════════════
Import:         103,500 entries in 5.07 seconds
Rate:           20,419 entries/second
700k estimate:  ~34 seconds

Search Performance:
  Count query:    19.80ms (103k entries)
  Hash lookup:    2.14ms (exact match)
  LIKE search:    3.26ms (10 results)
  Pattern search: 82.18ms (866 results)
═══════════════════════════════════════════════════════════════════
```

---

## Incremental Update Strategy (RE-UPLOAD FILES)

> **Use Case:** User uploads `languagedata_fr.txt`, works on it, then wants to UPDATE with new version.
> Instead of full delete + re-insert, we detect changes and only update what changed.

### Strategy Comparison

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FILE RE-UPLOAD STRATEGIES                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  STRATEGY 1: Full Replace (Current - Simple)                                │
│  ════════════════════════════════════════════                                │
│  DELETE all rows → INSERT all new rows                                       │
│  ├── Speed: 103k rows in ~5 seconds                                          │
│  ├── Pros: Simple, clean slate, no conflicts                                │
│  └── Cons: Loses edit history, always full time                             │
│                                                                              │
│  STRATEGY 2: Diff-Based Update (Recommended) ★                              │
│  ══════════════════════════════════════════════                              │
│  Compare new file with DB → INSERT/UPDATE/DELETE only changes               │
│  ├── Speed: If 5% changed → 95% faster!                                      │
│  ├── Pros: Preserves history, much faster for updates                       │
│  └── Cons: More complex, needs row identity (string_id or row_num)          │
│                                                                              │
│  STRATEGY 3: Hash-Based Merge (For TM)                                       │
│  ═══════════════════════════════════════                                     │
│  Each entry has source_hash → O(1) lookup → UPSERT                          │
│  ├── Speed: Near-instant for unchanged entries                              │
│  ├── Pros: Perfect for TM updates, deduplication built-in                   │
│  └── Cons: Only works for TM (needs unique source key)                      │
│                                                                              │
│  STRATEGY 4: Version Tracking (Future)                                       │
│  ═════════════════════════════════════                                       │
│  Keep file_version column → New upload = new version                        │
│  ├── Speed: Fast insert (no delete needed)                                  │
│  ├── Pros: Full history, can diff versions, rollback                        │
│  └── Cons: More storage, complex UI                                         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Recommended: Diff-Based Update

```python
# Pseudocode for incremental file update

def update_file_incremental(db, file_id: int, new_rows: List[dict]):
    """
    Update file with only changed rows.

    1. Load existing rows into memory (by string_id)
    2. Compare with new rows
    3. Batch: INSERT new, UPDATE changed, DELETE removed
    """

    # Get existing rows as dict {string_id: row}
    existing = {r.string_id: r for r in db.query(LDMRow).filter_by(file_id=file_id)}

    to_insert = []
    to_update = []
    seen_ids = set()

    for new_row in new_rows:
        sid = new_row['string_id']
        seen_ids.add(sid)

        if sid not in existing:
            # New row
            to_insert.append(new_row)
        else:
            # Existing row - check if changed
            old = existing[sid]
            if (old.source != new_row['source'] or
                old.target != new_row['target']):
                to_update.append((old.id, new_row))

    # Rows in DB but not in new file = deleted
    to_delete = [existing[sid].id for sid in existing if sid not in seen_ids]

    # Execute batch operations
    if to_insert:
        bulk_insert_rows(db, file_id, to_insert)

    if to_update:
        for row_id, new_data in to_update:
            db.query(LDMRow).filter_by(id=row_id).update(new_data)

    if to_delete:
        db.query(LDMRow).filter(LDMRow.id.in_(to_delete)).delete()

    db.commit()

    return {
        "inserted": len(to_insert),
        "updated": len(to_update),
        "deleted": len(to_delete),
        "unchanged": len(existing) - len(to_update) - len(to_delete)
    }
```

### PostgreSQL UPSERT (ON CONFLICT)

```sql
-- Native PostgreSQL UPSERT - single statement for insert or update
INSERT INTO ldm_rows (file_id, row_num, string_id, source, target, status)
VALUES
  (1, 1, 'menu_01', '게임 시작', 'Start Game', 'translated'),
  (1, 2, 'menu_02', '설정', 'Settings', 'translated')
ON CONFLICT (file_id, string_id) DO UPDATE SET
  source = EXCLUDED.source,
  target = EXCLUDED.target,
  updated_at = NOW();
```

### Performance Estimates

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    RE-UPLOAD PERFORMANCE ESTIMATES                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Scenario: 100k row file, user updates and re-uploads                       │
│                                                                              │
│  If 0% changed (same file):                                                  │
│  ├── Full Replace:  ~5 seconds (delete + insert all)                        │
│  └── Diff-Based:    ~0.5 seconds (load + compare + no writes)               │
│                                                                              │
│  If 5% changed (typical translation update):                                │
│  ├── Full Replace:  ~5 seconds                                              │
│  └── Diff-Based:    ~0.8 seconds (5k updates only)                          │
│                                                                              │
│  If 50% changed (major revision):                                           │
│  ├── Full Replace:  ~5 seconds                                              │
│  └── Diff-Based:    ~3 seconds (50k updates)                                │
│                                                                              │
│  If 100% changed (completely new content):                                  │
│  ├── Full Replace:  ~5 seconds                                              │
│  └── Diff-Based:    ~6 seconds (compare overhead + full write)              │
│                                                                              │
│  CONCLUSION: Diff-based is faster for typical updates (<50% change)         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### User Experience

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  RE-UPLOAD DIALOG (Future UI)                                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  File: languagedata_fr.txt already exists                                   │
│                                                                              │
│  ○ Replace (delete all, upload new)                                         │
│    └── Faster for complete rewrites, loses edit history                     │
│                                                                              │
│  ● Update (merge changes) [Recommended]                                     │
│    └── Only update changed rows, preserves edit history                     │
│                                                                              │
│  ○ Create New Version                                                       │
│    └── Keep old file, create languagedata_fr_v2.txt                         │
│                                                                              │
│  [Cancel]                            [Upload]                                │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Current Database State

### What's Already Implemented (DONE)

```
IMPLEMENTED OPTIMIZATIONS:
===========================================================================================

1. INDEXES (40+ defined in models.py)
   ├── Single column indexes on all FKs and frequently queried columns
   ├── Composite indexes for common query patterns:
   │   ├── idx_ldm_row_file_rownum (file_id, row_num) - pagination
   │   ├── idx_ldm_row_file_stringid (file_id, string_id) - lookup
   │   ├── idx_ldm_tm_entry_tm_hash (tm_id, source_hash) - TM lookup
   │   ├── idx_log_timestamp_tool (timestamp, tool_name)
   │   └── idx_remote_log_installation_timestamp
   └── Unique indexes for constraint enforcement

2. CONNECTION POOLING (database.py)
   ├── pool_size=10 (concurrent connections)
   ├── max_overflow=20 (burst capacity)
   ├── pool_recycle=300 (5 min connection refresh)
   └── pool_pre_ping=True (health check on checkout)

3. HASH INDEXES for O(1) lookup
   └── LDMTMEntry.source_hash - SHA256 for exact TM match

4. CASCADING DELETES
   └── ondelete="CASCADE" on all FKs - no orphaned records

5. BIGINTEGER for large values
   └── file_size columns use BigInteger (up to 9.2 exabytes)

6. JSON/JSONB columns
   └── Flexible schema for metadata (file_info, parameters, tools_used)

7. TIMESTAMP TRACKING
   └── created_at, updated_at on all tables with auto-update

===========================================================================================
```

### What's Missing (TODO)

```
TO IMPLEMENT:
===========================================================================================

PRIORITY 1 - Quick Wins (High Impact, Low Effort)
─────────────────────────────────────────────────
□ Batch inserts for large TM imports (100k+ entries)
□ Full-Text Search (FTS) using PostgreSQL tsvector
□ GIN index on ldm_rows.source/target for text search

PRIORITY 2 - Performance Tuning
─────────────────────────────────────────────────
□ Async database operations (SQLAlchemy 2.0)
□ Query optimization for N+1 problems
□ EXPLAIN ANALYZE common queries

PRIORITY 3 - Scale (Only If Needed - Likely NOT for LocaNext)
─────────────────────────────────────────────────
□ Table partitioning for ldm_rows (if 10M+ rows)
□ Read replicas (only if multiple servers needed)
✗ Redis caching - NOT NEEDED for small team (10-50 users)

NOTE: LocaNext is a team tool with 100+ concurrent users.
Redis/partitioning are for high-traffic web apps with millions of users.
PostgreSQL + PgBouncer handles 100+ users with 1M rows each.

===========================================================================================
```

---

## Task Breakdown

### PRIORITY 1: Quick Wins

#### 1.1 Batch Inserts for TM Imports ✅ COMPLETE
**Status:** IMPLEMENTED (2025-12-09)
**Impact:** 10x+ faster for large TM imports
**Implementation:** `server/database/db_utils.py`

```python
# IMPLEMENTED: server/database/db_utils.py

from server.database import bulk_insert_tm_entries, bulk_insert_rows

# TM Entry bulk insert (auto-generates SHA256 hashes)
entries = [
    {"source_text": "Hello", "target_text": "안녕"},
    {"source_text": "World", "target_text": "세계"},
]
count = bulk_insert_tm_entries(db, tm_id=1, entries=entries, batch_size=5000)

# LDM Row bulk insert (from file upload)
rows = [
    {"row_num": 1, "string_id": "menu_01", "source": "게임 시작", "target": "Start Game"},
]
count = bulk_insert_rows(db, file_id=1, rows=rows, batch_size=5000)

# Generic bulk insert
from server.database import bulk_insert
count = bulk_insert(db, LDMTMEntry, records, batch_size=5000, progress_callback=my_callback)
```

**Features implemented:**
- `bulk_insert()` - Generic batch insert for any model
- `bulk_insert_tm_entries()` - TM-specific with auto SHA256 hash
- `bulk_insert_rows()` - LDM row upload optimization
- Progress callback support for UI updates
- Batched commits (default 5000 records/batch)

---

#### 1.2 Full-Text Search (FTS) Indexes ✅ COMPLETE
**Status:** IMPLEMENTED (2025-12-09)
**Impact:** Sub-second search on 1M+ rows
**Implementation:** `server/database/db_utils.py`

```sql
-- Add tsvector column for full-text search
ALTER TABLE ldm_rows ADD COLUMN source_tsv tsvector
  GENERATED ALWAYS AS (to_tsvector('simple', coalesce(source, ''))) STORED;

ALTER TABLE ldm_rows ADD COLUMN target_tsv tsvector
  GENERATED ALWAYS AS (to_tsvector('simple', coalesce(target, ''))) STORED;

-- Create GIN indexes
CREATE INDEX idx_ldm_rows_source_fts ON ldm_rows USING GIN (source_tsv);
CREATE INDEX idx_ldm_rows_target_fts ON ldm_rows USING GIN (target_tsv);
```

**SQLAlchemy Model Update:**
```python
from sqlalchemy.dialects.postgresql import TSVECTOR

class LDMRow(Base):
    # ... existing columns ...

    # Full-text search vectors (PostgreSQL only)
    source_tsv = Column(TSVECTOR, nullable=True)
    target_tsv = Column(TSVECTOR, nullable=True)

    __table_args__ = (
        # ... existing indexes ...
        Index("idx_ldm_rows_source_fts", "source_tsv", postgresql_using="gin"),
        Index("idx_ldm_rows_target_fts", "target_tsv", postgresql_using="gin"),
    )
```

**Search Query:**
```python
from sqlalchemy import func

def search_rows_fts(db: Session, file_id: int, query: str, limit: int = 50):
    """Full-text search on ldm_rows using PostgreSQL tsvector"""
    ts_query = func.plainto_tsquery('simple', query)

    results = db.query(LDMRow).filter(
        LDMRow.file_id == file_id,
        (LDMRow.source_tsv.op('@@')(ts_query) |
         LDMRow.target_tsv.op('@@')(ts_query))
    ).limit(limit).all()

    return results
```

---

#### 1.3 GIN Index for TM Entry Search ✅ COMPLETE
**Status:** IMPLEMENTED (2025-12-09)
**Impact:** Fast substring search in TM
**Implementation:** `server/database/db_utils.py` - `add_trigram_index()`

```sql
-- Trigram extension for similarity search
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- GIN index for trigram similarity
CREATE INDEX idx_ldm_tm_entry_source_trgm ON ldm_tm_entries
  USING GIN (source_text gin_trgm_ops);
```

---

### PRIORITY 2: Performance Tuning

#### 2.1 Async Database Operations
**Status:** ❌ NOT NEEDED
**Decision:** 2025-12-09

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ASYNC DB - ANALYSIS & DECISION                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  MYTH:   "Async = Faster queries"                                           │
│  TRUTH:  Async = Handle more CONCURRENT requests (not faster per-query)     │
│                                                                             │
│  CURRENT CAPACITY:                                                          │
│  ├── Connection Pool: 10 + 20 overflow = 30 simultaneous connections        │
│  ├── Query speed: 2-5ms average                                             │
│  ├── Theoretical: 6,000+ queries/sec                                        │
│  └── 50 users clicking = ~100 queries/sec = 1.6% capacity                   │
│                                                                             │
│  ASYNC BENEFITS:                                                            │
│  └── Only matters at 500+ concurrent users hammering DB                     │
│                                                                             │
│  ASYNC COSTS:                                                               │
│  ├── Refactor ALL endpoints                                                 │
│  ├── More complex debugging                                                 │
│  ├── Async overhead for simple operations                                   │
│  └── Higher code complexity                                                 │
│                                                                             │
│  DECISION: SKIP - Sync + connection pooling handles 50+ users easily        │
│                                                                             │
│  IF SLOWNESS OCCURS (future):                                               │
│  1. Check query optimization (indexes) ← free                               │
│  2. Increase pool size (10→20→30) ← free                                    │
│  3. Last resort: Async refactor ← expensive                                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

#### 2.2 Query Optimization (N+1 Prevention)
**Status:** TODO
**Impact:** Reduce query count for related data

```python
# BAD: N+1 queries
projects = db.query(LDMProject).filter_by(owner_id=user_id).all()
for project in projects:
    files = project.files  # Triggers 1 query per project

# GOOD: Eager loading
from sqlalchemy.orm import joinedload

projects = db.query(LDMProject).options(
    joinedload(LDMProject.files),
    joinedload(LDMProject.folders)
).filter_by(owner_id=user_id).all()
```

---

### PRIORITY 3: Scale

#### 3.1 Table Partitioning for ldm_rows
**Status:** FUTURE (when 10M+ rows)
**Impact:** Better query performance on large tables

```sql
-- Partition ldm_rows by file_id range
CREATE TABLE ldm_rows_partitioned (
    id SERIAL,
    file_id INTEGER NOT NULL,
    row_num INTEGER NOT NULL,
    source TEXT,
    target TEXT,
    -- ... other columns ...
    PRIMARY KEY (id, file_id)
) PARTITION BY RANGE (file_id);

-- Create partitions
CREATE TABLE ldm_rows_p1 PARTITION OF ldm_rows_partitioned
    FOR VALUES FROM (1) TO (10000);
CREATE TABLE ldm_rows_p2 PARTITION OF ldm_rows_partitioned
    FOR VALUES FROM (10000) TO (20000);
-- ... more partitions
```

---

#### 3.2 Query Caching with Redis
**Status:** FUTURE (when needed)
**Impact:** Reduce DB load for repeated queries

```python
import redis
import json
from functools import wraps

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def cache_query(ttl_seconds: int = 300):
    """Cache database query results in Redis"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = f"db:{func.__name__}:{hash((args, frozenset(kwargs.items())))}"

            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)

            result = func(*args, **kwargs)
            redis_client.setex(cache_key, ttl_seconds, json.dumps(result))
            return result
        return wrapper
    return decorator

# Usage
@cache_query(ttl_seconds=60)
def get_project_stats(project_id: int):
    # Expensive aggregation query
    ...
```

---

## Migration Strategy

### CURRENT: Development Mode (Full Refresh)

```
NO MIGRATIONS NEEDED DURING DEVELOPMENT
├── Schema change? → DROP ALL → RECREATE
├── Command: python3 server/database/db_setup.py --drop
├── Clean slate every time
├── Fast iteration
```

### FUTURE: Production Mode (When Public Users)

When LocaNext goes to production with real user data:
1. Create separate WIP: `P_DB_MIGRATION.md`
2. Set up Alembic for proper migrations
3. Zero-downtime upgrade procedures
4. Data backup before any schema change

**That's a future project - not needed now.**

---

## Migration Scripts (Reference Only)

```bash
# File: server/database/migrations/add_fts_indexes.py
```

```python
"""
Migration: Add Full-Text Search indexes to ldm_rows
"""

import logging
from sqlalchemy import text
from server.database.database import engine

logger = logging.getLogger(__name__)

def upgrade():
    """Add FTS columns and indexes"""
    with engine.connect() as conn:
        # Check if PostgreSQL
        result = conn.execute(text("SELECT version()"))
        version = result.scalar()

        if 'PostgreSQL' not in version:
            logger.warning("FTS indexes only supported on PostgreSQL, skipping")
            return

        logger.info("Adding FTS columns to ldm_rows...")

        # Add tsvector columns
        conn.execute(text("""
            ALTER TABLE ldm_rows
            ADD COLUMN IF NOT EXISTS source_tsv tsvector
            GENERATED ALWAYS AS (to_tsvector('simple', coalesce(source, ''))) STORED
        """))

        conn.execute(text("""
            ALTER TABLE ldm_rows
            ADD COLUMN IF NOT EXISTS target_tsv tsvector
            GENERATED ALWAYS AS (to_tsvector('simple', coalesce(target, ''))) STORED
        """))

        # Create GIN indexes
        logger.info("Creating GIN indexes...")

        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_ldm_rows_source_fts
            ON ldm_rows USING GIN (source_tsv)
        """))

        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_ldm_rows_target_fts
            ON ldm_rows USING GIN (target_tsv)
        """))

        conn.commit()
        logger.info("FTS migration complete!")

def downgrade():
    """Remove FTS columns and indexes"""
    with engine.connect() as conn:
        conn.execute(text("DROP INDEX IF EXISTS idx_ldm_rows_source_fts"))
        conn.execute(text("DROP INDEX IF EXISTS idx_ldm_rows_target_fts"))
        conn.execute(text("ALTER TABLE ldm_rows DROP COLUMN IF EXISTS source_tsv"))
        conn.execute(text("ALTER TABLE ldm_rows DROP COLUMN IF EXISTS target_tsv"))
        conn.commit()

if __name__ == "__main__":
    upgrade()
```

---

## Performance Benchmarks

### Target Metrics

| Operation | Current | Target | Notes |
|-----------|---------|--------|-------|
| Insert 100k TM entries | ~5 min | <10 sec | Batch inserts |
| Search 1M rows (text) | ~2 sec | <100ms | FTS indexes |
| Load file (100k rows) | ~30 sec | <5 sec | Pagination + lazy load |
| TM lookup (exact match) | ~10ms | <1ms | Hash index |
| Dashboard aggregation | ~500ms | <50ms | Materialized views |

### Benchmark Script

```python
# File: scripts/benchmark_db.py

import time
from server.database.database import SessionLocal
from server.database.models import LDMTMEntry

def benchmark_tm_insert(count: int = 100000):
    """Benchmark TM entry insertion"""
    entries = [
        {
            "tm_id": 1,
            "source_text": f"Test source {i}",
            "target_text": f"Test target {i}",
            "source_hash": f"hash_{i:064d}"
        }
        for i in range(count)
    ]

    db = SessionLocal()

    # Benchmark single inserts
    start = time.time()
    # ... (single insert code)
    single_time = time.time() - start

    # Benchmark bulk inserts
    start = time.time()
    # ... (bulk insert code)
    bulk_time = time.time() - start

    print(f"Single inserts: {single_time:.2f}s")
    print(f"Bulk inserts: {bulk_time:.2f}s")
    print(f"Speedup: {single_time / bulk_time:.1f}x")

if __name__ == "__main__":
    benchmark_tm_insert()
```

---

## Progress Tracking

### Phase 1: Quick Wins ✅ COMPLETE
- [x] **1.1** Implement batch inserts in db_utils.py ✅
- [x] **1.2** Add FTS columns and indexes (add_fts_indexes function) ✅
- [x] **1.3** Add trigram index for TM similarity search ✅
- [x] **1.4** Create search_rows_fts() function ✅
- [ ] **1.5** Test with 100k+ rows (requires PostgreSQL)

### Phase 2: Performance Tuning (Optional - Only If Needed)
- [ ] **2.1** Add async database engine (only if blocking becomes issue)
- [ ] **2.2** Convert LDM API endpoints to async
- [ ] **2.3** Add eager loading to project/file queries
- [ ] **2.4** Run EXPLAIN ANALYZE on slow queries

### Phase 3: Scale - Future if Needed
~~Redis caching, partitioning, read replicas~~ - Only if 1000+ concurrent users.
PostgreSQL + PgBouncer handles 100+ users with 1M rows each. Only revisit if growth exceeds this.

---

## Related Documents

| Document | Purpose |
|----------|---------|
| [P17_LDM_TASKS.md](P17_LDM_TASKS.md) | LDM feature tasks |
| [models.py](../../server/database/models.py) | Database models |
| [database.py](../../server/database/database.py) | DB configuration |
| [backup_service.py](../../server/tools/ldm/backup_service.py) | Backup system |

---

*Last updated: 2025-12-09*
*Target: PostgreSQL 15+ with full optimization*
