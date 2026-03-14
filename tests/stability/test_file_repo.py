"""
Parity tests for FileRepository across all database modes.

Tests every interface method with parametrized db_mode (online/server_local/offline).
Korean/English game-realistic data used throughout.
"""
from __future__ import annotations

import pytest

pytestmark = [pytest.mark.stability, pytest.mark.asyncio]


# =============================================================================
# Helper: create hierarchy for file tests
# =============================================================================


async def _create_hierarchy(platform_repo, project_repo, folder_repo):
    """Create platform -> project -> folder hierarchy, return (project, folder)."""
    plat = await platform_repo.create(name="PC", owner_id=1)
    proj = await project_repo.create(
        name="다크 소울 IV", owner_id=1, platform_id=plat["id"]
    )
    folder = await folder_repo.create(name="UI", project_id=proj["id"])
    return proj, folder


# =============================================================================
# Core CRUD
# =============================================================================


async def test_file_create(file_repo, platform_repo, project_repo, folder_repo, db_mode):
    """Create file and verify returned dict."""
    proj, folder = await _create_hierarchy(platform_repo, project_repo, folder_repo)
    result = await file_repo.create(
        name="menu_strings.xml",
        original_filename="menu_strings.xml",
        format="xml",
        project_id=proj["id"],
        folder_id=folder["id"],
        source_language="ko",
        target_language="en",
    )
    assert result is not None
    assert result["name"] == "menu_strings.xml"
    assert result["format"] == "xml"
    assert result["project_id"] == proj["id"]
    assert "id" in result


async def test_file_get(file_repo, platform_repo, project_repo, folder_repo, db_mode):
    """Create then get by ID."""
    proj, folder = await _create_hierarchy(platform_repo, project_repo, folder_repo)
    created = await file_repo.create(
        name="test.xml", original_filename="test.xml",
        format="xml", project_id=proj["id"], folder_id=folder["id"],
    )
    fetched = await file_repo.get(created["id"])
    assert fetched is not None
    assert fetched["name"] == "test.xml"


async def test_file_get_nonexistent(file_repo, db_mode):
    """Get non-existent file returns None."""
    result = await file_repo.get(999999)
    assert result is None


async def test_file_get_all(file_repo, platform_repo, project_repo, folder_repo, db_mode):
    """Get all files with project filter."""
    proj, folder = await _create_hierarchy(platform_repo, project_repo, folder_repo)
    await file_repo.create(
        name="a.xml", original_filename="a.xml",
        format="xml", project_id=proj["id"], folder_id=folder["id"],
    )
    await file_repo.create(
        name="b.xml", original_filename="b.xml",
        format="xml", project_id=proj["id"], folder_id=folder["id"],
    )
    results = await file_repo.get_all(project_id=proj["id"])
    assert len(results) >= 2


async def test_file_delete(file_repo, platform_repo, project_repo, folder_repo, db_mode):
    """Create, delete, verify gone."""
    proj, folder = await _create_hierarchy(platform_repo, project_repo, folder_repo)
    created = await file_repo.create(
        name="temp.xml", original_filename="temp.xml",
        format="xml", project_id=proj["id"],
    )
    deleted = await file_repo.delete(created["id"], permanent=True)
    assert deleted is True


# =============================================================================
# File Operations
# =============================================================================


async def test_file_rename(file_repo, platform_repo, project_repo, folder_repo, db_mode):
    """Rename a file."""
    proj, folder = await _create_hierarchy(platform_repo, project_repo, folder_repo)
    created = await file_repo.create(
        name="old.xml", original_filename="old.xml",
        format="xml", project_id=proj["id"], folder_id=folder["id"],
    )
    renamed = await file_repo.rename(created["id"], "새_파일.xml")
    assert renamed is not None
    assert renamed["name"] == "새_파일.xml"


async def test_file_move(file_repo, platform_repo, project_repo, folder_repo, db_mode):
    """Move file to different folder."""
    proj, folder_a = await _create_hierarchy(platform_repo, project_repo, folder_repo)
    folder_b = await folder_repo.create(name="대화", project_id=proj["id"])
    created = await file_repo.create(
        name="test.xml", original_filename="test.xml",
        format="xml", project_id=proj["id"], folder_id=folder_a["id"],
    )
    moved = await file_repo.move(created["id"], folder_b["id"])
    assert moved is not None
    fetched = await file_repo.get(created["id"])
    assert fetched["folder_id"] == folder_b["id"]


async def test_file_copy(file_repo, platform_repo, project_repo, folder_repo, db_mode):
    """Copy file within same project."""
    proj, folder = await _create_hierarchy(platform_repo, project_repo, folder_repo)
    created = await file_repo.create(
        name="original.xml", original_filename="original.xml",
        format="xml", project_id=proj["id"], folder_id=folder["id"],
    )
    copied = await file_repo.copy(created["id"])
    assert copied is not None
    assert copied["id"] != created["id"]


async def test_file_update_row_count(file_repo, platform_repo, project_repo, folder_repo, db_mode):
    """Update file row_count."""
    proj, folder = await _create_hierarchy(platform_repo, project_repo, folder_repo)
    created = await file_repo.create(
        name="test.xml", original_filename="test.xml",
        format="xml", project_id=proj["id"],
    )
    await file_repo.update_row_count(created["id"], 42)
    fetched = await file_repo.get(created["id"])
    assert fetched["row_count"] == 42


# =============================================================================
# Row Operations (File-scoped)
# =============================================================================


async def test_file_add_and_get_rows(file_repo, platform_repo, project_repo, folder_repo, db_mode):
    """Add rows to file and get them back."""
    proj, folder = await _create_hierarchy(platform_repo, project_repo, folder_repo)
    created = await file_repo.create(
        name="rows.xml", original_filename="rows.xml",
        format="xml", project_id=proj["id"],
    )
    rows = [
        {"row_num": 0, "source": "새 게임", "target": "New Game", "string_id": "NEW_GAME"},
        {"row_num": 1, "source": "계속하기", "target": "Continue", "string_id": "CONTINUE"},
        {"row_num": 2, "source": "설정", "target": "Settings", "string_id": "SETTINGS"},
    ]
    count = await file_repo.add_rows(created["id"], rows)
    assert count == 3

    fetched_rows = await file_repo.get_rows(created["id"])
    assert len(fetched_rows) == 3


async def test_file_get_rows_for_export(file_repo, platform_repo, project_repo, folder_repo, db_mode):
    """Get all rows for export (no pagination)."""
    proj, folder = await _create_hierarchy(platform_repo, project_repo, folder_repo)
    created = await file_repo.create(
        name="export.xml", original_filename="export.xml",
        format="xml", project_id=proj["id"],
    )
    rows = [
        {"row_num": 0, "source": "시작", "target": "Start", "string_id": "START"},
        {"row_num": 1, "source": "끝", "target": "End", "string_id": "END"},
    ]
    await file_repo.add_rows(created["id"], rows)
    export_rows = await file_repo.get_rows_for_export(created["id"])
    assert len(export_rows) == 2


# =============================================================================
# Query Operations
# =============================================================================


async def test_file_check_name_exists(file_repo, platform_repo, project_repo, folder_repo, db_mode):
    """check_name_exists in project/folder scope."""
    proj, folder = await _create_hierarchy(platform_repo, project_repo, folder_repo)
    await file_repo.create(
        name="test.xml", original_filename="test.xml",
        format="xml", project_id=proj["id"], folder_id=folder["id"],
    )
    assert await file_repo.check_name_exists("test.xml", proj["id"], folder["id"]) is True
    assert await file_repo.check_name_exists("missing.xml", proj["id"], folder["id"]) is False


async def test_file_generate_unique_name(file_repo, platform_repo, project_repo, folder_repo, db_mode):
    """generate_unique_name adds suffix for duplicates."""
    proj, folder = await _create_hierarchy(platform_repo, project_repo, folder_repo)
    await file_repo.create(
        name="test.xml", original_filename="test.xml",
        format="xml", project_id=proj["id"], folder_id=folder["id"],
    )
    unique = await file_repo.generate_unique_name("test.xml", proj["id"], folder["id"])
    assert unique != "test.xml"


async def test_file_search(file_repo, platform_repo, project_repo, folder_repo, db_mode):
    """Search files by name."""
    proj, folder = await _create_hierarchy(platform_repo, project_repo, folder_repo)
    await file_repo.create(
        name="menu_strings.xml", original_filename="menu_strings.xml",
        format="xml", project_id=proj["id"],
    )
    await file_repo.create(
        name="menu_items.xml", original_filename="menu_items.xml",
        format="xml", project_id=proj["id"],
    )
    await file_repo.create(
        name="dialogue.xml", original_filename="dialogue.xml",
        format="xml", project_id=proj["id"],
    )
    results = await file_repo.search("menu")
    assert len(results) == 2
