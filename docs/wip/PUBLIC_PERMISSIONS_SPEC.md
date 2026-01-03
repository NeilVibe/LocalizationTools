# DESIGN-001: Public by Default Permission Model

> **Status:** IMPLEMENTED | **Date:** 2026-01-03 | **Build:** 439+

## Summary

Transformed LDM from "private by default" (owner_id filtering) to "public by default with optional restrictions".

**Before:** Each user only sees their own data (owner_id filtering in 77+ locations)
**After:** All users see everything by default. Admins can restrict specific platforms/projects.

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| TM restriction | Inherit from project/platform | Simpler to manage, TMs follow project scope |
| Name uniqueness | Globally unique | No duplicates anywhere - cleaner, avoids confusion |
| Who manages | Admin only | Centralized control, prevents accidental lockouts |
| Default state | All public | Team tool - everyone sees same data by default |

---

## Database Changes

### New Columns

```sql
-- LDMPlatform
ALTER TABLE ldm_platforms ADD COLUMN is_restricted BOOLEAN DEFAULT FALSE NOT NULL;

-- LDMProject
ALTER TABLE ldm_projects ADD COLUMN is_restricted BOOLEAN DEFAULT FALSE NOT NULL;
```

### New Table

```sql
CREATE TABLE ldm_resource_access (
    id SERIAL PRIMARY KEY,
    platform_id INTEGER REFERENCES ldm_platforms(id) ON DELETE CASCADE,
    project_id INTEGER REFERENCES ldm_projects(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    access_level VARCHAR(20) DEFAULT 'full',
    granted_by INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
    granted_at TIMESTAMP DEFAULT NOW(),

    UNIQUE (platform_id, user_id),
    UNIQUE (project_id, user_id)
);

CREATE INDEX idx_resource_access_platform ON ldm_resource_access(platform_id, user_id);
CREATE INDEX idx_resource_access_project ON ldm_resource_access(project_id, user_id);
```

### Updated Unique Constraints

All entity names are now globally unique (no duplicates anywhere):

| Table | Old Constraint | New Constraint |
|-------|---------------|----------------|
| ldm_platforms | `UNIQUE(name, owner_id)` | `UNIQUE(name)` |
| ldm_projects | `UNIQUE(name, owner_id)` | `UNIQUE(name)` |
| ldm_folders | `UNIQUE(name, project_id, parent_id)` | `UNIQUE(name)` |
| ldm_files | `UNIQUE(name, project_id, folder_id)` | `UNIQUE(name)` |
| ldm_translation_memories | (none) | `UNIQUE(name)` |

---

## Permission Rules

### Access Hierarchy

```
1. Admin/Superadmin → Full access to EVERYTHING
2. Public resource (is_restricted=False) → All users can access
3. Restricted resource → Only:
   - Owner (owner_id)
   - Users with explicit grant (ldm_resource_access)
4. TMs → Inherit from assigned project/platform
```

### Inheritance Chain

```
Platform (restricted)
└── Project → User must have PLATFORM access
    └── Folder → Inherits from PROJECT
        └── File → Inherits from PROJECT
            └── Rows → Inherits from FILE

TM Assignment:
├── Platform-level → Inherits platform restriction
├── Project-level → Inherits project restriction
└── Folder-level → Inherits project restriction
```

---

## API Endpoints

### Platform Restriction (Admin Only)

```
PUT /api/ldm/platforms/{id}/restriction?is_restricted=true|false
GET /api/ldm/platforms/{id}/access
POST /api/ldm/platforms/{id}/access  {user_ids: [1, 2, 3]}
DELETE /api/ldm/platforms/{id}/access/{user_id}
```

### Project Restriction (Admin Only)

```
PUT /api/ldm/projects/{id}/restriction?is_restricted=true|false
GET /api/ldm/projects/{id}/access
POST /api/ldm/projects/{id}/access  {user_ids: [1, 2, 3]}
DELETE /api/ldm/projects/{id}/access/{user_id}
```

---

## Permission Helper Functions

Located in `server/tools/ldm/permissions.py`:

```python
# Check access to specific resources
async def can_access_platform(db, platform_id, user) -> bool
async def can_access_project(db, project_id, user) -> bool
async def can_access_file(db, file_id, user) -> bool
async def can_access_folder(db, folder_id, user) -> bool
async def can_access_tm(db, tm_id, user) -> bool

# List accessible resources
async def get_accessible_platforms(db, user, include_projects=False) -> List
async def get_accessible_projects(db, user, platform_id=None) -> List
async def get_accessible_tms(db, user) -> List

# Manage access grants
async def grant_platform_access(db, platform_id, user_ids, granted_by) -> int
async def revoke_platform_access(db, platform_id, user_id) -> bool
async def grant_project_access(db, project_id, user_ids, granted_by) -> int
async def revoke_project_access(db, project_id, user_id) -> bool
async def get_platform_access_list(db, platform_id) -> List[dict]
async def get_project_access_list(db, project_id) -> List[dict]
```

---

## Files Modified

### Database
- `server/database/models.py` - Added `is_restricted` columns, `LDMResourceAccess` table, updated unique constraints

### New Files
- `server/tools/ldm/permissions.py` - Central permission logic

### Route Updates (13 files, 77+ locations)
- `platforms.py` - 7 locations + admin endpoints
- `projects.py` - 7 locations + admin endpoints
- `folders.py` - 6 locations
- `files.py` - 12 locations
- `rows.py` - 4 locations
- `tm_crud.py` - 6 locations
- `tm_entries.py` - 7 locations
- `tm_search.py` - 3 locations
- `tm_linking.py` - 5 locations
- `tm_assignment.py` - 8 locations
- `tm_indexes.py` - 4 locations
- `pretranslate.py` - 1 location
- `sync.py` - 2 locations

### Schema Updates
- `server/tools/ldm/schemas/project.py` - Added `is_restricted` to ProjectResponse

---

## Frontend Changes (Implemented)

### Visual Indicators
- Lock icon badge on restricted platforms/projects in ExplorerGrid
- Tooltip: "Restricted - Admin managed access"

### Admin Access Control Component
**File:** `locaNext/src/lib/components/admin/AccessControl.svelte`
- Toggle restriction on/off for platform/project
- View list of users with access
- Add users to access list
- Remove users from access list
- Only visible to admin users

### Context Menu Integration
**File:** `locaNext/src/lib/components/pages/FilesPage.svelte`
- "Manage Access..." option on platforms and projects
- Only visible to users with admin/superadmin role

---

## Migration Notes

Since we're in development, no migration needed - database can be fully refreshed.

For production migration:
1. Add columns with defaults
2. Create access table
3. Update unique constraints (may require deduplication)
4. Existing data becomes public by default

---

*Implemented 2026-01-03 | Session 18*
