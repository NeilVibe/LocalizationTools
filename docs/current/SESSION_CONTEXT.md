# Session Context

> Last Updated: 2026-01-17 (Session 46 - Patch Updater Fix)

---

## SESSION 46: Patch Updater - Finding the Truth

### The Lies I Told (And How I Found Them)

| Lie | Truth | How I Found It |
|-----|-------|----------------|
| "Hot-swap will work" | Windows locks files in use - can't overwrite | User said "blocked at app.asar" |
| "Just need to fix the download" | Download worked fine, swap failed | Tested curl from Windows - worked |
| "Reordering code will fix it" | Old app has old (broken) code | Realized installed app != new build |
| "skip_linux builds have installer" | skip_linux skips Windows build too | 404 on LocaNext-Setup.exe |

### Root Cause Chain

```
1. ATTEMPT: Replace app.asar while Electron running
   ↓
2. FAIL: Windows file locking prevents overwrite
   ↓
3. SYMPTOM: "blocked at app.asar" - download completes, swap fails
   ↓
4. HIDDEN: Error swallowed in try/catch, no visible feedback
```

### The Real Fix (Build 468+)

**Before (Broken):**
```javascript
// In applyPatchUpdate():
fs.copyFileSync(tempPath, destPath);  // ← FAILS: destPath is LOCKED
```

**After (Fixed):**
```javascript
// 1. Download to staging folder (not locked)
const stagingPath = path.join(STAGING_DIR, update.name);
await downloadFile(url, stagingPath);

// 2. Save pending update info
fs.writeFileSync(PENDING_FILE, JSON.stringify(pendingInfo));

// 3. On restart, PowerShell script swaps files AFTER app closes
spawn('powershell.exe', ['-File', scriptPath], { detached: true });
app.quit();
```

### Files Changed

| File | What |
|------|------|
| `electron/patch-updater.js` | Staging dir, pending file, swap script generation |
| `electron/main.js` | Check pending on startup, spawn swap script on restart |

### Chicken-and-Egg Problem

**Issue:** Old installed app has broken patch updater. New build has fix, but old app can't apply it.

**Solution:** Fresh install from new build. Then future updates work.

### Testing Protocol (MUST DO)

1. **Fresh install** from new build (not update from old)
2. Make a code change and build again
3. Open app - should detect update
4. Click "Restart Now" - should:
   - Create swap script
   - Close app
   - Script waits, swaps, restarts
5. Verify new version running

### Key Insight

**Never trust "it should work" - always verify the actual behavior.** The code looked correct but Windows file locking made it impossible. Had to test from Windows to find the truth.

---

## SESSION 45: Implementation Summary

### Work Completed

| Task | Status | Files Changed |
|------|--------|---------------|
| **Roadmap Cleanup** | ✅ DONE | Roadmap.md (957→369 lines) |
| **TM UX Polish** | ✅ DONE | TMExplorerGrid.svelte |
| **Toast Redesign** | ✅ DONE | GlobalToast.svelte, toastStore.js |
| **Windows PATH Tests** | ✅ DONE | tests/unit/test_windows_paths.py (30 tests) |
| **TM Source in Matches** | ✅ DONE | tm.py, tm_search.py, TMQAPanel.svelte |
| **TM Hierarchy Sprint 5** | ✅ DONE | TMExplorerGrid.svelte, TMUploadModal.svelte, TMPage.svelte |

### Changes Made

**1. Roadmap.md - Major Cleanup**
- Reduced from 957 → 369 lines (61% reduction)
- Added Repository Pattern verification table
- Collapsed completed milestones into `<details>` sections
- Clear current priorities at top

**2. TM UX Polish**
- Added "View Entries" to TM context menu (was missing!)
- Added tooltip: "Double-click to view/edit entries"
- TM entries now accessible via right-click menu

**3. Toast Redesign**
- Replaced bulky Carbon ToastNotification with custom minimal toast
- Moved from top-right to bottom-right (less invasive)
- Shorter durations (2-6s vs 3-8s)
- Added `silent` flag check (FAISS auto-sync no longer spams toasts)

**4. Windows PATH Tests**
- Created 30 new tests for cross-platform path handling
- Tests cover: normalization, download, upload, model, PKL, long paths, special chars
- Auto-included in CI (tests/unit/ already in workflow)

**5. TM Source in Matches**
- Added `tm_name` to TMSuggestion schema
- Backend now returns TM name with each match
- UI shows blue badge with TM name in match results

**6. TM Hierarchy Sprint 5 - Platform Management UI**
- Added "Upload TM Here" to platform/project/folder context menu
- TMUploadModal now accepts `targetScope` prop
- After upload, TM auto-assigns to the selected scope
- Modal heading shows target: "Upload TM to {name}"
- Complete TM Hierarchy system now finished (all 5 sprints)

---

## SESSION 45: Planning & Prioritization

### What We Have (Clarified)

| Feature | Status | How to Access |
|---------|--------|---------------|
| **TM Entry Viewer** | ✅ EXISTS | TM Page → Double-click TM → TMDataGrid (full-page) |
| **TM Entry Editing** | ✅ EXISTS | Double-click any row → Edit inline → Auto-saves |
| **TM Entry Add/Delete** | ✅ EXISTS | API endpoints exist, UI has context menu |
| **TM Auto-Sync** | ✅ EXISTS | Background task syncs indexes after changes |

### TM Repository Pattern - VERIFIED ✅

**Holy Trinity working for TM:**
```
        FACTORY (get_tm_repository)
              /\
             /  \
            /    \
    PostgreSQL    SQLite
      Repo          Repo
```

| TM Operation | Repository? | Both Modes? |
|--------------|-------------|-------------|
| List TMs | ✅ YES | ✅ YES |
| Get TM | ✅ YES | ✅ YES |
| Delete TM | ✅ YES | ✅ YES |
| **Get Entries** | ✅ YES | ✅ YES |
| **Add Entry** | ✅ YES | ✅ YES |
| **Update Entry** | ✅ YES | ✅ YES |
| **Delete Entry** | ✅ YES | ✅ YES |
| **Confirm Entry** | ✅ YES | ✅ YES |
| **Bulk Confirm** | ✅ YES | ✅ YES |
| Upload TM (file) | ❌ TMManager | ⚠️ Online only |
| Export TM (file) | ❌ TMManager | ⚠️ Online only |

**Why Upload/Export use TMManager:**
- Complex file parsing (TXT, XML, XLSX formats)
- Bulk insert with progress tracking
- File generation with multiple export formats
- Documented design decision (tm_crud.py line 12)

**UX Flow for TM Editing:**
```
TM Page → Navigate to TM → Double-click → TMDataGrid opens
         ├── Infinite scroll (200 entries/batch)
         ├── Double-click row = Edit inline
         ├── Optimistic UI (instant visual feedback)
         ├── Search bar for filtering
         ├── 8 metadata column options
         └── Changes auto-save to backend
```

### Task Manager & Toast Review ✅

**Task Manager Status:**
- ✅ TrackedOperation context manager works
- ✅ WebSocket events emit properly
- ✅ Frontend polls every 3s as fallback
- ✅ Silent operations tracked but don't spam toasts
- ❌ ActiveOperation NOT using Repository Pattern (by design - infrastructure code)

**Toast Redesign (Session 45):**

| Before | After |
|--------|-------|
| Carbon ToastNotification (bulky) | Custom minimal toast |
| Top-right position | Bottom-right position |
| 400px max width | 320px max width |
| 3-8 second durations | 2-6 second durations |
| Missing silent flag check | ✅ Respects `silent: true` |

**New Toast Design:**
```
┌─────────────────────────────────┐
│ ● Upload: data.xlsx         ✕  │  ← Slim, minimal
└─────────────────────────────────┘
   ↑ Icon    Message          Close
```

**Key Fixes:**
1. `GlobalToast.svelte` - Added `data.silent` check for operation_start/complete
2. Replaced Carbon ToastNotification with custom minimal component
3. Shorter durations (users check Task Manager for details)
4. Bottom-right positioning (less invasive)

### TM Upload/Export Gap

**Current State:**
- `POST /tm/upload` - Uses TMManager directly (PostgreSQL only)
- `GET /tm/{id}/export` - Uses TMManager directly (PostgreSQL only)

**Why This Gap Exists:**
1. Complex file parsing (TXT, XML, XLSX)
2. Bulk insert with progress tracking
3. File generation with multiple formats
4. Documented at `tm_crud.py:12`

**Options:**
1. **Accept gap** - Offline users can't upload/export TM files (current)
2. **Add SQLite support to TMManager** - Complex, needs offline file handling
3. **Create OfflineTMManager** - Separate implementation for SQLite

**Recommendation:** Accept gap for now. Offline mode is for working with synced data, not creating new TMs from files. Users can:
- Upload TMs in online mode
- Sync TMs to offline
- Edit/add entries offline (works via Repository Pattern)

### Priorities Confirmed

| Priority | Task | Status | Notes |
|----------|------|--------|-------|
| **P11-A** | Windows PATH Tests | TODO | 7 tests for Windows-specific paths |
| **P11-B** | TM UX Polish | TODO | Make TM entry editing more discoverable |
| **P11-C** | Toast Redesign | ✅ DONE | Minimal, slick, non-invasive |
| **LOW** | Dashboard Overhaul | PLANNED | Stronger, better, more organized |

### Windows PATH Tests (P11-A)

Tests to add for Windows builds:

| Test | Description |
|------|-------------|
| Download Path | File downloads go to correct location |
| Upload Path | File uploads work from Windows paths |
| Model Path | Qwen/embeddings load from AppData |
| PKL Path | Index files save/load correctly |
| Embeddings Path | Vector indexes stored properly |
| Install Path | App installs to Program Files |
| Merge Path | Merged files export to correct location |

### TM UX Polish (P11-B)

Current issue: Users don't know TM entry editor exists.

**Possible improvements:**
1. Add "Edit Entries" button/label more prominently in TM grid
2. Visual hint on TM items ("double-click to view entries")
3. Better onboarding/tooltips
4. Right-click context menu with "Edit Entries" option

### Dashboard Overhaul (P8)

**Status:** LOW PRIORITY (after platform stability)

**Goals:**
- Svelte 5 upgrade for adminDashboard
- Translation activity logging
- QA analytics
- Cleaner, more organized layout

---

## CI Verification of P10 Repository Pattern ✅ COMPLETE

**Status:** BOTH CI SYSTEMS VERIFIED | **Date:** 2026-01-16

### Results

| CI System | Build | Status | Iterations |
|-----------|-------|--------|------------|
| **Gitea** | 455 | ✅ SUCCESS | 2 (fixed missing import) |
| **GitHub** | 456 | ✅ SUCCESS | 1 (passed first try) |

| What | Status |
|------|--------|
| P10 DB Abstraction Layer | ✅ 100% COMPLETE |
| Repository Pattern Test Rewrite | ✅ All tests pass LOCAL |
| **Gitea CI** | ✅ **BUILD 455 PASSED** |
| **GitHub CI** | ✅ **BUILD 456 PASSED** |

### GDP-P10 Checkpoints Added to Both Workflows

Both `.gitea/workflows/build.yml` and `.github/workflows/build-electron.yml` now have:
- GDP-P10-1: Repository Imports Check
- GDP-P10-2: Factory Pattern Test
- GDP-P10-3: Abstract Interface Test
- GDP-P10-4: Test File Imports Check

### Loop Protocol Results

**Gitea:**
1. Build 454: FAILED - Missing `LDMTranslationMemory` import in tm_indexes.py
2. Build 455: SUCCESS - Fixed and all 1000+ tests passed

**GitHub:**
1. Build 456: SUCCESS - Passed on first try (17m14s)

---

## SESSION 43 COMPLETE ✅

### Repository Pattern Test Rewrite

**Goal:** Update all mocked tests to use Repository Pattern instead of direct DB mocking.

**Problem:** After P10 DB Abstraction Layer (Session 41), tests that mocked `get_async_db` started failing because routes now use Repository factories, not direct DB access.

**Error Example:**
```python
# OLD (broken): Mocked db.execute() but repo uses .scalar()
TypeError: '>' not supported between instances of 'MagicMock' and 'int'
```

### Solution: Mock at Repository Level

**Before (DB Level Mocking):**
```python
# Tests mocked the DB session
fastapi_app.dependency_overrides[get_async_db] = override_get_db
mock_db.execute = AsyncMock(return_value=mock_result)
```

**After (Repository Level Mocking):**
```python
# Tests now mock repository factories
fastapi_app.dependency_overrides[get_project_repository] = lambda: mock_project_repo
repos["project_repo"].get.return_value = sample_project
```

### Files Rewritten

| File | Tests | Changes |
|------|-------|---------|
| `test_mocked_full.py` | 52 | Full rewrite - mock all 9 repositories |
| `test_routes_qa.py` | 16 | Updated `_run_qa_checks` and endpoint tests |

### Mock Fixtures Created

| Fixture | Methods |
|---------|---------|
| `mock_project_repo` | get, get_all, create, delete, rename, etc. |
| `mock_file_repo` | get, get_by_project, create, generate_unique_name, etc. |
| `mock_folder_repo` | get, get_all, create, delete, get_with_contents, etc. |
| `mock_row_repo` | get, get_with_file, get_for_file, update, etc. |
| `mock_tm_repo` | get, get_all, get_entries, search_entries, add_entry, etc. |
| `mock_capability_repo` | get_user_capability, grant_capability, etc. |
| `mock_trash_repo` | get, create, restore, permanent_delete, etc. |

### Key Pattern Changes

| Aspect | Before | After |
|--------|--------|-------|
| **Dependency Override** | `get_async_db` | `get_*_repository` factories |
| **Return Types** | MagicMock objects | Dicts matching interface |
| **Method Names** | `db.execute()` | `repo.get()`, `repo.get_for_file()`, etc. |
| **Tuples** | N/A | `get_for_file()` returns `(rows, total)` |

### Test Results

| Suite | Before | After |
|-------|--------|-------|
| `test_mocked_full.py` | 15 failures | 52/52 ✅ |
| `test_routes_qa.py` | 9 failures | 16/16 ✅ |
| All LDM unit tests | ~120 passing | 131/131 ✅ |
| All unit tests | ~900 passing | 871/871 ✅ (33 skipped) |

### The Holy Trinity of DB 🔺

```
        FACTORY
       (runtime selection)
           /\
          /  \
         /    \
      REPO    ABSTRACT
   (interface)  (implementation)
```

- **Factory**: `get_*_repository()` - selects PostgreSQL or SQLite based on token
- **Repository**: Interface defining all operations (get, create, update, etc.)
- **Abstract**: Both PostgreSQL and SQLite implement the same interface

**Tests now mock at the Repository level, matching the architecture.**

---

## SESSION 42 COMPLETE ✅

### QACompilerNEW - 1:1 Monolith Alignment

**Goal:** Ensure QACompilerNEW is functionally identical to the monolith (QAExcelCompiler).

**Fixes Applied:**

| File | Issue | Fix |
|------|-------|-----|
| `config.py` | Missing Gimmick clustering | Added `"Gimmick": "Item"` |
| `compiler.py` | Case-sensitive Item check | Changed to `category.lower() == "item"` |
| `compiler.py` | Created missing sheets | Changed to skip with warning (like monolith) |
| `processing.py` | Complex fallback matching | Simplified to direct index matching only |
| `knowledge.py` | Font styling incomplete | Added `fill != _no_colour_fill` check |

**Code Removed (unused fallback logic):**
- `get_row_signature()` - 24 lines
- `find_matching_row_fallback()` - 29 lines
- `find_matching_row_item_fallback()` - 44 lines
- `unmatched_rows` tracking

**Verified 1:1 Identical:**

| Module | Status |
|--------|--------|
| Transfer (QA old → new) | ✓ All 7 functions identical |
| Compiler | ✓ Fixed (2 issues) |
| Processing | ✓ Direct index matching |
| Discovery | ✓ Folder patterns identical |
| Excel ops | ✓ Master creation identical |
| All 8 generators | ✓ Aligned |

**Clustering Confirmed:**
```
Master_System.xlsx = System + Skill + Help
Master_Item.xlsx   = Item + Gimmick
```

**Commits:**

| Commit | Description |
|--------|-------------|
| `6224ddd` | Fix: QACompilerNEW 1:1 alignment with monolith |
| `d2cd32b` | Chore: Update QACompilerNEW.zip |

---

## SESSION 41 COMPLETE ✅

### P10: DB Abstraction Layer - 100% COMPLETE

**Goal Achieved:** FULL ABSTRACT + REPO + FACTORY - Routes touch ONLY repositories, NEVER direct DB.

**Stats:**
- **65 → 7** direct DB calls (only intentional admin routes remain)
- **20/20** routes using Repository Pattern
- **9/9** factory functions passing user context
- **9/9** PostgreSQL repos with permissions baked in

### What Was Done

| Task | Status |
|------|--------|
| Factory functions pass `current_user` to PostgreSQL repos | ✅ All 9 |
| PostgreSQL repos have `_is_admin()`, `_can_access_*()` helpers | ✅ All 9 |
| Routes cleaned (removed `db: AsyncSession`, `can_access_*` checks) | ✅ 12 files |
| Documentation updated (P10, DB_ABSTRACTION, OFFLINE_ONLINE) | ✅ Complete |
| Tests fixed (test_mocked_full.py patches) | ✅ 189/190 passing |

### Route Files Cleaned

```
files.py         14→0 calls
folders.py        8→0 calls
platforms.py     11→3 calls (admin routes remain)
projects.py       9→3 calls (admin routes remain)
rows.py           3→0 calls
sync.py           6→1 calls (factory pattern)
pretranslate.py   1→0 calls
trash.py          2→0 calls
tm_crud.py        1→0 calls
tm_indexes.py     4→0 calls
tm_linking.py     3→0 calls
tm_search.py      3→0 calls
```

### Factory Pattern (Final)

```python
def get_file_repository(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
) -> FileRepository:
    if _is_offline_mode(request):
        return SQLiteFileRepository()  # No perms (single user)
    else:
        return PostgreSQLFileRepository(db, current_user)  # Perms baked in!
```

### Documentation Updated

| Doc | What Was Added |
|-----|----------------|
| `P10_DB_ABSTRACTION.md` | Factory Functions section, Mode Detection, all 9 factories |
| `DB_ABSTRACTION_LAYER.md` | P10 Permissions section, Full Route Migration Status |
| `OFFLINE_ONLINE_MODE.md` | Auto-Sync on File Open section (top of doc) |

### Commits

| Commit | Description |
|--------|-------------|
| `beddaff` | Feat: P10 DB Abstraction Layer - 100% COMPLETE (65→7 direct DB calls) |
| `14700b7` | Chore: Add QACompilerNEW project + update QA Excel files |

---

## SESSION 40 COMPLETE ✅

### Docs Reorganization Complete ✅

Reorganized 179 docs into clean structure:

```
docs/
├── INDEX.md              ← Navigation hub (NEW)
├── architecture/         ← System design (6 docs)
├── protocols/            ← Claude protocols (GDP)
├── current/              ← Active work (2 docs)
├── reference/            ← enterprise, cicd, security
├── guides/               ← tools, getting-started
└── archive/              ← 134 old docs
```

### Granular Debug Protocol (GDP) ✅

New debugging methodology documented after TM paste bug investigation.

**Key insight:** Bugs hide in gaps between what you THINK code does vs what it ACTUALLY does.

**5 Logging Levels:**
1. Entry Point - Function called?
2. Decision Point - Which branch?
3. Variable State - Actual values?
4. Pre-Action - What's about to happen?
5. Post-Action - What happened?

**Location:** `docs/protocols/GRANULAR_DEBUG_PROTOCOL.md`

### TM Paste Bug Root Cause Found ✅

**Problem:** TM paste went to "unassigned" instead of Offline Storage project.

**Root Cause:** Frontend sent JSON body, backend expected query parameters:
```javascript
// WRONG
fetch(url, { body: JSON.stringify({project_id: 66}) })

// RIGHT
fetch(`${url}?project_id=66`, { method: 'PATCH' })
```

**Fixed in:** `TMExplorerGrid.svelte`

### DB Abstraction Layer Vision

User requirement: **Full offline TM support** - TM assignment must work in SQLite too.

**Architecture:**
```
┌─────────────────────────────────────┐
│      DB Abstraction Interface       │
│   tm.assign(), tm.search(), etc.    │
└──────────────┬──────────────────────┘
               │
       ┌───────┴───────┐
       │               │
┌──────▼─────┐  ┌──────▼─────┐
│ PostgreSQL │  │   SQLite   │
│  Adapter   │  │   Adapter  │
└────────────┘  └────────────┘
```

**Docs Updated:**
- `architecture/ARCHITECTURE_SUMMARY.md` - Added DB abstraction design
- `architecture/OFFLINE_ONLINE_MODE.md` - Added full offline TM support
- `architecture/TM_HIERARCHY_PLAN.md` - Added SQLite TM schema

### Docs Review Progress

| Doc | Status |
|-----|--------|
| ARCHITECTURE_SUMMARY.md | ✅ Updated with DB abstraction |
| OFFLINE_ONLINE_MODE.md | ✅ Updated with full offline TM |
| TM_HIERARCHY_PLAN.md | ✅ Updated with SQLite support |
| ISSUES_TO_FIX.md | ✅ Cleaned up |
| SESSION_CONTEXT.md | ✅ Updating now |
| reference/cicd/* | 🔲 Pending |
| guides/* | 🔲 Pending |

---

## SESSION 39 COMPLETE

### Bugs Fixed

| Bug | Description | Status |
|-----|-------------|--------|
| **BUG-040** | `logger.warn is not a function` breaking sync + clipboard | ✅ Fixed |
| **BUG-041** | Sync Dashboard showing deleted files | ✅ Fixed |

### BUG-040: logger.warn Not a Function

**Problem:** Frontend code used `logger.warn()` but the logger API only has `logger.warning()`. This caused "logger.warn is not a function" errors that broke:
- Continuous sync
- TM clipboard operations
- Various error handlers

**Fix Applied:**
Changed all `logger.warn()` → `logger.warning()` in 4 files:
- `sync.js` (3 occurrences)
- `TaskManager.svelte` (1 occurrence)
- `TMDataGrid.svelte` (3 occurrences)
- `LDM.svelte` (1 occurrence)

### BUG-041: Stale Sync Subscriptions

**Problem:** Sync Dashboard showed files that were deleted. When files are deleted, their sync subscriptions weren't cleaned up, causing stale entries in the dashboard.

**Fix Applied:**

1. **Cleanup on Delete (files.py):**
   - Added subscription cleanup when files are deleted (PostgreSQL)
   - Added subscription cleanup when local files are deleted (SQLite)

2. **Auto-Cleanup on Fetch (sync.py):**
   - When fetching subscriptions, validate if files still exist
   - Automatically remove stale subscriptions for deleted files
   - Only return valid subscriptions to the UI

**Files Modified:**
- `server/tools/ldm/routes/files.py` - Lines 643-650, 1814-1819
- `server/tools/ldm/routes/sync.py` - Lines 200-225

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
| **UX-003** | TM move functionality (cut/copy/paste) | ✅ DONE |

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

### UX-003: TM Cut/Copy/Paste

**Problem:** Can't move TMs after creation - stuck in UNASSIGNED.

**Solution Implemented:**
- Added clipboard functionality to TMExplorerGrid.svelte
- Uses shared `clipboard.js` store (same as File Explorer)
- Full keyboard support: Ctrl+X (cut), Ctrl+C (copy), Ctrl+V (paste), Escape (clear)

**Features:**
| Feature | Description |
|---------|-------------|
| **Cut (Ctrl+X)** | Mark TMs for move, shows striped visual feedback |
| **Copy (Ctrl+C)** | Copy TMs (for duplicate - paste creates new) |
| **Paste (Ctrl+V)** | Move/copy TMs to current location |
| **Clipboard indicator** | Shows "X TMs cut/copied" with clear button |
| **Context menu** | Cut/Copy/Paste options in right-click menu |

**Paste Targets:**
- Home → Move to UNASSIGNED
- Platform → Assign to platform
- Project → Assign to project
- Folder → Assign to folder

**Files Modified:**
- `TMExplorerGrid.svelte` - Clipboard state, handlers, context menu, CSS
- `tests/tm_clipboard.spec.ts` - 3 tests (all passing)

**Backend:** Uses existing `PATCH /api/ldm/tm/{id}/assign` endpoint

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

**Builds:** Gitea 455, GitHub 456 | **Open Issues:** 0 | **Date:** 2026-01-16
**Tests:** 1000+ passing in BOTH CI systems - Repository Pattern verified
**Status:** P9 ✅, P10 ✅, **CI Verification ✅ COMPLETE (Both Systems)**

**Remotes Synced:**
- GitHub (origin): ✅ Build 456 passed
- Gitea: ✅ Build 455 passed

**What's Done:**
- All unit tests use Repository Pattern mocking (not DB mocking)
- 9 repository mock fixtures created
- GDP-P10 checkpoints added to BOTH CI workflows (Gitea + GitHub)
- Gitea Build 455 passed all tests (including Windows build)
- GitHub Build 456 passed all tests (17m14s, first try)
- Fixed missing import in tm_indexes.py (caught by Gitea CI)

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
| **P10** | **DB Abstraction Layer** | ✅ COMPLETE |
| P11 | TM Tree Folder Mirroring | TODO |
| P8 | Dashboard Overhaul | PLANNED |

### P9-TM: Full Offline TM Support ✅ COMPLETE

**Goal:** TM assignment works identically online and offline.

**Completed (Session 41):**
1. ✅ SQLite TM schema (`offline_tm_assignments`, `offline_tms`) - Already existed
2. ✅ DB abstraction layer (`TMRepository` interface) - `server/repositories/interfaces/tm_repository.py`
3. ✅ PostgreSQL adapter - `server/repositories/postgresql/tm_repo.py` (~400 lines)
4. ✅ SQLite adapter - `server/repositories/sqlite/tm_repo.py` (~280 lines)
5. ✅ Frontend uses abstraction - Token prefix `OFFLINE_MODE_` triggers SQLite adapter

**Architecture:**
```
server/repositories/
├── __init__.py                    # Exports TMRepository, AssignmentTarget, get_tm_repository
├── factory.py                     # Auto-selects PostgreSQL/SQLite based on auth token
├── interfaces/
│   └── tm_repository.py           # Abstract interface (15+ methods)
├── postgresql/
│   └── tm_repo.py                 # PostgreSQLTMRepository
└── sqlite/
    └── tm_repo.py                 # SQLiteTMRepository
```

**Commits:**
- `789c04b` - P9-ARCH: Implement Repository Pattern for TM database abstraction
- `4f60acb` - P9-ARCH: Fix SQLite schema for local-only TM entries

**Docs Updated:** ARCHITECTURE_SUMMARY.md, OFFLINE_ONLINE_MODE.md, TM_HIERARCHY_PLAN.md

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

*Session 43 | Build 454 | P10 COMPLETE + All Tests Using Repository Pattern*
