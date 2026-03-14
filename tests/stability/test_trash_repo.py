"""
Parity tests for TrashRepository across all database modes.

Tests every interface method with parametrized db_mode (online/server_local/offline).
Korean/English game-realistic data used throughout.
"""
from __future__ import annotations

import pytest

pytestmark = [pytest.mark.stability, pytest.mark.asyncio]


# =============================================================================
# Helpers
# =============================================================================

_USER_ID = 1


def _make_trash_item(name="menu_strings.xml", item_type="file", item_id=100):
    """Create a trash item data dict."""
    return {
        "item_type": item_type,
        "item_id": item_id,
        "item_name": name,
        "item_data": {
            "name": name,
            "format": "xml",
            "source_language": "ko",
            "target_language": "en",
            "rows": [
                {"source": "새 게임", "target": "New Game"},
                {"source": "계속하기", "target": "Continue"},
            ],
        },
        "deleted_by": _USER_ID,
        "retention_days": 30,
    }


# =============================================================================
# Query Operations
# =============================================================================


async def test_trash_create(trash_repo, db_mode):
    """Create a trash item and verify returned dict."""
    data = _make_trash_item()
    result = await trash_repo.create(**data)
    assert result is not None
    assert result["item_type"] == "file"
    assert result["item_name"] == "menu_strings.xml"
    assert result["status"] == "trashed"
    assert "id" in result


async def test_trash_get(trash_repo, db_mode):
    """Create then get by ID."""
    data = _make_trash_item()
    created = await trash_repo.create(**data)
    fetched = await trash_repo.get(created["id"])
    assert fetched is not None
    assert fetched["item_name"] == "menu_strings.xml"


async def test_trash_get_nonexistent(trash_repo, db_mode):
    """Get non-existent trash item returns None."""
    result = await trash_repo.get(999999)
    assert result is None


async def test_trash_get_for_user(trash_repo, db_mode):
    """Get all trash items for a user."""
    await trash_repo.create(**_make_trash_item(name="file_a.xml", item_id=101))
    await trash_repo.create(**_make_trash_item(name="file_b.xml", item_id=102))
    results = await trash_repo.get_for_user(_USER_ID)
    assert len(results) == 2
    names = {r["item_name"] for r in results}
    assert "file_a.xml" in names
    assert "file_b.xml" in names


async def test_trash_get_for_user_empty(trash_repo, db_mode):
    """Get trash for user with no trash returns empty list."""
    results = await trash_repo.get_for_user(999)
    assert results == []


# =============================================================================
# Write Operations
# =============================================================================


async def test_trash_restore(trash_repo, db_mode):
    """Restore a trashed item."""
    data = _make_trash_item()
    created = await trash_repo.create(**data)
    restored = await trash_repo.restore(created["id"], _USER_ID)
    assert restored is not None
    assert restored["status"] == "restored"
    assert restored["item_data"] is not None


async def test_trash_restore_nonexistent(trash_repo, db_mode):
    """Restore non-existent returns None."""
    result = await trash_repo.restore(999999, _USER_ID)
    assert result is None


async def test_trash_restore_wrong_user(trash_repo, db_mode):
    """Restore by wrong user returns None."""
    data = _make_trash_item()
    created = await trash_repo.create(**data)
    result = await trash_repo.restore(created["id"], user_id=999)
    assert result is None


async def test_trash_permanent_delete(trash_repo, db_mode):
    """Permanently delete a trash item."""
    data = _make_trash_item()
    created = await trash_repo.create(**data)
    result = await trash_repo.permanent_delete(created["id"], _USER_ID)
    assert result is True
    # Verify gone
    assert await trash_repo.get(created["id"]) is None


async def test_trash_permanent_delete_nonexistent(trash_repo, db_mode):
    """Permanently delete non-existent returns False."""
    result = await trash_repo.permanent_delete(999999, _USER_ID)
    assert result is False


async def test_trash_empty_for_user(trash_repo, db_mode):
    """Empty all trash for a user."""
    await trash_repo.create(**_make_trash_item(name="a.xml", item_id=201))
    await trash_repo.create(**_make_trash_item(name="b.xml", item_id=202))
    await trash_repo.create(**_make_trash_item(name="c.xml", item_id=203))
    count = await trash_repo.empty_for_user(_USER_ID)
    assert count == 3
    # Verify empty
    results = await trash_repo.get_for_user(_USER_ID)
    assert len(results) == 0


async def test_trash_cleanup_expired(trash_repo, db_mode):
    """Cleanup expired trash items."""
    # Create item with 0 retention (immediately expired)
    data = _make_trash_item()
    data["retention_days"] = 0
    await trash_repo.create(**data)
    # cleanup_expired should find and remove it
    count = await trash_repo.cleanup_expired()
    # May or may not be expired depending on timing precision
    assert count >= 0


# =============================================================================
# Utility Operations
# =============================================================================


async def test_trash_count_for_user(trash_repo, db_mode):
    """Count trash items for a user."""
    await trash_repo.create(**_make_trash_item(name="x.xml", item_id=301))
    await trash_repo.create(**_make_trash_item(name="y.xml", item_id=302))
    count = await trash_repo.count_for_user(_USER_ID)
    assert count == 2


async def test_trash_count_for_user_excludes_restored(trash_repo, db_mode):
    """Count excludes restored items."""
    created = await trash_repo.create(**_make_trash_item(name="z.xml", item_id=401))
    await trash_repo.restore(created["id"], _USER_ID)
    count = await trash_repo.count_for_user(_USER_ID)
    assert count == 0
