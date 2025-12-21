# Session Context - Claude Handoff Document

**Last Updated:** 2025-12-22 | **Build:** 324 (FAILED) | **Next:** 325

---

## CURRENT SESSION: CI FIX INVESTIGATION

### Build Status

| Build | Status | Issue |
|-------|--------|-------|
| 325 | PENDING | Enhanced schema upgrade logging |
| 324 | FAILED | `test_01_manual_sync_tm` 500 error |
| 323 | FAILED | `string_id` column missing |
| 322 | PASS | LIGHT build passed |

### Issue Being Fixed: test_01_manual_sync_tm 500 Error

The sync endpoint `/api/ldm/tm/{id}/sync` is returning 500. Possible causes:
1. Schema upgrade not executing properly
2. Model loading failure
3. File I/O issues

### Fix Applied: Enhanced Schema Upgrade Logging (Build 325)

Added comprehensive logging to `upgrade_schema()` to diagnose if columns are being added:
- Logs database type (SQLite/PostgreSQL)
- Logs table count
- Logs each ALTER TABLE execution
- Verifies columns after adding
- Reports summary (added/skipped count)

```python
# server/database/db_setup.py
def upgrade_schema(engine):
    logger.info("SCHEMA UPGRADE: Checking for missing columns...")
    logger.info(f"Database type: {db_type}")
    logger.info(f"Found {len(table_names)} tables in database")
    # ... detailed logging for each column check/add
    logger.info(f"Schema upgrade complete: {columns_added} added, {columns_skipped} already existed")
```

---

## SCHEMA UPGRADE MECHANISM

The `upgrade_schema()` function in `server/database/db_setup.py` automatically adds missing columns:

```python
missing_columns = [
    ("ldm_translation_memories", "mode", "VARCHAR(20)", "'standard'"),
    ("ldm_tm_entries", "string_id", "VARCHAR(255)", "NULL"),
]
```

**Key Points:**
- Runs during `initialize_database()` after `create_all()`
- Inspector created INSIDE connection for fresh metadata
- Verifies columns after adding
- Handles race conditions gracefully

---

## OFFLINE MODE (P33) - LOCAL Authentication

**How it works:**
1. SQLite mode creates `LOCAL` user (username: "LOCAL", no password)
2. Health endpoint returns `auto_token` for auto-login
3. Frontend calls `tryAutoLogin()` which uses the token
4. **No credentials needed** - fully automatic

---

## DEV_MODE Auto-Authentication (CI Behavior)

In CI, `DEV_MODE=true` enables auto-authentication on localhost:

```python
# server/utils/dependencies.py:313-317
if config.DEV_MODE and _is_localhost(request):
    if not credentials:
        logger.debug("DEV_MODE: Auto-authenticating as dev_admin")
        return _get_dev_user()  # user_id=1, username="dev_admin"
```

---

## FILES CHANGED THIS SESSION

```
server/database/db_setup.py
  - Lines 173-253: Enhanced upgrade_schema() with verbose logging
  - Adds 'mode' column to ldm_translation_memories
  - Adds 'string_id' column to ldm_tm_entries
```

---

## BUILD HISTORY (Recent)

| Build | Status | Issue | Fix |
|-------|--------|-------|-----|
| 325 | PENDING | Enhanced logging | See above |
| 324 | FAILED | Sync 500 error | string_id added but sync fails |
| 323 | FAILED | string_id missing | Added to upgrade_schema |
| 322 | PASS | LIGHT build | Schema upgrade working |
| 321 | PASS | Skip marker removed | StringID tests enabled |

---

## KEY PATHS

| What | Path |
|------|------|
| **Schema upgrade** | `server/database/db_setup.py:173-253` |
| **Sync endpoint** | `server/tools/ldm/api.py:2211-2303` |
| **TMSyncManager** | `server/tools/ldm/tm_indexer.py:1296-1920` |
| **DEV_MODE auth** | `server/utils/dependencies.py:313-317` |
| **TrackedOperation** | `server/utils/progress_tracker.py:226` |

---

## QUICK COMMANDS

```bash
# Start backend
python3 server/main.py

# Trigger QA-LIGHT build
echo "Build QA-LIGHT" >> GITEA_TRIGGER.txt
git add -A && git commit -m "Build 325" && git push origin main && git push gitea main

# Test schema upgrade locally
python3 -c "from server.database.db_setup import setup_database; setup_database()"
```

---

## NEXT STEPS

1. **Trigger Build 325** - Enhanced logging will show if schema upgrade executes
2. **Analyze CI logs** - Look for "SCHEMA UPGRADE" messages
3. **Identify root cause** - Determine why sync returns 500

---

*Session focus: CI debugging, schema upgrade verification*
