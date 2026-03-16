"""
Parity tests for RowRepository across all database modes.

Tests every interface method with parametrized db_mode (online/server_local/offline).
Korean/English game-realistic data used throughout.
"""
from __future__ import annotations

import pytest
from tests.stability.conftest import DbMode

pytestmark = [pytest.mark.stability, pytest.mark.asyncio]


# =============================================================================
# Helper: create hierarchy for row tests
# =============================================================================


async def _create_file(platform_repo, project_repo, file_repo):
    """Create platform -> project -> file, return file dict."""
    plat = await platform_repo.create(name="PC", owner_id=1)
    proj = await project_repo.create(
        name="다크 소울 IV", owner_id=1, platform_id=plat["id"]
    )
    f = await file_repo.create(
        name="menu_strings.xml", original_filename="menu_strings.xml",
        format="xml", project_id=proj["id"],
        source_language="ko", target_language="en",
    )
    return f


# =============================================================================
# Core CRUD
# =============================================================================


async def test_row_create(row_repo, platform_repo, project_repo, file_repo, db_mode):
    """Create row and verify returned dict."""
    f = await _create_file(platform_repo, project_repo, file_repo)
    result = await row_repo.create(
        file_id=f["id"], row_num=0,
        source="새 게임", target="New Game",
        string_id="MENU_NEW_GAME", status="pending",
    )
    assert result is not None
    assert result["source"] == "새 게임"
    assert result["target"] == "New Game"
    assert result["string_id"] == "MENU_NEW_GAME"
    assert "id" in result


async def test_row_get(row_repo, platform_repo, project_repo, file_repo, db_mode):
    """Create then get by ID."""
    f = await _create_file(platform_repo, project_repo, file_repo)
    created = await row_repo.create(
        file_id=f["id"], row_num=0, source="설정", target="Settings",
    )
    fetched = await row_repo.get(created["id"])
    assert fetched is not None
    assert fetched["source"] == "설정"


async def test_row_get_nonexistent(row_repo, db_mode):
    """Get non-existent row returns None."""
    result = await row_repo.get(999999)
    assert result is None


async def test_row_get_with_file(row_repo, platform_repo, project_repo, file_repo, db_mode):
    """Get row with file info."""
    f = await _create_file(platform_repo, project_repo, file_repo)
    created = await row_repo.create(
        file_id=f["id"], row_num=0, source="시작", target="Start",
    )
    result = await row_repo.get_with_file(created["id"])
    assert result is not None
    assert result["file_id"] == f["id"]


async def test_row_update(row_repo, platform_repo, project_repo, file_repo, db_mode):
    """Update row target and status."""
    f = await _create_file(platform_repo, project_repo, file_repo)
    created = await row_repo.create(
        file_id=f["id"], row_num=0, source="계속하기", target="",
    )
    updated = await row_repo.update(
        created["id"], target="Continue", status="translated",
    )
    assert updated is not None
    assert updated["target"] == "Continue"
    assert updated["status"] == "translated"


async def test_row_delete(row_repo, platform_repo, project_repo, file_repo, db_mode):
    """Create, delete, verify gone."""
    f = await _create_file(platform_repo, project_repo, file_repo)
    created = await row_repo.create(
        file_id=f["id"], row_num=0, source="Temp", target="Temp",
    )
    deleted = await row_repo.delete(created["id"])
    assert deleted is True
    assert await row_repo.get(created["id"]) is None


# =============================================================================
# Bulk Operations
# =============================================================================


async def test_row_bulk_create(row_repo, platform_repo, project_repo, file_repo, db_mode):
    """Bulk create rows with Korean game strings."""
    f = await _create_file(platform_repo, project_repo, file_repo)
    rows = [
        {"row_num": 0, "source": "새 게임", "target": "New Game", "string_id": "NEW_GAME"},
        {"row_num": 1, "source": "계속하기", "target": "Continue", "string_id": "CONTINUE"},
        {"row_num": 2, "source": "설정", "target": "Settings", "string_id": "SETTINGS"},
        {"row_num": 3, "source": "종료", "target": "Quit", "string_id": "QUIT"},
    ]
    count = await row_repo.bulk_create(f["id"], rows)
    assert count == 4

    # Verify they exist
    all_rows = await row_repo.get_all_for_file(f["id"])
    assert len(all_rows) == 4


async def test_row_bulk_update(row_repo, platform_repo, project_repo, file_repo, db_mode):
    """Bulk update multiple rows."""
    f = await _create_file(platform_repo, project_repo, file_repo)
    r1 = await row_repo.create(file_id=f["id"], row_num=0, source="A", target="")
    r2 = await row_repo.create(file_id=f["id"], row_num=1, source="B", target="")

    updates = [
        {"id": r1["id"], "target": "번역 A", "status": "translated"},
        {"id": r2["id"], "target": "번역 B", "status": "translated"},
    ]
    count = await row_repo.bulk_update(updates)
    assert count == 2

    fetched1 = await row_repo.get(r1["id"])
    assert fetched1["target"] == "번역 A"


# =============================================================================
# Query Operations
# =============================================================================


async def test_row_get_for_file(row_repo, platform_repo, project_repo, file_repo, db_mode):
    """Get paginated rows for a file."""
    f = await _create_file(platform_repo, project_repo, file_repo)
    rows = [
        {"row_num": i, "source": f"소스 {i}", "target": f"Target {i}", "string_id": f"STR_{i}"}
        for i in range(5)
    ]
    await row_repo.bulk_create(f["id"], rows)

    result_rows, total = await row_repo.get_for_file(f["id"], page=1, limit=3)
    assert len(result_rows) == 3
    assert total == 5


async def test_row_get_all_for_file(row_repo, platform_repo, project_repo, file_repo, db_mode):
    """Get all rows for a file (no pagination)."""
    f = await _create_file(platform_repo, project_repo, file_repo)
    rows = [
        {"row_num": 0, "source": "새 게임", "target": "New Game", "string_id": "NEW_GAME"},
        {"row_num": 1, "source": "계속하기", "target": "Continue", "string_id": "CONTINUE"},
    ]
    await row_repo.bulk_create(f["id"], rows)
    all_rows = await row_repo.get_all_for_file(f["id"])
    assert len(all_rows) == 2


async def test_row_count_for_file(row_repo, platform_repo, project_repo, file_repo, db_mode):
    """Count rows in a file."""
    f = await _create_file(platform_repo, project_repo, file_repo)
    rows = [
        {"row_num": i, "source": f"S{i}", "target": f"T{i}", "string_id": f"ID_{i}"}
        for i in range(3)
    ]
    await row_repo.bulk_create(f["id"], rows)
    assert await row_repo.count_for_file(f["id"]) == 3


# =============================================================================
# History Operations
# =============================================================================


async def test_row_edit_history(row_repo, platform_repo, project_repo, file_repo, db_mode):
    """Add and retrieve edit history."""
    f = await _create_file(platform_repo, project_repo, file_repo)
    created = await row_repo.create(
        file_id=f["id"], row_num=0,
        source="원본", target="Original",
    )
    await row_repo.add_edit_history(
        row_id=created["id"], user_id=1,
        old_target="Original", new_target="수정됨",
        old_status="pending", new_status="translated",
    )
    history = await row_repo.get_edit_history(created["id"])
    assert isinstance(history, list)
    if db_mode in (DbMode.SERVER_LOCAL, DbMode.OFFLINE):
        # SQLite modes: edit history not supported, returns empty list
        assert len(history) == 0
    else:
        assert len(history) >= 1


# =============================================================================
# Similarity Search
# =============================================================================


async def test_row_suggest_similar(row_repo, platform_repo, project_repo, file_repo, db_mode):
    """suggest_similar returns list (empty in SQLite, uses pg_trgm)."""
    f = await _create_file(platform_repo, project_repo, file_repo)
    await row_repo.create(file_id=f["id"], row_num=0, source="새 게임 시작", target="Start New Game")

    results = await row_repo.suggest_similar(source="새 게임")
    # SQLite returns empty list (pg_trgm not available)
    assert isinstance(results, list)
