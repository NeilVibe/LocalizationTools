# Session Context

> Last Updated: 2025-12-31

---

## Current State

**Build:** 848+ (latest)
**Status:** UI refinements complete, ready for next feature work

---

## Recent Work (2025-12-31)

### FileExplorer UI Refactor

- **Accordion navigation** - Full-height project list, drill-down into contents
- **Context menus replace buttons** - Right-click for Import, New Folder, Link TM, Rename
- **Rename support** - F2 hotkey, double-click, context menu
- **Folders collapsed by default** - Click to expand/collapse

### TM Manager Modal UX

- **Removed scrollbar** - Auto-expand based on content
- **Active/Inactive indicator** - Green dot for active, plain text for inactive

### TM Search Fix (BUG FIX!)

- **Bug:** `/tm/suggest` endpoint ignored `tm_id` parameter - only searched project rows, not TM entries
- **Fix:** Added `tm_id` parameter support - now searches `ldm_tm_entries` when TM is active
- **Schema updated:** `TMSuggestion` now supports both row-based and TM-based suggestions

### Toast Notifications Fix

- **Max 3 toasts** visible at once (no stacking)
- **Deduplication** - same toast filtered within 2s
- **"Unknown operation"** toasts filtered out

### Database Cleanup

- Cleaned all test projects/files/TMs
- Created fresh: 1 project, 1 file (10 rows), 1 TM (10 entries)

---

## What's Working

| Feature | Status |
|---------|--------|
| FileExplorer accordion style | ✅ |
| Project context menu | ✅ |
| Folder context menu | ✅ |
| File context menu | ✅ |
| Rename (F2, double-click) | ✅ |
| TM Manager modal | ✅ |
| Active TM indicator | ✅ |
| TM search with active TM | ✅ FIXED |
| Toast notifications | ✅ FIXED |

---

## Next Steps

1. **Testing** - Verify all context menu actions work correctly
2. **Edge cases** - Test with many projects/files
3. **P3: Offline/Online Mode** - Next major feature (see Roadmap.md)

---

## Quick Commands

```bash
# Check servers
./scripts/check_servers.sh

# Start backend
DEV_MODE=true python3 server/main.py

# Frontend dev
cd locaNext && npm run dev

# Desktop app
cd locaNext && npm run electron:dev
```

---

## Key Files Modified

- `src/lib/components/ldm/FileExplorer.svelte` - Accordion + context menus
- `src/lib/components/ldm/TMManager.svelte` - Modal UX fixes
- `server/tools/ldm/routes/projects.py` - Rename endpoint
- `server/tools/ldm/routes/folders.py` - Rename endpoint
- `server/tools/ldm/routes/files.py` - Rename endpoint

---

*Session context for Claude Code continuity*
