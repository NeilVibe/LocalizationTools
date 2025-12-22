# P37: LDM Codebase Refactoring Plan

**Created:** 2025-12-22 | **Status:** IN PROGRESS | **Priority:** HIGH

---

## CURRENT STATUS (2025-12-22)

### COMPLETED
- [x] Phase 1: Schemas extracted to `schemas/` (9 files)
- [x] Folder structure created: `routes/`, `services/`, `indexing/`, `helpers/`
- [x] 648 unit tests still pass

### IN PROGRESS
- [ ] Phase 2: Migrate route code from api.py to routes/*.py
- Routes with actual code: `health.py`, `projects.py`, `folders.py`
- Routes with stubs: `files.py`, `rows.py`, `tm_*.py`, `pretranslate.py`, `sync.py`, `settings.py`

### PENDING
- [ ] Phase 3: Extract services from tm_manager.py
- [ ] Phase 4: Split tm_indexer.py into indexing/
- [ ] Phase 5: Wire up router.py as main entry point
- [ ] Phase 6: Delete old monolith files

---

## PROBLEM STATEMENT

| File | Lines | Industry Standard | Verdict |
|------|-------|-------------------|---------|
| `ldm/api.py` | 3144 | 300-500 | **6x TOO BIG** |
| `ldm/tm_indexer.py` | 2105 | 300-500 | **4x TOO BIG** |
| `ldm/tm_manager.py` | 1133 | 300-500 | **2x TOO BIG** |
| `api/stats.py` | 1371 | 300-500 | 3x TOO BIG (defer) |

**Total lines to refactor:** 6,382 → target ~20 files

---

## TARGET STRUCTURE

### Current (Bad)

```
server/tools/ldm/
├── api.py                 # 3144 lines - MONOLITH
├── tm_indexer.py          # 2105 lines - MONOLITH
├── tm_manager.py          # 1133 lines - MONOLITH
├── pretranslate.py        # 209 lines - OK
├── websocket.py           # 182 lines - OK
├── backup_service.py      # 618 lines - borderline
├── tm.py                  # small - OK
├── __init__.py
└── file_handlers/
    ├── __init__.py
    ├── excel_handler.py
    ├── txt_handler.py
    └── xml_handler.py
```

### Target (Good)

```
server/tools/ldm/
├── __init__.py
├── router.py              # ~50 lines - Main router, imports all sub-routers
│
├── schemas/               # Pydantic models (extracted from api.py)
│   ├── __init__.py
│   ├── project.py         # ~40 lines - ProjectCreate, ProjectResponse
│   ├── folder.py          # ~30 lines - FolderCreate, FolderResponse
│   ├── file.py            # ~50 lines - FileResponse, PaginatedRows
│   ├── row.py             # ~40 lines - RowResponse, RowUpdate
│   ├── tm.py              # ~80 lines - TMResponse, TMUploadResponse, TMSearchResult
│   ├── pretranslate.py    # ~40 lines - PretranslateRequest/Response
│   ├── sync.py            # ~40 lines - SyncRequest/Response models
│   └── settings.py        # ~30 lines - EmbeddingEngineInfo, etc.
│
├── routes/                # API endpoints (extracted from api.py)
│   ├── __init__.py
│   ├── health.py          # ~30 lines - /health endpoint
│   ├── projects.py        # ~200 lines - Project CRUD
│   ├── folders.py         # ~150 lines - Folder CRUD
│   ├── files.py           # ~400 lines - File upload, list, download
│   ├── rows.py            # ~150 lines - Row get, update
│   ├── tm_crud.py         # ~200 lines - TM list, get, delete, upload
│   ├── tm_entries.py      # ~300 lines - TM entry CRUD, confirm, bulk
│   ├── tm_search.py       # ~150 lines - Exact search, semantic search
│   ├── tm_indexes.py      # ~200 lines - Build indexes, sync, status
│   ├── tm_linking.py      # ~150 lines - Link/unlink TM to project
│   ├── pretranslate.py    # ~200 lines - Pretranslation endpoint
│   ├── sync.py            # ~250 lines - Sync to central
│   └── settings.py        # ~100 lines - Embedding engine settings
│
├── services/              # Business logic (extracted from tm_manager.py)
│   ├── __init__.py
│   ├── tm_service.py      # ~400 lines - TM CRUD operations
│   ├── entry_service.py   # ~350 lines - TM entry operations
│   ├── file_service.py    # ~300 lines - File processing logic
│   └── project_service.py # ~200 lines - Project/folder logic
│
├── indexing/              # FAISS/Vector operations (extracted from tm_indexer.py)
│   ├── __init__.py
│   ├── indexer.py         # ~500 lines - TMIndexer class
│   ├── searcher.py        # ~400 lines - TMSearcher class
│   ├── sync_manager.py    # ~500 lines - TMSyncManager class
│   ├── utils.py           # ~100 lines - normalize_*, helpers
│   └── faiss_manager.py   # ~300 lines - FAISS operations (if not exists)
│
├── helpers/               # Utility functions
│   ├── __init__.py
│   ├── file_builders.py   # ~200 lines - _build_txt_file, _build_xml_file, etc.
│   └── validators.py      # ~100 lines - Validation helpers
│
├── file_handlers/         # KEEP AS-IS (already factored)
│   ├── __init__.py
│   ├── excel_handler.py
│   ├── txt_handler.py
│   └── xml_handler.py
│
├── pretranslate.py        # KEEP AS-IS (209 lines - OK)
├── websocket.py           # KEEP AS-IS (182 lines - OK)
├── backup_service.py      # KEEP AS-IS (618 lines - borderline, defer)
└── tm.py                  # KEEP AS-IS (small - OK)
```

---

## FOLDER SUMMARY

| Level | Count | Purpose |
|-------|-------|---------|
| **Root** | 1 | `ldm/` |
| **Subfolders** | 5 | `schemas/`, `routes/`, `services/`, `indexing/`, `helpers/` |
| **Sub-subfolders** | 0 | None needed |
| **New files** | ~25 | Split from 3 monoliths |

---

## FILE COUNT BY FOLDER

| Folder | Files | Total Lines (est.) |
|--------|-------|-------------------|
| `schemas/` | 8 | ~350 |
| `routes/` | 14 | ~2,480 |
| `services/` | 4 | ~1,250 |
| `indexing/` | 5 | ~1,800 |
| `helpers/` | 2 | ~300 |
| **Total new** | **33** | **~6,180** |

---

## EXECUTION PLAN

### Phase 1: Schemas (30 min)
Extract Pydantic models from `api.py` to `schemas/`

**Files to create:**
1. `schemas/__init__.py` - Export all models
2. `schemas/project.py` - ProjectCreate, ProjectResponse
3. `schemas/folder.py` - FolderCreate, FolderResponse
4. `schemas/file.py` - FileResponse, PaginatedRows
5. `schemas/row.py` - RowResponse, RowUpdate
6. `schemas/tm.py` - TMResponse, TMUploadResponse, TMSearchResult, etc.
7. `schemas/pretranslate.py` - PretranslateRequest/Response
8. `schemas/sync.py` - SyncFileToCentralRequest/Response
9. `schemas/settings.py` - EmbeddingEngineInfo, etc.

### Phase 2: Routes (1.5 hours)
Extract endpoints from `api.py` to `routes/`

**Files to create:**
1. `routes/__init__.py`
2. `routes/health.py` - lines 190-212
3. `routes/projects.py` - lines 214-303
4. `routes/folders.py` - lines 305-390
5. `routes/files.py` - lines 392-658, 2543-2784
6. `routes/rows.py` - lines 660-861
7. `routes/tm_crud.py` - lines 1195-1365, 1871-1936
8. `routes/tm_entries.py` - lines 1366-1819
9. `routes/tm_search.py` - lines 1723-1818
10. `routes/tm_indexes.py` - lines 1937-2306
11. `routes/tm_linking.py` - lines 940-1092
12. `routes/pretranslate.py` - lines 2313-2440
13. `routes/sync.py` - lines 2786-3048
14. `routes/settings.py` - lines 3049-3144

### Phase 3: Services (1 hour)
Extract business logic from `tm_manager.py`

**Files to create:**
1. `services/__init__.py`
2. `services/tm_service.py` - TM CRUD methods
3. `services/entry_service.py` - Entry CRUD methods
4. `services/file_service.py` - File processing
5. `services/project_service.py` - Project/folder logic

### Phase 4: Indexing (1 hour)
Split `tm_indexer.py` into logical units

**Files to create:**
1. `indexing/__init__.py`
2. `indexing/utils.py` - normalize_* functions
3. `indexing/indexer.py` - TMIndexer class
4. `indexing/searcher.py` - TMSearcher class
5. `indexing/sync_manager.py` - TMSyncManager class

### Phase 5: Helpers + Router (30 min)
1. `helpers/__init__.py`
2. `helpers/file_builders.py` - _build_txt/xml/excel_file
3. `helpers/validators.py`
4. `router.py` - Main router combining all sub-routers

### Phase 6: Cleanup + Tests (30 min)
1. Delete old monolith files
2. Update imports across codebase
3. Run full test suite
4. Verify coverage

---

## IMPORT STRATEGY

### Before (api.py)
```python
from server.tools.ldm.api import router
```

### After (router.py)
```python
# router.py
from fastapi import APIRouter
from .routes import projects, folders, files, rows, tm_crud, tm_entries, ...

router = APIRouter(prefix="/ldm", tags=["ldm"])

router.include_router(projects.router)
router.include_router(folders.router)
router.include_router(files.router)
# ... etc
```

### Usage unchanged
```python
from server.tools.ldm.router import router  # Same interface!
```

---

## RISK MITIGATION

| Risk | Mitigation |
|------|------------|
| Breaking imports | Keep `api.py` as thin re-export during transition |
| Missing endpoints | Grep for all `@router` decorators before/after |
| Test failures | Run tests after each phase |
| Circular imports | Use TYPE_CHECKING imports |

---

## SUCCESS CRITERIA

- [ ] No file > 500 lines
- [ ] All tests pass
- [ ] All endpoints still work
- [ ] Coverage maintained or improved
- [ ] Clean import structure

---

## ESTIMATED TIME

| Phase | Time |
|-------|------|
| Phase 1: Schemas | 30 min |
| Phase 2: Routes | 1.5 hours |
| Phase 3: Services | 1 hour |
| Phase 4: Indexing | 1 hour |
| Phase 5: Helpers + Router | 30 min |
| Phase 6: Cleanup + Tests | 30 min |
| **Total** | **5 hours** |

---

## POST-REFACTORING

After refactoring completes:
1. Update test file `tests/integration/test_ldm_api.py` if needed
2. Run full coverage report
3. Continue with P36 coverage improvement plan

---

*P37 LDM Refactoring Plan | Created 2025-12-22*
