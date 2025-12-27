# Issues To Fix

**Last Updated:** 2025-12-27 12:15 | **Build:** 395 | **Open:** 26

> **CRITICAL:** Full UI audit + console analysis revealed 26 issues. Build 395 fixes DID NOT WORK. Found EASY WORKAROUNDS that broke virtual scrolling. Missing API endpoint causing 5x 404 errors.

---

## Quick Summary

| Status | Count |
|--------|-------|
| **CRITICAL (Blocking)** | 5 |
| **HIGH (Major UX)** | 10 |
| **MEDIUM (UX Issues)** | 7 |
| **LOW (Cosmetic)** | 4 |

---

## CRITICAL - BLOCKING ISSUES

### UI-051: Edit Modal Softlock - Cannot Close

- **Reported:** 2025-12-27 (iPad + CDP audit)
- **Severity:** CRITICAL (App unusable)
- **Status:** OPEN
- **Problem:** Clicking target cell opens edit modal, but:
  1. X button doesn't close modal
  2. ESC key doesn't close modal
  3. Clicking overlay doesn't close modal
  4. User is completely softlocked
- **Evidence:** CDP screenshots show modal still open after X button click
- **Root Cause Analysis:**
  - Close button uses `onclick={closeEditModal}` (VirtualGrid.svelte:1279)
  - Carbon Components require `on:click` syntax (Svelte 4 events)
  - Same issue as BUG-037 (QA Panel X button)
- **File:** `VirtualGrid.svelte` lines 1268-1279
- **Fix Required:** Change `onclick` to `on:click` for close button and overlay

---

### UI-052: TM Suggestions Infinite Loading

- **Reported:** 2025-12-27 (iPad + CDP audit)
- **Severity:** CRITICAL (Edit modal unusable)
- **Status:** OPEN
- **Problem:** TM MATCHES panel shows loading spinner forever, never loads suggestions
- **Evidence:** CDP audit captured 6 loading spinners visible simultaneously
- **Root Cause Analysis:**
  - `fetchTMSuggestions()` may be failing silently
  - Network request might be blocked or timing out
  - API endpoint may not be responding
- **File:** `VirtualGrid.svelte` lines 424-456
- **Investigation Needed:** Check TM suggest API, network logs, error handling

---

### UI-053: Virtual Scrolling Completely Broken

- **Reported:** 2025-12-27 (CDP audit)
- **Severity:** CRITICAL (Performance, UX)
- **Status:** OPEN
- **Problem:** Scroll container expands to full content height instead of staying fixed
- **Evidence:** CDP audit showed `clientHeight = scrollHeight = 480136px`
  - This means container is 480,136px tall (matches content)
  - `canScroll: false` - scrolling disabled
  - Virtual scrolling is completely bypassed
  - Only first ~30 rows load, nothing else loads on scroll
- **ROOT CAUSE FOUND (EASY WORKAROUND DETECTED):**
  ```css
  /* LDM.svelte lines 802-803, 822-823 */
  .ldm-app {
    overflow: visible;  /* Changed from overflow: hidden to allow tooltips to escape */
  }
  .ldm-layout {
    overflow: visible;  /* Changed from overflow: hidden to allow tooltips to escape */
  }
  ```
  - Someone changed `overflow: hidden` → `overflow: visible` for tooltips
  - This BROKE the height constraint chain
  - Children can now expand beyond parent bounds
  - Scroll container grows to content height = 480K px
  - No scroll events fire → no lazy loading triggered
- **Files:**
  - `LDM.svelte` lines 802-803, 822-823 (overflow: visible)
  - `VirtualGrid.svelte` lines 1506-1512 (scroll-container)
- **Fix Required:**
  1. Revert `overflow: visible` back to `overflow: hidden` in LDM.svelte
  2. Fix tooltips using portals or fixed positioning instead
  3. Add `height: 0` to `.scroll-container` for proper flex behavior
  4. Test that lazy loading works after fix

---

### UI-054: Cells Not Expanding (Content Compressed)

- **Reported:** 2025-12-27 (iPad testing)
- **Severity:** CRITICAL (Content unreadable)
- **Status:** OPEN
- **Problem:** Cells show compressed text, not expanding to show content
- **Expected:** Cells should expand up to 200px (~8 lines) per UI-049 fix
- **Evidence:** User reports all cells compressed, Build 395 fix not working
- **Root Cause Analysis:**
  - `estimateRowHeight()` calculates height but virtual scroll uses MIN_ROW_HEIGHT (48px)
  - `getRowTop()` uses constant MIN_ROW_HEIGHT for positioning
  - Variable height and fixed positioning conflict
- **File:** `VirtualGrid.svelte` lines 907-939
- **Fix Required:** Either:
  1. Use actual heights for positioning (complex, O(n) performance)
  2. OR make all cells same height with internal scroll (simpler)

---

### UI-055: 171+ Hidden Modals in DOM (Memory Bloat)

- **Reported:** 2025-12-27 (CDP audit)
- **Severity:** CRITICAL (Performance, Memory)
- **Status:** OPEN
- **Problem:** 171 modal elements in DOM, most hidden
- **Evidence:** CDP audit: `totalModals: 171`, `closeButtonCount: 47`
- **Root Cause Analysis:**
  - Carbon Components create modals that aren't destroyed
  - Multiple modal instances accumulating
  - Each modal has ~10 child elements = 1700+ unnecessary DOM nodes
- **Impact:**
  - Memory leak
  - Slow DOM queries
  - Event listener accumulation
- **Fix Required:**
  1. Use `{#if}` to conditionally render modals instead of CSS hiding
  2. Ensure modals are destroyed when closed
  3. Investigate Carbon Components modal lifecycle

---

## HIGH - MAJOR UX ISSUES

### UI-056: Source Text Not Selectable

- **Reported:** 2025-12-27 (iPad testing)
- **Severity:** HIGH (UX inconsistency)
- **Status:** OPEN
- **Problem:** Source column text cannot be selected/highlighted by user
- **Expected:** Same selection behavior as target column
- **Root Cause:** Source cell lacks interactive states, no click handler
- **File:** `VirtualGrid.svelte` lines 1182-1189
- **Fix Required:** Add `user-select: text` to `.cell.source` CSS

---

### UI-057: Hover Highlight Split Colors (Two-Tone Bug)

- **Reported:** 2025-12-27 (iPad testing)
- **Severity:** HIGH (Visual confusion)
- **Status:** OPEN
- **Problem:** Hovering sometimes shows ONE color, sometimes shows split 2-color highlight
- **Description:** Weird interaction where highlight becomes 2 colors at once
- **Root Cause Analysis:**
  - Multiple hover states overlapping:
    - `.virtual-row:hover` (row background)
    - `.cell-hover` (cell background)
    - `.status-translated/:reviewed/:approved` (status colors)
  - When row hover + cell hover + status color all active = 3 conflicting colors
- **File:** `VirtualGrid.svelte` CSS lines 1536-1644
- **Fix Required:**
  1. Remove row-level hover, keep only cell-level
  2. OR use single unified hover state
  3. Ensure status colors don't conflict with hover states

---

### UI-058: Previous Fixes Not Applied (Build 395 Ineffective)

- **Reported:** 2025-12-27 (verification)
- **Severity:** HIGH (Process issue)
- **Status:** OPEN
- **Problem:** UI-048, UI-049, UI-050 fixes from Build 395 are NOT working:
  - UI-048: Hover still ugly (split colors)
  - UI-049: Cells still not expanding
  - UI-050: Lazy loading still broken
- **Possible Causes:**
  1. Build didn't complete successfully
  2. Playground not updated with new build
  3. Code changes not deployed correctly
  4. CSS specificity issues overriding fixes
- **Investigation:** Verify Build 395 artifacts, check deployed code

---

### UI-059: Row Selection State Inconsistent

- **Reported:** 2025-12-27 (CDP audit)
- **Severity:** HIGH (UX)
- **Status:** OPEN
- **Problem:** Selected row state conflicts with hover state
- **Evidence:** CDP audit shows `selectedRowId` changes on click but visual feedback inconsistent
- **Root Cause:** `.virtual-row.selected` CSS competing with cell-level states
- **File:** `VirtualGrid.svelte` CSS line 1540-1542

---

### UI-060: Click on Source Cell Opens Edit Modal

- **Reported:** 2025-12-27 (CDP audit)
- **Severity:** HIGH (Unexpected behavior)
- **Status:** OPEN
- **Problem:** Clicking source cell triggers row selection and can open edit modal
- **Expected:** Source cell should be read-only, only target editable
- **Root Cause:** `handleCellClick()` handles all cells, `ondblclick` on row not cell
- **File:** `VirtualGrid.svelte` lines 947-959, 1157

---

### UI-061: Routing Error on Page Load

- **Reported:** 2025-12-27 (CDP audit)
- **Severity:** HIGH (Error)
- **Status:** OPEN
- **Problem:** Console error: `Error: Not found: /C:/NEIL_PROJECTS.../index.html`
- **Evidence:** CDP captured error from `app.BX2D2d46.js:2`
- **Root Cause:** SvelteKit router trying to resolve file path as route
- **Impact:** May cause navigation issues

---

### UI-062: Failed Network Request (version.json)

- **Reported:** 2025-12-27 (CDP audit)
- **Severity:** HIGH (Missing resource)
- **Status:** OPEN
- **Problem:** `net::ERR_FILE_NOT_FOUND` for `file:///C:/_app/version.json`
- **Root Cause:** App looking for version.json in wrong path
- **Impact:** May affect version checking, auto-update

---

### UI-074: Missing API Endpoint /api/ldm/files (5x 404 Errors)

- **Reported:** 2025-12-27 (Console logs)
- **Severity:** HIGH (API error)
- **Status:** OPEN
- **Problem:** Frontend calls `/api/ldm/files?limit=100` which doesn't exist
- **Evidence:** Console shows `localhost:8888/api/ldm/files?limit=100 - 404 (Not Found)` x5
- **Root Cause:**
  - `ReferenceSettingsModal.svelte:46` calls `/api/ldm/files?limit=100`
  - Backend only has `/projects/{project_id}/files` (needs project ID)
  - NO `/api/ldm/files` endpoint exists!
- **Files:**
  - `ReferenceSettingsModal.svelte` line 46 (frontend call)
  - `server/tools/ldm/routes/files.py` (missing endpoint)
- **Fix Required:**
  1. Either create `/api/ldm/files` endpoint to list all files
  2. OR change ReferenceSettingsModal to use project-scoped endpoint
  3. Consider which approach fits the UX better

---

### UI-075: Console Error Objects Being Logged

- **Reported:** 2025-12-27 (Console logs)
- **Severity:** HIGH (Hidden errors)
- **Status:** OPEN
- **Problem:** Console shows `[ERROR] Console Error Object` multiple times
- **Evidence:** Errors logged from `By0xOlty.js:8` (minified logger)
- **Root Cause:** Application is catching and logging error objects but not showing details
- **File:** Logger implementation in built app
- **Investigation:** Need to find what's being caught and logged as `[ERROR] Console Error Object`

---

---

## MEDIUM - UX ISSUES

### UI-063: CSS Text Overflow Issues (20+ Elements)

- **Reported:** 2025-12-27 (CDP audit)
- **Severity:** MEDIUM (Visual)
- **Status:** OPEN
- **Problem:** 20+ elements have text overflow without ellipsis
- **Evidence:** CDP audit detected:
  - `bx--toggle-input__label`
  - `file-explorer`
  - `ldm-toolbar`
  - Multiple tooltip triggers
- **Fix Required:** Add `text-overflow: ellipsis` to affected elements

---

### UI-064: Target Cell Status Colors Conflict with Hover

- **Reported:** 2025-12-27 (code analysis)
- **Severity:** MEDIUM (Visual)
- **Status:** OPEN
- **Problem:** Status colors (translated/reviewed/approved) conflict with hover
- **Evidence:** CSS shows separate hover overrides per status type
- **File:** `VirtualGrid.svelte` lines 1639-1643

---

### UI-065: Edit Icon Visibility Inconsistent

- **Reported:** 2025-12-27 (code analysis)
- **Severity:** MEDIUM (UX)
- **Status:** OPEN
- **Problem:** Edit icon only visible on hover, not on selected cell
- **File:** `VirtualGrid.svelte` lines 1645-1660

---

### UI-066: Placeholder Rows Have Wrong Column Count

- **Reported:** 2025-12-27 (code analysis)
- **Severity:** MEDIUM (Visual)
- **Status:** OPEN
- **Problem:** Placeholder rows show single shimmer instead of matching column layout
- **File:** `VirtualGrid.svelte` lines 1161-1165

---

### UI-067: Filter Dropdown Styling Inconsistent

- **Reported:** 2025-12-27 (CDP audit)
- **Severity:** MEDIUM (Visual)
- **Status:** OPEN
- **Problem:** Filter dropdown height doesn't match search input
- **File:** `VirtualGrid.svelte` CSS lines 1443-1448

---

### UI-068: Resize Handle Not Visible Until Hover

- **Reported:** 2025-12-27 (code analysis)
- **Severity:** MEDIUM (Discoverability)
- **Status:** OPEN
- **Problem:** Column resize handle invisible until mouse hovers over exact position
- **File:** `VirtualGrid.svelte` CSS lines 1489-1504

---

### UI-069: QA Icon Position Conflicts with Edit Icon

- **Reported:** 2025-12-27 (code analysis)
- **Severity:** MEDIUM (Visual)
- **Status:** OPEN
- **Problem:** QA warning icon at `right: 1.5rem`, edit icon at `right: 0.25rem` - can overlap
- **File:** `VirtualGrid.svelte` CSS lines 1668-1672, 1645-1660

---

---

## LOW - COSMETIC ISSUES

### UI-070: Empty Divs in DOM (9 Found)

- **Reported:** 2025-12-27 (CDP audit)
- **Severity:** LOW (Cleanup)
- **Status:** OPEN
- **Problem:** 9 empty div elements in DOM
- **Impact:** Minor DOM bloat

---

### UI-071: Reference Column "No match" Styling

- **Reported:** 2025-12-27 (code analysis)
- **Severity:** LOW (Visual)
- **Status:** OPEN
- **Problem:** "No match" text in reference column could be clearer
- **File:** `VirtualGrid.svelte` lines 1698-1701

---

### UI-072: TM Empty Message Styling

- **Reported:** 2025-12-27 (code analysis)
- **Severity:** LOW (Visual)
- **Status:** OPEN
- **Problem:** "No similar translations found" message styling could be improved
- **File:** `VirtualGrid.svelte` lines 2040-2046

---

### UI-073: Shortcut Bar Takes Vertical Space

- **Reported:** 2025-12-27 (code analysis)
- **Severity:** LOW (Space efficiency)
- **Status:** OPEN
- **Problem:** Shortcut hints bar in edit modal could be more compact
- **File:** `VirtualGrid.svelte` lines 1271-1280

---

---

## INVESTIGATION NEEDED

### INV-001: Why Build 395 Fixes Don't Work

- **Question:** Did Build 395 deploy correctly?
- **Check:**
  1. Verify Gitea shows build 395 as SUCCESS
  2. Check Playground version matches build
  3. Inspect deployed VirtualGrid.svelte for fix code
  4. Check if CSS changes are present in built artifacts

### INV-002: TM Suggest API Performance

- **Question:** Why is TM loading infinitely?
- **Check:**
  1. Test `/api/ldm/tm/suggest` endpoint directly
  2. Check 2VEC model status
  3. Check FAISS index status
  4. Network timing analysis

---

## FIX PRIORITY ORDER

1. **UI-051** - Modal softlock (CRITICAL - users stuck)
2. **UI-053** - Virtual scroll broken (CRITICAL - affects all users)
3. **UI-054** - Cells not expanding (CRITICAL - content unreadable)
4. **UI-052** - TM infinite loading (CRITICAL - edit unusable)
5. **UI-055** - DOM bloat 171 modals (CRITICAL - performance)
6. **UI-057** - Split color hover (HIGH - confusing)
7. **UI-056** - Source not selectable (HIGH - UX)
8. **UI-058** - Verify Build 395 (HIGH - process)

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

*Updated 2025-12-27 11:30 | CDP Audit Complete | 24 OPEN Issues*
