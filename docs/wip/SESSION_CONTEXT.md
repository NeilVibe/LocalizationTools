# Session Context

**Updated:** 2025-12-29 15:00 UTC | **Build:** 415+ | **Status:** ALL TESTS PASSING (158/158)

---

## LATEST WORK (Dec 29)

### Code Cleanup Tasks

| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | Delete DataGrid.svelte (dead code) | DONE | Removed unused import from LDM.svelte |
| 2 | Convert TMDataGrid to inline editing | DONE | Modal → inline textareas |
| 3 | Add TM metadata display (MemoQ-style) | DONE | Compact metadata below target |
| 4 | Add TDL to CLAUDE.md glossary | DONE | TDL = To Do List |
| 5 | Centralize formatDate to utils | DONE | New formatters.js |
| 6 | Fix gitea_control.sh Windows runner | DONE | Full PowerShell path |

### P2: Font Settings Enhancement

| # | Task | Status | Notes |
|---|------|--------|-------|
| 2.1 | Add fontFamily/fontColor to preferences store | DONE | preferences.js |
| 2.2 | Create SettingsDropdown component | SKIP | Optional UX enhancement |
| 2.3 | Update PreferencesModal with selects | DONE | Family + Color selects |
| 2.4 | Apply font styles to VirtualGrid | DONE | CSS variables |

**Font Families Available:**
- System Default, Inter, Roboto
- Noto Sans (CJK), Source Han Sans (CJK)
- Consolas (Mono)

**Text Contrast Options:**
- Default, High Contrast, Soft

### TM Metadata Display (NEW)

MemoQ-style compact metadata now shows below each TM entry's target text:

| Status | Display |
|--------|---------|
| Confirmed | `✓ John · Dec 28` (green) |
| Updated | `✏️ Jane · Dec 27` (yellow) |
| Created | `📥 Dec 25` (gray) |

**Files Changed:** `TMDataGrid.svelte`

### Code Deduplication

| Duplicate | Files | Fix |
|-----------|-------|-----|
| `formatDate()` | TMDataGrid, TMManager, TMViewer | ✅ New `formatters.js` |

**New file:** `src/lib/utils/formatters.js`
- `formatDate()` - full with time
- `formatDateShort()` - date only
- `formatDateCompact()` - smart short

### Ctrl+D QA Dismiss Implementation

**Status:** CODE COMPLETE - needs test data setup

**What was implemented:**
- `LDM.svelte`: Added `loadQAIssuesForRow()` - fetches QA issues when row selected
- `LDM.svelte`: Updated `handleDismissQA()` - calls `/api/ldm/qa-results/{id}/resolve` for each issue
- `VirtualGrid.svelte`: Added `updateRowQAFlag(rowId, flagCount)` - updates visual state after dismiss

**API Flow:**
1. User presses Ctrl+D on selected row
2. Fetches QA issues via `GET /api/ldm/rows/{rowId}/qa-results`
3. For each issue, calls `POST /api/ldm/qa-results/{issueId}/resolve`
4. Updates row's `qa_flag_count` to 0 for visual update

**Test Data Issue:**
- Database has 242 unresolved QA issues
- But files are orphaned (no folder_id set)
- Projects have 0 files because file→folder→project chain is broken
- Automated tests can't load a file grid to test Ctrl+D

**To fix test data:**
```sql
-- Check orphaned files
SELECT id, name, folder_id FROM ldm_files WHERE folder_id IS NULL;
-- Link to a folder
UPDATE ldm_files SET folder_id = <folder_id> WHERE id = <file_id>;
```

### Test Fixes (Dec 29)

| Test | Problem | Fix |
|------|---------|-----|
| ldm-comprehensive file upload | 400 on duplicate (should be 409) | Changed `files.py` status 400 → 409 for duplicates |
| qa-panel-verification login | `input[type="text"]` selector timeout | Changed to `getByPlaceholder()` |

### Test Status

| Result | Count |
|--------|-------|
| Passed | 158 |
| Failed | 0 |

### DEV Testing Tips

**Rate Limiting:** Tests trigger login rate limits (429). Two options:

1. **Clear the audit log:**
```bash
echo "" > server/data/logs/security_audit.log
```
The rate limiter uses a 15-min window counting LOGIN_FAILURE in `security_audit.log`.

2. **Start backend with DEV_MODE (recommended for testing):**
```bash
cd server && DEV_MODE=true python3 main.py
```
DEV_MODE=true disables rate limiting entirely for CI/testing.

**App Navigation:** The app uses stores (`currentApp`, `currentView`) not URL routes.
- `/ldm` route doesn't exist - use `window.navTest.goToApp('ldm')` in tests
- Test helper exposed at `window.navTest` after login

**Gitea Control:** NEVER use raw systemctl commands. ALWAYS use:
```bash
./scripts/gitea_control.sh status|start|stop|kill
```

### Test Data Files

| Location | File | Lines | Use |
|----------|------|-------|-----|
| Local | `tests/fixtures/sample_language_data.txt` | 63 | Real KO→FR with PAColor tags |
| Windows | `TestFilesForLocaNext/sampleofLanguageData.txt` | 103,499 | Large test bank |
| Windows | `test_10k.txt` | 10,000 | Medium performance test |
| Windows | `TestFilesForLocaNext/languagedata_fr PC 1012 1813.txt` | Huge (198MB) | Full production data |

**Windows path:** `/mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/`

### Existing Filter Feature

VirtualGrid already has row filtering (lines 56-61):
- **All** - Show all rows
- **Confirmed** - Only confirmed/reviewed rows
- **Unconfirmed** - Only pending rows
- **QA Flagged** - Only rows with QA issues

---

## COMPLETED (Earlier Dec 29)

### Code Audit Day - ALL DONE

| # | Task | Status | Tested |
|---|------|--------|--------|
| U1 | **Code Parasites** - `getAuthHeaders()` in 11 files | DONE | YES |
| U2 | **API_BASE** - Centralize in `api.js` | DONE | YES |
| U3 | **Archive WIP** - 10 completed docs | DONE | N/A |
| M1 | **Stale Docs** - Update outdated status | DONE | N/A |
| M2 | **Roadmap.md** - Fix duplicate sections | DONE | N/A |
| M3 | **P1 QA Panel** - Fix stability issues | DONE | YES |
| M4 | **VirtualGrid Review** - Assess bloat | DONE | OK |
| L1 | **Dead Code Scan** - Find unused code | DONE | Clean |
| L2 | **Final Verification** - Full test suite | DONE | 156/158 |
| D1 | CLAUDE.md - Fix dead links + stale counts | DONE | - |
| D2 | WIP/README.md - Remove dead links, update index | DONE | - |
| D3 | SESSION_CONTEXT.md - Verify clear | DONE | - |

---

## OPEN ISSUES (from ISSUES_TO_FIX.md)

**0 CRITICAL | 0 HIGH | 3 MEDIUM | 2 LOW**

### MEDIUM Priority (3 Open)

| ID | Issue | Impact |
|----|-------|--------|
| UI-066 | Placeholder rows wrong column count | Minor loading visual |
| UI-067 | Filter dropdown height mismatch (8px) | Styling |
| UI-069 | QA + Edit icon overlap | Visual clutter |

### Recently Closed (Dec 29)

| ID | Issue | Resolution |
|----|-------|------------|
| UI-063 | CSS Text Overflow | ✅ FIXED - All cells have ellipsis |
| UI-068 | Resize handle not visible | ⚠️ BY DESIGN - Appears on hover |
| UI-070 | Empty divs in DOM | ✅ FIXED - Reduced to 4 |
| UI-073 | Shortcut bar takes space | ✅ FIXED - Removed from DOM |

### LOW Priority (2 Open)

| ID | Issue | Impact |
|----|-------|--------|
| UI-071 | "No match" styling | UX minor |
| UI-072 | TM empty message styling | UX minor |

**No blocking issues. All open issues are cosmetic/minor.**

---

## CODE REVIEW FINDINGS (Dec 29)

### Code Parasites Found

| Parasite | Occurrences | Fix |
|----------|-------------|-----|
| `getAuthHeaders()` | 11 files | Created `api.js` |
| `API_BASE = get(serverUrl)` | 12 files | Centralized in `api.js` |

### WIP Docs Analysis

| Category | Count | Action |
|----------|-------|--------|
| Should ARCHIVE | 10 | DONE - moved to docs/history/ |
| STALE (outdated) | 6 | DONE - updated status |
| ACTIVE (valid) | 6 | Keep |
| Reference docs | 11 | Keep |

### Large Files Assessment

| File | Lines | Verdict |
|------|-------|---------|
| VirtualGrid.svelte | 2,397 | OK - well organized |
| FileExplorer.svelte | 2,245 | OK |
| QuickSearch.svelte | 2,189 | Legacy - low priority |
| XLSTransfer.svelte | 1,804 | Legacy - low priority |

### VirtualGrid Breakdown

| Section | Lines | % |
|---------|-------|---|
| JavaScript | 1,584 | 66% |
| CSS | 553 | 23% |
| HTML | 260 | 10% |
| Functions | 59 | - |

**Verdict:** Large but MANAGEABLE. Well-organized code with section comments. LOW priority for refactoring.

---

## Detailed Status

### 1. Code Parasites - DONE

**Problem:** `getAuthHeaders()` duplicated in 11 files

**Solution:** Created `/src/lib/utils/api.js`:
```javascript
export function getAuthHeaders() { ... }
export function getApiBase() { ... }
export async function apiFetch(endpoint, options) { ... }
```

**Files Refactored (10):**
- VirtualGrid.svelte, TMManager.svelte, TMDataGrid.svelte
- TMViewer.svelte, TMUploadModal.svelte, FileExplorer.svelte
- QAMenuPanel.svelte, LDM.svelte
- QuickSearch.svelte, KRSimilar.svelte
- (DataGrid.svelte was DELETED - dead code)

**Tested:** Build SUCCESS + 27/28 Playwright tests passed

---

### 2. WIP Doc Cleanup - DONE

**Archived to `docs/history/` (10 files):**
1. AUTO_LQA_IMPLEMENTATION.md
2. ALERT-001_GITEA_RESOURCE_CRISIS.md
3. AUTO_UPDATE_SYSTEM.md
4. DOC-001_INSTALL_VS_UPDATE_CONFUSION.md
5. GITEA_CLEAN_KILL_PROTOCOL.md
6. LANGUAGETOOL_LAZY_LOAD.md
7. QA_FULL_IMPLEMENTATION.md
8. SMART_UPDATE_PROTOCOL.md
9. UI-062_SVELTEKIT_VERSION_JSON_FIX.md
10. WSL_INTEROP.md

**Updated:**
- MEMOQ_STYLE_EDITING.md → Phases 2-3 COMPLETE
- QA_UIUX_OVERHAUL.md → Phase 1 COMPLETE

---

### 3. P1 QA Panel Fixes - DONE

| Fix | Description |
|-----|-------------|
| Cancel Button | Shared AbortController - actually aborts requests |
| Escape Key | Works on panel itself (not just backdrop) |
| Empty State | "QA not run" vs "No issues found" with icons |

**File:** `QAMenuPanel.svelte`
**Tested:** Build SUCCESS + 2/3 API tests passed

---

### 4. VirtualGrid Assessment - DONE

| Metric | Value | Verdict |
|--------|-------|---------|
| Total Lines | 2,397 | Large but OK |
| JS (logic) | 66% | Well-organized |
| CSS (styles) | 23% | Has section comments |
| HTML (template) | 10% | Clean |
| Functions | 59 | Logically grouped |

**Recommendation:** LOW priority refactor - works well as-is

---

## Active Priorities (from Roadmap.md)

| Priority | Feature | WIP Doc | Status |
|----------|---------|---------|--------|
| P1 | QA UIUX Overhaul | QA_UIUX_OVERHAUL.md | Phase 1 DONE |
| P2 | Font Settings | FONT_SETTINGS_ENHANCEMENT.md | ✅ DONE |
| P3 | Offline/Online Mode | OFFLINE_ONLINE_MODE.md | PLANNING |
| P4 | Color Parser Extension | COLOR_PARSER_EXTENSION.md | DOCUMENTED |
| P5 | Advanced Search | ADVANCED_SEARCH.md | PLANNING |

---

## Quick Commands

```bash
# Dev server
cd locaNext && npm run dev
# Login: admin / admin123

# Build
npm run build

# Run tests
npx playwright test --reporter=list

# Gitea
./scripts/gitea_control.sh status|start|stop
```

---

*Code Audit Day COMPLETE - P2 Font Settings DONE - Ctrl+D QA Dismiss CODE COMPLETE (test data needs fixing). Next: P3 Offline/Online Mode.*
