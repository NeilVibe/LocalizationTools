# P26: Offline Mode for LocaNext

**Status:** Planning
**Priority:** High
**Created:** 2025-12-13

---

## Problem

Currently LocaNext has full central server interdependency:
- App tries to connect to central PostgreSQL server on startup
- If server unreachable → app fails or shows errors
- Users can't work when network is down or server is offline

## Solution: Automatic Offline Mode

When central server is unreachable, automatically switch to **OFFLINE MODE**:
- Detect connection failure on startup
- Enable local-only operation
- User continues working without interruption

## Scope

### Apps That Need Offline Mode
| App | Current State | Offline Mode Needed? |
|-----|--------------|---------------------|
| XLSTransfer | Works locally | No - already local |
| QuickSearch | Works locally | No - already local |
| KR Similar | Works locally | No - already local |
| **LDM** | Needs central DB | **YES** |

### LDM Offline Requirements
1. **Local SQLite fallback** - Store TM/rows locally when PostgreSQL unreachable
2. **Auto-detect** - Check server on startup, switch mode automatically
3. **Sync on reconnect** - When server available again, sync local changes
4. **UI indicator** - Show "OFFLINE" badge so user knows status

## Implementation Plan

### Phase 1: Detection
- [ ] Add server health check on app startup
- [ ] Timeout after 3 seconds → offline mode
- [ ] Store mode state in app context

### Phase 2: Local Storage
- [ ] SQLite database for offline LDM data
- [ ] Mirror PostgreSQL schema (simplified)
- [ ] Local TM storage and search

### Phase 3: UI Feedback
- [ ] "OFFLINE" indicator in status bar
- [ ] Warning when opening files in offline mode
- [ ] "Sync pending" counter for unsynced changes

### Phase 4: Sync
- [ ] Background server check (every 60s)
- [ ] Auto-sync when connection restored
- [ ] Conflict resolution (server wins? local wins? merge?)

## Technical Notes

```
Online Mode:
  App → PostgreSQL (central) → Real-time sync with other users

Offline Mode:
  App → SQLite (local) → Queue changes → Sync when online
```

## Questions to Resolve
1. Conflict resolution strategy when syncing?
2. How long to keep offline changes before warning?
3. Should offline mode support multi-user on same machine?

## Files to Modify
- `server/config.py` - Add offline detection
- `locaNext/electron/` - Add connection check
- `server/database/` - Add SQLite fallback
- `server/tools/ldm/` - Add offline storage layer

---

*This is a planning document. Implementation starts after approval.*
