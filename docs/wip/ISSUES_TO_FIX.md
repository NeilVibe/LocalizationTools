# Issues To Fix

**Purpose:** Track known bugs, UI issues, and improvements across LocaNext
**Last Updated:** 2025-12-16 12:30 KST

---

## Quick Summary

| Area | Open | Fixed/Implemented | Total |
|------|------|-------------------|-------|
| Svelte 5 Migration | 0 | 1 | 1 |
| LDM Connection | 0 | 3 | 3 |
| LDM UI/UX | 4 | 16 | 20 |
| LDM WebSocket | 0 | 2 | 2 |
| Installer | 0 | 2 | 2 |
| Navigation | 0 | 1 | 1 |
| Infrastructure | 0 | 6 | 6 |
| **Total** | **4** | **31** | **35** |

**Open Issues:** 4 (0 HIGH, 4 MEDIUM)

### Session 2025-12-16 (continued) Summary
- **FIXED:** CI test isolation - unit tests were dropping CI database tables
- **FIXED:** CI test bloat - Gitea runs ~273 tests in 5 min (not 1000+ in 23 min)
- **FIXED:** Connectivity tests included (`test_database_connectivity.py` - 26 tests)
- **BUILD 290:** Tests PASSED in 5m7s, but overall FAILED
- **CRITICAL:** 7 consecutive failures since Build 284 (Svelte 5 migration)
- **ISSUE:** Windows build step failing - runner may be down or Electron build broken
- **LAST PASSING:** Build 283 (22m48s)

### Session 2025-12-16 Summary (earlier)
- **FIXED:** BUG-011 - App stuck at "Connecting to LDM..." (Svelte 5 reactivity)
- **IMPLEMENTED:** BUG-007 - Auto-fallback to SQLite when PostgreSQL unreachable
- **IMPLEMENTED:** BUG-008 - Online/Offline indicator + "Go Online" button
- **ADDED:** CI tests:
  - `check_svelte_build.sh` - Catches Svelte 5 reactivity bugs
  - **PostgreSQL verification** - FAILS if server fell back to SQLite
  - `test_database_connectivity.py` - 26 new connectivity tests
- **PENDING:** BUG-009/010 (installer fixes ready, needs build)

---

## Open Issues

### PRIORITY 0 - ULTRA CRITICAL (App Broken)

#### BUG-011: Cannot Connect to Backend - App Stuck at "Connecting to LDM..."
- **Status:** [x] **FIXED** - ROOT CAUSE IDENTIFIED
- **Priority:** **PRIORITY 0 - ULTRA CRITICAL**
- **Reported:** 2025-12-16
- **Fixed:** 2025-12-16
- **Component:** LDM.svelte - Svelte 5 Reactivity Bug

**Problem:** App launches, shows login, user logs in, but then gets stuck at "Connecting to LDM..." forever. Cannot use the app at all.

**CDP Test Results:**
```
Loading state: { hasLoading: true, loadingText: 'loading Connecting to LDM...' }
LDM: { hasLDM: true, hasGrid: false, hasFileExplorer: false, projectCount: 0, fileCount: 0 }
```

**Root Cause: SVELTE 5 REACTIVITY BUG**

CDP investigation showed:
1. `onMount` runs successfully
2. `checkHealth()` API call succeeds (200 OK)
3. `fetchConnectionStatus()` API call succeeds (200 OK)
4. `loading = false` assignment executes
5. **BUT UI DOESN'T UPDATE** - loading stays true!

The problem: **Mixed Svelte 4 and Svelte 5 syntax**

```javascript
// BROKEN CODE (Svelte 4 style in Svelte 5 runes mode)
let loading = true;  // NOT reactive!
let connectionStatus = $state({...});  // This makes file use runes mode

// When ANY $state() is used, ALL let declarations become non-reactive
// loading = false does nothing to the UI
```

**Fix Applied:**

Convert all state variables to `$state()` runes:

```javascript
// FIXED CODE (Svelte 5 runes)
let healthStatus = $state(null);
let loading = $state(true);  // NOW REACTIVE!
let error = $state(null);
let projects = $state([]);
let selectedProjectId = $state(null);
let selectedFileId = $state(null);
let selectedFileName = $state("");
let selectedTMId = $state(null);
let selectedTMName = $state("");
let viewMode = $state('file');
let showTMManager = $state(false);
let showPreferences = $state(false);
let showServerStatus = $state(false);
let fileExplorer = $state(null);
let virtualGrid = $state(null);
```

**Files Changed:** `locaNext/src/lib/components/apps/LDM.svelte`

**Related Task:** P35_SVELTE5_MIGRATION.md - Full codebase needs migration to Svelte 5 runes

**Verification:** Needs rebuild and test

---

### CRITICAL - Connection/Offline Mode

#### BUG-007: LDM Not Connecting to Central Server - No Offline Fallback
- **Status:** [x] **IMPLEMENTED** - Needs Production Testing
- **Priority:** CRITICAL
- **Reported:** 2025-12-16
- **Implemented:** 2025-12-16
- **Component:** LDM Connection, Database Mode

**Problem:** When LDM cannot connect to central PostgreSQL server, there is no automatic fallback to offline mode. App just fails to connect.

**Implementation (Already Done):**
- `DATABASE_MODE=auto` (default) - tries PostgreSQL, falls back to SQLite
- `POSTGRES_CONNECT_TIMEOUT=3` seconds (configurable)
- `check_postgresql_reachable()` - quick socket check with timeout
- `test_postgresql_connection()` - full connection test
- Auto-fallback logic in `server/database/db_setup.py:375-393`

**Files:**
- `server/config.py:133` - DATABASE_MODE default
- `server/config.py:162` - POSTGRES_CONNECT_TIMEOUT
- `server/database/db_setup.py:29-51` - reachability check
- `server/database/db_setup.py:53-75` - connection test
- `server/database/db_setup.py:375-393` - auto-fallback logic

**Tests Added:** `tests/integration/test_database_connectivity.py` (26 tests)

**Next:** Test in production environment (Windows app without PostgreSQL)

---

#### BUG-008: No Offline/Online Mode Indicator or Toggle
- **Status:** [x] **IMPLEMENTED** - Needs Production Testing
- **Priority:** CRITICAL
- **Reported:** 2025-12-16
- **Implemented:** 2025-12-16
- **Component:** LDM UI, Settings

**Problem:** No visual indicator showing current connection mode (online/offline). No button to manually switch modes.

**Implementation (Already Done):**
- Online indicator: Green tag + Cloud icon (`LDM.svelte:604-608`)
- Offline indicator: Outline tag + CloudOffline icon (`LDM.svelte:609-613`)
- "Go Online" button: Appears when offline (`LDM.svelte:614-627`)
- `/api/go-online` endpoint: Checks PostgreSQL and attempts reconnect (`server/main.py:281`)
- `/api/status` endpoint: Reports connection mode (`server/main.py:259`)

**Files:**
- `locaNext/src/lib/components/apps/LDM.svelte:604-630` - UI indicator
- `server/main.py:259-278` - /api/status endpoint
- `server/main.py:281-320` - /api/go-online endpoint

**Tests Added:** `tests/integration/test_database_connectivity.py` (26 tests)

---

### HIGH - Installer Issues

#### BUG-009: NSIS Installer Shows No Details During Install
- **Status:** [x] **FIX IN CODE** - Will be included in next build
- **Priority:** HIGH
- **Reported:** 2025-12-16
- **Fixed:** 2025-12-15
- **Component:** installer/nsis-includes/installer-ui.nsh

**Problem:** Installer shows green progress bar but empty white details box. No text showing what's being extracted.

**Fix Applied:** Added `SetDetailsPrint both` and more DetailPrint messages.

**Verification:** Next build will include this fix.

---

#### BUG-010: First-Run Setup Window Not Closing on Completion
- **Status:** [x] **FIX IN CODE** - Will be included in next build
- **Priority:** HIGH
- **Reported:** 2025-12-16
- **Fixed:** 2025-12-15
- **Component:** locaNext/electron/first-run-setup.js

**Problem:** After first-run setup completes successfully, the setup window stays open instead of closing.

**Root Cause:** Window created with `closable: false`, but `setClosable(true)` not called before `close()`.

**Fix Applied:** Added `setupWindow.setClosable(true)` before close.

**Verification:** Next build will include this fix.

---

### MEDIUM - UI/UX Improvements

#### UI-001: Remove Light/Dark Mode Toggle
- **Status:** [ ] Open
- **Priority:** MEDIUM
- **Reported:** 2025-12-16
- **Component:** Settings/Preferences

**Problem:** Light/dark mode toggle is unnecessary. App should be dark mode only.

**Action:** Remove toggle, keep dark mode as default, remove light mode CSS.

---

#### UI-002: Preferences Menu Too Cluttered
- **Status:** [ ] Open
- **Priority:** MEDIUM
- **Reported:** 2025-12-16
- **Component:** Settings/Preferences

**Problem:** All settings crammed into one menu. Needs better organization.

**Expected:**
- Separate menus for: LDM viewing, TM settings, General
- Compartmentalized modal design
- Minimal options in main Preferences

---

#### UI-003: TM Activation Should Be Via Click/Modal Not Settings
- **Status:** [ ] Open
- **Priority:** MEDIUM
- **Reported:** 2025-12-16
- **Component:** TM Manager

**Problem:** Activating TMs requires going to settings. Should be direct interaction.

**Expected:**
- Click on TM opens modal (like LDM viewer)
- Modal shows: Read, Edit, Erase options
- Activate/Deactivate buttons at top
- Remove TM activation from Preferences

---

#### UI-004: Remove "Show TM Results in Grid" Option
- **Status:** [ ] Open
- **Priority:** MEDIUM
- **Reported:** 2025-12-16
- **Component:** LDM Grid, Preferences

**Problem:** TM results shown in grid is not useful. TM results should only appear in Edit Modal.

**Action:** Remove option from preferences, remove TM column from grid.

---

## Fixed Issues (2025-12-15 Session)

### BUG-006: Embedding Model Download Fails in First-Run Setup
- **Status:** ✅ Fixed
- **Priority:** CRITICAL
- **Reported:** 2025-12-15
- **Fixed:** 2025-12-15
- **Component:** First-run setup, download_model.py, health-check.js, repair.js

**Problem:** LocaNext.exe fails at "AI MODEL" download during first-run setup. The download script was downloading deprecated KR-SBERT model to wrong path instead of the current QWEN model.

**Root Cause:**
- `tools/download_model.py` was downloading `snunlp/KR-SBERT-V40K-klueNLI-augSTS` to `models/kr-sbert/`
- All code expects `Qwen/Qwen3-Embedding-0.6B` at `models/qwen-embedding/` (P20 migration completed 2025-12-09)
- The script was never updated after P20 model migration

**Investigation:**
- `server/tools/xlstransfer/config.py` expects `models/qwen-embedding`
- `server/tools/ldm/tm_indexer.py` uses `Qwen/Qwen3-Embedding-0.6B`
- `scripts/download_bert_model.py` correctly downloads QWEN (but isn't used in first-run)
- P20_MODEL_MIGRATION.md documents the completed migration

**Fix Applied:**
1. Rewrote `tools/download_model.py` to download QWEN model:
   - Model: `Qwen/Qwen3-Embedding-0.6B`
   - Target: `models/qwen-embedding/`
   - Uses sentence_transformers for proper download

2. Updated all path checks from `kr-sbert` to `qwen-embedding`:
   - `locaNext/electron/first-run-setup.js:406`
   - `locaNext/electron/health-check.js:166,206`
   - `locaNext/electron/repair.js:328`

3. Renamed "AI MODEL" to "Embedding Model" throughout:
   - `first-run-setup.js` (header comment, UI text)
   - `repair.js` (header comment, UI text)
   - `health-check.js` (comments)

**Files Changed:**
- `tools/download_model.py` (complete rewrite)
- `locaNext/electron/first-run-setup.js`
- `locaNext/electron/health-check.js`
- `locaNext/electron/repair.js`

**Verified by:** Code review - matches P20 migration spec

---

## Fixed Issues (2025-12-13 Session)

### BUG-005: Edit Modal Keyboard Shortcuts Not Working (P25)
- **Status:** ✅ Fixed
- **Priority:** HIGH
- **Reported:** 2025-12-13
- **Fixed:** 2025-12-13
- **Component:** VirtualGrid.svelte (`openEditModal`)

**Problem:** In the Cell Edit Modal, pressing `Ctrl+S` (Confirm/Reviewed) or `Ctrl+T` (Translate Only) did nothing.

**Root Cause:** When modal opened, focus stayed on `BODY` instead of the textarea. The `on:keydown={handleEditKeydown}` handler on the modal div never received keyboard events because focus was elsewhere.

**Investigation (CDP tests):**
1. `test_edit_keyboard.js` - JavaScript events worked (events dispatched programmatically)
2. `test_edit_keyboard_real.js` - Real key simulation via `Input.dispatchKeyEvent` worked when textarea was focused
3. Test without focus - **FAILED** - events never reached handler

**Fix Applied:**
```javascript
// In openEditModal() - added after showEditModal = true:
await tick();
const textarea = document.querySelector('.target-textarea');
if (textarea) {
  textarea.focus();
}
```

**Files Changed:** `locaNext/src/lib/components/ldm/VirtualGrid.svelte:484-489`

**Verified by:** CDP test `test_bug005_fix.js` - auto-focus works, Ctrl+S closes modal

---

## Fixed Issues (2025-12-12 Session)

### BUG-002: Target Lock Blocking Editing (P25)
- **Status:** ✅ Fixed
- **Priority:** HIGH (Blocking!)
- **Reported:** 2025-12-12
- **Fixed:** 2025-12-12
- **Component:** WebSocket service (`websocket.js`)

**Problem:** Target column shows "locked" even when nobody is editing. User cannot edit rows.

**Root Cause:** WebSocket service's `on()` method only registered internal listeners but didn't subscribe to actual Socket.IO events from the server. Server sent `ldm_lock_granted` but frontend never received it, causing 3-second timeout.

**Fix Applied:**
```javascript
// In websocket.js on() method:
// Added Socket.IO listener registration when first subscriber registers
if (this.socket) {
  this.socket.on(event, (data) => {
    this.emit(event, data);
  });
}
```

**Files Changed:** `locaNext/src/lib/api/websocket.js`

**Verified by:** CDP autonomous test (test_edit_final.js)

---

### BUG-003: Upload File Tooltip Hidden (P25)
- **Status:** ✅ Fixed
- **Priority:** Medium
- **Reported:** 2025-12-12
- **Fixed:** 2025-12-12
- **Component:** LDM FileExplorer tooltip CSS

**Problem:** Hover tooltip on "Upload File" button appears UNDER the main LanguageData view.

**Root Cause:** Parent containers had `overflow: hidden` which created clipping contexts that cut off tooltips even with high z-index.

**Fix Applied:**
- Changed `overflow` from `hidden` to `visible` on LDM layout containers
- Added CSS rules to ensure tooltips escape parent containers
- Modified: `app.css`, `LDM.svelte`, `FileExplorer.svelte`

---

### BUG-004: Search Bar Requires Icon Click (P25)
- **Status:** ✅ Fixed
- **Priority:** Medium
- **Reported:** 2025-12-12
- **Fixed:** 2025-12-12
- **Component:** LDM VirtualGrid search

**Problem:** User has to click icon on far right to search - tedious. Carbon `ToolbarSearch` component requires clicking to expand.

**Fix Applied:**
- Replaced `ToolbarSearch` with Carbon's `Search` component
- Search bar is now always expanded and ready for input
- Type and search immediately, no icon click needed
- Modified: `VirtualGrid.svelte`

---

### BUG-001: Go to Row Not Useful (P25)
- **Status:** ✅ Fixed
- **Priority:** Low
- **Reported:** 2025-12-12
- **Fixed:** 2025-12-12
- **Component:** LDM VirtualGrid.svelte

**Problem:** "Go to Row" button doesn't serve a clear purpose.

**Fix Applied:** Removed the "Go to Row" button entirely. Users can scroll or use search to find specific rows.

**Files Changed:** `VirtualGrid.svelte` - removed button, NumberInput, related CSS and handlers

---

### ISSUE-011: Missing TM Upload Menu in UI
- **Status:** ✅ Fixed
- **Priority:** High
- **Reported:** 2025-12-11
- **Fixed:** 2025-12-12
- **Component:** LDM Frontend

**Problem:** No UI exists for uploading Translation Memory files.

**Fix Applied:**
- Created `TMManager.svelte` - Modal for listing/managing TMs (view, delete, build indexes)
- Created `TMUploadModal.svelte` - Modal for uploading new TM files (TXT, XML, XLSX)
- Added `POST /api/ldm/files/{id}/register-as-tm` endpoint for context menu
- Added `create_tm()` and `add_entries_bulk()` methods to TMManager backend
- Integrated into LDM toolbar with "TM Manager" button
- Added Server Status button to LDM toolbar

**Files Changed:**
- `locaNext/src/lib/components/ldm/TMManager.svelte` (NEW)
- `locaNext/src/lib/components/ldm/TMUploadModal.svelte` (NEW)
- `locaNext/src/lib/components/apps/LDM.svelte` (toolbar integration)
- `server/tools/ldm/api.py` (register-as-tm endpoint)
- `server/tools/ldm/tm_manager.py` (create_tm, add_entries_bulk)

---

### ISSUE-013: WebSocket ldm_lock_row Events Not Received by Server
- **Status:** ✅ Fixed
- **Priority:** Medium
- **Reported:** 2025-12-12
- **Fixed:** 2025-12-12
- **Component:** LDM WebSocket (`websocket.py`, `ldm.js`, `websocket.js`)

**Problem:** When user double-clicks a cell to edit, the frontend sends `ldm_lock_row` event but the server never receives it. Other events like `ldm_join_file` work correctly.

**Root Cause:** The `lockRow()` call in `VirtualGrid.svelte` was **commented out** as a temporary workaround during earlier debugging. The server-side WebSocket handlers were working correctly all along.

**Verification:** Python Socket.IO client test confirmed all events work:
- `ldm_join_file` → `file_joined` ✓
- `ldm_get_locks` → `locks` ✓
- `ldm_lock_row` → `lock_granted` ✓

**Fix Applied:** Re-enabled the `lockRow()` call in `openEditModal()`:
```javascript
// Request row lock for editing
if (fileId) {
  const granted = await lockRow(fileId, parseInt(row.id));
  if (!granted) {
    logger.warning("Could not acquire lock", { rowId: row.id });
    alert("Could not acquire lock. Row may be in use by another user.");
    return;
  }
}
```

**Files Changed:** `locaNext/src/lib/components/ldm/VirtualGrid.svelte:464-472`

**Multi-user Safety:** Row locking now active - prevents edit conflicts in collaborative editing

---

## Earlier Issues (2025-12-12)

### ISSUE-012: Backend Not Starting - App Broken
- **Status:** ✅ Fixed
- **Priority:** Critical
- **Fixed:** 2025-12-12
- **Component:** Infrastructure (PostgreSQL service)

**Problem:** User reported playground app not working. Backend was not responding.

**Root Cause:** PostgreSQL service was not running in WSL. The service was stopped/inactive.

**Symptoms:**
- `curl http://localhost:8888/health` → Connection refused
- Server process stuck in "Dl" state (disk sleep)
- App couldn't connect to backend

**Fix Applied:**
```bash
sudo service postgresql start
```

**Prevention:** PostgreSQL service should auto-start. Consider adding to startup:
```bash
sudo systemctl enable postgresql
```

**Note:** Windows app also has a bundled backend that uses SQLite. This is a separate issue - the bundled backend should use PostgreSQL too, but for now, WSL backend must be running for the app to work properly.

---

## Recently Fixed (2025-12-11 Session 2)

### ISSUE-010: LDM File Upload Not Working
- **Status:** [x] Fixed (Cannot Reproduce)
- **Priority:** Critical
- **Fixed:** 2025-12-11
- **Component:** LDM FileExplorer.svelte / Backend API

**Problem:** User reported files could not be uploaded to LDM.

**Investigation Results:**
- DEV mode (API only): ✅ PASSED - 4 rows uploaded
- EXE mode (CDP via PowerShell): ✅ PASSED - 4 rows uploaded
- fullSequence test: ✅ PASSED - create, upload, select, edit all working

**Root Cause:** Cannot reproduce. Likely causes were:
1. Old build deployed to Windows playground
2. Server not running or database connection issue
3. PgBouncer misconfiguration (was on wrong port)

**Fix Applied:** Updated `.env` to use direct PostgreSQL (port 5432) instead of PgBouncer (6433)

**Verification:** CDP tests pass - full workflow working

---

### ISSUE-007: Project List Not Auto-Refreshing on Startup
- **Status:** [x] Fixed
- **Priority:** High
- **Fixed:** 2025-12-11
- **Component:** LDM FileExplorer.svelte

**Problem:** When LDM loads, the project list doesn't load automatically.

**Root Cause:** Missing `onMount` in FileExplorer.svelte. Parent tried to call `loadProjects()` before binding was ready.

**Fix Applied:**
- Added `onMount` in FileExplorer.svelte to auto-call `loadProjects()`
- FileExplorer now loads projects independently on mount
- Removed redundant call from parent LDM.svelte

**Verification:** CDP test confirmed 3 projects loaded automatically on startup

---

### ISSUE-008: File Click Does Nothing - Cannot View Content
- **Status:** [x] Fixed
- **Priority:** Critical
- **Fixed:** 2025-12-11 (Session 3 - CDP Verified)
- **Component:** LDM FileExplorer.svelte

**Problem:** Clicking on a file in the TreeView did nothing. Grid remained blank with "Select a file" placeholder.

**Root Cause:** `handleNodeSelect()` expected wrong event format from Carbon TreeView:
- **Expected:** `event.detail.data.type` (custom format)
- **Actual:** Carbon passes `{id: "file-1", text: "name.txt", leaf: true}`

**Error:** `TypeError: Cannot read properties of undefined (reading 'type')`

**Fix Applied:** Parse the node ID string which was formatted as `"{type}-{id}"`:
```javascript
// Parse our custom ID format: "file-{id}" or "folder-{id}"
const idParts = node.id.split('-');
const nodeType = idParts[0];  // 'file' or 'folder'
const nodeId = parseInt(idParts[1], 10);
```

**Verification:** CDP test confirmed:
- `Has content: true`
- `Cell count: 133`
- Korean text visible in grid

**Files Changed:** `FileExplorer.svelte:219-249`

---

### ISSUE-009: File Upload Still Not Working
- **Status:** [x] Fixed
- **Priority:** Critical
- **Fixed:** 2025-12-11
- **Component:** LDM FileExplorer.svelte

**Problem:** User reported upload still not working despite code fix.

**Root Cause:** Build wasn't deployed to Windows playground. User was running old version.

**Fix Applied:**
- Deployed fresh build to Windows playground
- Verified via CDP that upload works: 10 rows uploaded successfully

**Verification:** CDP test confirmed "TEST: File uploaded - 10 rows"

---

## Fixed Issues (2025-12-11)

### LDM - UI/UX Issues

#### ISSUE-001: Button Hover Tooltip Z-Index
- **Status:** [x] Fixed
- **Priority:** High
- **Fixed:** 2025-12-11
- **Component:** Global CSS (app.css)

**Problem:** Tooltip/hover bubble info was overshadowed by main content area.

**Fix Applied:**
- Added z-index 10000+ to all tooltip-related CSS classes in `app.css`
- Classes: `.bx--tooltip`, `.bx--assistive-text`, `.bx--popover-content`, etc.

---

#### ISSUE-002: File Upload Not Working
- **Status:** [x] Fixed (Partial - UI only)
- **Priority:** Critical
- **Fixed:** 2025-12-11
- **Component:** LDM FileExplorer.svelte

**Problem:** File upload showed no progress or feedback.

**Initial Fix Applied (UI):**
- Added `uploadProgress` and `uploadStatus` state variables
- Progress bar shows during upload (0-100%)
- Success/error notifications after upload
- Auto-close modal on success

**Root Cause Found:** See ISSUE-006 below.

---

#### ISSUE-006: FileUploader Event Binding Bug (Root Cause of ISSUE-002)
- **Status:** [x] Fixed
- **Priority:** Critical
- **Fixed:** 2025-12-11
- **Component:** LDM FileExplorer.svelte

**Problem:** Files selected in FileUploader never actually uploaded. Backend API worked (tested via curl), but frontend failed silently.

**Root Cause:** Carbon FileUploader `on:add` event returns internal FileItem objects, NOT raw File objects. The `bind:files` binding gives actual `File` objects.

**Bad Code:**
```svelte
<FileUploader on:add={(e) => uploadFiles = [...uploadFiles, ...e.detail]} />
```

**Fix Applied:**
```svelte
<FileUploader bind:files={uploadFiles} />
```

**Verification:** Backend upload works via curl - confirmed 4 rows uploaded successfully

---

#### ISSUE-003: Tasks Button Missing Icon
- **Status:** [x] Fixed
- **Priority:** Medium
- **Fixed:** 2025-12-11
- **Component:** +layout.svelte

**Problem:** Tasks button had no icon unlike other nav buttons.

**Fix Applied:**
- Imported `TaskComplete` icon from carbon-icons-svelte
- Changed from `HeaderNavItem` to custom button with icon
- Added matching CSS styling

---

#### ISSUE-004: Tasks Button Hover Cursor
- **Status:** [x] Fixed
- **Priority:** Low
- **Fixed:** 2025-12-11
- **Component:** +layout.svelte

**Problem:** Cursor didn't change to pointer on hover.

**Fix Applied:**
- Added `.tasks-button` CSS class with `cursor: pointer`
- Proper hover states matching Carbon header styling

---

#### ISSUE-005: LDM Default App Routing
- **Status:** [x] Fixed
- **Priority:** Critical
- **Fixed:** 2025-12-11

**Problem:** LDM didn't show as default app on startup.

**Root Cause:** In Electron file:// mode, +error.svelte acts as main page.

**Fix Applied:**
- Added LDM import and default case to `src/routes/+error.svelte`
- Documented in `docs/troubleshooting/ELECTRON_TROUBLESHOOTING.md`

---

## Fixed Issues Table

| ID | Description | Fixed Date | Files Changed |
|----|-------------|------------|---------------|
| ISSUE-001 | Tooltip z-index | 2025-12-11 | app.css |
| ISSUE-002 | File upload progress UI | 2025-12-11 | FileExplorer.svelte |
| ISSUE-003 | Tasks button icon | 2025-12-11 | +layout.svelte |
| ISSUE-004 | Tasks button cursor | 2025-12-11 | +layout.svelte |
| ISSUE-005 | LDM default app | 2025-12-11 | +error.svelte, +page.svelte |
| ISSUE-006 | FileUploader bind:files | 2025-12-11 | FileExplorer.svelte |

---

## Issue History

### Session 2025-12-11
- **6 issues identified and fixed** in single session
- Root cause of ISSUE-002 discovered via backend API testing (curl verified upload works)
- Key lesson: Carbon FileUploader requires `bind:files` not `on:add` for raw File objects

---

## How to Add New Issues

1. Use next available ISSUE-XXX number
2. Include:
   - Status: [ ] Open or [x] Fixed
   - Priority: Critical/High/Medium/Low
   - Reported date
   - Component affected
   - Clear problem description
   - Expected behavior
   - Suggested fix location

---

## Categories

- **LDM UI** - LanguageData Manager interface issues
- **Navigation** - App routing, menu issues
- **General** - Cross-app issues
- **Performance** - Speed/memory issues
- **Backend** - Server/API issues

---

*All issues from 2025-12-11 session have been resolved.*
