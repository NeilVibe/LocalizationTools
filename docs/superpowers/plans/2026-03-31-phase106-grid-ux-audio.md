# Phase 106 Plan: Grid UX Overhaul + Audio Fix (v2 — post 6-agent review)

> **Spec:** `docs/superpowers/specs/2026-03-31-phase106-grid-ux-audio.md`
> **Status:** PLAN v2 — incorporates 13 fixes from 6-agent review
> **Wave 1:** Plans 1 + 4 (independent, can parallelize)
> **Wave 2:** Plans 2 + 5 (inline edit + logging — logging references edit architecture)
> **Wave 3:** Plans 3 + 6 (audio investigation + cleanup)

---

## Plan 1: Status Color Fix

**Goal:** Neutral grid on import. Yellow only after user edit (Tab). Blue-green only after user confirm (Ctrl+S).

### Tasks

1. **Backend: File handlers — import status**
   - `server/tools/ldm/file_handlers/xml_handler.py:225` — `"translated" if target else "pending"` → `"original" if target else "pending"`
   - `server/tools/ldm/file_handlers/excel_handler.py:128` — same
   - `server/tools/ldm/file_handlers/txt_handler.py:102` — same
   - **No migration. User erases DB. New uploads get `"original"` status.**

2. **Backend: Pydantic schema** *(REVIEW FIX #3)*
   - `server/tools/ldm/routes/rows.py:311` — `BatchRowUpdate.status` Literal: add `"original"` to allowed values
   - `server/tools/ldm/schemas/row.py` — `RowUpdate.status` is `Optional[str]`, no change needed (already accepts any string)

3. **Backend: Unconfirmed filter — 4 locations** *(REVIEW FIX #1)*
   - `server/repositories/postgresql/row_repo.py:342` — SQLAlchemy unconfirmed filter: add `"original"`
   - `server/repositories/postgresql/row_repo.py:361` — count query: add `"original"`
   - `server/repositories/postgresql/row_repo.py:464` — raw SQL COPY path: add `"original"`
   - `server/repositories/sqlite/row_repo.py:391` — raw SQL: add `"original"`

4. **Backend: Auto-promote guard** *(REVIEW FIX #2 — CRITICAL)*
   - `server/repositories/postgresql/row_repo.py:172-173` — `if row.status == "pending"` → `if row.status in ("pending", "original")`
   - `server/repositories/sqlite/row_repo.py:195-198` — same change
   - **Without this, editing an `"original"` row NEVER turns yellow. Core workflow broken.**

5. **Backend: Download/export translated filter** *(REVIEW FIX #4)*
   - `server/repositories/postgresql/row_repo.py:391-392` — `status_filter="translated"` expansion: add `"original"` to the IN clause
   - `server/repositories/sqlite/row_repo.py:458-460` — same
   - **Without this, downloading "all translated" silently skips pre-existing translations.**

6. **Frontend: CellRenderer color mapping**
   - Add `class:status-original={!row.placeholder && row.status === 'original'}` — NO color
   - CSS:
     ```css
     .virtual-row.status-original { background: transparent; }
     .cell.target.status-original { background: transparent; border-left: none; }
     .status-dot.original { background: transparent; }
     ```
   - Keep yellow for `"translated"` (user pressed Tab), blue-green for `"reviewed"` (Ctrl+S)

7. **Frontend: gridState filter fix**
   - `gridState.svelte.ts:193` — add `|| r.status === 'original'` to unconfirmed filter

8. **Frontend: SelectionManager context menu**
   - `SelectionManager.svelte:392` — "Mark as translated" disabled guard: no change needed (`"original"` rows correctly show this enabled)
   - Add to files list for awareness

### Files Modified
- `server/tools/ldm/file_handlers/xml_handler.py`
- `server/tools/ldm/file_handlers/excel_handler.py`
- `server/tools/ldm/file_handlers/txt_handler.py`
- `server/tools/ldm/routes/rows.py`
- `server/repositories/postgresql/row_repo.py` (4 locations)
- `server/repositories/sqlite/row_repo.py` (3 locations)
- `locaNext/src/lib/components/ldm/grid/CellRenderer.svelte`
- `locaNext/src/lib/components/ldm/grid/gridState.svelte.ts`
- `locaNext/src/lib/components/ldm/grid/SelectionManager.svelte` (verify only)

### Verification
- Upload 173k row XML → ALL cells neutral grey
- Edit one cell, press Tab → THAT cell turns yellow, no others
- Edit another cell, press Ctrl+S → THAT cell turns blue-green
- Unconfirmed filter → shows `"original"` + `"pending"` + `"translated"` rows
- Download with `status_filter=translated` → includes `"original"` rows

---

## Plan 2: Inline Cell Editing — Positioned Overlay ON the Cell

**Goal:** Edit feels like the cell itself opened. MemoQ/Excel-style. No floating panel below the row.

### Architecture Change from v1 *(REVIEW FIX #6 — CRITICAL)*

**v1 plan said:** Put `<textarea>` INSIDE the virtualized row in CellRenderer.
**Problem:** Virtual scroll destroys the textarea when user scrolls away. `textareaEl` becomes null. Unsaved content lost. All 6 agents flagged this.

**v2 plan:** Keep the textarea as a **positioned overlay OUTSIDE the virtual scroll loop**, but position it EXACTLY on top of the target cell. Same visual result (looks like the cell opened), but the overlay survives scroll.

```
BEFORE (broken): Floating panel BELOW the row, shows Source+Target+Footer
AFTER (v2):      Textarea overlay EXACTLY on top of target cell, no Source, no Footer
                  Same width, same height, same font, same padding
                  Visually identical to the cell opening for editing
                  Lives OUTSIDE {#each visibleRows} — never destroyed by virtual scroll
```

### State Architecture *(REVIEW FIX #7)*

- `grid.editRowId` → moves to gridState.svelte.ts (CellRenderer reads it for highlight)
- `editValue` → stays LOCAL in EditOverlay (NOT in grid state — avoids keystroke reactivity cascade)
- `editTextareaEl` → plain `let` in EditOverlay (NOT reactive)

### Auto-Grow Without Jank *(REVIEW FIX #5 — CRITICAL)*

**Problem:** `$effect` on `editValue` calls `updateRowHeight` on every keystroke → iterates 173k Float64Array entries → `grid.rowsVersion++` → re-derives `visibleRows` → re-renders 50 rows. On every character.

**Fix:** Decouple textarea height from cumulative height update.

```
ON EVERY KEYSTROKE:
  1. textarea.style.height = 'auto'
  2. textarea.style.height = textarea.scrollHeight + 'px'
  3. Track prevHeight vs newHeight
  4. If height ACTUALLY changed (|delta| >= 1px):
     → debounced updateRowHeight (200ms timeout, or on blur)
     → NOT on every keystroke

ON BLUR / SAVE / CANCEL:
  → immediate updateRowHeight (final height)
```

This means during rapid typing on the same line: zero cumulative array updates. Only when a linebreak actually changes the height does the debounce fire.

### EditOverlay Restructure *(REVIEW FIX from architect agent)*

Don't create a renderless editController. **Keep EditOverlay.svelte as a component** but change its HTML:

**DELETE:**
- `.edit-overlay` floating panel div
- `.overlay-source` (source already visible in grid)
- `.overlay-footer` (hotkey bar moves to grid bottom)

**KEEP:**
- All keyboard handler logic
- All save/confirm/cancel logic
- Color picker context menu HTML + logic
- `lockRow`/`unlockRow` logic
- `textareaEl` reference (it owns the textarea)

**CHANGE:**
- The single `<textarea>` is now styled as `position: absolute` overlay on the cell
- Position computed from `getRowTop(editRowIndex) + columnOffset - scrollOffset`
- Width matches target column width exactly
- Height auto-grows with content
- Blue focus ring: `outline: 2px solid #0f62fe`

### Auto-Advance Sequence

```
1. Save current row to API (optimistic, single PUT)
2. Clear grid.editRowId → overlay textarea disappears
3. Set grid.selectedRowId = nextRow.id → CellRenderer highlights next row
4. scrollToRow(nextIndex) → containerEl.scrollTop = target position
5. Wait until next row is in visible range:
   → requestAnimationFrame → check if row is visible → if not, wait another RAF
   → MAX 5 RAFs then give up (don't open edit if scroll failed)
6. Set grid.editRowId = nextRow.id → overlay textarea appears on correct cell
7. tick() → textarea.focus() → cursor at end
```

### Sub-Steps for Safe Rollback *(REVIEW FIX #11)*

**Sub-step A (commit separately, git tag `phase106-plan2a`):**
- Move `editRowId` to gridState
- EditOverlay reads from `grid.editRowId` instead of local state
- Floating panel still renders (old UX preserved)
- Zero UX change — just state migration

**Sub-step B (commit separately):**
- Delete floating panel HTML
- Add positioned-overlay textarea
- Add auto-advance sequence
- Add hotkey bar at grid bottom

If Sub-step B fails, revert to tag. Sub-step A survives.

### Tasks

1. **Sub-step A: State migration**
   - `gridState.svelte.ts`: add `editRowId` to `grid` object, add to `resetGridState()`
   - `EditOverlay.svelte`: read/write `grid.editRowId` instead of local `editRowId`
   - `CellRenderer.svelte`: add `class:editing={grid.editRowId === row.id}` for highlight
   - Commit + tag

2. **Sub-step B: Overlay-on-cell**
   - `EditOverlay.svelte`: delete `.edit-overlay` panel HTML
   - `EditOverlay.svelte`: render `<textarea>` with `position: absolute; top: {cellTop}px; left: {targetColLeft}px; width: {targetColWidth}px`
   - Position computed from: `getRowTop(rowIndex) - scrollOffset + gridContainerOffsetTop`
   - Width from: CellRenderer's target column flex width (pass as prop or compute from DOM)
   - Auto-grow: immediate `style.height`, debounced `updateRowHeight` (200ms)
   - Scroll listener: reposition overlay on scroll (already exists, just fix the math)

3. **Auto-advance**
   - Replace `endEditAndMoveNext` with the 7-step sequence above
   - Add `scrollToRow(index)` to ScrollEngine if missing
   - Visible-range check before opening edit (max 5 RAF)

4. **Hotkey bar**
   - `VirtualGrid.svelte`: add `{#if grid.editRowId}` fixed bar at bottom
   - Content: `[Enter] Linebreak [Tab] Save+Next [Ctrl+S] Confirm [Esc] Cancel`

5. **Color picker**
   - Keep in EditOverlay, reads `textareaEl` directly (same component owns it)
   - No cross-component ref needed (overlay owns the textarea)

### Files Modified
- `locaNext/src/lib/components/ldm/grid/gridState.svelte.ts`
- `locaNext/src/lib/components/ldm/editor/EditOverlay.svelte` (MAJOR)
- `locaNext/src/lib/components/ldm/grid/CellRenderer.svelte` (highlight class only)
- `locaNext/src/lib/components/ldm/VirtualGrid.svelte` (hotkey bar)
- `locaNext/src/lib/components/ldm/grid/ScrollEngine.svelte` (scrollToRow)

### Verification
- Double-click target cell → textarea appears ON the cell (same position, width, font)
- Type → textarea stays on the cell, auto-grows
- Enter → linebreak, textarea expands, rows below shift (debounced 200ms)
- Tab → saves (yellow), textarea closes, next row opens (correct position)
- Ctrl+S → saves (blue-green), next row opens
- Esc → cancel, textarea closes, no advance
- Scroll during edit → textarea repositions with the cell (stays attached)
- Fast scroll away → textarea stays visible (not destroyed by virtual scroll)
- Right-click → color picker at cursor
- Rapid Tab 5x → each textarea appears on correct row

---

## Plan 3: Audio Player Fix

**Goal:** WEM audio files play in the Windows app.

### Specific Investigation Steps *(REVIEW FIX #12)*

1. **FIRST ACTION: Get the Windows log and grep for `vgmstream`**
   - Log location: `%APPDATA%\LocaNext\logs\main.log` OR `<installDir>\logs\`
   - Look for one of these lines:
     - `"Found vgmstream-cli in ..."` → path detection worked, problem is elsewhere
     - `"vgmstream-cli not found in any search path"` → path detection failed
     - Neither → `_find_vgmstream()` never ran (lazy init, first audio request triggers it)

2. **Check `LOCANEXT_RESOURCES_PATH` env var** *(REVIEW FIX #12)*
   - `locaNext/electron/main.js` lines 241-255 — the `spawn()` call
   - This env var is likely NEVER SET → search path 2 in `_find_vgmstream()` always misses
   - Fix: add `LOCANEXT_RESOURCES_PATH` to the spawn env

3. **Check `_vgmstream_checked` singleton guard**
   - `server/tools/ldm/services/media_converter.py` — if first call fails, all future calls return None silently
   - This means if timing is wrong on startup, audio is permanently disabled for the session

4. **Check CI bundling**
   - `.github/workflows/build-electron.yml` line ~893 — vgmstream download step
   - `package.json` `extraResources` — `bin/vgmstream` → `resources/bin/vgmstream`
   - Verify on Playground: does `<installDir>\resources\bin\vgmstream\vgmstream-cli.exe` exist?

5. **Two separate audio systems**
   - `AudioTab.svelte` → `/api/ldm/mapdata/audio/stream/{string_id}` (MapData pathway)
   - `AudioCodexPage.svelte` → `/api/ldm/codex/audio/stream/{event_name}` (Codex pathway)
   - Both broken or just one?

6. **Check if WEM files are accessible**
   - MegaIndex shows `WEM EN=57535 KR=57351 ZH=53022` — paths indexed
   - But are the physical WEM files accessible from the Windows app at runtime?
   - Perforce drive must be mounted

### Files to Read
- `server/tools/ldm/services/media_converter.py` — `_find_vgmstream()` and `stream_audio()`
- `locaNext/electron/main.js` lines 241-255 — spawn env vars
- `server/tools/ldm/routes/mapdata.py` — audio stream endpoint
- `server/tools/ldm/services/mapdata_service.py` — `get_audio_context()` and 3-folder routing
- `.github/workflows/build-electron.yml` — vgmstream download step
- `locaNext/src/lib/components/ldm/AudioTab.svelte` — player UI

### Verification
- Check Windows log for vgmstream detection line
- Verify binary exists at `<installDir>\resources\bin\vgmstream\vgmstream-cli.exe`
- Click audio tab on a row with audio → player renders
- Click play → audio plays

---

## Plan 4: Image Preload + Dedup (STOP THE SPAM)

**Goal:** Load image mappings into client cache on file open. Zero per-row API calls during scroll.

### Architecture *(incorporates REVIEW FIXES #8, #9, #10)*

**Batch endpoint — exact match only, no fuzzy:** *(FIX #9)*
```python
@router.post("/api/ldm/mapdata/images/batch")
async def batch_image_lookup(body: BatchImageRequest):
    """Exact-match image lookup for batch of StringIDs. No fuzzy fallback."""
    # Run in thread to avoid blocking event loop
    results = await asyncio.to_thread(_batch_lookup, body.string_ids)
    return results

def _batch_lookup(string_ids: list[str]) -> dict:
    results = {}
    for sid in string_ids:
        # EXACT MATCH ONLY — skip fuzzy scan stages
        info = mapdata_service._strkey_to_image.get(sid)
        if info:
            results[sid] = info
    return results
```

**Request size guard:** *(FIX #8)*
- Frontend: filter to unique non-null string_ids BEFORE sending
- From log: ~26k rows have images out of 173k. After dedup, likely ~20k unique string_ids
- If > 50k IDs: chunk into batches of 50k
- POST body: ~20k × 30 chars = ~600KB (well within limits)

**No fallback fetch during preload window:** *(FIX #10)*
- Add `$state imagesReady = false` flag in gridState
- CellRenderer: if `!imagesReady`, show nothing in image column (not a fallback fetch)
- After preload completes: `imagesReady = true` → image column renders from cache
- **ZERO per-row fetches at any time**

**Cache location and lifecycle:**
- `imageCache` = plain `new Map()` in `gridState.svelte.ts` (alongside `rowHeightCache`)
- Cleared in `resetGridState()` alongside other caches
- `imagesReady` = `$state(false)` in grid object, reset on file change

**ImageTab side panel — keep per-row fetch for DETAIL:**
- ImageTab shows full image + metadata + `fallback_reason` diagnostic text
- Batch preload returns existence + thumbnail only (exact match)
- ImageTab keeps its `$effect` fetch for selected row DETAIL view
- But add AbortController dedup (already has it) + cache check: if `imageCache.has(stringId)`, use cached thumbnail, only fetch for `fallback_reason` and full image path

**MegaIndex not built yet:**
- If batch endpoint returns 503 (MapDataService not initialized), set `imagesReady = true` with empty cache
- When MegaIndex builds later, frontend does NOT auto-retry batch (user would need to reload file)
- This is acceptable — MegaIndex build is a one-time setup action

### Tasks

1. **Backend: batch endpoint (exact match only, in thread)**
   - `server/tools/ldm/routes/mapdata.py` — new `POST /images/batch`
   - Direct dict lookup on `_strkey_to_image`, NO fuzzy scan
   - Wrapped in `asyncio.to_thread` for safety
   - Size guard: reject > 250k IDs with 413

2. **Frontend: preload on file open**
   - `gridState.svelte.ts` — add `imageCache = new Map()` and `imagesReady` flag
   - `VirtualGrid.svelte` or `GridPage.svelte` — after bulk load, call preload
   - Filter unique non-null string_ids, chunk if > 50k

3. **Frontend: CellRenderer reads from cache**
   - Image column: `{#if imagesReady && imageCache.has(row.string_id)}` → show thumbnail
   - No fallback fetch. Cache miss = no image shown.

4. **Frontend: ImageTab keeps detail fetch**
   - Keep `$effect` fetch for selected row detail (full image + fallback_reason)
   - Add cache check: skip API call if `imageCache.has(stringId)` and thumbnail is sufficient

### Files Modified
- `server/tools/ldm/routes/mapdata.py`
- `locaNext/src/lib/components/ldm/grid/gridState.svelte.ts`
- `locaNext/src/lib/components/ldm/grid/CellRenderer.svelte`
- `locaNext/src/lib/components/ldm/VirtualGrid.svelte` or `GridPage.svelte`
- `locaNext/src/lib/components/ldm/ImageTab.svelte` (cache check addition)

### Verification
- Open file → log: `GRID: preloaded images, total=20k, found=11k`
- Scroll → ZERO `/api/ldm/mapdata/image/` calls
- Click row with image → ImageTab loads detail (1 fetch for full info)
- MegaIndex not built → image column empty, no errors

---

## Plan 5: Grid Debug Logging Enrichment

**Goal:** Every grid operation produces a debug log. *(Moved to Wave 2 — references Plan 2 edit architecture)*

### Tasks

1. **gridState.svelte.ts**
   - `GRID: loaded {n} rows, {filtered} after filter, {memoryMB}MB`
   - `GRID: heights computed in {ms}ms for {n} rows`
   - `GRID: filter applied, {before} → {after} rows`

2. **CellRenderer.svelte**
   - `GRID: rendering rows {first}-{last} of {total}` (throttled 1/sec)
   - `GRID: image cache hit/miss {stringId}`

3. **ScrollEngine.svelte**
   - `GRID: scroll offset={px}, visible={first}-{last}` (throttled 1/sec)
   - `GRID: scrollToRow {index}, target top={px}`

4. **SelectionManager.svelte**
   - `GRID: selected row {id} (index={idx})`

5. **EditOverlay.svelte** (after Plan 2 restructure)
   - `GRID: edit start row={id}, cell top={px}, col left={px}`
   - `GRID: edit save row={id} in {ms}ms, status={status}`
   - `GRID: auto-advance from row {id} → row {nextId}, scrolled={px}`
   - `GRID: edit height debounce fired, row={id}, delta={px}`

6. **VirtualGrid.svelte**
   - `GRID: mounted, fileId={id}`
   - `GRID: ws cell update row={id}`

### Files Modified
- All grid module files (8 files)

---

## Plan 6: Other Log Issues (Cleanup)

**Goal:** Fix duplicate API calls, event loop blocking, ResizeObserver noise.

### Tasks

1. **Guard `loadRoot` with plain boolean** *(REVIEW FIX #13)*
   - `let loaded = false` — NOT `$state`, plain boolean. Prevents write-in-effect loop.
   - `if (loaded) return; loaded = true; loadRoot()`

2. **Guard platform/project fetches**
   - Cache in module-level Map, skip fetch if already populated

3. **MegaIndex: background thread**
   - `server/tools/ldm/routes/mega_index.py` — wrap build in `asyncio.to_thread`
   - Prevents 52s event loop block, fixes WS disconnect + offline/status timeout

4. **ResizeObserver suppression**
   - `locaNext/electron/main.js` — add window error handler that filters `ResizeObserver loop` messages

### Files to Investigate/Modify
- `locaNext/src/lib/components/pages/FilesPage.svelte`
- `server/tools/ldm/routes/mega_index.py`
- `locaNext/electron/main.js`

---

## Execution Order (FINAL)

| Wave | Plan | Parallelize | Depends On |
|------|------|-------------|------------|
| 1 | Plan 1 (Status Color) | Yes | Nothing |
| 1 | Plan 4 (Image Preload) | Yes | Nothing |
| 2 | Plan 2 Sub-A (State Migration) | No | Plan 1 |
| 2 | Plan 2 Sub-B (Overlay-on-Cell) | No | Sub-A committed + tagged |
| 2 | Plan 5 (Logging) | Yes | Plan 2 Sub-B (references edit architecture) |
| 3 | Plan 3 (Audio) | Yes | Nothing |
| 3 | Plan 6 (Cleanup) | Yes | Nothing |

**Complexity:**
- Plan 1: Medium (5+ backend files with 4 filter locations + 2 auto-promote guards)
- Plan 2: LARGE (2 sub-steps, overlay repositioning, debounced auto-grow, auto-advance sequence)
- Plan 3: Medium (investigation-heavy, specific files identified)
- Plan 4: Medium (batch endpoint + cache + preload lifecycle)
- Plan 5: Small (logging additions, done after Plan 2)
- Plan 6: Small-Medium (guards + background thread)

## Anti-Spam Guarantees

| Vector | Status | How |
|--------|--------|-----|
| 173k row UPDATE on import | **IMPOSSIBLE** | Status set at parse time per row, not UPDATE |
| Per-row image fetch on scroll | **ELIMINATED** | Batch preload cache, no fallback fetch |
| TM calls with no TM | **ALREADY GUARDED** | `if (!activeTMs) return` in StatusColors |
| Auto-grow cascade | **DEBOUNCED** | textarea height immediate, updateRowHeight on 200ms timer |
| editValue keystroke cascade | **ISOLATED** | editValue stays LOCAL in EditOverlay, not in grid state |
| Duplicate loadRoot | **GUARDED** | Plain boolean flag |
| Auto-advance N+1 | **IMPOSSIBLE** | One PUT per save, one startEdit per advance |
