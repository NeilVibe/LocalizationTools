# Font Settings Enhancement

**Priority:** P2 | **Status:** COMPLETE | **Created:** 2025-12-28 | **Completed:** 2025-12-29

---

## Current State

| Setting | Status |
|---------|--------|
| Font Size | ✅ Small (12px) / Medium (14px) / Large (16px) |
| Font Weight | ✅ Normal / Bold toggle |
| Font Family | ✅ System, Inter, Roboto, Noto Sans, Source Han, Consolas |
| Font Color | ✅ Default / High Contrast / Soft |

**Location:** `PreferencesModal.svelte`

---

## Proposed Changes

### 1. Settings Button UX Improvement

**Current:** Direct modal open
**Proposed:** Dropdown menu with categories

```
[Settings Button ▼]
  ├── Font Settings...
  ├── Grid Columns...
  ├── Reference File...
  └── TM Manager...
```

**Benefits:**
- Scalable for future settings
- Cleaner UI
- Quick access to specific settings

### 2. Font Family Selection

Add dropdown with common monospace and proportional fonts:

```javascript
const fontFamilies = [
  { value: 'system', label: 'System Default' },
  { value: 'inter', label: 'Inter' },
  { value: 'roboto', label: 'Roboto' },
  { value: 'noto-sans', label: 'Noto Sans' },
  { value: 'source-han', label: 'Source Han Sans (CJK)' },
  { value: 'consolas', label: 'Consolas (Monospace)' },
  { value: 'monaco', label: 'Monaco (Monospace)' }
];
```

**Note:** Include CJK-friendly fonts for Korean/Chinese/Japanese text.

### 3. Font Color Selection

Simple color picker or preset options:

```javascript
const fontColors = [
  { value: 'default', label: 'Default (Theme)', color: null },
  { value: 'black', label: 'Black', color: '#000000' },
  { value: 'dark-gray', label: 'Dark Gray', color: '#333333' },
  { value: 'blue', label: 'Blue', color: '#0043ce' },
  { value: 'green', label: 'Green', color: '#198038' }
];
```

---

## Implementation Plan

### Step 1: Create Settings Dropdown

New component: `SettingsDropdown.svelte`
```svelte
<OverflowMenu>
  <OverflowMenuItem text="Font Settings..." on:click={openFontModal} />
  <OverflowMenuItem text="Grid Columns..." on:click={openColumnsModal} />
  ...
</OverflowMenu>
```

### Step 2: Extend Preferences Store

```javascript
// preferences.js
const defaultPreferences = {
  fontSize: 'medium',
  fontWeight: 'normal',
  fontFamily: 'system',  // NEW
  fontColor: 'default'   // NEW
};
```

### Step 3: Update PreferencesModal

Add new selects for family and color.

### Step 4: Apply to Grid

```svelte
<div class="virtual-grid" style="
  font-size: {$fontSize};
  font-weight: {$fontWeight};
  font-family: {$fontFamily};
  color: {$fontColor};
">
```

---

## Files to Modify

| File | Changes |
|------|---------|
| `preferences.js` | Add fontFamily, fontColor to store |
| `PreferencesModal.svelte` | Add family/color selects |
| `VirtualGrid.svelte` | Apply font styles |
| `LDM.svelte` | Replace settings button with dropdown |
| NEW: `SettingsDropdown.svelte` | Settings menu component |

---

## Success Criteria

- [ ] Settings button shows dropdown menu (SKIPPED - optional UX)
- [x] Font family can be changed
- [x] Font color can be changed
- [x] Changes apply immediately to grid
- [x] Settings persist across sessions

---

## Implementation Notes

**Files Modified:**
- `preferences.js` - Added fontFamily, fontColor to store + helpers
- `PreferencesModal.svelte` - Added family/color Select components
- `VirtualGrid.svelte` - CSS variables for font-family and color

**CSS Variables:**
```css
--grid-font-size: 14px;
--grid-font-weight: 400;
--grid-font-family: "Noto Sans", sans-serif;
--grid-font-color: var(--cds-text-01);
```

*P2 COMPLETE - Core functionality implemented 2025-12-29*
