# Session Context

> Last Updated: 2026-01-03 (Session 19 - P3 In Progress)

---

## STABLE CHECKPOINT

**Pre-P3 Stable:** `ed1d4d3` | **Date:** 2026-01-03 | **Tag:** Ready for Offline/Online Mode

Use this checkpoint to go back to BEFORE P3 Offline/Online changes.

**Latest Commit:** `0dd2c43` | **Date:** 2026-01-03 | **Tag:** P3-2 Sync subscription model

---

## Current State

**Build:** 439 | **Open Issues:** 0
**Status:** Session 19 - P3 Offline/Online Mode Phase 2 Complete

### P3 Progress

| Phase | Status | Description |
|-------|--------|-------------|
| P3-1 | ✅ DONE | Download for offline infrastructure |
| P3-2 | ✅ DONE | Sync subscription model + dashboard |
| P3-3 | ⏳ TODO | Auto-sync file on open |
| P3-4 | ⏳ TODO | Continuous sync mechanism |

---

## SESSION 19 SUMMARY (2026-01-03)

### P3-1: Download Infrastructure (COMPLETE)

| Task | Status |
|------|--------|
| SQLite schema (`offline_schema.sql`) | ✅ |
| OfflineDatabase class (`offline.py`) | ✅ |
| Sync store (`sync.js`) | ✅ |
| Mode indicator UI | ✅ |
| Download API endpoint | ✅ |

### P3-2: Sync Subscription Model (COMPLETE)

| Task | Status |
|------|--------|
| `sync_subscriptions` table | ✅ |
| Subscribe/Unsubscribe endpoints | ✅ |
| Context menu: Enable/Disable Offline Sync | ✅ |
| Sync Dashboard with subscriptions list | ✅ |
| Remove subscription from dashboard | ✅ |

### Key Files Created/Modified

| File | Purpose |
|------|---------|
| `server/database/offline_schema.sql` | SQLite tables for offline + sync_subscriptions |
| `server/database/offline.py` | OfflineDatabase class with subscription methods |
| `server/tools/ldm/routes/sync.py` | Sync API endpoints (subscribe, list, download) |
| `locaNext/src/lib/stores/sync.js` | Sync state + subscription functions |
| `locaNext/src/lib/components/sync/SyncStatusPanel.svelte` | Mode indicator + dashboard |
| `locaNext/src/lib/components/pages/FilesPage.svelte` | Context menu with sync toggle |

### New API Endpoints

```
POST /api/ldm/offline/subscribe           - Subscribe for offline sync
DELETE /api/ldm/offline/subscribe/{type}/{id} - Unsubscribe
GET /api/ldm/offline/subscriptions        - List all subscriptions
GET /api/ldm/offline/status               - Get offline status (mode, stats)
GET /api/ldm/offline/files                - List downloaded files
POST /api/ldm/files/{id}/download-for-offline - Download single file
```

### Sync Dashboard UI

```
┌─────────────────────────────────────────────────────────────┐
│                    SYNC DASHBOARD                           │
│  ─────────────────────────────────────────────────────────  │
│  🟢 Online                                                  │
│  ─────────────────────────────────────────────────────────  │
│  Last Sync: 2 min ago    │   Pending Changes: 0            │
│  ─────────────────────────────────────────────────────────  │
│  Synced for Offline (3)                                     │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 📁 Game_Localization     project     ✓    [🗑]    │   │
│  │ 📁 Mobile_Strings        project     ✓    [🗑]    │   │
│  │ 📄 manual_fixes.txt      file        ✓    [🗑]    │   │
│  └─────────────────────────────────────────────────────┘   │
│                    [ Go Offline ]                           │
└─────────────────────────────────────────────────────────────┘
```

### Context Menu Options

Files, Projects, and Platforms now have:
- **Enable Offline Sync** - Subscribe and download for offline
- **Disable Offline Sync** - Remove subscription (data kept locally)

### Remaining for P3

| Task | Description |
|------|-------------|
| Auto-sync on file open | When user opens a file, auto-subscribe it |
| Continuous sync | Background periodic sync for subscribed items |

---

## Key Commits (Session 19)

| Commit | Description |
|--------|-------------|
| `649a315` | P3-1.1: SQLite schema |
| `da5d74f` | P3-1.2/1.3: Sync store + mode indicator |
| `d47e246` | P3-1.4-1.7: Complete Phase 1 |
| `0dd2c43` | P3-2: Sync subscription model + dashboard |

---

## PREVIOUS SESSION SUMMARIES

### Session 18 (2026-01-03) - DESIGN-001 Complete

| Change | Description |
|--------|-------------|
| **Default behavior** | All resources PUBLIC (everyone sees everything) |
| **Optional restriction** | Admins can restrict platforms/projects |
| **Globally unique names** | No duplicate names anywhere |
| **Access grants** | Admins assign users to restricted resources |

### Session 17 (2026-01-03) - All Bugs Fixed

| Bug | Fix |
|-----|-----|
| Color disappears after edit | Negative lookahead regex |
| Cell height too big | New `countDisplayLines()` algorithm |
| Resize bar scroll issue | Moved to wrapper outside scroll |
| Text bleeding/zombie rows | Reactive row positioning |

---

## KEY FILES

### P3 Implementation (Current)

| File | Purpose |
|------|---------|
| `server/database/offline_schema.sql` | SQLite tables |
| `server/database/offline.py` | OfflineDatabase class |
| `server/tools/ldm/routes/sync.py` | Sync API endpoints |
| `locaNext/src/lib/stores/sync.js` | Sync state management |
| `locaNext/src/lib/components/sync/SyncStatusPanel.svelte` | Mode indicator + dashboard |

### Core Implementation

| File | Purpose |
|------|---------|
| `locaNext/src/lib/components/ldm/VirtualGrid.svelte` | Main grid |
| `locaNext/src/lib/components/pages/FilesPage.svelte` | File explorer |
| `server/tools/ldm/permissions.py` | Permission helpers |

---

## ARCHITECTURE

```
LocaNext.exe (User PC)           Central PostgreSQL
├─ Electron + Svelte 5       →   ├─ All text data
├─ Embedded Python Backend       ├─ Users, sessions
├─ SQLite (offline storage)  ←   ├─ LDM rows, TM entries
├─ FAISS indexes (local)         └─ Logs
└─ Qwen model (optional)

ONLINE:  PostgreSQL (multi-user, WebSocket sync)
OFFLINE: SQLite (single-user, subscribed data only)

SYNC FLOW:
1. User subscribes (platform/project/file)
2. Initial download to SQLite
3. Continuous sync keeps data fresh
4. Changes tracked for push back
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
```

---

## STATS

| Metric | Value |
|--------|-------|
| Build | 439 |
| Tests | 1,548 |
| Endpoints | 220+ (P3 adds 6) |
| Open Issues | 0 |

---

*Session 19 - P3 Phase 2 Complete, Ready for Phase 3 (Auto-sync + Continuous sync)*
