# Session Context

> Last Updated: 2026-01-11 (Session 38 - Bug Fixes + UX Enhancements)

---

## SESSION 38 COMPLETE

### Bugs Fixed

| Bug | Description | Status |
|-----|-------------|--------|
| **BUG-038** | parent_id bug creating folders/uploading at project root | ✅ Fixed |
| **BUG-039** | Cell editor cursor jumping to beginning | ✅ Fixed |
| **TM Folders** | TM page now shows folders from Files page | ✅ Fixed |

### UX Enhancements Implemented

| Issue | Description | Status |
|-------|-------------|--------|
| **UX-001** | Revert row status hotkey (Ctrl+U) | ✅ DONE |
| **UX-002** | Right-click context menus in file viewer cells | ✅ DONE |
| **UX-003** | TM move functionality (cut/paste + "Move to...") | PLANNED |

### UX-001: Revert Row Status (Ctrl+U)

**Implementation:**
- Added `revertRowStatus()` function in VirtualGrid.svelte
- Ctrl+U sets row status to "untranslated" (reverts from confirmed/translated)
- Works in both edit mode and selection mode
- Makes API call to update backend

### UX-002: Cell Context Menu

**Implementation:**
- Right-click on any row in file viewer shows context menu
- Prevents browser default context menu

**Menu Options:**
```
┌─────────────────────────────┐
│ ✓ Confirm         Ctrl+S   │
│ 📝 Set as Translated       │
│ ↩ Set as Untranslated Ctrl+U│
│ ─────────────────────────── │
│ ⚠ Run QA on Row            │
│ ✗ Dismiss QA Issues  Ctrl+D │
│ + Add to TM                │
│ ─────────────────────────── │
│ 📋 Copy Source             │
│ 📋 Copy Target             │
│ 📋 Copy Row                │
└─────────────────────────────┘
```

**Files Modified:**
- `VirtualGrid.svelte` - Context menu state, handlers, UI, CSS

### Discussion: TM Management (UX-003 - PLANNED)

**Problem:** Can't move TMs after creation - stuck in UNASSIGNED.

**Solutions to implement:**
1. **Cut/Copy/Paste** - Same pattern as File Explorer
2. **"Move to..."** - Context menu → folder browser modal

---

## SESSION 37 COMPLETE

### UI Issues Being Fixed

| Issue | Description | Status |
|-------|-------------|--------|
| **UI-108** | TM page dropdown style → GRID style | ✅ COMPLETE |
| **UI-109** | Nested "Offline Storage > Offline Storage" | ✅ Fixed |
| **UI-110** | Browser right-click menu showing | ✅ Fixed |
| **UI-111** | Sync Dashboard modal too big | ✅ Fixed |
| **UI-113** | Login form cut off in Sync Dashboard | ✅ Fixed |

### Code Audit Findings

| File | Issue | Fix Applied |
|------|-------|-------------|
| TMExplorerTree.svelte | Svelte 4 `createEventDispatcher` | ✅ Removed |
| TMExplorerTree.svelte | Missing `oncontextmenu` handlers | ✅ Added |
| SyncStatusPanel.svelte | Modal size too large | ✅ Changed to "sm" |
| SyncStatusPanel.svelte | CSS values too big | ✅ Compacted |

---

## SESSION 36 COMPLETE ✅

### UI-107: Offline Storage Duplication Confusion ✅ FIXED

**Problem:** Users saw duplicate "Offline Storage" entries in File Explorer when Online.

**Fix Applied:**

| Step | What | Where | Change |
|------|------|-------|--------|
| **1** | Hide PostgreSQL platform from File Explorer | `FilesPage.svelte:206` | `.filter(p => p.name !== 'Offline Storage')` |
| **2** | Use CloudOffline icon in TM tree | `TMExplorerTree.svelte:553` | Conditional icon for "Offline Storage" platform |

**Result:**
```
FILE EXPLORER:
├── ☁️ Offline Storage     ← Only one! (SQLite local files)
├── 🏢 TestPlatform
└── ...

TM TREE:
├── 📦 Unassigned
├── ☁️ Offline Storage     ← Same icon! Consistent with File Explorer
├── 🏢 TestPlatform
└── ...
```

**Test Evidence:**
- Online mode: Both File Explorer and TM Tree show 1 "Offline Storage" with CloudOffline icon
- Offline mode: File Explorer shows 1 "Offline Storage" with CloudOffline icon
- Screenshots: `/tmp/ui107_fix_files.png`, `/tmp/ui107_fix_tm.png`, `/tmp/ui107_offline_files.png`
- Tests: `ui107_fix_test.spec.ts`, `ui107_offline_test.spec.ts` - Both pass

---

## SESSION 35 COMPLETE ✅

### Analysis: Offline Storage Duplication Confusion (UI-107)

**Problem:** Users see duplicate "Offline Storage" entries in File Explorer when Online.

**BUG CONFIRMED WITH TESTING (2026-01-08):**

| Location | Count | What's Shown |
|----------|-------|--------------|
| File Explorer (Online) | **2 entries** | ☁️ CloudOffline (SQLite) + 🏢 Platform (PostgreSQL) |
| TM Tree | 1 entry | 🏢 Platform icon (should be ☁️) |

**Test Evidence:**
- Clean DB → Visit TM page → PostgreSQL platform auto-created → File Explorer shows duplicates
- Screenshots: `/tmp/dup_01_tm_page.png`, `/tmp/dup_02_files_page.png`

**DB ID Analysis Completed:**

| Entry | ID Type | Database | Needed For |
|-------|---------|----------|------------|
| CloudOffline | String `'offline-storage'` | Virtual → SQLite | File operations |
| Offline Storage Platform | Auto-generated int | PostgreSQL | TM assignment FK |

**Key Finding:** CloudOffline does NOT need numeric DB ID - it uses SQLite `parent_id` chain.

**Key Decision:** Keep name "Offline Storage" everywhere - the confusion was duplicates and different icons, not the name.

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

**Build:** 454 | **Open Issues:** 1 (UX-003: TM move)
**Tests:** All passing
**Status:** All P9 features complete, UX-001/UX-002 done, Session 38 complete

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
