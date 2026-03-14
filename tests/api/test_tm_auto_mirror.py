"""
Tests for TM auto-mirror behavior on file upload.

Verifies that uploading a file to a folder automatically creates and assigns
a Translation Memory if none exists for that folder scope.

Uses mocked repositories to test the _auto_mirror_tm helper in isolation,
without needing a running server or database.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_tm_repo():
    """Mock TMRepository with async methods."""
    repo = AsyncMock()
    repo.get_for_scope = AsyncMock(return_value=[])
    repo.create = AsyncMock(return_value={"id": 100, "name": "TM - UI", "source_lang": "ko", "target_lang": "en"})
    repo.assign = AsyncMock(return_value={"id": 100, "assigned_to": "folder"})
    repo.activate = AsyncMock(return_value={"id": 100, "is_active": True})
    return repo


@pytest.fixture
def mock_folder_repo():
    """Mock FolderRepository with async methods."""
    repo = AsyncMock()
    repo.get = AsyncMock(return_value={"id": 1, "name": "UI", "project_id": 10})
    return repo


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestAutoMirrorTM:
    """Test the _auto_mirror_tm helper function."""

    @pytest.mark.asyncio
    async def test_creates_tm_when_none_exists(self, mock_tm_repo, mock_folder_repo):
        """Uploading a file to a folder with no TM creates a TM named 'TM - {folder_name}'."""
        from server.tools.ldm.routes.files import _auto_mirror_tm

        await _auto_mirror_tm(
            folder_id=1,
            project_id=10,
            tm_repo=mock_tm_repo,
            folder_repo=mock_folder_repo,
        )

        # Should check existing TMs for this folder
        mock_tm_repo.get_for_scope.assert_called_once_with(folder_id=1, include_inactive=True)
        # Should create with correct name
        mock_tm_repo.create.assert_called_once()
        call_kwargs = mock_tm_repo.create.call_args
        assert "TM - UI" in str(call_kwargs)
        # Should assign to folder
        mock_tm_repo.assign.assert_called_once()
        # Should activate
        mock_tm_repo.activate.assert_called_once()

    @pytest.mark.asyncio
    async def test_idempotent_no_duplicate_tm(self, mock_tm_repo, mock_folder_repo):
        """Uploading a second file to the same folder does NOT create a duplicate TM."""
        from server.tools.ldm.routes.files import _auto_mirror_tm

        # Simulate existing TM for this folder
        mock_tm_repo.get_for_scope = AsyncMock(return_value=[
            {"id": 50, "name": "TM - UI", "is_active": True}
        ])

        await _auto_mirror_tm(
            folder_id=1,
            project_id=10,
            tm_repo=mock_tm_repo,
            folder_repo=mock_folder_repo,
        )

        # Should NOT create a new TM
        mock_tm_repo.create.assert_not_called()
        mock_tm_repo.assign.assert_not_called()
        mock_tm_repo.activate.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_folder_id_skips(self, mock_tm_repo, mock_folder_repo):
        """If folder_id is None, auto-mirror is silently skipped."""
        from server.tools.ldm.routes.files import _auto_mirror_tm

        await _auto_mirror_tm(
            folder_id=None,
            project_id=10,
            tm_repo=mock_tm_repo,
            folder_repo=mock_folder_repo,
        )

        mock_tm_repo.get_for_scope.assert_not_called()
        mock_tm_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_failure_does_not_raise(self, mock_tm_repo, mock_folder_repo):
        """Auto-mirror failure does NOT block file upload (logs warning only)."""
        from server.tools.ldm.routes.files import _auto_mirror_tm

        mock_tm_repo.get_for_scope = AsyncMock(side_effect=Exception("DB connection lost"))

        # Should not raise
        await _auto_mirror_tm(
            folder_id=1,
            project_id=10,
            tm_repo=mock_tm_repo,
            folder_repo=mock_folder_repo,
        )

    @pytest.mark.asyncio
    async def test_folder_name_used_in_tm_name(self, mock_tm_repo, mock_folder_repo):
        """TM name includes the folder name for easy identification."""
        from server.tools.ldm.routes.files import _auto_mirror_tm

        mock_folder_repo.get = AsyncMock(return_value={"id": 5, "name": "Quests", "project_id": 10})

        await _auto_mirror_tm(
            folder_id=5,
            project_id=10,
            tm_repo=mock_tm_repo,
            folder_repo=mock_folder_repo,
        )

        create_call = mock_tm_repo.create.call_args
        # Verify the name contains "TM - Quests"
        assert create_call is not None
        name_arg = create_call.kwargs.get("name") or create_call.args[0]
        assert name_arg == "TM - Quests"
