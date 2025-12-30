# FileExplorer UI Refactor

> **Status:** COMPLETE | **Date:** 2025-12-31

---

## Summary

Simplified the FileExplorer component to use accordion-style navigation and context menus instead of button clutter.

---

## Changes Made

### 1. Accordion-Style Navigation

**Before:**
- Horizontal project tabs at top
- Limited vertical space for files
- Projects crowded when many exist

**After:**
- Full-height project list when no project selected
- Click project → drills into contents
- Back button (chevron left) to return to project list
- Folders closed by default, click to expand/collapse

### 2. Context Menus Replace Buttons

**Before:**
- Upload button in toolbar
- New Folder button in toolbar
- "Link a TM for auto-add" bar below project name

**After:**
- Right-click project header → Import File, New Folder, Link TM, Rename
- Right-click folder → Rename, Import File Here, Create Subfolder
- Right-click file → All existing options (Download, Merge, Convert, QA, etc.)
- Right-click empty space → Same as project header (Import File, New Folder)

### 3. Rename Support

- F2 hotkey for rename (like Windows Explorer)
- Double-click on project name to rename
- Context menu "Rename" option on projects, folders, files
- Inline editing with Enter to save, Escape to cancel

---

## Files Modified

| File | Changes |
|------|---------|
| `FileExplorer.svelte` | Accordion layout, context menus, rename support |
| `projects.py` | Added PATCH rename endpoint |
| `folders.py` | Added PATCH rename endpoint |
| `files.py` | Added PATCH rename endpoint |

---

## UX Patterns

### Right-Click Menus (Like Windows Explorer)

| Target | Available Actions |
|--------|------------------|
| Project header | Import File, New Folder, Link TM, Rename |
| Folder | Rename, Import File Here, Create Subfolder |
| File | Rename, Download, Merge, Convert, QA checks, TM registration |
| Empty space | Import File, New Folder, Link TM |

### Folder Expand/Collapse

- Folders start collapsed (closed)
- Click folder → toggles expand/collapse
- Chevron rotates to indicate state
- Children indented within folder

### TM Link Indicator

- Small green "TM" tag appears next to project name when TM is linked
- Right-click → "Change Linked TM..." if TM already linked
- Right-click → "Link TM..." if no TM linked

---

## Technical Notes

### Svelte 5 Patterns Used

```javascript
// Folder expand state
let expandedFolders = $state(new Set());

function toggleFolder(folderId) {
  const newExpanded = new Set(expandedFolders);
  if (newExpanded.has(folderId)) {
    newExpanded.delete(folderId);
  } else {
    newExpanded.add(folderId);
  }
  expandedFolders = newExpanded; // Reassign to trigger reactivity
}
```

### API Endpoints Added

```
PATCH /api/ldm/projects/{project_id}/rename?name=NewName
PATCH /api/ldm/folders/{folder_id}/rename?name=NewName
PATCH /api/ldm/files/{file_id}/rename?name=NewName
```

---

## Debug Tip Learned

**Backend server restart required for new endpoints!**

If you add new API endpoints and get "Not found" errors, check if the server was restarted:

```bash
curl localhost:8888/openapi.json | grep "your-endpoint"
```

If endpoint not listed → restart server:
```bash
pkill -f "python.*server/main.py"
DEV_MODE=true python3 server/main.py &
```

---

## TM Manager Modal UX Improvements (2025-12-31)

### Issues Fixed

1. **Scrollbar removed** - Modal now auto-expands based on content, no unnecessary scrollbar
2. **Active/Inactive UX improved**:
   - Active: Green dot indicator + "Active" text
   - Inactive: Plain gray "Inactive" text
   - Click to toggle state

### Implementation

```css
/* Override Carbon Modal's fixed max-height to auto-expand */
:global(.bx--modal-container--lg .bx--modal-content) {
  max-height: none;
  overflow: visible;
}
```

```svelte
<button class="status-toggle" class:is-active={isActive}>
  {#if isActive}
    <span class="status-dot active"></span>
    <span>Active</span>
  {:else}
    <span class="status-text-inactive">Inactive</span>
  {/if}
</button>
```

---

*Completed 2025-12-31*
