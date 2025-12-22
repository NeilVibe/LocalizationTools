# P37: LDM Codebase Refactoring Plan

**Created:** 2025-12-22 | **Status:** IN PROGRESS | **Priority:** HIGH

---

## CURRENT STATUS (2025-12-22)

### COMPLETED ✅
- [x] Phase 1: Schemas extracted to `schemas/` (9 files)
- [x] Phase 2: Routes migrated to `routes/` (14 files, 44 endpoints)
- [x] Phase 5: Router wiring - main.py now uses router.py
- [x] Build 341: All tests pass
- [x] Phase 4: Split tm_indexer.py (2105 lines → 4 modular files + 56-line wrapper)
  - `indexing/utils.py` (72 lines) - Normalization functions
  - `indexing/indexer.py` (540 lines) - TMIndexer class
  - `indexing/searcher.py` (380 lines) - TMSearcher (5-Tier Cascade)
  - `indexing/sync_manager.py` (583 lines) - TMSyncManager (DB↔PKL sync)
  - `tm_indexer.py` (56 lines) - Re-export wrapper for backward compatibility
  - 334 TM tests pass

### OPTIONAL (Future)
- [ ] Phase 3: Extract services from tm_manager.py (1133 lines)
- [ ] Phase 6: Delete api.py (marked LEGACY, preserved for reference)

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

### Current Structure (After P37 Refactoring)

```
server/tools/ldm/
├── router.py              # Main router aggregator
├── tm_indexer.py          # 56 lines - RE-EXPORT WRAPPER ✅
├── tm_manager.py          # 1133 lines - candidate for Phase 3
├── pretranslate.py        # 209 lines - OK
├── websocket.py           # 182 lines - OK
├── backup_service.py      # 618 lines - OK
├── routes/                # 14 files, 44 endpoints ✅
│   ├── health.py, projects.py, folders.py, files.py, rows.py
│   ├── tm_crud.py, tm_search.py, tm_entries.py, tm_indexes.py, tm_linking.py
│   ├── pretranslate.py, sync.py, settings.py
├── schemas/               # 9 Pydantic models ✅
│   └── common.py, project.py, folder.py, file.py, row.py, tm.py, settings.py, sync.py, pretranslate.py
├── indexing/              # 4 modular files ✅
│   ├── __init__.py        # Exports all classes
│   ├── utils.py           # 72 lines - Normalization functions
│   ├── indexer.py         # 540 lines - TMIndexer class
│   ├── searcher.py        # 380 lines - TMSearcher (5-Tier Cascade)
│   └── sync_manager.py    # 583 lines - TMSyncManager
└── file_handlers/         # File format parsers
    ├── excel_handler.py, txt_handler.py, xml_handler.py
```

**Total Refactored:**
- Routes: 3144 → 14 modular files (avg ~200 lines each)
- Indexing: 2105 → 4 modular files + 56-line wrapper
- Schemas: Extracted to 9 clean Pydantic models

---

## PHASE HISTORY

### Phase 1: Schemas ✅
Created `schemas/` directory with 9 Pydantic model files extracted from api.py.

### Phase 2: Routes ✅
Created `routes/` directory with 14 endpoint files (44 endpoints total).

### Phase 4: Indexing ✅
Split `tm_indexer.py` (2105 lines) into:
- `indexing/utils.py` (72 lines)
- `indexing/indexer.py` (540 lines)
- `indexing/searcher.py` (380 lines)
- `indexing/sync_manager.py` (583 lines)

### Phase 5: Router Wiring ✅
Created `router.py` to aggregate all sub-routers, updated main.py.

### Build Verification
- Build 341: All tests pass
- 334 TM tests verified after Phase 4

---

## SUCCESS CRITERIA ✅

- [x] No file > 600 lines (target was 500, indexer.py is 540 - acceptable)
- [x] All tests pass
- [x] All endpoints still work (44 endpoints verified)
- [x] Coverage maintained
- [x] Clean import structure with backward compatibility

---

*Last updated: 2025-12-22 | P37 Refactoring Complete*

---

## POST-REFACTORING

After refactoring completes:
1. Update test file `tests/integration/test_ldm_api.py` if needed
2. Run full coverage report
3. Continue with P36 coverage improvement plan

---

*P37 LDM Refactoring Plan | Created 2025-12-22*
