# TM Hierarchy & Assignment System

> **Status:** Partially Implemented | **Updated:** 2026-01-11
> **Created:** 2026-01-01
> **Priority:** HIGH - Core feature for production workflow

---

## Implementation Status

| Component | Status | Notes |
|-----------|--------|-------|
| Platform table | ✅ Done | `ldm_platforms` + `offline_platforms` |
| TM assignment table | ✅ Done | `ldm_tm_assignments` + `offline_tm_assignments` |
| TM Explorer Tree | ✅ Done | TMExplorerTree.svelte |
| Cut/Copy/Paste | ✅ Done | Keyboard + context menu |
| Offline Storage support | ✅ Done | PostgreSQL platform for TM FK |
| SQLite TM assignment | ✅ Done | Table exists, TMRepository works |
| DB abstraction layer | ✅ Done | TMRepository (PostgreSQL + SQLite) |
| **TM tree folder mirroring** | 🔲 Pending | `get_tree()` doesn't query folders yet |

### Known Gap: TM Tree Folder Mirroring

Both `PostgreSQLTMRepository.get_tree()` and `SQLiteTMRepository.get_tree()` have:
```python
"folders": []  # TODO: Add folder support
```

**TM assignment to folders WORKS** - data stored correctly in both DBs.
**TM Explorer UI doesn't SHOW folders** - need to add folder queries to `get_tree()`.

---

## Problem Statement

1. **No visibility** - When opening a file, user doesn't know which TM is active
2. **Flat TM structure** - TMs are not organized, no relationship to projects/folders
3. **Manual assignment** - Must manually select TM each time, no automatic scoping
4. **No project grouping** - Projects need higher-level organization (platforms)

---

## Solution Overview

### New Hierarchy Structure

```
Platform (NEW)
└── Project (existing)
    └── Folder (existing)
        └── Files (existing)
```

**TM Explorer mirrors this structure but shows TMs instead of files.**

### CRITICAL: TM Explorer is a READ-ONLY Mirror

```
┌─────────────────────────────────────────────────────────────────────┐
│  TM Explorer AUTOMATICALLY inherits structure from File Explorer   │
│  - Create Platform in File Explorer → appears in TM Explorer       │
│  - Create Project in File Explorer → appears in TM Explorer        │
│  - Create Folder in File Explorer → appears in TM Explorer         │
│  - Rename/Delete in File Explorer → auto-updated in TM Explorer    │
│                                                                     │
│  You NEVER manually create folders/projects/platforms in TM Explorer│
│  The structure is READ-ONLY - controlled entirely by File Explorer │
└─────────────────────────────────────────────────────────────────────┘
```

### "Unassigned" Folder (TM Explorer ONLY)

```
File Explorer:          TM Explorer:
├── Platform: PC        ├── [Unassigned] ← EXISTS ONLY HERE
│   └── Project: ...    │   └── orphan.tm
└── (no Unassigned)     ├── Platform: PC
                        │   └── ...
```

**Why Unassigned exists only in TM Explorer:**
- TMs need a home when first created (before placement)
- TMs need protection when their folder is deleted
- Files don't have this problem - files physically exist in folders

### TM Activation Scope

```
Platform: PC
├── TM: "PC_Global.tm" [ACTIVE] ← applies to ALL projects under PC
└── Project: Game1
    ├── TM: "Game1_Terms.tm" [ACTIVE] ← applies to all folders in Game1
    └── Folder: French
        ├── TM: "French_Specific.tm" [ACTIVE] ← applies only to French folder
        └── Files use: French_Specific + Game1_Terms + PC_Global (cascade)
```

### Key Concepts

| Concept | Description |
|---------|-------------|
| **Inheritance** | Child folders inherit parent TMs (cascade down) |
| **Override** | Closer scope TM takes priority for conflicts |
| **Multi-TM** | Multiple TMs can be active at different levels |
| **Unassigned** | Safety folder for orphaned TMs |

---

## Phase 1: Database Schema Changes

### New Tables

```sql
-- Platform table (above Project)
CREATE TABLE ldm_platforms (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    owner_id INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Update projects to reference platform
ALTER TABLE ldm_projects ADD COLUMN platform_id INTEGER REFERENCES ldm_platforms(id);

-- TM location/assignment table
CREATE TABLE ldm_tm_assignments (
    id SERIAL PRIMARY KEY,
    tm_id INTEGER REFERENCES ldm_translation_memories(id) ON DELETE CASCADE,
    -- Scope: only ONE of these should be set (NULL = unassigned)
    platform_id INTEGER REFERENCES ldm_platforms(id) ON DELETE SET NULL,
    project_id INTEGER REFERENCES ldm_projects(id) ON DELETE SET NULL,
    folder_id INTEGER REFERENCES ldm_folders(id) ON DELETE SET NULL,
    -- Activation status
    is_active BOOLEAN DEFAULT FALSE,
    -- Metadata
    assigned_at TIMESTAMP DEFAULT NOW(),
    assigned_by INTEGER REFERENCES users(id)
);

-- Index for fast lookups
CREATE INDEX idx_tm_assignments_scope ON ldm_tm_assignments(platform_id, project_id, folder_id);
```

### Migration Strategy

1. Create `ldm_platforms` table
2. Create default "Unassigned" platform (id=0, special)
3. Add `platform_id` to projects (nullable initially)
4. Create `ldm_tm_assignments` table
5. Migrate existing TMs to "Unassigned"

---

## Phase 2: Backend API

### New Endpoints

```
# Platforms
GET    /api/ldm/platforms              - List all platforms
POST   /api/ldm/platforms              - Create platform
PATCH  /api/ldm/platforms/{id}         - Update platform
DELETE /api/ldm/platforms/{id}         - Delete platform (projects move to Unassigned)

# TM Assignments
GET    /api/ldm/tm/{id}/assignment     - Get TM's current assignment
PATCH  /api/ldm/tm/{id}/assign         - Assign TM to platform/project/folder
PATCH  /api/ldm/tm/{id}/activate       - Activate/deactivate TM
GET    /api/ldm/tm/active?scope=...    - Get active TMs for a scope

# Scope Resolution
GET    /api/ldm/files/{id}/active-tms  - Get all active TMs for a file (resolved cascade)
```

### TM Resolution Logic

```python
def get_active_tms_for_file(file_id: int) -> List[TM]:
    """
    Returns TMs in priority order (most specific first):
    1. Folder-level TMs (if file is in a folder)
    2. Project-level TMs
    3. Platform-level TMs
    """
    file = get_file(file_id)
    active_tms = []

    # 1. Check folder chain (walk up to root)
    folder = file.folder
    while folder:
        tms = get_active_tms_for_folder(folder.id)
        active_tms.extend(tms)
        folder = folder.parent

    # 2. Check project
    tms = get_active_tms_for_project(file.project_id)
    active_tms.extend(tms)

    # 3. Check platform
    if file.project.platform_id:
        tms = get_active_tms_for_platform(file.project.platform_id)
        active_tms.extend(tms)

    return active_tms
```

---

## Phase 3: Frontend - TM Explorer Redesign

### Structure

```
TM Explorer (mirrors File Explorer)
├── [Unassigned] ← Special folder, always visible
│   └── orphaned_tm.tm
├── Platform: PC
│   ├── [+] Add TM here
│   ├── pc_global.tm [ACTIVE]
│   └── Project: Game1
│       ├── game1_terms.tm [ACTIVE]
│       └── Folder: French
│           └── french_specific.tm [ACTIVE]
└── Platform: Mobile
    └── Project: Game2
        └── ...
```

### Key UI Elements

1. **Tree View** - Same as File Explorer but TM-focused
2. **Activation Toggle** - Click to activate/deactivate TM at its scope
3. **Drag & Drop** - Move TMs between scopes
4. **Context Menu** - Create TM, Delete, Rename, Move to...
5. **Visual Indicators**:
   - Green dot = Active
   - Gray = Inactive
   - Folder icon shows if any TM inside is active

### File Viewer - TM Indicator

```
┌─────────────────────────────────────────────────────────┐
│ ← Back  │ filename.txt │ TXT │ TM: french.tm (Folder) │ [Change TM]
├─────────────────────────────────────────────────────────┤
│ Source                    │ Target                      │
```

Shows:
- Active TM name
- Scope level (Platform/Project/Folder)
- Click to see all inherited TMs
- Quick toggle to change

---

## Phase 4: Safety & Edge Cases

### Orphan Protection

```
When folder/project/platform is deleted:
1. Find all TMs assigned to that scope
2. Move TM assignments to "Unassigned"
3. Deactivate the TMs
4. Notify user: "X TMs moved to Unassigned"
```

### Conflict Resolution

```
If multiple TMs are active at same level:
- All contribute to TM matches
- Matches sorted by: match%, then TM priority (user can set)

If TM entry conflicts (same source, different target):
- Show all options to user
- Most recent TM entry wins for auto-insert
```

---

## Implementation Order

### Sprint 1: Foundation (Database + Basic API)
- [ ] Create migration for platforms table
- [ ] Create migration for tm_assignments table
- [ ] Add platform_id to projects
- [ ] Create "Unassigned" default platform
- [ ] Migrate existing TMs to Unassigned
- [ ] Platform CRUD endpoints
- [ ] TM assignment endpoints

### Sprint 2: TM Resolution Logic
- [ ] `get_active_tms_for_file()` function
- [ ] `/api/ldm/files/{id}/active-tms` endpoint
- [ ] Update TM match search to use resolved TMs
- [ ] Orphan protection on delete

### Sprint 3: Frontend - TM Explorer
- [ ] New TMExplorerTree component (mirrors file structure)
- [ ] Activation toggle UI
- [ ] Drag & drop TM reassignment
- [ ] Context menu (Create, Delete, Move)
- [ ] "Unassigned" special folder

### Sprint 4: Frontend - File Viewer Integration
- [ ] TM indicator in GridPage toolbar
- [ ] "Active TMs" dropdown/panel
- [ ] Quick TM toggle
- [ ] Show TM source in match results

### Sprint 5: Platform Management
- [ ] Platform CRUD UI
- [ ] Project assignment to platforms
- [ ] Platform-level TM management
- [ ] Migration UI for existing projects

---

## Open Questions

1. **Multiple active TMs** - Should user be able to activate multiple TMs at same scope level?
   - Recommendation: YES, with priority ordering

2. **TM creation location** - Where does "Create TM from file" place the new TM?
   - Recommendation: Same scope as the source file

3. **Cross-platform TMs** - Can a TM be shared across platforms?
   - Recommendation: NO, copy TM if needed (simpler model)

4. **Backward compatibility** - Existing files with linkedTM?
   - Migration: Convert to folder-level assignment

---

## Files to Modify

### Backend
- `server/database/models.py` - Add Platform model, update Project
- `server/tools/ldm/routes/platforms.py` - New file
- `server/tools/ldm/routes/tm.py` - Add assignment endpoints
- `server/tools/ldm/routes/files.py` - Add active-tms endpoint
- `server/tools/ldm/services/tm_resolver.py` - New file, resolution logic

### Frontend
- `src/lib/components/pages/TMPage.svelte` - Redesign with tree
- `src/lib/components/ldm/TMExplorerTree.svelte` - New component
- `src/lib/components/pages/GridPage.svelte` - Add TM indicator
- `src/lib/stores/tm.js` - TM state management
- `src/lib/stores/navigation.js` - Add platform support

### Database
- `migrations/xxx_add_platforms.py`
- `migrations/xxx_add_tm_assignments.py`

---

## Success Criteria

1. User can see active TM when opening any file
2. TMs organized in Platform > Project > Folder hierarchy
3. Activating TM at folder level auto-applies to all files in that folder
4. Deleted folders don't lose TMs (moved to Unassigned)
5. Drag & drop TM between scopes works
6. TM matches come from all active TMs in scope chain

---

## Offline TM Support (Target)

> See: [ARCHITECTURE_SUMMARY.md](ARCHITECTURE_SUMMARY.md) and [OFFLINE_ONLINE_MODE.md](OFFLINE_ONLINE_MODE.md)

### Goal: TM Works Identically Offline

SQLite needs equivalent tables:

```sql
-- offline_tm_assignments (mirrors ldm_tm_assignments)
CREATE TABLE offline_tm_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tm_id INTEGER NOT NULL,
    platform_id INTEGER,
    project_id INTEGER,
    folder_id INTEGER,
    is_active INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### DB Abstraction Pattern

```python
class TMRepository:
    """Same interface for PostgreSQL and SQLite."""
    async def assign(self, tm_id: int, target: AssignmentTarget) -> TM
    async def get_active_tms(self, scope: Scope) -> List[TM]

# Runtime selection
repo = PostgreSQLTMRepository() if online else SQLiteTMRepository()
```

---

*Updated 2026-01-11 | DB Abstraction for Full Offline Support*
