# DOC-002: Folder Schema Mismatch (updated_at Column)

**Issue ID:** DOC-002
**Date:** 2026-02-01
**Status:** Fixed
**Category:** Schema Mismatch

---

## Problem Statement

All folder creation operations failed in OFFLINE mode with the error:
```
no such column: updated_at
```

The `folder_repo.py` repository was using `updated_at` column in SQL statements, but the `offline_folders` SQLite table does not have this column. This caused a complete breakdown of folder functionality when operating in OFFLINE mode.

---

## Root Cause Analysis

### The Schema Difference

| Column | PostgreSQL (ONLINE) | SQLite (OFFLINE) |
|--------|---------------------|------------------|
| `id` | Yes | Yes |
| `project_id` | Yes | Yes |
| `name` | Yes | Yes |
| `parent_id` | Yes | Yes |
| `sort_order` | Yes | Yes |
| `created_at` | Yes | Yes |
| **`updated_at`** | **Yes** | **NO** |

The PostgreSQL schema for the `folders` table includes an `updated_at` column, but the SQLite `offline_folders` table was created without it.

### Why It Happened

1. **Schema Drift:** The ONLINE and OFFLINE schemas were designed at different times
2. **Copy-Paste Coding:** SQL statements were written for ONLINE mode first, then copied for OFFLINE mode without verifying column availability
3. **Lack of Schema Validation:** No automated check to verify OFFLINE SQL statements match OFFLINE schema

### Methods Affected

Five methods in `folder_repo.py` contained OFFLINE mode SQL that referenced `updated_at`:

1. `create_folder()` - INSERT statement
2. `update_folder()` - UPDATE statement with SET clause
3. `move_folder()` - UPDATE statement with SET clause
4. `reorder_folders()` - UPDATE statement with SET clause
5. `delete_folder()` - (indirectly affected through cascading operations)

---

## The Fix

### Changes Made to `folder_repo.py`

Removed all references to `updated_at` from OFFLINE mode SQL statements:

**1. create_folder() - INSERT statement**
```python
# BEFORE (broken)
INSERT INTO offline_folders (id, project_id, name, parent_id, sort_order, created_at, updated_at)
VALUES (?, ?, ?, ?, ?, ?, ?)

# AFTER (fixed)
INSERT INTO offline_folders (id, project_id, name, parent_id, sort_order, created_at)
VALUES (?, ?, ?, ?, ?, ?)
```

**2. update_folder() - UPDATE statement**
```python
# BEFORE (broken)
UPDATE offline_folders SET name = ?, updated_at = ? WHERE id = ?

# AFTER (fixed)
UPDATE offline_folders SET name = ? WHERE id = ?
```

**3. move_folder() - UPDATE statement**
```python
# BEFORE (broken)
UPDATE offline_folders SET parent_id = ?, updated_at = ? WHERE id = ?

# AFTER (fixed)
UPDATE offline_folders SET parent_id = ? WHERE id = ?
```

**4. reorder_folders() - UPDATE statement**
```python
# BEFORE (broken)
UPDATE offline_folders SET sort_order = ?, updated_at = ? WHERE id = ?

# AFTER (fixed)
UPDATE offline_folders SET sort_order = ? WHERE id = ?
```

---

## Prevention Guidelines

### For Future Development

1. **Schema Comparison Checklist**
   - Before writing OFFLINE mode SQL, ALWAYS check the actual SQLite schema
   - Run: `./scripts/db_manager.sh sqlite-analyze` to see current schema

2. **Test Both Modes**
   - Every database operation must be tested in BOTH ONLINE and OFFLINE modes
   - Schema mismatch errors only appear in the mode with the missing column

3. **Code Review Focus**
   - When reviewing repository code, specifically check:
     - Column lists in INSERT statements
     - SET clauses in UPDATE statements
     - Column references in SELECT statements

4. **Schema Documentation**
   - Maintain a side-by-side schema comparison document
   - Update whenever either schema changes

### Red Flags to Watch For

| Pattern | Risk |
|---------|------|
| Same SQL for ONLINE/OFFLINE | High - schemas differ |
| `updated_at` in OFFLINE SQL | High - column doesn't exist |
| `datetime('now')` for `updated_at` | Medium - verify column exists |
| Copy-pasting ONLINE SQL to OFFLINE | High - verify schema match |

---

## Impact

| Aspect | Before Fix | After Fix |
|--------|------------|-----------|
| Folder creation | Failed | Works |
| Folder rename | Failed | Works |
| Folder move | Failed | Works |
| Folder reorder | Failed | Works |
| OFFLINE mode usability | Broken | Functional |

---

## References

- **File:** `server/db/repositories/folder_repo.py`
- **Schema:** `server/db/offline_schema.py` (SQLite schema definition)
- **Schema:** `server/db/models.py` (PostgreSQL schema via SQLAlchemy)
- **DB Manager:** `./scripts/db_manager.sh sqlite-analyze`
- **Architecture:** `docs/architecture/OFFLINE_ONLINE_MODE.md`

---

## Lessons Learned

1. **OFFLINE and ONLINE are NOT identical** - Never assume SQL that works for one will work for the other
2. **Test in OFFLINE mode** - It's easy to forget since ONLINE is the default development mode
3. **Schema drift is silent** - There's no warning until runtime when the wrong mode is used
4. **`updated_at` is a PostgreSQL-ism** - SQLite schemas often omit it for simplicity

---

*Documented to prevent future schema mismatch issues between ONLINE and OFFLINE modes.*
