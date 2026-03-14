"""
Parity tests for PlatformRepository across all database modes.

Tests every interface method with parametrized db_mode (online/server_local/offline).
Korean/English game-realistic data used throughout.
"""
from __future__ import annotations

import pytest

pytestmark = [pytest.mark.stability, pytest.mark.asyncio]


# =============================================================================
# Core CRUD
# =============================================================================


async def test_platform_create(platform_repo, db_mode):
    """Create platform and verify returned dict has expected fields."""
    result = await platform_repo.create(name="PC", owner_id=1, description="PC Platform")
    assert result is not None
    assert result["name"] == "PC"
    assert result["owner_id"] == 1
    assert result["description"] == "PC Platform"
    assert "id" in result


async def test_platform_get(platform_repo, db_mode):
    """Create then get by ID, verify fields match."""
    created = await platform_repo.create(name="Console", owner_id=1)
    fetched = await platform_repo.get(created["id"])
    assert fetched is not None
    assert fetched["name"] == "Console"
    assert fetched["id"] == created["id"]


async def test_platform_get_nonexistent(platform_repo, db_mode):
    """Get a non-existent platform returns None."""
    result = await platform_repo.get(999999)
    assert result is None


async def test_platform_get_all(platform_repo, db_mode):
    """Create 2 platforms, get_all returns both."""
    await platform_repo.create(name="PC", owner_id=1)
    await platform_repo.create(name="Console", owner_id=1)
    results = await platform_repo.get_all()
    names = {r["name"] for r in results}
    assert "PC" in names
    assert "Console" in names
    assert len(results) >= 2


async def test_platform_update(platform_repo, db_mode):
    """Create, update name, verify updated."""
    created = await platform_repo.create(name="PC", owner_id=1)
    updated = await platform_repo.update(created["id"], name="콘솔")  # Korean: Console
    assert updated is not None
    assert updated["name"] == "콘솔"


async def test_platform_update_nonexistent(platform_repo, db_mode):
    """Update non-existent platform returns None."""
    result = await platform_repo.update(999999, name="Ghost")
    assert result is None


async def test_platform_delete(platform_repo, db_mode):
    """Create, delete, get returns None."""
    created = await platform_repo.create(name="Temp", owner_id=1)
    deleted = await platform_repo.delete(created["id"])
    assert deleted is True
    fetched = await platform_repo.get(created["id"])
    assert fetched is None


async def test_platform_delete_nonexistent(platform_repo, db_mode):
    """Delete non-existent platform returns False."""
    result = await platform_repo.delete(999999)
    assert result is False


# =============================================================================
# Platform-Specific Operations
# =============================================================================


async def test_platform_get_with_project_count(platform_repo, project_repo, db_mode):
    """Create platform + project, verify count=1."""
    plat = await platform_repo.create(name="PC", owner_id=1)
    await project_repo.create(name="다크 소울 IV", owner_id=1, platform_id=plat["id"])
    result = await platform_repo.get_with_project_count(plat["id"])
    assert result is not None
    assert result["project_count"] == 1


async def test_platform_set_restriction(platform_repo, db_mode):
    """Create, restrict, verify is_restricted=True."""
    created = await platform_repo.create(name="PC", owner_id=1)
    assert created["is_restricted"] is False or created["is_restricted"] == 0

    restricted = await platform_repo.set_restriction(created["id"], True)
    assert restricted is not None
    assert bool(restricted["is_restricted"]) is True

    unrestricted = await platform_repo.set_restriction(created["id"], False)
    assert bool(unrestricted["is_restricted"]) is False


async def test_platform_assign_project(platform_repo, project_repo, db_mode):
    """Assign and unassign a project to a platform."""
    plat = await platform_repo.create(name="PC", owner_id=1)
    proj = await project_repo.create(name="게임 프로젝트", owner_id=1)

    # Assign
    result = await platform_repo.assign_project(proj["id"], plat["id"])
    assert result is True

    # Verify
    projects = await platform_repo.get_projects(plat["id"])
    assert len(projects) == 1
    assert projects[0]["name"] == "게임 프로젝트"

    # Unassign
    result = await platform_repo.assign_project(proj["id"], None)
    assert result is True
    projects = await platform_repo.get_projects(plat["id"])
    assert len(projects) == 0


# =============================================================================
# Query Operations
# =============================================================================


async def test_platform_check_name_exists(platform_repo, db_mode):
    """check_name_exists returns True for existing, False for non-existing."""
    await platform_repo.create(name="PC", owner_id=1)
    assert await platform_repo.check_name_exists("PC") is True
    assert await platform_repo.check_name_exists("Xbox") is False


async def test_platform_check_name_exists_exclude(platform_repo, db_mode):
    """check_name_exists with exclude_id excludes the given platform."""
    created = await platform_repo.create(name="PC", owner_id=1)
    # Should be False when excluding itself
    assert await platform_repo.check_name_exists("PC", exclude_id=created["id"]) is False


async def test_platform_count(platform_repo, db_mode):
    """Count returns correct number after creating platforms."""
    initial = await platform_repo.count()
    await platform_repo.create(name="PC", owner_id=1)
    await platform_repo.create(name="모바일", owner_id=1)  # Korean: Mobile
    await platform_repo.create(name="콘솔", owner_id=1)  # Korean: Console
    assert await platform_repo.count() == initial + 3


async def test_platform_get_projects(platform_repo, project_repo, db_mode):
    """Create platform + 2 projects, verify list."""
    plat = await platform_repo.create(name="PC", owner_id=1)
    await project_repo.create(name="프로젝트 A", owner_id=1, platform_id=plat["id"])
    await project_repo.create(name="프로젝트 B", owner_id=1, platform_id=plat["id"])
    projects = await platform_repo.get_projects(plat["id"])
    assert len(projects) == 2
    names = {p["name"] for p in projects}
    assert "프로젝트 A" in names
    assert "프로젝트 B" in names


async def test_platform_search(platform_repo, db_mode):
    """Search platforms by name substring."""
    await platform_repo.create(name="PC Gaming", owner_id=1)
    await platform_repo.create(name="Console", owner_id=1)
    await platform_repo.create(name="PC VR", owner_id=1)

    results = await platform_repo.search("PC")
    assert len(results) == 2
    names = {r["name"] for r in results}
    assert "PC Gaming" in names
    assert "PC VR" in names


async def test_platform_get_accessible(platform_repo, db_mode):
    """get_accessible returns list (in SQLite modes, all platforms are accessible)."""
    await platform_repo.create(name="PC", owner_id=1)
    await platform_repo.create(name="Mobile", owner_id=1)
    results = await platform_repo.get_accessible()
    assert isinstance(results, list)
    assert len(results) >= 2


async def test_platform_get_accessible_with_projects(platform_repo, project_repo, db_mode):
    """get_accessible with include_projects adds project_count."""
    plat = await platform_repo.create(name="PC", owner_id=1)
    await project_repo.create(name="Test Project", owner_id=1, platform_id=plat["id"])
    results = await platform_repo.get_accessible(include_projects=True)
    pc_platform = next(r for r in results if r["name"] == "PC")
    assert pc_platform["project_count"] == 1


async def test_platform_create_duplicate_name_raises(platform_repo, db_mode):
    """Creating a platform with duplicate name raises ValueError."""
    await platform_repo.create(name="PC", owner_id=1)
    with pytest.raises(ValueError, match="already exists"):
        await platform_repo.create(name="PC", owner_id=1)
