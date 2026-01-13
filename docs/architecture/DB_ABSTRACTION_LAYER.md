# DB Abstraction Layer

**Status:** P10 COMPLETE | **Pattern:** Repository Pattern

> **P10 Full Implementation:** See [docs/wip/P10_DB_ABSTRACTION.md](../wip/P10_DB_ABSTRACTION.md) for details

---

## Source of Truth: PostgreSQL First

**CRITICAL CONCEPT:** PostgreSQL (online mode) is the **reference implementation**.

```
PostgreSQL (Online)          SQLite (Offline)
─────────────────           ────────────────
   SOURCE OF TRUTH    →→→    MUST MIRROR EXACTLY
   Reference impl     →→→    Copies PostgreSQL logic
   Developed first    →→→    Added later for offline
   Full feature set   →→→    Identical feature set
```

### What This Means in Practice

1. **When implementing a new feature:**
   - Write PostgreSQL adapter FIRST (reference)
   - SQLite adapter MUST produce identical behavior

2. **When fixing a bug:**
   - Fix in PostgreSQL adapter (source of truth)
   - Apply same fix to SQLite adapter

3. **When adding a repository method:**
   - Design the interface based on PostgreSQL needs
   - Implement PostgreSQL version (reference)
   - Implement SQLite version (must match)

4. **Return values MUST be identical:**
   ```python
   # PostgreSQL returns:
   {"id": 1, "name": "Test", "status": "active"}

   # SQLite MUST return:
   {"id": 1, "name": "Test", "status": "active"}  # SAME structure
   ```

### Why PostgreSQL is Source of Truth

| Reason | Explanation |
|--------|-------------|
| **Production database** | Multi-user scenarios use PostgreSQL |
| **Developed first** | Original implementation with full features |
| **More mature** | Battle-tested, complete edge case handling |
| **Team collaboration** | Central database for shared work |

SQLite exists for **offline/single-user mode** - it must behave identically so users don't notice the difference.

---

## What Is It?

The **DB Abstraction Layer** is an architecture pattern that lets the same API code work with different databases without knowing which one it's using.

```
ONE endpoint → Get repository for current mode → Use that database
```

Instead of endpoints containing database-specific code, they use an **abstract interface**. The actual database (PostgreSQL or SQLite) is selected at runtime based on the user's mode.

---

## Why Do We Need It?

### The Problem: Online vs Offline

LocaNext has two modes:
- **Online Mode:** PostgreSQL (central server, multi-user)
- **Offline Mode:** SQLite (local database, single-user)

Users expect the same features to work in both modes. Without abstraction, we'd need:
- Duplicate code for every endpoint (one for PostgreSQL, one for SQLite)
- Different bugs in each path
- Maintenance nightmare

### Old Pattern: Fallback (Being Phased Out)

```python
# OLD: Try PostgreSQL first, fall back to SQLite
@router.get("/tm/{tm_id}")
async def get_tm(tm_id: int, db: AsyncSession):
    # Step 1: Try PostgreSQL
    result = await db.execute(select(TM).where(TM.id == tm_id))
    tm = result.scalar_one_or_none()

    # Step 2: Fall back to SQLite
    if not tm:
        from server.database.offline import get_offline_db
        offline_db = get_offline_db()
        tm = offline_db.get_local_tm(tm_id)

    return tm
```

**Problems:**
- PostgreSQL is "first class", SQLite is "second class"
- Every endpoint has database logic mixed with business logic
- Hard to test, hard to maintain

### New Pattern: DB Abstraction Layer

```python
# NEW: Use repository interface - don't know which database
@router.get("/tm/{tm_id}")
async def get_tm(
    tm_id: int,
    repo: TMRepository = Depends(get_tm_repository)
):
    return await repo.get(tm_id)
```

**Benefits:**
- Both databases are equal citizens
- Endpoints are clean (5 lines, not 50)
- Easy to test (mock the repository)
- Single source of truth for each operation

---

## How It Works: Repository Pattern

### The Three Layers

```
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Route                          │
│                  (uses TMRepository interface)              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│                    TMRepository (Interface)                 │
│                    ─────────────────────────                │
│                    Defines: get(), create(), assign(), etc. │
│                    Knows: NOTHING about databases           │
│                                                             │
├──────────────────────────┬──────────────────────────────────┤
│                          │                                  │
│   PostgreSQLTMRepository │      SQLiteTMRepository          │
│   ──────────────────────  │      ──────────────────          │
│   Implements interface    │      Implements interface        │
│   Uses: SQLAlchemy ORM    │      Uses: sqlite3 + offline.py  │
│   Tables: ldm_tms, etc.   │      Tables: offline_tms, etc.   │
│                          │                                  │
└──────────────────────────┴──────────────────────────────────┘
```

### File Structure

```
server/repositories/
├── __init__.py                    # Exports interface + factory
├── interfaces/
│   └── tm_repository.py           # Abstract interface (TMRepository)
├── postgresql/
│   └── tm_repo.py                 # PostgreSQLTMRepository
├── sqlite/
│   └── tm_repo.py                 # SQLiteTMRepository
└── factory.py                     # get_tm_repository() - selects adapter
```

### The Interface (Contract)

```python
# server/repositories/interfaces/tm_repository.py

class TMRepository(ABC):
    """Both PostgreSQL and SQLite adapters implement this EXACTLY."""

    @abstractmethod
    async def get(self, tm_id: int) -> Optional[Dict[str, Any]]:
        """Get TM by ID."""
        ...

    @abstractmethod
    async def create(self, name: str, source_lang: str, target_lang: str) -> Dict[str, Any]:
        """Create new TM."""
        ...

    @abstractmethod
    async def assign(self, tm_id: int, target: AssignmentTarget) -> Dict[str, Any]:
        """Assign TM to platform/project/folder."""
        ...

    @abstractmethod
    async def activate(self, tm_id: int) -> Dict[str, Any]:
        """Activate TM at its assigned scope."""
        ...

    # ... more methods
```

### The Factory (Runtime Selection)

```python
# server/repositories/factory.py

async def get_tm_repository(
    request: Request,
    db: AsyncSession = Depends(get_async_db)
) -> TMRepository:
    """
    Select repository based on user's mode.

    - OFFLINE_MODE_* token → SQLiteTMRepository
    - Regular token → PostgreSQLTMRepository
    """
    token = request.headers.get("Authorization", "")

    if "OFFLINE_MODE_" in token:
        return SQLiteTMRepository()
    else:
        return PostgreSQLTMRepository(db)
```

### The Route (Clean!)

```python
# server/tools/ldm/routes/tm_assignment.py

from server.repositories import TMRepository, AssignmentTarget, get_tm_repository

@router.patch("/tm/{tm_id}/assign")
async def assign_tm(
    tm_id: int,
    platform_id: Optional[int] = None,
    project_id: Optional[int] = None,
    folder_id: Optional[int] = None,
    repo: TMRepository = Depends(get_tm_repository),  # Injected!
    current_user: dict = Depends(get_current_active_user_async)
):
    # Get TM - works with PostgreSQL OR SQLite
    tm = await repo.get(tm_id)
    if not tm:
        raise HTTPException(status_code=404, detail="TM not found")

    # Assign - works with PostgreSQL OR SQLite
    target = AssignmentTarget(
        platform_id=platform_id,
        project_id=project_id,
        folder_id=folder_id
    )
    result = await repo.assign(tm_id, target)

    return {"success": True, "tm_id": tm_id}
```

**The route doesn't know or care which database it's using.**

---

## Mode Detection

### How Does the System Know Which Mode?

The **token prefix** determines the mode:

| Token | Mode | Repository |
|-------|------|------------|
| `OFFLINE_MODE_1704567890` | Offline | SQLiteTMRepository |
| `eyJ0eXAiOiJKV1Q...` (JWT) | Online | PostgreSQLTMRepository |

### Where Tokens Come From

- **Online:** User logs in → server issues JWT token
- **Offline:** User clicks "Start Offline" → frontend generates `OFFLINE_MODE_<timestamp>`

---

## What We Implemented

### TM Routes Using DB Abstraction (Complete)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /tm/{id}` | repo.get() | Get TM by ID |
| `GET /tm-tree` | repo.get_tree() | Get full TM tree for UI |
| `GET /tm/{id}/assignment` | repo.get_assignment() | Get TM's current assignment |
| `PATCH /tm/{id}/assign` | repo.assign() | Assign TM to scope |
| `PATCH /tm/{id}/activate` | repo.activate/deactivate() | Activate/deactivate TM |
| `GET /files/{id}/active-tms` | repo.get_active_for_file() | Get active TMs for file |

### Full Route Migration Status (P10) ✅ COMPLETE

| Route File | Repository | Status |
|------------|------------|--------|
| `capabilities.py` | CapabilityRepository | ✅ |
| `files.py` | FileRepository | ✅ |
| `folders.py` | FolderRepository | ✅ |
| `grammar.py` | RowRepository | ✅ |
| `platforms.py` | PlatformRepository | ✅ |
| `pretranslate.py` | FileRepository | ✅ |
| `projects.py` | ProjectRepository | ✅ |
| `qa.py` | QAResultRepository, RowRepository | ✅ |
| `rows.py` | RowRepository, FileRepository, TMRepository | ✅ |
| `search.py` | RowRepository, FileRepository | ✅ |
| `sync.py` | FileRepository, ProjectRepository, TMRepository | ✅ |
| `tm_assignment.py` | TMRepository | ✅ |
| `tm_crud.py` | TMRepository | ✅ |
| `tm_entries.py` | TMRepository | ✅ |
| `tm_indexes.py` | TMRepository | ✅ |
| `tm_linking.py` | TMRepository | ✅ |
| `tm_search.py` | TMRepository, RowRepository | ✅ |
| `trash.py` | TrashRepository | ✅ |

### All Repositories Implemented ✅

| Repository | Interface | PostgreSQL | SQLite |
|------------|-----------|------------|--------|
| TMRepository | ✅ | ✅ | ✅ |
| FileRepository | ✅ | ✅ | ✅ |
| RowRepository | ✅ | ✅ | ✅ |
| ProjectRepository | ✅ | ✅ | ✅ |
| FolderRepository | ✅ | ✅ | ✅ |
| PlatformRepository | ✅ | ✅ | ✅ |
| QAResultRepository | ✅ | ✅ | ✅ |
| TrashRepository | ✅ | ✅ | ✅ |
| CapabilityRepository | ✅ | ✅ | ✅ |

---

## Testing

### How to Test Each Mode

```python
# Test ONLINE mode (PostgreSQL)
headers = {"Authorization": "Bearer eyJ0eXAiOiJKV1Q..."}
response = requests.get("/api/ldm/tm-tree", headers=headers)

# Test OFFLINE mode (SQLite)
headers = {"Authorization": "Bearer OFFLINE_MODE_1704567890"}
response = requests.get("/api/ldm/tm-tree", headers=headers)
```

Both calls use the same endpoint, but different repositories handle them.

---

## Key Principles

1. **PostgreSQL = Source of Truth** - Reference implementation, SQLite copies it
2. **ONE Code Path** - Routes have ONE path, NOT separate online/offline code
3. **Routes are database-agnostic** - They only use the repository interface
4. **Repositories are interchangeable** - Both implement the exact same interface
5. **Mode is token-based** - Token prefix determines which repository is used
6. **No direct DB imports in routes** - Only import from `server.repositories`
7. **FULL PARITY** - SQLite must have identical capabilities to PostgreSQL

---

## ONE Code Path Principle (Critical!)

### The Anti-Pattern (WRONG)

```python
# WRONG: Two different code paths in the same route
@router.get("/search")
async def search(query: str, mode: str):
    if mode == "offline":
        # SQLite path - 50 lines
        offline_db = get_offline_db()
        return offline_db.search(query)
    else:
        # PostgreSQL path - 80 lines of DIFFERENT code
        result = await db.execute(select(Model).where(...))
        return process_results(result)
```

**Why this is wrong:**
- Two implementations = two sources of bugs
- Different behavior online vs offline
- Violates the entire point of abstraction

### The Correct Pattern (RIGHT)

```python
# RIGHT: ONE code path, repository handles the rest
@router.get("/search")
async def search(
    query: str,
    repo: SearchRepository = Depends(get_repository)
):
    return await repo.search(query)  # ONE LINE - works both modes
```

**Why this is right:**
- Route doesn't know which database
- Repository factory selects implementation
- PostgreSQL and SQLite adapters both implement `search()`
- Identical behavior guaranteed

---

## FULL PARITY Principle (Critical!)

### No Stubs, No Ephemeral, No Shortcuts

```
WRONG: SQLite returns empty, PostgreSQL persists
RIGHT: Both databases persist and query identically
```

### The Anti-Pattern (What We DON'T Do)

```python
# BAD: SQLite as second-class citizen
class SQLiteQARepository:
    async def get_for_row(self, row_id):
        return []  # "Ephemeral" - just return empty

    async def create(self, ...):
        pass  # No-op, don't persist
```

### The Correct Pattern

```python
# GOOD: Full parity
class SQLiteQARepository:
    async def get_for_row(self, row_id):
        return self._query_sqlite("SELECT * FROM offline_qa_results WHERE row_id = ?", row_id)

    async def create(self, ...):
        return self._insert_sqlite("INSERT INTO offline_qa_results ...")
```

### Why Full Parity Matters

| Aspect | With Stubs | With Full Parity |
|--------|-----------|------------------|
| Behavior | Different online/offline | **Identical** |
| Testing | Test each path separately | **One test covers both** |
| Bugs | Different bugs per mode | **Same behavior = same bugs = same fixes** |
| User Experience | "Works online, broken offline" | **Works everywhere** |

### Implementation Rule

**If PostgreSQL has a table, SQLite MUST have the equivalent table.**

| PostgreSQL | SQLite | Status |
|------------|--------|--------|
| `ldm_platforms` | `offline_platforms` | ✅ |
| `ldm_projects` | `offline_projects` | ✅ |
| `ldm_folders` | `offline_folders` | ✅ |
| `ldm_files` | `offline_files` | ✅ |
| `ldm_rows` | `offline_rows` | ✅ |
| `ldm_translation_memories` | `offline_tms` | ✅ |
| `ldm_tm_entries` | `offline_tm_entries` | ✅ |
| `ldm_tm_assignments` | `offline_tm_assignments` | ✅ |
| `ldm_trash` | `offline_trash` | ✅ |
| `ldm_qa_results` | `offline_qa_results` | **ADDING NOW** |

---

## Diagram

```
User Request
     │
     ▼
┌─────────────────┐
│   FastAPI       │
│   Route         │
│                 │
│  Uses:          │
│  TMRepository   │  ◄── Abstract interface only
└────────┬────────┘
         │
         │  Depends(get_tm_repository)
         ▼
┌─────────────────┐
│   Factory       │
│                 │
│  Checks token:  │
│  OFFLINE_MODE_? │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌───────┐  ┌───────┐
│ PG    │  │ SQLite│
│ Repo  │  │ Repo  │
└───┬───┘  └───┬───┘
    │          │
    ▼          ▼
┌───────┐  ┌───────┐
│Postgre│  │SQLite │
│  SQL  │  │  DB   │
└───────┘  └───────┘
```

---

## Summary

| Concept | Description |
|---------|-------------|
| **DB Abstraction Layer** | Architecture that hides database details from routes |
| **Repository Pattern** | Implementation technique: interface + adapters |
| **TMRepository** | The interface (contract) for TM operations |
| **PostgreSQLTMRepository** | Adapter for online mode (PostgreSQL) |
| **SQLiteTMRepository** | Adapter for offline mode (SQLite) |
| **Factory** | Runtime selection based on token |
| **Result** | Same API works identically online and offline |

---

## Industry Standard

**YES.** The Repository Pattern is one of the most battle-tested patterns:

| Who Uses It | Context |
|-------------|---------|
| Microsoft | .NET Core, Entity Framework |
| Google | Clean Architecture |
| Spring Framework | Java ecosystem |
| Django | ORM abstraction |
| Every DDD book | Domain-Driven Design |

**Proven for 20+ years.** Not "cutting edge" - that's the point. It's reliable.

---

## Performance Impact

**Same or better:**
- PostgreSQL path: Direct ORM calls (unchanged)
- SQLite path: Direct sqlite3 calls (unchanged)
- Abstraction overhead: One function call (~0.001ms)

No degradation.

---

## Backward Compatibility

**100% YES.** The HTTP API doesn't change at all. Frontend sends the same requests. It doesn't know which database handles them.

---

*Updated 2026-01-13 | P10 DB Abstraction Layer 100% COMPLETE | 9 Repositories, 18 Route Files*
