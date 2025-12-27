# Issues To Fix

**Last Updated:** 2025-12-27 13:00 | **Build:** 396+ | **Open:** 15

> **STATUS:** Build 396 verified working. UI-051, UI-052, UI-053, UI-054, UI-056 FIXED. UI-055 and UI-057 fixed in this session.

---

## Quick Summary

| Status | Count |
|--------|-------|
| **FIXED (This Session)** | 7 |
| **CRITICAL (Blocking)** | 0 |
| **HIGH (Major UX)** | 6 |
| **MEDIUM (UX Issues)** | 7 |
| **LOW (Cosmetic)** | 4 |

---

## FIXED - Build 396+ (Verified Working)

### UI-051: Edit Modal Softlock - Cannot Close ✅ FIXED
- **Fixed in:** Build 396
- **Solution:** Custom modal with proper close button (`onclick={closeEditModal}`)
- **Verified:** CDP test confirms modal closes

### UI-052: TM Suggestions Infinite Loading ✅ FIXED
- **Fixed in:** Build 396
- **Solution:** Fixed `/api/ldm/tm/suggest` endpoint routing order
- **Verified:** TM suggestions load correctly

### UI-053: Virtual Scrolling Completely Broken ✅ FIXED
- **Fixed in:** Build 396
- **Solution:** CSS `height: 0` + `overflow: hidden` + flexbox constraints
- **Verified:** Container 847px (was 480,000px), virtual scroll working

### UI-054: Cells Not Expanding ✅ FIXED
- **Fixed in:** Build 396
- **Solution:** `estimateRowHeight()` with variable heights
- **Verified:** Variable heights detected in test

### UI-055: Modal DOM Bloat ✅ FIXED
- **Fixed in:** Build 397 (this session)
- **Problem:** 22+ modals always in DOM (was 171 before)
- **Solution:** Wrapped ALL Carbon Modals with `{#if}` conditionals:
  - FileExplorer.svelte: 7 modals
  - TMManager.svelte: 5 modals
  - DataGrid.svelte: 1 modal
  - TMDataGrid.svelte: 1 modal
  - TMUploadModal.svelte: Added dispatch('close')
  - TMViewer.svelte: Added dispatch('close')
- **Impact:** Modals now only render when needed, reducing DOM bloat to 0

### UI-056: Source Text Not Selectable ✅ FIXED
- **Fixed in:** Build 396
- **Solution:** Added `user-select: text` to source cells
- **Verified:** CDP test confirms source is selectable

### UI-057: Hover Highlight Split Colors ✅ FIXED
- **Fixed in:** Build 397 (this session)
- **Problem:** Source and target cells had different hover colors
- **Solution:** Added `.cell.source:hover` CSS rule matching target
- **File:** VirtualGrid.svelte line 1621-1624

---

## HIGH - MAJOR UX ISSUES

### UI-058: Previous Fixes Not Applied (Build 395 Ineffective)
- **Status:** RESOLVED - Build 396 contains all fixes, verified working

### UI-059: Row Selection State Inconsistent
- **Reported:** 2025-12-27
- **Severity:** HIGH (UX)
- **Status:** OPEN
- **Problem:** Selected row state conflicts with hover state
- **File:** VirtualGrid.svelte CSS line 1540-1542

### UI-060: Click on Source Cell Opens Edit Modal
- **Reported:** 2025-12-27
- **Severity:** HIGH (Unexpected behavior)
- **Status:** OPEN
- **Problem:** Clicking source cell can trigger edit modal
- **Expected:** Source cell should be read-only
- **File:** VirtualGrid.svelte lines 947-959, 1157

### UI-061: Routing Error on Page Load
- **Reported:** 2025-12-27
- **Severity:** HIGH (Error)
- **Status:** OPEN
- **Problem:** Console error: `Error: Not found: /C:/NEIL_PROJECTS.../index.html`
- **Root Cause:** SvelteKit router trying to resolve file path as route

### UI-062: Failed Network Request (version.json)
- **Reported:** 2025-12-27
- **Severity:** HIGH (Missing resource)
- **Status:** OPEN
- **Problem:** `net::ERR_FILE_NOT_FOUND` for `file:///C:/_app/version.json`
- **Root Cause:** App looking for version.json in wrong path

### UI-074: Missing API Endpoint /api/ldm/files
- **Reported:** 2025-12-27
- **Severity:** HIGH (API error)
- **Status:** OPEN
- **Problem:** Frontend calls `/api/ldm/files?limit=100` which doesn't exist
- **Fix Required:** Create endpoint or update ReferenceSettingsModal

### UI-075: Console Error Objects Being Logged
- **Reported:** 2025-12-27
- **Severity:** HIGH (Hidden errors)
- **Status:** OPEN
- **Problem:** Console shows `[ERROR] Console Error Object` without details

---

## MEDIUM - UX ISSUES

### UI-063: CSS Text Overflow Issues (20+ Elements)
- **Status:** OPEN
- **Problem:** 20+ elements have text overflow without ellipsis

### UI-064: Target Cell Status Colors Conflict with Hover
- **Status:** OPEN
- **Problem:** Status colors conflict with hover states

### UI-065: Edit Icon Visibility Inconsistent
- **Status:** OPEN
- **Problem:** Edit icon only visible on hover, not on selected cell

### UI-066: Placeholder Rows Have Wrong Column Count
- **Status:** OPEN
- **Problem:** Placeholder rows show single shimmer instead of matching columns

### UI-067: Filter Dropdown Styling Inconsistent
- **Status:** OPEN
- **Problem:** Filter dropdown height doesn't match search input

### UI-068: Resize Handle Not Visible Until Hover
- **Status:** OPEN
- **Problem:** Column resize handle invisible until hover

### UI-069: QA Icon Position Conflicts with Edit Icon
- **Status:** OPEN
- **Problem:** QA warning icon and edit icon can overlap

---

## LOW - COSMETIC ISSUES

### UI-070: Empty Divs in DOM (9 Found)
- **Status:** OPEN
- **Impact:** Minor DOM bloat

### UI-071: Reference Column "No match" Styling
- **Status:** OPEN
- **Problem:** "No match" text could be clearer

### UI-072: TM Empty Message Styling
- **Status:** OPEN
- **Problem:** "No similar translations found" styling

### UI-073: Shortcut Bar Takes Vertical Space
- **Status:** OPEN
- **Problem:** Shortcut hints bar could be more compact

---

## FIX PRIORITY ORDER (Remaining)

1. **UI-074** - Missing /api/ldm/files endpoint (5x 404 errors)
2. **UI-059** - Row selection conflicts
3. **UI-060** - Source cell triggers edit
4. **UI-061** - Routing error
5. **UI-062** - version.json error

---

## FIXED PREVIOUSLY (Reference)

<details>
<summary>Previous Session Fixes (2025-12-26)</summary>

- PERF-003: Lazy Loading + Scroll Lag - FIXED + VERIFIED
- BUG-036: Duplicate Names - FIXED + VERIFIED
- BUG-037: QA Panel X Button - FIXED + VERIFIED
- PERF-001: O(n^2) VirtualGrid bug - FIXED + VERIFIED

</details>

---

*Updated 2025-12-27 13:00 | 7 Issues FIXED | 15 OPEN Issues*
