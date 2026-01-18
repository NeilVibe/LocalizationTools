# Offline/Online Mode Architecture

**Status:** ✅ COMPLETE (P9) | **Updated:** 2026-01-18

---

## Overview

**Full offline parity** with automatic connection and manual sync.

| Feature | Status |
|---------|--------|
| Full Offline Mode | ✅ Everything works offline |
| DB Abstraction | ✅ Same API, different DB underneath |
| Auto-connect | ✅ Online if server reachable, auto-fallback |
| Manual sync | ✅ Right-click → Download/Sync |
| TM Operations | ✅ Cut/Copy/Paste work in SQLite |
| Recycle Bin | ✅ 30-day soft delete |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Repository Interface                      │
│              tm.get(), file.get(), row.update()              │
└──────────────────────────┬──────────────────────────────────┘
                           │
                 ┌─────────┴─────────┐
                 │                   │
          ┌──────▼──────┐     ┌──────▼──────┐
          │ PostgreSQL  │     │   SQLite    │
          │  (Online)   │     │  (Offline)  │
          └─────────────┘     └─────────────┘
```

### Mode Detection

```python
# Token present = Online mode, No token = Offline mode
mode = "online" if request.headers.get("Authorization") else "offline"
repo = get_repository(mode)  # Returns PostgreSQL or SQLite adapter
```

---

## Auto-Sync on File Open

When working ONLINE and opening a file, the full path hierarchy syncs to offline:

```
User opens file online
        │
        ▼
┌─────────────────────────────────────────┐
│  autoSyncFileOnOpen(fileId)             │
│                                         │
│  Syncs: Platform → Project → Folder →   │
│         File → Rows                     │
│                                         │
│  Result: File available offline         │
└─────────────────────────────────────────┘
```

---

## Sync Rules

| Direction | What Syncs | Notes |
|-----------|------------|-------|
| Online → Offline | Files, Rows, TMs | Full content sync |
| Offline → Online | Edited rows only | Additions and edits |
| **Never synced** | Deletions | Use Recycle Bin instead |

### Conflict Resolution: Last-Write-Wins

```
Online row: "Hello" (updated 10:00)
Offline row: "Bonjour" (updated 10:05)
                │
                ▼
Result: "Bonjour" wins (later timestamp)
```

---

## Virtual "Offline Storage" Project

When local files exist, projects list includes:

```json
{
    "id": -1,
    "name": "Offline Storage",
    "platform_id": -1
}
```

SQLite uses `project_id = -1` for offline-only files.

---

## Endpoints with Offline Support

| Endpoint | Offline | Notes |
|----------|---------|-------|
| `GET /files/{id}` | ✅ | Returns local file |
| `GET /files/{id}/rows` | ✅ | Returns local rows |
| `PUT /rows/{id}` | ✅ | Saves to SQLite |
| `GET /files/{id}/convert` | ✅ | Converts local |
| `POST /files/{id}/check-qa` | ✅ | QA on local |
| `POST /pretranslate` | ✅ | Pretranslates local |
| `GET /search` | ✅ | Searches SQLite |
| `GET /projects` | ✅ | Includes Offline Storage |
| `GET /tm` | ✅ | Includes SQLite TMs |

---

## Key Files

| Component | File |
|-----------|------|
| Sync Store | `locaNext/src/lib/stores/sync.js` |
| Sync Service | `server/services/sync_service.py` |
| Offline DB | `server/database/offline_db.py` |
| Launcher | `locaNext/src/lib/components/Launcher.svelte` |

---

## User Flow

```
┌─────────────────┐     ┌─────────────────┐
│   App Starts    │────▶│  Check Server   │
└─────────────────┘     └────────┬────────┘
                                 │
                    ┌────────────┴────────────┐
                    │                         │
             ┌──────▼──────┐          ┌───────▼───────┐
             │   ONLINE    │          │    OFFLINE    │
             │ PostgreSQL  │          │    SQLite     │
             │ Full access │          │  Local files  │
             └─────────────┘          └───────────────┘
```

---

*Architecture doc | P9 Complete | See ARCHITECTURE_SUMMARY.md for full system overview*
