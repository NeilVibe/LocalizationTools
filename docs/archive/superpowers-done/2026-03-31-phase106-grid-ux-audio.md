# Phase 106 Spec: Grid UX Overhaul + Audio Fix

> **Date:** 2026-03-31
> **Source:** Windows app testing on PEARL PC (log analysis + user feedback)
> **Status:** PLANNING — DO NOT IMPLEMENT UNTIL PLAN APPROVED

---

## Issues Found (from log + user testing)

### BUG-1: All cells yellow by default (WRONG)

**Root cause:** `xml_handler.py:225` sets `status: "translated"` for every row that has a target value. On a 173k row file, virtually ALL rows have targets, so ALL rows get yellow highlighting.

**Expected behavior:**
- **Default (uploaded):** Neutral/grey — no color. New status: `"original"` or keep `"translated"` but DON'T color it.
- **Yellow** (`#ffd600`): Only when user edits and presses **Tab** (save without confirming) → status `"translated"` meaning "changed but not confirmed"
- **Blue-green** (`#00c896`): Only when user presses **Ctrl+S** → status `"reviewed"` meaning "confirmed translation"

**Fix approach:** Add a new status `"original"` for rows imported with existing targets. Only `"translated"` (user-edited) and `"reviewed"` (user-confirmed) get colors.
**No migration needed.** User will erase DB and start fresh. New uploads get `"original"` status from the file handlers. No global UPDATE of 173k rows — status is set per-row at import time, and changed per-row on individual edits only.

### BUG-2: Base grid is FINE (no fix needed)

Content-aware auto-sizing works. Keep it.

### BUG-3: EditOverlay is a modal at bottom of screen (BROKEN)

**Current behavior:** `EditOverlay.svelte` renders as `position: absolute; top: {overlayTop}px` — a floating panel BELOW the selected row. It shows Source + Target + Footer with hotkeys. This is NOT inline editing. It's a modal that appears somewhere below the cell, far from the actual content.

**Expected behavior (MemoQ-style):** When user double-clicks a target cell, THE CELL ITSELF opens for editing. No modal. No panel. The target cell transforms into an editable textarea, positioned EXACTLY where the cell is, same width, same position. It looks like the cell just became editable.

**Reference:** MemoQ, SDL Trados — cell opens in-place. No extra Source panel, no extra footer during normal editing.

### BUG-4: Auto-advance to next row broken (INOPERABLE)

**Current behavior:** `endEditAndMoveNext(true)` on line 213-231 automatically calls `startEdit(nextRow)` after confirm. The problem: the overlay positions itself at `overlayTop` which is calculated from `getRowTop(rowIndex) + getRowHeight(rowIndex) - scrollOffset`. When auto-advancing, the scroll position hasn't updated yet, so the overlay appears FAR from the actual next row — somewhere at the bottom of the screen.

**Root cause:** Scroll-to-row doesn't happen before `startEdit()`. The overlay position calculation uses stale `scrollOffset`.

### BUG-5: Audio not playing

**Current behavior:** vgmstream-cli is not bundled in the Electron build. The audio tab shows files but clicking play does nothing.

**Root cause:** vgmstream-cli binary was supposed to be downloaded in CI and bundled into `resources/tools/vgmstream/`. This was implemented in Phase 103 commits but either the CI step failed or the binary path detection is wrong in production.

### BUG-6: Image API spam (no client-side cache)

**From log:** Same image StringID fetched 5-10+ times during scroll/edit. `mapdata/image/10002194124941296144` fetched 5x in 2 seconds. `mapdata/image/10012566539418469520` fetched 10+ times during editing. Each = OPTIONS preflight + GET = 2 HTTP requests.

**Root cause:** CellRenderer fetches image data lazily per visible row. Every scroll/edit re-triggers. No frontend cache.

**Fix:** Bulk preload ALL image mappings on file open. Store in plain Map. Zero per-row API calls.

### BUG-7: Duplicate API calls on navigation

**From log:** `loadRoot`, `GET /platforms`, `GET /projects` all fire 2x on every page navigation. `Loaded root` logged twice at 12:12:30 and 12:12:51.

**Root cause:** SvelteKit `+error.svelte` workaround for Electron `file://` protocol causes double mount.

### BUG-8: MegaIndex build blocks all API requests

**From log:** `GET /api/ldm/offline/status` took 52,766ms — blocked behind the synchronous MegaIndex build. WebSocket disconnected for 7 seconds during the build.

**Root cause:** MegaIndex build runs synchronously on the main asyncio event loop, blocking all other requests.

### BUG-9: No grid debug logging

**Current behavior:** Zero `console.log`/`console.debug` in VirtualGrid, GridPage, CellRenderer, gridState. Only logger calls in the 4 submodules (StatusColors, SelectionManager, ScrollEngine, SearchEngine). When things go wrong in the grid, the log shows NOTHING.

**Missing logging:**
- Row render timing (how long to render visible range)
- Scroll performance (FPS, jank detection)
- Height computation timing
- Selection changes with coordinates
- Edit overlay position calculations
- Image fetch dedup (same image fetched 10+ times — see log)

---

## Architecture Decision: Inline Cell Editing

### Option A: Transform cell in-place (MemoQ-style)
- When editing, the target cell's `<div>` becomes a `<textarea>`
- Same DOM position, same width, same height (auto-grows)
- Source shown as read-only row above (already visible in grid)
- No overlay, no modal, no panel
- **Pro:** True MemoQ feel. Cell IS the editor.
- **Con:** Must handle virtual scroll unmounting — if user scrolls away, the editing cell might get destroyed

### Option B: Positioned overlay EXACTLY on the cell (current approach, fixed)
- Keep the overlay but position it EXACTLY on top of the target cell
- Match cell width, top, left precisely
- Remove the Source panel (source is already visible in the adjacent column)
- Remove the footer (hotkeys can be a tooltip)
- **Pro:** Simpler to implement, overlay persists during scroll
- **Con:** Still technically an overlay, not the cell itself

### DECISION: Option A (true inline, MemoQ-style)

The cell itself becomes editable. The `<textarea>` replaces the cell content when editing. This is what MemoQ does and what the user wants.

---

## Plan Structure

### Plan 1: Status Color Fix (BUG-1)
- Add `"original"` status for rows imported with existing translations
- `xml_handler.py`, `excel_handler.py`, `txt_handler.py`: change `"translated"` → `"original"` for import
- `CellRenderer.svelte`: no color for `"original"`, yellow for `"translated"`, blue-green for `"reviewed"`
- `EditOverlay.svelte`: Tab saves as `"translated"`, Ctrl+S saves as `"reviewed"`
- Backend: accept `"original"` status in row schema

### Plan 2: Inline Cell Editing (BUG-3, BUG-4) — NUCLEAR REWRITE of EditOverlay
- Delete the floating panel approach
- CellRenderer.svelte: when a row is being edited, render `<textarea>` INSIDE the target cell div
- Textarea matches cell dimensions exactly
- Auto-grow textarea pushes row height (already have `updateRowHeight`)
- Tab: save as `"translated"`, advance to next row, scroll into view, THEN open edit
- Ctrl+S: save as `"reviewed"`, advance to next row
- Esc: cancel, cell reverts to display mode
- Enter: native linebreak
- Color picker: right-click on textarea (keep existing logic)
- Source text: already visible in the source column — no need to show it again
- Hotkey hints: show as a subtle bar at the bottom of the grid (always visible), not per-cell

### Plan 3: Audio Player Fix (BUG-5)
- Investigate vgmstream-cli bundling in CI (`.github/workflows/`)
- Check `sys.executable` path detection in production
- Verify the audio player component path resolution
- Test with actual WEM file

### Plan 4: Grid Debug Logging Enrichment (BUG-6)
- Add timing logs to: bulk load parse, visible range calc, row render, height compute
- Add position logs to: edit start (cell coords), scroll events (offset, visible range)
- Add dedup tracking: image fetch counter (detect spam)
- All logs use `logger.debug()` for grid operations, `logger.info()` for user actions

---

## Success Criteria

1. Uploaded file shows neutral/grey cells — NO yellow on import
2. After Tab: cell turns yellow (changed, not confirmed)
3. After Ctrl+S: cell turns blue-green (confirmed)
4. Double-click target cell: textarea appears INSIDE the cell, same position, same width
5. Tab from edit: saves, moves to next row, next row's target cell opens as textarea
6. Audio files play when clicking play button
7. Grid operations produce debug logs visible in Electron log
