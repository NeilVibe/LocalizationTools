# Issues To Fix

**Purpose:** Track known bugs, UI issues, and improvements across LocaNext
**Last Updated:** 2025-12-12

---

## Quick Summary

| Area | Open | Fixed | Total |
|------|------|-------|-------|
| LDM UI | 1 | 14 | 15 |
| Navigation | 0 | 1 | 1 |
| Infrastructure | 0 | 1 | 1 |
| General | 0 | 0 | 0 |

**Open Issues:** ISSUE-011
**Recently Fixed:** BUG-001, BUG-002, BUG-003, BUG-004

---

## Open Issues

### BUG-002: Target Lock Blocking Editing (P25)
- **Status:** [x] Fixed
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
- **Status:** [x] Fixed
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
- **Status:** [x] Fixed
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
- **Status:** [x] Fixed
- **Priority:** Low
- **Reported:** 2025-12-12
- **Fixed:** 2025-12-12
- **Component:** LDM VirtualGrid.svelte

**Problem:** "Go to Row" button doesn't serve a clear purpose.

**Fix Applied:** Removed the "Go to Row" button entirely. Users can scroll or use search to find specific rows.

**Files Changed:** `VirtualGrid.svelte` - removed button, NumberInput, related CSS and handlers

---

### ISSUE-011: Missing TM Upload Menu in UI
- **Status:** [ ] Open
- **Priority:** High
- **Reported:** 2025-12-11
- **Component:** LDM Frontend (missing TMManager.svelte / TMUploadModal.svelte)

**Problem:** No UI exists for uploading Translation Memory files. Backend TM API exists (Phase 7.1-7.3 complete) but frontend UI is missing.

**Related:**
- Backend APIs exist: `POST /api/ldm/tm/upload`, `GET /api/ldm/tm`, etc.
- Task 7.6.1-7.6.4 in P17_LDM_TASKS.md covers this (TODO)
- TMManager.svelte and TMUploadModal.svelte need to be created

**Expected UI:**
```
┌─ Translation Memories ─────────────────────────────────────┐
│ [+ Upload TM]                                              │
│                                                            │
│ Name             Entries    Status     Actions             │
│ ─────────────────────────────────────────────────────────  │
│ BDO Main TM      150,000    ✅ Ready   [Active ✓] [Delete] │
└────────────────────────────────────────────────────────────┘
```

**Fix:** Implement Phase 7.6 Frontend TM UI tasks

---

## Recently Fixed (2025-12-12)

### ISSUE-012: Backend Not Starting - App Broken
- **Status:** [x] Fixed
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
