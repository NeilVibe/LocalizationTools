# Session Context

> Last Updated: 2026-01-01 (Session 10 - In Progress)

---

## Current State

**Build:** 424
**Status:** Session 10 - Bug Fixes + New Feature Planning

---

## SESSION 10 UPDATES

### Bug Fixes (2026-01-01)

| Bug | Issue | Fix | Status |
|-----|-------|-----|--------|
| BUG-030 | Context menu buttons not working | Store file ref before `closeContextMenu()` | ✅ FIXED |
| XML Format | Wrong field names/order | PascalCase, StrOrigin→Str→StringId, no spaces | ✅ FIXED |

### New Feature: Offline/Online Sync System

**Status:** PLANNED | **Priority:** HIGH | **Doc:** `docs/wip/OFFLINE_ONLINE_SYNC.md`

Manual on-demand sync between Online (PostgreSQL) and Offline (SQLite):

| Feature | Description |
|---------|-------------|
| Mode Toggle | Switch Online ↔ Offline in UI |
| Sync to Offline | Right-click → download to SQLite |
| Sync to Online | Right-click → upload to PostgreSQL |
| Merge | Combine changes from both directions |
| Fully Offline | Use without any server connection |

---

### ACTIVE: Phase 10 UI Overhaul

**Status:** IN PROGRESS | **Doc:** `docs/wip/PHASE_10_MAJOR_UIUX_OVERHAUL.md`

**Approach:** Recycle 90%, Restructure 10%

**Implementation Steps:**
| Step | Task | Status |
|------|------|--------|
| 1 | Navigation store + LocaNext dropdown | 🔲 TODO |
| 2 | Extract FilesPage, TMPage, GridPage | 🔲 TODO |
| 3 | Transform Files → Windows Explorer style | 🔲 TODO |
| 4 | Transform TM → Explorer pattern | 🔲 TODO |
| 5 | Polish (Properties, keyboard shortcuts) | 🔲 TODO |

**Key Transformation:**
```
BEFORE (tree view):              AFTER (Windows Explorer):
┌─────────────────────┐         ┌─────────────────────────────────┐
│ Left panel + Grid   │   →     │ Full-page explorer OR grid      │
│ (cramped)           │         │ Breadcrumb navigation           │
└─────────────────────┘         │ Double-click = enter/open       │
                                └─────────────────────────────────┘
```

---

## SESSION 9 COMPLETE

---

## SESSION 9 FINDINGS (Critical Updates)

### Backend Status Audit Results

| Feature | Backend | Frontend | Actual Status |
|---------|---------|----------|---------------|
| **5-Tier Cascade TM** | ✅ Complete | ✅ Used in TM panel | **WORKING** |
| **Glossary Extractor** | ✅ Complete | ✅ Context menu | **WORKING** |
| **Standard Pretranslate** | ✅ Complete | ❌ No modal | Need UI |
| **XLS Pretranslate** | ✅ Complete | ❌ No modal | Need UI |
| **KR Similar Pretranslate** | ✅ Complete | ❌ No modal | Need UI |
| **StringID Variations** | ✅ Complete | ✅ Auto-handled | **WORKING** |
| **Merge (P3)** | ✅ Complete | ✅ Context menu | **WORKING** |
| **Convert (P4)** | ✅ Complete | ✅ Context menu | **WORKING** |

### StringID Handling - FULLY ACTIVE ✅

| Stage | Status | Location |
|-------|--------|----------|
| TM Upload | ✅ | `tm_crud.py:34` - `stringid_col` param + `mode="stringid"` |
| Index Building | ✅ | `indexer.py:261-278` - Stores variations structure |
| TM Search | ✅ | `searcher.py:113-130` - Returns all StringID variations |
| Pretranslation | ✅ | `pretranslate.py:209-225` - Matches by StringID first |

### 5-Tier Cascade - FULLY IMPLEMENTED ✅

Location: `server/tools/ldm/indexing/searcher.py`

| Tier | Name | Method | Threshold |
|------|------|--------|-----------|
| 1 | Perfect Whole Match | Hash lookup | 100% |
| 2 | Whole Embedding | FAISS search | ≥92% |
| 3 | Perfect Line Match | Hash lookup | 100% |
| 4 | Line Embedding | FAISS search | ≥92% |
| 5 | N-gram Fallback | Jaccard similarity | ≥92% |

### Issue Reclassification

**CLOSED - Already Working:**
- ~~FEAT-003: 5-Tier Cascade TM~~ → Already implemented
- ~~FEAT-004: Create Glossary~~ → Already working (FileExplorer context menu)

**RECLASSIFIED - Frontend Only:**
- FEAT-005/006/007 → Now: **TM-UI-001: Pretranslation Modal**

---

## NEW: TM UI/UX OVERHAUL

### TM-UI-001: Unified TM Panel

**Goal:** Single, unified TM management interface with ALL features.

**Current Problems:**
1. TM button in toolbar + TM tab in left panel (duplicate)
2. Threshold is hardcoded (92%) - user can't adjust
3. No pretranslation UI (backend exists, no frontend)
4. TM assignment to project is unclear

**Features Needed:**

```
┌─────────────────────────────────────────────────────────────┐
│  TRANSLATION MEMORIES                            [+ New TM] │
├─────────────────────────────────────────────────────────────┤
│  ● BDO_EN_Main (45,230 entries) ─── Active for: Project X   │
│    Mode: StringID │ Last updated: 2h ago                    │
│    [Activate] [Assign] [Edit] [Delete] [Export]             │
├─────────────────────────────────────────────────────────────┤
│  SETTINGS                                                   │
│  Match Threshold: [━━━━━●━━━] 92%  (50% - 100%)            │
│  [ ] Show matches below threshold (grayed)                  │
└─────────────────────────────────────────────────────────────┘
```

### TM-UI-002: Pretranslation Modal

**Trigger:** Right-click file → "Pretranslate..."

```
┌─────────────────────────────────────────────────────────────┐
│                    PRETRANSLATE FILE                        │
├─────────────────────────────────────────────────────────────┤
│  File: game_strings.xlsx (12,450 rows)                      │
│                                                             │
│  TM: [▼ BDO_EN_Main (45,230 entries)              ]        │
│                                                             │
│  Engine:                                                    │
│  ● Standard (TM 5-Tier Cascade)                             │
│  ○ XLS Transfer (code preservation)                         │
│  ○ KR Similar (structure adaptation)                        │
│                                                             │
│  Threshold: [━━━━━●━━━] 92%                                │
│                                                             │
│  [x] Skip rows with existing translation                    │
│                                                             │
│                    [Cancel]  [⚡ Pretranslate]              │
└─────────────────────────────────────────────────────────────┘
```

### TM-UI-003: User-Selectable Threshold

**Applies to:**
- TM match display in side panel
- Pretranslation modal
- Global TM settings

**Implementation:**
1. Add threshold slider to TM panel settings
2. Store in user preferences
3. Pass to all TM search/pretranslate calls

---

## SESSION 9 COMPLETED TASKS

| Task | Status | Details |
|------|--------|---------|
| UI-087 | ✅ DONE | Dropdown position fixed (CSS in +layout.svelte) |
| UI-094 | ✅ DONE | TM button removed from toolbar, "Manage" button added to TM tab |
| TM-UI-003 | ✅ DONE | Threshold slider in TM tab (50-100%, stored in preferences) |
| TM-UI-002 | ✅ DONE | Enhanced unified TM panel with upload/delete/export/activate |
| TM-UI-001 | ✅ DONE | PretranslateModal.svelte + context menu integration |
| UI-095 | ✅ DONE | QA buttons removed from toolbar, context menu triggers QAMenuPanel |
| UI-097 | ✅ DONE | Display Settings button removed from LDM toolbar, use top nav Preferences |
| Endpoints | ✅ VERIFIED | TM list, TM entries, TM suggest all working |

### TM-UI-003 Implementation Details

- Added `tmThreshold` to preferences store (default 0.92)
- Added slider in FileExplorer TM tab with real-time percentage display
- Updated all TM suggest API calls to use user's threshold preference:
  - `LDM.svelte:loadTMMatchesForRow()`
  - `VirtualGrid.svelte:fetchTMSuggestions()`
  - `VirtualGrid.svelte` (confirm row TM fetch)

### TM-UI-002 Implementation Details

- Added Upload button to TM tab header (opens TMUploadModal)
- Added right-click context menu on TM items with:
  - View Entries (opens TMViewer)
  - Export TM (downloads TSV file)
  - Activate/Deactivate toggle
  - Delete TM (with confirmation)
- Active TM visual indicator (checkmark icon, "ACTIVE" badge, blue border)
- "Settings" button opens TMManager for embedding engine settings
- Imported TMUploadModal and TMViewer components into FileExplorer

### TM-UI-001 Implementation Details

- Created `PretranslateModal.svelte` component with:
  - File info display (name, row count, format)
  - TM selection dropdown (auto-selects active TM)
  - Engine selection: Standard TM, XLS Transfer, KR Similar
  - Threshold slider (50-100%, uses preference default)
  - Skip existing translations checkbox
  - Progress bar during pretranslation
  - Success state with matched/skipped/total stats
- Added "Pretranslate..." to FileExplorer context menu (highlighted blue)
- Wired to `/api/ldm/pretranslate` endpoint

### UI-095 Implementation Details

- Removed "QA On/Off" toggle button from LDM toolbar
- Removed "QA" menu button from LDM toolbar
- Context menu items (Run Line/Term Check, Grammar) dispatch `runQA` event
- Added `handleRunQA()` in LDM.svelte to open QAMenuPanel when context menu QA triggered
- Cleaned up unused icon imports (Checkmark, WarningAlt, Report)
- QA functionality still works via: File context menu → Run QA → Results in grid + TMQAPanel

### UI-097 Implementation Details

- Removed "Display Settings" button (Settings gear icon) from LDM toolbar
- Removed PreferencesModal import and component from LDM.svelte
- Removed showPreferences state variable
- Cleaned up unused Settings icon import
- Users now access Preferences via: Top nav → Settings → Preferences

### UI-096 Implementation Details

- Created `FilePickerDialog.svelte` component with:
  - Project selector dropdown
  - Custom tree rendering with folder/file hierarchy
  - Folder expand/collapse with chevron indicators
  - File selection highlighting
  - Selected file info display at bottom
- Updated `ReferenceSettingsModal.svelte`:
  - Replaced flat dropdown with "Browse Files..." button
  - Shows selected file with name/row count + change/clear buttons
  - Opens FilePickerDialog for hierarchical browsing
- Uses same API endpoints as FileExplorer (`/api/ldm/projects`, `/api/ldm/projects/{id}/tree`)

### Additional Session 9 Fixes (Post-Review)

- **Pretranslate Modal:** Removed technical descriptions ("5-tier cascade...") - now shows user-friendly text
- **Context Menu:** Changed "Merge to LanguageData..." → "Merge..."
- **QA Buttons:** Consolidated 3 separate QA buttons into single "Run QA" button
- **Phase 10 Doc:** Created comprehensive planning document for major UI/UX overhaul

### BUG-030: Context Menu Buttons Not Working (FIXED)

**Root Cause:** `closeContextMenu()` sets `contextMenuFile = null`, but async functions were using `contextMenuFile` AFTER calling `closeContextMenu()`, causing "Cannot read properties of null" errors.

**Fixed Functions in FileExplorer.svelte:**
- `downloadFile()` - Store file reference before closing menu
- `extractGlossary()` - Store file reference before closing menu
- `runLineCheckQA()` - Store file reference before closing menu
- `runTermCheckQA()` - Store file reference before closing menu
- `runAllQA()` - Store file reference before closing menu
- `openPretranslateModal()` - Fixed logger to use stored reference

**Pattern Applied:**
```javascript
const file = { ...contextMenuFile };  // Store BEFORE close
closeContextMenu();  // Now safe to nullify
await fetch(`/api/files/${file.id}/...`);  // Use stored ref
```

---

## PRIORITY ORDER (Remaining)

### Phase 1: TM UI/UX Overhaul (Medium)

| # | Issue | Task | Status |
|---|-------|------|--------|
| 1 | ~~TM-UI-003~~ | ~~Add threshold selector~~ | ✅ DONE |
| 2 | ~~TM-UI-002~~ | ~~Enhance unified TM panel (upload/delete/export in tab)~~ | ✅ DONE |

### Phase 2: Pretranslation UI (Medium)

| # | Issue | Task | Status |
|---|-------|------|--------|
| 3 | ~~TM-UI-001~~ | ~~Pretranslation modal~~ | ✅ DONE |
| 4 | ~~FileExplorer~~ | ~~Add "Pretranslate..." context menu~~ | ✅ DONE |

### Phase 3: Other UI Cleanup

| # | Issue | Task | Status |
|---|-------|------|--------|
| 5 | ~~UI-095~~ | ~~QA to context menu~~ | ✅ DONE |
| 6 | ~~UI-097~~ | ~~Consolidate settings~~ | ✅ DONE |
| 7 | ~~UI-096~~ | ~~Reference file picker~~ | ✅ DONE |

---

## ENDPOINT TESTING CHECKLIST

Before any UI work, verify these endpoints work:

| Endpoint | Method | Test Status |
|----------|--------|-------------|
| `/api/ldm/pretranslate` | POST | 🔲 To Test |
| `/api/ldm/tm/suggest` | GET | 🔲 To Test |
| `/api/ldm/tm/{id}/entries` | GET | 🔲 To Test |
| `/api/ldm/tm/upload` | POST | 🔲 To Test |
| `/api/ldm/files/{id}/extract-glossary` | GET | 🔲 To Test |

---

## Quick Commands

```bash
# DEV servers
./scripts/start_all_servers.sh --with-vite

# Test specific endpoint
curl -X POST http://localhost:8888/api/ldm/pretranslate \
  -H "Content-Type: application/json" \
  -d '{"file_id": 1, "engine": "standard", "dictionary_id": 1}'

# Playwright tests
cd locaNext && npx playwright test --reporter=list
```

---

## Reference Docs

| Topic | Location |
|-------|----------|
| Open issues | `docs/wip/ISSUES_TO_FIX.md` |
| Pretranslation system | `docs/history/wip-archive/P36_PRETRANSLATION_STACK.md` |
| 5-Tier cascade code | `server/tools/ldm/indexing/searcher.py` |
| Endpoint protocol | `testing_toolkit/ENDPOINT_PROTOCOL.md` |
| DEV testing | `testing_toolkit/DEV_MODE_PROTOCOL.md` |

---

## Key Files Index

### Backend (All Complete ✅)

| Feature | File | Lines |
|---------|------|-------|
| 5-Tier Cascade | `server/tools/ldm/indexing/searcher.py` | 1-380 |
| Pretranslation Engine | `server/tools/ldm/pretranslate.py` | 1-520 |
| Pretranslation API | `server/tools/ldm/routes/pretranslate.py` | 1-142 |
| TM Manager | `server/tools/ldm/tm_manager.py` | 1-1100 |
| Glossary Extract | `server/tools/ldm/routes/files.py` | 880-981 |

### Frontend (Session 9 Additions)

| Feature | File | Status |
|---------|------|--------|
| TM Panel | `src/lib/components/ldm/FileExplorer.svelte` (TM tab) | ✅ Enhanced |
| Pretranslate Modal | `src/lib/components/ldm/PretranslateModal.svelte` | ✅ CREATED |
| File Picker Dialog | `src/lib/components/ldm/FilePickerDialog.svelte` | ✅ CREATED |
| Threshold Selector | `src/lib/components/ldm/FileExplorer.svelte` (TM tab) | ✅ Added |
| Reference Settings | `src/lib/components/ReferenceSettingsModal.svelte` | ✅ Enhanced |

---

*Session 9 - All tasks complete. 8 issues fixed: UI-087, UI-094, UI-095, UI-096, UI-097, TM-UI-001, TM-UI-002, TM-UI-003*
