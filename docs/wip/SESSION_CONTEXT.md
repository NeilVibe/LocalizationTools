# Session Context

> Last Updated: 2026-01-03 (Session 17 - Complete)

---

## STABLE CHECKPOINT

**Pre-P5 Stable:** `b6f2561` (Session 14) | **Date:** 2026-01-02 | **Tag:** Auto-updater verified

Use this if you need to go back to BEFORE P5 Advanced Search changes.

**Post-Session 17 Stable:** `3b7108e` | **Date:** 2026-01-03 | **Tag:** Build 438 - All bugs fixed

---

## Current State

**Build:** 438 | **Open Issues:** 1 (DESIGN-001)
**Status:** Session 17 complete - All bugs fixed, ready for P3

### Open Issues

1. **DESIGN-001: Remove owner_id filtering** - MEDIUM
   - All LDM data filtered by owner, wrong for team tool
   - All users should see same data

### Database State (Clean)

| Item | Count |
|------|-------|
| Platforms | 1 (Main Platform) |
| Projects | 1 (Main Project) |
| Folders | 1 (Main Folder) |
| Files | 1 (sample.txt, 3 rows) |
| TMs | 1 (Main TM, ko→en) |

---

## NEXT PHASE: P3 Offline/Online Mode

**Priority:** HIGH | **Effort:** 10 weeks | **Doc:** `OFFLINE_ONLINE_MODE.md`

### Quick Summary

| Feature | Description |
|---------|-------------|
| **Auto-Connect** | Always online if server reachable, auto-fallback to offline |
| **Manual Sync** | Right-click → Download/Sync (user controls WHAT and WHEN) |
| **Add/Edit Only** | No deletions synced between modes |
| **Recycle Bin** | 30-day soft delete before permanent removal |
| **Beautiful UI** | Sync Dashboard, Toast notifications, Status icons |

### Implementation Phases

| Phase | Scope | Weeks |
|-------|-------|-------|
| **Phase 1** | Foundation - Basic offline viewing/editing | 1-2 |
| **Phase 2** | Change Tracking - Track all local changes | 3-4 |
| **Phase 3** | Sync Engine - Push local changes to server | 5-6 |
| **Phase 4** | Conflict Resolution - Handle conflicts gracefully | 7-8 |
| **Phase 5** | File Dialog - Path selection for new files | 9 |
| **Phase 6** | Polish & Edge Cases - Production-ready | 10 |

### Key Files to Create/Modify

| File | Purpose |
|------|---------|
| `server/database/offline_schema.sql` | SQLite tables for offline |
| `server/api/sync.py` | Sync API endpoints |
| `server/sync/differ.py` | Diff algorithm |
| `server/sync/merger.py` | Merge logic |
| `SyncStatusPanel.svelte` | Mode indicator + dashboard |
| `SyncPreviewDialog.svelte` | Show what will sync |
| `ConflictResolver.svelte` | Conflict resolution UI |
| `SyncFileDialog.svelte` | Windows-style path selector |

---

## SESSION 17 SUMMARY (2026-01-03)

### All Bugs Fixed

| Bug | Root Cause | Fix |
|-----|------------|-----|
| **Color disappears after edit** | Regex stripped PAColor tags | Negative lookahead regex |
| **Cell height too big** | Double-counting newlines + wrap | New `countDisplayLines()` algorithm |
| **Resize bar scroll issue** | Bars inside scroll container | Moved to wrapper outside scroll |
| **Text bleeding/zombie rows** | `{@const}` not reactive | Call `getRowTop()`/`getRowHeight()` directly |

### Key Commits

| Commit | Description |
|--------|-------------|
| `f252d06` | Color fix + Cell height fix + Resize bar wrapper |
| `17067b8` | **ROOT CAUSE FIX:** Reactive row positioning |
| `3b7108e` | Build 438: Reactive row positioning fix |

### Build 438 - SUCCESS

| Platform | Status | Duration |
|----------|--------|----------|
| **Gitea** (Windows) | ✅ SUCCESS | 22m 23s |
| **GitHub** (Win/Mac/Linux) | ✅ SUCCESS | 15m 15s |

### FIXED: Text Bleeding / Zombie Rows (ROOT CAUSE)

**Problem:** After scrolling or resizing columns, rows would overlap or "zombie" rows would appear.

**Root Cause:** Svelte's `{@const}` creates a non-reactive constant:
```svelte
<!-- OLD (buggy) - rowTop evaluated ONCE, never updates -->
{@const rowTop = getRowTop(rowIndex)}
<div style="top: {rowTop}px">
```

When `cumulativeHeights` state changed (after measuring actual row heights), the `rowTop` variable didn't update because `{@const}` is not reactive.

**Fix:** Call the function directly in the style binding:
```svelte
<!-- NEW (correct) - reactive, recalculates when state changes -->
<div style="top: {getRowTop(rowIndex)}px; min-height: {getRowHeight(rowIndex)}px;">
```

**File:** `locaNext/src/lib/components/ldm/VirtualGrid.svelte:2100`

**Performance:** O(1) lookups from pre-computed `cumulativeHeights` array, negligible overhead.

### FIXED: Color Disappears After Edit Mode

**Root Cause:** Line 280 in `colorParser.js`:
```javascript
result.replace(/<[^>]+>/g, '');  // WRONG: strips ALL HTML tags including PAColor!
```

**Fix:** Use negative lookahead to preserve PAColor tags:
```javascript
result.replace(/<(?!\/?PA(?:Color|OldColor))[^>]+>/g, '');  // CORRECT
```

**File:** `locaNext/src/lib/utils/colorParser.js:280`

### FIXED: Cell Height Too Big

**Root Cause:** Old algorithm DOUBLE-COUNTED lines:
```javascript
// OLD (buggy):
const wrapLines = Math.ceil(maxLen / 55);     // Assumed all chars in one block
const totalLines = wrapLines + maxNewlines;   // Added newlines ON TOP = WRONG
```

**Fix:** New `countDisplayLines()` function splits by newlines FIRST:
```javascript
// NEW (correct):
const segments = normalized.split('\n');
let totalLines = 0;
for (const segment of segments) {
  totalLines += Math.max(1, Math.ceil(segment.length / 55));
}
```

**File:** `locaNext/src/lib/components/ldm/VirtualGrid.svelte:1593-1650`

### FIXED: Resize Bar Not Working After Scroll

**Problem:** Column resize bar disappeared or didn't work after scrolling.

**Fix:** Moved resize bars outside scroll-container into a new `scroll-wrapper` div.

**File:** `locaNext/src/lib/components/ldm/VirtualGrid.svelte:2069-2081`

---

## SESSION 16 SUMMARY (2026-01-03)

### P5 Advanced Search - COMPLETE

| Feature | Status |
|---------|--------|
| Fuzzy Search (pg_trgm) | ✅ Implemented |
| Search UI Redesign | ✅ Settings popover with mode icons |
| Mode Icons | ⊃ Contains, = Exact, ≠ Excludes, ≈ Similar |
| Threshold | 0.3 (configurable in rows.py) |

### 100% ENDPOINT COVERAGE ACHIEVED

**All 220 endpoints tested!**
- Generated 149 test stubs via `endpoint_audit.py --generate-stubs`
- Fixed 4 Auth bugs (activate/deactivate user transaction conflict)
- Location: `tests/api/test_generated_stubs.py`

---

## PREVIOUS SESSIONS

### Session 15 (2026-01-02) - P3 Planning
- Complete specification for Offline/Online Mode (~1200 lines)
- All design decisions resolved

### Session 14 (2026-01-02) - Auto-Updater Fix
- Fixed 7 auto-updater issues (AU-001 to AU-007)
- Changed from GitHub to Gitea generic provider
- Created 2-tag release system (versioned + `latest`)

### Session 13 (2026-01-01) - CI/CD Fixes
- Added gsudo for Windows service control
- Fixed macOS build (electron-builder config)
- Added pg_trgm extension to CI workflows

### Session 12 (2026-01-01) - UI Polish
- Fixed CTRL+S not adding to TM
- Added TM indicator with scope
- Unified Settings/User menu

### Session 11 (2026-01-01) - TM Hierarchy Complete
- All 5 sprints complete
- Database schema, backend, frontend all working

---

## KEY FILES

### P3 Implementation

| File | Purpose |
|------|---------|
| `docs/wip/OFFLINE_ONLINE_MODE.md` | **Complete spec (~1200 lines)** |

### Core Implementation Files

| File | Purpose |
|------|---------|
| `locaNext/src/lib/components/ldm/VirtualGrid.svelte` | Main grid (fixed) |
| `locaNext/src/lib/utils/colorParser.js` | Color parsing (fixed) |
| `locaNext/src/lib/components/ldm/FileExplorer.svelte` | File tree |
| `locaNext/src/routes/+layout.svelte` | App layout |
| `server/tools/ldm/routes/*.py` | LDM API endpoints |

### Planning Documents

| File | Purpose |
|------|---------|
| `docs/wip/OFFLINE_ONLINE_MODE.md` | P3 complete spec |
| `docs/wip/PHASE_10_MAJOR_UIUX_OVERHAUL.md` | Phase 10 plan |
| `docs/wip/ADVANCED_SEARCH.md` | P5 plan (DONE) |
| `docs/wip/COLOR_PARSER_EXTENSION.md` | P4 guide |
| `docs/wip/ISSUES_TO_FIX.md` | Bug tracker |

---

## ARCHITECTURE REMINDER

```
LocaNext.exe (User PC)           Central PostgreSQL
├─ Electron + Svelte 5       →   ├─ All text data
├─ Embedded Python Backend       ├─ Users, sessions
├─ FAISS indexes (local)         ├─ LDM rows, TM entries
├─ Model2Vec (~128MB)            └─ Logs
├─ Qwen (2.3GB, opt-in)
└─ File parsing (local)

ONLINE:  PostgreSQL (multi-user, WebSocket sync)
OFFLINE: SQLite (single-user, auto-fallback) ← P3 enhances this
```

---

## QUICK COMMANDS

```bash
# DEV servers
./scripts/start_all_servers.sh --with-vite

# Check servers
./scripts/check_servers.sh

# Build trigger
echo "Build" >> GITEA_TRIGGER.txt && git add -A && git commit -m "Build" && git push origin main && git push gitea main

# Playground install
./scripts/playground_install.sh --launch --auto-login

# Check build status (SQL)
python3 -c "
import sqlite3
c = sqlite3.connect('/home/neil1988/gitea/data/gitea.db').cursor()
c.execute('SELECT id, status, title FROM action_run ORDER BY id DESC LIMIT 3')
STATUS = {0:'UNKNOWN', 1:'SUCCESS', 2:'FAILURE', 3:'CANCELLED', 4:'SKIPPED', 5:'WAITING', 6:'RUNNING', 7:'BLOCKED'}
for r in c.fetchall(): print(f'Run {r[0]}: {STATUS.get(r[1], r[1]):8} - {r[2]}')"
```

---

## STATS

| Metric | Value |
|--------|-------|
| Build | 438 |
| Tests | 1,548 (+149) |
| Endpoints | 220 (100% tested!) |
| Open Issues | 1 (DESIGN-001) |
| Planning Docs | 4 complete |

---

*Session 17 Complete - All bugs fixed, Build 438 SUCCESS, Ready for P3 Offline/Online Mode*
