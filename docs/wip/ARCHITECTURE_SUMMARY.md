# Architecture Summary - Complete Reference

> Last Updated: 2026-01-08 (Session 35)

---

## Quick Reference Tables

### Online vs Offline Mode

| Aspect | **ONLINE Mode** | **OFFLINE Mode** |
|--------|-----------------|------------------|
| **Database** | PostgreSQL (central server) | SQLite (local file) |
| **Connection** | Server required | No server needed |
| **Login** | User credentials | "OFFLINE_MODE_xxx" token |
| **Data source** | Central DB | Local DB |
| **File storage** | Server filesystem | Local filesystem |
| **TM search** | PostgreSQL + FAISS | SQLite + FAISS |
| **Real-time sync** | WebSocket | N/A |
| **Multi-user** | Yes | Single user |
| **Grammar check** | Yes (LanguageTool) | No |

### Feature Availability

| Feature | Online | Offline | Notes |
|---------|:------:|:-------:|-------|
| View files | ✅ | ✅ | Online: all, Offline: downloaded |
| Edit cells | ✅ | ✅ | |
| Save changes | ✅ | ✅ | Saves to respective DB |
| TM search | ✅ | ✅ | FAISS is local |
| TM add entry | ✅ | ✅ | |
| Pretranslation | ✅ | ✅ | Qwen model local |
| QA checks | ✅ | ✅ | Pattern-based, local |
| File upload | ✅ | ✅ | |
| File conversion | ✅ | ✅ | |
| Create glossary | ✅ | ✅ | |
| Grammar/Spelling | ✅ | ❌ | Needs LanguageTool server |
| Real-time collab | ✅ | ❌ | Needs WebSocket |
| User management | ✅ | ❌ | Admin features |

---

## Offline Storage Explained

### What is Offline Storage?

**Offline Storage is a PLATFORM** that represents locally-created files that don't exist on the server yet.

| Location | ID | Purpose |
|----------|-----|---------|
| **PostgreSQL** | Auto (e.g., 31) | TM assignment target (FK constraint) |
| **SQLite** | -1 | File storage (virtual project_id) |

### Why Two Records?

1. **SQLite** uses `project_id = -1` for local files (no server equivalent)
2. **PostgreSQL** needs a real record for TM assignments (foreign key constraint)
3. These are NOT duplicates - they serve different purposes

### Hierarchy

```
TM Tree Structure:
├── Unassigned (TMs with no assignment - cannot be activated)
├── Offline Storage (Platform ID=31 in PostgreSQL)
│   └── Offline Storage (Project - for TM assignment)
├── TestPlatform
│   ├── TestProject
│   └── ...
└── ...
```

---

## TM Assignment Rules

### Assignment Levels

| Level | Description | Example |
|-------|-------------|---------|
| **Unassigned** | No assignment, cannot be activated | Imported TM not yet assigned |
| **Platform** | Applies to ALL projects under it | Company-wide TM |
| **Project** | Applies to that project only | Project-specific TM |
| **Folder** | Applies to that folder only | Folder-specific TM |

### Key Rules

1. **Unassigned TMs CANNOT be activated** - Must assign first
2. **Platform assignment = "Global"** for that platform's projects
3. **One scope per TM** - Cannot assign to multiple places
4. **Moving to Unassigned** = Removing assignment (right-click → Move to Unassigned)

### TM Activation Cascade

When editing a file, active TMs are resolved in order:
1. Folder-level TMs (walking up folder tree)
2. Project-level TMs
3. Platform-level TMs

---

## File Types

### sync_status Values

| Status | Meaning | Permissions |
|--------|---------|-------------|
| `'local'` | Created in Offline Storage | FULL CONTROL (rename, move, delete) |
| `'synced'` | Downloaded from server | Edit content only |
| `'modified'` | Local changes pending | Edit content only |
| `'orphaned'` | Server path deleted | Read only |

### Item Types (Frontend)

| Type | Description | Where |
|------|-------------|-------|
| `'file'` | Server file | PostgreSQL |
| `'folder'` | Server folder | PostgreSQL |
| `'project'` | Server project | PostgreSQL |
| `'platform'` | Server platform | PostgreSQL |
| `'local-file'` | Offline Storage file | SQLite |
| `'local-folder'` | Offline Storage folder | SQLite |
| `'offline-storage'` | Offline Storage root | Virtual |

---

## Database IDs

### SQLite (Offline)

| Table | ID Range | Notes |
|-------|----------|-------|
| `offline_files` | Auto-increment | Local files |
| `offline_folders` | Auto or negative | Local folders use negative IDs |
| Project ID | -1 | Virtual ID for Offline Storage |

### PostgreSQL (Online)

| Entity | ID | Notes |
|--------|-----|-------|
| Platforms | Auto-increment | Normal platforms |
| Offline Storage Platform | Auto (e.g., 31) | Created on demand |
| Offline Storage Project | Auto (e.g., 31) | Under Offline Storage platform |

---

## Code Architecture

### No Duplicates

The codebase follows **unified endpoints with fallback**:

```python
# Pattern used everywhere:
result = await db.execute(select(...))  # Try PostgreSQL first
if not result:
    offline_db.get_local_xxx()  # Fallback to SQLite
```

This is NOT duplicate code - it's a fallback pattern.

### Key Files

| File | Purpose |
|------|---------|
| `server/database/offline.py` | SQLite operations |
| `server/database/offline_schema.sql` | SQLite schema |
| `server/tools/ldm/routes/sync.py` | Offline endpoints |
| `server/tools/ldm/routes/tm_assignment.py` | TM tree + assignment |
| `locaNext/src/lib/stores/sync.js` | Sync state management |
| `locaNext/src/lib/components/pages/FilesPage.svelte` | File explorer |
| `locaNext/src/lib/components/ldm/TMExplorerTree.svelte` | TM tree UI |

---

## Optimistic UI Pattern

### What is Optimistic UI?

UI updates **INSTANTLY** on user action. Server syncs in background. If server fails, revert.

### Where It's Used

| Action | Optimistic? | Notes |
|--------|:-----------:|-------|
| File move | ✅ | Items removed from view immediately |
| TM selection | ✅ | Visual feedback instant |
| TM delete | ✅ | Modal shows, UI updates on confirm |
| Cell edit | ✅ | Value changes instantly |
| File upload | ❌ | Needs server response |

---

## Common Confusions

### Q: Why Unassigned AND Offline Storage?

**A:** They serve different purposes:
- **Unassigned** = TMs not assigned to ANY location (global pool)
- **Offline Storage** = A platform for LOCAL files (not on server)

Think of it like:
- Unassigned = "TMs in your inventory, not deployed"
- Offline Storage = "Your local workspace"

### Q: Can I assign TM to Unassigned?

**A:** "Unassigned" is not a location. Moving a TM to Unassigned = removing its assignment.
- Right-click TM → "Move to Unassigned" removes the assignment
- Unassigned TMs CANNOT be activated (must assign first)

### Q: Is offline code a module of online code?

**A:** Yes. The offline code is a **fallback layer**, not separate code:
- Same endpoints handle both online/offline
- Fallback pattern: PostgreSQL → SQLite
- No duplicate logic

### Q: Why do I see TWO "Offline Storage" entries? ⚠️ KNOWN ISSUE (UI-107)

**A:** This is a known UX issue. In Online Mode you see duplicates because two systems exist:

| System | Purpose | DB ID | Operations |
|--------|---------|-------|------------|
| **CloudOffline** | File storage | String `'offline-storage'` | SQLite: create/move/delete files |
| **Offline Storage Platform** | TM assignment | Integer `31` (PostgreSQL) | FK for TM assignments |

**Why Two Systems?**
```
File Operations:              TM Assignments:
SQLite + parent_id chain  vs  PostgreSQL + FK constraint
No DB ID needed               Needs real DB ID
```

CloudOffline uses SQLite endpoints (`/api/ldm/offline/storage/*`) that don't need PostgreSQL IDs.
TM assignments need foreign keys to platform_id/project_id, so PostgreSQL record is required.

**Planned Fix (UI-107):**
1. Hide PostgreSQL platform from File Explorer (only CloudOffline visible)
2. Rename TM tree: "Local Workspace" (not "Offline Storage")
3. Use CloudOffline icon in TM tree

See: `docs/wip/ISSUES_TO_FIX.md` → UI-107

### Q: Does CloudOffline have "DB ID power"?

**A:** Yes! CloudOffline doesn't need a numeric PostgreSQL ID because it uses a **different paradigm**:

| Operation | CloudOffline | Regular Platform |
|-----------|--------------|------------------|
| Create folder | SQLite `parent_id` | PostgreSQL `project_id` FK |
| Move file | SQLite update `parent_id` | PostgreSQL FK update |
| Upload file | SQLite insert | PostgreSQL insert |
| TM assignment | ❌ Not supported | ✅ PostgreSQL FK |

CloudOffline inherits its "power" from SQLite's simpler data model - no foreign key constraints needed.
TM assignments require the PostgreSQL platform because `LDMTMAssignment.platform_id` is a FK.

---

## Testing Quick Reference

```bash
# DEV servers
./scripts/start_all_servers.sh --with-vite

# Run TM tests
cd locaNext && npx playwright test tests/tm-*.spec.ts

# Run offline tests
cd locaNext && npx playwright test tests/offline-*.spec.ts
```

---

*Session 34 | Complete Architecture Reference*
