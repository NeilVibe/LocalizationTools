# Architecture Debt Report: Repository Pattern Layer Violations

> **Created:** 2026-01-31 (Session 59 continuation)
> **Status:** NEEDS FIX - 3 layer violations identified
> **Priority:** HIGH - Architectural cleanliness
> **Estimated Fix Time:** 2-3 hours

---

## Executive Summary

The LocaNext repository pattern is **90% elegant** but contains **3 specific layer violations** where PostgreSQL repositories check `config.ACTIVE_DATABASE_TYPE` internally instead of relying on the factory pattern for abstraction.

**The Problem:** PostgreSQL repos should NEVER know about SQLite. The factory should handle all mode switching.

**Root Cause:** Schema mismatch between SQLite repos (`offline_*` tables) and server SQLite fallback (`ldm_*` tables) forced a workaround in Build 516.

---

## Table of Contents

1. [Current Architecture Overview](#1-current-architecture-overview)
2. [What's Working (Elegant Parts)](#2-whats-working-elegant-parts)
3. [The 3 Layer Violations (Bandaids)](#3-the-3-layer-violations-bandaids)
4. [Root Cause Analysis](#4-root-cause-analysis)
5. [The Schema Mismatch Problem](#5-the-schema-mismatch-problem)
6. [Solution Options](#6-solution-options)
7. [Recommended Fix (Option C)](#7-recommended-fix-option-c)
8. [Implementation Plan](#8-implementation-plan)
9. [Files to Modify](#9-files-to-modify)
10. [Verification Checklist](#10-verification-checklist)

---

## 1. Current Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│  LAYER 1: Routes (API Endpoints)                                        │
│  └─ Use repositories via Depends() - CLEAN ✅                           │
├─────────────────────────────────────────────────────────────────────────┤
│  LAYER 2: Repository Interfaces (ABCs)                                  │
│  └─ 9 interfaces: TM, Row, File, Project, Folder, Platform, QA, Trash, │
│     Capability - CLEAN ✅                                               │
├─────────────────────────────────────────────────────────────────────────┤
│  LAYER 3: Factory (Dependency Injection)                                │
│  └─ _is_offline_mode() checks auth header - CLEAN ✅                    │
│  └─ Returns SQLite or PostgreSQL repos based on mode                    │
├─────────────────────────────────────────────────────────────────────────┤
│  LAYER 4: Repository Implementations                                    │
│  ├─ PostgreSQL repos (server/repositories/postgresql/) - 3 VIOLATIONS ❌│
│  └─ SQLite repos (server/repositories/sqlite/) - CLEAN ✅               │
├─────────────────────────────────────────────────────────────────────────┤
│  LAYER 5: Database Connection                                           │
│  ├─ PostgreSQL: asyncpg (true async) - CLEAN ✅                         │
│  └─ SQLite: aiosqlite (true async) - CLEAN ✅ (fixed in Session 59)     │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. What's Working (Elegant Parts)

### 2.1 Repository Interfaces (Perfect)

Location: `server/repositories/interfaces/`

All 9 interfaces properly defined as Abstract Base Classes:

```python
# Example: server/repositories/interfaces/tm_repository.py
class TMRepository(ABC):
    @abstractmethod
    async def get(self, tm_id: int) -> Optional[Dict[str, Any]]: ...

    @abstractmethod
    async def search_similar(self, tm_id: int, source: str, ...) -> List[Dict]: ...
```

### 2.2 Factory Pattern (Clean)

Location: `server/repositories/factory.py`

```python
def _is_offline_mode(request: Request) -> bool:
    """Detect if request is in offline mode via auth header."""
    auth_header = request.headers.get("Authorization", "")
    return auth_header.startswith("Bearer OFFLINE_MODE_")

def get_tm_repository(request, db, current_user) -> TMRepository:
    if _is_offline_mode(request):
        return SQLiteTMRepository()
    else:
        return PostgreSQLTMRepository(db, current_user)
```

### 2.3 SQLite Repos (Proper Graceful Degradation)

Location: `server/repositories/sqlite/`

SQLite repos correctly implement interface with graceful degradation:

```python
# server/repositories/sqlite/tm_repo.py lines 822-834
async def search_similar(self, tm_id: int, source: str, ...) -> List[Dict]:
    """Similarity search - not available in SQLite (pg_trgm is PostgreSQL-specific)."""
    logger.debug(f"[TM-REPO] Similarity search not available in SQLite")
    return []  # ✅ CORRECT - graceful degradation
```

### 2.4 aiosqlite Migration (Complete)

Connection layer is now fully async for both databases:
- PostgreSQL: asyncpg (was already async)
- SQLite: aiosqlite (fixed in Session 59, Build 516)

---

## 3. The 3 Layer Violations (Bandaids)

### Violation 1: `postgresql/row_repo.py` line 423

```python
async def _fuzzy_search(self, file_id: int, search_text: str, ...) -> Tuple[List, int]:
    """Fuzzy search with pg_trgm."""
    from server import config

    # ❌ LAYER VIOLATION: PostgreSQL repo checking for SQLite
    if config.ACTIVE_DATABASE_TYPE == "sqlite":
        logger.debug("[ROW-REPO] Fuzzy search not available (SQLite mode)")
        return [], 0

    # ... PostgreSQL-specific pg_trgm query ...
```

### Violation 2: `postgresql/row_repo.py` line 598

```python
async def suggest_similar(self, source: str, ...) -> List[Dict]:
    """Suggest similar translations using pg_trgm."""
    from server import config

    # ❌ LAYER VIOLATION: PostgreSQL repo checking for SQLite
    if config.ACTIVE_DATABASE_TYPE == "sqlite":
        logger.debug("[ROW-REPO] Similarity search not available (SQLite mode)")
        return []

    # ... PostgreSQL-specific similarity query ...
```

### Violation 3: `postgresql/tm_repo.py` line 1001

```python
async def search_similar(self, tm_id: int, source: str, ...) -> List[Dict]:
    """Search for similar TM entries using pg_trgm."""
    from server import config

    # ❌ LAYER VIOLATION: PostgreSQL repo checking for SQLite
    if config.ACTIVE_DATABASE_TYPE == "sqlite":
        logger.debug("[TM-REPO] Similarity search not available (SQLite mode)")
        return []

    # ... PostgreSQL-specific similarity query ...
```

---

## 4. Root Cause Analysis

### Why Do These Violations Exist?

**Build 515 attempted a "clean" fix:**
```python
# factory.py - attempted fix
def _is_offline_mode(request):
    # Check if server is using SQLite fallback
    if config.ACTIVE_DATABASE_TYPE == "sqlite":
        return True  # Route to SQLite repos
    # ... rest of logic
```

**This caused 500 errors because:**
- SQLite repos query `offline_projects`, `offline_folders`, `offline_files`
- Server creates `ldm_projects`, `ldm_folders`, `ldm_files`
- **Schema mismatch → tables don't exist → 500 errors**

**Build 516 "fixed" it with bandaids:**
- Reverted factory change
- Added SQLite checks inside PostgreSQL repos
- Works, but violates layer abstraction

### The Two Different SQLite Use Cases

| Use Case | Schema | Repos | Triggered By |
|----------|--------|-------|--------------|
| **OFFLINE MODE** (user's local data) | `offline_*` tables | SQLite repos | `Bearer OFFLINE_MODE_` header |
| **SERVER FALLBACK** (PostgreSQL down) | `ldm_*` tables | PostgreSQL repos | `ACTIVE_DATABASE_TYPE == "sqlite"` |

**The factory only handles Use Case 1, not Use Case 2.**

---

## 5. The Schema Mismatch Problem

### offline_schema.sql (SQLite Offline Mode)

```sql
-- Tables for offline mode (user's local cache)
CREATE TABLE offline_platforms (...);
CREATE TABLE offline_projects (...);
CREATE TABLE offline_folders (...);
CREATE TABLE offline_files (...);
CREATE TABLE offline_rows (...);
CREATE TABLE offline_tms (...);
CREATE TABLE offline_tm_entries (...);

-- Sync metadata (not in PostgreSQL)
CREATE TABLE sync_meta (...);
CREATE TABLE local_changes (...);
CREATE TABLE sync_subscriptions (...);
```

### models.py (Server Standard Schema)

```python
# Tables for server (PostgreSQL or SQLite fallback)
class LDMPlatform(Base):
    __tablename__ = "ldm_platforms"

class LDMProject(Base):
    __tablename__ = "ldm_projects"

class LDMFolder(Base):
    __tablename__ = "ldm_folders"

# ... etc
```

### The Mismatch

| SQLite Repos Expect | Server Creates |
|---------------------|----------------|
| `offline_platforms` | `ldm_platforms` |
| `offline_projects` | `ldm_projects` |
| `offline_folders` | `ldm_folders` |
| `offline_files` | `ldm_files` |
| `offline_rows` | `ldm_rows` |
| `offline_tms` | `ldm_translation_memories` |

**This is why we can't just route to SQLite repos when server falls back to SQLite.**

---

## 6. Solution Options

### Option A: Create Third Repo Type (NOT RECOMMENDED)

Create `ServerSQLiteRepository` classes that use `ldm_*` schema.

**Pros:** Clean separation
**Cons:**
- Duplicates 9 entire repository classes
- Maintenance nightmare
- Over-engineering

### Option B: Make SQLite Repos Use `ldm_*` Schema (RISKY)

Modify SQLite repos to query `ldm_*` tables instead of `offline_*`.

**Pros:** No new repos needed
**Cons:**
- Breaks offline mode (sync metadata lost)
- `offline_*` tables have extra columns for sync
- Architectural confusion

### Option C: Remove Violations, Accept Limitation (RECOMMENDED)

Remove the SQLite checks from PostgreSQL repos. Let PostgreSQL-specific functions fail naturally when database is SQLite.

**Pros:**
- Clean layer abstraction
- No code duplication
- Honest about limitations

**Cons:**
- Need to handle errors gracefully at route level
- Minor behavior change

### Option D: Hybrid - Factory Checks + Wrapper (MOST ELEGANT)

1. Factory detects server SQLite fallback mode
2. Returns PostgreSQL repos wrapped with capability checker
3. Wrapper handles graceful degradation, not repos

**Pros:**
- Perfect layer abstraction
- No violations in repos
- Graceful degradation preserved

**Cons:**
- More complex implementation
- New wrapper class needed

---

## 7. Recommended Fix (Option D - Most Elegant)

### Design

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Factory (enhanced)                                                     │
│  ├─ _is_offline_mode(request) → SQLiteRepo (for offline_* schema)      │
│  ├─ _is_sqlite_fallback() → CapabilityAwareWrapper(PostgreSQLRepo)     │
│  └─ else → PostgreSQLRepo (direct)                                     │
└─────────────────────────────────────────────────────────────────────────┘

CapabilityAwareWrapper:
├─ Wraps any repository
├─ Checks if method requires PostgreSQL-specific features
├─ Returns graceful degradation for unsupported methods
└─ Delegates to wrapped repo for supported methods
```

### New Class: CapabilityAwareWrapper

```python
# server/repositories/capability_wrapper.py (NEW FILE)

from typing import List, Dict, Any, Optional
from server import config
from loguru import logger

class CapabilityAwareWrapper:
    """
    Wraps a repository to handle capability-based graceful degradation.

    When server runs with SQLite fallback, PostgreSQL-specific features
    (similarity search, fuzzy search) gracefully return empty results
    without the repo needing to know about database type.
    """

    # Methods that require PostgreSQL-specific features
    POSTGRESQL_ONLY_METHODS = {
        'search_similar',      # Uses pg_trgm similarity()
        'suggest_similar',     # Uses pg_trgm similarity()
        '_fuzzy_search',       # Uses pg_trgm similarity()
    }

    def __init__(self, wrapped_repo):
        self._wrapped = wrapped_repo

    def __getattr__(self, name):
        """Intercept method calls to check capabilities."""
        attr = getattr(self._wrapped, name)

        if name in self.POSTGRESQL_ONLY_METHODS and self._is_sqlite_mode():
            # Return a wrapper that gracefully degrades
            async def graceful_degradation(*args, **kwargs):
                logger.debug(f"[CAPABILITY] {name}() not available in SQLite mode")
                # Return appropriate empty value based on method
                if name == '_fuzzy_search':
                    return [], 0
                return []
            return graceful_degradation

        return attr

    def _is_sqlite_mode(self) -> bool:
        """Check if running in SQLite fallback mode."""
        return config.ACTIVE_DATABASE_TYPE == "sqlite"
```

### Updated Factory

```python
# server/repositories/factory.py (MODIFIED)

from server.repositories.capability_wrapper import CapabilityAwareWrapper

def _is_sqlite_fallback() -> bool:
    """Check if server is running in SQLite fallback mode (not offline mode)."""
    from server import config
    return config.ACTIVE_DATABASE_TYPE == "sqlite"

def get_tm_repository(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
) -> TMRepository:
    """Get TM repository with capability awareness."""
    from server.repositories.postgresql.tm_repo import PostgreSQLTMRepository
    from server.repositories.sqlite.tm_repo import SQLiteTMRepository

    if _is_offline_mode(request):
        # Explicit offline mode - use SQLite repos with offline_* schema
        return SQLiteTMRepository()

    repo = PostgreSQLTMRepository(db, current_user)

    if _is_sqlite_fallback():
        # Server SQLite fallback - wrap with capability checker
        return CapabilityAwareWrapper(repo)

    return repo
```

### Clean PostgreSQL Repos

After implementing the wrapper, REMOVE the violations:

```python
# server/repositories/postgresql/row_repo.py - CLEAN VERSION

async def _fuzzy_search(self, file_id: int, search_text: str, ...) -> Tuple[List, int]:
    """Fuzzy search with pg_trgm."""
    # NO MORE SQLite check here!
    # The CapabilityAwareWrapper handles this at factory level

    sql = text("""
        SELECT r.*, similarity(r.source, :search) as sim
        FROM ldm_rows r
        WHERE r.file_id = :file_id
          AND similarity(r.source, :search) >= :threshold
        ORDER BY sim DESC
    """)
    # ... rest of implementation
```

---

## 8. Implementation Plan

### Phase 1: Create CapabilityAwareWrapper (30 minutes)

1. Create new file: `server/repositories/capability_wrapper.py`
2. Implement `CapabilityAwareWrapper` class
3. Define `POSTGRESQL_ONLY_METHODS` set
4. Test wrapper in isolation

### Phase 2: Update Factory (30 minutes)

1. Add `_is_sqlite_fallback()` function
2. Update all 9 `get_*_repository()` functions
3. Import and use `CapabilityAwareWrapper`
4. Test factory returns correct types

### Phase 3: Clean PostgreSQL Repos (1 hour)

1. Remove SQLite check from `row_repo.py` line 423
2. Remove SQLite check from `row_repo.py` line 598
3. Remove SQLite check from `tm_repo.py` line 1001
4. Remove `from server import config` imports (if no longer needed)
5. Update method docstrings

### Phase 4: Test (30 minutes)

1. Run full test suite: `pytest tests/ -x`
2. Test with PostgreSQL available
3. Test with SQLite fallback (stop PostgreSQL)
4. Verify graceful degradation works
5. Check logs for proper capability messages

### Phase 5: Documentation & Build (30 minutes)

1. Update this document with completion status
2. Update SESSION_CONTEXT.md
3. Commit changes
4. Trigger build (GitHub + Gitea)
5. Verify build success

---

## 9. Files to Modify

### New Files

| File | Purpose |
|------|---------|
| `server/repositories/capability_wrapper.py` | CapabilityAwareWrapper class |

### Modified Files

| File | Changes |
|------|---------|
| `server/repositories/factory.py` | Add `_is_sqlite_fallback()`, wrap repos |
| `server/repositories/postgresql/row_repo.py` | Remove lines 423-425, 598-600 |
| `server/repositories/postgresql/tm_repo.py` | Remove lines 1001-1003 |
| `docs/current/SESSION_CONTEXT.md` | Update with Session 60 |
| `docs/current/ISSUES_TO_FIX.md` | Mark ARCH-001 as fixed |

---

## 10. Verification Checklist

After implementation, verify:

- [ ] `CapabilityAwareWrapper` exists and works
- [ ] Factory uses wrapper for SQLite fallback mode
- [ ] PostgreSQL repos have NO `ACTIVE_DATABASE_TYPE` checks
- [ ] `grep -r "ACTIVE_DATABASE_TYPE" server/repositories/postgresql/` returns 0 results
- [ ] Tests pass with PostgreSQL: `pytest tests/ -x`
- [ ] Tests pass with SQLite fallback: `DATABASE_MODE=sqlite pytest tests/ -x`
- [ ] Similarity search works in PostgreSQL mode
- [ ] Similarity search returns empty in SQLite fallback mode
- [ ] Logs show `[CAPABILITY]` messages in SQLite fallback mode
- [ ] Build succeeds on GitHub
- [ ] Build succeeds on Gitea

---

## Appendix: Quick Reference for Next Session

### Start Commands

```bash
# Check current state
grep -n "ACTIVE_DATABASE_TYPE" server/repositories/postgresql/*.py

# Should find 3 violations before fix, 0 after

# Run tests
./scripts/start_all_servers.sh
pytest tests/ -x -q

# Check SQLite fallback mode
DATABASE_MODE=sqlite python3 -c "from server import config; print(config.ACTIVE_DATABASE_TYPE)"
```

### The 3 Lines to Remove

```
server/repositories/postgresql/row_repo.py:423-425
server/repositories/postgresql/row_repo.py:598-600
server/repositories/postgresql/tm_repo.py:1001-1003
```

### Git Commands After Fix

```bash
git add -A
git commit -m "Refactor: Remove layer violations with CapabilityAwareWrapper

- Created CapabilityAwareWrapper for graceful degradation
- Updated factory to wrap repos in SQLite fallback mode
- Removed ACTIVE_DATABASE_TYPE checks from PostgreSQL repos
- Clean layer abstraction preserved

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"

git push origin main
./scripts/gitea_control.sh start
git push gitea main
```

---

*Document created: 2026-01-31 | Ready for Session 60 implementation*
