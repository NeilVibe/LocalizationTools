# Issues To Fix

**Last Updated:** 2025-12-28 09:45 | **Build:** 404+ | **Open:** 11

> **STATUS:** UI-076, UI-077, UI-080 FIXED! Search + Duplicate prevention working.

---

## Quick Summary

| Status | Count |
|--------|-------|
| **FIXED/CLOSED** | 13 |
| **CRITICAL (Blocking)** | 0 |
| **HIGH (Major UX)** | 4 |
| **MEDIUM (UX Issues)** | 8 |
| **LOW (Cosmetic)** | 4 |
| **Total Open** | 11 |

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

### UI-058: Previous Fixes Not Applied ✅ RESOLVED
- **Status:** RESOLVED - Build 396 contains all fixes, verified working

### UI-060: Click on Source Cell Opens Edit Modal ✅ NOT A BUG
- **Tested:** 2025-12-27 - Double-click on TARGET opens modal (correct)
- **Source cell:** Single/double click does NOT open modal (correct)

---

## CRITICAL - BLOCKING ISSUES

*No critical issues*

---

## FIXED - 2025-12-28

### UI-076: Search Bar Not Filtering Rows ✅ FIXED
- **Reported:** 2025-12-28
- **Fixed:** 2025-12-28
- **Severity:** CRITICAL (Core feature broken)
- **Status:** FIXED
- **Problem:** Typing in search bar didn't filter rows
- **Root Cause:** THREE compounding issues:
  1. TypeScript syntax in non-TS Svelte file caused silent compile error
  2. `bind:value` with `$state()` caused Svelte to reset input values
  3. Effect was resetting searchTerm to "" on every run (not just fileId change)
- **Fix:**
  1. Removed TypeScript casts from `<script>` block
  2. Changed to `oninput` handler instead of `bind:value`
  3. Added previous value tracking to fileId effect
- **Verified:** Playwright test: 10,000 rows -> 4 rows with search "5000"
- **File:** VirtualGrid.svelte lines 53-65, 1145-1154, 1245-1254

### UI-080: Search Results Show Empty Cells ✅ FIXED
- **Reported:** 2025-12-28
- **Fixed:** 2025-12-28
- **Severity:** HIGH (Search broken visually)
- **Status:** FIXED
- **Problem:** Search filtered correctly (count changed) but cells showed shimmer/empty
- **Root Cause:** Array indexing bug
  - API returns original `row_num` values (e.g., 4, 11 for "proue" search)
  - Frontend stored at `rows[row_num - 1]` (indices 3, 10)
  - Virtual scroll renders indices 0, 1, 2... which were EMPTY
- **Fix:** Use sequential indices for search results:
  ```javascript
  const index = isSearching ? pageIndex : (row.row_num - 1);
  ```
- **Verified:** Playwright test: "proue" search shows 2 rows with correct content
- **File:** VirtualGrid.svelte loadRows() and loadPage() functions

### UI-077: Duplicate Names Allowed (Files + Folders) ✅ FIXED
- **Reported:** 2025-12-28
- **Fixed:** 2025-12-28
- **Severity:** HIGH (Data integrity)
- **Status:** FIXED
- **Problem:** Duplicate names allowed for files AND folders in same project
- **Fix:** Added duplicate name validation in all three endpoints:
  1. `files.py`: Check for duplicate file name in same project + folder before upload
  2. `folders.py`: Check for duplicate folder name in same project + parent before create
  3. `projects.py`: Check for duplicate project name for user before create (returns 400 not 500)
- **Files modified:**
  - `server/tools/ldm/routes/files.py` - Line 163-181
  - `server/tools/ldm/routes/folders.py` - Line 59-76
  - `server/tools/ldm/routes/projects.py` - Line 43-55

### UI-078: Color Tags Not Rendering ✅ FIXED
- **Reported:** 2025-12-28
- **Fixed:** 2025-12-28
- **Severity:** MEDIUM (Feature incomplete)
- **Status:** FIXED
- **Problem:** test_10k.txt used wrong `{Color(#67d173)}` format
- **Solution:** Deleted synthetic data, using real `sample_language_data.txt` with correct `<PAColor0xff...>` format
- **Verified:** Playwright test found 23 colored spans, 21 gold, 0 raw tags visible

---

## MEDIUM - UX IMPROVEMENTS

### UI-079: Grid Lines Not Visible Enough
- **Reported:** 2025-12-28
- **Severity:** MEDIUM (Visual)
- **Status:** OPEN
- **Problem:** Cell separator lines are not visible - grid lacks definition
- **Current:** Cells blend together without clear borders
- **Desired:** Subtle but visible grid lines between cells
- **File:** VirtualGrid.svelte CSS for `.cell` borders

---

## HIGH - MAJOR UX ISSUES

### UI-059: Row Selection State Inconsistent
- **Reported:** 2025-12-27
- **Severity:** HIGH (UX)
- **Status:** OPEN
- **Problem:** Selected row state conflicts with hover state
- **File:** VirtualGrid.svelte CSS line 1540-1542

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
