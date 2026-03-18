# Build 516 Session Notes - aiosqlite Migration & SQLite Mode Fixes

**Date:** 2026-01-31
**Builds:** 504-516
**Final Status:** SUCCESS (GitHub + Gitea)

---

## Summary

Completed the aiosqlite migration and fixed critical issues with PostgreSQL repos running in SQLite fallback mode.

---

## Issues Encountered & Solutions

### Issue 1: Server Hanging on "Creating database tables..."
**Builds affected:** 508-511
**Root cause:** SQLite cleanup was happening BETWEEN retry attempts, losing partial table creation progress.
**Fix:** Moved cleanup to BEFORE all retry attempts, increased timeout to 60s.

### Issue 2: `no such function: similarity`
**Builds affected:** 512-514
**Root cause:** TM suggest endpoint used PostgreSQL's `similarity()` function (pg_trgm extension) which doesn't exist in SQLite.
**Initial (wrong) fix:** Changed factory to return SQLite repos when `config.ACTIVE_DATABASE_TYPE == "sqlite"`.
**Problem with that fix:** SQLite repos use OFFLINE schema (`offline_projects`), but server creates STANDARD schema (`ldm_projects`).

### Issue 3: Wrong Schema Used (500 errors on list_projects, create_folder)
**Build affected:** 515
**Root cause:** Factory was returning SQLite repos, but those repos query `offline_projects` table which doesn't exist in server's SQLite database.
**Correct fix:**
1. Reverted factory change - SQLite repos are for OFFLINE MODE only
2. Added SQLite checks to PostgreSQL repos' similarity methods - they return empty results instead of failing

### Issue 4: PostgreSQL-specific SQL functions
**Functions affected:** `similarity()`, `to_char()`, `version()`
**Fix:** Added skip markers to tests that require PostgreSQL-specific functions.

---

## Architecture Clarification

```
TWO DIFFERENT SQLITE USE CASES:

1. SERVER SQLITE FALLBACK (when PostgreSQL unavailable)
   - Uses STANDARD schema: ldm_projects, ldm_folders, ldm_files, ldm_rows
   - Uses PostgreSQL repos (they work with standard schema)
   - Similarity functions return empty (graceful degradation)

2. OFFLINE MODE (user's local data)
   - Uses OFFLINE schema: offline_projects, offline_folders, offline_files, offline_rows
   - Uses SQLite repos
   - Triggered by "Bearer OFFLINE_MODE_" auth token
```

---

## Files Modified

| File | Change |
|------|--------|
| `server/repositories/factory.py` | Clarified offline mode detection (auth header only, not DB type) |
| `server/repositories/postgresql/row_repo.py` | Added SQLite checks to `suggest_similar()`, `_fuzzy_search()` |
| `server/repositories/postgresql/tm_repo.py` | Added SQLite check to `search_similar()` |
| `tests/api/test_p3_offline_sync.py` | Added `@requires_postgresql` skip markers |
| `tests/api/test_generated_stubs.py` | Added PostgreSQL connection check for skip markers |
| `.gitea/workflows/build.yml` | Fixed SQLite cleanup timing, increased timeout to 60s |

---

## Key Code Changes

### PostgreSQL repos graceful SQLite handling:
```python
async def suggest_similar(self, ...):
    from server import config

    # similarity() requires PostgreSQL pg_trgm extension
    # Return empty when running on SQLite
    if config.ACTIVE_DATABASE_TYPE == "sqlite":
        logger.debug("[ROW-REPO] Similarity search not available (SQLite mode)")
        return []

    # ... normal PostgreSQL code
```

### Factory keeps original behavior:
```python
def _is_offline_mode(request: Request) -> bool:
    """
    Offline mode is indicated by Authorization header starting with "OFFLINE_MODE_".

    NOTE: This is NOT about whether the server uses SQLite vs PostgreSQL.
    The SQLite repos use a separate OFFLINE schema which is different from
    the standard server schema.
    """
    auth_header = request.headers.get("Authorization", "")
    return auth_header.startswith("Bearer OFFLINE_MODE_")
```

---

## Test Results (Build 516)

- **GitHub:** SUCCESS (15m52s) - Windows + macOS installers
- **Gitea:** SUCCESS - Windows installer
- **Tests:** All passing (PostgreSQL-specific tests properly skipped)

---

## Lessons Learned

1. **SQLite repos ≠ Server SQLite fallback** - They're for completely different purposes
2. **PostgreSQL-specific functions need graceful degradation** - Return empty, don't crash
3. **CI cleanup timing matters** - Don't clean between retries
4. **Config checking at request time works** - `config.ACTIVE_DATABASE_TYPE` is set during server init
