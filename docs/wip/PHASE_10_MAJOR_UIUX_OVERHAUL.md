# Phase 10: Major UI/UX Overhaul

> Created: 2026-01-01 (Session 9) | Status: PLANNING | Priority: HIGH

---

## Overview

Complete restructure of LocaNext UI from left-column layout to **page-based navigation** with **Windows/SharePoint-style explorers**.

### Key Changes

| Current | Phase 10 |
|---------|----------|
| Left column with Files/TM tabs | **BOTH Files AND TM get their own full explorer PAGES** |
| Cramped left column UI | Full-width explorer with proper space |
| Dropdown project selection | Windows-style folder navigation |
| Small TM threshold slider | Full TM settings in dedicated TM Explorer page |

---

## 1. Navigation Restructure

### 1.1 LocaNext Main Button Dropdown
**Current:** LocaNext button does nothing useful (has weird "Skip to Main Content" accessibility link)
**Proposed:** Click LocaNext → Dropdown menu:
- Files → Opens File Explorer page
- TM → Opens TM Explorer page
- Dashboard → Opens Dashboard
- (Future: Reports, Admin, etc.)

### 1.2 Remove Left Column Layout
**Current:** Left column with Files/TM tabs, main area for grid
**Proposed:**
- Files and TM become FULL PAGES (not tabs in a column)
- More space for grid viewer
- More space for explorer content
- Cleaner, less cramped UI

### 1.3 Merge User Button into Settings
**Current:** Separate "user/admin" button and "Settings" button
**Proposed:** One "Settings" entry point containing:
- User Profile
- Preferences
- Application Settings
- Admin (if admin role)
- Logout

---

## 2. File Explorer Overhaul

### 2.1 Windows/SharePoint Style Explorer
**Current:** Dropdown for project selection, tree view for folders
**Proposed:** Normal explorer behavior:

| Action | Behavior |
|--------|----------|
| Double-click folder/project | Enter folder, show contents |
| Right-click file/folder/project | Context menu (Delete, Rename, Properties, Move) |
| Left-click + drag | Move file/folder to another location |
| Drop in "void" (root area) | Create new project (if at project level) or folder |
| Move folder | Moves entire folder INCLUDING all contents |
| Breadcrumb navigation | Click path segments to navigate back |

### 2.2 "The Void" Concept
- At project level: Empty space = right-click to create new project
- Inside project: Empty space = right-click to create new folder/file
- Drag items to "void" to move them up a level

### 2.3 Properties Panel
Right-click → Properties shows:
- **Date created**
- **Date modified**
- **Size** (file count, row count)
- **People currently working** (real-time: who has this project/file open)
- **Activity log** (recent translations, pretranslations, etc.)

---

## 3. TM Explorer (NEW)

### 3.1 Project-Based TM Organization
**Current:** Global TM list, manual assignment
**Proposed:** TMs live INSIDE projects (like files)

```
Projects/
├── BDO_EN/
│   ├── Files/
│   │   ├── main_strings.xlsx
│   │   └── quest_text.xlsx
│   └── TMs/
│       ├── BDO_Main_TM (45K entries) [ACTIVE]
│       └── BDO_Legacy_TM (12K entries)
├── Another_Project/
│   ├── Files/
│   └── TMs/
```

### 3.2 TM Explorer Features
| Feature | Description |
|---------|-------------|
| Same project list | Shows same projects as File Explorer |
| Create TM in project | Right-click project → New TM |
| Auto-assignment | TM inside project = automatically assigned |
| Active TM per project | Set which TM is active for THAT project |
| Upload TM | Drag & drop or Upload button |
| Delete/Rename TM | Right-click context menu |
| View TM entries | Double-click opens TM viewer |
| Export TM | Right-click → Export |

### 3.3 TM Activation
- Each project has ONE active TM
- Active TM shown with visual indicator
- TM searches use the project's active TM
- Can still do cross-project TM lookups (optional setting)

---

## 4. TM Panel Cleanup

### 4.1 Remove TM Settings Modal
**Current:** Settings button opens TMManager modal with embedding options
**Proposed:** Delete the modal. Only keep:
- **Fast/Deep toggle** (already in TM list header)
- Everything else via right-click context menu

### 4.2 Fix Threshold UI/UX
**Issue:** Current threshold slider is unbalanced, text cutting off
**Fix:**
- Better spacing/padding
- Percentage always visible
- Slider properly aligned
- Consider moving to project-level TM settings

---

## 5. Dashboard Enhancements

### 5.1 Stats Hierarchy
Data can be viewed at different scales:

| Level | Example Stats |
|-------|--------------|
| **Team** | Total translations, team productivity, languages covered |
| **Language** | Per-language progress, quality metrics |
| **Project** | Project completion %, active users, recent activity |
| **User** | Personal stats, contributions, activity log |

### 5.2 Project-Specific Dashboard
- Translation progress per project
- Pretranslation stats
- TM match rates
- Active users on project
- Recent activity timeline

### 5.3 Activity Monitoring
- Real-time: Who is working on what
- Historical: Activity log per project/file
- Metrics: Translation speed, TM hit rates

---

## 6. Skip to Main Content Fix

### 6.1 Issue
- URL shows `http://localhost:5173/#main-content`
- LocaNext button has hidden "Skip to Main Content" when tabbed
- This is an accessibility feature but behaves unexpectedly

### 6.2 Fix
- Keep accessibility but hide visual artifact
- Ensure URL doesn't show `#main-content` in normal navigation
- Review Carbon Components accessibility patterns

---

## 7. Implementation Phases

## IMPLEMENTATION PLAN (Detailed)

### Approach: Recycle 90%, Restructure 10%

**RECYCLE (keep as-is):**
| Component | Reuse | Notes |
|-----------|-------|-------|
| `FileExplorer.svelte` | 95% | Tree, context menu, drag/drop, upload |
| `VirtualGrid.svelte` | 100% | Grid viewer unchanged |
| TM tab content | 90% | Extract to TMPage |
| All API calls | 100% | Already working |
| Context menus | 100% | Already working |
| Modals (Pretranslate, etc.) | 100% | Keep as-is |

**NEW/RESTRUCTURE:**
| Task | Type | Effort |
|------|------|--------|
| Navigation store | NEW | ~20 lines |
| LocaNext dropdown | NEW | ~50 lines |
| FilesPage.svelte | WRAPPER | Wraps FileExplorer |
| TMPage.svelte | EXTRACT | Move TM content |
| LDM.svelte | RESTRUCTURE | Page switching |

---

### Step 1: Navigation Foundation
```
- Create stores/navigation.js (currentPage: 'files' | 'tm' | 'grid')
- Add LocaNext dropdown in +layout.svelte
- Wire basic page switching
```

### Step 2: Extract Pages (Keep Current Behavior)
```
src/lib/components/pages/
├── FilesPage.svelte      ← Wraps FileExplorer, full width
├── TMPage.svelte         ← Extract TM tab content
└── GridPage.svelte       ← Grid viewer when file open

LDM.svelte refactor:
- Remove left column
- Add page switching logic
- Full width for each page
```

### Step 3: Transform Files to Windows/SharePoint Explorer
```
BEFORE (tree view):              AFTER (Windows Explorer):
┌─────────────────────┐         ┌─────────────────────────────────┐
│ [▼ Select Project]  │         │ 📁 Projects > BDO_EN > Strings  │ ← Breadcrumb
│ ├── 📁 Folder1      │   →     ├─────────────────────────────────┤
│ │   └── 📄 file.txt │         │ Name          Size    Modified  │
│ └── 📄 other.txt    │         │ 📁 Folder1    3 items  2h ago   │
└─────────────────────┘         │ 📄 file.txt   1.2K    1h ago    │
                                └─────────────────────────────────┘
```

**Windows Explorer Behaviors:**
| Action | Behavior |
|--------|----------|
| Double-click folder | ENTER folder (not expand tree) |
| Double-click file | OPEN in grid viewer |
| Breadcrumb click | Navigate back to that level |
| Right-click | Context menu (existing) |
| Drag & drop | Move items (existing) |
| Empty space right-click | New folder/project |
| Backspace key | Go up one level |

### Step 4: Transform TM to Explorer Pattern
```
┌─────────────────────────────────────────┐
│ 📚 Translation Memories                 │
├─────────────────────────────────────────┤
│ Name              Entries   Status      │
│ 📚 BDO_Main_TM    45,230   ● ACTIVE    │
│ 📚 BDO_Legacy     12,100   ○ inactive  │
└─────────────────────────────────────────┘
Double-click: View entries
Right-click: Activate, Export, Delete
```

### Step 5: Polish & Enhance
```
- Properties panel (file/folder metadata)
- "Who's working" real-time indicator
- Activity log
- Keyboard shortcuts (Enter, Backspace, Delete, F2)
```

---

## Legacy Phases (Reference)

### Phase 10.1: Navigation & Layout (Foundation)
1. Create navigation store
2. Add LocaNext dropdown menu
3. Remove left column from LDM
4. Merge User into Settings

### Phase 10.2: File Explorer Redesign
1. Windows-style folder navigation (grid view, not tree)
2. Breadcrumb navigation
3. Double-click = enter/open
4. Properties panel

### Phase 10.3: TM Explorer
1. TM Explorer page (separate from Files)
2. Per-project TM organization
3. TM grid view with status indicators

### Phase 10.4: Dashboard & Monitoring
1. Project-level stats
2. Activity monitoring
3. Real-time presence indicators

---

## 8. Files to Modify

| Component | Changes |
|-----------|---------|
| `+layout.svelte` | Add LocaNext dropdown, remove skip-to-content issue |
| `AppBar.svelte` | Merge User into Settings |
| `LDM.svelte` | Remove left column, full-width grid |
| `FileExplorer.svelte` | Major rewrite for Windows-style UX |
| New: `TM Explorer` | New page/component |
| New: `/files/+page.svelte` | Files page route |
| New: `/tm/+page.svelte` | TM page route |
| `routes/` | New routing structure |

---

## 9. Quick Wins (Can Do Now)

- [ ] Fix threshold slider UI (padding/alignment)
- [ ] Remove TM Settings modal (keep Fast/Deep only)
- [ ] Fix Skip to Main Content URL artifact
- [ ] Merge User button into Settings

---

## 10. Open Questions

1. Should TMs be moveable between projects?
2. Cross-project TM search - on by default or opt-in?
3. Properties panel - modal or slide-out panel?
4. Dashboard - separate page or embedded in Files/TM views?

---

*This is a major overhaul. Recommend implementing in phases with user feedback at each stage.*
