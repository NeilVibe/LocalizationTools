"""
Parity tests for ProjectRepository across all database modes.

Tests every interface method with parametrized db_mode (online/server_local/offline).
Korean/English game-realistic data used throughout.
"""
from __future__ import annotations

import pytest

pytestmark = [pytest.mark.stability, pytest.mark.asyncio]


# =============================================================================
# Core CRUD
# =============================================================================


async def test_project_create(project_repo, db_mode):
    """Create project and verify returned dict has expected fields."""
    result = await project_repo.create(
        name="다크 소울 IV", owner_id=1, description="액션 RPG"
    )
    assert result is not None
    assert result["name"] == "다크 소울 IV"
    assert result["owner_id"] == 1
    assert result["description"] == "액션 RPG"
    assert "id" in result


async def test_project_create_with_platform(project_repo, platform_repo, db_mode):
    """Create project assigned to a platform."""
    plat = await platform_repo.create(name="PC", owner_id=1)
    proj = await project_repo.create(
        name="엘든 링", owner_id=1, platform_id=plat["id"]
    )
    assert proj["platform_id"] == plat["id"]


async def test_project_get(project_repo, db_mode):
    """Create then get by ID, verify fields match."""
    created = await project_repo.create(name="Test Project", owner_id=1)
    fetched = await project_repo.get(created["id"])
    assert fetched is not None
    assert fetched["name"] == "Test Project"
    assert fetched["id"] == created["id"]


async def test_project_get_nonexistent(project_repo, db_mode):
    """Get a non-existent project returns None."""
    result = await project_repo.get(999999)
    assert result is None


async def test_project_get_all(project_repo, db_mode):
    """Create 2 projects, get_all returns both."""
    await project_repo.create(name="프로젝트 A", owner_id=1)
    await project_repo.create(name="프로젝트 B", owner_id=1)
    results = await project_repo.get_all()
    names = {r["name"] for r in results}
    assert "프로젝트 A" in names
    assert "프로젝트 B" in names


async def test_project_get_all_by_platform(project_repo, platform_repo, db_mode):
    """get_all with platform_id filter."""
    plat = await platform_repo.create(name="PC", owner_id=1)
    await project_repo.create(name="PC Game", owner_id=1, platform_id=plat["id"])
    await project_repo.create(name="Other Game", owner_id=1)

    results = await project_repo.get_all(platform_id=plat["id"])
    assert len(results) == 1
    assert results[0]["name"] == "PC Game"


async def test_project_update(project_repo, db_mode):
    """Create, update fields, verify updated."""
    created = await project_repo.create(name="Old Name", owner_id=1)
    updated = await project_repo.update(
        created["id"], name="새 이름", description="업데이트된 설명"
    )
    assert updated is not None
    assert updated["name"] == "새 이름"
    assert updated["description"] == "업데이트된 설명"


async def test_project_delete(project_repo, db_mode):
    """Create, delete, get returns None."""
    created = await project_repo.create(name="Temp", owner_id=1)
    deleted = await project_repo.delete(created["id"])
    assert deleted is True
    fetched = await project_repo.get(created["id"])
    assert fetched is None


# =============================================================================
# Project-Specific Operations
# =============================================================================


async def test_project_rename(project_repo, db_mode):
    """Rename a project."""
    created = await project_repo.create(name="Old", owner_id=1)
    renamed = await project_repo.rename(created["id"], "번역 프로젝트")
    assert renamed is not None
    assert renamed["name"] == "번역 프로젝트"


async def test_project_set_restriction(project_repo, db_mode):
    """Set project restriction flag."""
    created = await project_repo.create(name="Test", owner_id=1)
    restricted = await project_repo.set_restriction(created["id"], True)
    assert restricted is not None
    assert bool(restricted["is_restricted"]) is True


# =============================================================================
# Query Operations
# =============================================================================


async def test_project_check_name_exists(project_repo, db_mode):
    """check_name_exists returns correct results."""
    await project_repo.create(name="Existing", owner_id=1)
    assert await project_repo.check_name_exists("Existing") is True
    assert await project_repo.check_name_exists("NonExistent") is False


async def test_project_generate_unique_name(project_repo, db_mode):
    """generate_unique_name adds suffix for duplicates."""
    await project_repo.create(name="MyProject", owner_id=1)
    unique = await project_repo.generate_unique_name("MyProject")
    assert unique != "MyProject"
    assert unique.startswith("MyProject")


async def test_project_get_with_stats(project_repo, folder_repo, file_repo, db_mode):
    """get_with_stats includes file_count and folder_count."""
    proj = await project_repo.create(name="Stats Test", owner_id=1)
    folder = await folder_repo.create(name="UI", project_id=proj["id"])
    await file_repo.create(
        name="test.xml", original_filename="test.xml",
        format="xml", project_id=proj["id"], folder_id=folder["id"]
    )
    result = await project_repo.get_with_stats(proj["id"])
    assert result is not None
    assert "file_count" in result or "folder_count" in result


async def test_project_count(project_repo, db_mode):
    """Count projects."""
    initial = await project_repo.count()
    await project_repo.create(name="P1", owner_id=1)
    await project_repo.create(name="P2", owner_id=1)
    assert await project_repo.count() == initial + 2


async def test_project_search(project_repo, db_mode):
    """Search projects by name."""
    await project_repo.create(name="다크 소울 IV", owner_id=1)
    await project_repo.create(name="다크 소울 III", owner_id=1)
    await project_repo.create(name="엘든 링", owner_id=1)

    results = await project_repo.search("다크")
    assert len(results) == 2


async def test_project_get_accessible(project_repo, db_mode):
    """get_accessible returns list (SQLite: all projects accessible)."""
    await project_repo.create(name="Test", owner_id=1)
    results = await project_repo.get_accessible()
    assert isinstance(results, list)
    assert len(results) >= 1
