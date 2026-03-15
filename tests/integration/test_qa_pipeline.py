"""
Integration tests for the full QA pipeline.

P16-02: Tests the complete QA workflow:
- Term Check flags glossary terms present in source but missing in target
- Line Check flags inconsistent translations for same source
- Summary counts are correct
- Resolve/dismiss works end-to-end
- Resolved issues persist across re-runs

Uses mock repositories to test the full pipeline without a database.
"""

from __future__ import annotations

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient

from server.tools.ldm.routes.qa import (
    _run_qa_checks,
    _build_line_check_index,
    _build_term_automaton,
    _apply_noise_filter,
    _save_qa_results,
)
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


def make_row(id=1, file_id=1, row_num=1, source="", target="", **kwargs):
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
        "qa_checked_at": kwargs.get("qa_checked_at"),
    }


# =============================================================================
# Full Term Check Pipeline
# =============================================================================

class TestTermCheckPipeline:
    """Test Term Check end-to-end: glossary terms in source missing from target."""

    @pytest.mark.asyncio
    async def test_term_check_flags_missing_glossary_term(self):
        """Term Check should flag when glossary source is in row source but target translation is missing."""
        # Game data row: source has "Iron Sword", target missing translation
        row = make_row(
            source="The Iron Sword of the Ancient",
            target="L'epee ancienne"  # Missing "Iron Sword" -> "Epee de fer"
        )
        glossary = [("Iron Sword", "Epee de fer"), ("Ancient", "Ancien")]

        issues = await _run_qa_checks(row, ["term"], None, glossary)
        term_issues = [i for i in issues if i["check_type"] == "term"]

        # Should flag "Iron Sword" missing
        assert len(term_issues) >= 1
        flagged_terms = [i["details"]["glossary_source"] for i in term_issues]
        assert "Iron Sword" in flagged_terms

    @pytest.mark.asyncio
    async def test_term_check_uses_aho_corasick_automaton(self):
        """Term Check with pre-built AC automaton should produce same results."""
        row = make_row(
            source="Dragon Scale armor",
            target="Armure en ecailles"  # Missing "Dragon Scale" -> "Ecaille de dragon"
        )
        glossary = [("Dragon Scale", "Ecaille de dragon")]
        automaton, term_map = _build_term_automaton(glossary)

        issues = await _run_qa_checks(
            row, ["term"], None, glossary,
            term_automaton=automaton, term_map=term_map
        )
        term_issues = [i for i in issues if i["check_type"] == "term"]
        assert len(term_issues) >= 1
        assert "Ecaille de dragon" in term_issues[0]["message"]

    @pytest.mark.asyncio
    async def test_term_check_passes_when_translation_present(self):
        """Term Check should NOT flag when glossary term is correctly translated."""
        row = make_row(
            source="Iron Sword of power",
            target="Epee de fer du pouvoir"  # Contains "Epee de fer"
        )
        glossary = [("Iron Sword", "Epee de fer")]

        issues = await _run_qa_checks(row, ["term"], None, glossary)
        term_issues = [i for i in issues if i["check_type"] == "term"]
        assert len(term_issues) == 0

    @pytest.mark.asyncio
    async def test_term_check_multiple_terms_in_source(self):
        """Term Check should check all glossary terms found in source."""
        row = make_row(
            source="Iron Sword and Fire Shield",
            target="Epee et bouclier"  # Missing both translations
        )
        glossary = [
            ("Iron Sword", "Epee de fer"),
            ("Fire Shield", "Bouclier de feu"),
        ]

        issues = await _run_qa_checks(row, ["term"], None, glossary)
        term_issues = [i for i in issues if i["check_type"] == "term"]
        assert len(term_issues) == 2


# =============================================================================
# Full Line Check Pipeline
# =============================================================================

class TestLineCheckPipeline:
    """Test Line Check: same source text with different target translations."""

    @pytest.mark.asyncio
    async def test_line_check_flags_inconsistent_translations(self):
        """Line Check should flag rows with same source but different targets."""
        rows = [
            make_row(id=1, row_num=1, source="Attack Power", target="Puissance d'attaque"),
            make_row(id=2, row_num=2, source="Attack Power", target="Force d'attaque"),  # Different!
            make_row(id=3, row_num=3, source="Defense", target="Defense"),
        ]

        # Check row 1 — should flag row 2 as inconsistent
        issues = await _run_qa_checks(rows[0], ["line"], rows, None)
        line_issues = [i for i in issues if i["check_type"] == "line"]

        assert len(line_issues) >= 1
        assert line_issues[0]["details"]["other_row_num"] == 2

    @pytest.mark.asyncio
    async def test_line_check_no_flag_for_consistent_translations(self):
        """Line Check should NOT flag when all same-source rows have same target."""
        rows = [
            make_row(id=1, row_num=1, source="Attack Power", target="Puissance d'attaque"),
            make_row(id=2, row_num=2, source="Attack Power", target="Puissance d'attaque"),
        ]

        issues = await _run_qa_checks(rows[0], ["line"], rows, None)
        line_issues = [i for i in issues if i["check_type"] == "line"]
        assert len(line_issues) == 0

    @pytest.mark.asyncio
    async def test_line_check_with_prebuilt_index(self):
        """Line Check with pre-built index should be equivalent to on-the-fly."""
        rows = [
            make_row(id=1, row_num=1, source="HP", target="PV"),
            make_row(id=2, row_num=2, source="HP", target="Points de vie"),
        ]
        index = _build_line_check_index(rows)

        issues = await _run_qa_checks(
            rows[0], ["line"], None, None,
            line_check_index=index
        )
        line_issues = [i for i in issues if i["check_type"] == "line"]
        assert len(line_issues) >= 1


# =============================================================================
# Summary Counts
# =============================================================================

class TestQASummaryCounts:
    """Test QA summary endpoint returns correct counts."""

    @pytest.fixture
    def mock_repos(self):
        qa_repo = MagicMock()
        row_repo = MagicMock()
        file_repo = MagicMock()
        tm_repo = MagicMock()
        return {"qa_repo": qa_repo, "row_repo": row_repo, "file_repo": file_repo, "tm_repo": tm_repo}

    @pytest.fixture
    def client_with_repos(self, mock_repos):
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

    def test_summary_returns_per_type_counts(self, client_with_repos):
        """GET /files/{file_id}/qa-summary should return line, term, pattern, total counts."""
        client, repos = client_with_repos

        repos["qa_repo"].get_summary = AsyncMock(return_value={
            "line": 3,
            "term": 5,
            "pattern": 2,
            "total": 10,
            "last_checked": "2025-06-01T00:00:00",
        })

        response = client.get("/api/ldm/files/1/qa-summary")
        assert response.status_code == 200

        data = response.json()
        assert data["line"] == 3
        assert data["term"] == 5
        assert data["pattern"] == 2
        assert data["total"] == 10

    def test_summary_with_zero_counts(self, client_with_repos):
        """Summary should handle zero counts (no issues found)."""
        client, repos = client_with_repos

        repos["qa_repo"].get_summary = AsyncMock(return_value={
            "line": 0, "term": 0, "pattern": 0, "total": 0,
            "last_checked": "2025-06-01T00:00:00",
        })

        response = client.get("/api/ldm/files/1/qa-summary")
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 0


# =============================================================================
# Resolve / Dismiss End-to-End
# =============================================================================

class TestResolveEndToEnd:
    """Test resolve/dismiss workflow end-to-end."""

    @pytest.fixture
    def mock_repos(self):
        qa_repo = MagicMock()
        row_repo = MagicMock()
        file_repo = MagicMock()
        tm_repo = MagicMock()
        return {"qa_repo": qa_repo, "row_repo": row_repo, "file_repo": file_repo, "tm_repo": tm_repo}

    @pytest.fixture
    def client_with_repos(self, mock_repos):
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

    def test_resolve_marks_issue_as_resolved(self, client_with_repos):
        """POST /qa-results/{id}/resolve should mark the issue as resolved."""
        client, repos = client_with_repos

        repos["qa_repo"].get = AsyncMock(return_value={
            "id": 42,
            "row_id": 1,
            "check_type": "term",
            "severity": "warning",
            "message": "Missing term 'Sword'",
            "resolved_at": None,
        })
        repos["qa_repo"].resolve = AsyncMock(return_value=True)

        response = client.post("/api/ldm/qa-results/42/resolve")
        assert response.status_code == 200
        assert response.json()["status"] == "resolved"

        # Verify resolve was called with result_id and user_id
        repos["qa_repo"].resolve.assert_called_once_with(42, 1)

    def test_resolve_nonexistent_returns_404(self, client_with_repos):
        """Resolving non-existent issue returns 404."""
        client, repos = client_with_repos
        repos["qa_repo"].get = AsyncMock(return_value=None)

        response = client.post("/api/ldm/qa-results/999/resolve")
        assert response.status_code == 404

    def test_resolve_already_resolved_returns_400(self, client_with_repos):
        """Resolving already-resolved issue returns 400."""
        client, repos = client_with_repos

        repos["qa_repo"].get = AsyncMock(return_value={
            "id": 42,
            "row_id": 1,
            "check_type": "term",
            "severity": "warning",
            "message": "Missing term 'Sword'",
            "resolved_at": "2025-06-01T00:00:00",
        })

        response = client.post("/api/ldm/qa-results/42/resolve")
        assert response.status_code == 400


# =============================================================================
# Resolved Issues Persist Across Re-runs
# =============================================================================

class TestResolvedPersistence:
    """Test that resolved issues are not recreated when QA is re-run."""

    @pytest.mark.asyncio
    async def test_save_qa_results_deletes_unresolved_only(self):
        """_save_qa_results should call delete_unresolved_for_row, not delete_all."""
        qa_repo = MagicMock()
        qa_repo.delete_unresolved_for_row = AsyncMock()
        qa_repo.bulk_create = AsyncMock()
        qa_repo.get_for_row = AsyncMock(return_value=[
            {"id": 1, "row_id": 1, "file_id": 1, "check_type": "pattern",
             "severity": "error", "message": "Test", "details": None,
             "created_at": "2025-01-01T00:00:00", "resolved_at": None}
        ])

        issues = [{"check_type": "pattern", "severity": "error", "message": "Test"}]
        await _save_qa_results(qa_repo, row_id=1, file_id=1, issues=issues)

        # Verify delete_unresolved_for_row was called (preserving resolved)
        qa_repo.delete_unresolved_for_row.assert_called_once_with(1)
        qa_repo.bulk_create.assert_called_once()


# =============================================================================
# Combined Pipeline Test
# =============================================================================

class TestCombinedPipeline:
    """Test running all QA checks together on realistic game data."""

    @pytest.mark.asyncio
    async def test_full_pipeline_on_game_data(self):
        """Run term + line + pattern checks on game-like data."""
        # Simulate game data rows
        rows = [
            make_row(id=1, row_num=1,
                     source="{0}의 Iron Sword 공격",
                     target="Attack of {0}"),  # Has {0}, missing "Epee de fer"
            make_row(id=2, row_num=2,
                     source="HP Recovery",
                     target="Recuperation de PV"),
            make_row(id=3, row_num=3,
                     source="HP Recovery",
                     target="Recuperation HP"),  # Different from row 2!
        ]

        glossary = [("Iron Sword", "Epee de fer")]

        # Check row 1: should have term issue (missing glossary)
        issues_r1 = await _run_qa_checks(rows[0], ["pattern", "line", "term"], rows, glossary)

        # Row 1 should have term issue but no pattern issue (both have {0})
        term_issues = [i for i in issues_r1 if i["check_type"] == "term"]
        pattern_issues = [i for i in issues_r1 if i["check_type"] == "pattern"]
        assert len(term_issues) >= 1, "Should flag missing 'Epee de fer'"
        assert len(pattern_issues) == 0, "Pattern {0} is present in both"

        # Check row 2: should have line issue (inconsistent with row 3)
        issues_r2 = await _run_qa_checks(rows[1], ["line"], rows, None)
        line_issues = [i for i in issues_r2 if i["check_type"] == "line"]
        assert len(line_issues) >= 1, "Should flag inconsistent 'HP Recovery' translation"

    @pytest.mark.asyncio
    async def test_noise_filter_on_frequent_terms(self):
        """Noise filter should remove terms that trigger too many times."""
        # Create 7 issues for "Attack" (exceeds MAX_ISSUES_PER_TERM=6)
        issues = []
        for i in range(7):
            issues.append({
                "check_type": "term",
                "severity": "warning",
                "message": f"Missing term 'Attack'",
                "details": {"glossary_source": "Attack", "glossary_target": "Attaque"}
            })
        # Add 1 issue for "Defense" (under threshold)
        issues.append({
            "check_type": "term",
            "severity": "warning",
            "message": "Missing term 'Defense'",
            "details": {"glossary_source": "Defense", "glossary_target": "Defense"}
        })

        filtered = _apply_noise_filter(issues)
        assert len(filtered) == 1
        assert filtered[0]["details"]["glossary_source"] == "Defense"
