# Session Context

> Last Updated: 2026-01-05 (Session 32 - P9 Move + Recycle Bin Audit)

---

## STABLE CHECKPOINT

**Post-Session 32:** Build 453 (pending) | **Date:** 2026-01-05

Offline Storage now supports move operations. Recycle Bin works for ONLINE, missing for OFFLINE.

---

## Current State

**Build:** 453 (pending) | **Open Issues:** 1 (P9-BIN-001)
**Tests:** Move functionality needs E2E testing
**Status:** P9 Move COMPLETE, Recycle Bin PARTIAL

---

## SESSION 32 IN PROGRESS

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

### Recycle Bin Status

| Mode | Status | Notes |
|------|--------|-------|
| **ONLINE** | ✅ Working | Items go to LDMTrash, 30-day retention, restore works |
| **OFFLINE** | ❌ Missing | Local files/folders permanently deleted, no soft delete |

**Finding:** `delete_local_file()` and `delete_local_folder()` in offline.py do HARD DELETE, not soft delete to trash.

---

## SESSION 32 COMMITS

| Commit | Description |
|--------|-------------|
| `09b6907` | P9: Add move support for files/folders in Offline Storage |
| `e585fea` | Fix: Remove duplicate isFileType() function declaration |
| `a581c02` | Add auto-purge scheduled task for expired trash items |

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
| **P9** | **Offline/Online Mode** | ✅ COMPLETE (move, CRUD) |
| **P9-BIN** | **Offline Recycle Bin** | ❌ MISSING |
| P8 | Dashboard Overhaul | PLANNED |

### P9 Status: COMPLETE ✅

1. ✅ Unified endpoints (done)
2. ✅ TM assignment to Offline Storage (done - Session 30)
3. ✅ Folder CRUD in Offline Storage (done - Session 31)
4. ✅ Move files/folders in Offline Storage (done - Session 32)
5. ✅ Push changes to server (done - Session 21)

### P9-BIN: Offline Recycle Bin (NEW)

**Status:** Not implemented

**Required:**
1. Create `offline_trash` table in SQLite
2. Modify `delete_local_file()` to soft delete
3. Modify `delete_local_folder()` to soft delete
4. Add restore functionality
5. Add local trash purge (30 days)

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

*Session 32 | Build 453 | P9 Move COMPLETE - Offline Recycle Bin MISSING*
