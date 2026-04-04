# Offline/Online Architecture - Technical Implementation

**Status:** Current Implementation | **Last Updated:** 2026-01-11

> ⚠️ **PLANNED CHANGE:** This doc describes the current **fallback pattern**. We're transitioning to a **DB abstraction layer** pattern. See [OFFLINE_ONLINE_MODE.md](OFFLINE_ONLINE_MODE.md) for the target architecture.

---

## Overview

LocaNext supports **both online (PostgreSQL) and offline (SQLite)** modes through a unified architecture. Every endpoint works with both databases using a **single implementation pattern** - no duplicate code.

### Current Pattern (Fallback)

```
ONE endpoint → Try PostgreSQL → Fall back to SQLite if not found
```

### Target Pattern (DB Abstraction - Planned)

```
ONE endpoint → Get repository for current mode → Use that database
```

See [ARCHITECTURE_SUMMARY.md](ARCHITECTURE_SUMMARY.md#db-abstraction-layer-target-architecture) for the abstraction design.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          FastAPI Endpoint                                │
│                     /api/ldm/files/{file_id}                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. Query PostgreSQL first:                                             │
│     result = await db.execute(select(LDMFile).where(id == file_id))    │
│     file = result.scalar_one_or_none()                                  │
│                                                                         │
│  2. If not found, fall back to SQLite:                                  │
│     if not file:                                                        │
│         offline_db = get_offline_db()                                   │
│         return offline_db.get_local_file(file_id)                       │
│                                                                         │
│  3. If still not found, return 404                                      │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## The Fallback Pattern

### Standard Pattern (All File/Row Endpoints)

```python
@router.get("/files/{file_id}")
async def get_file(
    file_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user_async)
):
    # Step 1: Try PostgreSQL
    result = await db.execute(
        select(LDMFile).where(LDMFile.id == file_id)
    )
    file = result.scalar_one_or_none()

    # Step 2: Fall back to SQLite
    if not file:
        from server.database.offline import get_offline_db
        offline_db = get_offline_db()
        local_file = offline_db.get_local_file(file_id)
        if local_file:
            return local_file  # Return SQLite data
        raise HTTPException(status_code=404, detail="File not found")

    # Step 3: Return PostgreSQL data
    return file
```

### Key Points

1. **Import inside the `if` block** - Only loads offline module when needed
2. **No duplicate logic** - Calls existing `offline.py` methods
3. **Same response format** - Both paths return compatible data structures
4. **Transparent to frontend** - Frontend doesn't know which DB was used

---

## Database Layer

### PostgreSQL (Online)

- **Location:** Central server
- **Models:** `server/database/models.py` (SQLAlchemy ORM)
- **Tables:** `ldm_files`, `ldm_rows`, `ldm_projects`, etc.
- **Use case:** Multi-user, real-time collaboration

### SQLite (Offline)

- **Location:** `~/.local/share/locanext/offline.db`
- **Implementation:** `server/database/offline.py`
- **Tables:** `offline_files`, `offline_rows`, etc.
- **Use case:** Single-user, local work

### offline.py Methods

| Method | Description |
|--------|-------------|
| `get_local_file(file_id)` | Get file metadata from SQLite |
| `get_rows_for_file(file_id)` | Get all rows for a file |
| `get_row(row_id)` | Get single row by ID |
| `update_row(row_id, data)` | Update row in SQLite |
| `delete_local_file(file_id)` | Delete file and rows |
| `rename_local_file(file_id, name)` | Rename a file |
| `search_local_files(query)` | Search files by name |

---

## File Scenarios

### Scenario 1: Local File (Offline Storage) - sync_status='local'

```
User imports file directly to Offline Storage
→ File exists ONLY in SQLite
→ sync_status = 'local'
→ FULL CONTROL: create folders, move files, rename, delete
```

**Permissions for Local Files:**
| Action | Allowed |
|--------|---------|
| Read content | ✅ |
| Edit content (rows) | ✅ |
| Rename file | ✅ |
| Move to folder | ✅ |
| Delete | ✅ |
| Create folders | ✅ |
| Move folders | ✅ |

### Scenario 2: Synced File (Valid Path) - sync_status='synced'

```
User downloaded server file for offline work
→ File exists in BOTH databases
→ sync_status = 'synced' or 'modified'
→ READ-ONLY STRUCTURE: can only edit content
```

**Permissions for Synced Files:**
| Action | Allowed |
|--------|---------|
| Read content | ✅ |
| Edit content (rows) | ✅ |
| Rename file | ❌ (server controls path) |
| Move to folder | ❌ (server controls path) |
| Delete | ❌ (server controls path) |
| Rename parent folders | ❌ |
| Move parent folders | ❌ |

### Scenario 3: Orphaned File (Invalid Path) - sync_status='orphaned'

```
File was synced but server deleted the original path
→ File exists in SQLite only
→ sync_status = 'orphaned'
→ READ-ONLY: can only view, needs re-assignment
```

**Orphaned files need to be:**
1. Re-assigned to a valid server path, OR
2. Moved to Offline Storage (becomes local)

### Scenario 4: Server File (PostgreSQL Only)

```
User is online, opens file from server
→ File exists ONLY in PostgreSQL
→ Full server-side control
```

### Scenario 5: File Not Found

```
User requests non-existent file_id
→ Endpoint queries PostgreSQL
→ File NOT found
→ Fall back to SQLite
→ File NOT found
→ Return 404
```

---

## Permission Matrix

```
┌────────────────────────────────────────────────────────────────────────┐
│                       OFFLINE MODE PERMISSIONS                          │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  OFFLINE STORAGE (sync_status='local')         FULL CONTROL            │
│  ─────────────────────────────────────         ────────────            │
│  📁 Offline Storage                                                     │
│     📁 My Drafts           ← Can create folders                        │
│        📄 new_work.txt     ← Can import/create files                   │
│        📄 imported.xlsx    ← Can edit, delete, move, rename            │
│     📁 Another Folder      ← Can move folders inside folders           │
│                                                                        │
│  SYNCED FROM SERVER (sync_status='synced')     READ STRUCTURE          │
│  ─────────────────────────────────────         ──────────────          │
│  📁 Nintendo (downloaded)  ← Cannot rename/delete/move folder          │
│     📁 Mario Kart          ← Cannot rename/delete/move folder          │
│        📄 menu.txt         ← CAN EDIT CONTENT (rows only)              │
│                            ← Cannot rename/move/delete file            │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Endpoint Categories

### Category 1: Full SQLite Fallback

These endpoints work completely with local files:

| Endpoint | Behavior |
|----------|----------|
| `GET /files/{id}` | Return file metadata from SQLite |
| `GET /files/{id}/rows` | Return all rows from SQLite |
| `PUT /rows/{id}` | Update row in SQLite |
| `DELETE /files/{id}` | Delete file from SQLite |
| `PATCH /files/{id}/rename` | Rename file in SQLite |
| `GET /files/{id}/download` | Download file from SQLite |
| `GET /files/{id}/convert` | Convert file (uses SQLite rows) |
| `GET /files/{id}/extract-glossary` | Extract glossary (uses SQLite rows) |
| `POST /files/{id}/merge` | Merge into file (updates SQLite rows) |
| `POST /files/{id}/register-as-tm` | Create TM from SQLite file |
| `POST /pretranslate` | Pre-translate using SQLite rows |
| `POST /files/{id}/check-grammar` | Grammar check SQLite rows |
| `POST /rows/{id}/check-grammar` | Grammar check single SQLite row |
| `POST /files/{id}/check-qa` | QA check SQLite rows |
| `POST /rows/{id}/check-qa` | QA check single SQLite row |
| `GET /search` | Search includes SQLite local files |
| `POST /files/upload?storage=local` | Upload directly to SQLite |

### Category 2: Read Structure Only (PostgreSQL-Only Operations)

These endpoints don't support local files because they're PostgreSQL concepts:

| Endpoint | Why PostgreSQL-Only |
|----------|---------------------|
| `PATCH /files/{id}/move` | Folders are PostgreSQL concept |
| `PATCH /files/{id}/move-cross-project` | Projects are PostgreSQL concept |
| `POST /files/{id}/copy` | Copying to projects is PostgreSQL |
| `GET /projects/*` | Projects are server-side |
| `GET /folders/*` | Folders are server-side |
| `GET /platforms/*` | Platforms are server-side |

**When called with local file_id, these return helpful 400 error:**

```python
if not file:
    offline_db = get_offline_db()
    if offline_db.get_local_file(file_id):
        raise HTTPException(
            status_code=400,
            detail="Cannot move local files to folders. Upload to server first."
        )
    raise HTTPException(status_code=404, detail="File not found")
```

### Category 3: Ephemeral for Local Files

These endpoints work with local files but don't persist results:

| Endpoint | Local File Behavior |
|----------|---------------------|
| `GET /rows/{id}/qa-results` | Returns empty list (no persistence) |
| `GET /files/{id}/qa-results` | Returns empty list |
| `GET /files/{id}/qa-summary` | Returns zeros |
| `GET /files/{id}/active-tms` | Returns empty list |

**Why:** QA results and TM assignments are PostgreSQL-only features. Local files get QA/grammar checking but results aren't persisted.

---

## Code Organization

### No Duplicate Logic

**Wrong (Parasite Code):**
```python
# sync.py - DUPLICATE endpoint for offline
@router.delete("/offline/storage/files/{file_id}")
async def delete_offline_file(file_id: int):
    # 50 lines of code duplicating delete logic
    ...

# files.py - Original endpoint
@router.delete("/files/{file_id}")
async def delete_file(file_id: int):
    # 50 lines of code for delete logic
    ...
```

**Correct (Unified with Fallback):**
```python
# files.py - ONE endpoint that handles both
@router.delete("/files/{file_id}")
async def delete_file(file_id: int, db, current_user):
    result = await db.execute(select(LDMFile).where(LDMFile.id == file_id))
    file = result.scalar_one_or_none()

    if not file:
        # Fallback to SQLite - calls existing method
        return await _delete_local_file(file_id)

    # PostgreSQL delete logic
    ...

async def _delete_local_file(file_id: int):
    """Helper that calls offline.py method - no duplicate logic."""
    from server.database.offline import get_offline_db
    offline_db = get_offline_db()
    file_info = offline_db.get_local_file(file_id)
    if not file_info:
        raise HTTPException(status_code=404, detail="File not found")

    offline_db.delete_local_file(file_id)
    return {"success": True, "deleted": file_info["name"]}
```

### Helper Function Pattern

For complex operations, create small helper functions that wrap `offline.py` calls:

```python
# In files.py - helpers at the bottom of the file

async def _get_local_file_metadata(file_id: int) -> dict:
    """Get file metadata from SQLite."""
    from server.database.offline import get_offline_db
    offline_db = get_offline_db()
    file_info = offline_db.get_local_file(file_id)
    if not file_info:
        raise HTTPException(status_code=404, detail="File not found")
    return {
        "id": file_info["id"],
        "name": file_info["name"],
        "format": file_info.get("format", "txt"),
        "row_count": file_info.get("row_count", 0),
        # ... map to response format
    }
```

---

## RowLike Wrapper Pattern

When SQLite returns dicts but code expects ORM-style objects:

```python
# SQLite returns: {"id": 1, "target": "text", "row_num": 5}
# Code expects:   row.id, row.target, row.row_num

class RowLike:
    """Wrapper to make SQLite dict compatible with ORM-style access."""
    def __init__(self, data: dict):
        self.id = data.get("id")
        self.row_num = data.get("row_num", 0)
        self.source = data.get("source", "")
        self.target = data.get("target", "")
        self.string_id = data.get("string_id")
        self.status = data.get("status", "pending")
        self.extra_data = data.get("extra_data")

# Usage in endpoint:
if not rows:
    offline_db = get_offline_db()
    rows_data = offline_db.get_rows_for_file(file_id)
    rows = [RowLike(r) for r in rows_data]

# Now same code works for both:
for row in rows:
    process(row.target)  # Works for both ORM and RowLike
```

---

## sync_status Values

### For Files (offline_files table)

| Value | Meaning | When Set |
|-------|---------|----------|
| `'local'` | Created in Offline Storage, never synced | On import to Offline Storage |
| `'synced'` | Downloaded from server, unchanged | After download/sync |
| `'modified'` | Has local changes pending push | After editing synced file |
| `'orphaned'` | Server deleted this file's path | On sync when server path gone |

### For Rows (offline_rows table)

| Value | Meaning |
|-------|---------|
| `'synced'` | Matches server version |
| `'modified'` | Local edits pending push |
| `'new'` | Created locally, not on server yet |

---

## Adding Fallback to a New Endpoint

### Step 1: Identify the Pattern

Is this endpoint for files/rows? Does it make sense offline?

### Step 2: Add the Fallback

```python
@router.get("/files/{file_id}/something")
async def do_something(file_id: int, db, current_user):
    # 1. Try PostgreSQL
    result = await db.execute(select(LDMFile).where(LDMFile.id == file_id))
    file = result.scalar_one_or_none()

    # 2. Fallback to SQLite
    if not file:
        from server.database.offline import get_offline_db
        offline_db = get_offline_db()
        local_file = offline_db.get_local_file(file_id)
        if not local_file:
            raise HTTPException(status_code=404, detail="File not found")
        # Process local file...
        return process_local(local_file)

    # 3. PostgreSQL path
    return process(file)
```

### Step 3: For Complex Operations, Add Helper

```python
async def _do_something_local(file_id: int):
    """Handle local file case."""
    from server.database.offline import get_offline_db
    offline_db = get_offline_db()
    # ... implementation
```

---

## Testing Offline Mode

### Unit Test Pattern

```python
def test_get_file_from_sqlite():
    """File should be returned from SQLite when not in PostgreSQL."""
    # Create file in SQLite only
    offline_db = get_offline_db()
    file_id = offline_db.create_local_file(name="test.txt", ...)

    # Call endpoint
    response = client.get(f"/api/ldm/files/{file_id}")

    # Should find it via SQLite fallback
    assert response.status_code == 200
    assert response.json()["name"] == "test.txt"
```

### Integration Test Pattern

```python
def test_full_offline_workflow():
    """Complete offline workflow: import → edit → export."""
    # 1. Upload to local storage
    response = client.post(
        "/api/ldm/files/upload?storage=local",
        files={"file": ("test.txt", content)}
    )
    file_id = response.json()["id"]

    # 2. Get rows
    response = client.get(f"/api/ldm/files/{file_id}/rows")
    assert response.status_code == 200

    # 3. Edit row
    row_id = response.json()["rows"][0]["id"]
    response = client.put(
        f"/api/ldm/rows/{row_id}",
        json={"target": "new translation"}
    )
    assert response.status_code == 200

    # 4. Download
    response = client.get(f"/api/ldm/files/{file_id}/download")
    assert response.status_code == 200
```

---

## Files Modified for Offline Support

| File | Changes |
|------|---------|
| `server/tools/ldm/routes/files.py` | 10+ endpoints with fallback |
| `server/tools/ldm/routes/rows.py` | GET rows, PUT row with fallback |
| `server/tools/ldm/routes/qa.py` | QA check endpoints with fallback |
| `server/tools/ldm/routes/grammar.py` | Grammar check endpoints with fallback |
| `server/tools/ldm/routes/pretranslate.py` | Pretranslate with file check |
| `server/tools/ldm/routes/tm_assignment.py` | Active TMs returns empty for local |
| `server/tools/ldm/routes/search.py` | Searches SQLite local files |
| `server/database/offline.py` | SQLite operations |

---

## Summary

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    UNIFIED OFFLINE/ONLINE PATTERN                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  STEP 1: Query PostgreSQL                                               │
│  ───────────────────────                                                │
│  result = await db.execute(select(Model).where(id == entity_id))       │
│  entity = result.scalar_one_or_none()                                   │
│                                                                         │
│  STEP 2: Fallback to SQLite                                             │
│  ─────────────────────────                                              │
│  if not entity:                                                         │
│      offline_db = get_offline_db()                                      │
│      local_entity = offline_db.get_method(entity_id)                    │
│      if local_entity:                                                   │
│          return process(local_entity)                                   │
│      raise HTTPException(404)                                           │
│                                                                         │
│  STEP 3: Process PostgreSQL Result                                      │
│  ────────────────────────────────                                       │
│  return process(entity)                                                 │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  BENEFITS:                                                              │
│  • ONE endpoint for both databases                                      │
│  • NO duplicate code                                                    │
│  • Transparent to frontend                                              │
│  • Easy to maintain                                                     │
│  • Consistent behavior                                                  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## TM Offline Support (CURRENT LIMITATION)

### Current State

**TMs are PostgreSQL-only.** This means:

| TM Operation | Online | Offline with DB | True Offline |
|--------------|--------|-----------------|--------------|
| Register file as TM | ✅ | ✅ | ❌ Fails |
| Search TM | ✅ | ✅ | ❌ Fails |
| Add TM entry | ✅ | ✅ | ❌ Fails |
| TM pre-translation | ✅ | ✅ | ❌ Fails |

**"Offline with DB"** = SQLite for files but PostgreSQL still available for TMs
**"True Offline"** = No PostgreSQL connection at all

### Why It Works "Offline"

When a user imports a file to Offline Storage and registers it as TM:
1. File data comes from SQLite
2. TM is created in PostgreSQL (if available)
3. This works because "offline mode" still connects to PostgreSQL when available

### Future: SQLite TM Storage

For true offline TM support, we need:

```sql
-- offline_tms table
CREATE TABLE offline_tms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    server_id INTEGER,        -- ID in PostgreSQL (NULL for local-only)
    name TEXT NOT NULL,
    source_lang TEXT,
    target_lang TEXT,
    entry_count INTEGER DEFAULT 0,
    sync_status TEXT DEFAULT 'local',  -- 'local', 'synced', 'modified'
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- offline_tm_entries table
CREATE TABLE offline_tm_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tm_id INTEGER REFERENCES offline_tms(id),
    server_id INTEGER,        -- ID in PostgreSQL
    source TEXT NOT NULL,
    target TEXT NOT NULL,
    sync_status TEXT DEFAULT 'local',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**Implementation Steps:**
1. Create SQLite TM tables
2. Add fallback to TM CRUD endpoints
3. Add fallback to TM search
4. Create TM sync flow

---

## Scenarios Summary

### Scenario 1: Local File Operations (FULL SUPPORT)

User imports file to Offline Storage → works 100% offline:
- ✅ View file, edit rows
- ✅ QA check, grammar check
- ✅ Convert, download, merge
- ✅ Create folders, move within Offline Storage
- ❌ Register as TM (requires PostgreSQL)

### Scenario 2: Synced File Operations (READ CONTENT)

User downloads server file for offline work:
- ✅ Edit content (rows)
- ✅ QA check, grammar check
- ❌ Move/rename file (server controls path)
- ❌ Delete file (server controls)

### Scenario 3: True Offline (NO POSTGRESQL)

App started without any network:
- ✅ All local file operations work
- ❌ TM operations fail (PostgreSQL-only)
- ❌ Cannot access server files
- ❌ Cannot sync

---

## Architecture: Identical Backend, Different Rules

The backend code is **IDENTICAL** for online and offline. The difference is in the **data source**:

```
                 ┌──────────────────────────────┐
                 │    SAME ENDPOINT LOGIC       │
                 │  (files.py, rows.py, etc.)   │
                 └───────────────┬──────────────┘
                                 │
                 ┌───────────────┼───────────────┐
                 │               │               │
         ┌───────▼───────┐ ┌────▼────┐ ┌───────▼───────┐
         │  PostgreSQL   │ │ Fallback │ │    SQLite     │
         │   (Primary)   │ │   Logic  │ │   (Backup)    │
         └───────────────┘ └──────────┘ └───────────────┘
```

**The Rule:** Try PostgreSQL first → Fall back to SQLite if not found

**Benefits:**
- No duplicate code
- Same validation, same response format
- Frontend doesn't know which DB was used
- Easy to maintain

---

*Technical implementation document. For user-facing specification, see [OFFLINE_ONLINE_MODE.md](OFFLINE_ONLINE_MODE.md).*
