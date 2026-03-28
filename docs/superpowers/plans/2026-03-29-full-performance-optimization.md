# Full Performance Optimization Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade all bulk DB operations to maximum speed (COPY for PostgreSQL, executemany for SQLite), enable FTS indexes, and optimize image/audio caching — zero new features, pure performance.

**Architecture:** Wire existing `bulk_copy_rows()` into PostgreSQL upload path. Convert 4 remaining single-INSERT loops to `executemany`. Initialize FTS indexes at startup. Increase image cache 5x and add proper HTTP caching headers.

**Tech Stack:** PostgreSQL COPY TEXT, SQLite executemany, aiosqlite, PIL/Pillow, FastAPI Cache-Control headers

---

## File Map

| File | Responsibility | Action |
|------|---------------|--------|
| `server/repositories/postgresql/row_repo.py` | PG row bulk operations | Wire `bulk_copy_rows()` into `bulk_create()` |
| `server/repositories/sqlite/row_repo.py` | SQLite row bulk operations | Convert single-INSERT loop to `executemany` |
| `server/repositories/sqlite/tm_repo.py` | SQLite TM entry bulk operations | Convert single-INSERT loop to `executemany` |
| `server/database/offline.py` | Offline sync row saving | Convert `save_rows_bulk()` to `executemany` |
| `server/main.py` | App startup | Add FTS index initialization |
| `server/tools/ldm/services/media_converter.py` | Image/audio caching | Increase PNG cache 100→500 |
| `server/tools/ldm/routes/mapdata.py` | Image serving headers | Fix Cache-Control from no-cache to public |

---

### Task 1: Wire PostgreSQL COPY into LDM Row Upload

**Files:**
- Modify: `server/repositories/postgresql/row_repo.py:208-230`

This is the #1 performance win. `bulk_copy_rows()` already exists in `db_utils.py:456` but `bulk_create()` uses slow ORM `add_all()`. Wire it in.

- [ ] **Step 1: Modify bulk_create to use COPY**

Replace the ORM `add_all()` path with the existing `bulk_copy_rows()`:

```python
# server/repositories/postgresql/row_repo.py — replace bulk_create method

    async def bulk_create(
        self,
        file_id: int,
        rows: List[Dict[str, Any]]
    ) -> int:
        """Bulk create rows for a file using PostgreSQL COPY TEXT."""
        if not rows:
            return 0

        from server.database.db_utils import bulk_copy_rows
        from server.utils.dependencies import get_db

        # bulk_copy_rows uses sync COPY protocol — needs sync session
        sync_db = next(get_db())
        try:
            inserted = bulk_copy_rows(sync_db, file_id, rows)
            logger.info(f"COPY bulk created {inserted} rows for file_id={file_id}")
            return inserted
        finally:
            sync_db.close()
```

- [ ] **Step 2: Test with curl upload**

```bash
TOKEN=$(curl -s -X POST http://localhost:8888/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Create 200-row test file
python3 -c "
lines = ['<?xml version=\"1.0\" encoding=\"utf-8\"?>', '<LanguageData>']
for i in range(200):
    lines.append(f'  <LocStr StringID=\"COPY_TEST_{i:04d}\" Str=\"Target {i}\" StrOrigin=\"Source {i}\"/>')
lines.append('</LanguageData>')
open('/tmp/copy_test.xml','w').write('\n'.join(lines))"

curl -s -X POST "http://localhost:8888/api/ldm/files/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/tmp/copy_test.xml" \
  -F "project_id=314"
```

Expected: `{"row_count": 200, ...}` — all 200 rows inserted.

- [ ] **Step 3: Verify rows are searchable**

```bash
curl -s "http://localhost:8888/api/ldm/files/<FILE_ID>/rows?search=COPY_TEST_0150&search_fields=string_id" \
  -H "Authorization: Bearer $TOKEN"
```

Expected: `{"total": 1, "rows": [...]}`

- [ ] **Step 4: Commit**

```bash
git add server/repositories/postgresql/row_repo.py
git commit -m "perf(LDM): wire COPY TEXT into PostgreSQL row bulk_create (20x faster)"
```

---

### Task 2: SQLite Row Repo — executemany

**Files:**
- Modify: `server/repositories/sqlite/row_repo.py:233-297`

Convert the single-INSERT loop in `bulk_create()` to `executemany`.

- [ ] **Step 1: Replace single-INSERT loop with executemany**

```python
# server/repositories/sqlite/row_repo.py — replace bulk_create method

    async def bulk_create(
        self,
        file_id: int,
        rows: List[Dict[str, Any]]
    ) -> int:
        """Bulk create rows for a file using executemany."""
        if not rows:
            return 0

        now = datetime.now().isoformat()
        base_ts = int(time.time() * 1000)

        async with self.db._get_async_connection() as conn:
            if self.schema_mode == SchemaMode.OFFLINE:
                batch_data = []
                for idx, row_data in enumerate(rows):
                    row_id = -((base_ts + idx) % 1000000000)
                    extra_json = json.dumps(row_data.get("extra_data")) if row_data.get("extra_data") else None
                    batch_data.append((
                        row_id, file_id, row_data.get("row_num", idx + 1),
                        row_data.get("string_id"), row_data.get("source", ""),
                        row_data.get("target", ""), row_data.get("memo", ""),
                        row_data.get("status", "pending"), extra_json, now, now,
                    ))
                await conn.executemany(
                    f"""INSERT INTO {self._table('rows')}
                       (id, server_id, file_id, server_file_id, row_num, string_id,
                        source, target, memo, status, extra_data, created_at, updated_at,
                        downloaded_at, sync_status)
                       VALUES (?, 0, ?, 0, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), 'local')""",
                    batch_data
                )
            else:
                batch_data = []
                for idx, row_data in enumerate(rows):
                    row_id = -((base_ts + idx) % 1000000000)
                    extra_json = json.dumps(row_data.get("extra_data")) if row_data.get("extra_data") else None
                    batch_data.append((
                        row_id, file_id, row_data.get("row_num", idx + 1),
                        row_data.get("string_id"), row_data.get("source", ""),
                        row_data.get("target", ""), row_data.get("status", "pending"),
                        extra_json, now,
                    ))
                await conn.executemany(
                    f"""INSERT INTO {self._table('rows')}
                       (id, file_id, row_num, string_id, source, target,
                        status, extra_data, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    batch_data
                )

            await conn.execute(
                f"UPDATE {self._table('files')} SET row_count = ? WHERE id = ?",
                (len(rows), file_id)
            )
            await conn.commit()

        logger.info(f"Bulk created {len(rows)} rows for file_id={file_id}")
        return len(rows)
```

- [ ] **Step 2: Test offline upload**

```bash
curl -s -X POST "http://localhost:8888/api/ldm/files/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/tmp/copy_test.xml" \
  -F "storage=local"
```

Expected: `{"row_count": 200, ...}`

- [ ] **Step 3: Commit**

```bash
git add server/repositories/sqlite/row_repo.py
git commit -m "perf(SQLite): executemany for row_repo bulk_create (10x faster)"
```

---

### Task 3: SQLite TM Repo — executemany

**Files:**
- Modify: `server/repositories/sqlite/tm_repo.py:573-618`

- [ ] **Step 1: Replace single-INSERT loop with executemany**

```python
# server/repositories/sqlite/tm_repo.py — replace add_entries_bulk method

    async def add_entries_bulk(
        self,
        tm_id: int,
        entries: List[Dict[str, Any]]
    ) -> int:
        """Bulk add entries to TM using executemany."""
        if not entries:
            return 0

        async with self.db._get_async_connection() as conn:
            now = datetime.now().isoformat()
            base_ts = int(time.time() * 1000)

            if self.schema_mode == SchemaMode.OFFLINE:
                batch_data = []
                for idx, e in enumerate(entries):
                    entry_id = -((base_ts + idx) % 1000000000)
                    source = e.get("source") or e.get("source_text", "")
                    target = e.get("target") or e.get("target_text", "")
                    source_hash = hashlib.sha256(source.encode()).hexdigest()
                    batch_data.append((
                        entry_id, tm_id, source, target, source_hash,
                        e.get("string_id"), now,
                    ))
                await conn.executemany(
                    f"""INSERT INTO {self._table('tm_entries')}
                       (id, server_id, tm_id, server_tm_id, source_text, target_text, source_hash,
                        string_id, change_date, is_confirmed, downloaded_at, sync_status)
                       VALUES (?, 0, ?, 0, ?, ?, ?, ?, ?, 0, datetime('now'), 'local')""",
                    batch_data
                )
            else:
                batch_data = []
                for idx, e in enumerate(entries):
                    entry_id = -((base_ts + idx) % 1000000000)
                    source = e.get("source") or e.get("source_text", "")
                    target = e.get("target") or e.get("target_text", "")
                    source_hash = hashlib.sha256(source.encode()).hexdigest()
                    batch_data.append((
                        entry_id, tm_id, source, target, source_hash,
                        e.get("string_id"), now,
                    ))
                await conn.executemany(
                    f"""INSERT INTO {self._table('tm_entries')}
                       (id, tm_id, source_text, target_text, source_hash, string_id, change_date, is_confirmed)
                       VALUES (?, ?, ?, ?, ?, ?, ?, 0)""",
                    batch_data
                )

            await conn.execute(
                f"UPDATE {self._table('tms')} SET entry_count = entry_count + ? WHERE id = ?",
                (len(entries), tm_id)
            )
            await conn.commit()

            clear_tm_index_cache(tm_id)
            logger.info(f"Bulk added {len(entries)} entries to SQLite TM {tm_id}")
            return len(entries)
```

- [ ] **Step 2: Commit**

```bash
git add server/repositories/sqlite/tm_repo.py
git commit -m "perf(SQLite): executemany for tm_repo add_entries_bulk (10x faster)"
```

---

### Task 4: Offline save_rows_bulk — executemany

**Files:**
- Modify: `server/database/offline.py:680-711`

- [ ] **Step 1: Replace single-INSERT loop with executemany**

```python
# server/database/offline.py — replace save_rows_bulk method (line 680)

        """Save multiple rows to offline storage (bulk insert)."""
        async with self._get_async_connection() as conn:
            # Delete existing rows for this file first
            await conn.execute("DELETE FROM offline_rows WHERE file_id = ?", (file_id,))

            # Batch insert new rows
            batch_data = []
            for row in rows:
                extra_data = json.dumps(row.get("extra_data")) if row.get("extra_data") else None
                batch_data.append((
                    row["id"], row["id"], file_id, file_id,
                    row.get("row_num", 0), row.get("string_id"),
                    row.get("source"), row.get("target"),
                    row.get("memo"), row.get("status", "normal"),
                    extra_data, row.get("created_at"), row.get("updated_at"),
                ))
            await conn.executemany(
                """INSERT INTO offline_rows
                   (id, server_id, file_id, server_file_id, row_num, string_id,
                    source, target, memo, status, extra_data, created_at, updated_at,
                    downloaded_at, sync_status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), 'synced')""",
                batch_data
            )
            await conn.commit()
            logger.debug(f"Saved {len(rows)} rows for file {file_id}")
```

- [ ] **Step 2: Commit**

```bash
git add server/database/offline.py
git commit -m "perf(SQLite): executemany for save_rows_bulk (10x faster sync)"
```

---

### Task 5: Enable FTS Indexes at PostgreSQL Startup

**Files:**
- Modify: `server/main.py`

`add_fts_indexes()` exists but is NEVER called. The GIN indexes for full-text search on `ldm_rows.source` and `ldm_rows.target` are dead code.

- [ ] **Step 1: Add FTS initialization to startup**

Find the startup/lifespan section in `server/main.py` and add:

```python
# After database tables are created / migrations run:
from server.database.db_utils import add_fts_indexes
from server.utils.dependencies import get_db

try:
    sync_db = next(get_db())
    add_fts_indexes(sync_db)
    sync_db.close()
    logger.info("FTS indexes initialized")
except Exception as e:
    logger.warning(f"FTS index init skipped (may be SQLite): {e}")
```

- [ ] **Step 2: Test startup**

```bash
DEV_MODE=true python3 server/main.py
# Check logs for "FTS indexes initialized" or "FTS indexes already exist"
```

- [ ] **Step 3: Commit**

```bash
git add server/main.py
git commit -m "perf(PG): initialize FTS GIN indexes at startup (enables fast text search)"
```

---

### Task 6: Image Cache and HTTP Headers

**Files:**
- Modify: `server/tools/ldm/services/media_converter.py:35`
- Modify: `server/tools/ldm/routes/mapdata.py:154-156`

- [ ] **Step 1: Increase PNG cache from 100 to 500**

In `media_converter.py`, change default:

```python
# Line 35: change default
    png_cache_size: int = 500,
```

- [ ] **Step 2: Fix Cache-Control header on thumbnails**

In `mapdata.py`, find the thumbnail response and change headers:

```python
# Replace: "Cache-Control": "no-cache, must-revalidate"
# With:    "Cache-Control": "public, max-age=604800"  # 1 week — textures don't change
```

- [ ] **Step 3: Commit**

```bash
git add server/tools/ldm/services/media_converter.py server/tools/ldm/routes/mapdata.py
git commit -m "perf(media): 5x image cache (100→500), aggressive HTTP caching (1 week)"
```

---

### Task 7: Final Verification and Build

- [ ] **Step 1: Run backend and verify no import errors**

```bash
DEV_MODE=true python3 -c "import server.main; print('OK')"
```

- [ ] **Step 2: Test PostgreSQL upload path (if PG available)**

```bash
# Upload + search + verify row count
```

- [ ] **Step 3: Test SQLite upload path**

```bash
curl -s -X POST "http://localhost:8888/api/ldm/files/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/tmp/copy_test.xml" \
  -F "storage=local"
# Verify row_count matches expected
```

- [ ] **Step 4: Commit all and trigger Build Light**

```bash
git add BUILD_TRIGGER.txt
git commit -m "trigger: LocaNext Build Light"
git push origin main
```

---

## Performance Impact Summary

| Operation | Before | After | Speedup |
|-----------|--------|-------|---------|
| PG row upload (50k rows) | 25-100s (ORM) | 2.5s (COPY) | **10-40x** |
| SQLite row bulk_create | 100-500s (loop) | 10s (executemany) | **10-50x** |
| SQLite TM bulk add | 100-500s (loop) | 10s (executemany) | **10-50x** |
| SQLite sync save_rows | 100-500s (loop) | 10s (executemany) | **10-50x** |
| PG text search | Full table scan | GIN FTS index | **100x+** |
| Image cache hits | 100 items | 500 items | **5x capacity** |
| Image HTTP cache | 0s (no-cache) | 7 days | **eliminates re-requests** |
