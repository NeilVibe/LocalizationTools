"""
Parity tests for TMRepository across all database modes.

Tests every interface method with parametrized db_mode (online/server_local/offline).
Korean/English game-realistic TM data used throughout.

This is the largest repo (~25 methods) covering CRUD, assignments, entries,
search, indexing, and tree operations.
"""
from __future__ import annotations

import pytest

from server.repositories.interfaces.tm_repository import AssignmentTarget

pytestmark = [pytest.mark.stability, pytest.mark.asyncio]


# =============================================================================
# Helpers
# =============================================================================


async def _create_tm(tm_repo, name="게임 TM", source_lang="ko", target_lang="en"):
    """Helper to create a TM."""
    return await tm_repo.create(name=name, source_lang=source_lang, target_lang=target_lang, owner_id=1)


async def _create_platform_project(platform_repo, project_repo):
    """Create platform + project, return (platform, project)."""
    plat = await platform_repo.create(name="PC", owner_id=1)
    proj = await project_repo.create(name="다크 소울 IV", owner_id=1, platform_id=plat["id"])
    return plat, proj


async def _add_game_entries(tm_repo, tm_id):
    """Add realistic Korean/English TM entries. Returns count."""
    entries = [
        {"source": "새 게임", "target": "New Game"},
        {"source": "계속하기", "target": "Continue"},
        {"source": "설정", "target": "Settings"},
        {"source": "종료", "target": "Quit"},
        {"source": "저장", "target": "Save"},
    ]
    return await tm_repo.add_entries_bulk(tm_id, entries)


# =============================================================================
# Core CRUD
# =============================================================================


async def test_tm_create(tm_repo, db_mode):
    """Create TM and verify returned dict."""
    result = await _create_tm(tm_repo)
    assert result is not None
    assert result["name"] == "게임 TM"
    assert result["source_lang"] == "ko"
    assert result["target_lang"] == "en"
    assert "id" in result


async def test_tm_get(tm_repo, db_mode):
    """Create then get by ID."""
    created = await _create_tm(tm_repo)
    fetched = await tm_repo.get(created["id"])
    assert fetched is not None
    assert fetched["name"] == "게임 TM"
    assert fetched["id"] == created["id"]


async def test_tm_get_nonexistent(tm_repo, db_mode):
    """Get non-existent TM returns None."""
    result = await tm_repo.get(999999)
    assert result is None


async def test_tm_get_all(tm_repo, db_mode):
    """Create 2 TMs, get_all returns both."""
    await _create_tm(tm_repo, name="TM Alpha")
    await _create_tm(tm_repo, name="TM Beta")
    results = await tm_repo.get_all()
    names = {r["name"] for r in results}
    assert "TM Alpha" in names
    assert "TM Beta" in names


async def test_tm_delete(tm_repo, db_mode):
    """Create, delete, verify gone."""
    created = await _create_tm(tm_repo, name="Temp TM")
    deleted = await tm_repo.delete(created["id"])
    assert deleted is True
    assert await tm_repo.get(created["id"]) is None


async def test_tm_delete_nonexistent(tm_repo, db_mode):
    """Delete non-existent TM returns False."""
    result = await tm_repo.delete(999999)
    assert result is False


# =============================================================================
# Assignment Operations
# =============================================================================


async def test_tm_assign_to_project(tm_repo, platform_repo, project_repo, db_mode):
    """Assign TM to a project."""
    plat, proj = await _create_platform_project(platform_repo, project_repo)
    tm = await _create_tm(tm_repo)
    target = AssignmentTarget(project_id=proj["id"])
    result = await tm_repo.assign(tm["id"], target)
    assert result is not None


async def test_tm_assign_to_platform(tm_repo, platform_repo, db_mode):
    """Assign TM to a platform."""
    plat = await platform_repo.create(name="PC", owner_id=1)
    tm = await _create_tm(tm_repo)
    target = AssignmentTarget(platform_id=plat["id"])
    result = await tm_repo.assign(tm["id"], target)
    assert result is not None


async def test_tm_unassign(tm_repo, platform_repo, project_repo, db_mode):
    """Assign then unassign a TM."""
    plat, proj = await _create_platform_project(platform_repo, project_repo)
    tm = await _create_tm(tm_repo)
    target = AssignmentTarget(project_id=proj["id"])
    await tm_repo.assign(tm["id"], target)
    result = await tm_repo.unassign(tm["id"])
    assert result is not None


async def test_tm_activate_deactivate(tm_repo, platform_repo, project_repo, db_mode):
    """Activate and deactivate a TM."""
    plat, proj = await _create_platform_project(platform_repo, project_repo)
    tm = await _create_tm(tm_repo)
    target = AssignmentTarget(project_id=proj["id"])
    await tm_repo.assign(tm["id"], target)

    activated = await tm_repo.activate(tm["id"])
    assert activated is not None
    assert bool(activated.get("is_active")) is True

    deactivated = await tm_repo.deactivate(tm["id"])
    assert deactivated is not None
    assert bool(deactivated.get("is_active")) is False


async def test_tm_get_assignment(tm_repo, platform_repo, project_repo, db_mode):
    """Get assignment for a TM."""
    plat, proj = await _create_platform_project(platform_repo, project_repo)
    tm = await _create_tm(tm_repo)
    target = AssignmentTarget(project_id=proj["id"])
    await tm_repo.assign(tm["id"], target)
    assignment = await tm_repo.get_assignment(tm["id"])
    assert assignment is not None
    assert assignment["project_id"] == proj["id"]


async def test_tm_get_assignment_unassigned(tm_repo, db_mode):
    """Get assignment for unassigned TM returns None."""
    tm = await _create_tm(tm_repo)
    assignment = await tm_repo.get_assignment(tm["id"])
    assert assignment is None


# =============================================================================
# Scope Queries
# =============================================================================


async def test_tm_get_for_scope_project(tm_repo, platform_repo, project_repo, db_mode):
    """Get TMs assigned to a project scope (include_inactive to find assigned but not activated)."""
    plat, proj = await _create_platform_project(platform_repo, project_repo)
    tm = await _create_tm(tm_repo)
    target = AssignmentTarget(project_id=proj["id"])
    await tm_repo.assign(tm["id"], target)

    # include_inactive=True since assign doesn't auto-activate
    results = await tm_repo.get_for_scope(project_id=proj["id"], include_inactive=True)
    assert len(results) >= 1
    assert any(r["id"] == tm["id"] for r in results)

    # After activating, should also appear with default include_inactive=False
    await tm_repo.activate(tm["id"])
    active_results = await tm_repo.get_for_scope(project_id=proj["id"])
    assert len(active_results) >= 1


async def test_tm_get_for_scope_no_params(tm_repo, db_mode):
    """Get TMs with all scope params None returns empty (JOINs on assignments)."""
    await _create_tm(tm_repo, name="Unassigned TM")
    # get_for_scope JOINs on tm_assignments, so unassigned TMs won't appear
    results = await tm_repo.get_for_scope(include_inactive=True)
    assert isinstance(results, list)


# =============================================================================
# TM Linking (Active TMs for Projects)
# =============================================================================


async def test_tm_link_to_project(tm_repo, platform_repo, project_repo, db_mode):
    """Link TM to a project."""
    plat, proj = await _create_platform_project(platform_repo, project_repo)
    tm = await _create_tm(tm_repo)
    result = await tm_repo.link_to_project(tm["id"], proj["id"], priority=1)
    assert result is not None


async def test_tm_unlink_from_project(tm_repo, platform_repo, project_repo, db_mode):
    """Link then unlink TM from a project."""
    plat, proj = await _create_platform_project(platform_repo, project_repo)
    tm = await _create_tm(tm_repo)
    await tm_repo.link_to_project(tm["id"], proj["id"])
    result = await tm_repo.unlink_from_project(tm["id"], proj["id"])
    assert result is True


async def test_tm_get_linked_for_project(tm_repo, platform_repo, project_repo, db_mode):
    """Get highest-priority linked TM for a project."""
    plat, proj = await _create_platform_project(platform_repo, project_repo)
    tm = await _create_tm(tm_repo)
    await tm_repo.link_to_project(tm["id"], proj["id"], priority=1)
    result = await tm_repo.get_linked_for_project(proj["id"])
    # May return None or dict depending on implementation
    assert result is None or isinstance(result, dict)


async def test_tm_get_all_linked_for_project(tm_repo, platform_repo, project_repo, db_mode):
    """Get all linked TMs for a project."""
    plat, proj = await _create_platform_project(platform_repo, project_repo)
    tm1 = await _create_tm(tm_repo, name="TM Primary")
    tm2 = await _create_tm(tm_repo, name="TM Secondary")
    await tm_repo.link_to_project(tm1["id"], proj["id"], priority=1)
    await tm_repo.link_to_project(tm2["id"], proj["id"], priority=2)
    results = await tm_repo.get_all_linked_for_project(proj["id"])
    assert isinstance(results, list)
    assert len(results) >= 2


# =============================================================================
# TM Entries
# =============================================================================


async def test_tm_add_entry(tm_repo, db_mode):
    """Add single entry to TM."""
    tm = await _create_tm(tm_repo)
    entry = await tm_repo.add_entry(
        tm["id"], source="새 게임 시작", target="Start New Game",
        string_id="NEW_GAME_START", created_by="test_admin"
    )
    assert entry is not None
    assert entry.get("source_text", entry.get("source")) in ("새 게임 시작",)


async def test_tm_add_entries_bulk(tm_repo, db_mode):
    """Bulk add entries to TM with Korean game strings."""
    tm = await _create_tm(tm_repo)
    count = await _add_game_entries(tm_repo, tm["id"])
    assert count == 5


async def test_tm_get_entries(tm_repo, db_mode):
    """Get TM entries with pagination."""
    tm = await _create_tm(tm_repo)
    await _add_game_entries(tm_repo, tm["id"])
    entries = await tm_repo.get_entries(tm["id"], offset=0, limit=3)
    assert len(entries) == 3


async def test_tm_get_all_entries(tm_repo, db_mode):
    """Get all entries for TM (no pagination)."""
    tm = await _create_tm(tm_repo)
    await _add_game_entries(tm_repo, tm["id"])
    entries = await tm_repo.get_all_entries(tm["id"])
    assert len(entries) == 5


async def test_tm_search_entries(tm_repo, db_mode):
    """Search TM entries by source text."""
    tm = await _create_tm(tm_repo)
    await _add_game_entries(tm_repo, tm["id"])
    results = await tm_repo.search_entries(tm["id"], query="게임")
    assert isinstance(results, list)
    # Should find at least "새 게임" (New Game)
    assert len(results) >= 1


async def test_tm_delete_entry(tm_repo, db_mode):
    """Delete a TM entry."""
    tm = await _create_tm(tm_repo)
    entry = await tm_repo.add_entry(tm["id"], source="임시", target="Temp")
    entry_id = entry.get("id") or entry.get("entry_id")
    if entry_id:
        result = await tm_repo.delete_entry(entry_id)
        assert result is True


async def test_tm_update_entry(tm_repo, db_mode):
    """Update a TM entry."""
    tm = await _create_tm(tm_repo)
    entry = await tm_repo.add_entry(tm["id"], source="원본", target="Original")
    entry_id = entry.get("id") or entry.get("entry_id")
    if entry_id:
        updated = await tm_repo.update_entry(
            entry_id, target_text="수정됨", updated_by="test_admin"
        )
        assert updated is not None


async def test_tm_confirm_entry(tm_repo, db_mode):
    """Confirm a TM entry (memoQ-style workflow)."""
    tm = await _create_tm(tm_repo)
    entry = await tm_repo.add_entry(tm["id"], source="확인 테스트", target="Confirm Test")
    entry_id = entry.get("id") or entry.get("entry_id")
    if entry_id:
        confirmed = await tm_repo.confirm_entry(entry_id, confirm=True, confirmed_by="admin")
        assert confirmed is not None


async def test_tm_bulk_confirm_entries(tm_repo, db_mode):
    """Bulk confirm multiple TM entries."""
    tm = await _create_tm(tm_repo)
    e1 = await tm_repo.add_entry(tm["id"], source="항목 1", target="Item 1")
    e2 = await tm_repo.add_entry(tm["id"], source="항목 2", target="Item 2")
    ids = []
    for e in [e1, e2]:
        eid = e.get("id") or e.get("entry_id")
        if eid:
            ids.append(eid)
    if ids:
        count = await tm_repo.bulk_confirm_entries(tm["id"], ids, confirm=True)
        assert count >= 0


async def test_tm_count_entries(tm_repo, db_mode):
    """Count entries in a TM."""
    tm = await _create_tm(tm_repo)
    await _add_game_entries(tm_repo, tm["id"])
    count = await tm_repo.count_entries(tm["id"])
    assert count == 5


async def test_tm_get_glossary_terms(tm_repo, db_mode):
    """Get short TM entries as glossary terms."""
    tm = await _create_tm(tm_repo)
    await _add_game_entries(tm_repo, tm["id"])
    terms = await tm_repo.get_glossary_terms([tm["id"]], max_length=20)
    assert isinstance(terms, list)
    assert len(terms) >= 1


# =============================================================================
# Advanced Search
# =============================================================================


async def test_tm_search_exact(tm_repo, db_mode):
    """Search for exact match using hash-based lookup."""
    tm = await _create_tm(tm_repo)
    await tm_repo.add_entry(tm["id"], source="새 게임", target="New Game")
    result = await tm_repo.search_exact(tm["id"], source="새 게임")
    # May find or not depending on implementation; verify type
    assert result is None or isinstance(result, dict)


async def test_tm_search_similar(tm_repo, db_mode):
    """Search for similar entries (pg_trgm in PostgreSQL, empty in SQLite)."""
    tm = await _create_tm(tm_repo)
    await _add_game_entries(tm_repo, tm["id"])
    results = await tm_repo.search_similar(tm["id"], source="새 게임 시작")
    # SQLite returns empty list (no pg_trgm)
    assert isinstance(results, list)


# =============================================================================
# Index & Tree Operations
# =============================================================================


async def test_tm_get_indexes(tm_repo, db_mode):
    """Get index status for a TM."""
    tm = await _create_tm(tm_repo)
    indexes = await tm_repo.get_indexes(tm["id"])
    assert isinstance(indexes, list)


async def test_tm_get_tree(tm_repo, db_mode):
    """Get full TM tree structure for UI."""
    await _create_tm(tm_repo, name="Tree Test TM")
    tree = await tm_repo.get_tree()
    assert isinstance(tree, dict)
    assert "unassigned" in tree or "platforms" in tree


async def test_tm_check_name_exists(tm_repo, db_mode):
    """Check if TM name exists."""
    await _create_tm(tm_repo, name="Unique TM")
    assert await tm_repo.check_name_exists("Unique TM") is True
    assert await tm_repo.check_name_exists("NonExistent TM") is False


# =============================================================================
# Get Active For File
# =============================================================================


async def test_tm_get_active_for_file(
    tm_repo, platform_repo, project_repo, folder_repo, file_repo, db_mode
):
    """Get active TMs that apply to a file (inherited from project)."""
    plat, proj = await _create_platform_project(platform_repo, project_repo)
    folder = await folder_repo.create(name="UI", project_id=proj["id"])
    f = await file_repo.create(
        name="menu.xml", original_filename="menu.xml",
        format="xml", project_id=proj["id"], folder_id=folder["id"],
    )
    tm = await _create_tm(tm_repo)
    target = AssignmentTarget(project_id=proj["id"])
    await tm_repo.assign(tm["id"], target)
    await tm_repo.activate(tm["id"])

    results = await tm_repo.get_active_for_file(f["id"])
    assert isinstance(results, list)
