# Session Context

> Last Updated: 2025-12-31 (Session 2)

---

## Current State

**Build:** 848+ (latest)
**Status:** UI bugs fixed, cell expansion working, TM matches fixed

---

## Recent Work (2025-12-31 - Session 2)

### BUG FIX: Grid Cells Not Expanding (Content Cut Off)

**Problem:** Long content in cells was cut off with ugly internal scrollbar. Users had to scroll INSIDE the cell to see all content.

**Root Cause:**
1. `MAX_ROW_HEIGHT = 300` capped cell height at 300px
2. `overflow-y: auto` on `.cell-content` created internal scrollbar

**Fix:**
- Increased `MAX_ROW_HEIGHT` from 300 to 800 in `VirtualGrid.svelte:30`
- Removed `overflow-y: auto` and `max-height` from `.cell-content`
- Updated `LINE_HEIGHT` (22 → 26) and `CELL_PADDING` (16 → 24) to match new spacing

### BUG FIX: TM Matches Panel Shows "No TM matches found"

**Problem:** Even with active TM (1.2K entries), the TM MATCHES panel showed no results.

**Root Cause:** `fetchTMSuggestions()` function (line 612) was NOT passing `tm_id` to the API, while another function (line 830) was.

**Fix:** Added `tm_id` parameter to `fetchTMSuggestions()`:
```javascript
if ($preferences.activeTmId) {
  params.append('tm_id', $preferences.activeTmId.toString());
}
```

### TM Modal More Spacious

- Increased padding: `padding: 1rem 0.5rem`
- Table cell padding: `0.75rem → 1rem 0.75rem`
- Header styling: lighter weight (500), smaller font (0.8125rem)
- Name cell max-width: `200px → 280px` with `word-break: break-word`

---

## Recent Work (2025-12-31 - Session 1)

### Direct File Upload (No Modal!)

- **Removed upload modal** - Now opens native file picker directly
- **Right-click → Import File** opens file dialog immediately
- **Toast notifications** for upload progress/success/failure

### Upload Performance Verified

| File | Size | Time | Speed | Rows |
|------|------|------|-------|------|
| SMALL | 371 KB | 0.99s | 375 KB/s | 1,183 |
| MEDIUM | 15.5 MB | 44.7s | 355 KB/s | 103,500 |
| BIG | 189 MB | 8.5min | 381 KB/s | 1.1M rows |

### UI Polish

- Cell padding: `0.5rem → 0.75rem 1rem`
- Line height: `1.4 → 1.6`
- Subtler borders: `border-strong → border-subtle`
- Header: removed uppercase, cleaner look

---

## What's Working

| Feature | Status |
|---------|--------|
| Grid cells expand to fit content | ✅ FIXED |
| No internal cell scrollbar | ✅ FIXED |
| TM matches panel works | ✅ FIXED |
| TM Modal spacious | ✅ FIXED |
| Direct file upload (no modal) | ✅ |
| Upload performance (tested) | ✅ |
| Task Manager error handling | ✅ |
| FileExplorer accordion style | ✅ |
| TM search with active TM | ✅ |

---

## Key Files Modified (Session 2)

- `src/lib/components/ldm/VirtualGrid.svelte` - Cell expansion fix, TM matches fix
- `src/lib/components/ldm/TMManager.svelte` - Modal spacing improvements

---

## Quick Commands

```bash
# Check servers
./scripts/check_servers.sh

# Start backend
DEV_MODE=true python3 server/main.py

# Frontend dev
cd locaNext && npm run dev

# User screenshots location (IMPORTANT!)
/mnt/c/Users/MYCOM/Pictures/Screenshots/
```

---

## Debug Tips

### User Screenshots Location
**CRITICAL:** User takes screenshots at `C:\Users\MYCOM\Pictures\Screenshots`
Access from WSL: `/mnt/c/Users/MYCOM/Pictures/Screenshots/`

### Cell Content Issues
If cells are cutting off content:
1. Check `MAX_ROW_HEIGHT` constant - increase if needed
2. Check `.cell-content` CSS - NO `overflow-y: auto` or `max-height`
3. Verify `LINE_HEIGHT` and `CELL_PADDING` match actual CSS values

### TM Not Working
If TM panel shows "No matches" even with active TM:
1. Check if `tm_id` is being passed to `/api/ldm/tm/suggest`
2. Look for `$preferences.activeTmId` - must be passed in params
3. Check server logs: `[TM-SUGGEST]` prefix shows what's happening

---

*Session context for Claude Code continuity*
