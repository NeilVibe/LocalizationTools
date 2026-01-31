# Session 60: Schema-Aware SQLite Repos

> **Time:** 8-12 hours
> **Priority:** HIGH
> **Result:** TRUE layer abstraction, ZERO violations

---

## The Problem

3 places where PostgreSQL repos check SQLite mode internally (LAYER VIOLATION):

```
server/repositories/postgresql/row_repo.py:423   → if config.ACTIVE_DATABASE_TYPE == "sqlite"
server/repositories/postgresql/row_repo.py:598   → if config.ACTIVE_DATABASE_TYPE == "sqlite"
server/repositories/postgresql/tm_repo.py:1001   → if config.ACTIVE_DATABASE_TYPE == "sqlite"
```

**Root cause:** SQLite repos use `offline_*` tables, server creates `ldm_*` tables. Schema mismatch.

---

## The Solution

Make SQLite repos work with EITHER schema. Factory picks the right mode.

```
FACTORY:
├─ Offline mode (header)  → SQLiteTMRepository(schema_mode="offline")  → offline_* tables
├─ Server SQLite fallback → SQLiteTMRepository(schema_mode="server")   → ldm_* tables
└─ PostgreSQL available   → PostgreSQLTMRepository(db, user)           → ldm_* tables

REPOS:
├─ PostgreSQL repos: Just do PostgreSQL stuff. No SQLite checks. PURE.
└─ SQLite repos: Use self._table("tms") → returns correct table name based on mode.
```

---

## Implementation

### Phase 1: Create Base Infrastructure (2 hours)

#### File 1: `server/repositories/sqlite/base.py`

```python
"""Schema-aware base class for SQLite repositories."""

from enum import Enum
from loguru import logger


class SchemaMode(Enum):
    OFFLINE = "offline"   # offline_* tables (user's local cache)
    SERVER = "server"     # ldm_* tables (server SQLite fallback)


SERVER_TABLE_MAP = {
    "platforms": "ldm_platforms",
    "projects": "ldm_projects",
    "folders": "ldm_folders",
    "files": "ldm_files",
    "rows": "ldm_rows",
    "tms": "ldm_translation_memories",
    "tm_entries": "ldm_tm_entries",
    "tm_assignments": "ldm_tm_assignments",
    "qa_results": "ldm_qa_results",
    "trash": "ldm_trash",
    "capabilities": "user_capabilities",
}


class SQLiteBaseRepository:
    """Base class for all SQLite repositories with schema awareness."""

    def __init__(self, schema_mode: SchemaMode = SchemaMode.OFFLINE):
        self.schema_mode = schema_mode
        self._db = None
        logger.debug(f"[SQLITE-BASE] schema_mode={schema_mode.value}")

    @property
    def db(self):
        """Lazy load database connection based on schema mode."""
        if self._db is None:
            if self.schema_mode == SchemaMode.OFFLINE:
                from server.database.offline import get_offline_db
                self._db = get_offline_db()
            else:
                from server.database.server_sqlite import get_server_sqlite_db
                self._db = get_server_sqlite_db()
        return self._db

    def _table(self, base_name: str) -> str:
        """Get correct table name for current schema mode."""
        if self.schema_mode == SchemaMode.OFFLINE:
            return f"offline_{base_name}"
        return SERVER_TABLE_MAP.get(base_name, f"ldm_{base_name}")
```

#### File 2: `server/database/server_sqlite.py`

```python
"""Server SQLite connection manager for fallback mode."""

import aiosqlite
from contextlib import asynccontextmanager
from loguru import logger
from server import config


class ServerSQLiteDatabase:
    """Async SQLite manager for server fallback (uses ldm_* tables)."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.db_path = config.SQLITE_DATABASE_PATH
        self._initialized = True
        logger.info(f"[SERVER-SQLITE] path={self.db_path}")

    @asynccontextmanager
    async def _get_async_connection(self):
        """Get async database connection."""
        conn = await aiosqlite.connect(self.db_path)
        conn.row_factory = aiosqlite.Row
        try:
            yield conn
        finally:
            await conn.close()


_server_sqlite_db = None


def get_server_sqlite_db() -> ServerSQLiteDatabase:
    """Get the server SQLite database instance."""
    global _server_sqlite_db
    if _server_sqlite_db is None:
        _server_sqlite_db = ServerSQLiteDatabase()
    return _server_sqlite_db
```

---

### Phase 2: Refactor SQLite Repos (4-6 hours)

For each repo, change from:

```python
class SQLiteProjectRepository(ProjectRepository):
    def __init__(self):
        self.db = get_offline_db()

    async def get(self, project_id: int):
        async with self.db._get_async_connection() as conn:
            cursor = await conn.execute(
                "SELECT * FROM offline_projects WHERE id = ?",  # HARDCODED
                (project_id,)
            )
```

To:

```python
from server.repositories.sqlite.base import SQLiteBaseRepository, SchemaMode

class SQLiteProjectRepository(SQLiteBaseRepository, ProjectRepository):
    def __init__(self, schema_mode: SchemaMode = SchemaMode.OFFLINE):
        super().__init__(schema_mode)

    async def get(self, project_id: int):
        table = self._table("projects")  # DYNAMIC

        async with self.db._get_async_connection() as conn:
            cursor = await conn.execute(
                f"SELECT * FROM {table} WHERE id = ?",
                (project_id,)
            )
```

**Order (by complexity):**
1. `project_repo.py`
2. `folder_repo.py`
3. `platform_repo.py`
4. `file_repo.py`
5. `capability_repo.py`
6. `trash_repo.py`
7. `qa_repo.py`
8. `row_repo.py`
9. `tm_repo.py`

---

### Phase 3: Update Factory (1 hour)

**File:** `server/repositories/factory.py`

Add:
```python
from server.repositories.sqlite.base import SchemaMode

def _is_sqlite_fallback() -> bool:
    """Check if server is running in SQLite fallback mode."""
    from server import config
    return config.ACTIVE_DATABASE_TYPE == "sqlite"
```

Update each `get_*_repository()`:
```python
def get_tm_repository(request, db, current_user) -> TMRepository:
    from server.repositories.postgresql.tm_repo import PostgreSQLTMRepository
    from server.repositories.sqlite.tm_repo import SQLiteTMRepository

    if _is_offline_mode(request):
        return SQLiteTMRepository(schema_mode=SchemaMode.OFFLINE)

    if _is_sqlite_fallback():
        return SQLiteTMRepository(schema_mode=SchemaMode.SERVER)

    return PostgreSQLTMRepository(db, current_user)
```

---

### Phase 4: Clean PostgreSQL Repos (30 min)

**DELETE these blocks:**

`row_repo.py` lines 423-425:
```python
if config.ACTIVE_DATABASE_TYPE == "sqlite":
    logger.debug("[ROW-REPO] Fuzzy search not available (SQLite mode)")
    return [], 0
```

`row_repo.py` lines 598-600:
```python
if config.ACTIVE_DATABASE_TYPE == "sqlite":
    logger.debug("[ROW-REPO] Similarity search not available (SQLite mode)")
    return []
```

`tm_repo.py` lines 1001-1003:
```python
if config.ACTIVE_DATABASE_TYPE == "sqlite":
    logger.debug("[TM-REPO] Similarity search not available (SQLite mode)")
    return []
```

**Verify:**
```bash
grep -n "ACTIVE_DATABASE_TYPE" server/repositories/postgresql/*.py
# Must return NOTHING
```

---

### Phase 5: Test (2 hours)

```bash
./scripts/start_all_servers.sh
pytest tests/ -x -q                              # PostgreSQL mode
DATABASE_MODE=sqlite pytest tests/ -x -q         # SQLite fallback mode
grep "ACTIVE_DATABASE_TYPE" server/repositories/postgresql/*.py  # Must be empty
```

---

### Phase 6: Commit (30 min)

```bash
git add -A
git commit -m "Refactor: Schema-aware SQLite repos - TRUE layer abstraction

- Created SQLiteBaseRepository with schema mode support
- Created ServerSQLiteDatabase for server fallback connections
- Refactored all 9 SQLite repos to use dynamic table names
- Updated factory with 3-mode detection
- Removed ACTIVE_DATABASE_TYPE checks from PostgreSQL repos

PostgreSQL repos are now PURE - no cross-layer knowledge.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"

git push origin main
./scripts/gitea_control.sh start && git push gitea main && ./scripts/gitea_control.sh stop
```

---

## Files

| Action | File |
|--------|------|
| CREATE | `server/repositories/sqlite/base.py` |
| CREATE | `server/database/server_sqlite.py` |
| MODIFY | `server/repositories/sqlite/project_repo.py` |
| MODIFY | `server/repositories/sqlite/folder_repo.py` |
| MODIFY | `server/repositories/sqlite/platform_repo.py` |
| MODIFY | `server/repositories/sqlite/file_repo.py` |
| MODIFY | `server/repositories/sqlite/capability_repo.py` |
| MODIFY | `server/repositories/sqlite/trash_repo.py` |
| MODIFY | `server/repositories/sqlite/qa_repo.py` |
| MODIFY | `server/repositories/sqlite/row_repo.py` |
| MODIFY | `server/repositories/sqlite/tm_repo.py` |
| MODIFY | `server/repositories/factory.py` |
| CLEAN | `server/repositories/postgresql/row_repo.py` |
| CLEAN | `server/repositories/postgresql/tm_repo.py` |

---

## Checklist

- [ ] `base.py` created
- [ ] `server_sqlite.py` created
- [ ] 9 SQLite repos refactored
- [ ] Factory updated
- [ ] 3 violations removed from PostgreSQL repos
- [ ] `grep ACTIVE_DATABASE_TYPE server/repositories/postgresql/*.py` returns nothing
- [ ] Tests pass
- [ ] Build succeeds

---

*Delete this file after completion.*
