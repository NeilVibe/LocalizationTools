"""
Parity tests for FolderRepository across all database modes.

Tests every interface method with parametrized db_mode (online/server_local/offline).
Korean/English game-realistic data used throughout.
"""
from __future__ import annotations

import pytest

pytestmark = [pytest.mark.stability, pytest.mark.asyncio]


# =============================================================================
# Helper: create a project for folder tests
# =============================================================================


async def _create_project(project_repo, name="테스트 프로젝트"):
    """Helper to create a project for folder operations."""
    return await project_repo.create(name=name, owner_id=1)


# =============================================================================
# Core CRUD
# =============================================================================


async def test_folder_create(folder_repo, project_repo, db_mode):
    """Create folder and verify returned dict."""
    proj = await _create_project(project_repo)
    result = await folder_repo.create(name="UI", project_id=proj["id"])
    assert result is not None
    assert result["name"] == "UI"
    assert result["project_id"] == proj["id"]
    assert "id" in result


async def test_folder_create_nested(folder_repo, project_repo, db_mode):
    """Create nested folder (subfolder)."""
    proj = await _create_project(project_repo)
    parent = await folder_repo.create(name="Assets", project_id=proj["id"])
    child = await folder_repo.create(name="텍스트", project_id=proj["id"], parent_id=parent["id"])
    assert child is not None
    assert child["parent_id"] == parent["id"]


async def test_folder_get(folder_repo, project_repo, db_mode):
    """Create then get by ID."""
    proj = await _create_project(project_repo)
    created = await folder_repo.create(name="메뉴", project_id=proj["id"])
    fetched = await folder_repo.get(created["id"])
    assert fetched is not None
    assert fetched["name"] == "메뉴"


async def test_folder_get_nonexistent(folder_repo, db_mode):
    """Get non-existent folder returns None."""
    result = await folder_repo.get(999999)
    assert result is None


async def test_folder_get_all(folder_repo, project_repo, db_mode):
    """Get all folders in a project."""
    proj = await _create_project(project_repo)
    await folder_repo.create(name="UI", project_id=proj["id"])
    await folder_repo.create(name="대화", project_id=proj["id"])  # Korean: Dialogue
    results = await folder_repo.get_all(proj["id"])
    assert len(results) == 2


async def test_folder_delete(folder_repo, project_repo, db_mode):
    """Create, delete, verify gone."""
    proj = await _create_project(project_repo)
    created = await folder_repo.create(name="Temp", project_id=proj["id"])
    deleted = await folder_repo.delete(created["id"])
    assert deleted is True
    assert await folder_repo.get(created["id"]) is None


# =============================================================================
# Folder-Specific Operations
# =============================================================================


async def test_folder_get_with_contents(folder_repo, project_repo, db_mode):
    """Get folder with subfolders and files info."""
    proj = await _create_project(project_repo)
    parent = await folder_repo.create(name="Assets", project_id=proj["id"])
    await folder_repo.create(name="Sub", project_id=proj["id"], parent_id=parent["id"])

    result = await folder_repo.get_with_contents(parent["id"])
    assert result is not None
    assert "subfolders" in result or "name" in result


async def test_folder_rename(folder_repo, project_repo, db_mode):
    """Rename a folder."""
    proj = await _create_project(project_repo)
    created = await folder_repo.create(name="Old", project_id=proj["id"])
    renamed = await folder_repo.rename(created["id"], "새 이름")
    assert renamed is not None
    assert renamed["name"] == "새 이름"


async def test_folder_move(folder_repo, project_repo, db_mode):
    """Move folder to different parent."""
    proj = await _create_project(project_repo)
    parent_a = await folder_repo.create(name="A", project_id=proj["id"])
    child = await folder_repo.create(name="Child", project_id=proj["id"], parent_id=parent_a["id"])
    parent_b = await folder_repo.create(name="B", project_id=proj["id"])

    moved = await folder_repo.move(child["id"], parent_b["id"])
    assert moved is not None
    fetched = await folder_repo.get(child["id"])
    assert fetched["parent_id"] == parent_b["id"]


# =============================================================================
# Query Operations
# =============================================================================


async def test_folder_check_name_exists(folder_repo, project_repo, db_mode):
    """check_name_exists in project scope."""
    proj = await _create_project(project_repo)
    await folder_repo.create(name="UI", project_id=proj["id"])
    assert await folder_repo.check_name_exists("UI", proj["id"]) is True
    assert await folder_repo.check_name_exists("Missing", proj["id"]) is False


async def test_folder_generate_unique_name(folder_repo, project_repo, db_mode):
    """generate_unique_name adds suffix for duplicates."""
    proj = await _create_project(project_repo)
    await folder_repo.create(name="UI", project_id=proj["id"])
    unique = await folder_repo.generate_unique_name("UI", proj["id"])
    assert unique != "UI"
    assert unique.startswith("UI")


async def test_folder_get_children(folder_repo, project_repo, db_mode):
    """Get direct subfolders."""
    proj = await _create_project(project_repo)
    parent = await folder_repo.create(name="Parent", project_id=proj["id"])
    await folder_repo.create(name="Child1", project_id=proj["id"], parent_id=parent["id"])
    await folder_repo.create(name="Child2", project_id=proj["id"], parent_id=parent["id"])

    children = await folder_repo.get_children(parent["id"])
    assert len(children) == 2


async def test_folder_search(folder_repo, project_repo, db_mode):
    """Search folders by name."""
    proj = await _create_project(project_repo)
    await folder_repo.create(name="UI Strings", project_id=proj["id"])
    await folder_repo.create(name="UI Menus", project_id=proj["id"])
    await folder_repo.create(name="Dialogue", project_id=proj["id"])

    results = await folder_repo.search("UI")
    assert len(results) == 2
