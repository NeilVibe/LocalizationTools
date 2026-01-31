# Architecture Fix Options: From EASY to HARD

> **Created:** 2026-01-31
> **Purpose:** Choose the RIGHT solution, not the quick one
> **CLAUDE.md Rule #2:** ALWAYS CHOOSE HARD

---

## The Problem (Reminder)

```
PostgreSQL repos check config.ACTIVE_DATABASE_TYPE == "sqlite" internally.
This is a LAYER VIOLATION.
```

**Root Cause:** Schema mismatch
- SQLite repos use `offline_*` tables (for user's local cache)
- Server creates `ldm_*` tables (standard schema)
- Can't route to SQLite repos when server falls back to SQLite

---

## Option Comparison

| Option | Difficulty | Elegance | Time | Maintenance |
|--------|------------|----------|------|-------------|
| A: CapabilityAwareWrapper | MEDIUM | ⭐⭐⭐ | 2-3 hours | Magic methods, hidden logic |
| B: Interface Segregation | HARD | ⭐⭐⭐⭐ | 4-6 hours | Clean interfaces, explicit |
| C: Schema-Aware SQLite Repos | VERY HARD | ⭐⭐⭐⭐⭐ | 8-12 hours | TRUE abstraction |
| D: Dual SQLite Repos | HARDEST | ⭐⭐⭐⭐⭐ | 12-16 hours | Complete separation |

---

## Option A: CapabilityAwareWrapper (MEDIUM - Already Documented)

**What it does:** Wraps repos and intercepts method calls with `__getattr__` magic.

**Why it's NOT the hard way:**
- Uses runtime interception (magic)
- Hides the logic in a wrapper
- Still a workaround, not a fix
- PostgreSQL repos still "exist" in SQLite mode, just wrapped

**Skip this option.**

---

## Option B: Interface Segregation Principle (HARD)

**What it does:** Create separate interface for similarity capabilities.

### Design

```python
# server/repositories/interfaces/similarity_capable.py (NEW)
from abc import ABC, abstractmethod

class SimilarityCapable(ABC):
    """Interface for repos that support similarity search."""

    @abstractmethod
    async def search_similar(self, ...) -> List[Dict]:
        """Search using pg_trgm similarity."""
        ...

    @abstractmethod
    async def suggest_similar(self, ...) -> List[Dict]:
        """Suggest similar entries."""
        ...

# PostgreSQL repos implement BOTH interfaces
class PostgreSQLTMRepository(TMRepository, SimilarityCapable):
    async def search_similar(self, ...):
        # Real pg_trgm implementation
        ...

# SQLite repos implement ONLY base interface
class SQLiteTMRepository(TMRepository):
    # NO search_similar method - doesn't implement SimilarityCapable
    pass
```

### Route Usage

```python
@router.get("/tm/{tm_id}/similar")
async def search_similar(
    tm_id: int,
    query: str,
    repo: TMRepository = Depends(get_tm_repository)
):
    # Check if repo has capability
    if not isinstance(repo, SimilarityCapable):
        return {"results": [], "message": "Similarity search not available in this mode"}

    results = await repo.search_similar(tm_id, query)
    return {"results": results}
```

### Pros
- Explicit capability checking
- No magic methods
- Routes know what they're dealing with
- Clean separation of concerns

### Cons
- Need to modify routes to check capabilities
- More verbose code
- Still doesn't fix the schema mismatch

### Files to Modify
- Create `server/repositories/interfaces/similarity_capable.py`
- Modify `server/repositories/interfaces/__init__.py`
- Modify `server/repositories/postgresql/tm_repo.py` - add interface
- Modify `server/repositories/postgresql/row_repo.py` - add interface
- Remove similarity methods from `server/repositories/interfaces/tm_repository.py`
- Remove similarity methods from `server/repositories/interfaces/row_repository.py`
- Modify routes that use similarity search (3-5 routes)

---

## Option C: Schema-Aware SQLite Repos (VERY HARD) ⭐ RECOMMENDED

**What it does:** Make SQLite repos work with EITHER schema based on mode.

### The Insight

The SQLite repos are perfectly good implementations. The ONLY problem is they query wrong table names:
- `offline_projects` instead of `ldm_projects`
- `offline_tms` instead of `ldm_translation_memories`

**Solution:** Pass schema prefix to SQLite repos.

### Design

```python
# server/repositories/sqlite/base.py (NEW)
class SQLiteBaseRepository:
    """Base class for SQLite repos with schema awareness."""

    def __init__(self, schema_mode: str = "offline"):
        """
        Args:
            schema_mode: "offline" for offline_* tables, "server" for ldm_* tables
        """
        self.schema_mode = schema_mode
        self.db = get_offline_db() if schema_mode == "offline" else get_server_sqlite_db()

    def _table(self, base_name: str) -> str:
        """Get table name with correct prefix."""
        if self.schema_mode == "offline":
            return f"offline_{base_name}"
        else:
            # Map to server table names
            TABLE_MAP = {
                "projects": "ldm_projects",
                "folders": "ldm_folders",
                "files": "ldm_files",
                "rows": "ldm_rows",
                "tms": "ldm_translation_memories",
                "tm_entries": "ldm_tm_entries",
                "platforms": "ldm_platforms",
            }
            return TABLE_MAP.get(base_name, f"ldm_{base_name}")
```

### SQLite Repo Usage

```python
# server/repositories/sqlite/project_repo.py
class SQLiteProjectRepository(SQLiteBaseRepository, ProjectRepository):

    async def get(self, project_id: int) -> Optional[Dict]:
        table = self._table("projects")  # Returns "offline_projects" or "ldm_projects"

        async with self.db._get_async_connection() as conn:
            cursor = await conn.execute(
                f"SELECT * FROM {table} WHERE id = ?",
                (project_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None
```

### Factory Usage

```python
# server/repositories/factory.py
def get_project_repository(request, db, current_user) -> ProjectRepository:
    if _is_offline_mode(request):
        # User's local cache - use offline_* schema
        return SQLiteProjectRepository(schema_mode="offline")

    if _is_sqlite_fallback():
        # Server SQLite fallback - use ldm_* schema
        return SQLiteProjectRepository(schema_mode="server")

    # PostgreSQL mode
    return PostgreSQLProjectRepository(db, current_user)
```

### Similarity Search Handling

For similarity search (pg_trgm), SQLite repos return empty:

```python
# server/repositories/sqlite/tm_repo.py
class SQLiteTMRepository(SQLiteBaseRepository, TMRepository):

    async def search_similar(self, tm_id: int, source: str, ...) -> List[Dict]:
        """Similarity search - not available in SQLite."""
        # This is CORRECT - SQLite doesn't have pg_trgm
        # The repo correctly returns empty, no violation
        logger.debug(f"[TM-REPO] Similarity search not available in SQLite")
        return []
```

This is NOT a violation because:
- SQLite repos are SUPPOSED to return empty for similarity
- They're implementing the interface correctly
- No cross-layer knowledge needed

### Pros
- TRUE abstraction - no wrapper magic
- SQLite repos work in BOTH modes
- Factory makes clean decisions
- PostgreSQL repos stay PURE (no SQLite checks)
- Reuses existing SQLite repo code

### Cons
- Need to refactor ALL 9 SQLite repos
- Need schema mapping logic
- Need separate database connection for server SQLite

### Files to Modify

**New Files:**
- `server/repositories/sqlite/base.py` - Schema-aware base class
- `server/database/server_sqlite.py` - Connection for server SQLite (ldm_* schema)

**Modified Files (All 9 SQLite repos):**
- `server/repositories/sqlite/tm_repo.py`
- `server/repositories/sqlite/row_repo.py`
- `server/repositories/sqlite/file_repo.py`
- `server/repositories/sqlite/project_repo.py`
- `server/repositories/sqlite/folder_repo.py`
- `server/repositories/sqlite/platform_repo.py`
- `server/repositories/sqlite/qa_repo.py`
- `server/repositories/sqlite/trash_repo.py`
- `server/repositories/sqlite/capability_repo.py`

**Clean PostgreSQL repos:**
- `server/repositories/postgresql/row_repo.py` - Remove violations
- `server/repositories/postgresql/tm_repo.py` - Remove violations

**Update factory:**
- `server/repositories/factory.py` - Add schema_mode logic

---

## Option D: Dual SQLite Repos (HARDEST)

**What it does:** Create completely separate repo classes for server SQLite mode.

### Design

```
server/repositories/
├── interfaces/           # Abstract base classes (unchanged)
├── postgresql/           # PostgreSQL implementations (cleaned)
├── sqlite/               # Offline mode (offline_* schema)
│   ├── tm_repo.py
│   ├── row_repo.py
│   └── ...
└── sqlite_server/        # Server fallback (ldm_* schema) (NEW)
    ├── tm_repo.py
    ├── row_repo.py
    └── ...
```

### Pros
- Complete separation
- No schema switching logic
- Each repo set is simple and focused
- Maximum clarity

### Cons
- Duplicates 9 entire repo classes
- Maintenance nightmare (changes need to be made in 2 places)
- Over-engineering for the actual problem

**Skip this option - too much duplication.**

---

## Recommendation: Option C (Schema-Aware SQLite Repos)

**Why:**
1. TRUE abstraction - no magic, no wrappers
2. Reuses existing code - SQLite repos just need table name flexibility
3. PostgreSQL repos stay PURE - no cross-layer knowledge
4. Clean factory logic - mode → repo type mapping
5. Future-proof - easy to add more schemas if needed

**Time estimate:** 8-12 hours
**Complexity:** HIGH but manageable
**Result:** ELEGANT, ROBUST architecture

---

## Implementation Plan for Option C

### Phase 1: Create Base Infrastructure (2 hours)

1. Create `server/repositories/sqlite/base.py`:
   - `SQLiteBaseRepository` class
   - `_table()` method for schema mapping
   - Schema mode enum

2. Create `server/database/server_sqlite.py`:
   - Connection manager for server SQLite (uses `ldm_*` tables)
   - Separate from `offline.py` (which uses `offline_*` tables)

### Phase 2: Refactor SQLite Repos (4-6 hours)

For each of the 9 SQLite repos:
1. Inherit from `SQLiteBaseRepository`
2. Replace hardcoded `offline_*` table names with `self._table("name")`
3. Accept `schema_mode` parameter in `__init__`
4. Test both modes

Order:
1. `project_repo.py` (simplest, good starting point)
2. `folder_repo.py`
3. `file_repo.py`
4. `row_repo.py`
5. `tm_repo.py` (most complex)
6. `platform_repo.py`
7. `qa_repo.py`
8. `trash_repo.py`
9. `capability_repo.py`

### Phase 3: Update Factory (1 hour)

1. Add `_is_sqlite_fallback()` function
2. Update all 9 `get_*_repository()` functions:
   - Offline mode → `SQLiteRepo(schema_mode="offline")`
   - SQLite fallback → `SQLiteRepo(schema_mode="server")`
   - PostgreSQL → `PostgreSQLRepo(db, user)`

### Phase 4: Clean PostgreSQL Repos (30 min)

Remove the 3 violations:
- `row_repo.py` lines 423-425
- `row_repo.py` lines 598-600
- `tm_repo.py` lines 1001-1003

### Phase 5: Testing (2 hours)

1. Unit tests for schema mapping
2. Integration tests with offline mode
3. Integration tests with SQLite fallback mode
4. Integration tests with PostgreSQL mode
5. Verify similarity search behavior in each mode

### Phase 6: Documentation & Commit (1 hour)

1. Update architecture docs
2. Mark ARCH-001 as FIXED
3. Commit with detailed message
4. Build and verify

---

## Quick Reference: Table Mapping

| Base Name | Offline Mode | Server Mode |
|-----------|--------------|-------------|
| projects | offline_projects | ldm_projects |
| folders | offline_folders | ldm_folders |
| files | offline_files | ldm_files |
| rows | offline_rows | ldm_rows |
| tms | offline_tms | ldm_translation_memories |
| tm_entries | offline_tm_entries | ldm_tm_entries |
| platforms | offline_platforms | ldm_platforms |
| qa_results | offline_qa_results | ldm_qa_results |
| trash | offline_trash | ldm_trash |

---

## Decision

**CHOOSE OPTION C** - Schema-Aware SQLite Repos

This is the HARD way. It takes 8-12 hours. But it results in:
- TRUE layer abstraction
- No magic wrappers
- No runtime interception
- Clean, explicit code
- ROBUST architecture that survives future changes

---

*Delete ARCHITECTURE_DEBT_REPORT.md after implementing Option C - it documents the MEDIUM solution.*
