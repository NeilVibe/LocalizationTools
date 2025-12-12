# P25: LDM UX Overhaul & Advanced Features

**Priority:** P25 | **Status:** In Progress (85%) | **Created:** 2025-12-12

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

## 9. TM MATCHING & QA SYSTEMS (SEPARATE)

### Core Principle: MEGA SPEED

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│  BUILD ONCE (background) → USE INSTANTLY (during work)                  │
│                                                                          │
│  TM Upload triggers BACKGROUND indexing:                                │
│  - User can continue working while indexing happens                     │
│  - Progress shown in Tasks panel                                        │
│  - Once done, all lookups are PRE-CACHED and INSTANT                   │
│                                                                          │
│  USER EXPERIENCE: SMOOTH. NO BLOCKING. NO WAITING.                      │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Core Architecture - TWO SEPARATE SYSTEMS

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│  SYSTEM 1: TM MATCHING (WebTranslatorNew Style)                         │
│  ─────────────────────────────────────────────────────────────────────  │
│  Purpose: Find similar translations → Show in Edit Modal                │
│  Method: QWEN Embeddings + 5-Tier Cascade + Single Threshold (92%)      │
│                                                                          │
│  + NPC (Neil's Probabilistic Check): Verify Target vs TM Targets (80%)  │
│                                                                          │
│  NOT QA. This is for SUGGESTIONS + VERIFICATION.                        │
│                                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  SYSTEM 2: QA CHECKS (QuickSearch Style)                                │
│  ─────────────────────────────────────────────────────────────────────  │
│  Purpose: Quality assurance → Find errors and inconsistencies           │
│                                                                          │
│  A. WORD CHECK (Term Check)                                             │
│     Method: Aho-Corasick automaton                                      │
│     Check: Glossary terms translated correctly?                         │
│                                                                          │
│  B. LINE CHECK (Inconsistency Check)                                    │
│     Method: Dictionary lookup (NOT embeddings)                          │
│     Check: Same source → Same target? If not → Inconsistent             │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘

BOTH SYSTEMS built from TM Upload → All pre-indexed → Instant during work
```

---

### TM UPDATE ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│  DB = CENTRAL SOURCE OF TRUTH (always up-to-date)                       │
│  FAISS = LOCAL INDEX (synced on demand)                                 │
│                                                                          │
│  DB updates happen AUTOMATICALLY:                                       │
│  - Re-upload TM file → DB updates instantly                             │
│  - Ctrl+S confirm string → DB updates instantly (if TM active)          │
│  - Multiple users update DB simultaneously → blazing fast               │
│                                                                          │
│  FAISS sync happens ON DEMAND:                                          │
│  - User clicks [Synchronize TM] button in TM menu                       │
│  - Pulls changes from DB → INSERT/UPDATE/DELETE locally                 │
│  - Re-embeds new/changed entries only                                   │
│  - Rebuilds FAISS index at the end                                      │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

### TM UPDATE FLOW - DETAILED STEPS

#### TRIGGER 1: Re-upload TM File

```
User uploads new TM file (same TM name)
        ↓
Parse file → new_data DataFrame (Source, Target)
        ↓
Fetch existing from DB → existing_data DataFrame
        ↓
pd.merge(new_data, existing_data, on='Source', how='outer', suffixes=('_new', '_old'))
        ↓
┌─────────────────────────────────────────────────────────────┐
│ DETECT CHANGES:                                              │
│                                                              │
│ to_insert = merged[Target_old.isna() & Target_new.notna()]  │
│ to_delete = merged[Target_new.isna() & Target_old.notna()]  │
│ to_update = merged[                                         │
│     Target_new.notna() &                                    │
│     Target_old.notna() &                                    │
│     (Target_new != Target_old)                              │
│ ]                                                            │
│ unchanged = the rest (skip)                                  │
└─────────────────────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────────────────────┐
│ DB OPERATIONS (PostgreSQL):                                  │
│                                                              │
│ INSERT INTO tm_entries (tm_id, source, target)              │
│   VALUES ... for each to_insert                              │
│                                                              │
│ UPDATE tm_entries SET target = new_target                   │
│   WHERE tm_id = ? AND source = ? for each to_update         │
│                                                              │
│ DELETE FROM tm_entries                                       │
│   WHERE tm_id = ? AND source IN (...) for to_delete         │
└─────────────────────────────────────────────────────────────┘
        ↓
DB is now up-to-date (all users see new data)
FAISS not touched yet (local sync needed)
```

#### TRIGGER 2: Ctrl+S Confirm String (TM Active)

```
User confirms translation with Ctrl+S
        ↓
Check: Is a TM active for this project?
        ↓
    NO → Just save row, done
    YES ↓
        ↓
Get Source + Target from confirmed row
        ↓
Check: Does this Source exist in TM?
        ↓
    NO → INSERT INTO tm_entries (tm_id, source, target)
    YES → UPDATE tm_entries SET target = ? WHERE source = ?
        ↓
DB updated instantly
User's local FAISS is now stale (sync needed later)
```

#### TRIGGER 3: User Clicks [Synchronize TM]

```
User clicks [Synchronize TM] button in TM menu
        ↓
Fetch ALL current TM entries from DB → db_data
        ↓
Load local state:
  - embeddings.npy (Source embeddings)
  - embeddings_target.npy (Target embeddings)
  - tm_dict.pkl (Source → Target + metadata)
        ↓
Compare db_data vs local tm_dict
        ↓
┌─────────────────────────────────────────────────────────────┐
│ DETECT CHANGES (same logic):                                 │
│                                                              │
│ to_embed_new = Sources in DB but not in local               │
│ to_embed_update = Sources where Target changed              │
│ to_remove = Sources in local but not in DB                  │
└─────────────────────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────────────────────┐
│ LOCAL OPERATIONS:                                            │
│                                                              │
│ 1. EMBEDDING (expensive, only for new/changed):             │
│    for each source in to_embed_new + to_embed_update:       │
│      source_emb = qwen_embed(source)                        │
│      target_emb = qwen_embed(target)                        │
│      store in embeddings arrays                             │
│                                                              │
│ 2. UPDATE tm_dict.pkl:                                      │
│    - Add new entries                                        │
│    - Update changed entries                                 │
│    - Remove deleted entries                                 │
│                                                              │
│ 3. REBUILD FAISS (fast, from all embeddings):               │
│    index = faiss.IndexHNSWFlat(dimension, M)                │
│    index.add(all_source_embeddings)                         │
│    faiss.write_index(index, "tm_source.faiss")              │
│                                                              │
│ 4. REBUILD Aho-Corasick (fast):                             │
│    automaton = ahocorasick.Automaton()                      │
│    for term in glossary_terms:                              │
│      automaton.add_word(term, term)                         │
│    automaton.make_automaton()                               │
│                                                              │
│ 5. REBUILD Line Check Dict (fast):                          │
│    line_dict = {source: target for source, target in db}    │
└─────────────────────────────────────────────────────────────┘
        ↓
Progress shown in Tasks panel:
  "Synchronizing TM..."
  "Embedding 127 new entries..."
  "Building FAISS index..."
  "Done!"
        ↓
Local FAISS now matches DB
User can use TM matching + NPC + QA
```

---

### WHY THIS ARCHITECTURE?

| Aspect | Benefit |
|--------|---------|
| **DB = instant** | Ctrl+S updates TM immediately, all users see it |
| **FAISS = on demand** | Heavy work only when user wants it |
| **Smart diff** | Only embed new/changed (not entire TM) |
| **Multi-user** | Everyone updates same DB, sync locally when ready |
| **No conflicts** | DB handles concurrency, local is read-only copy |

---

### TM MENU UI

```
┌─────────────────────────────────────────────────────────────┐
│  TM: BDO_EN_TM_v1.0                              [▼ Select] │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Status: ⚠️ 127 new entries available                       │
│  Last synced: 2025-12-13 10:30 KST                         │
│                                                             │
│  [ 🔄 Synchronize TM ]                                      │
│                                                             │
│  [ 📤 Re-upload TM File ]                                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Status shows:**
- ✅ Up to date (local matches DB)
- ⚠️ X new entries available (sync needed)
- 🔄 Syncing... (in progress)

---

### WHAT GETS REBUILT ON SYNC

| Resource | When | Speed |
|----------|------|-------|
| Source embeddings (.npy) | New/changed only | Slow (QWEN call) |
| Target embeddings (.npy) | New/changed only | Slow (QWEN call) |
| tm_dict.pkl | Full rebuild | Fast |
| FAISS index | Full rebuild | Fast |
| Aho-Corasick automaton | Full rebuild | Fast |
| Line Check dict | Full rebuild | Fast |

**Embedding is the bottleneck** - that's why we only embed new/changed.
Everything else rebuilds from scratch (cheap).

---

### SYSTEM 1: TM MATCHING

**Purpose:** Provide TM suggestions in Edit Modal (NOT QA)

**Technology:** Same as WebTranslatorNew
- QWEN Embeddings
- 5-Tier Cascade
- Single Threshold: **92%** (simplified from DUAL)
- FAISS for fast similarity search
- PKL for Source → Target mapping

**When TM is uploaded:**
```
TM Source/Target pairs
    ↓
QWEN generates embeddings for each Source + Target
    ↓
FAISS index built for similarity search
    ↓
PKL file: Source → Target mapping
    ↓
5-Tier Cascade ready (threshold: 92%)
```

**5-Tier Cascade:**
| Tier | Type | Display Rule |
|------|------|--------------|
| 1 | Perfect whole match | Show if exists, else nothing |
| 2 | Whole embedding match | Top 3 results ≥92% |
| 3 | Perfect line match | Show if exists, else nothing |
| 4 | Line embedding match | Top 3 results ≥92% |
| 5 | N-gram fallback | Top 3 results ≥92% |

**Usage:** When user opens Edit Modal → Search FAISS → Apply cascade → Show matches ≥92%

**This is NOT QA.** This is for finding similar translations to suggest.

---

### NPC: Neil's Probabilistic Check

**Purpose:** Verify user's translation is consistent with TM patterns

**Button:** [NPC] - appears in Edit Modal after TM results load

**Logic:**
```
1. TM panel already has Source matches ≥92%
2. User clicks [NPC] button
3. Embed user's Target (1 embedding call)
4. Cosine similarity vs each TM Target
5. Any match ≥80%? → ✅ Consistent
   No matches ≥80%? → ⚠️ Potential issue
```

**Code:**
```python
def npc_check(user_target, tm_targets, threshold=0.80):
    """Neil's Probabilistic Check - simple and fast"""
    user_embedding = embed(user_target)

    for tm_target in tm_targets:
        sim = cosine_sim(user_embedding, tm_target.embedding)
        if sim >= threshold:
            return "✅ Consistent"

    return "⚠️ Potential issue"
```

**Example:**
```
Source: "저장하기"
TM finds 3 matches ≥92%:
  - "저장" → "Save"
  - "저장하기" → "Save"
  - "저장합니다" → "Saving"

User types: "Save"
NPC: "Save" vs ["Save", "Save", "Saving"] → 100% match ✅

User types: "Delete"
NPC: "Delete" vs ["Save", "Save", "Saving"] → <80% ⚠️
```

**Why it works:**
- TM matches are high confidence (≥92% Source similarity)
- If user's Target doesn't match ANY expected Target (≥80%) → suspicious
- No FAISS needed for NPC, just direct cosine similarity
- Fast: 1 embedding call + N cosine calcs (N usually <10)

**Thresholds:**
| Check | Threshold | Purpose |
|-------|-----------|---------|
| Source → TM | 92% | High confidence matches only |
| User Target → TM Targets (NPC) | 80% | Lenient, "in the ballpark" |

---

### SYSTEM 2: QA CHECKS

**Purpose:** Quality assurance - find errors and inconsistencies

**Technology:** From QuickSearch
- Word Check: Aho-Corasick (pyahocorasick)
- Line Check: Simple dictionary lookup

**QA compares CURRENT FILE against TM.**

---

### QA Parsing Flow (Shared)

**Both Word Check and Line Check use the same initial parsing:**

```
Source in Edit Modal
        ↓
    normalize_newlines_universal(text)  ← NORMALIZE FIRST!
        ↓
    split('\n')  ← Always split by \n after normalization
        ↓
┌───────┴───────┬───────────────┐
↓               ↓               ↓
Line 1        Line 2         Line N
↓               ↓               ↓
├── WORD CHECK (Aho-Corasick scan each line)
└── LINE CHECK (Dict lookup each line)
```

### Newline Normalization (from WebTranslatorNew)

**Original (embedding.py:615):**
```python
def normalize_newlines(text):
    return text.replace('\\n', '\n') if text else text
```

**Extended for LDM (handles ALL formats):**
```python
def normalize_newlines_universal(text):
    """Handle ALL newline formats for consistent parsing"""
    if not text:
        return text

    # 1. Escaped \\n → \n (TEXT files store as literal backslash-n)
    text = text.replace('\\n', '\n')

    # 2. XML <br/> → \n (unescaped XML linebreak)
    text = text.replace('<br/>', '\n')
    text = text.replace('<br />', '\n')

    # 3. HTML-escaped &lt;br/&gt; → \n (escaped XML linebreak)
    text = text.replace('&lt;br/&gt;', '\n')
    text = text.replace('&lt;br /&gt;', '\n')

    return text
```

**Why normalize FIRST, then always split by `\n`:**
- Simpler logic - one split function
- TM and QA use same normalization = consistent matching
- No need to track file type during QA check

**Newline Formats:**
| Format | Source | Example |
|--------|--------|---------|
| `\n` | Actual newline | Multi-line in memory |
| `\\n` | TEXT files | Stored as literal `\n` |
| `<br/>` | XML files (parsed) | XML linebreak tag |
| `&lt;br/&gt;` | XML files (raw/escaped) | HTML-escaped XML |

---

### QA Word Check (Term Check)

**From:** QuickSearch Term Check function

**Method:** Aho-Corasick automaton

**When TM is uploaded:**
```
TM Source/Target pairs
    ↓
Filter by glossary rules:
  - NO sentences (exclude if ends with . ! ?)
  - Max 26 characters
  - Skip if contains punctuation or ellipsis
  - Unique entries only
    ↓
Build Aho-Corasick automaton (pyahocorasick)
    ↓
Build glossary dict: Source term → Expected target
```

**Config:** PRE-CONFIGURED, no user input needed
- Max length: 26 characters
- Exclude sentences (ending with . ! ?)
- Exclude entries with punctuation or …
- Result: Clean glossary of terms only

**How it works (on Edit Modal):**
```
Step 1: Parse source by linebreak
        source_lines = source_text.split('\n')

Step 2: For each line, Aho-Corasick scan
        for line in source_lines:
            found_terms = aho_corasick.scan(line)
            # found_terms = ["버튼", "클릭", "시작하기"]

Step 3: Get expected targets from glossary
        for term in found_terms:
            expected_target = glossary[term]
            # "시작하기" → "Get Started"

Step 4: Check if expected targets appear in user's translation
        for expected in expected_targets:
            if expected.lower() not in user_target.lower():
                flag_qa_warning(term, expected)
```

**Example:**
```
Source: "버튼을 클릭하여 시작하기"
User's Target: "Click button to start"

Word Check:
├── "버튼" → expected "button" → ✅ found in target
├── "클릭" → expected "click" → ✅ found in target
└── "시작하기" → expected "Get Started" → ❌ NOT FOUND

QA Flag: ⚠️ "시작하기" should be "Get Started"
```

### Why Aho-Corasick?

**Best choice for multi-pattern matching:**
- Searches ALL glossary terms in ONE pass
- O(n + m + z) complexity
- Same algorithm used in QuickSearch
- Library: `pyahocorasick` (Python, MIT license)

---

### QA Line Check (Inconsistency Check)

**From:** QuickSearch Line Check function

**Method:** Dictionary lookup (NOT embeddings!)

**When TM is uploaded:**
```
TM Source/Target pairs
    ↓
Build dictionary: Source → Target
    ↓
Save as .pkl for instant lookup
```

**How it works (on Edit Modal):**
```
Step 1: Parse source by linebreak
        source_lines = source_text.split('\n')

Step 2: For each line, exact dict lookup
        for line in source_lines:
            if line in tm_dict:
                tm_target = tm_dict[line]

Step 3: Compare TM target with user's target
        # Split user target by linebreak too
        user_lines = user_target.split('\n')

        if tm_target != corresponding_user_line:
            flag_qa_warning(line, tm_target, user_line)
```

**Example:**
```
Source: "저장하기\n취소하기"
User's Target: "Store\nCancel"

Line Check:
├── "저장하기" → TM says "Save" → User wrote "Store" → ❌ MISMATCH
└── "취소하기" → TM says "Cancel" → User wrote "Cancel" → ✅ OK

QA Flag: ⚠️ Line "저장하기" should be "Save" (TM), not "Store"
```

**This is NOT similarity matching.** It's exact source lookup per line.

---

### Other QA Checks

| Check | What It Does | Method | Severity |
|-------|--------------|--------|----------|
| **Missing Translation** | Empty target for translated status | Simple check | Warning |
| **Number Mismatch** | Numbers in source vs target don't match | Regex comparison | Warning |

These are simple checks, not based on TM.

---

### QA Status

**Spell Check & Grammar Check: SKIPPED**
- No good MIT/Apache licensed multi-language spell checker
- Hunspell is LGPL (copyleft concerns)
- Decision: Focus on TM-based QA instead

---

### QA Results Display

**In Grid:**
- QA Results column (far right, optional via Preferences)
- Color-coded: Red = error, Yellow = warning
- Click to see details

**In Edit Modal:**
- QA panel on right side (below TM matches)
- Shows issues for current row
- Can be toggled via Preferences

---

### Configuration Summary

**PRE-CONFIGURED (no user input):**
- Glossary rules: ≤26 chars, no sentences, no punctuation
- Check types and thresholds

**User CAN toggle:**
- Show/hide QA Results column
- Enable/disable live QA

---

## 10. TASKS

### Bugs (All Fixed)
- [x] BUG-001: Go to row removed ✅ FIXED 2025-12-12
- [x] BUG-002: Target lock blocking editing ✅ FIXED 2025-12-12
- [x] BUG-003: Upload tooltip z-index ✅ FIXED 2025-12-12
- [x] BUG-004: Search bar icon requirement ✅ FIXED 2025-12-12
- [x] ISSUE-013: WebSocket locking re-enabled ✅ FIXED 2025-12-12

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
- [x] Reference column toggle ✅ DONE 2025-12-12
- [x] Reference file selector ✅ DONE 2025-12-12
- [x] Reference match mode ✅ DONE 2025-12-12
- [x] TM Results toggle ✅ DONE 2025-12-12
- [x] TM selector ✅ DONE 2025-12-12
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

### Right-Click Context Menu
- [x] Native OS-style right-click menu on files ✅ Already existed (FileExplorer.svelte)
- [x] Download File option ✅ DONE 2025-12-12
- [ ] Run Full Line Check QA option
- [ ] Run Full Word Check QA option
- [x] Register as TM option ✅ DONE 2025-12-12

### Reference Column
- [x] Create Reference column component ✅ DONE 2025-12-12
- [x] Load reference from project file ✅ DONE 2025-12-12
- [x] Reference file selector in Preferences ✅ DONE 2025-12-12
- [x] Match by String ID ✅ DONE 2025-12-12
- [x] Match by String ID + Source ✅ DONE 2025-12-12
- [x] Match mode selector in Preferences ✅ DONE 2025-12-12

### Tasks Panel (Background Task Progress)
- [x] Create Tasks panel component ✅ Already existed (TaskManager.svelte)
- [x] Show all background tasks with status icons ✅ DONE
- [x] Real-time progress via WebSocket ✅ DONE
- [x] Task completion notifications ✅ DONE

### SYSTEM 1: TM Matching (WebTranslatorNew Style)

**UI (Done):**
- [x] TM upload UI (TMManager, TMUploadModal) ✅ DONE 2025-12-12
- [x] TM selection UI in Preferences ✅ DONE 2025-12-12
- [x] TM Results column in grid ✅ DONE 2025-12-12
- [x] Active TM indicator in preferences ✅ DONE 2025-12-12

**Backend (TODO):**
- [ ] Universal newline normalizer (`\n`, `\\n`, `<br/>`, `&lt;br/&gt;` → `\n`)
- [ ] QWEN embedding generation (local, background) - Source AND Target
- [ ] FAISS index building (HNSW)
- [ ] PKL file (Source → Target mapping)
- [ ] 5-Tier Cascade implementation
- [ ] Single Threshold: 92% (simplified from DUAL)
- [ ] Display rules: Perfect tiers = show if exists, Embedding tiers = top 3 ≥92%
- [ ] Progress tracking in Tasks panel

**TM DB Sync (TODO):**
- [ ] DB table: tm_entries (tm_id, source, target, created_at, updated_at)
- [ ] TRIGGER 1: Re-upload TM → pd.merge → INSERT/UPDATE/DELETE DB
- [ ] TRIGGER 2: Ctrl+S confirm → INSERT or UPDATE to DB (if TM active)
- [ ] TRIGGER 3: [Synchronize TM] button → pull DB → diff → re-embed new/changed → rebuild FAISS
- [ ] TM Menu UI with sync status (✅ Up to date / ⚠️ X new entries)
- [ ] Track last_synced timestamp per user per TM

**NPC (Neil's Probabilistic Check):**
- [ ] [NPC] button in Edit Modal (after TM results load)
- [ ] Embed user's Target (1 call)
- [ ] Cosine similarity vs TM Targets
- [ ] Threshold: 80% (lenient, "in the ballpark")
- [ ] Display: ✅ Consistent / ⚠️ Potential issue

### SYSTEM 2: QA Checks (QuickSearch Style)

**Word Check (Aho-Corasick):**
- [ ] Glossary extraction from TM (≤26 chars, no sentences, no punctuation)
- [ ] Aho-Corasick automaton build (pyahocorasick - MIT)
- [ ] Word Check logic: scan source text → find all terms → verify in target
- [ ] No word splitting needed - Aho-Corasick scans full text automatically

**Line Check (Dict Lookup):**
- [ ] Dictionary build from TM (Source → Target)
- [ ] Line Check logic: normalize → split('\n') → lookup each line → compare
- [ ] Works with 0 or N linebreaks (1 line = 1 lookup)

**Other Checks:**
- [ ] Missing translation check (simple: empty target?)
- [ ] Number mismatch check (regex: compare numbers in source vs target)

**UI:**
- [ ] QA Results column in grid
- [ ] QA panel in Edit Modal (below TM panel)
- [ ] QA Results toggle in Preferences

**SKIPPED:**
- [x] ~~Spell check~~ SKIPPED - no MIT/Apache multi-lang library
- [x] ~~Grammar check~~ SKIPPED - same reason

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
| TM Matching (suggestions) | TM Upload + QWEN + FAISS + 5-Tier (92%) |
| NPC (probabilistic check) | TM Matching + Target embeddings (80%) |
| QA Word Check | TM Upload + Glossary extraction + Aho-Corasick |
| QA Line Check | TM Upload + Dictionary build |
| TM Results column | TM Matching system |
| QA Results column | QA Word/Line Check systems |
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
