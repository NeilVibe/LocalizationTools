# Grid Redesign: Content-Aware Heights + Floating Edit Overlay (Option B v2)

**Date:** 2026-03-31
**Status:** APPROVED
**Problem:** Grid freezes, linebreaks broken, cells don't expand, 173k height rebuilds on every save

---

## Summary

Replace the broken variable-height grid + inline contenteditable with:
- **Content-aware row heights** computed ONCE on file load (cells match text beautifully)
- **Cumulative height array** built ONCE on load, NEVER fully rebuilt during editing
- **Single-row update on save** — recompute ONE row's height + incremental shift (0.15ms)
- **Floating edit overlay** anchored to the selected row (MemoQ-style)
- **Native `<textarea>`** for editing (Enter = linebreak, unlimited, no hacks)
- **`$state.raw`** for row data (zero proxy overhead on 173k objects)

---

## Height System: Compute Once, Update One

```
FILE OPEN (once):
  For each of 173k rows → estimateRowHeight(text)     ~4ms
  Build cumulative Float64Array                         ~1ms
  TOTAL: ~5ms. FROZEN after this.

SCROLLING:
  Binary search cumulative array → O(log n)            0.01ms
  Render ~50 visible rows at pre-computed heights       ~2ms

EDITING (overlay open):
  Grid heights: UNTOUCHED. Zero cost.

SAVE (Tab / Ctrl+S):
  Re-estimate ONE row's height                          0.001ms
  Compute delta (newHeight - oldHeight)
  Shift cumulative[rowIndex+1 .. end] by delta          0.15ms
  DONE. No full rebuild.

SEARCH / FILTER:
  Full rebuild on FILTERED subset (not all 173k)        ~2ms
```

---

## Architecture

### Two Zones

```
┌──────────────────────────────────────────────────────┐
│  GRID (content-aware heights, virtual scroll)         │
│  Row 14 (48px): 마을에 도착했습니다 │ Arrived...      │
│  Row 15 (72px): 이름을 입력하세요   │ Enter your     │
│                  최대 20자          │ name below...   │
│  ┌──────────────────────────────────────────────────┐ │
│  │ EDIT OVERLAY (floats over rows below)            │ │
│  │ Source: 이름을 입력하세요                         │ │
│  │         최대 20자                                │ │
│  │ ─────────────────────────────────────────────── │ │
│  │ Target: Enter your name█                        │ │
│  │         Maximum 20 characters                   │ │
│  │ [Tab: Save+Next] [Ctrl+S: Confirm] [Esc: Close] │ │
│  └──────────────────────────────────────────────────┘ │
│  Row 18 (48px): 전투 시작           │ Battle start    │
└──────────────────────────────────────────────────────┘
```

### Grid Zone (existing, simplified)

- Rows: `position: absolute; min-height: {rowHeight}px; top: {cumulativeTop}px`
- Content: FULL text displayed (no truncation, no ellipsis). Cells wrap naturally.
- Heights pre-computed from text content on load. Multi-line text = taller rows.
- Click = select row. Double-click = open edit overlay.
- NO inline editing. NO contenteditable. NO height recalculation during browsing.
- Scroll math: binary search on cumulative array — O(log n)

### Edit Overlay

- `position: absolute`, anchored below the selected row
- Appears ON TOP of the grid, covering rows below
- Contains: source text (read-only, TagText) + target textarea (editable)
- `<textarea bind:value>` — native linebreaks, auto-grows
- Keyboard: Enter = linebreak, Tab = save + next, Ctrl+S = confirm, Esc = cancel
- On save: update ONE row's height + incremental shift. Grid re-renders that row.

### State Management

```
gridState.svelte.ts (rewritten):
- allRows: $state.raw([])              ← NO proxy on 173k objects
- displayRows: $state.raw([])          ← filtered subset, also no proxy
- grid: $state({ scalars only })       ← cheap
- rowIndexById: new Map()              ← plain Map
- heightCache: new Map<number,number>()← plain Map, populated on load
- cumulativeHeights: Float64Array      ← built once on load, incremental update on save
- estimateRowHeight(row)               ← pure math, no DOM measurement
- getRowTop(i) → cumulativeHeights[i]  ← O(1) lookup
- findRowAtPosition(s) → binary search ← O(log n)
- updateRowHeight(index, newHeight)    ← single-row incremental shift, 0.15ms
```

---

## What Gets Deleted

| File/Code | Lines | Why |
|-----------|-------|-----|
| `InlineEditor.svelte` | 818 | All editing moves to EditOverlay |
| `rebuildCumulativeHeights` call on save | ~5 | Replaced by single-row `updateRowHeight` |
| `handleEditInput` (CellRenderer) | ~25 | No inline editing in cells |
| `measureRowHeight` action | ~25 | No post-render DOM measurement |
| contenteditable template + CSS | ~80 | No contenteditable |
| **Total removed** | **~950** | |

## What Gets Created

| File | Purpose | Est. Lines |
|------|---------|-----------|
| `editor/EditOverlay.svelte` | Floating edit panel with textarea | ~300 |

## What Gets Simplified

| File | Change |
|------|--------|
| `gridState.svelte.ts` | $state.raw for rows. Keep estimateRowHeight + cumulative array. Add updateRowHeight (single-row). Delete rebuildCumulativeHeights from save path. |
| `CellRenderer.svelte` (1025→~650) | Remove inline editing, contenteditable, handleEditInput. Keep full content display with wrapping. |
| `ScrollEngine.svelte` (234→~180) | Remove rebuildCumulativeHeights from loadRows (call buildHeights once). Simplify clientFilter. |
| `VirtualGrid.svelte` (388→~300) | Wire EditOverlay instead of InlineEditor. |

---

## What Stays The Same

- `estimateRowHeight` — still computes height from text content (pure math)
- `cumulativeHeights` Float64Array — still used for scroll positioning
- Binary search `findRowAtPosition` — still O(log n)
- `getRowTop(i)` — still reads cumulative array
- Virtual scroll rendering ~50 rows — unchanged
- Column layout, colors, status badges, QA badges — unchanged
- Search/filter — unchanged (rebuilds on filtered subset)

---

## Performance Comparison

| Operation | Current (broken) | New |
|-----------|---------|-----|
| File open | O(n) height + O(n) proxy + O(n) cumulative | O(n) height + O(n) cumulative (no proxy — $state.raw) |
| Scroll | Binary search (same) | Binary search (same) |
| Edit a cell | contenteditable + execCommand hacks + O(n) height on keystroke | Open overlay — zero grid cost |
| Save a cell | **O(n) rebuildCumulativeHeights = 4s freeze** | **O(1) re-estimate + O(remaining) shift = 0.15ms** |
| Linebreak | Broken after first `<br>` | Native `<textarea>` — unlimited |

---

## Linebreak Handling

| Direction | Conversion |
|-----------|-----------|
| DB → textarea | `<br/>` and `&lt;br/&gt;` → `\n` |
| textarea → DB | `\n` → `&lt;br/&gt;` (XML) or `\n` (text) |

---

## Edit Overlay Behavior

1. **Open**: Double-click row OR press Enter on selected row
2. **Position**: Anchored below selected row, overlaps rows below
3. **Layout**: Source (read-only TagText) on top, Target textarea below
4. **Auto-grow**: Textarea height = scrollHeight
5. **Keyboard**: Enter=linebreak, Tab=save+next, Ctrl+S=confirm, Esc=cancel
6. **On save**: `updateRowHeight(index, newEstimate)` → incremental shift → grid updates ONE row
7. **Close**: On save, cancel, or clicking outside

---

---

## Changed vs Confirmed Status System

### DB State

Current `status` field values and their meaning:

| Status | Color | Meaning | Merge? |
|--------|-------|---------|--------|
| `untranslated` | Gray | No translation yet | NO |
| `translated` | **Yellow** | Text changed but NOT reviewed | NO |
| `reviewed` | **Blue-green** | Confirmed by translator | **YES** |
| `approved` | Green | Approved by reviewer | **YES** |

**Key rule:** Merge operations (to-file, to-folder, DB merge) ONLY take rows with status `reviewed` or `approved`. Rows with `translated` (yellow/changed) are EXCLUDED from merge output.

### UI Colors

| Status | Row background | Status badge |
|--------|---------------|-------------|
| `untranslated` | default (layer-01) | none |
| `translated` | `rgba(255, 214, 0, 0.08)` | yellow dot |
| `reviewed` | `rgba(0, 200, 150, 0.08)` | blue-green dot |
| `approved` | `rgba(0, 180, 100, 0.08)` | green dot |

### Edit Flow

- **Tab (save)** → status becomes `translated` (yellow). Text is saved but NOT confirmed.
- **Ctrl+S (confirm)** → status becomes `reviewed` (blue-green). Text is saved AND confirmed.
- This matches MemoQ: Tab = next segment (auto-save as fuzzy), Ctrl+Enter = confirm segment.

### DB Metadata

The `ldm_rows` table already has `status`, `updated_by`, `updated_at`. No schema change needed — just enforce the status values consistently.

---

## Find & Replace All (Ctrl+F) — Mass Change Modal

### Trigger
- `Ctrl+H` opens the Find & Replace modal (Ctrl+F reserved for search bar focus)
- Or: menu button in toolbar

### Modal Layout

```
┌──────────────────────────────────────────────────────┐
│  Find & Replace                                [X]   │
│                                                       │
│  Find:    [________________________] [.*] [Aa] [W]   │
│  Replace: [________________________]                  │
│                                                       │
│  Scope: ○ All rows  ○ Selected rows  ○ Source  ● Target │
│                                                       │
│  ┌─ Matches (47 found) ─────────────────────────────┐ │
│  │ Row 142: "old text" → "new text"                 │ │
│  │ Row 891: "old text" → "new text"                 │ │
│  │ Row 2034: "old text" → "new text"                │ │
│  │ ...                                              │ │
│  └──────────────────────────────────────────────────┘ │
│                                                       │
│  [Replace & Change] [Replace & Confirm] [Replace All] │
│  [Change All]       [Confirm All]       [Cancel]      │
└──────────────────────────────────────────────────────┘
```

### Buttons

| Button | Action | Status set to |
|--------|--------|--------------|
| **Replace & Change** | Replace current match, move to next | `translated` (yellow) |
| **Replace & Confirm** | Replace current match, move to next | `reviewed` (blue-green) |
| **Replace All → Change** | Replace ALL matches | `translated` (yellow) |
| **Replace All → Confirm** | Replace ALL matches | `reviewed` (blue-green) |
| **Cancel** | Close modal, no changes | — |

### Options
- `[.*]` = Regex mode toggle
- `[Aa]` = Case-sensitive toggle
- `[W]` = Whole word toggle
- Scope: All rows / Source column / Target column

### Implementation
- Runs client-side on `displayRows` array (already in memory)
- Preview: `Array.filter` + regex match → show matches with context
- Apply: `for` loop over matches → `updateRow(rowId, { target: replaced, status })` → single API batch call
- After apply: rebuild heights for changed rows (incremental, not full)

### Backend
- New endpoint: `PUT /api/ldm/files/{file_id}/rows/batch-update`
- Body: `{ updates: [{ row_id, target, status }] }`
- Single transaction for all changes (atomic — all succeed or all fail)

### Audio Issue (Separate)
`vgmstream-cli` bundling/path issue. Fix separately.

### Image Mapping (Separate)
Expand C6 bridge beyond StringID-only matching. Fix separately.
