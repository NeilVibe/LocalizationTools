# P26: Async TMManager Refactor

**Created:** 2025-12-12 | **Priority:** HIGH | **Status:** Pending

---

## Problem

TMManager uses sync database sessions inside async endpoints:
```python
sync_db = next(get_db())  # Blocks event loop!
tm_manager = TMManager(sync_db)
```

At 100+ concurrent users, this could cause server freezing.

---

## Scope

| Component | Lines | Changes |
|-----------|-------|---------|
| `server/tools/ldm/tm_manager.py` | ~430 | Convert to async |
| `server/database/db_utils.py` | +50 | Add async bulk_copy |
| `server/tools/ldm/api.py` | 4 endpoints | Use async db |

**Estimated:** 2-3 hours + testing

---

## Affected Endpoints

| Line | Endpoint | TMManager Method |
|------|----------|-----------------|
| 850 | `create_tm_from_file` | `upload_tm()` |
| 952 | `tm_search` | `search_exact()` |
| 986 | `tm_search_fuzzy` | `search_like()` |
| 1011 | `tm_add_entry` | `add_entry()` |

---

## Implementation Steps

1. **Create AsyncTMManager class**
   - Copy TMManager to AsyncTMManager
   - Change `Session` to `AsyncSession`
   - Convert all methods to `async def`
   - Replace `self.db.query(...)` with `await self.db.execute(select(...))`

2. **Create async bulk operations**
   - `async_bulk_copy_tm_entries()`
   - `async_bulk_insert_tm_entries()`

3. **Update endpoints**
   - Remove `sync_db = next(get_db())`
   - Use `db: AsyncSession = Depends(get_async_db)`
   - Use AsyncTMManager

4. **Test**
   - Unit tests for AsyncTMManager
   - Integration tests for endpoints
   - Load test with concurrent users

---

## Current Mitigation

Operations are fast (indexed lookups), so blocking is minimal:
- `search_exact()` - O(1) hash lookup
- `search_like()` - Indexed LIKE
- `add_entry()` - Single insert

Not urgent unless TM grows very large or many concurrent users.

---

## Related Issues

- DR4-001: Sync DB Session in Async Endpoint
- DR4-002: Repeated Sync DB Pattern in TM Search

---

*Created from Code Review Phase 3*
