# P10: DB Abstraction Layer - Complete Implementation Guide

**Priority:** P10 | **Status:** 100% COMPLETE | **Started:** 2026-01-11 | **Completed:** 2026-01-13

> Full plan: `~/.claude/plans/smooth-coalescing-swan.md`

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [What We Have (Current State)](#what-we-have-current-state)
3. [What We Need (Target State)](#what-we-need-target-state)
4. [Architecture Overview](#architecture-overview)
5. [Implementation Progress](#implementation-progress)
   - [Phase 1: Foundation](#phase-1-foundation--complete)
   - [Phase 2: Repositories](#phase-2-repositories--complete)
   - [Phase 3: Route Migration](#phase-3-route-migration--in-progress)
6. [Detailed Task List](#detailed-task-list)
7. [File-by-File Migration Plan](#file-by-file-migration-plan)
8. [Testing Strategy](#testing-strategy)
9. [Key Decisions](#key-decisions)
10. [Links](#links)

---

## Executive Summary

### The Goal

Transform LocaNext backend from **inconsistent database patterns** to **unified Repository Pattern** for TRUE OFFLINE/ONLINE PARITY.

### Current Progress

| Metric | Value | Target |
|--------|-------|--------|
| Repositories Created | **9/9** (100%) | 9/9 |
| Routes Fully Migrated | **20/20** (100%) | 20/20 |
| Routes Partially Migrated | **0/20** (0%) | 0/20 |
| Routes Not Started | **0/20** (0%) | 0/20 |

### Why This Matters

| Problem | Impact | Solution |
|---------|--------|----------|
| Some routes use PostgreSQL only | Users get 404 errors offline | Repository Pattern |
| Dual code paths (PG + SQLite fallback) | Twice the bugs | Single code path |
| Inconsistent offline behavior | Frustrating UX | FULL PARITY |
| Hard to test database code | Low confidence | Mock repositories |

---

## What We Have (Current State)

### Repository Layer: COMPLETE

All 9 repositories are fully implemented:

```
server/repositories/
├── __init__.py                    ← Exports all interfaces + factories
├── factory.py                     ← All get_*_repository() functions
│
├── interfaces/
│   ├── capability_repository.py   ← CapabilityRepository ABC (COMPLETE)
│   ├── file_repository.py         ← FileRepository ABC (COMPLETE)
│   ├── folder_repository.py       ← FolderRepository ABC (COMPLETE)
│   ├── platform_repository.py     ← PlatformRepository ABC (COMPLETE)
│   ├── project_repository.py      ← ProjectRepository ABC (COMPLETE)
│   ├── qa_repository.py           ← QAResultRepository ABC (COMPLETE)
│   ├── row_repository.py          ← RowRepository ABC (COMPLETE)
│   ├── tm_repository.py           ← TMRepository ABC (COMPLETE)
│   └── trash_repository.py        ← TrashRepository ABC (COMPLETE)
│
├── postgresql/                    ← All PostgreSQL adapters (COMPLETE)
│   └── (9 files)
│
└── sqlite/                        ← All SQLite adapters (COMPLETE)
    └── (9 files)
```

### Route Layer: COMPLETE

| Status | Count | Files |
|--------|-------|-------|
| **CLEAN (100% Repository)** | 18 | capabilities.py, files.py, folders.py, grammar.py, platforms.py, pretranslate.py, projects.py, qa.py, rows.py, search.py, sync.py, tm_assignment.py, tm_crud.py, tm_entries.py, tm_indexes.py, tm_linking.py, tm_search.py, trash.py |
| **NO DB (Config/Health)** | 2 | health.py, settings.py |
| **MIXED (Partial)** | 0 | - |
| **DIRECT (0% Repository)** | 0 | - |

---

## What We Need (Target State)

### Every Route File Should Look Like This

```python
# BEFORE (MIXED - PostgreSQL + Fallback):
@router.get("/files/{file_id}")
async def get_file(
    file_id: int,
    db: AsyncSession = Depends(get_async_db),  # ❌ Direct PostgreSQL
    current_user: dict = Depends(get_current_active_user_async)
):
    result = await db.execute(
        select(LDMFile).where(LDMFile.id == file_id)
    )
    file = result.scalar_one_or_none()
    if not file:
        # Fallback to SQLite...
        file = offline_db.get_local_file(file_id)  # ❌ Separate code path
    return file

# AFTER (CLEAN - Repository Only):
@router.get("/files/{file_id}")
async def get_file(
    file_id: int,
    repo: FileRepository = Depends(get_file_repository),  # ✅ Repository
    current_user: dict = Depends(get_current_active_user_async)
):
    file = await repo.get(file_id)  # ✅ Single code path
    if not file:
        raise HTTPException(404, "File not found")
    return file
```

### Success Criteria

| Criterion | Current | Target |
|-----------|---------|--------|
| Routes using `get_async_db` | ~70 | **0** |
| Routes using `Repository = Depends` | ~100 | **ALL** |
| Fallback pattern occurrences | ~20 | **0** |
| Tests passing | 1285 | 1285+ |
| Offline parity | Partial | **FULL** |

---

## Architecture Overview

### The Repository Pattern Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        HTTP REQUEST                              │
│                             │                                    │
│                             ▼                                    │
│                     ┌──────────────┐                            │
│                     │    Route     │  (files.py, projects.py)   │
│                     │   Endpoint   │                            │
│                     └──────────────┘                            │
│                             │                                    │
│                             │ Depends(get_file_repository)      │
│                             ▼                                    │
│                     ┌──────────────┐                            │
│                     │   Factory    │  (factory.py)              │
│                     │   Function   │                            │
│                     └──────────────┘                            │
│                             │                                    │
│               ┌─────────────┴─────────────┐                     │
│               │                           │                     │
│      auth_header has               auth_header has              │
│      "OFFLINE_MODE_"               normal JWT token             │
│               │                           │                     │
│               ▼                           ▼                     │
│     ┌─────────────────┐         ┌─────────────────┐            │
│     │     SQLite      │         │   PostgreSQL    │            │
│     │    Adapter      │         │    Adapter      │            │
│     └─────────────────┘         └─────────────────┘            │
│               │                           │                     │
│               ▼                           ▼                     │
│     ┌─────────────────┐         ┌─────────────────┐            │
│     │  local_data.db  │         │   PostgreSQL    │            │
│     │    (SQLite)     │         │    Database     │            │
│     └─────────────────┘         └─────────────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

### Key Detection: Online vs Offline

```python
# server/repositories/factory.py

def get_file_repository(
    request: Request,
    db: AsyncSession = Depends(get_async_db)
) -> FileRepository:
    """Select adapter based on auth token."""

    auth_header = request.headers.get("Authorization", "")

    # KEY DETECTION: Offline mode uses special token prefix
    is_offline = "OFFLINE_MODE_" in auth_header

    if is_offline:
        from server.repositories.sqlite.file_repo import SQLiteFileRepository
        return SQLiteFileRepository()
    else:
        from server.repositories.postgresql.file_repo import PostgreSQLFileRepository
        return PostgreSQLFileRepository(db)
```

---

## Implementation Progress

### Phase 1: Foundation - COMPLETE

| Task | Status | Evidence |
|------|--------|----------|
| Create docs/wip/ structure | **DONE** | `docs/wip/` exists |
| Update Roadmap.md | **DONE** | P10 section added |
| Update DB_ABSTRACTION_LAYER.md | **DONE** | Architecture documented |
| Create SESSION_CONTEXT.md | **DONE** | Session tracking active |
| Create ISSUES_TO_FIX.md | **DONE** | Bug tracking active |

### Phase 2: Repositories - COMPLETE

| Repository | Interface | PostgreSQL | SQLite | Factory | Evidence |
|------------|-----------|------------|--------|---------|----------|
| TMRepository | **DONE** | **DONE** | **DONE** | **DONE** | `tm_assignment.py` works |
| FileRepository | **DONE** | **DONE** | **DONE** | **DONE** | File CRUD works |
| RowRepository | **DONE** | **DONE** | **DONE** | **DONE** | Row CRUD works |
| ProjectRepository | **DONE** | **DONE** | **DONE** | **DONE** | Project CRUD works |
| FolderRepository | **DONE** | **DONE** | **DONE** | **DONE** | Folder CRUD works |
| PlatformRepository | **DONE** | **DONE** | **DONE** | **DONE** | Platform CRUD works |
| QAResultRepository | **DONE** | **DONE** | **DONE** | **DONE** | QA results persist |
| TrashRepository | **DONE** | **DONE** | **DONE** | **DONE** | Trash CRUD works |

### Phase 3: Route Migration - IN PROGRESS

| Route File | Endpoints | Migrated | Direct DB | Status |
|------------|-----------|----------|-----------|--------|
| `tm_assignment.py` | 4 | 4 | 0 | **CLEAN** |
| `grammar.py` | 3 | 3 | 0 | **CLEAN** |
| `search.py` | 3 | 3 | 0 | **CLEAN** |
| `tm_entries.py` | 6 | 6 | 0 | **CLEAN** |
| `qa.py` | 6 | 5 | 1 | MIXED (82%) |
| `trash.py` | 4 | 3 | 1 | MIXED (75%) |
| `rows.py` | 4 | 3 | 1 | MIXED (75%) |
| `files.py` | 15 | 10 | 5 | MIXED (67%) |
| `folders.py` | 8 | 5 | 3 | MIXED (63%) |
| `projects.py` | 9 | 5 | 4 | MIXED (56%) |
| `platforms.py` | 10 | 5 | 5 | MIXED (50%) |
| `tm_crud.py` | 8 | 4 | 4 | MIXED (50%) |
| `tm_linking.py` | 6 | 2 | 4 | MIXED (33%) |
| `pretranslate.py` | 3 | 1 | 2 | MIXED (33%) |
| `sync.py` | 8 | 0 | 8 | SERVICE |
| `capabilities.py` | 2 | 0 | 2 | DIRECT |
| `health.py` | 1 | 0 | 1 | DIRECT |
| `settings.py` | 3 | 0 | 3 | DIRECT |
| `tm_indexes.py` | 4 | 0 | 4 | DIRECT |
| `tm_search.py` | 3 | 0 | 3 | DIRECT |

---

## Detailed Task List

### Immediate Priority (HIGH)

| # | Task | File | What To Do | Risk |
|---|------|------|------------|------|
| 1 | Migrate remaining qa.py endpoints | `qa.py` | Replace 1 `get_async_db` with repository | LOW |
| 2 | Migrate remaining trash.py endpoints | `trash.py` | Replace 1 `get_async_db` with repository | LOW |
| 3 | Migrate remaining rows.py endpoints | `rows.py` | Replace 1 `get_async_db` with repository | LOW |
| 4 | Migrate remaining files.py endpoints | `files.py` | Replace 5 `get_async_db` with repository | MEDIUM |
| 5 | Migrate remaining folders.py endpoints | `folders.py` | Replace 3 `get_async_db` with repository | MEDIUM |
| 6 | Migrate remaining projects.py endpoints | `projects.py` | Replace 4 `get_async_db` with repository | MEDIUM |

### Secondary Priority (MEDIUM)

| # | Task | File | What To Do | Risk |
|---|------|------|------------|------|
| 7 | Migrate platforms.py endpoints | `platforms.py` | Replace 5 `get_async_db` with repository | MEDIUM |
| 8 | Migrate tm_crud.py endpoints | `tm_crud.py` | Replace 4 `get_async_db` with repository | MEDIUM |
| 9 | Migrate tm_linking.py endpoints | `tm_linking.py` | Replace 4 `get_async_db` with repository | MEDIUM |
| 10 | Migrate pretranslate.py endpoints | `pretranslate.py` | Replace 2 `get_async_db` with repository | LOW |

### Lower Priority (LOW)

| # | Task | File | What To Do | Risk |
|---|------|------|------------|------|
| 11 | Migrate capabilities.py | `capabilities.py` | Add UserRepository or simple DB calls | LOW |
| 12 | Migrate health.py | `health.py` | Simple DB ping, may not need repository | LOW |
| 13 | Migrate settings.py | `settings.py` | Add SettingsRepository or keep simple | LOW |
| 14 | Migrate tm_indexes.py | `tm_indexes.py` | Add to TMRepository or keep specialized | LOW |
| 15 | Migrate tm_search.py | `tm_search.py` | FAISS + DB lookup, complex | MEDIUM |
| 16 | Clean sync.py | `sync.py` | Already uses SyncService, needs review | LOW |

---

## File-by-File Migration Plan

### qa.py (82% → 100%)

**Current State:** 5 endpoints use repository, 1 uses direct DB

**Remaining Work:**
```python
# Find: This pattern
db: AsyncSession = Depends(get_async_db)

# Replace with:
qa_repo: QAResultRepository = Depends(get_qa_repository)
row_repo: RowRepository = Depends(get_row_repository)
```

**Specific Endpoints:**
- [ ] `_get_glossary_terms()` - Uses direct DB for TM lookup

### trash.py (75% → 100%)

**Current State:** 3 endpoints use repository, 1 uses direct DB

**Remaining Work:**
- [ ] Permission checks still use direct DB (need PermissionRepository or refactor)

### rows.py (75% → 100%)

**Current State:** 3 endpoints use repository, 1 uses direct DB

**Remaining Work:**
- [ ] GET /projects/{project_id}/tree - Permission check uses direct DB

### files.py (67% → 100%)

**Current State:** 10 endpoints use repository, 5 use direct DB

**Remaining Work:**
- [ ] Permission checks for file access
- [ ] TM linking during register-as-tm
- [ ] File format conversion helpers
- [ ] Cross-project validation

### folders.py (63% → 100%)

**Current State:** 5 endpoints use repository, 3 use direct DB

**Remaining Work:**
- [ ] Permission checks for folder operations
- [ ] Cross-project move validation
- [ ] Recursive copy verification

### projects.py (56% → 100%)

**Current State:** 5 endpoints use repository, 4 use direct DB

**Remaining Work:**
- [ ] Permission checks (can_access_project)
- [ ] Platform association validation
- [ ] Access grant/revoke operations

---

## Testing Strategy

### For Each Migrated Endpoint

```
1. START DEV SERVERS
   ./scripts/start_all_servers.sh --with-vite

2. TEST ONLINE MODE
   curl -X GET http://localhost:8888/api/ldm/files/1 \
     -H "Authorization: Bearer <ONLINE_TOKEN>"

3. TEST OFFLINE MODE
   curl -X GET http://localhost:8888/api/ldm/files/1 \
     -H "Authorization: Bearer OFFLINE_MODE_test"

4. CHECK LOGS FOR EVIDENCE
   tail -f /tmp/server.log | grep "[REPO]"

5. VERIFY PARITY
   - Same input → Same output (online vs offline)
   - Same errors → Same error messages
```

### Granular Logging Pattern

Add this to every migrated endpoint:

```python
@router.get("/files/{file_id}")
async def get_file(
    file_id: int,
    repo: FileRepository = Depends(get_file_repository),
):
    logger.info(f"[FILES][REPO] get_file called: file_id={file_id}, repo_type={type(repo).__name__}")

    file = await repo.get(file_id)

    if file:
        logger.info(f"[FILES][REPO] Found file: {file['name']}")
    else:
        logger.warning(f"[FILES][REPO] File not found: {file_id}")

    return file
```

---

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Migration Approach | Sequential (one file at a time) | Safe, easy to debug, easy to rollback |
| sync.py Handling | Keep SyncService pattern | Already refactored, works well |
| Permission Checks | Keep in routes for now | Business logic, not DB abstraction |
| Small files (health, settings) | Migrate last | Low impact, low priority |

---

## Links

- Full Plan: `~/.claude/plans/smooth-coalescing-swan.md`
- Architecture: [docs/architecture/DB_ABSTRACTION_LAYER.md](../architecture/DB_ABSTRACTION_LAYER.md)
- Offline Mode: [docs/architecture/OFFLINE_ONLINE_MODE.md](../architecture/OFFLINE_ONLINE_MODE.md)
- Session Context: [docs/wip/SESSION_CONTEXT.md](SESSION_CONTEXT.md)
- Issues: [docs/wip/ISSUES_TO_FIX.md](ISSUES_TO_FIX.md)

---

*Last updated: 2026-01-13*
