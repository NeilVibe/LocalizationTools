# P10: DB Abstraction Layer

**Priority:** P10 | **Status:** IN PROGRESS | **Started:** 2026-01-11

> Full plan: `~/.claude/plans/smooth-coalescing-swan.md`

---

## Overview

Transform entire backend from inconsistent database patterns to unified **Repository Pattern**.

| Before | After |
|--------|-------|
| 1 route uses Repository (TM) | ALL routes use Repository |
| 6 routes use fallback pattern | No fallback |
| 10+ routes use direct PostgreSQL | No direct DB in routes |
| Inconsistent offline | **True offline parity** |

---

## Progress Tracker

### Phase 1: Documentation & Foundation ✅ COMPLETE

| Task | Status |
|------|--------|
| Create docs/wip/ structure | **DONE** |
| Update Roadmap.md | **DONE** |
| Update DB_ABSTRACTION_LAYER.md | **DONE** |
| Update OFFLINE_ONLINE_MODE.md | TODO (minor) |

### Phase 2: Core Repositories

| Repository | Interface | PostgreSQL | SQLite | Status |
|------------|-----------|------------|--------|--------|
| FileRepository | **DONE** | **DONE** | **DONE** | **DONE** |
| RowRepository | **DONE** | **DONE** | **DONE** | **DONE** |
| ProjectRepository | ☐ | ☐ | ☐ | TODO |

### Phase 3: Hierarchy Repositories

| Repository | Interface | PostgreSQL | SQLite | Status |
|------------|-----------|------------|--------|--------|
| FolderRepository | ☐ | ☐ | ☐ | TODO |
| PlatformRepository | ☐ | ☐ | ☐ | TODO |

### Phase 4: Support Repositories

| Repository | Interface | PostgreSQL | SQLite | Status |
|------------|-----------|------------|--------|--------|
| QAResultRepository | ☐ | ☐ | ☐ | TODO |
| TrashRepository | ☐ | ☐ | ☐ | TODO |

### Phase 5: Route Migration

| Route | Repository | Migrated | Tested |
|-------|------------|----------|--------|
| tm_assignment.py | TMRepository | **DONE** | **DONE** |
| files.py | FileRepository | **14/15** | ☐ |
| rows.py | RowRepository | **2/3** | ☐ |
| projects.py | ProjectRepository | ☐ | ☐ |
| folders.py | FolderRepository | ☐ | ☐ |
| platforms.py | PlatformRepository | ☐ | ☐ |
| qa.py | QAResultRepository | ☐ | ☐ |
| grammar.py | RowRepository | ☐ | ☐ |
| trash.py | TrashRepository | ☐ | ☐ |
| sync.py | All | ☐ | ☐ |

### Phase 5B: sync.py Refactoring

| Task | Status |
|------|--------|
| Create SyncService | ☐ |
| Create SubscriptionService | ☐ |
| Create OfflineTrashService | ☐ |
| Migrate sync.py to use services | ☐ |
| Apply Repository Pattern | ☐ |

### Phase 6: Testing

| Test Type | Created | Passing |
|-----------|---------|---------|
| Repository unit tests | ☐ | ☐ |
| Dual-mode tests | ☐ | ☐ |
| Integration tests | **DONE** | **33/36** |
| Regression (Playwright) | **DONE** | **100%** |

**Test Results (2026-01-11):** 144 passed, 0 failed, 17 skipped (100%)

---

## File Structure (Target)

```
server/repositories/
├── __init__.py
├── factory.py
├── interfaces/
│   ├── file_repository.py
│   ├── row_repository.py
│   ├── project_repository.py
│   ├── folder_repository.py
│   ├── platform_repository.py
│   ├── tm_repository.py        ← DONE
│   ├── qa_repository.py
│   └── trash_repository.py
├── postgresql/
│   └── (same structure)        ← 1 DONE
└── sqlite/
    └── (same structure)        ← 1 DONE
```

---

## Success Criteria

| Criterion | Current | Target |
|-----------|---------|--------|
| Routes using Repository | 1 | ALL |
| Fallback pattern occurrences | 6 | 0 |
| Tests passing | ✓ | ✓ |
| Offline parity | Partial | Full |

---

## Key Decisions

| Decision | Choice |
|----------|--------|
| Approach | Stability - Sequential (one at a time) |
| WIP Docs | Full Index |
| sync.py | Refactor to Service Layer first |

---

## Links

- Full Plan: `~/.claude/plans/smooth-coalescing-swan.md`
- Architecture: [docs/architecture/DB_ABSTRACTION_LAYER.md](../architecture/DB_ABSTRACTION_LAYER.md)
- Offline Mode: [docs/architecture/OFFLINE_ONLINE_MODE.md](../architecture/OFFLINE_ONLINE_MODE.md)

---

*Last updated: 2026-01-11*
