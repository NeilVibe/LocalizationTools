# Issues To Fix

**Purpose:** Track open bugs, features, and tasks in LocaNext
**Last Updated:** 2025-12-18 08:00 KST | **Build:** 297 (pending)

---

## Quick Summary

| Status | Count |
|--------|-------|
| **Open Bugs** | **0** |
| **Open Features (HIGH)** | **0** |
| **Open Tasks (HIGH)** | **0** |
| Fixed (archived) | 53 |

**✅ ALL ISSUES COMPLETE - BUG-020 + FEAT-001 done!**

---

## Priority Order

```
ALL ISSUES COMPLETE! ✅

ONGOING (LOW):
├── P25: LDM UX Overhaul (85% done)
└── BUG-021: Seamless UI during auto-update (optional)

RECENTLY FIXED:
├── BUG-020: ✅ memoQ-style metadata (is_confirmed, confirmed_by, confirmed_at, updated_at, updated_by)
├── FEAT-001: ✅ TM Metadata column enhancement (7 options in dropdown)
├── BUG-016: ✅ Global toast notifications for Task Manager events
├── FEAT-003: ✅ TM Viewer (paginated, sortable, searchable, inline edit)
├── FEAT-002: ✅ TM Export (TEXT/Excel/TMX with column selection)
├── TASK-002: ✅ Full E2E tests for all 3 engines (20 tests total)
├── TASK-001: ✅ TrackedOperation for ALL long processes
└── BUG-022: ✅ Now uses TMSyncManager.sync() (incremental)
```

---

## ✅ TASK-001: TrackedOperation for ALL Long Processes [FIXED]

- **Status:** [x] Fixed
- **Priority:** Was CRITICAL
- **Reported:** 2025-12-17
- **Fixed:** 2025-12-17
- **Component:** server/tools/ldm/api.py, server/tools/ldm/pretranslate.py

### What Was Fixed

All long-running operations now use `TrackedOperation` for UI progress tracking.

### Current State (After Fix)

| Operation | TrackedOperation? | File |
|-----------|-------------------|------|
| `build_tm_indexes` | ✅ YES | api.py:1268 |
| `pretranslate_file` | ✅ YES | api.py:1414 |
| `upload_file` | ✅ YES | api.py:538 |
| `upload_tm` | ✅ YES | api.py:1024 |
| Auto-sync (Standard) | ✅ YES | pretranslate.py:157 |
| Auto-sync (XLS Transfer) | ✅ YES | pretranslate.py:255 |
| Auto-sync (KR Similar) | ✅ YES | pretranslate.py:352 |

### Files Modified

1. `server/tools/ldm/api.py` - pretranslate_file, upload_file, upload_tm
2. `server/tools/ldm/pretranslate.py` - All 3 engine auto-sync sections

---

## ✅ BUG-022: Incremental Update [FIXED]

- **Status:** [x] Fixed
- **Priority:** Was CRITICAL
- **Reported:** 2025-12-17
- **Fixed:** 2025-12-17
- **Component:** server/tools/ldm/pretranslate.py

### What Was Fixed

Now using `TMSyncManager.sync()` instead of `TMIndexer.build_indexes()` for incremental updates.

### Performance Improvement

| TM Size | Before (Full Rebuild) | After (Incremental) |
|---------|----------------------|---------------------|
| 1,000 entries | ~10 seconds | ~milliseconds |
| 10,000 entries | ~1-2 minutes | ~1-2 seconds |
| 50,000 entries | ~5-10 minutes | ~5-10 seconds |

### Files Modified

1. `server/tools/ldm/pretranslate.py:157-167` (Standard TM) ✅
2. `server/tools/ldm/pretranslate.py:244-252` (XLS Transfer) ✅
3. `server/tools/ldm/pretranslate.py:326-334` (KR Similar) ✅

### Code After Fix

```python
# NOW FIXED - pretranslate.py uses incremental sync
if needs_rebuild:
    from server.tools.ldm.tm_indexer import TMSyncManager
    sync_manager = TMSyncManager(self.db, tm_id)
    sync_result = sync_manager.sync()  # ← INCREMENTAL! Only new/changed
    logger.info(f"TM sync complete: INSERT={sync_result['stats']['insert']}, ...")
```

---

## CRITICAL: Task Manager Integration

### TASK-002: Full E2E Tests for All Pretranslation Engines [COMPLETE ✅]
- **Status:** [x] Complete
- **Priority:** Was CRITICAL
- **Reported:** 2025-12-17
- **Completed:** 2025-12-17
- **Component:** tests/fixtures/stringid/

**All 3 engines now have comprehensive TRUE E2E tests.**

**Required Tests:**

#### Standard TM E2E:
```
1. Basic pretranslation (exact match)
2. Fuzzy matching at threshold (92%)
3. StringID variations (CRITICAL):
   ├── Same source "저장" with different StringIDs
   ├── UI_BUTTON_SAVE → "Save"
   ├── UI_MENU_SAVE → "Save Game"
   └── Verify CORRECT target selected by StringID
4. Duplicate handling:
   ├── Same source, same StringID → Use most recent
   ├── Same source, different StringID → Keep both (PKL has variations)
   └── PKL structure: {source: {stringid1: target1, stringid2: target2}}
5. Empty source handling
6. Unicode handling (Korean, Japanese, Chinese)
7. Multi-line text
8. Large TM (5000+ entries) performance
```

#### XLS Transfer E2E:
```
1. Basic translation with split/whole modes
2. Code preservation:
   ├── {ItemID}, {Count}, {Name} placeholders
   ├── <PAColor=...>, <PAFont=...> tags
   ├── \n newlines
   └── Numeric values
3. Threshold sensitivity
4. Triangle markers (▶) handling
5. Line-by-line vs whole text matching
6. Large dictionary performance
```

#### KR Similar E2E:
```
1. Basic similarity search
2. Structure adaptation:
   ├── Number alignment
   ├── Punctuation preservation
   └── Spacing adaptation
3. Triangle markers (▶) line-by-line
4. Threshold sensitivity
5. Split vs whole mode selection
6. Korean-specific patterns
```

**Test Data Requirements:**
- Real TM with 5000+ entries
- Multiple StringID variations per source
- Game-style codes and patterns
- Korean/English language pairs

**Files:**
- `tests/fixtures/stringid/true_e2e_standard.py` ✅ 6 tests
- `tests/fixtures/stringid/true_e2e_xls_transfer.py` ✅ 7 tests
- `tests/fixtures/stringid/true_e2e_kr_similar.py` ✅ 7 tests (NEW)
- `tests/fixtures/stringid/stringid_test_data.py` ✅ Test data module

---

## Open Bugs

### ✅ BUG-016: Global Toast Notifications [COMPLETE]
- **Status:** [x] Complete
- **Priority:** Was LOW
- **Reported:** 2025-12-17
- **Completed:** 2025-12-18
- **Component:** Frontend (Svelte)

**What Was Implemented:**
- ✅ Global toast notifications appear on ANY page when operations start/complete/fail
- ✅ Toast store for managing notifications (`toastStore.js`)
- ✅ GlobalToast component in layout (always visible)
- ✅ WebSocket event listeners for operation_start, operation_complete, operation_failed
- ✅ Different toast durations by type (3s start, 5s complete, 8s error)
- ✅ Slide-in animation for toasts

**Files Created/Modified:**
- `locaNext/src/lib/stores/toastStore.js` - NEW: Toast store with convenience functions
- `locaNext/src/lib/components/GlobalToast.svelte` - NEW: Global toast container
- `locaNext/src/routes/+layout.svelte` - Added GlobalToast component

**Usage Example:**
```javascript
import { toast } from '$lib/stores/toastStore.js';

// Simple toasts
toast.success('Operation completed');
toast.error('Something went wrong');
toast.info('Processing...');

// Task Manager specific (auto-triggered via WebSocket)
toast.operationStarted('Pretranslate', 'LDM');
toast.operationCompleted('Pretranslate', 'LDM', '5s');
toast.operationFailed('Pretranslate', 'LDM', 'File not found');
```

---

### ✅ BUG-020: memoQ-Style Metadata [COMPLETE]
- **Status:** [x] Complete
- **Priority:** Was HIGH
- **Reported:** 2025-12-17
- **Completed:** 2025-12-18
- **Component:** Database Schema + TM Manager + TM Viewer

**What Was Implemented:**
- ✅ Added `updated_at`, `updated_by` columns for modification tracking
- ✅ Added `confirmed_at`, `confirmed_by`, `is_confirmed` columns for confirmation workflow
- ✅ Added index on `(tm_id, is_confirmed)` for filtering
- ✅ Added `confirm_entry()` and `bulk_confirm_entries()` to TM Manager
- ✅ Added API endpoints: `POST /tm/{tm_id}/entries/{entry_id}/confirm` and `POST /tm/{tm_id}/entries/bulk-confirm`
- ✅ Updated TM Viewer with confirm button, confirmed row styling, new metadata options

**memoQ-Style Workflow:**
```
1. User views TM entries in TM Viewer
2. User clicks Confirm button on entry → Entry marked as confirmed
3. Confirmed entries show green highlight and checkmark icon
4. Metadata dropdown shows: Confirmed, Updated At, Confirmed At, Confirmed By
5. Can sort by confirmation status
```

**Files Modified:**
- `server/database/models.py` - Added 5 new columns + index
- `server/tools/ldm/tm_manager.py` - Added confirm methods, updated return dicts
- `server/tools/ldm/api.py` - Added confirm endpoints
- `locaNext/src/lib/components/ldm/TMViewer.svelte` - Confirm button, green styling, metadata options

---

### BUG-021: Seamless UI During Auto-Rebuild [LOW]
- **Status:** [ ] Open
- **Priority:** LOW
- **Reported:** 2025-12-17
- **Component:** Frontend

**Problem:** When TM rebuilds, UI should show brief indicator without blocking workflow.

**Expected Behavior:**
```
User modifies TM entry
    │
    └── TM marked dirty (updated_at changes)

User clicks Pretranslate
    │
    ├── Check: Is TM stale?
    │   └── YES → Show toast "Updating TM..."
    │             → Rebuild in background
    │             → Update toast "TM ready"
    │             → Proceed with pretranslation
```

**Files:**
- Frontend components (Svelte)
- `server/tools/ldm/api.py`

---

## HIGH Priority Features

### ✅ FEAT-001: TM Metadata Column Enhancement [COMPLETE]
- **Status:** [x] Complete
- **Priority:** Was HIGH
- **Reported:** 2025-12-17
- **Completed:** 2025-12-18
- **Component:** TM Viewer

**Description:** Enhanced metadata column with 7 dropdown options.

**Implemented Features:**
- ✅ ONE metadata column with dropdown selector
- ✅ Sort arrows (↑↓) on each column header for asc/desc
- ✅ All sortable columns

**Dropdown Options (7 total):**
1. StringID (default)
2. Confirmed (Yes/No)
3. Created At
4. Created By
5. Updated At
6. Confirmed At
7. Confirmed By

**Files:**
- `locaNext/src/lib/components/ldm/TMViewer.svelte` - metadataOptions array, getMetadataValue()

---

### ✅ FEAT-002: TM Export Options [COMPLETE]
- **Status:** [x] Complete
- **Priority:** Was HIGH
- **Reported:** 2025-12-17
- **Completed:** 2025-12-18
- **Component:** TM System

**Description:** Export TM with format and column selection.

**Implemented Features:**
- ✅ TEXT (TSV) - Tab-delimited export
- ✅ Excel (.xlsx) - Formatted with headers, freeze panes
- ✅ TMX - Industry standard with StringID properties
- ✅ Column selection (Source, Target, StringID, Created At)
- ✅ Export modal with format radio buttons

**Files Modified:**
- `server/tools/ldm/tm_manager.py` - `export_tm()`, `_export_text()`, `_export_excel()`, `_export_tmx()`
- `server/tools/ldm/api.py` - `GET /ldm/tm/{tm_id}/export` endpoint
- `locaNext/src/lib/components/ldm/TMManager.svelte` - Export modal UI

---

### ✅ FEAT-003: TM Viewer [COMPLETE]
- **Status:** [x] Complete
- **Priority:** Was HIGH (User priority)
- **Reported:** 2025-12-17
- **Completed:** 2025-12-18
- **Component:** Frontend + Backend API

**Description:** Grid viewer for TM entries with sorting and metadata.

**Implemented Features:**
1. ✅ Grid view of all TM entries (Source | Target | Metadata)
2. ✅ Sortable columns (click header for asc/desc)
3. ✅ Search/filter (source, target, StringID)
4. ✅ Pagination (50/100/200/500 per page)
5. ✅ Inline editing (double-click to edit)
6. ✅ Delete entry functionality
7. ✅ Metadata dropdown (StringID, Created At, Created By)

**API Endpoints:**
- ✅ `GET /ldm/tm/{tm_id}/entries` - Paginated entries
- ✅ `PUT /ldm/tm/{tm_id}/entries/{entry_id}` - Update entry
- ✅ `DELETE /ldm/tm/{tm_id}/entries/{entry_id}` - Delete entry

**Files Modified:**
- `server/tools/ldm/api.py` - Entry CRUD endpoints
- `server/tools/ldm/tm_manager.py` - `get_entries_paginated()`, `update_entry()`, `delete_entry()`
- `locaNext/src/lib/components/ldm/TMViewer.svelte` - NEW component
- `locaNext/src/lib/components/ldm/TMManager.svelte` - View button integration

---

## Recently Fixed (Build 297)

| ID | Description | Date | Fix |
|----|-------------|------|-----|
| **BUG-020** | memoQ-style metadata | 2025-12-18 | 5 new columns + confirm workflow + TM Viewer confirm button |
| **FEAT-001** | TM Metadata enhancement | 2025-12-18 | 7 metadata options in dropdown |
| **BUG-016** | Global Toast Notifications | 2025-12-18 | toastStore.js + GlobalToast.svelte in layout |
| **FEAT-003** | TM Viewer | 2025-12-18 | TMViewer.svelte + API endpoints (paginated, sort, search, inline edit) |
| **FEAT-002** | TM Export | 2025-12-18 | Export to TEXT/Excel/TMX with column selection |
| **TASK-002** | Full E2E tests for all 3 engines | 2025-12-17 | Created `true_e2e_kr_similar.py` (7 tests), existing 13 tests |
| **TASK-001** | TrackedOperation for ALL long processes | 2025-12-17 | Added to pretranslate, upload_file, upload_tm, auto-sync |
| **BUG-022** | Full rebuild on every sync | 2025-12-17 | Use `TMSyncManager.sync()` (incremental) |
| **BUG-013** | XLS Transfer EmbeddingsManager missing | 2025-12-17 | Created `EmbeddingsManager` class |
| **BUG-017** | KR Similar wrong interface | 2025-12-17 | Added `load_tm(tm_id: int)` |
| **BUG-018** | KR Similar search_multi_line missing | 2025-12-17 | Refactored to `find_similar()` |
| **BUG-019** | KR Similar search_single missing | 2025-12-17 | Refactored to `find_similar()` |
| **BUG-014** | No staleness check | 2025-12-17 | Added `indexed_at < updated_at` |
| **BUG-015** | No auto-update before pretranslation | 2025-12-17 | Auto-rebuild when stale |

**Full history:** [ISSUES_HISTORY.md](../history/ISSUES_HISTORY.md)

---

## Notes

### Progress Tracking System

**COMPLETE - 22 Operations Tracked**

Two tracking mechanisms (same underlying system):
1. `TrackedOperation` context manager (`server/utils/progress_tracker.py`) - Used in LDM
2. `BaseToolAPI.create_operation()` (`server/api/base_tool_api.py`) - Used in XLSTransfer, KR Similar, QuickSearch

Both write to:
- DB: `active_operations` table
- Real-time: WebSocket events (`emit_operation_start`, `emit_progress_update`, `emit_operation_complete`)
- API: `GET /api/progress/operations` - List all running operations
- Frontend: TaskManager.svelte component reads from API

**Coverage:**
| Tool | Count | Operations |
|------|-------|------------|
| LDM | 7 | upload_file, upload_tm, build_indexes, pretranslate, auto-sync (x3) |
| XLSTransfer | 5 | create_dictionary, translate_excel, check_newlines, combine_excel, newline_auto_adapt |
| KR Similar | 3 | find_similar, batch_search, build_index |
| QuickSearch | 7 | search, batch_search, build_corpus, etc. |
| **Total** | **22** | All long-running operations tracked |

### UI Blocking Policy

All long-running operations BLOCK the UI:
- TM index build → Progress modal
- TM index rebuild → "Updating TM..."
- Pretranslation → Row-by-row progress
- TM export → Progress bar
- File upload → Progress bar

### TM Auto-Update Flow

```
pretranslate(file_id, engine, tm_id)
    │
    ├── Check: tm.indexed_at < tm.updated_at?
    │   ├── YES (STALE) → Rebuild indexes
    │   │                 → Update indexed_at
    │   │                 → Proceed
    │   └── NO (FRESH) → Proceed immediately
    │
    └── Route to engine (standard/xls/kr)
```

---

*Updated 2025-12-18 11:00 KST. ALL ISSUES COMPLETE - BUG-020 + FEAT-001 done. 0 open bugs/features.*
