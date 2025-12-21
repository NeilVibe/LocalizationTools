# Issues To Fix

**Last Updated:** 2025-12-21 10:30 | **Build:** 313 | **Previous:** 312

---

## Quick Summary

| Status | Count |
|--------|-------|
| **OPEN** | 0 |
| **FIXED (This Session)** | 15 |

---

## FIXED - BUILD 313

### UI-047: TM Sidebar Shows "Pending" When Status is "Ready"

- **Problem:** TM list in sidebar always showed "Pending" tag even when TM was fully synced
- **Root Cause:** `FileExplorer.svelte` checked `tm.is_indexed` instead of `tm.status === 'ready'`
- **Investigation:**
  - Database query: ALL TMs have `status = "ready"` ✓
  - Server log: Shows `status=ready` after sync ✓
  - API response: Returns `"status": "ready"` ✓
  - Frontend bug: Wrong field being checked
- **Fix:** Changed condition from `tm.is_indexed` to `tm.status === 'ready'`
- **File:** `FileExplorer.svelte` (lines 755-759)
- **Status:** FIXED

---

## VERIFIED - BUILD 312

### UI-045: PresenceBar Tooltip Shows Username (VERIFIED)

- **Problem:** Hovering over "X viewing" showed "?" instead of the current user's name
- **Fix:** Added `isValidUsername()` function to filter out invalid names ("?", "Unknown", "LOCAL"), robust fallback chain
- **File:** `PresenceBar.svelte`
- **Verification:** CDP query confirmed `title="neil"` - tooltip shows username
- **Screenshot:** build312_VERIFIED.png (2025-12-21 08:40)
- **Status:** VERIFIED

---

## MINOR - FUTURE (Low Priority)

### UI-046: PresenceBar Cursor Shows "?" Instead of Normal Pointer

- **Problem:** When hovering over "1 viewing", the cursor shows a "?" (help cursor) instead of normal pointer
- **Root Cause:** CSS `cursor: help` style on `.presence-indicator`
- **Fix:** Change to `cursor: default` or `cursor: pointer`
- **File:** `PresenceBar.svelte` (CSS)
- **Priority:** Very Low - cosmetic only, tooltip works correctly
- **Status:** NOTED (not urgent)

---

## FIXED - BUILD 311 (VERIFIED)

### UI-044: Resizable Columns + Clear Separator

- **Problem:** Source/Target columns had no clear visual separation; couldn't resize columns like Excel
- **Fix:**
  - Added 2px visible border between source and target columns (`--cds-border-strong-01`)
  - Added draggable resize handle to adjust column widths (20%-80% range)
  - Header and cells use matching percentage-based widths via Svelte 5 `$state()`
  - Auto-adaptive layout using reactive percentage widths
- **Files:** `VirtualGrid.svelte`
- **Svelte 5 Features:**
  - `$state()` for sourceWidthPercent, isResizing state
  - Inline style bindings for reactive column widths
  - Mouse event handlers for drag-to-resize
- **Screenshot Verified:** 2025-12-21 00:45 (build311_coord.png)
- **Status:** VERIFIED

---

## FIXED - BUILD 310 (VERIFIED)

### UI-042: Simplified PresenceBar (Remove Avatars)

- **Problem:** Avatar icons (colored circles with initials) cluttering presence indicator
- **Fix:** Removed avatars, kept only "X viewing" text with hover tooltip showing viewer names
- **File:** `PresenceBar.svelte`
- **Status:** VERIFIED

---

### UI-043: Fix Empty 3rd Column + Tooltip

- **Problem:** Empty dark space showing as 3rd column; hover tooltip showing "?"
- **Fix:**
  - Made Source/Target columns flex to fill available width
  - Fixed tooltip to show current user when viewer list not available
- **Files:** `VirtualGrid.svelte`, `PresenceBar.svelte`
- **Status:** VERIFIED

---

## FIXED - BUILD 308

### UI-035: Removed Pagination from TMDataGrid

- **Problem:** "Items per page 100" dropdown and "1 of 1" pagination
- **Fix:** Replaced with infinite scroll (like TMViewer)
- **File:** `TMDataGrid.svelte`
- **Status:** FIXED

---

### UI-036: Removed Confirm Button from TMDataGrid

- **Problem:** Confirm/Unconfirm button on each TM entry row
- **Fix:** Removed button and toggleConfirm function
- **File:** `TMDataGrid.svelte`
- **Status:** FIXED

---

### UI-037: Removed "No email" Text

- **Problem:** User menu showed "No email" when user had no email set
- **Fix:** Only show email line if email exists
- **File:** `+layout.svelte`
- **Status:** FIXED

---

### UI-038: Added User Profile Modal

- **Problem:** Clicking username should open profile modal with user details
- **Fix:** Created UserProfileModal.svelte, shows name/team/department/language/role
- **Files:** `UserProfileModal.svelte`, `+layout.svelte`
- **Status:** FIXED

---

### UI-039: Fixed Third Column Logic

- **Problem:** Extra columns showing when they shouldn't
- **Fix:** Removed TM Results column - only StringID (left) and Reference (right) available as third column options
- **File:** `VirtualGrid.svelte`
- **Default:** File viewer shows 2 columns only (Source, Target)
- **Status:** FIXED

---

### UI-040: Fixed PresenceBar Tooltip Trigger

- **Problem:** Empty "i" button/trigger next to viewer avatars
- **Fix:** Removed `triggerText=""` from Tooltip, use native title attribute instead
- **File:** `PresenceBar.svelte`
- **Status:** FIXED

---

### UI-041: Removed VirtualGrid Footer

- **Problem:** "Showing rows X-Y of Z" footer in file viewer
- **Fix:** Removed grid-footer div and CSS
- **File:** `VirtualGrid.svelte`
- **Status:** FIXED

---

### BUG-032: Fixed Auto-Sync

- **Problem:** Auto-sync after TM entry edit wasn't updating TM status
- **Fix:** Added `tm.status = "ready"` after successful sync
- **File:** `api.py` (_auto_sync_tm_indexes function)
- **Status:** FIXED

---

### BUG-033: Fixed Manual Sync

- **Problem:** Manual sync wasn't updating TM status to "ready"
- **Fix:** Added status update after sync_tm_indexes completes
- **File:** `api.py` (sync_tm_indexes endpoint)
- **Status:** FIXED

---

### BUG-034: Fixed Pending Status

- **Problem:** TMs stayed "pending" even after indexes were built/synced
- **Root Cause:** Status wasn't being updated after sync operations
- **Fix:** Both auto-sync and manual sync now update status to "ready"
- **File:** `api.py`
- **Status:** FIXED

---

## Column Configuration Summary

| Viewer | Default Columns | Optional Columns |
|--------|-----------------|------------------|
| **File Viewer** | Source, Target | StringID (left), Reference (right) |
| **TM Viewer** | Source, Target, Metadata | - |
| **TM Grid** | Source, Target, Actions | - |

---

## History

### Previous Builds (Verified)

| ID | Description | Build |
|----|-------------|-------|
| UI-025-028 | TMViewer infinite scroll, no pagination | 301-304 |
| BUG-028-031 | Model2Vec, upload, WebSocket, TM upload | 301-307 |
| UI-031-034 | Font size, bold, tooltips | 304-305 |
| FONT-001 | Multilingual font support | 304 |

---

*Updated 2025-12-20 19:00 | 0 OPEN issues, 10 fixed this session*
