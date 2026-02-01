# Offline/Online Mode Architecture

**Status:** ✅ COMPLETE (P10) | **Updated:** 2026-02-01

---

## Overview

**Full offline parity** with automatic connection and manual sync.

| Feature | Status |
|---------|--------|
| Full Offline Mode | ✅ Everything works offline |
| DB Abstraction | ✅ Repository pattern with factory injection |
| Auto-connect | ✅ Online if server reachable, auto-fallback |
| Manual sync | ✅ Right-click → Download/Sync |
| TM Operations | ✅ Cut/Copy/Paste work in SQLite |
| Recycle Bin | ✅ 30-day soft delete |
| Negative ID Routing | ✅ Transparent routing for local entities |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Repository Interfaces                       │
│   TMRepository, FileRepository, RowRepository, etc.          │
└──────────────────────────┬──────────────────────────────────┘
                           │
              ┌────────────┴────────────┐
              │   Factory Functions     │
              │  get_tm_repository()    │
              │  get_file_repository()  │
              │  get_row_repository()   │
              │  ... (10 total)         │
              └────────────┬────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
  ┌──────▼──────┐   ┌──────▼──────┐   ┌──────▼──────┐
  │ PostgreSQL  │   │   SQLite    │   │   SQLite    │
  │  (Online)   │   │  (SERVER)   │   │  (OFFLINE)  │
  │ ldm_* tables│   │ ldm_* tables│   │offline_* tbl│
  └─────────────┘   └─────────────┘   └─────────────┘
```

### 3-Mode Architecture (ARCH-001)

The system supports three modes with automatic fallback:

| Mode | Database | Schema | When Used |
|------|----------|--------|-----------|
| **Online** | PostgreSQL | `ldm_*` tables | Server reachable, normal token |
| **SQLite Server** | SQLite | `ldm_*` tables | Server running but PostgreSQL unavailable |
| **Offline** | SQLite | `offline_*` tables | `OFFLINE_MODE_` header, desktop-only |

### Mode Detection

```python
# server/repositories/factory.py

def _is_offline_mode(request: Request) -> bool:
    """Detect offline mode via Authorization header."""
    auth_header = request.headers.get("Authorization", "")
    return auth_header.startswith("Bearer OFFLINE_MODE_")

def _is_sqlite_fallback() -> bool:
    """Detect SQLite fallback mode."""
    from server import config
    return config.ACTIVE_DATABASE_TYPE == "sqlite"

# Factory function example
def get_tm_repository(request, db, current_user) -> TMRepository:
    if _is_offline_mode(request):
        return SQLiteTMRepository(schema_mode=SchemaMode.OFFLINE)
    elif _is_sqlite_fallback():
        return SQLiteTMRepository(schema_mode=SchemaMode.SERVER)
    else:
        return PostgreSQLTMRepository(db, current_user)
```

### SchemaMode Enum

```python
# server/repositories/sqlite/base.py

class SchemaMode(Enum):
    OFFLINE = "offline"  # Uses offline_* tables (Electron local storage)
    SERVER = "server"    # Uses ldm_* tables (server SQLite fallback)
```

### Table Name Mapping

| Base Name | OFFLINE Schema | SERVER Schema |
|-----------|----------------|---------------|
| platforms | `offline_platforms` | `ldm_platforms` |
| projects | `offline_projects` | `ldm_projects` |
| folders | `offline_folders` | `ldm_folders` |
| files | `offline_files` | `ldm_files` |
| rows | `offline_rows` | `ldm_rows` |
| tms | `offline_tms` | `ldm_translation_memories` |
| tm_entries | `offline_tm_entries` | `ldm_tm_entries` |
| qa_results | `offline_qa_results` | `ldm_qa_results` |
| trash | `offline_trash` | `ldm_trash` |

---

## Negative ID Routing

Entities created offline use **negative IDs** to avoid collisions with server IDs.

### RoutingRowRepository

For row operations, a `RoutingRowRepository` transparently routes based on ID sign:

```python
# server/repositories/routing/row_repo.py

class RoutingRowRepository(RowRepository):
    """Routes row operations based on entity IDs."""

    def __init__(self, primary_repo: RowRepository):
        self._primary = primary_repo  # PostgreSQL or SQLite SERVER
        self._offline = SQLiteRowRepository(schema_mode=SchemaMode.OFFLINE)

    def _get_repo_for_id(self, entity_id: int) -> RowRepository:
        if entity_id < 0:
            return self._offline  # Local Electron data
        return self._primary      # Server data
```

**Routes never need to know about negative ID handling** - the factory injects the RoutingRowRepository which handles it transparently.

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

All offline-only entities use negative IDs (e.g., `-1`, `-2`, etc.) to avoid ID collisions with server data.

---

## Repository Interfaces

All 10 repository interfaces with factory functions:

| Interface | Factory Function | Purpose |
|-----------|------------------|---------|
| `TMRepository` | `get_tm_repository()` | Translation memories |
| `FileRepository` | `get_file_repository()` | Files |
| `RowRepository` | `get_row_repository()` | Row data (with routing) |
| `ProjectRepository` | `get_project_repository()` | Projects |
| `FolderRepository` | `get_folder_repository()` | Folders |
| `PlatformRepository` | `get_platform_repository()` | Platforms |
| `QAResultRepository` | `get_qa_repository()` | QA results |
| `TrashRepository` | `get_trash_repository()` | Soft-deleted items |
| `CapabilityRepository` | `get_capability_repository()` | User capabilities |
| (Sync) | `get_sync_repositories()` | Returns BOTH repos for sync |

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

## TMLoader - Unified TM Entry Loading

The `TMLoader` (in `server/tools/shared/tm_loader.py`) provides unified TM entry loading for pretranslation:

```python
from server.tools.shared.tm_loader import TMLoader

# Async (recommended for routes)
entries = await TMLoader.load_entries_async(tm_id)

# Sync (for EmbeddingsManager - MUST be called from sync context only)
entries = TMLoader.load_entries(tm_id)
```

**Source Detection:**
- Negative TM ID (`tm_id < 0`) → SQLite OFFLINE mode
- `ACTIVE_DATABASE_TYPE == "sqlite"` → SQLite SERVER mode
- Default → PostgreSQL

---

## Key Files

| Component | File |
|-----------|------|
| Repository Factory | `server/repositories/factory.py` |
| SchemaMode Enum | `server/repositories/sqlite/base.py` |
| TMLoader | `server/tools/shared/tm_loader.py` |
| Routing Row Repo | `server/repositories/routing/row_repo.py` |
| Sync Store | `locaNext/src/lib/stores/sync.js` |
| Sync Service | `server/services/sync_service.py` |
| Offline DB | `server/database/offline.py` |
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

## OFFLINE-Only Columns

The OFFLINE schema has additional columns for sync tracking:

| Column | Purpose |
|--------|---------|
| `server_id` | ID on server (for sync) |
| `sync_status` | pending/synced/conflict |
| `downloaded_at` | When downloaded |
| `server_platform_id` | Server's platform ID |
| `server_project_id` | Server's project ID |
| `server_file_id` | Server's file ID |
| `server_folder_id` | Server's folder ID |
| `server_tm_id` | Server's TM ID |
| `server_parent_id` | Server's parent ID |

These columns exist only in OFFLINE mode and are checked via `_has_column()` to conditionally include them in queries.

---

*Architecture doc | P10 Complete | See ARCHITECTURE_SUMMARY.md for full system overview*
