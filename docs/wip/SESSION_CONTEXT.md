# Session Context

> Last Updated: 2026-01-07 (Session 34 - TM Delete Modal)

---

## SESSION 34 COMPLETE ✅

### UI: TM Delete Modal (Clean UX) ✅ DONE

**Problem:** TM deletion used ugly browser `confirm()` dialog instead of clean UI.

**Solution Implemented:**

| Component | Change |
|-----------|--------|
| **TMExplorerTree.svelte** | Added `ConfirmModal` import and state |
| **TMExplorerTree.svelte** | Replaced `deleteTM()` to show modal instead of `confirm()` |
| **TMExplorerTree.svelte** | Replaced `deleteSelectedTMs()` for bulk delete modal |
| **TMExplorerTree.svelte** | Added `handleModalConfirm()` / `handleModalCancel()` handlers |

### Features:

| Feature | Before | After |
|---------|--------|-------|
| **Single TM delete** | Browser `confirm()` | Carbon modal with TM name + entry count |
| **Multi-select delete** | Browser `confirm()` | Carbon modal with selection count ("Delete 2 TMs") |
| **Multi-selection** | Already working | Verified: Ctrl+click, Shift+click |

### Tests Created

- `tests/tm-delete-modal.spec.ts` - Modal appearance, multi-select modal

### Commit

| Commit | Description |
|--------|-------------|
| `0d9dbef` | UI: Replace browser confirm() with Carbon modal for TM deletion |

---

## SESSION 33 COMPLETE ✅

### SYNC-009: Continuous Sync Causes Server Hang ✅ FIXED

**Problem:** After login, the continuous sync system hung the server.

**Root Cause:** The sync was calling `merge_row()` per row instead of using the optimized `merge_rows_batch()` function. With 1000+ row files, this meant 1000+ separate database operations.

**All Fixes Applied:**
1. ✅ Moved `initSync()` to only run AFTER authentication
2. ✅ Added guard to prevent duplicate `setTimeout` calls
3. ✅ Fixed bad `subscribe()()` pattern → use `get()` instead
4. ✅ Added `cleanupSync()` call on logout
5. ✅ **KEY FIX:** Use `merge_rows_batch()` instead of per-row `merge_row()`

**Files Modified:**
- `locaNext/src/routes/+layout.svelte` - initSync() timing
- `locaNext/src/lib/stores/sync.js` - Guard fixes, get() usage, cleanup
- `server/tools/ldm/routes/sync.py` - **Use batch merge**

**New Rule Added to CLAUDE.md:**
- Rule 15: **NO GREP FOR DEBUG** - Never use grep when debugging logs. Read FULL logs.

---

## STABLE CHECKPOINT

**Post-Session 34:** Build 454 | **Date:** 2026-01-07

All sync issues fixed. TM delete modal now uses clean Carbon UI.

---

## Current State

**Build:** 454 | **Open Issues:** 0
**Tests:** All passing
**Status:** All P9 features complete, TM UX improved

---

## SESSION 32 COMPLETE ✅

### P9: Move Files/Folders in Offline Storage ✅ DONE

**Problem:** Users couldn't drag-drop files into folders in Offline Storage.

**Solution Implemented:**

| Component | Change |
|-----------|--------|
| **Backend offline.py** | Added `move_local_file()`, `move_local_folder()` with cycle detection |
| **Backend sync.py** | Added `PATCH /offline/storage/files/{id}/move`, `PATCH /offline/storage/folders/{id}/move` |
| **Frontend FilesPage** | Updated `handleMoveItems()` to call new endpoints for local-file/local-folder |
| **Frontend ExplorerGrid** | Fixed `handleDragOver()`, `handleDrop()` to accept `local-folder` as drop target |

### Recycle Bin Auto-Purge ✅ DONE

**Problem:** Expired trash items (30 days) were never auto-deleted.

**Solution Implemented:**

| Component | Change |
|-----------|--------|
| **background_tasks.py** | Added `purge_expired_trash()` task running daily |
| **beat_schedule** | Added `purge-expired-trash` to Celery Beat |

### P9-BIN-001: Local Recycle Bin ✅ DONE

**Problem:** Offline Storage files/folders were PERMANENTLY deleted - no Recycle Bin support.

**Solution Implemented:**

| Component | Change |
|-----------|--------|
| **Schema offline_schema.sql** | Added `offline_trash` table with 30-day retention |
| **Backend offline.py** | Modified `delete_local_file()`, `delete_local_folder()` for soft delete |
| **Backend offline.py** | Added serialization helpers, trash operations (list, restore, permanent delete, empty, purge) |
| **Backend sync.py** | Added `/api/ldm/offline/trash` endpoints (GET, POST restore, DELETE) |
| **Frontend FilesPage** | Updated `loadTrashContents()` to fetch both PG and SQLite trash |
| **Frontend FilesPage** | Updated `restoreFromTrash()`, `permanentDeleteFromTrash()`, `emptyTrash()` for local items |

### Recycle Bin Status

| Mode | Status | Notes |
|------|--------|-------|
| **ONLINE** | ✅ Working | Items go to LDMTrash (PostgreSQL), 30-day retention |
| **OFFLINE** | ✅ Working | Items go to offline_trash (SQLite), 30-day retention |

**Test Results:** All passing - soft delete, 30-day retention, restore, permanent delete.

---

## SESSION 32 COMMITS

| Commit | Description |
|--------|-------------|
| `09b6907` | P9: Add move support for files/folders in Offline Storage |
| `e585fea` | Fix: Remove duplicate isFileType() function declaration |
| `a581c02` | Add auto-purge scheduled task for expired trash items |
| `a3862ff` | Docs: Update for Session 32 |
| `5c575ce` | P9-BIN-001: Add Recycle Bin for Offline Storage (backend) |
| `bfc04c7` | P9-BIN-001: Add API endpoints for local Recycle Bin |
| `049458f` | P9-BIN-001: Complete frontend for local Recycle Bin |

---

## SESSION 31 COMPLETE ✅

### P9: Offline Storage Folder CRUD ✅ DONE

**Problem:** Users couldn't create folders in Offline Storage - only files were supported.

**Solution Implemented:**

| Component | Change |
|-----------|--------|
| **Backend offline.py** | Added `create_local_folder()`, `get_local_folders()`, `delete_local_folder()`, `rename_local_folder()` |
| **Backend sync.py** | Added `POST/DELETE/PUT /api/ldm/offline/storage/folders` endpoints |
| **Backend sync.py** | Updated `/api/ldm/offline/local-files` to return folders with `parent_id` support |
| **Schema** | Updated `offline_folders` to allow NULL `server_id` for local folders |
| **Frontend** | Added `local-folder` type with navigation, create, delete support |

### API Endpoints Added

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/ldm/offline/storage/folders` | POST | Create folder |
| `/api/ldm/offline/storage/folders/{id}` | DELETE | Delete folder |
| `/api/ldm/offline/storage/folders/{id}/rename` | PUT | Rename folder |

### Tests Created

- `tests/offline-folder.spec.ts` - 7 tests (create, list, delete, rename, nested, validation)

---

## SESSION 30 COMPLETE ✅

### P9-ARCH: TM + Offline Storage Integration ✅ DONE

**Problem:** Offline Storage wasn't a real project, so TMs couldn't be assigned to it.

**Solution Implemented:**

| Component | Change |
|-----------|--------|
| **SQLite** | Created Offline Storage platform/project with ID=-1 |
| **PostgreSQL** | Created Offline Storage platform/project for TM assignment FK |
| **TM Tree** | Updated to include Offline Storage as first platform |
| **TM Assignment** | Drag-drop to Offline Storage works |
| **TM Activation** | Works after assignment |
| **TM Delete** | Added to context menu |
| **TM Multi-select** | Ctrl+click, Shift+click with bulk operations |

### Why Two Records?

| Database | ID | Purpose |
|----------|---|---------|
| PostgreSQL | Auto (31) | TM assignment foreign key target |
| SQLite | -1 | Offline file storage |

This is necessary because TM assignments have FK constraints to PostgreSQL tables.

### Files Modified

- `server/database/offline.py` - `OFFLINE_STORAGE_PLATFORM_ID = -1`, `_ensure_offline_storage_project()`
- `server/tools/ldm/routes/tm_assignment.py` - `ensure_offline_storage_platform/project()`, updated `get_tm_tree()`
- `locaNext/src/lib/components/ldm/TMExplorerTree.svelte` - Delete, multi-select, context menu

### Tests Created

- `tests/tm-offline-test.spec.ts` - TM tree, delete, multi-select
- `tests/tm-assignment-test.spec.ts` - Drag-drop assignment
- `tests/tm-activation-test.spec.ts` - TM activation

---

## File Scenarios (MEMORIZE)

| Scenario | sync_status | Permissions |
|----------|-------------|-------------|
| **Local File** (Offline Storage) | `'local'` | FULL CONTROL - move, rename, delete |
| **Synced File** (from server) | `'synced'` | READ STRUCTURE - edit content only |
| **Orphaned File** (server path deleted) | `'orphaned'` | READ ONLY - needs reassignment |

---

## PRIORITIES (Updated)

| Priority | Feature | Status |
|----------|---------|--------|
| **P9** | **Offline/Online Mode** | ✅ COMPLETE |
| **P9-BIN** | **Offline Recycle Bin** | ✅ COMPLETE (Session 32) |
| **P9-UI** | **TM Delete Modal** | ✅ COMPLETE (Session 34) |
| P8 | Dashboard Overhaul | PLANNED |

### P9 Status: COMPLETE ✅

1. ✅ Unified endpoints (done)
2. ✅ TM assignment to Offline Storage (done - Session 30)
3. ✅ Folder CRUD in Offline Storage (done - Session 31)
4. ✅ Move files/folders in Offline Storage (done - Session 32)
5. ✅ Push changes to server (done - Session 21)
6. ✅ Offline Recycle Bin (done - Session 32)
7. ✅ TM delete modal - clean UX (done - Session 34)

---

## ARCHITECTURE

```
LocaNext.exe (User PC)           Central PostgreSQL
├─ Electron + Svelte 5       →   ├─ All text data
├─ Embedded Python Backend       ├─ Users, sessions
├─ SQLite (offline storage)  ←   ├─ LDM rows, TM entries
├─ FAISS indexes (local)         └─ Logs
└─ Qwen model (optional)

UNIFIED PATTERN:
Endpoint → PostgreSQL first → SQLite fallback → Same response format

TM ASSIGNMENT:
Offline Storage platform in PostgreSQL (id=31) → TM can be assigned/activated
Offline files in SQLite (project_id=-1) → Uses Offline Storage TMs
```

---

## QUICK COMMANDS

```bash
# DEV servers
./scripts/start_all_servers.sh --with-vite

# Check servers
./scripts/check_servers.sh

# Run tests
cd locaNext && npx playwright test tests/offline-*.spec.ts

# Build trigger
echo "Build NNN" >> GITEA_TRIGGER.txt && git add -A && git commit -m "Build NNN: Description" && git push origin main && git push gitea main
```

---

*Session 34 | Build 454 | P9 COMPLETE - TM Delete Modal added*
