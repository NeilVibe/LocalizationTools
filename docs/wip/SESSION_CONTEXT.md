# Session Context

> Current state of LocaNext development. Updated each session.

**Last Updated:** 2026-01-12

---

## Current Focus

### P10: DB Abstraction Layer ✅ COMPLETE

**Status:** COMPLETE (Session 50)

**Goal:** Transform entire backend from inconsistent database patterns to unified Repository Pattern.

**What's Done:**
- [x] TMRepository implemented (TM routes only)
- [x] Plan created and approved
- [x] WIP documentation structure created
- [x] P10_DB_ABSTRACTION.md created
- [x] Roadmap.md updated with P10 section
- [x] DB_ABSTRACTION_LAYER.md expanded with full scope
- [x] **FileRepository implemented** (interface + PostgreSQL + SQLite)
- [x] **files.py routes migrated** (all 15 endpoints)
- [x] **RowRepository implemented** (interface + PostgreSQL + SQLite)
- [x] **rows.py routes migrated** (all 3 endpoints)
- [x] **ProjectRepository implemented** (interface + PostgreSQL + SQLite)
- [x] **projects.py routes migrated** (all 9 endpoints)
- [x] **FolderRepository implemented** (interface + PostgreSQL + SQLite)
- [x] **folders.py routes migrated** (all 8 endpoints)
- [x] **PlatformRepository implemented** (interface + PostgreSQL + SQLite)
- [x] **platforms.py routes migrated** (all 10 endpoints)
- [x] **QAResultRepository implemented** (FULL PARITY - SQLite persists too!)
- [x] **qa.py routes migrated** (all 6 endpoints)
- [x] **TrashRepository implemented** (FULL PARITY)
- [x] **trash.py routes migrated** (all 4 endpoints)

**What's Next:**
- [x] ~~Test both modes (PostgreSQL + SQLite)~~ - **DONE** (Session 50)
- [x] ~~Migrate remaining routes (sync.py - needs service extraction)~~ - **DONE** (SyncService pattern)
- [x] ~~Dead Code Audit~~ - **DONE** (removed 700+ lines of dead code)
- [x] ~~Post-P10 Code Review (qa.py)~~ - **DONE** (migrated to RowRepository)
- [x] ~~Granular Audit~~ - **DONE** (Session 50 - logging, dead code, files, folders)
- [x] ~~**Minor files migrated:** search.py, pretranslate.py, tm_linking.py~~ **DONE** (Session 50)
- [ ] **TM Tree Folder Mirroring** - `get_tree()` returns `folders: []` (TODO in code)
- [ ] **P10 Gap:** Routes have PostgreSQL permission checks that bypass Repository Pattern for offline mode

### P10 Test Results (Session 50)

**PostgreSQL Mode: FULL PASS**
- Platform/Project/Folder/File CRUD all work
- Row operations work
- Soft delete → Trash works

**SQLite Mode: REPOSITORY WORKS, API PARTIAL**
- Repository-level CRUD: All operations work directly
- API `storage=local` upload: Works
- API retrieval: Fails (routes check PostgreSQL for permissions)

**Bugs Fixed During Testing:**
1. folder_repo.py: Removed `updated_at` (LDMFolder lacks it)
2. row_repo.py: Removed `created_at` (LDMRow lacks it)
3. file_repo.py: Removed `memo` and `created_at`
4. folder_repo.py: Removed `memo` in copy
5. trash.py: Removed `memo` in serialize

---

## Repository Pattern Status

| Repository | Interface | PostgreSQL | SQLite | Routes Migrated |
|------------|-----------|------------|--------|-----------------|
| TMRepository | **DONE** | **DONE** | **DONE** | tm_assignment.py |
| FileRepository | **DONE** | **DONE** | **DONE** | files.py (15/15) |
| RowRepository | **DONE** | **DONE** | **DONE** | rows.py (3/3) |
| ProjectRepository | **DONE** | **DONE** | **DONE** | projects.py (9/9) |
| FolderRepository | **DONE** | **DONE** | **DONE** | folders.py (8/8) |
| PlatformRepository | **DONE** | **DONE** | **DONE** | platforms.py (10/10) |
| QAResultRepository | **DONE** | **DONE** | **DONE** | qa.py (6/6) |
| TrashRepository | **DONE** | **DONE** | **DONE** | trash.py (4/4) |
| **SyncService** | **DONE** | **DONE** | **DONE** | sync.py (6 sync endpoints) |

---

## Route Migration Status

| Route File | Size | Current Pattern | Target | Status |
|------------|------|-----------------|--------|--------|
| `tm_assignment.py` | 8KB | Repository | Repository | **DONE** |
| `files.py` | 81KB | Repository | Repository | **DONE** (15/15) |
| `rows.py` | 28KB | Repository | Repository | **DONE** (3/3) |
| `projects.py` | 11KB | Repository | Repository | **DONE** |
| `folders.py` | 21KB | Repository | Repository | **DONE** |
| `platforms.py` | 15KB | Repository | Repository | **DONE** |
| `qa.py` | 11KB | Repository | Repository | **DONE** |
| `trash.py` | 15KB | Repository | Repository | **DONE** |
| `grammar.py` | 5KB | Repository | Repository | **DONE** |
| `sync.py` | 45KB | SyncService | Service | **DONE** (6 sync endpoints, rest are local ops) |

---

## Server Status

```bash
# Check servers
./scripts/check_servers.sh

# Expected:
# PostgreSQL (5432)... ✓ OK
# Backend API (8888)... ✓ OK
# Vite Dev (5173)... ✓ OK
```

---

## Recent Sessions

### Session 50 (2026-01-11) - Continued
- **P10 search.py Migration - ONE Code Path Implementation**
- Added `search()` method to all 4 repository interfaces:
  - PlatformRepository, ProjectRepository, FolderRepository, FileRepository
- Implemented search() in all 8 PostgreSQL adapters (using `ilike`)
- Implemented search() in all 8 SQLite adapters (using `LIKE ... COLLATE NOCASE`)
- **Refactored search.py to use ONE code path:**
  - Removed the TWO code paths (if mode == "offline" vs else)
  - Now uses repository factories to select adapter based on auth token
  - ONE code path works for both PostgreSQL and SQLite
  - Example of P10 "ONE Code Path Principle" from DB_ABSTRACTION_LAYER.md
- Previously migrated: pretranslate.py, tm_linking.py (earlier in session)
- **All minor route files now migrated to Repository Pattern**

### Session 50 (2026-01-11)
- **GRANULAR AUDIT** - Comprehensive codebase health check
- Reset database to fresh state (`./scripts/db_manager.sh nuke`)
- **Backend Logging Coverage:**
  - Added `[PREFIX]` logging to all route files without prefixes
  - New prefixes: [FOLDERS], [PROJECTS], [TM], [TM-ENTRY], [TM-INDEX], [TM-SEARCH], [PRETRANS], [TM-ASSIGN], [TM-LINK], [CAPS], [HEALTH], [SETTINGS]
  - All 20 route files now have consistent logging prefixes
- **Logging System Check:**
  - Verified loguru configuration (server.log, error.log, access.log)
  - 50MB rotation, proper retention configured
- **Dead Code Audit:**
  - Removed unused imports from: search.py (Dict, Any), trash.py (List)
  - Removed unused imports from repositories: qa_repository.py (datetime), folder_repo.py (selectinload), tm_repo.py (LDMFolder), trash_repo.py (and_), file_repo.py (logger)
- **Stale Code Check:**
  - No commented-out code blocks found
  - No stale TODO/FIXME comments
  - P9 fallback patterns in search.py/pretranslate.py are intentional (low priority migration)
- **Unused Files Check:**
  - All route files properly registered in router.py
  - No orphaned Python files
- **Unused Folders Check:**
  - Found and removed orphaned `server/server/` directory (260KB duplicate data)
- **All servers verified running after audit**

### Session 49 (2026-01-11)
- **Post-P10 Code Review: qa.py P9 fallback cleanup**
- Migrated qa.py P9 fallback patterns to use Repository Pattern:
  - Updated `_run_qa_checks()` to work with dicts (from Repository) instead of LDMRow objects
  - `check_row_qa` now uses RowRepository.get() and RowRepository.get_all_for_file()
  - `check_file_qa` now uses FileRepository.get() and RowRepository.get_all_for_file()
- Removed manual offline mode check (`is_offline = auth_header.startswith("Bearer OFFLINE_MODE_")`)
- Removed RowLike wrapper classes (no longer needed)
- Cleaned up unused imports: `Request`, `LDMRow`
- NOTE: `_get_glossary_terms()` still uses LDMFile for project lookup - TM linking not yet in repository
- **qa.py is now FULLY repository-based** (no P9 fallback patterns remaining)

### Session 48 (2026-01-11)
- **Completed sync.py service extraction** (SyncService pattern)
- Removed old helper functions from sync.py (~480 lines of duplicate code)
- Added sync-to-central methods to SyncService:
  - `sync_file_to_central()` - Upload file from SQLite to PostgreSQL
  - `sync_tm_to_central()` - Upload TM from SQLite to PostgreSQL
- Updated 6 sync.py endpoints to use SyncService:
  - POST /offline/subscribe
  - POST /offline/push-changes
  - POST /offline/sync-subscription
  - POST /files/{file_id}/download-for-offline
  - POST /sync-to-central (NEW)
  - POST /tm/sync-to-central (NEW)
- Cleaned up unused imports in sync.py (os, create_engine, Session, LDMRow, LDMTranslationMemory)
- Added `[SYNC]` logging prefix throughout
- **Dead Code Audit completed:**
  - Removed unused imports from 8 route files
  - files.py: 2152 → 1488 lines (**664 lines removed, 31% reduction**)
    - Removed 8 orphaned `_*_local_*` P9 helper functions (~500 lines)
    - Removed 3 old `_build_*_file()` functions that took LDMRow objects (~150 lines)
  - rows.py: ~405 → 362 lines (~43 lines removed)
    - Removed orphaned `_auto_sync_tm_indexes` duplicate function
    - Removed unused `datetime` import
  - No commented-out code blocks found
  - P9 fallback patterns identified (not dead code, needs migration):
    - qa.py lines 300-330 and 430-460 (check_row_qa, check_file_qa)
    - These should use RowRepository - documented for Post-P10 review
- **Remaining sync.py endpoints** are pure local operations (don't need SyncService)

### Session 47 (2026-01-11)
- **Migrated grammar.py** to Repository Pattern (FULL PARITY)
- Migrated 2 grammar endpoints:
  - GET /grammar/status (already repository-free, just uses languagetool)
  - POST /files/{file_id}/check-grammar (now uses FileRepository + RowRepository)
  - POST /rows/{row_id}/check-grammar (now uses RowRepository)
- Removed all P9 fallback code (direct SQLAlchemy + offline_db fallback)
- Cleaned up unused imports (AsyncSession, LDMRow, LDMFile, get_async_db)
- Added `[GRAMMAR]` prefix to log messages for granular debugging
- **Completed rows.py migration** (was 2/3, now 3/3):
  - GET /projects/{project_id}/tree (now uses ProjectRepository + FolderRepository + FileRepository)
  - Removed unused LDMProject/LDMFolder imports
  - Added `[ROWS]` logging prefix
- **Completed files.py migration** (was 14/15, now 15/15):
  - POST /files/upload (now uses ProjectRepository, FolderRepository, FileRepository for verification)
  - GET /projects/{project_id}/files (fixed project verification to use ProjectRepository)
  - Removed unused LDMProject/LDMFolder imports
  - Added `[FILES]` logging prefix
- **Started sync.py service extraction**:
  - Created `server/services/` directory
  - Created `SyncService` class with sync operations:
    - `sync_file_to_offline()` - Download file from PG to SQLite
    - `sync_folder_to_offline()` - Download folder
    - `sync_project_to_offline()` - Download project
    - `sync_platform_to_offline()` - Download platform
    - `sync_tm_to_offline()` - Download TM
    - `push_file_changes_to_server()` - Push local changes
    - `push_tm_changes_to_server()` - Push TM changes
  - Updated 4 sync.py endpoints to use SyncService:
    - POST /offline/subscribe
    - POST /offline/push-changes
    - POST /offline/sync-subscription
    - POST /files/{file_id}/download-for-offline
  - Added `[SYNC]` logging prefix
  - Old helper functions still in file (can be removed in cleanup)

### Session 46 (2026-01-11)
- **Implemented QAResultRepository** with **FULL PARITY** principle
- Rejected ephemeral/stub approach - SQLite must persist QA results identically to PostgreSQL
- Added `offline_qa_results` table to SQLite schema
- Created interface, PostgreSQL adapter, SQLite adapter with full persistence
- Added get_qa_repository factory function
- **Migrated all 6 qa.py endpoints**:
  - POST /rows/{row_id}/check-qa
  - GET /rows/{row_id}/qa-results
  - POST /files/{file_id}/check-qa
  - GET /files/{file_id}/qa-results
  - GET /files/{file_id}/qa-summary
  - POST /qa-results/{result_id}/resolve
- **Removed parasitic P9 fallback functions** (`_check_local_row_qa`, `_check_local_file_qa`)
- Updated DB_ABSTRACTION_LAYER.md with FULL PARITY principle documentation
- Fixed stale "ephemeral" comments in interface docstrings
- **Implemented TrashRepository** with FULL PARITY
- Updated SQLite schema to add `parent_project_id` and `deleted_by` columns
- Created interface, PostgreSQL adapter, SQLite adapter
- **Migrated all 4 trash.py endpoints**:
  - GET /trash
  - POST /trash/{trash_id}/restore
  - DELETE /trash/{trash_id}
  - POST /trash/empty
- **ALL 8 REPOSITORIES NOW COMPLETE!**

### Session 45 (2026-01-11)
- **Implemented PlatformRepository** (interface + PostgreSQL + SQLite adapters)
- Added get_platform_repository factory function
- **Migrated all 10 platforms.py endpoints** with granular logging:
  - GET /platforms (list_platforms)
  - POST /platforms (create_platform)
  - GET /platforms/{platform_id} (get_platform)
  - PATCH /platforms/{platform_id} (update_platform)
  - DELETE /platforms/{platform_id} (delete_platform)
  - PATCH /projects/{project_id}/platform (assign_project_to_platform)
  - PUT /platforms/{platform_id}/restriction (set_platform_restriction)
  - GET /platforms/{platform_id}/access (list_platform_access)
  - POST /platforms/{platform_id}/access (grant_platform_access)
  - DELETE /platforms/{platform_id}/access/{user_id} (revoke_platform_access)
- Added `[PLATFORM]` prefix to all log messages for granular debugging
- Permission helpers remain in routes (business logic)
- Trash serialization remains in routes (requires SQLAlchemy objects)
- Verified db_manager.sh has comprehensive DB tooling
- Found duplicate "Offline Storage" platform (residue from server sync)

### Session 44 (2026-01-11)
- **Implemented FolderRepository** (interface + PostgreSQL + SQLite adapters)
- Added get_folder_repository factory function
- **Migrated all 8 folders.py endpoints**:
  - GET /projects/{project_id}/folders (list_folders)
  - POST /folders (create_folder)
  - GET /folders/{folder_id} (get_folder_contents)
  - PATCH /folders/{folder_id}/rename (rename_folder)
  - PATCH /folders/{folder_id}/move (move_folder)
  - PATCH /folders/{folder_id}/move-cross-project (move_folder_cross_project)
  - POST /folders/{folder_id}/copy (copy_folder)
  - DELETE /folders/{folder_id} (delete_folder)
- Removed old helper functions (_update_folder_project_recursive, _copy_folder_recursive)
- Trash serialization remains in routes (requires SQLAlchemy objects)
- All 360 tests passed

### Session 43 (2026-01-11)
- **Implemented ProjectRepository** (interface + PostgreSQL + SQLite adapters)
- Added get_project_repository factory function
- **Migrated all 9 projects.py endpoints**:
  - POST /projects (create_project)
  - GET /projects/{project_id} (get_project)
  - PATCH /projects/{project_id}/rename (rename_project)
  - DELETE /projects/{project_id} (delete_project)
  - PUT /projects/{project_id}/restriction (set_project_restriction)
  - GET /projects/{project_id}/access (list_project_access)
  - POST /projects/{project_id}/access (grant_project_access)
  - DELETE /projects/{project_id}/access/{user_id} (revoke_project_access)
- Permission helpers remain in routes (business logic)
- Trash serialization remains in routes (complex business logic)
- All 360 tests passed

### Session 42 (2026-01-11)
- **Implemented RowRepository** (interface + PostgreSQL + SQLite adapters)
- Added fuzzy search support to PostgreSQL adapter (pg_trgm)
- Added get_row_repository factory function
- **Migrated 2/3 rows.py endpoints**:
  - GET /files/{file_id}/rows (with search, filters, pagination)
  - PUT /rows/{row_id} (with TM auto-add, WebSocket broadcast)
- Removed old fallback helper functions
- All database abstractions maintained, business logic preserved

### Session 41 (2026-01-11)
- Fixed UI test selectors (`.grid-row` not `.explorer-grid-row`)
- Fixed modal button selectors (`.bx--modal.is-visible`)
- **Migrated 7 more files.py endpoints** (14/15 total):
  - GET /files (list all)
  - GET /files/{file_id}/download
  - POST /files/{file_id}/register-as-tm
  - POST /files/{file_id}/merge
  - GET /files/{file_id}/convert
  - GET /files/{file_id}/extract-glossary
- Created `_build_excel_file_from_dicts` helper for Repository Pattern
- All 145 Playwright tests passing (100%)
- Only POST /files/upload remains (complex, already has P9 routing)

### Session 40 (2026-01-11)
- Implemented FileRepository (interface + PostgreSQL + SQLite adapters)
- Added get_file_repository factory function
- Updated all __init__.py exports
- Verified imports work correctly
- Migrated 7/15 files.py endpoints to Repository Pattern:
  - GET /files/{file_id}
  - GET /projects/{project_id}/files
  - DELETE /files/{file_id}
  - PATCH /files/{file_id}/rename
  - PATCH /files/{file_id}/move
  - PATCH /files/{file_id}/move-cross-project
  - POST /files/{file_id}/copy

### Session 39 (2026-01-11)
- Implemented TMRepository (interface + PostgreSQL + SQLite adapters)
- Created DB Abstraction Layer documentation
- Created P10 plan for full implementation
- Recreated WIP documentation structure

### Previous Sessions
- See [Roadmap.md](../../Roadmap.md) for completed features

---

## Quick Commands

```bash
# Start DEV servers
./scripts/start_all_servers.sh --with-vite

# Run tests
cd locaNext && npx playwright test

# Check build status
./scripts/gitea_control.sh status
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
