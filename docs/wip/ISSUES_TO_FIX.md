# Issues To Fix

**Last Updated:** 2025-12-29 | **Build:** 415 (SUCCESS) | **Open:** 4 (0 CRITICAL)

> ✅ TEST-001 FIXED in Build 415
> All tests pass. CI pipeline operational.

---

## Quick Summary

| Status | Count |
|--------|-------|
| **FIXED/CLOSED** | 24 |
| **NOT A BUG/BY DESIGN** | 3 |
| **CRITICAL (Blocking)** | 0 ✅ |
| **HIGH (Major UX)** | 0 |
| **MEDIUM (Low Priority)** | 2 |
| **LOW (Cosmetic)** | 2 |
| **Total Open** | 4 |

---

## CRITICAL - BLOCKING BUILDS

*No critical issues* ✅

### TEST-001: Async Transaction Conflicts ✅ FIXED

- **Reported:** 2025-12-28
- **Fixed:** 2025-12-28 (Build 415)
- **Severity:** CRITICAL (Was blocking CI builds)
- **Status:** FIXED

**Problem:** Tests failed with "A transaction is already begun on this Session" (NOT the misleading "Future attached to different loop" error).

**Actual Root Cause:** `db.begin()` calls inside endpoints conflicted with `get_async_db()` which already manages transactions (auto-commit/rollback pattern).

**Fix:**
- Removed redundant `db.begin()` calls from:
  - `logs_async.py` - `submit_logs` endpoint
  - `sessions_async.py` - `start_session`, `session_heartbeat`, `end_session` endpoints
- Added `_check_async_engine_loop()` in `dependencies.py` for test isolation

**Files modified:**
- `server/api/logs_async.py`
- `server/api/sessions_async.py`
- `server/utils/dependencies.py`

---

## Issue Analysis Protocol

**BEFORE fixing any issue, follow this checklist:**

1. **UNDERSTAND** - Read the issue description fully
2. **LOCATE** - Find where the problem occurs (frontend/backend/both)
3. **CHECK IF FIXED** - Search codebase for existing fix (grep for issue ID, related code)
4. **TEST CURRENT STATE** - Reproduce the issue or verify it's already fixed
5. **ASSESS** - Determine:
   - Is it actually a bug or expected behavior?
   - Is it already implemented but not documented?
   - What is the root cause?
   - What is the clean fix approach?
6. **PLAN** - Document what needs to be done
7. **IMPLEMENT** - Only after steps 1-6 are complete
8. **VERIFY** - Test the fix works
9. **DOCUMENT** - Update this file and SESSION_CONTEXT.md

**DO NOT** dive into code changes without completing steps 1-5 first!

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

### UI-077: Duplicate Names Allowed (Files + Folders + TM) ✅ FIXED
- **Reported:** 2025-12-28
- **Fixed:** 2025-12-28
- **Severity:** HIGH (Data integrity)
- **Status:** FIXED
- **Problem:** Duplicate names allowed for files, folders, projects, AND TMs
- **Fix:** Added duplicate name validation in ALL FOUR endpoints:
  1. `files.py`: Check for duplicate file name in same project + folder before upload
  2. `folders.py`: Check for duplicate folder name in same project + parent before create
  3. `projects.py`: Check for duplicate project name for user before create (returns 400 not 500)
  4. `tm_crud.py`: Check for duplicate TM name for user before upload
- **Files modified:**
  - `server/tools/ldm/routes/files.py` - Line 163-181
  - `server/tools/ldm/routes/folders.py` - Line 59-76
  - `server/tools/ldm/routes/projects.py` - Line 43-55
  - `server/tools/ldm/routes/tm_crud.py` - Line 55-68

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

### UI-079: Grid Lines Not Visible Enough ✅ FIXED
- **Reported:** 2025-12-28
- **Fixed:** 2025-12-28
- **Severity:** MEDIUM (Visual)
- **Status:** FIXED
- **Problem:** Cell separator lines were not visible - grid lacked definition
- **Fix:** Changed border color from `border-subtle-01` to `border-strong-01` (#525252)
  - `.cell` border-right: stronger vertical lines between columns
  - `.virtual-row` border-bottom: stronger horizontal row separators
- **File:** VirtualGrid.svelte lines 1726, 1757

---

## HIGH - MAJOR UX ISSUES

### UI-059: Row Selection State Inconsistent ✅ FIXED
- **Reported:** 2025-12-27
- **Fixed:** 2025-12-28
- **Severity:** HIGH (UX)
- **Status:** FIXED
- **Problem:** Selected row state conflicts with hover state
- **Fix:**
  - Added `!important` to selected background to take priority over hover
  - Added `box-shadow` for visual depth
  - Added `.selected:hover` rule for combined state
- **File:** VirtualGrid.svelte lines 1739-1752

### UI-061: Routing Error on Page Load ✅ NOT A BUG
- **Reported:** 2025-12-27
- **Assessed:** 2025-12-28
- **Severity:** LOW (Expected behavior)
- **Status:** NOT A BUG - Already handled
- **Problem:** Console error: `Error: Not found: /C:/NEIL_PROJECTS.../index.html`
- **Root Cause:** SvelteKit router in Electron file:// mode - EXPECTED
- **Solution:** `+error.svelte` already handles this gracefully:
  - Logs as "expected in file:// mode"
  - Renders main app content from error page (workaround)
  - App works correctly despite the console message
- **File:** `locaNext/src/routes/+error.svelte`

### UI-062: Failed Network Request (version.json) ✅ FIXED
- **Reported:** 2025-12-27
- **Fixed:** 2025-12-28
- **Severity:** LOW (Cosmetic console error)
- **Status:** FIXED
- **Problem:** `net::ERR_FILE_NOT_FOUND` for `file:///C:/_app/version.json`
- **Root Cause:** SvelteKit runtime fetches `/_app/version.json` which becomes `C:/_app/version.json` in file:// mode
- **Solution:** Used `session.webRequest.onBeforeRequest` to intercept and redirect to correct path
- **Implementation:** `electron/main.js` lines 514-528
  - Intercepts `file:///*/_app/version.json` and `file:///C:/_app/version.json`
  - Redirects to `build/_app/version.json` in the app directory
- **Documentation:** [UI-062_SVELTEKIT_VERSION_JSON_FIX.md](UI-062_SVELTEKIT_VERSION_JSON_FIX.md)

### UI-074: Missing API Endpoint /api/ldm/files ✅ FIXED
- **Reported:** 2025-12-27
- **Fixed:** 2025-12-28 (verified existing)
- **Severity:** HIGH (API error)
- **Status:** FIXED
- **Problem:** Frontend calls `/api/ldm/files?limit=100` which didn't exist
- **Solution:** Endpoint already exists in `files.py` lines 56-88
  - `GET /files` returns all files across all user's projects
  - Tested: Returns 200 with correct file list
- **File:** `server/tools/ldm/routes/files.py`

### UI-075: Console Error Objects Being Logged ✅ FIXED
- **Reported:** 2025-12-27
- **Fixed:** 2025-12-28
- **Severity:** HIGH (Hidden errors)
- **Status:** FIXED
- **Problem:** Console shows `[ERROR] Console Error Object` without details
- **Root Cause:** `remote-logger.js` used `JSON.stringify(arg)` which returns `{}` for Error objects
- **Fix:** Properly serialize Error objects by extracting `message`, `stack`, `name`
- **File:** `locaNext/src/lib/utils/remote-logger.js` lines 89-103

---

## MEDIUM - UX ISSUES

### UI-063: CSS Text Overflow Issues ✅ FIXED
- **Status:** FIXED
- **Assessed:** 2025-12-28
- **Verified:** 2025-12-29 (Playwright test)
- **Problem:** Some elements have `overflow: hidden` without `text-overflow: ellipsis`
- **Test Result:** All 26 cells tested have both `overflow:hidden` AND `text-overflow:ellipsis`
- **Conclusion:** Ellipsis styling is properly applied to all grid cells

### UI-064: Target Cell Status Colors Conflict with Hover ⚠️ BY DESIGN
- **Status:** BY DESIGN (not a bug)
- **Assessed:** 2025-12-28
- **Problem:** Status colors conflict with hover states
- **Analysis:** CSS already handles this at lines 1877-1882
  - Status cells use `filter: brightness(1.1)` on hover
  - This brightens the status color rather than replacing it
  - Status color remains visible on hover (intentional)
- **Conclusion:** Current behavior is correct - user can see status while hovering

### UI-065: Edit Icon Visibility Inconsistent ✅ FIXED
- **Fixed:** 2025-12-28 (verified existing CSS)
- **Status:** FIXED
- **Problem:** Edit icon only visible on hover, not on selected cell
- **Fix:** CSS already exists at line 1908 showing edit icon at 0.7 opacity on selected cells

### UI-066: Placeholder Rows Have Wrong Column Count
- **Status:** OPEN (LOW PRIORITY)
- **Assessed:** 2025-12-28
- **Problem:** Placeholder rows show single shimmer instead of matching columns
- **Analysis:** Line 1343-1347 shows row_num + single loading-cell with shimmer
- **Impact:** Minor cosmetic during loading, doesn't affect functionality

### UI-067: Filter Dropdown Styling Inconsistent ✅ FIXED
- **Status:** FIXED
- **Assessed:** 2025-12-28
- **Fixed:** 2025-12-29
- **Problem:** Filter dropdown height doesn't match search input
- **Was:** Search input: 32px, Dropdown: 40px (8px difference)
- **Fix:** Added explicit `height: 2rem` to `.bx--dropdown`, `.bx--list-box`, `.bx--list-box__field`
- **Result:** Both elements now 32px - heights match
- **File:** VirtualGrid.svelte lines 1916-1927

### UI-068: Resize Handle Not Visible Until Hover ⚠️ BY DESIGN
- **Status:** BY DESIGN (not a bug)
- **Assessed:** 2025-12-28
- **Verified:** 2025-12-29 (Playwright test found 2 resize handles in DOM)
- **Problem:** Column resize handle invisible until hover
- **Analysis:** Resize handles exist in DOM, appear on hover - this is intentional UX
- **Conclusion:** Clean interface until user needs to resize - standard UX pattern

### UI-069: QA Icon Position Conflicts with Edit Icon
- **Status:** OPEN (LOW PRIORITY)
- **Assessed:** 2025-12-28
- **Problem:** QA warning icon and edit icon can overlap
- **Impact:** Visual clutter when both icons visible

---

## LOW - COSMETIC ISSUES

### UI-070: Empty Divs in DOM ✅ FIXED
- **Status:** FIXED
- **Assessed:** 2025-12-28
- **Verified:** 2025-12-29
- **Was:** 9 empty divs → **Now:** 4 (acceptable)
- **Impact:** Reduced DOM bloat

### UI-071: Reference Column "No match" Styling
- **Status:** OPEN (COSMETIC)
- **Assessed:** 2025-12-28
- **Problem:** "No match" text could be clearer
- **Impact:** Minor UX improvement opportunity

### UI-072: TM Empty Message Styling
- **Status:** OPEN (COSMETIC)
- **Assessed:** 2025-12-28
- **Problem:** "No similar translations found" styling
- **Impact:** Minor UX improvement opportunity

### UI-073: Shortcut Bar Takes Vertical Space ✅ FIXED
- **Status:** FIXED
- **Assessed:** 2025-12-28
- **Verified:** 2025-12-29
- **Resolution:** Shortcut bar no longer present in DOM (0 elements found)
- **Impact:** Vertical space recovered

---

## FIX PRIORITY ORDER (Remaining)

1. **UI-061** - Routing error on page load
2. **UI-062** - version.json network error
3. **UI-075** - Console error objects being logged
4. **UI-063** - CSS text overflow issues
5. **UI-064** - Status colors conflict with hover

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

*Updated 2025-12-29 | 24 Issues FIXED | 4 OPEN Issues*
