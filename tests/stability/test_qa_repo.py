"""
Parity tests for QAResultRepository across all database modes.

Tests every interface method with parametrized db_mode (online/server_local/offline).
Korean/English game-realistic QA data used throughout.
"""
from __future__ import annotations

import pytest

pytestmark = [pytest.mark.stability, pytest.mark.asyncio]


# =============================================================================
# Helpers
# =============================================================================


async def _create_file_with_rows(platform_repo, project_repo, file_repo, row_repo):
    """Create platform -> project -> file -> rows, return (file, [rows])."""
    plat = await platform_repo.create(name="PC", owner_id=1)
    proj = await project_repo.create(
        name="다크 소울 IV", owner_id=1, platform_id=plat["id"]
    )
    f = await file_repo.create(
        name="menu_strings.xml", original_filename="menu_strings.xml",
        format="xml", project_id=proj["id"],
        source_language="ko", target_language="en",
    )
    r1 = await row_repo.create(
        file_id=f["id"], row_num=0,
        source="새 게임", target="New Game",
        string_id="NEW_GAME", status="pending",
    )
    r2 = await row_repo.create(
        file_id=f["id"], row_num=1,
        source="계속하기", target="Continue",
        string_id="CONTINUE", status="pending",
    )
    return f, [r1, r2]


# =============================================================================
# Core CRUD
# =============================================================================


async def test_qa_create(
    qa_repo, platform_repo, project_repo, file_repo, row_repo, db_mode
):
    """Create a QA result and verify returned dict."""
    f, rows = await _create_file_with_rows(platform_repo, project_repo, file_repo, row_repo)
    result = await qa_repo.create(
        row_id=rows[0]["id"],
        file_id=f["id"],
        check_type="pattern",
        severity="warning",
        message="한국어 패턴 불일치",  # Korean: pattern mismatch
        details={"rule": "length_check", "expected": 10, "actual": 15},
    )
    assert result is not None
    assert result["check_type"] == "pattern"
    assert result["severity"] == "warning"
    assert "id" in result


async def test_qa_get(
    qa_repo, platform_repo, project_repo, file_repo, row_repo, db_mode
):
    """Create then get by ID."""
    f, rows = await _create_file_with_rows(platform_repo, project_repo, file_repo, row_repo)
    created = await qa_repo.create(
        row_id=rows[0]["id"], file_id=f["id"],
        check_type="line", severity="error",
        message="줄 수 불일치",
    )
    fetched = await qa_repo.get(created["id"])
    assert fetched is not None
    assert fetched["check_type"] == "line"


async def test_qa_get_nonexistent(qa_repo, db_mode):
    """Get non-existent QA result returns None."""
    result = await qa_repo.get(999999)
    assert result is None


# =============================================================================
# Query Operations
# =============================================================================


async def test_qa_get_for_row(
    qa_repo, platform_repo, project_repo, file_repo, row_repo, db_mode
):
    """Get QA results for a specific row."""
    f, rows = await _create_file_with_rows(platform_repo, project_repo, file_repo, row_repo)
    await qa_repo.create(
        row_id=rows[0]["id"], file_id=f["id"],
        check_type="pattern", severity="warning", message="Issue A",
    )
    await qa_repo.create(
        row_id=rows[0]["id"], file_id=f["id"],
        check_type="term", severity="error", message="Issue B",
    )
    results = await qa_repo.get_for_row(rows[0]["id"])
    assert len(results) == 2


async def test_qa_get_for_row_exclude_resolved(
    qa_repo, platform_repo, project_repo, file_repo, row_repo, db_mode
):
    """get_for_row excludes resolved issues by default."""
    f, rows = await _create_file_with_rows(platform_repo, project_repo, file_repo, row_repo)
    created = await qa_repo.create(
        row_id=rows[0]["id"], file_id=f["id"],
        check_type="pattern", severity="warning", message="Resolved Issue",
    )
    await qa_repo.resolve(created["id"], resolved_by=1)
    results = await qa_repo.get_for_row(rows[0]["id"], include_resolved=False)
    assert len(results) == 0
    results_all = await qa_repo.get_for_row(rows[0]["id"], include_resolved=True)
    assert len(results_all) == 1


async def test_qa_get_for_file(
    qa_repo, platform_repo, project_repo, file_repo, row_repo, db_mode
):
    """Get QA results for a file with row info."""
    f, rows = await _create_file_with_rows(platform_repo, project_repo, file_repo, row_repo)
    await qa_repo.create(
        row_id=rows[0]["id"], file_id=f["id"],
        check_type="pattern", severity="warning", message="Issue on row 0",
    )
    await qa_repo.create(
        row_id=rows[1]["id"], file_id=f["id"],
        check_type="term", severity="error", message="Issue on row 1",
    )
    results = await qa_repo.get_for_file(f["id"])
    assert len(results) == 2


async def test_qa_get_for_file_with_type_filter(
    qa_repo, platform_repo, project_repo, file_repo, row_repo, db_mode
):
    """Get QA results filtered by check_type."""
    f, rows = await _create_file_with_rows(platform_repo, project_repo, file_repo, row_repo)
    await qa_repo.create(
        row_id=rows[0]["id"], file_id=f["id"],
        check_type="pattern", severity="warning", message="Pattern issue",
    )
    await qa_repo.create(
        row_id=rows[0]["id"], file_id=f["id"],
        check_type="term", severity="error", message="Term issue",
    )
    results = await qa_repo.get_for_file(f["id"], check_type="pattern")
    assert len(results) == 1
    assert results[0]["check_type"] == "pattern"


async def test_qa_get_summary(
    qa_repo, platform_repo, project_repo, file_repo, row_repo, db_mode
):
    """Get QA summary for a file."""
    f, rows = await _create_file_with_rows(platform_repo, project_repo, file_repo, row_repo)
    await qa_repo.create(
        row_id=rows[0]["id"], file_id=f["id"],
        check_type="pattern", severity="warning", message="P1",
    )
    await qa_repo.create(
        row_id=rows[1]["id"], file_id=f["id"],
        check_type="line", severity="error", message="L1",
    )
    summary = await qa_repo.get_summary(f["id"])
    assert summary["total"] == 2
    assert summary["pattern"] == 1
    assert summary["line"] == 1


# =============================================================================
# Write Operations
# =============================================================================


async def test_qa_bulk_create(
    qa_repo, platform_repo, project_repo, file_repo, row_repo, db_mode
):
    """Bulk create QA results."""
    f, rows = await _create_file_with_rows(platform_repo, project_repo, file_repo, row_repo)
    results_data = [
        {"row_id": rows[0]["id"], "file_id": f["id"], "check_type": "pattern",
         "severity": "warning", "message": "Bulk Issue 1"},
        {"row_id": rows[1]["id"], "file_id": f["id"], "check_type": "term",
         "severity": "error", "message": "Bulk Issue 2"},
        {"row_id": rows[0]["id"], "file_id": f["id"], "check_type": "character",
         "severity": "warning", "message": "Bulk Issue 3"},
    ]
    count = await qa_repo.bulk_create(results_data)
    assert count == 3


async def test_qa_resolve(
    qa_repo, platform_repo, project_repo, file_repo, row_repo, db_mode
):
    """Mark a QA result as resolved."""
    f, rows = await _create_file_with_rows(platform_repo, project_repo, file_repo, row_repo)
    created = await qa_repo.create(
        row_id=rows[0]["id"], file_id=f["id"],
        check_type="pattern", severity="warning", message="To resolve",
    )
    resolved = await qa_repo.resolve(created["id"], resolved_by=1)
    assert resolved is not None
    assert resolved.get("resolved_at") is not None


async def test_qa_resolve_nonexistent(qa_repo, db_mode):
    """Resolve non-existent QA result returns None."""
    result = await qa_repo.resolve(999999, resolved_by=1)
    assert result is None


async def test_qa_delete_unresolved_for_row(
    qa_repo, platform_repo, project_repo, file_repo, row_repo, db_mode
):
    """Delete all unresolved QA results for a row."""
    f, rows = await _create_file_with_rows(platform_repo, project_repo, file_repo, row_repo)
    await qa_repo.create(
        row_id=rows[0]["id"], file_id=f["id"],
        check_type="pattern", severity="warning", message="A",
    )
    await qa_repo.create(
        row_id=rows[0]["id"], file_id=f["id"],
        check_type="term", severity="error", message="B",
    )
    count = await qa_repo.delete_unresolved_for_row(rows[0]["id"])
    assert count == 2

    # Verify they're gone
    results = await qa_repo.get_for_row(rows[0]["id"])
    assert len(results) == 0


async def test_qa_delete_for_file(
    qa_repo, platform_repo, project_repo, file_repo, row_repo, db_mode
):
    """Delete all QA results for a file."""
    f, rows = await _create_file_with_rows(platform_repo, project_repo, file_repo, row_repo)
    await qa_repo.create(
        row_id=rows[0]["id"], file_id=f["id"],
        check_type="pattern", severity="warning", message="X",
    )
    await qa_repo.create(
        row_id=rows[1]["id"], file_id=f["id"],
        check_type="line", severity="error", message="Y",
    )
    count = await qa_repo.delete_for_file(f["id"])
    assert count == 2


# =============================================================================
# Utility Operations
# =============================================================================


async def test_qa_count_unresolved_for_row(
    qa_repo, platform_repo, project_repo, file_repo, row_repo, db_mode
):
    """Count unresolved QA issues for a row."""
    f, rows = await _create_file_with_rows(platform_repo, project_repo, file_repo, row_repo)
    await qa_repo.create(
        row_id=rows[0]["id"], file_id=f["id"],
        check_type="pattern", severity="warning", message="Count A",
    )
    await qa_repo.create(
        row_id=rows[0]["id"], file_id=f["id"],
        check_type="term", severity="error", message="Count B",
    )
    count = await qa_repo.count_unresolved_for_row(rows[0]["id"])
    assert count == 2
