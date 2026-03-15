"""
Unit tests for QA inline badge data contract.

P16-02: Tests verify the data contract that QAInlineBadge depends on:
- GET /api/ldm/rows/{rowId}/qa-results returns correct structure
- Severity field values are valid
- Check_type field values are valid
- Resolve endpoint sets resolved_at
- Resolved issues are not recreated on re-run
"""

from __future__ import annotations

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient

from server.tools.ldm.routes.qa import _run_qa_checks
from server.main import app as wrapped_app
from server.utils.dependencies import get_current_active_user_async
from server.repositories.factory import (
    get_qa_repository,
    get_row_repository,
    get_tm_repository,
    get_file_repository,
)

# Get FastAPI app from Socket.IO wrapper
fastapi_app = wrapped_app.other_asgi_app


def make_row_dict(id=1, file_id=1, row_num=1, source="", target="", **kwargs):
    """Create a row dict matching Repository Pattern output."""
    return {
        "id": id,
        "file_id": file_id,
        "row_num": row_num,
        "source": source,
        "target": target,
        "status": kwargs.get("status", "pending"),
        "string_id": kwargs.get("string_id"),
        "created_at": datetime(2025, 1, 1).isoformat(),
        "updated_at": datetime(2025, 1, 1).isoformat(),
    }


# =============================================================================
# QA Results Data Contract (what QAInlineBadge expects)
# =============================================================================

class TestQAResultsDataContract:
    """Test that GET /rows/{rowId}/qa-results returns the structure QAInlineBadge needs."""

    @pytest.fixture
    def mock_repos(self):
        """Create mock repositories with QA results."""
        qa_repo = MagicMock()
        row_repo = MagicMock()
        file_repo = MagicMock()
        tm_repo = MagicMock()

        return {
            "qa_repo": qa_repo,
            "row_repo": row_repo,
            "file_repo": file_repo,
            "tm_repo": tm_repo,
        }

    @pytest.fixture
    def client_with_repos(self, mock_repos):
        """TestClient with mocked repositories."""
        async def override_get_user():
            return MagicMock(user_id=1, username="testuser")

        fastapi_app.dependency_overrides[get_current_active_user_async] = override_get_user
        fastapi_app.dependency_overrides[get_qa_repository] = lambda: mock_repos["qa_repo"]
        fastapi_app.dependency_overrides[get_row_repository] = lambda: mock_repos["row_repo"]
        fastapi_app.dependency_overrides[get_tm_repository] = lambda: mock_repos["tm_repo"]
        fastapi_app.dependency_overrides[get_file_repository] = lambda: mock_repos["file_repo"]

        client = TestClient(wrapped_app)
        yield client, mock_repos

        fastapi_app.dependency_overrides.clear()

    def test_qa_results_returns_required_fields(self, client_with_repos):
        """GET /rows/{rowId}/qa-results must return objects with id, row_id, check_type, severity, message."""
        client, repos = client_with_repos

        # Mock QA results with all required fields
        repos["qa_repo"].get_for_row = AsyncMock(return_value=[
            {
                "id": 1,
                "row_id": 42,
                "check_type": "term",
                "severity": "warning",
                "message": "Missing term 'Attack' for source",
                "details": {"glossary_source": "src", "glossary_target": "Attack"},
                "created_at": "2025-01-01T00:00:00",
                "resolved_at": None,
            },
            {
                "id": 2,
                "row_id": 42,
                "check_type": "pattern",
                "severity": "error",
                "message": "Missing patterns: {0}",
                "details": None,
                "created_at": "2025-01-01T00:00:00",
                "resolved_at": None,
            }
        ])

        response = client.get("/api/ldm/rows/42/qa-results")
        assert response.status_code == 200

        data = response.json()
        assert "issues" in data
        assert len(data["issues"]) == 2

        for issue in data["issues"]:
            # Required fields for QAInlineBadge
            assert "id" in issue
            assert "check_type" in issue
            assert "severity" in issue
            assert "message" in issue

    def test_severity_values_are_valid(self, client_with_repos):
        """Severity field must be one of: error, warning, info."""
        client, repos = client_with_repos

        repos["qa_repo"].get_for_row = AsyncMock(return_value=[
            {
                "id": 1, "row_id": 1, "check_type": "pattern",
                "severity": "error", "message": "Test error",
                "details": None, "created_at": "2025-01-01T00:00:00", "resolved_at": None,
            },
            {
                "id": 2, "row_id": 1, "check_type": "term",
                "severity": "warning", "message": "Test warning",
                "details": None, "created_at": "2025-01-01T00:00:00", "resolved_at": None,
            },
        ])

        response = client.get("/api/ldm/rows/1/qa-results")
        assert response.status_code == 200

        data = response.json()
        valid_severities = {"error", "warning", "info"}
        for issue in data["issues"]:
            assert issue["severity"] in valid_severities, \
                f"Invalid severity: {issue['severity']}"

    def test_check_type_values_are_valid(self, client_with_repos):
        """Check_type field must be one of: pattern, line, term."""
        client, repos = client_with_repos

        repos["qa_repo"].get_for_row = AsyncMock(return_value=[
            {
                "id": 1, "row_id": 1, "check_type": "pattern",
                "severity": "error", "message": "Test",
                "details": None, "created_at": "2025-01-01T00:00:00", "resolved_at": None,
            },
            {
                "id": 2, "row_id": 1, "check_type": "line",
                "severity": "warning", "message": "Test",
                "details": None, "created_at": "2025-01-01T00:00:00", "resolved_at": None,
            },
            {
                "id": 3, "row_id": 1, "check_type": "term",
                "severity": "warning", "message": "Test",
                "details": None, "created_at": "2025-01-01T00:00:00", "resolved_at": None,
            },
        ])

        response = client.get("/api/ldm/rows/1/qa-results")
        assert response.status_code == 200

        data = response.json()
        valid_types = {"pattern", "line", "term", "character", "grammar"}
        for issue in data["issues"]:
            assert issue["check_type"] in valid_types, \
                f"Invalid check_type: {issue['check_type']}"

    def test_resolve_endpoint_returns_success(self, client_with_repos):
        """POST /qa-results/{id}/resolve should return resolved status."""
        client, repos = client_with_repos

        # Mock unresolved QA result
        repos["qa_repo"].get = AsyncMock(return_value={
            "id": 1,
            "row_id": 1,
            "check_type": "term",
            "severity": "warning",
            "message": "Missing term",
            "resolved_at": None,
        })
        repos["qa_repo"].resolve = AsyncMock(return_value=True)

        response = client.post("/api/ldm/qa-results/1/resolve")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "resolved"
        assert data["result_id"] == 1

        # Verify resolve was called
        repos["qa_repo"].resolve.assert_called_once()

    def test_resolve_already_resolved_returns_400(self, client_with_repos):
        """Resolving an already-resolved issue should return 400."""
        client, repos = client_with_repos

        repos["qa_repo"].get = AsyncMock(return_value={
            "id": 1,
            "row_id": 1,
            "check_type": "term",
            "severity": "warning",
            "message": "Missing term",
            "resolved_at": "2025-06-01T00:00:00",
        })

        response = client.post("/api/ldm/qa-results/1/resolve")
        assert response.status_code == 400


# =============================================================================
# Severity Assignment Tests (verify _run_qa_checks assigns correct severity)
# =============================================================================

class TestSeverityAssignment:
    """Test that QA checks assign correct severity levels."""

    @pytest.mark.asyncio
    async def test_pattern_check_assigns_error_severity(self):
        """Pattern check issues should be severity 'error'."""
        row = make_row_dict(source="{0} test", target="test only")
        issues = await _run_qa_checks(row, ["pattern"], None, None)
        assert len(issues) >= 1
        assert all(i["severity"] == "error" for i in issues if i["check_type"] == "pattern")

    @pytest.mark.asyncio
    async def test_line_check_assigns_warning_severity(self):
        """Line check issues should be severity 'warning'."""
        row1 = make_row_dict(id=1, source="hello", target="bonjour")
        row2 = make_row_dict(id=2, row_num=2, source="hello", target="salut")
        issues = await _run_qa_checks(row1, ["line"], [row1, row2], None)
        assert len(issues) >= 1
        assert all(i["severity"] == "warning" for i in issues if i["check_type"] == "line")

    @pytest.mark.asyncio
    async def test_term_check_assigns_warning_severity(self):
        """Term check issues should be severity 'warning'."""
        row = make_row_dict(source="Iron Sword is good", target="C'est bon")
        glossary = [("Iron Sword", "Epee de fer")]
        issues = await _run_qa_checks(row, ["term"], None, glossary)
        assert len(issues) >= 1
        assert all(i["severity"] == "warning" for i in issues if i["check_type"] == "term")


# =============================================================================
# Re-run Preserves Resolved Issues
# =============================================================================

class TestResolvedIssuesPersistence:
    """Test that resolved issues are preserved across QA re-runs."""

    @pytest.fixture
    def mock_repos_for_rerun(self):
        """Create mock repositories for re-run testing."""
        qa_repo = MagicMock()
        row_repo = MagicMock()
        file_repo = MagicMock()
        tm_repo = MagicMock()

        return {
            "qa_repo": qa_repo,
            "row_repo": row_repo,
            "file_repo": file_repo,
            "tm_repo": tm_repo,
        }

    @pytest.fixture
    def client_for_rerun(self, mock_repos_for_rerun):
        """TestClient for re-run testing."""
        async def override_get_user():
            return MagicMock(user_id=1, username="testuser")

        fastapi_app.dependency_overrides[get_current_active_user_async] = override_get_user
        fastapi_app.dependency_overrides[get_qa_repository] = lambda: mock_repos_for_rerun["qa_repo"]
        fastapi_app.dependency_overrides[get_row_repository] = lambda: mock_repos_for_rerun["row_repo"]
        fastapi_app.dependency_overrides[get_tm_repository] = lambda: mock_repos_for_rerun["tm_repo"]
        fastapi_app.dependency_overrides[get_file_repository] = lambda: mock_repos_for_rerun["file_repo"]

        client = TestClient(wrapped_app)
        yield client, mock_repos_for_rerun

        fastapi_app.dependency_overrides.clear()

    def test_delete_unresolved_preserves_resolved(self, client_for_rerun):
        """Re-running QA should only delete unresolved issues (resolved persist)."""
        client, repos = client_for_rerun

        # Setup: file exists, row with source+target
        repos["file_repo"].get = AsyncMock(return_value={"id": 1, "name": "test.xml"})
        repos["row_repo"].get_all_for_file = AsyncMock(return_value=[
            make_row_dict(id=1, file_id=1, source="{0} test", target="test only")
        ])
        repos["tm_repo"].get_active_for_file = AsyncMock(return_value=[])
        repos["qa_repo"].delete_unresolved_for_row = AsyncMock()
        repos["qa_repo"].bulk_create = AsyncMock()
        repos["qa_repo"].get_for_row = AsyncMock(return_value=[
            {
                "id": 10, "row_id": 1, "file_id": 1, "check_type": "pattern",
                "severity": "error", "message": "Missing patterns: {0}",
                "details": None, "created_at": "2025-01-01T00:00:00", "resolved_at": None,
            }
        ])

        # Run file QA
        response = client.post("/api/ldm/files/1/check-qa", json={
            "checks": ["pattern"],
            "force": True
        })
        assert response.status_code == 200

        # Verify delete_unresolved_for_row was called (NOT delete_all)
        repos["qa_repo"].delete_unresolved_for_row.assert_called()
