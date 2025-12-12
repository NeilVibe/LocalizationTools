# P25: LDM UX Overhaul & Advanced Features

**Priority:** P25 | **Status:** In Progress (70%) | **Created:** 2025-12-12

---

## CORE PRINCIPLE

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│   UIUX MUST BE: CLEAN • ORGANIZED • SIMPLE                 │
│                                                             │
│   This is NON-NEGOTIABLE. Every design decision must ask:  │
│   - Is it clean? (no clutter, no visual noise)             │
│   - Is it organized? (clear hierarchy, logical layout)     │
│   - Is it simple? (intuitive, no learning curve)           │
│                                                             │
│   If the answer is NO → redesign until YES.                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Overview

Major UX improvements and new features for LDM based on user feedback.

---

## 1. BUGS TO FIX

### BUG-001: "Go to Row" Button Not Useful
- **Status:** [x] Fixed (2025-12-12)
- **Priority:** Medium
- **Problem:** Go to row button doesn't serve a clear purpose
- **Fix:** Removed the button entirely - users use search or scroll

### BUG-002: Target Lock Behavior Wrong
- **Status:** [x] Fixed (2025-12-12)
- **Priority:** High
- **Problem:** Target column shows "locked" even when nobody is editing
- **User cannot edit** - this is blocking!
- **Expected:** Lock only appears when someone IS currently editing that row
- **Fix:** Fixed WebSocket event relay in websocket.js

### BUG-003: Upload File Tooltip Hidden
- **Status:** [x] Fixed (2025-12-12)
- **Priority:** Medium
- **Problem:** Hover tooltip on "Upload File" button appears UNDER the main LanguageData view
- **Expected:** Tooltip should appear OVER (higher z-index)
- **Fix:** Changed overflow from `hidden` to `visible` on LDM layout containers. Added CSS to ensure tooltips escape parent containers.
- **Files Modified:** `app.css`, `LDM.svelte`, `FileExplorer.svelte`

### BUG-004: Search Bar Requires Icon Click
- **Status:** [x] Fixed (2025-12-12)
- **Priority:** Medium
- **Problem:** User has to click icon on far right to search - tedious (Carbon ToolbarSearch component)
- **Expected:** Just click on search bar and type, press Enter to search
- **Fix:** Replaced `ToolbarSearch` with Carbon's `Search` component which is always expanded and ready for input.
- **Files Modified:** `VirtualGrid.svelte`

---

## 2. GRID UX SIMPLIFICATION

### Current Problems
- "Status" column takes too much space
- Unused column on far right
- Too cluttered, not enough focus on Source/Target

### New Design Philosophy
**Start simple: Source + Target only. User adds columns via Preferences.**

### Design Principles (CRITICAL)
```
The grid MUST feel:
├── CLEAN - No clutter, no wasted space
├── SLICK - Modern, professional appearance
├── SPACIOUS - Full use of available space
├── AGREEABLE - Pleasant to work in for hours
└── ORGANIZED - Clear visual hierarchy
```

**No wasted space.** Every pixel should serve a purpose.

### Column System

| Column | Default | Optional | Position |
|--------|---------|----------|----------|
| Index # | Hidden | Show via Preferences | Far left |
| String ID | Hidden | Show via Preferences | Left of Source |
| Source | **Always visible** | - | Left |
| Target | **Always visible** | - | Center |
| Reference | Hidden | Show via Preferences | Right of Target |
| TM Results | Hidden | Show via Preferences | Far right |
| QA Results | Hidden | Show via Preferences | Far far right |

### Status Indication (Simplified)
Instead of a full "Status" column:
- **Translated:** Cell background turns GREEN
- **Locked/In-use:** Small "locked" badge/sticker on cell
- **Confirmed:** Cell background turns BLUE (or checkmark icon)

---

## 3. PREFERENCES MENU

New Preferences panel for grid customization:

```
┌─ Preferences ──────────────────────────────────────────────┐
│                                                            │
│  ═══ APPEARANCE ═══                                        │
│                                                            │
│  Theme:                                                    │
│  ○ Light Mode                                              │
│  ○ Dark Mode (Night)                                       │
│                                                            │
│  Font Size:     [▼ Medium    ]  (Small / Medium / Large)   │
│  Font Weight:   [ ] Bold text                              │
│  Text Color:    [■ Default   ]  (Default / Custom picker)  │
│                                                            │
│  ═══ COLUMNS ═══                                           │
│                                                            │
│  Show Columns:                                             │
│  [ ] Index Number                                          │
│  [ ] String ID                                             │
│  [ ] Reference Column                                      │
│  [ ] TM Results                                            │
│  [ ] QA Results (Live)                                     │
│                                                            │
│  ═══ REFERENCE ═══                                         │
│                                                            │
│  Reference Settings:                                       │
│  ○ Match by String ID only                                 │
│  ○ Match by String ID + Source text                        │
│  [Select Reference File...]  (from project or local)       │
│                                                            │
│  ═══ QA ═══                                                │
│                                                            │
│  QA Settings:                                              │
│  [ ] Enable Live QA                                        │
│  [ ] Spell Check                                           │
│  [ ] Grammar Check                                         │
│  [ ] Glossary/Term Check                                   │
│  [ ] Inconsistency Check                                   │
│                                                            │
│  ═══ TM ═══                                                │
│                                                            │
│  TM Settings:                                              │
│  [ ] Show TM suggestions                                   │
│  [Select Active TM...]                                     │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### Appearance Settings Details

| Setting | Options | Default |
|---------|---------|---------|
| **Theme** | Light / Dark (Night) | Light |
| **Font Size** | Small (12px) / Medium (14px) / Large (16px) | Medium |
| **Font Weight** | Normal / Bold | Normal |
| **Text Color** | Default (theme-based) / Custom | Default |

**Theme applies to:** Grid, modals, file explorer, all LDM UI.

**Font settings apply to:** Grid cells, edit modal textarea.

---

## 4. EDIT & CONFIRM WORKFLOW

### Design: Modal Edit (BIG, Clean, Spacious)

**Simple flow:**
```
Double-click cell → BIG modal opens → Edit → Ctrl+S or Ctrl+T → Done
```

**Modal is BETTER because:**
- Full view of text with line breaks
- TM suggestions always visible on right
- Resizable by user
- Professional CAT tool feel

### Modal Design - OPTIMIZED FOR SPACE

**CRITICAL: Maximize space utilization. No wasted pixels.**

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│  Ctrl+S = Confirm (Reviewed)  |  Ctrl+T = Translate Only  |  Esc = Cancel    [X] │
├────────────────────────────────────────────────────────┬─────────────────────────┤
│                                                        │                         │
│  SOURCE                                                │  TM MATCHES             │
│  ┌──────────────────────────────────────────────────┐  │                         │
│  │                                                  │  │  ┌─ 95% ─────────────┐  │
│  │  원본 텍스트가 여기에 표시됩니다.                │  │  │ Similar text...   │  │
│  │  여러 줄도 지원됩니다.                           │  │  └───────────────────┘  │
│  │                                                  │  │                         │
│  │                                                  │  │  ┌─ 87% ─────────────┐  │
│  └──────────────────────────────────────────────────┘  │  │ Another match...  │  │
│                                                        │  └───────────────────┘  │
│  TARGET                                                │                         │
│  ┌──────────────────────────────────────────────────┐  │  ┌─ 72% ─────────────┐  │
│  │                                                  │  │  │ Third option...   │  │
│  │  Translation goes here                           │  │  └───────────────────┘  │
│  │  Multi-line supported                            │  │                         │
│  │                                                  │  │  Click to apply         │
│  │                                                  │  │  Tab = Apply top match  │
│  │                                                  │  │                         │
│  └──────────────────────────────────────────────────┘  │                         │
│                                                        │                         │
└────────────────────────────────────────────────────────┴─────────────────────────┘
```

### Modal Design Rules

| Rule | Description |
|------|-------------|
| **No title bloat** | No "Edit Translation" header - use space for content |
| **No String ID** | Don't show in modal - user sees it in grid already |
| **No Status dropdown** | REMOVED - use Ctrl+S (Confirmed) or Ctrl+T (Translated) |
| **Shortcuts on TOP** | Small bar showing keyboard shortcuts - always visible |
| **TM on RIGHT column** | Dedicated column for TM matches, sticks to right |
| **Source UP, Target DOWN** | Clear visual hierarchy, both large |
| **RESIZABLE** | User can drag window edges, everything auto-expands |
| **Auto-fill space** | Source/Target textareas fill ALL available space |
| **BIG by default** | Modal starts at ~80% of screen width/height |

### Space Optimization Comparison

```
BAD (Current - wasted space):
┌─────────────────────────────────┐
│  Edit Translation          [X] │  ← Wasted on useless title
│  String ID: TEST_001           │  ← Unnecessary - visible in grid
│  Status: [▼ Pending    ]       │  ← REMOVE - use shortcuts instead
│  ┌─────────────────────────┐   │
│  │ Small textarea         │   │  ← Way too small
│  └─────────────────────────┘   │
│  TM: (at bottom, cramped)      │  ← Bad placement
└─────────────────────────────────┘

GOOD (New - space maximized):
┌───────────────────────────────────────────────────────────────┐
│ Ctrl+S=Confirm | Ctrl+T=Translate | Esc=Cancel           [X] │
├──────────────────────────────────────────────┬────────────────┤
│                                              │                │
│  SOURCE                                      │  TM MATCHES    │
│  ┌────────────────────────────────────────┐  │  ┌──────────┐  │
│  │                                        │  │  │ 95% ...  │  │
│  │  LARGE area - auto expands             │  │  └──────────┘  │
│  │                                        │  │  ┌──────────┐  │
│  └────────────────────────────────────────┘  │  │ 87% ...  │  │
│                                              │  └──────────┘  │
│  TARGET                                      │                │
│  ┌────────────────────────────────────────┐  │  Click = apply │
│  │                                        │  │  Tab = top     │
│  │  LARGE editing area - fills space      │  │                │
│  │                                        │  │                │
│  └────────────────────────────────────────┘  │                │
└──────────────────────────────────────────────┴────────────────┘
```

**Modal must be:** BIG, clean, keyboard-focused, resizable, space-optimized.

### Linebreak Handling (Automatic)

| File Type | Stored As | Display While Editing |
|-----------|-----------|----------------------|
| TEXT | `\n` | Visual newline ↵ |
| XML | `&lt;br/&gt;` | Visual newline ↵ |

**User sees:** Normal text with line breaks
**Storage:** Proper escape format per file type

### Keyboard Shortcuts

| Action | Shortcut | Effect |
|--------|----------|--------|
| **Edit** | Double-click cell | Open edit modal |
| **Confirm** | `Ctrl+S` | Save AND mark as "Confirmed" (for merge) |
| **Translate Only** | `Ctrl+T` | Save but NOT confirmed (won't be merged) |
| **Cancel** | `Esc` | Close modal, discard changes |
| **New line** | `Enter` | Insert linebreak |
| **Next TM** | `Tab` | Apply first TM suggestion |

**Only "Confirmed" strings will be included in Merge operation.**

---

## 5. RIGHT-CLICK CONTEXT MENU

### Design Philosophy
**Native OS-style context menu** - looks and feels like Windows right-click menu.

When user right-clicks on a file in the File Explorer:

```
┌────────────────────────────────────┐
│  📥 Download File                   │
│  ─────────────────────────────────  │
│  🔍 Run Full Line Check QA          │
│  🔤 Run Full Word Check QA          │
│  ─────────────────────────────────  │
│  📚 Upload as TM...                 │
│     → Opens TM registration modal   │
└────────────────────────────────────┘
```

### Right-Click Options

| Option | Description |
|--------|-------------|
| **Download File** | Download file with all edits (exact original format) |
| **Run Full Line Check QA** | Run comprehensive line-level QA on entire file |
| **Run Full Word Check QA** | Run comprehensive word-level QA on entire file |
| **Upload as TM** | Register this file as a Translation Memory |

### Upload as TM Flow

```
Right-click → "Upload as TM..."
    ↓
┌─────────────────────────────────────────────────────────┐
│                 REGISTER AS TM                          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  TM Name:     [ BDO_EN_TM_v1.0                       ]  │
│                                                         │
│  Project:     [▼ Select Project...                   ]  │
│               • BDO English                             │
│               • BDO German                              │
│               • (Create New Project)                    │
│                                                         │
│  Language:    [▼ English (EN)                        ]  │
│                                                         │
│  Description: [                                      ]  │
│               [ Optional notes about this TM         ]  │
│                                                         │
│                          [Cancel]  [Register TM]        │
└─────────────────────────────────────────────────────────┘
    ↓
TM registered on central server
    ↓
Local processing begins (embeddings, FAISS index)
    ↓
Progress shown in TASKS panel
    ↓
TM ready for use
```

### TM Processing Flow (Important!)

**Central Server:**
- TM metadata stored in PostgreSQL
- Source/target pairs stored in DB

**Local Processing (Heavy):**
- Embedding generation (runs locally)
- FAISS index building (runs locally)
- Progress tracked in Tasks panel

**When another user wants the TM:**
1. User selects TM from list
2. Local processing starts for THEIR machine
3. Progress shown in THEIR Tasks panel
4. Once done, TM is ready locally

```
┌─────────────────────────────────────────────────────────┐
│                    TASKS                                │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ✅ TM "BDO_EN_TM_v1.0" registered                      │
│                                                         │
│  ⏳ Processing TM embeddings...                         │
│     ████████░░░░░░░░░░░░ 42%                           │
│     12,340 / 29,500 entries                             │
│                                                         │
│  ⏳ Building FAISS index...                             │
│     Waiting for embeddings...                           │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Tasks Panel Rules:**
- Shows ALL background tasks with real-time progress
- Clean, organized list
- Each task shows: status icon, name, progress bar, details
- User knows EXACTLY what's happening

---

## 6. MERGE FUNCTION

### Purpose
Merge confirmed translations back into the original file format.

### Access (via Right-Click Menu)
Right-click on file → Download File

### Merge Logic

**For TEXT files:**
- String ID = Index columns (0+1+2+3+4)
- Korean = column index 5
- Translation = column index 6
- Match: `StringID + Korean` matches → Replace translation
- No match: Add as new string

**For XML files:**
- String ID = `stringid` attribute
- Source = `strorigin` attribute
- Match: `StringID + Source` matches → Replace translation
- No match: Add as new string

**For Excel files:**
- No merge (only 2 columns, no string ID)
- Used for teamwork, just download result

### File Types Supporting Merge
| Type | Merge Available | String ID |
|------|-----------------|-----------|
| TEXT | ✅ Yes | Index 0+1+2+3+4 |
| XML | ✅ Yes | stringid attribute |
| Excel | ❌ No | N/A |

---

## 7. REFERENCE COLUMN

### Purpose
Show reference translations from another file (like QuickSearch reference feature).

### Reference Sources
1. **Project file** - Select another file from same project
2. **Local file** - Load reference from local disk

### Match Modes
- **String ID only** - Match by string ID
- **String ID + Source** - Match by both (more accurate)

### Display
- Reference column appears right of Target
- Shows matched translation from reference file
- If no match: empty or "No reference"

---

## 8. TM INTEGRATION

### TM Upload
- Upload TM files (TMX, etc.) OR convert LDM file to TM via right-click
- During upload: Shows in **Tasks menu** with progress
- Embedding process runs in background (takes time for large TMs)

### TM Selection
- User can select which TM is active
- Active TM provides suggestions in TM Results column

### TM Results Column
- Shows best TM matches for current source
- Position: Far right (after Reference)
- Can be shown/hidden via Preferences

---

## 9. LIVE QA SYSTEM

### QA Checks (Run live while translating)

**CRITICAL:** QA must trigger INSTANTLY as user types. No lag allowed.

| Check | Description | Recommended Method | Speed |
|-------|-------------|-------------------|-------|
| **Spell Check** | Check spelling | `hunspell` or `pyspellchecker` | <5ms |
| **Grammar Check** | Check grammar | `language-tool-python` (local) | ~50ms |
| **Glossary/Term Check** | Verify terms match glossary | **Aho-Corasick** | <1ms |
| **Inconsistency Check** | Same source = same target | In-memory dict lookup | <1ms |

### Why Aho-Corasick for Glossary?

**Aho-Corasick is the BEST choice for glossary term matching:**
- Searches ALL terms in glossary simultaneously in ONE pass
- O(n + m + z) complexity - n=text length, m=patterns, z=matches
- Perfect for "find all glossary terms in this sentence"
- Used by antivirus, spam filters, DNA sequencing

**Alternatives considered:**
| Method | Speed | Why Not |
|--------|-------|---------|
| Regex per term | Slow | O(n * terms) - doesn't scale |
| Simple string search | Slow | O(n * terms) |
| Trie | Fast | Good but Aho-Corasick is better for multi-pattern |
| **Aho-Corasick** | **Fastest** | **Single pass, all patterns** |

**Library:** `pyahocorasick` (Python) - builds automaton once, queries are instant

### QA Results Column
- Shows issues found
- Position: Far far right (always last)
- Color-coded: Red = error, Yellow = warning

### Auto-Glossary Generation

**During TM Upload, automatically generate glossary:**

1. **Extraction Rules:**
   - Filter out sentences (anything ending with punctuation: `.` `!` `?`)
   - Max length: 26 characters
   - Take unique entries only
   - If duplicates: use most frequent version

2. **Processing:**
   - Embedding for semantic matching
   - Aho-Corasick index for fast term lookup

3. **Storage:**
   - Glossary stored per TM
   - Used for live QA term checking

**Question:** Any other glossary extraction rules needed?
- Minimum length? (e.g., > 2 characters)
- Exclude numbers-only entries?
- Exclude single words vs multi-word terms?

---

## 10. TASKS

### Bugs (Priority)
- [x] BUG-002: Target lock blocking editing (HIGH) ✅ FIXED 2025-12-12
- [x] BUG-003: Upload tooltip z-index ✅ FIXED 2025-12-12
- [x] BUG-004: Search bar icon requirement ✅ FIXED 2025-12-12
- [ ] BUG-001: Go to row usefulness

### Grid UX
- [x] Remove Status column, use cell colors instead ✅ DONE 2025-12-12
- [x] Remove Go to Row button ✅ DONE 2025-12-12
- [x] Make Source/Target the default view ✅ DONE 2025-12-12
- [x] Add Preferences menu (column toggles) ✅ DONE 2025-12-12

### Appearance (NEW)
- [x] Light/Dark theme toggle ✅ DONE 2025-12-12
- [x] Theme CSS variables ✅ DONE 2025-12-12
- [x] Font size selector (Small/Medium/Large) ✅ DONE 2025-12-12
- [x] Bold text toggle ✅ DONE 2025-12-12
- [ ] Custom text color picker
- [x] Persist preferences in localStorage ✅ DONE 2025-12-12

**Implementation:**
- Created `src/lib/stores/preferences.js` - Svelte store with localStorage persistence
- Added theme CSS variables in `app.css` (`:root` and `:root[data-theme="light"]`)
- Updated `PreferencesModal.svelte` with theme/font settings
- Added quick theme toggle button in header (sun/moon icons)

### Preferences Menu
- [x] Create Preferences panel/modal ✅ DONE 2025-12-12
- [x] Appearance settings section ✅ DONE 2025-12-12
- [x] Index number toggle ✅ DONE 2025-12-12
- [x] String ID toggle ✅ DONE 2025-12-12
- [ ] Reference column toggle (disabled - needs Reference feature)
- [ ] TM Results toggle (disabled - needs TM feature)
- [ ] QA Results toggle (disabled - needs QA feature)

### Edit Modal (Updated)
- [x] Clean, spacious modal design ✅ DONE 2025-12-12
- [x] Source text display (read-only) ✅ DONE 2025-12-12
- [x] Target text editing (large textarea) ✅ DONE 2025-12-12
- [x] TM suggestions panel ✅ DONE 2025-12-12
- [x] Implement Ctrl+S = Confirm (reviewed status) ✅ DONE 2025-12-12
- [x] Implement Ctrl+T = Translate only ✅ DONE 2025-12-12
- [x] Track "confirmed" status per row ✅ DONE 2025-12-12

**Implementation Details:**
- Modal is 85% width/height with two-column layout
- Left column: Source (read-only) + Target (editable textarea)
- Right column: TM matches panel with Apply button
- Shortcut bar at top showing all keyboard shortcuts
- Tab key applies first TM suggestion

### Merge Function / Download
- [x] Download endpoint (GET /api/ldm/files/{id}/download) ✅ DONE 2025-12-12
- [x] Download menu in grid header (overflow menu) ✅ DONE 2025-12-12
- [x] Filter by status (all, translated, reviewed) ✅ DONE 2025-12-12
- [x] TXT file export ✅ DONE 2025-12-12
- [x] XML file export ✅ DONE 2025-12-12
- [x] Excel file export ✅ DONE 2025-12-12
- [x] Format verification test (string_id split fix) ✅ DONE 2025-12-12
- [ ] Merge with original file (requires original file storage)

### Right-Click Context Menu (NEW)
- [ ] Native OS-style right-click menu on files
- [ ] Download File option
- [ ] Run Full Line Check QA option
- [ ] Run Full Word Check QA option
- [ ] Upload as TM option (opens TM registration modal)
- [ ] TM Registration modal (name, project, language, description)

### Reference Column
- [ ] Create Reference column component
- [ ] Load reference from project file
- [ ] Load reference from local file
- [ ] Match by String ID
- [ ] Match by String ID + Source

### Tasks Panel (Background Task Progress)
- [ ] Create Tasks panel component (sidebar or modal)
- [ ] Show all background tasks with status icons
- [ ] Real-time progress bars with percentages
- [ ] Task details (e.g., "12,340 / 29,500 entries")
- [ ] Clean, organized list design
- [ ] WebSocket updates for progress
- [ ] Task completion notifications

### TM Integration
- [ ] TM upload shows in Tasks panel
- [ ] TM local processing (embeddings, FAISS) with progress
- [ ] TM selection UI
- [ ] TM Results column
- [ ] Active TM indicator
- [ ] Another user selects TM → local processing with progress

### QA System
- [ ] Live QA framework
- [ ] Spell check integration
- [ ] Grammar check integration
- [ ] Glossary term check (Aho-Corasick)
- [ ] Inconsistency check
- [ ] QA Results column

### Auto-Glossary
- [ ] Extract terms during TM upload
- [ ] Filter rules (no sentences, max length, unique)
- [ ] Embedding for semantic
- [ ] Aho-Corasick index for fast lookup

---

## 11. COLUMN LAYOUT SUMMARY

**Default View:**
```
| Source | Target |
```

**Full View (all options enabled):**
```
| Index | String ID | Source | Target | Reference | TM Results | QA Results |
```

**Column Order (fixed):**
1. Index # (optional, far left)
2. String ID (optional)
3. Source (always)
4. Target (always)
5. Reference (optional)
6. TM Results (optional)
7. QA Results (optional, always far right)

---

## 12. DEPENDENCIES

| Feature | Depends On |
|---------|------------|
| Glossary Term Check | Auto-Glossary generation |
| Auto-Glossary | TM Upload |
| TM Results | TM Upload + Selection |
| Reference Column | File parser (TEXT, XML) |
| Merge | Confirmed status tracking |

---

## 13. DATA ARCHITECTURE REMINDER

```
┌─────────────────────────────────────────────────────────────┐
│                  GRID ←→ DB (Direct Connection)             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Upload File → Parse → Rows stored in DB (ldm_rows)         │
│                                                             │
│  Edit Cell → DB row updated INSTANTLY (<10ms)               │
│                                                             │
│  Download File → DB rows → Rebuild file (same format)       │
│                                                             │
│  NO file stored on disk. DB IS the source of truth.         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Multi-user:** Other users download → Get your changes instantly.

---

*Created: 2025-12-12*
*This is a comprehensive UX overhaul - implement in phases*
