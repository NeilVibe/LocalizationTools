# P21: Database Powerhouse - State of the Art Setup

**Created:** 2025-12-10
**Status:** PLANNING
**Priority:** HIGH
**Goal:** Handle 40+ users uploading 1M rows simultaneously with zero queuing

---

## Context from Discussion (2025-12-10)

### Architecture Confirmed
- **Local Processing:** All heavy work (embeddings, FAISS, parsing) done on user's PC
- **Central DB:** Only stores TEXT (source/target pairs, metadata)
- **WebSocket:** Real-time sync already implemented and working
- **Current Bottleneck:** Bulk INSERT for massive concurrent uploads

### Worst Case Scenario
```
40 users × 1M rows = 40 MILLION rows simultaneous insert
Each row ~200 bytes = 8GB of data
All hitting DB at the same time
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
│   1. COPY BINARY                  ★★★★★          Best for bulk import       │
│      COPY table FROM STDIN WITH (FORMAT BINARY)                             │
│      - 5-10x faster than INSERT                                             │
│      - Bypasses SQL parsing                                                 │
│      - Direct binary format                                                 │
│                                                                             │
│   2. COPY TEXT                    ★★★★☆          Standard bulk import       │
│      COPY table FROM STDIN                                                  │
│      - 3-5x faster than INSERT                                              │
│      - Simple CSV/text format                                               │
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
│   WINNER: COPY BINARY                                                       │
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
│                         40+ CONCURRENT USERS                                │
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

### Minimum (50 users, 1M rows each)
```
CPU:    4 cores (8 threads)
RAM:    16 GB
SSD:    500 GB NVMe
Cost:   ~$50-80/month (cloud) or $500-800 one-time (bare metal)
```

### Recommended (100 users, 1M rows each)
```
CPU:    8 cores (16 threads)
RAM:    32 GB
SSD:    1 TB NVMe
Cost:   ~$100-150/month (cloud) or $1000-1500 one-time (bare metal)
```

### Powerhouse (200+ users, unlimited rows)
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

**YES, WE NEED PGBOUNCER** for 40+ concurrent bulk uploads.

### Why PgBouncer?
```
WITHOUT PgBouncer:
─────────────────
• 40 users each hold connection for 60+ seconds
• PostgreSQL max_connections = 200
• Each connection uses ~10MB RAM
• 40 connections × 10MB = 400MB just for connections
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

## COPY Implementation Plan

### Current: bulk_insert() with INSERT
```python
# Current method (3-5x slower)
stmt = insert(model)
db.execute(stmt, batch)  # INSERT INTO ... VALUES (...), (...)
```

### New: bulk_copy() with COPY BINARY
```python
# New method (fastest possible)
from io import BytesIO
import struct

def bulk_copy_binary(db, table_name: str, columns: list, rows: list):
    """
    Use PostgreSQL COPY BINARY for maximum insert speed.
    5-10x faster than bulk INSERT.
    """
    # Build binary buffer
    buffer = BytesIO()

    # COPY header
    buffer.write(b'PGCOPY\n\xff\r\n\0')  # Signature
    buffer.write(struct.pack('>I', 0))    # Flags
    buffer.write(struct.pack('>I', 0))    # Extension area length

    for row in rows:
        # Field count
        buffer.write(struct.pack('>h', len(columns)))
        for value in row:
            if value is None:
                buffer.write(struct.pack('>i', -1))  # NULL
            else:
                encoded = str(value).encode('utf-8')
                buffer.write(struct.pack('>i', len(encoded)))
                buffer.write(encoded)

    # Trailer
    buffer.write(struct.pack('>h', -1))

    buffer.seek(0)

    # Execute COPY
    raw_conn = db.connection().connection
    cursor = raw_conn.cursor()
    cursor.copy_expert(
        f"COPY {table_name} ({','.join(columns)}) FROM STDIN WITH (FORMAT BINARY)",
        buffer
    )
    raw_conn.commit()
```

### Alternative: Use psycopg2 copy_from (simpler)
```python
from io import StringIO

def bulk_copy_csv(db, table_name: str, columns: list, rows: list):
    """
    Use PostgreSQL COPY with CSV format.
    3-5x faster than bulk INSERT, simpler than BINARY.
    """
    # Build CSV buffer
    buffer = StringIO()
    for row in rows:
        line = '\t'.join(
            '\\N' if v is None else str(v).replace('\t', ' ').replace('\n', '\\n')
            for v in row
        )
        buffer.write(line + '\n')

    buffer.seek(0)

    # Execute COPY
    raw_conn = db.connection().connection
    cursor = raw_conn.cursor()
    cursor.copy_from(buffer, table_name, columns=columns)
    raw_conn.commit()
```

---

## Implementation Tasks

### Phase 1: COPY Implementation (Priority: HIGH)
- [ ] 1.1 Create `bulk_copy()` function in `db_utils.py`
- [ ] 1.2 Create `bulk_copy_tm_entries()` wrapper
- [ ] 1.3 Create `bulk_copy_rows()` wrapper
- [ ] 1.4 Add fallback to INSERT for SQLite (dev mode)
- [ ] 1.5 Benchmark: Compare COPY vs INSERT speed
- [ ] 1.6 Update TM upload to use COPY
- [ ] 1.7 Update file upload to use COPY

### Phase 2: PostgreSQL Tuning (Priority: HIGH)
- [ ] 2.1 Create `postgresql.conf.recommended` template
- [ ] 2.2 Document memory calculation formula
- [ ] 2.3 Create tuning script for different server sizes
- [ ] 2.4 Add health check for DB performance
- [ ] 2.5 Add monitoring for connection count, query time

### Phase 3: PgBouncer Setup (Priority: MEDIUM)
- [ ] 3.1 Create `pgbouncer.ini` template
- [ ] 3.2 Create Docker Compose with PgBouncer
- [ ] 3.3 Update connection string to use PgBouncer port
- [ ] 3.4 Document PgBouncer installation
- [ ] 3.5 Add PgBouncer stats endpoint to admin dashboard

### Phase 4: Advanced Optimizations (Priority: LOW)
- [ ] 4.1 Table partitioning for very large datasets
- [ ] 4.2 Parallel COPY (split file, multiple connections)
- [ ] 4.3 Async COPY with progress tracking
- [ ] 4.4 Connection warming on server start

---

## Performance Targets

| Metric | Current | Target | Method |
|--------|---------|--------|--------|
| Bulk insert rate | 20k rows/sec | 100k rows/sec | COPY BINARY |
| 1M row upload time | 50 sec | 10 sec | COPY + tuning |
| Concurrent uploads | 10 | 100 | PgBouncer |
| Max connections | 30 | 1000 | PgBouncer |
| Memory efficiency | ~10MB/conn | ~2MB/conn | PgBouncer |

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
│   1. COPY BINARY          → 5-10x faster inserts                            │
│   2. PgBouncer            → 1000 connections, no exhaustion                 │
│   3. PostgreSQL Tuning    → Optimized for bulk writes                       │
│   4. 32GB RAM + NVMe SSD  → Handle 40M rows easily                          │
│                                                                             │
│   RESULT: 40 users upload 1M rows each = ~30 seconds total                  │
│           No queuing, no waiting, instant power                             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Questions for Next Session

1. Cloud or bare metal server?
2. Budget ceiling for DB server?
3. Want Docker Compose setup or manual installation?
4. Priority: Speed first or implement incrementally?

---

*Last Updated: 2025-12-10*
*Created from conversation about DB scalability and TM sync architecture*
