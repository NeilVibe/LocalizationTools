# Issues History - Archive of Fixed Issues

**Purpose:** Archive of resolved issues from ISSUES_TO_FIX.md
**Created:** 2025-12-16

---

## Summary

| Period | Issues Fixed |
|--------|--------------|
| 2025-12-17 | 21 (BUG-013 to BUG-022, FEAT-001 to FEAT-003, TASK-001 to TASK-002, Lazy Import Fix) |
| 2025-12-16 | 8 (UI-001 to UI-004, BUG-011, BUG-012, BUG-007, BUG-008) |
| 2025-12-15 | 1 (BUG-006) |
| 2025-12-13 | 1 (BUG-005) |
| 2025-12-12 | 8 (BUG-001 to BUG-004, ISSUE-011 to ISSUE-013) |
| 2025-12-11 | 20 (ISSUE-001 to ISSUE-010, LDM UI fixes) |
| **Total** | **59** |

---

## 2025-12-17 Session (Build 298)

### BUG-020: memoQ-Style TM Entry Metadata
- **Fixed:** 2025-12-17
- **Solution:** Added 5 columns (updated_at, updated_by, confirmed_at, confirmed_by, is_confirmed), confirm workflow in TM Viewer
- **Files:** `models.py`, `tm_manager.py`, `api.py`, `TMViewer.svelte`

### FEAT-001: TM Metadata Column Enhancement
- **Fixed:** 2025-12-17
- **Solution:** Expanded from 3 to 7 metadata options in dropdown
- **Files:** `TMViewer.svelte`

### BUG-016: Global Toast Notifications
- **Fixed:** 2025-12-17
- **Solution:** Created toastStore.js + GlobalToast.svelte, added to +layout.svelte
- **Files:** `toastStore.js`, `GlobalToast.svelte`, `+layout.svelte`

### FEAT-002: TM Export
- **Fixed:** 2025-12-17
- **Solution:** Export to TEXT/Excel/TMX with column selection
- **Files:** `tm_manager.py`, `api.py`, `TMManager.svelte`

### FEAT-003: TM Viewer
- **Fixed:** 2025-12-17
- **Solution:** Paginated grid, sort, search, inline edit, confirm button
- **Files:** `TMViewer.svelte`, `tm_manager.py`, `api.py`

### TASK-001: TrackedOperation for All Long Processes
- **Fixed:** 2025-12-17
- **Solution:** Added TrackedOperation to all 22 long-running operations
- **Files:** `api.py`, `pretranslate.py`

### TASK-002: Full E2E Tests
- **Fixed:** 2025-12-17
- **Solution:** 20 TRUE E2E tests for all 3 engines
- **Files:** `true_e2e_standard.py`, `true_e2e_xls_transfer.py`, `true_e2e_kr_similar.py`

### BUG-022: Full Rebuild on Every Sync
- **Fixed:** 2025-12-17
- **Solution:** Use TMSyncManager.sync() for incremental updates
- **Files:** `pretranslate.py`

### BUG-013 to BUG-019: Pipeline Fixes
- **Fixed:** 2025-12-17
- **BUG-013:** XLS Transfer EmbeddingsManager missing → Created class
- **BUG-014:** No staleness check → Added indexed_at < updated_at
- **BUG-015:** No auto-update → Auto-rebuild when stale
- **BUG-017:** KR Similar wrong interface → Added load_tm(tm_id)
- **BUG-018:** KR Similar search_multi_line missing → Refactored to find_similar()
- **BUG-019:** KR Similar search_single missing → Refactored to find_similar()

### Lazy Import Fix
- **Fixed:** 2025-12-17
- **Problem:** Server startup hang (30s+) due to eager SentenceTransformer import
- **Solution:** TYPE_CHECKING + local imports in functions
- **Files:** `translation.py`, `process_operation.py`, `translate_file.py`

---

## 2025-12-16 Session

### BUG-012: Server Configuration UI - PostgreSQL Connection
- **Fixed:** 2025-12-16 | **Verified:** Build 294 + Playground
- **Problem:** No UI to configure PostgreSQL settings for central server
- **Solution:** Added Server Config modal + 3 API endpoints + user config file
- **Files:** `server/config.py`, `server/main.py`, `ServerConfigModal.svelte`, `ServerStatus.svelte`, `test_server_config.py`

### BUG-011: App Stuck at "Connecting to LDM..." - Svelte 5 Reactivity
- **Fixed:** 2025-12-16
- **Problem:** App loads but UI stuck on loading screen forever
- **Root Cause:** Mixed Svelte 4/5 syntax - `let loading = true` not reactive when `$state()` used elsewhere
- **Solution:** Convert all state to `$state()` runes in LDM.svelte

### BUG-007: No Offline Fallback When PostgreSQL Unreachable
- **Fixed:** 2025-12-16
- **Solution:** `DATABASE_MODE=auto` with 3-second timeout, auto-fallback to SQLite

### BUG-008: No Online/Offline Indicator
- **Fixed:** 2025-12-16
- **Solution:** Visual indicator in LDM toolbar + "Go Online" button + `/api/status` endpoint

### UI-001 to UI-004: Compartmentalized UI Fixes
- **Fixed:** 2025-12-16 | **Verified:** CDP Screenshots
- **UI-001:** Dark mode only - removed theme toggle
- **UI-002:** Split preferences into Grid Columns, Reference Settings, Display Settings modals
- **UI-003:** TM activation via Power icon in TMManager
- **UI-004:** Removed "TM Results" checkbox from grid columns

---

## 2025-12-15 Session

### BUG-006: Embedding Model Download Fails in First-Run Setup
- **Fixed:** 2025-12-15
- **Problem:** Download script used deprecated KR-SBERT instead of QWEN
- **Solution:** Rewrote `tools/download_model.py` for Qwen3-Embedding-0.6B

---

## 2025-12-13 Session

### BUG-005: Edit Modal Keyboard Shortcuts Not Working
- **Fixed:** 2025-12-13
- **Problem:** Ctrl+S and Ctrl+T did nothing in edit modal
- **Root Cause:** Focus stayed on BODY, not textarea
- **Solution:** Added auto-focus on textarea in `openEditModal()`

---

## 2025-12-12 Session

### BUG-002: Target Lock Blocking Editing
- **Fixed:** 2025-12-12
- **Problem:** Rows showed "locked" even when nobody editing
- **Root Cause:** WebSocket `on()` didn't register Socket.IO listeners
- **Solution:** Added Socket.IO event registration in websocket.js

### BUG-003: Upload File Tooltip Hidden
- **Fixed:** 2025-12-12
- **Problem:** Tooltip appeared under main content
- **Solution:** Changed overflow from hidden to visible on parent containers

### BUG-004: Search Bar Requires Icon Click
- **Fixed:** 2025-12-12
- **Solution:** Replaced ToolbarSearch with always-expanded Search component

### BUG-001: Go to Row Not Useful
- **Fixed:** 2025-12-12
- **Solution:** Removed button entirely

### ISSUE-011: Missing TM Upload Menu
- **Fixed:** 2025-12-12
- **Solution:** Created TMManager.svelte and TMUploadModal.svelte

### ISSUE-012: Backend Not Starting
- **Fixed:** 2025-12-12
- **Problem:** PostgreSQL service stopped
- **Solution:** `sudo service postgresql start`

### ISSUE-013: WebSocket ldm_lock_row Events Not Received
- **Fixed:** 2025-12-12
- **Root Cause:** `lockRow()` was commented out
- **Solution:** Re-enabled lockRow() in openEditModal()

---

## 2025-12-11 Sessions

### ISSUE-001 to ISSUE-006: LDM UI Foundation
- Tooltip z-index fixes
- File upload progress UI
- Tasks button icon
- FileUploader bind:files fix
- LDM default app routing

### ISSUE-007 to ISSUE-010: File Operations
- Project list auto-refresh on startup
- File click handling (Carbon TreeView event format)
- File upload deployment verification

---

*Archive of fixed issues. For open issues, see [ISSUES_TO_FIX.md](../wip/ISSUES_TO_FIX.md)*
