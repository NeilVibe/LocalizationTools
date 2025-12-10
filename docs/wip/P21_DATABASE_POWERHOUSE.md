# P21: Database Powerhouse - State of the Art Setup

**Created:** 2025-12-10
**Status:** READY TO IMPLEMENT
**Priority:** HIGH
**Goal:** Handle 100+ users uploading 1M rows simultaneously with zero queuing
**Scalability:** Design for easy vertical scaling (just add RAM/CPU) + future horizontal scaling

---

## Context from Discussion (2025-12-10)

### Architecture Confirmed
- **Local Processing:** All heavy work (embeddings, FAISS, parsing) done on user's PC
- **Central DB:** Only stores TEXT (source/target pairs, metadata)
- **WebSocket:** Real-time sync already implemented and working
- **Current Bottleneck:** Bulk INSERT for massive concurrent uploads

### Worst Case Scenario
```
100 users × 1M rows = 100 MILLION rows simultaneous insert
Each row ~200 bytes = 20GB of data
All hitting DB at the same time
```

### Design Principles
```
1. SCALABILITY FIRST - Easy to scale up without code changes
2. SIMPLE BEFORE COMPLEX - COPY TEXT now, BINARY later if needed
3. VERTICAL THEN HORIZONTAL - Add RAM/CPU first, shard only if maxed
4. CAP STORAGE GROWTH - Tiered lifecycle prevents infinite growth
```

---

## Best INSERT Methods (Ranked)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    INSERT METHODS - PERFORMANCE RANKING                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   METHOD                          SPEED           USE CASE                  │
│   ══════════════════════════════════════════════════════════════════════   │
│                                                                             │
│   1. COPY TEXT ★ RECOMMENDED      ★★★★☆          Best balance speed/safety  │
│      COPY table FROM STDIN                                                  │
│      - 3-5x faster than INSERT                                              │
│      - Simple CSV/text format                                               │
│      - Human-readable, easy debugging                                       │
│      - Built-in psycopg2 support (copy_from)                                │
│                                                                             │
│   2. COPY BINARY (overkill)       ★★★★★          Only for 10M+ rows         │
│      COPY table FROM STDIN WITH (FORMAT BINARY)                             │
│      - 5-10x faster than INSERT                                             │
│      - Complex implementation, hard to debug                                │
│      - Risk of byte corruption                                              │
│      - NOT WORTH IT for our use case                                        │
│                                                                             │
│   3. Bulk INSERT (current)        ★★★☆☆          Good for moderate loads    │
│      INSERT INTO ... VALUES (...), (...), ...                               │
│      - Batch size 5000 rows                                                 │
│      - What we use now                                                      │
│                                                                             │
│   4. Individual INSERT            ★☆☆☆☆          Never use for bulk         │
│      INSERT INTO ... VALUES (...)                                           │
│      - 100x slower                                                          │
│                                                                             │
│   WINNER: COPY TEXT (90% of speed, 10% of complexity)                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Why COPY TEXT over COPY BINARY?

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    COPY TEXT vs COPY BINARY                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   COPY TEXT:                      COPY BINARY:                              │
│   ══════════                      ════════════                              │
│   3-5x faster than INSERT         5-10x faster than INSERT                  │
│   ~20 lines of code               ~50+ lines of code                        │
│   Human-readable data             Hex dumps to debug                        │
│   Clear error messages            Cryptic errors                            │
│   Built-in psycopg2 support       Manual struct packing                     │
│   Zero corruption risk            Medium corruption risk                    │
│                                                                             │
│   1M rows: 10-15 seconds          1M rows: 5-10 seconds                     │
│                                                                             │
│   VERDICT: Save 5-10 seconds but add complexity + risk?                     │
│            NOT WORTH IT.                                                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## State of the Art Database Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    POWERHOUSE DB ARCHITECTURE                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│                        100+ CONCURRENT USERS                                │
│                               │                                             │
│                               ▼                                             │
│                    ┌─────────────────────┐                                  │
│                    │     PgBouncer       │                                  │
│                    │  (Connection Pool)  │                                  │
│                    │                     │                                  │
│                    │  max_client = 1000  │                                  │
│                    │  pool_size = 100    │                                  │
│                    │  mode = transaction │                                  │
│                    └──────────┬──────────┘                                  │
│                               │                                             │
│                               ▼                                             │
│     ┌─────────────────────────────────────────────────────────────┐        │
│     │                    PostgreSQL 16                             │        │
│     │                                                              │        │
│     │  ┌────────────────────────────────────────────────────────┐ │        │
│     │  │ TUNED CONFIGURATION                                    │ │        │
│     │  │                                                        │ │        │
│     │  │ max_connections = 200                                  │ │        │
│     │  │ shared_buffers = 8GB          (25% of RAM)             │ │        │
│     │  │ effective_cache_size = 24GB   (75% of RAM)             │ │        │
│     │  │ work_mem = 256MB              (per operation)          │ │        │
│     │  │ maintenance_work_mem = 2GB    (for VACUUM, INDEX)      │ │        │
│     │  │ wal_buffers = 256MB           (write-ahead log)        │ │        │
│     │  │ checkpoint_completion_target = 0.9                     │ │        │
│     │  │ random_page_cost = 1.1        (SSD optimized)          │ │        │
│     │  │ effective_io_concurrency = 200 (SSD parallel reads)    │ │        │
│     │  │ max_parallel_workers_per_gather = 4                    │ │        │
│     │  │ max_parallel_workers = 8                               │ │        │
│     │  └────────────────────────────────────────────────────────┘ │        │
│     │                                                              │        │
│     │  ┌────────────────────────────────────────────────────────┐ │        │
│     │  │ STORAGE                                                │ │        │
│     │  │                                                        │ │        │
│     │  │ • NVMe SSD (3000+ MB/s read/write)                     │ │        │
│     │  │ • Separate disk for WAL (optional, extra speed)        │ │        │
│     │  │ • RAID 10 for redundancy (production)                  │ │        │
│     │  └────────────────────────────────────────────────────────┘ │        │
│     │                                                              │        │
│     └──────────────────────────────────────────────────────────────┘        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Server Specifications

### Minimum (100 users, 1M rows each)
```
CPU:    4 cores (8 threads)
RAM:    16 GB
SSD:    500 GB NVMe
Cost:   ~$50-80/month (cloud) or $500-800 one-time (bare metal)
```

### Recommended (100+ users, 1M rows each)
```
CPU:    8 cores (16 threads)
RAM:    32 GB
SSD:    1 TB NVMe
Cost:   ~$100-150/month (cloud) or $1000-1500 one-time (bare metal)
```

### Powerhouse (200+ users, 10M+ rows each)
```
CPU:    16 cores (32 threads)
RAM:    64 GB
SSD:    2 TB NVMe (RAID 10)
Cost:   ~$200-400/month (cloud) or $3000-5000 one-time (bare metal)
```

### Memory Calculation
```
40M rows × 200 bytes = 8 GB raw data
+ Indexes (~30% overhead) = 2.4 GB
+ WAL buffers = 256 MB
+ Work memory (40 connections × 256MB) = 10 GB
+ shared_buffers = 8 GB
+ OS overhead = 4 GB
────────────────────────
TOTAL RECOMMENDED: 32 GB RAM
```

---

## PgBouncer Configuration

**YES, WE NEED PGBOUNCER** for 100+ concurrent bulk uploads.

### Why PgBouncer?
```
WITHOUT PgBouncer:
─────────────────
• 100 users each hold connection for 60+ seconds
• PostgreSQL max_connections = 200
• Each connection uses ~10MB RAM
• 100 connections × 10MB = 1GB just for connections
• New users might get "too many connections" error

WITH PgBouncer:
───────────────
• 1000 app connections multiplexed to 100 DB connections
• Transaction pooling: connection released after each query batch
• Efficient reuse, no connection exhaustion
• Lower memory overhead
```

### pgbouncer.ini (Recommended)
```ini
[databases]
localizationtools = host=localhost port=5432 dbname=localizationtools

[pgbouncer]
listen_addr = 0.0.0.0
listen_port = 6432
auth_type = md5
auth_file = /etc/pgbouncer/userlist.txt

# Connection limits
max_client_conn = 1000        # Accept up to 1000 app connections
default_pool_size = 100       # 100 actual DB connections per pool
min_pool_size = 20            # Keep 20 connections warm
reserve_pool_size = 50        # Extra connections for bursts

# Pooling mode
pool_mode = transaction       # Release connection after transaction
                              # (Best for bulk inserts)

# Timeouts
server_idle_timeout = 600     # Close idle connections after 10 min
query_timeout = 300           # 5 min max query time (for big uploads)

# Performance
tcp_keepalive = 1
tcp_keepidle = 60
server_round_robin = 1        # Distribute load evenly
```

---

## COPY TEXT Implementation Plan

### Current: bulk_insert() with INSERT
```python
# Current method - 50 seconds for 1M rows
stmt = insert(model)
db.execute(stmt, batch)  # INSERT INTO ... VALUES (...), (...)
```

### New: bulk_copy() with COPY TEXT ★ RECOMMENDED
```python
from io import StringIO

def bulk_copy(connection, table_name: str, columns: list, rows: list):
    """
    Use PostgreSQL COPY TEXT for fast bulk inserts.
    3-5x faster than bulk INSERT, simple and safe.

    Args:
        connection: Raw psycopg2 connection (not SQLAlchemy session)
        table_name: Target table name
        columns: List of column names
        rows: List of tuples, each tuple is one row

    Example:
        bulk_copy(conn, 'ldm_rows',
                  ['file_id', 'row_num', 'source', 'target'],
                  [(1, 0, 'Hello', 'Bonjour'), (1, 1, 'World', 'Monde')])
    """
    # Build tab-separated text buffer
    buffer = StringIO()
    for row in rows:
        line = '\t'.join(
            '\\N' if v is None else str(v).replace('\\', '\\\\').replace('\t', ' ').replace('\n', '\\n')
            for v in row
        )
        buffer.write(line + '\n')

    buffer.seek(0)

    # Execute COPY
    cursor = connection.cursor()
    cursor.copy_from(buffer, table_name, columns=columns, null='\\N')
    connection.commit()

    return len(rows)
```

### Wrapper Functions
```python
def bulk_copy_tm_entries(db_session, entries: list):
    """
    Bulk insert TM entries using COPY TEXT.

    Args:
        db_session: SQLAlchemy session
        entries: List of dicts with 'source', 'target', 'tm_id', etc.
    """
    if not entries:
        return 0

    # Get raw connection from SQLAlchemy
    raw_conn = db_session.connection().connection

    columns = ['tm_id', 'source_text', 'target_text', 'source_hash', 'created_at']
    rows = [
        (e['tm_id'], e['source'], e['target'], e['source_hash'], e['created_at'])
        for e in entries
    ]

    return bulk_copy(raw_conn, 'tm_entries', columns, rows)


def bulk_copy_rows(db_session, file_id: int, rows: list):
    """
    Bulk insert LDM rows using COPY TEXT.

    Args:
        db_session: SQLAlchemy session
        file_id: The file these rows belong to
        rows: List of dicts with 'row_num', 'string_id', 'source', 'target'
    """
    if not rows:
        return 0

    raw_conn = db_session.connection().connection

    columns = ['file_id', 'row_num', 'string_id', 'source', 'target', 'status']
    data = [
        (file_id, r['row_num'], r.get('string_id', ''), r['source'], r.get('target', ''), 'pending')
        for r in rows
    ]

    return bulk_copy(raw_conn, 'ldm_rows', columns, data)
```

### SQLite Fallback (Dev Mode)
```python
def bulk_copy_with_fallback(db_session, table_name: str, columns: list, rows: list):
    """
    Use COPY TEXT for PostgreSQL, fall back to INSERT for SQLite.
    """
    dialect = db_session.bind.dialect.name

    if dialect == 'postgresql':
        raw_conn = db_session.connection().connection
        return bulk_copy(raw_conn, table_name, columns, rows)
    else:
        # SQLite fallback - use regular INSERT
        from sqlalchemy import text
        placeholders = ', '.join(['?' for _ in columns])
        cols = ', '.join(columns)
        stmt = text(f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders})")
        for row in rows:
            db_session.execute(stmt, row)
        db_session.commit()
        return len(rows)
```

---

## Implementation Guide

### Difficulty & Risk Assessment

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    IMPLEMENTATION DIFFICULTY                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   PHASE    DIFFICULTY   TIME      RISK    NOTES                             │
│   ═════════════════════════════════════════════════════════════════════════ │
│                                                                             │
│   Phase 1  ████░░░░░░   1-2 days  LOW     COPY TEXT is simple               │
│   COPY     (4/10)                         Built-in psycopg2 support         │
│                                           Human-readable, easy debug        │
│                                                                             │
│   Phase 2  ███░░░░░░░   1 day     LOW     Just config files                 │
│   Tuning   (3/10)                         Copy-paste recommended values     │
│                                           Easy to verify with benchmarks    │
│                                                                             │
│   Phase 3  ████░░░░░░   1-2 days  MEDIUM  Connection string changes         │
│   PgBouncer(4/10)                         Must update app config too        │
│                                           Test all endpoints after          │
│                                                                             │
│   Phase 4  ████████░░   3-5 days  HIGH    Complex, defer until needed       │
│   Advanced (8/10)                         Only if Phase 1-3 not enough      │
│                                                                             │
│   Phase 5  █████░░░░░   2-3 days  MEDIUM  File operations need care         │
│   Storage  (5/10)                         Don't lose user data!             │
│                                           Add confirmation prompts          │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   TOTAL ESTIMATE: 5-7 days for Phase 1-3 + 5                                │
│   (Phase 4 only if needed - probably never for 100 users)                   │
│                                                                             │
│   RECOMMENDED ORDER:                                                        │
│   1. Phase 2 first (easiest, immediate benefit)                             │
│   2. Phase 1 second (biggest speed gain, now LOW risk with COPY TEXT)       │
│   3. Phase 3 third (only if connection issues appear)                       │
│   4. Phase 5 anytime (independent, prevents storage bloat)                  │
│   5. Phase 4 never? (100 users won't need it)                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Critical Warnings

```
⚠️  COPY TEXT NOTES (Low Risk):
───────────────────────────────
1. Column order must match table definition
2. Escape special chars: tabs → spaces, newlines → \n, backslash → \\
3. NULL = '\N' string (handled by our function)
4. Transaction isolation - COPY locks briefly (normal)
5. Test with 100 rows first, then scale up

⚠️  PGBOUNCER PITFALLS:
──────────────────────
1. Prepared statements don't work in transaction mode
2. SET commands reset after transaction
3. App must use port 6432, not 5432
4. Auth file must match PostgreSQL users exactly

⚠️  TIERED STORAGE PITFALLS:
────────────────────────────
1. Never delete without 30-day trash first
2. Compression must be reversible (verify before delete)
3. Show user EXACTLY what will be archived/deleted
4. Admin override to prevent auto-deletion of critical files
```

### Testing Checklist (MANDATORY)

```
Before deploying each phase:

Phase 1 (COPY TEXT):
□ Test with 100 rows → verify data integrity
□ Test with 10,000 rows → verify speed improvement
□ Test with 1,000,000 rows → verify no timeout/memory issues
□ Test with special chars (tabs, newlines, unicode) → verify escaping works
□ Test SQLite fallback → verify dev mode still works
□ Benchmark: compare old INSERT vs new COPY TEXT speed

Phase 2 (Tuning):
□ Run pg_stat_statements before/after
□ Verify shared_buffers actually used (pg_buffercache)
□ Check no OOM errors under load

Phase 3 (PgBouncer):
□ All API endpoints still work
□ WebSocket connections work
□ No "prepared statement" errors
□ Connection count under 100 at peak

Phase 5 (Storage):
□ Archive a file → restore it → verify identical
□ Delete from trash → verify unrecoverable
□ Quota exceeded → verify oldest archived first
□ UI shows correct status badges
```

---

## Implementation Tasks

### Phase 1: COPY TEXT Implementation (Priority: HIGH, Difficulty: 4/10)
- [ ] 1.1 Create `bulk_copy()` function in `db_utils.py`
- [ ] 1.2 Create `bulk_copy_tm_entries()` wrapper
- [ ] 1.3 Create `bulk_copy_rows()` wrapper
- [ ] 1.4 Add fallback to INSERT for SQLite (dev mode)
- [ ] 1.5 Benchmark: Compare COPY TEXT vs INSERT speed
- [ ] 1.6 Update TM upload to use COPY TEXT
- [ ] 1.7 Update file upload to use COPY TEXT
- [ ] 1.8 **TEST: Special chars (tabs, newlines, unicode)**
- [ ] 1.9 **TEST: 1M row stress test**

### Phase 2: PostgreSQL Tuning (Priority: HIGH, Difficulty: 3/10) ← START HERE
- [ ] 2.1 Create `postgresql.conf.recommended` template
- [ ] 2.2 Document memory calculation formula
- [ ] 2.3 Create tuning script for different server sizes
- [ ] 2.4 Add health check for DB performance
- [ ] 2.5 Add monitoring for connection count, query time
- [ ] 2.6 **TEST: Before/after benchmarks**

### Phase 3: PgBouncer Setup (Priority: MEDIUM, Difficulty: 4/10)
- [ ] 3.1 Create `pgbouncer.ini` template
- [ ] 3.2 Create Docker Compose with PgBouncer
- [ ] 3.3 Update connection string to use PgBouncer port
- [ ] 3.4 Document PgBouncer installation
- [ ] 3.5 Add PgBouncer stats endpoint to admin dashboard
- [ ] 3.6 **TEST: All endpoints work through PgBouncer**
- [ ] 3.7 **TEST: WebSocket still works**

### Phase 4: Advanced Optimizations (Priority: LOW, Difficulty: 8/10) ← SKIP FOR NOW
- [ ] 4.1 Table partitioning for very large datasets
- [ ] 4.2 Parallel COPY (split file, multiple connections)
- [ ] 4.3 Async COPY with progress tracking
- [ ] 4.4 Connection warming on server start

### Phase 5: Tiered Storage Lifecycle (Priority: MEDIUM)

**Problem:** Without cleanup, storage grows forever.
```
100 users × 10 files × 250MB = 250 GB initial
+ daily uploads = unlimited growth
```

**Solution:** 3-Tier automatic lifecycle management.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    3-TIER STORAGE LIFECYCLE                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   TIER 1: ACTIVE (Hot)                                                      │
│   ════════════════════                                                      │
│   • Full data in PostgreSQL                                                 │
│   • Instant read/write                                                      │
│   • User quota: 10 GB per user                                              │
│   • Cost: $$$                                                               │
│                                                                             │
│              │                                                              │
│              ▼ (auto-compress when quota exceeded)                          │
│                                                                             │
│   TIER 2: ARCHIVED (Warm)                                                   │
│   ═══════════════════════                                                   │
│   • Compressed .gz files on disk                                            │
│   • Needs decompression to use (5-10 sec)                                   │
│   • Quota: 50 GB per user                                                   │
│   • Cost: $$                                                                │
│   • Badge in UI: "📦 Archived - Click to restore"                           │
│                                                                             │
│              │                                                              │
│              ▼ (auto-delete when archive quota exceeded)                    │
│                                                                             │
│   TIER 3: DELETED                                                           │
│   ════════════════                                                          │
│   • 30-day trash (optional recovery)                                        │
│   • Then permanently deleted                                                │
│   • Cost: $0                                                                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Compression Ratios (Real Numbers):**
| Data Type | Original | Compressed | Ratio |
|-----------|----------|------------|-------|
| Text/XML (translation files) | 250 MB | 25-50 MB | 5-10x |
| PostgreSQL TOAST (automatic) | 250 MB | 50-100 MB | 2-5x |
| Gzip on disk | 100 MB | 20-30 MB | 3-5x |
| **Total: Raw → Archived** | 250 MB | 20-30 MB | **8-12x** |

**Storage Math With Tiers:**
```
100 users, each uploads 10 files (250MB each):

WITHOUT tiers:
  100 × 10 × 250MB = 250 GB (and growing forever to infinity)

WITH tiers (10GB active, 50GB archive per user):
  Active:  100 × 10 GB = 1 TB max (PostgreSQL)
  Archive: 100 × 50 GB = 5 TB max (compressed on disk)

  TOTAL CAP: 6 TB (NEVER grows beyond this!)
```

**Implementation Tasks:**
- [ ] 5.1 Add `storage_used` column to users table
- [ ] 5.2 Add `file_status` enum (active/archived/deleted)
- [ ] 5.3 Create compression job (gzip to disk)
- [ ] 5.4 Create decompression on restore
- [ ] 5.5 Auto-archive trigger when active quota exceeded
- [ ] 5.6 Auto-delete trigger when archive quota exceeded
- [ ] 5.7 UI badges + "Restore" button
- [ ] 5.8 30-day trash before permanent deletion
- [ ] 5.9 Admin dashboard: storage usage per user

---

## Performance Targets

| Metric | Current | Target | Method |
|--------|---------|--------|--------|
| Bulk insert rate | 20k rows/sec | 60-100k rows/sec | COPY TEXT |
| 1M row upload time | 50 sec | 10-15 sec | COPY TEXT + tuning |
| Concurrent uploads | 10 | 100+ | PgBouncer |
| Max connections | 30 | 1000 | PgBouncer |
| Memory efficiency | ~10MB/conn | ~2MB/conn | PgBouncer |
| Storage growth | Unlimited | 6 TB max | Tiered Storage |

---

## Cost Estimates

### Cloud (Monthly)
| Provider | Spec | Cost |
|----------|------|------|
| AWS RDS | db.r6g.xlarge (4 vCPU, 32GB) | ~$300/month |
| DigitalOcean | 8 vCPU, 32GB | ~$150/month |
| Hetzner | CPX41 (8 vCPU, 32GB) | ~$50/month |
| Self-hosted | Your hardware | $0/month |

### Bare Metal (One-time)
| Spec | Cost |
|------|------|
| Dell PowerEdge (refurb) 16 core, 64GB, 1TB NVMe | ~$1500 |
| Custom build 8 core, 32GB, 500GB NVMe | ~$800 |
| Mini PC (Intel NUC) 4 core, 16GB, 256GB NVMe | ~$400 |

**Recommendation:** Start with 32GB RAM server (~$100-150/month cloud or $800-1500 bare metal)

---

## Summary

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    STATE OF THE ART DB SETUP                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   1. COPY TEXT            → 3-5x faster inserts (simple, safe)              │
│   2. PgBouncer            → 1000 connections, no exhaustion                 │
│   3. PostgreSQL Tuning    → Optimized for bulk writes                       │
│   4. 32GB RAM + NVMe SSD  → Handle 100M rows easily                         │
│   5. Tiered Storage       → 6 TB cap, never grows beyond                    │
│                                                                             │
│   RESULT: 100 users upload 1M rows each = ~2-3 minutes total                │
│           No queuing, no waiting, instant power                             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Scalability Path

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SCALABILITY - DESIGNED FOR GROWTH                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   CURRENT DESIGN HANDLES:                                                   │
│   • 100 users × 1M rows = ✅ No problem                                     │
│   • 100 users × 10M rows = ✅ Still fine                                    │
│                                                                             │
│   IF WE NEED MORE SPEED LATER:                                              │
│   ─────────────────────────────                                             │
│   Option A: Vertical Scaling (easiest)                                      │
│   • Add more RAM (32GB → 64GB → 128GB)                                      │
│   • Add more CPU cores (8 → 16 → 32)                                        │
│   • Faster NVMe (3000 → 7000 MB/s)                                          │
│   • Cost: Just upgrade server, no code changes                              │
│                                                                             │
│   Option B: Switch to COPY BINARY (code change)                             │
│   • 2x faster than COPY TEXT                                                │
│   • Only if vertical scaling maxed out                                      │
│   • More complex, but we have the plan ready                                │
│                                                                             │
│   Option C: Horizontal Scaling (future)                                     │
│   • Read replicas for search queries                                        │
│   • Sharding by user_id or project_id                                       │
│   • Only needed at 500+ concurrent heavy users                              │
│                                                                             │
│   PHILOSOPHY: Start simple, scale when needed, not before.                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Quick Start (After Implementation)

```bash
# 1. Apply PostgreSQL tuning
sudo cp config/postgresql.conf.recommended /etc/postgresql/16/main/postgresql.conf
sudo systemctl restart postgresql

# 2. Start PgBouncer (required for 100+ users)
sudo cp config/pgbouncer.ini /etc/pgbouncer/pgbouncer.ini
sudo systemctl start pgbouncer

# 3. Update .env to use PgBouncer port
DATABASE_URL=postgresql://user:pass@localhost:6432/localizationtools

# 4. Run benchmark to verify
python3 scripts/benchmark_copy.py
```

---

*Last Updated: 2025-12-10*
*Status: READY TO IMPLEMENT - All decisions made, code examples ready*
