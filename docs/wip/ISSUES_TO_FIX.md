# Issues To Fix

**Last Updated:** 2026-01-04 (Session 21 Continued) | **Build:** 444 | **Open:** 2

---

## Quick Summary

| Status | Count |
|--------|-------|
| **OPEN** | 2 |
| **FIXED/CLOSED** | 88 |
| **NOT A BUG/BY DESIGN** | 3 |
| **SUPERSEDED BY PHASE 10** | 2 |

---

## OPEN ISSUES - SESSION 20

### SYNC-008: TM Sync Not Supported

- **Reported:** 2026-01-03 (Session 20)
- **Severity:** MEDIUM
- **Status:** OPEN
- **Component:** sync.py, offline.py

**Problem:** TM should auto-sync when file/project/folder syncs.

**What's needed:**
1. `_sync_tm_to_offline()` function - sync TM entries to SQLite
2. Auto-trigger TM sync when parent entity syncs
3. TM merge logic (mostly INSERT - additive)

**TM linkage:** `ldm_tm_assignment` table links TMs to Platform/Project/Folder.

---

### ~~P3-PHASE4-6: Conflict Resolution & Polish~~ → MOSTLY DONE

- **Reported:** 2026-01-03 (Session 20)
- **Revised:** 2026-01-04 (Session 21)
- **Severity:** LOW (was MEDIUM)
- **Status:** ✅ MOSTLY DONE

**What the doc said:** Complex conflict resolution UI with dialogs.

**Reality:** `merge_row()` already implements **last-write-wins** by timestamp:
```python
if server_updated > local_updated:
    # Server wins automatically
else:
    # Local wins, will push later
```

**Remaining edge cases (LOW PRIORITY):**
- "Reviewed" row protection (don't auto-overwrite reviewed translations)
- New file path selection (only for files created offline - rare use case)
- **Component:** sync.js, sync.py

**Problem:** Phases 4-6 of P3 Offline/Online Mode not implemented:
- Phase 4: Conflict resolution UI
- Phase 5: File dialog path selection
- Phase 6: Polish & edge cases

---

## FIXED IN SESSION 21

### DB-001: Database Needs Full Cleanup - FIXED

- **Fixed:** 2026-01-03 (Session 21)
- Created fresh: Platform 27, Project 23, Folder 8, File 5
- Uploaded clean sample_language_data.txt (63 rows)

### P3-PHASE3: Push Local Changes to Server - FIXED

- **Fixed:** 2026-01-03 (Session 21)
- Added `GET /api/ldm/offline/push-preview/{file_id}` endpoint
- Added `POST /api/ldm/offline/push-changes` endpoint
- Implemented `syncFileToServer()` in frontend
- Added "Push Changes" button in Sync Dashboard

---

## SESSION 20 FIXES (2026-01-03)

### AU-007: Auto-Updater Race Condition ✅ FIXED

- **Reported:** 2026-01-03
- **Fixed:** 2026-01-03 (Session 20)
- **Severity:** HIGH
- **Status:** FIXED

**Problem:** User didn't see auto-update UI because `autoDownload=true` started download before UpdateModal mounted.

**Fix:**
1. Changed `autoDownload = false` in main.js
2. Added state storage (`pendingUpdateInfo`, `updateState`)
3. Added `get-update-state` IPC handler
4. UpdateModal checks for pending updates on mount

**Files:** `electron/main.js`, `electron/preload.js`, `UpdateModal.svelte`

---

### COLOR-001: Color Code Corruption on Confirm ✅ FIXED

- **Reported:** 2026-01-03
- **Fixed:** 2026-01-03 (Session 20)
- **Severity:** HIGH
- **Status:** FIXED

**Problem:** `confirmInlineEdit()` saved HTML spans instead of PAColor tags:
```
SAVED: <span style="color:#e9bd23">text</span>
SHOULD BE: <PAColor0xffe9bd23>text<PAOldColor>
```

**Root Cause:** Used `formatTextForSave(inlineEditValue)` directly without converting HTML to PAColor first.

**Fix:** Added `htmlToPaColor()` conversion before formatting:
```javascript
// OLD (BROKEN)
const textToSave = formatTextForSave(inlineEditValue);

// NEW (CORRECT)
const rawText = htmlToPaColor(inlineEditValue);
const textToSave = formatTextForSave(rawText);
```

**File:** `VirtualGrid.svelte:1363-1365`

---

### TOGGLE-001: Offline/Online Toggle Freeze ✅ FIXED

- **Reported:** 2026-01-03
- **Fixed:** 2026-01-03 (Session 20)
- **Severity:** HIGH
- **Status:** FIXED

**Problem:** Toggling offline → online → offline → online caused "Connecting..." to get stuck.

**Root Cause:** Race condition - rapid toggles caused concurrent reconnect attempts.

**Fix:**
1. Added `isReconnecting` flag in sync.js
2. Added try/finally to always reset `reconnecting` state in SyncStatusPanel.svelte
3. `goOffline()` now clears error state and cancels pending reconnects

**Files:** `sync.js:162-197`, `SyncStatusPanel.svelte:71-84`

---

### SYNC-001: Auto-sync on File Open ✅ VERIFIED WORKING

- **Reported:** 2026-01-03
- **Verified:** 2026-01-03 (Session 20)
- **Status:** CLOSED - Was already working

Playwright test confirmed auto-sync registers files correctly.

---

### SYNC-002: Right-Click Register Sync ✅ VERIFIED WORKING

- **Reported:** 2026-01-03
- **Verified:** 2026-01-03 (Session 20)
- **Status:** CLOSED - Was already working

Playwright test confirmed right-click sync option works.

---

### SYNC-003: Sync Modal Shows Items ✅ VERIFIED WORKING

- **Reported:** 2026-01-03
- **Verified:** 2026-01-03 (Session 20)
- **Status:** CLOSED - Was already working

Playwright test found 3 subscription items in modal.

---

### SYNC-004: Sync Modal Layout ✅ FIXED

- **Reported:** 2026-01-03
- **Fixed:** 2026-01-03 (Session 20)
- **Severity:** MEDIUM
- **Status:** FIXED

**Fix:** Changed modal size from "sm" to "lg", increased padding/gaps, added explorer-style items with icon boxes.

**File:** `SyncStatusPanel.svelte`

---

### SYNC-006: Online Status Indicator ✅ FIXED

- **Reported:** 2026-01-03
- **Fixed:** 2026-01-03 (Session 20)
- **Severity:** MEDIUM
- **Status:** FIXED

**Fix:** Added glowing green dot with animation, green border on button, green text in modal.

**File:** `SyncStatusPanel.svelte` (CSS)

---

### SYNC-007: Explorer-Type View ✅ FIXED

- **Reported:** 2026-01-03
- **Fixed:** 2026-01-03 (Session 20)
- **Severity:** MEDIUM
- **Status:** FIXED

**Fix:** Added 36x36px icon boxes, larger item padding, uppercase type labels, hover effects.

**File:** `SyncStatusPanel.svelte` (CSS)

---

## SESSION 17 FIXES (2026-01-03)

### UI-103: Text Bleeding / Zombie Rows After Scroll ✅ FIXED

- **Reported:** 2026-01-03
- **Fixed:** 2026-01-03 (Build 438)
- **Severity:** HIGH
- **Status:** FIXED
- **Component:** VirtualGrid.svelte

**Problem:** After scrolling or resizing columns, rows would overlap or "zombie" rows would appear.

**Root Cause:** Svelte's `{@const}` creates a non-reactive constant:
```svelte
<!-- OLD (buggy) - rowTop evaluated ONCE, never updates -->
{@const rowTop = getRowTop(rowIndex)}
<div style="top: {rowTop}px">
```

When `cumulativeHeights` state changed (after measuring actual row heights), the `rowTop` variable didn't update because `{@const}` is not reactive.

**Fix:** Call the function directly in the style binding:
```svelte
<!-- NEW (correct) - reactive, recalculates when state changes -->
<div style="top: {getRowTop(rowIndex)}px; min-height: {getRowHeight(rowIndex)}px;">
```

**Commit:** `17067b8`
**File:** `locaNext/src/lib/components/ldm/VirtualGrid.svelte:2100`

---

### UI-104: Color Disappears After Edit Mode ✅ FIXED

- **Reported:** 2026-01-03
- **Fixed:** 2026-01-03 (Build 438)
- **Severity:** HIGH
- **Status:** FIXED
- **Component:** colorParser.js

**Problem:** After editing a cell with PAColor tags and exiting edit mode, the colors would disappear.

**Root Cause:** `htmlToPaColor()` used a regex that stripped ALL HTML tags including PAColor:
```javascript
result.replace(/<[^>]+>/g, '');  // WRONG: strips PAColor too!
```

**Fix:** Use negative lookahead to preserve PAColor tags:
```javascript
result.replace(/<(?!\/?PA(?:Color|OldColor))[^>]+>/g, '');  // CORRECT
```

**Commit:** `f252d06`
**File:** `locaNext/src/lib/utils/colorParser.js:280`

---

### UI-105: Cell Height Too Big for Multi-line Content ✅ FIXED

- **Reported:** 2026-01-03
- **Fixed:** 2026-01-03 (Build 438)
- **Severity:** MEDIUM
- **Status:** FIXED
- **Component:** VirtualGrid.svelte

**Problem:** Cells with multi-line content were too tall (e.g., 486px instead of 398px).

**Root Cause:** Old algorithm DOUBLE-COUNTED lines:
```javascript
const wrapLines = Math.ceil(maxLen / 55);     // Assumed all chars in one block
const totalLines = wrapLines + maxNewlines;   // Added newlines ON TOP = WRONG
```

**Fix:** New `countDisplayLines()` function splits by newlines FIRST:
```javascript
const segments = normalized.split('\n');
let totalLines = 0;
for (const segment of segments) {
  totalLines += Math.max(1, Math.ceil(segment.length / 55));
}
```

**Commit:** `f252d06`
**File:** `locaNext/src/lib/components/ldm/VirtualGrid.svelte:1593-1650`

---

### UI-106: Resize Bar Not Working After Scroll ✅ FIXED

- **Reported:** 2026-01-03
- **Fixed:** 2026-01-03 (Build 438)
- **Severity:** MEDIUM
- **Status:** FIXED
- **Component:** VirtualGrid.svelte

**Problem:** Column resize bar disappeared or didn't work after scrolling.

**Fix:** Moved resize bars outside scroll-container into a new `scroll-wrapper` div.

**Commit:** `f252d06`
**File:** `locaNext/src/lib/components/ldm/VirtualGrid.svelte:2069-2081`

---

## OPEN ISSUES

*No open issues!*

---

## SESSION 18 FIXES (2026-01-03)

### DESIGN-001: Public by Default Permission Model ✅ FIXED

- **Reported:** 2026-01-03
- **Fixed:** 2026-01-03 (Session 18)
- **Severity:** HIGH (Design flaw)
- **Status:** FIXED
- **Component:** All LDM routes (platforms, projects, files, TMs)

**Problem:** All LDM data was filtered by `owner_id`, so each user only saw their own data. Wrong for a team tool.

**Solution:** Implemented "Public by Default" permission model:
- **Default:** All resources PUBLIC (everyone sees everything)
- **Optional:** Admins can RESTRICT specific platforms/projects
- **Globally unique names:** No duplicate names anywhere
- **Access grants:** Admins can assign users to restricted resources

**Changes Made:**
- Added `is_restricted` column to LDMPlatform and LDMProject
- Created `LDMResourceAccess` table for explicit access grants
- Updated unique constraints to be globally unique (no duplicates)
- Created `server/tools/ldm/permissions.py` with helper functions
- Updated 13 route files (77+ locations) to use permission helpers
- Added admin endpoints for restriction management

**Spec:** See `docs/wip/PUBLIC_PERMISSIONS_SPEC.md`

---

### UI-102: P5 Search Bar Too Small
- **Reported:** 2026-01-03
- **Severity:** MEDIUM (UI regression)
- **Status:** FIXED (partial)
- **Component:** VirtualGrid.svelte

**Problem:** P5 Advanced Search added `max-width: 400px` to `.search-control`, making search bar too restrictive.

**Fix applied:** Removed `max-width`, added `min-width: 200px` to match old behavior.

**File:** `locaNext/src/lib/components/ldm/VirtualGrid.svelte` line 2372

---

### 🎉 CLEAN SLATE (Session 16)

**Endpoint Coverage:** 220/220 (100%)
- Generated 149 test stubs covering all untested endpoints
- Fixed 4 Auth transaction bugs (activate/deactivate user)
- All tests passing

---

## FUTURE: Phase 10 Major UI/UX Overhaul

See **[PHASE_10_MAJOR_UIUX_OVERHAUL.md](PHASE_10_MAJOR_UIUX_OVERHAUL.md)** for:
- LocaNext dropdown navigation
- Files/TM as separate pages (not left column)
- Windows/SharePoint-style File Explorer
- TM Explorer with project-based TMs
- Dashboard enhancements with stats hierarchy

---

## Session 13 Updates (CI/CD Fixes)

| Issue | Root Cause | Fix | Status |
|-------|------------|-----|--------|
| CI-001 | SW lacked gsudo for Windows services | Added `gsudo` to `gitea_control.sh` | ✅ FIXED |
| CI-002 | macOS build references non-existent config | Changed to inline config in package.json | ✅ FIXED |
| CI-003 | TM similarity search 500 error | Added pg_trgm extension to both CI workflows | ✅ FIXED |

## Session 14 Updates (Auto-Updater Fix)

| Issue | Root Cause | Fix | Status |
|-------|------------|-----|--------|
| AU-001 | Semver leading zeros | Changed `%m%d` → `%-m%d` (26.0102 → 26.102) | ✅ FIXED |
| AU-002 | No `latest` release tag | Added step to create `latest` release for updater | ✅ FIXED |
| AU-003 | YAML heredoc broke parsing | Use ConvertTo-Json instead | ✅ FIXED |
| AU-004 | PowerShell curl JSON escaping | Write JSON to file, use @file | ✅ FIXED |
| AU-005 | UTF-8 BOM in JSON file | Use WriteAllText() instead of Out-File | ✅ FIXED |
| AU-006 | **STUPID REGEX** | Regex to extract version when CI already had it | ✅ FIXED |

## Session 15 Updates (Issue Verification)

Verified open issues - found 4 were already fixed:

| Issue | Was | Now | Status |
|-------|-----|-----|--------|
| UI-087 | Apps dropdown on far right | CSS fixed: centered below button | ✅ FIXED |
| UI-088 | Separate QA buttons | Now single "Run QA" in context menu | ✅ FIXED |
| UI-089/090/091 | Missing Delete buttons | Delete exists for File/Folder/Project/Platform | ✅ FIXED |
| UI-092 | Can't right-click closed project | ExplorerGrid (Windows-style), all items clickable | ✅ FIXED |

**Open issues reduced from 12 to 8.**

### AU-006: The Regex Idiocy (LESSON LEARNED)

**Problem:** `latest.yml` generation used regex to parse version from `version.py`:
```powershell
if ($versionContent -match 'VERSION\s*=\s*"(\d{2}\.\d{4}\.\d{4})"') {
```

**Why This Was Stupid:**
1. CI already generates the version and stores it in `${{ needs.check-build-trigger.outputs.version }}`
2. Regex was fragile - broke when version format changed from `MMDD` to `MDD`
3. Had a silent fallback `25.0101.0000` that masked the failure
4. Duplicated logic = multiple places to break

**Proper Fix:**
```powershell
env:
  VERSION: ${{ needs.check-build-trigger.outputs.version }}
run: |
  $version = $env:VERSION  # Just use it directly
```

**Rule:** Don't parse what you already have. Question old code that does unnecessary work.

---

## Session 9 Updates

**FIXED This Session:**
- ~~UI-087: Dropdown Position~~ → CSS fix in +layout.svelte (wrapper divs + positioning)
- ~~UI-094: TM Toolbar Button~~ → Removed button, added "Manage" to TM tab
- ~~UI-095: QA Buttons~~ → Removed from toolbar, QA in context menu only
- ~~UI-096: Reference File Picker~~ → Created FilePickerDialog.svelte for browsing
- ~~UI-097: Consolidate Settings~~ → Removed Settings from LDM toolbar, use top nav
- ~~TM-UI-001: Pretranslation Modal~~ → Created PretranslateModal.svelte + context menu
- ~~TM-UI-002: Unified TM Panel~~ → Enhanced TM tab with upload/delete/export/activate
- ~~TM-UI-003: Threshold Selector~~ → Slider in TM tab (50-100%), stored in preferences

**CLOSED (Already Working):**
- ~~FEAT-003: 5-Tier Cascade TM~~ → `server/tools/ldm/indexing/searcher.py` (380 lines)
- ~~FEAT-004: Create Glossary~~ → FileExplorer context menu → `/api/ldm/files/{id}/extract-glossary`
- ~~FEAT-005/006/007: Pretranslate~~ → Backend complete, frontend done via TM-UI-001

---

## ~~CRITICAL - UI OVERHAUL~~ ✅ ALL FIXED (Session 9)

### ~~UI-094: Remove TM Button from Toolbar~~ ✅ FIXED
- **Fixed:** 2026-01-01 (Session 9)
- **Solution:** Removed TM button from toolbar, added "Manage" button to TM tab
- **Files Modified:** `LDM.svelte`, `FileExplorer.svelte`

---

### ~~UI-095: Remove QA Buttons + Simplify~~ ✅ FIXED
- **Fixed:** 2026-01-01 (Session 9)
- **Solution:** Removed QA On/Off and QA button from toolbar. QA now via context menu.
- **Files Modified:** `LDM.svelte`, `FileExplorer.svelte`

---

### ~~UI-096: Reference File Picker Overhaul~~ ✅ FIXED
- **Fixed:** 2026-01-01 (Session 9)
- **Solution:** Created `FilePickerDialog.svelte` with hierarchical project/folder browsing.
- **Files Created:** `FilePickerDialog.svelte`
- **Files Modified:** `ReferenceSettingsModal.svelte`

---

### ~~UI-097: Consolidate Settings~~ ✅ FIXED
- **Fixed:** 2026-01-01 (Session 9)
- **Solution:** Removed Settings gear from LDM toolbar. Users use top nav → Settings → Preferences.
- **Files Modified:** `LDM.svelte`

---

## ~~HIGH - TM UI/UX OVERHAUL~~ ✅ ALL FIXED (Session 9)

### ~~TM-UI-001: Pretranslation Modal~~ ✅ FIXED
- **Fixed:** 2026-01-01 (Session 9)
- **Solution:** Created `PretranslateModal.svelte` with TM selector, engine selection (Standard/XLS/KR Similar), threshold slider, progress bar. Added "Pretranslate..." to FileExplorer context menu.
- **Files Created:** `PretranslateModal.svelte`
- **Files Modified:** `FileExplorer.svelte`

---

### ~~TM-UI-002: Unified TM Panel~~ ✅ FIXED
- **Fixed:** 2026-01-01 (Session 9)
- **Solution:** Enhanced TM tab in FileExplorer with:
  - Upload button (opens TMUploadModal)
  - Context menu: View Entries, Export TM, Activate/Deactivate, Delete
  - Active TM visual indicator (checkmark, "ACTIVE" badge, blue border)
  - Settings button for embedding engine config
- **Files Modified:** `FileExplorer.svelte`

---

### ~~TM-UI-003: User-Selectable Threshold~~ ✅ FIXED
- **Fixed:** 2026-01-01 (Session 9)
- **Solution:** Added `tmThreshold` to preferences store (default 0.92). Slider in TM tab (50-100%) with real-time percentage display. All TM suggest calls now use user's threshold preference.
- **Files Modified:** `FileExplorer.svelte`, `preferences.js`, `LDM.svelte`, `VirtualGrid.svelte`

---

## CLOSED - ALREADY WORKING (Session 9 Audit)

### FEAT-003: 5-Tier Cascade TM ✅ ALREADY IMPLEMENTED
- **Closed:** 2026-01-01 (Session 9)
- **Location:** `server/tools/ldm/indexing/searcher.py` (380 lines)
- **Tiers:** Hash whole → FAISS whole → Hash line → FAISS line → N-gram

### FEAT-004: Create Glossary ✅ ALREADY WORKING
- **Closed:** 2026-01-01 (Session 9)
- **Backend:** `server/tools/ldm/routes/files.py:880-981`
- **Frontend:** FileExplorer → right-click → "Create Glossary"
- **Endpoint:** `GET /api/ldm/files/{id}/extract-glossary`

### FEAT-005/006/007: Pretranslate ✅ BACKEND COMPLETE
- **Closed:** 2026-01-01 (Session 9)
- **Reclassified as:** TM-UI-001 (frontend only)
- **Backend:** `server/tools/ldm/pretranslate.py` (520 lines)
- **API:** `POST /api/ldm/pretranslate`
- **Engines:** Standard (5-tier), XLS Transfer, KR Similar

---

## ~~OPEN ISSUES - UI/UX (HIGH)~~ ✅ ALL FIXED (Session 15)

### ~~UI-088: Need Single "Run QA" Button~~ ✅ FIXED
- **Reported:** 2026-01-01
- **Fixed:** 2026-01-02 (Session 15 verification)
- **Status:** FIXED

**Was:** Separate "Run Full Term QA" and "Run Full Line QA" buttons
**Now:** Single "Run QA" button in context menu (FilesPage.svelte:1133)

---

### ~~UI-089/090/091: Missing Delete Buttons~~ ✅ FIXED
- **Reported:** 2026-01-01
- **Fixed:** 2026-01-02 (Session 15 verification)
- **Status:** FIXED

**Was:** No delete buttons visible
**Now:** Delete in context menu for File, Folder, Project, Platform (FilesPage.svelte:1141-1156)

---

## ~~OPEN ISSUES - ENDPOINT COVERAGE (HIGH)~~ ✅ ALL FIXED!

**Session 16 Achievement:** 100% endpoint coverage!
**Tests:** `tests/api/test_generated_stubs.py` (149 tests)
**Run:** `pytest tests/api/test_generated_stubs.py -v`

### ~~EP-001: LDM Core Coverage~~ ✅ FIXED (100%)
- **Reported:** 2026-01-01
- **Fixed:** 2026-01-03 (Session 16)
- **Severity:** HIGH → CLOSED
- **Status:** 75/75 endpoints tested (100%)

---

### ~~EP-002: Auth Coverage~~ ✅ FIXED (100%)
- **Reported:** 2026-01-01
- **Fixed:** 2026-01-03 (Session 16)
- **Severity:** HIGH → CLOSED
- **Status:** 24/24 endpoints tested (100%)

**Bug fixed:** activate_user/deactivate_user had SQLAlchemy transaction conflict

---

### ~~EP-003: Admin Stats Coverage~~ ✅ FIXED (100%)
- **Reported:** 2026-01-01
- **Fixed:** 2026-01-03 (Session 16)
- **Severity:** HIGH → CLOSED
- **Status:** 16/16 Admin Stats + 6 Rankings + 8 Telemetry = 30 tests (100%)

---

### ~~EP-004: XLSTransfer Coverage~~ ✅ FIXED (100%)
- **Reported:** 2026-01-01
- **Fixed:** 2026-01-03 (Session 16)
- **Severity:** HIGH → CLOSED
- **Status:** 13/13 endpoints tested (100%)

---

### ~~EP-005: QuickSearch Needs Audit~~ ✅ AUDIT COMPLETE
- **Reported:** 2026-01-01
- **Audited:** 2026-01-03 (Session 16)
- **Severity:** MEDIUM → CLOSED
- **Status:** NOT ABSORBED - KEEP AS STANDALONE APP

**Audit Findings:**
- QuickSearch is a **standalone app** accessible from Apps menu
- Frontend: `QuickSearch.svelte` (full-featured component)
- Backend: `/api/v2/quicksearch` (dictionary search endpoints)
- **Unique features NOT in LDM:**
  - Dictionary management (create, load, set reference)
  - Multi-game support (BDO, BDM, BDC, CD)
  - Multi-language support (15 languages)
  - File/folder source modes for dictionary creation
  - Reference dictionary comparison

**Relationship to LDM:** LDM's `pretranslate.py` uses QuickSearch backend libraries (XLSTransfer), but QuickSearch app provides standalone dictionary management that LDM doesn't have.

**Decision:** KEEP QuickSearch as standalone app. Not absorbed.

---

### ~~EP-006: KR Similar Needs Audit~~ ✅ AUDIT COMPLETE
- **Reported:** 2026-01-01
- **Audited:** 2026-01-03 (Session 16)
- **Severity:** MEDIUM → CLOSED
- **Status:** NOT ABSORBED - KEEP AS STANDALONE APP

**Audit Findings:**
- KR Similar is a **standalone app** accessible from Apps menu
- Frontend: `KRSimilar.svelte` (full-featured component)
- Backend: `/api/v2/kr-similar` (Korean similarity endpoints)
- **Unique features NOT in LDM:**
  - Korean semantic similarity using FAISS vectors
  - Dictionary management (create, load by dict type)
  - Extract Similar feature (batch extraction)
  - Auto Translate feature with threshold/top-k controls
  - Split pairs vs whole pairs search modes

**Relationship to LDM:** LDM's `pretranslate.py` uses KR Similar as one of the pretranslation engines, but KR Similar app provides standalone dictionary management and batch operations that LDM doesn't have.

**Decision:** KEEP KR Similar as standalone app. Not absorbed.

---

## ~~OPEN ISSUES - UI/UX (MEDIUM)~~ ✅ PARTIALLY FIXED (Session 15)

### ~~UI-087: Apps Dropdown Position Wrong~~ ✅ FIXED
- **Reported:** 2026-01-01
- **Fixed:** 2026-01-02 (Session 15 verification)
- **Status:** FIXED

**Was:** Apps dropdown appears on far right
**Now:** CSS fixed with `top: 100%`, `left: 50%`, `transform: translateX(-50%)` - centered below button

---

### ~~UI-092: Cannot Right-Click Closed Project~~ ✅ FIXED
- **Reported:** 2026-01-01
- **Fixed:** 2026-01-02 (Session 15 verification)
- **Status:** FIXED

**Was:** Tree view with collapsed projects, right-click didn't work
**Now:** ExplorerGrid (Windows-style grid view), all items have context menu via `oncontextmenu`

---

### UI-098: Threshold Slider UI/UX Issues
- **Reported:** 2026-01-01
- **Severity:** MEDIUM → **SUPERSEDED**
- **Component:** FileExplorer TM tab
- **Status:** SUPERSEDED BY PHASE 10

**Problem:** Threshold slider has visual issues (cramped, text cutting off).

**Resolution:** Will be properly implemented in Phase 10 TM Explorer page with dedicated space.

---

### UI-099: Remove TM Settings Modal
- **Reported:** 2026-01-01
- **Severity:** MEDIUM → **SUPERSEDED**
- **Component:** FileExplorer, TMManager
- **Status:** SUPERSEDED BY PHASE 10

**Problem:** TM Settings modal is redundant. Most options not useful.

**Resolution:** Phase 10 TM Explorer will have proper settings integrated into the page.

---

### ~~UI-100: Skip to Main Content URL Artifact~~ ✅ FIXED
- **Reported:** 2026-01-01
- **Fixed:** 2026-01-03 (Session 16)
- **Severity:** LOW → CLOSED
- **Component:** +layout.svelte, accessibility
- **Status:** FIXED

**Problem:**
- URL shows `#main-content` when navigating
- LocaNext button has "Skip to Main Content" when tabbed (accessibility feature but weird UX)

**Fix:**
- Added `hashchange` listener in onMount that removes `#main-content` from URL
- Uses `history.replaceState()` to clean URL without affecting browser history
- SkipToContent behavior preserved for accessibility (only visible on keyboard focus)
- File: `+layout.svelte` lines 185-193

---

### ~~UI-101: Merge User Button into Settings~~ ✅ ALREADY FIXED
- **Reported:** 2026-01-01
- **Verified Fixed:** 2026-01-03 (Session 16)
- **Severity:** MEDIUM → CLOSED
- **Component:** +layout.svelte
- **Status:** ALREADY FIXED

**Problem:** Separate "admin/user" button and "Settings" button - confusing duplication.

**Current State:** Settings dropdown already contains:
- User profile section (name, role, opens modal)
- Preferences
- About LocaNext
- Change Password
- Logout

No separate "User" button exists. All user-related actions are in the unified Settings dropdown.

---

## ~~OPEN ISSUES - CLEANUP (LOW)~~ ✅ CLOSED (Session 16)

### ~~CLEANUP-001: Remove QuickSearch if Absorbed~~ ✅ NOT APPLICABLE
- **Reported:** 2026-01-01
- **Closed:** 2026-01-03 (Session 16)
- **Severity:** LOW → CLOSED
- **Status:** NOT APPLICABLE

**Resolution:** EP-005 audit found QuickSearch is NOT absorbed. It remains a standalone app with unique features (dictionary management, multi-game/language support). KEEP.

---

### ~~CLEANUP-002: Remove KR Similar if Absorbed~~ ✅ NOT APPLICABLE
- **Reported:** 2026-01-01
- **Closed:** 2026-01-03 (Session 16)
- **Severity:** LOW → CLOSED
- **Status:** NOT APPLICABLE

**Resolution:** EP-006 audit found KR Similar is NOT absorbed. It remains a standalone app with unique features (FAISS similarity, batch extraction, auto translate). KEEP.

---

## VERIFICATION NEEDED

The following fixes have been coded but need manual DEV testing:

| Issue | Code Status | Verification |
|-------|-------------|--------------|
| UI-084: TM Matches | ✅ FIXED | Click row → check side panel |
| UI-085: Cell Height | ✅ FIXED | Load file with color tags → check heights |
| FEAT-002: Color Picker | ✅ ADDED | Edit mode → select text → right-click |

**To verify:** Start DEV servers, login, test each feature manually.

---

## RECENTLY FIXED (Dec 31)

### UI-084: TM Matches Not Showing in Side Panel ✅ FIXED

- **Reported:** 2025-12-31
- **Fixed:** 2025-12-31
- **Severity:** HIGH (Core feature broken)
- **Status:** FIXED
- **Component:** LDM.svelte

**Problem:** Clicking on a row didn't show TM matches in the TMQAPanel.

**Root Cause:** `loadTMMatchesForRow()` was calling non-existent API endpoints:
- `GET /api/ldm/files/{id}/active-tms` → 404
- `POST /api/ldm/tm/search` → 405

**Fix:** Updated to use working `GET /api/ldm/tm/suggest` endpoint (same as VirtualGrid).

**File:** `locaNext/src/lib/components/apps/LDM.svelte` lines 287-337

---

### UI-086: ColorText Not Rendering in Target Cell ✅ FIXED

- **Reported:** 2026-01-01
- **Fixed:** 2026-01-01
- **Severity:** HIGH
- **Status:** FIXED
- **Component:** colorParser.js

**Problem:** Target column showed raw `<PAColor0xfff3d900>` tags instead of colored text.

**Root Causes Found:**
1. HTML-escaped tags: `&lt;PAColor...&gt;` not being unescaped before parsing
2. Unclosed tags: `<PAColor...>text` without closing `<PAOldColor>` tag

**Fix:** Updated `colorParser.js` to:
1. Unescape HTML entities (`&lt;` → `<`) before parsing
2. Handle unclosed color tags (color extends to end of text)

**File:** `locaNext/src/lib/utils/colorParser.js`

---

### BUG-001: Browser Freeze - WebSocket Infinite Loop ✅ FIXED

- **Reported:** 2026-01-01
- **Fixed:** 2026-01-01
- **Severity:** CRITICAL (Chrome freezes, RAM/CPU spike)
- **Status:** FIXED
- **Component:** VirtualGrid.svelte:1782-1790

**Problem:** `$effect` at line 1782 called `joinFile(fileId)` without tracking previous value. Ran on EVERY state change → infinite WebSocket spam → browser freeze.

**Symptoms:**
- Chrome tab freezes
- RAM/CPU 100%
- Backend logs: `[WS] Not connected! Cannot send: ldm_join_file` (repeating)

**Fix:** Merged with the effect at line 1793 that already had `previousFileId` tracking. Now both operations (search reset + WebSocket subscribe) only run when `fileId` actually changes.

**File:** `locaNext/src/lib/components/ldm/VirtualGrid.svelte` lines 1781-1802

**Safeguard:** Added CS-015 to DEV_MODE_PROTOCOL.md

---

### UI-085: Cell Height Not Accounting for Color Tags ✅ FIXED

- **Reported:** 2025-12-31
- **Fixed:** 2025-12-31
- **Severity:** MEDIUM (Visual)
- **Status:** FIXED
- **Component:** VirtualGrid.svelte

**Problem:** Cell height was estimated using raw text length including color tags, but rendered text is shorter.

**Fix:** Import `stripColorTags` and strip color tags before calculating text length in `estimateRowHeight()`.

**File:** `locaNext/src/lib/components/ldm/VirtualGrid.svelte` lines 19, 1475-1481

---

### FEAT-002: Color Code Editing in Edit Mode ✅ ADDED

- **Reported:** 2025-12-31
- **Implemented:** 2025-12-31
- **Severity:** ENHANCEMENT
- **Status:** DONE
- **Component:** VirtualGrid.svelte

**Feature:**
1. Live color preview below textarea when editing cells with color tags
2. Right-click context menu to apply color codes to selected text
3. 8 PAColor options: Gold, Green, Blue, Red, Purple, Orange, Cyan, Pink

**How to Use:**
1. Double-click target cell to edit
2. Select text → right-click → pick color
3. Color tag automatically wraps selected text

**Files:** VirtualGrid.svelte lines 98-113, 1058-1118, 2053-2072, 2131-2160, 2547-2665

---

## RECENTLY FIXED (Dec 30)

### UI-081: Column Resize Bar Broken with Extra Columns ✅ FIXED

- **Reported:** 2025-12-30
- **Fixed:** 2025-12-30
- **Severity:** MEDIUM (UX degradation)
- **Status:** FIXED
- **Component:** VirtualGrid.svelte

**Problem:** When user enables Index or StringID columns, the column resize bar (full-height drag handle) disappears or stops working.

**Root Cause:** The resize bar was positioned at `left: {sourceWidthPercent}%` which only accounts for source/target split, not the additional fixed-width columns.

**Fix:**
- Added `fixedColumnsBeforeSource` derived value to calculate total width of visible fixed columns (Index + StringID)
- Updated resize bar position to use `calc({fixedWidth}px + {sourceWidthPercent}%)`
- Updated `handleResize()` to calculate dynamic limits based on visible fixed columns

**Files Modified:** `VirtualGrid.svelte` lines 118-131, 1675, 1507-1546

**Verified:** Playwright test confirms resize bar at `left: calc(50% + 0px)` (0px = no fixed columns visible)

---

### UI-082: Only Source/Target Columns Are Resizable ✅ FIXED

- **Reported:** 2025-12-30
- **Fixed:** 2025-12-30
- **Severity:** MEDIUM (Feature limitation)
- **Status:** FIXED
- **Component:** VirtualGrid.svelte

**Problem:** Users could only resize the source/target column split. Other columns (Index, StringID, Reference) had fixed widths and cannot be resized.

**Fix:** Implemented multi-column resize system:
- Added state for individual column widths: `indexColumnWidth`, `stringIdColumnWidth`, `referenceColumnWidth`
- Added `startColumnResize(event, columnKey)` handler for fixed column resize
- Updated `handleResize()` to handle both percentage-based (source/target) and pixel-based (fixed columns) resize
- Added resize handles to Index, StringID, and Reference cells
- Added CSS for `.column-resize-handle` and `.resizable-column`

**Column Width Limits:**
- Index: 40-120px
- StringID: 80-300px
- Reference: 150-500px

**Files Modified:** `VirtualGrid.svelte` lines 118-124, 1486-1546, 1783-1807, 1870-1895, 2074-2104

**Verified:** Playwright test confirms resize drag changes source width from 345px to 390px

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

## FIXED - 2026-01-03 (Session 21)

### UI-090: Column Resize Breaks After Adding Custom Column ✅ FIXED
- **Reported:** 2026-01-03 (Session 21)
- **Fixed:** 2026-01-03
- **Severity:** MEDIUM
- **Status:** FIXED
- **Component:** VirtualGrid.svelte
- **Problem:** After adding a custom column (index, stringId), original Source/Target columns couldn't be resized
- **Root Cause:** Source/Target cells used `flex: 0 0 {percent}%` which took percentage of FULL container, not remaining space after fixed columns. This caused resize bar position mismatch.
- **Fix:** Changed to flex-grow ratios `flex: {ratio} 1 0` so cells share remaining space proportionally
- **File:** VirtualGrid.svelte lines 2118-2122, 2152, 2172
- **Tests:** 156 passed, 14 skipped

### SYNC-005: Hierarchy Sync (Platform/Project/Folder) ✅ FIXED
- **Reported:** 2026-01-03 (Session 20)
- **Fixed:** 2026-01-04
- **Severity:** HIGH
- **Status:** FIXED
- **Component:** sync.py
- **Problem:** Only files could be synced. Path hierarchy (platform/project/folder) was missing in offline mode.
- **Root Cause:** `_sync_file_to_offline()` only saved file + rows, not parent entities.
- **Fix:**
  - File sync now syncs Platform → Project → Folder → File (in order)
  - Added `_sync_folder_to_offline()` for folder sync with all files
  - Added `_sync_folder_hierarchy()` for recursive parent folder sync
  - Updated `_sync_project_to_offline()` to include all folders
  - Added "folder" entity type to subscribe handler
- **Rule Added:** Server = source of truth for PATH. Offline structure edits revert on sync.
- **File:** sync.py lines 510-600, 785-848
- **Docs:** OFFLINE_ONLINE_MODE.md updated with Path Hierarchy Rule
- **Tests:** 156 passed, 14 skipped

### UI-091: Sync Registry Delete Flickers ✅ FIXED (Svelte 5 Pattern)
- **Reported:** 2026-01-04 (Session 21)
- **Fixed:** 2026-01-04
- **Severity:** LOW
- **Status:** FIXED
- **Component:** SyncStatusPanel.svelte
- **Problem:** Delete item from sync registry → item reappears briefly → gone on refresh
- **Root Cause:** Missing Svelte 5 proper patterns:
  1. No key in `{#each}` loop → bad DOM diffing
  2. Optimistic delete conflicted with store-triggered re-renders
- **Fix (Svelte 5 Best Practices):**
  ```svelte
  // 1. Track deleting items with $state Set
  let deletingIds = $state(new Set());

  // 2. Use $derived for filtered list
  let visibleSubscriptions = $derived(
    subscriptions.filter(s => !deletingIds.has(s.id))
  );

  // 3. Use key in {#each} for proper diffing
  {#each visibleSubscriptions as sub (sub.id)}

  // 4. Use Svelte 5 array mutation (splice)
  subscriptions.splice(index, 1);
  ```
- **File:** SyncStatusPanel.svelte lines 40, 132-160, 251
- **Tests:** 156 passed, 14 skipped

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

### UI-066: Placeholder Rows Have Wrong Column Count ✅ FIXED
- **Status:** FIXED
- **Assessed:** 2025-12-28
- **Fixed:** 2025-12-29
- **Problem:** Placeholder rows show single shimmer instead of matching columns
- **Fix:** Updated placeholder row to render same column structure as actual rows:
  - Row number (conditional)
  - StringID with shimmer (conditional)
  - Source with shimmer
  - Target with shimmer
  - Reference with shimmer (conditional)
- **File:** VirtualGrid.svelte lines 1713-1733

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

### UI-069: QA Icon Position Conflicts with Edit Icon ✅ FIXED
- **Status:** FIXED
- **Assessed:** 2025-12-28
- **Fixed:** 2025-12-29
- **Problem:** QA warning icon and edit icon can overlap
- **Fix:**
  - Moved QA icon left: `right: 1.75rem` (was 1.5rem)
  - Added `z-index: 1` to QA icon
  - Added `.cell.target.qa-flagged .edit-icon { right: 0.35rem }` rule
- **Result:** Icons now have ~10px gap, no overlap
- **File:** VirtualGrid.svelte lines 2280-2291

---

## LOW - COSMETIC ISSUES

### UI-070: Empty Divs in DOM ✅ FIXED
- **Status:** FIXED
- **Assessed:** 2025-12-28
- **Verified:** 2025-12-29
- **Was:** 9 empty divs → **Now:** 4 (acceptable)
- **Impact:** Reduced DOM bloat

### UI-071: Reference Column "No match" Styling ✅ FIXED
- **Status:** FIXED
- **Assessed:** 2025-12-28
- **Fixed:** 2025-12-29
- **Problem:** "No match" text could be clearer (was just "-")
- **Fix:** Changed "-" to "No match" with smaller italic text and 0.7 opacity
- **File:** VirtualGrid.svelte lines 1824-1825, 2332-2338

### UI-072: TM Empty Message Styling ✅ FIXED
- **Status:** FIXED
- **Assessed:** 2025-12-28
- **Fixed:** 2025-12-29
- **Problem:** Empty state messages lacked visual hierarchy
- **Fix:** Added icons to all empty states in TMQAPanel:
  - TM: Search icon + "Select a row to see TM matches"
  - TM empty: Search icon + "No TM matches found" (muted)
  - QA: Warning icon + "Select a row to see QA issues"
  - QA clean: Checkmark icon + "No QA issues" (green)
- **File:** TMQAPanel.svelte lines 110-114, 143-147, 166-169, 180-183

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

## FIXED THIS SESSION (2026-01-01)

| Issue | Fix |
|-------|-----|
| BUG-001 | Browser freeze - WebSocket infinite loop fixed |
| UI-086 | ColorText in target - escaped/unclosed tags handled |
| UI-093 | Preview removed from edit mode |
| WYSIWYG | Colors visible during editing (no raw tags) |
| Cursor | I-beam cursor in edit mode |

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

*Updated 2026-01-01 | 43 Issues FIXED (incl. 3 CI/CD) | 12 OPEN*
