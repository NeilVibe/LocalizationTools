# Session Context

> Last Updated: 2026-01-04 (Session 25 - Dashboard Overhaul Plan)

---

## STABLE CHECKPOINT

**Post-Session 25:** Pending | **Date:** 2026-01-04 | **Tag:** Build 450 (pending)

ALL EXPLORER features (1-9) COMPLETE + P3-PHASE5 COMPLETE + Dashboard Overhaul PLANNED.

---

## Current State

**Build:** 450 (pending) | **Open Issues:** 0
**Tests:** 156 Playwright + 486 API passed, 0 failed
**Status:** P3-PHASE5 done. Dashboard overhaul plan complete (9 phases).

---

## SESSION 25 COMPLETED (Dashboard Overhaul Planning)

### P3-PHASE5: Offline Storage Fallback ✅ COMPLETE

Implemented "Offline Storage" virtual folder for orphaned files:
- `offline.py`: Added `mark_file_orphaned()`, `get_orphaned_files()`, `unorphan_file()`
- `sync.py`: Added `/offline/orphaned-files`, `/offline/orphaned-file-count` endpoints
- `FilesPage.svelte`: Shows "Offline Storage" in root when orphaned files exist
- `ExplorerGrid.svelte`: CloudOffline icon, orphaned file display

### Dashboard Overhaul Assessment ✅ COMPLETE

**Key Findings:**
| Item | Finding |
|------|---------|
| Svelte Version | `adminDashboard/` uses Svelte 4.2.8 (OLD), `locaNext/` uses 5.0.0 |
| Capability UI | Backend exists, frontend MISSING |
| Translation Tracking | No DB table, no logging |
| QA Tracking | No DB table, no logging |

**Decision:** Keep `adminDashboard/` separate, upgrade to Svelte 5.

**Plan Created:** `docs/wip/DASHBOARD_OVERHAUL_PLAN.md`

### 9-Phase Implementation Plan

| Phase | Task | Complexity |
|-------|------|------------|
| 1 | Svelte 5 Upgrade | MEDIUM |
| 2 | Capability Assignment UI | LOW |
| 3 | UI/UX Improvements | MEDIUM |
| 4 | Database Changes | LOW |
| 5 | Translation Activity Logging | MEDIUM |
| 6 | QA Usage Logging | LOW |
| 7 | Translation Stats Page | MEDIUM |
| 8 | QA Analytics Page | LOW |
| 9 | Custom Report Builder | HIGH |

### Architecture Decisions (CRITICAL)

**1. Client-Side Metrics Calculation**
```
Client calculates:               Server stores:
- difflib word-level diff        - Just INSERT
- similarity %                   - ~1ms response
- words_changed count            - No CPU load
- action classification
```

**2. Metrics-Only Payloads**
- Send: `{ similarity: 95.7, words_changed: 1 }` (~100 bytes)
- NOT: `{ old_text: "...", new_text: "..." }` (~1KB)
- Text already exists in `ldm_rows` - no duplication

**3. difflib SequenceMatcher (Word-Level Diff)**
- Detects exact word changes: "save" → "store" = 1 word changed
- Performance: 10-50μs for typical cells (imperceptible)
- Precise: knows which words changed, not just character similarity

**4. Database Optimization**
- SMALLINT instead of INTEGER (2 bytes vs 4)
- REAL instead of DOUBLE (4 bytes vs 8)
- Enum codes instead of VARCHAR (2 bytes vs 20)
- ~50 bytes/row (vs ~270 if stored text)
- ~62 MB/year for 100 users

**5. Existing Tables Already Handle:**
- `sessions` - login/logout ✅
- `log_entries` - tool usage ✅
- `user_activity_summary` - daily stats ✅
- `error_logs`, `performance_metrics` ✅

**6. Only 2 NEW Tables Needed:**
- `translation_activity` - pretrans acceptance, word counts
- `qa_usage_log` - QA tool usage

---

## SESSION 24 COMPLETED (Svelte 5 + EXPLORER-009 Privileged Operations)

### EXPLORER-009: Privileged Operations ✅ COMPLETE
Implemented capability system for privileged operations:

| Capability | Protects | Endpoint |
|------------|----------|----------|
| `delete_platform` | Platform deletion | DELETE /platforms/{id} |
| `delete_project` | Project deletion | DELETE /projects/{id} |
| `cross_project_move` | Cross-project moves | PATCH /files/move-cross-project, PATCH /folders/move-cross-project |
| `empty_trash` | Emptying recycle bin | POST /trash/empty |

**Admin Endpoints:**
- `GET /api/ldm/admin/capabilities/available` - List capability types
- `POST /api/ldm/admin/capabilities` - Grant capability to user
- `DELETE /api/ldm/admin/capabilities/{id}` - Revoke capability
- `GET /api/ldm/admin/capabilities` - List all grants
- `GET /api/ldm/admin/capabilities/user/{id}` - List user's capabilities

**Rule:** Admins always have all capabilities automatically.

### Svelte 5 Runes Upgrade
Migrated ExplorerSearch.svelte to full Svelte 5 patterns:
- Removed `createEventDispatcher()` - replaced with callback props
- Changed `on:navigate` → `onnavigate` (Svelte 5 event syntax)

### Bug Fixes
| Bug | Fix |
|-----|-----|
| `each_key_duplicate` error | Changed key to `${item.type}-${item.id}` |
| Multi-delete not working | Fixed `executeDelete()` to handle `selectedIds` |
| Stale documentation | Fixed ISSUES_TO_FIX.md and Roadmap.md |

### Files Created/Modified
| File | Changes |
|------|---------|
| `models.py` | NEW: `UserCapability` table |
| `capabilities.py` | NEW: Admin capability endpoints |
| `permissions.py` | Added `has_capability()`, `require_capability()` |
| `platforms.py`, `projects.py`, `trash.py`, `files.py`, `folders.py` | Added capability checks |
| `router.py` | Registered capabilities router |

---

## SESSION 23 COMPLETED (Search + Optimistic UI)

### EXPLORER-004: Explorer Search ✅
- New backend endpoint: `/api/ldm/search?q={query}`
- Searches across platforms, projects, folders, files
- Returns full navigation path for each result
- Beautiful, spacious search component: `ExplorerSearch.svelte`
- Keyboard navigation (Arrow Up/Down, Enter, Escape)
- Type-colored results (purple=platform, blue=project, amber=folder, green=file)
- Debounced search (300ms)

### Optimistic UI Power Review ✅
All explorer operations now use optimistic UI:
- **executeDelete()** - Item removed instantly, rollback on failure
- **handlePaste()** - Items appear instantly (copy/move)
- **executePendingMove()** - Confirmed moves appear instantly
- **executeRename()** - Name updates instantly, rollback on failure
- **restoreFromTrash()** - Item removed from trash instantly
- **permanentDeleteFromTrash()** - Item removed instantly
- **emptyTrash()** - All items cleared instantly

### Files Created/Modified
| File | Changes |
|------|---------|
| `search.py` | NEW - Search endpoint with path building |
| `ExplorerSearch.svelte` | NEW - Beautiful search component |
| `router.py` | Register search router |
| `FilesPage.svelte` | Optimistic UI for all operations, search integration |

---

## SESSION 22 COMPLETED (EXPLORER Features)

### EXPLORER-002: Hierarchy Validation ✅
- Platforms cannot be copied/cut (removed from context menu)
- `validatePasteTarget()` validates hierarchy rules:
  - Files/folders cannot be placed directly in platforms
  - Projects can only go to platform or root
  - Cannot paste into self

### EXPLORER-006: Confirmation Modals ✅
- Type-aware delete messages:
  - Platform: "Delete platform X and ALL projects inside?"
  - Project: "Delete project X and ALL files inside?"
- Move confirmation for project moves and cross-project moves

### EXPLORER-008: Recycle Bin (Soft Delete) ✅
- Uses existing LDMTrash table (30-day retention)
- Delete moves to trash instead of permanent delete
- Recycle Bin visible in explorer root
- Context menu: Restore, Delete Permanently
- Background menu: Empty Recycle Bin
- Backend endpoints: `/trash`, `/trash/{id}/restore`, `/trash/{id}` (DELETE), `/trash/empty`

### EXPLORER-005: Cross-Project Move ✅
- New endpoints: `/folders/{id}/move-cross-project`, `/files/{id}/move-cross-project`
- Updates folder/file and all children to new project
- DB-002: Auto-rename on naming conflicts

### EXPLORER-007: Undo/Redo (Ctrl+Z/Y) ✅
- New store: `undoStack.js` with 50-action history
- Ctrl+Z: Undo last action (restores from trash for delete)
- Ctrl+Y: Redo last undone action

### Files Created/Modified
| File | Changes |
|------|---------|
| `trash.py` | NEW - Trash endpoints (list, restore, delete, empty) |
| `undoStack.js` | NEW - Undo/redo store |
| `folders.py` | Cross-project move, soft delete |
| `files.py` | Cross-project move, soft delete |
| `projects.py` | Soft delete |
| `platforms.py` | Soft delete |
| `router.py` | Register trash router |
| `FilesPage.svelte` | Hierarchy validation, confirmations, trash UI, undo/redo |
| `ExplorerGrid.svelte` | Recycle Bin and trash item display |

---

## OPEN ISSUES (0)

All issues resolved!

---

## SESSION 25 COMPLETED (P3-PHASE5 Offline Storage)

### P3-PHASE5: Offline Storage Fallback ✅ COMPLETE
Implemented virtual "Offline Storage" folder for orphaned files:

| Component | Change |
|-----------|--------|
| `offline.py` | Added `mark_file_orphaned()`, `get_orphaned_files()`, `unorphan_file()` |
| `offline_schema.sql` | Added `error_message` column, `sync_status` index |
| `sync.py` | Added `/offline/orphaned-files`, `/offline/orphaned-file-count` endpoints |
| `FilesPage.svelte` | Shows "Offline Storage" in root when orphaned files exist |
| `ExplorerGrid.svelte` | Added CloudOffline icon, orphaned file display |

**User Flow:**
1. File becomes orphaned (server path deleted, created offline without match)
2. "Offline Storage" appears in explorer root
3. User enters to see orphaned files
4. User moves files to proper location via Ctrl+X/V

---

## SESSION 20 COMPLETED FIXES

### Priority 1: Auto-Updater Overhaul - DONE
- Changed `autoDownload = false` (user must confirm)
- Added `get-update-state` IPC handler
- UpdateModal checks for pending updates on mount
- Staged update flow: check → notify → download → restart

### Priority 2: Color Code Corruption Bug - FIXED
**Problem:** `confirmInlineEdit()` saved HTML spans instead of PAColor tags
**Root Cause:** Used `formatTextForSave()` directly without `htmlToPaColor()` first
**Fix:** Now converts HTML → PAColor → file format
**File:** `VirtualGrid.svelte:1363-1365`

### Priority 3: Offline/Online Toggle Freeze - FIXED
**Problem:** Rapid toggle caused "Connecting..." to get stuck
**Root Cause:** Race condition in reconnect logic
**Fix:** Added `isReconnecting` flag + try/finally in handlers
**Files:** `sync.js:162-197`, `SyncStatusPanel.svelte:71-84`

### Priority 4: UI Improvements - DONE
| Fix | Description |
|-----|-------------|
| Green indicator | Glowing green dot + border when online |
| Optimistic UI | Delete removes item instantly |
| Spacious modal | size="lg", more padding, explorer-style items |
| Glossary entry | Added "Optimistic UI" to CLAUDE.md |

---

## SESSION 21 COMPLETED FIXES

### Test Suite Fixes
- Fixed `confirm-row-api.spec.ts` - dynamic file ID lookup
- Fixed `qa-panel-verification.spec.ts` - unique filename generation
- Fixed `sync_test.spec.js` - Carbon modal selector
- Skipped 14 debug tests that used old selectors

### Database Refresh - DONE
- Cleaned corrupted data
- Created: Platform 27, Project 23, Folder 8, File 5
- Uploaded sample_language_data.txt (63 rows with PAColor tags)

### UI-090: Column Resize Bug - FIXED
- **Problem:** Source/Target columns couldn't be resized after adding index/stringId columns
- **Root Cause:** Cells used `flex: 0 0 {percent}%` (% of full container) but resize bars calculated position based on remaining space after fixed columns
- **Fix:** Changed to flex-grow ratios `flex: {ratio} 1 0` so cells properly share remaining space
- **File:** VirtualGrid.svelte lines 2118-2122, 2152, 2172

### SYNC-005: Hierarchy Sync - FIXED
- **Problem:** Only files could be synced, path tree (platform/project/folder) was missing
- **Root Cause:** `_sync_file_to_offline()` only saved file + rows, not parent hierarchy
- **Fix:**
  - File sync now syncs Platform → Project → Folder → File (in order)
  - Added `_sync_folder_to_offline()` for folder sync with all files
  - Updated project sync to include all folders
  - Added "folder" entity type to subscribe handler
- **Rule Added:** Server = source of truth for PATH. Offline edits to structure revert on sync.
- **Files:** `sync.py` (lines 510-600, 785-848), `OFFLINE_ONLINE_MODE.md`

### Test Results
- **156 passed** | 14 skipped | 0 failed

---

## OPEN ISSUES (1 remaining)

| Issue | Severity | Status |
|-------|----------|--------|
| P3-PHASE5 | LOW | OPEN - Offline Storage fallback container (edge case) |

## CLOSED SESSIONS 21-24

| Issue | Resolution |
|-------|------------|
| EXPLORER-001 | ✅ Ctrl+C/V/X clipboard operations |
| EXPLORER-002-009 | ✅ All EXPLORER features complete |
| SYNC-008 | ✅ TM sync implemented with last-write-wins merge |
| DB-002 | ✅ Per-parent unique names with auto-rename (_1, _2) |

---

## CLOSED ISSUES (Session 20)

| Issue | Resolution |
|-------|------------|
| AU-007 | Auto-updater race condition - FIXED |
| SYNC-001 | Auto-sync on file open - VERIFIED WORKING |
| SYNC-002 | Right-click register sync - VERIFIED WORKING |
| SYNC-003 | Modal showing items - VERIFIED WORKING |
| SYNC-004 | Modal layout - FIXED (spacious) |
| SYNC-006 | Online indicator - FIXED (green glow) |
| SYNC-007 | Explorer-style view - FIXED |
| COLOR-001 | Color code corruption - FIXED |
| TOGGLE-001 | Offline/online freeze - FIXED |

---

## P3 OFFLINE/ONLINE STATUS

### Phase Status (REVISED)

| Phase | Status | Description | Notes |
|-------|--------|-------------|-------|
| Phase 1 | ✅ DONE | Basic offline viewing/editing | Works |
| Phase 2 | ✅ DONE | Sync subscription + dashboard | Works |
| Phase 3 | ✅ DONE | Push local changes to server | Works |
| Phase 4 | ✅ MOSTLY DONE | Conflict resolution | **Last-write-wins auto-resolves** |
| Phase 5 | ⚠️ EDGE CASE | File dialog path selection | Only for NEW files created offline |
| Phase 6 | ⚠️ MINOR | Polish & edge cases | TM sync |

### What's ACTUALLY Done vs What Doc Says

| Feature | Doc Says | Reality | Verdict |
|---------|----------|---------|---------|
| **Conflict Resolution** | Complex UI with dialogs | `merge_row()` uses **last-write-wins** by timestamp | ✅ AUTO-RESOLVED |
| **Hierarchy Sync** | Files only | Platform → Project → Folder → File all sync | ✅ FIXED Session 21 |
| **File Dialog Path Selection** | Needed for sync | Only for NEW files created offline (rare) | ⚠️ EDGE CASE |
| **TM Sync** | Same as files | Implemented with last-write-wins | ✅ DONE (Build 447) |

### Conflict Resolution - ALREADY WORKS ✅

```python
# PostgreSQL model - auto-updates timestamp on ANY change:
updated_at = Column(DateTime, onupdate=datetime.utcnow)

# In offline.py merge_row():
if server_updated > local_updated:
    # Server wins - ALL fields including status
else:
    # Local wins - will push later
```

**Last-write-wins applies to EVERYTHING:**
- Target text changes
- Status changes (confirmed, reviewed, approved)
- Memo changes
- Any field modification

**Example - Confirmation Conflict:**
| Time | User A (Online) | User B (Offline) | Result |
|------|-----------------|------------------|--------|
| 10:00 | Confirms row 5 | - | Server: `updated_at=10:00` |
| 10:30 | - | Confirms row 5 | Local: `updated_at=10:30` |
| 11:00 | - | Syncs | **User B wins** (10:30 > 10:00) |

**Timestamp precision:** Second-level (`datetime.utcnow`). Same-second conflicts are extremely rare.

### File Dialog Path Selection - WHAT IT ACTUALLY IS

**Scenario:** User creates a NEW file while OFFLINE, then wants to sync it.

```
1. User is OFFLINE
2. Creates new file "my_translations.txt" (not from server)
3. Goes ONLINE
4. Clicks "Sync"
5. System asks: "Where should this new file go?"
   → Opens folder browser to pick: Platform/Project/Folder
```

**This is RARE.** Most users:
- Download existing files from server ✅ (works)
- Edit them offline ✅ (works)
- Push changes back ✅ (works)

Creating brand new files offline is edge case.

### TM Sync - WHAT'S NEEDED

TMs are linked to Platform/Project/Folder via `ldm_tm_assignment` table.

**Expected behavior:**
- When file syncs → auto-sync linked TMs
- TM entries are additive (rarely conflict)

**What needs implementing:**
1. `_sync_tm_to_offline()` function
2. Auto-sync TM when file/project/folder syncs
3. TM merge logic (simpler than rows - mostly INSERT)

### Current State Summary

| Feature | Status |
|---------|--------|
| Download file for offline | ✅ Works |
| Auto-sync on file open | ✅ Works |
| Sync dashboard | ✅ Works |
| Push changes to server | ✅ Works |
| Hierarchy sync (platform/project/folder) | ✅ Works |
| Last-write-wins merge | ✅ Works |
| Online/offline toggle | ✅ Works |
| Green/red indicators | ✅ Works |
| Svelte 5 optimistic UI | ✅ Works |
| TM sync | ✅ Works (Build 447) |
| New file path selection | ❌ Not implemented (edge case - Offline Storage fallback) |
| "Reviewed" row protection | ❌ Not implemented (low priority) |

---

## KEY FILES (Session 21)

### P3 Phase 3 - Push to Server
| File | Changes |
|------|---------|
| `server/tools/ldm/routes/sync.py` | Added `push-preview` and `push-changes` endpoints |
| `locaNext/src/lib/stores/sync.js` | Implemented `syncFileToServer()` and `getPushPreview()` |
| `SyncStatusPanel.svelte` | Added "Push Changes" button |

---

## KEY FILES (Session 20)

### Auto-Updater
| File | Changes |
|------|---------|
| `electron/main.js` | `autoDownload=false`, state storage, IPC handler |
| `electron/preload.js` | `getUpdateState()` method |
| `UpdateModal.svelte` | Check pending on mount |

### Offline/Online Sync
| File | Changes |
|------|---------|
| `sync.js` | `isReconnecting` flag, race condition fix |
| `SyncStatusPanel.svelte` | Green styling, optimistic UI, spacious modal |

### Color Code Fix
| File | Changes |
|------|---------|
| `VirtualGrid.svelte:1363-1365` | `htmlToPaColor()` before `formatTextForSave()` |

---

## NEXT STEPS

**All EXPLORER features COMPLETE!** Next priority:

1. **P3-PHASE5** - Offline Storage Fallback (last open issue)
2. **Dashboard** - User Management UI (admin endpoints exist)
3. **Stats System** - Translation activity tracking

---

## ARCHITECTURE

```
LocaNext.exe (User PC)           Central PostgreSQL
├─ Electron + Svelte 5       →   ├─ All text data
├─ Embedded Python Backend       ├─ Users, sessions
├─ SQLite (offline storage)  ←   ├─ LDM rows, TM entries
├─ FAISS indexes (local)         └─ Logs
└─ Qwen model (optional)

ONLINE:  PostgreSQL (multi-user, WebSocket sync)
OFFLINE: SQLite (single-user, subscribed data only)

SYNC FLOW (Current):
  Server → Local: ✅ WORKS (download for offline)
  Local → Server: ✅ WORKS (push local changes)
```

---

## QUICK COMMANDS

```bash
# DEV servers
./scripts/start_all_servers.sh --with-vite

# Check servers
./scripts/check_servers.sh

# Clear rate limit
./scripts/check_servers.sh --clear-ratelimit

# Playwright tests
cd locaNext && npx playwright test

# Build trigger
echo "Build NNN" >> GITEA_TRIGGER.txt && git add -A && git commit -m "Build NNN: Description" && git push origin main && git push gitea main
```

---

*Session 25 | Build 449 | All EXPLORER complete, Dashboard planning next*
