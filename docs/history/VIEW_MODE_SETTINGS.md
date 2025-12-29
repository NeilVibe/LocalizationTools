# View Mode Settings (Modal vs Inline)

**Priority:** P2 | **Status:** PLANNING | **Created:** 2025-12-28

---

## Problem

Current edit workflow requires opening a modal for every edit. This adds friction for power users who want faster editing like in MemoQ.

---

## Proposed Solution: View Mode Toggle

Add a setting in **Settings > General** to choose between:

### Option 1: Modal Mode (Current)
```
Double-click cell → Opens Edit Modal
- Full editing interface
- TM search panel
- QA issues panel
- Spell check
```

### Option 2: Inline Mode (MemoQ-style)
```
Single-click cell  → Highlights row, triggers TM search (side panel)
Double-click cell  → Inline edit directly in grid
- No modal popup
- TM/QA shown in collapsible right column
- Faster workflow for experienced users
```

---

## UI Changes

### Settings > General
```
View Mode:
  ○ Modal (default) - Double-click opens edit modal
  ● Inline - Edit directly in grid, TM/QA in side panel
```

### Grid Changes (Inline Mode)

| Feature | Modal Mode | Inline Mode |
|---------|------------|-------------|
| Single-click | Select row | Select row + TM search |
| Double-click | Open modal | Inline edit in cell |
| TM results | In modal | Side panel (right) |
| QA issues | In modal | Side panel (right) |
| Save | Modal button | Enter or blur |

### New: TM/QA Column Toggle
```
Settings > Columns:
  [x] Show TM/QA Column

Grid:
  | Row | Source | Target | TM/QA |
  |-----|--------|--------|-------|
  | 1   | Hello  | Bonjour| 98% ⚠ |
```

- Shows TM match % and QA warning icon
- Clicking opens detail panel
- Can be hidden via settings

---

## Implementation Plan

### Phase 1: Settings Infrastructure
1. Add `viewMode` to preferences store ("modal" | "inline")
2. Add `showTmQaColumn` toggle
3. Update PreferencesModal with General section

### Phase 2: Inline Editing
1. Make cells editable on double-click (inline mode)
2. Handle Enter to save, Escape to cancel
3. Tab to next cell

### Phase 3: Side Panel
1. Create TM/QA side panel component
2. Show on single-click (inline mode)
3. Collapsible, resizable

### Phase 4: TM/QA Column
1. Add optional column to VirtualGrid
2. Show TM match % badge
3. Show QA warning icon if issues

---

## Files to Modify

| File | Changes |
|------|---------|
| `PreferencesModal.svelte` | Add General section, viewMode toggle |
| `preferences.js` | Add viewMode, showTmQaColumn settings |
| `VirtualGrid.svelte` | Handle inline edit mode |
| `LDMFileView.svelte` | Wire up single-click TM search |
| NEW: `TMQASidePanel.svelte` | Side panel for TM/QA |
| NEW: `TMQAColumn.svelte` | Optional grid column |

---

## Backward Compatibility

- Default: Modal mode (current behavior)
- Existing users unaffected
- New users can switch in settings
- Edit Modal code preserved, just toggled

---

## MemoQ Comparison

| MemoQ | LocaNext (Proposed) |
|-------|---------------------|
| Single-click = TM search | Same |
| Double-click = inline edit | Same |
| TM in side panel | Same |
| QA in separate view | QA in same side panel |

---

## Notes

- Keep Edit Modal for complex operations (bulk edit, metadata)
- Inline mode for quick translation work
- Both modes fully functional
- User preference saved locally

---

*Improves workflow speed for power users while keeping familiar modal for beginners*
