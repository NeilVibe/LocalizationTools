# Next Session TODO: Fix Architecture Layer Violations (THE HARD WAY)

> **Priority:** HIGH
> **Estimated Time:** 8-12 hours (we don't rush, we do it RIGHT)
> **Solution:** Option C - Schema-Aware SQLite Repos
> **Full Analysis:** [ARCHITECTURE_FIX_OPTIONS.md](ARCHITECTURE_FIX_OPTIONS.md)

---

## Why Option C is the HARD Way

| Approach | What It Does | Why It's Wrong/Right |
|----------|--------------|----------------------|
| ❌ CapabilityWrapper | Magic `__getattr__` interception | Hides logic, still a workaround |
| ❌ Dual SQLite Repos | Duplicate 9 repo classes | Over-engineering, maintenance hell |
| ✅ **Schema-Aware** | SQLite repos work with EITHER schema | TRUE abstraction, reuses code |

**Option C is HARD because:**
- Refactor ALL 9 SQLite repositories
- Create new base class infrastructure
- Create new database connection manager
- Update factory with proper mode detection
- Full testing across all 3 modes

**But it's RIGHT because:**
- NO magic wrappers
- NO runtime interception
- PostgreSQL repos stay PURE
- Clean, explicit, readable code
- Architecture survives future changes

---

## The Problem (Reminder)

```
3 Layer Violations:
- postgresql/row_repo.py:423  → checks SQLite mode
- postgresql/row_repo.py:598  → checks SQLite mode
- postgresql/tm_repo.py:1001  → checks SQLite mode

Root Cause:
- SQLite repos use "offline_*" tables
- Server creates "ldm_*" tables
- Schema mismatch forces workaround
```

---

## Implementation Plan

### Phase 1: Create Base Infrastructure (2 hours)

#### 1.1 Create SQLite Base Repository

**File:** `server/repositories/sqlite/base.py`

```python
"""
Schema-aware base class for SQLite repositories.

SQLite repos can operate in two modes:
- "offline": Uses offline_* tables (user's local cache)
- "server": Uses ldm_* tables (server SQLite fallback)
"""

from enum import Enum
from typing import Optional
from loguru import logger


class SchemaMode(Enum):
    OFFLINE = "offline"   # offline_projects, offline_tms, etc.
    SERVER = "server"     # ldm_projects, ldm_translation_memories, etc.


# Table name mapping for server mode
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
    """
    Base class for all SQLite repositories.

    Provides schema-aware table name resolution.
    """

    def __init__(self, schema_mode: SchemaMode = SchemaMode.OFFLINE):
        """
        Initialize with schema mode.

        Args:
            schema_mode: OFFLINE for offline_* tables, SERVER for ldm_* tables
        """
        self.schema_mode = schema_mode
        self._db = None

        logger.debug(f"[SQLITE-BASE] Initialized with schema_mode={schema_mode.value}")

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
        """
        Get the correct table name for the current schema mode.

        Args:
            base_name: Base table name without prefix (e.g., "projects", "tms")

        Returns:
            Full table name (e.g., "offline_projects" or "ldm_projects")
        """
        if self.schema_mode == SchemaMode.OFFLINE:
            return f"offline_{base_name}"
        else:
            # Use mapping for server tables (some have different names)
            return SERVER_TABLE_MAP.get(base_name, f"ldm_{base_name}")

    def _has_similarity_support(self) -> bool:
        """SQLite never has pg_trgm similarity support."""
        return False
```

#### 1.2 Create Server SQLite Connection Manager

**File:** `server/database/server_sqlite.py`

```python
"""
Server SQLite database connection manager.

Used when server falls back to SQLite (PostgreSQL unavailable).
Uses the SAME database file as the main server, but provides
async connection management similar to offline.py.

Key difference from offline.py:
- offline.py: Uses offline_* schema (for user's local cache)
- server_sqlite.py: Uses ldm_* schema (for server fallback)
"""

import aiosqlite
from contextlib import asynccontextmanager
from pathlib import Path
from loguru import logger
from server import config


class ServerSQLiteDatabase:
    """
    Async SQLite database manager for server fallback mode.

    Uses the same database file as the server (config.SQLITE_DATABASE_PATH)
    but provides async connection management.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        # Use the server's SQLite database path
        self.db_path = config.SQLITE_DATABASE_PATH
        self._initialized = True

        logger.info(f"[SERVER-SQLITE] Initialized with path: {self.db_path}")

    @asynccontextmanager
    async def get_async_connection(self):
        """Get async database connection."""
        conn = await aiosqlite.connect(self.db_path)
        conn.row_factory = aiosqlite.Row
        try:
            yield conn
        finally:
            await conn.close()

    # Alias for compatibility with existing code
    _get_async_connection = get_async_connection


# Singleton accessor
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

For EACH of the 9 SQLite repos, make these changes:

#### Template: How to Refactor Each Repo

**Before:**
```python
class SQLiteProjectRepository(ProjectRepository):
    def __init__(self):
        self.db = get_offline_db()

    async def get(self, project_id: int):
        async with self.db._get_async_connection() as conn:
            cursor = await conn.execute(
                "SELECT * FROM offline_projects WHERE id = ?",  # Hardcoded!
                (project_id,)
            )
```

**After:**
```python
from server.repositories.sqlite.base import SQLiteBaseRepository, SchemaMode

class SQLiteProjectRepository(SQLiteBaseRepository, ProjectRepository):
    def __init__(self, schema_mode: SchemaMode = SchemaMode.OFFLINE):
        super().__init__(schema_mode)

    async def get(self, project_id: int):
        table = self._table("projects")  # Dynamic!

        async with self.db._get_async_connection() as conn:
            cursor = await conn.execute(
                f"SELECT * FROM {table} WHERE id = ?",
                (project_id,)
            )
```

#### Refactor Order (by complexity)

1. **project_repo.py** - Simplest, good starting point
2. **folder_repo.py** - Similar structure
3. **platform_repo.py** - Small, straightforward
4. **file_repo.py** - Medium complexity
5. **capability_repo.py** - Small
6. **trash_repo.py** - Small
7. **qa_repo.py** - Medium
8. **row_repo.py** - Complex, many queries
9. **tm_repo.py** - Most complex, save for last

#### For Each File:

1. Add import: `from server.repositories.sqlite.base import SQLiteBaseRepository, SchemaMode`
2. Change class to inherit from `SQLiteBaseRepository`
3. Update `__init__` to accept `schema_mode` parameter
4. Replace ALL hardcoded table names with `self._table("name")`
5. Test the repo works in both modes

---

### Phase 3: Update Factory (1 hour)

**File:** `server/repositories/factory.py`

```python
from server.repositories.sqlite.base import SchemaMode

def _is_sqlite_fallback() -> bool:
    """Check if server is running in SQLite fallback mode."""
    from server import config
    return config.ACTIVE_DATABASE_TYPE == "sqlite"


def get_tm_repository(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
) -> TMRepository:
    """Get TM repository based on mode."""
    from server.repositories.postgresql.tm_repo import PostgreSQLTMRepository
    from server.repositories.sqlite.tm_repo import SQLiteTMRepository

    # Mode 1: Explicit offline mode (user's local cache)
    if _is_offline_mode(request):
        return SQLiteTMRepository(schema_mode=SchemaMode.OFFLINE)

    # Mode 2: Server SQLite fallback (PostgreSQL unavailable)
    if _is_sqlite_fallback():
        return SQLiteTMRepository(schema_mode=SchemaMode.SERVER)

    # Mode 3: Normal PostgreSQL mode
    return PostgreSQLTMRepository(db, current_user)
```

Update ALL 9 factory functions with this pattern.

---

### Phase 4: Clean PostgreSQL Repos (30 min)

**Remove these 3 blocks:**

#### row_repo.py lines 423-425:
```python
# DELETE THIS ENTIRE BLOCK
if config.ACTIVE_DATABASE_TYPE == "sqlite":
    logger.debug("[ROW-REPO] Fuzzy search not available (SQLite mode)")
    return [], 0
```

#### row_repo.py lines 598-600:
```python
# DELETE THIS ENTIRE BLOCK
if config.ACTIVE_DATABASE_TYPE == "sqlite":
    logger.debug("[ROW-REPO] Similarity search not available (SQLite mode)")
    return []
```

#### tm_repo.py lines 1001-1003:
```python
# DELETE THIS ENTIRE BLOCK
if config.ACTIVE_DATABASE_TYPE == "sqlite":
    logger.debug("[TM-REPO] Similarity search not available (SQLite mode)")
    return []
```

**Verify no violations remain:**
```bash
grep -n "ACTIVE_DATABASE_TYPE" server/repositories/postgresql/*.py
# Should return NOTHING
```

---

### Phase 5: Testing (2 hours)

```bash
# Start servers
./scripts/start_all_servers.sh

# Test 1: PostgreSQL mode (normal)
pytest tests/ -x -q
# Expected: All pass, similarity search works

# Test 2: SQLite fallback mode
DATABASE_MODE=sqlite pytest tests/ -x -q
# Expected: All pass, similarity returns empty

# Test 3: Offline mode (manual)
# Start app, enable offline mode, verify operations work

# Test 4: Verify no violations
grep -n "ACTIVE_DATABASE_TYPE" server/repositories/postgresql/*.py
# Expected: No results
```

---

### Phase 6: Documentation & Commit (1 hour)

```bash
# Update docs
# - Mark ARCH-001 as FIXED in ISSUES_TO_FIX.md
# - Add Session 60 to SESSION_CONTEXT.md
# - Delete NEXT_SESSION_TODO.md (it's done)
# - Delete ARCHITECTURE_DEBT_REPORT.md (outdated)

# Commit
git add -A
git commit -m "$(cat <<'EOF'
Refactor: Schema-aware SQLite repos (THE HARD WAY)

Architecture fix for layer violations (ARCH-001):

- Created SQLiteBaseRepository with schema mode support
- Created ServerSQLiteDatabase for server fallback connections
- Refactored all 9 SQLite repos to use dynamic table names
- Updated factory with proper 3-mode detection
- Removed ACTIVE_DATABASE_TYPE checks from PostgreSQL repos

SQLite repos now work with EITHER schema:
- SchemaMode.OFFLINE: Uses offline_* tables (user's local cache)
- SchemaMode.SERVER: Uses ldm_* tables (server SQLite fallback)

This is TRUE layer abstraction:
- No magic wrappers
- No runtime interception
- PostgreSQL repos stay PURE
- Clean, explicit, testable code

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"

# Push
git push origin main
./scripts/gitea_control.sh start
git push gitea main
./scripts/gitea_control.sh stop
```

---

## Checklist

- [ ] `server/repositories/sqlite/base.py` created
- [ ] `server/database/server_sqlite.py` created
- [ ] `project_repo.py` refactored and tested
- [ ] `folder_repo.py` refactored and tested
- [ ] `platform_repo.py` refactored and tested
- [ ] `file_repo.py` refactored and tested
- [ ] `capability_repo.py` refactored and tested
- [ ] `trash_repo.py` refactored and tested
- [ ] `qa_repo.py` refactored and tested
- [ ] `row_repo.py` refactored and tested
- [ ] `tm_repo.py` refactored and tested
- [ ] Factory updated with 3-mode detection
- [ ] PostgreSQL repos cleaned (3 violations removed)
- [ ] `grep ACTIVE_DATABASE_TYPE server/repositories/postgresql/*.py` returns nothing
- [ ] All tests pass in PostgreSQL mode
- [ ] All tests pass in SQLite fallback mode
- [ ] Build succeeds on GitHub
- [ ] Build succeeds on Gitea
- [ ] Documentation updated
- [ ] This file deleted

---

## Files Summary

### New Files (2)
| File | Purpose |
|------|---------|
| `server/repositories/sqlite/base.py` | Schema-aware base class |
| `server/database/server_sqlite.py` | Server SQLite connection manager |

### Modified Files (12)
| File | Changes |
|------|---------|
| `server/repositories/sqlite/project_repo.py` | Inherit base, dynamic tables |
| `server/repositories/sqlite/folder_repo.py` | Inherit base, dynamic tables |
| `server/repositories/sqlite/platform_repo.py` | Inherit base, dynamic tables |
| `server/repositories/sqlite/file_repo.py` | Inherit base, dynamic tables |
| `server/repositories/sqlite/capability_repo.py` | Inherit base, dynamic tables |
| `server/repositories/sqlite/trash_repo.py` | Inherit base, dynamic tables |
| `server/repositories/sqlite/qa_repo.py` | Inherit base, dynamic tables |
| `server/repositories/sqlite/row_repo.py` | Inherit base, dynamic tables |
| `server/repositories/sqlite/tm_repo.py` | Inherit base, dynamic tables |
| `server/repositories/factory.py` | 3-mode detection |
| `server/repositories/postgresql/row_repo.py` | Remove 2 violations |
| `server/repositories/postgresql/tm_repo.py` | Remove 1 violation |

---

*This is the HARD way. It takes time. But it's RIGHT.*
