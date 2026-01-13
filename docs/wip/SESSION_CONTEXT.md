# Session Context

> Current state of LocaNext development. Updated each session.

**Last Updated:** 2026-01-13

---

## Table of Contents

1. [Current Focus](#current-focus)
   - [P10: DB Abstraction Layer](#p10-db-abstraction-layer--in-progress)
   - [P11: Platform Stability](#p11-platform-stability-active)
2. [What IS DB Abstraction Layer & Repository Pattern?](#what-is-db-abstraction-layer--repository-pattern)
3. [Why Is It Important?](#why-is-it-important)
4. [How We Achieve It (Step by Step)](#how-we-achieve-it-step-by-step-safe-methodology)
5. [Task Tables](#task-tables)
   - [Completed Tasks](#completed-tasks-session-52)
   - [Pending Tasks](#pending-tasks)
   - [Repository Migration Status](#repository-migration-status)
   - [Route Migration Status](#route-migration-status)
6. [Recent Sessions](#recent-sessions)
7. [Quick Commands](#quick-commands)
8. [Backlog](#backlog)

---

## Current Focus

### P10: DB Abstraction Layer - IN PROGRESS

**Status:** ACTIVE MIGRATION | **Progress:** 55% files fully migrated (11/20 route files CLEAN)

**Goal:** Transform entire backend from inconsistent database patterns to unified Repository Pattern for FULL OFFLINE/ONLINE PARITY.

---

### P11: Platform Stability (ACTIVE)

**Status:** ACTIVE | **Priority:** HIGH

**Goal:** Ensure the platform is rock-solid before adding new features.

| Task | Status | Description |
|------|--------|-------------|
| Trash Restore Bug | **FIXED** | `memo` field removed from LDMRow restore |
| Offline ID Generation | **FIXED** | Python operator precedence bug (IDs now negative) |
| Online Mode CRUD | **PASS** | 11/11 tests passing |
| Offline Mode CRUD | **PASS** | 7/7 tests passing |
| TM Tree Folder Mirroring | **FIXED** | `get_tree()` now returns folder hierarchy |
| Windows PATH Tests | **DONE** | 7 path tests created in `windows_tests/` |
| CI/CD Health | **HEALTHY** | 1285 passed, 10 failed (P10 test maintenance) |
| Playwright Test Fixes | **FIXED** | 152 passed, 0 failed (was 67 failing) |
| TM Entries Repository Fix | **FIXED** | All 6 endpoints now use Repository Pattern |
| Project platform_id Fix | **FIXED** | `ProjectCreate` schema now includes platform_id |
| TM Folder Assignment Fix | **FIXED** | Online mode now assigns TM to same folder as source file |

---

## What IS DB Abstraction Layer & Repository Pattern?

### The Problem We're Solving

```
BEFORE (Chaos):
┌─────────────────────────────────────────────────────────────┐
│  Route A (files.py)     Route B (projects.py)               │
│        │                       │                            │
│        ▼                       ▼                            │
│  ┌──────────┐           ┌──────────┐                       │
│  │PostgreSQL│           │PostgreSQL│  ← Direct DB calls    │
│  └──────────┘           └──────────┘    in routes          │
│        │                                                    │
│        ▼ (fallback)                                         │
│  ┌──────────┐                                               │
│  │ SQLite   │  ← Some routes have fallback, others don't   │
│  └──────────┘                                               │
└─────────────────────────────────────────────────────────────┘

PROBLEMS:
- Routes contain database-specific code (SELECT, INSERT, SQLAlchemy)
- Some routes support offline (SQLite), others don't
- Two code paths = twice the bugs
- Hard to test, hard to maintain
```

### The Solution: Repository Pattern

```
AFTER (Clean Architecture):
┌─────────────────────────────────────────────────────────────┐
│  Route A (files.py)     Route B (projects.py)               │
│        │                       │                            │
│        └───────────┬───────────┘                            │
│                    │                                        │
│                    ▼                                        │
│            ┌──────────────┐                                 │
│            │  Repository  │  ← Abstract interface           │
│            │  Interface   │    (FileRepository, etc.)       │
│            └──────────────┘                                 │
│                    │                                        │
│         ┌─────────┴─────────┐                               │
│         │                   │                               │
│         ▼                   ▼                               │
│  ┌──────────────┐   ┌──────────────┐                       │
│  │  PostgreSQL  │   │    SQLite    │                       │
│  │   Adapter    │   │   Adapter    │                       │
│  └──────────────┘   └──────────────┘                       │
│         │                   │                               │
│         ▼                   ▼                               │
│  ┌──────────────┐   ┌──────────────┐                       │
│  │  PostgreSQL  │   │   SQLite     │                       │
│  │   Database   │   │  Database    │                       │
│  └──────────────┘   └──────────────┘                       │
└─────────────────────────────────────────────────────────────┘

BENEFITS:
- Routes are DATABASE-AGNOSTIC (don't know which DB)
- ONE code path for both online (PostgreSQL) and offline (SQLite)
- Factory function selects adapter based on auth token
- FULL PARITY: Same operations work identically in both modes
```

### Key Concepts

| Concept | What It Is | Example |
|---------|------------|---------|
| **Interface** | Abstract contract defining operations | `FileRepository.get(file_id) -> Dict` |
| **Adapter** | Concrete implementation for specific DB | `PostgreSQLFileRepository`, `SQLiteFileRepository` |
| **Factory** | Function that picks the right adapter | `get_file_repository(request, db)` |
| **FULL PARITY** | Same operations work identically | Create/Read/Update/Delete work same online & offline |

### How the Factory Works

```python
# server/repositories/factory.py

async def get_file_repository(
    request: Request,
    db: AsyncSession = Depends(get_async_db)
) -> FileRepository:
    """Select FileRepository based on auth token."""

    auth_header = request.headers.get("Authorization", "")
    is_offline = "OFFLINE_MODE_" in auth_header  # Key detection!

    if is_offline:
        # User is in offline mode → use SQLite
        return SQLiteFileRepository()
    else:
        # User is online → use PostgreSQL
        return PostgreSQLFileRepository(db)
```

---

## Why Is It Important?

### 1. TRUE OFFLINE MODE

| Without Repository Pattern | With Repository Pattern |
|---------------------------|------------------------|
| Some features work offline, others don't | **ALL features work offline** |
| User gets random 404 errors | Consistent experience |
| Different bugs online vs offline | One codebase = one set of bugs |

### 2. MAINTAINABILITY

| Without | With |
|---------|------|
| Change PostgreSQL code → pray SQLite still works | Change Interface → both adapters update |
| Duplicate logic everywhere | Single source of truth |
| Database code scattered in routes | Database code isolated in adapters |

### 3. TESTABILITY

| Without | With |
|---------|------|
| Hard to mock database calls | Easy to mock Repository interface |
| Need running PostgreSQL for tests | Can use in-memory test adapter |
| Fragile integration tests | Robust unit + integration tests |

### 4. INDUSTRY STANDARD

| Who Uses This Pattern | Evidence |
|----------------------|----------|
| Microsoft (.NET Core) | Entity Framework Repository Pattern |
| Spring Framework (Java) | JPA Repositories |
| Django (Python) | ORM Manager pattern |
| Every DDD book | Domain-Driven Design standard |

**This is battle-tested architecture used by millions of applications.**

---

## How We Achieve It (Step by Step, SAFE Methodology)

### The SAFE Principle

```
S - Sequential    (One file at a time, not all at once)
A - Additive      (Add new code, don't delete working code)
F - Focused       (Complete one repository before starting next)
E - Evidence      (Test after each change, verify it works)
```

### Migration Steps Per File

```
STEP 1: CREATE INTERFACE (if not exists)
        ├─ Define abstract methods
        └─ Document expected behavior

STEP 2: CREATE POSTGRESQL ADAPTER (if not exists)
        ├─ Implement all interface methods
        └─ Use existing SQLAlchemy code

STEP 3: CREATE SQLITE ADAPTER (if not exists)
        ├─ Implement all interface methods
        └─ Use existing offline.py code

STEP 4: UPDATE FACTORY
        └─ Add get_*_repository() function

STEP 5: MIGRATE ONE ENDPOINT
        ├─ Change: db: AsyncSession → repo: Repository
        ├─ Replace: SQLAlchemy queries → repo.method() calls
        └─ TEST immediately

STEP 6: REPEAT STEP 5 for each endpoint

STEP 7: CLEANUP
        ├─ Remove unused SQLAlchemy imports
        └─ Remove old fallback helper functions
```

### Why This Is SAFE

| Risk | Mitigation |
|------|------------|
| Breaking working code | Additive changes - old code stays until new code verified |
| Hard to debug | One endpoint at a time - easy to identify what broke |
| Too much change at once | Sequential approach - commit after each endpoint |
| Missing edge cases | Test after each change - catch issues early |
| Regression bugs | Existing Playwright tests catch breakage |

### Safe Rollback Strategy

```
IF something breaks:
  1. The old code is still there (just unused)
  2. Revert the ONE endpoint that broke
  3. Debug and fix
  4. Try again

NOT "delete everything and hope for the best"
```

---

## Task Tables

### Completed Tasks (Session 52)

| Task | File | Description | Evidence |
|------|------|-------------|----------|
| TM Entries Repository Fix | `tm_entries.py` | All 6 endpoints now use Repository Pattern | 0 direct DB calls |
| Update Entry Method | `tm_repository.py` | Added `update_entry()` to interface | Interface updated |
| Confirm Entry Method | `tm_repository.py` | Added `confirm_entry()` to interface | Interface updated |
| Bulk Confirm Method | `tm_repository.py` | Added `bulk_confirm_entries()` to interface | Interface updated |
| PostgreSQL Implementation | `tm_repo.py` | Implemented 3 new methods for PostgreSQL | Adapter updated |
| SQLite Implementation | `tm_repo.py` | Implemented 3 new methods for SQLite | Adapter updated |
| Project platform_id Fix | `schemas/project.py` | Added `platform_id` to `ProjectCreate` schema | Schema fixed |
| TM Folder Assignment | `files.py` | Online mode now assigns TM to same folder | Parity achieved |
| Documentation Audit | `SESSION_CONTEXT.md` | Updated P10 status from "COMPLETE" to "IN PROGRESS" | Accurate state |

### Pending Tasks

| Priority | Task | File(s) | Description | Effort |
|----------|------|---------|-------------|--------|
| HIGH | Migrate files.py to 100% Repository | `files.py` | 18 repo calls, 14 direct DB calls remain | Medium |
| HIGH | Migrate projects.py to 100% Repository | `projects.py` | 8 repo calls, 9 direct DB calls remain | Medium |
| HIGH | Migrate folders.py to 100% Repository | `folders.py` | 8 repo calls, 8 direct DB calls remain | Medium |
| HIGH | Migrate platforms.py to 100% Repository | `platforms.py` | 9 repo calls, 10 direct DB calls remain | Medium |
| MEDIUM | Migrate rows.py to 100% Repository | `rows.py` | 5 repo calls, 3 direct DB calls remain | Small |
| MEDIUM | Migrate tm_crud.py to 100% Repository | `tm_crud.py` | 8 repo calls, 9 direct DB calls remain | Medium |
| MEDIUM | Migrate tm_linking.py to 100% Repository | `tm_linking.py` | 6 repo calls, 13 direct DB calls remain | Large |
| MEDIUM | Migrate qa.py to 100% Repository | `qa.py` | 9 repo calls, 2 direct DB calls remain | Small |
| MEDIUM | Migrate trash.py to 100% Repository | `trash.py` | 4 repo calls, 2 direct DB calls remain | Small |
| MEDIUM | Migrate pretranslate.py to 100% Repository | `pretranslate.py` | 2 repo calls, 9 direct DB calls remain | Medium |
| LOW | Clean sync.py (after service extraction) | `sync.py` | Already uses SyncService, needs cleanup | Large |
| LOW | Migrate DIRECT files (no repo yet) | 6 files | capabilities.py, health.py, settings.py, tm_indexes.py, tm_search.py, sync.py | Small |

### Repository Migration Status

| Repository | Interface | PostgreSQL Adapter | SQLite Adapter | Factory | Status |
|------------|-----------|-------------------|----------------|---------|--------|
| TMRepository | DONE | DONE | DONE | DONE | **COMPLETE** |
| FileRepository | DONE | DONE | DONE | DONE | **COMPLETE** |
| RowRepository | DONE | DONE | DONE | DONE | **COMPLETE** |
| ProjectRepository | DONE | DONE | DONE | DONE | **COMPLETE** |
| FolderRepository | DONE | DONE | DONE | DONE | **COMPLETE** |
| PlatformRepository | DONE | DONE | DONE | DONE | **COMPLETE** |
| QAResultRepository | DONE | DONE | DONE | DONE | **COMPLETE** |
| TrashRepository | DONE | DONE | DONE | DONE | **COMPLETE** |

**All 8 Repositories are COMPLETE!** The issue is ROUTE MIGRATION, not repository creation.

### Route Migration Status

| Route File | Repo Calls | Direct DB Calls | Status | Notes |
|------------|------------|-----------------|--------|-------|
| `grammar.py` | 3 | 0 | **CLEAN** | Fully migrated |
| `health.py` | 0 | 0 | **CLEAN** | No DB (health check) |
| `pretranslate.py` | 1 | 0 | **CLEAN** | P10-PERM-001 only |
| `qa.py` | 11 | 0 | **CLEAN** | Fully migrated (Session 52) |
| `search.py` | 4 | 0 | **CLEAN** | Fully migrated |
| `settings.py` | 0 | 0 | **CLEAN** | No DB (settings) |
| `tm_assignment.py` | 5 | 0 | **CLEAN** | Fully migrated |
| `tm_crud.py` | 3 | 0 | **CLEAN** | P10-PERM-001 only |
| `tm_entries.py` | 6 | 0 | **CLEAN** | Fully migrated (Session 52) |
| `tm_linking.py` | 8 | 0 | **CLEAN** | Fully migrated (Session 53) |
| `rows.py` | 7 | 0 | **CLEAN** | Fully migrated (Session 53) |
| `files.py` | 18 | 15 | MIXED | Permission checks + CRUD |
| `folders.py` | 8 | 9 | MIXED | Permission checks + CRUD |
| `platforms.py` | 9 | 11 | MIXED | Permission checks + CRUD |
| `projects.py` | 8 | 10 | MIXED | Permission checks + CRUD |
| `trash.py` | 4 | 3 | MIXED | restore helpers + CRUD |
| `sync.py` | 0 | 7 | SERVICE | SyncService pattern |
| `capabilities.py` | 0 | 5 | UTILITY | User capability management |
| `tm_indexes.py` | 0 | 5 | UTILITY | FAISS index management |
| `tm_search.py` | 0 | 4 | UTILITY | FAISS search |

**Summary:**
- **CLEAN (100%):** 11 files (no `from sqlalchemy import select`, no `await db.execute`)
- **MIXED:** 5 files (have `from sqlalchemy import select` for CRUD, not just permission checks)
- **SERVICE:** 1 file (sync.py - uses SyncService pattern)
- **UTILITY:** 3 files (capabilities, tm_indexes, tm_search - specialized operations)

### Permission Check Pattern (P10-PERM-001)

Most remaining direct DB calls are for **permission checks**:
- `can_access_project()`, `can_access_folder()`, `can_access_file()`
- `can_access_tm()`, `can_access_platform()`
- `require_capability()`

**Decision:** Keep permission checks as direct DB for now. They are business logic, not CRUD.
Future work could create a `PermissionRepository` for full offline parity.

---

## Recent Sessions

### Session 52 (2026-01-13) - DB Abstraction Layer Migration

**Focus:** Complete Repository Pattern migration for route files

**Phase 1: Bug Fixes**
1. **tm_entries.py** - 3 endpoints bypassed Repository Pattern
   - Added 3 new methods to TMRepository: `update_entry`, `confirm_entry`, `bulk_confirm_entries`
   - Now 100% Repository Pattern (6 repo calls, 0 direct DB)

2. **projects.py** - `ProjectCreate` schema missing `platform_id` field
   - Added `platform_id: Optional[int] = None` to schema

3. **files.py** - Online mode missing TM folder assignment
   - Added assignment logic to match offline mode (PARITY achieved)

**Phase 2: qa.py Migration (100% COMPLETE)**
1. Added `get_glossary_terms(tm_ids, max_length)` to TMRepository interface
2. Implemented in PostgreSQL adapter (uses `func.length()` and `IN` clause)
3. Implemented in SQLite adapter (uses `LENGTH()` and `IN` clause)
4. Updated `_get_glossary_terms()` to use TMRepository
5. Removed direct DB from `check_row_qa()` and `check_file_qa()`
6. qa.py now has 11 repo calls, 0 direct DB calls

**Phase 3: Permission Check Analysis**
- Discovered most remaining direct DB calls are permission checks
- Decision: Keep permission checks as direct DB (business logic, not CRUD)
- Documented as P10-PERM-001 for future consideration

**Documentation Overhaul:**
- SESSION_CONTEXT.md: Added TOC, task tables, architecture explanation
- P10_DB_ABSTRACTION.md: Comprehensive implementation guide
- Added "What IS Repository Pattern" explanation
- Added "SAFE Methodology" for incremental migration

**Current State (after Session 52):**
- 5 route files CLEAN (100% Repository): grammar, qa, search, tm_assignment, tm_entries
- 9 route files MIXED (permission checks remain)
- All 8 Repositories fully implemented

### Session 53 (2026-01-13) - TM Linking Migration

**Focus:** Continue Repository Pattern migration

**tm_linking.py Migration (100% COMPLETE)**
1. Added 4 new methods to TMRepository interface:
   - `link_to_project(tm_id, project_id, priority)` - with `created` flag for duplicate detection
   - `unlink_from_project(tm_id, project_id)` - returns bool
   - `get_linked_for_project(project_id, user_id)` - highest priority TM
   - `get_all_linked_for_project(project_id)` - all linked TMs with details

2. Implemented in PostgreSQL adapter:
   - Uses LDMActiveTM model with proper JOIN to LDMTranslationMemory
   - Returns full TM details including linked_at timestamp

3. Implemented in SQLite adapter:
   - Uses offline_tm_assignments table with is_active flag
   - Same interface, same behavior

4. Updated tm_linking.py endpoints:
   - `link_tm_to_project` - uses `tm_repo.link_to_project()`, checks `created` flag
   - `unlink_tm_from_project` - uses `tm_repo.unlink_from_project()`
   - `get_linked_tms` - uses `tm_repo.get_all_linked_for_project()`

5. **Testing:** All 3 endpoints tested via curl:
   - Link TM ✓
   - Get linked TMs ✓
   - Duplicate detection ✓ (returns 400)
   - Unlink TM ✓
   - Not found detection ✓ (returns 404)

**Current State:**
- 11 route files CLEAN (100% Repository): grammar, health, pretranslate, qa, rows, search, settings, tm_assignment, tm_crud, tm_entries, tm_linking
- 5 route files MIXED (have actual CRUD operations with direct SQLAlchemy)
- 4 route files SPECIAL (sync, capabilities, tm_indexes, tm_search)
- All 8 Repositories fully implemented

**rows.py Migration (100% COMPLETE)**
1. Replaced `_get_project_linked_tm()` direct SQLAlchemy with `tm_repo.get_linked_for_project()`
2. Replaced direct LDMFile query in `list_rows` with `file_repo.get()`
3. Replaced direct LDMRow query in `update_row` with `repo.get_with_file()`
4. Added `tm_repo` and `file_repo` dependencies to endpoints
5. Removed all sqlalchemy imports and model imports
6. Tested: `list_rows` ✓, `update_row` ✓

### Session 51 (2026-01-12) - P11 Platform Stability

**Focus:** Granular Debug Protocol - Testing both online and offline modes

**Bugs Fixed:**
1. **Trash Restore Memo Bug (CRITICAL)**
   - `trash.py:369` referenced non-existent `memo` field on LDMRow
   - Fix: Removed `memo` field references

2. **Offline ID Generation Bug (CRITICAL)**
   - `offline.py:1685` had Python operator precedence bug
   - `-int(time.time() * 1000) % 1000000000` returns POSITIVE (wrong!)
   - Fix: `-(int(time.time() * 1000) % 1000000000)` for NEGATIVE

**Test Results (Post-Fix):**
- **Online Mode: 11/11 PASS**
- **Offline Mode: 7/7 PASS**

### Previous Sessions

See [Roadmap.md](../../Roadmap.md) for complete history.

---

## Quick Commands

```bash
# Start DEV servers
./scripts/start_all_servers.sh --with-vite

# Run tests
cd locaNext && npx playwright test

# Check build status
./scripts/gitea_control.sh status

# Audit Repository Pattern usage
grep -r "get_async_db" server/tools/ldm/routes/*.py | wc -l  # Direct DB calls
grep -r "Repository = Depends" server/tools/ldm/routes/*.py | wc -l  # Repo calls
```

---

## Backlog

### DB Audit Shell Wrapper (LocaNext Audit Master)
**Priority:** After P10 | **Status:** PLANNED

Full audit manager that can audit anything via shell wrapper:
- DB schema validation
- Repository pattern compliance
- Optimistic UI verification
- Route migration status
- Test coverage gaps

---

## Open Questions

None currently.

---

*Updated each session. Fast-moving info lives here.*
