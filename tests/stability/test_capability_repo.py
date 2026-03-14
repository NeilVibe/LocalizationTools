"""
Parity tests for CapabilityRepository across all database modes.

SPECIAL HANDLING: SQLiteCapabilityRepository is explicitly a stub.
SQLite modes are stubs by design -- testing graceful degradation, not functional parity.

For ONLINE mode: would test full capability management (skipped: no PostgreSQL).
For SERVER_LOCAL and OFFLINE modes: verify stub methods:
  - Don't raise exceptions (except grant_capability which raises NotImplementedError)
  - Return empty lists or None for queries
  - Return False for revoke
"""
from __future__ import annotations

import pytest

pytestmark = [pytest.mark.stability, pytest.mark.asyncio]


# =============================================================================
# Stub Behavior Tests (SQLite modes)
# =============================================================================


async def test_capability_get_user_returns_none(capability_repo, db_mode):
    """SQLite stub: get_user returns None."""
    result = await capability_repo.get_user(1)
    assert result is None


async def test_capability_get_capability_returns_none(capability_repo, db_mode):
    """SQLite stub: get_capability returns None."""
    result = await capability_repo.get_capability(1)
    assert result is None


async def test_capability_get_user_capability_returns_none(capability_repo, db_mode):
    """SQLite stub: get_user_capability returns None."""
    result = await capability_repo.get_user_capability(1, "admin")
    assert result is None


async def test_capability_grant_raises(capability_repo, db_mode):
    """SQLite stub: grant_capability raises NotImplementedError."""
    with pytest.raises(NotImplementedError):
        await capability_repo.grant_capability(
            user_id=1, capability_name="admin", granted_by=1
        )


async def test_capability_revoke_returns_false(capability_repo, db_mode):
    """SQLite stub: revoke_capability returns False."""
    result = await capability_repo.revoke_capability(1)
    assert result is False


async def test_capability_list_all_returns_empty(capability_repo, db_mode):
    """SQLite stub: list_all_capabilities returns empty list."""
    result = await capability_repo.list_all_capabilities()
    assert result == []


async def test_capability_list_user_returns_empty(capability_repo, db_mode):
    """SQLite stub: list_user_capabilities returns empty list."""
    result = await capability_repo.list_user_capabilities(1)
    assert result == []
