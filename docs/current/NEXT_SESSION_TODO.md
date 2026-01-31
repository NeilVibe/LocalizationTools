# Next Session TODO: Fix Architecture Layer Violations

> **Priority:** HIGH
> **Estimated Time:** 2-3 hours
> **Full Plan:** [ARCHITECTURE_DEBT_REPORT.md](ARCHITECTURE_DEBT_REPORT.md)

---

## Quick Context

The repository pattern has **3 layer violations** where PostgreSQL repos check `config.ACTIVE_DATABASE_TYPE == "sqlite"` internally. This violates the abstraction - repos should never know about other database types.

---

## The 3 Lines to Fix

```bash
# Find the violations
grep -n "ACTIVE_DATABASE_TYPE" server/repositories/postgresql/*.py
```

**Results should show:**
- `row_repo.py:423` - in `_fuzzy_search()`
- `row_repo.py:598` - in `suggest_similar()`
- `tm_repo.py:1001` - in `search_similar()`

---

## Implementation Steps

### Step 1: Create CapabilityAwareWrapper (30 min)

Create `server/repositories/capability_wrapper.py`:

```python
from typing import List, Dict, Any
from server import config
from loguru import logger

class CapabilityAwareWrapper:
    """Wraps repos to handle SQLite fallback gracefully."""

    POSTGRESQL_ONLY_METHODS = {
        'search_similar',
        'suggest_similar',
        '_fuzzy_search',
    }

    def __init__(self, wrapped_repo):
        self._wrapped = wrapped_repo

    def __getattr__(self, name):
        attr = getattr(self._wrapped, name)

        if name in self.POSTGRESQL_ONLY_METHODS and config.ACTIVE_DATABASE_TYPE == "sqlite":
            async def graceful_degradation(*args, **kwargs):
                logger.debug(f"[CAPABILITY] {name}() not available in SQLite mode")
                return [], 0 if name == '_fuzzy_search' else []
            return graceful_degradation

        return attr
```

### Step 2: Update Factory (30 min)

In `server/repositories/factory.py`:

1. Add import: `from server.repositories.capability_wrapper import CapabilityAwareWrapper`
2. Add function:
```python
def _is_sqlite_fallback() -> bool:
    from server import config
    return config.ACTIVE_DATABASE_TYPE == "sqlite"
```
3. Update each `get_*_repository()` to wrap when in fallback mode

### Step 3: Clean PostgreSQL Repos (1 hour)

Remove these blocks:

**row_repo.py lines 423-425:**
```python
# DELETE THIS
if config.ACTIVE_DATABASE_TYPE == "sqlite":
    logger.debug("[ROW-REPO] Fuzzy search not available (SQLite mode)")
    return [], 0
```

**row_repo.py lines 598-600:**
```python
# DELETE THIS
if config.ACTIVE_DATABASE_TYPE == "sqlite":
    logger.debug("[ROW-REPO] Similarity search not available (SQLite mode)")
    return []
```

**tm_repo.py lines 1001-1003:**
```python
# DELETE THIS
if config.ACTIVE_DATABASE_TYPE == "sqlite":
    logger.debug("[TM-REPO] Similarity search not available (SQLite mode)")
    return []
```

### Step 4: Test (30 min)

```bash
# Start servers
./scripts/start_all_servers.sh

# Run tests with PostgreSQL
pytest tests/ -x -q

# Test SQLite fallback
DATABASE_MODE=sqlite pytest tests/ -x -q

# Verify no violations remain
grep -n "ACTIVE_DATABASE_TYPE" server/repositories/postgresql/*.py
# Should return NOTHING
```

### Step 5: Commit & Build (30 min)

```bash
git add -A
git commit -m "Refactor: Remove layer violations with CapabilityAwareWrapper

- Created CapabilityAwareWrapper for graceful degradation
- Updated factory to wrap repos in SQLite fallback mode
- Removed ACTIVE_DATABASE_TYPE checks from PostgreSQL repos
- Clean layer abstraction preserved

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"

git push origin main
./scripts/gitea_control.sh start
git push gitea main
./scripts/gitea_control.sh stop
```

---

## Verification

After fix, confirm:
- [ ] `grep "ACTIVE_DATABASE_TYPE" server/repositories/postgresql/*.py` returns nothing
- [ ] All tests pass
- [ ] Similarity search works in PostgreSQL mode
- [ ] Similarity search returns `[]` in SQLite mode (graceful)
- [ ] Build succeeds

---

## Files Changed

| File | Action |
|------|--------|
| `server/repositories/capability_wrapper.py` | CREATE |
| `server/repositories/factory.py` | MODIFY |
| `server/repositories/postgresql/row_repo.py` | REMOVE violations |
| `server/repositories/postgresql/tm_repo.py` | REMOVE violations |
| `docs/current/ISSUES_TO_FIX.md` | Mark ARCH-001 FIXED |
| `docs/current/SESSION_CONTEXT.md` | Add Session 60 |

---

*Delete this file after completing the fix.*
